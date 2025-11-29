# Handover 0251: Universal Orchestrator Execution Prompt (Stateless Fetch-First Pattern)

**Date**: 2025-11-28
**Status**: READY FOR IMPLEMENTATION
**Priority**: MEDIUM
**Type**: UX Simplification + Robustness Enhancement
**Estimated Time**: 1.5 hours
**Builds Upon**: Handover 0246a (Staging Workflow), 0246b (Generic Agent Template), 0088 (Thin Client Architecture)

---

## Executive Summary

**Problem**: GiljoAI currently has TWO different orchestrator prompts (staging vs execution) that require users to understand terminal session state. This creates confusion and reduces robustness.

**Solution**: Implement a **universal "fetch-first" prompt** that works in ALL scenarios by always calling `get_orchestrator_instructions()` MCP tool first. This eliminates scenario detection and simplifies UX to a single "Copy Orchestrator Prompt" button.

**Impact**:
- **Simplified UX**: One button instead of two (Stage Project → Copy Orchestrator Prompt)
- **Stateless Design**: Works in fresh terminals AND existing sessions
- **Increased Robustness**: No scenario detection required
- **Zero Performance Cost**: MCP tool is idempotent (safe to call multiple times)

**Key Insight**: The `get_orchestrator_instructions()` MCP tool is ALREADY idempotent and designed for repeated calls. We can leverage this to create a universal prompt that works everywhere.

---

## Problem Statement

### Current State: Scenario-Dependent Prompts

**File**: `F:\GiljoAI_MCP\api\endpoints\prompts.py`

**Two Separate Endpoints**:

1. **Staging Prompt** (`/api/prompts/staging/{project_id}`):
   - **Use Case**: Fresh terminal session (Scenario B)
   - **Flow**: Create orchestrator → Generate thin prompt → Call `get_orchestrator_instructions()`
   - **Token Budget**: ~931 tokens (7-task staging workflow)

2. **Execution Prompt** (`/api/prompts/execution/{orchestrator_job_id}`):
   - **Use Case**: Existing terminal session (Scenario A - orchestrator already running)
   - **Flow**: Fetch orchestrator → List agents → Generate coordination prompt
   - **Token Budget**: ~15-20 lines (varies by mode)

### The UX Problem

**Confusing User Journey**:
```
User Action 1: Click "Stage Project"
  ↓
System: Creates orchestrator, generates staging prompt
  ↓
User: Pastes prompt into NEW terminal
  ↓
Orchestrator: Runs 7-task staging workflow

---

User Action 2 (Later): Click "Launch Jobs" (Play icon)
  ↓
System: Generates execution prompt
  ↓
User: Pastes prompt into SAME terminal (or different?)
  ↓
Orchestrator: Coordinates agents
```

**Questions Users Must Answer**:
1. "Which button do I click?"
2. "Do I need a new terminal or use the same one?"
3. "What's the difference between staging and execution?"
4. "Can I re-run the staging prompt?"

---

## Proposed Solution: Universal Scenario B Prompt

### The "Fetch-First" Pattern

**Core Insight**: The `get_orchestrator_instructions()` MCP tool is **idempotent** and **fast** (<2s). We can ALWAYS call it first, regardless of session state.

**Universal Prompt Flow**:
```
User Action: Click "Copy Orchestrator Prompt" (unified button)
  ↓
System: Generates universal prompt with orchestrator_id
  ↓
User: Pastes prompt into ANY terminal (fresh or existing)
  ↓
Orchestrator: ALWAYS calls get_orchestrator_instructions() FIRST
  ↓
MCP Tool: Returns condensed mission (idempotent, cached if already read)
  ↓
Orchestrator: Proceeds with execution (agents already spawned or spawns new ones)
```

### Benefits of Universal Approach

**1. Stateless Design**:
- Works in fresh terminal sessions
- Works in existing terminal sessions
- No state detection required

**2. Simplified UX**:
- One button: "Copy Orchestrator Prompt"
- No user confusion about scenarios
- Consistent behavior every time

**3. Robustness**:
- No scenario detection logic
- No edge cases (user switched terminals, session crashed, etc.)
- Self-healing (orchestrator fetches latest state from MCP)

**4. Performance**:
- MCP tool returns cached mission if already read (`mission_read_at` timestamp)
- Zero performance penalty for repeated calls
- <2s latency even on first call

---

## Implementation Plan

