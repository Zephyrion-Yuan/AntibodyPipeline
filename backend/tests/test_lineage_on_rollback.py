from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app import statuses
from app.activities.step_activities import (
    execute_step,
    update_batch_status,
    get_idle_versions,
    create_node_version,
    get_template_step_indices,
    get_latest_version_for_step,
)
from app.core.config import get_settings
from app.main import app
from app.models import Batch, WorkflowNodeVersion, LineageEdge
from app.workflows.batch_workflow import BatchWorkflow
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_rollback_creates_lineage_edge(db_session):
    settings = get_settings()

    batch = Batch(name="Lineage Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    old_v2 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=2,
        version=1,
        status=statuses.COMPLETED,
    )
    db_session.add(old_v2)
    db_session.commit()

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

        # Verify new version and lineage
        versions = (
            db_session.query(WorkflowNodeVersion)
            .filter(WorkflowNodeVersion.batch_id == batch.id, WorkflowNodeVersion.step_index == 2)
            .order_by(WorkflowNodeVersion.version)
            .all()
        )
        assert [v.version for v in versions] == [1, 2]
        assert versions[-1].status == statuses.COMPLETED
        edges = (
            db_session.query(LineageEdge)
            .filter(LineageEdge.relation == "rollback")
            .all()
        )
        assert len(edges) == 1
        rollback_edge = edges[0]
        assert rollback_edge.source_node_version_id == old_v2.id
        assert rollback_edge.target_node_version_id == versions[-1].id
    finally:
        set_client_override(None)
