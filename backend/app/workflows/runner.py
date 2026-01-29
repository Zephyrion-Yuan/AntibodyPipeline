import uuid
from typing import Optional

from temporalio.client import Client

from app.core.config import get_settings
from app.workflows.batch_workflow import BatchWorkflow

settings = get_settings()

_client_override: Optional[Client] = None


def set_client_override(client: Optional[Client]) -> None:
    global _client_override
    _client_override = client


async def get_temporal_client() -> Client:
    if _client_override is not None:
        return _client_override
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


async def start_batch_workflow(batch_id: uuid.UUID) -> str:
    client = await get_temporal_client()
    handle = await client.start_workflow(
        BatchWorkflow.run,
        str(batch_id),
        id=f"batch-workflow-{batch_id}",
        task_queue=settings.temporal_task_queue,
    )
    # Wait for completion so API stays simple and tests can assert side effects
    await handle.result()
    return handle.id
