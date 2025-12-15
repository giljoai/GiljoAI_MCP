# Handover 0350a: Create Unified `fetch_context()` MCP Tool

**Series**: 0350 (Context Management On-Demand Architecture)
**Date**: 2025-12-15
**Status**: Not Started
**Priority**: High
**Complexity**: Medium

---

## Architectural Decision (2025-12-15)

**Use ONE unified `fetch_context()` tool instead of 9 individual `get_*` tools.**

### Rationale

| Factor | 9 Individual Tools | 1 Unified Tool | Winner |
|--------|-------------------|----------------|--------|
| **MCP Context Budget** | ~900 tokens (9 schemas) | ~180 tokens (1 schema) | Unified |
| **AI Tool Selection** | Decision fatigue (which of 9?) | Clear single entry point | Unified |
| **SaaS Metering** | 9 endpoints to track | 1 endpoint to track | Unified |
| **API Versioning** | 9 APIs to version | 1 API to version | Unified |
| **Power User Flexibility** | Full control | Categories param = same control | Unified |

### Architecture

```
PUBLIC (exposed via MCP HTTP, loaded into agent context):
  fetch_context(categories, depth_config, ...)  <- ~180 tokens

INTERNAL (not exposed, zero context cost):
  get_product_context()      |
  get_vision_document()      |
  get_tech_stack()           |  Called internally by
  get_architecture()         |  fetch_context()
  get_testing()              |
  get_360_memory()           |
  get_git_history()          |
  get_agent_templates()      |
  get_project()              |
```

### Token Budget Savings
- **Before**: 9 tool schemas x ~100 tokens = ~900 tokens consumed at agent startup
- **After**: 1 tool schema x ~180 tokens = ~180 tokens consumed at agent startup
- **Savings**: ~720 tokens available for actual work

---

## Overview

Create a single `fetch_context()` MCP tool that dispatches to the 9 internal context tools based on the `categories` parameter. This tool will be the ONLY context-fetching tool exposed via MCP HTTP.

**Impact**:
- 720 token savings in MCP tool schema overhead
- Simpler AI tool selection (1 tool vs 9)
- Single entry point for SaaS metering and audit logging
- Server-side application of user's priority/depth configuration

---

## Tool Signature

### `fetch_context()`

```python
async def fetch_context(
    product_id: str,
    tenant_key: str,
    project_id: Optional[str] = None,
    categories: List[str] = ["all"],
    depth_config: Optional[Dict[str, str]] = None,
    apply_user_config: bool = True,
    format: str = "structured"
) -> Dict[str, Any]:
    """
    Unified context fetcher for orchestrators and agents.

    Fetches context from multiple categories in a single call.
    Server applies user's saved priority/depth configuration when apply_user_config=True.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        project_id: Optional project UUID (required for 'project' category)
        categories: List of categories to fetch, or ["all"] for all categories
                   Valid: product_core, vision_documents, tech_stack, architecture,
                          testing, memory_360, git_history, agent_templates, project
        depth_config: Override depth settings per category
                     Example: {"vision_documents": "light", "agent_templates": "minimal"}
        apply_user_config: Apply user's saved priority/depth settings (default: True)
        format: Response format - "structured" (nested by category) or "flat" (merged)

    Returns:
        Dict with context data organized by category, plus metadata
    """
```

### MCP Tool Schema (JSON-RPC)

```json
{
    "name": "fetch_context",
    "description": "Unified context fetcher. Retrieves product/project context by category with depth control. Categories: product_core (~100 tokens), vision_documents (0-24K), tech_stack (200-400), architecture (300-1.5K), testing (0-400), memory_360 (500-5K), git_history (500-5K), agent_templates (400-2.4K), project (~300). Use apply_user_config=true to respect user's saved settings.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "Product UUID"
            },
            "tenant_key": {
                "type": "string",
                "description": "Tenant isolation key"
            },
            "project_id": {
                "type": "string",
                "description": "Project UUID (required for 'project' category)"
            },
            "categories": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["all", "product_core", "vision_documents", "tech_stack",
                             "architecture", "testing", "memory_360", "git_history",
                             "agent_templates", "project"]
                },
                "description": "Categories to fetch. Use ['all'] for all categories.",
                "default": ["all"]
            },
            "depth_config": {
                "type": "object",
                "description": "Override depth per category. Example: {\"vision_documents\": \"light\"}",
                "additionalProperties": {"type": "string"}
            },
            "apply_user_config": {
                "type": "boolean",
                "description": "Apply user's saved priority/depth settings (default: true)",
                "default": true
            },
            "format": {
                "type": "string",
                "enum": ["structured", "flat"],
                "description": "Response format (default: structured)",
                "default": "structured"
            }
        },
        "required": ["product_id", "tenant_key"]
    }
}
```

