import asyncio, os, structlog
from temporalio.client import Client
from temporalio.worker import Worker
from workflows.leave_approval import LeaveApprovalWorkflow, verify_balance, request_manager_approval, record_decision, notify_employee

log = structlog.get_logger(__name__)

async def main() -> None:
    host = os.getenv("TEMPORAL_HOST_URL", "temporal:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "leave-approvals")

    client = await Client.connect(host, namespace=namespace)
    log.info("temporal.connected", host=host, namespace=namespace, task_queue=task_queue)

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[LeaveApprovalWorkflow],
        activities=[verify_balance, request_manager_approval, record_decision, notify_employee],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

