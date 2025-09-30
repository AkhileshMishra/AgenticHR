"""Leave Service - Leave management with requests, approvals, and balance tracking."""

import os
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime, date, timedelta

import structlog
from fastapi import FastAPI, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from celery import Celery

from .temporal_client import start_leave_workflow_sync

from app.db import get_db, init_db
from app.models import LeaveTypeORM, LeaveBalanceORM, LeaveRequestORM
from fastapi.middleware.cors import CORSMiddleware
from py_hrms_auth import (
    get_auth_context, 
    require_roles,
    AuthContext,
    AuthN,
    Permission,
    require_permission,
    require_resource_access
)

from py_hrms_auth.jwt_dep import JWKS_URL, OIDC_AUDIENCE, ISSUER
from py_hrms_auth.middleware import SecurityHeadersMiddleware
from py_hrms_observability import (
    init_audit_db, AuditLogMiddleware,
    configure_logging, LoggingMiddleware,
    configure_tracing, MetricsMiddleware,
    get_metrics, get_metrics_content_type
)
from py_hrms_tenancy import TenantMiddleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Celery configuration
celery_app = Celery(
    "leave-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/4")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    service_name = "leave-svc"
    service_version = app.version

    configure_logging(service_name=service_name)
    configure_tracing(service_name=service_name, service_version=service_version)

    logger.info("Starting leave-svc")
    await init_db()
    await init_audit_db()
    yield
    logger.info("Shutting down leave-svc")

app = FastAPI(
    title="leave-svc",
    description="Leave management service with requests, approvals, and balance tracking",
    version="0.1.0",
    lifespan=lifespan
)

AuthN(app, jwks_url=JWKS_URL, audience=OIDC_AUDIENCE, issuer=ISSUER)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)
app.add_middleware(LoggingMiddleware, service_name="leave-svc")
app.add_middleware(MetricsMiddleware, service_name="leave-svc")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLogMiddleware)

@app.get("/metrics")
async def get_service_metrics():
    return Response(content=get_metrics(), media_type=get_metrics_content_type())


class LeaveTypeIn(BaseModel):
    name: str
    description: Optional[str] = None
    annual_allocation: float = Field(default=0.0, ge=0)
    monthly_accrual: float = Field(default=0.0, ge=0)
    max_carry_forward: float = Field(default=0.0, ge=0)
    requires_approval: bool = True
    min_notice_days: int = Field(default=1, ge=0)
    max_consecutive_days: Optional[int] = Field(default=None, ge=1)

class LeaveTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    annual_allocation: float
    monthly_accrual: float
    max_carry_forward: float
    requires_approval: bool
    min_notice_days: int
    max_consecutive_days: Optional[int]
    is_active: bool

class LeaveRequestIn(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None

class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    days_requested: float
    reason: Optional[str]
    status: str
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]

class LeaveBalanceOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    year: int
    allocated: float
    used: float
    pending: float
    available: float

# Helper functions
def calculate_business_days(start_date: date, end_date: date) -> float:
    """Calculate business days between two dates."""
    # Simple implementation - in reality, this would account for holidays
    current = start_date
    days = 0
    while current <= end_date:
        if current.weekday() < 5:  # Monday = 0, Sunday = 6
            days += 1
        current += timedelta(days=1)
    return float(days)

async def check_leave_balance(session: AsyncSession, employee_id: str, leave_type_id: int, days_requested: float):
    """Check if employee has sufficient leave balance."""
    year = datetime.now().year
    balance = await session.execute(
        select(LeaveBalanceORM).where(
            and_(
                LeaveBalanceORM.employee_id == int(employee_id),
                LeaveBalanceORM.leave_type_id == leave_type_id,
                LeaveBalanceORM.year == year
            )
        )
    )
    
    balance_record = balance.scalar_one_or_none()
    if not balance_record:
        raise HTTPException(status_code=400, detail="No leave balance found for this leave type")
    
    if balance_record.available < days_requested:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient leave balance. Available: {balance_record.available}, Requested: {days_requested}"
        )

# Routes
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "leave-svc"}

