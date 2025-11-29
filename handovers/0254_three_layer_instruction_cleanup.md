# Handover 0254: Three-Layer Instruction Architecture Cleanup

**Date**: 2025-11-28
**Status**: READY FOR IMPLEMENTATION
**Priority**: CRITICAL
**Type**: Architectural Fix + Production Bug Fix
**Estimated Time**: 6 hours
**Builds Upon**: Handover 0246b (Generic Agent Template), 0106 (Dual-Field Templates), 0103 (Database Templates)

---

## Executive Summary

**Problem**: Three layers of agent instructions conflict with each other, causing agent confusion and errors. GenericAgentTemplate (Layer 2) contains incorrect MCP command names, and database template definitions (Layer 3) contain obsolete MCP commands that contradict the generic protocol.

**Impact**:
- Agents receive conflicting instructions across three layers
- MCP command names don't match actual tool signatures
- Database template definitions duplicate protocol but with wrong commands
- High risk of agent execution failures

**Solution**:
1. Fix all MCP command bugs in GenericAgentTemplate (Layer 2)
2. Fix database template definitions in template_seeder.py (6 base agents)
3. Remove obsolete MCP commands from database templates
4. Update orchestrator spawn prompt to reference GenericAgentTemplate (Layer 1)
5. Establish clear separation of concerns between layers

**Estimated Impact**:
- 100% reduction in MCP command errors
- Clear architectural separation (Protocol vs Role Expertise)
- Improved agent reliability and execution consistency
- Correct templates in exported agent packages

---

## User's Architecture Explanation

**Installation Flow (Correct Architecture)**:

```
1. User downloads GiljoAI MCP application
   ↓
2. Runs install.py
   ↓
3. install.py seeds PostgreSQL database with 6 base agents:
   - orchestrator (SYSTEM_MANAGED, protected from Template Manager)
   - implementer (visible in Template Manager)
   - tester (visible in Template Manager)
   - analyzer (visible in Template Manager)
   - reviewer (visible in Template Manager)
   - documenter (visible in Template Manager)
   ↓
4. Orchestrator is hidden from Agent Template Manager
   - Reason: Critical system agent, only admins can modify
   - Admin modifications happen in Admin Settings (admins only)
   ↓
5. Remaining 5 agents show in Template Manager
   - Users can toggle agents on/off (is_active field)
   ↓
6. When agent.is_active = True:
   A) Shows as available agent when orchestrator stages project mission
   B) Included in "Manual Agent Installation" ZIP download
   C) Included in agent export function
   ↓
7. Max 8 agent types can be used at any given time:
   - orchestrator (always present) + 7 user agents (max)
```

---

## Installation & Seeding Architecture

### Database Seeding Process

**File**: `src/giljo_mcp/template_seeder.py`

**Function**: `_get_default_templates_v103()` (lines 197-473)

**6 Base Agent Definitions**:
1. **orchestrator** - Master orchestrator (SYSTEM_MANAGED, admin-only)
2. **implementer** - Code implementation specialist
3. **tester** - Testing and quality assurance
4. **analyzer** - Requirements and architecture analysis
5. **reviewer** - Code review and quality checks
6. **documenter** - Documentation specialist

**Seeding Behavior** (lines 120-126):
```python
if template_def["role"] in SYSTEM_MANAGED_ROLES:
    logger.debug("Skipping system-managed template '%s' during seeding")
    continue  # Orchestrator skipped during tenant seeding
```

**Result**: Only **5 templates seeded per tenant** (orchestrator excluded as SYSTEM_MANAGED).

### Orchestrator Protection Mechanism

**Why Orchestrator is Protected**:
- Critical system agent that coordinates all other agents
- Improper modifications could break entire orchestration system
- Only system administrators should modify orchestrator behavior

**Admin Access**:
- Orchestrator template modifications available in **Admin Settings**
- Regular users see Template Manager with only 5 agents (implementer, tester, analyzer, reviewer, documenter)
- Multi-tenant isolation ensures each tenant has isolated templates

### Agent Toggle Behavior (is_active)

When `agent.is_active = True`:

**A) Available for Orchestrator Staging**:
```python
# During project staging (Task 4: Agent Discovery)
available_agents = get_available_agents(tenant_key, active_only=True)
# Returns only agents where is_active = True
```

