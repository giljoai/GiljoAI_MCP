# CE Launch Credential Scrub Checklist

**Purpose:** Before publishing the Community Edition on the `main` branch, ALL personal credentials, hardcoded passwords, and developer-specific secrets must be removed or replaced with environment variable references.

**Edition Scope:** CE

**Last Audited:** 2026-03-27

**Decision:** The entire `handovers/` directory is internal-only and will be excluded from the CE release. This eliminates ~25 files with credentials in one shot.

---

## Priority Legend

- **P0** -- Blocks release. Actual passwords/credentials in source code.
- **P1** -- High. Credentials in documentation shipped with CE.
- **P2** -- Medium. Credentials in test code or dev tooling.

---

## Directories Excluded from CE Release

These directories are internal-only and must NOT ship in the public CE branch:

| Directory | Reason |
|-----------|--------|
| `handovers/` | Internal dev handovers, contains credentials throughout |
| `backups/` | Recovery scripts with hardcoded DB passwords |
| `prompts/` | Internal agent prompt chains with test credentials |

Add these to the CE release filter (giltest.ignore.md or release script). This eliminates credentials in: all completed handover docs, reference docs (QUICK_LAUNCH.txt, start_to_finish_agent_FLOW.md), recovery scripts, and prompt chains.

---

## P0: Hardcoded Passwords in Source Code

These files contain real passwords that execute against the database or auth system. They MUST be fixed before any public release.

### Test user password `MHTGiljo4010!`

| # | File | Lines | Action |
|---|------|-------|--------|
| 1 | `dev_tools/control_panel.py` | 2474, 2484, 2524, 2553 | Replace with `os.getenv("TEST_USER_PASSWORD", "changeme")` |

### PostgreSQL password `4010` in Python code

| # | File | Lines | Action |
|---|------|-------|--------|
| 2 | `startup.py` | ~310 | Change default from `"4010"` to empty string or raise if unset |
| 3 | `uninstall.py` | ~97 | Change default from `"4010"` to empty string or raise if unset |
| 4 | `scripts/migrate_to_orgs.py` | ~80 | Replace hardcoded connection string with `os.getenv("DATABASE_URL")` |
| 5 | `scripts/verify_tool_index_performance.py` | ~204 | Replace hardcoded connection string with `os.getenv("DATABASE_URL")` |
| 6 | `scripts/migrate_add_tool_column.py` | ~264 | Replace hardcoded connection string with `os.getenv("DATABASE_URL")` |

### SQL files with passwords

| # | File | Lines | Action |
|---|------|-------|--------|
| 7 | `backups/migration_restore_0424_v3.sql` | 39, 88 | Excluded via `backups/` directory exclusion |
| 8 | `migrations/archive/pre_baseline/0352_vision_depth_optional_to_light.sql` | ~15 | Scrub password or exclude `migrations/archive/` from CE |

---

## P1: Credentials in Documentation Shipped with CE

Replace real passwords with placeholder syntax like `$DB_PASSWORD` or `<your-password>`.

### `PGPASSWORD=4010` in docs

| # | File | Action |
|---|------|--------|
| 9 | `docs/TESTING.md` | Replace `PGPASSWORD=4010` with `PGPASSWORD=$DB_PASSWORD` |
| 10 | `docs/guides/migration_strategy.md` | Replace `PGPASSWORD=4010` with `PGPASSWORD=$DB_PASSWORD` |
| 11 | `migration_report.md` (repo root) | Replace or delete -- one-time migration artifact |
| 12 | `tests/integration/README.md` | Replace `PGPASSWORD=4010` with `PGPASSWORD=$DB_PASSWORD` |
| 13 | `tests/integration/PHASE4_MANUAL_TESTING_GUIDE.md` | Replace `PGPASSWORD=4010` with `PGPASSWORD=$DB_PASSWORD` |

### `MHTGiljo4010!` in docs

| # | File | Action |
|---|------|--------|
| 14 | `docs/guides/SELECTOR_TEST_EXAMPLES.md` | Replace with `$TEST_PASSWORD` placeholder |
| 15 | `docs/archive/TEST_FIXES_FINAL_REPORT.md` | Replace or exclude `docs/archive/` from CE |

---

## P2: Credentials in Test Code and E2E Suites

Extract to environment variables or a `.env.test` file that's gitignored.

### E2E test files with `MHTGiljo4010!`

