# Handover 0036: Cookie Domain Whitelist for Cross-Port Authentication

**Handover ID**: 0036
**Creation Date**: 2025-10-19
**Target Date**: 2025-10-22 (3 day timeline)
**Priority**: HIGH
**Type**: SECURITY + UX ENHANCEMENT
**Estimated Complexity**: 70 minutes (1.2 hours)
**Status**: NOT STARTED
**Dependencies**: Handover 0035 (Unified Installer)

---

## 1. Context and Background

### Current Problem

**Authentication cookie transmission fails across different deployment contexts:**

**Symptom**: After successful login or admin account creation, users get stuck at `/login?redirect=/` with repeated 401 errors:
```
[AUTH] get_current_user called - path: /api/auth/me, cookie: False, api_key: False
[AUTH] FAILED - No valid authentication found
```

**Root Cause**: Cookie domain mismatch prevents cross-port cookie sharing.

**Technical Details**:
- Frontend runs on port `7274` (e.g., `http://10.1.0.164:7274`)
- Backend API runs on port `7272` (e.g., `http://10.1.0.164:7272`)
- Cookies set with `domain=None` are host+port specific
- Browser won't send cookies from `:7272` to `:7274` without explicit domain

**Current Cookie Setting** (`api/endpoints/auth.py:270`):
```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=False,
    samesite="lax",
    path="/",
    domain=None,  # ❌ TOO STRICT - prevents cross-port sharing
)
```

### User Impact

**Broken Scenarios**:
1. ❌ **LAN Access**: User installs on `10.1.0.164`, can't login from other machines
2. ❌ **Domain Deployment**: User deploys to `app.example.com`, authentication fails
3. ✅ **Localhost Only**: Works (single-port browser behavior)

**User Frustration**:
- Fresh install completes successfully
- Admin account created
- Redirected to login
- Login succeeds (200 OK)
- Immediately 401 on `/api/auth/me`
- Infinite redirect loop to login page

### Why This Wasn't Caught Earlier

1. **Development testing**: Mostly localhost-only (works with `domain=None`)
2. **Port consolidation**: Early v2.0 used single port (no cross-port issue)
3. **Handover 0035**: Split ports (7272 API, 7274 frontend) exposed the bug
4. **Fresh install focus**: Testing emphasized first-run flow, not multi-context deployment

---

## 2. Security Analysis

### Attack Vectors Considered

#### 1. Host Header Injection
**Attack**: Malicious actor sends `Host: evil.com` to steal cookies

**Mitigation**:
- Whitelist validation against config
- CORS enforcement (existing)
- SameSite=lax (prevents CSRF)

#### 2. Subdomain Cookie Theft
**Attack**: If `domain=example.com`, cookies visible to `evil.example.com`

**Mitigation**:
- IP addresses only (no subdomains possible)
- Explicit whitelist (no wildcard domains)
- Admin-controlled list

#### 3. Cookie Exposure
**Risk**: `secure=False` allows HTTP transmission

**Acceptable**: LAN deployment with firewall defense-in-depth

### Defense-in-Depth Layers

1. **CORS Whitelist** - Only approved origins receive responses
2. **Cookie Domain Whitelist** - Only approved domains get cookies
3. **SameSite=lax** - Prevents cross-site request forgery
4. **httpOnly=True** - Prevents JavaScript access (XSS protection)
5. **Rate Limiting** - 60 req/min prevents brute force
6. **OS Firewall** - Network access control (user configurable)

---

## 3. Technical Solution

### Phase 1: Cookie Domain Logic (5 minutes)

**File**: `api/endpoints/auth.py`

