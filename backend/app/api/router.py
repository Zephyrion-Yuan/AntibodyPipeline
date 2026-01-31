import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app import statuses
from app.models import Batch, WorkflowTemplateStep, WorkflowNodeVersion, LineageEdge, Artifact, Chain
from app.schemas.params import UpdateParamsRequest, WorkflowNodeVersionResponse, RollbackRequest
from app.schemas.version_list import NodeVersionListResponse, NodeVersionListItem, LineageRef
from app.schemas.lineage import LineageResponse, LineageEdgeOut, EntityType
from app.workflows.runner import start_batch_workflow, send_rollback_signal

api_router = APIRouter(prefix="/api")


@api_router.get("/batches/{batch_id}/graph")
def get_batch_graph(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    steps = (
        db.query(WorkflowTemplateStep)
        .filter(WorkflowTemplateStep.template_version == "v1")
        .order_by(WorkflowTemplateStep.step_index)
        .all()
    )

    nodes = [
        {
            "id": str(step.id),
            "type": "default",
            "data": {"label": step.name, "step_index": step.step_index},
            # simple layout: vertical stacking by step_index
            "position": {"x": 100, "y": step.step_index * 150},
            "draggable": False,
        }
        for step in steps
    ]

    edges = [
        {
            "id": f"{curr.id}->{nxt.id}",
            "source": str(curr.id),
            "target": str(nxt.id),
            "type": "default",
        }
        for curr, nxt in zip(steps, steps[1:])
    ]

    return {
        "batch_id": str(batch_id),
        "template_version": "v1",
        "nodes": nodes,
        "edges": edges,
    }


@api_router.post("/batches/{batch_id}/run")
async def run_batch(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    run_id = await start_batch_workflow(batch_id)
    # Refresh batch status after workflow completion
    db.refresh(batch)
    return {"run_id": run_id, "batch_id": str(batch_id), "status": batch.status}


@api_router.post("/batches/{batch_id}/rollback")
async def rollback_batch(
    batch_id: uuid.UUID,
    payload: RollbackRequest,
    db: Session = Depends(get_db),
):
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    await send_rollback_signal(batch_id, payload.from_step_index)
    return {
        "batch_id": str(batch_id),
        "from_step_index": payload.from_step_index,
        "status": "signaled",
    }


@api_router.get(
    "/batches/{batch_id}/steps/{step_index}/versions",
    response_model=NodeVersionListResponse,
)
def list_step_versions(
    batch_id: uuid.UUID,
    step_index: int,
    db: Session = Depends(get_db),
):
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    versions = (
        db.query(WorkflowNodeVersion)
        .filter(
            WorkflowNodeVersion.batch_id == batch_id,
            WorkflowNodeVersion.step_index == step_index,
        )
        .order_by(WorkflowNodeVersion.version.desc())
        .all()
    )

    def lineage_for(node_id: uuid.UUID) -> list[LineageRef]:
        edges = db.query(LineageEdge).filter(LineageEdge.target_node_version_id == node_id).all()
        refs: list[LineageRef] = []
        for edge in edges:
            if edge.target_node_version_id:
                refs.append(
                    LineageRef(
                        id=str(edge.id),
                        relation=edge.relation,
                        target_type="node",
                    )
                )
            if edge.target_artifact_id:
                refs.append(
                    LineageRef(
                        id=str(edge.id),
                        relation=edge.relation,
                        target_type="artifact",
                    )
                )
        return refs

    return NodeVersionListResponse(
        batch_id=str(batch_id),
        step_index=step_index,
        versions=[
            NodeVersionListItem(
                id=str(v.id),
                version=v.version,
                status=v.status,
                params=v.params,
                created_at=v.created_at,
                lineage=lineage_for(v.id),
            )
            for v in versions
        ],
    )


@api_router.get("/lineage/{entity_type}/{entity_id}", response_model=LineageResponse)
def get_lineage(
    entity_type: EntityType,
    entity_id: str,
    depth: int = 5,
    db: Session = Depends(get_db),
):
    if depth <= 0:
        raise HTTPException(status_code=400, detail="Depth must be positive")

    def resolve_node_version_id(et: EntityType, eid: str) -> uuid.UUID:
        if et == "node_version":
            node = db.get(WorkflowNodeVersion, uuid.UUID(eid))
            if not node:
                raise HTTPException(status_code=404, detail="Node version not found")
            return node.id
        if et == "artifact":
            art = db.get(Artifact, uuid.UUID(eid))
            if not art:
                raise HTTPException(status_code=404, detail="Artifact not found")
            return art.node_version_id
        if et == "chain":
            chain = db.get(Chain, uuid.UUID(eid))
            if not chain:
                raise HTTPException(status_code=404, detail="Chain not found")
            return chain.node_version_id
        raise HTTPException(status_code=400, detail="Unsupported entity type")

    start_node_id = resolve_node_version_id(entity_type, entity_id)

    visited = set()
    edges_out: list[LineageEdgeOut] = []

    frontier = [(start_node_id, 0)]
    while frontier:
        current_id, d = frontier.pop(0)
        if d >= depth:
            continue
        upstream_edges = (
            db.query(LineageEdge)
            .filter(LineageEdge.target_node_version_id == current_id)
            .all()
        )
        for edge in upstream_edges:
            edges_out.append(
                LineageEdgeOut(
                    id=str(edge.id),
                    relation=edge.relation,
                    source_node_version_id=str(edge.source_node_version_id),
                    target_type="node_version",
                    target_id=str(current_id),
                    depth=d + 1,
                )
            )
            if edge.source_node_version_id not in visited:
                visited.add(edge.source_node_version_id)
                frontier.append((edge.source_node_version_id, d + 1))

    return LineageResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        depth_limit=depth,
        edges=edges_out,
    )


@api_router.patch(
    "/batches/{batch_id}/steps/{step_index}/params",
    response_model=WorkflowNodeVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def update_step_params(
    batch_id: uuid.UUID,
    step_index: int,
    payload: UpdateParamsRequest,
    db: Session = Depends(get_db),
):
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    template_step = (
        db.query(WorkflowTemplateStep)
        .filter(
            WorkflowTemplateStep.template_version == "v1",
            WorkflowTemplateStep.step_index == step_index,
        )
        .first()
    )
    if template_step is None:
        raise HTTPException(status_code=404, detail="Step not found")

    current_max_version = (
        db.query(func.max(WorkflowNodeVersion.version))
        .filter(
            WorkflowNodeVersion.batch_id == batch_id,
            WorkflowNodeVersion.step_index == step_index,
        )
        .scalar()
    ) or 0

    new_version = current_max_version + 1

    node_version = WorkflowNodeVersion(
        batch_id=batch_id,
        template_version="v1",
        step_index=step_index,
        version=new_version,
        status=statuses.IDLE,
        params=payload.params,
    )
    db.add(node_version)
    db.commit()
    db.refresh(node_version)

    return WorkflowNodeVersionResponse(
        id=str(node_version.id),
        batch_id=str(batch_id),
        step_index=step_index,
        version=node_version.version,
        status=node_version.status,
        params=node_version.params,
        template_version=node_version.template_version,
    )