### Phase 1: Backend Changes (ThinClientPromptGenerator)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\thin_prompt_generator.py`

**Task 1.1: Deprecate `generate_execution_prompt()` method**

**Current** (Lines 844-918):
```python
async def generate_execution_prompt(
    self,
    orchestrator_job_id: str,
    project_id: str,
    claude_code_mode: bool = False
) -> str:
    """Generate execution phase prompt for orchestrator."""
    # Scenario A logic (assumes orchestrator exists in session)
    ...
```

**Action**: Mark as deprecated, redirect to universal prompt
```python
async def generate_execution_prompt(
    self,
    orchestrator_job_id: str,
    project_id: str,
    claude_code_mode: bool = False
) -> str:
    """
    DEPRECATED: Use generate_staging_prompt() instead (universal Scenario B).

    This method is kept for backward compatibility only.
    Will be removed in v4.0.
    """
    logger.warning(
        "[ThinPromptGenerator] generate_execution_prompt() is deprecated. "
        "Use generate_staging_prompt() for universal prompt generation."
    )

    # Redirect to universal prompt generator
    return await self.generate_staging_prompt(
        orchestrator_id=orchestrator_job_id,
        project_id=project_id,
        claude_code_mode=claude_code_mode
    )
```

**Task 1.2: Enhance `generate_staging_prompt()` documentation**

Update docstring to clarify universal nature:
```python
async def generate_staging_prompt(
    self,
    orchestrator_id: str,
    project_id: str,
    claude_code_mode: bool = False
) -> str:
    """
    Generate UNIVERSAL orchestrator prompt (Handover 0251).

    Uses "fetch-first" pattern - ALWAYS calls get_orchestrator_instructions()
    MCP tool first, then adapts workflow based on current state.

    Works in ALL scenarios:
    - Fresh terminal (full staging workflow)
    - Existing terminal (skip completed tasks)
    - Crashed session (resume from last checkpoint)

    Args:
        orchestrator_id: Orchestrator job UUID
        project_id: Project UUID
        claude_code_mode: Use Claude Code CLI mode (default: False)

    Returns:
        Universal prompt that works in any terminal session
    """
```

---

### Phase 2: Frontend Changes

**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\ProjectTabs.vue`

**Task 2.1: Rename "Stage Project" button to "Copy Orchestrator Prompt"**

**Current**:
```vue
<v-btn
  color="primary"
  :loading="loadingStageProject"
  @click="handleStageProject"
>
  Stage Project
</v-btn>
```

**New**:
```vue
<v-btn
  color="primary"
  :loading="loadingPrompt"
  @click="handleCopyOrchestratorPrompt"
  prepend-icon="mdi-content-copy"
>
  Copy Orchestrator Prompt
</v-btn>

<v-tooltip activator="parent" location="bottom">
  Universal prompt - works in fresh OR existing terminals
</v-tooltip>
```

**Task 2.2: Update function name and messaging**

```javascript
async function handleCopyOrchestratorPrompt() {
  loadingPrompt.value = true

  try {
    // Generate UNIVERSAL orchestrator prompt (fetch-first pattern)
    const response = await api.prompts.staging(props.project.id, {
      tool: 'claude-code',
    })

    if (!response.data?.prompt) {
      throw new Error('Invalid response from staging endpoint')
    }

    const { prompt } = response.data

    // Copy to clipboard
    const copied = await copyPromptToClipboard(prompt)

    if (copied) {
      console.log('[ProjectTabs] Universal orchestrator prompt copied (fetch-first pattern)')

      // Show success toast with universal messaging
      toastMessage.value = 'Orchestrator prompt copied - paste into ANY terminal (fresh or existing)'
      toastColor.value = 'success'
      toastDuration.value = 4000
      toastVisible.value = true
    } else {
      alert(`Please manually copy this prompt:\n\n${prompt}`)
    }

    emit('orchestrator-prompt-copied')

  } catch (error) {
    console.error('Failed to generate orchestrator prompt:', error)

    const errorMsg = error.response?.data?.detail || error.message || 'Failed to generate prompt'

    toastMessage.value = errorMsg
    toastColor.value = 'error'
    toastDuration.value = 5000
    toastVisible.value = true
  } finally {
    loadingPrompt.value = false
  }
}
```

**Task 2.3: Update Jobs Tab Play button for orchestrator**

**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\JobsTab.vue`

