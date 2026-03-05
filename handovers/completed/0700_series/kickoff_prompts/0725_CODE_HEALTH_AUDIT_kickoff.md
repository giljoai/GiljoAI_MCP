# 0725 Code Health Audit - Kickoff Prompt

```
You are the orchestrator for handover 0725 - Code Health Audit & Validation.

## Prerequisites
VERIFY FIRST: 0720 Complete Delinting must be FINISHED.
```bash
ruff check src/ api/
# Must show: All checks passed!
```

If 0720 is not complete, STOP and inform the user.

## Your Mission
RESEARCH ONLY - No code changes. Audit the codebase for:
1. Orphan/zombie code (files with no callers)
2. Deprecated markers (DEPRECATED, TODO, FIXME, HACK)
3. Legacy wrappers (alias = OldName patterns)
4. Naming convention violations
5. Dead code (unreachable, unused)
6. API/architecture inconsistencies
7. Test coverage gaps

## Read First
F:\GiljoAI_MCP\handovers\0725_CODE_HEALTH_AUDIT.md

## Research Team (Launch in Parallel)

### Agent 1: Orphan Hunter
```
Research orphan/zombie code in the codebase.

Tasks:
1. Run vulture for dead code: `vulture src/ api/ --min-confidence 80`
2. Check dependency graph: `cat handovers/0700_series/dependency_analysis.json`
3. Find files with 0 imports
4. Find functions with 0 callers

Report format:
- Orphan files: [list]
- Orphan functions: [list]
- Confidence level for each

DO NOT fix anything - research only.
```

### Agent 2: Deprecation Scanner
```
Research deprecated markers and legacy patterns.

Tasks:
1. grep -rn "DEPRECATED" src/ api/ --include="*.py"
2. grep -rn "TODO\|FIXME\|HACK\|XXX" src/ api/ --include="*.py"
3. Find alias patterns: `grep -rn "^[A-Za-z_]* = [A-Za-z_]*$" src/ api/`
4. Find single-line wrapper functions

Report format:
- DEPRECATED markers: [count, locations]
- TODO markers: [count, should be GitHub issues?]
- Legacy wrappers: [list with context]

DO NOT fix anything - research only.
```

### Agent 3: Naming Auditor
```
Research naming convention violations.

Python (PEP 8):
- Files: snake_case.py
- Functions/variables: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE

Frontend:
- Components: PascalCase.vue
- Functions: camelCase
- CSS: kebab-case

API:
- URLs: kebab-case
- JSON keys: snake_case

Tasks:
1. Find Python files with wrong naming
2. Find Vue components with wrong naming
3. Check API endpoint URL patterns
4. ruff check src/ api/ --select N --statistics

Report format:
- Python violations: [list]
- Frontend violations: [list]
- API violations: [list]

DO NOT fix anything - research only.
```

### Agent 4: Architecture Checker
```
Research API and architecture consistency.

Tasks:
1. Check response format consistency
2. Verify service layer patterns (returns objects not dicts)
3. Verify repository patterns (stateless, session param)
4. Check multi-tenant isolation in queries

Commands:
- grep -rn 'return {"' api/endpoints/ --include="*.py"
- grep -rn 'return {"' src/giljo_mcp/services/ --include="*.py"

Report format:
- Response inconsistencies: [list]
- Service pattern violations: [list]
- Repository pattern violations: [list]
- Multi-tenant gaps: [list]

DO NOT fix anything - research only.
```

### Agent 5: Coverage Analyzer
```
Research test coverage gaps.

Tasks:
1. Run coverage: pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=term-missing
2. Find production files without test files
3. Check for skipped tests and reasons
4. Identify untested critical paths

Report format:
- Overall coverage: [X]%
- Files with 0% coverage: [list]
- Missing test files: [list]
- Skipped tests: [count, reasons]

DO NOT fix anything - research only.
```

## After All Agents Complete

Compile the audit report using the template in the handover document.

Categorize findings:
- **Critical (Before v1.0):** Must fix
- **Important (Before v1.0):** Should fix
- **Minor (Post v1.0):** Nice to have

Create follow-up handover specs for any findings:
- 0726: Orphan Cleanup (if needed)
- 0727: Naming Fixes (if needed)
- 0728: API Standardization (if needed)

## Output
Final deliverable: `handovers/0725_AUDIT_REPORT.md`
```

---

Copy this prompt into a fresh session AFTER 0720 is complete.
