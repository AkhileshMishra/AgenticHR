from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, DateTime, Float, ForeignKey, Index, Text
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase): 
    pass

class ShiftORM(Base):
    __tablename__ = "shifts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Location tracking (optional)
    check_in_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_in_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_out_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_out_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Device tracking
    check_in_device: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    check_out_device: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
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
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Daily totals
    total_hours: Mapped[float] = mapped_column(Float, default=0.0)
    regular_hours: Mapped[float] = mapped_column(Float, default=0.0)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0.0)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status
    is_present: Mapped[bool] = mapped_column(Boolean, default=False)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    is_early_departure: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    first_check_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Unique constraint
    __table_args__ = (
        Index('ix_attendance_employee_date', 'employee_id', 'date', unique=True),
    )
