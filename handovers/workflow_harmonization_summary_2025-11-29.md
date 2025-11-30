# Workflow Harmonization Summary - 2025-11-29

**Agent**: Documentation Manager
**Date**: 2025-11-29
**Status**: Investigation Phase Complete - Awaiting Code Review & User Clarification

---

## Executive Summary

This handover documents a comprehensive review of GiljoAI's workflow documentation to identify contradictions between the reference materials (PDF slides) and the implementation guide (flow.md). The review uncovered **6 critical contradictions** that require user clarification and code verification before documentation can be harmonized.

**What Was Accomplished**:
- Complete review of 39 PDF workflow slides (Slide14-Slide39)
- Comprehensive analysis of `start_to_finish_agent_FLOW.md`
- Identification of 6 major workflow contradictions
- Documentation of specific code locations requiring investigation
- Creation of targeted questions for code review

**What Remains**:
- Code review of orchestration tools to determine ground truth
- User clarification on intended workflow vs. current implementation
- Resolution of contradictions through code fixes or documentation updates
- Final harmonization of all workflow documentation

---

## Work Completed

### Documents Reviewed

1. **PDF Workflow Slides** (`handovers/Reference_docs/Workflow PPT to JPG/`)
   - Slides 14-39 (26 slides total)
   - Focus: Orchestrator staging workflow, agent spawning, job lifecycle
   - Key sections: Initial staging (14-19), spawning process (23-30), execution (31-39)

2. **Flow Documentation** (`handovers/Reference_docs/start_to_finish_agent_FLOW.md`)
   - Complete end-to-end workflow documentation
   - Sections: User actions, orchestrator tasks, agent lifecycle, monitoring
   - Last updated: 2025-11-29 (prior to this investigation)

3. **Code Files Referenced** (for future investigation)
   - `src/giljo_mcp/tools/orchestration.py` - Orchestration MCP tools
   - `api/endpoints/agent_management.py` - Agent management endpoints
   - `frontend/src/components/projects/JobsTab.vue` - Job monitoring UI
   - `frontend/src/services/api.js` - Frontend API integration

---

## Critical Contradictions Found

### Contradiction 1: Agent Spawning Workflow

**PDF Slides 23-25 State**:
- "Orchestrator picks up 1st worker agent template from library"
- "Inject dynamic mission into {mission_here} placeholder"
- "Spawn agent via `spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)`"

**flow.md States**:
- "Orchestrator uses `get_generic_agent_template()` to get a standardized template"
- "Then calls `get_agent_mission()` to fetch agent-specific instructions"
- Two separate MCP tools instead of one spawn call with mission injection

**Critical Question**: Does spawning happen in one step (PDF) or two steps (flow.md)?

**Code to Investigate**:
- `src/giljo_mcp/tools/orchestration.py` - `spawn_agent_job()` function
- Check if mission is passed during spawn or fetched separately
- Line numbers: Search for `spawn_agent_job` definition and implementation

---

### Contradiction 2: Job State Transitions

**PDF Slides 26-27 State**:
- Job states: `pending` → `active` (via `acknowledge_job`) → `completed` (via `complete_job`)
- Three explicit states with defined transitions
- "Agent claims job (pending → active)"

**flow.md States**:
- Job states: `staged` → `pending` → `active` → `completed`
- **Four states** instead of three
- Additional `staged` state before `pending`

**Critical Question**: Is there a `staged` state in the actual implementation?

**Code to Investigate**:
- `src/giljo_mcp/models.py` - `AgentJob` model
- Check `status` column enum values
- Search for `JobStatus` enum or similar status constants
- Line numbers: Look for job status definition in models

---

### Contradiction 3: Agent Discovery Mechanism

**PDF Slides 17-18 State**:
- "Survey available agent templates on server"
- "Orchestrator uses `get_available_agents(tenant_key, active_only=True)` to get active agent list"
- Dynamic discovery via MCP tool

**flow.md States**:
- "Orchestrator has hard-coded list of expected agent types"
- "Expected agents: Coder, Tester, Debugger, Documentation Manager, Security Analyst"
- Static agent list in orchestrator prompt

**Critical Question**: Does agent discovery use dynamic MCP tool or static hardcoded list?

