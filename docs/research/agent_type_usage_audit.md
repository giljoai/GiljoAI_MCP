# Agent Type Usage Audit - Comprehensive Report

**Date**: 2026-01-10
**Purpose**: Document all usages of `agent_type` in MCP tools, prompt generation, and orchestrator code
**Context**: Researching whether `agent_type` can be removed or is semantically necessary

---

## Executive Summary

After comprehensive search, `agent_type` is used in **4 primary contexts**:

1. **Database field** (AgentExecution.agent_type) - Stores agent category/role
2. **MCP tool parameters** - Required parameter in spawn_agent_job and other coordination tools
3. **Prompt framing** - Included in thin client prompts and mission responses
4. **UI display** - Used for avatar colors, grouping, and categorization

**Key Finding**: `agent_type` is **NOT** embedded in agent prompts in a way that would affect behavior. It appears in:
- Tool **responses** (get_agent_mission, spawn_agent_job return values)
- Tool **metadata** (WebSocket events, status returns)
- **Framing/documentation** sections explaining the distinction to orchestrators

---

## 1. MCP Tool Usage

### 1.1 spawn_agent_job (Primary Tool)

**File**: `src/giljo_mcp/tools/orchestration.py`

**Lines 755-757** - MCP tool signature:
```python
async def spawn_agent_job(
    agent_type: str,
    agent_name: str,
    mission: str,
```

**Lines 801-803** - Docstring parameter:
```
Args:
    agent_type: Type of agent (backend-tester, frontend-dev, etc.)
    agent_name: Human-readable name for the agent
```

**Line 896** - Database storage (maps to job_type):
```python
job_type=agent_type,  # AgentJob uses job_type
```

**Line 914** - AgentExecution creation:
```python
agent_type=agent_type,
```

**Lines 926** - Thin prompt generation (NOT sent to agent):
```python
thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type}) for Project "{project.name}".
```

**Lines 980, 988** - Return value and WebSocket event:
```python
"agent_type": agent_type,
```

**Lines 1004-1009** - Handover 0383 warning logic:
```python
# Handover 0383 Option C: Warning when agent_name != agent_type
if agent_name != agent_type:
    response["warning"] = (
        f"agent_name '{agent_name}' differs from agent_type '{agent_type}'. "
        "Task tool MUST use agent_name (template filename), NOT agent_type."
    )
```

**Usage Type**: Required parameter, stored in database, returned in response metadata

---

### 1.2 get_agent_mission (Agent Reads Mission)

**File**: `src/giljo_mcp/tools/orchestration.py`

**Lines 653-654** - Return value (mission response):
```python
"agent_name": agent_execution.agent_name or agent_execution.agent_type,
"agent_type": agent_execution.agent_type,
```

**Lines 2431-2432** - Duplicate implementation (second version):
```python
"agent_name": agent_execution.agent_name or agent_execution.agent_type,
"agent_type": agent_execution.agent_type,
```

**Usage Type**: **RETURNED IN AGENT MISSION RESPONSE** - Agents receive this metadata

---

### 1.3 get_orchestrator_instructions (Orchestrator Reads Context)

**File**: `src/giljo_mcp/tools/tool_accessor.py`

**Lines 819-820** - Available agents framing (documentation section):
```python
"agent_type_usage": "Display category label for UI only (e.g., 'implementer').",
"task_tool_mapping": "Task(subagent_type=X) where X = agent_name from spawn_agent_job.",
```

**Usage Type**: Framing/documentation explaining the distinction

---

### 1.4 Other MCP Tools

**File**: `src/giljo_mcp/tools/agent_coordination.py`

**Lines 76, 94** - spawn_agent (legacy coordination tool):
```python
async def spawn_agent(
    job_id: str,
    agent_type: str,  # Parameter
```

**Lines 178, 182** - AgentExecution creation:
```python
agent_type=agent_type,
agent_name=f"{agent_type.title()} #{instance_number}",
```

