"""
Agents Gateway Service

This service provides AI agent integration for AgenticHR including:
- Agent management and configuration
- AI model provider integration
- Rate limiting and usage tracking
- Audit logging and compliance
- Multi-tenant support
"""
import os
import time
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, status
from pydantic import BaseModel, Field
import httpx
import structlog
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager

# Import AgenticHR libraries
from py_hrms_auth import (
    verify_bearer_token, require_permission, Permission,
    RateLimitMiddleware, SecurityHeadersMiddleware,
    RequestValidationMiddleware, RequestLoggingMiddleware
)
from py_hrms_observability import (
    configure_logging, configure_tracing, MetricsMiddleware,
    HealthChecker, add_health_endpoints, get_logger,
    track_business_operation, log_business_event
)
from py_hrms_tenancy import (
    TenantMiddleware, require_tenant, tenant_aware_dependency,
    get_tenant_session
)
from app.db import init_db, get_db
from app.models import AgentORM, AgentUsageORM, AgentRequestORM, AgentAuditORM, AgentRateLimitORM
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Configure logging and tracing
configure_logging("agents-gateway", log_level="INFO")
configure_tracing("agents-gateway", "0.1.0")

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    service_name = "agents-gateway"
    service_version = app.version

    configure_logging(service_name=service_name)
    configure_tracing(service_name=service_name, service_version=service_version)

    logger.info("Starting agents-gateway")
    await init_db()
    yield
    logger.info("Shutting down agents-gateway")

