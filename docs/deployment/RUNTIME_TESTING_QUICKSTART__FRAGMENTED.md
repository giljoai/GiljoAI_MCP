# Runtime Testing Quick Start Guide

**Purpose:** Execute service-dependent validation tests after configuration testing
**Prerequisites:** Configuration tests passed (Phase 3 complete)
**Estimated Time:** 30-60 minutes

---

## Before You Start

**Verify Prerequisites:**
```bash
cd C:/Projects/GiljoAI_MCP

# Check configuration is ready
cat config.yaml | grep "mode: server"
cat config.yaml | grep "server_ip: 10.1.0.118"

# Verify firewall rules exist
netsh advfirewall firewall show rule name="GiljoAI MCP API"
netsh advfirewall firewall show rule name="GiljoAI MCP Frontend"
```

Expected: All commands succeed, showing correct configuration.

---

## Step 1: Generate API Key (5 minutes)

### Generate Secure API Key
```bash
# Generate a secure API key
python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"
```

**Example Output:**
```
giljo_lan_xJ3kL9mNpQ7rT2vW8yZ4aB6cD1eF5gH0iJ2kL4mN6oP8qR0sT2uV4wX6yZ8aB0cD2eF4g
```

### Store API Key Securely

**Option A: Update config.yaml** (Recommended for testing)
```yaml
api_keys:
  require_for_modes:
    - server
    - lan
  keys:
    - name: "lan_deployment_key"
      key: "giljo_lan_[your-generated-key]"
      description: "LAN deployment key"
```

**Option B: Environment Variable**
```bash
# Windows
set GILJO_API_KEY=giljo_lan_[your-generated-key]

# Linux/Mac
export GILJO_API_KEY=giljo_lan_[your-generated-key]
```

**IMPORTANT:**
- Save the key securely (password manager)
- Do NOT commit to git
- Document key location

---

## Step 2: Start Services (2 minutes)

### Terminal 1: Start API Server
```bash
cd C:/Projects/GiljoAI_MCP
python api/run_api.py
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7272
```

**Verify API Started:**
- Server shows "Application startup complete"
- Listening on 0.0.0.0:7272 (all interfaces)
- No error messages

### Terminal 2: Start Frontend (Optional for API Testing)
```bash
cd C:/Projects/GiljoAI_MCP/frontend
npm run dev
```

**Expected Output:**
```
VITE v4.x ready in XXX ms
Local:   http://localhost:5173/
Network: http://10.1.0.118:5173/
```

**Note:** For API-only testing, frontend is optional. For full validation, start both.

---

## Step 3: Execute Runtime Tests (10-15 minutes)

### Test 1: Health Check (Localhost)
```bash
curl http://127.0.0.1:7272/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "deployment_mode": "server",
  "database": "connected"
}
```

✅ **PASS:** Status 200, JSON response with health data
❌ **FAIL:** Connection refused, 500 error, or no response

---

### Test 2: Health Check (LAN IP)
```bash
curl http://10.1.0.118:7272/health
```

**Expected Response:** Same as Test 1

✅ **PASS:** Same response as localhost test
❌ **FAIL:** Connection refused, timeout, or different response

**Note:** This verifies firewall allows LAN access

---

### Test 3: CORS Headers Validation
```bash
curl -H "Origin: http://10.1.0.118:7274" -I http://127.0.0.1:7272/health
```

**Expected Headers:**
```
HTTP/1.1 200 OK
access-control-allow-origin: http://10.1.0.118:7274
access-control-allow-credentials: true
```

✅ **PASS:** CORS headers present with correct origin
❌ **FAIL:** No CORS headers or wrong origin

---

### Test 4: Security Headers Check
```bash
curl -I http://127.0.0.1:7272/health
```

**Expected Headers:**
```
x-frame-options: DENY
x-content-type-options: nosniff
x-xss-protection: 1; mode=block
content-security-policy: default-src 'self'
```

✅ **PASS:** All security headers present
❌ **FAIL:** Missing security headers

---

### Test 5: API Authentication (Without Key)
```bash
curl http://127.0.0.1:7272/api/v1/projects
```

**Expected Response:**
```json
{
  "detail": "Not authenticated"
}
```

✅ **PASS:** 401 Unauthorized or 403 Forbidden
❌ **FAIL:** 200 OK (auth not enforced!)

---

### Test 6: API Authentication (With Key)
```bash
# Replace [YOUR-API-KEY] with your actual key
curl -H "X-API-Key: giljo_lan_[YOUR-API-KEY]" http://127.0.0.1:7272/api/v1/projects
```

**Expected Response:**
```json
{
  "projects": []
}
```

✅ **PASS:** 200 OK with JSON response
❌ **FAIL:** 401 Unauthorized (key not working)

---

### Test 7: Rate Limiting
```bash
# Send 70 requests (exceeds 60/min limit)
for i in {1..70}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:7272/health
  sleep 0.5
done
```

**Expected Output:**
- First ~60 requests: `200`
- Remaining requests: `429`

✅ **PASS:** Rate limit enforced (429 responses)
❌ **FAIL:** All 200 responses (rate limit not working)

---

### Test 8: WebSocket Connection (Browser Console)

**Frontend Access Required** - Open browser to `http://10.1.0.118:7274`

