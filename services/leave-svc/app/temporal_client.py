import os, asyncio
from temporalio.client import Client
from workflows.leave_approval import LeaveRequest  # ensure workflows is in PYTHONPATH for container

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST_URL", "temporal:7233")
TEMPORAL_NS = os.getenv("TEMPORAL_NAMESPACE", "default")
TEMPORAL_TQ = os.getenv("TEMPORAL_TASK_QUEUE", "leave-approvals")

async def start_leave_workflow(request_id: str, employee_id: int, days: float) -> str:
    client = await Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NS)
    handle = await client.start_workflow(
        "workflows.leave_approval.LeaveApprovalWorkflow.run",
        LeaveRequest(request_id=request_id, employee_id=employee_id, days=days),
        id=f"leave-{request_id}",
        task_queue=TEMPORAL_TQ,
    )
    return handle.id

def start_leave_workflow_sync(request_id: str, employee_id: int, days: float) -> str:
    return asyncio.get_event_loop().run_until_complete(start_leave_workflow(request_id, employee_id, days))