app = FastAPI(
    title="agents-gateway",
    description="AI Agents Gateway for AgenticHR",
    version="0.1.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware, log_body=False)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RateLimitMiddleware, calls=1000, period=60)  # Higher limit for AI gateway
app.add_middleware(MetricsMiddleware, service_name="agents-gateway")
app.add_middleware(TenantMiddleware, default_tenant="default")

# Pydantic models
class AgentRequest(BaseModel):
    """Agent request model"""
    agent_id: int
    message: str
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

class AgentResponse(BaseModel):
    """Agent response model"""
    request_id: str
    agent_id: int
    agent_name: str
    response: str
    usage: Dict[str, Any]
    latency_ms: int
    model_info: Dict[str, str]

class AgentConfig(BaseModel):
    """Agent configuration model"""
    name: str
    description: Optional[str] = None
    agent_type: str
    model_provider: str
    model_name: str
    system_prompt: Optional[str] = None
    instructions: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    allowed_roles: Optional[List[str]] = None
    rate_limit_per_hour: int = 100
    rate_limit_per_day: int = 1000

    class Config:
        orm_mode = True

class UsageStats(BaseModel):
    """Usage statistics model"""
    agent_id: int
    agent_name: str
    period: str
    request_count: int
    total_tokens: int
    estimated_cost: float
    avg_latency_ms: float
    success_rate: float

# AI Model Providers
class ModelProvider:
    """Base class for AI model providers"""
    
    def __init__(self, name: str, api_key: str, base_url: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response from AI model"""
        raise NotImplementedError

class OpenAIProvider(ModelProvider):
    """OpenAI model provider"""
    
    def __init__(self, api_key: str):
        super().__init__("openai", api_key, "https://api.openai.com/v1")
        self.client = None
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API"""
        try:
            # Initialize client if needed
            if not self.client:
                import openai
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason,
                "model": response.model
            }
        
        except Exception as e:
            logger.error("OpenAI API error", error=str(e))
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

class AnthropicProvider(ModelProvider):
    """Anthropic model provider"""
    
    def __init__(self, api_key: str):
        super().__init__("anthropic", api_key, "https://api.anthropic.com")
        self.client = None
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Anthropic API"""
        try:
            # Initialize client if needed
            if not self.client:
                import anthropic
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            # Convert messages format for Anthropic
            system_message = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            # Make API call
            response = await self.client.messages.create(
                model=model,
                system=system_message,
                messages=user_messages,
                **kwargs
            )
            
            return {
                "content": response.content[0].text,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                "finish_reason": response.stop_reason,
                "model": response.model
            }
        
        except Exception as e:
            logger.error("Anthropic API error", error=str(e))
            raise HTTPException(status_code=500, detail=f"Anthropic API error: {str(e)}")

# Model provider registry
model_providers = {
    "openai": OpenAIProvider(os.getenv("OPENAI_API_KEY", "")),
    "anthropic": AnthropicProvider(os.getenv("ANTHROPIC_API_KEY", "")),
}

# Agent service class
class AgentService:
    """Service for managing AI agents"""
    
    async def get_agent(self, db: AsyncSession, agent_id: int, tenant_id: str) -> Optional[AgentORM]:
        """Get agent configuration from the database."""
        result = await db.execute(
            select(AgentORM).where(AgentORM.id == agent_id, AgentORM.tenant_id == tenant_id, AgentORM.is_active == True)
        )
        return result.scalars().first()
    
    async def list_agents(self, db: AsyncSession, tenant_id: str, user_roles: List[str]) -> List[AgentORM]:
        """List available agents for user from the database."""
        query = select(AgentORM).where(AgentORM.tenant_id == tenant_id, AgentORM.is_active == True)
        
        result = await db.execute(query)
        all_agents = result.scalars().all()

        available_agents = []
        for agent in all_agents:
            allowed_roles = agent.allowed_roles or []
            if not allowed_roles or any(role in user_roles for role in allowed_roles):
                available_agents.append(agent)
        
        return available_agents
    
    async def create_agent(self, db: AsyncSession, agent_data: AgentConfig, tenant_id: str) -> AgentORM:
        """Create a new agent configuration in the database."""
        new_agent = AgentORM(**agent_data.dict(), tenant_id=tenant_id)
        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        return new_agent

    async def update_agent(self, db: AsyncSession, agent_id: int, tenant_id: str, agent_data: AgentConfig) -> Optional[AgentORM]:
        """Update an existing agent configuration in the database."""
        agent = await self.get_agent(db, agent_id, tenant_id)
        if not agent:
            return None
        for field, value in agent_data.dict(exclude_unset=True).items():
            setattr(agent, field, value)
        await db.commit()
        await db.refresh(agent)
        return agent

    async def delete_agent(self, db: AsyncSession, agent_id: int, tenant_id: str) -> bool:
        """Delete an agent configuration from the database."""
        agent = await self.get_agent(db, agent_id, tenant_id)
        if not agent:
            return False
        await db.delete(agent)
        await db.commit()
        return True

    async def check_rate_limit(
        self,
        db: AsyncSession,
        agent_id: int,
        user_id: str,
        tenant_id: str,
        rate_limit_per_hour: int,
        rate_limit_per_day: int
    ) -> bool:
        """Check if user is within rate limits for agent using the database."""
        now = datetime.utcnow()
        limit_key = f"{tenant_id}:{user_id}:{agent_id}"

        rate_limit_entry = await db.execute(
            select(AgentRateLimitORM).where(AgentRateLimitORM.limit_key == limit_key)
        )
        rate_limit_entry = rate_limit_entry.scalars().first()

        if not rate_limit_entry:
            rate_limit_entry = AgentRateLimitORM(
                limit_key=limit_key,
                agent_id=agent_id,
                user_id=user_id,
                tenant_id=tenant_id,
                hourly_count=0,
                daily_count=0,
                hourly_reset_at=now + timedelta(hours=1),
                daily_reset_at=now + timedelta(days=1),
            )
            db.add(rate_limit_entry)
            await db.commit()
            await db.refresh(rate_limit_entry)

        if now > rate_limit_entry.hourly_reset_at:
            rate_limit_entry.hourly_count = 0
            rate_limit_entry.hourly_reset_at = now + timedelta(hours=1)
        
        if now > rate_limit_entry.daily_reset_at:
            rate_limit_entry.daily_count = 0
            rate_limit_entry.daily_reset_at = now + timedelta(days=1)

        if rate_limit_entry.hourly_count >= rate_limit_per_hour or \
           rate_limit_entry.daily_count >= rate_limit_per_day:
            return False

        rate_limit_entry.hourly_count += 1
        rate_limit_entry.daily_count += 1
        await db.commit()
        return True
    
    async def log_request(
        self,
        db: AsyncSession,
        request_id: str,
        agent_id: int,
        user_id: str,
        tenant_id: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        latency_ms: int,
        status: str,
        model_name: str,
        provider_name: str
    ):
        """Log agent request for audit and billing."""
        input_tokens = response_data.get("usage", {}).get("input_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("output_tokens", 0)
        total_tokens = response_data.get("usage", {}).get("total_tokens", 0)

        agent_request_log = AgentRequestORM(
            request_id=request_id,
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            request_type="chat",
            input_text=request_data.get("message"),
            input_tokens=input_tokens,
            model_provider=provider_name,
            model_name=model_name,
            output_text=response_data.get("content"),
            output_tokens=output_tokens,
            finish_reason=response_data.get("finish_reason"),
            latency_ms=latency_ms,
            status=status,
            estimated_cost=0.0
        )
        db.add(agent_request_log)

        usage_entry = await db.execute(
            select(AgentUsageORM).where(
                AgentUsageORM.tenant_id == tenant_id,
                AgentUsageORM.agent_id == agent_id,
                AgentUsageORM.user_id == user_id,
                AgentUsageORM.date == datetime.utcnow().date()
            )
        )
        usage_entry = usage_entry.scalars().first()

        if not usage_entry:
            usage_entry = AgentUsageORM(
                tenant_id=tenant_id,
                agent_id=agent_id,
                user_id=user_id,
                date=datetime.utcnow().date(),
                agent_name="",
                request_count=0,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                estimated_cost=0.0
            )
            db.add(usage_entry)
            await db.flush()

        usage_entry.request_count += 1
        usage_entry.input_tokens += input_tokens
        usage_entry.output_tokens += output_tokens
        usage_entry.total_tokens += total_tokens

        await db.commit()

# Global agent service
agent_service = AgentService()

# Health checks
health_checker = HealthChecker("agents-gateway", "0.1.0")

async def check_openai_health():
    """Check OpenAI API health"""
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return {"status": "degraded", "message": "OpenAI API key not configured"}
        
        return {"status": "healthy", "message": "OpenAI API available"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"OpenAI API error: {str(e)}"}

async def check_anthropic_health():
    """Check Anthropic API health"""
    try:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return {"status": "degraded", "message": "Anthropic API key not configured"}
        
        return {"status": "healthy", "message": "Anthropic API available"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Anthropic API error: {str(e)}"}

health_checker.add_check("openai", check_openai_health)
health_checker.add_check("anthropic", check_anthropic_health)

add_health_endpoints(app, health_checker)

# API Endpoints

@app.post("/v1/agents", response_model=AgentConfig, status_code=status.HTTP_201_CREATED)
@require_permission(Permission.AGENT_WRITE)
async def create_agent(
    agent_data: AgentConfig,
    db: AsyncSession = Depends(get_db),
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
):
    """Create a new AI agent configuration."""
    try:
        new_agent = await agent_service.create_agent(db, agent_data, tenant_data["tenant_id"])
        return new_agent
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Agent with this name already exists for this tenant.")

@app.get("/v1/agents", response_model=List[AgentConfig])
@require_permission(Permission.AGENT_READ)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
):
    """List available agents for the user's tenant."""
    user_roles = auth.roles
    agents = await agent_service.list_agents(db, tenant_data["tenant_id"], user_roles)
    return [AgentConfig.from_orm(agent) for agent in agents]

@app.get("/v1/agents/{agent_id}", response_model=AgentConfig)
@require_permission(Permission.AGENT_READ)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
):
    """Get a specific AI agent configuration."""
    agent = await agent_service.get_agent(db, agent_id, tenant_data["tenant_id"])
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return AgentConfig.from_orm(agent)

