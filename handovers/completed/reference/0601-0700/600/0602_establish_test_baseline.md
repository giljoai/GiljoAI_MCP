# Handover 0602: Establish Test Baseline

**Phase**: 0
**Tool**: CLI (Local)
**Agent Type**: tdd-implementor
**Duration**: 6 hours
**Parallel Group**: Sequential
**Depends On**: 0601

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Handover 0600 audited 456 test files and categorized them. Handover 0601 fixed migration order and validated fresh install works. Now we need to establish the current test suite baseline.

**This Handover**: Run full test suite, categorize failures by root cause (Agent model removal, service changes, integration broken), establish coverage baseline, and create prioritized fix plan for Phase 5.

---

## Specific Objectives

- **Objective 1**: Run full test suite and capture all output (pass/fail/skip counts)
- **Objective 2**: Categorize test failures by root cause (refactoring impacts)
- **Objective 3**: Run coverage analysis and establish baseline percentage per module
- **Objective 4**: Document baseline metrics (X passing, Y failing, Z% coverage)
- **Objective 5**: Create prioritized fix plan for 50+ most critical test failures
- **Objective 6**: Identify quick wins vs complex fixes

---

## Tasks

### Task 1: Run Full Test Suite
**What**: Execute complete test suite with verbose output, capture all results
**Why**: Establish truth baseline - know exactly what works/breaks post-refactoring
**Commands**:
```bash
cd /f/GiljoAI_MCP

# Run full test suite with detailed output
pytest tests/ -v --tb=short --no-cov > handovers/600/0602_full_test_run.txt 2>&1

# Also run without -v to get summary
pytest tests/ --tb=line > handovers/600/0602_test_summary.txt 2>&1
```

**What to Capture**:
- Total tests discovered
- Tests passed
- Tests failed
- Tests skipped
- Execution time
- Failure patterns (common error messages)

### Task 2: Categorize Test Failures by Root Cause
**What**: Analyze test failures and group by underlying issue
**Why**: Understand systematic issues from refactoring (Handovers 0120-0130)
**Files**:
- `handovers/600/0602_full_test_run.txt` - Analyze failure messages
- Test files causing failures - Read to understand root cause

**Expected Failure Categories**:
1. **Agent Model Removal** (HIGH): Tests importing `from models import Agent` (removed in refactoring)
2. **Service Changes** (MEDIUM): Tests expecting old ProductService interface
3. **Integration Broken** (MEDIUM): Tests assuming monolithic architecture
4. **Import Errors** (LOW): Module reorganization broke imports
5. **Fixture Issues** (LOW): Database fixtures need updates
6. **Deprecated Code** (LOW): Tests for removed features

**Deliverable**: `handovers/600/0602_test_failures.json`:
```json
{
  "agent_model_removed": {
    "count": 47,
    "tests": ["tests/unit/test_agent_job_manager.py::test_create_job", ...],
    "fix_effort": "HIGH",
    "fix_strategy": "Replace Agent model with AgentJob or remove if obsolete"
  },
  "service_interface_changed": {
    "count": 32,
    "tests": ["tests/unit/test_product_service.py::test_create_product", ...],
    "fix_effort": "MEDIUM",
    "fix_strategy": "Update test to use new service method signatures"
  },
  ...
}
```

### Task 3: Run Coverage Analysis
**What**: Execute pytest with coverage reporting for all modules
**Why**: Establish coverage baseline to measure improvement in Phase 5
**Commands**:
```bash
cd /f/GiljoAI_MCP

# Run coverage on all source code
pytest tests/ --cov=src/giljo_mcp --cov-report=html --cov-report=term-missing > handovers/600/0602_coverage_run.txt 2>&1

# Coverage report will be in htmlcov/ directory (gitignored)
# Extract summary for documentation
grep "TOTAL" handovers/600/0602_coverage_run.txt
```