**Lines 294, 343, 359** - get_agent_execution return values:
```python
"agent_type": str,
```

**Lines 444, 460, 472** - get_team_roster return values:
```python
"agent_type": str (agent role),
```

**Lines 539, 547, 556** - get_pending_jobs:
```python
def get_pending_jobs(agent_type: str, tenant_key: str) -> Dict[str, Any]:
    """Get pending jobs assigned to this agent type."""
```

**Usage Type**: Legacy coordination APIs, metadata in returns

---

**File**: `src/giljo_mcp/tools/agent_job_status.py`

**Lines 250, 342** - Status return values:
```python
- agent_type: Type of agent (orchestrator, implementer, etc.)
```

---

**File**: `src/giljo_mcp/tools/context.py`

**Lines 1417, 1481, 1915, 1983** - Context tracking return values:
```python
"agent_type": execution.agent_type,
```

---

**File**: `src/giljo_mcp/tools/project.py`

**Line 460** - Workflow status return:
```python
"agent_type": execution.agent_type,
```

---

## 2. Prompt Generation & Orchestrator Code

### 2.1 ThinClientPromptGenerator (Orchestrator Prompts)

**File**: `src/giljo_mcp/thin_prompt_generator.py`

**Lines 194, 252** - Database queries (checking for orchestrator type):
```python
AgentExecution.agent_type == "orchestrator",
```

**Lines 288-289** - AgentExecution creation:
```python
agent_type="orchestrator",
agent_name=f"Orchestrator #{instance_number}",
```

**Lines 501, 625, 642** - MCP tool examples in staging prompt:
```python
✓ spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)
```

**Lines 1008-1015** - CLI mode rules (FRAMING - explains distinction):
```python
- agent_name: SINGLE SOURCE OF TRUTH - must EXACTLY match template name
- agent_type: Display category label (e.g., "implementer")

Example Task call (IMPLEMENTATION PHASE ONLY - not during staging):
  Task(subagent_type="{agent_name}", instructions="...")

In implementation phase, Task(subagent_type=X) uses agent_name value, NOT agent_type.
```

**Lines 1075** - Staging workflow step 5:
```python
agent_type can be descriptive category (for UI display only)
```

**Lines 1219, 1233, 1247** - Agent roster framing (implementation phase):
```python
# SECTION 2: Agent Jobs List (with CRITICAL agent_type field)
f"   - Agent Type: `{agent.agent_type}` (display category)"
"Each has a unique job_id and agent_type."
```

**Lines 1260, 1284** - Task tool examples:
```python
'    subagent_type="{agent_name}",  # CRITICAL: Use agent_name (template filename)'
```

**Lines 1366-1369** - Warning section:
```python
"- Task tool parameter `subagent_type` expects `agent_name`, NOT `agent_type`"
'- agent_name: Template filename (see allowed_agent_names in instructions)'
'- agent_type: Display category (e.g., "implementer")'
'- Using agent_type will fail with "Subagent type not found"'
```

**Usage Type**: FRAMING/DOCUMENTATION - Explains the distinction, NOT sent as instructions to agents

---

### 2.2 OrchestratorSuccession

**File**: `src/giljo_mcp/orchestrator_succession.py`

**Line 208** - Successor creation:
```python
agent_type=current_execution.agent_type,
```

**Line 443** - Message formatting:
```python
"type": msg.get("agent_type", "unknown"),
```

**Usage Type**: Database field propagation during succession

---

## 3. Template Management & Export

### 3.1 Template Validator

**File**: `src/giljo_mcp/validation/template_validator.py`

**Lines 77, 105, 114** - Validation function signature:
```python
def validate(
    template_content: str,
    template_id: str,
    agent_type: str,  # Type of agent (orchestrator, implementer, etc.)
```

**Lines 132, 166, 173, 182** - Validation execution:
```python
errors, warnings = self._run_all_rules(template_content, agent_type)
```

