import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from app.activities.step_activities import execute_step, get_idle_versions, update_batch_status
from app.core.config import get_settings
from app.workflows.batch_workflow import BatchWorkflow


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    activity_executor = ThreadPoolExecutor()
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[BatchWorkflow],
        activities=[execute_step, update_batch_status, get_idle_versions],
        activity_executor=activity_executor,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