**Browser Console:**
```javascript
const ws = new WebSocket('ws://10.1.0.118:7272/ws');
ws.onopen = () => console.log('✅ WebSocket connected');
ws.onerror = (err) => console.error('❌ WebSocket error:', err);
ws.onmessage = (msg) => console.log('Message:', msg.data);
```

**Expected Console Output:**
```
✅ WebSocket connected
```

✅ **PASS:** WebSocket connects successfully
❌ **FAIL:** Connection error or timeout

---

## Step 4: Client Device Testing (15-20 minutes)

### From Another LAN Device (10.1.0.x)

**Prerequisites:**
- Client device on same LAN subnet (10.1.0.x)
- Network connectivity to server

### Test 1: Network Connectivity
```bash
# From client device
ping 10.1.0.118
```

✅ **PASS:** Ping successful
❌ **FAIL:** Request timeout (network issue)

---

### Test 2: API Access from Client
```bash
# From client device
curl http://10.1.0.118:7272/health
```

**Expected:** Same health response as server tests

✅ **PASS:** 200 OK with health data
❌ **FAIL:** Connection refused (firewall blocking)

---

### Test 3: Frontend Access from Client

**Browser (from client device):**
```
http://10.1.0.118:7274
```

**Expected:**
- Frontend loads successfully
- Dashboard displays
- No CORS errors in console
- API calls succeed

✅ **PASS:** Full functionality works
❌ **FAIL:** CORS errors, blank page, or API failures

---

### Test 4: WebSocket from Client

**Browser Console (from client device):**
```javascript
const ws = new WebSocket('ws://10.1.0.118:7272/ws');
ws.onopen = () => console.log('✅ Connected');
ws.onerror = (err) => console.error('❌ Error:', err);
```

✅ **PASS:** WebSocket connects from client
❌ **FAIL:** Connection error

---

## Step 5: Performance Validation (Optional, 10 minutes)

### Load Test - Concurrent Requests
```bash
# Install apache bench (if not available)
# Windows: Download from Apache HTTP Server binaries
# Linux: apt-get install apache2-utils
# Mac: brew install httpd

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 http://127.0.0.1:7272/health
```

**Expected Metrics:**
- Requests per second: > 100
- Time per request: < 100ms
- Failed requests: 0

---

### Database Connection Pool Test
```bash
# Monitor database connections during load test
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE datname='giljo_mcp';"
```

**Expected:**
- Connection count reasonable (< 20)
- Connections released after requests complete

---

## Results Checklist

### Core Functionality
- [ ] API health check (localhost) - Test 1
- [ ] API health check (LAN IP) - Test 2
- [ ] CORS headers correct - Test 3
- [ ] Security headers present - Test 4
- [ ] Authentication enforced - Test 5, 6
- [ ] Rate limiting works - Test 7
- [ ] WebSocket connected - Test 8

### Client Access
- [ ] Client can ping server
- [ ] Client can access API
- [ ] Client can access frontend
- [ ] Client WebSocket works

### Optional Performance
- [ ] Load test passed
- [ ] Connection pool healthy

---

## Troubleshooting

### API Won't Start
```bash
# Check port in use
netstat -ano | findstr :7272

# Check config.yaml
cat config.yaml | grep -A5 "services:"

# Check database connection
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l
```

---

### Firewall Blocking Access
```bash
# Verify firewall rules
netsh advfirewall firewall show rule name="GiljoAI MCP API"

# Temporarily disable firewall (TESTING ONLY)
netsh advfirewall set allprofiles state off

# Re-enable after testing
netsh advfirewall set allprofiles state on
```

---

### CORS Errors
**Check config.yaml:**
```yaml
cors:
  allowed_origins:
    - http://127.0.0.1:7274
    - http://localhost:7274
    - http://10.1.0.118:7274  # Must be present
```

**Restart API after config changes**

---

### Rate Limiting Not Working
**Check config.yaml:**
```yaml
security:
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

**Verify middleware loaded in API logs**

---

## Success Criteria

**All Tests Must Pass:**
- ✅ All 8 runtime tests successful
- ✅ Client device can access all services
- ✅ No security warnings or errors
- ✅ Performance within acceptable limits

**When All Tests Pass:**
1. Document results in test report
2. Mark deployment as production-ready
3. Proceed to user onboarding

---

## Next Steps After Testing

### If All Tests Pass ✅
1. Create final deployment report
2. Update LAN_SECURITY_CHECKLIST.md (mark items complete)
3. Document API key distribution plan
4. Create user access guide
5. Schedule team onboarding

### If Tests Fail ❌
1. Document specific failures
2. Review configuration
3. Check firewall settings
4. Verify database connectivity
5. Consult troubleshooting section
6. Re-run tests after fixes

---

## Quick Reference

**API Endpoints:**
- Health: `http://10.1.0.118:7272/health`
- Projects: `http://10.1.0.118:7272/api/v1/projects`
- WebSocket: `ws://10.1.0.118:7272/ws`

**Frontend:**
- Dashboard: `http://10.1.0.118:7274`

**Database:**
- Host: localhost (not network accessible)
- Port: 5432
- Name: giljo_mcp

**Service Ports:**
- API: 7272 (TCP)
- Frontend: 7274 (TCP)
- PostgreSQL: 5432 (localhost only)

---

**Test Execution Time:** 30-60 minutes
**Recommended:** Execute all tests in order, document results as you go

**For detailed test procedures, see:** `docs/deployment/LAN_TEST_REPORT.md`

**End of Runtime Testing Quick Start Guide**