| # | File | Action |
|---|------|--------|
| 16 | `frontend/tests/e2e/helpers.ts` | Central file -- extract to `process.env.TEST_PASSWORD` with fallback |
| 17 | `frontend/tests/e2e/selector-validation.spec.ts` | Use helper from `helpers.ts` |
| 18 | `frontend/tests/e2e/cli-mode-toggle-staging.spec.js` | Use helper from `helpers.ts` |
| 19 | `frontend/tests/e2e/admin-settings-identity.spec.js` | Use helper from `helpers.ts` |
| 20 | `frontend/tests/e2e/message-counters.spec.js` | Use helper from `helpers.ts` |
| 21 | `frontend/tests/e2e/launch-button-staging-complete.spec.js` | Use helper from `helpers.ts` |
| 22 | `frontend/tests/e2e/message-routing-0289.spec.ts` | Use helper from `helpers.ts` |
| 23 | `frontend/tests/e2e/closeout-workflow.spec.ts` | Use helper from `helpers.ts` |
| 24 | `frontend/tests/e2e/auth-bypass.ts` | Use helper from `helpers.ts` |
| 25 | `frontend/tests/e2e/patch_auth.py` | Use `os.getenv("TEST_PASSWORD")` |
| 26 | `frontend/selector-validation.test.js` | Use `process.env.TEST_PASSWORD` |

### E2E test documentation with credentials

| # | File | Action |
|---|------|--------|
| 27 | `frontend/tests/e2e/README.md` | Replace password with `$TEST_PASSWORD` |
| 28 | `frontend/tests/e2e/HANDOVER_0287_QUICK_REFERENCE.md` | Delete -- completed handover doc, internal only |
| 29 | `frontend/tests/e2e/HANDOVER_0287_TEST_GUIDE.md` | Delete -- completed handover doc, internal only |
| 30 | `frontend/tests/e2e/HANDOVER_0287_SUMMARY.md` | Delete -- completed handover doc, internal only |
| 31 | `frontend/tests/e2e/ADMIN_SETTINGS_IDENTITY_TEST_GUIDE.md` | Replace password with placeholder |
| 32 | `frontend/tests/e2e/MESSAGE_COUNTERS_TEST_GUIDE.md` | Replace password with placeholder |
| 33 | `frontend/tests/e2e/MESSAGE_COUNTERS_QUICK_START.md` | Replace password with placeholder |
| 34 | `frontend/tests/e2e/MESSAGE_COUNTERS_DELIVERY.md` | Replace password with placeholder |
| 35 | `frontend/tests/e2e/README_ADMIN_SETTINGS.md` | Replace password with placeholder |
| 36 | `frontend/tests/e2e/TEST_EXECUTION_CHECKLIST.md` | Replace password with placeholder |
| 37 | `frontend/tests/e2e/temp_auth_changes.txt` | Delete -- temporary file |

---

## NOT in scope (keep as-is)

| Item | Reason |
|------|--------|
| `.env.example` | Template with placeholders, no real values |
| `frontend/.env.production` | Contains URLs only, no secrets |
| `frontend/.env.test` | Contains URLs only, no secrets |
| `install.py` / `installer/` | Prompts user for passwords at install time |
| GitHub username `patrik-giljoai` in URLs | Public repo URL, not a credential |
| `Linux_Installer/credentials/` | Empty directory with `.gitkeep` |

---

## Execution Plan

### Step 1: Configure CE release exclusions
Add to release filter (giltest.ignore.md or release script):
```
handovers/
backups/
prompts/
migrations/archive/
docs/archive/
```

### Step 2: Fix P0 source code (6 items)
Fix items 1-6 -- hardcoded passwords in Python files. These are functional code changes.

### Step 3: Fix P1 documentation (7 items)
Fix items 9-15 -- replace real passwords with placeholders in shipped docs.

### Step 4: Fix P2 test code (12 items)
Fix items 16-26 -- centralize test credentials behind `process.env.TEST_PASSWORD`.

### Step 5: Clean P2 test docs (10 items)
Fix items 27-37 -- scrub or delete test documentation with credentials.

### Step 6: Verify

```bash
# Must ALL return 0 results before release
grep -rn "MHTGiljo4010" .
grep -rn "PGPASSWORD=4010" .
grep -rn "Claude4010" .
grep -rn "password.*4010" --include="*.py" .
grep -rn "postgres:4010@" .
```

### Step 7: Git history (if needed)
If the CE `main` branch has these credentials in prior commits, use BFG Repo-Cleaner to purge them from history before making the repo public.

---

## Sign-off

| Step | Owner | Date | Done |
|------|-------|------|------|
| CE release exclusions configured | | | [ ] |
| P0 source code scrubbed | | | [ ] |
| P1 documentation scrubbed | | | [ ] |
| P2 test code scrubbed | | | [ ] |
| P2 test docs scrubbed/deleted | | | [ ] |
| Verification grep returns 0 results | | | [ ] |
| Git history cleaned (BFG or filter-branch) | | | [ ] |
| Fresh clone test passes | | | [ ] |