**Code to Investigate**:
- `src/giljo_mcp/tools/orchestration.py` - `get_available_agents()` function
- `src/giljo_mcp/tools/staging.py` - Orchestrator staging prompt generation
- Check if orchestrator prompt includes hardcoded agent list
- Line numbers: Search for `get_available_agents` and staging prompt templates

---

### Contradiction 4: Orchestrator Identity Verification

**PDF Slide 14 States**:
- "Orchestrator calls `get_orchestrator_instructions(orchestrator_id, tenant_key)`"
- "Server looks up job in `mcp_agent_jobs` table"
- "Returns: {orchestrator_id, tenant_key, mission_prompt, context_budget}"

**flow.md States**:
- Orchestrator prompt includes mission directly
- No explicit identity verification step mentioned
- Mission is embedded in thin-client prompt

**Critical Question**: Does orchestrator verify identity via MCP call or receive mission inline?

**Code to Investigate**:
- `src/giljo_mcp/tools/orchestration.py` - `get_orchestrator_instructions()` function
- `src/giljo_mcp/tools/staging.py` - Thin-client prompt generation
- Check if thin-client prompt includes mission or defers to MCP tool
- Line numbers: Search for `ThinClientPromptGenerator` and orchestrator prompt building

---

### Contradiction 5: Job Spawning vs. Activation

**PDF Slides 28-30 State**:
- Two-step process: Spawn job → Activate job
- "Spawned job is created in database with status `pending`"
- "Agent claims job (pending → active) via `acknowledge_job()`"

**flow.md States**:
- "Orchestrator spawns jobs using `spawn_agent_job()`"
- "Jobs are created in `staged` state"
- "Orchestrator activates staged jobs (staged → pending)"
- **Three-step process**: Spawn (staged) → Activate (pending) → Claim (active)

**Critical Question**: Is activation a separate step or does spawning create pending jobs directly?

**Code to Investigate**:
- `src/giljo_mcp/tools/orchestration.py` - `spawn_agent_job()` function
- Check initial job status when created
- Search for activation logic (staged → pending transition)
- Line numbers: Look for job creation code and status assignment

---

### Contradiction 6: MCP Health Check Timing

**PDF Slide 15 States**:
- "Orchestrator calls `health_check()` before starting work"
- Listed as Task 2 in 7-task staging workflow
- Explicit health verification step

**flow.md States**:
- No explicit health check mentioned in orchestrator workflow
- Orchestrator proceeds directly to environment understanding and agent discovery
- Health check not documented as required step

**Critical Question**: Is MCP health check required or optional in orchestrator workflow?

**Code to Investigate**:
- `src/giljo_mcp/tools/orchestration.py` - `health_check()` function
- `src/giljo_mcp/tools/staging.py` - Orchestrator staging prompt
- Check if health check is included in orchestrator instructions
- Line numbers: Search for `health_check` references

---

## Questions for Fresh Agent

A fresh agent with code review capabilities should investigate the following:

### 1. Agent Spawning Implementation
**Question**: How does `spawn_agent_job()` work?
- Does it accept a `mission` parameter?
- Does it inject mission into template or store mission separately?
- What is the relationship between `spawn_agent_job()` and `get_agent_mission()`?

**Files**: `src/giljo_mcp/tools/orchestration.py`
**Search For**: `spawn_agent_job` function definition and calls

---

### 2. Job Status State Machine
**Question**: What are the valid job statuses?
- Is there a `staged` status in the enum?
- What are the allowed state transitions?
- Where is the status enum defined?

**Files**: `src/giljo_mcp/models.py`
**Search For**: `JobStatus`, `AgentJob.status`, enum definitions

---

### 3. Agent Discovery Method
**Question**: How does orchestrator discover available agents?
- Is `get_available_agents()` called during staging?
- Is there a hardcoded agent list in the orchestrator prompt?
- Which approach is actually used in production?

**Files**:
- `src/giljo_mcp/tools/orchestration.py` (for MCP tool)
- `src/giljo_mcp/tools/staging.py` (for prompt generation)
**Search For**: `get_available_agents`, agent type lists, orchestrator template

---

