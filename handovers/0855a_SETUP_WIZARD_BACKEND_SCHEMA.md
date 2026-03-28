# Handover 0855a: Setup Wizard — Backend Schema + API Endpoints

**Date:** 2026-03-28
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** database-expert + tdd-implementor
**Priority:** High
**Estimated Complexity:** 3 hours
**Status:** Not Started
**Series:** 0855a-g (Setup Wizard Redesign)
**Spec:** `handovers/SETUP_WIZARD_REDESIGN.md`

---

## Read First (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — coding standards, TDD protocol, quality gates
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — project bootstrap
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow context
4. `handovers/SETUP_WIZARD_REDESIGN.md` — full spec for the wizard redesign

**Search before you build.** Use Serena `find_symbol` / `get_symbols_overview` to check if functionality already exists. Extend existing services — don't create new modules unless justified.

---

## Task Summary

Add 3 new columns to the `users` table for server-persisted wizard state, create API endpoints to read/write setup progress, and add an active API key lookup endpoint. This is the foundation — all frontend handovers (0855c-g) depend on these fields.

---

## Context and Background

Setup state is currently tracked entirely in `localStorage` (`giljo_startup_checklist_v1`), meaning it's lost on browser clear, can't survive device switches, and can't be queried server-side. The redesign moves all state to the User model with a PATCH endpoint the overlay will call on each step transition.

The existing `create_api_key` endpoint already checks for active keys (5-key limit). The wizard needs a read-only endpoint to check if a key already exists before offering to generate one.

---

## Technical Details

### Database Changes

**Users table — 3 new columns:**

```sql
ALTER TABLE users ADD COLUMN setup_complete BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN setup_selected_tools JSONB;
ALTER TABLE users ADD COLUMN setup_step_completed INTEGER NOT NULL DEFAULT 0;
```

