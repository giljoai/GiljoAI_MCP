# 0814 — Template Manager UI Redesign

**Status:** Complete
**Priority:** High
**Edition Scope:** CE
**Estimated Effort:** 8-12 hours
**Depends On:** 0813 (Agent Template Context Separation — COMPLETE)
**Branch:** `0813-template-context-separation` (continues in the same branch as 0813 — merge everything together after 0814 completes)
**Research Doc:** `handovers/agent_template.md`

---

## Partial Phase 1 Already Committed

A previous agent started Phase 1 backend work. These changes are already in the working tree (committed into the 0813 branch):
- **`crud.py`**: `create_template()` now injects canonical bootstrap via `_get_mcp_bootstrap_section()`, ignoring frontend `system_instructions`. Accepts `user_instructions`.
- **`models.py`**: `TemplateCreate` — `system_instructions` made optional (ignored on create), `user_instructions` field added with 50KB validator.
- **`template_service.py`**: `reset_system_instructions()` now uses `_get_mcp_bootstrap_section()` instead of stale hardcoded fallback.

The implementing agent should verify these changes are correct, then continue with Phase 2 (frontend) onwards.

---

## Problem Statement

After 0813 separated template content into three contexts (role identity, protocols, work order), the Template Manager UI was not updated to match. The frontend still edits the wrong field, producing a 403 on every save. Users have no way to edit the field that actually defines their agent's expertise (`user_instructions`). Four bugs must be fixed before templates are usable.

---

## Bugs to Fix

### BUG 1: Every template update returns 403 (HIGH)
- **Location:** `frontend/src/components/TemplateManager.vue:1166,1183`
- **Cause:** Frontend sends `system_instructions` in the PUT payload. Backend (`crud.py:258-263`) correctly blocks it with 403 (system_instructions is read-only after 0813).
- **Fix:** Replace `system_instructions` with `user_instructions` in the update payload. The textarea should bind to `user_instructions`.

### BUG 2: No user_instructions editor (HIGH)
- **Location:** `TemplateManager.vue:454-472`
- **Cause:** Dialog has a "System Prompt" textarea bound to `system_instructions`. The `user_instructions` field has zero UI representation.
- **Fix:** Replace the "System Prompt" textarea with a "Role & Expertise" textarea that edits `user_instructions`.

### BUG 3: No MCP bootstrap injection on create (MEDIUM)
- **Location:** `crud.py:137-225` (`create_template()`)
- **Cause:** The endpoint stores `system_instructions` verbatim from the request. No canonical bootstrap is injected.
- **Fix:** Import and call `_get_mcp_bootstrap_section()` from `template_seeder.py` to set `system_instructions` on create, ignoring whatever the frontend sends. Or move bootstrap injection to the TemplateService layer.

### BUG 4: Stale reset fallback (MEDIUM)
- **Location:** `template_service.py:923-944` (`reset_system_instructions()`)
- **Cause:** Hardcoded 5-line fallback that predates 0813. Does not use `_get_mcp_bootstrap_section()`.
- **Fix:** Import and use `_get_mcp_bootstrap_section()` as the canonical source.

---

## Implementation Plan

### Phase 1: Fix the Data Wiring (Backend)

**Goal:** Make `system_instructions` truly read-only AND ensure `user_instructions` flows correctly.

1. **`crud.py` — `create_template()`:**
   - Import `_get_mcp_bootstrap_section` from `template_seeder`
   - Always set `system_instructions = _get_mcp_bootstrap_section()` regardless of what the frontend sends
   - Accept `user_instructions` from the request body as the user-editable content
   - Verify `TemplateCreate` Pydantic model has `user_instructions` field

2. **`template_service.py` — `reset_system_instructions()`:**
   - Import `_get_mcp_bootstrap_section` from `template_seeder`
   - Replace hardcoded fallback with `_get_mcp_bootstrap_section()`

3. **`crud.py` — `update_template()`:**
   - Verify `user_instructions` is accepted in the PUT payload (already works at line 268-274)
   - No backend changes needed here — it already handles `user_instructions` correctly

4. **`_get_mcp_bootstrap_section()` accessibility:**
   - This function is currently module-level in `template_seeder.py`. If import creates circular dependencies, extract to a small `bootstrap.py` utility module.

### Phase 2: Redesign the Dialog (Frontend)

**Goal:** Replace the single "System Prompt" textarea with structured sections.