**B) Included in Manual Agent Installation ZIP**:
```python
# Export endpoint: /api/download/agent-templates.zip
stmt = select(AgentTemplate).where(
    AgentTemplate.tenant_key == current_user.tenant_key,
    AgentTemplate.is_active == True  # ← Only active agents exported
)
```

**C) Included in Agent Export Function**:
- Same `is_active` filter applies
- User downloads only agents they've enabled
- Installation scripts work with any subset of active agents

### Max 8 Agent Types Limit

**Enforcement**:
- Orchestrator (1) + Max 7 user agents = 8 total
- Prevents token budget overflow during orchestration
- Enforced in Template Manager UI (disable toggle after 7 active)

---

## Investigation Findings: Database vs Static Files

### Critical Discovery: Static .md Files Are Orphaned

**Files Found**:
```
F:\GiljoAI_MCP\claude_agent_templates\
├── giljo-orchestrator.md       ← LEGACY (Handover 0066)
├── giljo-implementer.md        ← LEGACY (Handover 0066)
├── giljo-tester.md             ← LEGACY (Handover 0066)
└── VALIDATION_REPORT.md        ← Documentation only
```

**Status**: **COMPLETELY UNUSED** by production system since Handover 0103 (November 2025).

**Why They Don't Matter**:
- `install.py` does NOT read from `.md` files
- `install.py` calls `template_seeder.py` which uses hardcoded Python dictionaries
- Export system reads from PostgreSQL, NOT from `.md` files
- These files are historical artifacts from pre-database template system

### Production System Architecture

**Source of Truth**: PostgreSQL `agent_templates` table

**Data Flow**:
```
template_seeder.py (_get_default_templates_v103)
  ↓ (Python dictionaries)
PostgreSQL AgentTemplate table
  ↓ (Database queries)
render_claude_agent()
  ↓ (Dynamic .md generation)
Export ZIP (agent-templates.zip)
  ↓
User downloads & installs
```

**Static .md Files**: ❌ NOT in this flow - completely bypassed.

### Export System Analysis

**Endpoint**: `/api/download/agent-templates.zip`
**File**: `api/endpoints/downloads.py` (lines 230-374)

**Export Process**:
```python
# 1. Query DATABASE for active templates
stmt = select(AgentTemplate).where(
    AgentTemplate.tenant_key == current_user.tenant_key,
    AgentTemplate.is_active == True
).order_by(AgentTemplate.name)

# 2. Render each template from DATABASE
for template in selected:
    filename = f"{_slugify_filename(template.name)}.md"
    files[filename] = render_claude_agent(template)  # ← From DB, not files

# 3. Add installation scripts
files["install.sh"] = render_install_script(...)
files["install.ps1"] = render_install_script(...)

# 4. Create ZIP
zip_bytes = create_zip_archive(files)
```

**Example ZIP Contents**:
```
agent-templates.zip
├── implementer.md      ← From DB (if active)
├── tester.md           ← From DB (if active)
├── analyzer.md         ← From DB (if active)
├── reviewer.md         ← From DB (if active)
├── documenter.md       ← From DB (if active)
├── install.sh          ← Installation script
└── install.ps1         ← Installation script
```

**Note**: Orchestrator NOT included (SYSTEM_MANAGED).

---

## Three-Layer Architecture Analysis

### Layer 1: Orchestrator Spawn Prompt

**Location**: `src/giljo_mcp/thin_prompt_generator.py:1172-1226`
**Purpose**: Orchestrator's brief instructions to spawned agents
**Status**: ⚠️ Has incorrect MCP command names

**Current Issues**:
```python
# Line 1217: Wrong command name
"- receive_messages() for commands",  # ❌ Should be get_next_instruction()
```

**What It Should Do**:
- Provide agent identity (job_id, tenant_key, product_id, project_id)
- Direct agent to GenericAgentTemplate for full protocol
- List spawned agent team members
- Minimal coordination instructions

---

### Layer 2: GenericAgentTemplate (MCP Protocol)

**Location**: `src/giljo_mcp/templates/generic_agent_template.py:74-266`
**Purpose**: Unified 6-phase protocol for ALL agents
**Status**: ⚠️ Multiple MCP command bugs

