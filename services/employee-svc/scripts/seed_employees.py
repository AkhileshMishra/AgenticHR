#!/usr/bin/env python3
"""
Employee seeder script - creates demo employees for testing
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models import EmployeeORM

DEMO_EMPLOYEES = [
    {
        "full_name": "Alice Johnson",
        "email": "alice.johnson@agentichr.com",
        "department": "Engineering",
        "position": "Senior Software Engineer",
        "phone": "+1-555-0101"
    },
    {
        "full_name": "Bob Smith",
        "email": "bob.smith@agentichr.com",
        "department": "Engineering",
        "position": "DevOps Engineer",
        "phone": "+1-555-0102"
    },
    {
        "full_name": "Carol Davis",
        "email": "carol.davis@agentichr.com",
        "department": "Product",
        "position": "Product Manager",
        "phone": "+1-555-0103"
    },
    {
        "full_name": "David Wilson",
        "email": "david.wilson@agentichr.com",
        "department": "Design",
        "position": "UX Designer",
        "phone": "+1-555-0104"
    },
    {
        "full_name": "Eva Brown",
        "email": "eva.brown@agentichr.com",
        "department": "Marketing",
        "position": "Marketing Manager",
        "phone": "+1-555-0105"
    },
    {
        "full_name": "Frank Miller",
        "email": "frank.miller@agentichr.com",
        "department": "Sales",
        "position": "Sales Representative",
        "phone": "+1-555-0106"
    },
    {
        "full_name": "Grace Lee",
        "email": "grace.lee@agentichr.com",
        "department": "HR",
        "position": "HR Manager",
        "phone": "+1-555-0107"
    },
    {
        "full_name": "Henry Taylor",
        "email": "henry.taylor@agentichr.com",
        "department": "Finance",
        "position": "Financial Analyst",
        "phone": "+1-555-0108"
    },
    {
        "full_name": "Ivy Chen",
        "email": "ivy.chen@agentichr.com",
        "department": "Engineering",
        "position": "Frontend Developer",
        "phone": "+1-555-0109"
    },
    {
        "full_name": "Jack Anderson",
        "email": "jack.anderson@agentichr.com",
        "department": "Engineering",
        "position": "Backend Developer",
        "phone": "+1-555-0110"
    },
    {
        "full_name": "Kate Rodriguez",
        "email": "kate.rodriguez@agentichr.com",
        "department": "Product",
        "position": "Product Designer",
        "phone": "+1-555-0111"
    },
    {
        "full_name": "Liam Thompson",
        "email": "liam.thompson@agentichr.com",
        "department": "Operations",
        "position": "Operations Manager",
        "phone": "+1-555-0112"
    },
    {
        "full_name": "Maya Patel",
        "email": "maya.patel@agentichr.com",
        "department": "Engineering",
        "position": "Data Engineer",
        "phone": "+1-555-0113"
    },
    {
        "full_name": "Noah Garcia",
        "email": "noah.garcia@agentichr.com",
        "department": "Security",
        "position": "Security Engineer",
        "phone": "+1-555-0114"
    },
    {
        "full_name": "Olivia Martinez",
        "email": "olivia.martinez@agentichr.com",
        "department": "Legal",
        "position": "Legal Counsel",
        "phone": "+1-555-0115"
    },
    {
        "full_name": "Paul White",
        "email": "paul.white@agentichr.com",
        "department": "Engineering",
        "position": "QA Engineer",
        "phone": "+1-555-0116"
    },
    {
        "full_name": "Quinn Johnson",
        "email": "quinn.johnson@agentichr.com",
        "department": "Customer Success",
        "position": "Customer Success Manager",
        "phone": "+1-555-0117"
    },
    {
        "full_name": "Rachel Kim",
        "email": "rachel.kim@agentichr.com",
        "department": "Design",
        "position": "Visual Designer",
        "phone": "+1-555-0118"
    },
    {
        "full_name": "Sam Wilson",
        "email": "sam.wilson@agentichr.com",
        "department": "Engineering",
        "position": "Site Reliability Engineer",
        "phone": "+1-555-0119"
    },
    {
        "full_name": "Tina Davis",
        "email": "tina.davis@agentichr.com",
        "department": "Marketing",
        "position": "Content Marketing Specialist",
        "phone": "+1-555-0120"
    },
    {
        "full_name": "Uma Singh",
        "email": "uma.singh@agentichr.com",
        "department": "Engineering",
        "position": "Machine Learning Engineer",
        "phone": "+1-555-0121"
    },
    {
        "full_name": "Victor Lopez",
        "email": "victor.lopez@agentichr.com",
        "department": "Sales",
        "position": "Sales Manager",
        "phone": "+1-555-0122"
    },
    {
        "full_name": "Wendy Clark",
        "email": "wendy.clark@agentichr.com",
        "department": "HR",
        "position": "Recruiter",
        "phone": "+1-555-0123"
    },
    {
        "full_name": "Xavier Brown",
        "email": "xavier.brown@agentichr.com",
        "department": "Finance",
        "position": "Accountant",
        "phone": "+1-555-0124"
    },
    {
        "full_name": "Yuki Tanaka",
        "email": "yuki.tanaka@agentichr.com",
        "department": "Engineering",
        "position": "Mobile Developer",
        "phone": "+1-555-0125"
    }
]

async def seed_employees():
    """Seed the database with demo employees"""
    print("🌱 Seeding employees...")
    
    async with SessionLocal() as session:
        # Check if employees already exist
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(EmployeeORM.id)))
        count = result.scalar()
        
        if count > 0:
            print(f"⚠️  Database already has {count} employees. Skipping seed.")
            return
        
        # Create employees
        employees = []
        for emp_data in DEMO_EMPLOYEES:
            employee = EmployeeORM(**emp_data)
            employees.append(employee)
        
        session.add_all(employees)
        await session.commit()
        
        print(f"✅ Successfully seeded {len(DEMO_EMPLOYEES)} employees")
        
        # Print summary by department
        from sqlalchemy import select
        result = await session.execute(
            select(EmployeeORM.department, func.count(EmployeeORM.id))
            .group_by(EmployeeORM.department)
            .order_by(EmployeeORM.department)
        )
        
        print("\n📊 Employees by department:")
        for dept, count in result.all():
            print(f"  {dept}: {count}")

if __name__ == "__main__":
    asyncio.run(seed_employees())
