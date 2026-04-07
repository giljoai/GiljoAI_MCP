# 0950h: God-Class Split — MessageService

**Series:** 0950 (Pre-Release Quality Sprint — God-Class Splitting Track)
**Phase:** 8 of 14
**Branch:** `feature/0950-pre-release-quality`
**Edition Scope:** CE
**Priority:** High
**Effort:** Heavy (4-6 hrs)
**Depends on:** 0950g (sequential to avoid entangled imports during the god-class splitting track)
**Status:** Not Started

### Reference Documents
- **Chain log:** `prompts/0950_chain/chain_log.json`
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

---

## Context

`src/giljo_mcp/services/message_service.py` is 1730 lines. It conflates two responsibilities: message CRUD / counter / acknowledgment management (core service work) and message routing / recipient resolution / broadcast fanout (coordination concerns). The oversized `list_messages` method is a query-building anti-pattern that mixes filter assembly with the public API.

This split separates routing into `message_routing_service.py` and makes `MessageService` responsible only for direct record operations. Both services filter every DB query by `tenant_key` — this is a security invariant that must be verified after every extraction.

---

## Pre-Work: Mandatory Caller Discovery

Before moving a single line of code:

```bash
grep -rn "MessageService\|message_service" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

grep -rn "list_messages\|route_message\|resolve_recipients\|broadcast_fanout\|fanout" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"
```

Key files expected (verify, do not assume):
- `api/endpoints/messages.py` — primary HTTP caller
- `src/giljo_mcp/tools/` — MCP tool callers
- `src/giljo_mcp/services/orchestration_service.py` — likely calls routing methods
- Test files under `tests/`

Record every reference. Every import and every call site must be updated as part of this handover.

---

## Scope

**Primary file:** `src/giljo_mcp/services/message_service.py` (1730 lines)

**New file to create:**
- `src/giljo_mcp/services/message_routing_service.py` — routing, recipient resolution, broadcast fanout

**Files to update (at minimum):**
- `api/endpoints/messages.py`
- Any tool file that imports `MessageService` and calls routing methods
- `src/giljo_mcp/services/orchestration_service.py` (if it calls routing methods)
- `src/giljo_mcp/services/__init__.py` (if it re-exports services)
- All test files that directly import or mock `MessageService` routing methods

---

## Implementation Plan

### Phase 1: Map the file

Read `src/giljo_mcp/services/message_service.py` in full. Classify every method:

**CRUD / counter / acknowledgment (stays in MessageService):**
- Create, read, update, delete message records
- Unread counter management
- Acknowledgment recording
- Message status tracking
- Any method that operates on a single message record

**Routing / recipient / broadcast (moves to MessageRoutingService):**
- Recipient resolution (determining which agents or users receive a message)
- Broadcast fanout (sending one message to multiple recipients)
- Route arbitration (deciding message routing path based on context)
- Any method whose primary job is "to whom does this message go"

**list_messages (requires surgery):**
- Identify the filter-assembly logic inside `list_messages`
- Extract a private `_build_list_query` helper that assembles the SQLAlchemy query from filters
- The public `list_messages` method calls `_build_list_query` and executes it — under 30 lines after extraction
- Both the helper and the public method stay in `MessageService` (query building is not routing)

Record the classification before writing code. If a method is ambiguous, keep it in `MessageService` — only move what is clearly routing logic.

### Phase 2: Create MessageRoutingService

Create `src/giljo_mcp/services/message_routing_service.py`.

Rules:
- `MessageRoutingService` may call `MessageService` methods (to fetch/create records) — it depends on `MessageService`, not the reverse
- `MessageService` must NOT import from `message_routing_service.py` — this would create a circular dependency
- All DB queries in `MessageRoutingService` must filter by `tenant_key`
- No method may exceed 200 lines
- No class may exceed 1000 lines

Constructor pattern: accept `db_session` and any injected dependencies via constructor (match the pattern used by existing services in `src/giljo_mcp/services/`).

### Phase 3: Refactor list_messages

Inside `MessageService`:
1. Create `_build_list_query(self, filters: ...) -> Select` — assembles the SQLAlchemy `select()` with all filter predicates
2. Rewrite `list_messages` to call `_build_list_query`, execute, and return results
3. Target: `list_messages` public method under 40 lines; `_build_list_query` under 100 lines

Verify the `tenant_key` filter is present in `_build_list_query` — it must be the first predicate applied, not an optional one.

### Phase 4: Reduce MessageService

After extraction and `list_messages` surgery:
- Target: `message_service.py` under 900 lines
- No method over 200 lines
- Verify no routing logic remains (grep for routing-specific method names to confirm they moved)

### Phase 5: Update all imports

For every file discovered in Pre-Work:
- Callers of routing methods must now import `MessageRoutingService` from `giljo_mcp.services.message_routing_service`
- Callers of CRUD/counter/acknowledgment methods continue to import `MessageService` from `giljo_mcp.services.message_service` — no change required for these
- Update dependency injection wiring if `MessageService` is injected via FastAPI `Depends()` in endpoints — routing callers may need a second `Depends()` for `MessageRoutingService`

