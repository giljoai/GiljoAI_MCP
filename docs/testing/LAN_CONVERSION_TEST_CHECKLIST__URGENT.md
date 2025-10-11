# LAN Mode Conversion Test Checklist

## Purpose
Verify that the localhost-to-LAN conversion flow works correctly after the API key modal fix.

## Root Cause (Fixed)
The API key modal was not appearing because `generate_api_key()` was being called multiple times on wizard re-runs, potentially causing issues. We implemented `get_or_create_api_key()` for idempotent behavior.

## Pre-Requisites

### 1. Environment Setup
- [ ] PostgreSQL 18 is running
- [ ] Project is on F: drive (server mode testing system)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies installed (`cd frontend && npm install`)

### 2. Initial State
- [ ] Current config.yaml shows:
  - `installation.mode: localhost`
  - `setup.completed: true`
  - `features.api_keys_required: false`
- [ ] No existing API keys in `~/.giljo-mcp/api_keys.json` (or backup if exists)

### 3. Services Running
```bash
# Terminal 1: Start API server
cd F:/GiljoAI_MCP
python api/run_api.py

# Terminal 2: Start frontend
cd F:/GiljoAI_MCP/frontend
npm run dev
```

- [ ] API server running on http://localhost:7272 (or configured port)
- [ ] Frontend running on http://localhost:7274 (or configured port)
- [ ] No errors in either terminal

---

## Test Scenario 1: Fresh LAN Conversion (No Existing API Key)

### Step 1: Access Setup Wizard
1. [ ] Open browser to `http://localhost:7274`
2. [ ] Click "Settings" or navigate to `/setup`
3. [ ] Wizard loads with 5 steps visible

**Expected:**
- Setup wizard displays correctly
- All steps are clickable/navigable

### Step 2: Navigate to Network Config (Step 4)
1. [ ] Click through steps 1-3 or navigate directly to Step 4
2. [ ] Select **LAN** mode radio button
3. [ ] LAN configuration form appears

**Expected:**
- Form shows fields:
  - Server IP (pre-filled or empty)
  - Hostname (default: "giljo.local")
  - Admin Username (default: "admin")
  - Admin Password (required)
  - Firewall configured checkbox

### Step 3: Fill in LAN Configuration
1. [ ] Enter Server IP: `10.1.0.164` (or your LAN IP)
2. [ ] Keep hostname: `giljo.local`
3. [ ] Keep username: `admin`
4. [ ] Enter password: `TestPassword123!`
5. [ ] Check "Firewall configured" if firewall is ready
6. [ ] Click "Next" to proceed to Step 5

**Expected:**
- Form validation passes
- Step 5 (Summary) loads

### Step 4: Review Summary and Save
1. [ ] Review configuration summary
2. [ ] Click **"Save and Exit"** button
3. [ ] Confirmation modal appears: "Switch to LAN Mode?"

**Expected:**
- Modal shows warning about LAN mode implications
- Two buttons: "Cancel" and "OK"

### Step 5: Confirm LAN Mode Switch
1. [ ] Click **"OK"** to confirm
2. [ ] Watch for loading indicator
3. [ ] **CRITICAL CHECK:** API key modal should appear

**Expected Result:**
- Modal title: "Save Your API Key"
- Modal body shows:
  - Warning text about API key security
  - API key display box with key starting with `gk_`
  - Copy button next to API key
  - Checkbox: "I have saved this API key securely"
  - "Continue" button (disabled until checkbox checked)

**Screenshot Point 1:** API key modal appearance

### Step 6: Copy and Confirm API Key
1. [ ] Copy the API key (click copy button or select and copy)
2. [ ] Verify key format: `gk_` + 40+ characters
3. [ ] Check the "I have saved this API key" checkbox
4. [ ] "Continue" button becomes enabled
5. [ ] Click **"Continue"**

**Expected:**
- Copy button shows "Copied!" feedback
- Checkbox enables Continue button
- Modal closes smoothly

### Step 7: Restart Instructions Modal
1. [ ] Restart modal appears immediately after API key modal closes
2. [ ] Modal shows platform-specific restart instructions

**Expected:**
- Modal title: "Restart Required"
- Windows instructions show:
  ```
  1. Stop services: stop_giljo.bat
  2. Start services: start_giljo.bat
  ```
- Button: "I've Restarted - Go to Dashboard"

**Screenshot Point 2:** Restart modal appearance

