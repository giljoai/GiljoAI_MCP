# Handover 0357: Agent Template Context Loading Fix

**Date**: 2025-12-19
**Status**: READY FOR IMPLEMENTATION
**Priority**: High
**Type**: Bug Fix - Context Management
**Estimated Effort**: 2-3 hours

---

## Context

During alpha trial testing, a critical issue was discovered where user settings for agent template depth were not being properly respected. The orchestrator was receiving only minimal agent template information (name/role/description summaries) even when the user had explicitly configured "full" depth in their settings.

This issue affects the orchestrator's ability to make nuanced task assignments, as it lacks access to complete agent prompts that describe each agent's capabilities, methodologies, and specialized focus areas.

**Related Systems:**
- Context prioritization and orchestration (Handover 0281, 0283)
- Agent template depth configuration (Handover 0347d)
- Mission planner context building (Handover 0347b)
- User settings persistence (My Settings → Context → Depth Configuration)

---

## Problem Statement

### Issue #1: Agent Templates Full Context Not Loading

**User Report:**
> User had "full" depth toggled in My Settings → Context → Depth Configuration → Agent Templates, but the orchestrator only received name/role/description summaries (~50 tokens/agent), not complete prompts (~2500 tokens/agent).

**Expected Behavior:**
When `depth_config["agent_templates"] = "full"`, the orchestrator should receive:
```json
{
  "agent_templates": {
    "depth": "full",
    "detail_level": "complete_prompts",
    "templates": [
      {
        "name": "backend-integration-tester",
        "role": "Backend Integration Tester",
        "description": "Specialist in backend integration testing...",
        "content": "# Backend Integration Tester Agent\n\n...",  // FULL PROMPT
        "cli_tool": "claude-code",
        "background_color": "#4CAF50",
        "category": "testing"
      }
    ],
    "instruction": "All agent templates included with full prompts for nuanced task assignment.",
    "token_impact": "~12500 tokens (full prompts)"
  }
}
```

**Actual Behavior:**
Instead, the orchestrator receives:
```json
{
  "agent_templates": {
    "depth": "type_only",
    "detail_level": "minimal_metadata",
    "templates": [
      {
        "name": "backend-integration-tester",
        "role": "Backend Integration Tester",
        "description": "Specialist in backend integration testing..." // TRUNCATED at 200 chars
      }
    ],
    "fetch_tool": "get_available_agents(tenant_key, active_only=True)",
    "instruction": "Agent templates listed with basic metadata. Call get_available_agents() for complete details if needed.",
    "token_impact": "~250 tokens (type only)"
  }
}
```

---

## Investigation Findings

### Code Flow Analysis

**Entry Point**: `get_orchestrator_instructions(orchestrator_id, tenant_key)`
**File**: `F:\GiljoAI_MCP\src\giljo_mcp\tools\orchestration.py` (lines 1422-1747)

**Flow:**
1. **User Config Fetch** (lines 1605-1620):
   ```python
   user_config = await _get_user_config(user_id, tenant_key, session)
   field_priorities = user_config["field_priorities"]
   depth_config = user_config["depth_config"]
   ```
   - Fetches user's `field_priority_config` and `depth_config` from database
   - Normalizes UI keys to internal keys (e.g., `memory_last_n_projects` → `memory_360`)
   - Falls back to `DEFAULT_DEPTH_CONFIG` if user has no custom config

2. **Mission Building** (lines 1646-1654):
   ```python
   condensed_mission = await planner._build_context_with_priorities(
       product=product,
       project=project,
       field_priorities=field_priorities,
       depth_config=depth_config,
       user_id=user_id,
       include_serena=include_serena,
   )
   ```
   - Passes `depth_config` to mission planner

3. **Agent Template Processing** (mission_planner.py lines 1913-1977):
   ```python
   agent_templates_priority = effective_priorities.get("agent_templates", 2)
   if agent_templates_priority in [1, 2, 3]:
       agent_depth = depth_config.get("agent_templates", "type_only")  # BUG HERE

       async with self.db_manager.get_session_async() as session:
           full_templates = await self._get_full_agent_templates(product.tenant_key, session)

       if agent_depth == "full":
           # Full mode: Complete agent templates with prompts
           agent_content = {
               "depth": "full",
               "templates": full_templates,  # Contains content field
               ...
           }
       else:
           # Type-only mode: Minimal metadata only
           minimal_templates = [truncate description to 200 chars]
           agent_content = {
               "depth": "type_only",
               "templates": minimal_templates,  # NO content field
               ...
           }
   ```

### Root Cause Analysis

**PRIMARY ISSUE**: The code flow is **CORRECT** but the depth configuration is not being properly saved or retrieved from the user settings.

