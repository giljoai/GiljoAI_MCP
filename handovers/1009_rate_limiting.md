# Handover 1009: Rate Limiting

## Overview
- **Ticket**: 1009
- **Parent**: 1000 (Greptile Remediation)
- **Status**: Pending
- **Risk**: MEDIUM
- **Tier**: 2 (User Approval Required)
- **Effort**: 6 hours

## Mission
Implement rate limiting on authentication endpoints to prevent brute force attacks.

## Files to Modify
- `api/endpoints/auth.py`
- `api/middleware/rate_limit.py` (new file)

## Pre-Implementation Research (MANDATORY)

Before starting implementation, the assigned agent MUST:

1. `find_symbol("login", relative_path="api/endpoints/auth.py", include_body=True)`
2. `find_symbol("register", relative_path="api/endpoints/auth.py", include_body=True)`
3. `find_referencing_symbols("login", relative_path="api/endpoints/auth.py")`
4. Check for existing rate limiting in codebase
5. Analyze how auth failures are currently logged

## User Approval Gate

Before implementation, confirm with user:
- [ ] Rate limit thresholds acceptable?
- [ ] IP-based or user-based limiting?
- [ ] Block duration after limit exceeded?
- [ ] Whitelist for testing IPs?

## Proposed Rate Limits

| Endpoint | Limit | Window | Block Duration |
|----------|-------|--------|----------------|
| POST /api/auth/login | 5 attempts | 1 minute | 5 minutes |
| POST /api/auth/register | 3 attempts | 1 minute | 10 minutes |
| POST /api/auth/password-reset | 3 attempts | 1 minute | 15 minutes |

## Implementation Approach

### Option A: In-Memory (Simple)
```python
from collections import defaultdict
import time

rate_limits = defaultdict(list)

def check_rate_limit(ip: str, endpoint: str, limit: int, window: int) -> bool:
    key = f"{ip}:{endpoint}"
    now = time.time()
    rate_limits[key] = [t for t in rate_limits[key] if now - t < window]
    if len(rate_limits[key]) >= limit:
        return False
    rate_limits[key].append(now)
    return True
```

### Option B: Redis-Based (Production)
Use Redis for distributed rate limiting across multiple servers.

### Option C: slowapi Library
Use slowapi for FastAPI-native rate limiting with decorators.

## Verification

1. Run: `pytest tests/endpoints/test_auth.py`
2. Manual: Exceed rate limit, verify 429 response
3. Wait for block duration, verify access restored
4. Test with whitelisted IP bypasses limits

## Cascade Risk
MEDIUM - Wrong thresholds can block legitimate users.

## Rollback Plan
Disable rate limiting middleware in `app.py` if issues found.

## Success Criteria
- Auth endpoints have rate limiting
- 429 Too Many Requests returned when exceeded
- Clear error message to users
- Logging of blocked attempts