### 4. Orchestrator Identity Flow
**Question**: How does orchestrator receive its mission?
- Does it call `get_orchestrator_instructions()` as first step?
- Is mission embedded in thin-client prompt?
- What does the actual orchestrator prompt look like?

**Files**:
- `src/giljo_mcp/tools/orchestration.py`
- `src/giljo_mcp/tools/staging.py`
**Search For**: `get_orchestrator_instructions`, `ThinClientPromptGenerator`, orchestrator prompt building

---

### 5. Job Activation Workflow
**Question**: What happens between job creation and agent claiming?
- Are jobs created in `staged` or `pending` status?
- Is there an explicit activation step (staged → pending)?
- Or do jobs go straight to pending when spawned?

**Files**: `src/giljo_mcp/tools/orchestration.py`
**Search For**: Job creation code, status transitions, `spawn_agent_job` implementation

---

### 6. MCP Health Check Usage
**Question**: Is health check part of orchestrator workflow?
- Is `health_check()` called during staging?
- Is it documented in orchestrator instructions?
- Is it required or optional?

**Files**:
- `src/giljo_mcp/tools/orchestration.py`
- `src/giljo_mcp/tools/staging.py`
**Search For**: `health_check`, staging workflow tasks

---

## Files to Review

### Priority 1: Core Orchestration Logic
1. **`src/giljo_mcp/tools/orchestration.py`**
   - Primary file for MCP tool implementations
   - Contains: `spawn_agent_job()`, `get_agent_mission()`, `get_available_agents()`, `get_orchestrator_instructions()`, `health_check()`
   - **Key Questions**: All 6 contradictions relate to tools in this file
   - **Lines to Check**: Search for each MCP tool function definition

2. **`src/giljo_mcp/tools/staging.py`** (if exists)
   - Orchestrator staging prompt generation
   - Thin-client prompt building
   - **Key Questions**: Contradictions 3, 4, 6 (agent discovery, identity verification, health check)
   - **Lines to Check**: Look for prompt templates and orchestrator instructions

3. **`src/giljo_mcp/models.py`**
   - Database models and enums
   - **Key Question**: Contradiction 2 (job states)
   - **Lines to Check**: Search for `AgentJob` model, `JobStatus` enum, status column definition

### Priority 2: API Endpoints & Frontend
4. **`api/endpoints/agent_management.py`**
   - Agent job management endpoints
   - **Key Questions**: Contradictions 1, 2, 5 (spawning, status transitions, activation)
   - **Lines to Check**: Job creation endpoints, status update logic

5. **`frontend/src/components/projects/JobsTab.vue`**
   - Job status display in UI
   - **Key Question**: Contradiction 2 (what statuses are displayed?)
   - **Lines to Check**: Status badge rendering, status filtering

6. **`frontend/src/services/api.js`**
   - Frontend API calls for job management
   - **Key Questions**: Contradictions 1, 5 (spawning API calls, activation calls)
   - **Lines to Check**: Job spawning functions, status update functions

### Priority 3: Documentation & Configuration
7. **`docs/ORCHESTRATOR.md`**
   - Orchestrator documentation (if exists)
   - May contain additional workflow details
   - **Lines to Check**: Staging workflow, job lifecycle

8. **`CLAUDE.md`**
   - Already reviewed - mentions 7-task staging workflow (0246a)
   - References thin-client architecture (0088)
   - **Lines to Check**: Orchestrator workflow sections (already documented in CLAUDE.md)

---

## Next Steps

### Step 1: Code Investigation (Fresh Agent Task)
A fresh agent should perform a comprehensive code review to answer the 6 critical questions:

**Tools to Use**:
- `mcp__serena__find_symbol` - Find MCP tool functions by name
- `mcp__serena__get_symbols_overview` - Get overview of key files
- `mcp__serena__find_referencing_symbols` - Trace MCP tool usage
- `Read` - Read specific code sections after locating them

**Deliverable**: Code review document answering each of the 6 questions with:
- Current implementation details
- Code snippets showing actual behavior
- Confirmation of which documentation is correct (PDF or flow.md)

---

### Step 2: User Clarification (User Task)
User should review the 6 contradictions and provide guidance:

