from pydantic import BaseModel, Field


class UpdateParamsRequest(BaseModel):
    params: dict = Field(default_factory=dict)


class WorkflowNodeVersionResponse(BaseModel):
    id: str
    batch_id: str
    step_index: int
    version: int
    status: str
    params: dict | None
    template_version: str


class RollbackRequest(BaseModel):
    from_step_index: int

class RollbackRequest(BaseModel):
    from_step_index: int
