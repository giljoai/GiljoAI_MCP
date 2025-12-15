# Handover 0350a: Expose Context Tools via MCP HTTP

**Series**: 0350 (Context Management On-Demand Architecture)
**Date**: 2025-01-15
**Status**: Not Started
**Priority**: High
**Complexity**: Medium

---

## Overview

GiljoAI MCP has 9 context tools implemented in `src/giljo_mcp/tools/context_tools/` (Handover 0316) but they are NOT exposed via the MCP HTTP endpoint. This handover wires them up for HTTP-based MCP clients (Claude Code, Codex CLI, etc.) to access the Context Management v2.0 system.

**Impact**: Enables external MCP clients to fetch context using priority/depth configuration without going through fat prompts.

---

## Background

### Context Management v2.0 (Handover 0316)

GiljoAI uses a 2-dimensional context model:
- **Priority Dimension**: CRITICAL (P1) → IMPORTANT (P2) → NICE_TO_HAVE (P3) → EXCLUDED (P4)
- **Depth Dimension**: Per-field granularity (e.g., vision: none/light/medium/full, 360 memory: 1/3/5/10 projects)

**9 Context Tools** (implemented but not exposed):
1. `get_product_context` - Product name, description, features (~100 tokens)
2. `get_vision_document` - Vision chunks with depth control (0-30K tokens)
3. `get_tech_stack` - Programming languages, frameworks, databases (200-400 tokens)
4. `get_architecture` - Architecture patterns, API style (300-1.5K tokens)
5. `get_testing` - Quality standards, strategy, frameworks (0-400 tokens)
6. `get_360_memory` - Project closeout summaries (500-5K tokens)
7. `get_git_history` - Aggregated git commits (500-5K tokens)
8. `get_agent_templates` - Agent template library (400-2.4K tokens)
9. `get_project` - Current project metadata (~300 tokens)

**Current State**:
- ✅ Tools implemented in `src/giljo_mcp/tools/context_tools/`
- ✅ Tools tested via direct imports
- ❌ NOT exposed in `mcp_http.py` tool_map
- ❌ NO ToolAccessor wrapper methods
- ❌ NOT listed in MCP `tools/list` endpoint

**Goal**: Make all 9 tools callable via MCP HTTP with multi-tenant isolation and proper error handling.

---

## Technical Implementation

### Phase 1: Add Tools to `mcp_http.py` Tool Map

**File**: `F:\GiljoAI_MCP\api\endpoints\mcp_http.py`

**Location**: Lines 138-528 (tool definitions), lines 564-609 (tool_map)

#### Step 1.1: Add Tool Definitions to `handle_tools_list()`

Insert after line 527 (before closing `]` of tools array):

