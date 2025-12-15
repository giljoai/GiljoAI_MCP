# Handover: 0347d - Agent Templates Depth Toggle

**Date:** 2025-12-14
**From Agent:** UX Designer
**To Agent:** TDD Implementor
**Priority:** Medium
**Estimated Complexity:** 2 hours
**Status:** Ready for Implementation
**Dependencies:** 0347b (MissionPlanner must use JSON)

---

## Problem Statement

Orchestrators currently receive minimal agent template information ("Type Only" mode with ~50 tokens/agent). While this is token-efficient, orchestrators sometimes need to understand agent capabilities in detail to make nuanced task assignment decisions. We need a UI toggle that allows users to control the level of agent template detail included in orchestrator instructions.

**Current Behavior:**
- Agent templates always return minimal metadata: `name`, `role`, `description` (~50 tokens/agent)
- Total cost for 5 agents: ~250 tokens
- Orchestrators must make assignment decisions based only on agent names/roles

**Desired Behavior:**
- User can toggle between "Type Only" and "Full" modes via Context Depth UI
- "Type Only": Returns minimal metadata (~50 tokens/agent) - **DEFAULT**
- "Full": Returns complete agent template including full prompt content (~2000-3000 tokens/agent)
- Total cost for 5 agents: ~250 tokens (Type Only) or ~12,500 tokens (Full)
- Setting persists in user's `depth_config`

---

## Scope

### In Scope
✅ Frontend toggle in Context Depth UI (My Settings → Context → Depth Configuration)
✅ Backend logic to check `depth_config["agent_templates"]` value
✅ Type Only mode: Return `name`, `role`, `description` only
✅ Full mode: Call `get_template()` for each enabled agent and merge full data
✅ TDD test suite covering both modes
✅ Token estimation updates

### Out of Scope
❌ Changes to agent template storage schema
❌ Changes to existing `get_template()` MCP tool
❌ UI for creating/editing agent templates
❌ Agent spawning logic modifications

---

## Tasks

### Backend Tasks
- [ ] **Task 1**: Add helper method `_get_full_agent_templates()` to `MissionPlanner`
  - Fetch enabled agent templates for tenant
  - Call `get_template(template_name)` for each template
  - Return array with fields: `name`, `role`, `description`, `content`, `cli_tool`, `background_color`, `category`
  - **Test First**: Write `test_get_full_agent_templates_returns_complete_data()`

- [ ] **Task 2**: Update `get_orchestrator_instructions()` to check depth config
  - Read `depth_config["agent_templates"]` value
  - If `"type_only"` (default): Return minimal metadata as currently
  - If `"full"`: Call `_get_full_agent_templates()` helper
  - **Test First**: Write `test_type_only_mode_returns_minimal_agent_data()`
  - **Test First**: Write `test_full_mode_returns_complete_agent_prompts()`

- [ ] **Task 3**: Update token estimation for Full mode
  - Type Only: ~50 tokens/agent (existing calculation)
  - Full: ~2000-3000 tokens/agent (measure actual content length)
  - **Test First**: Write `test_token_estimation_accurate_for_both_modes()`

### Frontend Tasks
- [ ] **Task 4**: Add "Agent Templates" depth toggle to UI
  - Location: `frontend/src/components/settings/ContextPriorityConfig.vue`
  - Already exists in `depthControlledContexts` computed property
  - Update `formatOptions()` to return proper labels:
    - `{ title: 'Type Only (~250 tokens for 5 agents)', value: 'type_only' }`
    - `{ title: 'Full (~12,500 tokens for 5 agents)', value: 'full' }`
  - Default: `'type_only'` (token-efficient)
  - **Test First**: Write `test_agent_templates_toggle_has_two_options()`

- [ ] **Task 5**: Verify toggle saves to backend
  - Ensure PUT `/api/v1/users/me/context/depth` includes `agent_template_detail` field
  - **Test First**: Write `test_agent_template_depth_saves_to_backend()`

### Integration Testing
- [ ] **Task 6**: E2E test for full workflow
  - Create project, stage orchestrator
  - Toggle agent templates to "Full" mode
  - Call `get_orchestrator_instructions()`
  - Verify response includes full agent content
  - Measure token count difference
  - **Test First**: Write `test_e2e_agent_template_depth_toggle_workflow()`

---

## Success Criteria

### Functional Requirements
- ✅ **Type Only mode** returns only `name`, `role`, `description` for each agent
- ✅ **Full mode** returns complete agent data including `content` field
- ✅ Toggle persists across sessions (stored in `depth_config`)
- ✅ Default is "Type Only" for token efficiency
- ✅ No breaking changes to existing orchestrator workflows