After updating:
```bash
grep -rn "from giljo_mcp.services.message_service import\|from src.giljo_mcp.services.message_service import" \
  /media/patrik/Work/GiljoAI_MCP/ --include="*.py"
```
Every remaining hit must import only symbols that still exist in `message_service.py`.

### Phase 6: Tenant isolation verification

This is security-critical. After all extractions:

```bash
grep -n "select\|SELECT\|query\|session\." \
  /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/services/message_routing_service.py
```

For every DB query found, manually verify it has a `.where(...tenant_key == ...)` predicate. If any query is missing the filter, add it before proceeding. This is not optional.

Run the same check on the modified `message_service.py` to confirm no existing filter was accidentally dropped.

### Phase 7: Verification

Run after every extraction phase:

```bash
# Startup check
python -c "from api.app import create_app; print('OK')"

# Unit tests
python -m pytest tests/unit/ -q --timeout=60 --no-cov

# Lint
ruff check src/ api/
```

All three must pass before proceeding. If a test fails, fix or delete it — never skip.

---

## Constraints

- No commented-out code. Delete removed code.
- No dict-return patterns. All error paths raise exceptions.
- No function may exceed 200 lines.
- No class may exceed 1000 lines.
- `MessageService` public interface must not change. Callers of CRUD methods need zero modification.
- `MessageRoutingService` is a new public interface — design it cleanly, it will be called directly by orchestration and endpoint code.
- Every DB query in both files must filter by `tenant_key`.
- No `ruff` violations in the final state.

---

## Cascading Impact Check

`MessageService` sits below `OrchestrationService` in the call chain. Verify that after this split, `OrchestrationService` still gets all the message operations it needs — either from `MessageService` directly (CRUD) or `MessageRoutingService` (routing). Do not remove any method that `OrchestrationService` calls.

Entity hierarchy reminder:
```
Product → Project → Job → Agent → Message
```
Messages belong to a Job context. Every query must be tenant-scoped. The `tenant_key` on a `Message` must always be verified against the authenticated user's `tenant_key` in the service layer — not just in the endpoint layer.

---

## Acceptance Criteria

- [ ] `src/giljo_mcp/services/message_service.py` is under 900 lines
- [ ] No method in `message_service.py` or `message_routing_service.py` exceeds 200 lines
- [ ] `list_messages` delegates to `_build_list_query`; public method is under 40 lines
- [ ] Every DB query in `message_routing_service.py` filters by `tenant_key`
- [ ] No routing logic remains in `message_service.py`
- [ ] All callers updated and imports verified
- [ ] `python -c "from api.app import create_app; print('OK')"` passes
- [ ] `python -m pytest tests/unit/ -q --timeout=60 --no-cov` passes with zero new failures
- [ ] `ruff check src/ api/` reports zero issues
- [ ] No commented-out code in any modified file

---

## Rollback

```bash
git checkout -- src/giljo_mcp/services/message_service.py
rm -f src/giljo_mcp/services/message_routing_service.py
```

---

## Commit Message Format

```
cleanup(0950h): split MessageService — extract MessageRoutingService

- Extract routing/recipient/broadcast methods into MessageRoutingService
- Refactor list_messages: delegate filter assembly to _build_list_query
- MessageService retains CRUD, counters, acknowledgment logic
- message_service.py reduced from 1730 lines to <900
- tenant_key filtering verified in all extracted queries
```

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0950_chain/chain_log.json`.
- Check `orchestrator_directives` on session `0950h` — if STOP, halt immediately.
- Read `notes_for_next` from session `0950g` — it may describe shared utilities discovered during the `ThinClientPromptGenerator` split that affect import paths here.

### Step 2: Mark Session Started
Update session `0950h` in chain_log.json: `"status": "in_progress"`.

### Step 3: Execute
Follow Phases 1-7 above in order. Run verification after each extraction phase.

### Step 4: Update Chain Log
Before stopping, update session `0950h` with:
- `tasks_completed`: each extraction and surgery step completed
- `deviations`: any deviation from this plan and why
- `blockers_encountered`: anything requiring escalation
- `notes_for_next`: critical context for 0950i (ProductService + ProjectService), especially if `MessageService` is called by `ProductService` or `ProjectService` and the routing split affects those call paths
- `cascading_impacts`: import path changes that 0950i-0950j agents must be aware of
- `summary`: one-paragraph summary
- `status`: `"complete"`

### Step 5: STOP
Do NOT spawn the next terminal. The orchestrator handles that.

---

## Progress Updates

**Status: COMPLETE**

- MessageService: 1790 → 874 lines (CRUD/read/ack/complete)
- MessageRoutingService: 863 lines (send/broadcast/routing)
- 11 methods extracted, list_messages refactored with _build_list_query
- All callers updated (messages.py, tool_accessor.py, dependencies.py)
- 5 unit tests updated to use MessageRoutingService
- Tenant isolation verified: 28 queries pass
- Zero new test failures, ruff clean, startup OK
