# Handover 0278: Mode-Aware MCP Catalog & Agent Profile Architecture

> **⚠️ SUPERSEDED** - This handover was never implemented. The problem it aimed to solve
> (mode-aware MCP responses, token reduction) was addressed differently via **Handover 0285**
> (Enhanced MCP Tool Descriptions). That approach embeds WHO/WHEN/WHAT guidance directly in
> tool descriptions, eliminating the need for `execution_mode` parameter differentiation.
>
> Archived: 2025-12-03

**Date**: 2025-12-01
**Status**: ❌ SUPERSEDED (by Handover 0285)
**Type**: Architecture Enhancement
**Impact**: Critical - Fixes multi-terminal agent prompts, enables mode-aware MCP catalogs
**Prerequisite**: Handover 0277 (Serena simplification) complete

---

## Executive Summary

**Problem**: Multi-terminal agent prompts are bloated (2000+ lines) and missing agent profiles. Claude Code CLI mode and Multi-Terminal mode have different profile sourcing needs but share same MCP response structure.

**Solution**:
1. Enhanced `get_agent_mission()` MCP tool returns mode-aware responses
2. Multi-terminal agents get profile from MCP (server-managed)
3. Claude Code agents get profile from local `.md` files (client-managed)
4. Split MCP catalog: lean for Claude Code, full for Multi-Terminal
5. Lean multi-terminal paste (~10 lines vs 2000+)

**Token Savings**: ~1,950 tokens per agent paste in multi-terminal mode

---

## Architecture Overview (ASCII)

### System Architecture Reality

```
┌─────────────────────────────────────────────────────────────────┐
│                      GILJOAI MCP SERVER                          │
│                    (Central Hub - Server PC)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              PostgreSQL Database                          │  │
│  │  - AgentTemplate (profiles, rules, expertise)            │  │
│  │  - MCPAgentJob (missions, status, metadata)              │  │
│  │  - Project (mission, description)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              MCP Tools (HTTP Endpoints)                   │  │
│  │  - get_orchestrator_instructions()                        │  │
│  │  - get_agent_mission()  ← ENHANCED IN THIS HANDOVER      │  │
│  │  - spawn_agent_job()                                      │  │
│  │  - report_progress()                                      │  │
│  │  - complete_job()                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    MCP-over-HTTP (JSON-RPC)
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌───────────────────┐                  ┌───────────────────┐
│   CLIENT PC #1    │                  │   CLIENT PC #2    │
│ (Claude Code CLI) │                  │ (Multi-Terminal)  │
├───────────────────┤                  ├───────────────────┤
│                   │                  │                   │
│ ~/.claude/agents/ │                  │  Terminal 1:      │
│  ├─ orchestrator.md│                 │    Orchestrator   │
│  ├─ implementer.md│ ← LOCAL FILES   │  Terminal 2:      │
│  ├─ tester.md     │                  │    Implementer    │
│  └─ analyzer.md   │                  │  Terminal 3:      │
│                   │                  │    Tester         │
│ Profile Source:   │                  │                   │
│   LOCAL .md files │                  │ Profile Source:   │
│                   │                  │   MCP SERVER      │
└───────────────────┘                  └───────────────────┘
```

**Key Insight**: Agents run on **Client PC**, not on MCP server. They only communicate via MCP-over-HTTP.

---

## Current State Problems

### Problem 1: Multi-Terminal Agent Prompt Bloat

**Current Implementation** (`api/endpoints/prompts.py` lines 224-319):

```bash
# Agent: Implementer Agent
# Type: implementer
# Mission: [FULL 1000-LINE MISSION EMBEDDED HERE]

cd /project/path
export AGENT_ID=agent_001
mkdir -p .missions
cat > .missions/agent_001.md << 'EOF'
[ENTIRE MISSION TEXT - 1000+ LINES]
EOF

claude-agent execute --mission-file=.missions/agent_001.md
```

**Problems**:
- ❌ Mission embedded in paste (1000+ lines)
- ❌ No agent profile/expertise
- ❌ No behavioral rules
- ❌ No MCP instructions
- ❌ Assumes bash works (not universal)
- ❌ Creates file on disk (.missions/ folder)

---

### Problem 2: Missing Agent Profile in Multi-Terminal

**Current Flow**:
```
User pastes → Agent prompt (no profile)
              ↓
Agent calls → get_agent_mission(job_id, tenant_key)
              ↓
Returns:      { "mission": "...", "estimated_tokens": 250 }
              ↓
Agent has:    ❌ No expertise guidance
              ❌ No behavioral rules
              ❌ No success criteria
              ❌ No MCP tool catalog
```

**Root Cause**: `get_agent_mission()` only returns mission text, not agent profile.