**Update `login()` endpoint** (lines 197-299):
```python
# SECURITY: Cookie domain handling for cross-port authentication
# Background: Frontend (port 7274) needs cookies set by API (port 7272)
#
# Domain behavior:
#   - domain=None → Strict (exact host:port match) - MOST SECURE
#   - domain="10.1.0.164" → Loose (all ports on that IP) - NEEDED for cross-port
#
# Security considerations:
#   1. NEVER trust user-supplied Host header directly (Host header injection risk)
#   2. IP addresses don't have subdomains, so domain=IP is relatively safe
#   3. CORS whitelist provides defense-in-depth
#   4. SameSite=lax prevents CSRF
#
# For production with HTTPS domains, validate against whitelist!
cookie_domain = None
if request and request.client:
    # Get the host from the request (e.g., "10.1.0.164:7272" or "localhost:7272")
    host_header = request.headers.get("host", "")
    if host_header:
        # Strip port if present (e.g., "10.1.0.164:7272" -> "10.1.0.164")
        host_only = host_header.split(":")[0]

        # SECURITY: Only set domain for IP addresses (no subdomains)
        # For localhost/127.0.0.1, use domain=None for strictest security
        # For domain names (production), validate against whitelist
        import re
        is_ip_address = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host_only)

        # Load whitelist from config
        from giljo_mcp.config_manager import get_config
        config = get_config()
        allowed_domains = config.get("security", {}).get("cookie_domains", [])

        if is_ip_address and host_only not in ("127.0.0.1",):
            # Safe: IP address (no subdomain risk)
            cookie_domain = host_only
        elif host_only in allowed_domains:
            # Explicitly whitelisted domain
            cookie_domain = host_only
        # else: domain=None (strictest - localhost or unknown domain)

# Set httpOnly cookie (session cookie - expires on browser close)
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=False,  # Set to True in production with HTTPS
    samesite="lax",
    path="/",  # Accessible from all paths (frontend and API)
    domain=cookie_domain,  # Set to validated domain for cross-port sharing
)
```

**Update `create_first_admin()` endpoint** (lines 640-850):
- Apply identical cookie domain logic
- Ensures admin creation flow works correctly

**Breaking Risk**: 🟢 **0%** - Reading optional config field with safe fallback

---

### Phase 2: Config Schema Update (5 minutes)

**File**: `installer/core/config.py`

**Update `_generate_security_config()` method** (lines 504-561):

```python
def _generate_security_config(self) -> Dict[str, Any]:
    """Generate security configuration for v3.0 unified architecture."""
    # ... existing CORS logic ...

    # Cookie domain whitelist (Handover 0036)
    # Domains explicitly allowed for cookie sharing (cross-port auth)
    cookie_domains = []

    # Add installer-selected external host if it's a domain name
    external_host = self.settings.get("external_host", "localhost")
    if external_host and external_host not in ("localhost", "127.0.0.1"):
        # Check if it's a domain name (not IP)
        import re
        is_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', external_host)
        if not is_ip:
            cookie_domains.append(external_host)

    security_config = {
        "cors": {
            "allowed_origins": cors_origins
        },
        "cookie_domains": cookie_domains,  # NEW: Whitelist for cookie domain setting
        "api_keys": {
            "info": "API keys optional for localhost (auto-login enabled)",
            "generate_command": "python -c \"import secrets; print(f'giljo_{secrets.token_urlsafe(32)}')\"",
        },
        "rate_limiting": {
            "enabled": True,
            "requests_per_minute": 60,
        },
    }

    return security_config
```

**Breaking Risk**: 🟢 **0%** - New optional field with empty list default

---

### Phase 3: Installer Domain Prompt (10 minutes)

**File**: `install.py`

**Update `ask_installation_questions()` method** (lines 232-343):

**Add after external_host selection** (around line 280):

```python
# Ask if user wants to add a domain name for cookie whitelist
if self.settings['external_host'] not in ('localhost', '127.0.0.1'):
    # Check if external_host is an IP address
    import re
    is_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
                     self.settings['external_host'])

    if is_ip:
        print(f"\n{Fore.CYAN}[Optional] Domain Name Configuration{Style.RESET_ALL}")
        print(f"If you plan to access this server via a domain name (e.g., app.example.com),")
        print(f"enter it now to enable cookie-based authentication.")
        print(f"Leave blank if you'll only use IP addresses.")

        domain_input = input(f"\n{Fore.YELLOW}Domain name (optional): {Style.RESET_ALL}").strip()

        if domain_input:
            # Store for config generation
            self.settings['custom_domain'] = domain_input
            self._print_success(f"Domain '{domain_input}' will be added to authentication whitelist")
        else:
            self._print_info("Skipping domain configuration - IP-only deployment")
```