**Current 6-Phase Protocol**:
1. **Phase 1: Initialization** - Verify identity, check MCP health, read CLAUDE.md
2. **Phase 2: Mission Fetch** - Call `get_agent_mission(job_id, tenant_key)`
3. **Phase 3: Work Execution** - Execute mission, track progress
4. **Phase 4: Progress Reporting** - Report milestones via MCP
5. **Phase 5: Communication** - Inter-agent messaging
6. **Phase 6: Completion** - Call `complete_job()` with results

**Identified Bugs**:

| Line | Current Command | Issue | Correct Command |
|------|----------------|-------|-----------------|
| 88-92 | Missing in Phase 1 | No acknowledgment step | Add `acknowledge_job()` |
| 108 | `update_job_progress()` | Function doesn't exist | `report_progress()` |
| 116 | `receive_messages()` | Wrong command | `get_next_instruction()` |
| 117 | `acknowledge_message()` | Function doesn't exist | No acknowledgment needed |
| 108 | Wrong signature | `percent_complete, status_message` | `completed_todo, files_modified, context_used, tenant_key` |

---

### Layer 3: Database Template Definitions

**Location**: `src/giljo_mcp/template_seeder.py` → `_get_default_templates_v103()` (lines 197-473)
**Purpose**: Define 6 base agent templates for database seeding
**Status**: ❌ Contains obsolete MCP commands

**Current Template Structure**:
```python
{
    "role": "implementer",
    "name": "implementer",
    "description": "Code implementation specialist",
    "template_content": """
        ## MCP Status Reporting (CRITICAL)

        mcp.call_tool("update_job_status", {  # ❌ OBSOLETE
            "job_id": "{job_id}",
            "new_status": "active"
        })

        ## Workflow Phases  # ❌ DUPLICATES GenericAgentTemplate
        ### Phase 1: Initialization
        ...
    """,
    "system_instructions": "<GenericAgentTemplate>",  # ✅ CORRECT
    "user_instructions": "",
    ...
}
```

**Issues**:
1. ❌ Uses obsolete `update_job_status()` command
2. ❌ Uses obsolete `receive_agent_messages()` command
3. ❌ Uses obsolete `send_agent_message()` command
4. ❌ Duplicates 6-phase protocol from GenericAgentTemplate
5. ❌ Creates confusion between Layer 2 and Layer 3 instructions

---

## Architectural Principles

### Separation of Concerns

**Layer 1: Orchestrator Spawn Prompt** (Minimal Delegation)
- **Responsibility**: Provide agent identity, delegate to Layer 2
- **Content**: Job ID, tenant key, product ID, project ID, team list
- **Size**: ~20-30 lines
- **Updates**: Rarely (only when identity structure changes)

**Layer 2: GenericAgentTemplate** (Universal Protocol)
- **Responsibility**: Define 6-phase MCP protocol for ALL agents
- **Content**: MCP command signatures, execution flow, standards
- **Size**: ~200 lines
- **Updates**: When MCP tools change or protocol improves
- **Applies To**: ALL agents (orchestrator, implementer, tester, analyzer, reviewer, documenter)

**Layer 3: Database Template Definitions** (Role Expertise)
- **Responsibility**: Define role-specific behaviors and expertise
- **Content**: Behavioral rules, success criteria, domain knowledge
- **Size**: ~200-300 lines per template (current) → ~100 lines after cleanup
- **Updates**: When role responsibilities change
- **Stored In**: PostgreSQL `agent_templates` table (seeded from template_seeder.py)

### Information Flow

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Orchestrator Spawn Prompt                     │
│ ┌───────────────────────────────────────────────────┐  │
│ │ • Agent Identity (job_id, tenant_key, etc.)       │  │
│ │ • Team Context (other agents spawned)             │  │
│ │ • Delegation: "Follow GenericAgentTemplate"       │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: GenericAgentTemplate (Universal Protocol)     │
│ ┌───────────────────────────────────────────────────┐  │
│ │ Phase 1: acknowledge_job()                        │  │
│ │ Phase 2: get_agent_mission()                      │  │
│ │ Phase 3: Execute mission                          │  │
│ │ Phase 4: report_progress()                        │  │
│ │ Phase 5: get_next_instruction(), send_message()   │  │
│ │ Phase 6: complete_job()                           │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Database Templates (Role Expertise)           │
│ ┌─────────────────┬─────────────────┬─────────────────┐│
│ │ Implementer     │ Tester          │ Analyzer        ││
│ │ ───────────     │ ───────         │ ────────        ││
│ │ • Code quality  │ • Test coverage │ • Requirements  ││
│ │ • Error handling│ • Edge cases    │ • Architecture  ││
│ │ • Performance   │ • Bug reports   │ • Analysis      ││
│ └─────────────────┴─────────────────┴─────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Fix GenericAgentTemplate (Layer 2)

