# Handover 0906: install.py --dev Flag & Install Cleanup

**Date:** 2026-04-03
**Priority:** Medium
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Add a `--dev` flag to `install.py` matching the existing `startup.py --dev` convention. Gate developer-only install steps (pre-commit hooks, NLTK data download) behind this flag so the default CE user install is faster and leaner. Also fix duplicate demo data seeding and stale docstring.

**Why:** A CE user downloading GiljoAI to use it should not wait for pre-commit hooks (~30-60s) or NLTK data downloads (~10-30s) they will never need. Developers contributing to the codebase opt in with `--dev`. This matches the existing `startup.py --dev` pattern.

**Expected outcome:** `python install.py` is faster by ~40-90 seconds. `python install.py --dev` installs everything including dev tooling. README.md documents the distinction.

---

## Current State

### install.py install_dependencies() (lines 1381-1495)
After `pip install -r requirements.txt`, three sequential steps always run:
1. **pip install pre-commit + pre-commit install** (lines 1443-1463) — Dev-only tool, irrelevant to CE users
2. **NLTK data download** (lines 1465-1477) — Network call for vision summarization feature. Can be deferred to startup.py or first use.
3. Both steps are in try/except so they soft-fail, but still add 40-90 seconds to every install

### Duplicate demo data seeding
`_seed_agent_job_demo_data()` is called in TWO places:
- Line 341: In `run()` main flow (step 6.6)
- Line 1665: Inside `setup_database()`

The call in `setup_database()` (line 1665) is the correct location since it has access to the tenant_key. The call in `run()` (line 341) is redundant.

### Stale docstring
Line 22: `8. Open browser (http://localhost:7274)` — should be 7272 after handover 0902 (single-port serving).

---

## Files to Modify

| File | Change |
|------|--------|
| `install.py` | Add `--dev` flag; gate pre-commit + NLTK behind it; remove duplicate seeding; fix docstring |
| `README.md` | Document `install.py --dev` in Quick Start and Installation Modes sections |
| `handovers/handover_catalogue.md` | Add 0906 entry |

---

## Implementation Plan

### Phase 1: install.py changes

1. Add `--dev` click option to `main()` function
2. Pass `dev` flag through settings dict
3. Wrap pre-commit install block (lines 1443-1463) in `if self.settings.get("dev"):`
4. Wrap NLTK download block (lines 1465-1477) in `if self.settings.get("dev"):`
5. Add info message in non-dev path: "Skipping dev tools. Use --dev for pre-commit hooks and NLTK data."
6. Remove duplicate `_seed_agent_job_demo_data()` call from `run()` (lines 335-347) — keep the one inside `setup_database()`
7. Fix docstring line 22: 7274 → 7272

### Phase 2: README.md updates

1. Add `--dev` to the install.py command-line options in Quick Start
2. Update Installation Modes section to show the flag distinction
3. Add install.py options table matching the existing startup.py options table

### Phase 3: Catalogue update

1. Add 0906 to handover_catalogue.md active table and quick reference

---

## Testing Requirements

- `python install.py --help` shows `--dev` flag with description
- Default install skips pre-commit and NLTK steps (verify via output messages)
- `--dev` install runs pre-commit and NLTK steps
- Demo data seeding only runs once (inside setup_database)
- `ruff check install.py` passes clean

---

## Success Criteria

- Default `python install.py` is 40-90 seconds faster (no pre-commit, no NLTK download)
- `python install.py --dev` preserves full developer experience
- README.md clearly documents the distinction
- No duplicate demo seeding
- Stale port reference fixed
