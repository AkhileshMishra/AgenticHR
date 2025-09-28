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
    broker=os.getenv("RABBITMQ_URL", "redis://redis:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting auth-svc")
    yield
    logger.info("Shutting down auth-svc")


# FastAPI application
app = FastAPI(
    title="Auth Service",
    description="Authentication and MFA service for AgenticHR",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response model."""
    message: str
    redirect_url: str
    requires_mfa: bool = False
    mfa_methods: list[str] = []


class MFAChallengeRequest(BaseModel):
    """MFA challenge request model."""
    session_id: str
    method: str  # "totp" or "webauthn"


class MFAVerifyRequest(BaseModel):
    """MFA verification request model."""
    session_id: str
    method: str
    code: str = None  # For TOTP
    credential: Dict[str, Any] = None  # For WebAuthn


class TOTPEnrollRequest(BaseModel):
    """TOTP enrollment request model."""
    pass


class TOTPEnrollResponse(BaseModel):
    """TOTP enrollment response model."""
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class UserProfileResponse(BaseModel):
    """User profile response model."""
    user_id: str
    username: str
    email: str
    first_name: str = None
    last_name: str = None
    roles: list[str] = []
    tenant_id: str = None
    mfa_enabled: bool = False
    mfa_methods: list[str] = []


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "auth-svc", "version": "0.1.0"}


# Authentication endpoints
@app.post("/v1/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user credentials.
    
    In a real implementation, this would:
    1. Validate credentials against the user store
    2. Check if MFA is required
    3. Create a session or return appropriate redirect
    
    For now, this is a stub that demonstrates the flow.
    """
    logger.info("Login attempt", username=request.username)
    
    # Stub implementation - in production, validate against user store
    if request.username == "admin@agentichr.local" and request.password == "admin":
        return LoginResponse(
            message="Login successful",
            redirect_url="/dashboard",
            requires_mfa=True,
            mfa_methods=["totp", "webauthn"]
        )
    elif request.username == "employee@agentichr.local" and request.password == "employee":
        return LoginResponse(
            message="Login successful",
            redirect_url="/employee/dashboard",
            requires_mfa=False
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@app.post("/v1/mfa/challenge")
async def mfa_challenge(request: MFAChallengeRequest):
    """
    Initiate MFA challenge.
    
    For TOTP: Returns challenge details
    For WebAuthn: Returns challenge options
    """
    logger.info("MFA challenge requested", method=request.method, session_id=request.session_id)
    
    if request.method == "totp":
        return {
            "challenge_id": "totp_challenge_123",
            "message": "Enter your TOTP code"
        }
    elif request.method == "webauthn":
        return {
            "challenge_id": "webauthn_challenge_123",
            "challenge": "base64_encoded_challenge",
            "allowCredentials": [],
            "timeout": 60000
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported MFA method"
        )


@app.post("/v1/mfa/verify")
async def mfa_verify(request: MFAVerifyRequest):
    """
    Verify MFA response.
    
    For TOTP: Verify the provided code
    For WebAuthn: Verify the credential assertion
    """
    logger.info("MFA verification attempt", method=request.method, session_id=request.session_id)
    
    # Stub implementation - in production, verify against stored credentials
    if request.method == "totp" and request.code == "123456":
        return {
            "verified": True,
            "access_token": "jwt_access_token_here",
            "refresh_token": "jwt_refresh_token_here",
            "expires_in": 3600
        }
    elif request.method == "webauthn" and request.credential:
        return {
            "verified": True,
            "access_token": "jwt_access_token_here",
            "refresh_token": "jwt_refresh_token_here",
            "expires_in": 3600
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA verification failed"
        )


@app.post("/v1/logout")
async def logout(auth: AuthContext = Depends(get_auth_context)):
    """Logout user and invalidate session."""
    logger.info("User logout", user_id=auth.user_id)
    
    # In production, invalidate the session/token
    return {"message": "Logged out successfully"}


# MFA Management endpoints
@app.post("/v1/mfa/totp/enroll", response_model=TOTPEnrollResponse)
async def enroll_totp(
    request: TOTPEnrollRequest,
    auth: AuthContext = Depends(get_auth_context)
):
    """
    Enroll user in TOTP MFA.
    
    Generates a new TOTP secret and QR code for the user.
    """
    logger.info("TOTP enrollment requested", user_id=auth.user_id)
    
    # In production, generate actual TOTP secret and QR code
    import pyotp
    import qrcode
    import io
    import base64
    
    secret = pyotp.random_base32()
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=auth.email or auth.username,
        issuer_name="AgenticHR"
    )
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Generate backup codes
    backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]
    
    return TOTPEnrollResponse(
        secret=secret,
        qr_code_url=f"data:image/png;base64,{img_str}",
        backup_codes=backup_codes
    )


@app.get("/v1/profile", response_model=UserProfileResponse)
async def get_profile(auth: AuthContext = Depends(get_auth_context)):
    """Get current user profile."""
    logger.info("Profile requested", user_id=auth.user_id)
    
    return UserProfileResponse(
        user_id=auth.user_id,
        username=auth.username,
        email=auth.email or "",
        roles=auth.roles,
        tenant_id=auth.tenant_id,
        mfa_enabled=True,  # Stub - check actual MFA status
        mfa_methods=["totp", "webauthn"]
    )


# Password management endpoints
@app.post("/v1/password/reset-request")
async def request_password_reset(email: EmailStr):
    """Request password reset."""
    logger.info("Password reset requested", email=email)
    
    # In production, send reset email
    return {"message": "Password reset email sent if account exists"}


@app.post("/v1/password/reset")
async def reset_password(token: str, new_password: str):
    """Reset password with token."""
    logger.info("Password reset attempt", token=token[:10] + "...")
    
    # In production, validate token and update password
    return {"message": "Password reset successfully"}


# Session management
@app.get("/v1/sessions")
async def list_sessions(auth: AuthContext = Depends(get_auth_context)):
    """List active sessions for the user."""
    logger.info("Sessions list requested", user_id=auth.user_id)
    
    # Stub - return mock sessions
    return {
        "sessions": [
            {
                "session_id": "session_123",
                "device": "Chrome on Windows",
                "ip_address": "192.168.1.100",
                "last_activity": "2024-01-01T12:00:00Z",
                "current": True
            }
        ]
    }


@app.delete("/v1/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context)
):
    """Revoke a specific session."""
    logger.info("Session revocation requested", session_id=session_id, user_id=auth.user_id)
    
    # In production, revoke the session
    return {"message": "Session revoked successfully"}


# Celery tasks
@celery_app.task
def send_login_notification(user_id: str, ip_address: str, user_agent: str):
    """Send login notification email."""
    logger.info("Sending login notification", user_id=user_id, ip_address=ip_address)
    # Implementation would send actual notification
    return {"status": "sent", "user_id": user_id}


@celery_app.task
def cleanup_expired_sessions():
    """Clean up expired sessions."""
    logger.info("Cleaning up expired sessions")
    # Implementation would clean up expired sessions
    return {"status": "completed", "cleaned": 0}


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured logging."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use structlog configuration
    )
