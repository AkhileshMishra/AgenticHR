import os
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from celery import Celery
from typing import List, Optional
from datetime import datetime
from app.db import SessionLocal
from app.models import EmployeeORM
from py_hrms_auth import (
    verify_bearer_token, 
    require_permission, 
    Permission,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    RequestLoggingMiddleware,
    audit_log
)

app = FastAPI(
    title="employee-svc",
    description="Employee management service with full CRUD operations",
    version="0.1.0"
)

# Add security middleware
app.add_middleware(RequestLoggingMiddleware, log_body=False)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

class EmployeeIn(BaseModel):
    full_name: str
    email: EmailStr
    department: str = "General"
    position: Optional[str] = None
    phone: Optional[str] = None

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None

class EmployeeOut(BaseModel):
    id: int
    full_name: str
    email: str
    department: str
    position: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EmployeeList(BaseModel):
    employees: List[EmployeeOut]
    total: int
    page: int
    per_page: int

async def get_db():
    async with SessionLocal() as session:
        yield session

@app.get("/health")
def health():
    return {"status": "healthy", "service": "employee-svc", "version": "0.1.0"}

@app.get("/v1/employees", response_model=EmployeeList)
@require_permission(Permission.EMPLOYEE_READ_ALL)
async def list_employees(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session=Depends(get_db),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """List employees with pagination and filtering"""
    query = select(EmployeeORM).where(EmployeeORM.is_active == True)
    
    if department:
        query = query.where(EmployeeORM.department == department)
    
    if search:
        query = query.where(
            (EmployeeORM.full_name.ilike(f"%{search}%")) |
            (EmployeeORM.email.ilike(f"%{search}%"))
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await session.execute(query)
    employees = result.scalars().all()
    
    return EmployeeList(
        employees=employees,
        total=total,
        page=page,
        per_page=per_page
    )

@app.post("/v1/employees", response_model=EmployeeOut)
@require_permission(Permission.EMPLOYEE_WRITE)
async def create_employee(
    employee: EmployeeIn,
    session=Depends(get_db),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """Create a new employee"""
    try:
        db_employee = EmployeeORM(
            full_name=employee.full_name,
            email=employee.email,
            department=employee.department,
            position=employee.position,
            phone=employee.phone
        )
        session.add(db_employee)
        await session.commit()
        await session.refresh(db_employee)
        
        # Trigger welcome email task
        send_welcome_email.delay(db_employee.id, db_employee.email)
        
        return db_employee
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Employee with this email already exists")

@app.get("/v1/employees/{employee_id}", response_model=EmployeeOut)
@require_permission(Permission.EMPLOYEE_READ)
async def get_employee(
    employee_id: int,
    session=Depends(get_db),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """Get employee by ID"""
    result = await session.execute(
        select(EmployeeORM).where(
            EmployeeORM.id == employee_id,
            EmployeeORM.is_active == True
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@app.put("/v1/employees/{employee_id}", response_model=EmployeeOut)
@require_permission(Permission.EMPLOYEE_WRITE)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    session=Depends(get_db),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """Update employee information"""
    result = await session.execute(
        select(EmployeeORM).where(
            EmployeeORM.id == employee_id,
            EmployeeORM.is_active == True
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update only provided fields
    update_data = employee_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    try:
        await session.commit()
        await session.refresh(employee)
        return employee
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Employee with this email already exists")

@app.delete("/v1/employees/{employee_id}")
@require_permission(Permission.EMPLOYEE_DELETE)
async def delete_employee(
    employee_id: int,
    session=Depends(get_db),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """Soft delete employee"""
    result = await session.execute(
        select(EmployeeORM).where(
            EmployeeORM.id == employee_id,
            EmployeeORM.is_active == True
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Soft delete
    employee.is_active = False
    await session.commit()
    return {"message": "Employee deleted successfully"}

# --- Celery wiring ---
celery_app = Celery(
    "employee-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=None,
)

@celery_app.task(name="employee.reindex")
def reindex_employee(emp_id: int):
    """Reindex employee in search engine"""
    return {"ok": True, "employee_id": emp_id, "action": "reindexed"}

@celery_app.task(name="employee.send_welcome_email")
def send_welcome_email(emp_id: int, email: str):
    """Send welcome email to new employees"""
    import time
    time.sleep(2)  # simulate email sending delay
    return {"ok": True, "employee_id": emp_id, "email": email, "status": "sent"}

@celery_app.task(name="employee.generate_id_card")
def generate_id_card(emp_id: int):
    """Generate ID card for employee"""
    import time
    time.sleep(3)  # simulate ID card generation
    return {"ok": True, "employee_id": emp_id, "id_card": "generated", "status": "ready"}
