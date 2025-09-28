"""
Leave Approval Workflow

This workflow handles the complete leave approval process:
1. Manager approval (with timeout)
2. HR approval (for certain leave types)
3. Notifications at each step
4. Automatic rejection on timeout
"""
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..shared.activities import (
    send_notification,
    update_leave_request_status,
    NotificationRequest
)

class LeaveApprovalInput(BaseModel):
    request_id: int
    employee_id: int
    employee_email: str
    employee_name: str
    manager_id: int
    manager_email: str
    hr_required: bool = False
    hr_id: Optional[int] = None
    hr_email: Optional[str] = None
    leave_type: str
    start_date: str
    end_date: str
    days_requested: float
    reason: Optional[str] = None

class ApprovalDecision(BaseModel):
    approved: bool
    approver_id: int
    comments: Optional[str] = None

@workflow.defn
class LeaveApprovalWorkflow:
    def __init__(self) -> None:
        self.retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

    @workflow.run
    async def run(self, input: LeaveApprovalInput) -> Dict[str, Any]:
        """Main workflow execution"""
        
        workflow.logger.info(
            f"Starting leave approval workflow for request {input.request_id}"
        )
        
        try:
            # Step 1: Notify manager about pending approval
            await self._notify_manager_pending(input)
            
            # Step 2: Wait for manager approval (with timeout)
            manager_decision = await self._wait_for_manager_approval(input)
            
            if not manager_decision.approved:
                # Manager rejected - workflow ends
                await self._handle_rejection(input, manager_decision, "manager")
                return {
                    "status": "rejected",
                    "rejected_by": "manager",
                    "reason": manager_decision.comments
                }
            
            # Step 3: Manager approved - notify employee
            await self._notify_employee_manager_approved(input)
            
            # Step 4: HR approval if required
            if input.hr_required and input.hr_id and input.hr_email:
                hr_decision = await self._wait_for_hr_approval(input)
                
                if not hr_decision.approved:
                    # HR rejected - workflow ends
                    await self._handle_rejection(input, hr_decision, "hr")
                    return {
                        "status": "rejected",
                        "rejected_by": "hr",
                        "reason": hr_decision.comments
                    }
                
                # HR approved
                await self._handle_final_approval(input, hr_decision.approver_id)
                return {
                    "status": "approved",
                    "approved_by": "hr",
                    "final_approver": hr_decision.approver_id
                }
            else:
                # No HR approval required - manager approval is final
                await self._handle_final_approval(input, manager_decision.approver_id)
                return {
                    "status": "approved",
                    "approved_by": "manager",
                    "final_approver": manager_decision.approver_id
                }
                
        except Exception as e:
            workflow.logger.error(f"Workflow failed: {e}")
            await self._handle_workflow_error(input, str(e))
            return {
                "status": "error",
                "error": str(e)
            }

    async def _notify_manager_pending(self, input: LeaveApprovalInput) -> None:
        """Notify manager about pending leave request"""
        notification = NotificationRequest(
            recipient_id=input.manager_id,
            recipient_email=input.manager_email,
            template="leave_approval_pending",
            subject=f"Leave Request Approval Required - {input.employee_name}",
            data={
                "employee_name": input.employee_name,
                "leave_type": input.leave_type,
                "start_date": input.start_date,
                "end_date": input.end_date,
                "days_requested": input.days_requested,
                "reason": input.reason,
                "request_id": input.request_id
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _wait_for_manager_approval(self, input: LeaveApprovalInput) -> ApprovalDecision:
        """Wait for manager approval with timeout"""
        try:
            # Wait for manager approval signal (7 days timeout)
            decision = await workflow.wait_condition(
                lambda: workflow.info().get_signal("manager_approval"),
                timeout=timedelta(days=7)
            )
            
            return ApprovalDecision(**decision)
            
        except workflow.TimeoutError:
            # Manager didn't respond in time - auto-reject
            workflow.logger.warning(
                f"Manager approval timeout for request {input.request_id}"
            )
            
            # Notify about timeout
            await self._notify_approval_timeout(input, "manager")
            
            return ApprovalDecision(
                approved=False,
                approver_id=input.manager_id,
                comments="Auto-rejected due to manager approval timeout"
            )

    async def _wait_for_hr_approval(self, input: LeaveApprovalInput) -> ApprovalDecision:
        """Wait for HR approval with timeout"""
        # First notify HR
        notification = NotificationRequest(
            recipient_id=input.hr_id,
            recipient_email=input.hr_email,
            template="leave_hr_approval_pending",
            subject=f"HR Approval Required - {input.employee_name} Leave Request",
            data={
                "employee_name": input.employee_name,
                "leave_type": input.leave_type,
                "start_date": input.start_date,
                "end_date": input.end_date,
                "days_requested": input.days_requested,
                "reason": input.reason,
                "request_id": input.request_id,
                "manager_approved": True
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )
        
        try:
            # Wait for HR approval signal (3 days timeout)
            decision = await workflow.wait_condition(
                lambda: workflow.info().get_signal("hr_approval"),
                timeout=timedelta(days=3)
            )
            
            return ApprovalDecision(**decision)
            
        except workflow.TimeoutError:
            # HR didn't respond in time - auto-reject
            workflow.logger.warning(
                f"HR approval timeout for request {input.request_id}"
            )
            
            await self._notify_approval_timeout(input, "hr")
            
            return ApprovalDecision(
                approved=False,
                approver_id=input.hr_id,
                comments="Auto-rejected due to HR approval timeout"
            )

    async def _notify_employee_manager_approved(self, input: LeaveApprovalInput) -> None:
        """Notify employee that manager approved"""
        notification = NotificationRequest(
            recipient_id=input.employee_id,
            recipient_email=input.employee_email,
            template="leave_manager_approved",
            subject="Leave Request - Manager Approved",
            data={
                "employee_name": input.employee_name,
                "leave_type": input.leave_type,
                "start_date": input.start_date,
                "end_date": input.end_date,
                "hr_required": input.hr_required
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _handle_final_approval(self, input: LeaveApprovalInput, approver_id: int) -> None:
        """Handle final approval of leave request"""
        # Update leave request status
        await workflow.execute_activity(
            update_leave_request_status,
            input.request_id,
            "approved",
            approver_id,
            "Approved via workflow",
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )
        
        # Notify employee of final approval
        notification = NotificationRequest(
            recipient_id=input.employee_id,
            recipient_email=input.employee_email,
            template="leave_final_approved",
            subject="Leave Request Approved",
            data={
                "employee_name": input.employee_name,
                "leave_type": input.leave_type,
                "start_date": input.start_date,
                "end_date": input.end_date,
                "days_requested": input.days_requested
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _handle_rejection(
        self, 
        input: LeaveApprovalInput, 
        decision: ApprovalDecision, 
        rejected_by: str
    ) -> None:
        """Handle rejection of leave request"""
        # Update leave request status
        await workflow.execute_activity(
            update_leave_request_status,
            input.request_id,
            "rejected",
            decision.approver_id,
            decision.comments,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )
        
        # Notify employee of rejection
        notification = NotificationRequest(
            recipient_id=input.employee_id,
            recipient_email=input.employee_email,
            template="leave_rejected",
            subject="Leave Request Rejected",
            data={
                "employee_name": input.employee_name,
                "leave_type": input.leave_type,
                "start_date": input.start_date,
                "end_date": input.end_date,
                "rejected_by": rejected_by,
                "reason": decision.comments
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _notify_approval_timeout(self, input: LeaveApprovalInput, approver_type: str) -> None:
        """Notify about approval timeout"""
        # Notify employee
        employee_notification = NotificationRequest(
            recipient_id=input.employee_id,
            recipient_email=input.employee_email,
            template="leave_timeout_rejected",
            subject="Leave Request Auto-Rejected",
            data={
                "employee_name": input.employee_name,
                "leave_type": input.leave_type,
                "approver_type": approver_type,
                "timeout_days": 7 if approver_type == "manager" else 3
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            employee_notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _handle_workflow_error(self, input: LeaveApprovalInput, error: str) -> None:
        """Handle workflow errors"""
        # Notify admin about workflow error
        admin_notification = NotificationRequest(
            recipient_id=0,  # Admin
            recipient_email="admin@agentichr.com",
            template="workflow_error",
            subject="Leave Approval Workflow Error",
            data={
                "request_id": input.request_id,
                "employee_name": input.employee_name,
                "error": error,
                "workflow_id": workflow.info().workflow_id
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            admin_notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    @workflow.signal
    def manager_approval(self, decision: Dict[str, Any]) -> None:
        """Signal for manager approval decision"""
        workflow.info().set_signal("manager_approval", decision)

    @workflow.signal
    def hr_approval(self, decision: Dict[str, Any]) -> None:
        """Signal for HR approval decision"""
        workflow.info().set_signal("hr_approval", decision)

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query current workflow status"""
        return {
            "workflow_id": workflow.info().workflow_id,
            "run_id": workflow.info().run_id,
            "status": "running"
        }