### Token Budget Validation
- ✅ **Type Only**: ~50 tokens/agent (3 agents = ~150 tokens, 5 agents = ~250 tokens)
- ✅ **Full**: ~2000-3000 tokens/agent (3 agents = ~7,500 tokens, 5 agents = ~12,500 tokens)
- ✅ Token delta matches specification table (see Mode Comparison below)

### Test Coverage
- ✅ **Unit tests**: Helper method, depth config reading, token estimation
- ✅ **Integration tests**: Full workflow from UI toggle to orchestrator response
- ✅ **Edge cases**: Invalid depth values, missing config, backwards compatibility
- ✅ **Coverage target**: >80% for modified files

### UX Requirements
- ✅ Toggle labels clearly explain token costs
- ✅ Help text explains when to use each mode
- ✅ Settings auto-save on change
- ✅ UI shows current selection accurately

---

## Mode Comparison

### Type Only Mode (Default - Token Efficient)

Returns minimal agent metadata sufficient for `spawn_agent_job`:

```json
"agent_templates": [
  {
    "name": "implementer",
    "role": "implementer",
    "description": "Implementation specialist for writing production-grade code"
  }
]
```

**Token cost**: ~50 tokens per agent (~250 tokens for 5 agents)

**Use cases**:
- Standard staging - orchestrator only needs agent names for spawning
- Token budget constraints
- Simple task assignment (agent role is obvious from name)

### Full Mode (Complete Agent Context)

Returns full agent template including the complete agent prompt/instructions:

```json
"agent_templates": [
  {
    "name": "implementer",
    "role": "implementer",
    "description": "Implementation specialist for writing production-grade code",
    "content": "## MCP COMMUNICATION PROTOCOL (Handover 0090)\n\nYou have access to comprehensive MCP tools...[full agent prompt]...",
    "cli_tool": "claude",
    "background_color": "#3498DB",
    "category": "role"
  }
]
```

**Token cost**: ~2000-3000 tokens per agent (~10,000-15,000 tokens for 5 agents)

**Use cases**:
- Orchestrator needs to understand agent capabilities for task assignment decisions
- Custom/specialized agents where orchestrator should review full instructions
- Debugging agent behavior or validating agent prompts
- Complex projects requiring nuanced agent selection

### Token Budget Impact

| Agents | Type Only | Full Mode | Delta |
|--------|-----------|-----------|-------|
| 3 agents | ~150 tokens | ~7,500 tokens | +7,350 |
| 5 agents | ~250 tokens | ~12,500 tokens | +12,250 |
| 8 agents | ~400 tokens | ~20,000 tokens | +19,600 |

**Recommendation**: Default to "Type Only" for token efficiency. Use "Full" only when orchestrator needs to make nuanced agent assignment decisions based on agent capabilities.

---

## Implementation Details

### Backend Changes

#### File: `src/giljo_mcp/mission_planner.py`

Add helper method to fetch full agent templates:

```python
async def _get_full_agent_templates(
    self,
    tenant_key: str,
    session: AsyncSession
) -> List[Dict[str, Any]]:
    """
    Fetch complete agent templates including full content.

    Used when depth_config["agent_templates"] = "full".
    Returns all template fields for orchestrator analysis.

    Args:
        tenant_key: Tenant isolation key
        session: Database session

    Returns:
        List of complete agent template dicts with fields:
        - name: Template name (e.g., "implementer")
        - role: Agent role (e.g., "implementer")
        - description: Brief description
        - content: Full agent prompt/instructions (2000-3000 tokens)
        - cli_tool: Tool to use (e.g., "claude")
        - background_color: UI color code
        - category: Template category (e.g., "role")
    """
    from giljo_mcp.models import AgentTemplate
    from sqlalchemy import and_, select

    # Fetch enabled agent templates
    result = await session.execute(
        select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            )
        )
    )
    templates = result.scalars().all()

    # Build full template data
    full_templates = []
    for template in templates:
        full_templates.append({
            "name": template.name,
            "role": template.role,
            "description": template.description or "",
            "content": template.content or "",  # Full agent prompt
            "cli_tool": template.cli_tool or "claude",
            "background_color": template.background_color or "#3498DB",
            "category": template.category or "role"
        })

    return full_templates
```

#### File: `src/giljo_mcp/tools/orchestration.py`

Update `get_orchestrator_instructions()` to check depth config:

