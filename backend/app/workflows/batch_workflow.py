import uuid
from datetime import timedelta

from temporalio import workflow

from app import statuses


@workflow.defn(name="batch_workflow")
class BatchWorkflow:
    @workflow.run
    async def run(self, batch_id: str) -> str:
        batch_uuid = uuid.UUID(batch_id)
        await workflow.execute_activity(
            "update_batch_status",
            args=[batch_uuid, statuses.RUNNING],
            schedule_to_close_timeout=timedelta(seconds=30),
        )

        idle_versions = await workflow.execute_activity(
            "get_idle_versions",
            args=[batch_uuid],
            schedule_to_close_timeout=timedelta(seconds=30),
        )

        for item in idle_versions:
            step_index = item["step_index"]
            node_version_id = item["node_version_id"]
            await workflow.execute_activity(
                "execute_step",
                args=[batch_uuid, step_index, node_version_id],
                schedule_to_close_timeout=timedelta(seconds=30),
            )

        await workflow.execute_activity(
            "update_batch_status",
            args=[batch_uuid, statuses.COMPLETED],
            schedule_to_close_timeout=timedelta(seconds=30),
        )

        return batch_id
