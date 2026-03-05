# Kickoff: Handover 0700-REMEDIATION

**Series:** 0700 Code Cleanup Series
**Risk Level:** LOW
**Estimated Effort:** 1-2 hours
**Date:** 2026-02-06

---

## Mission Statement

Fix gaps identified in audit of completed handovers 0700a, 0700h, and 0700i.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0700_REMEDIATION.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY - DO THIS FIRST)

**YOU MUST validate scope before executing ANY changes.**

### Launch Validation Subagent

```
Use deep-researcher subagent with this prompt:

"Validate the scope for 0700-REMEDIATION. Verify claimed gaps and find any additional ones.

RUN THESE COMMANDS:
```bash
# Light mode - find ALL remnants (not just claimed files)
grep -rn "light" frontend/src/ --include="*.vue" --include="*.js" --include="*.css" | grep -v node_modules | grep -v ".spec.js"

# DEPRECATED - count ALL markers
grep -rn "DEPRECATED" src/ api/ --include="*.py"

# instance_number - find ALL references
grep -rn "instance_number" . --include="*.py" --include="*.js" --include="*.vue" | grep -v node_modules
```

CLAIMED GAPS TO VALIDATE:
1. App.vue lines 47-49 have [data-theme='light']
2. settings.js has light mode checks
3. thin_prompt_generator.py has DEPRECATED instance_number
4. Multiple .spec.js files have instance_number in fixtures
5. operations.py has commented instance_number code

REPORT:
- Which claims are ACCURATE?
- Which claims are WRONG or OUTDATED?
- What ADDITIONAL gaps exist?
- What is the COMPLETE scope?"
```

### Document Validation Results

Before proceeding to execution, write:
```
## VALIDATION RESULTS
- Light mode gaps: [CONFIRMED X files / EXPANDED to Y files / NOT FOUND]
- DEPRECATED gaps: [COUNT found, LIST files]
- instance_number gaps: [COUNT found, LIST files]
- Additional findings: [LIST]
- Scope adjustment: [NONE / EXPANDED / REDUCED]
```

---

## PHASE 1: EXECUTION

**Only after Phase 0 is complete.**

### Task 1: Light Mode Remnants (0700a)

Delete/modify based on validation findings:
- `frontend/src/App.vue` - Delete light mode CSS
- `frontend/src/stores/settings.js` - Remove light mode checks
- Any additional files found in validation

### Task 2: DEPRECATED Markers (0700h)

Remove based on validation findings:
- `src/giljo_mcp/thin_prompt_generator.py` - Remove deprecated param docs
- Any additional files found in validation
- **KEEP** documentation comments (like product_memory_entry.py line 6)

### Task 3: instance_number Fixtures (0700i)

Remove from all test fixtures found in validation:
- All `.spec.js` files with instance_number in mock data
- `api/endpoints/agent_jobs/operations.py` - Delete commented code

---

## PHASE 2: VERIFICATION

```bash
# Light mode gone
grep -rn "data-theme.*light\|themePreference.*light" frontend/src/ --include="*.vue" --include="*.js" | grep -v spec | wc -l
# Expected: 0

# DEPRECATED markers minimal
grep -rn "DEPRECATED" src/ --include="*.py" | wc -l
# Expected: 1 or 0

# instance_number gone from tests
grep -rn "instance_number" frontend/src/ --include="*.spec.js" | wc -l
# Expected: 0

# instance_number gone from backend
grep -rn "instance_number" api/ src/ --include="*.py" | grep -v "# Historical\|# Documentation" | wc -l
# Expected: 0
```

---

## Communication

Write completion entry to `handovers/0700_series/comms_log.json`:

```json
{
  "id": "0700-remediation-complete-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0700-REMEDIATION",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "0700a/h/i gaps remediated",
  "message": "[Summary including validation findings]",
  "files_affected": ["[list]"],
  "action_required": false,
  "context": {
    "validation_phase": {
      "claimed_gaps": "[X]",
      "confirmed_gaps": "[Y]",
      "additional_gaps_found": "[Z]",
      "scope_adjustment": "[NONE/EXPANDED/REDUCED]"
    },
    "execution_phase": {
      "light_mode_files_fixed": "[count]",
      "deprecated_markers_removed": "[count]",
      "test_fixtures_updated": "[count]"
    }
  }
}
```

---

## Success Criteria

- [ ] **Phase 0: Validation subagent launched and findings documented**
- [ ] **Phase 1: All validated gaps fixed**
- [ ] **Phase 2: Verification commands pass**
- [ ] comms_log.json entry written with validation context
- [ ] Changes committed

---

## Commit Message Template

```
cleanup(0700-remediation): Fix validated gaps from 0700a/h/i

Validation phase found [X] gaps ([Y] claimed, [Z] additional).

0700a fixes:
- [List light mode changes]

0700h fixes:
- [List DEPRECATED changes]

0700i fixes:
- [List instance_number changes]

```
