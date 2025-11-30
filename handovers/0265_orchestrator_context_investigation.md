# Handover 0265: Orchestrator Context Wiring - Implementation Roadmap

**Date**: 2025-11-29
**Agent**: System Architect
**Status**: Implementation Plan Ready
**Type**: Multi-Handover Roadmap (0266-0272)
**Related**: Handovers 0264 (Workflow Harmonization), 0246a-c (Orchestrator Workflow Pipeline)

---

## Executive Summary

This document provides a comprehensive implementation roadmap to fix critical orchestrator context wiring issues. Investigation revealed that while the thin client architecture works correctly (~450-550 tokens), the orchestrator lacks essential context and instructions due to missing UI-backend wiring, absent integration instructions, and incomplete context generation.

**Critical Issues to Fix**:
1. Field priorities not persisting from UI to orchestrator (empty `{}`)
2. Missing Serena MCP usage instructions despite being enabled
3. Absent 360 memory context and update instructions
4. GitHub integration toggle not persisting or fetching commits
5. Missing comprehensive MCP tool catalog and usage patterns

**Implementation Strategy**: 7 focused handover projects (0266-0272) addressing issues in priority order, with clear scope, testing criteria, and success metrics for each.

---

## Session Background

### Previous Work Context

This investigation builds on recent workflow harmonization work:

- **Handover 0264**: Workflow harmonization resolving 6 contradictions between PDF guide and flow.md
- **Workflow Code Review**: Dual-status system (database values vs API aliases)
- **Validation Report**: Two types of agent spawning (MCP server via spawn_agent_job vs Claude CLI native)
- **7-Task Staging Workflow**: Identity verification, MCP health, environment understanding, agent discovery, context prioritization, job spawning, activation
- **WebSocket Bug Fix**: Resolved spawned_by chain population issue in 0264

### Testing Scenario

User was testing the orchestrator context system with:
- **Product**: TinyContacts (personal contact management app)
- **Action**: Used "Stage Project" button in UI
- **Investigation**: Called `get_orchestrator_instructions()` MCP tool to analyze what context the orchestrator receives
- **Configuration**: UI showed all context toggles enabled (Product Core, Vision Documents, Tech Stack, etc.)

---

## Key Findings from get_orchestrator_instructions()

### 1. Empty Field Priorities

**Observed**:
```json
{
  "field_priorities": {},
  "context_depth": "moderate"
}
```

**Expected**:
```json
{
  "field_priorities": {
    "product_core": 1,
    "vision_documents": 2,
    "tech_stack": 1,
    "architecture": 2,
    "testing": 2,
    "memory_360": 2,
    "git_history": 2,
    "agent_templates": 1
  },
  "context_depth": "moderate"
}
```

**Impact**: Orchestrator cannot apply context prioritization because it receives no priority configuration, despite UI showing all contexts enabled.

### 2. Missing Context Types

**360 Memory**: Absent despite toggle enabled
```json
// Expected but missing:
{
  "memory_360": {
    "sequential_history": [
      {
        "sequence": 1,
        "type": "project_closeout",
        "summary": "...",
        "git_commits": [...]
      }
    ]
  }
}
```

**Git History**: Absent despite GitHub integration toggle enabled
```json
// Expected but missing:
{
  "git_history": {
    "commits": [
      {
        "sha": "abc123",
        "message": "...",
        "author": "...",
        "timestamp": "..."
      }
    ]
  }
}
```

**Testing Config**: Absent despite toggle enabled
```json
// Expected but missing:
{
  "testing": {
    "quality_standards": "...",
    "strategy": "...",
    "frameworks": [...]
  }
}
```

**Agent Templates**: Present but minimal (names only, not full template bodies)
```json
// Actual (minimal):
{
  "agent_templates": {
    "templates": [
      {"name": "Orchestrator", "id": "..."},
      {"name": "Implementer", "id": "..."}
    ]
  }
}
```

### 3. Token Count Analysis

**Important Distinction**: Thin client architecture separates *send* vs *fetch* token counts.

