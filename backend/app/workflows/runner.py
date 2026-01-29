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


async def start_batch_workflow(batch_id: uuid.UUID, wait_for_result: bool = True) -> str:
    client = await get_temporal_client()
    handle = await client.start_workflow(
        BatchWorkflow.run,
        id=f"batch-workflow-{batch_id}",
        task_queue=settings.temporal_task_queue,
        args=[str(batch_id), False],
    )
    if wait_for_result:
        await handle.result()
    return handle.id


async def send_rollback_signal(batch_id: uuid.UUID, from_step_index: int) -> str:
    client = await get_temporal_client()
    workflow_id = f"batch-workflow-{batch_id}"
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal("rollback", from_step_index)
        return handle.id
    except Exception:
        # Start workflow if not found, then signal
        handle = await client.start_workflow(
            BatchWorkflow.run,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            args=[str(batch_id), True],
        )
        await handle.signal("rollback", from_step_index)
        return handle.id
    await handle.signal("rollback", from_step_index)
    return handle.id
