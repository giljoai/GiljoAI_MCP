# API Dependencies

This document covers all dependencies related to REST API functionality, HTTP clients, and web service communication in GiljoAI MCP.

## Overview

GiljoAI MCP provides a comprehensive REST API for agent management, project coordination, and system monitoring. The API stack includes:

- **FastAPI** for the web framework
- **Pydantic** for data validation
- **httpx** for HTTP client operations
- **uvicorn** for ASGI server

## Core API Dependencies

### fastapi (>=0.100.0) - **CRITICAL**

**Purpose:** Modern, fast web framework for building APIs

**Key Features:**

- Automatic OpenAPI/Swagger documentation
- Built-in WebSocket support
- Async/await support
- Type hints validation
- Dependency injection

**Used In:**

- `src/giljo_mcp/api/` - Main API application
- REST endpoints for agent management
- WebSocket endpoints for real-time communication
- Authentication and authorization

**API Endpoints:**

```python
# Agent Management
POST   /api/v1/agents/
GET    /api/v1/agents/{agent_id}
PUT    /api/v1/agents/{agent_id}/activate
DELETE /api/v1/agents/{agent_id}

# Project Management
POST   /api/v1/projects/
GET    /api/v1/projects/{project_id}
PUT    /api/v1/projects/{project_id}

# System
GET    /api/v1/health
GET    /api/v1/status
GET    /api/v1/metrics
```

### pydantic (>=2.0.0) - **CRITICAL**

**Purpose:** Data validation using Python type annotations

**Key Features:**

- Automatic data validation
- JSON serialization/deserialization
- Settings management
- Error handling with detailed messages

**Used In:**

- API request/response models
- Configuration management
- Database model validation
- Settings classes

**Example Models:**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    mission: Optional[str] = None
    project_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')

class AgentResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime
    mission: Optional[str] = None
```

### httpx (>=0.25.0)

**Purpose:** Modern HTTP client for external API calls

**Key Features:**

- Async/sync HTTP client
- HTTP/2 support
- Connection pooling
- Request/response middleware
- Timeout handling

**Used In:**

- External AI API calls (OpenAI, Anthropic)
- Health checks for external services
- Integration with third-party services
- Service discovery

**Example Usage:**

```python
import httpx
from src.giljo_mcp.config import get_config

async def call_openai_api(prompt: str):
    config = get_config()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.openai_api_key}"},
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0
        )
        return response.json()
```

### uvicorn[standard] (>=0.23.0)

**Purpose:** Lightning-fast ASGI server

**Key Features:**

- High-performance async server
- Hot reload for development
- Multiple worker support
- WebSocket support
- SSL/TLS support

**Used In:**

- Running the FastAPI application
- Development server with hot reload
- Production deployment

**Configuration:**

```python
# Development
uvicorn src.giljo_mcp.api.main:app --reload --port 8000

# Production
uvicorn src.giljo_mcp.api.main:app --workers 4 --port 8000
```

## Additional API Dependencies

### python-multipart (>=0.0.6)

**Purpose:** Form data and file upload support

**Used For:**

- File upload endpoints
- Form-based authentication
- Multipart form data handling

### python-jose[cryptography] (>=3.3.0)

**Purpose:** JWT token handling

**Used For:**

- API authentication tokens
- Session management
- Secure token validation

## API Architecture

```
┌─────────────────┐    HTTP/REST     ┌─────────────────┐
│   Frontend      │ ──────────────→  │   FastAPI App   │
│   Dashboard     │      JSON        │   (uvicorn)     │
└─────────────────┘                  └─────────────────┘
                                             │
                                             │ httpx
                                             ▼
┌─────────────────┐                 ┌─────────────────┐
│   External APIs │                 │   Database      │
│   - OpenAI      │ ←───────────────│   - SQLAlchemy  │
│   - Anthropic   │                 │   - Async ORM   │
│   - GitHub      │                 └─────────────────┘
└─────────────────┘
```

## Request/Response Models

### Agent Management

```python
# Create Agent Request
{
    "name": "code_analyzer",
    "mission": "Analyze code structure and identify patterns",
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "config": {
        "max_context": 50000,
        "timeout": 300
    }
}