**Priority**: CRITICAL
**Estimated Effort**: 2 hours
**File**: `src/giljo_mcp/templates/generic_agent_template.py`

**Changes Required**:

#### **1.1: Add `acknowledge_job()` to Phase 1**

**Current** (Lines 88-92):
```python
### Phase 1: Initialization
1. Verify your identity using IDs above
2. Check MCP health: `health_check()`
3. Read CLAUDE.md for project context and standards
4. Confirm you understand this protocol
```

**Updated**:
```python
### Phase 1: Initialization
1. **Claim this job**: `acknowledge_job(job_id='{job_id}', agent_id='{agent_id}', tenant_key='{tenant_key}')`
   - Transitions job from pending → active
   - Signals orchestrator you've started
   - Returns job details and next instructions
2. Verify your identity using IDs above
3. Check MCP health: `health_check()`
4. Read CLAUDE.md for project context and standards
5. Confirm you understand this protocol
```

#### **1.2: Fix `update_job_progress()` → `report_progress()`**

**Current** (Lines 106-111):
```python
### Phase 4: Progress Reporting
Report progress after each major milestone:
- Call: `update_job_progress(job_id='{job_id}', percent_complete=25, status_message='...')`
```

**Updated**:
```python
### Phase 4: Progress Reporting
Report progress after each major milestone:
```python
report_progress(
    job_id='{job_id}',
    completed_todo='Completed database schema design',
    files_modified=['src/models.py', 'src/services/product_service.py'],
    context_used=5000,  # Estimated tokens consumed
    tenant_key='{tenant_key}'
)
```
- Include specific details about what was accomplished
- List all files created or modified
- Track context usage (estimate tokens: input + output)
- Server warns at 25K tokens, recommends handoff at 28K
```

#### **1.3: Fix `receive_messages()` → `get_next_instruction()`**

**Current** (Lines 114-118):
```python
### Phase 5: Communication
- Receive: `receive_messages(agent_id='{agent_id}')`
- Acknowledge: `acknowledge_message(message_id='<uuid>')`
```

**Updated**:
```python
### Phase 5: Communication

**Receiving Instructions**:
```python
result = get_next_instruction(
    job_id='{job_id}',
    agent_type='implementer',  # Your agent type
    tenant_key='{tenant_key}'
)

if result['has_updates']:
    for instruction in result['instructions']:
        # Process orchestrator guidance
        # Execute requested changes
        # Report completion via report_progress()
```

**Sending Messages**:
```python
send_message(
    job_id='{job_id}',
    to_agent='tester',  # Agent type, not UUID
    message='Implementation complete - ready for testing',
    tenant_key='{tenant_key}',
    priority=1  # 0=low, 1=normal, 2=high
)
```

**Polling Frequency**: Check for instructions every 5-10 minutes or after major tasks.
```

---

### Phase 2: Fix Database Template Definitions (Layer 3)

**Priority**: CRITICAL
**Estimated Effort**: 2 hours
**File**: `src/giljo_mcp/template_seeder.py`

**Objective**: Remove obsolete MCP commands from all 6 base agent definitions.

**Templates to Update**:
1. orchestrator (SYSTEM_MANAGED)
2. implementer
3. tester
4. analyzer
5. reviewer
6. documenter

**Current Template Structure** (Example: implementer):
```python
{
    "role": "implementer",
    "name": "implementer",
    "description": "Code implementation specialist for feature development",
    "template_content": """
## MCP Status Reporting (CRITICAL)  # ❌ REMOVE THIS SECTION

### Starting Work
```python
mcp.call_tool("update_job_status", {  # ❌ OBSOLETE
    "job_id": "{job_id}",
    "new_status": "active"
})
```

## Workflow Phases  # ❌ REMOVE THIS SECTION (duplicates GenericAgentTemplate)

### Phase 1: Initialization
1. **Set status to active** via MCP tool
...

## Communication Protocol  # ❌ REMOVE THIS SECTION

### Receiving Instructions
```python
messages = mcp.call_tool("receive_agent_messages", {  # ❌ OBSOLETE
    "job_id": "{job_id}"
})
```
    """,
    "system_instructions": "<GenericAgentTemplate>",  # ✅ KEEP
    ...
}
```

