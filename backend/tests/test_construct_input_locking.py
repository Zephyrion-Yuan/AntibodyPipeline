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
from app.models import Batch, Construct, WorkflowNodeVersion
from app.workflows.batch_workflow import BatchWorkflow
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_construct_input_requires_rollback_to_change(db_session):
    settings = get_settings()

    batch = Batch(name="Construct Input Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # Seed idle versions for steps 1-3
    step_versions = [
        WorkflowNodeVersion(batch_id=batch.id, template_version="v1", step_index=i, status=statuses.IDLE)
        for i in [1, 2, 3]
    ]
    db_session.add_all(step_versions)
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
                    run_resp = await client.post(f"/api/batches/{batch.id}/run")
                    assert run_resp.status_code == 200

                handle = env.client.get_workflow_handle(f"batch-workflow-{batch.id}")
                await handle.result()

                db_session.expire_all()
                constructs_initial = db_session.query(Construct).all()
                assert len(constructs_initial) == 1
                step3_versions = (
                    db_session.query(WorkflowNodeVersion)
                    .filter(WorkflowNodeVersion.batch_id == batch.id, WorkflowNodeVersion.step_index == 3)
                    .order_by(WorkflowNodeVersion.version)
                    .all()
                )
                assert len(step3_versions) == 1
                first_input = step3_versions[0].input_construct_id
                assert first_input is not None

                # Trigger rollback from step 2 to produce new construct and new step3 version
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    rollback_resp = await client.post(
                        f"/api/batches/{batch.id}/rollback",
                        json={"from_step_index": 2},
                    )
                    assert rollback_resp.status_code == 200

                handle = env.client.get_workflow_handle(f"batch-workflow-{batch.id}")
                await handle.result()

                db_session.expire_all()
                constructs_after = db_session.query(Construct).order_by(Construct.created_at).all()
                assert len(constructs_after) == 2

                step3_versions = (
                    db_session.query(WorkflowNodeVersion)
                    .filter(WorkflowNodeVersion.batch_id == batch.id, WorkflowNodeVersion.step_index == 3)
                    .order_by(WorkflowNodeVersion.version)
                    .all()
                )
                assert [v.version for v in step3_versions] == [1, 2]
                assert step3_versions[0].input_construct_id == first_input
                assert step3_versions[1].input_construct_id is not None
                assert step3_versions[1].input_construct_id != first_input

            executor.shutdown(wait=True)
    finally:
        set_client_override(None)