### Step 8: Restart Services
1. [ ] Open new terminal in `F:/GiljoAI_MCP`
2. [ ] Run: `stop_giljo.bat` (or Ctrl+C in API/frontend terminals)
3. [ ] Wait for services to stop (3-5 seconds)
4. [ ] Run: `start_giljo.bat` (or restart manually)
5. [ ] Verify API server logs show:
   - `Mode: lan` or `Deployment mode: LAN`
   - `API binding to 0.0.0.0:7272`
   - `API key authentication enabled`

**Expected:**
- Services stop cleanly
- Services restart in LAN mode
- No errors in logs

### Step 9: Confirm Restart and Navigate to Dashboard
1. [ ] Click **"I've Restarted - Go to Dashboard"**
2. [ ] Page redirects to `http://localhost:7274`
3. [ ] Dashboard loads

**Expected:**
- Dashboard displays normally
- **GREEN BANNER appears at top:** "LAN Mode Activated!"
- Banner includes:
  - Success message
  - Server IP: 10.1.0.164
  - API port: 7272
  - Instructions to configure clients

**Screenshot Point 3:** Dashboard with green LAN welcome banner

### Step 10: Verify Configuration Changes
1. [ ] Open `F:/GiljoAI_MCP/config.yaml`
2. [ ] Check the following fields:

**Expected config.yaml changes:**
```yaml
installation:
  mode: lan  # Changed from localhost

services:
  api:
    host: 0.0.0.0  # Changed from 127.0.0.1

features:
  api_keys_required: true  # Changed from false
  multi_user: true  # Changed from false

server:
  ip: 10.1.0.164
  hostname: giljo.local
  admin_user: admin
  firewall_configured: true
```

### Step 11: Verify API Key Storage
1. [ ] Check file exists: `C:/Users/[username]/.giljo-mcp/api_keys.json`
2. [ ] File is encrypted (binary format, not readable)
3. [ ] Check logs for key generation confirmation

**Expected in API server logs:**
```
API key ready for LAN mode (idempotent)
Reusing existing active API key 'LAN Setup Key' (prefix: gk_xxx...)
```
OR
```
No existing key found for 'LAN Setup Key', creating new API key
API key created/retrieved for 'LAN Setup Key' (prefix: gk_xxx...)
```

### Step 12: Verify Admin Account Storage
1. [ ] Check file exists: `C:/Users/[username]/.giljo-mcp/admin_account.json`
2. [ ] File is encrypted (binary format, not readable)

**Expected in API server logs:**
```
Stored encrypted admin account for user 'admin'
```

---

## Test Scenario 2: Re-run Wizard (Idempotent Behavior)

### Purpose
Verify that re-running the wizard returns the SAME API key (idempotent behavior).

### Pre-Requisite
- [ ] Scenario 1 completed successfully
- [ ] API key from Scenario 1 saved externally (e.g., notepad)

### Steps
1. [ ] Navigate back to setup wizard: `http://localhost:7274/setup`
2. [ ] Complete steps 1-4, selecting LAN mode again
3. [ ] Fill in same LAN configuration (or different values)
4. [ ] Click "Save and Exit" → Confirm LAN mode
5. [ ] **CRITICAL CHECK:** API key modal appears again

**Expected Result:**
- API key modal appears (same as before)
- **API key displayed is IDENTICAL to the one from Scenario 1**
- No new key was generated
- Logs show: `Reusing existing active API key 'LAN Setup Key'`

### Verification
1. [ ] Compare displayed API key to saved key from Scenario 1
2. [ ] Keys match exactly (idempotent behavior confirmed)

---

## Test Scenario 3: Error Handling

### Test 3a: AuthManager Not Available
**Simulate:** Stop API server during LAN config submission

1. [ ] Start wizard, select LAN mode
2. [ ] Fill in config, click "Save and Exit"
3. [ ] Stop API server before clicking "OK" in confirmation modal
4. [ ] Click "OK"

**Expected:**
- Error message appears
- User is notified that authentication system is not available
- No partial state saved

### Test 3b: Network Error During API Call
**Simulate:** Disconnect network or block port

**Expected:**
- Error notification appears
- User can retry or cancel
- Wizard state preserved

### Test 3c: User Closes API Key Modal Without Saving
1. [ ] Complete LAN config and trigger API key modal
2. [ ] Click outside modal or close button (if available)

**Expected:**
- Warning appears: "Are you sure? You won't be able to access this key again"
- If confirmed close: proceed to restart modal
- If cancel: stay on API key modal

---

## Edge Cases

### Edge Case 1: Revoked API Key Exists
**Setup:** Manually revoke the "LAN Setup Key" via API or tool

