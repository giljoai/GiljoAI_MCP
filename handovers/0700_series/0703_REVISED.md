# Handover 0703-REVISED: Auth & Middleware Consolidation

**Series:** 0700 Code Cleanup Series
**Risk Level:** MEDIUM
**Estimated Effort:** 2-3 hours
**Date:** 2026-02-06
**Supersedes:** 0703 (original only deleted 1 file)

---

## Mission Statement

Consolidate duplicate auth/middleware code and establish consistent patterns. Original 0703 only deleted `api/middleware.py` (260 lines). This revision addresses the full scope identified in audit.

---

## Audit Findings (To Address)

| Gap | Severity | Action |
|-----|----------|--------|
| Duplicate RateLimiter classes | CRITICAL | Consolidate or clearly differentiate |
| 6 duplicate Pydantic models in auth endpoints | CRITICAL | Extract to shared module |
| Logging patterns not documented | MEDIUM | Add to CLAUDE.md |
| Missing type hints in api/dependencies.py | LOW | Add type hints |
| rate_limit.py not exported from __init__.py | LOW | Fix exports |

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY)

### Launch Validation Subagent

```
Use deep-researcher subagent:

"Validate the scope for 0703-REVISED auth/middleware cleanup.

TASK 1: Validate RateLimiter duplication
```bash
# Find all RateLimiter classes
grep -rn "class RateLimiter\|class.*RateLimiter" api/ src/ --include="*.py"

# Find all rate limiter imports
grep -rn "from.*rate_limit\|from.*rate_limiter" api/ src/ tests/ --include="*.py"

# Check what each is used for
grep -rn "get_rate_limiter\|RateLimitMiddleware\|EndpointRateLimiter" api/ --include="*.py"
```

TASK 2: Validate Pydantic model duplication
```bash
# Find duplicate model definitions
grep -rn "class PinPasswordResetRequest\|class CheckFirstLoginRequest\|class CompleteFirstLoginRequest" api/endpoints/ --include="*.py"

# Count duplicates
for model in PinPasswordResetRequest PinPasswordResetResponse CheckFirstLoginRequest CheckFirstLoginResponse CompleteFirstLoginRequest CompleteFirstLoginResponse; do
  echo "$model: $(grep -rn "class $model" api/endpoints/ --include="*.py" | wc -l)"
done
```

TASK 3: Check logging patterns
```bash
# Standard logging
grep -rn "import logging" src/ api/ --include="*.py" | wc -l

# Structured logging
grep -rn "from.*logging import get_logger\|from giljo_mcp.logging import" src/ api/ --include="*.py" | wc -l

# List structured logging files
grep -rn "from.*logging import get_logger" src/ api/ --include="*.py"
```

TASK 4: Check type hints in dependencies.py
```bash
grep -n "def get_db\|def get_current" api/dependencies.py
```

REPORT:
1. RateLimiter classes: [count, locations, purposes]
2. Duplicate Pydantic models: [count, which ones]
3. Logging pattern split: [standard count vs structured count]
4. Type hint gaps: [list functions without return types]
5. Additional findings: [any other auth/middleware issues]"
```

### Document Validation

```
## VALIDATION RESULTS
- RateLimiter duplication: [CONFIRMED/DIFFERENT - explain]
- Pydantic duplication: [X models duplicated in Y files]
- Logging patterns: [X standard, Y structured]
- Type hint gaps: [list]
- Additional: [any new findings]
```

---

## PHASE 1: EXECUTION

### Task 1: Consolidate or Differentiate RateLimiters

**Option A: Consolidate** (if they do the same thing)
- Keep one implementation
- Update all imports
- Delete duplicate

**Option B: Differentiate** (if they serve different purposes)
- Rename to clarify purpose:
  - `rate_limit.py` → `auth_rate_limiter.py` (auth-specific)
  - `rate_limiter.py` → `global_rate_limiter.py` (middleware)
- Update `__init__.py` exports
- Document when to use which

