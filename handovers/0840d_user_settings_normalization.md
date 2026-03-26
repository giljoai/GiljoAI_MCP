# Handover 0840d: User Settings Normalization

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Planning Session)
**To Agent:** Next Session (database-expert + tdd-implementor)
**Priority:** High
**Estimated Complexity:** 6-8 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Normalize user settings by: (1) creating a `user_field_priorities` relational table to replace `User.field_priority_config` JSONB, (2) extracting `User.depth_config` JSONB into proper columns on the `users` table, and (3) locking "Product Info" as always-on (not toggleable). This removes the last user-facing JSONB fields that store fixed-schema data.

**Prerequisite:** Handover 0840c (Product Config Normalization) must be complete. Check chain log.

## Context and Background

`User.field_priority_config` stores 9 boolean toggles in a JSONB dict with a version envelope. `User.depth_config` stores 7 fixed keys controlling context depth. Both have stable schemas that never change — they are fixed structures masquerading as flexible JSONB.

The user confirmed: category toggles operate at the group level (e.g., "Tech Stack" toggles ALL tech stack fields on/off). "Product Info" (formerly "Basic Info") is ALWAYS ON and should appear locked in the UI.

**IMPORTANT:** Check the chain log for notes from 0840c. The Product Info rename and "always on" locking should already be done in 0840c's frontend work. If not, handle it here.

## Technical Details

### New Schema

```sql
-- User Field Priorities table (replaces field_priority_config JSONB)
CREATE TABLE user_field_priorities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_key VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, category)
);
CREATE INDEX idx_user_field_priorities_user ON user_field_priorities(user_id, tenant_key);

-- Categories: tech_stack, architecture, testing, vision_documents,
--             memory_360, git_history, agent_templates
-- NOTE: No row for product_info — it is always on and not toggleable

-- Depth config → proper columns on users table
ALTER TABLE users ADD COLUMN depth_vision_documents VARCHAR(20) DEFAULT 'medium';
ALTER TABLE users ADD COLUMN depth_memory_last_n INTEGER DEFAULT 3;
ALTER TABLE users ADD COLUMN depth_git_commits INTEGER DEFAULT 25;
ALTER TABLE users ADD COLUMN depth_agent_templates VARCHAR(20) DEFAULT 'type_only';
ALTER TABLE users ADD COLUMN depth_tech_stack_sections VARCHAR(20) DEFAULT 'all';
ALTER TABLE users ADD COLUMN depth_architecture VARCHAR(20) DEFAULT 'overview';
ALTER TABLE users ADD COLUMN execution_mode VARCHAR(20) DEFAULT 'claude_code';
```

### Current field_priority_config Structure (Being Replaced)
```json
{
  "version": "3.0",
  "priorities": {
    "product_core": {"toggle": true},
    "project_description": {"toggle": true},
    "memory_360": {"toggle": true},
    "tech_stack": {"toggle": true},
    "testing": {"toggle": true},
    "vision_documents": {"toggle": true},
    "architecture": {"toggle": true},
    "agent_templates": {"toggle": true},
    "git_history": {"toggle": false}
  }
}
```

### Category Mapping (Old → New)

| Old Key | New Category | Toggleable? |
|---------|-------------|-------------|
| `product_core` | (removed) | NO — always on, no row in table |
| `project_description` | (removed) | NO — always on, no row in table |
| `tech_stack` | `tech_stack` | YES |
| `architecture` | `architecture` | YES |
| `testing` | `testing` | YES |
| `vision_documents` | `vision_documents` | YES |
| `memory_360` | `memory_360` | YES |
| `git_history` | `git_history` | YES |
| `agent_templates` | `agent_templates` | YES |

### Current depth_config Structure (Being Replaced)
```json
{
  "vision_documents": "medium",
  "memory_last_n_projects": 3,
  "git_commits": 25,
  "agent_templates": "type_only",
  "tech_stack_sections": "all",
  "architecture_depth": "overview",
  "execution_mode": "claude_code"
}
```

### Files That Must Change

**Models:**
- `src/giljo_mcp/models/auth.py` — Remove `field_priority_config` and `depth_config` JSONB columns. Add 7 depth columns. Create `UserFieldPriority` model.

**Services:**
- `src/giljo_mcp/services/user_service.py` — Rewrite `get_field_priority_config`, `update_field_priority_config`, `get_depth_config`, `update_depth_config`, `get_execution_mode`. Query `user_field_priorities` table instead of JSONB.
- `src/giljo_mcp/services/protocol_builder.py` — Reads `depth_config` and `field_priority_config`. Update to use new columns/table.
- `src/giljo_mcp/services/product_tuning_service.py` — Reads `depth_config` as fallback. Update.
- `src/giljo_mcp/thin_prompt_generator.py` — Reads `field_priority_config.get("priorities", {})`. Update.
- `src/giljo_mcp/services/project_service.py` — Reads `field_priority_config`. Update.

**Tools:**
- `src/giljo_mcp/tools/tool_accessor.py` — Passes `depth_config`. Update.

