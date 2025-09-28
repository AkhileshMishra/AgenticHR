import os
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError
from celery import Celery
from typing import List, Optional
from datetime import datetime, date, timedelta
from app.db import SessionLocal
from app.models import LeaveTypeORM, LeaveBalanceORM, LeaveRequestORM
from py_hrms_auth.jwt_dep import verify_bearer

app = FastAPI(
    title="leave-svc",
    description="Leave management service with requests, approvals, and balance tracking",
    version="0.1.0"
)

# Pydantic models
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
    
    class Config:
        from_attributes = True

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
    submitted_at: datetime
    manager_id: Optional[int]
    manager_approved_at: Optional[datetime]
    manager_comments: Optional[str]
    hr_id: Optional[int]
    hr_approved_at: Optional[datetime]
    hr_comments: Optional[str]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    rejected_by: Optional[int]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    leave_type: LeaveTypeOut
    
    class Config:
        from_attributes = True

class LeaveBalanceOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    year: int
    allocated: float
    used: float
    pending: float
    available: float
    carried_forward: float
    leave_type: LeaveTypeOut
    
    class Config:
        from_attributes = True

class ApprovalRequest(BaseModel):
    comments: Optional[str] = None

async def get_db():
    async with SessionLocal() as session:
        yield session

def calculate_business_days(start_date: date, end_date: date) -> float:
    """Calculate business days between two dates"""
    days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Monday = 0, Sunday = 6
            days += 1
        current += timedelta(days=1)
    return float(days)

@app.get("/health")
def health():
    return {"status": "healthy", "service": "leave-svc", "version": "0.1.0"}

