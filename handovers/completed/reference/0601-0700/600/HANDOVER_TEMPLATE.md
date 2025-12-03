# Handover 06XX: [Handover Title]

**Phase**: [0-6]
**Tool**: [CLI/CCW]
**Agent Type**: [specific-agent-name]
**Duration**: [X hours/days]
**Parallel Group**: [Group letter/number or "Sequential"]
**Depends On**: [Handover IDs or "None"]

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: [Brief 1-2 sentence summary of what came before, if dependencies exist]

**This Handover**: [2-3 sentences explaining what this handover accomplishes and why it matters]

---

## Specific Objectives

[Clear, measurable objectives for this handover. Use bullet points:]

- Objective 1: [Specific, measurable goal]
- Objective 2: [Specific, measurable goal]
- Objective 3: [Specific, measurable goal]

---

## Tasks

### Task 1: [Task Name]
**What**: [What needs to be done]
**Why**: [Why this task is important]
**Files**: [Specific file paths to read/modify]
**Commands**: [Specific commands to run, if applicable]

**Example**:
```python
# Example code pattern to follow (if applicable)
```

### Task 2: [Task Name]
**What**: [What needs to be done]
**Why**: [Why this task is important]
**Files**: [Specific file paths to read/modify]
**Commands**: [Specific commands to run, if applicable]

### Task 3: [Task Name]
[Continue for all tasks...]

---

## Success Criteria

- [ ] **Code**: [Specific code deliverable - e.g., "ProductService has create_product() method"]
- [ ] **Tests**: [Specific test requirement - e.g., "Unit tests pass with 80%+ coverage"]
- [ ] **Coverage**: [Coverage target - e.g., "≥ 80% coverage on ProductService"]
- [ ] **Multi-Tenant**: [If applicable - "Tenant isolation verified (User A cannot access User B's data)"]
- [ ] **Documentation**: [Doc update requirement - e.g., "CLAUDE.md updated with Project 600 status"]
- [ ] **Commit**: [Commit message requirement - e.g., "Commit created: 'feat: Implement ProductService validation'"]
- [ ] **Validation**: [Validation requirement - e.g., "Fresh install completes in <5 min"]

---

## Validation Steps

**How to verify this handover is complete:**

```bash
# Step 1: Run specific tests
pytest tests/unit/test_X.py -v --cov=src/giljo_mcp/X --cov-report=term-missing

# Step 2: Verify coverage target
# Expected: ≥ 80% coverage, all tests pass

# Step 3: Run integration tests (if applicable)
pytest tests/integration/test_X.py -v

# Step 4: Manual validation (if applicable)
# Example: Create product, verify in database

# Step 5: Performance check (if applicable)
# Example: Benchmark fresh install time
```

**Expected Output**: [Describe what success looks like - test output, coverage percentage, etc.]

---

## Deliverables

### Code
- **Created**: [List new files created, if any]
  - `path/to/new_file.py` - [Brief description]
- **Modified**: [List files modified]
  - `path/to/existing_file.py` - [What was changed]

### Tests
- **Unit Tests**: [List test files created/modified]
  - `tests/unit/test_X.py` - [What tests cover]
- **Integration Tests**: [List integration test files, if applicable]
  - `tests/integration/test_X.py` - [What tests cover]
- **E2E Tests**: [List E2E test files, if applicable]
  - `tests/e2e/test_X.py` - [What workflows tested]

### Documentation
- **Updated**: [List documentation updated]
  - `docs/X.md` - [What was updated]
- **Created**: [List new documentation]
  - `handovers/600/06XX_completion_report.md` - [Handover completion summary]

### Git Commit
- **Message**: [Example commit message]
  - Example: `feat: Implement ProductService validation (Handover 06XX)`
- **Branch**: [For CCW: branch name; For CLI: "master"]

---

## Dependencies

### Requires (Before Starting)
[What must exist/be complete before starting this handover:]

- **Handover 06XX**: [What was delivered by dependency handover]
- **Files**: [Specific files that must exist]
- **Database**: [Database state required - e.g., "All 31 tables created"]
- **Environment**: [Environment setup required - e.g., "PostgreSQL 14+ installed"]

### Blocks (What's Waiting)
[What handovers are blocked until this one completes:]

- **Handover 06YY**: [Why it depends on this handover]
- **Handover 06ZZ**: [Why it depends on this handover]

---

## Notes for Agent

### CLI (Local) Execution
[If this is a CLI handover, specific notes for local execution:]

- You have database access - use `pytest` fixtures with real DB
- Run migrations if needed: `alembic upgrade head`
- Commit directly to master after validation

### CCW (Cloud) Execution
[If this is a CCW handover, specific notes for cloud execution:]

- Create branch: `06XX-feature-name`
- Mock database if needed (no real DB access)
- Create PR with test results in description
- Include coverage report snippet in PR

### Common Patterns
[Reference to common patterns from AGENT_REFERENCE_GUIDE.md:]

- Service pattern: See AGENT_REFERENCE_GUIDE.md, section "Common Patterns - Service Pattern"
- API pattern: See AGENT_REFERENCE_GUIDE.md, section "Common Patterns - API Endpoint Pattern"
- Test pattern: See AGENT_REFERENCE_GUIDE.md, section "Common Patterns - Test Pattern"

### Quality Checklist
Before marking this handover complete:

- [ ] Ruff + Black compliant (no linting errors)
- [ ] Full type hints (mypy clean)
- [ ] Comprehensive error handling
- [ ] Multi-tenant isolation verified (if applicable)
- [ ] All tests pass (100% pass rate)
- [ ] Coverage target met (80%+ or as specified)
- [ ] Documentation updated (if applicable)
- [ ] Commit message follows conventions

---

## Completion Report Template

**Create this file after handover complete**: `handovers/600/06XX_completion_report.md`

```markdown
# Handover 06XX Completion Report

**Date**: YYYY-MM-DD
**Agent**: [agent-type]
**Duration**: [Actual time taken]
**Status**: Complete

## Objectives Met
- [x] Objective 1
- [x] Objective 2
- [x] Objective 3

## Deliverables
- Code: [Files created/modified]
- Tests: [Test coverage achieved]
- Docs: [Documentation updated]

## Test Results
[Paste pytest output or summary]

Coverage: X%
Tests Passing: Y/Y (100%)

## Challenges
[Any issues encountered and how resolved]

## Next Steps
- Handover 06YY can now proceed (dependency resolved)
```

---

**Document Control**:
- **Template Version**: 1.0
- **Created**: 2025-11-14
- **Use**: Copy this template when creating individual handover files (0600-0631)
