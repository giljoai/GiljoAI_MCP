# Project 0015 – Orchestrator Protection & Admin Editor

## Summary
Lock down the core Orchestrator agent so it can no longer be modified, exported, or toggled by end users while introducing an admin-only editor with explicit warnings. The orchestrator prompt becomes a hard-coded system asset with optional overrides gated behind Administrator role checks.

## Key Requirements
1. **Immutable Orchestrator Agent**
   - Remove the orchestrator from Template Manager lists/toggles and exclude it from exports.
   - Count it as a permanent active agent slot so users can enable only seven additional agents.
   - Prevent CRUD/toggle/delete/reset operations for this role at the API level.

2. **Canonical Prompt Source**
   - Store the default orchestrator prompt in code and load it via a dedicated service.
   - Persist admin overrides centrally (e.g., `configurations` table) with size/validation checks.
   - Update mission generation to reference this canonical source instead of seeded templates.

3. **Admin “System” Tab**
   - Add a new tab after Security in Admin Settings that exposes a guarded editor.
   - Require admin role; show the current prompt, allow edits, provide Save + Restore Default.
   - Display strong warnings about the risk of editing and log metadata for changes.

4. **Docs & Tests**
   - Update Template Manager guidance and add a System Settings note covering the new flow.
   - Add backend tests for guardrails and system prompt endpoints; frontend tests for filtering and editor state.