```python
# Inside get_orchestrator_instructions() function

# Get depth config (existing code)
depth_config = metadata.get("depth_config", {})

# Check agent templates depth setting (NEW CODE)
agent_template_depth = depth_config.get("agent_templates", "type_only")

if agent_template_depth == "full":
    # Full mode: Get complete agent templates with content
    from giljo_mcp.mission_planner import MissionPlanner
    planner = MissionPlanner(db_manager)

    # Fetch full templates (includes content field)
    agent_templates = await planner._get_full_agent_templates(
        tenant_key=tenant_key,
        session=session
    )

    logger.info(
        f"[AGENT_TEMPLATES] Full mode: {len(agent_templates)} templates with complete content",
        extra={"orchestrator_id": orchestrator_id, "mode": "full"}
    )
else:
    # Type Only mode: Minimal metadata (existing behavior)
    result = await session.execute(
        select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            )
        )
    )
    templates = result.scalars().all()

    agent_templates = [
        {
            "name": t.name,
            "role": t.role,
            "description": t.description[:200] if t.description else ""
        }
        for t in templates
    ]

    logger.info(
        f"[AGENT_TEMPLATES] Type Only mode: {len(agent_templates)} templates with minimal metadata",
        extra={"orchestrator_id": orchestrator_id, "mode": "type_only"}
    )

# Add to response
response["agent_templates"] = agent_templates
```

### Frontend Changes

#### File: `frontend/src/components/settings/ContextPriorityConfig.vue`

Update `formatOptions()` method (line ~323):

```javascript
function formatOptions(context: { key: string; options?: (string | number)[] }) {
  // ... existing vision_documents handling ...

  // Agent Templates depth toggle (NEW CODE)
  if (context.key === 'agent_templates') {
    return [
      {
        title: 'Type Only (~250 tokens for 5 agents)',
        value: 'type_only',
        subtitle: 'Name, role, description only - token efficient'
      },
      {
        title: 'Full (~12,500 tokens for 5 agents)',
        value: 'full',
        subtitle: 'Complete agent prompts - for nuanced task assignment'
      }
    ]
  }

  // ... existing memory_360 and git_history handling ...
}
```

**Verify existing code** (should already be present):
- Line ~203: `agent_templates` context definition with `options: ['type_only', 'full']`
- Line ~258: Default config `agent_templates: { enabled: true, priority: 2, depth: 'type_only' }`
- Line ~305-307: `updateDepth()` handles agent_templates
- Line ~317-318: `getDepthValue()` returns agent_templates depth
- Line ~426-428: API load maps `agent_template_detail` to `agent_templates.depth`
- Line ~460: API save sends `agent_template_detail` field

---

## TDD Test Suite

### Test Principles (MUST FOLLOW)

1. **Write the test FIRST** (it should fail initially)
2. **Implement minimal code** to make test pass
3. **Refactor** if needed while keeping tests green
4. **Test BEHAVIOR**, not implementation details
5. **Use descriptive test names** like `test_type_only_mode_returns_minimal_agent_data`
6. **Avoid testing internal implementation** - focus on observable outcomes

### Backend Unit Tests

#### File: `tests/services/test_mission_planner.py`