---

## Technical Implementation

### Phase 1: Create `fetch_context.py` Module

**File**: `src/giljo_mcp/tools/context_tools/fetch_context.py` (NEW)

```python
"""
Unified context fetcher for GiljoAI MCP.

Handover 0350a: Single entry point for all context fetching.
Dispatches to internal get_* tools based on categories parameter.
"""

from typing import Any, Dict, List, Optional
import logging

from giljo_mcp.database import DatabaseManager

# Internal tools (NOT exposed via MCP)
from giljo_mcp.tools.context_tools.get_product_context import get_product_context
from giljo_mcp.tools.context_tools.get_vision_document import get_vision_document
from giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack
from giljo_mcp.tools.context_tools.get_architecture import get_architecture
from giljo_mcp.tools.context_tools.get_testing import get_testing
from giljo_mcp.tools.context_tools.get_360_memory import get_360_memory
from giljo_mcp.tools.context_tools.get_git_history import get_git_history
from giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates
from giljo_mcp.tools.context_tools.get_project import get_project

logger = logging.getLogger(__name__)

# Category to internal tool mapping
CATEGORY_TOOLS = {
    "product_core": get_product_context,
    "vision_documents": get_vision_document,
    "tech_stack": get_tech_stack,
    "architecture": get_architecture,
    "testing": get_testing,
    "memory_360": get_360_memory,
    "git_history": get_git_history,
    "agent_templates": get_agent_templates,
    "project": get_project,
}

# Default depth settings per category
DEFAULT_DEPTHS = {
    "product_core": None,  # No depth param
    "vision_documents": "medium",
    "tech_stack": "all",
    "architecture": "overview",
    "testing": "full",
    "memory_360": 5,  # last_n_projects
    "git_history": 25,  # commits
    "agent_templates": "standard",
    "project": None,  # No depth param
}

ALL_CATEGORIES = list(CATEGORY_TOOLS.keys())


async def fetch_context(
    product_id: str,
    tenant_key: str,
    project_id: Optional[str] = None,
    categories: List[str] = None,
    depth_config: Optional[Dict[str, Any]] = None,
    apply_user_config: bool = True,
    format: str = "structured",
    db_manager: Optional[DatabaseManager] = None,
) -> Dict[str, Any]:
    """
    Unified context fetcher - dispatches to internal tools.

    See module docstring for full documentation.
    """
    if categories is None:
        categories = ["all"]

    # Expand "all" to full category list
    if "all" in categories:
        categories = ALL_CATEGORIES.copy()

    # Validate categories
    invalid = [c for c in categories if c not in CATEGORY_TOOLS]
    if invalid:
        return {
            "error": f"Invalid categories: {invalid}",
            "valid_categories": ALL_CATEGORIES,
            "metadata": {"estimated_tokens": 0}
        }

    # Load user config if requested
    effective_depths = DEFAULT_DEPTHS.copy()
    if apply_user_config and db_manager:
        user_config = await _load_user_depth_config(product_id, tenant_key, db_manager)
        if user_config:
            effective_depths.update(user_config)

    # Apply explicit depth overrides
    if depth_config:
        effective_depths.update(depth_config)

    # Fetch each category
    results = {}
    total_tokens = 0
    errors = []

    for category in categories:
        try:
            result = await _fetch_category(
                category=category,
                product_id=product_id,
                tenant_key=tenant_key,
                project_id=project_id,
                depth=effective_depths.get(category),
                db_manager=db_manager
            )
            results[category] = result.get("data", {})
            total_tokens += result.get("metadata", {}).get("estimated_tokens", 0)
        except Exception as e:
            logger.error(f"Error fetching {category}: {e}")
            errors.append({"category": category, "error": str(e)})

    # Build response
    response = {
        "source": "fetch_context",
        "categories_requested": categories,
        "categories_returned": list(results.keys()),
        "data": results if format == "structured" else _flatten_results(results),
        "metadata": {
            "estimated_tokens": total_tokens,
            "format": format,
            "apply_user_config": apply_user_config,
            "depth_config_applied": effective_depths,
        }
    }

    if errors:
        response["errors"] = errors

    return response


async def _fetch_category(
    category: str,
    product_id: str,
    tenant_key: str,
    project_id: Optional[str],
    depth: Any,
    db_manager: DatabaseManager,
) -> Dict[str, Any]:
    """Dispatch to internal tool based on category."""

    tool_func = CATEGORY_TOOLS[category]

    # Build kwargs based on category
    kwargs = {"db_manager": db_manager}

    if category == "project":
        if not project_id:
            return {"data": {}, "metadata": {"error": "project_id required", "estimated_tokens": 0}}
        kwargs["project_id"] = project_id
        kwargs["tenant_key"] = tenant_key
    elif category == "agent_templates":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["detail"] = depth
    elif category == "vision_documents":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["chunking"] = depth
    elif category == "memory_360":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["last_n_projects"] = int(depth)
    elif category == "git_history":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["commits"] = int(depth)
    elif category in ("tech_stack", "architecture", "testing"):
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["depth" if category != "tech_stack" else "sections"] = depth
    else:
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key

    return await tool_func(**kwargs)


async def _load_user_depth_config(
    product_id: str,
    tenant_key: str,
    db_manager: DatabaseManager
) -> Optional[Dict[str, Any]]:
    """Load user's saved depth configuration from database."""
    # TODO: Implement user config loading from User.field_priority JSONB
    # For now, return None to use defaults
    return None


def _flatten_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested category results into single dict."""
    flat = {}
    for category, data in results.items():
        if isinstance(data, dict):
            for key, value in data.items():
                flat[f"{category}_{key}"] = value
        else:
            flat[category] = data
    return flat
```

