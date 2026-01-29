from concurrent.futures import ThreadPoolExecutor
import uuid

import httpx
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app import statuses
from app.activities.step_activities import (
    execute_step,
    get_idle_versions,
    update_batch_status,
    create_node_version,
    get_template_step_indices,
    get_latest_version_for_step,
)
from app.core.config import get_settings
from app.main import app
from app.models import Batch, LineageEdge, WorkflowNodeVersion
from app.workflows.batch_workflow import BatchWorkflow
from app.workflows.runner import set_client_override


@pytest.mark.anyio
async def test_rollback_creates_new_versions(db_session):
    settings = get_settings()

    batch = Batch(name="Rollback Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # Seed completed versions for step 1 and 2
    v1 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=1,
        status=statuses.COMPLETED,
    )
    v2 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=2,
        version=1,
        status=statuses.COMPLETED,
    )
    db_session.add_all([v1, v2])
    db_session.commit()
    old_v2_id = v2.id
    old_v2_status = v2.status
    old_v2_artifact_uri = v2.artifact_uri

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

                # Wait for workflow to finish processing rollback
                handle = env.client.get_workflow_handle(f"batch-workflow-{batch.id}")
                await handle.result()

            executor.shutdown(wait=True)

        versions = (
            db_session.query(WorkflowNodeVersion)
            .filter(WorkflowNodeVersion.batch_id == batch.id)
            .order_by(WorkflowNodeVersion.step_index, WorkflowNodeVersion.version)
            .all()
        )
        # Expect old versions still present and new versions for steps 2 and 3
        step2_versions = [v for v in versions if v.step_index == 2]
        step3_versions = [v for v in versions if v.step_index == 3]

        assert len(step2_versions) == 2  # old + new
        assert step2_versions[-1].version == 2
        assert step2_versions[-1].status == statuses.COMPLETED

        assert len(step3_versions) == 1
        assert step3_versions[0].version == 1
        assert step3_versions[0].status == statuses.COMPLETED

        # rollback lineage: old step2 -> new step2
        old_step2 = next(v for v in step2_versions if v.version == 1)
        new_step2 = next(v for v in step2_versions if v.version == 2)

        edge = (
            db_session.query(LineageEdge)
            .filter(
                LineageEdge.source_node_version_id == old_step2.id,
                LineageEdge.target_node_version_id == new_step2.id,
                LineageEdge.relation == "rollback",
            )
            .one_or_none()
        )
        assert edge is not None

        # ensure old node_version remains unchanged
        db_session.refresh(old_step2)
        assert old_step2.id == old_v2_id
        assert old_step2.status == old_v2_status
        assert old_step2.artifact_uri == old_v2_artifact_uri
    finally:
        set_client_override(None)
