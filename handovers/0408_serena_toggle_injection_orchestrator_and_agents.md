# Handover 0408: Serena MCP Toggle Injection for Orchestrators and Agents

## Summary

Wire the Serena MCP toggle (`config.yaml → features.serena_mcp.use_in_prompts`) into both:
1. **Orchestrators** via `get_orchestrator_instructions()` - for staging/code research
2. **Agents** via `spawn_agent_job()` mission injection - automatic, no reliance on orchestrator memory

Currently, the toggle only affects newly spawned orchestrators (in `spawn_agent_job`). This handover ensures:
- Existing orchestrators see the toggle when fetching instructions
- All spawned agents automatically receive Serena instructions in their mission

---

## Problem Statement

### Current State (Gap Identified in Alpha Testing)

| Location | Serena Toggle Read? | When Used |
|----------|---------------------|-----------|
| `spawn_agent_job()` orchestrator path | Yes | Creating new orchestrator only |
| CLI prompt generation | Yes | Copy-paste prompt for Codex/Gemini |
| `get_orchestrator_instructions()` | **NO** | Existing orchestrator fetching instructions |
| Agent mission (via `spawn_agent_job`) | **NO** | Agents never see Serena instructions |

### User Experience Issue

1. User toggles Serena MCP on/off in UI
2. Existing orchestrator calls `get_orchestrator_instructions()`
3. **No change observed** - toggle not reflected
4. User must spawn new orchestrator to see effect

### Requirements

**A) Orchestrator Staging**: Orchestrators need Serena available during staging to research code for context when building mission plans.

**B) Agent Injection**: Agents should receive Serena instructions automatically - we cannot rely on orchestrators to remember to include them in each agent's mission.

---

## Solution Design

### 1. Orchestrator: Inject into `get_orchestrator_instructions()` Response

**File**: `src/giljo_mcp/tools/orchestration.py`
**Function**: `get_orchestrator_instructions()` (line ~2048)

**Injection Point**: After `condensed_mission` is built (line ~2246), before building response.

**Logic**:
```python
# After line 2246 (condensed_mission built)
# Handover 0408: Read Serena toggle and inject if enabled
include_serena = False
try:
    config_path = Path.cwd() / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
except Exception as e:
    logger.warning(f"[SERENA] Failed to read config: {e}")

if include_serena:
    from giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions
    serena_notice = generate_serena_instructions(enabled=True)
    # Prepend to mission for visibility during staging
    full_mission = serena_notice + "\n\n---\n\n" + full_mission
    logger.info(f"[SERENA] Injected notice into orchestrator instructions for {agent_id}")
```

**Alternative**: Add `serena_mcp_enabled` field to response instead of/in addition to mission injection:
```python
response = {
    # ... existing fields ...
    "integrations": {
        "serena_mcp_enabled": include_serena,
    }
}
```

**Recommendation**: Do BOTH - inject into mission AND add flag to response. This gives orchestrator:
1. Immediate awareness (flag)
2. Persistent reminder in mission text

---

### 2. Agents: Inject into Mission at Spawn Time

**File**: `src/giljo_mcp/services/orchestration_service.py`
**Function**: `spawn_agent_job()` (line ~534)

**Injection Point**: Before storing mission in `AgentJob` (line ~604).

**Logic** (insert around line 598, before AgentJob creation):
```python
# Handover 0408: Inject Serena instructions into agent mission if enabled
include_serena = False
try:
    config_path = Path.cwd() / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
except Exception as e:
    self._logger.warning(f"[SERENA] Failed to read config for agent spawn: {e}")

if include_serena:
    from giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions
    serena_notice = generate_serena_instructions(enabled=True)
    mission = serena_notice + "\n\n---\n\n" + mission
    self._logger.info(f"[SERENA] Injected notice into agent mission for {agent_name}")
```

**Result**: When agent calls `get_agent_mission()`, the mission field already contains Serena instructions.

---

## Files to Modify

| File | Function | Change |
|------|----------|--------|
| `src/giljo_mcp/tools/orchestration.py` | `get_orchestrator_instructions()` | Add Serena toggle check + inject into mission + add `integrations` field |
| `src/giljo_mcp/services/orchestration_service.py` | `spawn_agent_job()` | Add Serena toggle check + inject into mission before DB storage |

---

## Implementation Steps

### Step 1: Update `get_orchestrator_instructions()`

Location: `src/giljo_mcp/tools/orchestration.py` around line 2246

1. Add import at top of function:
   ```python
   from pathlib import Path
   import yaml
   ```

2. After `condensed_mission = await planner._build_context_with_priorities(...)` (line ~2246):
   ```python
   # Handover 0408: Serena MCP injection for orchestrators
   include_serena = False
   try:
       config_path = Path.cwd() / "config.yaml"
       if config_path.exists():
           with open(config_path, encoding="utf-8") as f:
               config_data = yaml.safe_load(f) or {}
           include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
   except Exception as e:
       logger.warning(f"[SERENA] Failed to read config in get_orchestrator_instructions: {e}")

   if include_serena:
       from giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions
       serena_notice = generate_serena_instructions(enabled=True)
       # Prepend to full_mission after it's built (around line 2255)
   ```

