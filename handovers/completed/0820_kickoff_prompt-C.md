# Kickoff Prompt: Handover 0820 -- Remove Context Priority Framing

**Copy-paste this into a fresh Claude Code terminal.**

---

You are starting a fresh implementation session for **Handover 0820: Remove Context Priority Framing**.

## First Steps (MANDATORY -- do these before writing any code)

1. **Read the handover instructions:**
   ```
   Read F:\GiljoAI_MCP\handovers\HANDOVER_INSTRUCTIONS.md
   ```

2. **Read the quick launch and agent flow references:**
   ```
   Read F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt
   Read F:\GiljoAI_MCP\handovers\Reference_docs\AGENT_FLOW_SUMMARY.md
   ```

3. **Read the handover spec (this is your work order):**
   ```
   Read F:\GiljoAI_MCP\handovers\0820_remove_context_priority_framing.md
   ```

4. **Read the edition isolation guide (required before writing code):**
   ```
   Read F:\GiljoAI_MCP\docs\EDITION_ISOLATION_GUIDE.md
   ```

5. **Check git status and confirm you are on `master` branch. Confirm backup branch `Removal_context_framing` exists (DO NOT checkout to it -- it is the safety net).**

## What You Are Doing

Removing the entire CRITICAL/IMPORTANT/REFERENCE priority framing system from the codebase. This system assigns priority integers (1/2/3/4) and labels to context categories to influence LLM fetch decisions. Testing proved LLMs ignore these labels entirely. The binary toggle (on/off) and depth controls stay -- they work and are useful.

**What goes:** Priority integers, priority labels (CRITICAL/IMPORTANT/REFERENCE), framing text injection into prompts, the `framing_helpers.py` module, priority selectors in the UI, `field-priority` API endpoints' priority logic, all related tests and docs.

**What stays:** Toggle switches (on/off per category), depth controls (how much data to serve per category), the `depth_config` column and its API endpoints.

## Execution Strategy

Work through the 4 phases defined in the handover. After each phase, run the relevant test suite to catch breakage before proceeding.

### Phase 1: Backend Core
- Simplify `defaults.py` (remove priority ints, keep toggles)
- Delete or gut `framing_helpers.py` (check if `format_list_safely`/`_stringify_content` are imported elsewhere first -- if yes, relocate them)
- Update `thin_prompt_generator.py` (replace priority-based logic with toggle checks)
- Update `mission_planner.py` (remove tiered framing instructions)
- Update `protocol_builder.py` (simplify normalization to toggle-only)
- Update `orchestration_service.py` (replace framing-based architecture with toggle-based fetch list)
- Remove `_derive_priority()` from `project_closeout.py`
- Simplify `user_service.py` (toggle-only validation)
- Update `fetch_context.py` (remove priority application, keep depth)
- Clean up `testing_config_generator.py`
- Delete `tests/unit/test_framing_helpers_validation.py`
- Update other backend tests
- **Run:** `pytest tests/ -x --tb=short` (fix failures before proceeding)

### Phase 2: API Endpoints
- Simplify `FieldPriorityConfig` model in `api/endpoints/users.py` to toggle-only schema
- Update 3 field-priority endpoints (GET/PUT/POST reset) for toggle-only payloads
- Clean up `prompts.py` and `simple_handover.py`
- Update test fixtures in `conftest.py`
- **Run:** `pytest tests/ -x --tb=short`

### Phase 3: Frontend
- Rewrite `ContextPriorityConfig.vue` -- strip priority selectors, keep toggle switches + depth controls
- Consider renaming component to `ContextConfig.vue` (update all imports if so)
- Simplify `settings.js` store (toggle-only state)
- Update `api.js` service calls
- Simplify/remove `useFieldPriority.js` composable
- Update `UserSettings.vue` imports if component renamed
- Update `ProductIntroTour.vue`:
  - Line 168: `'Priority + depth settings'` --> `'Toggleable categories + depth settings'`
  - Line 173: `'Context priority + depth controls...'` --> `'Context toggles + depth controls...'`
- Delete priority-specific test files, rewrite toggle-focused tests
- Delete `frontend/CONTEXT_PRIORITY_CONFIG_DUAL_ENDPOINT_IMPLEMENTATION.md`
- **Run:** `cd frontend && npm run test -- --run` (fix failures before proceeding)

### Phase 4: Documentation
- Delete `docs/user_guides/field_priorities_guide.md` (entire file is obsolete v1.0 guide)
- Delete or rewrite `docs/architecture/FIELD_PRIORITIES_SYSTEM.md`
- Update these docs (see handover for exact line numbers):
  - `docs/guides/context_configuration_guide.md`
  - `docs/api/context_tools.md`
  - `docs/SERVICES.md`
  - `docs/ORCHESTRATOR.md`
  - `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
  - `docs/architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md`
  - `docs/README_FIRST.md`
  - `docs/components/STAGING_WORKFLOW.md`
- Update reference docs:
  - `handovers/Reference_docs/QUICK_LAUNCH.txt`
  - `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`
  - `handovers/Reference_docs/HARMONIZED_WORKFLOW.md`
  - `handovers/Reference_docs/start_to_finish_agent_FLOW.md`
  - `handovers/Reference_docs/Simple_Vision.md`
  - `WEBSITE_MESSAGING_REVISION_BRIEF.md`

### Final Verification

After all 4 phases, run:
```bash
# Backend tests
pytest tests/ -x --tb=short

# Frontend tests
cd frontend && npm run test -- --run

# Verify no orphaned references remain
grep -r "priority.*framing\|CRITICAL.*IMPORTANT.*REFERENCE\|inject_priority_framing\|apply_rich_entry_framing\|build_framed_context_response\|build_priority_excluded_response" src/ api/ frontend/src/ --include="*.py" --include="*.js" --include="*.vue" --include="*.ts"

# Should return zero results (excluding comments in this handover itself)
```

## Rules

- Follow TDD discipline per HANDOVER_INSTRUCTIONS.md
- Every DB query must filter by `tenant_key`
- No AI signatures in code or commits
- Delete old code, don't comment it out
- Do NOT modify files in `handovers/completed/` -- those are historical records
- Do NOT checkout or modify the `Removal_context_framing` backup branch
- Do NOT use `--no-verify` on commits without user approval
- Commit after each completed phase with a descriptive message
- Update the handover document with completion status when done
