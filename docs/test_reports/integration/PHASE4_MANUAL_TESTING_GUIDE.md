# Phase 4: Manual End-to-End Testing Guide

**Date:** October 12, 2025
**Task:** Verify v3.0 Unified Authentication - NO LOCALHOST BYPASS
**Tester:** Backend Integration Tester Agent

## Overview

This guide provides comprehensive manual testing scenarios to verify that the localhost bypass logic has been COMPLETELY REMOVED and that all connections (localhost and network IP) require proper JWT authentication or API key authentication.

## Prerequisites

Before beginning manual testing:

1. **Fresh Installation Required**: Start with a fresh install to verify the complete flow
   ```bash
   # Drop existing database
   psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

   # Run fresh installation
   python install.py
   ```

2. **Network Configuration**: Ensure you can access the system from both:
   - Localhost: `http://127.0.0.1:7274`
   - Network IP: `http://10.1.0.164:7274` (or your network IP)

3. **Browser Tools**: Use browser developer tools (F12) to inspect:
   - Network requests (status codes, headers, cookies)
   - Console logs
   - Application storage (cookies, local storage)

## Test Scenario 1: Fresh Installation from Localhost

**Objective:** Verify complete setup flow from localhost requires authentication

### Steps

1. **Start Fresh Installation**
   ```bash
   python install.py
   ```
   - Installer creates `admin/admin` account
   - Sets `default_password_active: true`
   - Starts API server on port 7272
   - Starts frontend on port 7274

2. **Access Frontend (Localhost)**
   - Open browser: `http://localhost:7274`
   - **Expected**: Router redirects to `/change-password`
   - **Why**: Router navigation guard detects `default_password_active: true`

3. **Verify Authentication Required**
   - **Before Password Change**: Open DevTools > Network tab
   - Navigate to `http://localhost:7274/dashboard`
   - **Expected**: Redirect to `/change-password` (frontend routing)
   - **Verify**: GET `/api/auth/me` returns 401 (no fake localhost user)

4. **Change Default Password**
   - On `/change-password` page:
     - Username: `admin` (pre-filled)
     - Current Password: `admin`
     - New Password: `MySecurePassword123!` (meets complexity requirements)
     - Confirm Password: `MySecurePassword123!`
   - Click "Change Password"

   **Expected Results:**
   - POST `/api/auth/change-password` returns 200
   - Response includes JWT token
   - Frontend stores token in cookie
   - Redirect to `/setup` (setup wizard)
   - `default_password_active: false` in database

5. **Complete Setup Wizard**
   - **Step 1**: MCP Configuration (optional - can skip)
   - **Step 2**: Serena Activation (optional - can skip)
   - **Step 3**: Complete (summary)
   - Click "Go to Dashboard"

   **Expected Results:**
   - POST `/api/setup/complete` returns 200
   - `setup_completed: true` in database
   - Redirect to `/dashboard`

6. **Verify Authenticated Access**
   - Dashboard loads successfully
   - GET `/api/auth/me` returns 200 with user profile
   - **Verify**: Response contains real user data (NOT fake localhost user)
   ```json
   {
     "id": "uuid-here",
     "username": "admin",
     "role": "admin",
     "tenant_key": "default"
   }
   ```

### Success Criteria

- [ ] Fresh install creates `admin/admin` with `default_password_active: true`
- [ ] Frontend forces password change (no bypass)
- [ ] `/api/auth/me` returns 401 before authentication (no fake user)
- [ ] Password change succeeds and returns JWT token
- [ ] Setup wizard completes successfully
- [ ] Dashboard requires authentication (JWT cookie)
- [ ] All requests use JWT cookie (no special localhost treatment)

---

## Test Scenario 2: Access from Network IP

**Objective:** Verify network IP connections are treated identically to localhost

### Steps

1. **Prerequisites**: Complete Scenario 1 (setup completed, password changed)

2. **Access from Network IP**
   - From another device on the network, open: `http://10.1.0.164:7274`
   - **Expected**: Login page or `/change-password` redirect (same as localhost)

3. **Attempt Unauthenticated Access**
   - Navigate to: `http://10.1.0.164:7274/dashboard`
   - **Expected**: Redirect to login page
   - **Verify**: GET `/api/auth/me` returns 401 (same as localhost)

4. **Login from Network IP**
   - On login page:
     - Username: `admin`
     - Password: `MySecurePassword123!` (changed password from Scenario 1)
   - Click "Login"

   **Expected Results:**
   - POST `/api/auth/login` returns 200
   - Response includes JWT token in cookie
   - Redirect to `/dashboard`

