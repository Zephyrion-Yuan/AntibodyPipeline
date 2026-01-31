from typing import List, Literal
from pydantic import BaseModel

EntityType = Literal["node_version", "artifact", "chain"]


class LineageEdgeOut(BaseModel):
    id: str
    relation: str
    source_node_version_id: str
    target_type: Literal["node_version", "artifact"]
    target_id: str
    depth: int


class LineageResponse(BaseModel):
    entity_type: EntityType
    entity_id: str
    depth_limit: int
    edges: List[LineageEdgeOut]
