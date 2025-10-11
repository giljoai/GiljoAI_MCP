# Backend Integration Tester: Auth Endpoints & Middleware

**Mission:** Implement authentication endpoints and update middleware to support JWT + API keys

**Duration:** 2-3 days

**Dependencies:** Database Expert must complete schema implementation first

---

## Your Mission

You are the Backend Integration Tester responsible for implementing the complete authentication backend: endpoints for login/registration, JWT token management, API key CRUD, and authentication middleware.

### What You're Building

- User authentication endpoints (register, login, logout)
- JWT token generation and validation
- API key CRUD endpoints (list, generate, revoke)
- Updated authentication middleware (supports both JWT and API keys)
- Comprehensive integration tests

### Why This Matters

This backend will:
- Enable secure user login for the web dashboard
- Generate personal API keys for MCP tools
- Validate requests from both web users (JWT) and tools (API keys)
- Maintain localhost mode compatibility (no auth for 127.0.0.1)

---

## Prerequisites

Before you begin, ensure the Database Expert has completed:
- ✅ User and APIKey models defined in `src/giljo_mcp/models.py`
- ✅ Alembic migration created and tested
- ✅ PasswordManager utility (`src/giljo_mcp/auth/password_manager.py`)
- ✅ APIKeyManager utility (`src/giljo_mcp/auth/api_key_manager.py`)

---

## Part 1: JWT Token System

### Install PyJWT

Add to `requirements.txt` (if not already present):
```
pyjwt==2.8.0
cryptography==41.0.7  # For additional JWT algorithms
```

### Create JWT Manager

Location: `src/giljo_mcp/auth/jwt_manager.py` (NEW FILE)

```python
"""
JWT token generation and validation for web dashboard sessions.

Token format:
- Algorithm: HS256
- Expiry: 24 hours
- Storage: httpOnly cookie
- Payload: user_id, username, role
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID
import jwt
from fastapi import HTTPException


class JWTManager:
    """Manage JWT tokens for user sessions."""

    # Secret key from environment (must be set in .env)
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    ALGORITHM = "HS256"
    EXPIRY_HOURS = 24

    @classmethod
    def create_token(cls, user_id: UUID, username: str, role: str) -> str:
        """
        Generate a JWT token for a user.

        Args:
            user_id: User's UUID
            username: Username
            role: User's role (admin, developer, viewer)

        Returns:
            Encoded JWT token string

        Example:
            >>> create_token(uuid4(), "alice", "developer")
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        """
        now = datetime.utcnow()
        expiry = now + timedelta(hours=cls.EXPIRY_HOURS)

        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "username": username,
            "role": role,
            "iat": now,  # Issued at
            "exp": expiry  # Expiration
        }

        token = jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return token

    @classmethod
    def validate_token(cls, token: str) -> Optional[Dict]:
        """
        Validate and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload if valid, None if invalid/expired

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @classmethod
    def get_user_from_token(cls, token: str) -> UUID:
        """
        Extract user ID from token.

        Args:
            token: JWT token string

        Returns:
            User UUID

        Raises:
            HTTPException: If token invalid
        """
        payload = cls.validate_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return UUID(user_id_str)
```

---

## Part 2: Authentication Endpoints

Location: `api/endpoints/auth.py` (NEW FILE)