- `setup_complete` — Boolean flag. `true` after user finishes or dismisses the wizard permanently.
- `setup_selected_tools` — JSONB array of tool identifiers, e.g. `["claude_code", "codex_cli"]`. Nullable (null = hasn't reached Step 1 yet).
- `setup_step_completed` — Highest completed step (0-4). 0 = not started, 4 = all steps done.

### Existing Code Reference

**User model** (`src/giljo_mcp/models/auth.py`, ~370 lines): The `User` class has existing setup-adjacent fields at ~line 60: `must_change_password = Column(Boolean, default=False)` and `must_set_pin = Column(Boolean, default=False)`. Add the new columns after these.

**Auth endpoints** (`api/endpoints/auth.py`, ~793 lines): Existing patterns use `Depends(get_current_active_user)` for auth and `Depends(get_db)` for sessions. The existing `create_api_key` endpoint is at ~line 538. The API key service (`src/giljo_mcp/services/auth_service.py`, ~896 lines) already checks for existing active keys at line 376-389 (5-key limit via `SELECT COUNT(*)`).

**Exception-based error handling:** Post-0480, all layers raise exceptions — never `return {"success": False, ...}`. Use `raise HTTPException(...)` or service-layer exceptions.

### Model Changes

**File:** `src/giljo_mcp/models/auth.py` — `User` class

Add columns after `must_set_pin`:

```python
setup_complete = Column(Boolean, default=False, nullable=False, server_default="false")
setup_selected_tools = Column(JSONB, nullable=True)
setup_step_completed = Column(Integer, default=0, nullable=False, server_default="0")
```

### API Changes

**File:** `api/endpoints/auth.py`

1. **Ensure `GET /api/v1/auth/me` returns new fields.** Check the response schema (Pydantic model) includes `setup_complete`, `setup_selected_tools`, `setup_step_completed`. If using a `UserResponse` schema, add the fields there.

2. **New endpoint: `PATCH /api/v1/auth/me/setup-state`**

```python
class SetupStateUpdate(BaseModel):
    setup_selected_tools: Optional[List[str]] = None
    setup_step_completed: Optional[int] = Field(None, ge=0, le=4)
    setup_complete: Optional[bool] = None

@router.patch("/me/setup-state")
async def update_setup_state(
    payload: SetupStateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Update only provided fields on current_user
    # Commit and return updated user
```

3. **New endpoint: `GET /api/v1/auth/api-keys/active`**

Returns metadata (prefix, created_at, is_active) for the user's active API keys. Does NOT return the plaintext key. The wizard uses this to determine whether to show "Generate Configuration" vs "Show Configuration."

```python
@router.get("/api-keys/active")
async def get_active_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Query active keys for current_user.id
    # Return list of {id, key_prefix, created_at, is_active, expires_at}
```

### Alembic Migration

**File:** `migrations/versions/xxxx_0855a_user_setup_state.py`

Must include idempotency guards per CLAUDE.md:

```python
def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("users")]

    if "setup_complete" not in columns:
        op.add_column("users", sa.Column("setup_complete", sa.Boolean(), nullable=False, server_default="false"))
    if "setup_selected_tools" not in columns:
        op.add_column("users", sa.Column("setup_selected_tools", JSONB(), nullable=True))
    if "setup_step_completed" not in columns:
        op.add_column("users", sa.Column("setup_step_completed", sa.Integer(), nullable=False, server_default="0"))
```

### Cascading Analysis

- **Downstream:** No impact. These are leaf fields on the User model with no foreign keys.
- **Upstream:** No impact. Organization model unchanged.
- **Sibling:** No impact. These fields don't interact with `must_change_password` or `must_set_pin`.
- **Installation:** Fresh installs via `install.py` will pick up the new columns from the migration. No `install.py` changes needed — migration is self-contained with idempotency guards.

---

## Implementation Plan

### Phase 1: Model + Migration (TDD)
1. Write test: verify `setup_complete`, `setup_selected_tools`, `setup_step_completed` exist on User model with correct defaults
2. Add columns to `User` class in `auth.py`
3. Create Alembic migration with idempotency guards
4. Run migration, verify test passes

### Phase 2: PATCH Endpoint (TDD)
1. Write test: PATCH `/me/setup-state` updates fields, validates range (0-4), returns updated user
2. Write test: partial updates work (only send `setup_step_completed`, others unchanged)
3. Implement endpoint
4. Verify tests pass

### Phase 3: Active Keys Endpoint (TDD)
1. Write test: GET `/api-keys/active` returns active keys for current user only (tenant isolation)
2. Write test: returns empty list when no active keys
3. Implement endpoint
4. Verify tests pass

### Phase 4: Response Schema
1. Verify GET `/me` includes new fields in response
2. Update Pydantic response schema if needed

**Recommended Sub-Agents:** database-expert (migration), tdd-implementor (endpoint tests)

---

## Testing Requirements

**Unit Tests:**
- User model default values (setup_complete=false, setup_step_completed=0, setup_selected_tools=null)
- SetupStateUpdate Pydantic validation (step range 0-4, tool list format)

**Integration Tests:**
- PATCH `/me/setup-state` — full update, partial update, invalid step (5), unauthorized
- GET `/api-keys/active` — with keys, without keys, tenant isolation (can't see other tenant's keys)
- GET `/me` — includes new fields in response

---

## Dependencies and Blockers

**Dependencies:** None — this is the first handover in the series.
**Blockers:** None known.

---

## Success Criteria

- [ ] 3 new columns on `users` table with correct defaults
- [ ] Alembic migration runs idempotently (safe on fresh + existing DBs)
- [ ] PATCH `/me/setup-state` updates any combination of fields
- [ ] GET `/api-keys/active` returns key metadata without plaintext
- [ ] GET `/me` includes setup fields in response
- [ ] All new tests passing
- [ ] Tenant isolation verified on all new endpoints

---

## Rollback Plan

Drop the 3 columns via `downgrade()` in the Alembic migration. No data loss — these are new fields with no pre-existing data.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/models/auth.py` | Add 3 columns to User class |
| `migrations/versions/xxxx_0855a_user_setup_state.py` | New migration |
| `api/endpoints/auth.py` | Add PATCH + GET endpoints, update response schema |
| `tests/` | New test file for setup state endpoints |
