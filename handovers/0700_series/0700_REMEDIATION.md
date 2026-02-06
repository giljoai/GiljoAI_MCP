# Handover 0700-REMEDIATION: Fix Gaps in 0700a/h/i

**Series:** 0700 Code Cleanup Series
**Risk Level:** LOW
**Estimated Effort:** 1-2 hours
**Date:** 2026-02-06

---

## Mission Statement

Fix gaps identified in audit of completed handovers 0700a, 0700h, and 0700i. These are remnants that should have been caught during original execution.

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY)

**Before executing ANY changes, you MUST run validation research.**

### Step 1: Launch Validation Subagent

Use a deep-researcher subagent to verify the scope is complete:

```
Validate the scope for 0700-REMEDIATION. Check if we're missing anything.

VALIDATE THESE CLAIMED GAPS:
1. 0700a - Light mode remnants in App.vue and settings.js
2. 0700h - DEPRECATED markers (claimed 2 remain)
3. 0700i - instance_number in test fixtures

RUN THESE VERIFICATION COMMANDS:
```bash
# Light mode check - find ALL remnants
grep -rn "light" frontend/src/ --include="*.vue" --include="*.js" --include="*.css" | grep -v node_modules | grep -v ".spec.js"

# DEPRECATED check - count ALL markers
grep -rn "DEPRECATED" src/ api/ --include="*.py" | wc -l

# instance_number check - find ALL references
grep -rn "instance_number" . --include="*.py" --include="*.js" --include="*.vue" --include="*.ts" | grep -v node_modules
```

REPORT:
1. Are the claimed gaps accurate?
2. Are there ADDITIONAL gaps not listed?
3. What is the COMPLETE scope?
```

### Step 2: Await Validation Results

- If validation finds **additional gaps**: Add them to scope before proceeding
- If validation finds **claimed gaps are wrong**: Correct the scope
- If validation **confirms scope**: Proceed to Phase 1

### Step 3: Document Validation

Write a brief validation summary before executing:
```
VALIDATION COMPLETE:
- Light mode gaps: [CONFIRMED/EXPANDED/CORRECTED]
- DEPRECATED gaps: [CONFIRMED/EXPANDED/CORRECTED]
- instance_number gaps: [CONFIRMED/EXPANDED/CORRECTED]
- Additional findings: [LIST OR NONE]
```

---

## Audit Findings Summary (TO BE VALIDATED)

| Handover | Gap | Severity |
|----------|-----|----------|
| 0700a | Light mode CSS/JS remnants | MEDIUM |
| 0700h | 2 DEPRECATED markers remain | LOW |
| 0700i | Test fixtures still have instance_number | MEDIUM |

---

## PHASE 1: EXECUTION

**Only proceed after Phase 0 validation is complete.**

### Task 1: Fix 0700a Light Mode Remnants

**Gap:** CSS and JS light mode remnants still exist

**File 1:** `frontend/src/App.vue`
- Lines 47-49: Delete `[data-theme='light']` CSS block

```vue
<!-- DELETE these lines (47-49): -->
[data-theme='light'] {
  color-scheme: light;
}
```

**File 2:** `frontend/src/stores/settings.js`
- Line 49: Remove `|| themePreference === 'light'` check
- Line 65: Remove `|| currentThemePreference === 'light'` check

**File 3:** `frontend/src/components/projects/TESTING_SUMMARY.md`
- Remove any light mode testing references

### Task 2: Fix 0700h DEPRECATED Markers

**Gap:** 2 DEPRECATED markers remain (should be 0)

**File 1:** `src/giljo_mcp/thin_prompt_generator.py`
- Line 1066: Remove deprecated `instance_number` parameter documentation

**File 2:** `src/giljo_mcp/models/product_memory_entry.py`
- Line 6: This is ACCEPTABLE - historical documentation comment about JSONB replacement
- **Action:** Keep as-is (documentation, not code)

### Task 3: Fix 0700i Test Fixture Remnants

**Gap:** Test fixtures still contain instance_number data

**Files to fix:**
- `frontend/src/components/projects/JobsTab.spec.js` (line 102)
- `frontend/src/components/projects/JobsTab.integration.spec.js` (line 75)
- `frontend/src/components/projects/__tests__/MessageStream.spec.js` (lines 44, 55, 72, 509)
- `frontend/src/components/projects/__tests__/MessageInput.agent-id.spec.js` (lines 36, 41, 101)
- `frontend/src/components/projects/__tests__/AgentDisplayName.spec.js` (line 144)

**Action:** Remove `instance_number` field from all mock data objects

**File:** `api/endpoints/agent_jobs/operations.py`
- Line 303: Delete commented-out ORDER BY line

---

## PHASE 2: VERIFICATION

```bash
# 0700a: No light mode remnants
grep -rn "data-theme.*light" frontend/src/ --include="*.vue" --include="*.js" | grep -v spec | wc -l
# Expected: 0

# 0700h: DEPRECATED markers (allow 1 for documentation)
grep -rn "DEPRECATED" src/ --include="*.py" | wc -l
# Expected: 1 (product_memory_entry.py documentation only)

# 0700i: No instance_number in test fixtures
grep -rn "instance_number" frontend/src/ --include="*.spec.js" | wc -l
# Expected: 0

# 0700i: No commented instance_number code
grep -rn "instance_number" api/ --include="*.py" | grep "#" | wc -l
# Expected: 0
```

---

## Success Criteria

- [ ] **Phase 0 validation completed and documented**
- [ ] Light mode CSS deleted from App.vue
- [ ] Light mode checks removed from settings.js
- [ ] DEPRECATED instance_number removed from thin_prompt_generator.py
- [ ] All test fixtures updated to remove instance_number
- [ ] Commented code in operations.py deleted
- [ ] Verification commands pass
- [ ] comms_log.json entry written
- [ ] Changes committed

---

## Commit Message Template

```
cleanup(0700-remediation): Fix gaps from 0700a/h/i audit

Remediation of gaps found during comprehensive audit:

0700a fixes:
- Deleted [data-theme='light'] CSS block from App.vue
- Removed light mode checks from settings.js

0700h fixes:
- Removed deprecated instance_number documentation

0700i fixes:
- Removed instance_number from all test fixtures
- Deleted commented ORDER BY code in operations.py

Validation: [SCOPE CONFIRMED/EXPANDED by research agent]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