| Metric | Value | Assessment |
|--------|-------|------------|
| Thin prompt (sent to user) | ~450-550 tokens | ✅ GOOD - Lean clipboard prompt |
| Fetched context (orchestrator receives) | ~10K tokens | ✅ ACCEPTABLE - Rich data is fine |
| Target prompt budget | <1K tokens | ✅ MET - Thin prompt stays under budget |

**Clarification Needed**: The flow.md documentation should clarify:
- **Thin prompt**: What the user pastes (~450-550 tokens) - THIS is the optimization target
- **Fetched context**: What the orchestrator receives from MCP tools (~10K tokens) - Rich data is OK here

The confusion arises because we optimized the *thin prompt* from ~3,500 → ~450-550 tokens (85% reduction), but the *fetched context* can be larger (10K+) since it's not clipboard-limited.

---

## UI-Backend Disconnects Identified

### 1. Context Priority Settings

**Location**: My Settings → Context → Field Priority Configuration

**Symptoms**:
- UI shows all contexts enabled with priority badges (Priority 1, Priority 2, etc.)
- Backend receives `field_priorities: {}` (empty object)
- Settings appear to save (no error messages) but don't persist

**Suspected Cause**:
- Frontend emitting settings update event
- Backend endpoint receiving request but not saving to database
- OR: Orchestrator prompt generator not reading saved settings

**Code Paths to Investigate**:
```python
# Backend: Settings persistence
# api/endpoints/settings.py
@router.put("/context-priorities")
async def update_context_priorities(...)
    # Is this saving to Product.context_settings?

# Backend: Orchestrator prompt generation
# src/giljo_mcp/prompt_generation/thin_client_generator.py
def _build_staging_prompt(...)
    # Is this reading Product.context_settings?
```

### 2. GitHub Integration Toggle

**Location**: My Settings → Integrations → GitHub Integration

**Symptoms**:
- Toggle can be enabled in UI
- Toggle state doesn't persist across page refreshes
- Backend doesn't receive GitHub commits in orchestrator context

**Expected Behavior**:
- Toggle state saved to `Product.product_memory.git_integration`
- When enabled, orchestrator fetches git commits via `fetch_git_history()` MCP tool
- Commits appear in `get_orchestrator_instructions()` response

**Suspected Cause**:
- Frontend toggle state not emitting save event
- Backend endpoint not updating `Product.product_memory` JSONB field
- OR: Git history fetcher not checking toggle state

**Code Paths to Investigate**:
```python
# Backend: GitHub toggle persistence
# api/endpoints/settings.py
@router.put("/integrations/github")
async def update_github_integration(...)
    # Is this updating Product.product_memory?

# Backend: Git history fetching
# src/giljo_mcp/tools/fetch_git_history.py
async def fetch_git_history(...)
    # Is this checking Product.product_memory.git_integration?
```

### 3. Other Settings Potentially Affected

**Settings that may have similar UI-backend wiring issues**:

| Setting | Location | Suspected Issue |
|---------|----------|-----------------|
| Serena MCP Toggle | My Settings → Advanced → Serena MCP | Toggle state may not persist |
| Context Depth | My Settings → Context → Depth Configuration | May not reach orchestrator |
| Advanced Settings | My Settings → Advanced | General persistence issues |

**Recommendation**: Audit all settings endpoints to verify:
1. Frontend emits correct WebSocket/HTTP events
2. Backend receives and saves to database
3. Backend reads saved settings when generating prompts/fetching context

---

## Configuration Architecture

### Current System (v2.0 Context Management)

**2-Dimensional Model**:
- **Priority Dimension** (WHAT to fetch): Priority 1-4 (Critical → Excluded)
- **Depth Dimension** (HOW MUCH detail): Light, Moderate, Heavy

**Storage**:
```python
# Product model
class Product(Base):
    context_settings = Column(JSONB, nullable=True)
    # Expected structure:
    # {
    #   "field_priorities": {
    #     "product_core": 1,
    #     "vision_documents": 2,
    #     ...
    #   },
    #   "context_depth": "moderate"
    # }
```

