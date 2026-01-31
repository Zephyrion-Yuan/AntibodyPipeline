import pathlib
import uuid
from typing import Optional

from temporalio import activity

from app.db.session import SessionLocal
from app.models import (
    Artifact,
    Batch,
    Chain,
    Construct,
    ConstructChain,
    LineageEdge,
    WorkflowNodeVersion,
    WorkflowTemplateStep,
)
from app import statuses


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
                    WorkflowNodeVersion.version.desc(),
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
def execute_step(
    batch_id: uuid.UUID,
    step_index: int,
    node_version_id: uuid.UUID | str,
    parent_node_version_id: uuid.UUID | str | None = None,
) -> str:
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

        parent_version = None
        if parent_node_version_id:
            parent_version = session.get(WorkflowNodeVersion, uuid.UUID(str(parent_node_version_id)))

        node_version.status = "running"
        session.add(node_version)
        session.commit()

        node_version.status = "completed"
        node_version.artifact_uri = artifact_uri
        session.add(node_version)

        # create artifact and lineage to artifact
        artifact = None
        if artifact_uri:
            artifact = Artifact(
                node_version_id=node_version.id,
                uri=artifact_uri,
                content_type="text/plain",
            )
            session.add(artifact)
            session.flush()
            session.add(
                LineageEdge(
                    source_node_version_id=node_version.id,
                    target_artifact_id=artifact.id,
                    relation="artifact",
                )
            )

        # Chain production: step_index 1 assumed to create chain
        if step_index == 1:
            chain = Chain(
                node_version_id=node_version.id,
                name=f"chain-{node_version.version}",
                sequence=(node_version.params or {}).get("sequence"),
            )
            session.add(chain)
            session.flush()
            if parent_version and parent_version.params != node_version.params:
                session.add(
                    LineageEdge(
                        source_node_version_id=parent_version.id,
                        target_node_version_id=node_version.id,
                        relation="derive",
                    )
                )

        # Construct production: step_index 2 combines existing chains
        if step_index == 2:
            chains = (
                session.query(Chain)
                .join(WorkflowNodeVersion, Chain.node_version_id == WorkflowNodeVersion.id)
                .filter(WorkflowNodeVersion.batch_id == batch_id)
                .all()
            )
            construct = Construct(
                node_version_id=node_version.id,
                name=f"construct-{node_version.version}",
            )
            session.add(construct)
            session.flush()
            for chain in chains:
                session.add(
                    ConstructChain(construct_id=construct.id, chain_id=chain.id)
                )
                session.add(
                    LineageEdge(
                        source_node_version_id=chain.node_version_id,
                        target_construct_id=construct.id,
                        relation="derive",
                    )
                )
            session.add(
                LineageEdge(
                    source_node_version_id=node_version.id,
                    target_construct_id=construct.id,
                    relation="construct",
                )
            )

        # Step 3 consumes a construct; record the exact construct used
        if step_index == 3:
            if node_version.input_construct_id:
                construct = session.get(Construct, node_version.input_construct_id)
            else:
                construct = (
                    session.query(Construct)
                    .join(WorkflowNodeVersion, Construct.node_version_id == WorkflowNodeVersion.id)
                    .filter(
                        WorkflowNodeVersion.batch_id == batch_id,
                        WorkflowNodeVersion.step_index == 2,
                    )
                    .order_by(
                        WorkflowNodeVersion.version.desc(),
                        WorkflowNodeVersion.created_at.desc(),
                        Construct.created_at.desc(),
                        Construct.id.desc(),
                    )
                    .first()
                )
                if construct:
                    node_version.input_construct_id = construct.id
                    session.add(node_version)
            if construct is None:
                raise ValueError("No construct available for step 3 consumption")

        session.commit()

    return artifact_uri or ""


@activity.defn(name="create_node_version")
def create_node_version(
    batch_id: uuid.UUID,
    step_index: int,
    parent_node_version_id: uuid.UUID | None = None,
    relation: str | None = None,
) -> str:
    with SessionLocal() as session:
        previous = None
        if parent_node_version_id:
            previous = session.get(WorkflowNodeVersion, parent_node_version_id)
        if previous is None:
            previous = (
                session.query(WorkflowNodeVersion)
                .filter(
                    WorkflowNodeVersion.batch_id == batch_id,
                    WorkflowNodeVersion.step_index == step_index,
                )
                .order_by(
                    WorkflowNodeVersion.version.desc(),
                    WorkflowNodeVersion.created_at.desc(),
                    WorkflowNodeVersion.updated_at.desc(),
                    WorkflowNodeVersion.id.desc(),
                )
                .first()
            )
        new_version = ((previous.version if previous else 0) + 1)
        node_version = WorkflowNodeVersion(
            batch_id=batch_id,
            template_version="v1",
            step_index=step_index,
            version=new_version,
            status=statuses.IDLE,
        )
        session.add(node_version)
        session.flush()

        if previous is not None and relation:
            session.add(
                LineageEdge(
                    source_node_version_id=previous.id,
                    target_node_version_id=node_version.id,
                    relation=relation,
                )
            )
        session.commit()
        return str(node_version.id)


@activity.defn(name="get_template_step_indices")
def get_template_step_indices() -> list[int]:
    with SessionLocal() as session:
        return [
            row[0]
            for row in session.query(WorkflowTemplateStep.step_index)
            .filter(WorkflowTemplateStep.template_version == "v1")
            .order_by(WorkflowTemplateStep.step_index)
            .all()
        ]


@activity.defn(name="get_latest_version_for_step")
def get_latest_version_for_step(batch_id: uuid.UUID, step_index: int) -> str | None:
    with SessionLocal() as session:
        latest = (
            session.query(WorkflowNodeVersion)
            .filter(
                WorkflowNodeVersion.batch_id == batch_id,
                WorkflowNodeVersion.step_index == step_index,
            )
            .order_by(
                WorkflowNodeVersion.version.desc(),
                WorkflowNodeVersion.created_at.desc(),
                WorkflowNodeVersion.updated_at.desc(),
                WorkflowNodeVersion.id.desc(),
            )
            .first()
        )
        return str(latest.id) if latest else None
