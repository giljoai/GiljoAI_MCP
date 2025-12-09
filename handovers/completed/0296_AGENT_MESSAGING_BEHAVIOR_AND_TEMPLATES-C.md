# Handover 0296: Agent Messaging Behavior & Template Updates

## Status: REFERENCE DOCUMENT (No implementation needed)
## Priority: HIGH
## Type: Template / Prompt Refactor + Tests
## Depends On: 0295_MESSAGING_CONTRACT_AND_CATEGORIES.md

---

## Note (2025-12-07)

This document serves as a **reference specification** for agent messaging behavior.
The messaging contract and template updates described here have been incorporated into:
- Current agent templates in `src/giljo_mcp/templates/`
- Thin prompt generator patterns
- MessageService implementation

No separate implementation action needed - this is design documentation.

---

---

## 1. Goal

Align all **agent templates and thin prompts** (orchestrator, implementers, testers, documenters, analyzers, etc.) with the **simplified messaging contract** defined in 0295:

- Use **only** the canonical message tools:
  - `send_message`, `receive_messages`, `acknowledge_message`, `list_messages`.
- Treat messaging strictly as:
  - Direct messages (agent ↔ agent, user ↔ orchestrator).
  - Broadcast messages (agent or orchestrator → all agents).
  - Audit trail for key decisions / coordination.
- Keep **signals** (job status) and **instructions** (missions) out of the messaging layer in prompts.

This handover is purely about **behavior and documentation in the templates** – no DB schema changes.

---

## 2. Current Issues

1. Some templates and docs still refer to older tools like:
   - `send_mcp_message`, `read_mcp_messages`, queue‑specific `acknowledge_message(job_id, tenant_key, ...)`.
2. Messaging behaviors are not consistently described:
   - Some agents are told to communicate primarily via Claude Code’s internal chat.
   - Others use MCP messaging intermittently, without clear rules.
3. Auditability requirement:  
   - We want significant coordination decisions recorded in the MCP messages system, even when agents are also chatting in the terminal.

---

## 3. Desired Messaging Behavior (All Agents)

### 3.1 Orchestrator

The orchestrator should:

- Use MCP messaging to:
  - Send instructions and coordination messages to implementers/testers/documenters.
  - Broadcast major state changes: e.g. staging complete, test phase complete, project ready for closeout.
  - Receive questions and status from agents (and summarize to the user if needed).
- Messaging tools (thin prompt syntax):
  - `mcp__giljo-mcp__send_message(...)`
  - `mcp__giljo-mcp__receive_messages(...)`
  - `mcp__giljo-mcp__acknowledge_message(...)`
  - `mcp__giljo-mcp__list_messages(...)` (for history / context reload).
- Always:
  - Acknowledge messages as soon as they are processed.
  - Use MCP messaging for any decision or coordination that the user might want to audit later.

### 3.2 Implementers, Testers, Documenters, Analyzers

Each specialist agent should:

- Report **status and blockers** primarily via job tools (`report_progress`, `complete_job`, `report_error`) and **optionally** via messages if a textual audit is useful.
- Use MCP messaging to:
  - Ask orchestrator for clarification.
  - Coordinate with the next agent in a pipeline (e.g. implementer → tester → documenter).
  - Send summary/handoff notes (e.g. “Implementation complete, tests needed on X”).
- Behaviors:
  - Read messages at reasonable intervals:
    - At startup (after fetching mission).
    - After completing major sub‑tasks.
  - Acknowledge each message once processed.

### 3.3 User via Web UI

The user’s “Message Center” should:

- Send:
  - Direct messages to orchestrator.
  - Broadcasts to all active agents for the project.
- These messages should be surfaced to agents exactly the same way as any other message – no special client‑side shortcuts.

---

## 4. Files to Update

### 4.1 Template Seeder & System Templates

**Primary file:**

- `src/giljo_mcp/template_seeder.py`

Look for:

- System templates for:
  - Orchestrator
  - Implementer
  - Tester
  - Analyzer
  - Reviewer
  - Documenter
- Any references to older messaging tools:
  - `send_mcp_message`, `read_mcp_messages`, legacy `acknowledge_message(job_id, tenant_key, ...)`.

Update these templates so that:

- They describe **only the supported tools** for messaging:
  - `send_message`, `receive_messages`, `acknowledge_message`, `list_messages`.
- They explain the difference between:
  - Messaging (audit/coordination).
  - Signals (job status tools).
  - Instructions (mission fetch).

### 4.2 Exported Claude Agent Templates

**Directory:**

- `claude_agent_templates/` (and any other exported agent template directories).

Ensure that:

- The “thin client” instructions for each agent mention:
  - How to call `mcp__giljo-mcp__send_message`, `receive_messages`, `acknowledge_message`.
  - That important coordination decisions should be mirrored via MCP messages even if they are also discussed in Claude Code chat.
- No outdated queue tools are present in these `.md` files.

### 4.3 Tool Catalog / Prompt Generation

**File:**

- `src/giljo_mcp/prompt_generation/mcp_tool_catalog.py`

Ensure messaging tools are documented there as:

- `communication.send_message`
- `communication.receive_messages`
- `communication.acknowledge_message`
- `communication.list_messages`

and that no deprecated tools are suggested as first‑class options to agents.

---

## 5. TDD Plan

**Key principle:** Tests first, then minimal implementation, then refactor – as per `handovers/Reference_docs/QUICK_LAUNCH.txt`.

### 5.1 Prompt Content Tests

**New test files:**

- `tests/templates/test_template_seeder_messaging_contract.py`
- `tests/templates/test_exported_claude_templates_messaging_contract.py` (if needed)

Suggested tests:

- `test_orchestrator_template_uses_only_supported_messaging_tools()`
  - Seed templates for a test tenant.
  - Extract orchestrator template text.
  - Assert it mentions `send_message`, `receive_messages`, `acknowledge_message`.
  - Assert it does **not** mention `send_mcp_message` or `read_mcp_messages`.
- `test_specialist_templates_define_clear_messaging_behavior()`
  - For implementer/tester/documenter:
    - Check presence of “acknowledge messages as you read them”.
    - Check explicit mention of messaging vs job status tools.

### 5.2 Tool Catalog Tests

**File:**

- `tests/prompt_generation/test_mcp_tool_catalog_messaging.py`

Tests:

- `test_mcp_tool_catalog_exposes_only_supported_messaging_tools()`
  - Assert that `tools/list` for communication includes only:
    - `send_message`, `receive_messages`, `acknowledge_message`, `list_messages`.
  - Assert that older queue tools, if present in code, are not exposed in the public catalog.

---

## 6. Constraints & Notes

- **Do NOT break `install.py`:**
  - Template seeding must still work on a fresh database.
  - No schema changes are expected in this handover.
- **Follow Quick Launch rules:**
  - Prefer service layer and existing abstractions; do not embed direct DB queries in prompts or new endpoints.
- **Assume agents run remotely over HTTP:**
  - All behavior should be described in terms of HTTP MCP tools, not local/stdio FastMCP.

---

## 7. Acceptance Criteria

1. All system templates and exported Claude templates:
   - Use only the canonical messaging tools.
   - Clearly describe agent messaging behavior (when to send, when to read, when to acknowledge).
2. No new or existing public template mentions:
   - `send_mcp_message`, `read_mcp_messages`, or queue‑style `acknowledge_message(job_id, tenant_key, ...)` as primary tools.
3. MCP tool catalog and any prompt‑generation helpers:
   - Expose only the canonical messaging tools for communication.
4. New tests described above are in place and passing.


