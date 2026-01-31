import httpx
import pytest

from app import statuses
from app.main import app
from app.models import Batch, WorkflowNodeVersion, LineageEdge


@pytest.mark.anyio
async def test_lineage_endpoint_returns_upstream_edges(db_session):
    batch = Batch(name="Lineage Endpoint")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

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
        step_index=1,
        version=2,
        status=statuses.COMPLETED,
    )
    db_session.add_all([v1, v2])
    db_session.flush()

    edge = LineageEdge(
        source_node_version_id=v1.id,
        target_node_version_id=v2.id,
        relation="rollback",
    )
    db_session.add(edge)
    db_session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/lineage/node_version/{v2.id}")
    assert resp.status_code == 200
    data = resp.json()
    edges = data["edges"]
    assert len(edges) == 1
    assert edges[0]["relation"] == "rollback"
    assert edges[0]["source_node_version_id"] == str(v1.id)
    assert edges[0]["target_id"] == str(v2.id)