```python
        # Context Management Tools (Handover 0350)
        {
            "name": "get_product_context",
            "description": "Fetch product core information (name, description, features, path, status). Returns ~100 tokens. Multi-tenant isolated by product_id + tenant_key.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include meta_data JSONB field (default: false)",
                        "default": False
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_vision_document",
            "description": "Fetch vision document chunks with depth control. Depth options: 'none' (0 tokens), 'light' (~10K tokens, 2 chunks), 'medium' (~17.5K tokens, 4 chunks), 'full' (~24K tokens, all chunks). Supports pagination via offset/limit. Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "chunking": {
                        "type": "string",
                        "enum": ["none", "light", "medium", "full"],
                        "description": "Depth level (default: medium)",
                        "default": "medium"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N chunks (for pagination, default: 0)",
                        "default": 0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max chunks to return (None = use chunking default)"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_tech_stack",
            "description": "Fetch tech stack information with depth control. Sections: 'required' (languages, frameworks, database, ~200 tokens) or 'all' (includes infrastructure, dev_tools, ~400 tokens). Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "sections": {
                        "type": "string",
                        "enum": ["required", "all"],
                        "description": "Detail level (default: all)",
                        "default": "all"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_architecture",
            "description": "Fetch architecture documentation with depth control. Depth: 'overview' (primary pattern + truncated notes, ~300 tokens) or 'detailed' (full architecture notes, ~1.5K tokens). Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "depth": {
                        "type": "string",
                        "enum": ["overview", "detailed"],
                        "description": "Detail level (default: overview)",
                        "default": "overview"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_testing",
            "description": "Fetch testing strategy and quality standards. Depth: 'none' (0 tokens), 'basic' (strategy + coverage_target, ~150 tokens), 'full' (all fields + frameworks, ~400 tokens). Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "depth": {
                        "type": "string",
                        "enum": ["none", "basic", "full"],
                        "description": "Detail level (default: full)",
                        "default": "full"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_360_memory",
            "description": "Fetch 360 memory (sequential project history) with depth control. Returns last N projects from product_memory.sequential_history. Depth: 1 project (~500 tokens), 3 projects (~1.5K tokens), 5 projects (~2.5K tokens), 10 projects (~5K tokens). Supports pagination via offset/limit. Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "last_n_projects": {
                        "type": "integer",
                        "description": "Number of recent projects (default: 3)",
                        "default": 3
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N projects (for pagination, default: 0)",
                        "default": 0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max projects to return (None = return all up to last_n_projects)"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_git_history",
            "description": "Fetch git commit history with depth control. Returns aggregated commits from product_memory.sequential_history. Depth: 10 commits (~500 tokens), 25 commits (~1.25K tokens), 50 commits (~2.5K tokens), 100 commits (~5K tokens). Returns empty if GitHub integration disabled. Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "commits": {
                        "type": "integer",
                        "description": "Number of recent commits (default: 25)",
                        "default": 25
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_agent_templates",
            "description": "Fetch agent templates with depth control. Templates are tenant-wide (not product-specific). Depth: 'minimal' (name + one-line purpose, ~400 tokens), 'standard' (name + purpose + key config, ~800 tokens), 'full' (complete template JSON, ~2.4K tokens). Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product UUID (for context, not filtering)"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "detail": {
                        "type": "string",
                        "enum": ["minimal", "standard", "full"],
                        "description": "Detail level (default: standard)",
                        "default": "standard"
                    }
                },
                "required": ["product_id", "tenant_key"]
            }
        },
        {
            "name": "get_project",
            "description": "Fetch current project context (metadata, mission, status). Returns ~300 tokens. Optionally includes orchestrator_summary if project completed. Multi-tenant isolated.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project UUID"},
                    "tenant_key": {"type": "string", "description": "Tenant isolation key"},
                    "include_summary": {
                        "type": "boolean",
                        "description": "Include orchestrator_summary if completed (default: false)",
                        "default": False
                    }
                },
                "required": ["project_id", "tenant_key"]
            }
        },
```

#### Step 1.2: Add Tool Routes to `handle_tools_call()` Tool Map

Insert after line 608 (before closing `}` of tool_map):

```python
        # Context Management Tools (Handover 0350)
        "get_product_context": state.tool_accessor.get_product_context,
        "get_vision_document": state.tool_accessor.get_vision_document,
        "get_tech_stack": state.tool_accessor.get_tech_stack,
        "get_architecture": state.tool_accessor.get_architecture,
        "get_testing": state.tool_accessor.get_testing,
        "get_360_memory": state.tool_accessor.get_360_memory,
        "get_git_history": state.tool_accessor.get_git_history,
        "get_agent_templates": state.tool_accessor.get_agent_templates,
        "get_project": state.tool_accessor.get_project,
```

---

