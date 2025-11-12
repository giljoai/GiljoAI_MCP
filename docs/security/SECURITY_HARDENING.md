# Security Hardening Guide

**Created**: 2025-11-12
**Handover**: 0129c - Security Hardening & OWASP Compliance
**Status**: Production-Ready

---

## Overview

GiljoAI MCP implements comprehensive, production-grade security hardening following industry best practices and OWASP Top 10 (2021) guidelines.

This document describes all security measures implemented in Handover 0129c.

---

## Security Layers

GiljoAI MCP uses a **defense-in-depth** approach with 7 security layers:

1. **CORS Protection** - Controls cross-origin requests
2. **Rate Limiting** - Prevents abuse and DoS attacks
3. **Security Headers** - Browser-level protections (HSTS, CSP, etc.)
4. **Input Validation** - Blocks malicious inputs (SQL injection, XSS, path traversal)
5. **Authentication** - Enforces authentication on all endpoints
6. **CSRF Protection** - Prevents cross-site request forgery (optional)
7. **Database-Level Tenant Isolation** - Row-level security

---

## 1. Security Headers Middleware

**File**: `api/middleware/security.py`
**Class**: `SecurityHeadersMiddleware`

### Headers Implemented

| Header | Value | Purpose |
|--------|-------|---------|
| **Strict-Transport-Security** | `max-age=31536000; includeSubDomains; preload` | Enforces HTTPS for 1 year |
| **Content-Security-Policy** | Strict policy with Vue support | Prevents XSS attacks |
| **X-Frame-Options** | `DENY` | Prevents clickjacking |
| **X-Content-Type-Options** | `nosniff` | Prevents MIME sniffing |
| **Referrer-Policy** | `strict-origin-when-cross-origin` | Controls referrer information |
| **Permissions-Policy** | Disables unnecessary features | Limits browser APIs |
| **X-XSS-Protection** | `1; mode=block` | Legacy XSS protection |

### Content Security Policy (CSP)

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval';  # Vue needs eval
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self' data:;
connect-src 'self' ws: wss:;  # WebSocket support
frame-ancestors 'none';
base-uri 'self';
form-action 'self'
```

**Note**: `unsafe-inline` and `unsafe-eval` are required for Vue.js. In production, consider using nonce-based CSP for tighter security.

### Usage

```python
# api/app.py
from api.middleware import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware, hsts_max_age=31536000)
```

---

## 2. Rate Limiting Middleware

**File**: `api/middleware/rate_limiter.py`
**Class**: `RateLimitMiddleware`, `EndpointRateLimiter`

### Features

- **Per-IP rate limiting** using sliding window algorithm
- **Configurable limits** (default: 100 requests/minute)
- **Exempt paths** (health checks, metrics)
- **X-RateLimit-*** headers** for client information
- **Proxy support** (X-Forwarded-For, X-Real-IP)
- **Per-endpoint rate limiting** decorator

### Global Rate Limiting

```python
# api/app.py
from api.middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,
    exempt_paths=["/api/health", "/api/metrics"]
)
```

### Per-Endpoint Rate Limiting

```python
from api.middleware import EndpointRateLimiter

@router.post("/api/auth/login")
@EndpointRateLimiter(requests_per_minute=10)  # Stricter for login
async def login(request: Request, credentials: LoginCredentials):
    # Login logic...
    pass
```

### Rate Limit Headers

All responses include:
- `X-RateLimit-Limit`: Maximum requests allowed per minute
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

When rate limit is exceeded (429 response):
- `Retry-After`: Seconds until rate limit resets

---

## 3. Input Validation Middleware

**File**: `api/middleware/input_validator.py`
**Class**: `InputValidationMiddleware`, `RequestSanitizer`

### Protections

1. **SQL Injection** - Blocks SQL patterns (`UNION SELECT`, `DROP TABLE`, etc.)
2. **XSS (Cross-Site Scripting)** - Blocks script injection (`<script>`, `javascript:`, etc.)
3. **Path Traversal** - Blocks directory traversal (`../`, `..\`)
4. **Command Injection** - Validates against shell commands

### Blocked Patterns

**SQL Injection**:
- `UNION SELECT`, `DROP TABLE`, `EXEC()`, SQL comments (`--`, `#`, `/* */`)
- `OR 1=1`, `AND 1=1`, `INSERT INTO`, `UPDATE SET`, `DELETE FROM`

**XSS**:
- `<script>` tags, `javascript:` protocol
- Event handlers (`onerror=`, `onload=`, `onclick=`, `onmouseover=`)
- `<iframe>`, `<embed>`, `<object>` tags

**Path Traversal**:
- `../` (Unix), `..\` (Windows)

### Usage

```python
# api/app.py
from api.middleware import InputValidationMiddleware

app.add_middleware(InputValidationMiddleware, strict_mode=False)
```

### Request Sanitization

```python
from api.middleware import RequestSanitizer, sanitize

# In endpoints
sanitizer = RequestSanitizer()
safe_data = sanitizer.sanitize(user_input)

# Or use convenience function
safe_string = sanitize("<script>alert('xss')</script>")
# Returns: "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
```

---

## 4. CSRF Protection Middleware

**File**: `api/middleware/csrf.py`
**Class**: `CSRFProtectionMiddleware`
**Status**: ⚠️ Optional - Requires frontend integration

### How It Works

1. On first request, generates CSRF token and sets in cookie (`csrf_token`)
2. Frontend reads token from cookie
3. Frontend includes token in `X-CSRF-Token` header for state-changing requests
4. Middleware validates token matches cookie

### Protects Against

- Cross-Site Request Forgery attacks
- Unauthorized state-changing requests from malicious sites

### Frontend Integration

```javascript
// Add to axios interceptor
axios.interceptors.request.use(config => {
  // Get CSRF token from cookie
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1];

  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }

  return config;
});
```

### Enable in Production

```python
# api/app.py
from api.middleware import CSRFProtectionMiddleware

