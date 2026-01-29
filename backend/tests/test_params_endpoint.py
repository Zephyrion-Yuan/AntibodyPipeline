import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app import statuses
from app.activities.step_activities import execute_step, get_idle_versions, update_batch_status
from app.core.config import get_settings
from app.main import app
from app.models import Batch, WorkflowNodeVersion
from app.workflows.batch_workflow import BatchWorkflow
from app.workflows import runner
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_patch_creates_new_idle_version_without_running_workflow(db_session, monkeypatch):
    settings = get_settings()
    batch = Batch(name="Param Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # Seed an existing completed version for step 1
    existing = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=1,
        status=statuses.COMPLETED,
    )
    db_session.add(existing)
    db_session.commit()

    called = False

    async def fake_start(*args, **kwargs):  # noqa: ARG001
        nonlocal called
        called = True
        raise AssertionError("Temporal should not be triggered by params patch")

    monkeypatch.setattr(runner, "start_batch_workflow", fake_start)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/batches/{batch.id}/steps/1/params",
            json={"params": {"alpha": 1}},
        )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["version"] == 2
    assert payload["status"] == statuses.IDLE
    assert payload["params"] == {"alpha": 1}
    assert called is False

    versions = (
        db_session.query(WorkflowNodeVersion)
        .filter(WorkflowNodeVersion.batch_id == batch.id, WorkflowNodeVersion.step_index == 1)
        .order_by(WorkflowNodeVersion.version)
        .all()
    )
    assert [v.version for v in versions] == [1, 2]
    assert versions[-1].status == statuses.IDLE
    assert versions[0].status == statuses.COMPLETED
    db_session.refresh(batch)
    assert batch.status == statuses.PENDING


@pytest.mark.anyio
async def test_run_executes_only_latest_idle_version_after_params_update(db_session):
    settings = get_settings()
    batch = Batch(name="Run After Params")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # existing completed version for step 1
    completed = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=1,
        status=statuses.COMPLETED,
    )
    db_session.add(completed)
    db_session.commit()

    # create new idle via API
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/batches/{batch.id}/steps/1/params",
            json={"params": {"beta": 2}},
        )
    assert resp.status_code == 201
    new_version_id = uuid.UUID(resp.json()["id"])

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
                    run_resp = await client.post(f"/api/batches/{batch.id}/run")
                    assert run_resp.status_code == 200
                    assert run_resp.json()["status"] == statuses.COMPLETED
            executor.shutdown(wait=True)

        # verify statuses
        versions = (
            db_session.query(WorkflowNodeVersion)
            .filter(WorkflowNodeVersion.batch_id == batch.id, WorkflowNodeVersion.step_index == 1)
            .order_by(WorkflowNodeVersion.version)
            .all()
        )
        assert len(versions) == 2
        assert versions[0].status == statuses.COMPLETED  # old
        latest = versions[1]
        assert latest.id == new_version_id
        assert latest.status == statuses.COMPLETED
        assert latest.params == {"beta": 2}
    finally:
        set_client_override(None)
