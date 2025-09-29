"""Employee Service - CRUD operations for employees."""

import os
from contextlib import asynccontextmanager
from typing import List, Optional

import structlog
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from celery import Celery

from app.db import get_db, init_db
from app.models import EmployeeORM
from py_hrms_auth import (
    get_auth_context, 
    require_roles,
    AuthContext
)

from py_hrms_auth.jwt_dep import JWKS_URL, OIDC_AUDIENCE, ISSUER

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
    "employee-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    service_name = "employee-svc"
    service_version = app.version

    configure_logging(service_name=service_name)
    configure_tracing(service_name=service_name, service_version=service_version)

    logger.info("Starting employee-svc")
    await init_db()
    await init_audit_db()
    yield
    logger.info("Shutting down employee-svc")

app = FastAPI(
    title="employee-svc",
    description="Employee management service with full CRUD operations",
    version="0.1.0",
    lifespan=lifespan
)

# JWT authentication is handled by middleware


class EmployeeIn(BaseModel):
    full_name: str
    email: EmailStr
    department: str = "General"
    position: Optional[str] = None
    phone: Optional[str] = None

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None

class EmployeeOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    department: str
    position: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool

class EmployeeList(BaseModel):
    employees: List[EmployeeOut]
    total: int
    page: int
    per_page: int

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "employee-svc"}

@app.get("/v1/employees", response_model=EmployeeList)
async def list_employees(
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    query_str: Optional[str] = Query(None, alias="query"),
    access_context: AuthContext = Depends(get_auth_context)
):
    """List all employees with pagination and search."""
    query = select(EmployeeORM).where(EmployeeORM.is_active == True)
    if query_str:
        query = query.where(EmployeeORM.full_name.ilike(f"%{query_str}%"))
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await session.execute(query)
    employees = result.scalars().all()
    
    return EmployeeList(
        employees=[EmployeeOut.from_orm(e) for e in employees],
        total=total,
        page=page,
        per_page=per_page
    )

@app.post("/v1/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee: EmployeeIn,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Create a new employee."""
    try:
        db_employee = EmployeeORM(**employee.dict())
        session.add(db_employee)
        await session.commit()
        await session.refresh(db_employee)
        
        send_welcome_email.delay(db_employee.id, db_employee.email)
        
        return EmployeeOut.from_orm(db_employee)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Employee with this email already exists")

@app.get("/v1/employees/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: int,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Get a single employee by ID."""
    employee = await session.get(EmployeeORM, employee_id)
    if not employee or not employee.is_active:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeOut.from_orm(employee)

@app.put("/v1/employees/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Update an employee."""
    employee = await session.get(EmployeeORM, employee_id)
    if not employee or not employee.is_active:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(employee, key, value)
    
    await session.commit()
    await session.refresh(employee)
    return EmployeeOut.from_orm(employee)

@app.delete("/v1/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    session: AsyncSession = Depends(get_db),
    access_context: AuthContext = Depends(get_auth_context)
):
    """Soft delete an employee."""
    employee = await session.get(EmployeeORM, employee_id)
    if not employee or not employee.is_active:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee.is_active = False
    await session.commit()

@celery_app.task(name="employee.send_welcome_email")
def send_welcome_email(employee_id: int, email: str):
    """Send a welcome email to a new employee."""
    logger.info("Sending welcome email", employee_id=employee_id, email=email)
    # In a real implementation, this would use an email service
    print(f"Welcome email sent to {email} for employee {employee_id}")

@celery_app.task(name="employee.reindex_employee")
def reindex_employee(employee_id: int):
    """Reindex an employee in the search service."""
    logger.info("Reindexing employee", employee_id=employee_id)
    # In a real implementation, this would call an external search service
    print(f"Employee {employee_id} reindexed")



from py_hrms_auth.middleware import SecurityHeadersMiddleware
from py_hrms_observability import (
    init_audit_db, AuditLogMiddleware,
    configure_logging, LoggingMiddleware,
    configure_tracing, MetricsMiddleware,
    get_metrics, get_metrics_content_type
)
from py_hrms_tenancy import TenantMiddleware


app.add_middleware(TenantMiddleware)
app.add_middleware(LoggingMiddleware, service_name="employee-svc")
app.add_middleware(MetricsMiddleware, service_name="employee-svc")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLogMiddleware)

@app.get("/metrics")
async def get_service_metrics():
    return Response(content=get_metrics(), media_type=get_metrics_content_type())

