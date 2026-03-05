# 0720 Complete Delinting - Orchestrator Kickoff

## Context

You are the orchestrator for handover 0720 - Complete Codebase Delinting.

**Background**: The 0707-LINT handover was only ~15% completed. The codebase has 1,850+ lint issues including:
- 13 F821 (undefined names) - **RUNTIME BUGS**
- 324 B008 (mutable defaults) - **BUG PATTERN**
- 700+ TRY/style issues
- Broken frontend ESLint

**Your Mission**: Coordinate an agent team to achieve **zero lint errors** across the entire codebase.

---

## Phase Execution Order

Execute phases **sequentially** (dependencies exist):

| Phase | Agent | Focus | Est. Time |
|-------|-------|-------|-----------|
| 1 | Bug Fixer | F821, B008, F841, F401, E711, E712 | 1-2 hours |
| 2 | Code Quality | ERA001, RUF012, B007, B025, PLW0603, A00x | 1 hour |
| 3 | Style Fixer | TRY series, TID252, PERF, SIM | 1-2 hours |
| 4 | Configuration | .ruff.toml suppressions | 30 min |
| 5 | Frontend | ESLint fix + cleanup | 1 hour |

**Phase 5 can run in parallel with phases 1-4** since it's a separate codebase.

---

## Your Workflow

### 1. Initial Assessment
```bash
cd F:/GiljoAI_MCP
source venv/Scripts/activate
ruff check src/ api/ --statistics | head -30
```

### 2. Launch Phase 1 Agent
Read the full handover: `F:\GiljoAI_MCP\handovers\0720_COMPLETE_DELINT.md`
Use the Phase 1 kickoff prompt from that file.

### 3. Verify Phase Completion
After each phase agent reports completion:
```bash
ruff check src/ api/ --select [PHASE_RULES] --statistics
# Must show 0 for that phase's rules
```

### 4. Run Tests
```bash
pytest tests/ -x -q --tb=short
```
If tests fail, debug before proceeding.

### 5. Proceed to Next Phase
Repeat steps 2-4 for each phase.

### 6. Final Validation
```bash
ruff check src/ api/
# Expected: All checks passed!

cd frontend && npm run lint
# Expected: No errors

pre-commit run --all-files
# Expected: All hooks passed
```

---

## Commit Strategy

Create one commit per phase:
```
fix(0720-P1): Critical bug fixes - undefined names, mutable defaults
fix(0720-P2): Code quality cleanup - dead code, globals, shadowing
fix(0720-P3): Style and performance fixes - exception handling, imports
chore(0720-P4): Ruff configuration with documented suppressions
fix(0720-P5): Frontend ESLint fixes and configuration
```

---

## Success Criteria

- [ ] `ruff check src/ api/` returns 0 errors
- [ ] `cd frontend && npm run lint` returns 0 errors
- [ ] `pre-commit run --all-files` passes all hooks
- [ ] All tests passing (`pytest tests/`)
- [ ] 5 commits created (one per phase)

---

## Reference

Full handover document: `F:\GiljoAI_MCP\handovers\0720_COMPLETE_DELINT.md`

Contains:
- Detailed issue breakdown by rule
- Per-phase agent kickoff prompts
- Fix patterns and examples
- Suppression rationale

---

## Start

Begin by reading the handover document, then launch Phase 1.