@app.put("/v1/agents/{agent_id}", response_model=AgentConfig)
@require_permission(Permission.AGENT_WRITE)
async def update_agent(
    agent_id: int,
    agent_data: AgentConfig,
    db: AsyncSession = Depends(get_db),
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
):
    """Update an existing AI agent configuration."""
    updated_agent = await agent_service.update_agent(db, agent_id, tenant_data["tenant_id"], agent_data)
    if not updated_agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return AgentConfig.from_orm(updated_agent)

@app.delete("/v1/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission(Permission.AGENT_DELETE)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
):
    """Delete an AI agent configuration."""
    success = await agent_service.delete_agent(db, agent_id, tenant_data["tenant_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return

@app.post("/v1/agents/{agent_id}/chat", response_model=AgentResponse)
@track_business_operation("agent_chat", service_name="agents-gateway")
async def chat_with_agent(
    agent_id: int,
    request: AgentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
):
    """Chat with an AI agent."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    user_id = auth.user_id
    tenant_id = tenant_data["tenant_id"]
    
    agent = await agent_service.get_agent(db, agent_id, tenant_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    user_roles = auth.roles
    allowed_roles = agent.allowed_roles or []
    if not allowed_roles or not any(role in user_roles for role in allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied to this agent")
    
    if not await agent_service.check_rate_limit(db, agent_id, user_id, tenant_id, agent.rate_limit_per_hour, agent.rate_limit_per_day):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        provider_name = agent.model_provider
        provider = model_providers.get(provider_name)
        
        if not provider:
            raise HTTPException(status_code=500, detail=f"Model provider not available: {provider_name}")
        
        messages = []
        
        if agent.system_prompt:
            messages.append({
                "role": "system",
                "content": agent.system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        model_params = {
            "max_tokens": request.max_tokens or agent.model_config.get("max_tokens", 1000) if agent.model_config else 1000,
            "temperature": request.temperature or agent.model_config.get("temperature", 0.7) if agent.model_config else 0.7
        }
        
        response_data = await provider.generate_response(
            messages=messages,
            model=agent.model_name,
            **model_params
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        background_tasks.add_task(
            agent_service.log_request,
            db=db,
            request_id=request_id,
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            request_data=request.dict(),
            response_data=response_data,
            latency_ms=latency_ms,
            status="success",
            model_name=agent.model_name,
            provider_name=provider_name
        )
        
        return AgentResponse(
            request_id=request_id,
            agent_id=agent_id,
            agent_name=agent.name,
            response=response_data["content"],
            usage=response_data["usage"],
            latency_ms=latency_ms,
            model_info={
                "model_name": response_data["model"],
                "provider": provider_name
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error chatting with agent", error=str(e), agent_id=agent_id, request_id=request_id)
        background_tasks.add_task(
            agent_service.log_request,
            db=db,
            request_id=request_id,
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            request_data=request.dict(),
            response_data={},
            latency_ms=int((time.time() - start_time) * 1000),
            status="failed",
            model_name=agent.model_name,
            provider_name=agent.model_provider
        )
        raise HTTPException(status_code=500, detail=f"Failed to chat with agent: {str(e)}")

