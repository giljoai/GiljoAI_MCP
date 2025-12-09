# Session Memory: Handover 0335 - CLI Mode Agent Template Validation (COMPLETE)

**Date**: 2025-12-09
**Agent**: Documentation Manager
**Handover**: 0335_CLI_MODE_AGENT_TEMPLATE_VALIDATION.md
**Status**: COMPLETE (4/4 tasks + 4 bug fixes)
**Session Type**: Continuation (Tasks 1-2 completed in previous session)

---

## Executive Summary

This session completed **Handover 0335: CLI Mode Agent Template Validation**, implementing template export tracking, UI staleness indicators, and fixing critical WebSocket/execution mode bugs discovered during testing.

**What Changed**:
- Database: Added `last_exported_at` column to track exports
- API: Added export timestamp updates across 3 export flows
- WebSocket: Real-time `template:exported` events for UI updates
- Frontend: Export Status column with staleness detection
- Bug Fixes: 4 critical issues (WebSocket imports, Vue lazy-loading, API response, execution mode)

**Commits**: 1 commit this session (`1b488be8`), 5 commits previous session

---

## Tasks Completed This Session

### Task 3: Database Export Tracking ✅

**Objective**: Track when templates are exported to CLI

**Database Schema Changes**:
```python
# File: src/giljo_mcp/models/templates.py
# Added column:
last_exported_at = Column(DateTime, nullable=True)
```

**Migration**:
```python
# File: migrations/versions/7983bf9c91c9_add_last_exported_at_to_agent_templates_.py
# Idempotent approach (safe for existing deployments):
op.execute("""
    ALTER TABLE mcp_agent_templates
    ADD COLUMN IF NOT EXISTS last_exported_at TIMESTAMP WITHOUT TIME ZONE;
""")
```

**API Response Schema**:
```python
# File: api/endpoints/templates/crud.py
# Modified _convert_to_response() to include:
{
    "last_exported_at": "2025-12-08T20:38:14.123Z",  # Timestamp of last export
    "may_be_stale": true                              # True if updated_at > last_exported_at
}
```

**Computation Logic**:
```python
may_be_stale = (
    template.updated_at is not None
    and template.last_exported_at is not None
    and template.updated_at > template.last_exported_at
)
```

---

### Task 4: UI Staleness Indicator ✅

**Objective**: Show export status in TemplateManager.vue

**UI Implementation**:
```vue
<!-- File: frontend/src/components/TemplateManager.vue -->
<!-- Added "Export Status" column to data table -->
<template>
  <v-data-table>
    <template v-slot:item.export_status="{ item }">
      <!-- Warning chip if template modified after export -->
      <v-chip v-if="item.may_be_stale" color="warning" size="small">
        <v-icon start size="small">mdi-alert</v-icon>
        Updated
      </v-chip>

      <!-- Never exported -->
      <span v-else-if="!item.last_exported_at" class="text-grey">Never</span>

      <!-- Exported and up-to-date -->
      <span v-else class="text-success">
        {{ formatDate(item.last_exported_at) }}
      </span>
    </template>
  </v-data-table>
</template>
```

**Visual Behavior**:
- **Never exported**: Grey "Never" text
- **Exported and up-to-date**: Green timestamp
- **Stale (updated after export)**: Orange warning chip with "Updated" text

---

## Bug Fixes (4 Critical Issues)

### Bug Fix 1: WebSocket ws_manager Import Error

**Problem**:
```python
# File: api/endpoints/downloads.py
from api.websocket import ws_manager  # ❌ ModuleNotFoundError
```

**Root Cause**: `api/websocket.py` exports `WebSocketManager` class but NOT a singleton `ws_manager` instance.

**Solution**: Retrieve from FastAPI app state
```python
# Fixed in 3 locations (download_agent_templates, import_personal_agents_rest, import_product_agents_rest):
ws_manager = getattr(request.app.state, "websocket_manager", None)
if ws_manager:
    await ws_manager.broadcast_templates_exported(
        tenant_key=tenant_key,
        template_ids=[t.id for t in templates],
        export_type="manual_zip",  # or "personal_agents" / "product_agents"
    )
```

**Files Modified**:
- `api/endpoints/downloads.py` (3 functions fixed)

---

### Bug Fix 2: WebSocket Events Not Received by TemplateManager

**Problem**: WebSocket events broadcast successfully, but `TemplateManager.vue` didn't update in real-time when export triggered from "integrations" tab.

