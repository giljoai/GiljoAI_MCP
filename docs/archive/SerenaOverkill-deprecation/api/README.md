# API Endpoints - Complex Serena Implementation

This directory documents the API endpoints that would have been created for Serena
detection and attachment. Some were planned but never implemented.

## Planned Endpoints

### GET /api/setup/detect-serena

**Purpose**: Detect if Serena MCP is installed on the system

**Request**:
```http
GET /api/setup/detect-serena HTTP/1.1
Host: localhost:7272
```

**Response** (Success):
```json
{
  "installed": true,
  "uvx_available": true,
  "version": "1.2.3",
  "error": null
}
```

**Response** (Not Found):
```json
{
  "installed": false,
  "uvx_available": true,
  "version": null,
  "error": "Serena not found via uvx"
}
```

**Response** (uvx Not Available):
```json
{
  "installed": false,
  "uvx_available": false,
  "version": null,
  "error": "uvx not found on system PATH"
}
```

**Implementation**:
```python
from fastapi import APIRouter, HTTPException
from src.giljo_mcp.services.serena_detector import SerenaDetector

router = APIRouter(prefix="/api/setup", tags=["setup"])

@router.get("/detect-serena")
async def detect_serena():
    """Detect if Serena MCP is installed."""
    detector = SerenaDetector()
    result = detector.detect()
    return result
```

**Why This Is Wrong**:
- Subprocess calls on every request (slow, unreliable)
- Detection doesn't guarantee Claude Code has Serena
- Backend API can't know about Claude Code's MCP configuration
- Timeout handling adds complexity

### POST /api/setup/attach-serena

**Purpose**: Attach Serena MCP to Claude Code by modifying ~/.claude.json

**Request**:
```http
POST /api/setup/attach-serena HTTP/1.1
Host: localhost:7272
Content-Type: application/json

{
  "project_root": "/path/to/project"
}
```

**Response** (Success):
```json
{
  "success": true,
  "backup_path": "/home/user/.claude_backups/backup_20251006_143022.json",
  "error": null
}
```

**Response** (Failure):
```json
{
  "success": false,
  "backup_path": "/home/user/.claude_backups/backup_20251006_143022.json",
  "error": "Permission denied: /home/user/.claude.json"
}
```

**Implementation**:
```python
from pathlib import Path
from pydantic import BaseModel
from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

class AttachRequest(BaseModel):
    project_root: str

@router.post("/attach-serena")
async def attach_serena(request: AttachRequest):
    """Attach Serena MCP to Claude Code."""
    project_root = Path(request.project_root)

    if not project_root.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project root not found: {project_root}"
        )

    manager = ClaudeConfigManager()
    result = manager.inject_serena(project_root)

    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result["error"]
        )

    return result
```

**Why This Is Wrong**:
- Modifies ~/.claude.json (file outside our project)
- Assumes single .claude.json (what about multiple projects?)
- Can't verify changes actually affect Claude Code
- Complex rollback logic for wrong operation
- Security concern: API endpoint modifying user's home directory

### POST /api/setup/detach-serena

**Purpose**: Remove Serena MCP from Claude Code configuration

**Request**:
```http
POST /api/setup/detach-serena HTTP/1.1
Host: localhost:7272
```

**Response** (Success):
```json
{
  "success": true,
  "message": "Serena MCP removed successfully",
  "error": null
}
```

**Response** (Not Found):
```json
{
  "success": true,
  "message": "Serena not found in config",
  "error": null
}
```

**Implementation**:
```python
@router.post("/detach-serena")
async def detach_serena():
    """Remove Serena MCP from Claude Code."""
    manager = ClaudeConfigManager()
    result = manager.remove_serena()
    return result
```

**Why This Is Wrong**:
- Manipulates file outside our scope
- Can't handle multiple .claude.json files across projects
- User should manage their own Claude Code configuration

### GET /api/setup/serena-status

**Purpose**: Get current Serena configuration status

**Request**:
```http
GET /api/setup/serena-status HTTP/1.1
Host: localhost:7272
```

**Response**:
```json
{
  "enabled": true,
  "installed": true,
  "registered": true,
  "version": "1.2.3",
  "project_root": "/path/to/project"
}
```

**Implementation**:
```python
from src.giljo_mcp.services.config_service import ConfigService

@router.get("/serena-status")
async def serena_status():
    """Get Serena configuration status."""
    config_service = ConfigService()
    detector = SerenaDetector()

    # Get config
    config = config_service.get_serena_config()

    # Detect installation
    detection = detector.detect()

    # Check if registered in .claude.json
    manager = ClaudeConfigManager()
    claude_config = manager._load_config()
    registered = "serena" in claude_config.get("mcpServers", {})

    return {
        "enabled": config.get("enabled", False),
        "installed": detection["installed"],
        "registered": registered,
        "version": detection.get("version"),
        "project_root": str(Path.cwd())
    }
```

**Why This Is Wrong**:
- Combines state from multiple sources (config.yaml, subprocess, ~/.claude.json)
- Complex state that can be inconsistent
- "Registered" check assumes single .claude.json

## API Architecture

### Router Registration
```python
# api/app.py
from api.endpoints.setup import router as setup_router

app = FastAPI(title="GiljoAI MCP")
app.include_router(setup_router)
```

### Error Handling
```python
from fastapi import HTTPException

@router.post("/attach-serena")
async def attach_serena(request: AttachRequest):
    try:
        # Attachment logic
        ...
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Response Models
```python
from pydantic import BaseModel

class DetectionResponse(BaseModel):
    installed: bool
    uvx_available: bool
    version: str | None
    error: str | None

