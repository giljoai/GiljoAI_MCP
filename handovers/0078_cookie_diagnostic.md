# Cookie Diagnostic Steps for Task Save Issue

## Problem
After login, authentication works initially but subsequent API requests fail with "Cookie header present: False"

## Diagnostic Steps

### 1. Check Browser Cookies (CRITICAL)
1. Open DevTools (F12) → **Application** tab → **Cookies** → `http://10.1.0.164:7274`
2. Look for cookie named `access_token`
3. **Check these fields**:
   - **Exists?**: Yes/No
   - **Value**: Should be a long JWT token
   - **Domain**: Should be `.10.1.0.164` or `10.1.0.164`
   - **Path**: Should be `/`
   - **SameSite**: Should be `Lax`
   - **HttpOnly**: Should be `✓` (checked)
   - **Secure**: Should be blank (not checked)

### 2. Check Network Requests
1. DevTools (F12) → **Network** tab
2. Try to create a task
3. Find the `POST /api/v1/tasks/` request
4. Click on it → **Headers** tab
5. **Request Headers** section:
   - Look for `Cookie:` header
   - Should contain `access_token=eyJhbGc...`
6. **If Cookie header is missing**:
   - Cookie is not being sent by browser
   - Likely a SameSite or domain issue

### 3. Backend Server Check
From backend logs, the issue is:
```
23:29:43 - INFO - [AuthMiddleware] Cookie header present: False
```

This means the backend is **NOT receiving the cookie** from the browser.

## Root Causes & Fixes

### Issue A: Cookie Domain Mismatch
**Symptom**: Cookie set with wrong domain attribute

**Check backend logs during login** for:
```
Cookie domain set to IP address (safe): 10.1.0.164
```

If you see this, cookie domain is correct.

### Issue B: SameSite=Lax Blocking Cookies
**Symptom**: Cross-site request blocking cookies

**Workaround**: Change SameSite to "none" (requires HTTPS in production)

**Fix**: Edit `api/endpoints/auth.py` line 408:
```python
# FROM:
samesite="lax",

# TO:
samesite="none",  # Allows cross-site cookies
secure=True,      # Required with SameSite=none (may need to disable for HTTP)
```

⚠️ **WARNING**: `SameSite=none` requires `secure=True`, which requires HTTPS

### Issue C: Browser Third-Party Cookie Settings
**Symptom**: Browser blocking third-party cookies

**Check**: Chrome Settings → Privacy → Third-party cookies → Should be enabled

### Issue D: Port Mismatch (Frontend:7274 vs API:7272)
**Symptom**: Cookie set on port 7272 not accessible on port 7274

**Current Setup**:
- Frontend: http://10.1.0.164:7274
- API: http://10.1.0.164:7272

Cookie domain is set to `10.1.0.164` (no port), so it SHOULD work across ports.

**Verify**: Check cookie domain in browser DevTools

## Quick Fix Recommendation

**Try changing SameSite to "none" temporarily** to diagnose:

```python
# api/endpoints/auth.py line 403-412
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=False,  # Keep False for HTTP testing
    samesite="none",  # CHANGED: Allow cross-origin cookies
    path="/",
    domain=cookie_domain,
)
```

Then restart API server and test again.

## Expected Behavior After Fix

1. Login → Cookie stored in browser
2. Create task → Cookie sent with request
3. Backend logs: `[AuthMiddleware] Cookie header present: True`
4. Task saves successfully with correct product_id
