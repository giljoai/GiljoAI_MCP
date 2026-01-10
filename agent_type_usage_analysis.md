# Frontend `agent_type` Usage Analysis Report

**Date**: 2026-01-10
**Scope**: Complete frontend Vue code analysis
**Finding**: `agent_type` is **PERVASIVELY COUPLED** to core UI/UX logic across components, stores, utilities, and services.

---

## Executive Summary

The field `agent_type` is NOT just a display property. Renaming it to `role` would break:
- **Avatar colors and initials** across 5 components
- **Conditional rendering logic** in 7+ components
- **Sorting and filtering** in stores
- **API request building** in services
- **WebSocket event handling**
- **Multiple utility functions** that hard-code type mappings

**Impact Assessment**: **CRITICAL** - This would require changes in 20+ files across the entire frontend codebase.

---

## Usage Categories

### 1. FUNCTIONAL (Logic & Conditionals) - CRITICAL

#### 1.1 Sorting & Filtering
- **File**: `frontend/src/stores/agentJobsStore.js` (Lines 107-111)
  - **Logic**: Orchestrators sorted FIRST by design (priority logic)
  - **Code**:
    ```javascript
    const aIsOrchestrator = a.agent_type === 'orchestrator' ? 0 : 1
    const bIsOrchestrator = b.agent_type === 'orchestrator' ? 0 : 1
    if (aIsOrchestrator !== bIsOrchestrator) return aIsOrchestrator - bIsOrchestrator
    return (a.agent_type || '').localeCompare(b.agent_type || '')
    ```
  - **Purpose**: Ensures orchestrators always appear first in UI lists

- **File**: `frontend/src/stores/agentJobs.js` (Lines 55-58)
  - **Logic**: Table filtering by agent type
  - **Code**:
    ```javascript
    if (tableFilters.value.agent_type.length) {
      filtered = filtered.filter((a) =>
        tableFilters.value.agent_type.includes(a.agent_type),
      )
    }
    ```
  - **Purpose**: Users can filter by agent type in the UI

- **File**: `frontend/src/composables/useAgentData.js` (Lines 46-47)
  - **Logic**: Sorting priority for orchestrators
  - **Code**:
    ```javascript
    if (a.agent_type === 'orchestrator') return -1
    if (b.agent_type === 'orchestrator') return 1
    ```

#### 1.2 Action Availability Logic (Claude Code CLI Mode)
- **File**: `frontend/src/utils/actionConfig.js` (Lines 114, 139, 188, 205)
  - **Logic**: Determines which actions are available based on agent type
  - **Key Functions**:
    - `shouldShowLaunchAction()` - Only orchestrator can launch in CLI mode (Line 114)
    - `shouldShowHandOverAction()` - Only orchestrator can hand over (Line 139)
    - `getActionReasons()` - Validates launch action only for orchestrator (Line 188)
    - `getActionDisabledReason()` - Only orchestrator can hand over (Line 205)

- **File**: `frontend/src/components/orchestration/AgentCardGrid.vue` (Lines 173, 193)
  - **Logic**: Claude Code mode checks
  - **Code**:
    ```javascript
    if (props.usingClaudeCodeSubagents) {
      return agent.is_orchestrator || agent.agent_type === 'orchestrator'
    }
    ```
  - **Purpose**: Restricts actions to orchestrator in Claude Code CLI mode

#### 1.3 Conditional Rendering
- **File**: `frontend/src/components/projects/JobsTab.vue` (Line 211)
  - **Logic**: Hand Over button only shows for orchestrators
  - **Code**:
    ```javascript
    v-if="agent.agent_type === 'orchestrator' && ['working', 'complete', 'completed'].includes(agent.status)"
    ```

- **File**: `frontend/src/components/projects/LaunchTab.vue` (Lines 240-241, 251)
  - **Logic**: Filter agents for non-orchestrators, filter orchestrators separately
  - **Code**:
    ```javascript
    const nonOrchestratorAgents = computed(() => {
      return sortedJobs.value.filter((agent) => agent.agent_type !== 'orchestrator')
    })

    const orchestrators = sortedJobs.value
      .filter((agent) => agent.agent_type === 'orchestrator')
      .sort((a, b) => (b.instance_number || 0) - (a.instance_number || 0))
    ```

