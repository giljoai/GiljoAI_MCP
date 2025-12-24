# Handover 1007: Nonce-Based CSP Implementation

**Date**: 2025-12-18
**Status**: Pending
**Parent**: 1000 (Greptile Remediation)
**Risk Level**: HIGH
**Tier**: 3 (Staging + Full Test Suite)
**Estimated Effort**: 8 hours

---

## Mission

Replace `unsafe-inline` and `unsafe-eval` directives in Content Security Policy (CSP) with nonce-based approach to eliminate critical security vulnerabilities while maintaining full frontend functionality.

## Context

**Current Vulnerability**: CSP allows arbitrary inline scripts and eval() usage via `unsafe-inline` and `unsafe-eval` directives, creating XSS attack vectors.

**Target State**: Cryptographically secure nonces for all inline scripts/styles, eliminating unsafe directives while preserving Vue.js functionality.

**Cascade Risk**: HIGH - Misconfiguration can break entire frontend rendering, dynamic imports, and WebSocket connections.

---

## Files to Modify

### Backend
- `api/middleware/security.py` - Add nonce generation and CSP header modification
- `api/app.py` - May need to pass nonce to frontend template

### Frontend
- `frontend/index.html` - Add nonce attributes to inline scripts/styles
- `frontend/vite.config.js` - Configure Vite plugin for nonce injection

---

## Why This is HIGH Risk

1. **Vue.js Template Compilation**: Dev mode requires eval() for template compilation
2. **Inline Scripts**: Must match nonces exactly or components won't load
3. **Dynamic Imports**: Code splitting requires proper CSP configuration
4. **WebSocket Connections**: May be blocked if CSP misconfigured
5. **Cascading Failure**: Single CSP error can render entire dashboard unusable

---

## Pre-Implementation Research (MANDATORY)

### Phase 1: Code Analysis
```
1. mcp__serena__get_symbols_overview("api/middleware/security.py")
2. mcp__serena__find_symbol("CORSSecurityMiddleware", depth=2, include_body=True)
3. Read("api/middleware/security.py") - Full CSP header logic
4. Read("frontend/index.html") - Identify all inline scripts
5. Read("frontend/vite.config.js") - Current build configuration
```

### Phase 2: Vue.js Production Analysis
- Check if production build uses eval() (likely no - Vue compiler optimizes)
- Verify dynamic import strategy (Vite code splitting)
- Identify any inline event handlers in components

### Phase 3: Vite Plugin Research
- Investigate `vite-plugin-csp` or `vite-plugin-csp-guard`
- Validate nonce injection strategy for HMR (hot module reload)
- Confirm compatibility with Vue 3 + Vuetify

---

## Current CSP (Vulnerable)

```python
# api/middleware/security.py (current)
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # VULNERABLE
    "style-src 'self' 'unsafe-inline'; "                  # VULNERABLE
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self' ws: wss:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)
```

---

## Target CSP (Secure)

```python
# api/middleware/security.py (target)
import secrets

# Generate cryptographically secure nonce per request
nonce = secrets.token_urlsafe(16)

response.headers["Content-Security-Policy"] = (
    f"default-src 'self'; "
    f"script-src 'self' 'nonce-{nonce}'; "  # Nonce-based scripts
    f"style-src 'self' 'nonce-{nonce}'; "   # Nonce-based styles
    f"img-src 'self' data: blob:; "
    f"font-src 'self' data:; "
    f"connect-src 'self' ws: wss:; "
    f"frame-ancestors 'none'; "
    f"base-uri 'self'; "
    f"form-action 'self'"
)

# Inject nonce into response context for frontend template
response.headers["X-CSP-Nonce"] = nonce  # Or use template injection
```

---

## Implementation Phases

### Phase 1: Research (No Code Changes)

**Objective**: Understand current state and identify all inline code.

**Tasks**:
1. Document all inline scripts in `frontend/index.html`
2. Check Vue production build for eval() usage (`npm run build` + inspect dist/)
3. Identify Vite plugin options (vite-plugin-csp vs custom solution)
4. List all components with inline event handlers (if any)

**Deliverable**: Research document with findings and recommended approach.

---

### Phase 2: Backend (Nonce Generation)

**Objective**: Generate and inject nonces into CSP headers.

**Tasks**:
1. Add nonce generation to `CORSSecurityMiddleware.__call__()`
2. Store nonce in request state for template access
3. Modify CSP header to use nonce
4. Pass nonce to frontend via:
   - Option A: Custom header (`X-CSP-Nonce`)
   - Option B: Template injection (if using Jinja2)

**Code Example**:
```python
# api/middleware/security.py
async def __call__(self, scope, receive, send):
    if scope["type"] == "http":
        # Generate nonce per request
        nonce = secrets.token_urlsafe(16)
        scope["state"]["csp_nonce"] = nonce

        # Modify CSP header to use nonce
        response.headers["Content-Security-Policy"] = (
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            # ... rest of CSP
        )
```