**9 MCP Context Tools**:
1. `fetch_product_context` - Product Core badge
2. `fetch_vision_document` - Vision Documents badge (paginated)
3. `fetch_tech_stack` - Tech Stack badge
4. `fetch_architecture` - Architecture badge
5. `fetch_testing_config` - Testing badge
6. `fetch_360_memory` - 360 Memory badge (paginated)
7. `fetch_git_history` - Git History badge
8. `fetch_agent_templates` - Agent Templates badge
9. `fetch_project_context` - Project Context badge

**Orchestrator Workflow**:
1. Thin prompt generated by `ThinClientPromptGenerator._build_staging_prompt()`
2. User pastes thin prompt (~450-550 tokens) into Claude Code
3. Orchestrator calls `get_orchestrator_instructions(orchestrator_id, tenant_key)` MCP tool
4. Tool fetches context based on `Product.context_settings.field_priorities`
5. Orchestrator receives rich context (~10K tokens) for decision-making

---

## Token Budget Clarification

### Thin Client Architecture Goals

**Primary Optimization Target**: User clipboard prompt (thin prompt)
- **v1.0 (Fat Prompt)**: ~3,500 tokens (entire mission + context embedded)
- **v2.0 (Thin Prompt)**: ~450-550 tokens (mission fetched via MCP tool)
- **Reduction**: 85% token savings

**Secondary Metric**: Fetched context (what orchestrator receives)
- **Current**: ~10K tokens (product + vision + tech + arch + templates)
- **Target**: No hard limit - richness is acceptable here
- **Reason**: Not clipboard-limited, only LLM context window matters

### What Gets Counted Where

| Component | Token Count | Optimization Target | User Impact |
|-----------|-------------|---------------------|-------------|
| Thin prompt (paste to clipboard) | ~450-550 | ✅ YES | High - must be small |
| Fetched context (MCP tool response) | ~10K | ⚠️ SOFT | Low - LLM can handle it |
| Agent mission (spawned agents) | ~1,253 | ✅ YES | High - clipboard again |
| Context tools (individual fetches) | Varies | ⚠️ SOFT | Low - server-side |

**Documentation Update Needed**:
- Update `docs/ORCHESTRATOR.md` to clarify send vs fetch distinction
- Update `handovers/Reference_docs/start_to_finish_agent_FLOW.md` to explain token budgets
- Add diagram showing thin prompt (~500 tokens) → MCP tool → rich context (10K tokens)

---

## Related Work Summary

### Dual-Status System (0264)

**Database Values** (source of truth):
- `pending`, `active`, `completed`, `failed`, `cancelled`

**API Aliases** (user-friendly labels):
- `pending` → "Waiting to be Claimed"
- `active` → "Working"
- `completed` → "Complete"
- `failed` → "Error"
- `cancelled` → "Cancelled"

**Implementation**:
```python
# api/endpoints/jobs.py
STATUS_DISPLAY_MAP = {
    "pending": "Waiting to be Claimed",
    "active": "Working",
    "completed": "Complete",
    "failed": "Error",
    "cancelled": "Cancelled"
}
```

### Two Types of Agent Spawning (0264)

**Type 1: MCP Server Spawning** (via `spawn_agent_job` tool)
- Creates database record (`AgentJob`)
- Returns job_id for tracking
- User must manually spawn agent in separate Claude Code window
- Orchestrator tracks via `spawned_by` chain

**Type 2: Claude CLI Native Spawning** (via `--agent` flag)
- No database record until agent reports in
- Orchestrator has no visibility until agent starts
- Used for quick testing, not recommended for production

**Current System**: Relies on Type 1 (MCP server spawning) for proper orchestration.

### 7-Task Staging Workflow (0246a)

