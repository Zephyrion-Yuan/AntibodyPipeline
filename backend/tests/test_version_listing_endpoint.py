import httpx
import pytest

from app import statuses
from app.main import app
from app.models import Batch, WorkflowNodeVersion, LineageEdge


@pytest.mark.anyio
async def test_list_versions_returns_desc_order_with_lineage(db_session):
    batch = Batch(name="Version List")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # create two versions for step 1
    v1 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=1,
        status=statuses.COMPLETED,
        params={"a": 1},
    )
    v2 = WorkflowNodeVersion(
        batch_id=batch.id,
        template_version="v1",
        step_index=1,
        version=2,
        status=statuses.IDLE,
        params={"b": 2},
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
        resp = await client.get(f"/api/batches/{batch.id}/steps/1/versions")
    assert resp.status_code == 200
    body = resp.json()
    versions = body["versions"]
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[0]["params"] == {"b": 2}
    assert versions[1]["params"] == {"a": 1}

    # lineage references exist for v2 (from v1)
    v2_lineage = versions[0]["lineage"]
    assert len(v2_lineage) == 1
    assert v2_lineage[0]["relation"] == "rollback"
    assert v2_lineage[0]["target_type"] == "node"
