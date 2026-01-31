from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app import statuses
from app.activities.step_activities import (
    create_node_version,
    execute_step,
    get_idle_versions,
    get_latest_version_for_step,
    get_template_step_indices,
    update_batch_status,
)
from app.core.config import get_settings
from app.main import app
from app.models import Batch, Chain, Construct, ConstructChain, LineageEdge, WorkflowNodeVersion
from app.workflows.batch_workflow import BatchWorkflow
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_construct_created_and_preserved_on_rollback(db_session):
    settings = get_settings()

    batch = Batch(name="Construct Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # Seed initial versions and produce chain (step 1) and construct (step 2)
    step1 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=1,
        status=statuses.IDLE,
        params={"sequence": "AAA"},
    )
    step2 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=2,
        version=1,
        status=statuses.IDLE,
    )
    db_session.add_all([step1, step2])
    db_session.commit()

    execute_step(batch.id, 1, step1.id)  # creates chain
    execute_step(batch.id, 2, step2.id)  # creates construct

    env = await WorkflowEnvironment.start_time_skipping()
    try:
        async with env:
            set_client_override(env.client)
            executor = ThreadPoolExecutor()
            worker = Worker(
                env.client,
                task_queue=settings.temporal_task_queue,
                workflows=[BatchWorkflow],
                activities=[
                    execute_step,
                    update_batch_status,
                    get_idle_versions,
                    create_node_version,
                    get_template_step_indices,
                    get_latest_version_for_step,
                ],
                activity_executor=executor,
            )

            async with worker:
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        f"/api/batches/{batch.id}/rollback", json={"from_step_index": 2}
                    )
                    assert resp.status_code == 200

                handle = env.client.get_workflow_handle(f"batch-workflow-{batch.id}")
                await handle.result()

            executor.shutdown(wait=True)

            db_session.expire_all()

            constructs = db_session.query(Construct).all()
        assert len(constructs) == 2

        chains = db_session.query(Chain).all()
        assert len(chains) == 1
        chain = chains[0]

        cc_links = db_session.query(ConstructChain).all()
        assert len(cc_links) == 2
        assert all(link.chain_id == chain.id for link in cc_links)

        derive_edges = (
            db_session.query(LineageEdge)
            .filter(LineageEdge.target_construct_id.isnot(None), LineageEdge.relation == "derive")
            .all()
        )
        assert len(derive_edges) == 2
        assert {edge.source_node_version_id for edge in derive_edges} == {chain.node_version_id}
        assert {edge.target_construct_id for edge in derive_edges} == {c.id for c in constructs}

        construct_edges = (
            db_session.query(LineageEdge)
            .filter(LineageEdge.relation == "construct")
            .all()
        )
        assert len(construct_edges) == 2
        assert {edge.target_construct_id for edge in construct_edges} == {c.id for c in constructs}

        step2_versions = (
            db_session.query(WorkflowNodeVersion)
            .filter(
                WorkflowNodeVersion.batch_id == batch.id,
                WorkflowNodeVersion.step_index == 2,
            )
            .order_by(WorkflowNodeVersion.version)
            .all()
        )
        assert [v.version for v in step2_versions] == [1, 2]
        status_values = [v.status for v in step2_versions]
        assert status_values == [statuses.COMPLETED, statuses.COMPLETED]
    finally:
        set_client_override(None)
