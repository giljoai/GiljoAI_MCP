# Project 0015 – Orchestrator Protection & Admin Editor

## Summary
Lock down the core Orchestrator agent so it can no longer be modified, exported, or toggled by end users while introducing an admin-only editor with explicit warnings. The orchestrator prompt becomes a hard-coded system asset with optional overrides gated behind Administrator role checks.

## Key Requirements
1. **Immutable Orchestrator Agent**
   - Remove the orchestrator from Template Manager lists/toggles and exclude it from exports.
   - Count it as a permanent active agent slot so users can enable only seven additional agents.
   - Prevent CRUD/toggle/delete/reset operations for this role at the API level.
   - ✅ Implemented via backend guardrails (`SYSTEM_MANAGED_ROLES`) plus frontend filtering and a new stats endpoint.

2. **Canonical Prompt Source**
   - Store the default orchestrator prompt in code and load it via a dedicated service.
   - Persist admin overrides centrally (e.g., `configurations` table) with size/validation checks.
   - Update mission generation to reference this canonical source instead of seeded templates.
   - ✅ Added `SystemPromptService`, admin APIs, and updated `MissionTemplateGeneratorV2` to use this canonical source.

3. **Admin “System” Tab**
   - Add a new tab after Security in Admin Settings that exposes a guarded editor.
   - Require admin role; show the current prompt, allow edits, provide Save + Restore Default.
   - Display strong warnings about the risk of editing and log metadata for changes.
   - ✅ New System tab in `SystemSettings.vue` with warning banners, dirty-state tracking, save, and restore controls.

4. **Docs & Tests**
   - Update Template Manager guidance and add a System Settings note covering the new flow.
   - Add backend tests for guardrails and system prompt endpoints; frontend tests for filtering and editor state.

## Testing & Migration Notes
- **Backend**: expand pytest coverage for `GET/PUT/POST /api/v1/system/orchestrator-prompt`, template toggle/delete guards, and exporters to ensure system-managed roles never leak.
- **Frontend**: add Vitest coverage for the 7-slot counter logic and the System tab editor (dirty state, save, restore flows).
- **Manual smoke**: verify Template Manager shows 1 reserved slot, exports omit orchestrator files, and the admin System tab can load/save/restore with warning banners.
- **Migration**: seeding now skips orchestrator templates; any legacy rows remain active but hidden. Run a one-time cleanup/migration that enforces `is_active=True` for existing orchestrator records and removes previous installer exports.

---

## Progress Updates

### 2025-11-07: Implementation Complete ✅
- **Status**: All requirements implemented and verified
- **Key Deliverables**:
  - ✅ Immutable Orchestrator Agent with `SYSTEM_MANAGED_ROLES` guardrails
  - ✅ Canonical Prompt Source via `SystemPromptService`
  - ✅ Admin "System" Tab in SystemSettings.vue with warnings and controls
  - ✅ Backend and frontend protection mechanisms deployed
- **Implementation Evidence**:
  - `src/giljo_mcp/system_roles.py` - SYSTEM_MANAGED_ROLES definition
  - `src/giljo_mcp/system_prompts/service.py` - SystemPromptService
  - `src/giljo_mcp/template_seeder.py` - Orchestrator seeding protection
  - `src/giljo_mcp/thin_prompt_generator.py` - Canonical prompt usage
- **Testing**: Backend guardrails validated, frontend filtering confirmed
- **Result**: Orchestrator is now protected system asset, immutable by end users

**PROJECT_0115 Status**: ✅ COMPLETE - Ready for archival
