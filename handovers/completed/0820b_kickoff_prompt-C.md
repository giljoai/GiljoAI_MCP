# Kickoff Prompt: Handover 0820b -- Context Priority Removal Remediation

**Copy-paste this into a fresh Claude Code terminal.**

---

You are starting a fresh implementation session for **Handover 0820b: Context Priority Removal -- Audit Remediation**.

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
   Read F:\GiljoAI_MCP\handovers\0820b_context_priority_removal_remediation.md
   ```

4. **Read the edition isolation guide (required before writing code):**
   ```
   Read F:\GiljoAI_MCP\docs\EDITION_ISOLATION_GUIDE.md
   ```

5. **Check git status and confirm you are on `master` branch.**

## What You Are Doing

Handover 0820 removed the entire CRITICAL/IMPORTANT/REFERENCE priority framing system (-5,698 lines across 53 files). A 4-agent audit found issues in the implementation. This handover fixes all 16 findings across 4 phases.

**Key context:** The priority framing system assigned integer priorities (1/2/3/4) to context categories. 0820 replaced it with a simple toggle (on/off) + depth (how much detail) model. The toggle system works. The audit found places where old data formats, stale tests, and documentation were not fully cleaned up.

### The 3 most important things to understand:

1. **Data format change:** Old v2.0 configs stored `{"priorities": {"product_core": 1, "vision_documents": 2}}` (integers). New v3.0 stores `{"priorities": {"product_core": {"toggle": true}}, "version": "3.0"}`. The `_normalize_field_toggles()` function in `protocol_builder.py` handles conversion -- use it.

2. **Nested dict bug:** Several code paths extract raw `user.field_priority_config.get("priorities", {})` and pass it downstream as `field_toggles`. For v3.0, this yields `{"key": {"toggle": bool}}` nested dicts. A `{"toggle": False}` dict evaluates as truthy in Python, so disabled categories get incorrectly included. The fix: flatten to `{key: bool}` before passing.

3. **Test/doc cleanup:** Many tests and docs still reference the old priority model (P1/P2/P3 buckets, `priority-*` selectors, integer formats). Delete or rewrite these.

## Execution Strategy

Work through the 4 phases defined in the handover. After each phase, run the relevant test suite.

### Phase 1: Backend Data Compatibility (6 fixes)
- Fix CRITICAL: Normalize legacy data in API endpoint (`api/endpoints/users.py`)
- Fix HIGH: Flatten toggle dicts in `prompts.py` (lines 177, 382)
- Fix HIGH: Flatten toggle dicts in `project_service.py` (line 2023)
- Fix HIGH: Add `"field_priorities"` fallback in `orchestration_service.py` (line 2493)
- Fix MEDIUM: Stale docstring in `user_service.py` (line 1142)
- Fix MEDIUM: Stale comment in `thin_prompt_generator.py` (line 596)
- **Run:** `pytest tests/ -x --tb=short -k "not test_auth_org and not test_user_service_crud"`

### Phase 2: Backend Test Fixes (3 fixes)
- Fix HIGH: Delete stale `test_frontend_test_spec_uses_vision_documents` in `test_depth_config_standardization.py`
- Fix MEDIUM: Update `test_returns_framing_based_context` assertion (dict -> list) in `test_orchestration_service_instructions.py`
- Fix MEDIUM: Fix data types in `test_thin_client_prompt_generator_agent_templates_core.py`
- **Run:** `pytest tests/ -x --tb=short -k "not test_auth_org and not test_user_service_crud"`

### Phase 3: Frontend Test Fixes (4 fixes)
- Fix HIGH: Delete broken `'Context Priority Management'` describe block in `UserSettings.spec.js` (lines 66-380)
- Fix MEDIUM: Clean up 3 selector validation files (delete priority-* tests/entries)
- Fix MEDIUM: Remove ESLint ignore for `ContextPriorityConfig.vue`
- Fix MEDIUM: Rename `data-testid="reset-context-priority-btn"` to `reset-context-config-btn`
- **Run:** `cd frontend && npm run test -- --run`

### Phase 4: Documentation Cleanup (3 fixes)
- Fix MEDIUM: Deep-clean `ORCHESTRATOR_CONTEXT_FLOW_SSoT.md` (~64 stale priority refs with code examples)
- Fix MEDIUM: Update 4 missed doc files (SERVICES.md, service_response_models.md, SELECTOR_TEST_EXAMPLES.md, SELECTOR_TEST_GUIDE.md)
- Fix MEDIUM: Fix "context priority configurator" in `Simple_Vision.md` line 454
- **Run:** Grep verification for zero orphaned references

### Final Verification

```bash
# Backend tests
pytest tests/ -x --tb=short -k "not test_auth_org and not test_user_service_crud"

