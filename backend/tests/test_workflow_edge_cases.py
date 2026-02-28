import uuid

import httpx
import pytest
from concurrent.futures import ThreadPoolExecutor
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app import statuses
from app.activities.step_activities import (
    execute_step,
    get_idle_versions,
    update_batch_status,
)
from app.core.config import get_settings
from app.main import app
from app.models import Batch, WorkflowNodeVersion
from app.workflows.batch_workflow import BatchWorkflow
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_rollback_invalid_step_index_returns_404(db_session):
    """Rollback with a step_index not in the template should return 404."""
    batch = Batch(name="Invalid Rollback", status=statuses.COMPLETED)
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/batches/{batch.id}/rollback",
            json={"from_step_index": 99},
        )
        assert resp.status_code == 404
        assert "Step index not found" in resp.json()["detail"]


def test_step3_without_construct_raises_error(db_session):
    """Step 3 execution with no construct from step 2 should raise ValueError."""
    batch = Batch(name="Missing Construct")
    db_session.add(batch)
    db_session.commit()

    nv = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=3,
        version=1,
        status=statuses.IDLE,
    )
    db_session.add(nv)
    db_session.commit()

    with pytest.raises(ValueError, match="No construct available"):
        execute_step(batch.id, 3, nv.id)


@pytest.mark.anyio
async def test_run_with_no_idle_versions_completes(db_session):
    """Running a batch with no idle node versions should complete without error."""
    settings = get_settings()
    batch = Batch(name="Empty Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

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
                    resp = await client.post(f"/api/batches/{batch.id}/run")
                    assert resp.status_code == 200
                    assert resp.json()["status"] == statuses.COMPLETED

            executor.shutdown(wait=True)
    finally:
        set_client_override(None)