**Evidence from code:**
- `DEFAULT_DEPTH_CONFIG` sets `"agent_templates": "type_only"` (line 124)
- User config fetch at lines 1605-1620 falls back to defaults if `user.depth_config` is `None`
- The mission planner correctly checks `agent_depth == "full"` and branches accordingly

**Hypothesis:**
1. **User settings not persisting**: The "full" toggle in My Settings → Context → Depth Configuration may not be saving to the database
2. **Key mismatch**: The UI might be using a different key than `"agent_templates"` (e.g., `"agent_template_depth"`)
3. **Default override**: User config exists but doesn't include `agent_templates` key, so it falls back to default `"type_only"`

### Key Code Locations

**Configuration Defaults:**
```python
# orchestration.py lines 121-126
DEFAULT_DEPTH_CONFIG = {
    "memory_360": 5,
    "git_history": 20,
    "agent_templates": "type_only",  # ← Default
    "vision_documents": "light",
}
```

**User Config Retrieval:**
```python
# orchestration.py lines 178-208
raw_depth_config = user.depth_config
if raw_depth_config is not None:
    # Key mapping: UI/database keys → internal code keys
    key_mapping = {
        "memory_last_n_projects": "memory_360",
        "git_commits": "git_history",
        "agent_templates": "agent_templates",  # ← Direct mapping
        "vision_documents": "vision_documents",
    }
    ...
else:
    depth_config = DEFAULT_DEPTH_CONFIG.copy()  # ← Falls back to "type_only"
```

**Agent Template Processing:**
```python
# mission_planner.py lines 1918-1975
agent_depth = depth_config.get("agent_templates", "type_only")

if agent_depth == "full":
    # Returns full templates with content field
    agent_content = {"templates": full_templates, ...}
else:
    # Returns truncated templates WITHOUT content field
    minimal_templates = [truncate to 200 chars]
    agent_content = {"templates": minimal_templates, ...}
```

---

## Implementation Plan

### Step 1: Verify User Settings Persistence

**Goal**: Confirm whether the "full" toggle in UI is saving to database

**Actions:**
1. Check the Settings API endpoint that handles depth config updates
   - File: `F:\GiljoAI_MCP\api\endpoints\settings.py`
   - Look for `PUT /api/v1/settings/context/depth` or similar

2. Verify the frontend payload when user toggles "full":
   - File: `F:\GiljoAI_MCP\frontend\src\components\settings\DepthConfiguration.vue` (or similar)
   - Check if it sends `{"agent_templates": "full"}` or a different key

3. Query database to confirm saved value:
   ```sql
   SELECT id, username, depth_config FROM users WHERE tenant_key = '<tenant>';
   ```
   - Check if `depth_config` column contains `{"agent_templates": "full"}`

**Possible Findings:**
- **If NULL**: Settings UI is not saving properly → fix UI/API
- **If different key**: Key mismatch → add mapping to `key_mapping` dict
- **If "type_only"**: UI is reverting to default → fix UI state management

### Step 2: Add Diagnostic Logging

**Goal**: Add detailed logging to trace depth config flow

**Changes:**
```python
# orchestration.py line 1620 (after user config fetch)
logger.info(
    f"[DEPTH_CONFIG] User depth configuration retrieved",
    extra={
        "user_id": user_id,
        "tenant_key": tenant_key,
        "raw_depth_config": user.depth_config,
        "normalized_depth_config": depth_config,
        "agent_templates_depth": depth_config.get("agent_templates"),
        "has_custom_config": user.depth_config is not None,
    },
)

# mission_planner.py line 1918 (before agent template processing)
logger.info(
    f"[AGENT_TEMPLATES] Processing with depth configuration",
    extra={
        "agent_templates_priority": agent_templates_priority,
        "agent_depth": agent_depth,
        "depth_config_input": depth_config,
        "effective_depth": agent_depth,
    },
)
```

**Benefits:**
- Traces exact depth config values at each stage
- Identifies where "full" is being lost
- Provides audit trail for debugging

### Step 3: Fix Root Cause (Based on Findings)

**Scenario A: UI Not Saving**
```typescript
// frontend/src/components/settings/DepthConfiguration.vue
const saveDepthConfig = async () => {
  const payload = {
    agent_templates: agentTemplatesDepth.value,  // Ensure this uses correct key
    vision_documents: visionDocumentsDepth.value,
    memory_last_n_projects: memoryDepth.value,
    git_commits: gitHistoryDepth.value,
  };

  await api.put('/api/v1/settings/context/depth', payload);

  // VERIFY: Check response confirms save
  console.log('[DEPTH_CONFIG] Saved:', payload);
};
```