**Test:**
1. [ ] Re-run wizard with LAN mode
2. [ ] Submit configuration

**Expected:**
- New API key generated with timestamped name: `LAN Setup Key (2025-10-07)`
- Logs show: `Revoked key exists with name 'LAN Setup Key', creating new key`

### Edge Case 2: Multiple Rapid Submissions
**Test:** Click "Save and Exit" multiple times rapidly

**Expected:**
- Only one API call is made (button disables)
- No duplicate keys created
- UI prevents double-submission

---

## Rollback Procedure (If Tests Fail)

### If API Key Modal Doesn't Appear:
1. Check browser console for JavaScript errors
2. Check API server logs for backend errors
3. Verify `get_or_create_api_key()` is being called (line 65 in setup.py)
4. Check network tab: response should have `api_key` field

### If Config Not Updated:
1. Check `config.yaml` manually for changes
2. Verify write permissions on config file
3. Check API logs for config save errors

### If Services Don't Restart in LAN Mode:
1. Check `config.yaml` shows correct mode
2. Verify API server reads config on startup
3. Check for port conflicts (0.0.0.0 binding)

### Emergency Rollback:
```bash
# Restore config to localhost mode manually
cd F:/GiljoAI_MCP
# Edit config.yaml:
# - installation.mode: localhost
# - services.api.host: 127.0.0.1
# - features.api_keys_required: false

# Restart services
stop_giljo.bat
start_giljo.bat
```

---

## Success Criteria

### All Tests Pass If:
- [ ] API key modal appears in Scenario 1
- [ ] API key is displayed and copyable
- [ ] Restart modal appears after API key modal
- [ ] Dashboard shows green banner after restart
- [ ] config.yaml updated correctly
- [ ] API keys stored in encrypted file
- [ ] Idempotent behavior confirmed in Scenario 2
- [ ] No errors in browser console
- [ ] No errors in API logs (except expected warnings)

---

## Notes for Tester

### Logging Locations:
- **API Server:** Terminal output or `logs/api.log`
- **Frontend:** Browser console (F12)
- **Config File:** `F:/GiljoAI_MCP/config.yaml`
- **API Keys:** `C:/Users/[username]/.giljo-mcp/api_keys.json` (encrypted)

### Common Issues:
1. **Modal doesn't appear:** Check backend returned `api_key` in response
2. **"Continue" button disabled:** Must check the confirmation checkbox first
3. **Services won't start:** Check port availability (7272, 7274)
4. **Config not persisting:** Check file permissions

### Screenshots to Capture:
1. API key modal with key displayed
2. Restart instructions modal
3. Dashboard with green LAN banner
4. Browser console (no errors)
5. API logs showing successful key generation

---

## Test Results Template

```
Test Date: _______________
Tester: _______________
Environment: F: drive (Server mode system)

Scenario 1 (Fresh LAN Conversion): [ ] PASS [ ] FAIL
  - API key modal appeared: [ ] YES [ ] NO
  - API key format valid: [ ] YES [ ] NO
  - Restart modal appeared: [ ] YES [ ] NO
  - Dashboard banner appeared: [ ] YES [ ] NO
  - Config updated: [ ] YES [ ] NO

Scenario 2 (Idempotent Re-run): [ ] PASS [ ] FAIL
  - Same API key returned: [ ] YES [ ] NO
  - No new key created: [ ] YES [ ] NO

Scenario 3 (Error Handling): [ ] PASS [ ] FAIL [ ] N/A
  - Errors handled gracefully: [ ] YES [ ] NO

Issues Found:
_________________________________________________________________
_________________________________________________________________

Recommendations:
_________________________________________________________________
_________________________________________________________________
```

---

## Developer Notes

**Files Modified in Fix:**
- `src/giljo_mcp/auth.py` - Added `get_or_create_api_key()` method
- `api/endpoints/setup.py` - Changed line 65 to use new method
- `tests/integration/test_lan_conversion_flow.py` - Comprehensive test suite

**Root Cause:**
The `generate_api_key()` method always created new keys, which could cause issues on wizard re-runs. The new `get_or_create_api_key()` method provides idempotent behavior:
- Returns existing active key if found
- Creates timestamped key if revoked key exists
- Creates new key if no key exists

**Key Changes:**
1. Backend always returns a valid API key for LAN mode
2. Frontend modal display logic unchanged (still checks `result.api_key`)
3. Idempotent behavior ensures consistent user experience

**Test Coverage:**
- 10 unit/integration tests passing
- 3 end-to-end tests (require manual testing or full API server)
