# Download & Export API Endpoints Research
## Existing Patterns & Implementation Guide

**Research Date**: 2025-11-03  
**Codebase**: GiljoAI_MCP v3.0+  
**Status**: Complete Analysis of Existing Patterns

---

## 1. Existing Download/Export Endpoints

### 1.1 Claude Code Template Export Endpoint
**File**: `api/endpoints/claude_export.py` (625 lines)

**Endpoint**:
```
POST /api/export/claude-code
```

**Authentication**: 
- JWT cookie or X-API-Key header
- Dependency: `Depends(get_current_active_user)`

**Request Model**:
```python
class ClaudeExportRequest(BaseModel):
    export_path: str  # Must end with .claude/agents
```

**Response Model**:
```python
class ClaudeExportResult(BaseModel):
    success: bool
    exported_count: int
    files: list[dict[str, str]]  # [{name, path}, ...]
    message: str
    backup: Optional[dict[str, Any]]  # NEW: Handover 0075
```

**Key Features**:
- Multi-tenant isolation via `current_user.tenant_key`
- YAML frontmatter generation for Claude Code compatibility
- Automatic backup creation (`.old.YYYYMMDD_HHMMSS` format)
- ZIP backup support (Handover 0075)
- Path validation (only `.claude/agents/` directories)
- Programmatic export functions (for orchestrator use)

**Response Pattern**:
- Returns JSON response (not file download)
- Contains file paths and metadata
- Backup info included in response

---

### 1.2 MCP Installer Download Endpoints
**File**: `api/endpoints/mcp_installer.py` (464 lines)

**Endpoints**:
```
GET /api/mcp-installer/windows
GET /api/mcp-installer/unix
GET /api/mcp-installer/download/{token}/{platform}
```

**Authentication**:
- `get_current_user` (optional for public token endpoint)
- API key from `get_current_user` dependency

**Response Pattern**:
```python
# File download response
return Response(
    content=script_content,
    media_type="application/bat",  # or "application/sh"
    headers={"Content-Disposition": "attachment; filename=..."}
)
```

**Key Features**:
- Template-based script generation
- Embedded credentials (server URL, API key, username)
- Response object with Content-Disposition header
- Media type specific per file type
- Filename in Content-Disposition header

**Credential Handling**:
```python
# From request user context
api_key = getattr(current_user, 'api_key', f'gk_{current_user.username}_default')
server_url = get_server_url()  # From config.yaml
organization = current_user.organization.name
```

---

### 1.3 Template Archive/Export Functionality
**File**: `api/endpoints/templates.py` (1212 lines)

**Export-Related Features**:
- Template version history via GET /{template_id}/history
- Template diff comparison via GET /{template_id}/diff
- Template preview via POST /{template_id}/preview
- Archive creation on every update (automatic)

**Archive Response Model**:
```python
class TemplateHistoryResponse(BaseModel):
    id: str
    template_id: str
    name: str
    version: str
    template_content: str
    archive_reason: Optional[str]
    archive_type: str  # "auto" or "manual"
    archived_by: Optional[str]
    archived_at: datetime
    is_restorable: bool
    usage_count_at_archive: Optional[int]
    avg_generation_ms_at_archive: Optional[float]
```

---

## 2. Authentication Patterns

### 2.1 Standard Authentication Flow
**File**: `src/giljo_mcp/auth/dependencies.py`

**Two Authentication Methods** (v3.0 Unified):
1. JWT Cookie (web users): access_token from httpOnly cookie
2. API Key Header (MCP tools): X-API-Key header with gk_ prefix

**Priority Order**:
```python
async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    # 1. Try JWT cookie
    if access_token:
        try:
            payload = JWTManager.verify_token(access_token)
            return user_from_database
    
    # 2. Try API key header
    if x_api_key:
        verify_api_key(x_api_key)
        return user_from_api_key
    
    # 3. 401 if both fail
    raise HTTPException(401, "Unauthorized")
```

### 2.2 Active User Check
```python
@router.get("/...")
async def endpoint(
    current_user: User = Depends(get_current_active_user),  # Enforces is_active=True
    db: AsyncSession = Depends(get_db_session)
):
    # current_user guaranteed to exist and be active
    pass
```

### 2.3 Multi-Tenant Isolation
```python
# Always filter by current_user.tenant_key
context = {"tenant_key": current_user.tenant_key}
stmt = select(Template).where(
    Template.tenant_key == context["tenant_key"]
)
```

### 2.4 Admin-Only Endpoints
```python
@router.post("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(require_admin)  # Requires role="admin"
):
    pass
```