```python
"""
TDD Test Suite for Agent Templates Depth Toggle (Handover 0347d)

Test coverage:
- Helper method returns full agent template data
- Type Only mode returns minimal metadata
- Full mode returns complete agent prompts
- Token estimation accurate for both modes
- Invalid depth values default to type_only
- Backwards compatibility with missing config
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_get_full_agent_templates_returns_complete_data(db_manager, sample_tenant):
    """
    REQUIREMENT: _get_full_agent_templates() returns complete agent data

    BEHAVIOR TESTED:
    - Fetches enabled agent templates for tenant
    - Returns all required fields (name, role, description, content, cli_tool, etc.)
    - Content field contains full agent prompt (2000-3000 tokens)

    SUCCESS CRITERIA:
    - All enabled templates returned
    - Each template has 7 required fields
    - content field is non-empty and substantial (>1000 chars)
    """
    # Arrange: Create test agent templates with full content
    from giljo_mcp.mission_planner import MissionPlanner
    from giljo_mcp.models import AgentTemplate

    async with db_manager.get_session_async() as session:
        # Create sample agent template with full content
        template = AgentTemplate(
            name="implementer",
            role="implementer",
            description="Implementation specialist",
            content="## IMPLEMENTER AGENT\n\n" + ("X" * 2000),  # Simulate full prompt
            cli_tool="claude",
            background_color="#3498DB",
            category="role",
            tenant_key=sample_tenant,
            is_active=True
        )
        session.add(template)
        await session.commit()

        # Act: Call helper method
        planner = MissionPlanner(db_manager)
        result = await planner._get_full_agent_templates(
            tenant_key=sample_tenant,
            session=session
        )

        # Assert: Verify complete data returned
        assert len(result) == 1
        assert result[0]["name"] == "implementer"
        assert result[0]["role"] == "implementer"
        assert result[0]["description"] == "Implementation specialist"
        assert len(result[0]["content"]) > 1000  # Full prompt content
        assert result[0]["cli_tool"] == "claude"
        assert result[0]["background_color"] == "#3498DB"
        assert result[0]["category"] == "role"


@pytest.mark.asyncio
async def test_type_only_mode_returns_minimal_agent_data(db_manager, sample_orchestrator):
    """
    REQUIREMENT: Type Only mode returns minimal metadata (~50 tokens/agent)

    BEHAVIOR TESTED:
    - depth_config["agent_templates"] = "type_only" (or missing)
    - Returns only name, role, description (truncated to 200 chars)
    - Does NOT return content, cli_tool, background_color, category

    SUCCESS CRITERIA:
    - Response has agent_templates array
    - Each agent has exactly 3 fields: name, role, description
    - Token estimate ~50/agent (150-250 chars per agent)
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Arrange: Set depth config to type_only
    sample_orchestrator.job_metadata = {
        "depth_config": {"agent_templates": "type_only"}
    }

    # Act: Call get_orchestrator_instructions
    result = await get_orchestrator_instructions(
        orchestrator_id=sample_orchestrator.job_id,
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    # Assert: Verify minimal metadata only
    assert "agent_templates" in result
    agents = result["agent_templates"]

    for agent in agents:
        # Should have exactly 3 fields
        assert set(agent.keys()) == {"name", "role", "description"}

        # Description truncated to 200 chars
        assert len(agent["description"]) <= 200

        # Should NOT have full content fields
        assert "content" not in agent
        assert "cli_tool" not in agent
        assert "background_color" not in agent
        assert "category" not in agent


@pytest.mark.asyncio
async def test_full_mode_returns_complete_agent_prompts(db_manager, sample_orchestrator):
    """
    REQUIREMENT: Full mode returns complete agent data (~2000-3000 tokens/agent)

    BEHAVIOR TESTED:
    - depth_config["agent_templates"] = "full"
    - Returns all 7 fields including full content
    - Content field contains complete agent prompt

    SUCCESS CRITERIA:
    - Response has agent_templates array
    - Each agent has 7 fields: name, role, description, content, cli_tool, background_color, category
    - content field length >1000 chars (indicates full prompt)
    - Token estimate ~2000-3000/agent
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Arrange: Set depth config to full
    sample_orchestrator.job_metadata = {
        "depth_config": {"agent_templates": "full"}
    }

    # Act: Call get_orchestrator_instructions
    result = await get_orchestrator_instructions(
        orchestrator_id=sample_orchestrator.job_id,
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    # Assert: Verify complete data returned
    assert "agent_templates" in result
    agents = result["agent_templates"]

    for agent in agents:
        # Should have all 7 fields
        assert "name" in agent
        assert "role" in agent
        assert "description" in agent
        assert "content" in agent
        assert "cli_tool" in agent
        assert "background_color" in agent
        assert "category" in agent

        # Content should be substantial (full prompt)
        assert len(agent["content"]) > 1000


@pytest.mark.asyncio
async def test_token_estimation_accurate_for_both_modes(db_manager, sample_orchestrator):
    """
    REQUIREMENT: Token estimates match specification

    BEHAVIOR TESTED:
    - Type Only: ~50 tokens/agent (5 agents = ~250 tokens)
    - Full: ~2000-3000 tokens/agent (5 agents = ~12,500 tokens)

    SUCCESS CRITERIA:
    - Type Only mode: agent_templates section ~200-300 tokens total
    - Full mode: agent_templates section ~10,000-15,000 tokens total
    - Delta matches specification table
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Act: Get Type Only mode token estimate
    sample_orchestrator.job_metadata = {
        "depth_config": {"agent_templates": "type_only"}
    }

    result_type_only = await get_orchestrator_instructions(
        orchestrator_id=sample_orchestrator.job_id,
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    # Estimate tokens for agent_templates array (1 token ≈ 4 chars)
    import json
    type_only_json = json.dumps(result_type_only["agent_templates"])
    type_only_tokens = len(type_only_json) // 4

    # Act: Get Full mode token estimate
    sample_orchestrator.job_metadata = {
        "depth_config": {"agent_templates": "full"}
    }

    result_full = await get_orchestrator_instructions(
        orchestrator_id=sample_orchestrator.job_id,
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    full_json = json.dumps(result_full["agent_templates"])
    full_tokens = len(full_json) // 4

    # Assert: Token estimates within expected ranges
    # Assuming 5 agents in test data
    assert 200 <= type_only_tokens <= 400, f"Type Only tokens: {type_only_tokens}"
    assert 10000 <= full_tokens <= 20000, f"Full mode tokens: {full_tokens}"

    # Delta should be significant (>7000 tokens for 5 agents)
    delta = full_tokens - type_only_tokens
    assert delta > 7000, f"Token delta too small: {delta}"


@pytest.mark.asyncio
async def test_invalid_depth_values_default_to_type_only(db_manager, sample_orchestrator):
    """
    REQUIREMENT: Invalid depth values gracefully default to type_only

    BEHAVIOR TESTED:
    - depth_config["agent_templates"] = "invalid_value"
    - depth_config["agent_templates"] = null
    - depth_config missing entirely
    - All cases default to type_only behavior

    SUCCESS CRITERIA:
    - No errors raised
    - Returns minimal metadata (type_only mode)
    - Logs warning about invalid value
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    invalid_values = ["invalid", None, "", "moderate", "standard"]

    for invalid_value in invalid_values:
        # Arrange: Set invalid depth config
        sample_orchestrator.job_metadata = {
            "depth_config": {"agent_templates": invalid_value}
        }

        # Act: Call get_orchestrator_instructions
        result = await get_orchestrator_instructions(
            orchestrator_id=sample_orchestrator.job_id,
            tenant_key=sample_orchestrator.tenant_key,
            db_manager=db_manager
        )

        # Assert: Should not error, should default to type_only
        assert "agent_templates" in result
        agents = result["agent_templates"]

        # Verify minimal metadata (type_only behavior)
        if len(agents) > 0:
            assert set(agents[0].keys()) == {"name", "role", "description"}


@pytest.mark.asyncio
async def test_backwards_compatibility_missing_config(db_manager, sample_orchestrator):
    """
    REQUIREMENT: Missing depth_config gracefully defaults to type_only

    BEHAVIOR TESTED:
    - job_metadata missing depth_config entirely
    - Existing orchestrators created before this feature

    SUCCESS CRITERIA:
    - No errors raised
    - Defaults to type_only mode
    - Returns minimal metadata
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Arrange: No depth_config (old orchestrator)
    sample_orchestrator.job_metadata = {}

    # Act: Call get_orchestrator_instructions
    result = await get_orchestrator_instructions(
        orchestrator_id=sample_orchestrator.job_id,
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    # Assert: Should default to type_only
    assert "agent_templates" in result
    agents = result["agent_templates"]

    if len(agents) > 0:
        # Minimal metadata only
        assert set(agents[0].keys()) == {"name", "role", "description"}
```

