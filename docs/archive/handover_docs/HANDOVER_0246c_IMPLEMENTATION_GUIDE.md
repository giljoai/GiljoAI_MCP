# Handover 0246c Implementation Guide

**Title**: Dynamic Agent Discovery & Token Reduction
**Date**: 2025-11-24
**Status**: READY FOR IMPLEMENTATION
**Priority**: HIGH
**Timeline**: 2 days

---

## Quick Reference

**What**: Create MCP tool for dynamic agent discovery to eliminate embedded templates from orchestrator prompts.

**Why**: 25% token reduction (594 → 450 tokens), improving context efficiency for all projects.

**How**: 4 implementation phases totaling ~5 hours of coding + testing.

**Files**:
- Create: `src/giljo_mcp/tools/agent_discovery.py`
- Modify: `src/giljo_mcp/prompt_generators/thin_prompt_generator.py`
- Modify: `src/giljo_mcp/tools/__init__.py`
- Modify: `src/giljo_mcp/tools/orchestration.py`
- Create: `tests/unit/test_agent_discovery.py`
- Create: `tests/integration/test_orchestrator_discovery.py`

**Success Metric**: Orchestrator prompt reduces from 594 → 450 tokens

---

## The Problem

### Current State: Wasteful Template Embedding

Your orchestrator prompt currently includes this:
```python
# In thin_prompt_generator.py, _format_agent_templates()
def _format_agent_templates(self) -> str:
    """Format available agent templates for orchestrator."""
    templates_info = []

    templates = self.template_manager.get_active_templates(
        session=self.session,
        tenant_key=self.tenant_key
    )

    for template in templates:
        templates_info.append(
            f"- **{template.name}**: {template.role}"
        )

    return "\n".join(templates_info)
```

**Token Breakdown**:
```
Orchestrator Prompt: 594 tokens total
├── Core Instructions: 452 tokens (76%) ← Essential, changes per project
└── Agent Templates: 142 tokens (24%) ← WASTE, static and duplicated
    ├── implementer: 28 tokens
    ├── tester: 26 tokens
    ├── reviewer: 29 tokens
    ├── documenter: 31 tokens
    └── analyzer: 28 tokens
```

**Why This Is Inefficient**:
1. Templates are STATIC (same for all orchestrators)
2. Embedded in EVERY orchestrator prompt
3. ALSO returned by `get_orchestrator_instructions()` MCP tool
4. Wasteful duplication across 100K orchestrator instances annually

---

## The Solution

### What We're Building

**New MCP Tool**: `get_available_agents()`
```python
# Returns agent templates with version metadata
{
  "success": true,
  "data": {
    "agents": [
      {
        "name": "implementer",
        "role": "Code Implementation Specialist",
        "version_tag": "11242024",
        "expected_filename": "implementer_11242024.md"
      }
    ],
    "count": 1
  }
}
```

**Updated Prompt**:
```
Orchestrator Prompt: 450 tokens total
├── Core Instructions: 450 tokens (100%)
├── Discovery Instruction: "Use get_available_agents() to discover agents"
└── NO embedded templates ✅
```

**Token Savings**: 594 → 450 tokens (**25% reduction**)

---

## Implementation Phases

### Phase 1: Create MCP Tool (2-3 hours)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\tools\agent_discovery.py` (NEW)

**What to Write**:
```python
"""Dynamic agent discovery tool for orchestrators."""

from typing import Any, Dict
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models import AgentTemplate


async def get_available_agents(
    session: AsyncSession,
    tenant_key: str
) -> Dict[str, Any]:
    """
    Get available agent templates with version metadata.

    Used by orchestrators to discover available agents dynamically
    without requiring embedded templates in prompts.
    """
    try:
        # Fetch active templates
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.is_active == True
        ).order_by(AgentTemplate.created_at)

        result = await session.execute(stmt)
        templates = result.scalars().all()

        # Format response with version metadata
        agents = []
        for template in templates:
            agent_info = {
                "name": template.name,
                "role": template.role,
                "description": template.description or "",
                "version_tag": template.version_tag or "",
                "expected_filename": f"{template.name}_{template.version_tag}.md",
                "created_at": template.created_at.isoformat()
            }
            agents.append(agent_info)

        return {
            "success": True,
            "data": {
                "agents": agents,
                "count": len(agents),
                "fetched_at": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

**Key Points**:
- Tenant-isolated (filters by tenant_key)
- Only returns active templates
- Includes version metadata for validation
- Returns datetime for caching decisions

---

### Phase 2: Remove Template Embedding (1-2 hours)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\prompt_generators\thin_prompt_generator.py`