app.add_middleware(
    CSRFProtectionMiddleware,
    exempt_paths=["/api/auth/login", "/api/auth/signup", "/api/health"]
)
```

---

## 5. Authentication Middleware

**File**: `api/middleware/auth.py`
**Class**: `AuthMiddleware`

### Features

- **Always-on authentication** (no localhost bypass)
- **Session-based auth** with secure cookies
- **JWT token support**
- **Public endpoint exemptions**
- **Tenant key validation**

### Public Endpoints

The following endpoints bypass authentication:
- `/health`, `/docs`, `/redoc`, `/openapi.json`
- `/api/auth/login`, `/api/auth/create-first-admin`
- `/api/setup/status`, `/api/v1/config/frontend`
- `/mcp` (MCP-over-HTTP with X-API-Key)
- `/api/download/*` (token-based downloads)

All other endpoints **require authentication**.

---

## 6. CORS Protection

**Current**: FastAPI's `CORSMiddleware`
**Future**: Enhanced `CORSSecurityMiddleware` (api/middleware/security.py)

### Current Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Enhanced CORS (Optional)

```python
from api.middleware import CORSSecurityMiddleware

app.add_middleware(
    CORSSecurityMiddleware,
    allowed_origins=["http://localhost:3000", "https://yourdomain.com"]
)
```

---

## 7. Database-Level Security

### Tenant Isolation

- **Row-level security** via `TenantMixin`
- **Tenant key validation** on every query
- **Zero cross-tenant leakage**
- **SQLAlchemy ORM** prevents SQL injection

### Password Security

- **bcrypt hashing** with salt
- **Strong KDF** (Key Derivation Function)
- **No password storage in logs**

---

## Security Testing

### Run Security Tests

```bash
# All security tests
pytest tests/security/ -v

# OWASP Top 10 compliance audit
pytest tests/security/test_owasp_audit.py -v

# Comprehensive security suite
pytest tests/security/test_security_comprehensive.py -v
```

### Test Coverage

- ✅ Security headers validation
- ✅ Rate limiting enforcement
- ✅ Input validation (SQL injection, XSS, path traversal)
- ✅ CSRF protection (when enabled)
- ✅ OWASP Top 10 compliance
- ✅ Integration tests

---

## Production Deployment Checklist

### Required

- [ ] Deploy behind HTTPS reverse proxy (nginx, Cloudflare, etc.)
- [ ] Verify HSTS header is working (`Strict-Transport-Security`)
- [ ] Redirect HTTP → HTTPS
- [ ] Use valid SSL certificate
- [ ] Configure CORS for production origins
- [ ] Tune rate limits based on usage patterns
- [ ] Set up log aggregation and monitoring
- [ ] Enable security alerts (rate limit violations, auth failures)

### Optional (Recommended)

- [ ] Enable CSRF protection (requires frontend integration)
- [ ] Add per-endpoint rate limiting for sensitive endpoints
- [ ] Implement Redis-backed rate limiter for distributed systems
- [ ] Set up security monitoring dashboard
- [ ] Schedule regular security audits
- [ ] Enable Web Application Firewall (WAF)

---

## Security Monitoring

### Events to Monitor

1. **Rate Limit Violations**
   - Logged in `api/middleware/rate_limiter.py`
   - Pattern: `Rate limit exceeded for IP: {ip}`

2. **Authentication Failures**
   - Logged in `api/middleware/auth.py`
   - Pattern: `Auth result: authenticated=False`

3. **Input Validation Failures**
   - Logged in `api/middleware/input_validator.py`
   - Pattern: `Blocked unsafe query parameter`

4. **Path Traversal Attempts**
   - Logged in `api/middleware/input_validator.py`
   - Pattern: `Blocked path traversal attempt`

### Recommended Monitoring Tools

- **Log Aggregation**: ELK Stack, Datadog, Splunk
- **Alerts**: PagerDuty, Opsgenie
- **Metrics**: Prometheus + Grafana
- **APM**: New Relic, Datadog APM

---

## Configuration

### Environment Variables

```bash
# Rate limiting
API_RATE_LIMIT=100  # Requests per minute (default: 300)
DISABLE_RATE_LIMIT=false  # Set to true to disable (dev only)

# Security
HTTPS_ONLY=true  # Enforce HTTPS (production)
```

### Middleware Configuration

All middleware is configured in `api/app.py`. See inline comments for details.

---

## Troubleshooting

### Issue: Rate Limiting Too Strict

**Solution**: Increase rate limit or exempt specific endpoints

```python
# Increase global limit
app.add_middleware(RateLimitMiddleware, requests_per_minute=300)

# Or exempt endpoints
rate_limiter.exempt_paths.append("/api/your-endpoint")
```

### Issue: CSRF Blocking Legitimate Requests

**Solution**: Verify frontend sends `X-CSRF-Token` header

```javascript
// Check cookie exists
console.log(document.cookie);  // Should include csrf_token

// Check header is sent
console.log(request.headers['X-CSRF-Token']);
```

### Issue: Input Validation Blocking Legitimate Input

**Solution**: Review patterns and adjust if needed

```python
# Disable strict mode
app.add_middleware(InputValidationMiddleware, strict_mode=False)

# Or sanitize instead of blocking
from api.middleware import sanitize
safe_input = sanitize(user_input)
```

---

## References

- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [MDN Security Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers#security)
- [Content Security Policy (CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [HTTP Strict Transport Security (HSTS)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security)

---

**Last Updated**: 2025-11-12
**Handover**: 0129c - Security Hardening & OWASP Compliance
**Next Review**: Before Production Deployment
