"""Employee database models."""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, Index
from sqlalchemy.sql import func
from datetime import datetime

from app.db import Base

class EmployeeORM(Base):
    __tablename__ = "employees"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, default="General", index=True)
    position: Mapped[str] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_employees_active_department', 'is_active', 'department'),
        Index('ix_employees_active_created', 'is_active', 'created_at'),
        Index('ix_employees_search', 'full_name', 'email'),
    )
