# Handover 0330: De-Linting Risk Assessment & Roadmap

**Date**: 2025-12-05
**Scope**: Comprehensive codebase quality audit
**Author**: Claude Code (Parallel Agent Analysis)

---

## Executive Summary

| Metric | Backend (Python) | Frontend (Vue) | Combined |
|--------|------------------|----------------|----------|
| **Total Issues** | 3,545 | 66 | 3,611 |
| **Critical (Runtime)** | 28 | 0 | 28 |
| **Security Issues** | 16 | 4 | 20 |
| **Auto-fixable** | 1,226 (35%) | 27 (41%) | 1,253 |
| **LOC Analyzed** | 67,754 | 52,722 | 120,476 |
| **Files Affected** | 204 | 60 | 264 |

**Overall Health Score**: 78/100 (Good - Production Ready with Improvements)

---

## Risk Rankings (Priority Order)

### CRITICAL - Fix Immediately (Risk: HIGH)

| # | Issue | Count | Location | Impact | Effort |
|---|-------|-------|----------|--------|--------|
| 1 | **F821 - Undefined names** | 26 | Backend | Runtime crashes | 2-3 hrs |
| 2 | **E722 - Bare except** | 2 | Backend | Hides bugs/crashes | 1 hr |
| 3 | **v-html XSS risk** | 4 | Frontend | Security vulnerability | 2-3 hrs |

**Total Critical Effort**: 5-7 hours

---

### HIGH - Fix This Week (Risk: MEDIUM-HIGH)

| # | Issue | Count | Location | Impact | Effort |
|---|-------|-------|----------|--------|--------|
| 4 | **B008 - Mutable defaults** | 336 | Backend | Shared state bugs | 8-12 hrs |
| 5 | **BLE001 - Blind exceptions** | 251 | Backend | Silent failures | 10-15 hrs |
| 6 | **B904 - Raise without from** | 133 | Backend | Lost error context | 4-6 hrs |
| 7 | **console.log cleanup** | 148+ | Frontend | Info leakage, perf | 4-6 hrs |

**Total High Effort**: 26-39 hours

---

### MEDIUM - Fix This Month (Risk: MEDIUM)

| # | Issue | Count | Location | Impact | Effort |
|---|-------|-------|----------|--------|--------|
| 8 | **PLC0415 - Import placement** | 461 | Backend | Startup performance | 15-20 hrs |
| 9 | **UP006 - Type annotations** | 439 | Backend | Python 3.9+ compat | 8-12 hrs |
| 10 | **TRY401 - Verbose logging** | 220 | Backend | Log noise | 6-8 hrs |
| 11 | **TRY301 - Raise in try** | 161 | Backend | Error handling | 5-7 hrs |
| 12 | **Pickle deserialization** | 1 | Backend | Security (controlled) | 2-4 hrs |

**Total Medium Effort**: 36-51 hours

---

### LOW - Backlog (Risk: LOW)

| # | Issue | Count | Location | Impact | Effort |
|---|-------|-------|----------|--------|--------|
| 13 | **ARG001 - Unused args** | 184 | Backend | Code cleanliness | 6-8 hrs |
| 14 | **F401 - Unused imports** | 127 | Backend | Minor perf | 2-3 hrs |
| 15 | **var keyword** | 2 | Frontend | ES6 compliance | 30 min |
| 16 | **Prettier formatting** | 23 | Frontend | Style consistency | 20 min |
| 17 | **B104 - Bind 0.0.0.0** | 13 | Backend | Intentional design | 0 (documented) |

**Total Low Effort**: 9-12 hours

---

## Feature-Based Risk Matrix

Based on the feature catalogues (27 backend + 21 frontend categories):

### Backend Features - Risk Assessment

| Feature | Issues | Risk Level | Priority | Notes |
|---------|--------|------------|----------|-------|
| **Orchestration** | 97 | HIGH | 1 | Core functionality, most complex |
| **Tool Accessor** | 92 | HIGH | 2 | Central MCP dispatcher |
| **Project Service** | 86 | HIGH | 3 | 2,563 LOC, critical path |
| **User Service** | 71 | MEDIUM | 4 | Auth flows |
| **Downloads** | 66 | MEDIUM | 5 | File handling security |
| **Product Lifecycle** | 63 | MEDIUM | 6 | Vision uploads |
| **Prompts** | 59 | MEDIUM | 7 | Token-sensitive |
| **Product Vision** | 58 | MEDIUM | 8 | Document handling |
| **Product Service** | 58 | MEDIUM | 9 | Core CRUD |
| **Template Seeder** | 56 | LOW | 10 | Setup-time only |
| **Context Tools** | 53 | LOW | 11 | Read-only operations |
| **State Manager** | 53 | LOW | 12 | Setup wizard |