class AttachmentResponse(BaseModel):
    success: bool
    backup_path: str | None
    error: str | None

class StatusResponse(BaseModel):
    enabled: bool
    installed: bool
    registered: bool
    version: str | None
    project_root: str
```

## Security Considerations

### Input Validation
```python
from pathlib import Path

def validate_project_root(path: str) -> Path:
    """Validate project root path."""
    project_root = Path(path).resolve()

    # Prevent path traversal
    if ".." in path:
        raise ValueError("Path traversal not allowed")

    # Must be absolute path
    if not project_root.is_absolute():
        raise ValueError("Path must be absolute")

    # Must exist
    if not project_root.exists():
        raise ValueError("Path does not exist")

    return project_root
```

**Problem**: All this security is for validating paths to manipulate files outside our scope.

### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/detect-serena")
@limiter.limit("5/minute")  # Prevent DoS via subprocess calls
async def detect_serena(request: Request):
    ...
```

**Problem**: Rate limiting to prevent abuse of subprocess calls we shouldn't make.

### Authentication
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@router.post("/attach-serena")
async def attach_serena(
    request: AttachRequest,
    api_key: str = Depends(api_key_header)
):
    if api_key != os.getenv("GILJO_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    ...
```

**Problem**: Authentication for endpoints that modify files outside our project.

## Testing

### Endpoint Tests (from test_setup_serena_api.py)

```python
import pytest
from fastapi.testclient import TestClient

def test_detect_serena_success(client: TestClient, mock_detector):
    """Test successful Serena detection."""
    mock_detector.detect.return_value = {
        "installed": True,
        "uvx_available": True,
        "version": "1.2.3",
        "error": None
    }

    response = client.get("/api/setup/detect-serena")

    assert response.status_code == 200
    assert response.json()["installed"] is True
    assert response.json()["version"] == "1.2.3"

def test_attach_serena_success(client: TestClient, mock_manager):
    """Test successful Serena attachment."""
    mock_manager.inject_serena.return_value = {
        "success": True,
        "backup_path": "/path/to/backup.json",
        "error": None
    }

    response = client.post(
        "/api/setup/attach-serena",
        json={"project_root": "/path/to/project"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

def test_attach_serena_invalid_path(client: TestClient):
    """Test attachment with invalid project root."""
    response = client.post(
        "/api/setup/attach-serena",
        json={"project_root": "/nonexistent/path"}
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"]
```

**Why These Tests Are Wrong**:
- Testing API endpoints for operations we shouldn't do
- Mocking services that shouldn't exist
- Validating error handling for wrong functionality

## What Should Have Been Built Instead

### Simple Config Endpoint

```python
from pathlib import Path
import yaml
from pydantic import BaseModel

class SerenaConfigUpdate(BaseModel):
    use_in_prompts: bool

@router.patch("/api/config/serena")
async def update_serena_config(update: SerenaConfigUpdate):
    """Update Serena prompt inclusion setting."""
    config_path = Path.cwd() / "config.yaml"

    # Read current config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    # Update Serena setting
    if "features" not in config:
        config["features"] = {}
    if "serena_mcp" not in config["features"]:
        config["features"]["serena_mcp"] = {}

    config["features"]["serena_mcp"]["use_in_prompts"] = update.use_in_prompts

    # Write updated config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    return {
        "success": True,
        "use_in_prompts": update.use_in_prompts
    }

@router.get("/api/config/serena")
async def get_serena_config():
    """Get current Serena configuration."""
    config_path = Path.cwd() / "config.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    serena_config = config.get("features", {}).get("serena_mcp", {})

    return {
        "use_in_prompts": serena_config.get("use_in_prompts", False)
    }
```

**Lines of Code**: ~40 vs ~200+ (80% reduction)

**What's Better**:
- Only manages config.yaml (our file)
- Simple CRUD operations
- No subprocess calls
- No file manipulation outside our scope
- Fast, reliable, simple

## Complexity Comparison

### Complex Approach
- **Endpoints**: 4 (detect, attach, detach, status)
- **Services**: 3 (SerenaDetector, ClaudeConfigManager, ConfigService)
- **External calls**: Subprocess (uvx, serena)
- **File manipulation**: ~/.claude.json (outside our project)
- **Error modes**: 8+ (subprocess timeout, permissions, invalid JSON, etc.)
- **Security concerns**: High (subprocess injection, file permissions, path traversal)

### Simple Approach
- **Endpoints**: 2 (GET /config/serena, PATCH /config/serena)
- **Services**: 0 (direct YAML read/write)
- **External calls**: None
- **File manipulation**: config.yaml (our file)
- **Error modes**: 1 (config file not found)
- **Security concerns**: Low (only our config file)

## Key Lessons

### 1. API Endpoints Reflect Architecture
Wrong architecture → wrong endpoints

### 2. Subprocess Calls from API Are Red Flags
If your API spawns processes, ask: "Should this be the user's responsibility?"

### 3. File Manipulation Outside Project Scope
Endpoints that modify ~/.claude.json cross boundaries we shouldn't cross.

### 4. Complex State Across Multiple Sources
Combining state from config.yaml, subprocess, and ~/.claude.json is fragile.

### 5. CRUD Operations for Our Data Only
APIs should manage our own data (config.yaml), not external files.

## Conclusion

These API endpoints demonstrate RESTful design and proper FastAPI usage, but they're
built for the wrong functionality. The endpoints themselves are well-structured, but
they expose operations we shouldn't perform.

**Remember**: A well-designed API for the wrong operations is still wrong.

---

**Date**: October 6, 2025
**Archive Purpose**: Learning reference for API design mistakes
**Status**: Deprecated - use simple config CRUD instead
