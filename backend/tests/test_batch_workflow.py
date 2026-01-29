import asyncio
import httpx
import pytest
from concurrent.futures import ThreadPoolExecutor
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.activities.step_activities import execute_step, get_idle_versions, update_batch_status
from app.core.config import get_settings
from app.main import app
from app import statuses
from app.models import Batch, WorkflowNodeVersion
from app.workflows.batch_workflow import BatchWorkflow
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_run_endpoint_triggers_workflow(db_session):
    settings = get_settings()
    batch = Batch(name="Temporal Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # seed idle versions for steps 1-3
    idle_versions = [
        WorkflowNodeVersion(batch_id=batch.id, template_version="v1", step_index=i, status=statuses.IDLE)
        for i in [1, 2, 3]
    ]
    db_session.add_all(idle_versions)
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
                activities=[execute_step, update_batch_status, get_idle_versions],
                activity_executor=executor,
            )

            async with worker:
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(f"/api/batches/{batch.id}/run")
                    assert response.status_code == 200
                    payload = response.json()
                    assert payload["batch_id"] == str(batch.id)
                    assert payload["status"] == "completed"

            # After worker finishes, verify node versions created in order
            versions = (
                db_session.query(WorkflowNodeVersion)
                .filter(WorkflowNodeVersion.batch_id == batch.id)
                .order_by(WorkflowNodeVersion.step_index)
                .all()
            )
            assert [v.step_index for v in versions] == [1, 2, 3]
            assert all(v.status == "completed" for v in versions)
            executor.shutdown(wait=True)
    finally:
        set_client_override(None)