- **File**: `frontend/src/components/projects/AgentDetailsModal.vue` (Line 313)
  - **Logic**: Different UI for orchestrators
  - **Code**:
    ```javascript
    const isOrchestrator = computed(() => {
      return props.agent?.agent_type === 'orchestrator'
    })
    ```

- **File**: `frontend/src/components/projects/LaunchTab.vue` (Line 448)
  - **Logic**: Orchestrators have no editable missions
  - **Code**:
    ```javascript
    if (agent.agent_type === 'orchestrator') {
      // Orchestrators don't have editable missions
    }
    ```

#### 1.4 CLI Mode Implementation
- **File**: `frontend/src/components/projects/JobsTab.vue` (Lines 749-750)
  - **Logic**: Generates different prompt for orchestrators in CLI mode
  - **Code**:
    ```javascript
    if (agent.agent_type === 'orchestrator') {
      // CLI mode: Generate implementation prompt
    }
    ```
  - **Purpose**: Special handling for orchestrator orchestration workflow

---

### 2. DISPLAY (UI Labels, Colors, Avatars) - CRITICAL

#### 2.1 Avatar Colors & Initials (Hard-Coded Mappings)

**File**: `frontend/src/components/projects/JobsTab.vue` (Lines 571-599)
- **Hard-Coded Color Palette**:
  ```javascript
  function getAgentColor(agentType) {
    const colors = {
      orchestrator: '#D4A574', // Tan/Beige - Project coordination
      analyzer: '#E74C3C', // Red - Analysis & research
      implementer: '#3498DB', // Blue - Code implementation
      implementor: '#3498DB', // Blue - Code implementation (alias)
      tester: '#FFC300', // Yellow - Testing & QA
      reviewer: '#9B59B6', // Purple - Code review
      documenter: '#27AE60', // Green - Documentation
      researcher: '#27AE60', // Green - Research (alias)
    }
  }

  function getAgentAbbr(agentType) {
    const abbrs = {
      orchestrator: 'OR',
      analyzer: 'AN',
      implementer: 'IM',
      implementor: 'IM',
      tester: 'TE',
      reviewer: 'RV',
      documenter: 'DO',
      researcher: 'RE',
    }
  }
  ```
- **Used in**:
  - Line 26: Avatar color
  - Line 27: Avatar text (initials)

**File**: `frontend/src/components/projects/LaunchTab.vue` (Lines 285-315)
- **Identical Color Mapping** (Code duplication!)
- **Used in**:
  - Line 122: Avatar background
  - Line 123: Avatar text

**File**: `frontend/src/composables/useAgentData.js` (Lines 97-124)
- **Centralized but Different Colors** (inconsistency!)
  ```javascript
  const getAgentTypeColor = (agentType) => {
    const colors = {
      orchestrator: 'orange',
      analyzer: 'red',
      implementer: 'blue',
      tester: 'yellow',
      reviewer: 'purple',
    }
  }

  const getAgentAbbreviation = (agentType) => {
    const abbr = {
      orchestrator: 'Or',
      analyzer: 'An',
      implementer: 'Im',
      tester: 'Te',
      reviewer: 'Re',
    }
  }
  ```
- **Used in**:
  - `AgentTableView.vue` (Lines 14, 16)
  - `AgentCardGrid.vue` (via import)

#### 2.2 Components Using agent_type for Display

| File | Line(s) | Usage | Purpose |
|------|---------|-------|---------|
| `JobsTab.vue` | 23, 26-27, 30, 35 | Avatar color, initials, label | Display agent avatar in table |
| `JobsTab.vue` | 281, 311-312, 314 | Agent details modal display | Show agent type in details |
| `LaunchTab.vue` | 120-126 | Agent card avatar & name | Display agent in slim card |
| `LaunchTab.vue` | 345-348 | Instance number calculation | Determine agent instance |
| `LaunchTab.vue` | 426 | Mock data | Initialize orchestrator object |
| `AgentCard.vue` | 5 | CSS class binding | Style card by agent type |
| `AgentCard.vue` | 15 | Agent type label display | Header text |
| `AgentCard.vue` | 447 | Computed property for color | Card styling |
| `AgentTableView.vue` | 14, 16, 20, 25 | Avatar in table, agent name | Display in table view |
| `AgentDetailsModal.vue` | 23 | Agent chip display | Show agent type badge |
| `SuccessionTimeline.vue` | 33 | Instance type label | Succession timeline |
| `MessageAuditModal.vue` | 245 | Agent label display | Message audit label |

