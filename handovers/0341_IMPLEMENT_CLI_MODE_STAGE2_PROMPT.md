# Handover 0341: Implement CLI Mode Stage 2 (Implementation Prompt)

**Date:** 2025-12-09
**From Agent:** Claude Opus 4.5 (Completed Stage 1)
**To Agent:** TDD Implementor
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Ready for Implementation

---

## BEFORE YOU START - READ THESE

1. **QUICK_LAUNCH.txt** (TDD discipline, patterns, commands):
   ```
   F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt
   ```

2. **Architecture slides** (understand what we're building):
   ```
   F:\GiljoAI_MCP\handovers\Reference_docs\Workflow PPT to JPG\Slide2.JPG
   F:\GiljoAI_MCP\handovers\Reference_docs\Workflow PPT to JPG\Slide3.JPG
   F:\GiljoAI_MCP\handovers\Reference_docs\Workflow PPT to JPG\Slide4.JPG
   ```

3. **Stage 1 summary** (what was already done):
   ```
   F:\GiljoAI_MCP\handovers\0340_CLI_MODE_TWO_PHASE_ARCHITECTURE_SUMMARY.md
   ```

---

## TDD DISCIPLINE (Non-Negotiable)

```
1. Write the test FIRST (it should fail initially)
2. Implement minimal code to make test pass
3. Refactor if needed
4. Test should focus on BEHAVIOR (what the code does),
   not IMPLEMENTATION (how it does it)
5. Use descriptive test names like 'test_implementation_prompt_returns_spawned_agents'
6. Avoid testing internal implementation details
```

---

## CONTEXT: Two-Phase CLI Mode

```
┌─────────────────────┐     ┌─────────────────────┐
│ Stage 1: STAGING    │     │ Stage 2: IMPLEMENT  │
│ (Launch Tab)        │ --> │ (Jobs Tab)          │
│                     │     │                     │
│ ✅ DONE (0339)      │     │ ❌ YOUR TASK        │
│ - agent_type rules  │     │ - Implementation    │
│ - forbidden patterns│     │   prompt endpoint   │
│ - lifecycle flow    │     │ - Task tool launch  │
└─────────────────────┘     └─────────────────────┘
```

**Stage 1** (COMPLETE): User clicks [Stage Project] → Orchestrator spawns agent jobs
**Stage 2** (YOUR TASK): User clicks [▶ Implement] → Orchestrator launches agents via Task tool

---

## WHAT YOU'RE BUILDING

When user clicks [▶ Implement] button on orchestrator card in Jobs Tab:
1. Browser calls API endpoint
2. API returns implementation prompt
3. User copies prompt into Claude Code terminal
4. Orchestrator uses Task tool to launch each spawned agent

---

## DELIVERABLES

### 1. API Endpoint

**File:** `api/endpoints/prompts.py`

```python
@router.get("/implementation/{project_id}")
async def get_implementation_prompt(
    project_id: str,
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """Get CLI mode implementation prompt for launching spawned agents"""
    result = await prompt_service.generate_implementation_prompt(project_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["data"]
```

### 2. Backend Method

**File:** `src/giljo_mcp/thin_prompt_generator.py`

```python
async def generate_implementation_prompt(
    self,
    project_id: str,
    orchestrator_id: str = None
) -> str:
    """Generate implementation prompt for CLI mode Task tool launching"""
    # 1. Fetch spawned agents (status='waiting' or 'preparing')
    # 2. Generate Task tool launch instructions
    # 3. Include agent_type enforcement (same as staging)
    pass
```

### 3. Jobs Tab UI Handler

**File:** `frontend/src/components/projects/JobsTab.vue`

```javascript
async function handleImplementClick(orchestratorJob) {
    // Currently shows toast - change to:
    const response = await api.get(`/api/prompts/implementation/${projectId}`)
    showCopyDialog(response.data.prompt)
}
```

### 4. get_agent_mission() Enhancement (Optional)

**File:** `src/giljo_mcp/tools/orchestration.py`

Return full 6-phase protocol in `get_agent_mission()` response.

---

## IMPLEMENTATION PROMPT CONTENT (Draft)

```markdown
# Implementation Phase - Launch Spawned Agents

You completed staging. Now launch your agents using Task tool.

## Spawned Agents
| agent_type | agent_name | job_id |
|------------|------------|--------|
| implementer | Backend Impl | {uuid} |
| implementer | Frontend Impl | {uuid} |
| tester | Integration Tests | {uuid} |

## Launch Each Agent

For each agent, call Task tool:

```
Task(
    subagent_type="{agent_type}",  # MUST match exactly - see staging rules
    prompt="You are {agent_name}. Job ID: {job_id}. Tenant: {tenant_key}.
            Call get_agent_mission('{job_id}', '{tenant_key}') to start."
)
```

## CRITICAL: agent_type Rules (Same as Staging)
- agent_type MUST match template filename exactly
- agent_name is display only - NEVER use for Task tool
- FORBIDDEN: Task(subagent_type="{agent_name}")
```

---

## TEST FILE STRUCTURE

**Create:** `tests/api/test_implementation_prompt_api.py`

```python
@pytest.mark.asyncio
async def test_implementation_prompt_returns_spawned_agents():
    """Implementation prompt should list all spawned agents"""
    pass

@pytest.mark.asyncio
async def test_implementation_prompt_uses_correct_agent_type():
    """Task tool instructions must use agent_type, not agent_name"""
    pass

@pytest.mark.asyncio
async def test_implementation_prompt_requires_cli_mode():
    """Endpoint should only work when project is in CLI mode"""
    pass

@pytest.mark.asyncio
async def test_implementation_prompt_returns_error_if_no_agents_spawned():
    """Should return helpful error if staging not complete"""
    pass
```

---

## SUCCESS CRITERIA

1. ✅ Tests written FIRST (RED) → Implementation → Tests pass (GREEN)
2. ✅ `/api/prompts/implementation/{project_id}` returns valid prompt
3. ✅ Prompt lists all spawned agents with correct agent_type
4. ✅ Task tool instructions use strict agent_type (not agent_name)
5. ✅ Jobs Tab [▶] button copies prompt (not toast)
6. ✅ Multi-tenant isolation enforced
7. ✅ Error handling for edge cases (no agents, wrong mode)

---

## EXISTING PATTERNS TO FOLLOW

**Staging prompt endpoint** (similar pattern):
- `api/endpoints/prompts.py` - staging endpoint
- `src/giljo_mcp/thin_prompt_generator.py` - `generate_staging_prompt()`

**Service layer pattern**:
- See `F:\GiljoAI_MCP\docs\SERVICES.md`

**Agent job queries**:
- `src/giljo_mcp/services/orchestration_service.py` - job management

---

## COMMANDS YOU'LL NEED

```bash
# Run tests (TDD cycle)
pytest tests/api/test_implementation_prompt_api.py -v

# Check database for spawned agents
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp \
  -c "SELECT agent_type, agent_name, status FROM mcp_agent_jobs WHERE project_id='...';"

# Start dev server
python startup.py --dev

# Frontend dev server
cd frontend && npm run dev
```

---

## QUESTIONS TO ASK USER (If Unclear)

1. Should [▶] button open modal or auto-copy to clipboard?
2. Include only 'waiting' agents, or all non-completed?
3. What error message if no agents spawned yet?

---

## START EXECUTION

1. Read QUICK_LAUNCH.txt
2. Read architecture slides
3. Write failing tests (RED)
4. Implement (GREEN)
5. Refactor if needed
6. Commit with descriptive message
