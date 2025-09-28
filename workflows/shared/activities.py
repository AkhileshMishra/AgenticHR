"""
Shared activities for AgenticHR workflows
"""
import httpx
import os
from temporalio import activity
from typing import Dict, Any, Optional
from pydantic import BaseModel

class NotificationRequest(BaseModel):
    recipient_id: int
    recipient_email: str
    template: str
    subject: str
    data: Dict[str, Any]

class APIRequest(BaseModel):
    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    json_data: Optional[Dict[str, Any]] = None

@activity.defn
async def send_notification(request: NotificationRequest) -> Dict[str, Any]:
    """Send notification via email/SMS"""
    # In a real implementation, this would integrate with email/SMS service
    activity.logger.info(
        f"Sending notification to {request.recipient_email}: {request.subject}"
    )
    
    # Simulate notification sending
    return {
        "success": True,
        "notification_id": f"notif_{request.recipient_id}_{activity.info().workflow_run_id}",
        "recipient": request.recipient_email,
        "template": request.template
    }

@activity.defn
async def call_service_api(request: APIRequest) -> Dict[str, Any]:
    """Make HTTP API call to internal services"""
    base_url = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=f"{base_url}{request.url}",
                headers=request.headers or {},
                json=request.json_data,
                timeout=30.0
            )
            
            response.raise_for_status()
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.content else None
            }
            
        except httpx.HTTPError as e:
            activity.logger.error(f"API call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }

@activity.defn
async def update_leave_request_status(
    request_id: int, 
    status: str, 
    approver_id: Optional[int] = None,
    comments: Optional[str] = None
) -> Dict[str, Any]:
    """Update leave request status"""
    
    update_data = {
        "status": status,
        "updated_at": activity.info().current_time_millis()
    }
    
    if approver_id:
        update_data["approved_by"] = approver_id
        update_data["approved_at"] = activity.info().current_time_millis()
    
    if comments:
        update_data["manager_comments"] = comments
    
    api_request = APIRequest(
        method="PUT",
        url=f"/leave/requests/{request_id}/status",
        json_data=update_data
    )
    
    result = await call_service_api(api_request)
    
    if result["success"]:
        activity.logger.info(f"Updated leave request {request_id} to status {status}")
    else:
        activity.logger.error(f"Failed to update leave request {request_id}: {result.get('error')}")
    
    return result

@activity.defn
async def create_employee_record(employee_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create employee record in employee service"""
    
    api_request = APIRequest(
        method="POST",
        url="/v1/employees",
        json_data=employee_data
    )
    
    result = await call_service_api(api_request)
    
    if result["success"]:
        activity.logger.info(f"Created employee record for {employee_data.get('email')}")
    else:
        activity.logger.error(f"Failed to create employee: {result.get('error')}")
    
    return result

@activity.defn
async def create_user_account(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create user account in auth service"""
    
    api_request = APIRequest(
        method="POST",
        url="/v1/users",
        json_data=user_data
    )
    
    result = await call_service_api(api_request)
    
    if result["success"]:
        activity.logger.info(f"Created user account for {user_data.get('email')}")
    else:
        activity.logger.error(f"Failed to create user account: {result.get('error')}")
    
    return result

@activity.defn
async def assign_equipment(employee_id: int, equipment_list: list) -> Dict[str, Any]:
    """Assign equipment to employee"""
    
    # Simulate equipment assignment
    activity.logger.info(f"Assigning equipment to employee {employee_id}: {equipment_list}")
    
    return {
        "success": True,
        "employee_id": employee_id,
        "equipment_assigned": equipment_list,
        "assignment_id": f"eq_{employee_id}_{activity.info().workflow_run_id}"
    }

@activity.defn
async def setup_workspace(employee_id: int, department: str) -> Dict[str, Any]:
    """Setup workspace for new employee"""
    
    # Simulate workspace setup
    activity.logger.info(f"Setting up workspace for employee {employee_id} in {department}")
    
    return {
        "success": True,
        "employee_id": employee_id,
        "department": department,
        "workspace_id": f"ws_{employee_id}_{activity.info().workflow_run_id}",
        "desk_number": f"DESK-{employee_id:04d}"
    }

@activity.defn
async def schedule_orientation(employee_id: int, start_date: str) -> Dict[str, Any]:
    """Schedule orientation session for new employee"""
    
    # Simulate orientation scheduling
    activity.logger.info(f"Scheduling orientation for employee {employee_id} on {start_date}")
    
    return {
        "success": True,
        "employee_id": employee_id,
        "orientation_date": start_date,
        "session_id": f"orient_{employee_id}_{activity.info().workflow_run_id}",
        "location": "Conference Room A"
    }

@activity.defn
async def generate_employee_id_card(employee_id: int) -> Dict[str, Any]:
    """Generate ID card for employee"""
    
    # Simulate ID card generation
    activity.logger.info(f"Generating ID card for employee {employee_id}")
    
    return {
        "success": True,
        "employee_id": employee_id,
        "card_id": f"ID-{employee_id:06d}",
        "status": "generated",
        "pickup_location": "HR Office"
    }