### Phase 2: Add ToolAccessor Wrapper Methods

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\tools\tool_accessor.py`

**Location**: After line 319 (after `get_product_settings()` method)

**Pattern**: Each wrapper follows the async delegation pattern with db_manager injection.

#### Step 2.1: Add 9 Wrapper Methods

Insert after line 319:

```python
    # Context Management Tools (Handover 0350)

    async def get_product_context(
        self,
        product_id: str,
        tenant_key: str,
        include_metadata: bool = False
    ) -> dict[str, Any]:
        """
        Fetch product core information (Product Context tool).

        Handover 0350: Wrapper for get_product_context() MCP tool.
        Returns product name, description, features, path, status (~100 tokens).

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            include_metadata: Include meta_data JSONB field (default: False)

        Returns:
            Dict with product info and metadata
        """
        from giljo_mcp.tools.context_tools.get_product_context import get_product_context

        return await get_product_context(
            product_id=product_id,
            tenant_key=tenant_key,
            include_metadata=include_metadata,
            db_manager=self.db_manager
        )

    async def get_vision_document(
        self,
        product_id: str,
        tenant_key: str,
        chunking: str = "medium",
        offset: int = 0,
        limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Fetch vision document chunks with depth control (Vision Documents tool).

        Handover 0350: Wrapper for get_vision_document() MCP tool.
        Returns vision chunks based on depth: none/light/medium/full (0-30K tokens).

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            chunking: Depth level ("none", "light", "medium", "full")
            offset: Skip first N chunks (for pagination)
            limit: Max chunks to return (None = use chunking default)

        Returns:
            Dict with vision chunks and pagination metadata
        """
        from giljo_mcp.tools.context_tools.get_vision_document import get_vision_document

        return await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking=chunking,
            offset=offset,
            limit=limit,
            db_manager=self.db_manager
        )

    async def get_tech_stack(
        self,
        product_id: str,
        tenant_key: str,
        sections: str = "all"
    ) -> dict[str, Any]:
        """
        Fetch tech stack information with depth control (Tech Stack tool).

        Handover 0350: Wrapper for get_tech_stack() MCP tool.
        Returns tech stack fields: required (languages, frameworks, database) or all (200-400 tokens).

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            sections: Detail level ("required" or "all")

        Returns:
            Dict with tech stack info and metadata
        """
        from giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack

        return await get_tech_stack(
            product_id=product_id,
            tenant_key=tenant_key,
            sections=sections,
            offset=0,  # Reserved for future pagination
            limit=None,  # Reserved for future pagination
            db_manager=self.db_manager
        )

    async def get_architecture(
        self,
        product_id: str,
        tenant_key: str,
        depth: str = "overview"
    ) -> dict[str, Any]:
        """
        Fetch architecture documentation with depth control (Architecture tool).

        Handover 0350: Wrapper for get_architecture() MCP tool.
        Returns architecture patterns, API style, design patterns (300-1.5K tokens).

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            depth: Detail level ("overview" or "detailed")

        Returns:
            Dict with architecture info and metadata
        """
        from giljo_mcp.tools.context_tools.get_architecture import get_architecture

        return await get_architecture(
            product_id=product_id,
            tenant_key=tenant_key,
            depth=depth,
            offset=0,  # Reserved for future pagination
            limit=None,  # Reserved for future pagination
            db_manager=self.db_manager
        )

    async def get_testing(
        self,
        product_id: str,
        tenant_key: str,
        depth: str = "full"
    ) -> dict[str, Any]:
        """
        Fetch testing strategy and quality standards (Testing tool).

        Handover 0350: Wrapper for get_testing() MCP tool.
        Returns quality standards, testing strategy, frameworks (0-400 tokens).

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            depth: Detail level ("none", "basic", "full")

        Returns:
            Dict with testing config and metadata
        """
        from giljo_mcp.tools.context_tools.get_testing import get_testing

        return await get_testing(
            product_id=product_id,
            tenant_key=tenant_key,
            depth=depth,
            db_manager=self.db_manager
        )

    async def get_360_memory(
        self,
        product_id: str,
        tenant_key: str,
        last_n_projects: int = 3,
        offset: int = 0,
        limit: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Fetch 360 memory (sequential project history) with depth control (360 Memory tool).

        Handover 0350: Wrapper for get_360_memory() MCP tool.
        Returns last N projects from product_memory.sequential_history (500-5K tokens).

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            last_n_projects: Number of recent projects (1/3/5/10)
            offset: Skip first N projects (for pagination)
            limit: Max projects to return (None = use last_n_projects)

        Returns:
            Dict with sequential history and pagination metadata
        """
        from giljo_mcp.tools.context_tools.get_360_memory import get_360_memory

        return await get_360_memory(
            product_id=product_id,
            tenant_key=tenant_key,
            last_n_projects=last_n_projects,
            offset=offset,
            limit=limit,
            db_manager=self.db_manager
        )

    async def get_git_history(
        self,
        product_id: str,
        tenant_key: str,
        commits: int = 25
    ) -> dict[str, Any]:
        """
        Fetch git commit history with depth control (Git History tool).

        Handover 0350: Wrapper for get_git_history() MCP tool.
        Returns aggregated commits from product_memory.sequential_history (500-5K tokens).
        Returns empty if GitHub integration disabled.

        Args:
            product_id: Product UUID
            tenant_key: Tenant isolation key
            commits: Number of recent commits (10/25/50/100)

        Returns:
            Dict with git commits and metadata
        """
        from giljo_mcp.tools.context_tools.get_git_history import get_git_history

        return await get_git_history(
            product_id=product_id,
            tenant_key=tenant_key,
            commits=commits,
            offset=0,  # Reserved for future pagination
            limit=None,  # Reserved for future pagination
            db_manager=self.db_manager
        )

    async def get_agent_templates(
        self,
        product_id: str,
        tenant_key: str,
        detail: str = "standard"
    ) -> dict[str, Any]:
        """
        Fetch agent templates with depth control (Agent Templates tool).

        Handover 0350: Wrapper for get_agent_templates() MCP tool.
        Returns active agent templates (tenant-wide, not product-specific) (400-2.4K tokens).

        Args:
            product_id: Product UUID (for context, not filtering)
            tenant_key: Tenant isolation key
            detail: Detail level ("minimal", "standard", "full")

        Returns:
            Dict with agent templates and metadata
        """
        from giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates

        return await get_agent_templates(
            product_id=product_id,
            tenant_key=tenant_key,
            detail=detail,
            offset=0,  # Reserved for future pagination
            limit=None,  # Reserved for future pagination
            db_manager=self.db_manager
        )

    async def get_project(
        self,
        project_id: str,
        tenant_key: str,
        include_summary: bool = False
    ) -> dict[str, Any]:
        """
        Fetch current project context (Project Context tool).

        Handover 0350: Wrapper for get_project() MCP tool.
        Returns project metadata, mission, status (~300 tokens).

        Args:
            project_id: Project UUID
            tenant_key: Tenant isolation key
            include_summary: Include orchestrator_summary if completed (default: False)

        Returns:
            Dict with project info and metadata
        """
        from giljo_mcp.tools.context_tools.get_project import get_project

        return await get_project(
            project_id=project_id,
            tenant_key=tenant_key,
            include_summary=include_summary,
            db_manager=self.db_manager
        )
```

---

## Testing Strategy

### Unit Tests

**Location**: `F:\GiljoAI_MCP\tests\tools\test_context_tools_mcp_http.py` (NEW FILE)

```python
"""
Unit tests for Context Tools MCP HTTP integration (Handover 0350)

Tests verify that context tools are properly exposed via MCP HTTP endpoint
and ToolAccessor wrapper methods work correctly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_get_product_context_via_tool_accessor():
    """Test get_product_context() via ToolAccessor wrapper"""
    from giljo_mcp.tools.tool_accessor import ToolAccessor

    db_manager = MagicMock()
    tenant_manager = MagicMock()
    accessor = ToolAccessor(db_manager, tenant_manager)

    with patch('giljo_mcp.tools.context_tools.get_product_context.get_product_context') as mock_func:
        mock_func.return_value = {
            "source": "product_context",
            "data": {"product_name": "Test Product"},
            "metadata": {"estimated_tokens": 100}
        }

        result = await accessor.get_product_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            include_metadata=False
        )

        assert result["source"] == "product_context"
        assert "product_name" in result["data"]
        mock_func.assert_called_once_with(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            include_metadata=False,
            db_manager=db_manager
        )


@pytest.mark.asyncio
async def test_get_vision_document_via_tool_accessor():
    """Test get_vision_document() via ToolAccessor wrapper"""
    from giljo_mcp.tools.tool_accessor import ToolAccessor

    db_manager = MagicMock()
    tenant_manager = MagicMock()
    accessor = ToolAccessor(db_manager, tenant_manager)

    with patch('giljo_mcp.tools.context_tools.get_vision_document.get_vision_document') as mock_func:
        mock_func.return_value = {
            "source": "vision_documents",
            "depth": "light",
            "data": [{"content": "chunk 1", "chunk_order": 1}],
            "metadata": {"estimated_tokens": 2500}
        }

        result = await accessor.get_vision_document(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            chunking="light",
            offset=0,
            limit=2
        )

        assert result["source"] == "vision_documents"
        assert result["depth"] == "light"
        mock_func.assert_called_once()


# Add similar tests for remaining 7 tools...
```

### Integration Tests

**Location**: `F:\GiljoAI_MCP\tests\integration\test_context_tools_mcp_endpoint.py` (NEW FILE)

```python
"""
Integration tests for Context Tools MCP HTTP endpoint (Handover 0350)

Tests verify end-to-end flow: HTTP request → MCP endpoint → ToolAccessor → Context tool
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_mcp_tools_list_includes_context_tools(test_client: AsyncClient, api_key_header):
    """Verify all 9 context tools appear in tools/list"""

    # MCP initialize
    init_response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"client_info": {"name": "test-client"}},
            "id": 1
        },
        headers=api_key_header
    )
    assert init_response.status_code == 200

    # MCP tools/list
    list_response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        },
        headers=api_key_header
    )

    assert list_response.status_code == 200
    data = list_response.json()

    tool_names = [tool["name"] for tool in data["result"]["tools"]]

    # Verify all 9 context tools present
    assert "get_product_context" in tool_names
    assert "get_vision_document" in tool_names
    assert "get_tech_stack" in tool_names
    assert "get_architecture" in tool_names
    assert "get_testing" in tool_names
    assert "get_360_memory" in tool_names
    assert "get_git_history" in tool_names
    assert "get_agent_templates" in tool_names
    assert "get_project" in tool_names


