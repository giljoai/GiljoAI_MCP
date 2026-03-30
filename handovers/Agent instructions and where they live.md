Agent instructions and where they live

This document summarizes where agent instructions live after 0349/0353 and how we plan to **slim** templates while keeping behavior centralized on the server.

> **Note:** Session memory for 0353 implementation is documented in `completed/0363_session_agent_instruction_slimming-C.md` (renumbered from 0353 to avoid conflict with `0353_agent_team_awareness_and_mission_context.md`).

---

1. Instruction Layers (Post-0349)

We now have three clearly separated layers:

- **Template layer** (Claude `.md`, `GenericAgentTemplate`, seeder MCP section):
  - Teaches how to talk to the MCP server.
  - Injects identity: `agent_id`, `job_id` / `agent_job_id`, `product_id`, `project_id`, `tenant_key`.
  - Emphasizes that MCP tools are native: `mcp__giljo_mcp__*` (no HTTP/curl/SDK).
  - Points agents to `get_agent_mission` and `full_protocol`.
  - Avoids re-encoding the full lifecycle.
  - **Orchestrator vs Agent differences** (Handover 0432):
    - Orchestrator: MCP + Check-in + Orchestrator Messaging + Closeout framing
    - Regular agents: Agent Guidelines + MCP + Context Request + Check-in + Agent Messaging
    - Orchestrator excludes "REQUESTING BROADER CONTEXT" (doesn't ask itself for context)

- **Protocol layer**:
  - `_generate_agent_protocol()` + `get_agent_mission()` in `src/giljo_mcp/services/orchestration_service.py`.
  - Returns `full_protocol` with the 5-phase lifecycle:
    - Startup (including TodoWrite/planning).
    - Execution.
    - Progress reporting.
    - Communication/message handling.
    - Completion and error handling.
  - This is the **single behavioral authority**.

- **Mission layer**:
  - `mission` + context returned by `get_agent_mission(agent_job_id, tenant_key)`.
  - Contains per-job assignment, project/product context, and (after 0353) team/dependency info.

---

2. Current Wiring Changes (Already Implemented)

2.1 Generic multi-terminal agent template

- File: `src/giljo_mcp/templates/generic_agent_template.py`
- Now:
  - Injects identity: `agent_id`, `job_id`, `product_id`, `project_id`, `tenant_key`.
  - Has a concise **MCP wiring** section:
    - MCP tools are native.
    - Key tools: `mcp__giljo_mcp__get_agent_mission`, `mcp__giljo_mcp__report_progress`, `mcp__giljo_mcp__complete_job`, `mcp__giljo_mcp__report_error`.
  - Delegates behavior:
    - First action: call `mcp__giljo_mcp__get_agent_mission(agent_job_id="{job_id}", tenant_key="{tenant_key}")`.
    - Then read `mission` + `full_protocol` and follow `full_protocol` for all lifecycle behavior.

2.2 Thin client spawn prompts

- HTTP MCP spawn tool: `OrchestrationService.spawn_agent_job` in `src/giljo_mcp/services/orchestration_service.py`.
- MCP tool variant: `_spawn_agent_job_impl` in `src/giljo_mcp/tools/orchestration.py`.
- Both now:
  - Keep the identity line ("I am {agent_name}…").
  - Include a short "MCP tools are native" block.
  - Replace long "MANDATORY STARTUP SEQUENCE" with:
    - Step 1: call `mcp__giljo_mcp__get_agent_mission(agent_job_id, tenant_key)`.
    - Step 2: follow `full_protocol` from that response.

2.3 Template Injection for Multi-Terminal Mode (Handover 0417)

When `spawn_agent_job()` is called, the backend checks `Project.execution_mode`:

- **`multi_terminal` mode** (Claude Code Web, Gemini CLI, Codex CLI, etc.):
  - Backend looks up `AgentTemplate` by `agent_name`
  - Injects template content into `AgentJob.mission` with **tidy framing**:
    ```
    ╔═════════════════════════════════════════════════════════════════════════╗
    ║                     AGENT EXPERTISE & PROTOCOL                           ║
    ╚═════════════════════════════════════════════════════════════════════════╝

    [template.system_instructions + template.user_instructions]

    ╔═════════════════════════════════════════════════════════════════════════╗
    ║                       YOUR ASSIGNED WORK                                 ║
    ╚═════════════════════════════════════════════════════════════════════════╝

    [orchestrator's mission assignment]
    ```
  - Agent calls `get_agent_mission()` → receives full injected content
  - **Token savings**: Orchestrator passes only work (~50 tokens) instead of full role (~500 tokens)

- **`claude_code_cli` mode**:
  - **NO injection** - Task tool loads `.claude/agents/{agent_name}.md` automatically
  - `AgentJob.mission` contains only the orchestrator's work assignment
  - Template expertise comes from the file system, not the database

**Key Files**:
- Injection logic: `src/giljo_mcp/services/orchestration_service.py` (lines 636-684)
- Framing pattern matches: `_build_orchestrator_protocol()` in `src/giljo_mcp/tools/orchestration.py`

2.4 Claude Code Task instructions

- File: `src/giljo_mcp/thin_prompt_generator.py`, `_build_claude_code_execution_prompt`.
- Task instructions now:
  - Tell subagents to call `mcp__giljo_mcp__get_agent_mission(agent_job_id, tenant_key)` as a tool.
  - Explicitly mention that this returns `mission` + `full_protocol`.
  - Tell subagents to follow `full_protocol` for lifecycle behavior.

2.5 Seeder / exported MCP section

- File: `src/giljo_mcp/template_seeder.py`, `_get_mcp_coordination_section()`.
- Keeps CRITICAL "MCP tools are native" section.
- Replaces detailed lifecycle steps with:
  - Tool summary.
  - Bootstrap sequence pointing to `get_agent_mission` + `full_protocol`.
  - Generic tool-call format and self-navigation notes.
- **Orchestrator template** (Handover 0432):
  - Excludes "REQUESTING BROADER CONTEXT" section
  - Includes "Before Closeout" verification steps
  - Includes "If Requirements Are Unclear" with BLOCKED protocol
- **Regular agent templates** (Handover 0432):
  - Include "Agent Guidelines" section with BLOCKED protocol
  - Include "REQUESTING BROADER CONTEXT" (to ask orchestrator)
  - Include "If Blocked or Unclear" with correct `report_error()` syntax

2.6 Status Values and BLOCKED Protocol (Handover 0432)

**AgentExecution status values** (from `models/agent_identity.py`):
- `waiting` → `working` → `complete` / `blocked` / `failed` / `cancelled` / `decommissioned`

**Status transitions**:
```
waiting ─[acknowledge_job()]─→ working
working ─[report_progress()]─→ working (updates progress/todos, no status change)
working ─[complete_job()]─→ complete
working ─[report_error()]─→ blocked
blocked ─[acknowledge_job()]─→ working (resume from blocked)
```

**BLOCKED protocol**:
1. Call `report_error(job_id, "BLOCKED: <reason>")` to mark blocked
2. Send message explaining what you need
3. Wait for response via `receive_messages()`
4. Call `acknowledge_job()` to resume (sets status back to working)

**Note**: All `report_error()` calls set status to "blocked" (not "failed"). Use "BLOCKED:" prefix in message for clarity.

---

3. Slimming Strategy (0353) - Implementation Status

**Slimming strategy** for seeded/exported agent templates:

- Seeded templates (`template_seeder.py` → DB → Agent Template Manager → export → `.claude/agents/*.md`) will:
  - Keep:
    - Front matter (name, description, model).
    - CRITICAL MCP wiring + "tools are native" block.
    - Role-specific guidance (implementer vs tester vs analyzer etc.).
    - A short startup note:
      - "Call `mcp__giljo_mcp__get_agent_mission(agent_job_id, tenant_key)`."
      - "Follow `full_protocol` for lifecycle behavior."
      - "Team information (if any) is provided in your mission text."
  - Remove:
    - Full Phase 1–6 lifecycle sections.
    - CHECK-IN PROTOCOL pseudo-code.
    - Inter-agent messaging pseudo-code.
    - Placeholder-heavy examples (`<AGENT_TYPE>`, `<TENANT_KEY>`, etc.).

**Implementation status** (Handover 0432):
- ✅ Agent Guidelines section implemented (regular agents)
- ✅ BLOCKED protocol documented with correct `report_error()` / `acknowledge_job()` syntax
- ✅ Orchestrator/agent template separation (different system_instructions)
- ✅ Closeout framing added to orchestrator
- ⏳ Team/dependency sections in mission text - pending
- ⏳ Detailed closeout verification protocol in `full_protocol` - pending

- Mission text (set via `spawn_agent_job`) will be enhanced (0353) to include:
  - **YOUR IDENTITY** – role + job_id.
  - **YOUR TEAM** – compact table of other agents, their roles, and deliverables.
  - **YOUR DEPENDENCIES** – upstream/downstream relationships.
  - **COORDINATION** – who to message and when (using existing MCP tools).

- `full_protocol` will:
  - Remain the authoritative behavioral spec.
  - Clarify ID usage (`job_id`/`agent_job_id` vs `agent_name`).
  - Explicitly tell agents to:
    - Read team/dependency sections in `mission`.
    - Use `send_message`/`receive_messages` for coordination, not `list_messages`.

---

4. Branching Plan for Implementation

- A dedicated branch will be created (e.g., `0353_agent_instruction_slimming`) from `master` with this document and the 0349/0353 handovers as context.
- That branch will:
  - Implement the seeder/DB/export template slimming.
  - Implement mission team-awareness changes in `spawn_agent_job`.
- `master` will remain the working branch for other fixes/features; 0353 work will be merged once fully implemented and tested.