---

### Problem 3: One-Size-Fits-All MCP Response

**Current `get_agent_mission()` Response** (`src/giljo_mcp/tools/orchestration.py` lines 306-389):

```python
return {
    "success": True,
    "agent_job_id": agent_job_id,
    "agent_name": agent_job.agent_type,
    "agent_type": agent_job.agent_type,
    "mission": agent_job.mission or "",
    "project_id": str(agent_job.project_id),
    "estimated_tokens": estimated_tokens,
    "status": agent_job.status,
    "thin_client": True,
}
```

**Problems**:
- ❌ No agent profile (from AgentTemplate table)
- ❌ No MCP catalog
- ❌ Same response for both execution modes
- ❌ Claude Code agents get profile twice (local .md + MCP would be redundant)
- ❌ Multi-terminal agents get no profile at all

---

## Proposed Solution Architecture

### Solution Flow Comparison (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLAUDE CODE CLI MODE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

USER ACTION:
  ┌─────────────────────────────────────────┐
  │ Paste 1 prompt → Orchestrator terminal  │
  └──────────────────┬──────────────────────┘
                     ▼
ORCHESTRATOR:
  ┌──────────────────────────────────────────────────────────────────┐
  │ 1. Read ~/.claude/agents/implementer.md (LOCAL FILE)            │
  │    ├─ Agent expertise ✅                                         │
  │    ├─ Behavioral rules ✅                                        │
  │    └─ "FIRST ACTION: get_agent_mission(job_id, tenant_key)"     │
  │                                                                   │
  │ 2. Spawn @implementer subagent                                   │
  │    └─ Pass: agent_id, job_id, project_id, tenant_key           │
  └──────────────────┬───────────────────────────────────────────────┘
                     ▼
IMPLEMENTER SUBAGENT:
  ┌──────────────────────────────────────────────────────────────────┐
  │ 1. Already has profile from ~/.claude/agents/implementer.md     │
  │                                                                   │
  │ 2. Call: get_agent_mission(job_id, tenant_key, mode="claude")   │
  │    ├─ include_profile=False (already have it locally)           │
  │    └─ Returns:                                                   │
  │        {                                                         │
  │          "mission": "Implement auth feature...",                 │
  │          "mcp_catalog": {                                        │
  │            "mode": "claude_code_cli",                            │
  │            "essential_tools": [                                  │
  │              "report_progress(job_id, progress)",                │
  │              "complete_job(job_id, result)"                      │
  │            ],                                                    │
  │            "coordination": "Use native conversation"             │
  │          }                                                       │
  │        }                                                         │
  │                                                                   │
  │ 3. Execute mission using local profile + MCP mission            │
  └──────────────────────────────────────────────────────────────────┘

