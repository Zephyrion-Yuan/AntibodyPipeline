from fastapi.testclient import TestClient

from app.main import app
from app.models import Batch


client = TestClient(app)


def test_graph_endpoint_returns_three_nodes_in_order(db_session):
    batch = Batch(name="Graph Batch")
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    response = client.get(f"/api/batches/{batch.id}/graph")
    assert response.status_code == 200

    payload = response.json()
    assert payload["template_version"] == "v1"

    nodes = payload["nodes"]
    edges = payload["edges"]

    assert len(nodes) == 3
    step_indices = [node["data"]["step_index"] for node in nodes]
    assert step_indices == [1, 2, 3]

    assert len(edges) == 2
    node_by_id = {node["id"]: node for node in nodes}
    for edge in edges:
        source_idx = node_by_id[edge["source"]]["data"]["step_index"]
        target_idx = node_by_id[edge["target"]]["data"]["step_index"]
        assert target_idx - source_idx == 1
