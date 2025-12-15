# Handover 0350d: Update Documentation for On-Demand Context Fetch Architecture

**Series**: 0350 (Context Management On-Demand Architecture)
**Date**: 2025-12-15
**Status**: Ready for Execution
**Priority**: High
**Estimated Effort**: 2-3 hours

## Executive Summary

After implementing the on-demand fetch architecture (Handover 0350-0352), documentation is now outdated. CLAUDE.md references deprecated `fetch_*` tools, implies monolithic context delivery, and lacks documentation for the 3-tier priority system. This handover updates all documentation to reflect the new architecture.

## Problem Statement

### Critical Gaps

1. **CLAUDE.md Context Management Section (Lines 151-184)**
   - References old tool names: `fetch_product_context`, `fetch_vision_document`, etc.
   - Section title says "v2.0" but architecture is now v3.0 (on-demand)
   - Implies context is embedded in orchestrator instructions (monolithic)
   - No documentation of 3-tier priority system (CRITICAL/IMPORTANT/REFERENCE)

2. **Missing API Reference**
   - No documentation exists for the 9 context tools
   - Parameters, return values, and examples not documented
   - Depth configurations not explained

3. **Architecture Not Explained**
   - Framing vs. on-demand fetch not documented
   - No explanation of why on-demand prevents truncation
   - Priority tier actions (MUST/SHOULD/MAY) not defined

## Current State Analysis

### Existing Tools (Implemented in 0350-0352)

All tools are in `F:\GiljoAI_MCP\src\giljo_mcp\tools\context_tools\`:

```
get_product_context.py       # Product name, description, features
get_vision_document.py        # Vision chunks (paginated)
get_tech_stack.py            # Tech stack configuration
get_architecture.py          # Architecture patterns
get_testing.py               # Testing configuration
get_360_memory.py            # Sequential project history
get_git_history.py           # Git commits
get_agent_templates.py       # Agent template metadata
get_project.py               # Project metadata
```

### Priority Tier System (from framing_helpers.py)

```python
Priority 1 (CRITICAL)   -> Framing: "REQUIRED"    -> Action: MUST call
Priority 2 (IMPORTANT)  -> Framing: "RECOMMENDED" -> Action: SHOULD call
Priority 3 (REFERENCE)  -> Framing: "OPTIONAL"    -> Action: MAY call
Priority 4 (OFF)        -> (excluded)             -> Action: Never call
```

### On-Demand Architecture Flow

1. Orchestrator calls `get_orchestrator_instructions()`
2. Receives framing (~500 tokens) with priority indicators
3. Orchestrator calls individual `get_*` tools based on priority
4. No risk of truncating 50K+ vision documents

## Proposed Changes

### 1. Update CLAUDE.md Context Management Section

**Location**: Lines 151-184

**Replace entire section with:**

```markdown
## Context Management (v3.0 - On-Demand Fetch)

GiljoAI uses an on-demand context fetch architecture to prevent token truncation.

### Architecture Overview

**Problem Solved**: Previous monolithic approach embedded all context in orchestrator instructions, causing truncation when vision documents exceeded 50K tokens.

**Solution**:
1. `get_orchestrator_instructions()` returns framing (~500 tokens) with priority indicators
2. Orchestrator calls individual `get_*` tools based on priority tier
3. Context is fetched on-demand, never truncated

### 3-Tier Priority System

| Tier | Label | Framing | Orchestrator Action |
|------|-------|---------|---------------------|
| **Priority 1** | CRITICAL | "REQUIRED" | MUST call `get_*` tool |
| **Priority 2** | IMPORTANT | "RECOMMENDED" | SHOULD call `get_*` tool |
| **Priority 3** | REFERENCE | "OPTIONAL" | MAY call `get_*` tool if needed |
| **Priority 4** | OFF | (excluded) | Never call tool |

**Configuration**:
- Priority: My Settings → Context → Field Priority Configuration
- Depth: My Settings → Context → Depth Configuration

### 9 Context Tools (On-Demand via MCP HTTP)

All tools follow the pattern: `get_<field_name>(product_id, tenant_key, depth_config)`