**Root Cause**: Vue component lazy-loading
- TemplateManager is on "agents" tab (v-window-item)
- Export buttons are on "integrations" tab
- When export happens, TemplateManager is **NOT MOUNTED** → WebSocket handler not registered

**Solution**: Vue provide/inject pattern with parent-level WebSocket handler

**Parent Component** (`frontend/src/views/UserSettings.vue`):
```javascript
// 1. Provide reactive event data
const templateExportEvent = ref(null)
provide('templateExportEvent', templateExportEvent)

// 2. Register WebSocket handler at parent level (always mounted)
onMounted(() => {
  socketService.on('template:exported', handleTemplateExportEvent)
})

// 3. Update provided ref with unique event ID
function handleTemplateExportEvent(eventData) {
  templateExportEvent.value = {
    ...eventData,
    _eventId: Date.now()  // Force reactivity even if data same
  }
}
```

**Child Component** (`frontend/src/components/TemplateManager.vue`):
```javascript
// 1. Inject event data from parent
const injectedExportEvent = inject('templateExportEvent', ref(null))

// 2. Watch for events from parent
watch(injectedExportEvent, (newEvent) => {
  if (newEvent) processTemplateExportEvent(newEvent)
}, { deep: true })

// 3. Keep direct WebSocket handler (for when component IS mounted)
onMounted(() => {
  socketService.on('template:exported', processTemplateExportEvent)
})
```

**Why This Works**:
- Parent always mounted → always receives events
- Child can be unmounted → uses inject to get events from parent
- Belt-and-suspenders: Child also registers direct handler when mounted
- `_eventId` timestamp ensures Vue detects changes even if data identical

---

### Bug Fix 3: API Response Missing Export Fields

**Problem**: `last_exported_at` saved to database but not returned in API responses.

**Root Cause**: `_convert_to_response()` helper in `crud.py` wasn't including the new fields.

**Solution**:
```python
# File: api/endpoints/templates/crud.py
def _convert_to_response(template: AgentTemplate) -> TemplateResponse:
    # Compute staleness flag
    may_be_stale = (
        template.updated_at is not None
        and template.last_exported_at is not None
        and template.updated_at > template.last_exported_at
    )

    return TemplateResponse(
        id=template.id,
        agent_type=template.agent_type,
        # ... other fields ...
        last_exported_at=template.last_exported_at,  # ✅ Added
        may_be_stale=may_be_stale,                   # ✅ Added
        created_at=template.created_at,
        updated_at=template.updated_at,
    )
```

**Files Modified**:
- `api/endpoints/templates/crud.py`

---

### Bug Fix 4: Execution Mode Not Affecting Staging Prompt

**Problem**: Toggling "Claude Code CLI" mode in LaunchTab didn't change the staging prompt - always showed "Multi-Terminal" block.

**Root Cause**: Stale prop value
1. LaunchTab updates `execution_mode` in backend via API ✅
2. Backend updates database ✅
3. But `ProjectTabs.vue` passes `props.project` to LaunchTab
4. That prop value is from initial page load (stale)
5. When "Stage Project" clicked, uses stale `props.project.execution_mode`

**Solution**: Event emission pattern

**Child Component** (`frontend/src/components/projects/LaunchTab.vue`):
```javascript
// 1. Declare event
const emit = defineEmits(['execution-mode-changed'])

// 2. Emit after successful API update
async function toggleExecutionMode() {
  const newMode = project.value.execution_mode === 'cli' ? 'multi_terminal' : 'cli'
  await api.patch(`/api/projects/${project.value.id}`, {
    execution_mode: newMode
  })
  emit('execution-mode-changed', newMode)  // ✅ Notify parent
}
```

**Parent Component** (`frontend/src/components/projects/ProjectTabs.vue`):
```vue
<template>
  <LaunchTab
    :project="project"
    @execution-mode-changed="handleExecutionModeChanged"
  />
</template>

<script setup>
function handleExecutionModeChanged(newMode) {
  // Update prop directly (Vue allows this for objects)
  props.project.execution_mode = newMode
}
</script>
```

**Why This Works**:
- Child emits event after successful API update
- Parent receives event and updates prop value
- Next time "Stage Project" clicked, uses fresh value
- No need to refetch entire project from API

**Files Modified**:
- `frontend/src/components/projects/LaunchTab.vue`
- `frontend/src/components/projects/ProjectTabs.vue`

---

## Three Export Flows (All Update Timestamps)

