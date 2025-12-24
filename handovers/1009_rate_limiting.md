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

---

## Implementation Summary

### Status: ✅ COMPLETE

**Implementation Date**: 2025-12-24
**Methodology**: Test-Driven Development (RED → GREEN → REFACTOR)
**Test Results**: 12/12 tests passing

### Files Created/Modified

**Created**:
- `api/middleware/rate_limit.py` - Rate limiting middleware (184 lines)
- `tests/unit/test_rate_limiting.py` - Comprehensive test suite (357 lines)

**Modified**:
- `api/endpoints/auth.py` - Applied rate limiting to `/login` and `/register`
- `api/endpoints/auth_pin_recovery.py` - Applied rate limiting to `/verify-pin-and-reset-password`

### Implementation Decisions

#### User-Approved Limits
After user consultation, the following limits were approved:
- **Login**: 5 attempts/minute per IP (60 second lockout)
- **Register**: 3 attempts/minute per IP (60 second lockout)
- **Password Reset**: 3 attempts/minute per IP (60 second lockout)
- **Blocking**: IP-based (not user-based)

#### Technical Approach
Selected **Option A: In-Memory** for simplicity:
- Sliding window algorithm for accurate rate tracking
- `collections.deque` for efficient timestamp management
- Automatic cleanup of expired entries
- Thread-safe counter increments
- Singleton pattern for global rate limiter instance

#### Key Features
1. **IP-Based Isolation**: Each IP has separate rate limit counter
2. **HTTP 429 Response**: Standard "Too Many Requests" with Retry-After header
3. **Logging**: All violations logged with IP, endpoint, and timestamp
4. **Cross-Platform**: Uses `time.time()` for compatibility
5. **Memory Management**: Automatic cleanup of expired entries (1-hour window)

### Test Coverage

**12 Comprehensive Tests**:
1. ✅ Under limit succeeds
2. ✅ At limit succeeds
3. ✅ Over limit returns 429
4. ✅ After cooldown succeeds
5. ✅ Different IPs have separate limits
6. ✅ Register endpoint has 3/min limit
7. ✅ Password reset endpoint has 3/min limit
8. ✅ Violations are logged
9. ✅ Retry-After header shows remaining time
10. ✅ Missing client IP defaults to 'unknown'
11. ✅ Concurrent requests counted correctly
12. ✅ Cleanup removes expired entries

### How to Verify

**Run Tests**:
```bash
pytest tests/unit/test_rate_limiting.py -v
```
Expected: 12 passed

**Manual Testing**:
```bash
# Test login rate limit (5 attempts/minute)
for i in {1..6}; do
  curl -X POST http://localhost:7272/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}' \
    -i | grep "HTTP"
done
# 6th request should return: HTTP/1.1 429 Too Many Requests
```

**Check Logs**:
```bash
# Look for rate limit violations
grep "Rate limit exceeded" logs/api.log
```

### Response Format

**Success (HTTP 200)**:
```json
{
  "message": "Login successful",
  "username": "admin",
  "role": "admin",
  "tenant_key": "tk_..."
}
```

**Rate Limited (HTTP 429)**:
```json
{
  "detail": "Too many requests. Limit: 5 per 60 seconds. Try again later."
}
```

**Headers**:
```
Retry-After: 45
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Window: 60
```

### Security Considerations

1. **Dual Protection for Password Reset**:
   - IP-based rate limit (3/min) prevents distributed attacks
   - Per-user account lockout (5 failed → 15 min) prevents targeted attacks
   - Both protections work independently

2. **Logging**:
   - All violations logged with IP address
   - Enables monitoring for attack patterns
   - Format: `"Rate limit exceeded - IP: X.X.X.X, Endpoint: /path, Limit: 5/60s"`

3. **Client IP Detection**:
   - Falls back to 'unknown' if client info missing
   - Prevents crashes on edge cases

### Performance Impact

- **Memory**: ~100 bytes per IP (deque of timestamps)
- **CPU**: O(n) cleanup where n = requests in window (typically <10)
- **Latency**: <1ms per request check
- **Scalability**: Suitable for single-server deployments

### Future Enhancements (Not Implemented)

1. **Redis Backend**: For multi-server deployments
2. **Whitelist**: Trusted IPs bypass rate limits
3. **Dynamic Limits**: Adjust based on user role
4. **Rate Limit Headers**: Include in all responses (not just 429)

### Rollback Instructions

If issues arise, disable rate limiting:

**Option 1**: Comment out rate limit checks in endpoints:
```python
# api/endpoints/auth.py
# rate_limiter = get_rate_limiter()
# rate_limiter.check_rate_limit(request, limit=5, window=60, raise_on_limit=True)
```

**Option 2**: Modify limits to be very high:
```python
# Effectively disable by setting very high limit
rate_limiter.check_rate_limit(request, limit=10000, window=60, raise_on_limit=True)
```

### Related Documentation

- Test suite: `tests/unit/test_rate_limiting.py`
- Implementation: `api/middleware/rate_limit.py`
- Architecture: Sliding window algorithm with in-memory storage

### Commits

1. `87bfd619` - test: Add comprehensive tests for rate limiting (RED phase)
2. `67c3d42c` - feat: Implement rate limiting middleware (GREEN phase)
3. `f355ae51` - feat: Apply rate limiting to auth endpoints

**Total Lines Changed**: +572 lines (tests + implementation)