**Breaking Risk**: 🟢 **0%** - Optional prompt, Enter to skip

---

### Phase 4: Admin Settings UI (30 minutes)

**File**: `frontend/src/views/SystemSettings.vue`

**Add new Security tab** (after Integrations tab, line ~20):

```vue
<v-tab value="security">
  <v-icon start>mdi-shield-lock</v-icon>
  Security
</v-tab>
```

**Add Security tab content** (in `<v-window>` section):

```vue
<!-- Security Settings -->
<v-window-item value="security">
  <v-card>
    <v-card-title>Security Configuration</v-card-title>
    <v-card-subtitle>Manage authentication and access control</v-card-subtitle>

    <v-card-text>
      <!-- Cookie Domains Whitelist -->
      <h3 class="text-h6 mb-3">Cookie Domain Whitelist</h3>
      <p class="text-body-2 mb-4">
        Domains allowed for cross-port cookie-based authentication.
        Add domain names here if users access the system via URLs (not IPs).
      </p>

      <v-alert type="info" variant="tonal" class="mb-4">
        <strong>Note:</strong> IP addresses are automatically allowed.
        Only add domain names here (e.g., app.example.com).
      </v-alert>

      <!-- Domain List -->
      <v-list v-if="cookieDomains.length > 0" class="mb-4">
        <v-list-item
          v-for="domain in cookieDomains"
          :key="domain"
          class="border-sm mb-2"
        >
          <v-list-item-title>{{ domain }}</v-list-item-title>
          <template v-slot:append>
            <v-btn
              icon="mdi-delete"
              size="small"
              color="error"
              variant="text"
              @click="removeCookieDomain(domain)"
            ></v-btn>
          </template>
        </v-list-item>
      </v-list>

      <v-alert v-else type="warning" variant="tonal" class="mb-4">
        No domain names configured. IP-based access only.
      </v-alert>

      <!-- Add Domain Form -->
      <v-row>
        <v-col cols="12" md="8">
          <v-text-field
            v-model="newDomain"
            label="Domain Name"
            placeholder="app.example.com"
            hint="Enter domain without http:// or port"
            persistent-hint
            :rules="[validateDomain]"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="4">
          <v-btn
            color="primary"
            block
            @click="addCookieDomain"
            :disabled="!newDomain || !validateDomain(newDomain)"
          >
            <v-icon start>mdi-plus</v-icon>
            Add Domain
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</v-window-item>
```

**Add Vue script logic**:

```javascript
// Data
const cookieDomains = ref([])
const newDomain = ref('')

// Methods
const loadCookieDomains = async () => {
  try {
    const response = await api.settings.getCookieDomains()
    cookieDomains.value = response.data.domains || []
  } catch (error) {
    console.error('Failed to load cookie domains:', error)
  }
}

const addCookieDomain = async () => {
  try {
    await api.settings.addCookieDomain(newDomain.value)
    cookieDomains.value.push(newDomain.value)
    newDomain.value = ''
    // Show success message
  } catch (error) {
    console.error('Failed to add domain:', error)
    // Show error message
  }
}

const removeCookieDomain = async (domain) => {
  try {
    await api.settings.removeCookieDomain(domain)
    cookieDomains.value = cookieDomains.value.filter(d => d !== domain)
    // Show success message
  } catch (error) {
    console.error('Failed to remove domain:', error)
    // Show error message
  }
}

const validateDomain = (value) => {
  if (!value) return true
  // Basic domain validation
  const domainRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/
  return domainRegex.test(value) || 'Invalid domain name'
}

// Load on mount
onMounted(() => {
  loadCookieDomains()
})
```

**Breaking Risk**: 🟡 **5%** - New tab might need CSS tweaks

---

### Phase 5: Settings API Endpoints (20 minutes)

**File**: `api/endpoints/user_settings.py` (currently empty)

**Add CRUD endpoints**:

```python
"""
User Settings endpoints for authenticated, per-user operations.

Handover 0036: Cookie domain whitelist management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import List
import yaml
from pathlib import Path

from src.giljo_mcp.auth.dependencies import get_current_active_user, require_admin
from src.giljo_mcp.models import User

router = APIRouter()


class CookieDomainsResponse(BaseModel):
    """Response with list of allowed cookie domains"""
    domains: List[str]


class AddCookieDomainRequest(BaseModel):
    """Request to add a domain to cookie whitelist"""
    domain: str = Field(..., min_length=3, max_length=255)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate domain format"""
        import re
        # Basic domain validation
        domain_regex = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(domain_regex, v):
            raise ValueError("Invalid domain name format")

        # Prevent IP addresses (they're automatically allowed)
        ip_regex = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if re.match(ip_regex, v):
            raise ValueError("IP addresses are automatically allowed - only add domain names")

        return v


class RemoveCookieDomainRequest(BaseModel):
    """Request to remove a domain from cookie whitelist"""
    domain: str


@router.get("/settings/cookie-domains", response_model=CookieDomainsResponse, tags=["user-settings"])
async def get_cookie_domains(current_user: User = Depends(require_admin)):
    """
    Get list of allowed cookie domains (admin only).

    Returns the current whitelist of domain names allowed for cookie-based authentication.
    IP addresses are automatically allowed and not shown in this list.
    """
    config_path = Path.cwd() / "config.yaml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        domains = config.get("security", {}).get("cookie_domains", [])
        return CookieDomainsResponse(domains=domains)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {str(e)}"
        )


@router.post("/settings/cookie-domains", status_code=status.HTTP_201_CREATED, tags=["user-settings"])
async def add_cookie_domain(
    request: AddCookieDomainRequest,
    current_user: User = Depends(require_admin)
):
    """
    Add a domain to cookie whitelist (admin only).

    Allows the specified domain to receive authentication cookies.
    Use this when deploying the system behind a domain name.
    """
    config_path = Path.cwd() / "config.yaml"

    try:
        # Load current config
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Get or create cookie_domains list
        if "security" not in config:
            config["security"] = {}
        if "cookie_domains" not in config["security"]:
            config["security"]["cookie_domains"] = []

        # Add domain if not already present
        if request.domain not in config["security"]["cookie_domains"]:
            config["security"]["cookie_domains"].append(request.domain)

        # Write updated config
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return {"message": f"Domain '{request.domain}' added to cookie whitelist"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.delete("/settings/cookie-domains", tags=["user-settings"])
async def remove_cookie_domain(
    request: RemoveCookieDomainRequest,
    current_user: User = Depends(require_admin)
):
    """
    Remove a domain from cookie whitelist (admin only).

    Revokes cookie authentication access for the specified domain.
    """
    config_path = Path.cwd() / "config.yaml"

    try:
        # Load current config
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Remove domain
        domains = config.get("security", {}).get("cookie_domains", [])
        if request.domain in domains:
            domains.remove(request.domain)
            config["security"]["cookie_domains"] = domains

            # Write updated config
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            return {"message": f"Domain '{request.domain}' removed from cookie whitelist"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{request.domain}' not found in whitelist"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )
```

**Breaking Risk**: 🟢 **0%** - New endpoints in empty router

---

### Phase 6: Frontend API Service (5 minutes)

**File**: `frontend/src/services/api.js`

**Add to settings section** (around line 193):

```javascript
// Settings & Configuration
settings: {
  get: () => apiClient.get('/api/v1/config/'),
  update: (data) => apiClient.put('/api/v1/config/', data),
  getProduct: () => apiClient.get('/api/v1/config/product/'),

  // Cookie domain whitelist management (Handover 0036)
  getCookieDomains: () => apiClient.get('/api/v1/user/settings/cookie-domains'),
  addCookieDomain: (domain) => apiClient.post('/api/v1/user/settings/cookie-domains', { domain }),
  removeCookieDomain: (domain) => apiClient.delete('/api/v1/user/settings/cookie-domains', { data: { domain } }),
},
```

**Breaking Risk**: 🟢 **0%** - Adding to existing object

---

## 4. Implementation Plan

### Recommended Approach: **Phased Implementation**

**Phase 1** (20 min): Core functionality (auth.py + config.py)
- Update cookie domain logic
- Add config schema field
- **TEST**: Login works on LAN IPs

**Phase 2** (10 min): Installer integration
- Add optional domain prompt
- **TEST**: Fresh install with domain

