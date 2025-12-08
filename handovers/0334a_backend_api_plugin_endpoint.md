# Handover 0334a: Backend API - Plugin Template Endpoint

## Status: READY FOR IMPLEMENTATION
## Priority: HIGH (Critical Path for 0334 Series)
## Type: Backend API / Feature Enhancement
## Parent Handover: 0334 (Claude Code Plugin Integration)
## Estimated Effort: 3-4 hours (TDD with specialized subagents)

---

## Context: How We Got Here

### The Journey from Handover 0333 to 0334a

1. **Handover 0333** (COMPLETE): Simplified staging prompt from 150+ lines to ~35 lines by:
   - Moving agent discovery from embedded lists to MCP `get_available_agents()` calls
   - Reducing orchestrator token footprint by 71% (420 tokens saved)
   - Establishing dynamic agent discovery pattern

2. **Discovery of agent_type Enforcement Problem**:
   - During testing, we found orchestrators must match exact template names when spawning agents
   - Example: `agent_type: "Documentation Manager"` must exactly match database `role` field
   - This creates a tight coupling between orchestrator prompts and database state

3. **User Insight - Claude Code Plugin System**:
   - Claude Code has a plugin architecture that can fetch agents dynamically from external sources
   - Plugins act as "agent marketplaces" - providing a curated list of available agents
   - This matches perfectly with GiljoAI's multi-tenant template architecture

