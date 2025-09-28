"""Auth Service - Authentication and MFA service for AgenticHR."""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from celery import Celery

from py_hrms_auth import AuthContext, get_auth_context

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

# Celery configuration
celery_app = Celery(
    "auth-svc",
    broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting auth-svc")
    yield
    logger.info("Shutting down auth-svc")

app = FastAPI(
    title="auth-svc",
    description="Authentication and MFA service for AgenticHR",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "auth-svc", "version": app.version}

class UserProfile(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    roles: list[str]
    tenant_id: str | None

@app.get("/v1/me", response_model=UserProfile)
async def get_current_user(auth: AuthContext = Depends(get_auth_context)):
    """Get the profile of the currently authenticated user."""
    return UserProfile(
        user_id=auth.user_id,
        username=auth.username,
        email=auth.email,
        roles=auth.roles,
        tenant_id=auth.tenant_id
    )

@celery_app.task(name="auth.send_login_notification")
def send_login_notification(user_id: str, ip_address: str):
    """Send a login notification to the user."""
    logger.info("Sending login notification", user_id=user_id, ip_address=ip_address)
    # In a real implementation, this would send an email or push notification
    print(f"Login notification for user {user_id} from IP {ip_address}")

@celery_app.task(name="auth.cleanup_expired_sessions")
def cleanup_expired_sessions():
    """Clean up expired user sessions."""
    logger.info("Cleaning up expired sessions")
    # In a real implementation, this would query the session store and remove expired sessions
    print("Expired sessions cleaned up")

