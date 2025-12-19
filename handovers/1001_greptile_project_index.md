# Handover 1001: Greptile Project Index

## Overview

**Ticket**: 1001 (Project Index)
**Status**: Active
**Created**: 2025-12-18
**Parent**: 1000

Index of all remediation projects from Greptile analysis.

---

## MANDATORY: Agent Protocol

**Before starting ANY project:**

1. **Read Serena Memory**: `agent_change_protocol_greptile`
2. **Follow Pre-Implementation Research** for each project below
3. **Document Impact Analysis** before making changes
4. **Verify Tests Pass** after each change

**Risk Tiers:**
- **Tier 1** (ZERO/LOW): Auto-execute, minimal research
- **Tier 2** (MEDIUM): User approval required
- **Tier 3** (HIGH): Staging + full test suite

---

## Phase 1: Quick Wins

### Tier 1 - Auto-Execute

### 1002 - Fix Bare Except Clause

**Risk**: VERY LOW | **Tier**: 1 (Auto-Execute)

**Mission**: Replace bare `except:` with proper exception handling and logging

**Files**:
- `api/endpoints/statistics.py` (line 508)

**Pre-Implementation Research**:
```
# Minimal - this is a logging-only change
1. Read the function containing the bare except
2. Verify no other bare excepts in the file
```

**Implementation**:
```python
# BEFORE
except:
    db_query_time = -1

# AFTER
except Exception as e:
    logger.exception("Database health check failed")
    db_query_time = -1
```

**Effort**: 1 hour
**Tests**: Verify health check endpoint still works
**Cascade Risk**: None - logging only, no behavior change

---

### 1003 - Sanitize Filesystem Paths

**Risk**: LOW | **Tier**: 1 (Auto-Execute)

**Mission**: Remove internal filesystem paths from API error messages

**Files**:
- `src/giljo_mcp/services/product_service.py` (lines 1330-1348)

**Pre-Implementation Research**:
```
1. find_symbol("validate_project_path", include_body=True)
2. Search for other HTTPException with path in detail
3. Verify no frontend code parses these error messages
```

**Implementation**:
```python
# BEFORE
raise HTTPException(status_code=400, detail=f"Project path does not exist: {path}")

# AFTER
raise HTTPException(status_code=400, detail="Project path does not exist")
# Log the actual path internally
logger.warning(f"Project path validation failed: {path}")
```

**Effort**: 2 hours
**Tests**: Verify error messages don't expose paths
**Cascade Risk**: Low - string changes only, frontend may need adjustment if parsing errors

---

### 1004 - Secure Cookie Configuration

**Risk**: LOW | **Tier**: 1 (Auto-Execute)

**Mission**: Add configurable `secure=True` flag for HTTPS deployments

**Files**:
- `api/endpoints/auth.py` (lines 393, 879)
- `config.yaml` (add security.cookies.secure option)

**Pre-Implementation Research**:
```
1. find_symbol("set_cookie", relative_path="api/endpoints/auth.py")
2. Count all set_cookie calls in auth.py
3. Verify config loading pattern in auth.py
```

**Implementation**:
```python
# Add to config
security:
  cookies:
    secure: false  # Set true for HTTPS production

# Update auth.py
secure_cookies = config.get("security", {}).get("cookies", {}).get("secure", False)
response.set_cookie(..., secure=secure_cookies, ...)
```

**Effort**: 2 hours
**Tests**: Verify cookies work in both HTTP and HTTPS modes
**Cascade Risk**: None - defaults to current behavior (secure=False)

---

## Phase 2: Dependency Hygiene

### 1005 - Synchronize pyproject.toml

**Mission**: Align pyproject.toml versions with requirements.txt

**Files**:
- `pyproject.toml`
- `requirements.txt`

**Changes**:
| Package | requirements.txt | pyproject.toml (update to) |
|---------|-----------------|---------------------------|
| httpx | >=0.25.0 | >=0.25.0 |
| websockets | >=12.0 | >=12.0 |
| alembic | >=1.12.0 | >=1.12.0 |
| asyncpg | >=0.29.0 | >=0.29.0 |