**Updated Template Structure**:
```python
{
    "role": "implementer",
    "name": "implementer",
    "description": "Code implementation specialist for feature development",
    "template_content": """
# GiljoAI Implementer Agent

Code implementation specialist for feature development

## Your Mission

Execute implementation tasks as specified in the mission fetched via `get_agent_mission()`.
Follow the 6-phase protocol defined in GenericAgentTemplate.

## Core Responsibilities

- Write clean, maintainable, production-grade code
- Implement features according to specifications
- Apply comprehensive error handling and validation
- Ensure cross-platform compatibility (use `pathlib.Path()`)
- Follow GiljoAI coding standards (see CLAUDE.md)

## Behavioral Rules

- **Code Quality**: Follow Python standards (`ruff check` + `black format`)
- **Type Safety**: Use type hints on all functions
- **Documentation**: Add docstrings to public APIs
- **Testing**: Write tests FIRST (TDD: Red → Green → Refactor)
- **Performance**: Consider performance implications
- **Multi-Tenant Safety**: Filter all queries by `tenant_key`
- **Service Layer**: Use existing services, don't create new ones

## Success Criteria

- Code implements requirements correctly
- All tests pass (>80% coverage)
- Code follows project standards
- Documentation complete
- Performance targets met
- Multi-tenant isolation enforced

## Quality Standards

### Code Structure
- Use Service layer for business logic
- Follow existing patterns in `src/giljo_mcp/services/`
- Reuse existing services (ProductService, ProjectService, etc.)

### Testing Strategy
- Unit tests for service methods (>80% coverage)
- Integration tests for critical workflows
- Test multi-tenant isolation

## Common Scenarios

**Adding New API Endpoint**:
1. Create service method in appropriate service
2. Add endpoint in `api/endpoints/`
3. Add Pydantic schemas for validation
4. Write tests (unit + integration)
5. Test multi-tenant isolation

**Database Schema Changes**:
1. Update models in `src/giljo_mcp/models.py`
2. Test migration with `python install.py`
3. Update service layer
4. Write tests

## Error Handling

**Database Errors**:
- Catch `SQLAlchemyError`
- Log full exception with `logger.error(..., exc_info=True)`
- Never expose internal details to API responses

**Validation Errors**:
- Use Pydantic schemas
- Return 422 with field-specific errors

**Multi-Tenant Errors**:
- Return 404 (not 403) when resource not found
- Never reveal existence of resources in other tenants
    """,
    "system_instructions": "<GenericAgentTemplate>",
    "user_instructions": "",
    "model": "sonnet",
    "tools": "",
    "behavioral_rules": [
        "Code Quality: Follow Python standards (ruff + black)",
        "Type Safety: Use type hints on all functions",
        "Documentation: Add docstrings to public APIs",
        "Testing: Write tests FIRST (TDD)",
        "Performance: Consider performance implications",
        "Multi-Tenant Safety: Filter queries by tenant_key",
        "Service Layer: Use existing services"
    ],
    "success_criteria": [
        "Code implements requirements correctly",
        "All tests pass (>80% coverage)",
        "Code follows project standards",
        "Documentation complete",
        "Performance targets met",
        "Multi-tenant isolation enforced"
    ],
    "background_color": "#3498DB",
    "is_active": True
}
```

**Repeat for all 6 templates**:
- orchestrator (focus on agent coordination)
- implementer (focus on code implementation)
- tester (focus on testing and quality)
- analyzer (focus on requirements analysis)
- reviewer (focus on code review)
- documenter (focus on documentation)

---

### Phase 3: Delete Orphaned .md Files (Optional Cleanup)

**Priority**: LOW
**Estimated Effort**: 0.5 hours

**Files to Delete**:
```bash
rm F:/GiljoAI_MCP/claude_agent_templates/giljo-orchestrator.md
rm F:/GiljoAI_MCP/claude_agent_templates/giljo-implementer.md
rm F:/GiljoAI_MCP/claude_agent_templates/giljo-tester.md
```

