"""Attendance service database models."""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, DateTime, Float, Index, Text
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from app.db import Base

class ShiftORM(Base):
    __tablename__ = "shifts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Location tracking (optional)
    check_in_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_in_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_out_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_out_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Device tracking
    device_info: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Calculated fields
    total_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status and notes
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)  # active, completed, incomplete
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_shifts_employee_date', 'employee_id', 'date'),
        Index('ix_shifts_date_status', 'date', 'status'),
        Index('ix_shifts_employee_status', 'employee_id', 'status'),
    )

class AttendanceSummaryORM(Base):
    __tablename__ = "attendance_summaries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Monthly totals
    total_days_worked: Mapped[int] = mapped_column(Integer, default=0)
    total_hours: Mapped[float] = mapped_column(Float, default=0.0)
    average_hours_per_day: Mapped[float] = mapped_column(Float, default=0.0)
    late_arrivals: Mapped[int] = mapped_column(Integer, default=0)
    early_departures: Mapped[int] = mapped_column(Integer, default=0)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Unique constraint
    __table_args__ = (
        Index('ix_attendance_employee_month', 'employee_id', 'month', unique=True),
    )