1. **get_product_context** - Product name, description, features
2. **get_vision_document** - Vision document chunks (paginated, depth-aware)
3. **get_tech_stack** - Programming languages, frameworks, databases
4. **get_architecture** - Architecture patterns, API style, design patterns
5. **get_testing** - Testing config (quality standards, strategy, frameworks)
6. **get_360_memory** - Sequential project history (paginated)
7. **get_git_history** - Aggregated git commits from all projects
8. **get_agent_templates** - Agent template metadata (minimal/standard/full)
9. **get_project** - Current project metadata

**See**: [docs/api/context_tools.md](docs/api/context_tools.md) for complete API reference.

### Depth Configuration

Depth controls how much detail to fetch (where applicable):

- **Vision Documents**: none/light/moderate/heavy (0-30K tokens)
- **Tech Stack**: required/all (200-400 tokens)
- **Architecture**: overview/detailed (300-1.5K tokens)
- **Testing**: none/basic/full (0-400 tokens)
- **360 Memory**: 1/3/5/10 projects (500-5K tokens)
- **Git History**: 10/25/50/100 commits (500-5K tokens)
- **Agent Templates**: minimal/standard/full (400-2.4K tokens)

### Backward Compatibility

- Old monolithic approach deprecated (v2.0)
- `fetch_*` tools no longer exist (renamed to `get_*`)
- ThinClientPromptGenerator uses on-demand architecture
```

### 2. Create New API Reference Document

**Create**: `F:\GiljoAI_MCP\docs\api\context_tools.md`

**Content**: (See Appendix A)

### 3. Update Orchestrator Documentation References

**File**: `F:\GiljoAI_MCP\docs\ORCHESTRATOR.md`

**Find and replace**:
- `fetch_*` → `get_*`
- Add reference to `docs/api/context_tools.md`

### 4. Update Thin Client Migration Guide

**File**: `F:\GiljoAI_MCP\docs\guides\thin_client_migration_guide.md`

**Find and replace**:
- `fetch_*` → `get_*`
- Update examples to show on-demand pattern

## Implementation Steps

### Step 1: Update CLAUDE.md

```bash
# Edit F:\GiljoAI_MCP\CLAUDE.md
# Replace lines 151-184 with new section (see Proposed Changes #1)
```

**Verification**:
- No references to `fetch_*` tools remain
- Version updated to v3.0
- 3-tier priority system documented
- On-demand architecture explained

### Step 2: Create API Reference

```bash
# Create F:\GiljoAI_MCP\docs\api\context_tools.md
# Use content from Appendix A
```

**Verification**:
- All 9 tools documented
- Parameters with types listed
- Return schemas provided
- Examples included

### Step 3: Update Cross-References

```bash
# Update F:\GiljoAI_MCP\docs\ORCHESTRATOR.md
# Update F:\GiljoAI_MCP\docs\guides\thin_client_migration_guide.md
# Replace all fetch_* references with get_*
```

**Verification**:
- All cross-references updated
- Links to new API reference work
- No broken links

## Success Criteria

- [ ] No `fetch_*` references in CLAUDE.md
- [ ] Context Management section updated to v3.0
- [ ] 3-tier priority system documented
- [ ] On-demand architecture explained
- [ ] API reference created at `docs/api/context_tools.md`
- [ ] All 9 tools documented with examples
- [ ] Cross-references updated in ORCHESTRATOR.md
- [ ] Cross-references updated in thin_client_migration_guide.md
- [ ] All links work

## Testing Plan

### Documentation Review

```bash
# 1. Search for old tool names
grep -r "fetch_product_context" docs/ CLAUDE.md
grep -r "fetch_vision_document" docs/ CLAUDE.md
grep -r "fetch_tech_stack" docs/ CLAUDE.md
# Should return 0 results after update

# 2. Verify new tool names
grep -r "get_product_context" docs/ CLAUDE.md
grep -r "get_vision_document" docs/ CLAUDE.md
# Should find references in CLAUDE.md and docs/api/context_tools.md