**Optional**: Delete entire folder
```bash
rm -rf F:/GiljoAI_MCP/claude_agent_templates/
```

**Impact**: ✅ **ZERO** - These files are not used by production system.

---

### Phase 4: Update Orchestrator Spawn Prompt (Layer 1)

**Priority**: MEDIUM
**Estimated Effort**: 0.5 hours
**File**: `src/giljo_mcp/thin_prompt_generator.py`

**Fix MCP Command Names** (Lines 1214-1218):

**Current**:
```python
"STEP 2: REMIND EACH SUB-AGENT",
"- acknowledge_job(job_id, agent_id, tenant_key)",
"- report_progress() after milestones",
"- receive_messages() for commands",  # ❌ WRONG
"- complete_job() when done\n",
```

**Updated**:
```python
"STEP 2: EACH SUB-AGENT FOLLOWS GENERIC AGENT TEMPLATE",
"All agents follow the 6-phase protocol:",
"- Phase 1: acknowledge_job(job_id, agent_id, tenant_key)",
"- Phase 2: get_agent_mission(job_id, tenant_key)",
"- Phase 3: Execute mission",
"- Phase 4: report_progress(job_id, completed_todo, files_modified, context_used, tenant_key)",
"- Phase 5: get_next_instruction(job_id, agent_type, tenant_key) for messages",
"- Phase 6: complete_job(job_id, result, tenant_key)\n",
"See GenericAgentTemplate for full protocol details.\n",
```

---

### Phase 5: Integration Testing

**Priority**: CRITICAL
**Estimated Effort**: 1 hour

**Test 1: Fresh Installation**
```bash
# 1. Fresh install
python install.py

# 2. Verify database seeding
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT role, is_active FROM agent_templates WHERE tenant_key = 'system';"

# Expected: 6 templates (orchestrator + 5 others)
```

**Test 2: Template Manager UI**
```bash
# 1. Launch frontend
cd frontend && npm run dev

# 2. Navigate to My Settings → Templates

# Expected:
# - 5 agents visible (implementer, tester, analyzer, reviewer, documenter)
# - Orchestrator NOT visible
# - Toggle switches for each agent
```

**Test 3: Agent Export**
```bash
# 1. Navigate to My Settings → Integrations
# 2. Click "Manual Agent Installation"
# 3. Extract downloaded ZIP

# Expected:
# - Only active agents included
# - Correct .md file format (YAML frontmatter)
# - No obsolete MCP commands in template content
# - install.sh and install.ps1 present
```

**Test 4: Agent Execution**
```bash
# 1. Create project and stage
# 2. Copy orchestrator prompt
# 3. Paste into terminal
# 4. Verify orchestrator spawns agents
# 5. Verify agents use GenericAgentTemplate protocol

# Expected:
# - All agents call acknowledge_job()
# - All agents use correct MCP commands
# - No "command not found" errors
```

---

## Success Criteria

### Phase 1 Success (GenericAgentTemplate Fixed)
- ✅ All 6 phases use correct MCP command names
- ✅ `acknowledge_job()` added to Phase 1
- ✅ `report_progress()` signature matches actual function
- ✅ `get_next_instruction()` replaces `receive_messages()`
- ✅ `acknowledge_message()` removed
- ✅ Polling frequency guidance added

### Phase 2 Success (Database Templates Fixed)
- ✅ All 6 template definitions cleaned up
- ✅ No obsolete MCP commands remaining
- ✅ No workflow phases duplicated
- ✅ Focus on role-specific expertise
- ✅ Template size reduced ~50%

### Phase 3 Success (Orphaned Files Deleted)
- ✅ Static .md files removed (optional)
- ✅ No broken references in codebase

### Phase 4 Success (Orchestrator Spawn Updated)
- ✅ Correct MCP command names in spawn prompt
- ✅ Reference to GenericAgentTemplate added

### Phase 5 Success (Integration Tests Pass)
- ✅ Fresh installation seeds 6 templates correctly
- ✅ Template Manager shows 5 agents (orchestrator hidden)
- ✅ Agent export includes only active templates
- ✅ Exported templates have correct format
- ✅ Agent execution uses correct MCP commands