#### 2.3 CSS Classes Generated from agent_type
- **File**: `AgentCard.vue` (Line 5)
  - **Code**: `:class="['agent-card--' + agent.agent_type, ...]"`
  - **Purpose**: Dynamic CSS classes for styling different agent types

#### 2.4 Data Attributes for Testing/Styling
- **File**: `JobsTab.vue` (Line 23)
  - **Code**: `:data-agent-type="agent.agent_type"`
  - **Purpose**: HTML data attribute for E2E testing

- **File**: `LaunchTab.vue` (Line 120)
  - **Code**: `:data-agent-type="agent.agent_type"`

---

### 3. API & SERVICE LAYER - MODERATE

#### 3.1 WebSocket Event Handling
- **File**: `frontend/src/stores/websocketEventRouter.js` (Lines 122, 127, 138, 142)
  - **Logic**: Agent health alerts include agent_type
  - **Code**:
    ```javascript
    const { health_state, agent_type, issue_description } = payload
    message: `${agent_type} - ${issue_description}`
    ```
  - **Purpose**: Display agent type in health notifications

- **File**: `frontend/src/composables/useStalenessMonitor.js` (Line 43, 46)
  - **Logic**: Staleness notifications include agent_type
  - **Code**:
    ```javascript
    message: `${job.agent_name || job.agent_type} has been inactive for over 10 minutes`
    agent_type: job.agent_type
    ```

#### 3.2 Message Handling
- **File**: `frontend/src/components/projects/MessageStream.vue` (Line 223)
  - **Logic**: Extract agent type from messages
  - **Code**:
    ```javascript
    function getAgentType(message) {
      return message.agent_type || message.from_agent || 'orchestrator'
    }
    ```

- **File**: `frontend/src/components/projects/MessageInput.vue` (Lines 108, 136)
  - **Logic**: Display agent type in dropdown labels
  - **Code**:
    ```javascript
    const agentType = agent.agent_type || 'Unknown'
    const label = `${agentType} (Instance ${instanceNum}) - ${truncatedId}`
    ```

#### 3.3 Logging & Debugging
- **File**: `JobsTab.vue` (Lines 806, 835, 845)
  - **Logic**: Console logging for debugging
  - **Code**:
    ```javascript
    console.log('[JobsTab] Messages action:', agent.agent_type)
    console.log('[JobsTab] Agent role action:', agent.agent_type)
    console.log('[JobsTab] Agent job action:', agent.agent_type)
    ```

---

## IMPACT ASSESSMENT: Renaming `agent_type` → `role`

### What Would Break

| Category | Count | Impact | Severity |
|----------|-------|--------|----------|
| **Functional Logic** | 12+ | Sorting, filtering, CLI mode, conditionals | CRITICAL |
| **Color/Avatar Mappings** | 3 functions | Avatar display, 2 files with duplication | CRITICAL |
| **Display Components** | 8+ | Agent cards, tables, modals, timelines | HIGH |
| **WebSocket/Services** | 5+ | Event handling, notifications, logging | MODERATE |
| **Test Files** | 10+ | Data attributes, test expectations | MODERATE |

### Files Requiring Changes

```
CRITICAL (Must change):
  ✓ frontend/src/utils/actionConfig.js (Lines 114, 139, 188, 205)
  ✓ frontend/src/stores/agentJobsStore.js (Lines 107-111)
  ✓ frontend/src/stores/agentJobs.js (Lines 55-58, 155, 30)
  ✓ frontend/src/composables/useAgentData.js (Lines 46-47, 97-124)
  ✓ frontend/src/components/projects/JobsTab.vue (Lines 23, 26-27, 30, 35, 211, 571-599, 749, 806, 835, 845)
  ✓ frontend/src/components/projects/LaunchTab.vue (Lines 120-126, 240-241, 251, 285-315, 345-348, 426, 448)
  ✓ frontend/src/components/projects/AgentDetailsModal.vue (Lines 22-24, 313, 355)
  ✓ frontend/src/components/orchestration/AgentCardGrid.vue (Lines 173, 193)
  ✓ frontend/src/components/orchestration/AgentTableView.vue (Lines 14, 16, 20, 25, 180-181)
  ✓ frontend/src/components/AgentCard.vue (Lines 5, 15, 447)

HIGH IMPACT (Visual/UX):
  ✓ frontend/src/components/projects/SuccessionTimeline.vue (Line 33)
  ✓ frontend/src/components/projects/MessageAuditModal.vue (Line 245)
  ✓ frontend/src/components/StatusBoard/ActionIcons.vue (Line 161 - mock data)

MODERATE (Tests & Utilities):
  ✓ frontend/src/stores/websocketEventRouter.js (Lines 122, 127, 138, 142)
  ✓ frontend/src/composables/useStalenessMonitor.js (Lines 43, 46)
  ✓ frontend/src/components/projects/MessageStream.vue (Line 223)
  ✓ frontend/src/components/projects/MessageInput.vue (Lines 108, 136)
  ✓ Multiple test files (*.spec.js)
```