### Flow 1: Manual ZIP Download
**Endpoint**: `GET /api/download/agent-templates.zip`
**Trigger**: User clicks download button in UI
**Code**:
```python
# File: api/endpoints/downloads.py
async def download_agent_templates():
    # ... create ZIP ...

    # Update timestamps
    for template in templates:
        template.last_exported_at = datetime.now(timezone.utc)
    await db.commit()

    # Broadcast event
    ws_manager = getattr(request.app.state, "websocket_manager", None)
    if ws_manager:
        await ws_manager.broadcast_templates_exported(
            tenant_key=tenant_key,
            template_ids=[t.id for t in templates],
            export_type="manual_zip"
        )
```

### Flow 2: Personal Agents Export
**Endpoint**: `POST /api/download/mcp/gil_import_personalagents`
**Trigger**: MCP tool call from Claude Code
**Code**:
```python
# File: api/endpoints/downloads.py
async def import_personal_agents_rest():
    # ... export to ~/.claude/agents/ ...

    # Update timestamps
    for template in templates:
        template.last_exported_at = datetime.now(timezone.utc)
    await db.commit()

    # Broadcast event
    await ws_manager.broadcast_templates_exported(
        tenant_key=tenant_key,
        template_ids=[t.id for t in templates],
        export_type="personal_agents"
    )
```

### Flow 3: Product Agents Export
**Endpoint**: `POST /api/download/mcp/gil_import_productagents`
**Trigger**: MCP tool call from Claude Code
**Code**:
```python
# File: api/endpoints/downloads.py
async def import_product_agents_rest():
    # ... export to [project_path]/.claude/agents/ ...

    # Update timestamps + broadcast (same pattern as above)
    export_type="product_agents"
```

**WebSocket Event Format** (all flows):
```json
{
  "type": "template:exported",
  "data": {
    "tenant_key": "tk_abc123",
    "template_ids": ["uuid1", "uuid2", "uuid3"],
    "export_type": "manual_zip",  // or "personal_agents" / "product_agents"
    "exported_at": "2025-12-08T20:38:14.123Z",
    "exported_count": 3
  },
  "timestamp": "2025-12-08T20:38:14.123Z"
}
```

---

## Architecture: Belt-and-Suspenders CLI Mode Rules

The CLI mode validation rules appear in **TWO places** for maximum enforcement:

### A) User's Pasted Prompt (Human-Readable)
**Location**: `src/giljo_mcp/thin_prompt_generator.py` lines 1003-1050

**When**: `execution_mode='cli'` AND `claude_code_mode=True`

**Content**: Full markdown block with:
- **AGENT SPAWNING RULES** table
- **Why This Matters** explanation
- **Example spawning calls**
- **Validation instructions**

**Purpose**: Claude Code user sees rules directly in pasted prompt

---

### B) get_orchestrator_instructions() Response (Machine-Readable)
**Location**: `src/giljo_mcp/tools/tool_accessor.py` lines 662-702

**When**: `execution_mode='cli'`

**Content**: JSON structure with:
```json
{
  "cli_mode_rules": {
    "agent_type_usage": "Use exact template names from allowed_agent_types",
    "agent_name_usage": "Use {agent_type} as agent_name (no numbers/suffixes)",
    "task_tool_mapping": "Only spawn agents for tasks that match template capabilities"
  },
  "spawning_examples": [
    {
      "correct": "spawn_agent_job(agent_type='implementer', agent_name='implementer', ...)",
      "incorrect": "spawn_agent_job(agent_type='implementer', agent_name='implementer-1', ...)"
    }
  ],
  "agent_spawning_constraint": {
    "allowed_agent_types": ["implementer", "tester", "analyzer", ...]
  }
}
```

**Purpose**: Machine-readable validation data for orchestrator logic

---

## Files Modified (Complete List)

### Backend Files
```
api/endpoints/downloads.py                   # WebSocket broadcasts + timestamp updates (3 functions)
api/endpoints/templates/crud.py              # Added last_exported_at & may_be_stale to response
api/websocket.py                             # Added broadcast_templates_exported() method
src/giljo_mcp/models/templates.py           # Added last_exported_at column
migrations/versions/7983bf9c91c9_*.py        # Alembic migration (idempotent)
```

### Frontend Files
```
frontend/src/components/TemplateManager.vue  # Export Status column + inject pattern
frontend/src/views/UserSettings.vue          # provide pattern + parent WebSocket handler
frontend/src/components/projects/LaunchTab.vue    # emit execution-mode-changed
frontend/src/components/projects/ProjectTabs.vue  # handle execution-mode-changed
```

