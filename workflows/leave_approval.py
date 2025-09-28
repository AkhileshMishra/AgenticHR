from __future__ import annotations
from dataclasses import dataclass
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
import structlog
import httpx

log = structlog.get_logger(__name__)

# -------- Activities (idempotent) --------
@activity.defn(retry_policy=RetryPolicy(initial_interval=1, backoff_coefficient=2, maximum_attempts=6))
async def verify_balance(employee_id: int, days: float) -> bool:
    # TODO: query leave-svc balance via HTTP
    return True

@activity.defn(retry_policy=RetryPolicy(initial_interval=1, backoff_coefficient=2, maximum_attempts=6))
async def request_manager_approval(request_id: str, employee_id: int) -> bool:
    # TODO: send approval task/notification
    return True

@activity.defn(retry_policy=RetryPolicy(initial_interval=1, backoff_coefficient=2, maximum_attempts=6))
async def record_decision(request_id: str, approved: bool) -> None:
    # TODO: call leave-svc to persist final status
    return None

@activity.defn(retry_policy=RetryPolicy(initial_interval=1, backoff_coefficient=2, maximum_attempts=6))
async def notify_employee(employee_id: int, approved: bool) -> None:
    # TODO: call notify-svc / email provider
    return None

# ---------- Workflow -----------
@dataclass
class LeaveRequest:
    request_id: str
    employee_id: int
    days: float

@workflow.defn
class LeaveApprovalWorkflow:
    @workflow.run
    async def run(self, req: LeaveRequest) -> str:
        logger = workflow.logger
        logger.info("leave-workflow.start", req=req)

        ok = await workflow.execute_activity(
            verify_balance, req.employee_id, req.days,
            start_to_close_timeout=workflow.timedelta(seconds=30)
        )
        if not ok:
            await workflow.execute_activity(
                record_decision, req.request_id, False,
                start_to_close_timeout=workflow.timedelta(seconds=30)
            )
            return "rejected:insufficient_balance"

        approved = await workflow.execute_activity(
            request_manager_approval, req.request_id, req.employee_id,
            start_to_close_timeout=workflow.timedelta(seconds=60)
        )

        await workflow.execute_activity(
            record_decision, req.request_id, approved,
            start_to_close_timeout=workflow.timedelta(seconds=30)
        )
        await workflow.execute_activity(
            notify_employee, req.employee_id, approved,
            start_to_close_timeout=workflow.timedelta(seconds=30)
        )
        logger.info("leave-workflow.done", approved=approved)
        return "approved" if approved else "rejected"