3. After `full_mission = f"{agent_job.mission}\n\n---\n\n{json.dumps(condensed_mission, indent=2)}"` (line ~2255):
   ```python
   if include_serena:
       full_mission = serena_notice + "\n\n---\n\n" + full_mission
       logger.info(f"[SERENA] Injected into orchestrator instructions", extra={"agent_id": agent_id})
   ```

4. Add to response dict (around line 2267):
   ```python
   response = {
       # ... existing fields ...
       "integrations": {
           "serena_mcp_enabled": include_serena,
       },
   }
   ```

### Step 2: Update `spawn_agent_job()` in OrchestrationService

Location: `src/giljo_mcp/services/orchestration_service.py` around line 598

1. Add imports at top of file (if not present):
   ```python
   from pathlib import Path
   import yaml
   ```

2. Before `AgentJob` creation (around line 598, after metadata_dict):
   ```python
   # Handover 0408: Inject Serena instructions into agent mission if enabled
   include_serena = False
   try:
       config_path = Path.cwd() / "config.yaml"
       if config_path.exists():
           with open(config_path, encoding="utf-8") as f:
               config_data = yaml.safe_load(f) or {}
           include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
   except Exception as e:
       self._logger.warning(f"[SERENA] Failed to read config for agent spawn: {e}")

   if include_serena:
       from giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions
       serena_notice = generate_serena_instructions(enabled=True)
       mission = serena_notice + "\n\n---\n\n" + mission
       self._logger.info(
           f"[SERENA] Injected notice into agent mission",
           extra={"agent_name": agent_name, "agent_type": agent_type}
       )
   ```

### Step 3: Add Tests

Create test file: `tests/test_serena_toggle_injection.py`

```python
"""Tests for Serena MCP toggle injection (Handover 0408)."""
import pytest
from unittest.mock import patch, MagicMock

class TestSerenaOrchestratorInjection:
    """Test Serena injection into get_orchestrator_instructions."""

    @pytest.mark.asyncio
    async def test_serena_enabled_shows_in_response(self):
        """When Serena enabled, instructions include notice and flag."""
        # Mock config with Serena enabled
        # Call get_orchestrator_instructions
        # Assert response contains integrations.serena_mcp_enabled = True
        # Assert mission contains "Serena MCP Available"
        pass

    @pytest.mark.asyncio
    async def test_serena_disabled_not_in_response(self):
        """When Serena disabled, no notice or flag."""
        # Mock config with Serena disabled
        # Call get_orchestrator_instructions
        # Assert integrations.serena_mcp_enabled = False
        # Assert mission does NOT contain "Serena MCP"
        pass

class TestSerenaAgentInjection:
    """Test Serena injection into spawn_agent_job."""

    @pytest.mark.asyncio
    async def test_agent_mission_includes_serena_when_enabled(self):
        """Spawned agent mission contains Serena notice when enabled."""
        # Mock config with Serena enabled
        # Call spawn_agent_job
        # Fetch AgentJob.mission from DB
        # Assert mission starts with Serena notice
        pass

    @pytest.mark.asyncio
    async def test_agent_mission_clean_when_disabled(self):
        """Spawned agent mission has no Serena when disabled."""
        # Mock config with Serena disabled
        # Call spawn_agent_job
        # Assert mission does NOT contain "Serena MCP"
        pass
```

---

## Verification

### Manual Testing

1. **Orchestrator Test**:
   - Toggle Serena OFF in UI
   - Existing orchestrator calls `get_orchestrator_instructions()`
   - Verify `integrations.serena_mcp_enabled = false`
   - Verify mission does NOT contain "Serena MCP"

2. **Toggle and Refetch**:
   - Toggle Serena ON in UI
   - Same orchestrator calls `get_orchestrator_instructions()` again
   - Verify `integrations.serena_mcp_enabled = true`
   - Verify mission NOW contains "Serena MCP Available"

3. **Agent Test**:
   - Toggle Serena ON
   - Orchestrator spawns agent via `spawn_agent_job()`
   - Agent calls `get_agent_mission()`
   - Verify mission contains "Serena MCP Available"

### Automated Testing

```bash
pytest tests/test_serena_toggle_injection.py -v
```

---

## Token Impact

| Component | Before | After | Delta |
|-----------|--------|-------|-------|
| Serena notice | ~50 tokens | ~50 tokens | 0 |
| Orchestrator instructions | ~5K-10K | +50 | Negligible |
| Agent mission | ~2K | +50 | Negligible |
| Response field (`integrations`) | 0 | ~20 tokens | Minimal |

---

## Rollback Plan

If issues arise:
1. Remove Serena injection code from both functions
2. Revert to current behavior (spawn-time only injection)
3. Toggle continues to work for new spawns only

---

## References

- Handover 0277: Simplified Serena MCP instructions (~50 tokens)
- `src/giljo_mcp/prompt_generation/serena_instructions.py`: `generate_serena_instructions()`
- `api/endpoints/serena.py`: Toggle endpoint storing to `config.yaml`
- Alpha testing conversation: Toggle not reflected in `get_orchestrator_instructions()`