---

## Git Commits

### This Session (1 commit)
```
1b488be8 - feat(0335): Complete template export tracking and execution mode fix
  - Bug fix: WebSocket ws_manager import (use app.state)
  - Bug fix: TemplateManager not receiving events (provide/inject)
  - Bug fix: API response missing export fields
  - Bug fix: Execution mode prop staleness (event emission)
  - Added: Export Status column to TemplateManager
  - Added: broadcast_templates_exported() WebSocket method
```

### Previous Session (5 commits - for reference)
```
858a0e10 - fix(0335): Reset staging state when switching between projects
1f35ea5b - feat(0335): Add WebSocket real-time export status updates
66c76019 - chore(0335): Add Alembic migration for last_exported_at column
2db3b3bb - feat(0335): Add template staleness tracking and UI indicator
617b5298 - feat(0335): Add CLI mode rules and validation to orchestrator instructions
```

---

## Testing Checklist (All Verified)

### Export Status Persistence
- [x] Export templates via manual ZIP download
- [x] Refresh browser page
- [x] Timestamps persist in "Export Status" column
- [x] Database column populated correctly

### Real-Time WebSocket Updates
- [x] Navigate to "integrations" tab
- [x] Click "Export Personal Agents" or "Export Product Agents"
- [x] Switch to "agents" tab
- [x] TemplateManager updates WITHOUT page refresh
- [x] Console shows no errors

### Staleness Detection
- [x] Export templates (green timestamp appears)
- [x] Edit template content
- [x] "Export Status" shows orange warning chip "Updated"
- [x] Re-export template
- [x] Warning chip disappears, green timestamp updates

### Execution Mode Propagation
- [x] Create new project
- [x] Toggle "Claude Code CLI" mode ON
- [x] Click "Stage Project"
- [x] Staging prompt shows CLI MODE block (not Multi-Terminal)
- [x] Toggle mode OFF
- [x] Re-stage project
- [x] Staging prompt shows Multi-Terminal block

### WebSocket Import Pattern
- [x] All 3 export functions use `getattr(request.app.state, "websocket_manager", None)`
- [x] No import errors in logs
- [x] Events broadcast successfully

---

## Known Patterns for Future Work

### Pattern 1: WebSocket Access in FastAPI Endpoints
```python
# ✅ CORRECT - Retrieve from app state
ws_manager = getattr(request.app.state, "websocket_manager", None)
if ws_manager:
    await ws_manager.broadcast_...(...)

# ❌ WRONG - Direct import fails
from api.websocket import ws_manager  # ModuleNotFoundError
```

**Why**: `api/websocket.py` exports `WebSocketManager` class, not a singleton instance. The singleton is created in `api/app.py` and attached to `app.state`.

---

### Pattern 2: Cross-Tab Vue Communication (Lazy-Loaded Components)
```javascript
// Parent (always mounted):
const eventData = ref(null)
provide('eventKey', eventData)

onMounted(() => {
  socketService.on('event:type', (data) => {
    eventData.value = { ...data, _eventId: Date.now() }  // Force reactivity
  })
})

// Child (may be lazy-loaded):
const injectedEvent = inject('eventKey', ref(null))

watch(injectedEvent, (newEvent) => {
  if (newEvent) processEvent(newEvent)
}, { deep: true })

// Belt-and-suspenders: Direct handler when mounted
onMounted(() => {
  socketService.on('event:type', processEvent)
})
```

**Why**: Vuetify's `v-window-item` lazy-loads components. If event fires while component unmounted, direct WebSocket handler misses it. Parent handler + provide/inject ensures events always captured.

---

### Pattern 3: Prop Update via Event Emission
```javascript
// Child component (modifies backend state):
const emit = defineEmits(['value-changed'])

async function updateValue() {
  const newValue = await api.patch('/endpoint', { value: newValue })
  emit('value-changed', newValue)  // ✅ Notify parent
}

// Parent component (owns prop):
function handleValueChanged(newValue) {
  props.object.property = newValue  // ✅ Update prop directly
}
```

**Why**: Vue allows mutating object properties passed as props. This avoids full API refetch while keeping parent's data fresh.

---

### Pattern 4: Idempotent Alembic Migrations
```python
# ✅ CORRECT - Safe for existing deployments
def upgrade():
    op.execute("""
        ALTER TABLE table_name
        ADD COLUMN IF NOT EXISTS column_name TYPE;
    """)

# ❌ WRONG - Fails if column exists
def upgrade():
    op.add_column('table_name', sa.Column('column_name', TYPE))
```