# Frontend tests
cd frontend && npm run test -- --run

# Grep for orphaned references
grep -r "priority.*framing\|CRITICAL.*IMPORTANT.*REFERENCE\|inject_priority_framing\|apply_rich_entry_framing\|build_framed_context_response\|build_priority_excluded_response" src/ api/ frontend/src/ --include="*.py" --include="*.js" --include="*.vue" --include="*.ts"
```

## Key Files Reference

| File | What to Do |
|------|-----------|
| `api/endpoints/users.py` | Fix C1: normalize before Pydantic validation |
| `api/endpoints/prompts.py` | Fix H1: flatten at lines 177, 382 |
| `src/giljo_mcp/services/project_service.py` | Fix H1: flatten at line 2023 |
| `src/giljo_mcp/services/orchestration_service.py` | Fix H2: add fallback at line 2493 |
| `src/giljo_mcp/services/protocol_builder.py` | Reference: `_normalize_field_toggles()` is the correct normalizer |
| `src/giljo_mcp/services/user_service.py` | Fix M: docstring line 1142 |
| `src/giljo_mcp/thin_prompt_generator.py` | Fix L: comment line 596 |
| `tests/services/test_depth_config_standardization.py` | Fix H4: delete test at lines 151-168 |
| `tests/services/test_orchestration_service_instructions.py` | Fix M1: line 97 dict->list |
| `tests/services/test_thin_client_prompt_generator_agent_templates_core.py` | Fix M: data types at lines 58-60, 130, 228, 232 |
| `frontend/tests/views/UserSettings.spec.js` | Fix H3: delete lines 66-380 |
| `frontend/tests/e2e/selector-validation.spec.ts` | Fix M5: delete priority tests |
| `frontend/selector-validation.test.js` | Fix M5: delete priority tests |
| `frontend/validate-selectors.js` | Fix M5: delete priority entry |
| `frontend/eslint.config.js` | Fix M6: remove ignore line 24 |
| `frontend/src/components/settings/ContextPriorityConfig.vue` | Fix M7: rename testid line 9 |
| `docs/architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md` | Fix M2: deep-clean ~64 refs |
| `docs/SERVICES.md` | Fix M3: line 24 |
| `docs/architecture/service_response_models.md` | Fix M3: lines 91-93 |
| `docs/guides/SELECTOR_TEST_EXAMPLES.md` | Fix M3: lines 454-528+ |
| `docs/guides/SELECTOR_TEST_GUIDE.md` | Fix M3: lines 215-265, 440-488 |
| `handovers/Reference_docs/Simple_Vision.md` | Fix M4: line 454 |

## Rules

- Follow TDD discipline per HANDOVER_INSTRUCTIONS.md
- Every DB query must filter by `tenant_key`
- No AI signatures in code or commits
- Delete old code, don't comment it out
- Do NOT modify files in `handovers/completed/` -- those are historical records
- Do NOT use `--no-verify` on commits without user approval
- Commit after each completed phase with a descriptive message
- Update the handover document with completion status when done