**Questions for User**:
1. Which workflow is the **intended design** (PDF or flow.md)?
2. If code doesn't match intended design, should we fix code or update docs?
3. Are there recent changes that made one set of docs obsolete?
4. Which reference should be considered authoritative going forward?

**Context for User**:
- PDF slides appear to describe a **simplified 3-state workflow** (pending → active → completed)
- flow.md describes a **more complex 4-state workflow** (staged → pending → active → completed)
- Some contradictions may reflect evolution of the system over time

---

### Step 3: Resolution & Harmonization (Documentation Manager Task)
Based on code review and user guidance:

**If PDF is Correct**:
- Update `start_to_finish_agent_FLOW.md` to match PDF workflow
- Verify code implements PDF workflow (or file bugs if not)
- Mark flow.md sections as outdated where contradictions exist

**If flow.md is Correct**:
- Update PDF slides or mark them as outdated
- Verify code implements flow.md workflow
- Consider creating new reference diagrams matching flow.md

**If Neither is Fully Correct**:
- Use code as ground truth
- Update both PDF references and flow.md to match actual implementation
- Document any known bugs or planned changes

**Final Deliverable**: Harmonized documentation with:
- All contradictions resolved
- Single source of truth for workflow
- Clear migration notes if workflow changed over time
- Updated CLAUDE.md references to workflow documentation

---

## Additional Context

### Handover References
This investigation relates to several recent handovers mentioned in CLAUDE.md:

- **Handover 0246a**: 7-Task Staging Workflow (931 tokens, 22% under budget)
- **Handover 0246b**: Generic Agent Template with 6-phase protocol (1,253 tokens)
- **Handover 0246c**: Dynamic Agent Discovery (71% token savings, 420 tokens)

These handovers suggest the **PDF workflow may be more recent** (Nov 2025) than flow.md, but code review is needed to confirm.

### Modified Files (Git Status)
Current git status shows uncommitted changes to:
- `api/endpoints/agent_management.py`
- `frontend/src/components/projects/JobsTab.vue`
- `frontend/src/services/api.js`
- `src/giljo_mcp/tools/orchestration.py`

These modifications may relate to workflow changes and should be reviewed during code investigation.

### Timeline Context
- **flow.md Last Updated**: 2025-11-29 (today, before this investigation)
- **PDF Slides**: Appear to be recent (reference handovers 0246a-c from Nov 2025)
- **Workflow PPT**: Modified recently (per git status)
- **Code Changes**: Multiple orchestration files modified (uncommitted)

This suggests **active development** in the orchestration area, which may explain contradictions.

---

## Success Criteria

This handover will be considered successfully resolved when:

1. ✅ All 6 contradictions have been investigated via code review
2. ✅ User has provided clarification on intended workflow
3. ✅ Single authoritative workflow reference has been established
4. ✅ All documentation (PDF, flow.md, CLAUDE.md) has been harmonized
5. ✅ Any code bugs found during investigation have been filed or fixed
6. ✅ Clear migration notes exist if workflow evolved over time

---

## For the Fresh Agent

**Your Mission**:
1. Read this handover document completely
2. Use Serena MCP tools to investigate the 6 critical questions
3. Document your findings with code snippets and line numbers
4. Create a code review report answering each question
5. Recommend which documentation should be updated based on code reality

**Expected Time**: 2-3 hours for thorough code investigation

**Tools You'll Need**:
- `mcp__serena__find_symbol` - Find functions by name
- `mcp__serena__get_symbols_overview` - Get file structure
- `mcp__serena__search_for_pattern` - Search for specific patterns
- `Read` - Read code after locating it

**Output Format**: Create `workflow_code_review_2025-11-29.md` with:
- Answer to each of the 6 questions
- Code snippets supporting each answer
- File paths and line numbers
- Recommendation on which docs to update

---

## Contact & Questions

**Original Agent**: Documentation Manager
**Date Created**: 2025-11-29
**Session Context**: Workflow harmonization investigation

If you need clarification on this handover, review the source documents:
- `handovers/Reference_docs/Workflow PPT to JPG/` (Slides 14-39)
- `handovers/Reference_docs/start_to_finish_agent_FLOW.md`
- This handover document

**Ready to proceed?** Start with code investigation of `src/giljo_mcp/tools/orchestration.py` using Serena tools.