**Why**: Production databases may have manual schema changes or partial migrations. `IF NOT EXISTS` makes migration idempotent (safe to run multiple times).

---

## Lessons Learned

### 1. WebSocket Singleton Access
**Issue**: Importing `ws_manager` directly from `api.websocket` failed.

**Lesson**: Always retrieve singletons from `request.app.state` in FastAPI endpoints. Centralized initialization in `api/app.py` ensures single source of truth.

**Pattern**:
```python
# api/app.py (initialization)
app.state.websocket_manager = WebSocketManager()

# Endpoints (access)
ws_manager = getattr(request.app.state, "websocket_manager", None)
```

---

### 2. Vue Lazy-Loading with WebSockets
**Issue**: Components on inactive tabs don't receive WebSocket events.

**Lesson**: For critical events, register handler at parent level (always mounted) AND use provide/inject to pass events to children.

**Anti-Pattern**: Relying solely on `onMounted()` WebSocket handlers in lazy-loaded components.

**Best Practice**: Belt-and-suspenders approach (parent + child handlers).

---

### 3. API Response Schema Completeness
**Issue**: Database updated but API response missing new fields.

**Lesson**: When adding database columns, **always update**:
1. SQLAlchemy model (`models.py`)
2. Alembic migration (`migrations/versions/`)
3. Pydantic response schema (`schemas.py` or inline)
4. API response conversion function (`_convert_to_response()`)

**Checklist**:
```
[ ] Database column added
[ ] Migration created and tested
[ ] Response schema includes new field
[ ] API endpoint returns new field
[ ] Frontend component receives new field
```

---

### 4. Prop Staleness in Event-Driven UIs
**Issue**: Backend updates succeed but UI shows stale data from initial page load.

**Lesson**: When child components modify backend state, emit events so parent can update props. Avoids full API refetch while keeping data fresh.

**Pattern**: Child emits → Parent updates prop → Child sees fresh data via prop reactivity.

---

## Next Steps for Future Developers

### If Handover 0335 Needs Extension:
1. **Export History Tracking**: Add `export_history` JSONB column to track all exports (timestamps, types, counts)
2. **Bulk Export Actions**: Add "Export All" button that updates all templates at once
3. **Export Notifications**: Show toast notification when export completes (via WebSocket event)
4. **CLI Mode Enforcement**: Add backend validation that rejects spawning calls with invalid agent_name patterns

### If Working on Related Features:
1. **Template Versioning**: Track template versions and allow rollback (see `may_be_stale` pattern as foundation)
2. **Export Analytics**: Show metrics like "Most Exported Template" or "Templates Never Exported"
3. **Automated Export**: Trigger export automatically when template updated (configurable setting)

---

## Architecture Context (Critical Knowledge)

### Multi-Tenant Isolation
- Every API endpoint filters by `tenant_key` (extracted from JWT token)
- WebSocket events scoped to tenant (no cross-tenant leakage)
- Export flows respect tenant isolation (only export user's templates)

### Thin Client Architecture
- Orchestrator prompts are **thin** (~450-550 tokens)
- Full mission fetched via `get_orchestrator_instructions()` MCP tool
- Context pulled dynamically based on user's Priority × Depth configuration
- Export tracking supports this (templates must be in CLI for MCP tool access)

### Belt-and-Suspenders Philosophy
- CLI mode rules in **both** pasted prompt AND MCP tool response
- WebSocket handlers in **both** parent AND child components
- Export timestamps updated in **all three** export flows

**Why**: Redundancy ensures system works even if one path fails. Critical for production reliability.

---

## Conclusion

**Handover 0335 Status**: COMPLETE ✅

This session transformed template export from a "fire and forget" operation into a fully tracked, real-time system with:
- Database persistence of export history
- Real-time UI updates via WebSocket events
- Visual staleness indicators for modified templates
- Robust error handling and cross-component communication

The four bug fixes discovered during testing demonstrate the value of comprehensive end-to-end validation. Each fix has been documented with patterns for future reference.

**All functionality verified and production-ready.**

---

**Document Version**: 1.0
**Created**: 2025-12-09
**Last Updated**: 2025-12-09
**Author**: Documentation Manager Agent
**Related Handover**: handovers/0335_CLI_MODE_AGENT_TEMPLATE_VALIDATION.md
