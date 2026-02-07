# Handover 0725: Code Health Audit & Validation

**Series:** 0700 Code Cleanup Series (Final Validation)
**Risk Level:** LOW (Research Only)
**Estimated Effort:** 4-6 hours (research team)
**Date:** 2026-02-07
**Status:** READY AFTER 0720 COMPLETE
**Prerequisites:** 0720 Complete Delinting MUST be finished first

---

## Mission Statement

Validate that the 0700 cleanup series achieved its goals. Research-only audit to identify any remaining:
- Orphan/zombie code (files with no callers)
- Deprecated markers (DEPRECATED, TODO, FIXME, HACK)
- Legacy wrappers/bridges (alias patterns like `new_func = old_func`)
- Naming inconsistencies (mixed conventions)
- Dead code (unreachable, unused)
- Unprofessional patterns

**Output:** Audit report with findings. NO CODE CHANGES in this handover.

---

## Research Team Structure

| Agent | Focus |
|-------|-------|
| Orphan Hunter | Files/functions with no callers |
| Deprecation Scanner | DEPRECATED, TODO, legacy wrappers |
| Naming Auditor | Convention violations |
| Architecture Checker | API/service consistency |
| Coverage Analyzer | Test coverage gaps |

---

## Phase 1: Orphan & Zombie Code Detection

### Commands
```bash
# Dead code detection
vulture src/ api/ --min-confidence 80

# Use existing dependency graph
cat handovers/0700_series/dependency_analysis.json | jq '.orphan_modules'
```

### Check For
- Python files never imported
- Vue components never used
- Functions with 0 callers
- Test files for deleted modules

---

## Phase 2: Deprecation & Legacy Pattern Scan

### Commands
```bash
# Markers
grep -rn "DEPRECATED\|TODO\|FIXME\|HACK\|XXX" src/ api/ --include="*.py"

# Alias patterns (legacy wrappers)
grep -rn "^[A-Za-z_]* = [A-Za-z_]*$" src/ api/ --include="*.py"
```

### Check For
- DEPRECATED markers in production code
- TODOs that should be GitHub issues
- Wrapper patterns like `old_func = new_func`

---

## Phase 3: Naming Convention Audit

### Standards

| Context | Element | Convention |
|---------|---------|------------|
| Python | Files | snake_case.py |
| Python | Functions | snake_case |
| Python | Classes | PascalCase |
| Python | Constants | UPPER_SNAKE |
| Vue | Components | PascalCase.vue |
| JS | Functions | camelCase |
| API | URLs | kebab-case |
| API | JSON keys | snake_case |

### Commands
```bash
# Python naming issues
ruff check src/ api/ --select N --statistics

# Find files with wrong naming
find src/ api/ -name "*.py" | grep -E "[A-Z]"
find frontend/src/components -name "*.vue" | xargs basename
```

---

## Phase 4: API & Architecture Consistency

### Check For
- Response format consistency (all use same pattern)
- Service layer returns objects, not dicts
- Repository layer is stateless
- Multi-tenant isolation in all queries

### Commands
```bash
# Dict returns in services (should be objects)
grep -rn 'return {"' src/giljo_mcp/services/ --include="*.py"

# Check endpoint patterns
grep -rn "@router\." api/endpoints/ --include="*.py"
```

---

## Phase 5: Test Coverage Validation

### Commands
```bash
# Coverage report
pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=term-missing

# Find untested files
for f in $(find src/giljo_mcp -name "*.py"); do
  base=$(basename "$f" .py)
  find tests/ -name "*${base}*" -type f | grep -q . || echo "NO TEST: $f"
done
```

### Targets
- >80% overall coverage
- All services have unit tests
- All endpoints have integration tests

---

## Audit Report Template

Output file: `handovers/0725_AUDIT_REPORT.md`

```markdown
# 0725 Code Health Audit Report

**Date:** [DATE]
**Status:** [PASS/FAIL/PARTIAL]

## Findings Summary

| Category | Status | Issues |
|----------|--------|--------|
| Orphan Code | [CLEAN/ISSUES] | [count] |
| Deprecated Markers | [CLEAN/ISSUES] | [count] |
| Naming Conventions | [CLEAN/ISSUES] | [count] |
| Dead Code | [CLEAN/ISSUES] | [count] |
| API Consistency | [CLEAN/ISSUES] | [count] |
| Test Coverage | [X]% | [gaps] |

## Recommendations

### Before v1.0
1. [Critical issues]

### Post v1.0
1. [Minor issues]

## Follow-up Handovers Needed
- 0726: [if orphans found]
- 0727: [if naming issues]
- 0728: [if API issues]
```

---

## Success Criteria

- [ ] All 5 phases researched
- [ ] Audit report generated
- [ ] Findings categorized by severity
- [ ] Follow-up handovers created if needed
- [ ] NO code changes made (research only)