5. **Verify Authenticated Access**
   - Dashboard loads successfully
   - GET `/api/auth/me` returns 200 with user profile
   - **Verify**: Same user data as localhost (no difference)

6. **Compare Localhost vs Network IP**
   - Open DevTools > Network tab
   - Compare requests from localhost and network IP
   - **Expected**: Identical behavior (status codes, headers, responses)

### Success Criteria

- [ ] Network IP requires login (no bypass)
- [ ] `/api/auth/me` returns 401 before authentication (same as localhost)
- [ ] Login from network IP succeeds and returns JWT cookie
- [ ] JWT cookie works for both localhost and network IP
- [ ] No difference in authentication behavior based on IP address

---

## Test Scenario 3: API Key Authentication

**Objective:** Verify API keys work consistently from both localhost and network IP

### Steps

1. **Prerequisites**: Logged in as admin (from Scenario 1 or 2)

2. **Create API Key (Localhost)**
   - Navigate to: `http://localhost:7274/settings/api-keys`
   - Click "Create API Key"
   - Name: "Test API Key"
   - Permissions: `["*"]` (all permissions)
   - Click "Create"

   **Expected Results:**
   - POST `/api/auth/api-keys` returns 201
   - Response includes plaintext API key (shown ONCE)
   - Copy API key: `gk_xxxxxxxxxxxxxxxxxxxx`

3. **Test API Key from Localhost**
   - Use curl or Postman to test:
   ```bash
   curl -H "X-API-Key: gk_xxxxxxxxxxxxxxxxxxxx" http://localhost:7272/api/auth/me
   ```

   **Expected Results:**
   - GET `/api/auth/me` returns 200
   - Response contains user profile (same as JWT authentication)

4. **Test API Key from Network IP**
   - From another device, use curl:
   ```bash
   curl -H "X-API-Key: gk_xxxxxxxxxxxxxxxxxxxx" http://10.1.0.164:7272/api/auth/me
   ```

   **Expected Results:**
   - GET `/api/auth/me` returns 200
   - Response identical to localhost (same user profile)

5. **Test Invalid API Key**
   ```bash
   curl -H "X-API-Key: gk_invalid_key" http://localhost:7272/api/auth/me
   ```

   **Expected Results:**
   - GET `/api/auth/me` returns 401
   - Error message: "Not authenticated. Please login or provide a valid API key."

6. **Test No Authentication**
   ```bash
   curl http://localhost:7272/api/auth/me
   ```

   **Expected Results:**
   - GET `/api/auth/me` returns 401
   - Same error message as invalid API key

### Success Criteria

- [ ] API key creation succeeds (admin only)
- [ ] API key works from localhost
- [ ] API key works from network IP (identical behavior)
- [ ] Invalid API key returns 401 (not 200 with fake user)
- [ ] No API key returns 401 (not 200 with fake user)
- [ ] API keys work consistently regardless of IP address

---

## Test Scenario 4: Public Endpoints (Setup/Login)

**Objective:** Verify setup and login endpoints remain publicly accessible

### Steps

1. **Test Public Endpoints (No Auth Required)**

   **a. Health Check**
   ```bash
   curl http://localhost:7272/health
   ```
   - **Expected**: 200 OK

   **b. Frontend Config**
   ```bash
   curl http://localhost:7272/api/v1/config/frontend
   ```
   - **Expected**: 200 OK with config data

   **c. Login Endpoint**
   ```bash
   curl -X POST http://localhost:7272/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "MySecurePassword123!"}'
   ```
   - **Expected**: 200 OK with JWT token

   **d. Change Password Endpoint**
   ```bash
   curl -X POST http://localhost:7272/api/auth/change-password \
     -H "Content-Type: application/json" \
     -d '{"current_password": "admin", "new_password": "NewPass123!", "confirm_password": "NewPass123!"}'
   ```
   - **Expected**: 200 OK (if default password active) OR 404 (if no admin user)

2. **Test Protected Endpoints (Auth Required)**

   **a. Projects Endpoint**
   ```bash
   curl http://localhost:7272/api/v1/projects
   ```
   - **Expected**: 401 Unauthorized (no authentication)

   **b. Agents Endpoint**
   ```bash
   curl http://localhost:7272/api/v1/agents
   ```
   - **Expected**: 401 Unauthorized

   **c. Messages Endpoint**
   ```bash
   curl http://localhost:7272/api/v1/messages
   ```
   - **Expected**: 401 Unauthorized