**Frontend:**
- `frontend/src/components/settings/ContextPriorityConfig.vue` — Major rewrite: read from/write to new API shape. Lock "Product Info" toggle with "Always On" badge. Remove `product_core` and `project_description` toggles (or show them locked).
- API endpoint for field priorities must accept/return the new table-based structure

**Config:**
- `src/giljo_mcp/config/defaults.py` — Update DEFAULT_FIELD_PRIORITY_CONFIG and DEFAULT_DEPTH_CONFIG

### Migration Data Backfill

```sql
-- Backfill user_field_priorities from field_priority_config JSONB
INSERT INTO user_field_priorities (user_id, tenant_key, category, enabled)
SELECT u.id, u.tenant_key, cat.category,
  COALESCE((u.field_priority_config->'priorities'->cat.category->>'toggle')::boolean, TRUE)
FROM users u
CROSS JOIN (VALUES ('tech_stack'), ('architecture'), ('testing'),
  ('vision_documents'), ('memory_360'), ('git_history'), ('agent_templates')) AS cat(category)
WHERE u.field_priority_config IS NOT NULL;

-- Backfill depth columns
UPDATE users SET
  depth_vision_documents = COALESCE(depth_config->>'vision_documents', 'medium'),
  depth_memory_last_n = COALESCE((depth_config->>'memory_last_n_projects')::integer, 3),
  depth_git_commits = COALESCE((depth_config->>'git_commits')::integer, 25),
  depth_agent_templates = COALESCE(depth_config->>'agent_templates', 'type_only'),
  depth_tech_stack_sections = COALESCE(depth_config->>'tech_stack_sections', 'all'),
  depth_architecture = COALESCE(depth_config->>'architecture_depth', 'overview'),
  execution_mode = COALESCE(depth_config->>'execution_mode', 'claude_code')
WHERE depth_config IS NOT NULL;
```

## Implementation Plan

### Phase 1: Database Migration
1. Create Alembic migration with idempotency guards
2. Create `user_field_priorities` table
3. Add 7 depth columns to users
4. Backfill data
5. Drop `field_priority_config` and `depth_config` JSONB columns

### Phase 2: Model Updates
1. Create UserFieldPriority model
2. Update User model (add depth columns, relationships, remove JSONB columns)
3. Update defaults.py

### Phase 3: Service Layer Rewrite
1. user_service.py — Query/update user_field_priorities table, read/write depth columns
2. protocol_builder.py — Read depth columns directly
3. thin_prompt_generator.py — Query user_field_priorities table
4. project_service.py — Query user_field_priorities table
5. product_tuning_service.py — Read depth columns

### Phase 4: Frontend Updates
1. ContextPriorityConfig.vue — New API shape, locked Product Info toggle
2. API endpoints for field priorities and depth config

### Phase 5: Test Rewrite
**Files requiring REWRITE:**
- `tests/services/test_user_service_auth_config.py` (~13 tests)
- `tests/services/test_depth_config_standardization.py` (9 tests)
- `tests/services/test_user_field_priorities.py` (6 tests)

**Files requiring UPDATE:**
- `tests/services/test_protocol_builder_ch2_fetch.py` (20 tests)
- `tests/services/test_thin_client_prompt_generator_*.py` (6 tests)
- `tests/services/test_orchestration_service_*.py` (15 tests)

### Phase 6: Verify
1. Lint clean, all tests pass
2. Frontend settings page works: toggle categories, change depths
3. Product Info appears locked

## Success Criteria

- [ ] `user_field_priorities` table created
- [ ] 7 depth columns on users table
- [ ] Old JSONB columns dropped
- [ ] "Product Info" locked as always-on in UI
- [ ] `product_core` and `project_description` no longer toggleable
- [ ] All tests pass
- [ ] `ruff check` clean
- [ ] Committed to `feature/0840-jsonb-normalization`

## Rollback Plan

`alembic downgrade -1`. Git revert.

## Coding Principles (from HANDOVER_INSTRUCTIONS.md)

- TDD, Clean Code, Tenant isolation, Exception-based errors, Search before build
- Trace full chain: model → service → tool → endpoint → frontend → test

## STOP CONDITIONS

- Frontend ContextPriorityConfig.vue has undocumented dependencies on the JSONB structure
- Protocol builder relies on JSONB shape in non-obvious ways

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Verify 0840c is `complete`. Read `notes_for_next`.

### Step 2: Mark Session Started

### Step 3: Execute Handover Tasks

### Step 4: Update Chain Log

### Step 5: Commit Work
```bash
git add -A
git commit -m "feat: Normalize user settings — field priorities table + depth columns (0840d)"
```

### Step 6: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0840e - Project Meta + Minor Cleanups\" --tabColor \"#FF5722\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0840e. READ FIRST: F:\GiljoAI_MCP\handovers\0840e_project_meta_minor_cleanups.md then READ: F:\GiljoAI_MCP\prompts\0840_chain\0840e_prompt.md for chain instructions. You are on branch feature/0840-jsonb-normalization. Use database-expert and tdd-implementor subagents.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