---

## 3. ZIP File Generation Pattern

### 3.1 Implementation (from claude_export.py)
```python
import zipfile
from pathlib import Path
from datetime import datetime, timezone

def create_zip_backup(agents_dir: Path) -> Optional[Path]:
    """Create timestamped zip backup of directory"""
    # 1. Check directory exists
    if not agents_dir.exists():
        return None
    
    # 2. Find .md files to backup
    md_files = list(agents_dir.glob("*.md"))
    if not md_files:
        return None
    
    # 3. Create backups directory
    backups_dir = agents_dir.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Generate timestamped filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"agents_backup_{timestamp}.zip"
    backup_path = backups_dir / backup_filename
    
    # 5. Create zip archive
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for md_file in md_files:
            zipf.write(md_file, arcname=md_file.name)
    
    logger.info(f"Created backup: {backup_path} ({len(md_files)} files)")
    return backup_path
```

**Key Patterns**:
- Always use pathlib.Path (cross-platform)
- Timestamp format: YYYYMMDD_HHMMSS
- Create subdirectory for backups
- Relative paths in ZIP (arcname=)
- ZIP_DEFLATED compression
- Logging at each step
- Return Path object or None

---

## 4. File Download Response Pattern

### 4.1 Response-Based Download (Recommended)
```python
from fastapi import APIRouter
from fastapi.responses import Response

@router.get("/download-file")
async def download_file(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Download file endpoint"""
    # 1. Generate or retrieve file content
    content = generate_or_load_content()
    
    # 2. Return Response with headers
    return Response(
        content=content,
        media_type="application/zip",  # or "application/json", "text/plain", etc.
        headers={
            "Content-Disposition": "attachment; filename=my-file.zip"
        }
    )
```

**Media Type Examples**:
- application/zip - ZIP files
- application/json - JSON files
- application/pdf - PDF files
- text/plain - Text files
- text/csv - CSV files
- application/octet-stream - Binary/unknown

**Content-Disposition Header**:
```
attachment; filename=filename.ext
```
- attachment forces download (vs inline display)
- filename parameter sets downloaded filename

### 4.2 FileResponse (Alternative)
```python
from fastapi.responses import FileResponse

@router.get("/download-file")
async def download_file():
    return FileResponse(
        path="/path/to/file.zip",
        filename="exported-templates.zip",
        media_type="application/zip"
    )
```

**Note**: FileResponse not used in existing codebase (Response is preferred)

---

## 5. Route Registration Pattern

### 5.1 Endpoint Registration in app.py
**File**: `api/app.py` (line ~525-565)

```python
# Import endpoint module
from .endpoints import (
    claude_export,
    templates,
    # ... others
)

# Register router with prefix and tags
app.include_router(
    claude_export.router,
    prefix="/api",
    tags=["claude-export"]
)

app.include_router(
    templates.router,
    prefix="/api/v1/templates",
    tags=["templates"]
)
```

**Pattern for New Download Endpoints**:
```python
# In api/endpoints/downloads.py
router = APIRouter()

@router.get("/download-templates")
async def download_templates(...):
    pass

# In api/app.py
from .endpoints import downloads
app.include_router(downloads.router, prefix="/api", tags=["downloads"])
```

---

## 6. Database Query Patterns

### 6.1 Multi-Tenant Isolation Template
```python
from sqlalchemy import select, and_
from src.giljo_mcp.models import AgentTemplate

# Always filter by tenant_key
stmt = select(AgentTemplate).where(
    and_(
        AgentTemplate.tenant_key == current_user.tenant_key,
        AgentTemplate.id == template_id
    )
)
result = await db.execute(stmt)
template = result.scalar_one_or_none()

if not template:
    raise HTTPException(status_code=404, detail="Not found or access denied")
```

### 6.2 Bulk Query Pattern
```python
# Get all templates for tenant
stmt = (
    select(AgentTemplate)
    .where(AgentTemplate.tenant_key == current_user.tenant_key)
    .order_by(AgentTemplate.name)
)
result = await db.execute(stmt)
templates = result.scalars().all()
```

---

## 7. Error Handling Patterns

### 7.1 HTTPException Usage
```python
from fastapi import HTTPException

# Invalid input
raise HTTPException(
    status_code=400,
    detail="Invalid export path format"
)

# Not found
raise HTTPException(
    status_code=404,
    detail="Template not found or access denied"
)

# Unauthorized
raise HTTPException(
    status_code=401,
    detail="Authentication required"
)

# Forbidden (access denied)
raise HTTPException(
    status_code=403,
    detail="System templates are read-only"
)

# Server error
raise HTTPException(
    status_code=500,
    detail=f"Export failed: {str(e)}"
)
```