### Phase 2: Add to `mcp_http.py`

**File**: `api/endpoints/mcp_http.py`

#### Step 2.1: Add Tool Definition to `handle_tools_list()`

Insert in the tools array (around line 527):

```python
        # Unified Context Tool (Handover 0350a)
        {
            "name": "fetch_context",
            "description": "Unified context fetcher. Retrieves product/project context by category with depth control. Categories: product_core (~100 tokens), vision_documents (0-24K), tech_stack (200-400), architecture (300-1.5K), testing (0-400), memory_360 (500-5K), git_history (500-5K), agent_templates (400-2.4K), project (~300). Use apply_user_config=true to respect user's saved settings. Single tool replaces 9 individual tools for 720 token savings in MCP schema overhead.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "project_id": {"type": "string", "description": "Project UUID (for 'project' category)"},
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["all", "product_core", "vision_documents", "tech_stack",
                                     "architecture", "testing", "memory_360", "git_history",
                                     "agent_templates", "project"]
                        },
                        "description": "Categories to fetch. ['all'] for everything.",
                        "default": ["all"]
                    },
                    "depth_config": {
                        "type": "object",
                        "description": "Override depth per category. Example: {\"vision_documents\": \"light\"}"
                    },
                    "apply_user_config": {
                        "type": "boolean",
                        "description": "Apply user's saved settings (default: true)",
                        "default": True
                    },
                    "format": {
                        "type": "string",
                        "enum": ["structured", "flat"],
                        "default": "structured"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
```

#### Step 2.2: Add Tool Route to `handle_tools_call()` Tool Map

Insert in tool_map (around line 608):

```python
        # Unified Context Tool (Handover 0350a)
        "fetch_context": state.tool_accessor.fetch_context,
```

### Phase 3: Add ToolAccessor Wrapper

**File**: `src/giljo_mcp/tools/tool_accessor.py`

Insert after existing context-related methods:

```python
    # Unified Context Tool (Handover 0350a)

    async def fetch_context(
        self,
        product_id: str,
        tenant_key: str,
        project_id: Optional[str] = None,
        categories: List[str] = None,
        depth_config: Optional[Dict[str, Any]] = None,
        apply_user_config: bool = True,
        format: str = "structured"
    ) -> Dict[str, Any]:
        """
        Unified context fetcher - single entry point for all context.

        Handover 0350a: Replaces 9 individual tools with 1 unified tool.
        Saves ~720 tokens in MCP schema overhead.

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            project_id: Project UUID (required for 'project' category)
            categories: Categories to fetch, or ["all"]
            depth_config: Override depth settings per category
            apply_user_config: Apply user's saved priority/depth (default: True)
            format: "structured" (nested) or "flat" (merged)

        Returns:
            Dict with context data organized by category
        """
        from giljo_mcp.tools.context_tools.fetch_context import fetch_context

        return await fetch_context(
            product_id=product_id,
            tenant_key=tenant_key,
            project_id=project_id,
            categories=categories or ["all"],
            depth_config=depth_config,
            apply_user_config=apply_user_config,
            format=format,
            db_manager=self.db_manager
        )
```