**Add missing to pyproject.toml**:
- psycopg2-binary
- python-dotenv
- click, colorama
- aiohttp, psutil, aiofiles
- tiktoken, structlog

**Effort**: 3 hours
**Tests**: `pip install -e .` succeeds with correct versions

---

### 1006 - Add pip-audit to CI/CD

**Mission**: Add vulnerability scanning to GitHub Actions

**Files**:
- `.github/workflows/ci.yml`

**Implementation**:
```yaml
- name: Run pip-audit
  run: |
    pip install pip-audit
    pip-audit --strict
```

**Effort**: 2 hours
**Tests**: CI pipeline fails on known vulnerabilities

---

## Phase 3: Production Hardening

### 1007 - Nonce-Based CSP

**Risk**: HIGH | **Tier**: 3 (Staging + Full Test Suite)

**Mission**: Replace unsafe-inline/unsafe-eval with nonce-based CSP

**Files**:
- `api/middleware/security.py`
- `frontend/index.html` (add nonce to script tags)
- `frontend/vite.config.js` (configure nonce injection)

**Pre-Implementation Research (MANDATORY)**:
```
1. get_symbols_overview("api/middleware/security.py")
2. find_symbol("CORSSecurityMiddleware", depth=2, include_body=True)
3. Read all CSP-related code in security.py
4. Analyze frontend/index.html for inline scripts
5. Check Vue.js production build for eval() usage
6. Research: vite-plugin-csp-guard or similar
```

**Impact Analysis Template**:
```markdown
## CSP Impact Analysis
- Current CSP policy: [document]
- Inline scripts found: [count and locations]
- Dynamic eval usage: [yes/no, where]
- Vue.js compatibility: [tested/not tested]
- Nonce generation strategy: [per-request/per-session]
```

**Verification Gates**:
1. Frontend builds successfully
2. All Vue components render
3. No console CSP violations
4. Dynamic imports work
5. WebSocket connections unaffected

**Effort**: 8 hours
**Cascade Risk**: HIGH - Can break entire frontend if misconfigured

---

### 1008 - Security Headers Validation

**Mission**: Add middleware to validate security headers on responses

**Files**:
- `api/middleware/security.py`

**Headers to validate**:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Strict-Transport-Security (when HTTPS)

**Effort**: 4 hours

---

### 1009 - Rate Limiting

**Risk**: MEDIUM | **Tier**: 2 (User Approval Required)

**Mission**: Implement rate limiting on authentication endpoints

**Files**:
- `api/endpoints/auth.py`
- `api/middleware/rate_limit.py` (new)

**Pre-Implementation Research (MANDATORY)**:
```
1. find_symbol("login", relative_path="api/endpoints/auth.py", include_body=True)
2. find_symbol("register", relative_path="api/endpoints/auth.py", include_body=True)
3. find_referencing_symbols("login", relative_path="api/endpoints/auth.py")
4. Check for existing rate limiting in codebase
5. Analyze how auth failures are currently logged
```

**Endpoints**:
- POST /api/auth/login - 5 attempts/minute
- POST /api/auth/register - 3 attempts/minute
- POST /api/auth/password-reset - 3 attempts/minute

**User Approval Gate**:
```
Before implementation, confirm with user:
- [ ] Rate limit thresholds acceptable?
- [ ] IP-based or user-based limiting?
- [ ] Block duration after limit exceeded?
- [ ] Whitelist for testing IPs?
```

**Effort**: 6 hours
**Cascade Risk**: MEDIUM - Wrong thresholds can block legitimate users

---

## Phase 4: Code Quality

### 1010 - Lifespan Refactor

**Risk**: MEDIUM | **Tier**: 2 (User Approval Required)

**Mission**: Extract api/app.py lifespan blocks into composable functions

**Files**:
- `api/app.py`
- `api/startup/` (new module)

