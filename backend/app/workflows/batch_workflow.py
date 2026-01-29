import uuid
from datetime import timedelta

from temporalio import workflow

from app import statuses


@workflow.defn(name="batch_workflow")
class BatchWorkflow:
    def __init__(self) -> None:
        self.rollback_from: int | None = None

    @workflow.signal
    async def rollback(self, from_step_index: int) -> None:
        self.rollback_from = from_step_index

    @workflow.run
    async def run(self, batch_id: str, wait_for_signal: bool = False) -> str:
        batch_uuid = uuid.UUID(batch_id)
        await workflow.execute_activity(
            "update_batch_status",
            args=[batch_uuid, statuses.RUNNING],
            schedule_to_close_timeout=timedelta(seconds=30),
        )

        if wait_for_signal:
            await workflow.wait_condition(lambda: self.rollback_from is not None)
        else:
            self.rollback_from = None

        if self.rollback_from is None:
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
        else:
            # Rollback path: create new versions from rollback_from to end and execute
            template_steps = await workflow.execute_activity(
                "get_template_step_indices",
                args=[],
                schedule_to_close_timeout=timedelta(seconds=30),
            )
            for step_index in template_steps:
                if step_index < self.rollback_from:
                    continue
                parent_id = await workflow.execute_activity(
                    "get_latest_version_for_step",
                    args=[batch_uuid, step_index],
                    schedule_to_close_timeout=timedelta(seconds=30),
                )
                node_version_id = await workflow.execute_activity(
                    "create_node_version",
                    args=[batch_uuid, step_index, parent_id, "rollback"],
                    schedule_to_close_timeout=timedelta(seconds=30),
                )
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