**Verification**:
- Nonce changes on every request
- CSP header includes nonce
- No syntax errors in CSP

---

### Phase 3: Frontend (Nonce Injection)

**Objective**: Inject nonces into inline scripts and configure Vite.

**Tasks**:
1. Configure Vite plugin for nonce injection
2. Update `index.html` to use nonce placeholders
3. Ensure HMR (hot module reload) works in dev mode
4. Test production build with nonces

**Vite Configuration**:
```javascript
// frontend/vite.config.js
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    vue(),
    // CSP nonce plugin (research required for exact plugin)
    {
      name: 'csp-nonce-injection',
      transformIndexHtml(html) {
        // Inject nonce placeholder during build
        return html.replace(
          /<script>/g,
          '<script nonce="__CSP_NONCE__">'
        )
      }
    }
  ]
})
```

**index.html Updates**:
```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <!-- Nonce will be injected by backend -->
    <script nonce="__CSP_NONCE__">
      // Inline initialization code
    </script>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js" nonce="__CSP_NONCE__"></script>
  </body>
</html>
```

**Verification**:
- Dev server starts without errors
- Production build includes nonces
- HMR works in dev mode

---

### Phase 4: Testing (CRITICAL)

**Objective**: Verify all frontend functionality with new CSP.

**Test Checklist**:
- [ ] All Vue components render correctly
- [ ] No CSP violations in browser console
- [ ] Dynamic imports work (code splitting)
- [ ] WebSocket connections establish
- [ ] Vuetify components render
- [ ] StatusBoard components load
- [ ] Agent action buttons functional
- [ ] Message center updates in real-time
- [ ] Project launch workflow works
- [ ] Login/logout flows functional

**Browser Testing**:
1. Chrome DevTools → Console (check for CSP errors)
2. Chrome DevTools → Network (verify nonces in headers)
3. Firefox DevTools (cross-browser validation)

**E2E Test Suite**:
```bash
# Run full test suite
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Frontend E2E tests (if implemented)
cd frontend/
npm run test:e2e
```

**Verification Gates**:
1. ✅ Frontend builds successfully
2. ✅ All Vue components render
3. ✅ Zero CSP violations in console
4. ✅ Dynamic imports work
5. ✅ WebSocket connections unaffected
6. ✅ Full E2E test suite passes

---

## Rollback Plan

**If Critical Issues Found**:
1. Revert CSP to include `unsafe-inline` temporarily:
   ```python
   response.headers["Content-Security-Policy"] = (
       "script-src 'self' 'unsafe-inline'; "  # Temporary rollback
       # ... rest of CSP
   )
   ```
2. Document specific failure mode
3. Create focused fix for identified issue
4. Re-test and re-deploy

**Rollback Triggers**:
- Frontend fails to load
- CSP errors block critical functionality
- WebSocket connections fail
- E2E tests fail at >20% rate

---

## Success Criteria

### Security
- ✅ No `unsafe-inline` in CSP
- ✅ No `unsafe-eval` in CSP
- ✅ Nonces are cryptographically secure (16+ bytes)
- ✅ Nonces change per request

### Functionality
- ✅ All frontend components render
- ✅ Dynamic imports work
- ✅ WebSocket connections functional
- ✅ HMR works in dev mode

### Validation
- ✅ Security headers pass validation (securityheaders.com)
- ✅ Zero CSP violations in browser console
- ✅ E2E test suite passes

---

## Post-Implementation Documentation

### Update Required Docs
1. `docs/SECURITY.md` - Document nonce-based CSP approach
2. `docs/FRONTEND.md` - Explain Vite plugin configuration
3. `api/middleware/security.py` - Add inline comments for nonce logic

### Developer Guide
Create brief guide for adding inline scripts:
```markdown
## Adding Inline Scripts with CSP Nonces

When adding inline scripts to index.html:
1. Use nonce placeholder: `<script nonce="__CSP_NONCE__">`
2. Backend will inject actual nonce at runtime
3. Verify no CSP violations in browser console
```

---

## Related Handovers

- **1000**: Greptile Remediation (parent)
- **1001**: HSTS Configuration (completed)
- **1002**: CSP Upgrade-Insecure-Requests (completed)
- **1006**: X-Content-Type-Options Header (pending)

---

## Notes

- **Vite Plugin Research**: Must validate which CSP plugin works best with Vue 3 + Vuetify
- **Dev vs Production**: Dev mode may require different CSP (HMR uses eval in some cases)
- **Performance**: Nonce generation adds minimal overhead (<1ms per request)
- **Browser Support**: Nonces supported in all modern browsers (IE11 not supported anyway)

---

## Agent Assignments (Recommended)

- **Primary**: `network-security-engineer` (CSP expert)
- **Support**: `frontend-tester` (Vue.js validation)
- **Review**: `system-architect` (integration validation)
