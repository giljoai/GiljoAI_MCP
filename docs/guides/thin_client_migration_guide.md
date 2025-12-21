# Thin Client Migration Guide

**Author**: GiljoAI Development Team
**Date**: 2025-11-02
**Last Updated**: 2025-12-15 (On-Demand Fetch v3.0)
**Version**: v3.2
**Handover**: 0088 - Thin Client Stage Project Architecture Fix
**Status**: Completed — Thin client is the default
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - User journey explaining project launch flow
- **[start_to_finish_agent_FLOW.md](../../handovers/start_to_finish_agent_FLOW.md)** - Technical verification
- **[STAGE_PROJECT_FEATURE.md](../STAGE_PROJECT_FEATURE.md)** - Stage Project feature documentation

**Key Terminology** (harmonized):
- UI button: **"Stage Project"**
- Backend endpoint: `POST /api/v1/projects/{id}/activate`
- Initial job status: **"waiting"** (not "pending")

**Agent Templates** (6 default):
- orchestrator, implementer, tester, analyzer, reviewer, documenter

---

## Overview

Handover 0088 replaces 3000-line "fat prompts" with 10-line "thin prompts" that fetch missions via MCP tools. This guide explains how to migrate from the deprecated `OrchestratorPromptGenerator` to the new `ThinClientPromptGenerator`. New development must use the thin client generator and `POST /api/prompts/orchestrator`.

---

## Why This Change?

### The Problem: Fat Prompts

The old approach generated 2000-3000 line prompts with the entire mission embedded directly:

**Issues**:
- ❌ Defeats context prioritization and orchestration feature
- ❌ Terrible user experience (copying 3000 lines)
- ❌ Immutable missions (can't update after launch)
- ❌ High API costs (30K tokens upfront)
- ❌ Unprofessional appearance

### The Solution: Thin Client Architecture

The new approach generates ~10 line prompts with identity only:

**Benefits**:
- ✅ context prioritization and orchestration ACTIVE
- ✅ Professional UX (copy 10 lines, not 3000)
- ✅ Dynamic missions (can refetch updates)
- ✅ Lower API costs (50 tokens upfront, 6K via MCP)
- ✅ Commercial-grade appearance

---

## Migration Steps

### For Developers

#### 1. Replace OrchestratorPromptGenerator

**OLD (Fat Prompt)**:
```python
from src.giljo_mcp.prompt_generator import OrchestratorPromptGenerator

# Generate fat prompt
generator = OrchestratorPromptGenerator(db, tenant_key)
result = await generator.generate(project_id, tool)

# Result: 3000-line prompt with 30K tokens
```

**NEW (Thin Prompt)**:
```python
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

# Generate thin prompt
generator = ThinClientPromptGenerator(db, tenant_key)
result = await generator.generate(
    project_id=project_id,
    user_id=user_id,  # CRITICAL for field priorities
    tool=tool,
    instance_number=1
)

# Result: 10-line prompt with 50 tokens
```

#### 2. Update API Endpoints

**OLD**:
```python
from src.giljo_mcp.prompt_generator import OrchestratorPromptGenerator

@router.post("/orchestrator")
async def generate_orchestrator_prompt(request, current_user, db):
    generator = OrchestratorPromptGenerator(db, current_user.tenant_key)
    result = await generator.generate(request.project_id, request.tool)
    return result
```

**NEW**:
```python
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

@router.post("/orchestrator")
async def generate_orchestrator_prompt(request, current_user, db):
    generator = ThinClientPromptGenerator(db, current_user.tenant_key)
    result = await generator.generate(
        project_id=request.project_id,
        user_id=str(current_user.id),  # CRITICAL
        tool=request.tool,
        instance_number=request.instance_number or 1
    )
    return result
```

#### 3. Update Response Schema

**OLD**:
```python
class OrchestratorPromptResponse(BaseModel):
    prompt: str  # 3000 lines
    token_estimate: int  # 30,000 tokens
```

**NEW**:
```python
class ThinPromptResponse(BaseModel):
    prompt: str  # 10 lines
    orchestrator_id: str
    project_id: str
    project_name: str
    estimated_prompt_tokens: int  # ~50 tokens
    mcp_tool_name: str  # "get_orchestrator_instructions"
    instructions_stored: bool  # True
```

#### 4. Update Frontend Components

**OLD**:
```javascript
// LaunchTab.vue
const generatedPrompt = ref('')  // 3000 lines
const tokenEstimate = ref(0)     // 30,000 tokens
```

**NEW**:
```javascript
// LaunchTab.vue
const generatedPrompt = ref('')         // 10 lines
const orchestratorId = ref('')
const estimatedPromptTokens = ref(0)    // ~50 tokens
const missionTokens = ref(0)            // ~6,000 tokens
```

---

### For Users

**No action required**. Thin client architecture is transparent to end users:

1. **Before**: Copy/paste 3000 lines
2. **After**: Copy/paste 10 lines
3. **Same functionality**, better experience

### Context Fetching (v3.0 - On-Demand)

Orchestrators now fetch context on-demand using the unified `fetch_context()` tool:

```python
# Orchestrator calls get_orchestrator_instructions() and receives framing
# Then fetches context based on priority tier (one category per call):
product_core = await fetch_context(
    product_id=product_id,
    tenant_key=tenant_key,
    categories=["product_core"]  # Array with ONE category (Handover 0351)
)
tech_stack = await fetch_context(
    product_id=product_id,
    tenant_key=tenant_key,
    categories=["tech_stack"]  # Separate call for each category
)
```

**See**: [Context Tools API Reference](../api/context_tools.md) for complete documentation.

---

## Key Differences

| Aspect | Fat Prompt (OLD) | Thin Prompt (NEW) |
|--------|------------------|-------------------|
| Prompt Size | 2000-3000 lines | ~10 lines |
| Upfront Tokens | 30,000 tokens | 50 tokens |
| Mission Delivery | Embedded in prompt | Fetched via MCP |
| Field Priorities | Bypassed | Applied (70% reduction) |
| User Experience | Copy 3000 lines | Copy 10 lines |
| Mission Updates | Immutable | Dynamic (can refetch) |
| API Costs | High | Low |
| Professional | No | Yes |

---

## Benefits

### Token Reduction
- **Fat Prompt**: 30,000 tokens (mission embedded)
- **Thin Prompt**: 50 tokens (prompt) + 6,000 tokens (MCP fetch)
- **Savings**: 23,950 tokens (79.8% reduction)
- **Target**: ≥70% ✅ EXCEEDED

### User Experience
- **OLD**: User copies 3000 lines into Claude Code CLI
- **NEW**: User copies 10 lines into Claude Code CLI
- **Improvement**: 99.7% reduction in paste burden

### Professional Appearance
- **OLD**: Unprofessional (commercial products don't ask users to copy novels)
- **NEW**: Professional (commercial-grade thin client architecture)

### Dynamic Missions
- **OLD**: Mission frozen at launch time
- **NEW**: Orchestrator can refetch updated mission anytime via MCP

### Lower API Costs
- **OLD**: 30K tokens consumed upfront (even if unused)
- **NEW**: 50 tokens upfront, 6K only when needed

---

## Migration Timeline

### Phase 1: Backwards Compatibility (v3.1 - Current)

**Status**: Both generators available
- ✅ `ThinClientPromptGenerator` (recommended)
- ⚠️ `OrchestratorPromptGenerator` (deprecated)

**Action**: New development must use thin client generator

### Phase 2: Default Migration (v3.2 - Q1 2026)

**Status**: Thin client becomes default
- ✅ `ThinClientPromptGenerator` (default)
- ⚠️ `OrchestratorPromptGenerator` (available with warning)

**Action**: Migrate existing code to thin client generator

### Phase 3: Complete Removal (v4.0 - Q2 2026)

**Status**: Fat prompts removed
- ✅ `ThinClientPromptGenerator` (only option)
- ❌ `OrchestratorPromptGenerator` (removed)

**Action**: All code must use thin client generator

---

## Common Pitfalls

### Pitfall 1: Forgetting to Pass user_id

**WRONG**:
```python
# Field priorities ignored!
result = await generator.generate(project_id=project_id)
```

**CORRECT**:
```python
# Field priorities applied
result = await generator.generate(
    project_id=project_id,
    user_id=str(current_user.id)  # CRITICAL
)
```

**Impact**: Without `user_id`, field priorities are ignored and context prioritization and orchestration is lost.

---

### Pitfall 2: Embedding Mission in Prompt

**WRONG**:
```python
# Defeats thin client architecture!
prompt = f"""
Orchestrator ID: {orchestrator_id}

YOUR MISSION:
{condensed_mission}  # DON'T EMBED THIS
"""
```

**CORRECT**:
```python
# Thin client - mission fetched via MCP
prompt = f"""
Orchestrator ID: {orchestrator_id}

Call get_orchestrator_instructions('{orchestrator_id}')
"""
```

**Impact**: Embedding mission defeats the entire purpose of thin client architecture.

---

### Pitfall 3: Not Storing Metadata

**WRONG**:
```python
# Field priorities lost!
orchestrator = MCPAgentJob(
    id=orchestrator_id,
    mission=condensed_mission
    # NO metadata!
)
```

**CORRECT**:
```python
# Store field priorities for MCP tool
orchestrator = MCPAgentJob(
    id=orchestrator_id,
    mission=condensed_mission,
    metadata={
        'field_priorities': field_priorities,  # CRITICAL
        'user_id': user_id,                    # CRITICAL
        'tool': tool
    }
)
```

**Impact**: MCP tool can't apply field priorities without metadata.

---

## Testing

### Unit Tests

```bash
# Test thin prompt generator
python -m pytest tests/thin_prompt/test_thin_client_generator.py -v

# Test MCP tools
python -m pytest tests/tools/test_orchestrator_instructions.py -v

# Test API endpoints
python -m pytest tests/api/test_thin_prompt_endpoint.py -v
```

### Integration Tests

```bash
# Test E2E workflow
python -m pytest tests/thin_prompt/test_thin_client_e2e.py -v

# Test context prioritization
python -m pytest tests/thin_prompt/test_token_reduction.py -v
```

### Manual Testing

1. Generate thin prompt in UI (Projects → Stage Project)
2. Verify prompt is ~10 lines
3. Copy to clipboard
4. Paste into Claude Code CLI
5. Verify orchestrator calls `get_orchestrator_instructions()`
6. Verify mission fetched correctly
7. Check token estimates

---

## Support

### Questions?

See: `handovers/0088_thin_client_stage_project_fix.md`

### Issues?

Check:
- MCP server logs: `~/.giljo_mcp/logs/mcp_adapter.log`
- API server logs: `~/.giljo_mcp/logs/api.log`
- Database status: `psql -U postgres -d giljo_mcp`

### Need Help?

Contact: GiljoAI Development Team

---

**Last Updated**: 2025-12-15
**Version**: v3.2
**Status**: Active Migration Guide