```python
"""
Authentication endpoints for LAN mode.

Endpoints:
- POST /api/auth/register - Create new user (admin only)
- POST /api/auth/login - Login with username/password
- POST /api/auth/logout - Logout (clear cookie)
- GET /api/auth/me - Get current user info
- GET /api/auth/api-keys - List user's API keys
- POST /api/auth/api-keys - Generate new API key
- DELETE /api/auth/api-keys/{key_id} - Revoke API key
"""
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from src.giljo_mcp.database import get_db_session
from src.giljo_mcp.models import User, APIKey
from src.giljo_mcp.auth.password_manager import PasswordManager
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.auth.api_key_manager import APIKeyManager

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# --- Request/Response Models ---

class RegisterRequest(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    full_name: Optional[str] = None
    role: str = "developer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class APIKeyResponse(BaseModel):
    id: UUID
    name: Optional[str]
    key_prefix: str
    created_at: datetime
    last_used: Optional[datetime]
    is_active: bool


class APIKeyCreateRequest(BaseModel):
    name: Optional[str] = None


class APIKeyCreateResponse(BaseModel):
    id: UUID
    name: Optional[str]
    key: str  # Full key shown ONCE
    created_at: datetime
    warning: str = "Save this key securely. It won't be shown again."


# --- Authentication Helper ---

async def get_current_user(request: Request) -> User:
    """
    Get current authenticated user from JWT token.

    Used as dependency for protected endpoints.
    """
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = JWTManager.get_user_from_token(token)

    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user


# --- Endpoints ---

@router.post("/register", response_model=UserResponse)
async def register_user(request: RegisterRequest, current_user: User = Depends(get_current_user)):
    """
    Register a new user (admin only).

    Args:
        request: User registration data

    Returns:
        Created user info

    Raises:
        HTTPException: If username exists or validation fails
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin permission required")

    # Validate password strength
    password_error = PasswordManager.validate_password_strength(request.password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    with get_db_session() as session:
        # Check username uniqueness
        existing = session.query(User).filter(User.username == request.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Hash password
        password_hash = PasswordManager.hash_password(request.password)

        # Create user
        user = User(
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            full_name=request.full_name,
            role=request.role
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        return user


@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """
    Login with username and password.

    Args:
        request: Login credentials

    Returns:
        Success message and user info

    Sets:
        session_token cookie (httpOnly, 24h expiry)
    """
    with get_db_session() as session:
        # Find user
        user = session.query(User).filter(User.username == request.username).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        if not PasswordManager.verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Generate JWT token
        token = JWTManager.create_token(user.id, user.username, user.role)

        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=True,  # HTTPS only (ignored in localhost mode)
            samesite="strict",
            max_age=86400  # 24 hours
        )

        # Update last login
        user.last_login = datetime.utcnow()
        session.commit()

        return {
            "message": "Login successful",
            "user": {
                "username": user.username,
                "role": user.role
            }
        }


@router.post("/logout")
async def logout(response: Response):
    """Logout (clear session cookie)."""
    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's information."""
    return current_user


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """List current user's API keys."""
    with get_db_session() as session:
        keys = session.query(APIKey).filter(APIKey.user_id == current_user.id).all()
        return keys


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(request: APIKeyCreateRequest, current_user: User = Depends(get_current_user)):
    """
    Generate a new personal API key.

    Returns full key ONCE - must be saved by user.
    """
    # Generate key
    full_key, key_hash, key_prefix = APIKeyManager.generate_api_key(current_user.id)

    with get_db_session() as session:
        # Create API key record
        api_key = APIKey(
            user_id=current_user.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=request.name
        )

        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        return APIKeyCreateResponse(
            id=api_key.id,
            name=api_key.name,
            key=full_key,  # Shown ONCE
            created_at=api_key.created_at
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: UUID, current_user: User = Depends(get_current_user)):
    """Revoke (delete) an API key."""
    with get_db_session() as session:
        key = session.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        ).first()

        if not key:
            raise HTTPException(status_code=404, detail="API key not found")

        session.delete(key)
        session.commit()

        return {"message": "API key revoked successfully"}
```

---

## Part 3: Authentication Middleware

Location: `api/middleware/auth.py` (UPDATE EXISTING)

```python
"""
Authentication middleware supporting both JWT tokens and API keys.

Modes:
- Localhost (127.0.0.1): No authentication required
- LAN/WAN: Requires JWT token (web) or API key (tools)
"""
from fastapi import Request, HTTPException
from typing import Optional
import os

from src.giljo_mcp.database import get_db_session
from src.giljo_mcp.models import User, APIKey
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.auth.api_key_manager import APIKeyManager


def is_localhost_request(request: Request) -> bool:
    """Check if request is from localhost."""
    client_host = request.client.host
    return client_host in ["127.0.0.1", "localhost", "::1"]


async def authenticate_request(request: Request) -> Optional[User]:
    """
    Authenticate incoming request.

    Authentication methods (in order):
    1. Skip auth for localhost mode (127.0.0.1)
    2. Try JWT token (web dashboard)
    3. Try API key (MCP tools, CLI)
    4. Reject if no valid auth

    Returns:
        User object if authenticated, None for localhost
    """
    # Skip auth for localhost
    if is_localhost_request(request):
        return None  # No auth required

    # Try JWT token (from cookie)
    token = request.cookies.get("session_token")
    if token:
        try:
            user_id = JWTManager.get_user_from_token(token)
            with get_db_session() as session:
                user = session.query(User).filter(
                    User.id == user_id,
                    User.is_active == True
                ).first()
                if user:
                    return user
        except HTTPException:
            pass  # Invalid JWT, try API key

    # Try API key (from header)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        with get_db_session() as session:
            # Find all active API keys
            keys = session.query(APIKey).filter(APIKey.is_active == True).all()

            # Check each key
            for key_record in keys:
                if APIKeyManager.verify_api_key(api_key, key_record.key_hash):
                    # Update last used timestamp
                    key_record.last_used = datetime.utcnow()
                    session.commit()

                    # Get user
                    user = session.query(User).filter(
                        User.id == key_record.user_id,
                        User.is_active == True
                    ).first()
                    if user:
                        return user

    # No valid authentication found
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide valid JWT token or API key."
    )
```