**Phase 3** (40 min): Admin UI + API
- Add Security tab
- Create CRUD endpoints
- **TEST**: Add/remove domains via UI

**Breaking Risk by Phase**:
- Phase 1: 🟢 **0%** (core logic, backwards compatible)
- Phase 2: 🟢 **0%** (optional installer prompt)
- Phase 3: 🟡 **5%** (new UI component, minor styling risk)

---

## 5. Testing Requirements

### Unit Tests

**Create**: `tests/api/test_cookie_domain_whitelist.py`

```python
"""Test cookie domain whitelist functionality"""
import pytest
from api.endpoints.auth import login, create_first_admin

def test_cookie_domain_localhost():
    """domain=None for localhost"""
    # Mock request with Host: localhost:7272
    # Assert cookie domain is None

def test_cookie_domain_lan_ip():
    """domain=<IP> for LAN addresses"""
    # Mock request with Host: 10.1.0.164:7272
    # Assert cookie domain is "10.1.0.164"

def test_cookie_domain_whitelisted():
    """domain=<domain> for whitelisted domains"""
    # Mock config with cookie_domains: ["app.example.com"]
    # Mock request with Host: app.example.com:7272
    # Assert cookie domain is "app.example.com"

def test_cookie_domain_not_whitelisted():
    """domain=None for non-whitelisted domains"""
    # Mock config with empty cookie_domains
    # Mock request with Host: evil.com:7272
    # Assert cookie domain is None
```

**Create**: `tests/installer/test_cookie_domain_config.py`

```python
"""Test config generation includes cookie_domains"""
def test_config_generates_cookie_domains_field():
    """Ensure security.cookie_domains exists in generated config"""

def test_installer_adds_custom_domain():
    """Ensure installer prompt adds domain to config"""
```

### Integration Tests

**Manual Test Scenarios**:

1. **Localhost Deployment**
   - Install with localhost
   - Create admin
   - Login
   - ✅ Should work (domain=None)

2. **LAN IP Deployment**
   - Install on 10.1.0.164
   - Access from 10.1.0.200
   - Create admin
   - Login
   - ✅ Should work (domain="10.1.0.164")

3. **Domain Deployment**
   - Install with domain "app.test.local"
   - Add to /etc/hosts
   - Access via app.test.local:7274
   - Add domain to whitelist (installer or admin UI)
   - Login
   - ✅ Should work (domain="app.test.local")

4. **Non-Whitelisted Domain**
   - Access via non-whitelisted domain
   - Login
   - ❌ Should fail gracefully (domain=None, strict mode)

### Performance Tests

**Cookie domain validation overhead**: < 1ms per request

---

## 6. Dependencies and Blockers

### Dependencies

✅ **Handover 0035** - Unified installer (completed)
✅ **Existing CORS config** - Pattern already established
✅ **Admin settings page** - Already exists (`SystemSettings.vue`)

### Known Blockers

**NONE** - All dependencies satisfied

### Questions Needing Answers

**NONE** - Implementation approach finalized

---

## 7. Success Criteria

### Definition of Done

- [ ] Cookie domain logic reads from config whitelist
- [ ] Config schema includes `security.cookie_domains` field
- [ ] Installer prompts for optional domain name
- [ ] Admin UI has Security tab with domain management
- [ ] API endpoints for CRUD operations on whitelist
- [ ] Unit tests pass (cookie logic, config generation)
- [ ] Integration tests pass (localhost, LAN, domain)
- [ ] Manual testing on all three deployment contexts
- [ ] Documentation updated (installation guide, admin manual)
- [ ] Code committed with handover reference
- [ ] Handover moved to `/handovers/completed/` with `-C` suffix

### Acceptance Tests

1. **Fresh Install - Localhost**
   - Run `python install.py`
   - Select localhost
   - Login works ✅

2. **Fresh Install - LAN IP**
   - Run `python install.py`
   - Select network IP (e.g., 10.1.0.164)
   - Access from another device
   - Login works ✅

3. **Fresh Install - Domain**
   - Run `python install.py`
   - Select custom domain option
   - Enter "app.example.com"
   - Configure DNS/hosts file
   - Login works ✅

