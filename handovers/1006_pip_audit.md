# Handover 1006: Add pip-audit to CI/CD

**Date**: 2025-12-18
**Ticket**: 1006
**Parent**: 1000 (Greptile Remediation)
**Status**: Pending
**Risk**: ZERO
**Tier**: 1 (Auto-Execute)
**Effort**: 2 hours

## Overview

Add vulnerability scanning to GitHub Actions using pip-audit to detect known security vulnerabilities in Python dependencies as part of the continuous integration pipeline.

## Mission

Integrate pip-audit into the existing GitHub Actions workflow to automatically scan for security vulnerabilities in Python dependencies on every push and pull request.

## Files to Modify

- `.github/workflows/ci.yml` - Add pip-audit step to existing CI workflow

## Pre-Implementation Research

### Current CI Workflow Structure
1. Examine `.github/workflows/ci.yml` to understand current workflow steps
2. Identify dependency installation step location
3. Determine optimal placement for security audit (after dependency installation, before tests)

### pip-audit Compatibility
1. Verify pip-audit works with Python 3.11+ (project requirement)
2. Confirm compatibility with project's dependency management (requirements.txt or pyproject.toml)
3. Check for any known issues with FastAPI/SQLAlchemy/other core dependencies

### Workflow Placement Strategy
**Recommended Order**:
1. Checkout code
2. Set up Python
3. Install dependencies
4. **Run pip-audit** ← New step
5. Run linters (ruff, black)
6. Run tests (pytest)

**Rationale**: Fail fast on security issues before running expensive test suites.

## Implementation

### Option A: Strict Mode (Recommended for Production)

Add this step after dependency installation in `.github/workflows/ci.yml`:

```yaml
- name: Install pip-audit
  run: pip install pip-audit

- name: Run security audit
  run: pip-audit --strict --desc on
```

**Behavior**:
- `--strict`: CI fails immediately if any vulnerabilities are found
- `--desc on`: Shows detailed vulnerability descriptions
- Exit code 1 on vulnerabilities → pipeline fails

**Pros**: Enforces zero-tolerance for known vulnerabilities
**Cons**: May block deployments if vulnerabilities exist in transitive dependencies

---

### Option B: Warning Mode (Recommended for Initial Rollout)

```yaml
- name: Install pip-audit
  run: pip install pip-audit

- name: Run security audit
  run: pip-audit --desc on || true
  continue-on-error: true
```

**Behavior**:
- CI continues even if vulnerabilities are found
- Shows warnings in workflow output
- Does not block deployments

**Pros**: Provides visibility without disrupting current workflow
**Cons**: Does not enforce remediation

---

### Option C: Fail on High/Critical Only (Balanced Approach)

```yaml
- name: Install pip-audit
  run: pip install pip-audit

- name: Run security audit (High/Critical only)
  run: pip-audit --severity high critical --strict --desc on
```

**Behavior**:
- Only fails CI for high and critical severity vulnerabilities
- Allows low/medium vulnerabilities to pass with warnings

**Pros**: Balances security enforcement with development velocity
**Cons**: May miss medium-severity vulnerabilities that could be exploited

---

## Recommended Implementation (Phased Rollout)

### Phase 1: Warning Mode (Week 1)
Deploy Option B to establish baseline and identify existing vulnerabilities without blocking development.

### Phase 2: Strict Mode (Week 2+)
After addressing all identified vulnerabilities, switch to Option A to enforce zero-tolerance policy.

## Verification Steps

### 1. Initial Deployment
```bash
# Create feature branch
git checkout -b feature/1006-pip-audit

# Modify .github/workflows/ci.yml (add pip-audit step)
# Commit and push
git add .github/workflows/ci.yml
git commit -m "feat(1006): Add pip-audit to CI pipeline"
git push origin feature/1006-pip-audit
```

### 2. Monitor GitHub Actions
1. Navigate to repository → Actions tab
2. Verify new workflow run includes "Run security audit" step
3. Check output for vulnerability reports
4. Confirm step completes successfully

