import os
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
from celery import Celery
from typing import List, Optional
from datetime import datetime, date, timedelta
from app.db import SessionLocal
from app.models import ShiftORM, AttendanceSummaryORM
from py_hrms_auth.jwt_dep import verify_bearer

app = FastAPI(
    title="attendance-svc",
    description="Attendance management service with check-in/out and reporting",
    version="0.1.0"
)

# Pydantic models
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
    date: datetime
    check_in: datetime
    check_out: Optional[datetime]
    total_hours: Optional[float]
    break_minutes: int
    status: str
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class AttendanceSummaryOut(BaseModel):
    id: int
    employee_id: int
    date: datetime
    total_hours: float
    regular_hours: float
    overtime_hours: float
    break_minutes: int
    is_present: bool
    is_late: bool
    is_early_departure: bool
    first_check_in: Optional[datetime]
    last_check_out: Optional[datetime]
    
    class Config:
        from_attributes = True

class AttendanceReport(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    total_days: int
    present_days: int
    absent_days: int
    total_hours: float
    regular_hours: float
    overtime_hours: float
    late_days: int
    early_departure_days: int

async def get_db():
    async with SessionLocal() as session:
        yield session

@app.get("/health")
def health():
    return {"status": "healthy", "service": "attendance-svc", "version": "0.1.0"}

@app.post("/v1/checkin", response_model=ShiftOut)
async def check_in(
    request: CheckInRequest,
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Check in employee for the day"""
    now = datetime.utcnow()
    today = now.date()
    
    # Check if already checked in today
    existing_shift = await session.execute(
        select(ShiftORM).where(
            and_(
                ShiftORM.employee_id == request.employee_id,
                func.date(ShiftORM.date) == today,
                ShiftORM.status == "active"
            )
        )
    )
    
    if existing_shift.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already checked in today")
    
    # Create new shift
    shift = ShiftORM(
        employee_id=request.employee_id,
        date=now,
        check_in=now,
        check_in_lat=request.latitude,
        check_in_lng=request.longitude,
        check_in_device=request.device_info,
        notes=request.notes,
        status="active"
    )
    
    session.add(shift)
    await session.commit()
    await session.refresh(shift)
    
    # Trigger attendance processing
    process_daily_attendance.delay(request.employee_id, today.isoformat())
    
    return shift

@app.post("/v1/checkout", response_model=ShiftOut)
async def check_out(
    request: CheckOutRequest,
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Check out employee for the day"""
    now = datetime.utcnow()
    today = now.date()
    
    # Get current user from auth
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    # Find active shift for today
    result = await session.execute(
        select(ShiftORM).where(
            and_(
                ShiftORM.employee_id == int(user_id),  # Use authenticated user's ID
                func.date(ShiftORM.date) == today,
                ShiftORM.status == "active",
                ShiftORM.check_out.is_(None)
            )
        )
    )
    
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="No active check-in found for today")
    
    # Calculate total hours
    time_diff = now - shift.check_in
    total_hours = time_diff.total_seconds() / 3600 - (request.break_minutes / 60)
    
    # Update shift
    shift.check_out = now
    shift.check_out_lat = request.latitude
    shift.check_out_lng = request.longitude
    shift.check_out_device = request.device_info
    shift.break_minutes = request.break_minutes
    shift.total_hours = max(0, total_hours)  # Ensure non-negative
    shift.status = "completed"
    
    if request.notes:
        shift.notes = f"{shift.notes or ''}\nCheckout: {request.notes}".strip()
    
    await session.commit()
    await session.refresh(shift)
    
    # Trigger attendance processing
    process_daily_attendance.delay(shift.employee_id, today.isoformat())
    
    return shift

@app.get("/v1/attendance/summary", response_model=List[AttendanceSummaryOut])
async def get_attendance_summary(
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Get attendance summary with filtering"""
    query = select(AttendanceSummaryORM)
    
    # Apply filters
    if employee_id:
        query = query.where(AttendanceSummaryORM.employee_id == employee_id)
    
    if start_date:
        query = query.where(func.date(AttendanceSummaryORM.date) >= start_date)
    
    if end_date:
        query = query.where(func.date(AttendanceSummaryORM.date) <= end_date)
    
    query = query.order_by(AttendanceSummaryORM.date.desc())
    
    result = await session.execute(query)
    summaries = result.scalars().all()
    
    return summaries

@app.get("/v1/attendance/report", response_model=AttendanceReport)
async def get_attendance_report(
    employee_id: int,
    start_date: date,
    end_date: date,
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Generate attendance report for employee"""
    
    # Get attendance summaries for the period
    result = await session.execute(
        select(AttendanceSummaryORM).where(
            and_(
                AttendanceSummaryORM.employee_id == employee_id,
                func.date(AttendanceSummaryORM.date) >= start_date,
                func.date(AttendanceSummaryORM.date) <= end_date
            )
        )
    )
    
    summaries = result.scalars().all()
    
    # Calculate totals
    total_days = (end_date - start_date).days + 1
    present_days = len([s for s in summaries if s.is_present])
    absent_days = total_days - present_days
    total_hours = sum(s.total_hours for s in summaries)
    regular_hours = sum(s.regular_hours for s in summaries)
    overtime_hours = sum(s.overtime_hours for s in summaries)
    late_days = len([s for s in summaries if s.is_late])
    early_departure_days = len([s for s in summaries if s.is_early_departure])
    
    return AttendanceReport(
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        present_days=present_days,
        absent_days=absent_days,
        total_hours=total_hours,
        regular_hours=regular_hours,
        overtime_hours=overtime_hours,
        late_days=late_days,
        early_departure_days=early_departure_days
    )

@app.get("/v1/shifts", response_model=List[ShiftOut])
async def get_shifts(
    employee_id: Optional[int] = Query(None),
    date_filter: Optional[date] = Query(None),
    session=Depends(get_db),
    auth=Depends(verify_bearer)
):
    """Get shifts with filtering"""
    query = select(ShiftORM)
    
    if employee_id:
        query = query.where(ShiftORM.employee_id == employee_id)
    
    if date_filter:
        query = query.where(func.date(ShiftORM.date) == date_filter)
    
    query = query.order_by(ShiftORM.date.desc())
    
    result = await session.execute(query)
    shifts = result.scalars().all()
    
    return shifts

# --- Celery wiring ---
celery_app = Celery(
    "attendance-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=None,
)

@celery_app.task(name="attendance.process_daily")
def process_daily_attendance(employee_id: int, date_str: str):
    """Process daily attendance summary"""
    import asyncio
    from datetime import datetime
    
    async def _process():
        target_date = datetime.fromisoformat(date_str).date()
        
        async with SessionLocal() as session:
            # Get all shifts for the day
            result = await session.execute(
                select(ShiftORM).where(
                    and_(
                        ShiftORM.employee_id == employee_id,
                        func.date(ShiftORM.date) == target_date
                    )
                )
            )
            shifts = result.scalars().all()
            
            if not shifts:
                return {"ok": False, "reason": "no_shifts"}
            
            # Calculate daily totals
            total_hours = sum(s.total_hours or 0 for s in shifts)
            break_minutes = sum(s.break_minutes for s in shifts)
            
            # Determine regular vs overtime (8 hours standard)
            regular_hours = min(total_hours, 8.0)
            overtime_hours = max(0, total_hours - 8.0)
            
            # Check if present, late, early departure
            first_shift = min(shifts, key=lambda s: s.check_in)
            last_shift = max(shifts, key=lambda s: s.check_out or s.check_in)
            
            is_present = len(shifts) > 0
            is_late = first_shift.check_in.time() > datetime.strptime("09:00", "%H:%M").time()
            is_early_departure = (
                last_shift.check_out and 
                last_shift.check_out.time() < datetime.strptime("17:00", "%H:%M").time()
            )
            
            # Upsert attendance summary
            existing = await session.execute(
                select(AttendanceSummaryORM).where(
                    and_(
                        AttendanceSummaryORM.employee_id == employee_id,
                        func.date(AttendanceSummaryORM.date) == target_date
                    )
                )
            )
            
            summary = existing.scalar_one_or_none()
            if not summary:
                summary = AttendanceSummaryORM(
                    employee_id=employee_id,
                    date=datetime.combine(target_date, datetime.min.time())
                )
                session.add(summary)
            
            # Update summary
            summary.total_hours = total_hours
            summary.regular_hours = regular_hours
            summary.overtime_hours = overtime_hours
            summary.break_minutes = break_minutes
            summary.is_present = is_present
            summary.is_late = is_late
            summary.is_early_departure = is_early_departure
            summary.first_check_in = first_shift.check_in
            summary.last_check_out = last_shift.check_out
            
            await session.commit()
            
            return {
                "ok": True, 
                "employee_id": employee_id, 
                "date": date_str,
                "total_hours": total_hours
            }
    
    return asyncio.run(_process())

@celery_app.task(name="attendance.generate_report")
def generate_monthly_report(employee_id: int, year: int, month: int):
    """Generate monthly attendance report"""
    return {
        "ok": True, 
        "employee_id": employee_id, 
        "year": year, 
        "month": month,
        "report": "generated"
    }