# 3. Verify links work
# Manually check all [docs/api/context_tools.md] links
```

### Content Accuracy

- Verify priority tier table matches `framing_helpers.py` implementation
- Verify tool list matches `src/giljo_mcp/tools/context_tools/` directory
- Verify depth options match product configuration UI

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Documentation becomes out of sync with code | High | Add "last verified" date to API reference |
| Depth options change in future | Medium | Link to definitive source (UI config) |
| New tools added without updating docs | Medium | Add comment in tool registration code pointing to docs |

## Related Work

**Depends on**:
- Handover 0350 (Research)
- Handover 0351 (Implementation - if exists)
- Handover 0352 (Testing - if exists)

**Enables**:
- Accurate onboarding for new developers
- Correct orchestrator implementation by agents
- Proper priority configuration by users

## Notes

### Current Documentation State

- CLAUDE.md is the authoritative project documentation (claudeMd system)
- All agents read CLAUDE.md to understand the project
- Outdated documentation directly impacts agent behavior

### Tool Naming Convention

- Old: `fetch_*` (implied monolithic retrieval)
- New: `get_*` (implies on-demand fetch)
- This naming change is intentional and reflects architectural shift

### Priority vs. Depth

- **Priority**: WHAT to fetch (CRITICAL/IMPORTANT/REFERENCE/OFF)
- **Depth**: HOW MUCH to fetch (light/moderate/heavy, 1/3/5/10, etc.)
- Both are orthogonal dimensions (2D context model)

## Appendix A: API Reference Content

**File**: `F:\GiljoAI_MCP\docs\api\context_tools.md`

```markdown
# Context Tools API Reference

**Version**: v3.0 (On-Demand Fetch)
**Last Updated**: 2025-12-15

## Overview

Context tools enable orchestrators to fetch context on-demand based on priority configuration. All tools return structured JSON responses and are multi-tenant isolated.

## Architecture

### On-Demand Fetch Pattern

1. Orchestrator calls `get_orchestrator_instructions()`
2. Receives framing (~500 tokens) with priority indicators
3. Orchestrator calls individual `get_*` tools based on priority tier
4. Context is assembled without truncation risk

### Common Parameters

All tools accept these standard parameters:

- **product_id** (str, required): Product UUID
- **tenant_key** (str, required): Tenant isolation key
- **depth_config** (str, optional): Depth level (varies by tool)

### Common Response Schema

```json
{
  "source": "<tool_name>",
  "data": { ... },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 100,
    "depth": "moderate",
    "priority": 2
  }
}
```

## Tool Reference

### 1. get_product_context

Fetch general product information (Product Core).

**Parameters**:
```python
product_id: str          # Product UUID (required)
tenant_key: str          # Tenant key (required)
include_metadata: bool   # Include meta_data JSONB (default: False)
```

**Returns**:
```json
{
  "source": "product_context",
  "data": {
    "product_name": "GiljoAI MCP",
    "product_description": "Multi-tenant server orchestrating...",
    "project_path": "/path/to/project",
    "core_features": ["Feature 1", "Feature 2"],
    "is_active": true,
    "created_at": "2025-11-01T10:00:00"
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 100
  }
}
```

**Depth Config**: N/A (always returns core fields)

**Example**:
```python
result = await get_product_context(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    include_metadata=False
)
```

---

### 2. get_vision_document

Fetch vision documents with pagination and depth control.

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
depth: str           # Depth level: none/light/moderate/heavy (default: moderate)
page: int            # Page number for pagination (default: 1)
page_size: int       # Items per page (default: 10)
```

**Depth Options**:
- `none`: No vision documents fetched (0 tokens)
- `light`: Summaries only (~500 tokens)
- `moderate`: Summaries + key sections (~5K tokens)
- `heavy`: Full vision documents (~30K tokens)

**Returns**:
```json
{
  "source": "vision_documents",
  "data": {
    "documents": [
      {
        "name": "product_vision.md",
        "summary": "Overview of product goals...",
        "content": "# Vision\n\n...",  // Only if depth=moderate/heavy
        "tokens": 1500
      }
    ],
    "total": 3,
    "page": 1,
    "page_size": 10,
    "has_more": false
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 1500,
    "depth": "moderate"
  }
}
```

**Example**:
```python
result = await get_vision_document(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    depth="moderate",
    page=1
)
```

---

### 3. get_tech_stack

Fetch technology stack configuration.

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
depth: str           # Depth level: required/all (default: all)
```

**Depth Options**:
- `required`: Only required tech (languages, main frameworks) ~200 tokens
- `all`: Full stack including dev tools, testing, etc. ~400 tokens