**Decision criteria from validation:**
- If APIs are identical → Consolidate
- If APIs differ (auth vs global) → Differentiate with clear names

### Task 2: Extract Shared Auth Models

Create `api/endpoints/auth_models.py`:

```python
"""Shared Pydantic models for authentication endpoints.

Used by both auth.py and auth_pin_recovery.py.
"""
from pydantic import BaseModel, Field, field_validator
# ... validators ...

class PinPasswordResetRequest(BaseModel):
    """Request to reset password using recovery PIN."""
    # Move from auth.py

class PinPasswordResetResponse(BaseModel):
    """Response after PIN-based password reset."""
    # Move from auth.py

class CheckFirstLoginRequest(BaseModel):
    """Request to check first login status."""
    # Move from auth.py

class CheckFirstLoginResponse(BaseModel):
    """Response with first login status."""
    # Move from auth.py

class CompleteFirstLoginRequest(BaseModel):
    """Request to complete first login setup."""
    # Move from auth.py

class CompleteFirstLoginResponse(BaseModel):
    """Response after first login completion."""
    # Move from auth.py
```

Update imports in:
- `api/endpoints/auth.py` - Import from auth_models
- `api/endpoints/auth_pin_recovery.py` - Import from auth_models, delete duplicates

### Task 3: Document Logging Patterns

Add to `CLAUDE.md` in appropriate section:

```markdown
## Logging Standards

**Standard logging** (default for most code):
```python
import logging
logger = logging.getLogger(__name__)
```

**Structured logging** (for critical paths):
```python
from giljo_mcp.logging import get_logger, ErrorCode
logger = get_logger(__name__)
```

Use structured logging in:
- Authentication flows (auth endpoints, middleware)
- Database operations (connection, transactions)
- WebSocket handlers
- MCP tool orchestration

All other code should use standard logging.
```

### Task 4: Add Type Hints to dependencies.py

```python
from typing import Generator, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

def get_db() -> Generator[Session, None, None]:
    """Get synchronous database session."""
    ...

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session."""
    ...
```

### Task 5: Fix Middleware Exports

Update `api/middleware/__init__.py` to include all public APIs:

```python
from .rate_limiter import RateLimitMiddleware, EndpointRateLimiter, RateLimiter
from .rate_limit import get_rate_limiter, AuthRateLimiter  # Add if keeping separate
from .auth import AuthMiddleware
# ... other exports
```

---

## PHASE 2: VERIFICATION

```bash
# No duplicate Pydantic models
grep -rn "class PinPasswordResetRequest" api/endpoints/ --include="*.py" | wc -l
# Expected: 1 (in auth_models.py only)

# Auth endpoints still work
python -c "from api.endpoints.auth import router; print('auth OK')"
python -c "from api.endpoints.auth_pin_recovery import router; print('pin_recovery OK')"

# Middleware imports clean
python -c "from api.middleware import RateLimitMiddleware, get_rate_limiter; print('middleware OK')"

# Type hints present
grep -n "def get_db.*->" api/dependencies.py

# CLAUDE.md has logging section
grep -A5 "Logging Standards" CLAUDE.md
```

---

## Success Criteria

- [ ] Phase 0 validation complete
- [ ] RateLimiter situation resolved (consolidated or differentiated)
- [ ] Pydantic models extracted to auth_models.py
- [ ] Logging patterns documented in CLAUDE.md
- [ ] Type hints added to dependencies.py
- [ ] Middleware exports fixed
- [ ] All auth endpoints still work
- [ ] comms_log entry written
- [ ] Committed

---

## Commit Message Template

```
cleanup(0703-revised): Consolidate auth/middleware code

Comprehensive auth cleanup based on audit findings:

- [Consolidated/Differentiated] RateLimiter implementations
- Extracted 6 Pydantic models to api/endpoints/auth_models.py
- Documented logging patterns in CLAUDE.md
- Added type hints to api/dependencies.py
- Fixed middleware __init__.py exports

Validation: Subagent confirmed [X] duplicates, [Y] resolved.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