### Frontend Features - Risk Assessment

| Feature | Issues | Risk Level | Priority | Notes |
|---------|--------|------------|----------|-------|
| **JobsTab** | 16 | HIGH | 1 | Real-time monitoring, v-html? |
| **LaunchTab** | 13 | HIGH | 2 | Orchestrator launch flow |
| **main.js** | 14 | MEDIUM | 3 | App bootstrap |
| **UserSettings** | 12 | MEDIUM | 4 | Config persistence |
| **MessageItem** | v-html | HIGH | 5 | XSS risk - sanitize |
| **BroadcastPanel** | v-html | HIGH | 6 | XSS risk - sanitize |
| **TemplateManager** | v-html | HIGH | 7 | XSS risk - sanitize |
| **DatabaseConnection** | v-html | MEDIUM | 8 | Admin-only page |

---

## Security Findings Summary

### Backend Security (Bandit)

| Finding | Severity | Status | Action |
|---------|----------|--------|--------|
| B104 - Bind 0.0.0.0 | Medium | **Accepted** | Documented design decision |
| B608 - SQL injection | Medium | **False Positive** | Error messages, not queries |
| B301 - Pickle | Medium | **Review** | Verify Redis security |

### Frontend Security

| Finding | Severity | Status | Action |
|---------|----------|--------|--------|
| v-html in 4 files | High | **Fix Required** | Use DOMPurify or v-text |

---

## Recommended Remediation Plan

### Phase 1: Critical Fixes (Week 1) - 5-7 hours

```bash
# 1. Fix undefined names (will crash app)
ruff check src/ api/ --select F821 --fix
pytest tests/ --tb=short

# 2. Fix bare except clauses
ruff check src/ api/ --select E722 --fix

# 3. Frontend v-html audit (manual)
# Review: MessageItem.vue, BroadcastPanel.vue, TemplateManager.vue, DatabaseConnection.vue
# Add DOMPurify: npm install dompurify
```

### Phase 2: Quick Wins (Week 1-2) - 4-6 hours

```bash
# Backend auto-fixes (1,226 issues)
ruff check src/ api/ --fix

# Frontend auto-fixes
cd frontend
npm run lint -- --fix
npx prettier --write src/

# Remove console.log from critical paths
grep -r "console.log" src/components/projects/ --files-with-matches
```

### Phase 3: Exception Handling (Week 2-4) - 20-30 hours

Focus on top 10 files:
1. orchestration.py (97 issues)
2. app.py (92 issues)
3. tool_accessor.py (92 issues)
4. project_service.py (86 issues)
5. user_service.py (71 issues)

Pattern to apply:
```python
# Before (BLE001 + B904)
try:
    result = await service.operation()
except Exception:
    logger.error("Failed")
    raise

# After
try:
    result = await service.operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise ServiceError("Context message") from e
```

### Phase 4: Code Quality (Month 2) - 30-40 hours

- Import organization (PLC0415)
- Type annotations (UP006)
- Unused argument cleanup (ARG001)
- Enable stricter linting in CI

### Phase 5: Prevention (Ongoing)

```yaml
# .pre-commit-config.yaml - Re-enable hooks
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## Effort Estimates

| Phase | Hours | Timeline | Developer(s) |
|-------|-------|----------|--------------|
| Phase 1: Critical | 5-7 | Week 1 | 1 |
| Phase 2: Quick Wins | 4-6 | Week 1-2 | 1 |
| Phase 3: Exceptions | 20-30 | Week 2-4 | 1-2 |
| Phase 4: Quality | 30-40 | Month 2 | 1-2 |
| Phase 5: Prevention | 2-4 | Ongoing | 1 |
| **Total** | **61-87** | **6-8 weeks** | **1-2** |

---

## Success Metrics

After remediation:

| Metric | Current | Target |
|--------|---------|--------|
| Critical issues | 28 | 0 |
| Security issues | 20 | 0 |
| Total linting issues | 3,611 | < 500 |
| Auto-fixable remaining | 1,253 | 0 |
| CI/CD lint blocking | No | Yes |
| Pre-commit hooks | Disabled | Enabled |

---

## Related Documents

- `0330_feature_catalogue_backend.md` - 27 backend feature categories
- `0330_feature_catalogue_frontend.md` - 21 frontend feature categories
- `0330_python_linting_report.md` - Detailed Python analysis
- `0330_frontend_linting_report.md` - Detailed Vue analysis

---

## Approval

- [ ] Review critical fixes plan
- [ ] Approve Phase 1 timeline
- [ ] Assign developer(s)
- [ ] Schedule Phase 3 sprint

**Next Action**: Fix 28 critical issues (F821 + E722) - estimated 2-3 hours