**What to Capture**:
- Overall coverage percentage
- Coverage per module:
  - Services (product_service.py, project_service.py, etc.)
  - Models (models.py)
  - MCP Tools (tools/*.py)
  - API Endpoints (api/endpoints/*.py)
  - Utilities (utils/*.py)

### Task 4: Document Baseline Metrics
**What**: Create comprehensive baseline report with all metrics
**Why**: Provide clear "before" picture for Phase 5 improvements
**Files**: `handovers/600/0602_test_baseline.md`

**Report Structure**:
```markdown
# Test Suite Baseline Report (Handover 0602)

## Executive Summary
- Total tests: 456
- Passing: 280 (61.4%)
- Failing: 150 (32.9%)
- Skipped: 26 (5.7%)
- Execution time: 8m 32s

## Coverage Baseline
- Overall: 58.3%
- Services: 62.1%
- Models: 71.4%
- MCP Tools: 51.2%
- API Endpoints: 43.8%

## Failure Analysis
[Summary by category from Task 2]

## Fix Plan
[Prioritized list from Task 5]
```

### Task 5: Create Prioritized Fix Plan
**What**: Identify 50+ most critical test failures and create fix roadmap
**Why**: Guide Phase 5 work - fix highest impact issues first
**Files**: `handovers/600/0602_test_baseline.md` - Section "Fix Plan"

**Prioritization Criteria**:
1. **P0 Critical**: Tests blocking core functionality (product/project creation)
2. **P1 High**: Tests for primary features (agent jobs, orchestration)
3. **P2 Medium**: Tests for secondary features (templates, settings)
4. **P3 Low**: Tests for edge cases or deprecated features

**Fix Plan Format**:
```markdown
## Fix Plan (50 Critical Tests)

### P0 Critical (15 tests)
1. `tests/unit/test_product_service.py::test_create_product` - Agent model import error
   - **Issue**: Importing removed Agent model
   - **Fix**: Remove Agent import, use AgentJob if needed
   - **Effort**: 15 min

2. `tests/integration/test_product_workflow.py::test_full_workflow` - Service interface changed
   - **Issue**: ProductService.create() expects different args
   - **Fix**: Update test to use new create_product() signature
   - **Effort**: 30 min

[Continue for all 50 tests...]

### P1 High (20 tests)
[...]

### P2 Medium (10 tests)
[...]

### P3 Low (5 tests)
[...]
```

### Task 6: Identify Quick Wins
**What**: Find 10-15 tests that can be fixed in <30 min each
**Why**: Build momentum in Phase 5, show rapid progress
**Files**: `handovers/600/0602_test_baseline.md` - Section "Quick Wins"

**Quick Win Criteria**:
- Simple import fix (change `from models import X` to `from models import Y`)
- Simple signature update (add/remove parameter)
- Fixture rename (old fixture name → new fixture name)

**Example Quick Wins**:
```markdown
## Quick Wins (15 tests, <5 hours total)

1. `tests/unit/test_utils.py::test_validate_tenant_key` - Import error
   - **Fix**: Change `from models import Tenant` to `from models import Product`
   - **Effort**: 5 min

2. `tests/api/test_health.py::test_health_endpoint` - Endpoint moved
   - **Fix**: Update URL from `/health` to `/api/v1/health`
   - **Effort**: 10 min

[...]
```

### Task 7: Run Focused Test Subset (Sanity Check)
**What**: Run tests for critical paths only to verify some tests DO pass
**Why**: Ensure test infrastructure works, not ALL tests broken
**Commands**:
```bash
# Run just unit tests for services (should have some passing)
pytest tests/unit/test_product_service.py -v

# Run just API health endpoint (should pass)
pytest tests/api/test_health.py -v

# Run authentication tests (should pass)
pytest tests/integration/test_auth_endpoints.py -v
```

**Document**: Which critical test modules DO pass (build confidence)

---

## Success Criteria

- [ ] **Full Test Suite Run**: Complete test suite executed, all output captured
- [ ] **Failure Categorization**: Test failures grouped by root cause (6+ categories)
- [ ] **Coverage Baseline**: Coverage metrics documented per module
- [ ] **Baseline Report**: Comprehensive baseline report created
- [ ] **Fix Plan**: 50+ critical tests identified with fix strategy
- [ ] **Quick Wins**: 10-15 quick win tests identified (<30 min each)
- [ ] **Commit**: Baseline report and artifacts committed

---

## Validation Steps

**How to verify this handover is complete:**

```bash
# Step 1: Verify test run output exists
test -f handovers/600/0602_full_test_run.txt
test -f handovers/600/0602_test_summary.txt
grep "passed\|failed\|skipped" handovers/600/0602_test_summary.txt

# Step 2: Verify coverage output exists
test -f handovers/600/0602_coverage_run.txt
grep "TOTAL" handovers/600/0602_coverage_run.txt

# Step 3: Verify failure categorization JSON
test -f handovers/600/0602_test_failures.json
python -c "import json; data=json.load(open('handovers/600/0602_test_failures.json')); print(f'Categories: {len(data)}')"

# Step 4: Verify baseline report exists and is comprehensive
test -f handovers/600/0602_test_baseline.md
grep -c "Fix Plan" handovers/600/0602_test_baseline.md  # Should be 1
grep -c "Quick Wins" handovers/600/0602_test_baseline.md  # Should be 1
grep -c "Coverage Baseline" handovers/600/0602_test_baseline.md  # Should be 1

# Step 5: Manual review of baseline report
# - Does it have clear metrics (X passing, Y failing, Z% coverage)?
# - Is fix plan prioritized (P0/P1/P2/P3)?
# - Are quick wins identified (10-15 tests)?
```

**Expected Output**:
- Full test suite run captured (~280 passing, ~150 failing based on refactoring impact)
- Coverage baseline ~55-65% overall (dropped from pre-refactoring due to new service layer)
- Failure categories clearly defined (Agent model, service changes, etc.)
- Fix plan with 50+ tests prioritized by impact
- Quick wins identified for rapid progress

---

## Deliverables

### Code
- **Created**: None (analysis task only)

### Documentation
- **Created**:
  - `handovers/600/0602_test_baseline.md` - Comprehensive baseline report (3,000+ words)
  - `handovers/600/0602_full_test_run.txt` - Complete test suite output (for reference)
  - `handovers/600/0602_test_summary.txt` - Test suite summary
  - `handovers/600/0602_coverage_run.txt` - Coverage analysis output
  - `handovers/600/0602_test_failures.json` - Failure categorization

### Git Commit
- **Message**: `test: Establish baseline metrics and failure analysis (Handover 0602)`
- **Branch**: master (CLI execution)

---

## Dependencies

### Requires (Before Starting)
- **Handover 0600**: Test file categorization complete
- **Handover 0601**: Fresh install working (database migrations fixed)
- **Environment**: pytest installed, coverage plugin installed
- **Database**: PostgreSQL running (for integration tests)

### Blocks (What's Waiting)
- **Handover 0603-0608** (Phase 1): Service validation depends on understanding current test state
- **Handover 0624-0626** (Phase 5): Test suite completion depends on fix plan

---

## Notes for Agent

### CLI (Local) Execution
This is a CLI handover requiring local execution:

- You have database access - integration tests will use real DB
- Run full pytest suite (may take 5-15 minutes)
- Generate HTML coverage report (htmlcov/ is gitignored, but analyze it)
- Commit baseline report to master after analysis

### Test Execution Strategy
Given 456 test files:

- Run full suite ONCE to establish baseline
- Don't try to fix tests in this handover (that's Phase 5)
- Focus on ANALYSIS and CATEGORIZATION
- Document patterns (not individual test details)

### Common Patterns
Reference from AGENT_REFERENCE_GUIDE.md:

- Testing commands: See "Testing Commands" section
- Coverage targets: See "Quality Standards" section (80%+ goal)
- Test patterns: See "Common Patterns - Test Pattern" section

### Expected Failure Patterns
From Handovers 0120-0130 refactoring:

1. **Agent model removed**: ~40-50 tests import `from models import Agent`
   - Fix: Remove imports or replace with AgentJob

2. **Service interfaces changed**: ~30-40 tests use old method signatures
   - Fix: Update to new ProductService.create_product() etc.

3. **Integration tests broken**: ~20-30 tests assume monolithic architecture
   - Fix: Update to use service layer pattern

4. **Import reorganization**: ~10-20 tests have stale imports
   - Fix: Update import paths

### Quality Checklist
Before marking this handover complete:

- [ ] Full test suite executed (all 456 test files)
- [ ] Coverage report generated (HTML + term output)
- [ ] Baseline metrics accurate (verified counts)
- [ ] Failure categories comprehensive (6+ root causes)
- [ ] Fix plan prioritized by impact (P0/P1/P2/P3)
- [ ] Quick wins identified (10-15 tests, <30 min each)
- [ ] Baseline report committed
- [ ] Commit message follows convention

---

**Document Control**:
- **Handover**: 0602
- **Created**: 2025-11-14
- **Status**: Ready for execution
