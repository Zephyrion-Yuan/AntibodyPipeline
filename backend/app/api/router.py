import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, WorkflowTemplateStep
from app.workflows.runner import start_batch_workflow

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