**Usage Type**: Validation context (NOT used for behavior, only validation rules)

---

### 3.2 Template Seeder

**File**: `src/giljo_mcp/template_seeder.py`

**Lines 752, 812, 957** - MCP tool examples in template content:
```python
- `mcp__giljo-mcp__get_next_instruction(job_id, agent_type, tenant_key)`
```

**Usage Type**: Documentation/examples in template files

---

### 3.3 Export (/gil_get_claude_agents)

**No direct `agent_type` usage found in export code**

---

## 4. Handover Documentation

### 4.1 Handover 0351 - Agent Name Single Source of Truth

**File**: `handovers/completed/0351_agent_name_single_source_of_truth-C.md`

**Key Decision (Line 14)**:
```
Change the semantic meaning of `agent_name` and `agent_type` fields so that
`agent_name` becomes the single source of truth for template matching, while
`agent_type` becomes a display category.
```

**Semantic Change Table (Lines 37-41)**:
```
| Field | OLD Meaning | NEW Meaning |
|-------|-------------|-------------|
| agent_name | Display label ("Backend API Implementer") | Template filename ("implementer-frontend") |
| agent_type | Template match ("implementer") | Display category ("implementer") |
```

**Default Behavior (Lines 43-45)**:
```
- Template "implementer" (no suffix) → agent_name="implementer", agent_type="implementer"
- Template "implementer-frontend" → agent_name="implementer-frontend", agent_type="implementer"
```

**Usage Type**: Design decision - `agent_type` reduced to display/UI category

---

### 4.2 Handover 0383 - Spawn Response Task Tool Clarity

**File**: `handovers/completed/0383_spawn_response_task_tool_clarity-C.md`

**Problem Statement (Line 14)**:
```
Alpha testing revealed that orchestrators may confuse `agent_name` (template filename)
with `agent_type` (UI category) when writing execution plans.
```

**Solution - Option C (Lines 66-74)**:
```python
# Warning when agent_name != agent_type
response = {
    "job_id": "uuid-here",
    "agent_name": "implementer-frontend",
    "agent_type": "implementer",
    "warning": "agent_name 'implementer-frontend' differs from agent_type 'implementer'. Task tool MUST use agent_name."
}
```

**Usage Type**: Metadata warning to prevent orchestrator confusion

---

## 5. Is agent_type in Agent Prompts?

### Answer: NO (with caveats)

**NOT in agent instructions**: `agent_type` does NOT appear in the core mission/instructions sent to agents.

**DOES appear in**:
1. **get_agent_mission() response** (Line 654 in orchestration.py):
   - Agents receive `agent_type` as metadata in the mission payload
   - BUT this is separate from the actual mission instructions

2. **Thin client prompt header** (Line 926 in orchestration.py):
   ```python
   thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type}) for Project "{project.name}"."""
   ```
   - This is the ~10 line thin prompt pasted into terminal
   - NOT the full mission (which is fetched via get_agent_mission)

3. **Orchestrator framing sections**:
   - Staging prompts explain the `agent_name` vs `agent_type` distinction
   - Implementation prompts include agent roster with both fields
   - These are DOCUMENTATION/FRAMING, not behavioral instructions

**Conclusion**: `agent_type` is metadata that agents receive but don't act upon. It's used for:
- UI categorization (avatar colors, grouping)
- Database organization
- Orchestrator understanding (so they know agent_name != agent_type)
- Warning generation (when fields differ)

---

## 6. Can agent_type Be Removed?

### Technical Feasibility: YES
- Database could use only `agent_name`
- UI could derive categories from agent_name parsing (e.g., "implementer-frontend" → "implementer")
- MCP tools could accept only `agent_name`

### Architectural Reasons to KEEP:

1. **Explicit Categorization**:
   - `agent_type` provides explicit role categorization independent of naming
   - Template "custom-backend-specialist" might have `agent_type="implementer"`
   - Avoids parsing/guessing logic

