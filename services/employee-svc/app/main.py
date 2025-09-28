"""Employee Service - Employee management service for AgenticHR."""

import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID, uuid4

import structlog
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

from py_hrms_auth import AuthContext, get_auth_context, RequireEmployeeManager, RequireEmployeeSelf

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting employee-svc")
    yield
    logger.info("Shutting down employee-svc")


# FastAPI application
app = FastAPI(
    title="Employee Service",
    description="Employee management service for AgenticHR",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Enums
class EmploymentStatus(str, Enum):
    """Employment status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"


class EmploymentType(str, Enum):
    """Employment type enumeration."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"
    CONSULTANT = "consultant"


class Gender(str, Enum):
    """Gender enumeration."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


# Models
class Address(BaseModel):
    """Address model."""
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class EmergencyContact(BaseModel):
    """Emergency contact model."""
    name: str
    relationship: str
    phone: str
    email: Optional[EmailStr] = None


class EmployeeBase(BaseModel):
    """Base employee model."""
    employee_id: str = Field(..., description="Unique employee identifier")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    address: Optional[Address] = None
    emergency_contact: Optional[EmergencyContact] = None


class EmployeeCreate(EmployeeBase):
    """Employee creation model."""
    department_id: Optional[str] = None
    position: str
    employment_type: EmploymentType
    start_date: date
    salary: Optional[float] = None
    manager_id: Optional[str] = None


class EmployeeUpdate(BaseModel):
    """Employee update model."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    address: Optional[Address] = None
    emergency_contact: Optional[EmergencyContact] = None
    department_id: Optional[str] = None
    position: Optional[str] = None
    employment_type: Optional[EmploymentType] = None
    salary: Optional[float] = None
    manager_id: Optional[str] = None
    status: Optional[EmploymentStatus] = None


class Employee(EmployeeBase):
    """Full employee model."""
    id: UUID
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    position: str
    employment_type: EmploymentType
    status: EmploymentStatus
    start_date: date
    end_date: Optional[date] = None
    salary: Optional[float] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmployeeList(BaseModel):
    """Employee list response model."""
    employees: List[Employee]
    total: int
    page: int
    size: int
    pages: int


class EmployeeDocument(BaseModel):
    """Employee document model."""
    id: UUID
    employee_id: str
    document_type: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by: str
    uploaded_at: datetime


# Mock database - In production, this would be a real database
MOCK_EMPLOYEES = {
    "EMP001": Employee(
        id=uuid4(),
        employee_id="EMP001",
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        phone="+1-555-0101",
        date_of_birth=date(1990, 5, 15),
        gender=Gender.FEMALE,
        address=Address(
            street="123 Main St",
            city="San Francisco",
            state="CA",
            postal_code="94105",
            country="USA"
        ),
        emergency_contact=EmergencyContact(
            name="John Smith",
            relationship="Spouse",
            phone="+1-555-0102",
            email="john.smith@example.com"
        ),
        department_id="DEPT001",
        department_name="Human Resources",
        position="HR Manager",
        employment_type=EmploymentType.FULL_TIME,
        status=EmploymentStatus.ACTIVE,
        start_date=date(2020, 1, 15),
        salary=75000.0,
        manager_id="EMP000",
        manager_name="CEO",
        tenant_id="tenant_001",
        created_at=datetime.now(),
        updated_at=datetime.now()
    ),
    "EMP002": Employee(
        id=uuid4(),
        employee_id="EMP002",
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1-555-0201",
        date_of_birth=date(1985, 8, 22),
        gender=Gender.MALE,
        department_id="DEPT002",
        department_name="Engineering",
        position="Software Engineer",
        employment_type=EmploymentType.FULL_TIME,
        status=EmploymentStatus.ACTIVE,
        start_date=date(2019, 3, 10),
        salary=95000.0,
        manager_id="EMP003",
        manager_name="Engineering Manager",
        tenant_id="tenant_001",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "employee-svc", "version": "0.1.0"}


# Employee CRUD endpoints
@app.get("/v1/employees", response_model=EmployeeList)
async def list_employees(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    department_id: Optional[str] = Query(None, description="Filter by department"),
    status: Optional[EmploymentStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    auth: AuthContext = RequireEmployeeManager
):
    """List employees with pagination and filtering."""
    logger.info(
        "Listing employees",
        user_id=auth.user_id,
        page=page,
        size=size,
        department_id=department_id,
        status=status,
        search=search
    )
    
    # Filter employees based on criteria
    employees = list(MOCK_EMPLOYEES.values())
    
    if department_id:
        employees = [emp for emp in employees if emp.department_id == department_id]
    
    if status:
        employees = [emp for emp in employees if emp.status == status]
    
    if search:
        search_lower = search.lower()
        employees = [
            emp for emp in employees
            if search_lower in emp.first_name.lower()
            or search_lower in emp.last_name.lower()
            or search_lower in emp.email.lower()
        ]
    
    # Pagination
    total = len(employees)
    start = (page - 1) * size
    end = start + size
    employees_page = employees[start:end]
    
    return EmployeeList(
        employees=employees_page,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@app.get("/v1/employees/{employee_id}", response_model=Employee)
async def get_employee(
    employee_id: str,
    auth: AuthContext = RequireEmployeeSelf
):
    """Get employee by ID."""
    logger.info("Getting employee", employee_id=employee_id, user_id=auth.user_id)
    
    # Check if user can access this employee's data
    if not auth.has_role("employee.manager") and not auth.has_role("hr.admin"):
        # Users can only access their own data
        if employee_id != auth.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    employee = MOCK_EMPLOYEES.get(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee


@app.post("/v1/employees", response_model=Employee, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    auth: AuthContext = RequireEmployeeManager
):
    """Create a new employee."""
    logger.info("Creating employee", user_id=auth.user_id, employee_id=employee_data.employee_id)
    
    # Check if employee already exists
    if employee_data.employee_id in MOCK_EMPLOYEES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee with this ID already exists"
        )
    
    # Create new employee
    new_employee = Employee(
        id=uuid4(),
        **employee_data.model_dump(),
        status=EmploymentStatus.ACTIVE,
        tenant_id=auth.tenant_id or "default",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    MOCK_EMPLOYEES[employee_data.employee_id] = new_employee
    
    logger.info("Employee created", employee_id=employee_data.employee_id)
    return new_employee


@app.put("/v1/employees/{employee_id}", response_model=Employee)
async def update_employee(
    employee_id: str,
    employee_data: EmployeeUpdate,
    auth: AuthContext = RequireEmployeeManager
):
    """Update an employee."""
    logger.info("Updating employee", employee_id=employee_id, user_id=auth.user_id)
    
    employee = MOCK_EMPLOYEES.get(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Update employee data
    update_data = employee_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    employee.updated_at = datetime.now()
    
    logger.info("Employee updated", employee_id=employee_id)
    return employee


@app.delete("/v1/employees/{employee_id}")
async def delete_employee(
    employee_id: str,
    auth: AuthContext = RequireEmployeeManager
):
    """Delete an employee (soft delete by setting status to terminated)."""
    logger.info("Deleting employee", employee_id=employee_id, user_id=auth.user_id)
    
    employee = MOCK_EMPLOYEES.get(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Soft delete by setting status to terminated
    employee.status = EmploymentStatus.TERMINATED
    employee.end_date = date.today()
    employee.updated_at = datetime.now()
    
    logger.info("Employee deleted", employee_id=employee_id)
    return {"message": "Employee deleted successfully"}


# Employee profile endpoints
@app.get("/v1/employees/{employee_id}/profile", response_model=Employee)
async def get_employee_profile(
    employee_id: str,
    auth: AuthContext = RequireEmployeeSelf
):
    """Get employee profile (same as get_employee but different endpoint for clarity)."""
    return await get_employee(employee_id, auth)


@app.put("/v1/employees/{employee_id}/profile")
async def update_employee_profile(
    employee_id: str,
    profile_data: EmployeeUpdate,
    auth: AuthContext = RequireEmployeeSelf
):
    """Update employee profile (limited fields for self-service)."""
    logger.info("Updating employee profile", employee_id=employee_id, user_id=auth.user_id)
    
    # Users can only update their own profile
    if employee_id != auth.user_id and not auth.has_role("employee.manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    employee = MOCK_EMPLOYEES.get(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Limit fields that can be updated via self-service
    allowed_fields = {
        "phone", "address", "emergency_contact"
    }
    
    if not auth.has_role("employee.manager"):
        update_data = {
            k: v for k, v in profile_data.model_dump(exclude_unset=True).items()
            if k in allowed_fields
        }
    else:
        update_data = profile_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    employee.updated_at = datetime.now()
    
    logger.info("Employee profile updated", employee_id=employee_id)
    return {"message": "Profile updated successfully"}


# Employee documents endpoints
@app.get("/v1/employees/{employee_id}/documents")
async def list_employee_documents(
    employee_id: str,
    auth: AuthContext = RequireEmployeeSelf
):
    """List employee documents."""
    logger.info("Listing employee documents", employee_id=employee_id, user_id=auth.user_id)
    
    # Check access permissions
    if not auth.has_role("employee.manager") and employee_id != auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Mock documents - in production, fetch from document service
    documents = [
        EmployeeDocument(
            id=uuid4(),
            employee_id=employee_id,
            document_type="contract",
            file_name="employment_contract.pdf",
            file_path="/documents/emp001/contract.pdf",
            file_size=1024000,
            mime_type="application/pdf",
            uploaded_by="hr@example.com",
            uploaded_at=datetime.now()
        )
    ]
    
    return {"documents": documents}


# Department endpoints
@app.get("/v1/departments")
async def list_departments(auth: AuthContext = RequireEmployeeSelf):
    """List all departments."""
    logger.info("Listing departments", user_id=auth.user_id)
    
    # Mock departments
    departments = [
        {"id": "DEPT001", "name": "Human Resources", "manager_id": "EMP001"},
        {"id": "DEPT002", "name": "Engineering", "manager_id": "EMP003"},
        {"id": "DEPT003", "name": "Sales", "manager_id": "EMP004"},
        {"id": "DEPT004", "name": "Marketing", "manager_id": "EMP005"},
    ]
    
    return {"departments": departments}


# Statistics endpoints
@app.get("/v1/employees/stats")
async def get_employee_statistics(auth: AuthContext = RequireEmployeeManager):
    """Get employee statistics."""
    logger.info("Getting employee statistics", user_id=auth.user_id)
    
    employees = list(MOCK_EMPLOYEES.values())
    
    stats = {
        "total_employees": len(employees),
        "active_employees": len([emp for emp in employees if emp.status == EmploymentStatus.ACTIVE]),
        "by_department": {},
        "by_employment_type": {},
        "by_status": {}
    }
    
    # Calculate statistics
    for emp in employees:
        # By department
        dept = emp.department_name or "Unknown"
        stats["by_department"][dept] = stats["by_department"].get(dept, 0) + 1
        
        # By employment type
        emp_type = emp.employment_type.value
        stats["by_employment_type"][emp_type] = stats["by_employment_type"].get(emp_type, 0) + 1
        
        # By status
        status_val = emp.status.value
        stats["by_status"][status_val] = stats["by_status"].get(status_val, 0) + 1
    
    return stats


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured logging."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use structlog configuration
    )