**Orchestrator Staging Tasks** (931 tokens total):
1. Identity verification (WHO am I, WHAT do I orchestrate)
2. MCP health check (can I reach the server)
3. Environment understanding (project/product context)
4. Agent discovery (which agents are available via `get_available_agents()`)
5. Context prioritization (apply user's field_priorities)
6. Job spawning (spawn required agents via `spawn_agent_job`)
7. Activation monitoring (track agent startup)

**Token Optimization**:
- v1.0: ~3,500 tokens (all agents embedded in prompt)
- v2.0: ~931 tokens staging + ~420 tokens discovery = ~1,351 tokens
- Savings: 61% reduction

### WebSocket Bug Fix (0264)

**Issue**: `spawned_by` chain not populating in real-time
**Cause**: Missing WebSocket event emission after job creation
**Fix**: Added `emit_job_event()` call in `spawn_agent_job` MCP tool

```python
# src/giljo_mcp/tools/spawn_agent.py
async def spawn_agent_job(...):
    # Create job
    new_job = await AgentJobManager.create_job(...)

    # Emit WebSocket event (ADDED)
    await emit_job_event(
        tenant_key=tenant_key,
        event_type="job_created",
        job_data=new_job.to_dict()
    )
```

---

## Implementation Handover Sequence

### 🔴 Critical Priority - Core Functionality Fixes

#### Handover 0266: Fix Field Priority Persistence Bug
**Estimated Time**: 4 hours
**Dependencies**: None
**Scope**: Fix the critical bug preventing field priorities from reaching orchestrator

**Root Cause Identified**:
```python
# api/endpoints/prompts.py line 455
field_priorities = job_metadata.get("fields", {})  # BUG: Should be "priorities"
# User settings stored with key "priorities" but code looks for "fields"
```

**Implementation**:
1. Fix key mismatch in `prompts.py` line 455: `"fields"` → `"priorities"`
2. Update `spawn_agent_job` in `orchestration.py` to pass field priorities to job metadata
3. Verify `User.field_priority_config` JSONB persists correctly
4. Add integration test for priority persistence flow

**Testing**:
- Enable priorities in UI → Stage project → Verify non-empty `field_priorities` in response
- Query database: `SELECT field_priority_config FROM users WHERE id = '...'`
- Call `get_orchestrator_instructions()` and verify priorities present

**Success Criteria**:
- ✅ Field priorities persist from UI to database
- ✅ Orchestrator receives non-empty `field_priorities` object
- ✅ Priorities control what context is included/excluded

---

#### Handover 0267: Add Serena MCP Instructions
**Estimated Time**: 3 hours
**Dependencies**: Handover 0266 (field priorities working)
**Scope**: Generate and include Serena MCP usage instructions when enabled

**Current Gap**:
- Code checks `config.yaml` for Serena toggle (orchestration.py:1379-1390)
- Passes `include_serena=True/False` to context builder
- But NO actual usage instructions are generated

**Implementation**:
1. Create `_generate_serena_instructions()` method in `ThinClientPromptGenerator`
2. Include when Serena enabled:
   ```python
   serena_instructions = """
   ## Serena MCP Integration
   Status: ENABLED

   CRITICAL: Use Serena tools BEFORE reading full files to save tokens.

   Available Tools:
   - mcp__serena__find_symbol: Navigate to code symbols
   - mcp__serena__get_symbols_overview: Get file structure
   - mcp__serena__search_for_pattern: Search code patterns
   - mcp__serena__find_referencing_symbols: Find references

   Usage Pattern:
   1. Use get_symbols_overview for file structure
   2. Use find_symbol to locate specific code
   3. Only read full files when necessary

   When spawning agents, include Serena availability in their mission.
   """
   ```
3. Add to orchestrator context in `get_orchestrator_instructions()`
4. Pass Serena status to spawned agents

**Testing**:
- Enable Serena in config.yaml
- Stage project and verify Serena instructions present
- Spawn agent and verify it knows Serena is available

---

### 🟠 High Priority - Context Enrichment

#### Handover 0268: Implement 360 Memory Context
**Estimated Time**: 4 hours
**Dependencies**: Handover 0266
**Scope**: Include 360 memory in orchestrator context with usage instructions

**Current Gap**:
- Code checks priority for `product_memory.sequential_history`
- Calls `_extract_product_history` if priority > 0
- But doesn't include instructions for using/updating 360 memory

**Implementation**:
1. Enhance `_extract_product_history()` in `mission_planner.py`:
   ```python
   async def _extract_product_history(self, product, priority):
       history = product.product_memory.get("sequential_history", [])

       # Format based on priority level
       if priority == 1:  # CRITICAL - Full history
           memory_context = self._format_full_history(history)
       elif priority == 2:  # IMPORTANT - Recent 5 projects
           memory_context = self._format_recent_history(history[-5:])
       else:  # NICE_TO_HAVE - Summary only
           memory_context = self._format_summary(history)

       # Add usage instructions
       memory_context += """

       ## 360 Memory Instructions
       Projects Completed: {len(history)}

       INSTRUCTIONS:
       - Reference historical patterns for decisions
       - At project completion: close_project_and_update_memory()
       - Use mini-git if GitHub disabled
       - Learn from past successes/failures
       """
       return memory_context
   ```
2. Include in `get_orchestrator_instructions()` response
3. Add memory update reminder to orchestrator staging prompt

**Testing**:
- Close a project with summary
- Stage new project
- Verify 360 memory appears with instructions
- Check orchestrator uses historical context

---

#### Handover 0269: Fix GitHub Integration Toggle
**Estimated Time**: 5 hours
**Dependencies**: None (can run parallel with others)
**Scope**: Make GitHub toggle persist and fetch commits

**Current Gaps**:
- No backend endpoint for GitHub toggle
- Toggle doesn't persist to `Product.product_memory.git_integration`
- No git history fetching when enabled

**Implementation**:
1. Create settings endpoint:
   ```python
   # api/endpoints/settings.py
   @router.put("/integrations/github")
   async def update_github_integration(
       enabled: bool,
       session: AsyncSession = Depends(get_session),
       current_user: User = Depends(get_current_user)
   ):
       product = await get_active_product(session, current_user.tenant_key)

       if not product.product_memory:
           product.product_memory = {}

       product.product_memory["git_integration"] = {
           "enabled": enabled,
           "updated_at": datetime.utcnow().isoformat()
       }

       await session.commit()
       await emit_settings_event(...)
       return {"status": "success"}
   ```
2. Update frontend to call endpoint on toggle
3. Create git history fetcher:
   ```python
   async def fetch_git_history(product_id, tenant_key):
       product = await get_product(...)
       if not product.product_memory.get("git_integration", {}).get("enabled"):
           return None

       # Run git commands
       commits = await run_git_log(product.project_path)
       return format_git_history(commits)
   ```
4. Include in orchestrator context when enabled

**Testing**:
- Toggle GitHub integration ON
- Refresh page - verify still ON
- Stage project - verify git history included
- Toggle OFF - verify no git history

---

#### Handover 0270: Add MCP Tool Instructions
**Estimated Time**: 4 hours
**Dependencies**: Handover 0266
**Scope**: Create comprehensive MCP tool catalog with usage patterns

**Current Gap**:
- Orchestrator only knows about `get_available_agents()`
- No comprehensive tool list or usage instructions
- Agents don't know what tools are available

**Implementation**:
1. Create tool catalog generator:
   ```python
   def generate_mcp_tool_catalog():
       return """
       ## Available MCP Tools

       ### Orchestration Tools
       - get_orchestrator_instructions: Fetch your mission
       - spawn_agent_job: Create new agent jobs
       - get_workflow_status: Monitor agent progress
       - update_project_mission: Persist mission plan
       - create_successor_orchestrator: Handover when needed

       ### Context Tools (9 total)
       - fetch_product_context: Product name/description
       - fetch_vision_document: Vision docs (paginated)
       - fetch_tech_stack: Languages/frameworks
       - fetch_architecture: Design patterns
       - fetch_testing_config: Quality standards
       - fetch_360_memory: Historical projects
       - fetch_git_history: Recent commits
       - fetch_agent_templates: Agent library
       - fetch_project_context: Current project

       ### Communication Tools
       - send_message: Send to other agents
       - receive_messages: Get pending messages
       - report_progress: Update job status
       - report_error: Report issues

       ### Project Tools
       - close_project_and_update_memory: Complete project
       - get_available_agents: Discover agent types

       USAGE PATTERNS:
       1. Always fetch instructions first
       2. Use context tools based on priorities
       3. Spawn agents for specialized work
       4. Monitor and coordinate progress
       5. Update memory at completion
       """
   ```
2. Include in orchestrator instructions
3. Pass relevant subset to spawned agents

**Testing**:
- Stage orchestrator
- Verify tool catalog present
- Check orchestrator uses tools correctly
- Verify agents receive relevant tool list

---

### 🟡 Medium Priority - Additional Context

#### Handover 0271: Add Testing Configuration Context
**Estimated Time**: 3 hours
**Dependencies**: Handover 0266
**Scope**: Include testing configuration based on priority

**Implementation**:
1. Extract testing config from Product model
2. Format based on priority level:
   - Priority 1: Full testing strategy and frameworks
   - Priority 2: Quality standards only
   - Priority 3: Basic test types
   - Priority 4: Exclude entirely
3. Include in orchestrator context
4. Pass to test-focused agents

**Testing**:
- Configure testing in product settings
- Set different priority levels
- Verify appropriate detail included
- Check tester agents receive config

---

### 🟢 Quality Assurance

#### Handover 0272: Comprehensive Integration Test Suite
**Estimated Time**: 6 hours
**Dependencies**: Handovers 0266-0271 complete
**Scope**: Full test coverage for context wiring

**Implementation**:
1. **Unit Tests**:
   - Settings persistence (all endpoints)
   - Context generation (all types)
   - Priority filtering logic
   - Tool catalog generation

2. **Integration Tests**:
   ```python
   async def test_full_context_flow():
       # Configure all settings
       await update_field_priorities(...)
       await enable_github_integration(...)
       await enable_serena_mcp(...)

       # Stage orchestrator
       job = await stage_project(...)

       # Fetch instructions
       context = await get_orchestrator_instructions(...)

       # Verify all components present
       assert context["field_priorities"] != {}
       assert "serena_instructions" in context["mission"]
       assert "memory_360" in context["mission"]
       assert "git_history" in context["mission"]
       assert "mcp_tool_catalog" in context["mission"]
   ```

3. **E2E Tests**:
   - Complete UI → Backend → Orchestrator flow
   - Settings persistence across sessions
   - WebSocket event propagation
   - Agent spawning with context

4. **Performance Tests**:
   - Context generation < 2 seconds
   - Settings persistence < 500ms
   - No memory leaks in long sessions

**Success Criteria**:
- ✅ >90% code coverage for settings flow
- ✅ All integration tests passing
- ✅ E2E tests verify complete workflow
- ✅ Performance within targets

---

## Testing Checklist

### Context Priority Settings

- [ ] Enable all contexts in UI (Product Core, Vision, Tech Stack, etc.)
- [ ] Save settings and verify no error messages
- [ ] Refresh page and verify toggles still enabled
- [ ] Query database: `SELECT context_settings FROM products WHERE id = '...'`
- [ ] Verify `context_settings` JSONB contains `field_priorities` object
- [ ] Stage project and call `get_orchestrator_instructions()`
- [ ] Verify response contains non-empty `field_priorities`

### GitHub Integration Toggle

- [ ] Enable GitHub integration toggle in UI
- [ ] Save and verify no error messages
- [ ] Refresh page and verify toggle still enabled
- [ ] Query database: `SELECT product_memory FROM products WHERE id = '...'`
- [ ] Verify `product_memory.git_integration = true`
- [ ] Stage project and call `get_orchestrator_instructions()`
- [ ] Verify response contains `git_history` with commits

### 360 Memory

- [ ] Close a project with a summary (use "Close Project and Update Memory" button)
- [ ] Query database: `SELECT product_memory FROM products WHERE id = '...'`
- [ ] Verify `product_memory.sequential_history` contains entry
- [ ] Stage new project and call `get_orchestrator_instructions()`
- [ ] Verify response contains `memory_360` with sequential history

### Testing Config

- [ ] Configure testing standards in product settings
- [ ] Query database: `SELECT testing_config FROM products WHERE id = '...'`
- [ ] Verify `testing_config` JSONB contains data
- [ ] Stage project and call `get_orchestrator_instructions()`
- [ ] Verify response contains `testing` section

---

## Code Investigation Paths

### Settings Persistence Flow

```python
# 1. Frontend: User toggles context priority
# frontend/src/components/settings/ContextSettings.vue
async function saveContextSettings() {
  await settingsStore.updateContextPriorities(priorities)
  // Does this emit WebSocket event?
  // Does this call API endpoint?
}

# 2. Backend: Settings endpoint receives request
# api/endpoints/settings.py
@router.put("/context-priorities")
async def update_context_priorities(
    request: ContextPrioritiesRequest,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    # Does this save to Product.context_settings?
    # Does this commit the transaction?
    # Does this emit WebSocket event?
    pass

# 3. Backend: Orchestrator reads settings
# src/giljo_mcp/prompt_generation/thin_client_generator.py
class ThinClientPromptGenerator:
    async def _build_staging_prompt(self, ...):
        # Does this query Product.context_settings?
        # Does this pass field_priorities to MCP tools?
        pass

# 4. Backend: MCP tool uses priorities
# src/giljo_mcp/tools/get_orchestrator_instructions.py
async def get_orchestrator_instructions(
    orchestrator_id: str,
    tenant_key: str
):
    # Does this read Product.context_settings?
    # Does this filter context based on field_priorities?
    pass
```

### Database Schema Verification

```sql
-- Verify Product table has context_settings column
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'products'
  AND column_name IN ('context_settings', 'product_memory', 'testing_config');

-- Check current product settings
SELECT
    id,
    name,
    context_settings,
    product_memory->'git_integration' as github_enabled,
    product_memory->'sequential_history' as memory_history,
    testing_config
FROM products
WHERE name = 'TinyContacts';

-- Verify orchestrator job context
SELECT
    id,
    agent_type,
    status,
    context_tracking
FROM mcp_agent_jobs
WHERE agent_type = 'orchestrator'
ORDER BY created_at DESC
LIMIT 5;
```

---

## Success Criteria

**This handover is complete when**:

1. ✅ Context priority settings persist from UI to database
2. ✅ `get_orchestrator_instructions()` returns non-empty `field_priorities`
3. ✅ GitHub toggle persists across page refreshes
4. ✅ Orchestrator receives git history when toggle enabled
5. ✅ 360 memory appears in orchestrator context
6. ✅ Testing config appears in orchestrator context
7. ✅ flow.md clarifies send vs fetch token distinction
8. ✅ All settings endpoints audited and documented

**Current Status**: Investigation complete, action items identified, ready for implementation.

---

## Related Documentation

- [docs/ORCHESTRATOR.md](../docs/ORCHESTRATOR.md) - Orchestrator architecture and context tracking
- [docs/360_MEMORY_MANAGEMENT.md](../docs/360_MEMORY_MANAGEMENT.md) - Product memory system
- [handovers/Reference_docs/start_to_finish_agent_FLOW.md](Reference_docs/start_to_finish_agent_FLOW.md) - Workflow guide
- [handovers/0246a_staging_workflow.md](0246a_staging_workflow.md) - Orchestrator staging tasks
- [handovers/0246c_dynamic_agent_discovery.md](0246c_dynamic_agent_discovery.md) - Agent discovery optimization
- [handovers/0264_workflow_harmonization.md](0264_workflow_harmonization.md) - Recent workflow fixes

---

## Implementation Timeline & Resource Allocation

### Week 1: Critical Fixes (20 hours)
- **Day 1-2**: Handover 0266 (Field Priority Bug) - 4 hours
- **Day 2**: Handover 0267 (Serena Instructions) - 3 hours
- **Day 3**: Handover 0268 (360 Memory) - 4 hours
- **Day 4**: Handover 0270 (MCP Tool Catalog) - 4 hours
- **Day 5**: Integration testing - 5 hours

### Week 2: Enhancements & QA (15 hours)
- **Day 6-7**: Handover 0269 (GitHub Integration) - 5 hours
- **Day 8**: Handover 0271 (Testing Config) - 3 hours
- **Day 9-10**: Handover 0272 (Test Suite) - 6 hours
- **Day 10**: Documentation updates - 1 hour

**Total Estimated Time**: 35 hours

---

## Critical Code Locations Reference

### Field Priority Bug (Handover 0266)
```
F:\GiljoAI_MCP\api\endpoints\prompts.py - Line 455
F:\GiljoAI_MCP\src\giljo_mcp\tools\orchestration.py - Line 1253-1255
F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py - Line 990
```

### Serena Integration (Handover 0267)
```
F:\GiljoAI_MCP\src\giljo_mcp\tools\orchestration.py - Line 1379-1390
F:\GiljoAI_MCP\src\giljo_mcp\prompt_generation\thin_client_generator.py
```

### 360 Memory (Handover 0268)
```
F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py - Line 1324-1336
F:\GiljoAI_MCP\src\giljo_mcp\tools\close_project.py
```

### GitHub Integration (Handover 0269)
```
F:\GiljoAI_MCP\api\endpoints\settings.py - (needs creation)
F:\GiljoAI_MCP\frontend\src\components\settings\IntegrationsTab.vue
```

---

## Success Metrics Summary

### Immediate Validation (After Each Handover)
1. **0266**: `field_priorities` non-empty in orchestrator response
2. **0267**: Serena instructions present when enabled
3. **0268**: 360 memory context with usage instructions included
4. **0269**: GitHub toggle persists and fetches commits
5. **0270**: Complete MCP tool catalog available
6. **0271**: Testing config respects priority levels
7. **0272**: All integration tests passing

### Overall Project Success
- ✅ Orchestrator receives complete context (not just product/vision)
- ✅ All UI settings persist to backend correctly
- ✅ Integration instructions guide orchestrator behavior
- ✅ Field priorities control context inclusion/exclusion
- ✅ 90%+ test coverage for settings/context flow
- ✅ Documentation updated with accurate information

---

## Notes for Implementation Agents

### Critical Context
This is fixing WIRING issues, not architectural problems:
- **Thin client architecture**: Working correctly (~450-550 tokens)
- **Rich context fetching**: Working as designed (~10K tokens OK)
- **Problem**: Settings not reaching orchestrator, missing instructions

### First Project Considerations
Since this is the FIRST project in a product:
- No existing 360 memory → Include instructions anyway
- No git history → Include git commands for future use
- No claude.md → Serena won't have much to index initially
- **Key Point**: Instructions should be present even with no data

### Implementation Order Matters
1. **Fix field priorities FIRST** (0266) - Everything depends on this
2. **Then add missing instructions** (0267, 0268, 0270)
3. **Fix GitHub in parallel** (0269) - Independent work
4. **Testing config after priorities work** (0271)
5. **Test suite LAST** (0272) - Needs all fixes in place

### Testing With TinyContacts
Use the existing TinyContacts product for all testing:
- Already configured in system
- Has vision documents uploaded
- Perfect for validating all context types
- Simple to stage and test repeatedly

### Key Insight
We're NOT reducing tokens anymore - we want RICH, STRUCTURED data:
- Thin prompt stays small (450-550 tokens) for clipboard
- Fetched context can be rich (10K+ tokens) for capability
- Instructions are critical even if features have no data yet

---

**End of Implementation Roadmap - Handover 0265**