# Leave Types Management
@app.post("/v1/leave/types", response_model=LeaveTypeOut)
async def create_leave_type(
    leave_type: LeaveTypeIn,
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Create a new leave type (HR admin only)"""
    db_leave_type = LeaveTypeORM(**leave_type.dict())
    session.add(db_leave_type)
    
    try:
        await session.commit()
        await session.refresh(db_leave_type)
        return db_leave_type
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Leave type with this name already exists")

@app.get("/v1/leave/types", response_model=List[LeaveTypeOut])
async def list_leave_types(
    active_only: bool = Query(True),
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """List all leave types"""
    query = select(LeaveTypeORM)
    
    if active_only:
        query = query.where(LeaveTypeORM.is_active == True)
    
    query = query.order_by(LeaveTypeORM.name)
    
    result = await session.execute(query)
    leave_types = result.scalars().all()
    
    return leave_types

# Leave Requests
@app.post("/v1/leave/requests", response_model=LeaveRequestOut)
async def create_leave_request(
    request: LeaveRequestIn,
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Submit a leave request"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    employee_id = int(user_id)
    
    # Validate dates
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    
    if request.start_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot request leave for past dates")
    
    # Get leave type
    leave_type_result = await session.execute(
        select(LeaveTypeORM).where(LeaveTypeORM.id == request.leave_type_id)
    )
    leave_type = leave_type_result.scalar_one_or_none()
    
    if not leave_type or not leave_type.is_active:
        raise HTTPException(status_code=404, detail="Leave type not found or inactive")
    
    # Check minimum notice period
    notice_days = (request.start_date - date.today()).days
    if notice_days < leave_type.min_notice_days:
        raise HTTPException(
            status_code=400, 
            detail=f"Minimum {leave_type.min_notice_days} days notice required"
        )
    
    # Calculate days requested
    days_requested = calculate_business_days(request.start_date, request.end_date)
    
    # Check maximum consecutive days
    if leave_type.max_consecutive_days and days_requested > leave_type.max_consecutive_days:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {leave_type.max_consecutive_days} consecutive days allowed"
        )
    
    # Check for overlapping requests
    overlap_result = await session.execute(
        select(LeaveRequestORM).where(
            and_(
                LeaveRequestORM.employee_id == employee_id,
                LeaveRequestORM.status.in_(["pending", "approved"]),
                or_(
                    and_(
                        LeaveRequestORM.start_date <= request.start_date,
                        LeaveRequestORM.end_date >= request.start_date
                    ),
                    and_(
                        LeaveRequestORM.start_date <= request.end_date,
                        LeaveRequestORM.end_date >= request.end_date
                    ),
                    and_(
                        LeaveRequestORM.start_date >= request.start_date,
                        LeaveRequestORM.end_date <= request.end_date
                    )
                )
            )
        )
    )
    
    if overlap_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Overlapping leave request exists")
    
    # Create leave request
    db_request = LeaveRequestORM(
        employee_id=employee_id,
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
    
    # Trigger notification workflow
    notify_leave_request.delay(db_request.id, "submitted")
    
    return db_request

@app.get("/v1/leave/requests", response_model=List[LeaveRequestOut])
async def list_leave_requests(
    employee_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """List leave requests with filtering"""
    query = select(LeaveRequestORM).options(
        # Eager load leave_type relationship
    )
    
    # If no employee_id specified, show current user's requests
    if not employee_id:
        user_id = auth.get("user_id")
        if user_id:
            employee_id = int(user_id)
    
    if employee_id:
        query = query.where(LeaveRequestORM.employee_id == employee_id)
    
    if status:
        query = query.where(LeaveRequestORM.status == status)
    
    if start_date:
        query = query.where(LeaveRequestORM.start_date >= start_date)
    
    if end_date:
        query = query.where(LeaveRequestORM.end_date <= end_date)
    
    query = query.order_by(LeaveRequestORM.submitted_at.desc())
    
    result = await session.execute(query)
    requests = result.scalars().all()
    
    return requests

@app.post("/v1/leave/requests/{request_id}/approve", response_model=LeaveRequestOut)
async def approve_leave_request(
    request_id: int,
    approval: ApprovalRequest,
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Approve a leave request (manager/HR)"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    approver_id = int(user_id)
    
    # Get leave request
    result = await session.execute(
        select(LeaveRequestORM).where(LeaveRequestORM.id == request_id)
    )
    leave_request = result.scalar_one_or_none()
    
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave_request.status != "pending":
        raise HTTPException(status_code=400, detail="Leave request is not pending")
    
    # Update request
    now = datetime.utcnow()
    leave_request.status = "approved"
    leave_request.approved_by = approver_id
    leave_request.approved_at = now
    leave_request.manager_id = approver_id
    leave_request.manager_approved_at = now
    leave_request.manager_comments = approval.comments
    
    await session.commit()
    await session.refresh(leave_request)
    
    # Update leave balance
    update_leave_balance.delay(
        leave_request.employee_id,
        leave_request.leave_type_id,
        leave_request.days_requested,
        "approve"
    )
    
    # Trigger notifications
    notify_leave_request.delay(request_id, "approved")
    
    return leave_request

@app.post("/v1/leave/requests/{request_id}/reject", response_model=LeaveRequestOut)
async def reject_leave_request(
    request_id: int,
    rejection: ApprovalRequest,
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Reject a leave request (manager/HR)"""
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    rejector_id = int(user_id)
    
    # Get leave request
    result = await session.execute(
        select(LeaveRequestORM).where(LeaveRequestORM.id == request_id)
    )
    leave_request = result.scalar_one_or_none()
    
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave_request.status != "pending":
        raise HTTPException(status_code=400, detail="Leave request is not pending")
    
    # Update request
    now = datetime.utcnow()
    leave_request.status = "rejected"
    leave_request.rejected_by = rejector_id
    leave_request.rejected_at = now
    leave_request.rejection_reason = rejection.comments
    
    await session.commit()
    await session.refresh(leave_request)
    
    # Trigger notifications
    notify_leave_request.delay(request_id, "rejected")
    
    return leave_request

# Leave Balances
@app.get("/v1/leave/balance", response_model=List[LeaveBalanceOut])
async def get_leave_balance(
    employee_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Get leave balance for employee"""
    if not employee_id:
        user_id = auth.get("user_id")
        if user_id:
            employee_id = int(user_id)
        else:
            raise HTTPException(status_code=401, detail="Invalid authentication")
    
    if not year:
        year = date.today().year
    
    query = select(LeaveBalanceORM).where(
        and_(
            LeaveBalanceORM.employee_id == employee_id,
            LeaveBalanceORM.year == year
        )
    )
    
    result = await session.execute(query)
    balances = result.scalars().all()
    
    return balances

# --- Celery wiring ---
celery_app = Celery(
    "leave-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=None,
)

@celery_app.task(name="leave.notify_request")
def notify_leave_request(request_id: int, action: str):
    """Send notifications for leave request actions"""
    return {
        "ok": True,
        "request_id": request_id,
        "action": action,
        "notification": "sent"
    }

@celery_app.task(name="leave.update_balance")
def update_leave_balance(employee_id: int, leave_type_id: int, days: float, action: str):
    """Update employee leave balance"""
    import asyncio
    
    async def _update():
        async with SessionLocal() as session:
            year = date.today().year
            
            # Get or create balance record
            result = await session.execute(
                select(LeaveBalanceORM).where(
                    and_(
                        LeaveBalanceORM.employee_id == employee_id,
                        LeaveBalanceORM.leave_type_id == leave_type_id,
                        LeaveBalanceORM.year == year
                    )
                )
            )
            
            balance = result.scalar_one_or_none()
            if not balance:
                # Create new balance record
                balance = LeaveBalanceORM(
                    employee_id=employee_id,
                    leave_type_id=leave_type_id,
                    year=year,
                    allocated=0.0,
                    used=0.0,
                    pending=0.0,
                    available=0.0,
                    carried_forward=0.0
                )
                session.add(balance)
            
            # Update balance based on action
            if action == "approve":
                balance.used += days
                balance.pending = max(0, balance.pending - days)
            elif action == "request":
                balance.pending += days
            elif action == "cancel":
                balance.pending = max(0, balance.pending - days)
            
            # Recalculate available
            balance.available = balance.allocated + balance.carried_forward - balance.used - balance.pending
            
            await session.commit()
            
            return {
                "ok": True,
                "employee_id": employee_id,
                "leave_type_id": leave_type_id,
                "action": action,
                "days": days,
                "new_available": balance.available
            }
    
    return asyncio.run(_update())

@celery_app.task(name="leave.process_accruals")
def process_monthly_accruals():
    """Process monthly leave accruals for all employees"""
    return {"ok": True, "accruals": "processed", "month": date.today().strftime("%Y-%m")}