### Phase 4: Update `__init__.py`

**File**: `src/giljo_mcp/tools/context_tools/__init__.py`

Add export for fetch_context:

```python
from giljo_mcp.tools.context_tools.fetch_context import fetch_context

__all__ = [
    "fetch_context",  # PUBLIC - exposed via MCP HTTP
    # Internal tools (not exposed, used by fetch_context)
    "get_product_context",
    "get_vision_document",
    "get_tech_stack",
    "get_architecture",
    "get_testing",
    "get_360_memory",
    "get_git_history",
    "get_agent_templates",
    "get_project",
]
```

---

## Usage Examples

### Basic Usage (All Categories)

```python
# Fetch all context with user's saved settings
result = await fetch_context(
    product_id="uuid-123",
    tenant_key="tk_abc"
)
# Returns ~35K tokens (all categories at default depth)
```

### Specific Categories

```python
# Fetch only product core and tech stack
result = await fetch_context(
    product_id="uuid-123",
    tenant_key="tk_abc",
    categories=["product_core", "tech_stack"]
)
# Returns ~500 tokens
```

### With Depth Override

```python
# Fetch vision at light depth (saves tokens)
result = await fetch_context(
    product_id="uuid-123",
    tenant_key="tk_abc",
    categories=["vision_documents"],
    depth_config={"vision_documents": "light"}
)
# Returns ~10K tokens instead of ~17.5K
```

### Power User (Override User Config)

```python
# Ignore user's saved settings, use explicit depths
result = await fetch_context(
    product_id="uuid-123",
    tenant_key="tk_abc",
    categories=["vision_documents", "agent_templates"],
    depth_config={
        "vision_documents": "full",
        "agent_templates": "minimal"
    },
    apply_user_config=False
)
```

---

## Response Structure

### Structured Format (Default)

```json
{
    "source": "fetch_context",
    "categories_requested": ["product_core", "tech_stack"],
    "categories_returned": ["product_core", "tech_stack"],
    "data": {
        "product_core": {
            "product_name": "GiljoAI MCP",
            "description": "Multi-tenant orchestration server",
            "features": ["context management", "agent coordination"]
        },
        "tech_stack": {
            "languages": ["Python 3.11"],
            "frameworks": ["FastAPI", "Vue 3"],
            "database": "PostgreSQL 18"
        }
    },
    "metadata": {
        "estimated_tokens": 500,
        "format": "structured",
        "apply_user_config": true,
        "depth_config_applied": {
            "product_core": null,
            "tech_stack": "all"
        }
    }
}
```

### Flat Format

```json
{
    "source": "fetch_context",
    "data": {
        "product_core_product_name": "GiljoAI MCP",
        "product_core_description": "Multi-tenant orchestration server",
        "tech_stack_languages": ["Python 3.11"],
        "tech_stack_frameworks": ["FastAPI", "Vue 3"]
    },
    "metadata": {...}
}
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/tools/test_fetch_context.py` (NEW)

```python
"""Unit tests for fetch_context unified tool (Handover 0350a)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_fetch_context_all_categories():
    """Test fetching all categories"""
    from giljo_mcp.tools.context_tools.fetch_context import fetch_context

    with patch.multiple(
        'giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value={"data": {"name": "Test"}, "metadata": {"estimated_tokens": 100}}),
        get_tech_stack=AsyncMock(return_value={"data": {"languages": ["Python"]}, "metadata": {"estimated_tokens": 200}}),
        # ... mock other tools
    ):
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["product_core", "tech_stack"],
            db_manager=MagicMock()
        )

        assert result["source"] == "fetch_context"
        assert "product_core" in result["data"]
        assert "tech_stack" in result["data"]
        assert result["metadata"]["estimated_tokens"] == 300


@pytest.mark.asyncio
async def test_fetch_context_invalid_category():
    """Test error handling for invalid category"""
    from giljo_mcp.tools.context_tools.fetch_context import fetch_context

    result = await fetch_context(
        product_id="test-uuid",
        tenant_key="tenant-abc",
        categories=["invalid_category"],
        db_manager=MagicMock()
    )

    assert "error" in result
    assert "invalid_category" in result["error"]


@pytest.mark.asyncio
async def test_fetch_context_depth_override():
    """Test depth override works"""
    from giljo_mcp.tools.context_tools.fetch_context import fetch_context

    with patch(
        'giljo_mcp.tools.context_tools.fetch_context.get_vision_document',
        new_callable=AsyncMock
    ) as mock_vision:
        mock_vision.return_value = {"data": [], "metadata": {"estimated_tokens": 0}}

        await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["vision_documents"],
            depth_config={"vision_documents": "light"},
            db_manager=MagicMock()
        )

        # Verify light depth was passed
        call_kwargs = mock_vision.call_args.kwargs
        assert call_kwargs.get("chunking") == "light"
```

