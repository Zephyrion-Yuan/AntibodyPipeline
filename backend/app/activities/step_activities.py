import pathlib
import uuid
from typing import Optional

from temporalio import activity

from app.db.session import SessionLocal
from app.models import Batch, WorkflowNodeVersion, WorkflowTemplateStep


def _mock_artifact_path(batch_id: uuid.UUID, step_index: int) -> str:
    artifacts_dir = pathlib.Path("/tmp/antibody_artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"batch_{batch_id}_step_{step_index}.txt"
    path.write_text(f"Mock artifact for batch {batch_id}, step {step_index}\n", encoding="utf-8")
    return str(path)


@activity.defn(name="update_batch_status")
def update_batch_status(batch_id: uuid.UUID, status: str) -> None:
    with SessionLocal() as session:
        batch = session.get(Batch, batch_id)
        if batch is None:
            raise ValueError(f"Batch {batch_id} not found")
        batch.status = status
        session.add(batch)
        session.commit()


@activity.defn(name="get_idle_versions")
def get_idle_versions(batch_id: uuid.UUID) -> list[dict]:
    """Return latest idle node_version per step_index, ordered by step_index."""
    with SessionLocal() as session:
        template_step_indices = [
            row[0]
            for row in session.query(WorkflowTemplateStep.step_index)
            .filter(WorkflowTemplateStep.template_version == "v1")
            .order_by(WorkflowTemplateStep.step_index)
            .all()
        ]

        pending: list[dict] = []
        for step_index in template_step_indices:
            latest = (
                session.query(WorkflowNodeVersion)
                .filter(
                    WorkflowNodeVersion.batch_id == batch_id,
                    WorkflowNodeVersion.step_index == step_index,
                    WorkflowNodeVersion.status == "idle",
                )
                .order_by(
                    WorkflowNodeVersion.created_at.desc(),
                    WorkflowNodeVersion.updated_at.desc(),
                    WorkflowNodeVersion.id.desc(),
                )
                .first()
            )
            if latest:
                pending.append(
                    {"step_index": step_index, "node_version_id": str(latest.id)}
                )
        return pending


@activity.defn(name="execute_step")
def execute_step(batch_id: uuid.UUID, step_index: int, node_version_id: uuid.UUID | str) -> str:
    """Mock computation for a template step; updates existing node version."""
    artifact_uri: Optional[str] = None
    if step_index in (1, 2, 3):
        artifact_uri = _mock_artifact_path(batch_id, step_index)

    with SessionLocal() as session:
        node_uuid = uuid.UUID(str(node_version_id))
        node_version = session.get(WorkflowNodeVersion, node_uuid)
        if node_version is None:
            raise ValueError(f"Node version {node_version_id} not found")
        if node_version.status != "idle":
            return node_version.artifact_uri or ""

        node_version.status = "running"
        session.add(node_version)
        session.commit()

        node_version.status = "completed"
        node_version.artifact_uri = artifact_uri
        session.add(node_version)
        session.commit()

    return artifact_uri or ""