@pytest.mark.asyncio
async def test_mcp_call_get_product_context(test_client: AsyncClient, api_key_header, test_product):
    """Test calling get_product_context via MCP HTTP"""

    response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_product_context",
                "arguments": {
                    "product_id": str(test_product.id),
                    "tenant_key": test_product.tenant_key,
                    "include_metadata": False
                }
            },
            "id": 3
        },
        headers=api_key_header
    )

    assert response.status_code == 200
    data = response.json()

    assert "result" in data
    assert data["result"]["isError"] is False

    # Parse content text (JSON string)
    import json
    result_data = json.loads(data["result"]["content"][0]["text"])

    assert result_data["source"] == "product_context"
    assert "data" in result_data
    assert "metadata" in result_data


# Add similar integration tests for remaining 8 tools...
```

---

## Error Handling

All context tools follow consistent error patterns:

### 1. **Product Not Found**
```json
{
    "source": "product_context",
    "data": {},
    "metadata": {
        "error": "product_not_found",
        "estimated_tokens": 0
    }
}
```

### 2. **Empty Data (No Vision Documents)**
```json
{
    "source": "vision_documents",
    "data": [],
    "metadata": {
        "total_chunks": 0,
        "estimated_tokens": 0
    }
}
```

### 3. **GitHub Integration Disabled**
```json
{
    "source": "git_history",
    "data": [],
    "metadata": {
        "git_integration_enabled": false,
        "reason": "git_integration_disabled"
    }
}
```

---

## Multi-Tenant Isolation

**CRITICAL**: All context tools enforce multi-tenant isolation by filtering queries with BOTH `product_id` AND `tenant_key` (or `project_id` + `tenant_key` for project context).

**Example Query Pattern** (from `get_product_context.py`):
```python
stmt = select(Product).where(
    Product.id == product_id,
    Product.tenant_key == tenant_key
)
```

**No Cross-Tenant Leakage**: If a client provides valid `product_id` but wrong `tenant_key`, the tool returns empty/not-found response (NOT an error that leaks existence).

---

## Token Budget Reference

| Tool                  | Depth               | Estimated Tokens |
|-----------------------|---------------------|------------------|
| `get_product_context` | (always full)       | ~100             |
| `get_vision_document` | none                | 0                |
|                       | light (2 chunks)    | ~10,000          |
|                       | medium (4 chunks)   | ~17,500          |
|                       | full (all chunks)   | ~24,000          |
| `get_tech_stack`      | required            | ~200             |
|                       | all                 | ~400             |
| `get_architecture`    | overview            | ~300             |
|                       | detailed            | ~1,500           |
| `get_testing`         | none                | 0                |
|                       | basic               | ~150             |
|                       | full                | ~400             |
| `get_360_memory`      | 1 project           | ~500             |
|                       | 3 projects          | ~1,500           |
|                       | 5 projects          | ~2,500           |
|                       | 10 projects         | ~5,000           |
| `get_git_history`     | 10 commits          | ~500             |
|                       | 25 commits          | ~1,250           |
|                       | 50 commits          | ~2,500           |
|                       | 100 commits         | ~5,000           |
| `get_agent_templates` | minimal             | ~400             |
|                       | standard            | ~800             |
|                       | full                | ~2,400           |
| `get_project`         | (always full)       | ~300             |

**Total Budget Range**: 100 tokens (minimal) → ~50,000 tokens (all tools at max depth)

---

## Files Modified

### 1. `api/endpoints/mcp_http.py`
- **Lines 138-527**: Add 9 tool definitions to `handle_tools_list()`
- **Lines 564-609**: Add 9 tool routes to `handle_tools_call()` tool_map

### 2. `src/giljo_mcp/tools/tool_accessor.py`
- **After line 319**: Add 9 async wrapper methods for context tools

### 3. Tests (NEW FILES)
- `tests/tools/test_context_tools_mcp_http.py` - Unit tests for wrapper methods
- `tests/integration/test_context_tools_mcp_endpoint.py` - Integration tests for MCP endpoint

---

## Success Criteria

- ✅ All 9 context tools listed in `mcp_http.py` tools/list response
- ✅ All 9 tools callable via MCP HTTP `tools/call` method
- ✅ All 9 ToolAccessor wrapper methods implemented and working
- ✅ Multi-tenant isolation enforced (product_id + tenant_key filtering)
- ✅ Error handling consistent across all tools (empty responses for not-found)
- ✅ Unit tests pass (>80% coverage for wrapper methods)
- ✅ Integration tests pass (end-to-end MCP HTTP flow)
- ✅ Token estimates accurate (within 10% of documented budgets)

---

## Rollback Plan

If issues arise after deployment:

1. **Remove tool definitions** from `handle_tools_list()` (lines 138-527)
2. **Remove tool routes** from `handle_tools_call()` tool_map (lines 564-609)
3. **Comment out wrapper methods** in `tool_accessor.py` (lines 319+)
4. **Restart API server**: `python api/run_api.py`

**No database changes required** - this handover only exposes existing tools.

---

## Documentation Updates Required

### 1. `docs/MCP_TOOLS_MANUAL.md`
Add section:

```markdown
## Context Management Tools (v3.2+)