# Agent Response
{
    "id": "agent_456",
    "name": "code_analyzer",
    "status": "active",
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "created_at": "2024-01-01T12:00:00Z",
    "mission": "Analyze code structure and identify patterns",
    "metrics": {
        "tasks_completed": 5,
        "tokens_used": 12500,
        "uptime_seconds": 3600
    }
}
```

### Project Management

```python
# Create Project Request
{
    "name": "E-commerce Platform",
    "description": "Build a full-stack e-commerce solution",
    "repository_url": "https://github.com/user/ecommerce",
    "settings": {
        "ai_models": ["gpt-4", "claude-3"],
        "max_agents": 10
    }
}

# Project Response
{
    "id": "proj_123",
    "name": "E-commerce Platform",
    "status": "active",
    "agent_count": 3,
    "created_at": "2024-01-01T10:00:00Z",
    "repository_url": "https://github.com/user/ecommerce"
}
```

## Authentication & Security

### API Key Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(token: str = Depends(security)):
    if not verify_token(token.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return token.credentials
```

### JWT Token Authentication

```python
from jose import JWTError, jwt

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Error Handling

### HTTP Exception Handling

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Validation Error Handling

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "body": exc.body
        }
    )
```

## Performance Optimization

### Response Caching

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.get("/api/v1/agents/{agent_id}")
@cache(expire=300)  # Cache for 5 minutes
async def get_agent(agent_id: str):
    return await get_agent_from_db(agent_id)
```

### Request Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/v1/agents")
@limiter.limit("100/minute")
async def list_agents(request: Request):
    return await get_all_agents()
```

## Configuration

### Environment Variables

```bash
# API Server
GILJO_API_HOST=0.0.0.0
GILJO_API_PORT=8000
GILJO_API_WORKERS=4

# Security
GILJO_SECRET_KEY=your-secret-key
GILJO_ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Performance
GILJO_API_CACHE_TTL=300
GILJO_API_RATE_LIMIT=100
```

### API Configuration Class

```python
from pydantic_settings import BaseSettings

class APISettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    secret_key: str
    token_expire_minutes: int = 30

    # External API keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    class Config:
        env_prefix = "GILJO_API_"
```

## Testing

### Unit Tests

```python
from fastapi.testclient import TestClient
from src.giljo_mcp.api.main import app

client = TestClient(app)

def test_create_agent():
    response = client.post(
        "/api/v1/agents/",
        json={
            "name": "test_agent",
            "project_id": "test_project"
        }
    )
    assert response.status_code == 201
    assert response.json()["name"] == "test_agent"
```

### Integration Tests

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_api_integration():
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        # Create project
        project_response = await ac.post("/api/v1/projects/", json={
            "name": "Test Project"
        })
        project_id = project_response.json()["id"]

        # Create agent in project
        agent_response = await ac.post("/api/v1/agents/", json={
            "name": "test_agent",
            "project_id": project_id
        })

        assert agent_response.status_code == 201
```

## Monitoring & Observability

### Health Check Endpoint

```python
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "dependencies": {
            "database": await check_database_health(),
            "redis": await check_redis_health()
        }
    }
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)

    return response
```

## Troubleshooting

### Common Issues

#### 1. FastAPI Import Error

```bash
# Solution: Install FastAPI
pip install fastapi>=0.100.0 uvicorn[standard]>=0.23.0
```

#### 2. Pydantic Validation Errors

```bash
# Check your model definitions
python -c "from src.giljo_mcp.api.models import AgentCreateRequest; print('Models OK')"
```

#### 3. HTTP Client Timeout Issues

```python
# Increase timeout in httpx calls
async with httpx.AsyncClient(timeout=60.0) as client:
    response = await client.get(url)
```

#### 4. CORS Issues

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Best Practices

### 1. API Design

- Use RESTful conventions
- Implement proper HTTP status codes
- Provide clear error messages
- Use consistent response formats

### 2. Data Validation

- Validate all input data with Pydantic
- Use appropriate field constraints
- Handle validation errors gracefully

### 3. Performance

- Implement caching for expensive operations
- Use connection pooling for HTTP clients
- Monitor API performance metrics

### 4. Security

- Always validate and sanitize input
- Use proper authentication mechanisms
- Implement rate limiting
- Log security events

## Related Documentation

- [WebSocket Dependencies](./websocket.md) - Real-time communication
- [Database Dependencies](./database.md) - Data persistence
- [Security Dependencies](./security.md) - Authentication & authorization
- [Complete Dependencies Guide](../DEPENDENCIES.md) - All project dependencies

---

_The API layer is the primary interface for interacting with GiljoAI MCP. Ensure all dependencies are properly configured for optimal performance._