2. **UI Consistency**:
   - Avatar colors based on `agent_type` (implementer=blue, tester=green, etc.)
   - Grouping in Template Manager by type
   - Filtering/searching by role

3. **Orchestrator Clarity**:
   - Framing/documentation sections use `agent_type` to explain the distinction
   - Warnings when `agent_name != agent_type` prevent Task tool errors
   - Explicit separation helps prevent confusion

4. **Database Semantics**:
   - `AgentExecution.agent_type` is role/category
   - `AgentExecution.agent_name` is instance identifier
   - Aligns with two-dimensional model (WHO = role, WHICH = instance)

5. **Backward Compatibility**:
   - Existing agents with `agent_type` = `agent_name` continue working
   - Removal would require database migration and UI refactor

---

## 7. Recommendation

**KEEP `agent_type` as a semantic field** for the following reasons:

1. **Not causing prompt bloat**: It appears only in metadata, not behavioral instructions
2. **Serves clear UI purpose**: Categorization, coloring, grouping
3. **Prevents orchestrator errors**: Explicit distinction reduces Task tool confusion
4. **Minimal cost**: ~50 tokens across all prompts (one field in responses)
5. **Clear semantics**: Role vs Instance separation is architecturally sound

**If removal is desired**, the alternative is:
- Parse `agent_name` to extract role prefix (e.g., "implementer-frontend" → "implementer")
- Store only `agent_name` in database
- Derive `agent_type` dynamically in UI/API responses
- Remove `agent_type` parameter from spawn_agent_job

**Trade-off**: Savings of ~50 tokens per orchestrator vs increased parsing logic and potential naming constraints

---

## 8. Files with agent_type Usage

### Core MCP Tools:
- `src/giljo_mcp/tools/orchestration.py` (19 occurrences)
- `src/giljo_mcp/tools/agent_coordination.py` (15 occurrences)
- `src/giljo_mcp/tools/tool_accessor.py` (5 occurrences)
- `src/giljo_mcp/tools/context.py` (4 occurrences)
- `src/giljo_mcp/tools/agent_job_status.py` (2 occurrences)
- `src/giljo_mcp/tools/project.py` (1 occurrence)
- `src/giljo_mcp/tools/agent_coordination_external.py` (8 occurrences)

### Prompt Generation:
- `src/giljo_mcp/thin_prompt_generator.py` (20 occurrences)
- `src/giljo_mcp/orchestrator_succession.py` (2 occurrences)

### Template Management:
- `src/giljo_mcp/validation/template_validator.py` (6 occurrences)
- `src/giljo_mcp/template_seeder.py` (3 occurrences)

### Handovers:
- `handovers/completed/0351_agent_name_single_source_of_truth-C.md` (50+ occurrences)
- `handovers/completed/0383_spawn_response_task_tool_clarity-C.md` (15+ occurrences)

---

## 9. Summary by Question

### Q1: Is agent_type embedded in agent prompts?
**A**: NO - Only in metadata/framing sections, not behavioral instructions

### Q2: Is it used in get_orchestrator_instructions?
**A**: YES - In framing/documentation explaining the distinction (Lines 819-820 in tool_accessor.py)

### Q3: Is it used in get_agent_mission?
**A**: YES - **Returned in mission response metadata** (Lines 654, 2432 in orchestration.py)

### Q4: Is it in spawn_agent_job response?
**A**: YES - Returned in response and WebSocket events (Lines 980, 988 in orchestration.py)

### Q5: Is it part of team roster/framing?
**A**: YES - Implementation phase agent roster includes `agent_type` (Lines 1233, 1247 in thin_prompt_generator.py)

### Q6: Does any MCP tool use agent_type for logic?
**A**: YES - But only for:
  - Database queries (filtering orchestrators)
  - Validation warnings (when agent_name != agent_type)
  - WebSocket event metadata
  - NOT for behavioral decision-making

---

**Audit Complete**: 2026-01-10