GiljoAI provides 9 context tools for fetching product/project information with granular depth control.

### `get_product_context`
Fetch product core information (name, description, features).
- **Token Budget**: ~100
- **Parameters**: `product_id`, `tenant_key`, `include_metadata` (optional)

### `get_vision_document`
Fetch vision document chunks with depth control.
- **Token Budget**: 0-24K (depth: none/light/medium/full)
- **Parameters**: `product_id`, `tenant_key`, `chunking`, `offset`, `limit`

[... document remaining 7 tools ...]
```

### 2. `CLAUDE.md`
Update Context Management section:

```markdown
**9 MCP Context Tools** (HTTP-exposed as of v3.2):
1. `get_product_context` - Product name, description, features → **"Product Core" badge**
2. `get_vision_document` - Vision document chunks (paginated) → **"Vision Documents" badge**
[... list remaining tools ...]

**Example Usage** (Claude Code CLI):
```bash
# Fetch product context
mcp__giljo-mcp__get_product_context(product_id="...", tenant_key="...")

# Fetch light vision chunks
mcp__giljo-mcp__get_vision_document(product_id="...", tenant_key="...", chunking="light")
```
```

---

## Related Handovers

- **Handover 0316**: Context Management v2.0 implementation (created the 9 context tools)
- **Handover 0088**: Thin Client Architecture (prompted need for MCP-exposed context tools)
- **Handover 0246**: Orchestrator Workflow Pipeline (uses these tools for context fetching)
- **Handover 0334**: HTTP-only MCP (removed stdio, made HTTP authoritative transport)

---

## Notes

- **No Breaking Changes**: Existing MCP tools continue to work unchanged
- **Backward Compatible**: Tools support legacy depth values (e.g., "moderate" → "medium")
- **Pagination Ready**: Vision, 360 Memory support pagination (offset/limit) for future scaling
- **Git Integration Aware**: `get_git_history` returns empty if GitHub integration disabled
- **Agent Templates Tenant-Wide**: `get_agent_templates` returns templates for entire tenant (not product-specific)

---

## Completion Checklist

- [ ] Phase 1: Add tool definitions to `mcp_http.py` (handle_tools_list)
- [ ] Phase 1: Add tool routes to `mcp_http.py` (handle_tools_call)
- [ ] Phase 2: Add 9 wrapper methods to `tool_accessor.py`
- [ ] Testing: Create unit tests (`test_context_tools_mcp_http.py`)
- [ ] Testing: Create integration tests (`test_context_tools_mcp_endpoint.py`)
- [ ] Testing: Run full test suite (`pytest tests/ -v`)
- [ ] Documentation: Update `MCP_TOOLS_MANUAL.md`
- [ ] Documentation: Update `CLAUDE.md` Context Management section
- [ ] Verification: Test all 9 tools via MCP HTTP client (Claude Code CLI)
- [ ] Deployment: Commit changes with message: "feat: Expose 9 context tools via MCP HTTP (Handover 0350)"

---

**Estimated Effort**: 2-3 hours (straightforward plumbing work, no business logic changes)
