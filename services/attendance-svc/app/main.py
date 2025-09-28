"""Attendance Service - Time tracking and attendance management."""

import os
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime, date, timedelta

import structlog
from fastapi import FastAPI, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from celery import Celery

from app.db import get_db, init_db
from app.models import ShiftORM, AttendanceSummaryORM
from py_hrms_auth import get_auth_context, require_roles, AuthContext

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
    "attendance-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/3")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting attendance-svc")
    await init_db()
    yield
    logger.info("Shutting down attendance-svc")

app = FastAPI(
    title="attendance-svc",
    description="Attendance management service with check-in/out and reporting",
    version="0.1.0",
    lifespan=lifespan
)

class CheckInRequest(BaseModel):
    employee_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None

class CheckOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None
    break_minutes: int = Field(default=0, ge=0)

class ShiftOut(BaseModel):
    id: int
    employee_id: int
    date: date
    check_in: datetime
    check_out: Optional[datetime]
    total_hours: Optional[float]
    break_minutes: int
    status: str
    notes: Optional[str]

class AttendanceSummaryOut(BaseModel):
    id: int
    employee_id: int
    month: date
    total_days_worked: int
    total_hours: float
    average_hours_per_day: float
    late_arrivals: int
    early_departures: int

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "attendance-svc"}

@app.post("/v1/check-in", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
async def check_in(
    request: CheckInRequest,
    session: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context)
):
    """Check in an employee for their shift."""
    today = date.today()
    
    # Check if employee already checked in today
    existing_shift = await session.execute(
        select(ShiftORM).where(
            and_(
                ShiftORM.employee_id == request.employee_id,
                func.date(ShiftORM.date) == today,
                ShiftORM.check_out.is_(None)
            )
        )
    )
    
    if existing_shift.scalar_one_or_none():
        raise HTTPException(
            status_code=400, 
            detail="Employee already checked in today"
        )
    
    shift = ShiftORM(
        employee_id=request.employee_id,
        date=datetime.now(),
        check_in=datetime.now(),
        status="active",
        notes=request.notes,
        check_in_latitude=request.latitude,
        check_in_longitude=request.longitude,
        device_info=request.device_info
    )
    
    session.add(shift)
    await session.commit()
    await session.refresh(shift)
    
    # Trigger notification
    send_check_in_notification.delay(request.employee_id, shift.id)
    
    return ShiftOut.from_orm(shift)

@app.post("/v1/check-out/{shift_id}", response_model=ShiftOut)
async def check_out(
    shift_id: int,
    request: CheckOutRequest,
    session: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context)
):
    """Check out an employee from their shift."""
    shift = await session.get(ShiftORM, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    if shift.check_out:
        raise HTTPException(status_code=400, detail="Already checked out")
    
    now = datetime.now()
    shift.check_out = now
    shift.break_minutes = request.break_minutes
    shift.status = "completed"
    
    # Calculate total hours
    work_duration = now - shift.check_in
    work_hours = work_duration.total_seconds() / 3600
    break_hours = request.break_minutes / 60
    shift.total_hours = max(0, work_hours - break_hours)
    
    if request.notes:
        shift.notes = f"{shift.notes or ''}\nCheck-out: {request.notes}".strip()
    
    shift.check_out_latitude = request.latitude
    shift.check_out_longitude = request.longitude
    
    await session.commit()
    await session.refresh(shift)
    
    # Trigger summary update
    update_attendance_summary.delay(shift.employee_id, shift.date.year, shift.date.month)
    
    return ShiftOut.from_orm(shift)

@app.get("/v1/shifts", response_model=List[ShiftOut])
async def list_shifts(
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_roles(["hr.admin", "hr.manager"]))
):
    """List shifts with optional filtering."""
    query = select(ShiftORM)
    
    if employee_id:
        query = query.where(ShiftORM.employee_id == employee_id)
    
    if start_date:
        query = query.where(func.date(ShiftORM.date) >= start_date)
    
    if end_date:
        query = query.where(func.date(ShiftORM.date) <= end_date)
    
    query = query.order_by(ShiftORM.date.desc())
    
    result = await session.execute(query)
    shifts = result.scalars().all()
    
    return [ShiftOut.from_orm(shift) for shift in shifts]

@app.get("/v1/summary/{employee_id}", response_model=List[AttendanceSummaryOut])
async def get_attendance_summary(
    employee_id: int,
    year: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context)
):
    """Get attendance summary for an employee."""
    query = select(AttendanceSummaryORM).where(
        AttendanceSummaryORM.employee_id == employee_id
    )
    
    if year:
        query = query.where(func.extract('year', AttendanceSummaryORM.month) == year)
    
    query = query.order_by(AttendanceSummaryORM.month.desc())
    
    result = await session.execute(query)
    summaries = result.scalars().all()
    
    return [AttendanceSummaryOut.from_orm(summary) for summary in summaries]

@celery_app.task(name="attendance.send_check_in_notification")
def send_check_in_notification(employee_id: int, shift_id: int):
    """Send check-in notification."""
    logger.info("Sending check-in notification", employee_id=employee_id, shift_id=shift_id)
    # In a real implementation, this would send a notification
    print(f"Check-in notification sent for employee {employee_id}, shift {shift_id}")

@celery_app.task(name="attendance.update_attendance_summary")
def update_attendance_summary(employee_id: int, year: int, month: int):
    """Update monthly attendance summary for an employee."""
    logger.info("Updating attendance summary", employee_id=employee_id, year=year, month=month)
    # In a real implementation, this would calculate and update the summary
    print(f"Attendance summary updated for employee {employee_id}, {year}-{month}")

@celery_app.task(name="attendance.generate_daily_reports")
def generate_daily_reports():
    """Generate daily attendance reports."""
    logger.info("Generating daily attendance reports")
    # In a real implementation, this would generate reports for managers
    print("Daily attendance reports generated")
