# Handover 1000: Greptile Remediation Roadmap

## Overview

**Ticket**: 1000 (Master Roadmap)
**Status**: Active
**Created**: 2025-12-18
**Priority**: High

Greptile's automated security analysis identified potential issues. After Claude Code deep research validation, we found that **most CRITICAL findings are false positives**, but legitimate improvements remain.

## Greptile Analysis Summary

### False Positives (No Action Needed)

| Finding | Greptile Severity | Why It's OK |
|---------|-------------------|-------------|
| Hardcoded secrets | CRITICAL | `secrets.token_urlsafe(32)` during install |
| Host Header Injection | CRITICAL | Defense-in-depth: IP validation + domain whitelist |
| SQL Injection | CRITICAL | SQLAlchemy ORM throughout |
| WebSocket Auth Bypass | HIGH | Intentional during setup (no users exist) |
| Authentication duplication | MEDIUM | Well-centralized in `auth/dependencies.py` |
| Naming conventions | MEDIUM | Consistent snake_case throughout |
| Database efficiency | MEDIUM | 11+ indexes, proper async handling |
| Resource leaks | HIGH | Excellent cleanup patterns |

### Valid Findings (Action Required)

| Finding | Severity | Project | Status |
|---------|----------|---------|--------|
| Bare `except:` in statistics.py | MEDIUM | 1002 | Pending |
| Filesystem paths in errors | MEDIUM | 1003 | Pending |
| No secure cookie option | LOW | 1004 | Pending |
| pyproject.toml out of sync | MEDIUM | 1005 | Pending |
| No vulnerability scanning | MEDIUM | 1006 | Pending |
| CSP unsafe-inline | MEDIUM | 1007 | Pending |
| No security headers validation | LOW | 1008 | Pending |
| No rate limiting | MEDIUM | 1009 | Pending |
| Startup complexity | LOW | 1010 | Pending |
| Repository pattern underuse | LOW | 1011 | Pending |
| No security linting | MEDIUM | 1012 | Pending |

## Phase Structure

### Phase 1: Quick Wins (1002-1004)
- **Timeline**: 1-2 handovers
- **Effort**: 5 hours total
- **Impact**: Closes easy Greptile findings

### Phase 2: Dependency Hygiene (1005-1006)
- **Timeline**: 1 handover
- **Effort**: 5 hours total
- **Impact**: CI/CD security scanning

### Phase 3: Production Hardening (1007-1009)
- **Timeline**: 2-3 handovers
- **Effort**: 18 hours total
- **Impact**: Enterprise security posture

### Phase 4: Code Quality (1010-1012)
- **Timeline**: 2 handovers
- **Effort**: 12 hours total
- **Impact**: Maintainability

### Phase 5: Monitoring (1013-1014) - FUTURE
- **Timeline**: TBD
- **Effort**: 14 hours total
- **Impact**: Production observability

## Agent Protocol (MANDATORY)

**Before starting ANY project, agents MUST:**
1. Read Serena memory: `agent_change_protocol_greptile`
2. Follow the pre-change research protocol
3. Document impact analysis before making changes
4. Verify tests pass after changes

---

## Execution Order (Safety-First)

### Tier 1: Zero/Very Low Risk (Auto-Execute)
| Order | Project | Risk | Effort | Description |
|-------|---------|------|--------|-------------|
| 1 | 1002 | VERY LOW | 1h | Fix bare except |
| 2 | 1003 | LOW | 2h | Sanitize paths |
| 3 | 1004 | LOW | 2h | Secure cookie config |
| 4 | 1005 | LOW | 3h | Sync pyproject.toml |
| 5 | 1006 | ZERO | 2h | Add pip-audit (CI only) |
| 6 | 1008 | LOW | 4h | Security headers |
| 7 | 1012 | ZERO | 2h | Add bandit (linting only) |

### Tier 2: Medium Risk (User Approval Required)
| Order | Project | Risk | Effort | Gate |
|-------|---------|------|--------|------|
| 8 | 1009 | MEDIUM | 6h | Review rate limit thresholds |
| 9 | 1010 | MEDIUM | 4h | Integration tests pass |

### Tier 3: High Risk (Careful Review + Staging)
| Order | Project | Risk | Effort | Gate |
|-------|---------|------|--------|------|
| 10 | 1007 | HIGH | 8h | Vue.js testing in staging |
| 11 | 1011 | HIGH | 6h | Full test suite + manual QA |

## Success Criteria

- All `except:` bare clauses eliminated
- No internal paths in API responses
- pip-audit clean in CI/CD
- bandit passing (no HIGH/CRITICAL)
- Auth endpoints rate-limited

## References

- Greptile Analysis: December 2025
- Claude Code Research: 2025-12-18
- Research Agents: ad13e38, af2d8f8, aa19ebf