### Frontend Unit Tests

#### File: `frontend/src/components/settings/ContextPriorityConfig.spec.js`

```javascript
/**
 * TDD Test Suite for Agent Templates Depth Toggle UI (Handover 0347d)
 *
 * Test Coverage:
 * - Agent templates toggle has exactly 2 options (type_only, full)
 * - Options have correct values and labels
 * - Default value is 'type_only'
 * - Token estimates displayed correctly
 * - Toggle saves to backend via depth_config API
 * - Help text explains when to use each mode
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('ContextPriorityConfig - Agent Templates Depth Toggle', () => {
  let contexts
  let config

  beforeEach(() => {
    contexts = [
      {
        key: 'agent_templates',
        label: 'Agent Templates',
        options: ['type_only', 'full'],
        helpText: 'Type Only = Name/Version | Full = With descriptions'
      }
    ]

    config = {
      agent_templates: { enabled: true, priority: 2, depth: 'type_only' }
    }
  })

  /**
   * Test 1: Agent templates toggle has exactly 2 options
   *
   * REQUIREMENT: Only 2 depth options (type_only, full)
   * BEHAVIOR: formatOptions() returns array with 2 items
   */
  it('test_agent_templates_toggle_has_two_options', () => {
    // Arrange: Mock formatOptions method
    const formatOptions = (context) => {
      if (context.key === 'agent_templates') {
        return [
          {
            title: 'Type Only (~250 tokens for 5 agents)',
            value: 'type_only',
            subtitle: 'Name, role, description only - token efficient'
          },
          {
            title: 'Full (~12,500 tokens for 5 agents)',
            value: 'full',
            subtitle: 'Complete agent prompts - for nuanced task assignment'
          }
        ]
      }
      return []
    }

    const agentContext = contexts.find(c => c.key === 'agent_templates')

    // Act: Get formatted options
    const options = formatOptions(agentContext)

    // Assert: Exactly 2 options
    expect(options).toHaveLength(2)
    expect(options[0].value).toBe('type_only')
    expect(options[1].value).toBe('full')
  })

  /**
   * Test 2: Type Only option shows correct token estimate
   *
   * REQUIREMENT: Type Only label must include "~250 tokens for 5 agents"
   * BEHAVIOR: First option has correct title and subtitle
   */
  it('test_type_only_option_shows_correct_token_estimate', () => {
    // Arrange: formatOptions for agent_templates
    const formatOptions = (context) => {
      if (context.key === 'agent_templates') {
        return [
          {
            title: 'Type Only (~250 tokens for 5 agents)',
            value: 'type_only',
            subtitle: 'Name, role, description only - token efficient'
          },
          {
            title: 'Full (~12,500 tokens for 5 agents)',
            value: 'full',
            subtitle: 'Complete agent prompts - for nuanced task assignment'
          }
        ]
      }
      return []
    }

    const agentContext = contexts.find(c => c.key === 'agent_templates')
    const options = formatOptions(agentContext)

    // Act: Find type_only option
    const typeOnlyOption = options.find(opt => opt.value === 'type_only')

    // Assert: Correct label and subtitle
    expect(typeOnlyOption).toBeDefined()
    expect(typeOnlyOption.title).toContain('Type Only')
    expect(typeOnlyOption.title).toContain('~250 tokens')
    expect(typeOnlyOption.subtitle).toContain('token efficient')
  })

  /**
   * Test 3: Full option shows correct token estimate
   *
   * REQUIREMENT: Full label must include "~12,500 tokens for 5 agents"
   * BEHAVIOR: Second option has correct title and subtitle
   */
  it('test_full_option_shows_correct_token_estimate', () => {
    // Arrange: formatOptions for agent_templates
    const formatOptions = (context) => {
      if (context.key === 'agent_templates') {
        return [
          {
            title: 'Type Only (~250 tokens for 5 agents)',
            value: 'type_only',
            subtitle: 'Name, role, description only - token efficient'
          },
          {
            title: 'Full (~12,500 tokens for 5 agents)',
            value: 'full',
            subtitle: 'Complete agent prompts - for nuanced task assignment'
          }
        ]
      }
      return []
    }

    const agentContext = contexts.find(c => c.key === 'agent_templates')
    const options = formatOptions(agentContext)

    // Act: Find full option
    const fullOption = options.find(opt => opt.value === 'full')

    // Assert: Correct label and subtitle
    expect(fullOption).toBeDefined()
    expect(fullOption.title).toContain('Full')
    expect(fullOption.title).toContain('~12,500 tokens')
    expect(fullOption.subtitle).toContain('nuanced task assignment')
  })

  /**
   * Test 4: Default value is 'type_only'
   *
   * REQUIREMENT: Default agent_templates depth is 'type_only' (token efficient)
   * BEHAVIOR: Initial config has depth = 'type_only'
   */
  it('test_default_value_is_type_only', () => {
    // Assert: Default config has type_only
    expect(config.agent_templates.depth).toBe('type_only')
    expect(config.agent_templates.depth).not.toBe('full')
  })

  /**
   * Test 5: Agent template depth saves to backend
   *
   * REQUIREMENT: PUT /api/v1/users/me/context/depth includes agent_template_detail
   * BEHAVIOR: API payload includes agent_templates depth value
   */
  it('test_agent_template_depth_saves_to_backend', () => {
    // Arrange: Create API payload
    const apiPayload = {
      depth_config: {
        memory_last_n_projects: config.memory_360?.count || 3,
        git_commits: config.git_history?.count || 25,
        vision_documents: config.vision_documents?.depth || 'medium',
        agent_template_detail: config.agent_templates?.depth || 'type_only'
      }
    }

    // Assert: agent_template_detail in payload
    expect(apiPayload.depth_config).toHaveProperty('agent_template_detail')
    expect(apiPayload.depth_config.agent_template_detail).toBe('type_only')
  })

  /**
   * Test 6: Changing depth updates config
   *
   * REQUIREMENT: User can toggle between type_only and full modes
   * BEHAVIOR: updateDepth() changes config.agent_templates.depth
   */
  it('test_changing_depth_updates_config', () => {
    // Arrange: Initial state
    expect(config.agent_templates.depth).toBe('type_only')

    // Act: Change to full
    config.agent_templates.depth = 'full'

    // Assert: Config updated
    expect(config.agent_templates.depth).toBe('full')

    // Act: Change back to type_only
    config.agent_templates.depth = 'type_only'

    // Assert: Config updated
    expect(config.agent_templates.depth).toBe('type_only')
  })
})
```