4. **Admin UI - Add Domain**
   - Go to Settings → Security
   - Add "new.example.com"
   - Restart server
   - Access via new.example.com
   - Login works ✅

5. **Admin UI - Remove Domain**
   - Remove domain from whitelist
   - Restart server
   - Access via removed domain
   - Login fails (domain=None) ✅

---

## 8. Rollback Plan

### If Things Go Wrong

**Rollback Steps**:

1. **Revert cookie logic**:
   ```bash
   git checkout HEAD~1 -- api/endpoints/auth.py
   ```

2. **Remove config field** (manual edit):
   ```yaml
   # Remove from config.yaml:
   security:
     cookie_domains: []  # ← Delete this line
   ```

3. **Restart server**:
   ```bash
   python startup.py
   ```

**Fallback Behavior**:
- Config field missing → Empty list → IP addresses still work
- Cookie domain=None → Localhost-only mode (safe default)

**Recovery Time**: < 5 minutes

---

## 9. Additional Resources

### Related Files

**Authentication**:
- `api/endpoints/auth.py:197-299` - `/login` endpoint
- `api/endpoints/auth.py:640-850` - `/create-first-admin` endpoint
- `src/giljo_mcp/auth/jwt_manager.py` - JWT token generation

**Configuration**:
- `installer/core/config.py:504-561` - Security config generation
- `config.yaml:90-105` - Live config (security section)

**Frontend**:
- `frontend/src/views/SystemSettings.vue` - Admin settings page
- `frontend/src/services/api.js` - API service layer

### Related Handovers

- **Handover 0035**: Unified installer architecture (dependency)
- **Handover 0034**: First admin creation (auth context)
- **Handover 0032**: MCP over HTTP (port separation introduced)

### External Resources

**Cookie Security Best Practices**:
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [MDN Set-Cookie Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie)
- [SameSite Cookie Explanation](https://web.dev/samesite-cookies-explained/)

**Similar Implementations**:
- Django CSRF_COOKIE_DOMAIN
- Express.js session domain configuration
- FastAPI cookie handling examples

---

## 10. Progress Updates

### 2025-10-19 - Initial Planning
**Status:** Not Started
**Work Done:**
- Problem diagnosed (cross-port cookie authentication failure)
- Security analysis completed
- Implementation plan drafted
- Breaking risk assessment: 1-2% (minimal)
- Estimated time: 70 minutes

**Next Steps:**
- Implement Phase 1 (cookie domain logic)
- Test on LAN deployment
- Implement Phase 2 (installer integration)
- Implement Phase 3 (admin UI + API)
- Comprehensive testing
- Documentation update

**Blockers:** None

---

## 11. Implementation Notes

### Code Quality Standards

**Follow existing patterns**:
- Use `pathlib.Path()` for all file operations
- Match existing code style (Black formatting)
- Use existing validation patterns (Pydantic)
- Follow v3.0 unified architecture principles

**Security First**:
- Validate all user input (domain regex)
- Whitelist approach (explicit allow list)
- Defense-in-depth (CORS + cookie domain + SameSite)
- Fail-safe defaults (domain=None if unknown)

**User Experience**:
- Optional prompts (Enter to skip)
- Clear error messages
- Admin UI feedback (success/error toasts)
- Minimal configuration required

---

## 12. Open Questions

**NONE** - All design decisions finalized

---

## Final Checklist

**Before Starting:**
- [x] Git status checked
- [x] Related files identified
- [x] Security implications analyzed
- [x] Breaking risk assessed (1-2%)
- [x] Implementation plan detailed
- [x] Testing strategy defined
- [x] Success criteria specified

**During Implementation:**
- [ ] Phase 1 complete (cookie logic)
- [ ] Phase 2 complete (installer)
- [ ] Phase 3 complete (admin UI)
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing on all contexts

**After Completion:**
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Git commit created
- [ ] Handover moved to `/handovers/completed/0036_...-C.md`

---

**Remember:** This handover fixes a critical UX blocker (authentication loop) and enables flexible deployment (localhost, LAN, domain). The implementation is low-risk (1-2% breaking probability) with clear rollback path (5 min recovery).

Take care to validate domain input and maintain security-first approach throughout implementation.