**Returns**:
```json
{
  "source": "tech_stack",
  "data": {
    "languages": ["Python", "JavaScript"],
    "frameworks": {
      "backend": ["FastAPI", "SQLAlchemy"],
      "frontend": ["Vue 3", "Vuetify"]
    },
    "databases": ["PostgreSQL"],
    "tools": ["pytest", "ruff", "black"],  // Only if depth=all
    "version_constraints": {              // Only if depth=all
      "python": "3.11+",
      "node": "18+"
    }
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 400,
    "depth": "all"
  }
}
```

**Example**:
```python
result = await get_tech_stack(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    depth="all"
)
```

---

### 4. get_architecture

Fetch architecture documentation.

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
depth: str           # Depth level: overview/detailed (default: overview)
```

**Depth Options**:
- `overview`: High-level patterns only ~300 tokens
- `detailed`: Full architecture with design patterns ~1.5K tokens

**Returns**:
```json
{
  "source": "architecture",
  "data": {
    "primary_pattern": "Modular monolith with service layer",
    "api_style": "REST + JSON, WebSockets for real-time",
    "design_patterns": [           // Only if depth=detailed
      "Repository",
      "Dependency Injection",
      "Factory",
      "SOLID principles"
    ],
    "notes": "Local-first, zero-config..."  // Only if depth=detailed
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 1500,
    "depth": "detailed"
  }
}
```

**Example**:
```python
result = await get_architecture(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    depth="detailed"
)
```

---

### 5. get_testing

Fetch testing configuration.

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
depth: str           # Depth level: none/basic/full (default: basic)
```

**Depth Options**:
- `none`: No testing config (0 tokens)
- `basic`: Strategy and coverage target ~100 tokens
- `full`: Full config with frameworks and tools ~400 tokens

**Returns**:
```json
{
  "source": "testing",
  "data": {
    "strategy": "TDD with >80% coverage",
    "coverage_target": 80,
    "frameworks": [                // Only if depth=full
      "pytest",
      "pytest-asyncio",
      "Vitest"
    ],
    "quality_standards": "..."     // Only if depth=full
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 400,
    "depth": "full"
  }
}
```

**Example**:
```python
result = await get_testing(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    depth="full"
)
```

---

### 6. get_360_memory

Fetch sequential project history (360 memory).

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
limit: int           # Number of projects to fetch: 1/3/5/10 (default: 5)
```

**Returns**:
```json
{
  "source": "360_memory",
  "data": {
    "sequential_history": [
      {
        "sequence": 1,
        "type": "project_closeout",
        "project_id": "uuid",
        "summary": "Completed feature X...",
        "git_commits": [...],
        "timestamp": "2025-11-16T10:00:00Z"
      }
    ],
    "total": 10,
    "returned": 5
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 2500,
    "limit": 5
  }
}
```

**Example**:
```python
result = await get_360_memory(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    limit=5
)
```

---

### 7. get_git_history

Fetch aggregated git commits from all projects.

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
limit: int           # Number of commits: 10/25/50/100 (default: 25)
```

**Returns**:
```json
{
  "source": "git_history",
  "data": {
    "commits": [
      {
        "hash": "59db3da6",
        "message": "fix: Complete dynamic tier assignment...",
        "author": "Claude Opus",
        "date": "2025-12-15T10:00:00Z",
        "project_id": "uuid"
      }
    ],
    "total": 100,
    "returned": 25
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 1250,
    "limit": 25
  }
}
```

**Example**:
```python
result = await get_git_history(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    limit=25
)
```

---

### 8. get_agent_templates

