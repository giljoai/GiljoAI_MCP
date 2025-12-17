# GiljoAI Agent Protocol Integration Report

**Date:** 2025-12-16
**Test Project:** TinyContacts
**Orchestrator Job ID:** 6792fae5-c46b-4ed7-86d6-df58aa833df3
**Tenant:** ***REMOVED***

---

## Executive Summary

During integration testing of the GiljoAI MCP server with Claude Code CLI agents, we identified **6 cascading failures** that prevented agents from properly using MCP tools. This report documents each failure point, provides evidence, and recommends specific fixes.

**Key Finding:** MCP tools ARE available to subagents as native tool calls. The failures were due to documentation/template mismatches, not infrastructure issues.

---

## Test Environment

- **Platform:** Windows (win32)
- **MCP Server:** GiljoAI MCP v3.1.0 (healthy, database connected)
- **Agent Templates Location:** `F:\TinyContacts\.claude\agents\`
- **Agents Tested:** analyzer, implementer, documenter
- **Spawn Method:** Claude Code CLI Task tool

---

## FAILURE ANALYSIS

### Failure Point 1: Tool Name Mismatch (CRITICAL)

**Severity:** CRITICAL
**Location:** Agent templates (`.claude/agents/*.md`)

**Problem:** Templates use WRONG tool naming convention:
```
Template says:  mcp__giljo_mcp__get_pending_jobs (UNDERSCORE)
Actual tool:    mcp__giljo-mcp__get_pending_jobs (HYPHEN)
```

**Evidence from `analyzer.md` lines 55-59:**
```
Call `mcp__giljo_mcp__get_pending_jobs(agent_type="<AGENT_TYPE>"...`
Call `mcp__giljo_mcp__acknowledge_job(job_id=<job_id>...`
Call `mcp__giljo_mcp__update_job_status(job_id=<job_id>...`
```

**Impact:** Agents following template instructions call non-existent tools, causing silent failures.

**Fix Required:** Find/replace `mcp__giljo_mcp__` with `mcp__giljo-mcp__` in all templates (~20+ occurrences per file).

---

### Failure Point 2: Non-Existent Tools Referenced

**Severity:** CRITICAL
**Location:** Agent templates

**Problem:** Templates reference tools that don't exist in MCP server:
- `mcp__giljo-mcp__update_job_status` - **DOES NOT EXIST**

**Actual Available Tools for Status Management:**
| Tool | Effect on Status |
|------|------------------|
| `acknowledge_job(job_id, agent_id)` | pending → working |
| `complete_job(job_id, result)` | working → complete |
| `report_error(job_id, error)` | working → blocked |

**Evidence:** Called `mcp__giljo-mcp__health_check()` successfully, confirmed server v3.1.0. Enumerated all available tools - no `update_job_status` exists.

**Impact:** Agents cannot update Kanban status as templates instruct. The analyzer agent that "worked" actually used `acknowledge_job` and `complete_job` correctly (implicit status changes).

**Fix Required:** Remove ALL references to `update_job_status`. Replace with:
```
# Instead of: update_job_status(job_id, new_status="active")
# Use:        acknowledge_job(job_id, agent_id)

# Instead of: update_job_status(job_id, new_status="completed")
# Use:        complete_job(job_id, result)

# Instead of: update_job_status(job_id, new_status="blocked", reason="...")
# Use:        report_error(job_id, error)
```

---

### Failure Point 3: Unsubstituted Placeholders

**Severity:** HIGH
**Location:** Agent templates

**Problem:** Templates use placeholders that are never replaced:
- `<AGENT_TYPE>`
- `<TENANT_KEY>`
- `<job_id>`

**Evidence from template line 55:**
```
agent_type="<AGENT_TYPE>", tenant_key="<TENANT_KEY>"
```

**Impact:** If agents copy-paste from templates, they use literal placeholder strings instead of actual values.

**Fix Required:** Either:
1. Templates should use descriptive language instead of literal placeholders, OR
2. Spawn prompt must explicitly provide all actual values

---

### Failure Point 4: Wrong Protocol Order in MCP Server Response

**Severity:** HIGH
**Location:** MCP server's `full_protocol` field returned by `get_agent_mission`

**Problem:** The 6-phase protocol puts COMMUNICATION after EXECUTION:
```
Phase 1: STARTUP
Phase 2: EXECUTION      <-- Starts work immediately
Phase 3: PROGRESS REPORTING
Phase 4: COMMUNICATION  <-- Checks messages TOO LATE
Phase 5: COMPLETION
Phase 6: CLEANUP
```

**Evidence:** Called `mcp__giljo-mcp__get_agent_mission` and examined `full_protocol` field. Phase 4 (Communication) says "Check for messages" but comes AFTER Phase 2 (Execution).

**Impact:** Agents never check for orchestrator messages/instructions before starting work. They miss any corrections or guidance sent after spawn.

**Fix Required:** Reorder phases:
```
Phase 1: STARTUP + CHECK MESSAGES  <-- Check for orchestrator instructions FIRST
Phase 2: EXECUTION
Phase 3: PROGRESS REPORTING + CHECK MESSAGES
Phase 4: COMPLETION
Phase 5: ERROR HANDLING
```

---

### Failure Point 5: Minimal Spawn Instructions from Orchestrator

**Severity:** HIGH
**Location:** Orchestrator spawn prompt (what I sent to Task tool)

**Problem:** Original spawn prompt was too minimal:
```
You are analyzer (job_id: b9ead95a-...)
Tenant: ***REMOVED***

First action: Call mcp__giljo-mcp__get_agent_mission...
```

**What was missing:**
- No explicit "MCP tools are NATIVE tool calls" warning
- No step-by-step startup sequence checklist
- No instruction to check messages before starting work
- No instruction to call acknowledge_job
- Relied entirely on templates + get_agent_mission response

**Impact:** When first MCP call failed (due to agents trying curl/HTTP), agents had no fallback instructions. They guessed at how to access MCP and chose wrong methods.

**Fix Required:** Enhanced spawn prompt template with:
1. Explicit "native tool call" warning
2. Mandatory startup sequence (numbered steps)
3. Actual values substituted (not placeholders)
4. Redundancy (belt and suspenders approach)

---

### Failure Point 6: Python-Style Examples Confused Agents

**Severity:** HIGH
**Location:** Agent templates, examples section

**Problem:** Templates use Python SDK syntax in examples:
```python
mcp.call_tool("mcp__giljo_mcp__update_job_status", {
    "job_id": "your-job-id",
    "new_status": "active"
})
```

**Impact:** Agents interpreted these examples as requiring:
- Python SDK calls
- HTTP requests via curl
- Some form of programmatic access

They did NOT understand these are native tool calls (like Read/Write/Bash).

**Evidence from agent outputs:**
- Analyzer tried: `curl -X POST "https://giljo-mcp.replit.app/get_agent_mission"`
- Documenter tried: `mcp call giljo-mcp get_agent_mission`
- Implementer tried: `curl -X POST http://localhost:3000/api/mcp/get-agent-mission`

**Fix Required:** Change examples from Python syntax to plain text:
```
Tool: mcp__giljo-mcp__acknowledge_job
Parameters:
  - job_id: "your-job-id"
  - agent_id: "analyzer"

Call this directly as a tool, like Read or Write.
```

---

## PROOF THAT MCP TOOLS WORK

After identifying the issues, we spawned a diagnostic agent with CORRECTED instructions:

**Corrected spawn prompt included:**
```
CRITICAL: MCP TOOL USAGE
MCP tools are NATIVE tool calls, NOT HTTP endpoints.
Use them EXACTLY like you use Read, Write, Bash, or Glob tools.
```

**Results:**
| Tool | Result |
|------|--------|
| `mcp__giljo-mcp__health_check` | SUCCESS - Server v3.1.0 healthy |
| `mcp__giljo-mcp__get_agent_mission` | SUCCESS - Retrieved full mission |
| `mcp__giljo-mcp__acknowledge_job` | SUCCESS - Status changed to "working" |
| `mcp__giljo-mcp__report_progress` | SUCCESS - Progress recorded |
| `mcp__giljo-mcp__complete_job` | SUCCESS - Job completed |

**Conclusion:** Infrastructure is working. Problem was instructions/documentation.

---

## ROOT CAUSE SUMMARY TABLE

| # | Failure Point | Severity | Fix Location |
|---|---------------|----------|--------------|
| 1 | Tool names: underscore vs hyphen | CRITICAL | Templates |
| 2 | `update_job_status` doesn't exist | CRITICAL | Templates |
| 3 | Unsubstituted placeholders | HIGH | Templates + Spawn |
| 4 | Protocol checks messages too late | HIGH | MCP Server |
| 5 | Spawn prompt too minimal | HIGH | Orchestrator |
| 6 | Python-style examples confuse agents | HIGH | Templates |

---

## RECOMMENDED FIXES

### Fix 1: Template Tool Name Correction

**Files:** All `.claude/agents/*.md`

**Action:** Find/replace
- Find: `mcp__giljo_mcp__`
- Replace: `mcp__giljo-mcp__`

---

### Fix 2: Remove Non-Existent Tool References

**Files:** All `.claude/agents/*.md`

**Action:** Remove all references to `update_job_status`. Replace with:

| Old (REMOVE) | New (USE) |
|--------------|-----------|
| `update_job_status(new_status="active")` | `acknowledge_job(job_id, agent_id)` |
| `update_job_status(new_status="completed")` | `complete_job(job_id, result)` |
| `update_job_status(new_status="blocked")` | `report_error(job_id, error)` |

---

### Fix 3: Add Critical Warning Box

**Files:** All `.claude/agents/*.md`

**Action:** Add this IMMEDIATELY after YAML frontmatter:

```markdown
---
name: analyzer
description: ...
model: sonnet
---

## CRITICAL: MCP TOOL USAGE

**MCP tools are NATIVE tool calls - use them like Read, Write, Bash, Glob.**

- CORRECT: Call `mcp__giljo-mcp__get_agent_mission` as a tool with parameters
- WRONG: curl, HTTP requests, fetch(), requests.post(), SDK calls

The tools are already connected. Just call them directly.

---
```

---

### Fix 4: Update Phase 1 to Check Messages

**Files:** All `.claude/agents/*.md`

**Current Phase 1:**
```
1. Call get_pending_jobs
2. Find your assigned job
3. Call acknowledge_job
4. Update job status (DOESN'T EXIST!)
```

**New Phase 1:**
```
### Phase 1: Job Acknowledgment (BEFORE ANY WORK)
1. Call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)` - Get mission
2. Call `mcp__giljo-mcp__acknowledge_job(job_id, agent_id)` - Mark as WORKING
3. Call `mcp__giljo-mcp__receive_messages(agent_id)` - Check for instructions
4. Review any messages BEFORE starting work
```

---

### Fix 5: Change Example Format

**Files:** All `.claude/agents/*.md`

**Current (confusing):**
```python
mcp.call_tool("mcp__giljo_mcp__update_job_status", {
    "job_id": "your-job-id",
    "new_status": "active"
})
```

**New (clear):**
```
Tool: mcp__giljo-mcp__acknowledge_job
Parameters:
  - job_id: "your-job-id"
  - agent_id: "analyzer"
```

---

### Fix 6: Enhanced Spawn Prompt Template

**Location:** Orchestrator instructions (the 128-line prompt)

**Add this spawn prompt template for orchestrator to use:**

```markdown
## AGENT: {agent_name}
Job ID: {job_id}
Tenant: {tenant_key}

---

## CRITICAL: MCP TOOL USAGE (READ THIS FIRST)

MCP tools are **NATIVE tool calls** - identical to Read, Write, Bash, Glob.
- CORRECT: Call `mcp__giljo-mcp__get_agent_mission` directly as a tool
- WRONG: curl, HTTP, fetch, requests, SDK calls

---

## MANDATORY STARTUP SEQUENCE

Execute these IN ORDER before starting your mission:

1. **Get Mission:**
   Tool: `mcp__giljo-mcp__get_agent_mission`
   Params: agent_job_id="{job_id}", tenant_key="{tenant_key}"

2. **Acknowledge Job (marks you as WORKING):**
   Tool: `mcp__giljo-mcp__acknowledge_job`
   Params: job_id="{job_id}", agent_id="{agent_name}"

3. **Check Messages (BEFORE starting work):**
   Tool: `mcp__giljo-mcp__receive_messages`
   Params: agent_id="{agent_name}"

4. **Execute your mission** (details in get_agent_mission response)

5. **Report Progress** (after each milestone):
   Tool: `mcp__giljo-mcp__report_progress`
   Params: job_id="{job_id}", progress={"percent": X, "message": "..."}

6. **Complete Job** (when done):
   Tool: `mcp__giljo-mcp__complete_job`
   Params: job_id="{job_id}", result={"summary": "...", "artifacts": [...]}

---

Your full mission is in the database. Call get_agent_mission to retrieve it.
```

---

### Fix 7: MCP Server full_protocol Update

**Location:** MCP server code that generates `full_protocol` in `get_agent_mission` response

**New Protocol:**
```markdown
## Agent Lifecycle Protocol (5 Phases)

### Phase 1: STARTUP (BEFORE ANY WORK)
1. Call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)` - Get mission
2. Call `mcp__giljo-mcp__acknowledge_job(job_id, agent_id)` - Mark as WORKING
3. Call `mcp__giljo-mcp__receive_messages(agent_id)` - Check for instructions
4. Review any messages and incorporate feedback BEFORE starting work

### Phase 2: EXECUTION
- Execute assigned tasks from mission
- Use todo lists to track progress internally
- Maintain focus on mission objectives

### Phase 3: PROGRESS REPORTING (After each milestone)
1. Call `mcp__giljo-mcp__report_progress(job_id, progress)`
2. Call `mcp__giljo-mcp__receive_messages(agent_id)` - Check for new instructions
3. Incorporate any orchestrator feedback before continuing

### Phase 4: COMPLETION
1. Call `mcp__giljo-mcp__complete_job(job_id, result)`
2. Await acknowledgment or further instructions

### Phase 5: ERROR HANDLING (If blocked)
1. Call `mcp__giljo-mcp__report_error(job_id, error)` - Marks job as BLOCKED
2. STOP work and await orchestrator guidance

---
**CRITICAL: MCP tools are NATIVE tool calls. Use them like Read/Write/Bash.**
**Do NOT use curl, HTTP, or SDK calls.**
```

---

## FILES TO MODIFY

| File | Changes Required |
|------|------------------|
| `F:\TinyContacts\.claude\agents\analyzer.md` | Fixes 1-5 |
| `F:\TinyContacts\.claude\agents\implementer.md` | Fixes 1-5 |
| `F:\TinyContacts\.claude\agents\documenter.md` | Fixes 1-5 |
| `F:\TinyContacts\.claude\agents\reviewer.md` | Fixes 1-5 |
| `F:\TinyContacts\.claude\agents\tester.md` | Fixes 1-5 |
| Orchestrator prompt document | Fix 6 (spawn template) |
| MCP server `full_protocol` generation | Fix 7 (phase order) |

---

## TESTING PLAN

After implementing fixes:

1. **Single Agent Test:**
   - Spawn analyzer with corrected spawn prompt
   - Verify: get_agent_mission called
   - Verify: acknowledge_job called
   - Verify: receive_messages called BEFORE work starts
   - Verify: Workflow status shows agent as "working" not "waiting"

2. **Multi-Agent Test:**
   - Spawn all 3 agents in parallel
   - Verify all follow startup sequence
   - Verify workflow_status shows correct counts

3. **Message Test:**
   - Send message to agent mid-work via orchestrator
   - Verify agent receives and acknowledges message
   - Verify agent incorporates feedback

---

## CONCLUSION

The GiljoAI MCP infrastructure is working correctly. The integration failures were caused by documentation/template mismatches:

1. **Templates had wrong tool names** (underscore vs hyphen)
2. **Templates referenced non-existent tools** (update_job_status)
3. **Protocol order was wrong** (check messages too late)
4. **Examples used confusing format** (Python SDK style)
5. **Spawn prompts lacked explicit instructions** (assumed templates were sufficient)

With the recommended fixes, agents will:
- Understand MCP tools are native calls
- Call correct tools with correct names
- Check messages before starting work
- Report status changes properly
- Coordinate with orchestrator effectively

---

**Report Generated By:** Orchestrator 6792fae5-c46b-4ed7-86d6-df58aa833df3
**Test Project:** TinyContacts (97d95e5a-51dd-47ae-92de-7f8839de503a)
**MCP Server Version:** 3.1.0
