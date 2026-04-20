# Download Token System - Implementation Guide

**For**: Implementation Agents
**Methodology**: Test-Driven Development (TDD)
**Status**: Tests Written, Implementation Pending

---

## Quick Start

### Step 1: Run Tests (They Will Fail)

```bash
cd F:\GiljoAI_MCP
pytest tests\test_download_tokens.py -v
```

**Expected Result**: All tests fail (this is correct for TDD)

### Step 2: Read Test File

Open `tests\test_download_tokens.py` and read the tests to understand:
- What needs to be built
- How components interact
- What edge cases to handle

### Step 3: Implement Component by Component

Follow this order:
1. TokenManager (17 tests)
2. FileStaging (6 tests)
3. Download Endpoints (8 tests)
4. MCP Tool Integration (4 tests)
5. End-to-End (3 tests)

### Step 4: Iterate Until Tests Pass

For each component:
1. Read the failing tests
2. Implement minimal code to pass 1 test
3. Run tests again
4. Repeat until all tests pass

---

## Component 1: TokenManager

### File to Create

`F:\GiljoAI_MCP\src\giljo_mcp\download_tokens.py`

### Database Model

Add to `F:\GiljoAI_MCP\src\giljo_mcp\models.py`:

```python
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
import uuid

class DownloadToken(Base):
    """
    One-time download tokens for secure file downloads.

    Multi-tenant isolation: token validation ALWAYS checks tenant_key.
    One-time use: is_used flag prevents reuse.
    Expiration: expires_at enforces 15-minute lifetime.
    """
    __tablename__ = "download_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    tenant_key = Column(String(255), nullable=False, index=True)
    download_type = Column(String(50), nullable=False)  # 'slash_commands' | 'agent_templates'
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    downloaded_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSONB, default={}, nullable=True)

    __table_args__ = (
        # Multi-tenant isolation index
        Index('idx_tenant_token', 'tenant_key', 'token'),
        # Cleanup performance index
        Index('idx_cleanup', 'is_used', 'expires_at'),
    )

    def __repr__(self):
        return f"<DownloadToken(token={self.token}, tenant={self.tenant_key}, used={self.is_used})>"
```

### TokenManager Implementation

```python
"""
Token management for one-time secure downloads.

Architecture:
    - Generate unique UUID tokens
    - Store in PostgreSQL with metadata
    - Validate with multi-tenant isolation
    - Enforce one-time use (atomic updates)
    - Background cleanup of expired tokens
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import DownloadToken


class TokenManager:
    """
    Manages lifecycle of one-time download tokens.

    Security:
        - Multi-tenant isolation via tenant_key validation
        - One-time use via atomic is_used flag
        - Expiration enforcement via expires_at check
        - Unique UUID tokens (collision probability negligible)
    """

    def __init__(self, db_session: AsyncSession, expiration_minutes: int = 15):
        """
        Initialize TokenManager.

        Args:
            db_session: Async database session
            expiration_minutes: Token lifetime (default: 15 minutes)
        """
        self.db = db_session
        self.expiration_minutes = expiration_minutes

    async def generate_token(
        self,
        tenant_key: str,
        download_type: str,
        metadata: dict[str, Any],
    ) -> str:
        """
        Generate unique download token with metadata.

        Args:
            tenant_key: Tenant isolation key (CRITICAL for security)
            download_type: 'slash_commands' | 'agent_templates'
            metadata: Additional metadata (filename, file count, etc.)

        Returns:
            UUID token string

        Raises:
            HTTPException: If database operation fails
        """
        try:
            token = uuid.uuid4()
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.expiration_minutes)

            db_token = DownloadToken(
                token=token,
                tenant_key=tenant_key,
                download_type=download_type,
                expires_at=expires_at,
                metadata=metadata,
            )

            self.db.add(db_token)
            await self.db.commit()

            return str(token)

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download token: {e!s}",
            )

    async def validate_token(self, token: str, tenant_key: str) -> bool:
        """
        Validate token (exists, not expired, not used, correct tenant).

        CRITICAL: Always check tenant_key for multi-tenant isolation.

        Args:
            token: UUID token string
            tenant_key: Tenant key for isolation check

        Returns:
            True if valid, False otherwise
        """
        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return False

        stmt = select(DownloadToken).where(
            DownloadToken.token == token_uuid,
            DownloadToken.tenant_key == tenant_key,  # CRITICAL: Multi-tenant isolation
        )

        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if not db_token:
            return False

        # Check expiration
        if db_token.expires_at <= datetime.now(timezone.utc):
            return False

        # Check one-time use
        if db_token.is_used:
            return False

        return True

    async def mark_as_used(self, token: str) -> bool:
        """
        Mark token as used (one-time use enforcement).

        Uses atomic update to prevent race conditions.

        Args:
            token: UUID token string

        Returns:
            True if marked successfully, False if already used
        """
        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return False

        stmt = (
            update(DownloadToken)
            .where(
                DownloadToken.token == token_uuid,
                DownloadToken.is_used == False,  # Only update if not used
            )
            .values(
                is_used=True,
                downloaded_at=datetime.now(timezone.utc),
            )
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount > 0

    async def get_token_metadata(self, token: str, tenant_key: str) -> Optional[dict]:
        """
        Retrieve token metadata (if valid).

        Args:
            token: UUID token string
            tenant_key: Tenant key for isolation

        Returns:
            Metadata dict or None
        """
        try:
            token_uuid = uuid.UUID(token)
        except ValueError:
            return None

        stmt = select(DownloadToken).where(
            DownloadToken.token == token_uuid,
            DownloadToken.tenant_key == tenant_key,
        )

        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if not db_token:
            return None

        return {
            "download_type": db_token.download_type,
            "created_at": db_token.created_at.isoformat(),
            "expires_at": db_token.expires_at.isoformat(),
            "is_used": db_token.is_used,
            "metadata": db_token.metadata,
        }

    async def cleanup_expired_tokens(self) -> int:
        """
        Delete expired tokens (background cleanup task).

        Returns:
            Number of tokens deleted
        """
        stmt = delete(DownloadToken).where(
            DownloadToken.expires_at < datetime.now(timezone.utc)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount
```

