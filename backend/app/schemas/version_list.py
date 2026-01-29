from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LineageRef(BaseModel):
    id: str
    relation: str
    target_type: str  # "node" or "artifact"


class NodeVersionListItem(BaseModel):
    id: str
    version: int
    status: str
    params: dict | None
    created_at: datetime
    lineage: List[LineageRef]


class NodeVersionListResponse(BaseModel):
    batch_id: str
    step_index: int
    versions: List[NodeVersionListItem]