**What to Delete**:
1. Locate the `_format_agent_templates()` method (lines ~778-853)
2. Delete the entire method
3. Find where it's called in prompt building
4. Remove the call and the template section

**What to Replace**:

BEFORE:
```python
agent_templates = self._format_agent_templates()  # DELETE THIS LINE

prompt = f"""
Your role is to orchestrate {project_name}...

## Available Agents

{agent_templates}  # DELETE THIS SECTION

## Project Context
...
"""
```

AFTER:
```python
# No more agent template fetching!

prompt = f"""
Your role is to orchestrate {project_name}...

## Available Agents

To discover available agents, call the `get_available_agents()` MCP tool.
This provides dynamic access to agent templates without embedding them in the prompt.

## Project Context
...
"""
```

**Key Points**:
- Simple string replacement in prompt
- Add lightweight discovery instruction
- No functional change, just efficiency

---

### Phase 3: Register MCP Tool (30 minutes)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\tools\__init__.py`

**What to Add**:
```python
from .agent_discovery import get_available_agents

# In MCP_TOOLS registration
"get_available_agents": {
    "name": "get_available_agents",
    "description": "Discover available agent templates dynamically",
    "function": get_available_agents
}
```

**Verify**:
- Tool is exported in `__init__.py`
- Tool is registered in MCP tools registry
- Tool has proper function signature

---

### Phase 4: Update Orchestrator Instructions (1 hour)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\tools\orchestration.py`

**What to Change**:

Find the `get_orchestrator_instructions()` method and update the response:

BEFORE:
```python
result = {
    "success": True,
    "data": {
        "instructions": thin_prompt,  # 594 tokens
        "project": project_data,
        "context": context_data,
        "agent_templates": templates,  # Now unused
    }
}
```

AFTER:
```python
result = {
    "success": True,
    "data": {
        "instructions": thin_prompt,  # Now 450 tokens
        "project": project_data,
        "context": context_data,
        # agent_templates: REMOVED (use get_available_agents() instead)
    }
}
```

**Docstring Update**:
```python
async def get_orchestrator_instructions(
    self, orchestrator_id: str, tenant_key: str
) -> Dict[str, Any]:
    """
    Get orchestrator mission with context prioritization.

    Handover 0246c: Removed embedded agent templates (142 tokens).
    Orchestrators fetch agents dynamically via get_available_agents() MCP tool.

    Token reduction: 594 → 450 tokens (25% savings)
    """
```

---

## Testing Strategy (TDD)

### Write Tests FIRST (RED Phase)

**Unit Tests**: `tests/unit/test_agent_discovery.py`

```python
@pytest.mark.asyncio
async def test_get_available_agents_returns_templates(db_session, test_tenant):
    """Test discovery tool returns agent templates with metadata"""
    # Create test templates
    # Call get_available_agents()
    # Assert response has agents with version_tag

@pytest.mark.asyncio
async def test_get_available_agents_excludes_inactive(db_session, test_tenant):
    """Test only active templates are returned"""

@pytest.mark.asyncio
async def test_get_available_agents_tenant_isolated(db_session, test_tenant, other_tenant):
    """Test tenant isolation in agent discovery"""
```

**Integration Tests**: `tests/integration/test_orchestrator_discovery.py`

```python
@pytest.mark.asyncio
async def test_orchestrator_prompt_no_embedded_templates(db_session, test_project):
    """Test prompt no longer contains embedded templates"""
    # Assert "## Available Agents\n\n- **implementer**" NOT in prompt
    # Assert "get_available_agents()" IS in prompt

@pytest.mark.asyncio
async def test_prompt_token_reduction(db_session, test_project):
    """Test prompt is smaller without templates"""
    # Calculate token count
    # Assert < 495 tokens (target: 450)

@pytest.mark.asyncio
async def test_discovery_tool_available_in_orchestrator(db_session, test_project):
    """Test orchestrator can call get_available_agents()"""
```

### Run Tests

**RED Phase** (before implementation):
```bash
pytest tests/unit/test_agent_discovery.py -v
# EXPECTED: All tests FAIL
```