**Scenario B: Key Mismatch**
```python
# orchestration.py lines 180-186 (add missing mapping)
key_mapping = {
    "memory_last_n_projects": "memory_360",
    "git_commits": "git_history",
    "agent_templates": "agent_templates",
    "agent_template_depth": "agent_templates",  # Add alternate key
    "vision_documents": "vision_documents",
}
```

**Scenario C: Default Override**
```python
# orchestration.py lines 207-208 (merge instead of replace)
else:
    # Merge user config with defaults (user values take precedence)
    depth_config = DEFAULT_DEPTH_CONFIG.copy()
    if raw_depth_config:
        depth_config.update(raw_depth_config)
```

### Step 4: Add Unit Tests

**Test Coverage:**
```python
# tests/test_agent_template_depth.py

async def test_full_agent_templates_with_user_config():
    """Test that user's 'full' depth config loads complete agent templates."""
    # Arrange
    user = create_user_with_depth_config({"agent_templates": "full"})
    orchestrator = create_orchestrator(project_id, user_id=user.id)

    # Act
    result = await get_orchestrator_instructions(orchestrator.job_id, tenant_key)

    # Assert
    mission_data = json.loads(result["mission"])
    agent_templates = mission_data["important"]["agent_templates"]

    assert agent_templates["depth"] == "full"
    assert agent_templates["detail_level"] == "complete_prompts"
    assert "content" in agent_templates["templates"][0]
    assert len(agent_templates["templates"][0]["content"]) > 1000  # Full prompt


async def test_type_only_agent_templates_with_user_config():
    """Test that user's 'type_only' depth config loads minimal templates."""
    # Arrange
    user = create_user_with_depth_config({"agent_templates": "type_only"})
    orchestrator = create_orchestrator(project_id, user_id=user.id)

    # Act
    result = await get_orchestrator_instructions(orchestrator.job_id, tenant_key)

    # Assert
    mission_data = json.loads(result["mission"])
    agent_templates = mission_data["important"]["agent_templates"]

    assert agent_templates["depth"] == "type_only"
    assert agent_templates["detail_level"] == "minimal_metadata"
    assert "content" not in agent_templates["templates"][0]
    assert len(agent_templates["templates"][0]["description"]) <= 203


async def test_agent_templates_default_when_no_user_config():
    """Test that default 'type_only' is used when user has no depth config."""
    # Arrange
    user = create_user_with_depth_config(None)  # No custom config
    orchestrator = create_orchestrator(project_id, user_id=user.id)

    # Act
    result = await get_orchestrator_instructions(orchestrator.job_id, tenant_key)

    # Assert
    mission_data = json.loads(result["mission"])
    agent_templates = mission_data["important"]["agent_templates"]

    assert agent_templates["depth"] == "type_only"  # Falls back to default
```

### Step 5: Integration Testing

**Manual Test Workflow:**
1. **Configure Settings:**
   - Login to web dashboard
   - Navigate to My Settings → Context → Depth Configuration
   - Set "Agent Templates" to "Full"
   - Save settings
   - Verify database: `SELECT depth_config FROM users WHERE id = '<user_id>';`

2. **Create Orchestrator:**
   - Create new project
   - Launch orchestrator
   - Orchestrator calls `get_orchestrator_instructions()`

3. **Verify Mission Content:**
   - Check orchestrator logs for `[DEPTH_CONFIG]` and `[AGENT_TEMPLATES]` log entries
   - Verify `mission` field contains:
     ```json
     {
       "important": {
         "agent_templates": {
           "depth": "full",
           "templates": [
             {
               "name": "backend-integration-tester",
               "content": "<FULL PROMPT CONTENT HERE>"
             }
           ]
         }
       }
     }
     ```

4. **Test Fallback:**
   - Clear user's `depth_config` in database: `UPDATE users SET depth_config = NULL WHERE id = '<user_id>';`
   - Launch new orchestrator
   - Verify it falls back to `"type_only"` default

---

## Files to Modify

### Primary Files

1. **`F:\GiljoAI_MCP\src\giljo_mcp\tools\orchestration.py`**
   - Lines 178-230: Add diagnostic logging to `_get_user_config()`
   - Verify key mapping at lines 180-186
   - Consider merging user config with defaults (lines 207-208)

2. **`F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py`**
   - Lines 1913-1977: Add diagnostic logging before agent template processing
   - Verify `agent_depth` retrieval at line 1918

3. **`F:\GiljoAI_MCP\api\endpoints\settings.py`**
   - Verify depth config save endpoint
   - Add validation for `agent_templates` key
   - Add logging for depth config updates

