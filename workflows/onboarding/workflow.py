"""
Employee Onboarding Workflow

This workflow handles the complete employee onboarding process:
1. Create employee record
2. Create user account
3. IT setup (equipment, accounts)
4. HR setup (orientation, documentation)
5. Manager assignment and introduction
6. Completion verification
"""
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..shared.activities import (
    send_notification,
    create_employee_record,
    create_user_account,
    assign_equipment,
    setup_workspace,
    schedule_orientation,
    generate_employee_id_card,
    NotificationRequest
)

class OnboardingInput(BaseModel):
    # Employee details
    full_name: str
    email: str
    phone: Optional[str] = None
    department: str
    position: str
    start_date: str
    manager_id: int
    manager_email: str
    
    # HR details
    hr_id: int
    hr_email: str
    
    # IT requirements
    equipment_needed: List[str] = []
    system_access: List[str] = []
    
    # Additional info
    employee_type: str = "full_time"  # full_time, part_time, contractor
    security_clearance: Optional[str] = None

class TaskCompletion(BaseModel):
    task_id: str
    completed: bool
    completed_by: int
    completion_date: str
    notes: Optional[str] = None

@workflow.defn
class OnboardingWorkflow:
    def __init__(self) -> None:
        self.retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )
        self.completed_tasks: Dict[str, TaskCompletion] = {}
        self.employee_id: Optional[int] = None

    @workflow.run
    async def run(self, input: OnboardingInput) -> Dict[str, Any]:
        """Main onboarding workflow execution"""
        
        workflow.logger.info(
            f"Starting onboarding workflow for {input.full_name} ({input.email})"
        )
        
        try:
            # Phase 1: Core Setup
            await self._phase_1_core_setup(input)
            
            # Phase 2: IT Setup
            await self._phase_2_it_setup(input)
            
            # Phase 3: HR Setup
            await self._phase_3_hr_setup(input)
            
            # Phase 4: Manager Introduction
            await self._phase_4_manager_introduction(input)
            
            # Phase 5: Completion and Follow-up
            await self._phase_5_completion(input)
            
            return {
                "status": "completed",
                "employee_id": self.employee_id,
                "completed_tasks": len(self.completed_tasks),
                "start_date": input.start_date
            }
            
        except Exception as e:
            workflow.logger.error(f"Onboarding workflow failed: {e}")
            await self._handle_workflow_error(input, str(e))
            return {
                "status": "error",
                "error": str(e),
                "completed_tasks": len(self.completed_tasks)
            }

    async def _phase_1_core_setup(self, input: OnboardingInput) -> None:
        """Phase 1: Create core employee and user records"""
        workflow.logger.info("Phase 1: Core Setup")
        
        # Create employee record
        employee_data = {
            "full_name": input.full_name,
            "email": input.email,
            "department": input.department,
            "position": input.position,
            "phone": input.phone
        }
        
        employee_result = await workflow.execute_activity(
            create_employee_record,
            employee_data,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=self.retry_policy
        )
        
        if employee_result["success"]:
            self.employee_id = employee_result["data"]["id"]
            self._mark_task_completed("create_employee_record", 0, "System")
        else:
            raise Exception(f"Failed to create employee record: {employee_result.get('error')}")
        
        # Create user account
        user_data = {
            "email": input.email,
            "full_name": input.full_name,
            "employee_id": self.employee_id,
            "role": "employee",
            "department": input.department
        }
        
        user_result = await workflow.execute_activity(
            create_user_account,
            user_data,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=self.retry_policy
        )
        
        if user_result["success"]:
            self._mark_task_completed("create_user_account", 0, "System")
        else:
            raise Exception(f"Failed to create user account: {user_result.get('error')}")
        
        # Notify HR that core setup is complete
        await self._notify_hr_core_setup_complete(input)

    async def _phase_2_it_setup(self, input: OnboardingInput) -> None:
        """Phase 2: IT equipment and system setup"""
        workflow.logger.info("Phase 2: IT Setup")
        
        # Assign equipment
        if input.equipment_needed:
            equipment_result = await workflow.execute_activity(
                assign_equipment,
                self.employee_id,
                input.equipment_needed,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=self.retry_policy
            )
            
            if equipment_result["success"]:
                self._mark_task_completed("assign_equipment", 0, "IT System")
        
        # Setup workspace
        workspace_result = await workflow.execute_activity(
            setup_workspace,
            self.employee_id,
            input.department,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=self.retry_policy
        )
        
        if workspace_result["success"]:
            self._mark_task_completed("setup_workspace", 0, "IT System")
        
        # Wait for IT tasks completion (manual tasks)
        await self._wait_for_it_tasks_completion(input)

    async def _phase_3_hr_setup(self, input: OnboardingInput) -> None:
        """Phase 3: HR documentation and orientation"""
        workflow.logger.info("Phase 3: HR Setup")
        
        # Schedule orientation
        orientation_result = await workflow.execute_activity(
            schedule_orientation,
            self.employee_id,
            input.start_date,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=self.retry_policy
        )
        
        if orientation_result["success"]:
            self._mark_task_completed("schedule_orientation", input.hr_id, "HR")
        
        # Generate ID card
        id_card_result = await workflow.execute_activity(
            generate_employee_id_card,
            self.employee_id,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=self.retry_policy
        )
        
        if id_card_result["success"]:
            self._mark_task_completed("generate_id_card", 0, "System")
        
        # Wait for HR tasks completion
        await self._wait_for_hr_tasks_completion(input)

    async def _phase_4_manager_introduction(self, input: OnboardingInput) -> None:
        """Phase 4: Manager assignment and introduction"""
        workflow.logger.info("Phase 4: Manager Introduction")
        
        # Notify manager about new employee
        manager_notification = NotificationRequest(
            recipient_id=input.manager_id,
            recipient_email=input.manager_email,
            template="new_employee_manager_intro",
            subject=f"New Team Member - {input.full_name}",
            data={
                "employee_name": input.full_name,
                "employee_email": input.email,
                "position": input.position,
                "department": input.department,
                "start_date": input.start_date,
                "employee_id": self.employee_id
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            manager_notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )
        
        # Wait for manager introduction completion
        await self._wait_for_manager_introduction(input)

    async def _phase_5_completion(self, input: OnboardingInput) -> None:
        """Phase 5: Completion verification and follow-up"""
        workflow.logger.info("Phase 5: Completion")
        
        # Send welcome email to employee
        welcome_notification = NotificationRequest(
            recipient_id=self.employee_id,
            recipient_email=input.email,
            template="employee_welcome",
            subject=f"Welcome to AgenticHR, {input.full_name}!",
            data={
                "employee_name": input.full_name,
                "position": input.position,
                "department": input.department,
                "start_date": input.start_date,
                "manager_email": input.manager_email,
                "hr_email": input.hr_email
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            welcome_notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )
        
        # Schedule 30-day follow-up
        await self._schedule_follow_up(input)
        
        # Notify completion to HR
        await self._notify_onboarding_complete(input)

    async def _wait_for_it_tasks_completion(self, input: OnboardingInput) -> None:
        """Wait for IT tasks to be completed manually"""
        required_tasks = ["system_access_setup", "email_account_setup"]
        
        for task in required_tasks:
            try:
                completion = await workflow.wait_condition(
                    lambda t=task: self.completed_tasks.get(t) is not None,
                    timeout=timedelta(days=3)
                )
            except workflow.TimeoutError:
                # Send escalation notification
                await self._send_task_escalation(input, task, "IT")

    async def _wait_for_hr_tasks_completion(self, input: OnboardingInput) -> None:
        """Wait for HR tasks to be completed manually"""
        required_tasks = ["documentation_complete", "benefits_enrollment"]
        
        for task in required_tasks:
            try:
                completion = await workflow.wait_condition(
                    lambda t=task: self.completed_tasks.get(t) is not None,
                    timeout=timedelta(days=5)
                )
            except workflow.TimeoutError:
                await self._send_task_escalation(input, task, "HR")

    async def _wait_for_manager_introduction(self, input: OnboardingInput) -> None:
        """Wait for manager introduction to be completed"""
        try:
            completion = await workflow.wait_condition(
                lambda: self.completed_tasks.get("manager_introduction") is not None,
                timeout=timedelta(days=2)
            )
        except workflow.TimeoutError:
            await self._send_task_escalation(input, "manager_introduction", "Manager")

    async def _notify_hr_core_setup_complete(self, input: OnboardingInput) -> None:
        """Notify HR that core setup is complete"""
        notification = NotificationRequest(
            recipient_id=input.hr_id,
            recipient_email=input.hr_email,
            template="onboarding_core_complete",
            subject=f"Core Setup Complete - {input.full_name}",
            data={
                "employee_name": input.full_name,
                "employee_id": self.employee_id,
                "start_date": input.start_date,
                "next_steps": ["IT setup", "Documentation", "Orientation scheduling"]
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _send_task_escalation(self, input: OnboardingInput, task: str, department: str) -> None:
        """Send escalation notification for overdue tasks"""
        notification = NotificationRequest(
            recipient_id=input.hr_id,
            recipient_email=input.hr_email,
            template="onboarding_task_overdue",
            subject=f"Onboarding Task Overdue - {input.full_name}",
            data={
                "employee_name": input.full_name,
                "task": task,
                "department": department,
                "overdue_days": 3 if department == "IT" else 5
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _schedule_follow_up(self, input: OnboardingInput) -> None:
        """Schedule 30-day follow-up"""
        # This would typically start a child workflow or schedule a future workflow
        workflow.logger.info(f"Scheduling 30-day follow-up for employee {self.employee_id}")

    async def _notify_onboarding_complete(self, input: OnboardingInput) -> None:
        """Notify HR that onboarding is complete"""
        notification = NotificationRequest(
            recipient_id=input.hr_id,
            recipient_email=input.hr_email,
            template="onboarding_complete",
            subject=f"Onboarding Complete - {input.full_name}",
            data={
                "employee_name": input.full_name,
                "employee_id": self.employee_id,
                "start_date": input.start_date,
                "completed_tasks": len(self.completed_tasks),
                "total_duration": "workflow_duration"
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    async def _handle_workflow_error(self, input: OnboardingInput, error: str) -> None:
        """Handle workflow errors"""
        notification = NotificationRequest(
            recipient_id=input.hr_id,
            recipient_email=input.hr_email,
            template="onboarding_error",
            subject=f"Onboarding Workflow Error - {input.full_name}",
            data={
                "employee_name": input.full_name,
                "error": error,
                "workflow_id": workflow.info().workflow_id,
                "completed_tasks": len(self.completed_tasks)
            }
        )
        
        await workflow.execute_activity(
            send_notification,
            notification,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=self.retry_policy
        )

    def _mark_task_completed(self, task_id: str, completed_by: int, completed_by_name: str) -> None:
        """Mark a task as completed"""
        self.completed_tasks[task_id] = TaskCompletion(
            task_id=task_id,
            completed=True,
            completed_by=completed_by,
            completion_date=workflow.info().current_time_millis(),
            notes=f"Completed by {completed_by_name}"
        )

    @workflow.signal
    def complete_task(self, task_completion: Dict[str, Any]) -> None:
        """Signal to mark a task as completed"""
        completion = TaskCompletion(**task_completion)
        self.completed_tasks[completion.task_id] = completion

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query current onboarding status"""
        return {
            "workflow_id": workflow.info().workflow_id,
            "employee_id": self.employee_id,
            "completed_tasks": list(self.completed_tasks.keys()),
            "total_completed": len(self.completed_tasks),
            "status": "running"
        }

    @workflow.query
    def get_completed_tasks(self) -> Dict[str, TaskCompletion]:
        """Query completed tasks"""
        return self.completed_tasks