### 3. Test Failure Scenario (Strict Mode Only)
```bash
# Temporarily add a known vulnerable package to requirements.txt
echo "Django==2.2.0" >> requirements.txt  # Known CVEs in old Django

# Commit and push to trigger CI
git add requirements.txt
git commit -m "test: Verify pip-audit catches vulnerabilities"
git push

# Expected: CI should fail with vulnerability details
# Revert test change after verification
git revert HEAD
git push
```

### 4. Validate Output Quality
- Vulnerability descriptions are clear and actionable
- CVE identifiers are present
- Affected package versions are shown
- Remediation guidance is provided (if available)

## Cascade Risk Assessment

**Risk Level**: ZERO

**Justification**:
- **No Code Changes**: Only modifies CI configuration
- **No Runtime Impact**: pip-audit runs during build, not production
- **No Database Changes**: No schema modifications
- **No API Changes**: No endpoint modifications
- **Isolated Failure**: If pip-audit fails, only CI pipeline is affected (code remains untouched)

**Rollback Plan**:
Simply remove the pip-audit step from `.github/workflows/ci.yml` if issues arise.

## Success Criteria

### Functional Requirements
- [x] pip-audit runs automatically on every push and pull request
- [x] Workflow fails on known vulnerabilities (strict mode) or shows warnings (warning mode)
- [x] Clear, actionable output showing security status
- [x] No false positives blocking legitimate deployments

### Non-Functional Requirements
- [x] CI pipeline execution time increases by <30 seconds
- [x] No impact on local development workflow
- [x] Vulnerability reports are accessible to all team members

### Validation Checklist
1. GitHub Actions workflow includes pip-audit step
2. pip-audit executes after dependency installation
3. Vulnerabilities are detected and reported correctly
4. Team has documented process for addressing vulnerabilities
5. Workflow configuration matches chosen option (A, B, or C)

## Additional Considerations

### False Positive Handling
If pip-audit reports false positives:
```yaml
- name: Run security audit
  run: pip-audit --ignore-vuln GHSA-xxxx-xxxx-xxxx --strict
```

### Caching pip-audit Installation
To speed up CI runs:
```yaml
- name: Cache pip-audit
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-audit-${{ hashFiles('**/requirements.txt') }}

- name: Install pip-audit
  run: pip install pip-audit
```

### Integration with Dependabot
pip-audit complements Dependabot by:
- Providing real-time vulnerability scanning in CI
- Detecting vulnerabilities in transitive dependencies
- Offering more granular control over severity thresholds

**Recommendation**: Use both tools for comprehensive security coverage.

## Documentation Updates Required

After implementation, update:
1. `docs/TESTING.md` - Add pip-audit to CI/CD testing strategy
2. `README.md` - Add security scanning badge (optional)
3. `CONTRIBUTING.md` - Document vulnerability remediation process

## Timeline

**Estimated Effort**: 2 hours

| Phase | Duration | Activity |
|-------|----------|----------|
| Research | 30 min | Review current CI workflow, test pip-audit locally |
| Implementation | 30 min | Add pip-audit step to workflow YAML |
| Testing | 30 min | Trigger CI, verify output, test failure scenario |
| Documentation | 30 min | Update relevant docs, create handover summary |

**Total**: 2 hours

## Related Tickets

- **1000**: Greptile Remediation (Parent)
- **1005**: Fix cryptography vulnerability (may be detected by pip-audit)
- **1007**: Fix SQLAlchemy vulnerability (may be detected by pip-audit)

## References

- [pip-audit documentation](https://pypi.org/project/pip-audit/)
- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [NIST vulnerability severity levels](https://nvd.nist.gov/vuln-metrics/cvss)

---

**Next Steps**:
1. Review and approve this handover
2. Assign to implementer (tier 1 auto-execute)
3. Create feature branch and implement Option B (warning mode)
4. Monitor for 1 week, then upgrade to Option A (strict mode)