### 7.2 Try-Except Pattern
```python
try:
    # Do work
    result = await some_operation()
    return result
except ValueError as e:
    logger.warning(f"Validation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail=f"Operation failed: {e}")
```

---

## 8. Logging Patterns

### 8.1 Standard Logging Usage
```python
import logging

logger = logging.getLogger(__name__)

# Info level
logger.info(f"Operation started for user: {current_user.username}")

# Warning level
logger.warning(f"Export path validation failed: {error}")

# Error with exception info
logger.exception(f"Export failed: {e}")

# Debug for development
logger.debug(f"Processing file: {filename}")
```

---

## 9. Validation Patterns

### 9.1 Pydantic Field Validators
```python
from pydantic import BaseModel, Field, field_validator

class ExportRequest(BaseModel):
    export_path: str = Field(
        ...,
        description="Path to export directory",
        examples=["/path/to/dir"]
    )
    
    @field_validator("export_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        # Normalize for cross-platform
        normalized = v.replace("\\", "/")
        
        # Business logic validation
        if not normalized.endswith(".claude/agents"):
            raise ValueError("Path must end with '.claude/agents'")
        
        return v
```

### 9.2 Runtime Validation
```python
# Check directory exists
if not export_dir.exists():
    raise ValueError(f"Directory does not exist: {export_dir}")

# Check is directory
if not export_dir.is_dir():
    raise ValueError(f"Path is not a directory: {export_dir}")

# Check permissions
if not export_dir.stat().st_mode & 0o200:
    raise ValueError(f"No write permission: {export_dir}")
```

---

## 10. Recommended Implementation Checklist

When implementing new download/export endpoints, follow this pattern:

### Step 1: Create Pydantic Models
```python
class DownloadRequest(BaseModel):
    # Request parameters
    template_ids: list[str]
    include_backups: bool = False
    format: str = "zip"

class DownloadResponse(BaseModel):
    # Response metadata
    success: bool
    file_size_bytes: int
    file_count: int
    generated_at: datetime
```

### Step 2: Create Router Module
```python
# api/endpoints/downloads.py
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import zipfile
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/download-templates")
async def download_templates(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    format: str = Query("zip", regex="^(zip|json|csv)$")
):
    """Download templates in specified format"""
    try:
        # 1. Validate and authorize
        if not current_user.is_active:
            raise HTTPException(401, "User not active")
        
        # 2. Query data with tenant isolation
        stmt = select(Template).where(
            Template.tenant_key == current_user.tenant_key
        )
        result = await db.execute(stmt)
        templates = result.scalars().all()
        
        if not templates:
            raise HTTPException(404, "No templates found")
        
        # 3. Generate file content
        if format == "zip":
            content = await generate_zip(templates)
            media_type = "application/zip"
            filename = f"templates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        elif format == "json":
            content = json.dumps([t.dict() for t in templates])
            media_type = "application/json"
            filename = "templates.json"
        
        # 4. Return response
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Download failed: {e}")
        raise HTTPException(500, f"Download failed: {str(e)}")
```

### Step 3: Register in app.py
```python
from .endpoints import downloads

app.include_router(
    downloads.router,
    prefix="/api",
    tags=["downloads"]
)
```

### Step 4: Add to Handover Documentation
- Document endpoint
- List supported formats
- Provide example curl/API calls
- Note any breaking changes

---

## 11. Summary of Key Patterns

| Pattern | Location | Usage |
|---------|----------|-------|
| Authentication | src/giljo_mcp/auth/dependencies.py | Depends(get_current_active_user) |
| Multi-Tenant | All endpoints | where(Model.tenant_key == user.tenant_key) |
| File Download | mcp_installer.py | Response(..., headers={"Content-Disposition": ...}) |
| ZIP Creation | claude_export.py | zipfile.ZipFile(..., "w", ZIP_DEFLATED) |
| Error Handling | All endpoints | HTTPException(status_code, detail) |
| Logging | All modules | logger.info/warning/exception() |
| Validation | Templates/requests | @field_validator or runtime checks |
| Router Registration | app.py | app.include_router(router, prefix, tags) |

---

## 12. Files to Reference for Implementation

1. **claude_export.py** - Best example for template export (ZIP backup pattern)
2. **mcp_installer.py** - Best example for file download response
3. **templates.py** - Best example for CRUD with history/versioning
4. **dependencies.py** - Authentication patterns
5. **app.py** - Router registration patterns

---

**End of Research Document**