---

## Detailed Findings

### Finding 1: Multiple Hard-Coded Color Mappings

**Problem**: Three different places maintain color mappings for agent types:
1. `JobsTab.vue` (Hex colors: #D4A574, #E74C3C, etc.)
2. `LaunchTab.vue` (Same hex colors - DUPLICATED)
3. `useAgentData.js` (Vuetify colors: orange, red, blue - INCONSISTENT)

**Risk**: Different components display different colors for the same agent type.

**Recommendation**: Centralize in a single utility file (e.g., `frontend/src/utils/agentTypeConfig.js`).

### Finding 2: No Centralized agent_type Constants

**Problem**: Agent type values are hard-coded throughout:
- "orchestrator" appears 30+ times
- "analyzer", "implementer", "tester", etc. appear multiple times

**Risk**: Typos could break filtering/sorting logic.

**Recommendation**: Create `frontend/src/utils/agentTypeConstants.js`:
```javascript
export const AGENT_TYPES = {
  ORCHESTRATOR: 'orchestrator',
  ANALYZER: 'analyzer',
  IMPLEMENTER: 'implementer',
  TESTER: 'tester',
  REVIEWER: 'reviewer',
  DOCUMENTER: 'documenter',
  RESEARCHER: 'researcher',
}

export const AGENT_TYPE_COLORS = {
  orchestrator: '#D4A574',
  analyzer: '#E74C3C',
  // ...
}

export const AGENT_TYPE_ABBRS = {
  orchestrator: 'OR',
  analyzer: 'AN',
  // ...
}
```

### Finding 3: CLI Mode Logic is Deeply Coupled

**Problem**: Claude Code CLI mode checks for `agent_type === 'orchestrator'` in:
- `actionConfig.js` - Determines available actions
- `AgentCardGrid.vue` - Restricts launches
- `AgentTableView.vue` - Restricts copies
- `JobsTab.vue` - Generates special prompts

**Risk**: If orchestrator type name changes, entire CLI mode breaks.

**Recommendation**: Use centralized constant `AGENT_TYPES.ORCHESTRATOR` instead of string literals.

---

## Answers to Key Questions

### Q1: Is agent_type used to determine badge colors?
**YES** - Extensively.
- `JobsTab.vue`: Lines 26-27 (avatar color and initials)
- `LaunchTab.vue`: Lines 122-123 (avatar styling)
- `useAgentData.js`: Lines 97-106 (color mapping)
- `AgentTableView.vue`: Lines 14, 16 (table cell avatar)

### Q2: Is it used for avatar generation?
**YES** - Every agent display uses it.
- `JobsTab.vue`: Lines 26-27 `<v-avatar :color="getAgentColor(agent.agent_type)">`
- `LaunchTab.vue`: Lines 122-123 generates color from `agent.agent_type`
- `AgentTableView.vue`: Lines 14-16 displays avatar with type-based color
- `AgentCard.vue`: Computed color property (Line 447)

### Q3: Is it used in filtering/sorting logic?
**YES** - Critical to data flow.
- **Sorting**: `agentJobsStore.js` (Lines 107-111), `useAgentData.js` (Lines 46-47)
  - Orchestrators always sort first
- **Filtering**: `agentJobs.js` (Lines 55-58)
  - Users can filter by agent_type in table
- **Separation**: `LaunchTab.vue` (Lines 240-251)
  - Non-orchestrators vs orchestrators displayed separately

### Q4: What components display agent_type?
**8+ Components**:
1. `JobsTab.vue` - Main status table
2. `LaunchTab.vue` - Agent launch cards
3. `AgentCard.vue` - Agent status cards
4. `AgentTableView.vue` - Alternative table view
5. `AgentDetailsModal.vue` - Agent details popup
6. `AgentCardGrid.vue` - Grid layout
7. `SuccessionTimeline.vue` - Succession history
8. `MessageAuditModal.vue` - Message audit display

### Q5: What would break if we renamed to `role`?
**Everything**:
- Avatar colors wouldn't display (color mappings keyed by agent_type)
- Filtering would fail (filter logic checks agent_type value)
- Sorting would break (orchestrators not sorted first)
- CLI mode would fail (action restrictions check for 'orchestrator')
- Hand Over buttons wouldn't appear (conditional on agent_type === 'orchestrator')
- Tests would fail (data-agent-type attributes checked)

---

## Conclusion

**Status**: `agent_type` is **DEEPLY WOVEN** into the frontend architecture.

**Recommendation**: **DO NOT RENAME** without:
1. Creating centralized agent type constants
2. Consolidating color/abbreviation mappings
3. Comprehensive refactoring across 20+ files
4. Full E2E test coverage to verify sorting/filtering/CLI mode
5. Visual regression testing for avatar colors

**If rename is absolutely necessary**: Expect 2-3 days of work with high risk of breaking critical workflows (CLI mode, sorting, filtering, avatar display).

---

# Backend `agent_type` Usage Analysis Report

**Date**: 2026-01-10
**Scope**: Complete backend Python code analysis
**Finding**: `agent_type` is used for **BOTH functional logic AND display/identification**

---

## Executive Summary (Backend)

**Finding**: `agent_type` is used for:
1. **FUNCTIONAL LOGIC** (8+ critical locations) - Orchestrator detection, health monitoring, dependency resolution
2. **DATABASE FILTERING** (10+ locations) - Query filtering and grouping
3. **DISPLAY/LOGGING** (Pervasive) - API responses, log messages, documentation

**Impact of Rename**: **HIGH** - Requires:
- Database migration (`agent_type` column → `role`)
- API contract updates (Pydantic schemas)
- Functional logic updates (8+ files)
- Configuration updates (health timeouts, dependency rules)

**Recommendation**: Proceed with rename but plan for comprehensive testing of orchestrator-specific logic.

---

## Database Schema

### Primary Usage: AgentExecution Model
```python
# src/giljo_mcp/models/agent_identity.py:170
agent_type = Column(
    String(100),
    nullable=False,
    comment="Agent type: orchestrator, analyzer, implementer, tester, etc.",
)
```

### Secondary Usage: AgentJob Model
```python
# src/giljo_mcp/models/agent_identity.py:75
job_type = Column(
    String(100),
    nullable=False,
    comment="Type of job (orchestrator, analyzer, implementer, tester, etc.)",
)
```

**Note**: `job_type` on AgentJob often maps to `agent_type` on AgentExecution.

---

## Backend Usage Categories

### 1. FUNCTIONAL - Used in Logic/Conditionals (CRITICAL)

#### 1.1 Orchestrator Detection (8+ Locations)

**Purpose**: Special handling for orchestrator agents vs other agents

| File | Line | Logic | Impact |
|------|------|-------|--------|
| `services/orchestration_service.py` | 660 | Set context_budget=200000 for orchestrators | Budget allocation |
| `services/orchestration_service.py` | 1846 | Validate only orchestrators trigger succession | Security validation |
| `tools/orchestration.py` | 835 | Prevent duplicate orchestrators in project | Duplication prevention |
| `tools/orchestration.py` | 2645 | Duplicate orchestrator check (second location) | Duplication prevention |
| `tools/orchestration.py` | 2608 | Skip template validation for orchestrators | Workflow exception |
| `api/endpoints/prompts.py` | 647 | Restrict execution prompts to orchestrators | API authorization |
| `api/endpoints/agent_jobs/succession.py` | 274, 388 | Only orchestrators can succession | Succession control |
| `api/endpoints/agent_jobs/table_view.py` | 267 | Set `is_orchestrator` flag for UI | UI state |

**Code Example**:
```python
# src/giljo_mcp/services/orchestration_service.py:660
if agent_type == "orchestrator":
    agent_execution.context_budget = 200000  # Sonnet 4.5 default
```

**Impact**: All 8 locations would need `agent_type` → `role` update.

#### 1.2 Health Monitoring Timeouts

**Purpose**: Different timeout thresholds per agent type

| File | Line | Logic |
|------|------|-------|
| `monitoring/health_config.py` | 48 | `get_timeout_for_agent(agent_type)` - lookup timeout |
| `monitoring/agent_health_monitor.py` | 310 | Fetch timeout for specific agent type |

**Timeout Configuration**:
```python
# src/giljo_mcp/monitoring/health_config.py:34
timeout_overrides: Dict[str, int] = field(default_factory=lambda: {
    "orchestrator": 15,  # Orchestrators get more time
    "analyzer": 5,
    "implementer": 10,
    "tester": 8,
    "reviewer": 6,
    "documenter": 5
})
```

**Impact**: Dictionary keys would need updating OR add alias support.

#### 1.3 Dependency Resolution

**Purpose**: Determine agent workflow dependencies (upstream/downstream)

| File | Line | Logic |
|------|------|-------|
| `services/orchestration_service.py` | 138-145 | Match agent_type against dependency_rules |

**Dependency Rules**:
```python
# src/giljo_mcp/services/orchestration_service.py:123
dependency_rules = {
    "analyzer": {"upstream": [], "downstream": ["implementer", "documenter", "tester"]},
    "implementer": {"upstream": ["analyzer"], "downstream": ["tester", "reviewer", "documenter"]},
    "tester": {"upstream": ["implementer"], "downstream": ["reviewer"]},
    "reviewer": {"upstream": ["implementer", "tester"], "downstream": ["documenter"]},
    "documenter": {"upstream": ["analyzer", "implementer", "reviewer"], "downstream": []},
}
```

**Impact**: Dictionary keys would need updating OR add alias support.

#### 1.4 Testing Context Prioritization

**Purpose**: Provide different testing context depth based on agent type

| File | Line | Logic |
|------|------|-------|
| `prompt_generation/testing_config_generator.py` | 232-238 | Full config for tester/implementer, standards for reviewer |

```python
if agent_type in ["tester", "implementer"]:
    return cls.generate_context(testing_config, priority=1)
elif agent_type in ["reviewer"]:
    return cls.generate_context(testing_config, priority=2)
```

**Impact**: Update list checks to use new field name.

#### 1.5 MCP Tool Catalog Generation

**Purpose**: Different workflow sections for orchestrators vs other agents

| File | Line | Logic |
|------|------|-------|
| `prompt_generation/mcp_tool_catalog.py` | 810-813 | Orchestrator gets full workflow, others get "Quick Start" |

```python
if agent_type == "orchestrator":
    catalog += self._generate_usage_workflow()
else:
    catalog += "## Quick Start\n\n1. Call `get_agent_mission()` to fetch your assignment\n"
```

**Impact**: Update conditional to use new field name.

#### 1.6 Message Routing

**Purpose**: Exclude sender from broadcast messages

| File | Line | Logic |
|------|------|-------|
| `services/message_service.py` | 181 | Skip sender agent_type in broadcast |
| `services/message_service.py` | 301 | Filter out sender agent_type |

```python
if execution.agent_type == sender_type:
    continue  # Skip sender
```

**Impact**: Update field name in skip logic.

---

### 2. IDENTIFICATION - Database Filtering/Matching

#### 2.1 Query Filtering (10+ Locations)

| File | Line | Purpose |
|------|------|---------|
| `agent_job_manager.py` | 656, 697 | Filter pending/active jobs by agent_type |
| `repositories/agent_job_repository.py` | 142, 277, 284 | Filter jobs by agent_type |
| `services/orchestration_service.py` | 1599 | Filter executions by agent_type |
| `api/endpoints/agent_jobs/table_view.py` | 149-151 | Filter agent jobs table |

**Pattern**: Standard WHERE clause filtering
```python
if agent_type:
    stmt = stmt.where(AgentExecution.agent_type == agent_type)
```

**Impact**: Column name change in database queries.

#### 2.2 Sorting/Grouping (2+ Locations)

| File | Line | Purpose |
|------|------|---------|
| `api/endpoints/agent_jobs/table_view.py` | 176-177 | Sort by agent_type column |
| `repositories/agent_job_repository.py` | 290 | Group by agent_type for statistics |

```python
sort_column = AgentExecution.agent_type
type_stmt = select(Job.agent_type, func.count(Job.id)).group_by(Job.agent_type)
```

**Impact**: Column name change in ORDER BY and GROUP BY clauses.

---

### 3. DISPLAY - API Responses & Logging

#### 3.1 API Response Fields (Pervasive)

| File | Line | Purpose |
|------|------|---------|
| `api/endpoints/agent_jobs/table_view.py` | 42, 249 | Return agent_type in AgentExecutionRow |
| `api/endpoints/agent_jobs/status.py` | 47, 228 | Include agent_type in job status |
| `api/schemas/agent_job.py` | 25, 58, 94 | Pydantic schema fields |
| `api/schemas/prompt.py` | 55 | Prompt response schema |

**Pydantic Schema Example**:
```python
# api/schemas/agent_job.py:25
agent_type: str = Field(
    ..., description="Agent type (orchestrator, implementer, etc.)"
)
```

**Impact**: Update Pydantic field names across all schemas.

#### 3.2 Logging/Debugging (50+ Locations)

**Pervasive throughout codebase** - Used in log messages:
```python
logger.info(f"Spawned agent: agent_type={agent_type}, project_id={project_id}")
logger.debug(f"[LIST_JOBS DEBUG] Agent {execution.agent_type} (job={job.job_id})")
```

**Impact**: Update log message variable names (cosmetic).

#### 3.3 Documentation/Prompts (5+ Locations)

| File | Line | Purpose |
|------|------|---------|
| `thin_prompt_generator.py` | 1008, 1075, 1233 | Explain agent_type vs agent_name |
| `thin_prompt_generator.py` | 1367-1369 | Warning about Task tool usage |

**Documentation Pattern**:
```python
- agent_name: SINGLE SOURCE OF TRUTH - must match template name
- agent_type: Display category label (e.g., "implementer")
```

**Impact**: Update documentation strings.

---

### 4. VALIDATION - Input Checking

| File | Line | Purpose |
|------|------|---------|
| `agent_job_manager.py` | 125, 188 | Validate agent_type not empty |
| `tools/agent_coordination.py` | 124, 578 | Validate agent_type not empty |
| `services/orchestration_service.py` | 1002 | Validate agent_type not empty |

**Pattern**: Simple null/empty checks
```python
if not agent_type or not agent_type.strip():
    return {"success": False, "error": "agent_type cannot be empty"}
```

**Impact**: Update parameter name in validation logic.

---

## Legacy Code References

### AgentRole Enum (Deprecated)
```python
# src/giljo_mcp/enums.py:9
class AgentRole(Enum):
    """Standard agent roles with predefined capabilities."""
    ORCHESTRATOR = "orchestrator"
    ANALYZER = "analyzer"
    IMPLEMENTER = "implementer"
    TESTER = "tester"
    REVIEWER = "reviewer"
```

**Usage**: Mostly in deprecated `orchestrator.py`. NOT widely used in current codebase.

**Note**: This enum uses "Role" naming, suggesting historical intent to use "role" terminology.

---

## What Would Break with agent_type → role Rename?

### ✅ SAFE (Display/Logging Only)
- Log messages (50+ locations) - cosmetic only
- Documentation strings - update references
- Comments - update terminology

### ⚠️ REQUIRES UPDATES (Functional Logic)
- **Health monitoring timeout lookup** (2 files)
  - Update `timeout_overrides` dictionary keys OR add alias
- **Dependency resolution** (1 file)
  - Update `dependency_rules` dictionary keys OR add alias
- **Testing context prioritization** (1 file)
  - Update if/elif conditions
- **MCP tool catalog generation** (1 file)
  - Update conditional check
- **Message routing** (1 file)
  - Update skip-sender logic
- **Orchestrator detection** (8 files)
  - Update all `agent_type == "orchestrator"` checks

### 🔥 CRITICAL (Database/API Contracts)
- **Database migration**
  - Rename column `agent_type` → `role` in `agent_executions` table
  - Rename column `job_type` → `role` in `agent_jobs` table (optional)
- **API schemas** (4+ files)
  - Update Pydantic models: `agent_type` → `role` in all request/response schemas
- **Query filtering** (10+ files)
  - Update WHERE, ORDER BY, GROUP BY clauses
- **MCP tool signatures** (5+ tools)
  - Update function parameters: `agent_type` → `role`
- **Frontend integration**
  - Frontend expects `agent_type` in API responses
  - See frontend analysis for 20+ file impact

---

## Recommended Migration Strategy

### Phase 1: Database Schema (Week 1)
1. **Add `role` column** to `agent_executions` table (nullable)
2. **Backfill `role`** from `agent_type` for existing records
3. **Dual-write** application code to write to both fields
4. **Deploy and monitor** - verify data consistency

### Phase 2: Application Code (Week 2)
1. **Update functional logic**
   - Add alias support to `timeout_overrides` and `dependency_rules`
   - Update orchestrator detection to check `role` first, fallback to `agent_type`
2. **Update query filters**
   - Change WHERE/ORDER BY/GROUP BY to use `role` column
3. **Update validation**
   - Change parameter names from `agent_type` to `role`
4. **Deploy and test** - comprehensive integration testing

### Phase 3: API Contracts (Week 3)
1. **Update Pydantic schemas**
   - Add `role` field to all schemas
   - Deprecate `agent_type` field (keep for backward compatibility)
2. **Update API documentation**
   - Swagger/OpenAPI specs reflect new field name
3. **Deploy with backward compatibility**
   - Return both `role` and `agent_type` in responses

### Phase 4: Frontend Migration (Week 4)
1. **Update frontend** to use `role` field (see frontend analysis)
2. **Remove `agent_type` from API responses** once frontend migrated
3. **Drop `agent_type` column** from database
4. **Full cleanup** - remove all backward compatibility code

---

## Alternative: Add Alias Without Full Rename

**Option**: Keep `agent_type` as database field but expose as `role` in API/UI

**Pros**:
- No database migration needed
- Backward compatible
- Lower risk

**Cons**:
- Code maintains confusing naming internally
- Technical debt persists
- Semantic clarity not achieved at core layer

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Database migration failure | Low | CRITICAL | Use blue-green deployment, rollback plan |
| API contract breaking change | Medium | HIGH | Phased rollout with dual-field support |
| Orchestrator logic breaks | Medium | CRITICAL | Comprehensive unit tests for all 8 locations |
| Health monitoring fails | Low | HIGH | Test with multiple agent types |
| Dependency resolution breaks | Low | MEDIUM | Integration tests for workflow dependencies |
| Frontend breaks | HIGH | CRITICAL | Full E2E test suite (see frontend analysis) |

---

## Testing Requirements

### Unit Tests (Backend)
- [ ] Orchestrator detection (8 test cases)
- [ ] Health monitoring timeouts (6 agent types)
- [ ] Dependency resolution (5 agent types)
- [ ] Testing context prioritization (3 agent types)
- [ ] Message routing (broadcast filtering)

### Integration Tests (Backend)
- [ ] Spawn orchestrator (prevent duplicates)
- [ ] Trigger succession (orchestrator-only)
- [ ] Filter jobs by role
- [ ] Sort/group by role
- [ ] API responses include `role` field

### E2E Tests (Full Stack)
- [ ] Frontend displays correct avatars (color/initials)
- [ ] Sorting works (orchestrators first)
- [ ] Filtering works (by role)
- [ ] CLI mode restrictions (orchestrator-only actions)
- [ ] Hand Over button (orchestrator-only)

---

## Conclusion (Backend)

**Agent_type is FUNCTIONALLY SIGNIFICANT** in:
1. Orchestrator detection (8+ locations)
2. Health monitoring timeouts (configurable per type)
3. Workflow dependency resolution
4. Testing context prioritization
5. Message broadcast filtering
6. MCP tool catalog generation

**Renaming agent_type → role is FEASIBLE** but requires:
- Database migration (HIGH IMPACT)
- API contract updates (HIGH IMPACT)
- Functional logic updates (MEDIUM IMPACT)
- Comprehensive testing (CRITICAL)
- Frontend coordination (see frontend analysis - 20+ files)

**Estimated Effort**:
- Backend: 1-2 weeks
- Frontend: 2-3 days
- Testing: 1 week
- **Total**: 3-4 weeks for safe, phased rollout

**Risk Level**: MEDIUM-HIGH (database migrations always carry risk)

