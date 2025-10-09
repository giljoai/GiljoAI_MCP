# PC 2 LAN Testing - Step-by-Step Instructions

**Date:** January 7, 2025
**Purpose:** Verify GiljoAI MCP network connectivity from secondary computer
**Prerequisites:** PC 1 (F: Drive) configured for LAN mode and services restarted

---

## Context

PC 1 (F: Drive - Windows) has just completed the LAN setup wizard and is configured as a server with the following settings:

- **Server IP:** `10.1.0.164` (auto-detected)
- **API Port:** `7272`
- **Frontend Port:** `7274`
- **Mode:** `server` (bound to 0.0.0.0)
- **Authentication:** API key required
- **Services:** Restarted and running

Your task is to test network connectivity from PC 2 (another device on the same local network).

---

## Pre-Flight Checklist (PC 1 - Server)

Before testing from PC 2, verify on PC 1:

### 1. Services Are Running

Open Command Prompt on PC 1 and check:

```bash
# Check if API server is running
curl http://localhost:7272/health
# Expected: {"status": "ok"}

# Check if frontend is running
curl http://localhost:7274
# Expected: HTML content
```

If not running, restart services:

```bash
cd F:\GiljoAI_MCP
.\stop_giljo.bat
.\start_giljo.bat
# Wait 10-15 seconds
```

### 2. Firewall Configuration

**Windows Firewall Rules Required:**

```powershell
# Run as Administrator in PowerShell
New-NetFirewallRule -DisplayName "GiljoAI API Server" -Direction Inbound -LocalPort 7272 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "GiljoAI Frontend" -Direction Inbound -LocalPort 7274 -Protocol TCP -Action Allow
```

**Verify Rules:**

```powershell
Get-NetFirewallRule -DisplayName "*GiljoAI*" | Format-Table -AutoSize
```

Should show two rules, both enabled.

### 3. Network Information

Verify server IP from PC 1:

```bash
ipconfig | findstr IPv4
```

Look for your LAN adapter (not Hyper-V virtual adapter). Should show `10.1.0.164`.

---

## Testing from PC 2

### Step 1: Basic Network Connectivity

**Test:** Can PC 2 reach PC 1 on the network?

```bash
# From PC 2 command prompt/terminal
ping 10.1.0.164
```

**Expected Result:**
```
Reply from 10.1.0.164: bytes=32 time<10ms TTL=128
Reply from 10.1.0.164: bytes=32 time<10ms TTL=128
Reply from 10.1.0.164: bytes=32 time<10ms TTL=128
Reply from 10.1.0.164: bytes=32 time<10ms TTL=128
```

**If Fails:**
- Verify both PCs are on same network (same subnet)
- Check router AP Isolation setting (must be OFF)
- Verify PC 1 firewall isn't blocking ICMP
- Check network cables/WiFi connection

---

### Step 2: API Health Check

**Test:** Can PC 2 reach the API server?

```bash
# From PC 2
curl http://10.1.0.164:7272/health
```

**Expected Result:**
```json
{"status":"ok"}
```

**If Fails:**
- API server not running on PC 1 → restart services
- Firewall blocking port 7272 → check firewall rules
- Wrong IP/port → verify with `ipconfig` on PC 1
- API bound to localhost only → check `config.yaml` has `host: 0.0.0.0`

---

### Step 3: Frontend Browser Access

**Test:** Can PC 2 open the dashboard in a browser?

**From PC 2 Web Browser:**
```
http://10.1.0.164:7274
```

**Expected Result:**
- GiljoAI MCP dashboard loads
- Shows login or API key prompt
- No CORS errors in browser console (F12 → Console tab)

**If Fails:**
- Frontend not running → check PC 1 services
- Firewall blocking port 7274 → check firewall rules
- CORS error → verify `config.yaml` has PC 2's IP in `allowed_origins`
- Connection refused → frontend crashed, check logs on PC 1

---

### Step 4: API Key Authentication

**Test:** Can PC 2 authenticate with the API?

You'll need the API key generated during setup (shown in API Key Modal on PC 1).

**Method 1: Using curl**

```bash
# From PC 2
curl -H "X-API-Key: <YOUR_API_KEY_HERE>" http://10.1.0.164:7272/api/v1/projects
```

**Expected Result:**
```json
[]
```
(Empty array if no projects created yet, or list of projects)