**Pre-Implementation Research (MANDATORY)**:
```
1. get_symbols_overview("api/app.py", depth=1)
2. find_symbol("lifespan", relative_path="api/app.py", include_body=True)
3. Map initialization order dependencies:
   - Which init blocks depend on others?
   - What state is shared between blocks?
4. find_referencing_symbols("state", relative_path="api/app.py")
5. Document the current startup sequence
```

**Dependency Map Template**:
```markdown
## Startup Order Dependencies
1. _init_database() - No dependencies
2. _init_event_bus() - Depends on: [list]
3. _init_health_monitor() - Depends on: [list]
4. _init_cleanup_tasks() - Depends on: [list]

## Shared State
- state.db_manager: Created by [X], used by [Y, Z]
- state.event_bus: Created by [X], used by [Y, Z]
```

**Extract**:
- `_init_database()` (~40 lines)
- `_init_event_bus()` (~38 lines)
- `_init_health_monitor()` (~51 lines)
- `_init_cleanup_tasks()` (~80 lines)

**Verification**:
1. Server starts successfully
2. All background tasks initialize
3. Shutdown is graceful (no hanging tasks)
4. Integration tests pass

**Effort**: 4 hours
**Cascade Risk**: MEDIUM - Wrong order can cause startup failures

---

### 1011 - Repository Pattern Standardization

**Risk**: HIGH | **Tier**: 3 (Staging + Full Test Suite)

**Mission**: Reduce direct queries in endpoints, use repository pattern

**Files**:
- `api/endpoints/*.py` (40+ files)
- `src/giljo_mcp/repositories/` (expand)

**Pre-Implementation Research (MANDATORY)**:
```
1. get_symbols_overview("src/giljo_mcp/repositories/base.py")
2. List all repository classes in src/giljo_mcp/repositories/
3. Search for direct SQLAlchemy queries in api/endpoints/:
   - search_for_pattern("select\(", relative_path="api/endpoints")
   - search_for_pattern("session\.execute", relative_path="api/endpoints")
4. Identify which models have repositories vs which don't
5. Map: endpoint → model → existing repository (if any)
```

**Phased Approach (REQUIRED)**:
```markdown
## Phase 1: Audit (no code changes)
- Count direct queries per endpoint
- Identify high-frequency query patterns
- Document existing repository coverage

## Phase 2: Repository Creation (one model at a time)
- Create repository for most-queried model
- Migrate ONE endpoint to use it
- Verify tests pass
- Repeat

## Phase 3: Endpoint Migration (incremental)
- Migrate endpoints one file at a time
- Run tests after each file
- STOP if any test fails
```

**DO NOT**:
- Change all 40+ files at once
- Modify query logic while migrating
- Remove tenant_key filtering

**Effort**: 6 hours (spread across multiple sessions)
**Cascade Risk**: HIGH - Affects database layer across entire application

---

### 1012 - Bandit Security Linting

**Mission**: Add bandit to pre-commit hooks

**Files**:
- `.pre-commit-config.yaml`
- `pyproject.toml` (bandit config)

**Implementation**:
```yaml
- repo: https://github.com/PyCQA/bandit
  rev: 1.7.5
  hooks:
    - id: bandit
      args: ["-c", "pyproject.toml"]
```

**Effort**: 2 hours

---

## Phase 5: Future (1013-1014)

### 1013 - Structured Logging

**Mission**: Implement error codes and structured log format
**Effort**: 6 hours

### 1014 - Security Event Auditing

**Mission**: Log security events (login, permission checks, etc.)
**Effort**: 8 hours

---

## Summary

| Phase | Projects | Total Effort |
|-------|----------|--------------|
| 1 - Quick Wins | 1002-1004 | 5 hours |
| 2 - Dependencies | 1005-1006 | 5 hours |
| 3 - Hardening | 1007-1009 | 18 hours |
| 4 - Quality | 1010-1012 | 12 hours |
| 5 - Future | 1013-1014 | 14 hours |
| **Total** | **13 projects** | **54 hours** |

---