**GREEN Phase** (after implementation):
```bash
pytest tests/unit/test_agent_discovery.py -v
pytest tests/integration/test_orchestrator_discovery.py -v
# EXPECTED: All tests PASS
```

**Coverage Check**:
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html
# EXPECTED: >80% coverage on new code
```

---

## Verification Checklist

Before marking complete:

- [ ] `get_available_agents()` created and functional
- [ ] Tool registered in MCP tools
- [ ] `_format_agent_templates()` removed
- [ ] Prompt generation updated
- [ ] `get_orchestrator_instructions()` updated
- [ ] Orchestrator prompt token count verified: <495 tokens
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Coverage >80% on new code
- [ ] No breaking changes to existing endpoints
- [ ] Structured logging added to discovery tool
- [ ] Tenant isolation verified
- [ ] Git commit created

---

## Token Verification Method

### Before Implementation
```bash
python -c "
from src.giljo_mcp.prompt_generators.thin_prompt_generator import ThinPromptGenerator
# Create instance
generator = ThinPromptGenerator(...)
prompt = generator.generate_orchestrator_prompt(...)
token_count = len(prompt.split())  # Rough estimate
print(f'Current token count: {token_count}')
# EXPECTED: ~594 tokens
"
```

### After Implementation
```bash
python -c "
from src.giljo_mcp.prompt_generators.thin_prompt_generator import ThinPromptGenerator
# Create instance
generator = ThinPromptGenerator(...)
prompt = generator.generate_orchestrator_prompt(...)
token_count = len(prompt.split())  # Rough estimate
print(f'New token count: {token_count}')
# EXPECTED: ~450 tokens (25% reduction)
"
```

---

## Common Issues & Solutions

### Issue 1: Tool Not Found

**Problem**: Orchestrator calls `get_available_agents()` but tool not found.

**Solution**: Verify tool is registered in `src/giljo_mcp/tools/__init__.py` and exported properly.

### Issue 2: Token Count Not Reduced

**Problem**: After removing templates, prompt still ~594 tokens.

**Solution**: Verify `_format_agent_templates()` method was completely removed and call was deleted.

### Issue 3: Agent Templates Missing from Response

**Problem**: Orchestrator can't get agents via MCP tool.

**Solution**: Verify `get_available_agents()` is accessible as MCP tool, not internal function.

---

## Rollback Plan

If issues arise:

```bash
# 1. Remove discovery tool registration
git edit src/giljo_mcp/tools/__init__.py  # Remove get_available_agents

# 2. Restore template embedding
git restore src/giljo_mcp/prompt_generators/thin_prompt_generator.py

# 3. Restore old prompt structure
git restore src/giljo_mcp/tools/orchestration.py

# 4. Delete new files
git rm src/giljo_mcp/tools/agent_discovery.py
git rm tests/unit/test_agent_discovery.py
git rm tests/integration/test_orchestrator_discovery.py

# 5. Commit rollback
git commit -m "revert: Rollback Handover 0246c (dynamic agent discovery)"

# 6. Verify tests pass with old code
pytest tests/ -v
```

---

## Success Looks Like

**After 0246c is complete**:

1. ✅ Orchestrator prompt: 450 tokens (was 594)
2. ✅ All tests passing
3. ✅ Coverage >80%
4. ✅ No breaking changes
5. ✅ Commit message documents changes
6. ✅ Session memory created

**Real-World Impact**:
- 10% context budget savings per project
- 144 tokens available for larger contexts
- Foundation for future agent registration systems

---

## Key Insights

**Why This Matters**:
- Static data belongs in tools, not prompts
- Orchestrators should fetch what they need when they need it
- Embedded templates waste tokens on every instance
- Discovery tool enables future optimizations (versioning, hot-reload)

**Design Pattern**:
- Thin prompts (essential content only)
- Fat tools (provide context on demand)
- Orchestrators as smart clients (fetch and decide)

---

## Next Steps

1. **Implementer**: Start with Phase 1 - Create `agent_discovery.py`
2. **Testing**: Write failing tests (TDD RED phase)
3. **Implementation**: Implement phases 1-4
4. **Verification**: Run full test suite
5. **Commit**: Push with descriptive message

---

**Document Version**: 1.0
**Author**: Documentation Manager Agent
**Date**: 2025-11-24
**Status**: Ready for Implementer pickup
