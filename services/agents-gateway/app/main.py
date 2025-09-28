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
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
import httpx
import structlog

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

# Configure logging and tracing
configure_logging("agents-gateway", log_level="INFO")
configure_tracing("agents-gateway", "0.1.0")

logger = get_logger(__name__)

app = FastAPI(
    title="agents-gateway",
    description="AI Agents Gateway for AgenticHR",
    version="0.1.0"
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
    
    def __init__(self):
        self.default_agents = self._load_default_agents()
    
    def _load_default_agents(self) -> Dict[int, Dict[str, Any]]:
        """Load default agent configurations"""
        return {
            1: {
                "id": 1,
                "name": "HR Assistant",
                "description": "General HR assistance and information",
                "agent_type": "hr_assistant",
                "model_provider": "openai",
                "model_name": "gpt-4",
                "system_prompt": "You are a helpful HR assistant for AgenticHR. Help employees with HR-related questions, policies, and procedures. Be professional, accurate, and empathetic.",
                "capabilities": ["answer_questions", "provide_guidance", "explain_policies"],
                "allowed_roles": ["employee", "manager", "hr_admin"],
                "rate_limit_per_hour": 50,
                "rate_limit_per_day": 500,
                "is_active": True
            },
            2: {
                "id": 2,
                "name": "Leave Processor",
                "description": "Process and manage leave requests",
                "agent_type": "leave_processor",
                "model_provider": "openai",
                "model_name": "gpt-4",
                "system_prompt": "You are a leave processing agent for AgenticHR. Help process leave requests, check balances, and provide leave-related information. Follow company policies strictly.",
                "capabilities": ["process_leave", "check_balances", "calculate_accruals"],
                "allowed_roles": ["employee", "manager", "hr_admin"],
                "rate_limit_per_hour": 30,
                "rate_limit_per_day": 300,
                "is_active": True
            },
            3: {
                "id": 3,
                "name": "Timesheet Approver",
                "description": "Review and approve timesheets",
                "agent_type": "timesheet_approver",
                "model_provider": "anthropic",
                "model_name": "claude-3-sonnet-20240229",
                "system_prompt": "You are a timesheet approval agent for AgenticHR. Review timesheets for accuracy, flag anomalies, and assist with approval workflows.",
                "capabilities": ["review_timesheets", "flag_anomalies", "approve_timesheets"],
                "allowed_roles": ["manager", "hr_admin"],
                "rate_limit_per_hour": 20,
                "rate_limit_per_day": 200,
                "is_active": True
            }
        }
    
    async def get_agent(self, agent_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get agent configuration"""
        # In production, this would query the database
        return self.default_agents.get(agent_id)
    
    async def list_agents(self, tenant_id: str, user_roles: List[str]) -> List[Dict[str, Any]]:
        """List available agents for user"""
        available_agents = []
        
        for agent in self.default_agents.values():
            if not agent["is_active"]:
                continue
            
            # Check if user has required roles
            allowed_roles = agent.get("allowed_roles", [])
            if any(role in user_roles for role in allowed_roles):
                available_agents.append(agent)
        
        return available_agents
    
    async def check_rate_limit(
        self,
        agent_id: int,
        user_id: str,
        tenant_id: str
    ) -> bool:
        """Check if user is within rate limits for agent"""
        # Simplified rate limiting - in production use Redis or database
        # For now, always allow
        return True
    
    async def log_request(
        self,
        request_id: str,
        agent_id: int,
        user_id: str,
        tenant_id: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        latency_ms: int,
        status: str
    ):
        """Log agent request for audit and billing"""
        log_business_event(
            "agent_request",
            request_id=request_id,
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            status=status,
            latency_ms=latency_ms,
            input_tokens=response_data.get("usage", {}).get("input_tokens", 0),
            output_tokens=response_data.get("usage", {}).get("output_tokens", 0)
        )

# Global agent service
agent_service = AgentService()

# Health checks
health_checker = HealthChecker("agents-gateway", "0.1.0")

async def check_openai_health():
    """Check OpenAI API health"""
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return {"status": "degraded", "message": "OpenAI API key not configured"}
        
        # Simple health check
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

@app.get("/v1/agents", response_model=List[Dict[str, Any]])
@require_permission(Permission.SYSTEM_ADMIN)  # Or create specific agent permissions
async def list_agents(
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """List available agents for user"""
    user_roles = auth.get("roles", [])
    agents = await agent_service.list_agents(tenant_data["tenant_id"], user_roles)
    
    return agents

@app.get("/v1/agents/{agent_id}")
@require_permission(Permission.SYSTEM_ADMIN)
async def get_agent(
    agent_id: int,
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """Get agent configuration"""
    agent = await agent_service.get_agent(agent_id, tenant_data["tenant_id"])
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent

@app.post("/v1/agents/{agent_id}/chat", response_model=AgentResponse)
@track_business_operation("agent_chat", service_name="agents-gateway")
async def chat_with_agent(
    agent_id: int,
    request: AgentRequest,
    background_tasks: BackgroundTasks,
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """Chat with an AI agent"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    user_id = auth.get("user_id", "unknown")
    tenant_id = tenant_data["tenant_id"]
    
    # Get agent configuration
    agent = await agent_service.get_agent(agent_id, tenant_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if user has permission to use this agent
    user_roles = auth.get("roles", [])
    allowed_roles = agent.get("allowed_roles", [])
    if not any(role in user_roles for role in allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied to this agent")
    
    # Check rate limits
    if not await agent_service.check_rate_limit(agent_id, user_id, tenant_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Get model provider
        provider_name = agent["model_provider"]
        provider = model_providers.get(provider_name)
        
        if not provider:
            raise HTTPException(status_code=500, detail=f"Model provider not available: {provider_name}")
        
        # Prepare messages
        messages = []
        
        # Add system prompt
        if agent.get("system_prompt"):
            messages.append({
                "role": "system",
                "content": agent["system_prompt"]
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Prepare model parameters
        model_params = {
            "max_tokens": request.max_tokens or 1000,
            "temperature": request.temperature or 0.7
        }
        
        # Generate response
        response_data = await provider.generate_response(
            messages=messages,
            model=agent["model_name"],
            **model_params
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Log request in background
        background_tasks.add_task(
            agent_service.log_request,
            request_id=request_id,
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            request_data=request.dict(),
            response_data=response_data,
            latency_ms=latency_ms,
            status="success"
        )
        
        return AgentResponse(
            request_id=request_id,
            agent_id=agent_id,
            agent_name=agent["name"],
            response=response_data["content"],
            usage=response_data["usage"],
            latency_ms=latency_ms,
            model_info={
                "provider": provider_name,
                "model": response_data["model"]
            }
        )
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Log error in background
        background_tasks.add_task(
            agent_service.log_request,
            request_id=request_id,
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            request_data=request.dict(),
            response_data={"error": str(e)},
            latency_ms=latency_ms,
            status="error"
        )
        
        logger.error(
            "Agent request failed",
            request_id=request_id,
            agent_id=agent_id,
            error=str(e)
        )
        
        raise HTTPException(status_code=500, detail=f"Agent request failed: {str(e)}")

@app.get("/v1/usage/stats")
@require_permission(Permission.REPORTS_READ)
async def get_usage_stats(
    agent_id: Optional[int] = None,
    period: str = "day",  # day, week, month
    tenant_data=Depends(tenant_aware_dependency),
    auth=Depends(verify_bearer_token),
    access_context=None
):
    """Get usage statistics"""
    # Mock data for now - in production this would query the database
    stats = [
        UsageStats(
            agent_id=1,
            agent_name="HR Assistant",
            period=period,
            request_count=150,
            total_tokens=45000,
            estimated_cost=2.25,
            avg_latency_ms=850,
            success_rate=0.98
        ),
        UsageStats(
            agent_id=2,
            agent_name="Leave Processor",
            period=period,
            request_count=75,
            total_tokens=22500,
            estimated_cost=1.12,
            avg_latency_ms=920,
            success_rate=0.99
        )
    ]
    
    if agent_id:
        stats = [s for s in stats if s.agent_id == agent_id]
    
    return stats

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from py_hrms_observability import get_metrics, get_metrics_content_type
    
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9003)