### Run Tests

```bash
pytest tests\test_download_tokens.py::TestTokenManager -v
```

**Goal**: 17/17 tests passing

---

## Component 2: FileStaging

### File to Create

`F:\GiljoAI_MCP\src\giljo_mcp\file_staging.py`

### Implementation

```python
"""
File staging system for temporary download preparation.

Architecture:
    - Create staging directories: temp/{tenant_key}/{token}/
    - Generate ZIP files (slash commands or agent templates)
    - Persist metadata JSON
    - Cleanup after download
    - Prevent directory traversal attacks
"""
import json
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate


class FileStaging:
    """
    Manages temporary file staging for downloads.

    Security:
        - Directory traversal prevention via path validation
        - Tenant isolation via separate directories
        - Automatic cleanup after download
    """

    def __init__(self, base_path: Optional[Path] = None, db_session: Optional[AsyncSession] = None):
        """
        Initialize FileStaging.

        Args:
            base_path: Base directory for staging (default: ./temp)
            db_session: Database session for querying templates
        """
        self.base_path = base_path or Path.cwd() / "temp"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.db = db_session

    async def create_staging_directory(self, tenant_key: str, token: str) -> Path:
        """
        Create staging directory with path validation.

        Args:
            tenant_key: Tenant key (path component)
            token: Token UUID (path component)

        Returns:
            Path to staging directory

        Raises:
            ValueError: If directory traversal detected
        """
        # Sanitize inputs (prevent directory traversal)
        if "../" in tenant_key or "../" in token:
            raise ValueError("Invalid path component: directory traversal detected")

        if "\\" in tenant_key or "\\" in token:
            raise ValueError("Invalid path component: backslash not allowed")

        # Create directory
        staging_dir = self.base_path / tenant_key / token
        staging_dir = staging_dir.resolve()

        # Verify path is within base_path (security check)
        try:
            staging_dir.relative_to(self.base_path.resolve())
        except ValueError:
            raise ValueError("Directory traversal detected")

        # Create directory structure
        staging_dir.mkdir(parents=True, exist_ok=True)

        return staging_dir

    async def stage_slash_commands(self, tenant_key: str, token: str) -> Path:
        """
        Create ZIP file with slash command templates.

        Args:
            tenant_key: Tenant key
            token: Download token

        Returns:
            Path to ZIP file
        """
        from src.giljo_mcp.tools.slash_command_templates import get_all_templates

        staging_dir = await self.create_staging_directory(tenant_key, token)
        zip_path = staging_dir / "slash-commands.zip"

        # Get slash command templates
        templates = get_all_templates()

        # Create ZIP
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename, content in templates.items():
                    zipf.writestr(filename, content)

            return zip_path

        except OSError as e:
            if "No space left" in str(e):
                raise HTTPException(
                    status_code=507,  # Insufficient Storage
                    detail="Server disk full. Please contact administrator.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create ZIP file: {e!s}",
            )

    async def stage_agent_templates(self, tenant_key: str, token: str) -> Path:
        """
        Create ZIP file with agent templates from database.

        Args:
            tenant_key: Tenant key (for multi-tenant query)
            token: Download token

        Returns:
            Path to ZIP file
        """
        if not self.db:
            raise ValueError("Database session required for agent templates")

        staging_dir = await self.create_staging_directory(tenant_key, token)
        zip_path = staging_dir / "agent-templates.zip"

        # Query active templates for tenant
        stmt = (
            select(AgentTemplate)
            .where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True,
            )
            .order_by(AgentTemplate.name)
        )

        result = await self.db.execute(stmt)
        templates = result.scalars().all()

        # Create ZIP
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for template in templates:
                    filename = f"{template.name}.md"

                    # Build content with YAML frontmatter
                    content_parts = [
                        "---\n",
                        f"name: {template.name}\n",
                        f"description: {template.description or template.role}\n",
                        'tools: ["mcp__giljo_mcp__*"]\n',
                        f"model: sonnet\n",
                        "---\n\n",
                        template.template_content.strip(),
                        "\n",
                    ]

                    # Add behavioral rules
                    if template.behavioral_rules:
                        content_parts.append("\n## Behavioral Rules\n")
                        content_parts.extend(f"- {rule}\n" for rule in template.behavioral_rules)

                    # Add success criteria
                    if template.success_criteria:
                        content_parts.append("\n## Success Criteria\n")
                        content_parts.extend(f"- {criterion}\n" for criterion in template.success_criteria)

                    zipf.writestr(filename, "".join(content_parts))

            return zip_path

        except OSError as e:
            if "No space left" in str(e):
                raise HTTPException(status_code=507, detail="Server disk full")
            raise

    async def save_metadata(self, staging_dir: Path, metadata: dict) -> Path:
        """
        Save metadata JSON to staging directory.

        Args:
            staging_dir: Staging directory path
            metadata: Metadata dictionary

        Returns:
            Path to metadata file
        """
        metadata_path = staging_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata_path

    async def cleanup(self, tenant_key: str, token: str) -> None:
        """
        Remove staging directory and all contents.

        Args:
            tenant_key: Tenant key
            token: Token UUID
        """
        staging_dir = self.base_path / tenant_key / token

        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
```