### Integration Tests

**File**: `tests/integration/test_fetch_context_mcp.py` (NEW)

```python
"""Integration tests for fetch_context MCP endpoint (Handover 0350a)"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_mcp_tools_list_includes_fetch_context(test_client: AsyncClient, api_key_header):
    """Verify fetch_context appears in tools/list"""

    # MCP tools/list
    response = await test_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1},
        headers=api_key_header
    )

    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    # Should have fetch_context
    assert "fetch_context" in tool_names

    # Should NOT have individual tools (they're internal)
    assert "get_product_context" not in tool_names
    assert "get_vision_document" not in tool_names


@pytest.mark.asyncio
async def test_mcp_call_fetch_context(test_client: AsyncClient, api_key_header, test_product):
    """Test calling fetch_context via MCP HTTP"""

    response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_context",
                "arguments": {
                    "product_id": str(test_product.id),
                    "tenant_key": test_product.tenant_key,
                    "categories": ["product_core"]
                }
            },
            "id": 2
        },
        headers=api_key_header
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["isError"] is False
```

---

## Token Budget Reference

| Category | Depth Options | Token Range |
|----------|--------------|-------------|
| `product_core` | (none) | ~100 |
| `vision_documents` | none/light/medium/full | 0 / ~10K / ~17.5K / ~24K |
| `tech_stack` | required/all | ~200 / ~400 |
| `architecture` | overview/detailed | ~300 / ~1.5K |
| `testing` | none/basic/full | 0 / ~150 / ~400 |
| `memory_360` | 1/3/5/10 projects | ~500 / ~1.5K / ~2.5K / ~5K |
| `git_history` | 10/25/50/100 commits | ~500 / ~1.25K / ~2.5K / ~5K |
| `agent_templates` | minimal/standard/full | ~400 / ~800 / ~2.4K |
| `project` | (none) | ~300 |

**Total Range**: ~100 tokens (single category) to ~50K tokens (all at max depth)

---

## Files Modified

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/context_tools/fetch_context.py` | NEW - Unified dispatcher |
| `src/giljo_mcp/tools/context_tools/__init__.py` | Add fetch_context export |
| `api/endpoints/mcp_http.py` | Add tool definition + route |
| `src/giljo_mcp/tools/tool_accessor.py` | Add wrapper method |
| `tests/tools/test_fetch_context.py` | NEW - Unit tests |
| `tests/integration/test_fetch_context_mcp.py` | NEW - Integration tests |

---

## Success Criteria

- [ ] `fetch_context` appears in MCP tools/list response
- [ ] `fetch_context` callable via MCP HTTP tools/call
- [ ] Individual `get_*` tools NOT exposed via MCP (internal only)
- [ ] Categories param filters which tools are called
- [ ] depth_config overrides default depths
- [ ] apply_user_config loads user's saved settings
- [ ] Multi-tenant isolation enforced
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Token savings verified (~720 tokens saved vs 9 individual tools)

---

## Completion Checklist

- [ ] Phase 1: Create `fetch_context.py` module
- [ ] Phase 2: Add tool definition to `mcp_http.py`
- [ ] Phase 2: Add tool route to `mcp_http.py` tool_map
- [ ] Phase 3: Add ToolAccessor wrapper method
- [ ] Phase 4: Update `__init__.py` exports
- [ ] Testing: Create unit tests
- [ ] Testing: Create integration tests
- [ ] Verification: Test via MCP HTTP client
- [ ] Commit: "feat: Create unified fetch_context() MCP tool (Handover 0350a)"

---

## Related Handovers

- **0350b**: Refactor `get_orchestrator_instructions()` to reference `fetch_context()`
- **0350c**: Frontend 3-tier UI + field rename
- **0350d**: Documentation updates for unified tool

---

**Estimated Effort**: 3-4 hours (new module + plumbing + tests)
