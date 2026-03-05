# Kickoff: Handover 0707-LINT - Manual Lint Cleanup

**Series:** 0700 Code Cleanup Series
**Risk Level:** LOW-MEDIUM
**Estimated Effort:** 2-3 hours
**Date:** 2026-02-06

---

## Mission Statement

Clean up lint issues requiring manual review. Auto-fixable issues handled first via `ruff --fix`.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0707_LINT.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`

---

## PHASE 0: AUTO-FIX FIRST (MANDATORY)

Run these commands BEFORE validation:

```bash
# Auto-fix 708+ issues
ruff check src/ api/ --fix

# Format code
ruff format src/ api/

# Commit auto-fixes separately
git add -A && git commit -m "cleanup(0707): Auto-fix lint issues via ruff --fix"
```

---

## PHASE 0.5: VALIDATION RESEARCH

### Launch Validation Subagent

```
"Validate remaining lint issues after auto-fix.

```bash
# Current status
ruff check src/ api/ --statistics | head -20

# Specific counts
echo "ERA001 (commented code): $(ruff check src/ api/ --select ERA001 2>&1 | grep -c 'ERA001')"
echo "BLE001 (blind except): $(ruff check src/ api/ --select BLE001 2>&1 | grep -c 'BLE001')"
echo "B904 (raise without from): $(ruff check src/ api/ --select B904 2>&1 | grep -c 'B904')"
echo "T201 (print statements): $(ruff check src/ api/ --select T201 2>&1 | grep -c 'T201')"
```

REPORT: Remaining issues by category."
```

---

## PHASE 1: EXECUTION PRIORITY

1. **ERA001** - Delete commented-out code (highest value)
2. **BLE001** - Fix blind excepts (security)
3. **B904** - Add exception chaining (best practice)
4. **T201** - Replace prints with logging

---

## PHASE 2: VERIFICATION

```bash
# Final lint check
ruff check src/ api/ --statistics

# Tests pass
pytest tests/ -x -q

# App loads
python -c "from api.app import app; print('OK')"
```

---

## Communication

```json
{
  "id": "0707-lint-complete-001",
  "timestamp": "[ISO]",
  "from_handover": "0707-LINT",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Manual lint cleanup complete",
  "message": "[Summary of fixes]",
  "files_affected": [],
  "action_required": false,
  "context": {
    "auto_fixed": 708,
    "era001_removed": "[X]",
    "ble001_fixed": "[X]",
    "b904_fixed": "[X]",
    "t201_fixed": "[X]",
    "total_remaining": "[X]"
  }
}
```

---

## Success Criteria

- [ ] Auto-fix run and committed
- [ ] ERA001 < 10 remaining
- [ ] BLE001 = 0
- [ ] B904 = 0
- [ ] T201 < 5 (CLI only)
- [ ] Tests passing
- [ ] Final commit made