Fetch agent template metadata.

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
depth: str           # Depth level: minimal/standard/full (default: standard)
```

**Depth Options**:
- `minimal`: Template names only ~100 tokens
- `standard`: Names + descriptions ~800 tokens
- `full`: Full templates with protocols ~2.4K tokens

**Returns**:
```json
{
  "source": "agent_templates",
  "data": {
    "templates": [
      {
        "name": "backend-integration-tester",
        "description": "Tests backend integrations...",  // Only if depth=standard/full
        "protocol": "6-phase lifecycle...",              // Only if depth=full
        "capabilities": [...]                            // Only if depth=full
      }
    ],
    "total": 12
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 2400,
    "depth": "full"
  }
}
```

**Example**:
```python
result = await get_agent_templates(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    depth="standard"
)
```

---

### 9. get_project

Fetch current project metadata (Project Context - Always Critical).

**Parameters**:
```python
product_id: str       # Product UUID (required)
tenant_key: str       # Tenant key (required)
project_id: str      # Project UUID (required)
```

**Returns**:
```json
{
  "source": "project_context",
  "data": {
    "project_name": "Setup project structure",
    "project_description": "This project is about setting up...",
    "project_path": "F:\\TinyContacts",
    "status": "active",
    "created_at": "2025-12-01T10:00:00Z"
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "project_id": "uuid",
    "estimated_tokens": 150
  }
}
```

**Example**:
```python
result = await get_project(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    project_id="456e7890-e89b-12d3-a456-426614174001"
)
```

---

## Priority System Integration

### Priority Tier Framing

When `get_orchestrator_instructions()` returns framing, it includes priority indicators:

```json
{
  "field_priorities": {
    "product_context": 1,      // CRITICAL -> MUST call get_product_context
    "vision_documents": 2,     // IMPORTANT -> SHOULD call get_vision_document
    "architecture": 3,         // REFERENCE -> MAY call get_architecture
    "testing": 4               // OFF -> Never call get_testing
  },
  "priority_map": {
    "critical": ["product_context", "project_context"],
    "important": ["vision_documents", "tech_stack"],
    "reference": ["architecture", "360_memory", "git_history"]
  },
  "_priority_frame": {
    "product_context": "REQUIRED - Call get_product_context()",
    "vision_documents": "RECOMMENDED - Call get_vision_document()",
    "architecture": "OPTIONAL - Call get_architecture() if needed"
  }
}
```

### Orchestrator Decision Logic

```python
# Example orchestrator logic
for field, priority in field_priorities.items():
    if priority == 1:  # CRITICAL
        # MUST call
        result = await get_{field}(product_id, tenant_key, depth_config)
    elif priority == 2:  # IMPORTANT
        # SHOULD call (unless token budget tight)
        if tokens_remaining > 10000:
            result = await get_{field}(product_id, tenant_key, depth_config)
    elif priority == 3:  # REFERENCE
        # MAY call (only if specifically needed for mission)
        if mission_requires(field):
            result = await get_{field}(product_id, tenant_key, depth_config)
    # priority 4 (OFF) = never call
```

## Multi-Tenant Isolation

All tools enforce multi-tenant isolation:

```python
# All queries filter by tenant_key
stmt = select(Product).where(
    Product.id == product_id,
    Product.tenant_key == tenant_key
)
```

**Security**: Agents cannot access context from other tenants, even with valid product_id.

## Error Handling

### Common Error Responses

```json
{
  "source": "tool_name",
  "data": {},
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "...",
    "estimated_tokens": 0,
    "error": "product_not_found"
  }
}
```

**Error Codes**:
- `product_not_found`: Product ID + tenant key combination invalid
- `project_not_found`: Project ID not found for tenant
- `invalid_depth`: Depth parameter not recognized
- `database_error`: Database query failed

## Token Estimation

Token estimates use the heuristic: **1 token ≈ 4 characters**

```python
def estimate_tokens(data: Any) -> int:
    import json
    text = json.dumps(data)
    return len(text) // 4
```

**Accuracy**: ~90% accurate for JSON responses, may vary for markdown content.

## Backward Compatibility

### Deprecated Tools (v2.0)

- `fetch_product_context` → `get_product_context`
- `fetch_vision_document` → `get_vision_document`
- `fetch_tech_stack` → `get_tech_stack`
- `fetch_architecture` → `get_architecture`
- `fetch_testing_config` → `get_testing`
- `fetch_360_memory` → `get_360_memory`
- `fetch_git_history` → `get_git_history`
- `fetch_agent_templates` → `get_agent_templates`
- `fetch_project_context` → `get_project`

**Migration**: Update all tool calls to use `get_*` naming convention.

## See Also

- [CLAUDE.md](../../CLAUDE.md) - Project documentation
- [ORCHESTRATOR.md](../ORCHESTRATOR.md) - Orchestrator guide
- [thin_client_migration_guide.md](../guides/thin_client_migration_guide.md) - Migration guide
```

---

**End of Handover 0350d**