4. **`F:\GiljoAI_MCP\frontend\src\components\settings\DepthConfiguration.vue`** (or similar)
   - Verify UI sends correct payload format
   - Ensure "full" toggle maps to `{"agent_templates": "full"}`
   - Add debug logging for save operations

### Test Files

5. **`F:\GiljoAI_MCP\tests\test_agent_template_depth.py`** (NEW)
   - Unit tests for depth config retrieval
   - Integration tests for orchestrator instructions
   - Regression tests for default fallback

6. **`F:\GiljoAI_MCP\tests\test_settings_api.py`**
   - Tests for depth config persistence
   - Validate API endpoint behavior

---

## Testing Strategy

### Unit Tests
- ✅ User config retrieval with `agent_templates: "full"`
- ✅ User config retrieval with `agent_templates: "type_only"`
- ✅ Default fallback when `depth_config` is `None`
- ✅ Key mapping for alternate keys
- ✅ Agent template content inclusion/exclusion based on depth

### Integration Tests
- ✅ Full E2E flow: UI → API → Database → MCP Tool → Mission
- ✅ Orchestrator receives correct depth in mission payload
- ✅ Settings persistence across page reloads
- ✅ Multi-tenant isolation (User A's settings don't affect User B)

### Manual Tests
- ✅ Toggle "full" in UI, verify database update
- ✅ Launch orchestrator, check logs for depth config
- ✅ Verify mission JSON contains full template content
- ✅ Test with fresh user (no custom config) → should get defaults

---

## Success Criteria

### Functional Requirements
1. ✅ When user sets `agent_templates: "full"` in My Settings:
   - Database `users.depth_config` contains `{"agent_templates": "full"}`
   - Orchestrator receives `mission` with full template content
   - Each template includes `content` field with complete prompt (~2500 tokens/agent)

2. ✅ When user sets `agent_templates: "type_only"` in My Settings:
   - Orchestrator receives minimal templates (~50 tokens/agent)
   - Templates include only `name`, `role`, `description` (truncated at 200 chars)

3. ✅ When user has no custom depth config:
   - System falls back to `DEFAULT_DEPTH_CONFIG` (`"type_only"`)
   - Behavior is identical to explicit `"type_only"` setting

### Non-Functional Requirements
4. ✅ Diagnostic logging provides clear audit trail:
   - Log depth config at retrieval (orchestration.py)
   - Log effective depth at processing (mission_planner.py)
   - Include user_id, tenant_key, raw/normalized values

5. ✅ Performance:
   - `"type_only"` mode: ~250 tokens total (5 agents × 50 tokens)
   - `"full"` mode: ~12,500 tokens total (5 agents × 2500 tokens)
   - No unnecessary database queries

### Test Coverage
6. ✅ Unit test coverage >80% for:
   - `_get_user_config()`
   - `_build_context_with_priorities()` (agent template section)
   - Settings API depth config endpoint

7. ✅ Integration tests validate:
   - End-to-end settings flow
   - Orchestrator mission generation
   - Multi-tenant isolation

---

## Rollback Plan

If implementation causes regressions:

1. **Immediate Rollback:**
   ```bash
   git revert <commit-hash>
   git push origin master
   ```

2. **Restore Default Behavior:**
   ```python
   # Temporarily force "type_only" in mission_planner.py line 1918
   agent_depth = "type_only"  # Override user config during investigation
   ```

3. **Database Repair (if needed):**
   ```sql
   -- Reset all users to default depth config
   UPDATE users SET depth_config = NULL WHERE depth_config IS NOT NULL;
   ```

4. **Communication:**
   - Notify users via dashboard banner
   - Provide temporary workaround (use `get_available_agents()` MCP tool)

---

## Related Documentation

- [Handover 0281](handovers/completed/0281_context_depth_dimensions.md) - Context prioritization and orchestration Phase 1
- [Handover 0283](handovers/completed/0283_depth_config_implementation.md) - Depth config implementation
- [Handover 0347d](handovers/completed/0347d_agent_template_depth.md) - Agent template 2-level depth system
- [Handover 0347b](handovers/completed/0347b_json_context_format.md) - JSON context format
- [Context API Documentation](docs/api/context_tools.md) - fetch_context() and depth parameters

---

## Notes

- **Token Impact**: Full agent templates add ~12,500 tokens to orchestrator mission. Ensure context budget (150K tokens) can accommodate this when enabled.
- **Default Rationale**: Default is `"type_only"` to minimize token usage for new users. Power users can opt into "full" mode for nuanced task assignment.
- **Future Enhancement**: Consider adding `"medium"` depth level (name + role + truncated description ~500 chars) for balance between tokens and detail.