### Integration Test

#### File: `tests/integration/test_agent_template_depth_e2e.py`

```python
"""
E2E Integration Test for Agent Templates Depth Toggle (Handover 0347d)

Tests complete workflow:
1. User changes depth setting via API
2. Orchestrator fetches instructions
3. Response includes correct agent template data based on depth
4. Token counts match specification
"""

import pytest

@pytest.mark.asyncio
async def test_e2e_agent_template_depth_toggle_workflow(
    client,
    db_manager,
    sample_user,
    sample_product,
    sample_project
):
    """
    REQUIREMENT: Complete workflow from UI toggle to orchestrator response

    WORKFLOW:
    1. Create orchestrator job
    2. Set agent_templates depth to "type_only" via API
    3. Call get_orchestrator_instructions
    4. Verify minimal agent data returned
    5. Set agent_templates depth to "full" via API
    6. Call get_orchestrator_instructions again
    7. Verify complete agent data returned
    8. Measure token count difference

    SUCCESS CRITERIA:
    - Type Only mode: ~250 tokens for agent_templates
    - Full mode: ~12,500 tokens for agent_templates
    - Delta matches specification (>7,000 tokens)
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions
    from giljo_mcp.models import MCPAgentJob
    import json

    # Step 1: Create orchestrator job
    async with db_manager.get_session_async() as session:
        orchestrator = MCPAgentJob(
            job_id="test-orch-001",
            agent_type="orchestrator",
            agent_name="Test Orchestrator",
            project_id=sample_project.id,
            tenant_key=sample_user.tenant_key,
            status="pending",
            job_metadata={
                "user_id": str(sample_user.id),
                "depth_config": {"agent_templates": "type_only"}
            }
        )
        session.add(orchestrator)
        await session.commit()

    # Step 2: Set depth to "type_only" (already set in metadata)

    # Step 3: Call get_orchestrator_instructions
    result_type_only = await get_orchestrator_instructions(
        orchestrator_id="test-orch-001",
        tenant_key=sample_user.tenant_key,
        db_manager=db_manager
    )

    # Step 4: Verify minimal agent data
    assert "agent_templates" in result_type_only
    agents_type_only = result_type_only["agent_templates"]

    for agent in agents_type_only:
        assert set(agent.keys()) == {"name", "role", "description"}
        assert "content" not in agent

    # Measure token count for type_only
    type_only_json = json.dumps(agents_type_only)
    type_only_tokens = len(type_only_json) // 4

    # Step 5: Update depth to "full"
    async with db_manager.get_session_async() as session:
        result = await session.execute(
            select(MCPAgentJob).where(MCPAgentJob.job_id == "test-orch-001")
        )
        orch = result.scalar_one()
        orch.job_metadata["depth_config"]["agent_templates"] = "full"
        await session.commit()

    # Step 6: Call get_orchestrator_instructions again
    result_full = await get_orchestrator_instructions(
        orchestrator_id="test-orch-001",
        tenant_key=sample_user.tenant_key,
        db_manager=db_manager
    )

    # Step 7: Verify complete agent data
    assert "agent_templates" in result_full
    agents_full = result_full["agent_templates"]

    for agent in agents_full:
        # Must have all 7 fields
        assert "name" in agent
        assert "role" in agent
        assert "description" in agent
        assert "content" in agent  # Full prompt
        assert "cli_tool" in agent
        assert "background_color" in agent
        assert "category" in agent

        # Content must be substantial
        assert len(agent["content"]) > 1000

    # Step 8: Measure token count difference
    full_json = json.dumps(agents_full)
    full_tokens = len(full_json) // 4

    # Assert: Token counts match specification
    assert 200 <= type_only_tokens <= 400, f"Type Only: {type_only_tokens}"
    assert 10000 <= full_tokens <= 20000, f"Full: {full_tokens}"

    delta = full_tokens - type_only_tokens
    assert delta > 7000, f"Delta too small: {delta}"

    print(f"✅ Type Only: {type_only_tokens} tokens")
    print(f"✅ Full: {full_tokens} tokens")
    print(f"✅ Delta: {delta} tokens")
```

