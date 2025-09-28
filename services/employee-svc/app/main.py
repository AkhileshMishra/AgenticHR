import os
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from celery import Celery
from app.db import SessionLocal
from app.models import EmployeeORM
from py_hrms_auth.jwt_dep import verify_bearer

app = FastAPI(
    title="employee-svc",
    description="Employee management service for AgenticHR",
    version="0.1.0"
)

class EmployeeIn(BaseModel):
    full_name: str
    email: EmailStr

class EmployeeOut(EmployeeIn):
    id: int

    class Config:
        from_attributes = True

@app.get("/health")
def health():
    return {"status": "healthy", "service": "employee-svc", "version": "0.1.0"}

@app.post("/v1/employees", response_model=EmployeeOut, dependencies=[Depends(verify_bearer)])
async def create_employee(body: EmployeeIn):
    """Create a new employee"""
    async with SessionLocal() as session:
        employee = EmployeeORM(full_name=body.full_name, email=body.email)
        session.add(employee)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=409, detail="Email already exists")
        await session.refresh(employee)
        return employee

@app.get("/v1/employees/{emp_id}", response_model=EmployeeOut, dependencies=[Depends(verify_bearer)])
async def get_employee(emp_id: int):
    """Get employee by ID"""
    async with SessionLocal() as session:
        result = await session.execute(select(EmployeeORM).where(EmployeeORM.id == emp_id))
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee

@app.get("/v1/employees", response_model=list[EmployeeOut], dependencies=[Depends(verify_bearer)])
async def list_employees(skip: int = 0, limit: int = 100):
    """List employees with pagination"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(EmployeeORM).offset(skip).limit(limit)
        )
        employees = result.scalars().all()
        return employees

@app.put("/v1/employees/{emp_id}", response_model=EmployeeOut, dependencies=[Depends(verify_bearer)])
async def update_employee(emp_id: int, body: EmployeeIn):
    """Update employee by ID"""
    async with SessionLocal() as session:
        result = await session.execute(select(EmployeeORM).where(EmployeeORM.id == emp_id))
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        employee.full_name = body.full_name
        employee.email = body.email
        
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=409, detail="Email already exists")
        
        await session.refresh(employee)
        return employee

@app.delete("/v1/employees/{emp_id}", status_code=204, dependencies=[Depends(verify_bearer)])
async def delete_employee(emp_id: int):
    """Delete employee by ID"""
    async with SessionLocal() as session:
        result = await session.execute(select(EmployeeORM).where(EmployeeORM.id == emp_id))
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        await session.delete(employee)
        await session.commit()
        return None

# --- Celery wiring (new) ---
celery_app = Celery(
    "employee-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=None,
)

@celery_app.task(name="employee.reindex")
def reindex_employee(emp_id: int):
    # placeholder task to prove worker runs
    return {"ok": True, "employee_id": emp_id}