**Method 2: Browser DevTools**

1. Open `http://10.1.0.164:7274` on PC 2
2. Open browser console (F12)
3. Enter API key when prompted
4. Verify API calls succeed (Network tab → should see 200 OK responses)

**If Fails:**
- "Unauthorized" → API key incorrect or not sent
- "Forbidden" → API key valid but lacks permissions
- "Connection refused" → Network/firewall issue

---

### Step 5: CORS Verification

**Test:** Does the frontend on PC 2 successfully communicate with API on PC 1?

1. Open `http://10.1.0.164:7274` on PC 2
2. Open browser console (F12)
3. Navigate through dashboard
4. Check Console tab for errors

**Expected Result:**
- No CORS errors
- API calls succeed
- Dashboard loads data

**If CORS Error:**
```
Access to fetch at 'http://10.1.0.164:7272/api/...' from origin 'http://10.1.0.164:7274' has been blocked by CORS policy
```

**Fix:**
Edit `config.yaml` on PC 1:
```yaml
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://10.1.0.164:7274  # Add this
      - http://<PC2_IP>:7274    # Add PC 2's IP if accessing from there
```

Then restart API server:
```bash
cd F:\GiljoAI_MCP
.\stop_backend.bat
.\start_backend.bat
```

---

### Step 6: Create Test Project

**Test:** Full CRUD operation from PC 2

**From PC 2 Browser at `http://10.1.0.164:7274`:**

1. Click **[+ New Project]**
2. Fill in:
   - Name: "PC2 Test Project"
   - Mission: "Test network connectivity from PC 2"
   - Agents: Leave default or select "orchestrator-coordinator"
3. Click **[Create Project]**

**Expected Result:**
- Project created successfully
- Shows in projects list
- No errors in console

**If Fails:**
- Check API key authentication
- Check CORS settings
- Verify database connection on PC 1
- Check PC 1 logs: `F:\GiljoAI_MCP\logs\api.log`

---

### Step 7: WebSocket Real-Time Updates

**Test:** Real-time communication between PC 1 and PC 2

**Setup:**
1. PC 1: Open dashboard at `http://localhost:7274`
2. PC 2: Open dashboard at `http://10.1.0.164:7274`

**Test:**
3. PC 2: Create a new project
4. PC 1: Should see the new project appear in real-time (without refresh)

**Expected Result:**
- Both dashboards show same data
- Updates appear instantly
- WebSocket connection stable

**If Fails:**
- WebSocket connection rejected → check firewall
- Updates delayed → check network latency
- Connection drops → check network stability

---

## Troubleshooting Guide

### Issue: Ping Works, API Doesn't

**Diagnosis:** Firewall blocking specific ports

**Fix:**
```powershell
# On PC 1 (as Administrator)
New-NetFirewallRule -DisplayName "GiljoAI API" -Direction Inbound -LocalPort 7272 -Protocol TCP -Action Allow
```

---

### Issue: CORS Errors in Browser

**Diagnosis:** `allowed_origins` in config doesn't include PC 2's access URL

**Fix:**
Edit `F:\GiljoAI_MCP\config.yaml`:
```yaml
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://10.1.0.164:7274  # Server's IP
      - http://<PC2_IP>:7274    # Client's IP if needed
```

Restart API: `.\stop_backend.bat && .\start_backend.bat`

---

### Issue: Connection Refused

**Diagnosis:** Service not running or wrong IP/port

**Verify on PC 1:**
```bash
netstat -an | findstr 7272
netstat -an | findstr 7274
```

Should show:
```
TCP    0.0.0.0:7272    0.0.0.0:0    LISTENING
TCP    0.0.0.0:7274    0.0.0.0:0    LISTENING
```

If shows `127.0.0.1` instead of `0.0.0.0`, config is wrong:
```yaml
# config.yaml should have:
installation:
  mode: server  # NOT localhost

services:
  api:
    host: 0.0.0.0  # NOT 127.0.0.1
```

---

### Issue: Router AP Isolation

**Diagnosis:** Router has AP Isolation enabled (common on guest WiFi)

**Symptoms:**
- Ping fails between devices
- Both devices can access internet
- Both devices connected to same WiFi

**Fix:**
1. Access router admin panel (usually `192.168.1.1` or `192.168.0.1`)
2. Look for "AP Isolation", "Client Isolation", or "Wireless Isolation"
3. Disable the setting
4. Reconnect devices