4. **Key Realization - GiljoAI as Agent Marketplace**:
   - We can use the plugin as a bridge between Claude Code and our PostgreSQL database
   - Each tenant gets their own custom agent library (multi-tenant isolation)
   - Plugin calls our backend API to fetch templates dynamically
   - **Critical Constraint**: Plugins cannot pass JWT tokens (they're external tools, not authenticated users)

### Why This Sub-Handover Exists

We need a NEW API endpoint specifically designed for the Claude Code plugin that:
- Uses `tenant_key` query parameter (no JWT authentication required)
- Returns the full agent instructions (not just descriptions)
- Includes capabilities arrays for Claude Code's agent system
- Provides cache hints for client-side performance
- Has rate limiting to prevent enumeration attacks

This sub-handover implements the backend API endpoint. Sister handovers will implement:
- **0334b**: Claude Code plugin itself (TypeScript/JavaScript)
- **0334c**: Plugin installation and configuration guide
- **0334d**: Integration testing between plugin and API

---

## Problem Statement

**Current State**: The existing `/api/v1/agents/templates` endpoint:
- Requires JWT authentication via `get_current_active_user` dependency
- Returns metadata-only responses (no full instructions)
- Designed for web dashboard consumption, not plugin integration
- Response format incompatible with Claude Code's agent schema

**Desired State**: A new `/api/v1/agent-templates/plugin` endpoint that:
- Accepts `tenant_key` as query parameter (no JWT required)
- Returns full agent instructions (`template_content` field)
- Includes `capabilities` arrays for Claude Code
- Has built-in rate limiting (prevent tenant_key enumeration)
- Maintains multi-tenant isolation (only returns templates for specified tenant)

---

## Technical Specification

### Endpoint Definition

**URL**: `GET /api/v1/agent-templates/plugin`

**Authentication**: None (public endpoint with rate limiting)

**Query Parameters**:
| Parameter | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| `tenant_key` | string | Yes | User's tenant key (format: `tk_<uuid>`) | Must match pattern `^tk_[a-f0-9-]{36}$` |
| `include_inactive` | boolean | No | Include inactive templates (default: false) | Optional flag |

**Rate Limiting**:
- 100 requests per minute per `tenant_key`
- 429 Too Many Requests if limit exceeded
- Rate limit window: 60 seconds (sliding window)

**Response Schema** (200 OK):
```json
{
  "templates": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Documentation Manager",
      "role": "documentation-manager",
      "category": "role",
      "description": "Maintains project documentation, devlogs, and session memories",
      "full_instructions": "You are the Documentation Manager Agent...",
      "capabilities": [
        "documentation_writing",
        "devlog_creation",
        "session_memory_management",
        "markdown_formatting"
      ],
      "version": "1.0.0",
      "background_color": "#4CAF50",
      "cli_tool": "claude",
      "model": "sonnet"
    }
  ],
  "tenant_key": "tk_550e8400-e29b-41d4-a716-446655440000",
  "count": 1,
  "cache_ttl": 300
}
```

**Error Responses**:

| Status Code | Condition | Response Body |
|-------------|-----------|---------------|
| 400 | Missing or invalid `tenant_key` | `{"detail": "Invalid tenant_key format. Expected: tk_<uuid>"}` |
| 404 | Tenant not found | `{"detail": "No templates found for tenant"}` (not an error - empty list) |
| 429 | Rate limit exceeded | `{"detail": "Rate limit exceeded. Try again in 60 seconds."}` |
| 500 | Internal server error | `{"detail": "Internal server error"}` |

**Important**: Return empty list (200 OK) for unknown tenant_keys, not 404. This prevents tenant enumeration attacks.

---

## Implementation Details

### File Location

**Primary File**: `F:\GiljoAI_MCP\api\endpoints\agent_templates.py` (add to existing file)

**Test File**: `F:\GiljoAI_MCP\tests\api\test_agent_templates_plugin.py` (create new)

### Pydantic Models

Add these models to `agent_templates.py`:

```python
from typing import Optional
from pydantic import BaseModel, Field, validator


class PluginTemplate(BaseModel):
    """Agent template response for Claude Code plugin"""
    id: str = Field(..., description="Template UUID")
    name: str = Field(..., description="Human-readable template name")
    role: str = Field(..., description="Agent role identifier (kebab-case)")
    category: str = Field(..., description="Template category (role, project_type, custom)")
    description: Optional[str] = Field(None, description="Template description")
    full_instructions: str = Field(..., description="Complete agent instructions (system + user)")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    version: str = Field(..., description="Template version (semver)")
    background_color: Optional[str] = Field(None, description="Hex color code for visualization")
    cli_tool: str = Field(default="claude", description="CLI tool: claude, codex, gemini")
    model: Optional[str] = Field(None, description="Model selection: sonnet, opus, haiku")

    @validator("full_instructions")
    def validate_instructions_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("full_instructions cannot be empty")
        return v


class PluginTemplateResponse(BaseModel):
    """Response model for plugin template endpoint"""
    templates: list[PluginTemplate] = Field(..., description="List of agent templates")
    tenant_key: str = Field(..., description="Tenant key used for query")
    count: int = Field(..., description="Number of templates returned")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
```

### Rate Limiting Implementation

Add rate limiting helper (inline implementation for simplicity):

```python
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict

# In-memory rate limit store (use Redis in production)
_rate_limit_store: Dict[str, list[datetime]] = defaultdict(list)

def check_rate_limit(tenant_key: str, limit: int = 100, window_seconds: int = 60) -> bool:
    """
    Check if request is within rate limit.

    Args:
        tenant_key: Tenant identifier
        limit: Maximum requests per window
        window_seconds: Time window in seconds

    Returns:
        True if within limit, False if exceeded
    """
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)

    # Clean old requests
    _rate_limit_store[tenant_key] = [
        req_time for req_time in _rate_limit_store[tenant_key]
        if req_time > window_start
    ]

    # Check limit
    if len(_rate_limit_store[tenant_key]) >= limit:
        return False

    # Record request
    _rate_limit_store[tenant_key].append(now)
    return True
```

**Production Note**: Replace in-memory store with Redis for distributed rate limiting:
```python
# TODO (v4.0): Migrate to Redis for production
# redis_client.incr(f"rate_limit:{tenant_key}", expiry=60)
```

### Endpoint Function

Add this endpoint to `agent_templates.py`:

```python
@router.get("/plugin", response_model=PluginTemplateResponse)
async def get_templates_for_plugin(
    tenant_key: str = Query(..., description="User's tenant key (format: tk_<uuid>)", regex=r"^tk_[a-f0-9-]{36}$"),
    include_inactive: bool = Query(False, description="Include inactive templates"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Fetch agent templates for Claude Code plugin.

    This endpoint is designed for external plugin consumption and does NOT require
    JWT authentication. Instead, it uses tenant_key for multi-tenant isolation.

    **Security Considerations**:
    - Rate limited to 100 requests/minute per tenant_key
    - Returns empty list for unknown tenant_keys (prevents enumeration)
    - Only returns active templates unless include_inactive=true
    - Excludes system-managed roles (orchestrator, staging)

    **Response**:
    - templates: Array of full agent templates with instructions
    - tenant_key: Echo of input tenant_key for verification
    - count: Number of templates returned
    - cache_ttl: Suggested cache duration (300 seconds)

    **Example**:
    ```
    GET /api/v1/agent-templates/plugin?tenant_key=tk_550e8400-e29b-41d4-a716-446655440000
    ```
    """
    from api.app import state

    # Rate limiting check
    if not check_rate_limit(tenant_key):
        logger.warning(f"Rate limit exceeded for tenant: {tenant_key}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 100 requests per minute per tenant."
        )

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Query active templates for tenant
        async with state.db_manager.get_session_async() as session:
            # Build query
            stmt = (
                select(AgentTemplate)
                .where(AgentTemplate.tenant_key == tenant_key)
                .where(AgentTemplate.role.notin_(list(SYSTEM_MANAGED_ROLES)))
                .order_by(AgentTemplate.category, AgentTemplate.role)
            )

            # Filter by active status unless include_inactive=True
            if not include_inactive:
                stmt = stmt.where(AgentTemplate.is_active == True)

            result = await session.execute(stmt)
            templates = result.scalars().all()

        # Build response (return empty list for unknown tenants, not 404)
        plugin_templates = []
        for template in templates:
            # Combine system + user instructions for full instructions
            full_instructions = build_full_instructions(template)

            # Extract capabilities from meta_data or default to role-based
            capabilities = template.meta_data.get("capabilities", []) if template.meta_data else []
            if not capabilities:
                # Fallback: generate capabilities from role name
                capabilities = generate_default_capabilities(template.role)

            plugin_templates.append(
                PluginTemplate(
                    id=template.id,
                    name=template.name,
                    role=template.role or "general",
                    category=template.category,
                    description=template.description,
                    full_instructions=full_instructions,
                    capabilities=capabilities,
                    version=template.version,
                    background_color=template.background_color,
                    cli_tool=template.cli_tool,
                    model=template.model,
                )
            )

        logger.info(
            f"Plugin endpoint: Returned {len(plugin_templates)} templates for tenant {tenant_key}"
        )

        return PluginTemplateResponse(
            templates=plugin_templates,
            tenant_key=tenant_key,
            count=len(plugin_templates),
            cache_ttl=300,  # 5 minutes cache hint
        )

    except Exception as e:
        logger.error(f"Failed to fetch plugin templates for tenant {tenant_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


def build_full_instructions(template: AgentTemplate) -> str:
    """
    Build complete agent instructions from template.

    Combines system_instructions + user_instructions (v3.1 dual-field system).
    Falls back to template_content for backward compatibility.

    Args:
        template: AgentTemplate database object

    Returns:
        Complete agent instructions as markdown string
    """
    # v3.1 dual-field system (Handover 0106)
    if template.system_instructions or template.user_instructions:
        system_part = template.system_instructions or ""
        user_part = template.user_instructions or ""
        return f"{system_part}\n\n{user_part}".strip()

    # Fallback to legacy template_content
    return template.template_content or ""


def generate_default_capabilities(role: str) -> list[str]:
    """
    Generate default capabilities from role name.

    This is a fallback for templates that don't have capabilities
    defined in meta_data.

    Args:
        role: Agent role identifier (e.g., "documentation-manager")

    Returns:
        List of capability strings
    """
    # Convert role to capability tokens
    # Example: "documentation-manager" -> ["documentation", "management"]
    tokens = role.lower().replace("-", "_").split("_")

    # Add generic capabilities
    capabilities = tokens.copy()
    capabilities.append("collaboration")
    capabilities.append("mcp_integration")

    return capabilities
```

---

## TDD Testing Plan

### Test File Structure

Create `tests/api/test_agent_templates_plugin.py`:

```python
"""
Integration tests for plugin template endpoint.

Tests cover:
- Valid tenant_key returns templates
- Invalid tenant_key returns empty list (not error)
- Missing tenant_key returns 400
- Rate limiting triggers 429
- Only active templates returned by default
- include_inactive flag works correctly
- Multi-tenant isolation verified
- Full instructions field populated correctly
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from api.app import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
async def sample_templates(db_session: AsyncSession, test_tenant_key: str):
    """Create sample templates for testing"""
    templates = [
        AgentTemplate(
            tenant_key=test_tenant_key,
            name="Documentation Manager",
            role="documentation-manager",
            category="role",
            description="Manages documentation",
            template_content="You are a documentation manager...",
            system_instructions="# System Instructions\n\nUse MCP tools for coordination.",
            user_instructions="# User Instructions\n\nMaintain docs in /docs folder.",
            version="1.0.0",
            is_active=True,
            cli_tool="claude",
            model="sonnet",
            background_color="#4CAF50",
        ),
        AgentTemplate(
            tenant_key=test_tenant_key,
            name="Backend Developer",
            role="backend-developer",
            category="role",
            description="Develops backend APIs",
            template_content="You are a backend developer...",
            version="1.0.0",
            is_active=True,
            cli_tool="claude",
        ),
        AgentTemplate(
            tenant_key=test_tenant_key,
            name="Archived Agent",
            role="archived-agent",
            category="role",
            description="Inactive template",
            template_content="Archived...",
            version="1.0.0",
            is_active=False,  # Inactive
        ),
    ]

    db_session.add_all(templates)
    await db_session.commit()

    return templates


@pytest.mark.asyncio
async def test_valid_tenant_returns_templates(client, sample_templates, test_tenant_key):
    """Valid tenant_key should return all active templates"""
    response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={test_tenant_key}")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "templates" in data
    assert "tenant_key" in data
    assert "count" in data
    assert "cache_ttl" in data

    # Should return 2 active templates (not the archived one)
    assert data["count"] == 2
    assert len(data["templates"]) == 2

    # Verify template fields
    doc_manager = next(t for t in data["templates"] if t["role"] == "documentation-manager")
    assert doc_manager["name"] == "Documentation Manager"
    assert doc_manager["full_instructions"]  # Should have content
    assert "MCP tools" in doc_manager["full_instructions"]  # System instructions included
    assert "/docs folder" in doc_manager["full_instructions"]  # User instructions included
    assert doc_manager["capabilities"]  # Should have capabilities list
    assert doc_manager["version"] == "1.0.0"
    assert doc_manager["background_color"] == "#4CAF50"


@pytest.mark.asyncio
async def test_invalid_tenant_returns_empty_list(client):
    """Unknown tenant_key should return empty list (not 404)"""
    fake_tenant_key = "tk_00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={fake_tenant_key}")

    # Should return 200 OK with empty list (prevents tenant enumeration)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["templates"] == []
    assert data["tenant_key"] == fake_tenant_key


@pytest.mark.asyncio
async def test_missing_tenant_key_returns_400(client):
    """Missing tenant_key should return 400 Bad Request"""
    response = client.get("/api/v1/agent-templates/plugin")

    assert response.status_code == 422  # FastAPI validation error
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_invalid_tenant_key_format_returns_400(client):
    """Invalid tenant_key format should return 400"""
    invalid_keys = [
        "not-a-tenant-key",
        "tk_invalid",
        "tk_",
        "12345678-1234-1234-1234-123456789012",  # Missing tk_ prefix
    ]

    for invalid_key in invalid_keys:
        response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={invalid_key}")
        assert response.status_code == 422, f"Failed for key: {invalid_key}"


@pytest.mark.asyncio
async def test_rate_limiting_triggers_429(client, test_tenant_key):
    """Exceeding rate limit should return 429"""
    # Send 101 requests (limit is 100)
    for i in range(101):
        response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={test_tenant_key}")

        if i < 100:
            assert response.status_code == 200, f"Request {i} should succeed"
        else:
            # 101st request should be rate limited
            assert response.status_code == 429, f"Request {i} should be rate limited"
            data = response.json()
            assert "rate limit" in data["detail"].lower()


@pytest.mark.asyncio
async def test_include_inactive_flag(client, sample_templates, test_tenant_key):
    """include_inactive=true should return inactive templates"""
    # Without flag: should return 2 active templates
    response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={test_tenant_key}")
    assert response.status_code == 200
    assert response.json()["count"] == 2

    # With flag: should return all 3 templates (including inactive)
    response = client.get(
        f"/api/v1/agent-templates/plugin?tenant_key={test_tenant_key}&include_inactive=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3

    # Verify archived template included
    archived = next((t for t in data["templates"] if t["role"] == "archived-agent"), None)
    assert archived is not None
    assert archived["name"] == "Archived Agent"


@pytest.mark.asyncio
async def test_multi_tenant_isolation(client, db_session):
    """Templates should be isolated by tenant_key"""
    tenant_a_key = "tk_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    tenant_b_key = "tk_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    # Create templates for two different tenants
    template_a = AgentTemplate(
        tenant_key=tenant_a_key,
        name="Tenant A Agent",
        role="agent-a",
        category="role",
        template_content="Agent A instructions",
        version="1.0.0",
        is_active=True,
    )
    template_b = AgentTemplate(
        tenant_key=tenant_b_key,
        name="Tenant B Agent",
        role="agent-b",
        category="role",
        template_content="Agent B instructions",
        version="1.0.0",
        is_active=True,
    )

    db_session.add_all([template_a, template_b])
    await db_session.commit()

    # Query Tenant A
    response_a = client.get(f"/api/v1/agent-templates/plugin?tenant_key={tenant_a_key}")
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert data_a["count"] == 1
    assert data_a["templates"][0]["name"] == "Tenant A Agent"

    # Query Tenant B
    response_b = client.get(f"/api/v1/agent-templates/plugin?tenant_key={tenant_b_key}")
    assert response_b.status_code == 200
    data_b = response_b.json()
    assert data_b["count"] == 1
    assert data_b["templates"][0]["name"] == "Tenant B Agent"


@pytest.mark.asyncio
async def test_full_instructions_field_populated(client, sample_templates, test_tenant_key):
    """full_instructions should combine system + user instructions"""
    response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={test_tenant_key}")

    assert response.status_code == 200
    data = response.json()

    doc_manager = next(t for t in data["templates"] if t["role"] == "documentation-manager")
    full_instructions = doc_manager["full_instructions"]

    # Should contain both system and user instructions
    assert "System Instructions" in full_instructions
    assert "MCP tools" in full_instructions
    assert "User Instructions" in full_instructions
    assert "/docs folder" in full_instructions

    # Should not be empty
    assert len(full_instructions) > 100


@pytest.mark.asyncio
async def test_capabilities_field_present(client, sample_templates, test_tenant_key):
    """capabilities field should be present and populated"""
    response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={test_tenant_key}")

    assert response.status_code == 200
    data = response.json()

    for template in data["templates"]:
        assert "capabilities" in template
        assert isinstance(template["capabilities"], list)
        # Should have at least default capabilities
        assert len(template["capabilities"]) > 0


@pytest.mark.asyncio
async def test_system_managed_roles_excluded(client, db_session, test_tenant_key):
    """System-managed roles (orchestrator, staging) should be excluded"""
    # Create orchestrator template
    orchestrator = AgentTemplate(
        tenant_key=test_tenant_key,
        name="Orchestrator",
        role="orchestrator",  # System-managed role
        category="role",
        template_content="Orchestrator instructions",
        version="1.0.0",
        is_active=True,
    )

    db_session.add(orchestrator)
    await db_session.commit()

    # Query templates
    response = client.get(f"/api/v1/agent-templates/plugin?tenant_key={test_tenant_key}")

    assert response.status_code == 200
    data = response.json()

    # Orchestrator should NOT be included
    roles = [t["role"] for t in data["templates"]]
    assert "orchestrator" not in roles
```

---

## Files Summary

### New Files
- **None** (adding to existing file)

### Modified Files
1. **`F:\GiljoAI_MCP\api\endpoints\agent_templates.py`**
   - Add `PluginTemplate` Pydantic model
   - Add `PluginTemplateResponse` Pydantic model
   - Add `check_rate_limit()` function (inline rate limiter)
   - Add `build_full_instructions()` function
   - Add `generate_default_capabilities()` function
   - Add `get_templates_for_plugin()` endpoint function

### Test Files
2. **`F:\GiljoAI_MCP\tests\api\test_agent_templates_plugin.py`** (create new)
   - 10 integration test functions
   - Full coverage of endpoint behavior
   - Multi-tenant isolation verification
   - Rate limiting validation

---

## Success Criteria Checklist

- [ ] Endpoint responds to `GET /api/v1/agent-templates/plugin`
- [ ] Returns templates filtered by `tenant_key`
- [ ] Includes `full_instructions` field (system + user instructions combined)
- [ ] Includes `capabilities` array (from meta_data or generated)
- [ ] Rate limiting prevents abuse (100 req/min per tenant)
- [ ] Returns empty list for unknown `tenant_key` (not 404)
- [ ] Returns 422 for missing or invalid `tenant_key` format
- [ ] Returns 429 when rate limit exceeded
- [ ] `include_inactive=true` returns inactive templates
- [ ] Default behavior excludes inactive templates
- [ ] Multi-tenant isolation verified (no cross-tenant leakage)
- [ ] System-managed roles (orchestrator, staging) excluded
- [ ] All 10 integration tests pass
- [ ] Response includes `cache_ttl` hint (300 seconds)

---

## Dependencies

### Parent Handover
- **Handover 0334** (IN PROGRESS): Claude Code Plugin Integration (master handover)

### Sister Handovers (Sequential)
- **Handover 0334b** (NEXT): Claude Code plugin implementation (TypeScript)
- **Handover 0334c** (AFTER 0334b): Plugin installation guide
- **Handover 0334d** (FINAL): Integration testing (plugin ↔ API)

### Database Dependencies
- `AgentTemplate` model exists with all required fields
- `SYSTEM_MANAGED_ROLES` constant defined (from `src.giljo_mcp.system_roles`)
- Database session factory available via `get_db_session()` dependency

### External Dependencies
- FastAPI framework for endpoint routing
- Pydantic for request/response validation
- SQLAlchemy for database queries
- PostgreSQL 18 for data storage

---

## Security Considerations

### 1. Tenant Enumeration Prevention
**Risk**: Attackers could enumerate valid tenant_keys by testing patterns.

**Mitigation**:
- Return empty list (200 OK) for unknown tenant_keys, not 404
- Rate limit prevents brute-force enumeration
- No error messages that reveal tenant existence

### 2. Rate Limiting
**Current**: In-memory rate limiting (sliding window, 100 req/min)

**Production Upgrade Path** (v4.0):
```python
# TODO: Migrate to Redis for distributed rate limiting
async def check_rate_limit_redis(tenant_key: str) -> bool:
    key = f"rate_limit:plugin:{tenant_key}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, 60)
    return current <= 100
```

### 3. Data Exposure
**What's Exposed**: Full agent instructions (intentional for plugin use)

**What's Protected**:
- User authentication tokens (no JWT required/exposed)
- Cross-tenant data (strict tenant_key filtering)
- System-managed roles (orchestrator, staging excluded)
- Inactive templates (excluded by default)

### 4. Query Parameter Validation
**Regex Pattern**: `^tk_[a-f0-9-]{36}$`

**Validates**:
- Prefix: `tk_` (tenant key identifier)
- Format: 36-character UUID (lowercase hex)
- Prevents: SQL injection, XSS, path traversal

---

## Performance Considerations

### Database Query Optimization

**Current Query**:
```python
select(AgentTemplate)
    .where(AgentTemplate.tenant_key == tenant_key)
    .where(AgentTemplate.role.notin_(list(SYSTEM_MANAGED_ROLES)))
    .where(AgentTemplate.is_active == True)
    .order_by(AgentTemplate.category, AgentTemplate.role)
```

**Index Coverage** (from models/templates.py):
- `idx_template_tenant` - Covers `tenant_key` filter
- `idx_template_active` - Covers `is_active` filter
- `idx_template_role` - Covers `role` sort

**Expected Performance**: <50ms for tenants with <100 templates

### Caching Strategy

**Client-Side Caching**:
- Response includes `cache_ttl: 300` (5 minutes)
- Plugin should cache responses to reduce API calls
- Cache key: `{tenant_key}:{include_inactive}`

**Server-Side Caching** (Future Enhancement):
```python
# TODO (v4.0): Add server-side cache layer
@lru_cache(maxsize=1000, ttl=300)
async def get_cached_templates(tenant_key: str, include_inactive: bool):
    # Cache at service layer
    pass
```

---

## Testing Strategy

### TDD Workflow (RED-GREEN-REFACTOR)

**RED Phase**: Write 10 failing tests first
1. `test_valid_tenant_returns_templates` - Verify basic functionality
2. `test_invalid_tenant_returns_empty_list` - Test enumeration prevention
3. `test_missing_tenant_key_returns_400` - Validate required params
4. `test_invalid_tenant_key_format_returns_400` - Test regex validation
5. `test_rate_limiting_triggers_429` - Verify rate limiting
6. `test_include_inactive_flag` - Test optional flag
7. `test_multi_tenant_isolation` - Critical security test
8. `test_full_instructions_field_populated` - Data completeness
9. `test_capabilities_field_present` - Required field validation
10. `test_system_managed_roles_excluded` - Security filter

**GREEN Phase**: Implement minimal code to pass tests
- Add Pydantic models
- Implement endpoint function
- Add helper functions (build_full_instructions, etc.)
- Implement rate limiting

**REFACTOR Phase**: Optimize and clean
- Add logging statements
- Optimize database queries
- Add TODO comments for v4.0 improvements
- Document edge cases

### Test Coverage Target
- **Unit Tests**: 90%+ (Pydantic models, helper functions)
- **Integration Tests**: 100% (all endpoint paths covered)
- **Edge Cases**: Invalid inputs, rate limiting, multi-tenant

---

## Rollback Plan

### If Deployment Causes Issues

**Step 1: Remove Endpoint**
```bash
# Revert the commit
git revert <commit_hash>

# Rebuild API
cd api/
python -m pip install -e .

# Restart server
python startup.py
```

**Step 2: Verify Existing Endpoints Still Work**
```bash
# Test existing template endpoint
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:7272/api/v1/agents/templates
```

**Step 3: Notify Dependent Teams**
- Update handover 0334b (plugin team) about rollback
- Document reason for rollback in handover notes
- Create new sub-handover for fixes if needed

### Rollback Safety
- New endpoint is isolated (no changes to existing endpoints)
- No database migrations required
- No breaking changes to existing functionality
- Plugin can gracefully handle 404 (endpoint not found)

---

## Code Examples

### Complete Endpoint Implementation

```python
# Add to: api/endpoints/agent_templates.py

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES


# In-memory rate limit store (use Redis in production)
_rate_limit_store: Dict[str, list[datetime]] = defaultdict(list)


def check_rate_limit(tenant_key: str, limit: int = 100, window_seconds: int = 60) -> bool:
    """Check if request is within rate limit (sliding window)"""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)

    # Clean old requests
    _rate_limit_store[tenant_key] = [
        req_time for req_time in _rate_limit_store[tenant_key]
        if req_time > window_start
    ]

    # Check limit
    if len(_rate_limit_store[tenant_key]) >= limit:
        return False

    # Record request
    _rate_limit_store[tenant_key].append(now)
    return True


class PluginTemplate(BaseModel):
    """Agent template response for Claude Code plugin"""
    id: str
    name: str
    role: str
    category: str
    description: Optional[str] = None
    full_instructions: str
    capabilities: list[str] = Field(default_factory=list)
    version: str
    background_color: Optional[str] = None
    cli_tool: str = "claude"
    model: Optional[str] = None

    @validator("full_instructions")
    def validate_instructions_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("full_instructions cannot be empty")
        return v


class PluginTemplateResponse(BaseModel):
    """Response model for plugin template endpoint"""
    templates: list[PluginTemplate]
    tenant_key: str
    count: int
    cache_ttl: int = 300


def build_full_instructions(template: AgentTemplate) -> str:
    """Build complete instructions from system + user fields"""
    if template.system_instructions or template.user_instructions:
        system_part = template.system_instructions or ""
        user_part = template.user_instructions or ""
        return f"{system_part}\n\n{user_part}".strip()
    return template.template_content or ""


def generate_default_capabilities(role: str) -> list[str]:
    """Generate default capabilities from role name"""
    tokens = role.lower().replace("-", "_").split("_")
    capabilities = tokens.copy()
    capabilities.extend(["collaboration", "mcp_integration"])
    return capabilities


@router.get("/plugin", response_model=PluginTemplateResponse)
async def get_templates_for_plugin(
    tenant_key: str = Query(..., regex=r"^tk_[a-f0-9-]{36}$"),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Fetch agent templates for Claude Code plugin (no JWT auth required).

    Rate limited to 100 requests/minute per tenant_key.
    Returns empty list for unknown tenants (prevents enumeration).
    """
    from api.app import state

    # Rate limiting
    if not check_rate_limit(tenant_key):
        logger.warning(f"Rate limit exceeded for tenant: {tenant_key}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            stmt = (
                select(AgentTemplate)
                .where(AgentTemplate.tenant_key == tenant_key)
                .where(AgentTemplate.role.notin_(list(SYSTEM_MANAGED_ROLES)))
                .order_by(AgentTemplate.category, AgentTemplate.role)
            )

            if not include_inactive:
                stmt = stmt.where(AgentTemplate.is_active == True)

            result = await session.execute(stmt)
            templates = result.scalars().all()

        # Build response
        plugin_templates = []
        for template in templates:
            full_instructions = build_full_instructions(template)
            capabilities = template.meta_data.get("capabilities", []) if template.meta_data else []
            if not capabilities:
                capabilities = generate_default_capabilities(template.role)

            plugin_templates.append(
                PluginTemplate(
                    id=template.id,
                    name=template.name,
                    role=template.role or "general",
                    category=template.category,
                    description=template.description,
                    full_instructions=full_instructions,
                    capabilities=capabilities,
                    version=template.version,
                    background_color=template.background_color,
                    cli_tool=template.cli_tool,
                    model=template.model,
                )
            )

        logger.info(f"Plugin: Returned {len(plugin_templates)} templates for {tenant_key}")

        return PluginTemplateResponse(
            templates=plugin_templates,
            tenant_key=tenant_key,
            count=len(plugin_templates),
            cache_ttl=300,
        )

    except Exception as e:
        logger.error(f"Plugin endpoint error for {tenant_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Example Usage (curl)

```bash
# Fetch templates for a tenant
curl -X GET "http://localhost:7272/api/v1/agent-templates/plugin?tenant_key=tk_550e8400-e29b-41d4-a716-446655440000"

# Include inactive templates
curl -X GET "http://localhost:7272/api/v1/agent-templates/plugin?tenant_key=tk_550e8400-e29b-41d4-a716-446655440000&include_inactive=true"

# Invalid tenant_key (should return empty list)
curl -X GET "http://localhost:7272/api/v1/agent-templates/plugin?tenant_key=tk_00000000-0000-0000-0000-000000000000"
```

---

## Additional Notes

### Relationship to Other Handovers

**Handover 0333** (COMPLETE):
- Simplified staging prompt from 150+ lines to ~35 lines
- Introduced `get_available_agents()` MCP tool pattern
- Established dynamic agent discovery approach
- **Key Insight**: Orchestrators can call MCP tools to fetch agents instead of embedding lists

**Handover 0334** (PARENT):
- Master handover for Claude Code plugin integration
- This sub-handover (0334a) is the backend API component
- Enables plugin to fetch GiljoAI templates dynamically

**Handover 0334b** (NEXT):
- Claude Code plugin implementation (TypeScript/JavaScript)
- Will consume this API endpoint
- Requires this handover to be COMPLETE before starting

### Why Not Use Existing `/api/v1/agents/templates` Endpoint?

**Existing Endpoint Issues**:
1. **JWT Authentication Required**: Plugin can't pass JWT tokens (external tool)
2. **Metadata-Only Response**: Returns template list, not full instructions
3. **Download Pattern**: Requires separate call per template (inefficient)
4. **Dashboard-Focused**: Designed for web UI, not plugin consumption

**New Endpoint Benefits**:
1. **No Auth Required**: Uses tenant_key query param (safe with rate limiting)
2. **Full Instructions**: Returns complete agent instructions in single call
3. **Plugin-Optimized**: Response schema matches Claude Code's agent system
4. **Capabilities Array**: Helps Claude Code understand agent specializations

### Production Improvements (v4.0)

**Rate Limiting**:
- Migrate from in-memory to Redis (distributed systems)
- Add per-IP rate limiting (prevent DDoS from single source)
- Implement token bucket algorithm (more flexible than sliding window)

**Caching**:
- Add server-side cache layer (Redis or in-memory LRU)
- Cache invalidation on template updates
- Cache warming for frequently accessed tenants

**Monitoring**:
- Add metrics for endpoint usage (Prometheus/Grafana)
- Track rate limit violations (alert on patterns)
- Monitor cache hit rates

**Security**:
- Add API key authentication (optional tier for enterprise)
- Implement request signing (HMAC validation)
- Add CORS configuration for plugin origins

---

## Completion Criteria

### Definition of Done

This handover is considered COMPLETE when:

1. **Code Implemented**:
   - All Pydantic models added to `agent_templates.py`
   - Endpoint function implemented with full error handling
   - Helper functions (`build_full_instructions`, etc.) working correctly
   - Rate limiting functional (in-memory implementation)

2. **Tests Passing**:
   - All 10 integration tests pass (100% coverage of endpoint paths)
   - Multi-tenant isolation verified
   - Rate limiting tested (101 requests trigger 429)
   - Edge cases covered (invalid inputs, empty lists)

3. **Documentation Updated**:
   - API endpoint documented in code comments
   - Pydantic models have field descriptions
   - Rate limiting algorithm documented
   - TODO comments added for v4.0 improvements

4. **Manual Verification**:
   - Endpoint accessible via curl/Postman
   - Response matches specification exactly
   - Rate limiting triggers at 100 requests
   - Empty list returned for unknown tenant_key (not 404)

5. **Handover 0334b Ready**:
   - Plugin team can start implementation (API contract finalized)
   - Example responses documented
   - Error codes documented for plugin error handling

### Acceptance Test

Run this sequence to verify completion:

```bash
# 1. Start server
python startup.py

# 2. Get tenant_key from database
TENANT_KEY=$(PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -t -c "SELECT tenant_key FROM users LIMIT 1;" | xargs)

# 3. Test endpoint
curl -X GET "http://localhost:7272/api/v1/agent-templates/plugin?tenant_key=$TENANT_KEY"

# 4. Verify response structure
# Should return JSON with: templates, tenant_key, count, cache_ttl

# 5. Test rate limiting (run 101 times)
for i in {1..101}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    "http://localhost:7272/api/v1/agent-templates/plugin?tenant_key=$TENANT_KEY"
done
# First 100 should return 200, 101st should return 429

# 6. Run integration tests
pytest tests/api/test_agent_templates_plugin.py -v
# All 10 tests should pass
```

If all 6 steps succeed, this handover is COMPLETE and ready for handoff to 0334b.

---

**END OF HANDOVER 0334a**

**Next Steps**: Await approval to begin implementation using TDD workflow (RED-GREEN-REFACTOR).