---

## Part 4: Integration Tests

Location: `tests/integration/test_auth_endpoints.py` (NEW FILE)

```python
"""Integration tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from src.giljo_mcp.models import User, APIKey
from src.giljo_mcp.auth.password_manager import PasswordManager

client = TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    password_hash = PasswordManager.hash_password("TestPassword123!")
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=password_hash,
        role="developer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_success(test_user):
    """Test successful login."""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "TestPassword123!"
    })

    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert "session_token" in response.cookies


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post("/api/auth/login", json={
        "username": "nonexistent",
        "password": "WrongPassword123!"
    })

    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_get_current_user(test_user):
    """Test getting current user info."""
    # Login first
    login_response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "TestPassword123!"
    })

    # Get user info with session cookie
    response = client.get("/api/auth/me", cookies=login_response.cookies)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "developer"


def test_create_api_key(test_user):
    """Test API key generation."""
    # Login
    login_response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "TestPassword123!"
    })

    # Create API key
    response = client.post(
        "/api/auth/api-keys",
        json={"name": "Test Key"},
        cookies=login_response.cookies
    )

    assert response.status_code == 200
    data = response.json()
    assert data["key"].startswith("gk_")
    assert data["warning"] == "Save this key securely. It won't be shown again."


def test_api_key_authentication(test_user):
    """Test authentication with API key."""
    from src.giljo_mcp.auth.api_key_manager import APIKeyManager
    from src.giljo_mcp.database import get_db_session

    # Generate API key
    full_key, key_hash, key_prefix = APIKeyManager.generate_api_key(test_user.id)

    with get_db_session() as session:
        api_key = APIKey(
            user_id=test_user.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Test Key"
        )
        session.add(api_key)
        session.commit()

    # Use API key to access endpoint
    response = client.get(
        "/api/auth/me",
        headers={"X-API-Key": full_key}
    )

    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


def test_localhost_bypasses_auth():
    """Test localhost requests bypass authentication."""
    # Request from 127.0.0.1 (test client default)
    response = client.get("/api/projects")  # Protected endpoint

    # Should succeed without auth (localhost mode)
    assert response.status_code in [200, 404]  # 200 or empty list
```

---

## Acceptance Criteria

Before marking complete, verify:

- [ ] JWT token generation works
- [ ] JWT token validation works (24h expiry)
- [ ] POST /api/auth/register creates users (admin only)
- [ ] POST /api/auth/login returns JWT cookie
- [ ] POST /api/auth/logout clears cookie
- [ ] GET /api/auth/me returns current user
- [ ] POST /api/auth/api-keys generates personal key
- [ ] GET /api/auth/api-keys lists user's keys
- [ ] DELETE /api/auth/api-keys/{id} revokes key
- [ ] Middleware validates JWT tokens (web dashboard)
- [ ] Middleware validates API keys (MCP tools)
- [ ] Localhost mode (127.0.0.1) bypasses auth
- [ ] Invalid credentials return 401
- [ ] Expired tokens return 401
- [ ] All integration tests pass (90%+ coverage)
- [ ] No security vulnerabilities (SQL injection, XSS)

---

## Files to Create/Modify

**New Files:**
- `src/giljo_mcp/auth/jwt_manager.py` (JWT utilities)
- `api/endpoints/auth.py` (authentication endpoints)
- `tests/integration/test_auth_endpoints.py` (integration tests)

**Modified Files:**
- `api/middleware/auth.py` (update authentication middleware)
- `api/app.py` (register auth router)
- `requirements.txt` (ensure PyJWT, bcrypt listed)

---

## Handoff Information

When complete, hand off to **Frontend Tester** with:

**Backend Ready:**
- Login endpoint: POST /api/auth/login (returns JWT cookie)
- User info endpoint: GET /api/auth/me (current user)
- API key endpoints: GET/POST/DELETE /api/auth/api-keys
- Authentication middleware working (JWT + API keys)

**Frontend Should Build:**
- Login page (username/password form)
- Axios interceptor (401 → redirect to login)
- API key management UI (Settings → API Keys)
- User management UI (Admin → Users)

**Important Notes:**
- JWT stored in httpOnly cookie (no JavaScript access)
- API key shown ONCE after generation (must copy)
- Localhost mode bypasses login automatically

---

Good luck implementing the authentication backend! 🔐