---

## Success Criteria

Check all that apply:

- [ ] Ping from PC 2 to PC 1 succeeds
- [ ] API health check returns `{"status": "ok"}`
- [ ] Frontend loads in PC 2 browser
- [ ] API key authentication works
- [ ] No CORS errors in browser console
- [ ] Projects list loads from PC 2
- [ ] Can create project from PC 2
- [ ] Real-time updates work (WebSocket)
- [ ] Dashboard fully functional from PC 2

If all checked: **LAN mode is working correctly!** 🎉

---

## What to Report Back

### Success Report Template

```markdown
## PC 2 LAN Testing Results

**Date:** [Date]
**PC 1 (Server):** 10.1.0.164
**PC 2 (Client):** [Your PC 2 IP]

### Test Results
- ✅ Ping: Success
- ✅ API Health: Success
- ✅ Frontend Load: Success
- ✅ API Auth: Success
- ✅ CORS: No errors
- ✅ Project CRUD: Success
- ✅ WebSocket: Success

### Notes
- All tests passed without issues
- Network latency: ~5ms
- No firewall configuration needed (already open)

**Status:** LAN mode fully functional
```

### Failure Report Template

```markdown
## PC 2 LAN Testing Results

**Date:** [Date]
**PC 1 (Server):** 10.1.0.164
**PC 2 (Client):** [Your PC 2 IP]

### Test Results
- ✅ Ping: Success
- ❌ API Health: Failed
- ⏸️ Frontend Load: Not tested (API failed)
- ⏸️ API Auth: Not tested
- ⏸️ CORS: Not tested
- ⏸️ Project CRUD: Not tested
- ⏸️ WebSocket: Not tested

### Error Details
- API Health returned: "Connection refused"
- Verified API running on PC 1: Yes (curl localhost:7272/health works)
- Firewall rules: Checked, rule exists but may be disabled
- Port 7272 listening: Yes, on 0.0.0.0

### Actions Taken
1. Verified API running locally on PC 1 ✅
2. Checked firewall rules on PC 1 (found rule, but not sure if active)
3. Attempted curl from PC 2 again (still fails)

### Next Steps Needed
- Help verifying Windows Firewall rule is actually active
- Consider temporarily disabling firewall for testing
- Check if antivirus is blocking port 7272

**Status:** Blocked at API connectivity
```

---

## Additional Resources

- **LAN Setup Guide:** `F:\GiljoAI_MCP\docs\LAN_SETUP_GUIDE.md`
- **Session Memory:** `F:\GiljoAI_MCP\docs\sessions\2025-01-07-lan-wizard-ux-complete.md`
- **DevLog:** `F:\GiljoAI_MCP\docs\devlog\2025-01-07-lan-wizard-ux-complete.md`
- **API Logs:** `F:\GiljoAI_MCP\logs\api.log`
- **Frontend Logs:** Browser console (F12 → Console tab)

---

## Quick Reference Commands

### PC 1 (Server) - F:\GiljoAI_MCP

```bash
# Check services
curl http://localhost:7272/health
curl http://localhost:7274

# Restart services
.\stop_giljo.bat
.\start_giljo.bat

# Check listening ports
netstat -an | findstr 7272
netstat -an | findstr 7274

# Get server IP
ipconfig | findstr IPv4

# View API logs
type logs\api.log | more
```

### PC 2 (Client)

```bash
# Basic connectivity
ping 10.1.0.164

# API health
curl http://10.1.0.164:7272/health

# Test with API key
curl -H "X-API-Key: YOUR_KEY_HERE" http://10.1.0.164:7272/api/v1/projects

# Browser
http://10.1.0.164:7274
```

---

## Safety Notes

- **Do not expose to internet** - This setup is for LAN only
- **API key is sensitive** - Do not share publicly
- **Firewall rules** - Only open ports 7272 and 7274 on trusted network
- **Database security** - PostgreSQL stays on localhost (never exposed to network)

---

**Good luck with testing! Report back with results.**

If you encounter issues not covered in this guide, provide:
1. Exact error message
2. Step where it failed
3. Output of diagnostic commands
4. PC 1 and PC 2 IP addresses
5. Network topology (router model, WiFi vs Ethernet, etc.)