---

## Files to Modify

### Backend Files
| File | Change | Lines Affected |
|------|--------|----------------|
| `src/giljo_mcp/mission_planner.py` | Add `_get_full_agent_templates()` helper | +40 lines |
| `src/giljo_mcp/tools/orchestration.py` | Check depth config, conditionally fetch full templates | ~30 lines |
| `tests/services/test_mission_planner.py` | Add 6 unit tests | +200 lines |
| `tests/integration/test_agent_template_depth_e2e.py` | Add E2E test | +100 lines |

### Frontend Files
| File | Change | Lines Affected |
|------|--------|----------------|
| `frontend/src/components/settings/ContextPriorityConfig.vue` | Update `formatOptions()` for agent_templates | ~15 lines |
| `frontend/src/components/settings/ContextPriorityConfig.spec.js` | Add 6 unit tests | +150 lines |

**Note**: Most frontend infrastructure already exists (context definition, API integration, depth handling). Only `formatOptions()` needs updating for better labels.

---

## Testing Strategy

### Phase 1: Unit Tests (TDD)
1. **Write test first**: `test_get_full_agent_templates_returns_complete_data()`
2. **Run test**: Should FAIL (method doesn't exist yet)
3. **Implement**: `_get_full_agent_templates()` method
4. **Run test**: Should PASS
5. **Repeat** for all 6 backend unit tests

### Phase 2: Integration Test (TDD)
1. **Write test first**: `test_e2e_agent_template_depth_toggle_workflow()`
2. **Run test**: Should FAIL (depth config not checked)
3. **Implement**: Depth config checking in `get_orchestrator_instructions()`
4. **Run test**: Should PASS

### Phase 3: Frontend Tests (TDD)
1. **Write test first**: `test_agent_templates_toggle_has_two_options()`
2. **Run test**: Should FAIL (formatOptions() returns generic labels)
3. **Implement**: Update `formatOptions()` for agent_templates
4. **Run test**: Should PASS
5. **Repeat** for all 6 frontend unit tests

### Phase 4: Manual Testing
1. Open My Settings → Context → Depth Configuration
2. Find "Agent Templates" row
3. Verify toggle shows "Type Only (~250 tokens)" and "Full (~12,500 tokens)"
4. Switch to "Full" mode
5. Create new project and stage orchestrator
6. Verify `get_orchestrator_instructions()` response includes full agent content
7. Measure token count (should be ~12,500 for 5 agents)
8. Switch back to "Type Only" mode
9. Stage new orchestrator
10. Verify response has minimal metadata (~250 tokens for 5 agents)

---

## Rollback Plan

### If Implementation Fails
1. **Revert backend changes**: Remove `_get_full_agent_templates()` method
2. **Revert orchestration.py**: Remove depth config checking
3. **Revert frontend**: Restore generic `formatOptions()` labels
4. **Database**: No migration required (uses existing `depth_config` JSONB)
5. **Fallback behavior**: All orchestrators receive Type Only mode (existing behavior)

### Rollback Command
```bash
git revert <commit-hash>
```

### Verification After Rollback
```bash
# Run tests to ensure no breakage
pytest tests/services/test_mission_planner.py -v
pytest tests/integration/ -v

# Verify API still works
curl -X GET http://localhost:7272/api/v1/users/me/context/depth \
  -H "Authorization: Bearer $TOKEN"
```

---

## Documentation Updates

After implementation, update:

1. **CLAUDE.md** (Context Management v2.0 section):
   - Add agent_templates depth dimension
   - Update token estimates table

2. **docs/ORCHESTRATOR.md**:
   - Document when to use Type Only vs Full mode
   - Add token budget impact examples

3. **User Guide** (`docs/user_guides/context_configuration.md`):
   - Add screenshot of agent_templates toggle
   - Explain use cases for each mode

---

## Related Handovers

- **0347a**: YAML Context Builder (prerequisite - data structure)
- **0347b**: MissionPlanner YAML Refactor (dependency - MUST use YAML)
- **0347c**: Response Fields Enhancement (parallel work)
- **0347e**: Vision Document 4-Level Depth (similar pattern)
- **0347f**: Integration & E2E Testing (final validation)

---

## Notes

### Design Decisions

1. **Why "Type Only" as default?**
   - Token efficiency (85% savings: ~250 vs ~12,500 tokens)
   - Most orchestrators only need agent names for spawning
   - User can opt-in to Full mode when needed

2. **Why not intermediate mode (e.g., "Standard")?**
   - Binary choice is clearer: minimal vs complete
   - Reduces decision paralysis
   - Token costs are dramatically different (250 vs 12,500)
   - Can add intermediate mode later if user feedback requests it

3. **Why include subtitle in options?**
   - Explains token cost AND use case
   - Helps users make informed decision
   - Follows pattern from vision_documents toggle

### Edge Cases Handled

- ✅ Invalid depth values → default to type_only
- ✅ Missing depth_config → default to type_only
- ✅ Backwards compatibility with old orchestrators
- ✅ Inactive agent templates filtered out
- ✅ Empty agent template list (no crash)

### Future Enhancements

- **Handover 0347g**: Add "Standard" mode (name + description + first 500 chars of content)
- **Handover 0347h**: Agent template usage analytics (track which mode users prefer)
- **Handover 0347i**: Smart recommendations (suggest Full mode for complex projects)

---

**End of Handover 0347d**