@app.get("/v1/leave-types", response_model=List[LeaveTypeOut])
@require_permission(Permission.LEAVE_READ)
async def list_leave_types(
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """List all active leave types."""
    result = await session.execute(
        select(LeaveTypeORM).where(LeaveTypeORM.is_active == True)
    )
    leave_types = result.scalars().all()
    return [LeaveTypeOut.from_orm(lt) for lt in leave_types]

@app.post("/v1/leave-types", response_model=LeaveTypeOut, status_code=status.HTTP_201_CREATED)
@require_permission(Permission.LEAVE_MANAGE)
async def create_leave_type(
    leave_type: LeaveTypeIn,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Create a new leave type."""
    db_leave_type = LeaveTypeORM(**leave_type.dict())
    session.add(db_leave_type)
    await session.commit()
    await session.refresh(db_leave_type)
    return LeaveTypeOut.from_orm(db_leave_type)

@app.post("/v1/leave-requests", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
@require_permission(Permission.LEAVE_WRITE)
async def create_leave_request(
    request: LeaveRequestIn,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Create a new leave request."""
    # Validate dates
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    
    # Calculate business days
    days_requested = calculate_business_days(request.start_date, request.end_date)
    
    # Check leave balance
    await check_leave_balance(session, access_context.user_id, request.leave_type_id, days_requested)
    
    db_request = LeaveRequestORM(
        employee_id=int(access_context.user_id),
        leave_type_id=request.leave_type_id,
        start_date=request.start_date,
        end_date=request.end_date,
        days_requested=days_requested,
        reason=request.reason,
        status="pending"
    )
    
    session.add(db_request)
    await session.commit()
    await session.refresh(db_request)
    
    # Trigger approval workflow
    from .temporal_client import start_leave_workflow_sync
    wf_id = start_leave_workflow_sync(str(db_request.id), db_request.employee_id, db_request.days_requested)
    logger.info("Temporal workflow started", workflow_id=wf_id, request_id=db_request.id)
    return LeaveRequestOut.from_orm(db_request)

@app.get("/v1/leave-requests", response_model=List[LeaveRequestOut])
@require_permission(Permission.LEAVE_READ)
async def list_leave_requests(
    employee_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """List leave requests."""
    query = select(LeaveRequestORM)
    
    # If not HR admin, only show own requests
    if not access_context.has_any_role(["hr.admin", "hr.manager"]):
        query = query.where(LeaveRequestORM.employee_id == int(access_context.user_id))
    elif employee_id:
        query = query.where(LeaveRequestORM.employee_id == employee_id)
    
    if status_filter:
        query = query.where(LeaveRequestORM.status == status_filter)
    
    query = query.order_by(LeaveRequestORM.created_at.desc())
    
    result = await session.execute(query)
    requests = result.scalars().all()
    
    return [LeaveRequestOut.from_orm(req) for req in requests]

@app.put("/v1/leave-requests/{request_id}/approve", response_model=LeaveRequestOut)
@require_permission(Permission.LEAVE_APPROVE)
async def approve_leave_request(
    request_id: int,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Approve a leave request."""
    leave_request = await session.get(LeaveRequestORM, request_id)
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave_request.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    leave_request.status = "approved"
    leave_request.approved_by = int(access_context.user_id)
    leave_request.approved_at = datetime.now()
    
    await session.commit()
    await session.refresh(leave_request)
    
    # Update leave balance
    update_leave_balance.delay(leave_request.employee_id, leave_request.leave_type_id, leave_request.days_requested)
    
    # Send notification
    send_leave_approval_notification.delay(leave_request.id, "approved")
    
    return LeaveRequestOut.from_orm(leave_request)

@app.put("/v1/leave-requests/{request_id}/reject", response_model=LeaveRequestOut)
@require_permission(Permission.LEAVE_APPROVE)
async def reject_leave_request(
    request_id: int,
    rejection_reason: str,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Reject a leave request."""
    leave_request = await session.get(LeaveRequestORM, request_id)
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave_request.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    leave_request.status = "rejected"
    leave_request.approved_by = int(access_context.user_id)
    leave_request.approved_at = datetime.now()
    leave_request.rejection_reason = rejection_reason
    
    await session.commit()
    await session.refresh(leave_request)
    
    # Send notification
    send_leave_approval_notification.delay(leave_request.id, "rejected")
    
    return LeaveRequestOut.from_orm(leave_request)

@app.get("/v1/leave-balances/{employee_id}", response_model=List[LeaveBalanceOut])
@require_resource_access("leave", resource_id_param="employee_id")
@require_permission(Permission.LEAVE_READ)
async def get_leave_balances(
    employee_id: int,
    year: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Get leave balances for an employee."""
    # Check authorization
    if not access_context.has_any_role(["hr.admin", "hr.manager"]) and int(access_context.user_id) != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = select(LeaveBalanceORM).where(LeaveBalanceORM.employee_id == employee_id)
    
    if year:
        query = query.where(LeaveBalanceORM.year == year)
    else:
        query = query.where(LeaveBalanceORM.year == datetime.now().year)
    
    result = await session.execute(query)
    balances = result.scalars().all()
    
    return [LeaveBalanceOut.from_orm(balance) for balance in balances]

# Celery tasks
@celery_app.task(name="leave.trigger_leave_approval_workflow")
def trigger_leave_approval_workflow(request_id: int):
    """Trigger leave approval workflow."""
    logger.info("Triggering leave approval workflow", request_id=request_id)
    # In a real implementation, this would trigger a Temporal workflow
    print(f"Leave approval workflow triggered for request {request_id}")

@celery_app.task(name="leave.update_leave_balance")
def update_leave_balance(employee_id: int, leave_type_id: int, days_used: float):
    """Update employee leave balance."""
    logger.info("Updating leave balance", employee_id=employee_id, leave_type_id=leave_type_id, days_used=days_used)
    # In a real implementation, this would update the database
    print(f"Leave balance updated for employee {employee_id}: -{days_used} days")

@celery_app.task(name="leave.send_leave_approval_notification")
def send_leave_approval_notification(request_id: int, status: str):
    """Send leave approval/rejection notification."""
    logger.info("Sending leave notification", request_id=request_id, status=status)
    # In a real implementation, this would send an email/push notification
    print(f"Leave {status} notification sent for request {request_id}")

@celery_app.task(name="leave.process_monthly_accruals")
def process_monthly_accruals():
    """Process monthly leave accruals for all employees."""
    logger.info("Processing monthly leave accruals")
    # In a real implementation, this would calculate and update accruals
    print("Monthly leave accruals processed")