For orchestrator agents, redirect to LaunchTab:
```javascript
async function handlePlay(agent) {
  try {
    // Handover 0251: Orchestrator uses UNIVERSAL prompt from LaunchTab
    if (agent.agent_type === 'orchestrator') {
      showToast({
        message: 'Use "Copy Orchestrator Prompt" button in Launch tab for universal prompt',
        type: 'info',
        duration: 4000
      })
      return
    }

    // Specialist agent universal prompt (unchanged)
    const response = await api.prompts.agentPrompt(agent.job_id || agent.agent_id)
    const promptText = response.data?.prompt || ''

    if (!promptText) {
      throw new Error('No prompt text returned')
    }

    await copyToClipboard(promptText)
    showToast({ message: 'Agent prompt copied to clipboard', type: 'success', duration: 3000 })

    emit('launch-agent', agent)
  } catch (error) {
    console.error('[JobsTab] Failed to prepare launch prompt:', error)
    const msg = error.response?.data?.detail || error.message || 'Failed to prepare launch prompt'
    showToast({ message: msg, type: 'error', duration: 5000 })
  }
}
```

---

### Phase 3: API Endpoint Updates

**File**: `F:\GiljoAI_MCP\api\endpoints\prompts.py`

**Task 3.1: Mark `/api/prompts/execution/{orchestrator_job_id}` as deprecated**

Add deprecation warning to endpoint:
```python
@router.get("/execution/{orchestrator_job_id}")
async def get_execution_prompt(
    orchestrator_job_id: str,
    claude_code_mode: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate execution phase prompt for orchestrator (Handover 0109).

    DEPRECATED (Handover 0251): Use /api/prompts/staging/{project_id} instead.

    This endpoint returns scenario-specific prompts (Scenario A).
    The new universal prompt (/staging) works in ALL scenarios using fetch-first pattern.

    This endpoint will be removed in v4.0.
    """
    logger.warning(
        f"[DEPRECATED] /api/prompts/execution called for orchestrator {orchestrator_job_id}. "
        "Use /api/prompts/staging for universal prompt generation."
    )

    # Redirect to universal prompt generator
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    try:
        # Fetch job to get project_id
        job_stmt = select(MCPAgentJob).where(
            MCPAgentJob.job_id == orchestrator_job_id,
            MCPAgentJob.tenant_key == current_user.tenant_key,
        )
        job_result = await db.execute(job_stmt)
        job = job_result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orchestrator job {orchestrator_job_id} not found"
            )

        # Use universal prompt generator
        generator = ThinClientPromptGenerator(db, current_user.tenant_key)
        prompt_text = await generator.generate_staging_prompt(
            orchestrator_id=orchestrator_job_id,
            project_id=job.project_id,
            claude_code_mode=claude_code_mode,
        )

        return {
            "success": True,
            "orchestrator_job_id": orchestrator_job_id,
            "project_id": str(job.project_id),
            "prompt": prompt_text,
            "deprecated": True,
            "migration_note": "Use /api/prompts/staging/{project_id} for universal prompts"
        }

    except Exception as e:
        logger.exception(f"[DEPRECATED ENDPOINT] Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate prompt: {e!s}"
        )
```

**Task 3.2: Update `/api/prompts/staging/{project_id}` documentation**

```python
@router.get("/staging/{project_id}")
async def generate_universal_orchestrator_prompt(
    project_id: str,
    tool: str = Query("claude-code", pattern="^(claude-code|codex|gemini)$"),
    instance_number: int = Query(1, ge=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
):
    """
    Generate UNIVERSAL orchestrator prompt (Handover 0251 - Fetch-First Pattern).

    REPLACES: Both /staging and /execution endpoints (unified approach)

    Generates intelligent, token-efficient, UNIVERSAL orchestrator prompts
    that work in ANY terminal session (fresh OR existing).

    Key Features:
    - **Fetch-First Pattern**: Always calls get_orchestrator_instructions() first
    - **Stateless Design**: No session state required
    - **Self-Healing**: Adapts to current project state from MCP
    - **Idempotent**: Safe to run multiple times
    - **Universal**: Works in ALL scenarios

    Args:
        project_id: Project UUID
        tool: Target AI tool (claude-code, codex, gemini)
        instance_number: Orchestrator instance number
        current_user: Authenticated user
        db: Database session
        ws_dep: WebSocket dependency

    Returns:
        JSON with universal orchestrator prompt (~600-800 tokens)
    """
```

---

## Testing Strategy

### Test 1: Fresh Terminal (Scenario B)