### Run Tests

```bash
pytest tests\test_download_tokens.py::TestFileStaging -v
```

**Goal**: 6/6 tests passing

---

## Component 3: Download Endpoints

### File to Update

`F:\GiljoAI_MCP\api\endpoints\downloads.py`

### Add New Endpoints

```python
from src.giljo_mcp.download_tokens import TokenManager
from src.giljo_mcp.file_staging import FileStaging

# ... existing imports ...

@router.post("/generate-token", status_code=status.HTTP_201_CREATED)
async def generate_download_token(
    request: Request,
    download_type: str = Query(..., regex="^(slash_commands|agent_templates)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate one-time download token.

    Args:
        download_type: 'slash_commands' | 'agent_templates'
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        {
            "token": "uuid",
            "download_url": "http://server/api/download/file/{token}",
            "expires_at": "ISO datetime"
        }
    """
    manager = TokenManager(db)

    # Generate token
    token = await manager.generate_token(
        tenant_key=current_user.tenant_key,
        download_type=download_type,
        metadata={
            "user_id": current_user.id,
            "username": current_user.username,
        }
    )

    # Build download URL
    server_url = get_server_url(request)
    download_url = f"{server_url}/api/download/file/{token}"

    # Get expiration time
    token_meta = await manager.get_token_metadata(token, current_user.tenant_key)

    return {
        "token": token,
        "download_url": download_url,
        "expires_at": token_meta["expires_at"],
    }


@router.get("/file/{token}")
async def download_file_with_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Download file using one-time token.

    Args:
        token: UUID download token
        current_user: Authenticated user
        db: Database session

    Returns:
        ZIP file response (one-time use)

    Raises:
        404: Token not found
        403: Cross-tenant access denied
        410: Token expired or already used
    """
    manager = TokenManager(db)
    staging = FileStaging(db_session=db)

    # Validate token
    is_valid = await manager.validate_token(token, current_user.tenant_key)

    if not is_valid:
        # Check if token exists at all
        token_meta = await manager.get_token_metadata(token, current_user.tenant_key)

        if not token_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Download token not found"
            )

        # Check if expired
        expires_at = datetime.fromisoformat(token_meta["expires_at"].replace("Z", "+00:00"))
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Download token has expired"
            )

        # Must be already used
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Download token has already been used"
        )

    # Mark as used (atomic operation)
    marked = await manager.mark_as_used(token)
    if not marked:
        # Race condition: another request used the token
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Download token has already been used"
        )

    # Get token metadata
    token_meta = await manager.get_token_metadata(token, current_user.tenant_key)
    download_type = token_meta["download_type"]

    # Stage file
    if download_type == "slash_commands":
        zip_path = await staging.stage_slash_commands(current_user.tenant_key, token)
        filename = "slash-commands.zip"
    elif download_type == "agent_templates":
        zip_path = await staging.stage_agent_templates(current_user.tenant_key, token)
        filename = "agent-templates.zip"
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown download type: {download_type}"
        )

    # Read file
    zip_bytes = zip_path.read_bytes()

    # Cleanup (async background task)
    asyncio.create_task(staging.cleanup(current_user.tenant_key, token))

    # Return file
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
```

