#!/usr/bin/env python3
"""
Temporal Worker for AgenticHR Workflows

This worker handles all workflow and activity execution for the AgenticHR platform.
"""
import asyncio
import logging
import os
from temporalio import Worker
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner

# Import workflows
from leave_approval.workflow import LeaveApprovalWorkflow
from onboarding.workflow import OnboardingWorkflow

# Import activities
from shared.activities import (
    send_notification,
    call_service_api,
    update_leave_request_status,
    create_employee_record,
    create_user_account,
    assign_equipment,
    setup_workspace,
    schedule_orientation,
    generate_employee_id_card
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main worker function"""
    
    # Temporal server configuration
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "agentichr")
    
    logger.info(f"Connecting to Temporal server at {temporal_host}")
    logger.info(f"Using namespace: {temporal_namespace}")
    
    # Create Temporal client
    client = await Client.connect(
        temporal_host,
        namespace=temporal_namespace
    )
    
    # Create worker
    worker = Worker(
        client,
        task_queue="agentichr-workflows",
        workflows=[
            LeaveApprovalWorkflow,
            OnboardingWorkflow
        ],
        activities=[
            send_notification,
            call_service_api,
            update_leave_request_status,
            create_employee_record,
            create_user_account,
            assign_equipment,
            setup_workspace,
            schedule_orientation,
            generate_employee_id_card
        ],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    
    logger.info("Starting AgenticHR workflow worker...")
    logger.info("Registered workflows:")
    logger.info("  - LeaveApprovalWorkflow")
    logger.info("  - OnboardingWorkflow")
    logger.info("Registered activities:")
    logger.info("  - send_notification")
    logger.info("  - call_service_api")
    logger.info("  - update_leave_request_status")
    logger.info("  - create_employee_record")
    logger.info("  - create_user_account")
    logger.info("  - assign_equipment")
    logger.info("  - setup_workspace")
    logger.info("  - schedule_orientation")
    logger.info("  - generate_employee_id_card")
    
    # Run worker
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
