# Handover 0298: Legacy Messaging Queue & FastMCP Cleanup

## Status: READY FOR IMPLEMENTATION  
## Priority: MEDIUM  
## Type: Refactor / Tech Debt  
## Depends On: 0295 (contract), 0296 (templates), 0297 (UI)

---

## 1. Goal

Once 0295–0297 are complete and stable, consolidate the messaging implementation by:

- Removing or strictly isolating **legacy queue‑based messaging and FastMCP‑only tools** that are no longer used in the HTTP MCP + SaaS model.
- Ensuring that:
  - The **messages table + MessageService** is the only messaging **source of truth**.
  - JSONB mirrors on `MCPAgentJob.messages` are used only for counters/persistence, not as a separate queue.
  - No public docs or templates reference deprecated tools.

This reduces cognitive load and risk for future contributors and agentic coding tools.

---

## 2. Legacy Components to Review

### 2.1 Agent Messaging / Communication Tools

**Files:**

- `src/giljo_mcp/tools/agent_messaging.py`
- `src/giljo_mcp/tools/agent_communication.py`

These currently define:

- `send_mcp_message`, `read_mcp_messages`, queue‑style `acknowledge_message(job_id, tenant_key, message_id, agent_id, ...)`, `check_orchestrator_messages`, `report_status`, etc., wired via `FastMCP`.

In the HTTP MCP / remote‑agent world, these are:

- Either unused.
- Or should be considered **internal** signaling tools, not part of the public messaging contract.

### 2.2 AgentMessageQueue / Queue Abstractions

**Files:**

- `src/giljo_mcp/agent_message_queue.py`
- Any remaining `AgentCommunicationQueue` or older queue manager names.

These provide a richer, ACID‑style message queue built on:

- `Message` + `MCPAgentJob` models.

The current architecture already routes core messaging via `MessageService`; we want to ensure queue abstractions don’t introduce a **second** public messaging API.

---

## 3. Refactor Strategy

### 3.1 Inventory & Usage Analysis (tests first)

1. Use symbolic tools (Serena) to locate all **call sites** of:
   - `send_mcp_message`, `read_mcp_messages`, queue‑`acknowledge_message`, `check_orchestrator_messages`.
2. Write tests that **document current behavior** at the highest level still using those APIs (if any).  
   Examples:
   - `tests/integration/test_legacy_queue_messaging_flow.py`
3. Decide per call site:
   - Migrate to the standard messaging contract (preferred).
   - Or mark as clearly internal (no exposure to HTTP MCP / external agents).

### 3.2 Migrate or Remove Public Exposure

For each legacy tool:

1. **HTTP MCP & Tool Catalog:**
   - Ensure `/mcp` and `mcp_tool_catalog.py` no longer expose queue‑style messaging tools as public.
2. **Templates / Docs:**
   - Confirm 0296 has removed all references to legacy tools from orchestrator/agent templates.
3. **Code Paths:**
   - Where possible, replace queue‑based messaging calls with calls into `MessageService` + JSONB persistence.

### 3.3 Internalization or Deletion

After migration:

- If no code paths require these queue abstractions:
  - Remove the following:
    - FastMCP `@mcp.tool()` wrappers for messaging.
    - Unused methods in `AgentMessageQueue` that duplicate `MessageService`.
  - Keep only the minimal logic needed for:
    - Stats.
    - Dead‑letter / stuck‑message detection, if still valuable.
- If some internal logic still benefits from queue abstractions:
  - Move those files under an explicit `legacy` or `internal` namespace.
  - Add clear module‑level comments:
    - “For internal server‑side queue management only; **not** part of MCP public contract.”

---

## 4. TDD & Safety

Given that this is largely a deletion/refactor task, tests must be used to **lock in current behavior** before deleting anything.

### 4.1 Tests to Add/Extend

- `tests/integration/test_messaging_contract_regression.py`
  - Prove that messaging via:
    - HTTP MCP tools.
    - REST `/api/messages/...`
  - Works exactly as in 0295–0297 (direct, broadcast, ack, list).
- `tests/services/test_agent_message_queue_legacy_behavior.py` (temporary)
  - Capture any behavior we are relying on indirectly.

After migration, these tests should:

- Still pass using `MessageService` only.
- Be updated to remove references to legacy queue types once behavior is proven equivalent.

### 4.2 Install & Migration Safety

- No new DB schema changes are expected; if any are needed:
  - They must be accompanied by Alembic migrations.
  - `install.py` must be verified on a fresh database.

---

## 5. Constraints & Non‑Goals

- **Non‑goal:** Re‑architecture of WebSocket events (already addressed in 0294 & 0297).
- **Non‑goal:** Changes to user‑visible behavior beyond cleaning up unused features.
- **Constraint:** If any environments still depend on FastMCP stdio mode, ensure they are either:
  - Updated to use HTTP MCP and the unified messaging contract, or
  - Explicitly documented as unsupported/legacy.

---

## 6. Acceptance Criteria

1. The only public messaging APIs for agents and orchestrators are:
   - MessageService via HTTP MCP tools + REST endpoints.
2. No templates, docs, or tool catalogs instruct agents to use legacy queue tools.
3. Legacy queue code is either:
   - Deleted, or
   - Clearly marked as internal/legacy, with no external exposure.
4. All new and existing tests pass (`pytest`), and `install.py` continues to bootstrap and seed successfully.

