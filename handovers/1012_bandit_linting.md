# Handover 1012: Bandit Security Linting

## Overview
- **Ticket**: 1012
- **Parent**: 1000 (Greptile Remediation)
- **Status**: Pending
- **Risk**: ZERO
- **Tier**: 1 (Auto-Execute)
- **Effort**: 2 hours

## Mission
Add bandit security linting to pre-commit hooks to catch security issues early in the development workflow.

## Context
As part of the Greptile Remediation project (1000), we're adding comprehensive linting to improve code quality and security. Bandit is a security-focused linter that identifies common security issues in Python code before they reach production.

## Files to Modify
- `.pre-commit-config.yaml`
- `pyproject.toml` (bandit configuration)

## Pre-Implementation Research

### 1. Check Existing Pre-commit Setup
Verify if `.pre-commit-config.yaml` exists and review current hooks to ensure proper integration.

### 2. Review Current Codebase
Identify any existing security patterns or issues that bandit might flag:
- Password handling
- SQL query construction
- Cryptographic functions
- Shell command execution
- Assert usage in tests

### 3. Determine Severity Thresholds
Define which severity levels block commits vs. warn only.

## Implementation

### Step 1: Add Bandit to Pre-commit Config

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  # ... existing repos ...

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml", "-r", "src/", "api/"]
        exclude: tests/
```

### Step 2: Configure Bandit Settings

Add to `pyproject.toml`:

```toml
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv", "node_modules"]
skips = ["B101"]  # Skip assert warnings (used in tests)

[tool.bandit.assert_used]
skips = ["*_test.py", "*test*.py"]
```

## Bandit Severity Levels

| Level | Action | Description |
|-------|--------|-------------|
| **HIGH** | Must fix before commit | Critical security vulnerabilities |
| **MEDIUM** | Should fix, can be skipped with justification | Potential security issues |
| **LOW** | Review, fix if easy | Minor concerns or best practice violations |

## Common Findings to Expect

### B101: assert_used
- **Issue**: Assert statements used
- **Action**: Skip in tests (configured in pyproject.toml)
- **Justification**: Assert is appropriate for test validation

### B105: hardcoded_password_string
- **Issue**: Hardcoded password detected
- **Action**: Verify false positives (e.g., variable names containing "password")
- **Fix**: Ensure real passwords use environment variables or secrets management

### B608: hardcoded_sql_expressions
- **Issue**: SQL injection potential
- **Action**: Verify SQLAlchemy parameterization is used
- **Justification**: SQLAlchemy ORM prevents SQL injection by default

### B201: flask_debug_true
- **Issue**: Flask debug mode enabled
- **Action**: Ensure debug is controlled via environment variables

### B104: hardcoded_bind_all_interfaces
- **Issue**: Binding to 0.0.0.0
- **Action**: Verify this is intentional (see v3.0 network architecture)
- **Justification**: Documented in Admin Settings v3.0 (Handovers 0025-0029)

## Verification Steps

### 1. Install Pre-commit Hook
```bash
pre-commit install
```

### 2. Run Bandit on Entire Codebase
```bash
pre-commit run bandit --all-files
```

### 3. Review Findings
- Categorize by severity (HIGH/MEDIUM/LOW)
- Identify false positives
- Document legitimate skips

### 4. Fix Critical Issues
- Address all HIGH severity findings
- Fix MEDIUM severity where practical
- Document any skipped checks with justification

### 5. Update Configuration
Add skips to `pyproject.toml` for justified exceptions:

```toml
[tool.bandit]
exclude_dirs = ["tests", "venv", ".venv", "node_modules"]
skips = [
    "B101",  # assert_used - allowed in tests
    "B104",  # hardcoded_bind_all_interfaces - intentional per v3.0 architecture
]
```

### 6. Test Pre-commit Hook
```bash
# Make a trivial change
echo "# test" >> src/giljo_mcp/utils.py

# Commit and verify bandit runs
git add src/giljo_mcp/utils.py
git commit -m "test: Verify bandit pre-commit hook"
```

## Expected Timeline
- **Research & Setup**: 30 minutes
- **Initial Scan & Review**: 45 minutes
- **Fix Critical Issues**: 30 minutes
- **Documentation & Verification**: 15 minutes
- **Total**: ~2 hours

## Cascade Risk
**ZERO** - This handover only adds linting infrastructure. No code changes are required unless security issues are found, which would be addressed separately.

## Success Criteria
- ✅ Bandit runs automatically on every commit
- ✅ No HIGH or CRITICAL findings in codebase
- ✅ All skipped checks are documented with justification
- ✅ Configuration is committed and versioned
- ✅ Documentation updated in CLAUDE.md if needed

## Related Documentation
- [Pre-commit Documentation](https://pre-commit.com/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [GiljoAI Security Guidelines](docs/SECURITY.md) (if exists)

## Notes
- Bandit may flag intentional design decisions (e.g., 0.0.0.0 binding per v3.0 architecture)
- All skips must be justified and documented
- Consider adding bandit to CI/CD pipeline in future handovers
- This sets foundation for continuous security monitoring

---

**Status**: Ready for implementation
**Dependencies**: None
**Blockers**: None
