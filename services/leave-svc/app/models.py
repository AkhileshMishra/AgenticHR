from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, DateTime, Float, ForeignKey, Index, Text, Date
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Optional

from app.db import Base

class LeaveTypeORM(Base):
    __tablename__ = "leave_types"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Accrual settings
    annual_allocation: Mapped[float] = mapped_column(Float, default=0.0)  # Days per year
    monthly_accrual: Mapped[float] = mapped_column(Float, default=0.0)   # Days per month
    max_carry_forward: Mapped[float] = mapped_column(Float, default=0.0) # Max days to carry forward
    
    # Rules
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    min_notice_days: Mapped[int] = mapped_column(Integer, default=1)
    max_consecutive_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class LeaveBalanceORM(Base):
    __tablename__ = "leave_balances"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Balance tracking
    allocated: Mapped[float] = mapped_column(Float, default=0.0)      # Total allocated for year
    used: Mapped[float] = mapped_column(Float, default=0.0)           # Used so far
    pending: Mapped[float] = mapped_column(Float, default=0.0)        # Pending approval
    available: Mapped[float] = mapped_column(Float, default=0.0)      # Available to use
    carried_forward: Mapped[float] = mapped_column(Float, default=0.0) # From previous year
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    leave_type: Mapped[LeaveTypeORM] = relationship("LeaveTypeORM")
    
    # Unique constraint
    __table_args__ = (
        Index('ix_leave_balance_employee_type_year', 'employee_id', 'leave_type_id', 'year', unique=True),
    )

class LeaveRequestORM(Base):
    __tablename__ = "leave_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    
    # Request details
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    days_requested: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Approval workflow
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # pending, approved, rejected, cancelled
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Manager approval
    manager_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    manager_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    manager_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # HR approval (for certain types)
    hr_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hr_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    hr_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Final decision
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    leave_type: Mapped[LeaveTypeORM] = relationship("LeaveTypeORM")
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_leave_requests_employee_status', 'employee_id', 'status'),
        Index('ix_leave_requests_dates', 'start_date', 'end_date'),
        Index('ix_leave_requests_manager', 'manager_id', 'status'),
    )
