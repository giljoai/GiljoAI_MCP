# Handover 1008: Security Headers Validation

**Date**: 2025-12-18
**Parent**: 1000 (Greptile Remediation)
**Status**: Pending
**Risk**: LOW
**Tier**: 1 (Auto-Execute)
**Effort**: 4 hours

---

## Mission

Add middleware to validate and enforce security headers on all HTTP responses to meet OWASP security best practices and prevent common web vulnerabilities (MIME sniffing, clickjacking, XSS).

---

## Objective

Implement FastAPI middleware that automatically adds critical security headers to all responses while maintaining compatibility with existing WebSocket and HTTP functionality.

---

## Files to Modify

- `api/middleware/security.py` (new or existing)
- `api/app.py` (register middleware if new)

---

## Pre-Implementation Research

Before implementing, gather context using Serena tools:

1. **Check if middleware exists**:
   ```python
   find_symbol("SecurityHeadersMiddleware", relative_path="api/middleware")
   ```

2. **Review current middleware setup**:
   ```python
   get_symbols_overview("api/app.py", depth=1)
   ```

3. **Check existing header handling**:
   ```python
   search_for_pattern(substring_pattern="x-content-type-options", relative_path="api/")
   ```

---

## Security Headers Specification

### Required Headers (All Responses)

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevent clickjacking via iframes |
| `X-XSS-Protection` | `1; mode=block` | Enable legacy XSS filter (browser-level) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer information leakage |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Disable unused browser features |

### Conditional Headers

| Header | Condition | Value |
|--------|-----------|-------|
| `Strict-Transport-Security` | HTTPS only | `max-age=31536000; includeSubDomains` |

**Note**: HSTS header should only be added when serving over HTTPS to avoid breaking HTTP dev environments.

---

## Implementation

### Option 1: ASGI Middleware (Recommended)

```python
# api/middleware/security.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all HTTP responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    - Strict-Transport-Security: (HTTPS only)
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Core security headers (all responses)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS only for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
```

### Option 2: Pure ASGI Middleware (Lower-level)

```python
# api/middleware/security.py
class SecurityHeadersMiddleware:
    """
    Low-level ASGI middleware for security headers.
    Use when BaseHTTPMiddleware has performance concerns.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Pass through WebSocket and other connections
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))

                # Add security headers
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"x-xss-protection"] = b"1; mode=block"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers[b"permissions-policy"] = b"geolocation=(), microphone=(), camera=()"

                # HSTS for HTTPS only
                if scope.get("scheme") == "https":
                    headers[b"strict-transport-security"] = b"max-age=31536000; includeSubDomains"

                message["headers"] = list(headers.items())

            await send(message)

        await self.app(scope, receive, send_with_headers)
```

### Registration in api/app.py

```python
from api.middleware.security import SecurityHeadersMiddleware

# Add middleware (order matters - this should be early in chain)
app.add_middleware(SecurityHeadersMiddleware)
```

---

## Testing Strategy

### 1. Unit Tests

Create `tests/middleware/test_security_headers.py`:

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.middleware.security import SecurityHeadersMiddleware

@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app

@pytest.fixture
def client(app):
    return TestClient(app)

def test_security_headers_present(client):
    """Verify all required security headers are added."""
    response = client.get("/test")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-xss-protection"] == "1; mode=block"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers["permissions-policy"]

def test_hsts_not_added_for_http(client):
    """HSTS should not be added for HTTP requests."""
    response = client.get("/test")
    assert "strict-transport-security" not in response.headers

def test_existing_headers_preserved(client):
    """Middleware should not override existing headers."""
    # This would require a custom endpoint that sets headers
    # Left as implementation detail
    pass
```

### 2. Integration Tests

```bash
# Manual verification with curl
curl -I http://localhost:7272/api/health

# Expected headers:
# x-content-type-options: nosniff
# x-frame-options: DENY
# x-xss-protection: 1; mode=block
# referrer-policy: strict-origin-when-cross-origin
# permissions-policy: geolocation=(), microphone=(), camera=()
```

### 3. Online Validation

Use [securityheaders.com](https://securityheaders.com) to validate headers once deployed.

### 4. WebSocket Compatibility

```python
# tests/middleware/test_security_headers.py
def test_websocket_not_affected(client):
    """WebSocket connections should pass through without modification."""
    with client.websocket_connect("/ws/test") as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "pong"
```

---

## Verification Checklist

- [ ] All security headers present on HTTP responses
- [ ] HSTS only added for HTTPS connections
- [ ] WebSocket connections unaffected
- [ ] Existing API tests still pass
- [ ] No performance degradation
- [ ] Headers validate on securityheaders.com
- [ ] pytest tests/middleware/ passes with >80% coverage

---

## Cascade Risk

**Risk Level**: LOW

**Rationale**:
- Additive middleware (no existing behavior changed)
- Headers are response-only (no request processing)
- WebSocket connections explicitly passed through
- HSTS conditional on HTTPS (safe for dev environments)

**Potential Issues**:
- If frontend embeds in iframe, `X-Frame-Options: DENY` will break it (unlikely)
- Some old browsers may not support all headers (graceful degradation)

---

## Success Criteria

1. **Security**: All required headers present on responses
2. **Compatibility**: No impact on existing functionality (API, WebSocket, frontend)
3. **Testing**: pytest coverage >80% for middleware module
4. **Validation**: Passes online security header checks
5. **Documentation**: Middleware purpose and headers documented in code

---

## Notes

- **HSTS Caution**: Only enable HSTS on production HTTPS deployments. Dev environments using HTTP will break if HSTS is cached by browser.
- **CSP Future Work**: Content-Security-Policy is complex and should be a separate handover (1009?) to avoid scope creep.
- **Header Precedence**: Middleware runs early to ensure headers are added before other middleware or endpoint handlers potentially modify response.

---

## References

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/advanced/middleware/)
- [Security Headers Scanner](https://securityheaders.com)
