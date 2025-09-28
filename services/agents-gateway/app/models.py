"""
Database models for Agents Gateway

This module defines the database models for:
- Agent definitions and configurations
- AI model configurations
- Request/response logging
- Usage tracking and billing
- Audit trails
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from py_hrms_tenancy import TenantAwareBase

class AgentORM(TenantAwareBase):
    """Agent configuration model"""
    __tablename__ = "agents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hr_assistant, leave_processor, etc.
    
    # AI Model Configuration
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, anthropic, etc.
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)  # gpt-4, claude-3, etc.
    model_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # temperature, max_tokens, etc.
    
    # System Prompt and Behavior
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    capabilities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # allowed operations
    
    # Access Control
    allowed_roles: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # roles that can use this agent
    rate_limit_per_hour: Mapped[Optional[int]] = mapped_column(Integer, default=100)
    rate_limit_per_day: Mapped[Optional[int]] = mapped_column(Integer, default=1000)
    
    # Status and Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

class ModelProviderORM(TenantAwareBase):
    """AI model provider configuration"""
    __tablename__ = "model_providers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)  # openai, anthropic, etc.
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # API Configuration
    api_base_url: Mapped[Optional[str]] = mapped_column(String(200))
    api_key_name: Mapped[str] = mapped_column(String(50), default="api_key")  # env var name
    
    # Provider-specific settings
    default_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    supported_models: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Rate limiting and costs
    rate_limit_rpm: Mapped[Optional[int]] = mapped_column(Integer)  # requests per minute
    rate_limit_tpm: Mapped[Optional[int]] = mapped_column(Integer)  # tokens per minute
    cost_per_1k_input_tokens: Mapped[Optional[float]] = mapped_column(Float)
    cost_per_1k_output_tokens: Mapped[Optional[float]] = mapped_column(Float)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentRequestORM(TenantAwareBase):
    """Agent request/response logging"""
    __tablename__ = "agent_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Request identification
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Agent and user info
    agent_id: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Request details
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)  # chat, completion, function_call
    input_text: Mapped[Optional[str]] = mapped_column(Text)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Model details
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Response details
    output_text: Mapped[Optional[str]] = mapped_column(Text)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    finish_reason: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Performance metrics
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Status and error handling
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, error, timeout
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_code: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Cost tracking
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

class AgentUsageORM(TenantAwareBase):
    """Agent usage tracking and billing"""
    __tablename__ = "agent_usage"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Tracking period
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # daily aggregation
    hour: Mapped[Optional[int]] = mapped_column(Integer)  # hourly breakdown
    
    # Agent and user info
    agent_id: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Usage metrics
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance metrics
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    success_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Cost tracking
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentAuditORM(TenantAwareBase):
    """Audit trail for agent operations"""
    __tablename__ = "agent_audit"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Event identification
    event_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # request, config_change, etc.
    
    # Agent and user info
    agent_id: Mapped[Optional[int]] = mapped_column(Integer)
    agent_name: Mapped[Optional[str]] = mapped_column(String(100))
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Event details
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Context and metadata
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Request details
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AgentRateLimitORM(TenantAwareBase):
    """Rate limiting tracking"""
    __tablename__ = "agent_rate_limits"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Rate limit key (combination of agent, user, tenant)
    limit_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    
    # Tracking info
    agent_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Rate limit counters
    hourly_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Reset timestamps
    hourly_reset_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    daily_reset_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
