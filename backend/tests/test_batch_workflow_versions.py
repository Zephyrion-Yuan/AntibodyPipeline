import uuid
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.core.config import get_settings
from app.main import app
from app import statuses
from app.models import Batch, WorkflowNodeVersion
from app.workflows.batch_workflow import BatchWorkflow
from app.activities.step_activities import execute_step, update_batch_status, get_idle_versions
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_run_executes_only_latest_idle_versions(db_session):
    settings = get_settings()

    batch = Batch(name="Versioned Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # Existing completed version should not be rerun
    completed_v1 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        status=statuses.COMPLETED,
        artifact_uri="/tmp/old.txt",
    )
    db_session.add(completed_v1)

    # Two idle versions for step_index 2; only latest should run
    now = datetime.now(timezone.utc)
    idle_old = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=2,
        status=statuses.IDLE,
        created_at=now - timedelta(seconds=5),
        updated_at=now - timedelta(seconds=5),
    )
    db_session.add(idle_old)
    db_session.flush()

    idle_new = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=2,
        status=statuses.IDLE,
        created_at=now,
        updated_at=now,
    )
    db_session.add(idle_new)

    # idle for step 3
    idle_three = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=3,
        status=statuses.IDLE,
    )
    db_session.add(idle_three)
    db_session.commit()

    # Creating idle versions alone should not change status
    db_session.refresh(idle_old)
    db_session.refresh(idle_new)
    db_session.refresh(idle_three)
    assert idle_new.status == statuses.IDLE
    assert idle_three.status == statuses.IDLE
    assert idle_old.created_at < idle_new.created_at
    pending = get_idle_versions(batch.id)
    assert {"step_index": 2, "node_version_id": str(idle_new.id)} in pending
    assert {"step_index": 3, "node_version_id": str(idle_three.id)} in pending

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
                    assert response.json()["status"] == statuses.COMPLETED

            executor.shutdown(wait=True)

        # Refresh from DB
        versions = (
            db_session.query(WorkflowNodeVersion)
            .filter(WorkflowNodeVersion.batch_id == batch.id)
            .order_by(WorkflowNodeVersion.step_index, WorkflowNodeVersion.created_at)
            .all()
        )

        # step_index 1 should remain completed (was not rerun)
        step1_versions = [v for v in versions if v.step_index == 1]
        assert len(step1_versions) == 1
        assert step1_versions[0].status == statuses.COMPLETED

        # step_index 2 latest idle should now be completed, older idle unchanged
        step2_versions = [v for v in versions if v.step_index == 2]
        assert len(step2_versions) == 2
        db_session.refresh(idle_new)
        db_session.refresh(idle_old)
        latest_step2 = max(step2_versions, key=lambda v: v.created_at)
        oldest_step2 = min(step2_versions, key=lambda v: v.created_at)
        assert idle_new.status == statuses.COMPLETED
        assert idle_old.status == statuses.IDLE

        # step_index 3 idle should be completed
        step3_versions = [v for v in versions if v.step_index == 3]
        db_session.refresh(idle_three)
        assert idle_three.status == statuses.COMPLETED, f"step3 status {idle_three.status}"
    finally:
        set_client_override(None)