**File:** `frontend/src/components/TemplateManager.vue`

#### Section 1: Identity (already partially exists)
- Role dropdown (already exists at line 342-351)
- Custom suffix input (already exists)
- Generated name preview (already exists as `generatedName` computed)
- Color swatch (already exists, auto-assigned from role)

#### Section 2: Role & Expertise Editor (NEW — replaces "System Prompt" textarea)
- Replace label "System Prompt" with "Role & Expertise"
- Replace hint text with: "Describe this agent's specialization, expertise, and personality. This content defines who the agent is."
- Bind textarea to `user_instructions` instead of `system_instructions`/`template`
- Provide seed text for new templates based on role (from `_get_default_templates_v103()` user_instructions)

#### Section 3: Protocol Notice (NEW — replaces nothing, informational only)
- `v-alert` with `type="info"` and `variant="tonal"`
- Text: "GiljoAI automatically injects orchestration protocols at runtime. These handle MCP connectivity, lifecycle management, and team coordination."
- Non-editable, no expandable details
- Show below the Role Editor

#### Section 4: CLI-Specific Fields (restructure existing)
- Currently: model dropdown only shown for Claude, description only for Claude
- Keep the `cli_tool` radio buttons (Claude/Codex/Gemini)
- **Claude tab:** model dropdown (sonnet/opus/haiku), description, tools
- **Codex tab:** Placeholder text — "Codex-specific fields coming in a future update" (not yet wired to export)
- **Gemini tab:** Placeholder text — "Gemini-specific fields coming in a future update" (not yet wired to export)
- These placeholders prevent scope creep. Codex/Gemini export is a separate handover.

#### Section 5: Rules & Criteria (already exists, keep as-is)
- Behavioral rules list (already implemented)
- Success criteria list (already implemented)

### Phase 3: Fix the Data Flow

**Goal:** Wire the frontend field names to match the backend contract.

1. **Loading templates** (`TemplateManager.vue:1002`):
   - Load `user_instructions` field from API response (currently only loads `system_instructions`)
   - Map to `editingTemplate.value.user_instructions`

2. **Opening edit dialog** (`TemplateManager.vue:1094-1110`):
   - Populate `user_instructions` from the template record
   - Do NOT populate the old `template` field from `system_instructions`

3. **Saving** (`TemplateManager.vue:1155-1195`):
   - **Create:** Send `user_instructions` (the textarea content). Do NOT send `system_instructions`.
   - **Update:** Send `user_instructions` (the textarea content). Do NOT send `system_instructions`.
   - Remove `system_instructions` from both create and update payloads entirely.

4. **API response model:**
   - Verify `TemplateResponse` includes `user_instructions` in the response
   - Verify `_convert_to_response()` in `crud.py` maps `user_instructions`

### Phase 4: Export Pipeline Consistency

**Goal:** Ensure the filesystem export path produces the same output as ZIP/token paths.

1. **`claude_export.py` — `generate_yaml_frontmatter()`:**
   - This function is used by the filesystem export path and produces different output than `render_claude_agent()`
   - Option A: Replace the filesystem export path to use `render_claude_agent()` (preferred — single renderer)
   - Option B: Update `generate_yaml_frontmatter()` to match `render_claude_agent()` behavior (maintaining two renderers is a maintenance burden)

2. **`downloads.py` — `generate_yaml_frontmatter()`:**
   - Dead code (zero references). Delete it.

### Phase 5: Tests

1. **Backend tests:**
   - `create_template()` injects bootstrap as `system_instructions`
   - `create_template()` stores `user_instructions` from request
   - `update_template()` does NOT accept `system_instructions`
   - `update_template()` accepts and stores `user_instructions`
   - `reset_system_instructions()` produces canonical bootstrap
   - Export paths produce identical output for the same template

2. **Frontend tests (if test infrastructure exists):**
   - Save button sends `user_instructions`, not `system_instructions`
   - Role editor textarea binds to `user_instructions`
   - Protocol notice is visible and non-editable

---

## Files to Modify

| File | Changes |
|---|---|
| `frontend/src/components/TemplateManager.vue` | Redesign dialog, fix field bindings, fix save payload |
| `api/endpoints/templates/crud.py` | Inject bootstrap on create, verify update contract |
| `src/giljo_mcp/services/template_service.py` | Fix `reset_system_instructions()` to use canonical bootstrap |
| `api/endpoints/claude_export.py` | Unify with `render_claude_agent()` or update to match |
| `api/endpoints/downloads.py` | Delete dead `generate_yaml_frontmatter()` |
| `src/giljo_mcp/template_renderer.py` | No changes expected (already updated in 0813) |