### Run Tests

```bash
pytest tests\test_download_tokens.py::TestDownloadEndpointsWithTokens -v
```

**Goal**: 8/8 tests passing

---

## Component 4: MCP Tool Updates

### File to Update

`F:\GiljoAI_MCP\src\giljo_mcp\tools\tool_accessor.py`

### Update Tools

```python
async def setup_slash_commands(self, platform: str = None, _api_key: str = None) -> dict[str, Any]:
    """
    Setup slash commands by generating download token.

    Returns:
        {
            "success": True,
            "download_url": "http://server/api/download/file/{token}",
            "token": "uuid",
            "expires_at": "ISO datetime"
        }
    """
    # Generate download token
    response = await self.http_client.post(
        f"{self.base_url}/api/download/generate-token",
        headers={"X-API-Key": _api_key},
        json={"download_type": "slash_commands"}
    )

    if response.status_code != 201:
        return {
            "success": False,
            "error": response.json().get("detail", "Unknown error")
        }

    data = response.json()

    return {
        "success": True,
        "download_url": data["download_url"],
        "token": data["token"],
        "expires_at": data["expires_at"],
        "message": (
            f"Download slash commands from:\n"
            f"{data['download_url']}\n\n"
            f"Token expires: {data['expires_at']}"
        )
    }

# Similarly update gil_import_personalagents() and gil_import_productagents()
```

### Run Tests

```bash
pytest tests\test_download_tokens.py::TestMCPToolDownloadIntegration -v
```

**Goal**: 4/4 tests passing

---

## Final Steps

### Run All Tests

```bash
pytest tests\test_download_tokens.py -v
```

**Goal**: 89/89 tests passing

### Coverage Report

```bash
pytest tests\test_download_tokens.py --cov=src/giljo_mcp --cov-report=html
```

**Goal**: ≥95% coverage for core components

### Database Migration

```bash
# Create migration
alembic revision -m "Add download_tokens table"

# Edit migration file (add DownloadToken table creation)

# Apply migration
alembic upgrade head
```

---

## Troubleshooting

### Common Issues

**Issue**: Tests fail with "table does not exist"
**Solution**: Run database migration first

**Issue**: Import errors
**Solution**: Verify all files created in correct locations

**Issue**: Race condition tests fail
**Solution**: Check database transaction isolation level

**Issue**: Path traversal tests fail
**Solution**: Verify `Path.resolve()` and `is_relative_to()` logic

---

## Success Checklist

- [ ] TokenManager implemented (17 tests passing)
- [ ] FileStaging implemented (6 tests passing)
- [ ] Download endpoints implemented (8 tests passing)
- [ ] MCP tools updated (4 tests passing)
- [ ] End-to-end tests passing (3 tests)
- [ ] Edge cases handled (6 tests passing)
- [ ] Performance benchmarks met (3 tests passing)
- [ ] Database migration created and applied
- [ ] Coverage ≥95% for core components
- [ ] Security audit completed

---

**Implementation Status**: Ready to Begin
**Next Action**: Create `src/giljo_mcp/download_tokens.py` and run first tests