PROFILE SOURCE: ~/.claude/agents/*.md (CLIENT PC)
MCP CATALOG: Lean (3-5 essential tools only)


┌─────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-TERMINAL MODE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

USER ACTION:
  ┌─────────────────────────────────────────────────────────────┐
  │ Paste 3 prompts:                                            │
  │   Terminal 1 → Orchestrator                                 │
  │   Terminal 2 → Implementer (lean ~10 lines)                 │
  │   Terminal 3 → Tester (lean ~10 lines)                      │
  └──────────────────┬──────────────────────────────────────────┘
                     ▼
IMPLEMENTER AGENT (Terminal 2):
  ┌──────────────────────────────────────────────────────────────────┐
  │ Paste contains:                                                  │
  │   You are the Implementer Agent.                                 │
  │                                                                   │
  │   Agent ID: agent_001                                            │
  │   Job ID: job_123                                                │
  │   Tenant: tenant_456                                             │
  │                                                                   │
  │   FIRST ACTION: get_agent_mission('job_123', 'tenant_456')      │
  │                                                                   │
  │ ──────────────────────────────────────────────────────────────  │
  │                                                                   │
  │ 1. Call: get_agent_mission(job_id, tenant_key, mode="multi")    │
  │    ├─ include_profile=True (no local .md files)                 │
  │    └─ Returns:                                                   │
  │        {                                                         │
  │          "mission": "Implement auth feature...",                 │
  │          "agent_profile": {                                      │
  │            "expertise": "Production-grade code specialist",      │
  │            "behavioral_rules": [                                 │
  │              "Follow TDD discipline",                            │
  │              "Write cross-platform code (use Path())",           │
  │              "Production-ready from start"                       │
  │            ],                                                    │
  │            "success_criteria": [                                 │
  │              "All tests passing",                                │
  │              "Code reviewed",                                    │
  │              "Documentation updated"                             │
  │            ]                                                     │
  │          },                                                      │
  │          "mcp_catalog": {                                        │
  │            "mode": "multi_terminal",                             │
  │            "essential_tools": [                                  │
  │              "get_agent_mission(job_id, tenant_key)",            │
  │              "report_progress(job_id, progress)",                │
  │              "complete_job(job_id, result)"                      │
  │            ],                                                    │
  │            "coordination_tools": [                               │
  │              "send_message(to_agent, content)",                  │
  │              "receive_messages(agent_id)",                       │
  │              "broadcast(content, project_id)",                   │
  │              "get_workflow_status(project_id)"                   │
  │            ],                                                    │
  │            "coordination": "Use MCP messaging for agent comms"   │
  │          }                                                       │
  │        }                                                         │
  │                                                                   │
  │ 2. Execute mission using MCP profile + mission                  │
  └──────────────────────────────────────────────────────────────────┘

PROFILE SOURCE: MCP get_agent_mission() response (SERVER)
MCP CATALOG: Full (10-15 tools including coordination)
```

---

## Mode Comparison Matrix

| Aspect | Claude Code CLI Mode | Multi-Terminal Mode |
|--------|---------------------|---------------------|
| **User Pastes** | 1 orchestrator prompt | N agent prompts (1 per terminal) |
| **Paste Size** | ~600 tokens (orchestrator) | ~50 tokens per agent |
| **Agent Profile Source** | Local `~/.claude/agents/*.md` | MCP `get_agent_mission()` |
| **Mission Source** | MCP `get_agent_mission()` | MCP `get_agent_mission()` |
| **Profile in MCP Response** | ❌ No (redundant, already local) | ✅ Yes (only source) |
| **MCP Catalog Size** | Lean (3-5 essential tools) | Full (10-15 tools + coordination) |
| **Coordination Method** | Native conversation (subagents) | MCP messaging tools |
| **Template Maintenance** | User exports once, rarely updates | Server-managed, always current |
| **Template Location** | Client PC `~/.claude/agents/` | Server database `AgentTemplate` table |

---

## Implementation Plan

### Phase 1: Enhance `get_agent_mission()` MCP Tool

**File**: `src/giljo_mcp/tools/orchestration.py`

**Current Signature** (lines 306-389):
```python
async def get_agent_mission(agent_job_id: str, tenant_key: str) -> dict[str, Any]:
```

**New Signature**:
```python
async def get_agent_mission(
    agent_job_id: str,
    tenant_key: str,
    execution_mode: str = "multi_terminal"  # NEW: "claude_code_cli" or "multi_terminal"
) -> dict[str, Any]:
```

**New Implementation**:
```python
async def get_agent_mission(
    agent_job_id: str,
    tenant_key: str,
    execution_mode: str = "multi_terminal"
) -> dict[str, Any]:
    """
    Fetch agent-specific mission and context (Mode-Aware Architecture).

    Returns different response structure based on execution mode:
    - claude_code_cli: Mission + lean MCP catalog (profile in local .md)
    - multi_terminal: Mission + profile + full MCP catalog (no local .md)

    Args:
        agent_job_id: Agent job UUID
        tenant_key: Tenant isolation key
        execution_mode: "claude_code_cli" or "multi_terminal" (default)

    Returns:
        Mode-aware dictionary containing mission, optional profile, and MCP catalog
    """
    try:
        async with db_manager.get_session_async() as session:
            # Fetch agent job
            result = await session.execute(
                select(MCPAgentJob).where(
                    and_(
                        MCPAgentJob.job_id == agent_job_id,
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
            )
            agent_job = result.scalar_one_or_none()

            if not agent_job:
                return {
                    "error": "NOT_FOUND",
                    "message": f"Agent job {agent_job_id} not found"
                }

            # Fetch agent template (for multi-terminal profile)
            template = None
            if execution_mode == "multi_terminal":
                template_result = await session.execute(
                    select(AgentTemplate).where(
                        and_(
                            AgentTemplate.name == agent_job.agent_type,
                            AgentTemplate.tenant_key == tenant_key,
                            AgentTemplate.is_active == True
                        )
                    )
                )
                template = template_result.scalar_one_or_none()

            # Build base response
            response = {
                "success": True,
                "agent_job_id": agent_job_id,
                "agent_name": agent_job.agent_type,
                "agent_type": agent_job.agent_type,
                "mission": agent_job.mission or "",
                "project_id": str(agent_job.project_id),
                "status": agent_job.status,
                "execution_mode": execution_mode,
                "thin_client": True,
            }

            # Add profile for multi-terminal mode
            if execution_mode == "multi_terminal" and template:
                response["agent_profile"] = {
                    "expertise": template.user_instructions or "",
                    "behavioral_rules": template.behavioral_rules or [],
                    "success_criteria": template.success_criteria or [],
                    "system_instructions": template.system_instructions or ""
                }

            # Add mode-aware MCP catalog
            response["mcp_catalog"] = _generate_mcp_catalog(
                execution_mode=execution_mode,
                agent_type=agent_job.agent_type
            )

            return response

    except Exception as e:
        logger.error(f"[ERROR] Failed to get agent mission: {e}", exc_info=True)
        return {
            "error": "INTERNAL_ERROR",
            "message": f"Unexpected error: {e!s}"
        }
```

---

### Phase 2: Create Mode-Aware MCP Catalog Generator

**New File**: `src/giljo_mcp/prompt_generation/mode_aware_catalog.py`

```python
"""
Mode-Aware MCP Catalog Generator (Handover 0278)

Generates different MCP tool catalogs based on execution mode:
- Claude Code CLI: Lean catalog (3-5 essential tools, no coordination)
- Multi-Terminal: Full catalog (10-15 tools, full coordination suite)
"""

from typing import Literal

ExecutionMode = Literal["claude_code_cli", "multi_terminal"]


def generate_mcp_catalog(
    execution_mode: ExecutionMode,
    agent_type: str
) -> dict:
    """
    Generate mode-aware MCP catalog.

    Args:
        execution_mode: "claude_code_cli" or "multi_terminal"
        agent_type: Agent role (orchestrator, implementer, tester, etc.)

    Returns:
        MCP catalog dictionary with mode-specific tools
    """
    if execution_mode == "claude_code_cli":
        return _generate_claude_code_catalog(agent_type)
    else:
        return _generate_multi_terminal_catalog(agent_type)


def _generate_claude_code_catalog(agent_type: str) -> dict:
    """
    Lean catalog for Claude Code CLI mode.

    Agents use native conversation for coordination.
    Only essential MCP tools needed.
    """
    return {
        "mode": "claude_code_cli",
        "coordination_method": "Native conversation with orchestrator and subagents",
        "profile_source": "Local ~/.claude/agents/{agent_type}.md file",
        "essential_tools": [
            {
                "name": "report_progress",
                "signature": "report_progress(job_id: str, progress: dict)",
                "when": "After each milestone (25%, 50%, 75%, 100%)",
                "why": "Keep orchestrator informed of progress"
            },
            {
                "name": "complete_job",
                "signature": "complete_job(job_id: str, result: dict)",
                "when": "When all work is finished",
                "why": "Mark job as complete and submit deliverables"
            },
            {
                "name": "report_error",
                "signature": "report_error(job_id: str, error: str)",
                "when": "If blocked or encountering fatal errors",
                "why": "Escalate to orchestrator for intervention"
            }
        ],
        "coordination_guidance": """
## Coordination in Claude Code Mode

You are a subagent in the orchestrator's session. Coordinate via:
- **Native conversation**: Talk directly with orchestrator and other subagents
- **MCP tools**: Only for progress tracking and completion
- **No messaging tools needed**: You share context natively

When blocked: Report to orchestrator in conversation, use report_error() for DB tracking.
        """.strip(),
        "estimated_tokens": 420
    }


def _generate_multi_terminal_catalog(agent_type: str) -> dict:
    """
    Full catalog for Multi-Terminal mode.

    Agents are independent terminals, need full coordination suite.
    """
    return {
        "mode": "multi_terminal",
        "coordination_method": "MCP messaging tools (independent terminals)",
        "profile_source": "MCP get_agent_mission() response (server-managed)",
        "essential_tools": [
            {
                "name": "report_progress",
                "signature": "report_progress(job_id: str, progress: dict)",
                "when": "After each milestone (25%, 50%, 75%, 100%)",
                "why": "Update orchestrator and UI dashboard"
            },
            {
                "name": "complete_job",
                "signature": "complete_job(job_id: str, result: dict)",
                "when": "When all work is finished",
                "why": "Mark job as complete and submit deliverables"
            },
            {
                "name": "report_error",
                "signature": "report_error(job_id: str, error: str)",
                "when": "If blocked or encountering fatal errors",
                "why": "Pause job and escalate to orchestrator"
            }
        ],
        "coordination_tools": [
            {
                "name": "send_message",
                "signature": "send_message(to_agent: str, content: str, project_id: str)",
                "when": "Need to coordinate with specific agent",
                "why": "Direct agent-to-agent communication",
                "example": "send_message('tester', 'Auth implementation ready for testing', project_id)"
            },
            {
                "name": "receive_messages",
                "signature": "receive_messages(agent_id: str, project_id: str)",
                "when": "Check for updates from other agents",
                "why": "Poll for pending messages (every 5-10 minutes)",
                "example": "receive_messages(agent_id, project_id)"
            },
            {
                "name": "broadcast",
                "signature": "broadcast(content: str, project_id: str, priority: str)",
                "when": "Announce milestone to entire team",
                "why": "Notify all agents of important updates",
                "example": "broadcast('Database migration complete', project_id, 'high')"
            },
            {
                "name": "get_workflow_status",
                "signature": "get_workflow_status(project_id: str, tenant_key: str)",
                "when": "Check team progress before proceeding",
                "why": "See status of all agents in project",
                "example": "get_workflow_status(project_id, tenant_key)"
            }
        ],
        "coordination_guidance": """
## Coordination in Multi-Terminal Mode

You are an independent agent in a separate terminal. Coordinate via:
- **MCP messaging tools**: Required for all agent communication
- **Polling**: Check receive_messages() every 5-10 minutes
- **Broadcasts**: Use for milestone announcements
- **Workflow status**: Check get_workflow_status() before dependencies

Pattern:
1. Start work → report_progress(25%)
2. Check receive_messages() for updates
3. Reach milestone → broadcast() to team
4. Need dependency → send_message() to specific agent
5. Complete work → complete_job()

When blocked: send_message() to orchestrator + report_error() for tracking.
        """.strip(),
        "estimated_tokens": 1850
    }


def get_catalog_for_orchestrator_staging() -> dict:
    """
    Catalog for orchestrator during staging phase (5-task workflow).

    Same for both execution modes - staging happens before mode matters.
    """
    return {
        "phase": "staging",
        "workflow": "5-task staging sequence",
        "tools": [
            {
                "task": 1,
                "name": "health_check",
                "signature": "health_check()",
                "purpose": "Verify MCP connection",
                "required": True,
                "timeout": "2 seconds"
            },
            {
                "task": 2,
                "name": "get_orchestrator_instructions",
                "signature": "get_orchestrator_instructions(orchestrator_id, tenant_key)",
                "purpose": "Fetch full context and mission-building instructions",
                "required": True,
                "timeout": "10 seconds"
            },
            {
                "task": 3,
                "name": "Analyze & Create Mission",
                "signature": "N/A (agent reasoning)",
                "purpose": "Synthesize mission from context",
                "required": True
            },
            {
                "task": 4,
                "name": "update_project_mission",
                "signature": "update_project_mission(project_id, mission)",
                "purpose": "Persist mission to database",
                "required": True,
                "timeout": "5 seconds"
            },
            {
                "task": 5,
                "name": "spawn_agent_job",
                "signature": "spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)",
                "purpose": "Create agent database records (Type 1 spawning)",
                "required": True,
                "repeat": "For each agent needed",
                "timeout": "3 seconds per agent"
            }
        ],
        "estimated_tokens": 850
    }
```

---

### Phase 3: Update Multi-Terminal Agent Prompt Generator

**File**: `api/endpoints/prompts.py`

**Current** (lines 224-319):
```python
@router.get("/agent/{agent_id}", response_model=AgentPromptResponse)
async def generate_agent_prompt(agent_id: str, ...):
    # [Bloaty bash script generation - 2000+ lines]
```

**New Implementation**:
```python
@router.get("/agent/{agent_id}", response_model=AgentPromptResponse)
async def generate_agent_prompt(
    agent_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate lean multi-terminal agent prompt (Handover 0278).

    Agent fetches profile + mission from MCP (not embedded in paste).
    Paste is ~10 lines instead of 2000+.
    """
    # Get agent job with tenant isolation
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == agent_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Generate lean prompt (fetch-first pattern)
    agent_display_name = agent.agent_name or f"{agent.agent_type.title()} Agent"

    prompt = f"""You are the {agent_display_name}.

**IDENTITY:**
Agent ID: {agent.job_id}
Job ID: {agent.job_id}
Project ID: {agent.project_id}
Tenant: {current_user.tenant_key}

**FIRST ACTION (MANDATORY):**
Call: get_agent_mission('{agent.job_id}', '{current_user.tenant_key}', execution_mode='multi_terminal')

This returns:
- Your specific mission assignment
- Agent profile (expertise, behavioral rules, success criteria)
- MCP tool catalog (full coordination suite)
- Coordination protocol

DO NOT begin work until mission is fetched and understood.
"""

    instructions = f"""Copy the prompt above to your terminal to start this agent.

**Agent Details:**
- Name: {agent_display_name}
- Type: {agent.agent_type}
- Status: {agent.status}

**Prerequisites:**
- Claude Code or compatible CLI tool installed
- MCP connection to server configured
- Agent will fetch all instructions from MCP server

**What Happens Next:**
1. Agent calls get_agent_mission() (FIRST ACTION)
2. Receives mission + profile + MCP catalog from server
3. Begins work following mission instructions
4. Coordinates with other agents via MCP messaging tools
"""

    return AgentPromptResponse(
        prompt=prompt,
        agent_id=agent.job_id,
        agent_name=agent_display_name,
        agent_type=agent.agent_type,
        tool_type=agent.tool_type or "claude",
        instructions=instructions,
        mission_preview="[Mission fetched from MCP - not embedded in paste]",
        estimated_tokens=len(prompt) // 4
    )
```

**Token Savings**:
- Before: ~8,000 tokens per agent paste (2000-line mission embedded)
- After: ~200 tokens per agent paste (mission fetched via MCP)
- **Savings: ~7,800 tokens per agent (~97% reduction)**

---

### Phase 4: Update Claude Code Orchestrator Execution Prompt

**File**: `src/giljo_mcp/thin_prompt_generator.py`

**Method**: `_build_claude_code_execution_prompt()` (lines 1246-1300)

**Current**:
```python
"STEP 2: REMIND EACH SUB-AGENT",
"- acknowledge_job(job_id=\"{job_id}\", agent_id=\"{agent_id}\", tenant_key=\"...\")",
"- report_progress() after milestones",
```

**Enhanced**:
```python
"STEP 2: SPAWN SUB-AGENTS",
"For each agent, use Claude Code Task tool:",
"",
"Example:",
"  You are spawning the Implementer subagent.",
"  ",
"  Agent Identity:",
"  - Name: implementer",
"  - Agent ID: agent_001",
"  - Job ID: job_123",
"  - Project ID: proj_abc",
"  - Tenant: tenant_456",
"  ",
"  First Action:",
"  Call get_agent_mission('job_123', 'tenant_456', execution_mode='claude_code_cli')",
"  ",
"  This returns your mission + lean MCP catalog.",
"  Your profile is already in ~/.claude/agents/implementer.md",
"",
"STEP 3: COORDINATION",
"- Subagents coordinate via native conversation (you're in same session)",
"- No MCP messaging needed (use for progress tracking only)",
"- Monitor via get_workflow_status()",
```

---

### Phase 5: Update Agent Template Export

**File**: `src/giljo_mcp/template_manager.py` or export endpoint

**Enhanced `.md` Template Format**:

```markdown
# {agent_type}.md - {Agent Display Name}

You are the {Agent Display Name} - {brief expertise description}.

## Expertise
{user_instructions from AgentTemplate}

## Behavioral Rules
{behavioral_rules from AgentTemplate as bullet list}

## Success Criteria
{success_criteria from AgentTemplate as bullet list}

---

## FIRST ACTION (MANDATORY)

Call: get_agent_mission('{job_id}', '{tenant_key}', execution_mode='claude_code_cli')

**Parameters will be provided when orchestrator spawns you.**

This returns:
- Your specific mission assignment
- Lean MCP catalog (essential tools only)
- Coordination guidance

DO NOT begin work until mission is fetched.

---

## MCP Tools Available

You will receive the full MCP catalog when you call get_agent_mission().
Key tools:
- report_progress() - Update after milestones
- complete_job() - Submit deliverables
- report_error() - Escalate blockers

Use native conversation for coordination with orchestrator and other subagents.
```

**Token Size**: ~300-500 tokens per template (vs 1500+ previously)

---

## Files to Modify

### Backend (Python)

1. **`src/giljo_mcp/tools/orchestration.py`** (lines 306-389)
   - Enhance `get_agent_mission()` signature
   - Add `execution_mode` parameter
   - Add agent profile fetching for multi-terminal mode
   - Add MCP catalog generation

2. **`src/giljo_mcp/prompt_generation/mode_aware_catalog.py`** (NEW FILE)
   - Create `generate_mcp_catalog()` function
   - Create `_generate_claude_code_catalog()` function
   - Create `_generate_multi_terminal_catalog()` function
   - Create `get_catalog_for_orchestrator_staging()` function

3. **`api/endpoints/prompts.py`** (lines 224-319)
   - Rewrite `generate_agent_prompt()` to use lean fetch-first pattern
   - Remove bash script generation
   - Remove mission embedding
   - Add `get_agent_mission()` call instruction

4. **`src/giljo_mcp/thin_prompt_generator.py`** (lines 1246-1300)
   - Update `_build_claude_code_execution_prompt()` with spawn instructions
   - Add execution_mode parameter passing
   - Update coordination guidance

5. **`src/giljo_mcp/template_manager.py`** or export endpoint
   - Update agent template export to include fetch-first instructions
   - Add execution_mode awareness
   - Simplify template to ~300-500 tokens

### Frontend (Vue)

6. **`frontend/src/components/orchestration/AgentCardGrid.vue`** or similar
   - Update "Copy Prompt" button to use new lean prompt endpoint
   - Add execution mode badge/indicator
   - Update tooltip/help text

### Testing

7. **`tests/test_orchestration.py`** (NEW or enhance existing)
   - Test `get_agent_mission()` with both modes
   - Verify profile included only for multi-terminal
   - Verify catalog differences between modes

8. **`tests/integration/test_agent_prompts.py`** (NEW)
   - Test multi-terminal prompt generation
   - Test Claude Code prompt generation
   - Verify token counts (~200 vs ~8000)

---

## Testing Strategy

### Unit Tests

```python
# tests/test_orchestration.py

async def test_get_agent_mission_claude_code_mode(db_session, test_agent_job):
    """
    Claude Code mode: No profile (redundant, in local .md), lean catalog
    """
    result = await get_agent_mission(
        agent_job_id=test_agent_job.job_id,
        tenant_key=test_agent_job.tenant_key,
        execution_mode="claude_code_cli"
    )

    assert result["success"] == True
    assert "mission" in result
    assert "agent_profile" not in result  # ← Profile NOT included
    assert result["mcp_catalog"]["mode"] == "claude_code_cli"
    assert len(result["mcp_catalog"]["essential_tools"]) <= 5
    assert "coordination_tools" not in result["mcp_catalog"]


async def test_get_agent_mission_multi_terminal_mode(db_session, test_agent_job, test_template):
    """
    Multi-terminal mode: Profile included, full catalog
    """
    result = await get_agent_mission(
        agent_job_id=test_agent_job.job_id,
        tenant_key=test_agent_job.tenant_key,
        execution_mode="multi_terminal"
    )

    assert result["success"] == True
    assert "mission" in result
    assert "agent_profile" in result  # ← Profile INCLUDED
    assert result["agent_profile"]["expertise"] == test_template.user_instructions
    assert result["mcp_catalog"]["mode"] == "multi_terminal"
    assert len(result["mcp_catalog"]["essential_tools"]) >= 3
    assert "coordination_tools" in result["mcp_catalog"]
    assert len(result["mcp_catalog"]["coordination_tools"]) >= 4


async def test_multi_terminal_prompt_generation(async_client, test_agent_job):
    """
    Multi-terminal prompt should be lean (~200 tokens)
    """
    response = await async_client.get(f"/api/prompts/agent/{test_agent_job.job_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify lean prompt
    assert len(data["prompt"]) < 1000  # ~200 tokens, max 1000 chars
    assert "get_agent_mission" in data["prompt"]
    assert "execution_mode='multi_terminal'" in data["prompt"]

    # Verify mission NOT embedded
    assert test_agent_job.mission not in data["prompt"]
    assert "Mission fetched from MCP" in data["mission_preview"]
```

### Integration Tests

```python
# tests/integration/test_mode_aware_flow.py

async def test_claude_code_cli_flow(async_client, test_orchestrator_job):
    """
    End-to-end Claude Code CLI mode flow
    """
    # 1. Get orchestrator staging prompt
    response = await async_client.get(f"/api/prompts/staging/{test_orchestrator_job.job_id}")
    staging_prompt = response.json()["prompt"]

    # Verify staging prompt exists and is lean
    assert "claude_code_cli" in staging_prompt or "Claude Code" in staging_prompt

    # 2. Simulate orchestrator calling get_agent_mission (claude mode)
    # (Would be called by actual Claude Code orchestrator)
    # Verify it gets mission + lean catalog, no profile


async def test_multi_terminal_flow(async_client, test_agent_job):
    """
    End-to-end Multi-Terminal mode flow
    """
    # 1. Get multi-terminal agent prompt
    response = await async_client.get(f"/api/prompts/agent/{test_agent_job.job_id}")
    agent_prompt = response.json()["prompt"]

    # Verify lean prompt
    assert len(agent_prompt) < 1000
    assert "get_agent_mission" in agent_prompt
    assert "multi_terminal" in agent_prompt

    # 2. Simulate agent calling get_agent_mission (multi mode)
    # (Would be called by actual agent in terminal)
    # Verify it gets mission + profile + full catalog
```

---

## Migration Strategy

### Step 1: Backward Compatible Implementation

**Phase A**: Add new `execution_mode` parameter with default
```python
async def get_agent_mission(
    agent_job_id: str,
    tenant_key: str,
    execution_mode: str = "multi_terminal"  # Default to safe mode
):
```

**Result**: Existing calls work (default to multi-terminal), new calls can specify mode.

---

### Step 2: Update Orchestrator Prompts

**Claude Code Orchestrator**:
- Update spawn instructions to pass `execution_mode='claude_code_cli'`
- No breaking changes (still works without parameter)

**Multi-Terminal Prompts**:
- Update `api/endpoints/prompts.py` to generate lean prompts
- Old prompts still work (mission embedded as fallback)

---

### Step 3: Update Agent Templates

**Export New Templates**:
- Users re-export templates via "Claude Export Agents" button
- New templates include fetch-first instructions
- Old templates still work (orchestrator handles both)

---

### Step 4: Deprecation (Optional - Future)

After 2-3 releases:
- Remove mission embedding from multi-terminal prompts
- Require `execution_mode` parameter (no default)
- Log warnings when old patterns detected

---

## Success Criteria

### Functional Requirements

- ✅ Multi-terminal agent prompts are ~200 tokens (vs ~8000 previously)
- ✅ Claude Code agents get lean catalog (3-5 tools)
- ✅ Multi-terminal agents get full catalog (10-15 tools)
- ✅ Multi-terminal agents receive profile from MCP
- ✅ Claude Code agents use local .md profile (not from MCP)
- ✅ Backward compatible (old prompts still work)

### Non-Functional Requirements

- ✅ Token savings: ~7,800 tokens per multi-terminal agent paste
- ✅ Template export: ~300-500 tokens per .md file
- ✅ Test coverage: >80% for new catalog generation
- ✅ No breaking changes to existing workflows

---

## Risks & Mitigations

### Risk 1: Users with Old Templates

**Risk**: Users exported templates before this handover, missing fetch-first instructions.

**Mitigation**:
- Orchestrator prompts include spawn instructions (overrides old templates)
- Dashboard shows "Templates Outdated" warning if version mismatch
- One-click re-export button in UI

---

### Risk 2: Execution Mode Detection

**Risk**: Agent doesn't know which mode it's in, calls wrong catalog.

**Mitigation**:
- `execution_mode` parameter is EXPLICIT in all calls (no auto-detection)
- Orchestrator passes mode when spawning
- Multi-terminal prompts hard-code mode in paste

---

### Risk 3: Profile Duplication in Claude Code Mode

**Risk**: Profile sent twice (local .md + MCP response).

**Mitigation**:
- `execution_mode='claude_code_cli'` explicitly excludes profile from MCP
- Only mission + lean catalog returned

---

## Future Enhancements (Out of Scope)

1. **Dynamic Mode Detection**: Auto-detect execution mode from client headers
2. **Catalog Customization**: Per-user MCP catalog preferences
3. **Profile Versioning**: Track template version, auto-update notifications
4. **Catalog Analytics**: Track which tools agents actually use, optimize catalog

---

## Appendix: Token Analysis

### Before This Handover

**Multi-Terminal Agent Paste**:
```
Mission embedded: ~6,000 tokens
Bash commands: ~500 tokens
Headers: ~100 tokens
Total: ~6,600 tokens per agent

Project with 5 agents: ~33,000 tokens in pastes alone
```

**Claude Code Templates**:
```
Profile: ~800 tokens
MCP catalog: ~1,200 tokens
Mission template: ~200 tokens
Total: ~2,200 tokens per .md file

8 templates: ~17,600 tokens stored locally
```

---

### After This Handover

**Multi-Terminal Agent Paste**:
```
Identity: ~50 tokens
Fetch instruction: ~30 tokens
Help text: ~70 tokens
Total: ~150 tokens per agent

Project with 5 agents: ~750 tokens in pastes (95% reduction)
```

**Claude Code Templates**:
```
Profile: ~300 tokens
Fetch instruction: ~100 tokens
Total: ~400 tokens per .md file

8 templates: ~3,200 tokens stored locally (82% reduction)
```

**MCP Responses**:
```
Claude Code catalog: ~420 tokens
Multi-terminal catalog: ~1,850 tokens
Agent profile: ~600 tokens

Multi-terminal response: ~2,450 tokens (fetched on-demand, not in paste)
```

---

## References

- **Handover 0277**: Serena simplification (6K → 50 tokens)
- **Handover 0246a-c**: Orchestrator workflow & token optimization
- **Handover 0088**: Thin client architecture (fetch-first pattern)
- **Flow Documentation**: `handovers/Reference_docs/start_to_finish_agent_FLOW.md`
- **AgentTemplate Model**: `src/giljo_mcp/models/templates.py` lines 27-122
- **Current get_agent_mission()**: `src/giljo_mcp/tools/orchestration.py` lines 306-389

---

**END OF HANDOVER 0278**

**Status**: 📋 Ready for review and implementation
**Estimated Implementation Time**: 6-8 hours (with testing)
**Token Impact**: ~97% reduction in multi-terminal pastes, ~82% reduction in templates