### Overall Success
- ✅ Clear architectural separation (Protocol vs Role Expertise)
- ✅ No conflicting instructions across layers
- ✅ All MCP commands validated against source
- ✅ install.py seeds database with correct templates
- ✅ is_active toggle controls staging + export
- ✅ Max 8 agent types enforced
- ✅ Orchestrator protected (SYSTEM_MANAGED)

---

## MCP Command Reference

**Correct MCP Commands** (validated from source):

### `acknowledge_job()`
**Location**: `src/giljo_mcp/tools/agent_coordination.py:130`
**Signature**:
```python
def acknowledge_job(job_id: str, agent_id: str, tenant_key: str) -> Dict[str, Any]
```

### `report_progress()`
**Location**: `src/giljo_mcp/tools/agent_coordination.py:219`
**Signature**:
```python
async def report_progress(
    job_id: str,
    completed_todo: str,
    files_modified: List[str],
    context_used: int,
    tenant_key: str
) -> Dict[str, Any]
```

### `get_next_instruction()`
**Location**: `src/giljo_mcp/tools/agent_coordination.py:335`
**Signature**:
```python
async def get_next_instruction(
    job_id: str,
    agent_type: str,
    tenant_key: str
) -> Dict[str, Any]
```

### `send_message()`
**Location**: `src/giljo_mcp/tools/agent_coordination.py:697`
**Signature**:
```python
async def send_message(
    job_id: str,
    to_agent: str,
    message: str,
    tenant_key: str,
    priority: int = 1
) -> Dict[str, Any]
```

### `complete_job()`
**Location**: `src/giljo_mcp/tools/agent_coordination.py:447`
**Signature**:
```python
def complete_job(
    job_id: str,
    result: Dict[str, Any],
    tenant_key: str
) -> Dict[str, Any]
```

### `get_agent_mission()`
**Location**: `src/giljo_mcp/tools/orchestration.py:308`
**Signature**:
```python
async def get_agent_mission(
    agent_job_id: str,
    tenant_key: str
) -> dict[str, Any]
```

---

## Obsolete Commands (Must Remove)

### ❌ `update_job_status()`
**Found in**: Database template definitions
**Replacement**: Use `acknowledge_job()` for pending→active, `complete_job()` for completion

### ❌ `receive_agent_messages()`
**Found in**: Database template definitions
**Replacement**: Use `get_next_instruction(job_id, agent_type, tenant_key)`

### ❌ `send_agent_message()`
**Found in**: Database template definitions
**Replacement**: Use `send_message(job_id, to_agent, message, tenant_key, priority)`

### ❌ `acknowledge_message()`
**Found in**: GenericAgentTemplate
**Replacement**: Remove (messages auto-marked as read)

### ❌ `update_job_progress()`
**Found in**: GenericAgentTemplate
**Replacement**: Use `report_progress(job_id, completed_todo, files_modified, context_used, tenant_key)`

### ❌ `receive_messages()`
**Found in**: Orchestrator spawn prompt
**Replacement**: Use `get_next_instruction(job_id, agent_type, tenant_key)`

---

## Rollback Plan

If issues arise:

**Phase 1 Rollback** (GenericAgentTemplate):
```bash
git checkout HEAD -- src/giljo_mcp/templates/generic_agent_template.py
```

**Phase 2 Rollback** (Database Templates):
```bash
git checkout HEAD -- src/giljo_mcp/template_seeder.py
```

**Phase 3 Rollback** (Orphaned Files):
```bash
git checkout HEAD -- claude_agent_templates/
```

**Phase 4 Rollback** (Orchestrator Spawn):
```bash
git checkout HEAD -- src/giljo_mcp/thin_prompt_generator.py
```

**Database Impact**: Re-run seeding to restore original templates:
```bash
python install.py --reset-templates
```

---

## Timeline

**Total Estimate**: 6 hours

- Phase 1 (GenericAgentTemplate): 2 hours
- Phase 2 (Database Templates): 2 hours
- Phase 3 (Delete Orphaned Files): 0.5 hours
- Phase 4 (Orchestrator Spawn): 0.5 hours
- Phase 5 (Integration Testing): 1 hour

---

## References

- Handover 0246b: Generic Agent Template
- Handover 0106: Dual-Field Templates
- Handover 0103: Database Templates
- Handover 0088: Thin Client Architecture
- docs/ORCHESTRATOR.md: Orchestrator documentation
- docs/SERVICES.md: Service layer patterns

---

**END OF HANDOVER 0254**