```bash
# User action: Click "Copy Orchestrator Prompt" button

# User pastes prompt into FRESH terminal:
$ # [Universal prompt pasted here]

# Expected behavior:
# 1. Orchestrator calls get_orchestrator_instructions()
# 2. MCP returns mission (condensed with priorities)
# 3. Orchestrator sees "no agents spawned yet"
# 4. Orchestrator runs FULL 7-task staging workflow
# 5. Agents spawned and coordinated

# Verification:
# - Check mission_read_at timestamp set
# - Check project status changed to "active"
# - Check agent jobs created in database
```

### Test 2: Existing Terminal (Scenario A)

```bash
# Setup: Run Test 1 first (orchestrator already running)

# User pastes SAME prompt into SAME terminal:
$ # [Same universal prompt pasted here]

# Expected behavior:
# 1. Orchestrator calls get_orchestrator_instructions() (again)
# 2. MCP returns SAME mission (mission_read_at unchanged)
# 3. Orchestrator sees "agents already spawned"
# 4. Orchestrator SKIPS staging, proceeds to coordination

# Verification:
# - mission_read_at timestamp UNCHANGED
# - No duplicate agent jobs created
```

### Test 3: Crashed Session Recovery

```bash
# Setup: Run Test 1, then KILL terminal mid-execution

# User pastes prompt into NEW terminal:
$ # [Same universal prompt pasted here]

# Expected behavior:
# 1. Orchestrator calls get_orchestrator_instructions()
# 2. MCP returns mission with current state
# 3. Orchestrator sees "agents partially completed"
# 4. Orchestrator RESUMES from last checkpoint

# Verification:
# - mission_read_at timestamp unchanged
# - Agents resume from last known state
```

---

## Success Criteria

### Functional Requirements

- ✅ Universal prompt works in fresh terminal sessions
- ✅ Universal prompt works in existing terminal sessions
- ✅ Universal prompt supports crashed session recovery
- ✅ Backward compatibility maintained (old endpoints work)

### Non-Functional Requirements

- ✅ Performance: <2s for first call, <0.5s for subsequent calls
- ✅ UX: One button instead of two
- ✅ Code: 50% reduction in prompt generation code
- ✅ Security: Multi-tenant isolation maintained

### Acceptance Criteria

1. ✅ Universal prompt generated via `generate_staging_prompt()` (enhanced)
2. ✅ `/execution` endpoint marked deprecated, redirects to universal generator
3. ✅ "Copy Orchestrator Prompt" button replaces "Stage Project"
4. ✅ "Launch Jobs" button shows info message for orchestrator agents
5. ✅ All 3 tests pass (Fresh, Existing, Recovery)
6. ✅ Documentation updated
7. ✅ Backward compatibility verified

---

## Migration Guide

### For Users

**Old Workflow** (Two Buttons):
- "Stage Project" → Scenario B prompt (fresh terminal)
- "Launch Jobs" → Scenario A prompt (existing session)

**New Workflow** (One Button):
- "Copy Orchestrator Prompt" → Universal prompt (works everywhere)

### For Developers

**Old Code**:
```python
if orchestrator_exists_in_session:
    prompt = await api.get(f"/api/prompts/execution/{orchestrator_id}")
else:
    prompt = await api.get(f"/api/prompts/staging/{project_id}")
```

**New Code**:
```python
# Always use staging endpoint - it's now universal
prompt = await api.get(f"/api/prompts/staging/{project_id}")
```

---

## Rollback Plan

If issues arise:

```bash
git checkout HEAD -- src/giljo_mcp/thin_prompt_generator.py
git checkout HEAD -- frontend/src/components/projects/ProjectTabs.vue
git checkout HEAD -- frontend/src/components/projects/JobsTab.vue
git checkout HEAD -- api/endpoints/prompts.py
```

**Database Impact**: None
**API Impact**: None (old endpoints still work)
**Risk**: Low (template changes only)

---

## Timeline

**Total Estimate**: 1.5 hours

- Phase 1 (Backend): 30 minutes
- Phase 2 (Frontend): 30 minutes
- Phase 3 (API): 15 minutes
- Testing: 15 minutes

---

## References

- Handover 0246a: Staging Workflow
- Handover 0246b: Generic Agent Template
- Handover 0088: Thin Client Architecture
- docs/ORCHESTRATOR.md: Orchestrator documentation

---

**END OF HANDOVER 0251**