---

## What NOT to Do

- Do NOT add Codex TOML export or Gemini MD export — that is a separate handover
- Do NOT expose `system_instructions` content in the UI — protocols are IP
- Do NOT change the 6 canonical role colors or the role dropdown options
- Do NOT modify `_get_mcp_bootstrap_section()` — it is canonical from 0813
- Do NOT break multi-terminal mode — changes to `system_instructions`/`user_instructions` affect `_resolve_spawn_template()` which bakes both into `AgentJob.mission`

---

## Verification Checklist

- [ ] Create a new template → `system_instructions` contains canonical MCP bootstrap
- [ ] Edit an existing template → save succeeds (no 403)
- [ ] Edit the Role & Expertise textarea → `user_instructions` is stored and persisted
- [ ] Reset system instructions → produces canonical bootstrap, not stale fallback
- [ ] ZIP download → exported `.md` files contain user_instructions prose
- [ ] Slash command (`/gil_get_claude_agents`) → same output as ZIP
- [ ] Filesystem export → same output as ZIP (if Phase 4 Option A applied)
- [ ] Multi-terminal agent → receives role from `user_instructions` via `_resolve_spawn_template()`
- [ ] Protocol notice visible in dialog, non-editable
- [ ] No lint errors (`ruff check src/ api/`)

---

## Cascading Analysis

**Downstream impact:**
- Templates are consumed by: export pipeline (ZIP/token/filesystem), `_resolve_spawn_template()` (multi-terminal), `get_agent_templates` context tool (staging), `render_claude_agent()` (all export paths)
- All downstream consumers already handle `user_instructions` correctly after 0813
- The fix is upstream (UI writes the right field), downstream already works

**Upstream impact:**
- No schema changes needed — `user_instructions` column already exists
- No migration needed

**Sibling impact:**
- Other frontmatter fields (model, tools, color) are unchanged
- CLI radio buttons keep existing behavior

**Installation impact:**
- No schema changes, no new dependencies, no config changes
- `install.py` unaffected

---

## Follow-Up: Multi-CLI Export (0815)

0814 fixes the Claude Code pipeline. A follow-up handover will add:
- `render_codex_agent()` — TOML output (`config.toml` + per-role `.toml`)
- `render_gemini_agent()` — Gemini-flavored MD (different YAML frontmatter schema)
- Rename `/gil_get_claude_agents` → `/gil_get_agents` with CLI-aware routing
- Wire Codex/Gemini tab fields in the Template Manager (currently placeholders)
- Per-CLI export buttons or dynamic download selection
- Additional staging mode radio buttons (Codex/Gemini subagent modes)

See `handovers/agent_template.md` Section 8 for the full multi-CLI roadmap and design options.

---

## Implementation Summary (2026-03-10)

### What Was Built
- **Phase 1 (backend)**: Already committed — `create_template()` injects canonical bootstrap, `reset_system_instructions()` uses canonical source, `update_template()` blocks `system_instructions` with 403
- **Phase 2+3 (frontend)**: Replaced "System Prompt" textarea with "Role & Expertise" editor bound to `user_instructions`, added protocol notice v-alert, fixed all save/load/edit/duplicate data flow
- **Phase 4 (export)**: Unified filesystem export to use `render_claude_agent()` as single renderer, deleted 2 dead `generate_yaml_frontmatter()` functions (claude_export.py + downloads.py)
- **Phase 5 (tests)**: 20 tests covering bootstrap injection, user_instructions flow, 403 blocking, reset canonical, render consistency

### Key Files Modified
- `frontend/src/components/TemplateManager.vue` — dialog redesign, field bindings, save payloads
- `api/endpoints/claude_export.py` — unified to render_claude_agent(), dead code removed (-141 lines)
- `api/endpoints/downloads.py` — dead generate_yaml_frontmatter() removed (-56 lines)
- `tests/unit/test_0814_template_manager_ui.py` — 20 backend tests

### Commits
- `341dee82` Phase 1 backend (prior agent)
- `1eac861e` Phase 5 tests (20 passing)
- `835c629f` Phase 2+3+4 frontend + export unification

### Net Effect
-191 lines (39 added, 230 removed). All 4 bugs fixed. Single renderer for all export paths.