3. **Verify Public/Protected Distinction**
   - Public endpoints: `/health`, `/api/auth/login`, `/api/auth/change-password`, `/api/setup/*`
   - Protected endpoints: `/api/v1/*` (except frontend config), `/api/auth/me`, `/api/auth/api-keys`

### Success Criteria

- [ ] Public endpoints accessible without authentication
- [ ] Protected endpoints return 401 without authentication
- [ ] No fake localhost user created for protected endpoints
- [ ] Login endpoint works from any IP
- [ ] Setup endpoints work from any IP (during setup mode)

---

## Test Scenario 5: WebSocket Authentication

**Objective:** Verify WebSocket connections require JWT authentication

### Steps

1. **Test WebSocket Without Authentication**
   - Open browser console: `http://localhost:7274`
   - Run JavaScript:
   ```javascript
   const ws = new WebSocket('ws://localhost:7272/ws');
   ws.onopen = () => console.log('Connected');
   ws.onerror = (error) => console.error('Connection failed:', error);
   ws.onclose = (event) => console.log('Connection closed:', event.code, event.reason);
   ```

   **Expected Results:**
   - Connection attempt fails OR closes immediately
   - Status code: 1008 (policy violation) OR 403 (forbidden)
   - Reason: "Authentication required"

2. **Test WebSocket With JWT Token**
   - Login first, then extract JWT token from cookie
   - Open browser console:
   ```javascript
   const token = document.cookie.match(/access_token=([^;]+)/)[1];
   const ws = new WebSocket(`ws://localhost:7272/ws?token=${token}`);
   ws.onopen = () => console.log('Connected successfully');
   ws.onmessage = (msg) => console.log('Message:', msg.data);
   ```

   **Expected Results:**
   - Connection succeeds
   - WebSocket remains open
   - Can send/receive messages

3. **Test WebSocket During Setup Mode**
   - **Note**: This requires a fresh install with setup NOT completed
   - During setup wizard, WebSocket should work without auth (for progress updates)
   - After setup completed, WebSocket requires auth

### Success Criteria

- [ ] WebSocket without authentication fails (post-setup)
- [ ] WebSocket with JWT token succeeds
- [ ] WebSocket during setup mode works without auth (progress updates)
- [ ] No special localhost treatment for WebSocket connections

---

## Verification Checklist

### Core Authentication Requirements

- [ ] **NO Localhost Bypass**: Localhost requires authentication (no auto-login)
- [ ] **Unified Authentication**: Localhost and network IP treated identically
- [ ] **JWT Required**: All protected endpoints require JWT token or API key
- [ ] **No Fake Users**: `/api/auth/me` returns 401 (not fake localhost user)

### Password Management

- [ ] **Default Password Blocks Login**: `admin/admin` requires password change first
- [ ] **Password Change Succeeds**: Sets `default_password_active: false`
- [ ] **Complexity Requirements**: Password must meet security requirements
- [ ] **Login After Change**: New password works immediately

### Token Management

- [ ] **JWT Cookie**: Login sets httpOnly cookie with JWT token
- [ ] **Token Expiry**: JWT tokens expire after 24 hours
- [ ] **Cookie Scope**: JWT cookie works for both localhost and network IP
- [ ] **Token Validation**: Invalid tokens return 401 (not fake user)

### API Key Management

- [ ] **Key Creation**: Admin can create API keys
- [ ] **Key Format**: API keys start with `gk_` prefix
- [ ] **Key Security**: Keys are hashed in database (bcrypt)
- [ ] **Key Permissions**: Keys support permission scoping
- [ ] **Key Revocation**: Admin can revoke keys
- [ ] **Cross-IP Support**: API keys work from any IP address

### Multi-Tenant Isolation

- [ ] **Tenant Filtering**: All queries filtered by `tenant_key`
- [ ] **User Isolation**: Users can only access their tenant's data
- [ ] **API Key Isolation**: API keys scoped to user's tenant
- [ ] **WebSocket Isolation**: WebSocket messages filtered by tenant

---

## Expected Test Results Summary

| Test Scenario | Expected Outcome | Verification Method |
|--------------|-----------------|---------------------|
| Localhost requires auth | 401 without JWT | `GET /api/auth/me` |
| Network IP requires auth | 401 without JWT | Same as localhost |
| Login returns JWT (localhost) | 200 with cookie | `POST /api/auth/login` |
| Login returns JWT (network IP) | 200 with cookie | Same as localhost |
| JWT works (localhost) | 200 with user profile | `GET /api/auth/me` + cookie |
| JWT works (network IP) | 200 with user profile | Same as localhost |
| API key works (localhost) | 200 with user profile | `GET /api/auth/me` + header |
| API key works (network IP) | 200 with user profile | Same as localhost |
| No fake localhost user | 401 (not 200 with fake user) | No `username: "localhost"` |
| Default password blocks login | 403 (password change required) | `POST /api/auth/login` |
| Password change succeeds | 200 with JWT token | `POST /api/auth/change-password` |
| Setup wizard completes | 200 with redirect | `POST /api/setup/complete` |
| WebSocket requires auth | Connection fails | WebSocket connection test |
| Public endpoints accessible | 200 without auth | `/health`, `/api/auth/login` |
| Protected endpoints blocked | 401 without auth | `/api/v1/*` |

---

## Troubleshooting Common Issues

### Issue 1: Test Database Schema Mismatch

**Symptom:** `UndefinedColumnError: column "database_initialized" of relation "setup_state" does not exist`

**Solution:**
```bash
# Drop and recreate test database
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test;"
psql -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Recreate tables
python -c "from src.giljo_mcp.database import DatabaseManager; import asyncio; asyncio.run(DatabaseManager('postgresql://postgres:$DB_PASSWORD@localhost/giljo_mcp_test', is_async=True).create_tables_async())"
```

### Issue 2: Firewall Blocking Network Access

**Symptom:** Network IP connections fail or timeout

**Solution:**
```powershell
# Windows: Check firewall rules
Get-NetFirewallRule -DisplayName "GiljoAI*"

# Add rule if needed
New-NetFirewallRule -DisplayName "GiljoAI MCP - Allow LAN" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272,7274 `
    -RemoteAddress 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

### Issue 3: JWT Cookie Not Being Set

**Symptom:** Login succeeds but subsequent requests fail

**Solution:**
- Check browser DevTools > Application > Cookies
- Verify `access_token` cookie exists
- Check cookie attributes (httpOnly, SameSite, Secure)
- Ensure CORS is configured correctly for your network IP

### Issue 4: API Key Not Working

**Symptom:** API key returns 401

**Solution:**
- Verify API key format: `gk_` prefix
- Check API key is active in database
- Ensure correct header: `X-API-Key` (not `Authorization`)
- Verify user associated with API key is active

---

## Manual Testing Report Template

After completing all test scenarios, document your results:

```markdown
# v3.0 Unified Authentication - Manual Testing Report

**Date:** [Date]
**Tester:** [Name]
**Environment:** [localhost / network IP / both]

## Test Results

### Scenario 1: Fresh Installation from Localhost
- [ ] PASS / [ ] FAIL
- Notes: [Any issues encountered]

### Scenario 2: Access from Network IP
- [ ] PASS / [ ] FAIL
- Notes: [Any issues encountered]

### Scenario 3: API Key Authentication
- [ ] PASS / [ ] FAIL
- Notes: [Any issues encountered]

### Scenario 4: Public Endpoints
- [ ] PASS / [ ] FAIL
- Notes: [Any issues encountered]

### Scenario 5: WebSocket Authentication
- [ ] PASS / [ ] FAIL
- Notes: [Any issues encountered]

## Key Findings

1. **Localhost Bypass Removed**: [CONFIRMED / NOT VERIFIED]
2. **Unified Authentication**: [CONFIRMED / NOT VERIFIED]
3. **No Fake Users**: [CONFIRMED / NOT VERIFIED]
4. **Password Flow Works**: [CONFIRMED / NOT VERIFIED]
5. **API Keys Work Consistently**: [CONFIRMED / NOT VERIFIED]

## Issues Discovered

[List any issues found during testing]

## Recommendations

[Any recommendations for improvements]
```

---

## Next Steps

After completing manual testing:

1. **Document Results**: Fill out manual testing report template
2. **File Issues**: Create GitHub issues for any problems found
3. **Update Documentation**: Update user docs if needed
4. **Commit Tests**: Commit integration test suite for CI/CD
5. **Deploy**: Proceed with deployment if all tests pass

---

## Contact

For questions about this testing guide:
- **Agent**: Backend Integration Tester Agent
- **Project**: GiljoAI MCP v3.0
- **Phase**: Phase 4 - Manual End-to-End Testing
