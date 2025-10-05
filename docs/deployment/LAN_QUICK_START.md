# LAN Quick Start Guide - GiljoAI MCP

**Get your LAN deployment running in 15 minutes**

**Version:** 1.0
**Date:** 2025-10-05

---

## For System Administrators (Server Setup)

### Prerequisites Checklist

Before you begin, ensure you have:

- [ ] Windows machine with admin access
- [ ] Python 3.11+ installed
- [ ] PostgreSQL 18 installed and running
- [ ] Node.js 18+ and npm installed
- [ ] Git repository cloned to `C:\Projects\GiljoAI_MCP`
- [ ] Static LAN IP address for server (e.g., 10.1.0.118)

**Check installed versions:**
```bash
python --version          # Should be 3.11+
psql --version           # Should be PostgreSQL 18
node --version           # Should be 18+
```

---

### Quick Install Steps (10-15 minutes)

#### Step 1: Find Your Server IP (1 minute)

```bash
# Windows - Get your LAN IP
ipconfig | grep "IPv4 Address"

# Note your IP address (e.g., 10.1.0.118)
```

**Write it down:** Server IP: `_______________`

---

#### Step 2: Install Dependencies (2 minutes)

```bash
cd C:\Projects\GiljoAI_MCP

# Install Python packages
pip install -r requirements.txt

# Install frontend packages
cd frontend
npm install
cd ..
```

---

#### Step 3: Configure for LAN (3 minutes)

**Edit `config.yaml`** - Change these lines:

```yaml
installation:
  mode: server              # Change from 'localhost'

services:
  api:
    host: 0.0.0.0          # Change from '127.0.0.1'

security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://YOUR_SERVER_IP:7274    # Add your IP
      - http://YOUR_SUBNET.*:7274     # Add subnet wildcard

network:
  bind_all_interfaces: true
  server_ip: YOUR_SERVER_IP           # Your LAN IP
  subnet: YOUR_SUBNET/24              # Your subnet (e.g., 10.1.0.0/24)
```

**Example for server 10.1.0.118:**
```yaml
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://10.1.0.118:7274
      - http://10.1.0.*:7274

network:
  bind_all_interfaces: true
  server_ip: 10.1.0.118
  subnet: 10.1.0.0/24
```

**Create `frontend/.env.production`** with:
```env
VITE_API_URL=http://YOUR_SERVER_IP:7272
VITE_WS_URL=ws://YOUR_SERVER_IP:7272
```

---

#### Step 4: Generate API Key (1 minute)

```bash
python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"
```

**Copy the output** (e.g., `giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94`)

**Save it to `.env` file:**
```bash
echo "GILJO_API_KEY=giljo_lan_YOUR_KEY_HERE" >> .env
```

**IMPORTANT:** Save this key somewhere safe. You'll need it for client access.

---

#### Step 5: Configure Firewall (2 minutes)

**Open PowerShell as Administrator** and run:

```powershell
# Allow API access
netsh advfirewall firewall add rule name="GiljoAI MCP API" dir=in action=allow protocol=TCP localport=7272 profile=domain,private

# Allow Frontend access
netsh advfirewall firewall add rule name="GiljoAI MCP Frontend" dir=in action=allow protocol=TCP localport=7274 profile=domain,private
```

**Verify rules created:**
```powershell
netsh advfirewall firewall show rule name="GiljoAI MCP API"
```

You should see: `Enabled: Yes`

---

#### Step 6: Start Services (1 minute)

**Terminal 1 - Start API:**
```bash
cd C:\Projects\GiljoAI_MCP
python api/run_api.py
```

**Wait for:** `Uvicorn running on http://0.0.0.0:7272`

**Terminal 2 - Start Frontend:**
```bash
cd C:\Projects\GiljoAI_MCP\frontend
npm run dev
```

**Wait for:** `Network: http://YOUR_SERVER_IP:7274/`

---

#### Step 7: Validation (2 minutes)

**Test localhost access:**
```bash
curl http://127.0.0.1:7272/health
```

**Expected response:**
```json
{"status": "healthy", "version": "2.0.0", "deployment_mode": "server"}
```

**Test LAN access:**
```bash
curl http://YOUR_SERVER_IP:7272/health
```

**Same response expected.**

**Test in browser:**
1. Open browser
2. Navigate to: `http://YOUR_SERVER_IP:7274`
3. Dashboard should load

---

### Your Server is Ready!

**Server Status:**
- API Server: `http://YOUR_SERVER_IP:7272`
- Frontend: `http://YOUR_SERVER_IP:7274`
- API Key: `giljo_lan_YOUR_KEY`

**Next Steps:**
1. Share access information with team members
2. Test from another LAN device
3. Review full deployment documentation if issues occur

**Access Information to Share:**
```
GiljoAI MCP Server Access

API URL: http://YOUR_SERVER_IP:7272
Frontend URL: http://YOUR_SERVER_IP:7274
API Key: giljo_lan_YOUR_KEY

Instructions:
1. Ensure you're on the same network (subnet YOUR_SUBNET.0/24)
2. Open browser to frontend URL
3. For API access, include header: X-API-Key: YOUR_KEY
```

---

## For End Users (Client Setup)

### What You Need

Your administrator should provide:
- [ ] Server IP address (e.g., 10.1.0.118)
- [ ] API Key (e.g., giljo_lan_XXXXX...)
- [ ] Confirmation you're on the same network

### Quick Connection Steps (5 minutes)

#### Step 1: Test Connectivity (1 minute)

```bash
# Can you reach the server?
ping SERVER_IP

# Example:
ping 10.1.0.118
```

**Success:** You should see replies. If "Request timed out," contact your network admin.

---

#### Step 2: Access Frontend (1 minute)

**Open browser and navigate to:**
```
http://SERVER_IP:7274
```

**Example:**
```
http://10.1.0.118:7274
```

**Expected:** GiljoAI MCP dashboard loads.

**If you see a connection error:**
- Verify server IP is correct
- Check you're on the same network
- Ask admin to verify firewall rules

---

#### Step 3: Verify WebSocket Connection (1 minute)

**In browser with dashboard open:**
1. Press F12 to open DevTools
2. Click Console tab
3. Look for message: `Connected to ws://SERVER_IP:7272`

**If you see WebSocket errors:**
- Refresh page
- Check network connection
- Verify with admin that API server is running

---

#### Step 4: Test API Access (Optional - for developers)

**If you're developing against the API:**

```bash
# Test without API key (should fail)
curl http://SERVER_IP:7272/api/v1/projects

# Expected: 401 Unauthorized

# Test with API key (should succeed)
curl -H "X-API-Key: YOUR_API_KEY" http://SERVER_IP:7272/api/v1/projects

# Expected: JSON response
```

**Set up API key in your environment:**

**Windows:**
```batch
setx GILJO_API_URL "http://SERVER_IP:7272"
setx GILJO_API_KEY "giljo_lan_YOUR_KEY"
```

**Linux/Mac:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export GILJO_API_URL=http://SERVER_IP:7272
export GILJO_API_KEY=giljo_lan_YOUR_KEY
```

**Or create `.env` file in your project:**
```env
GILJO_API_URL=http://10.1.0.118:7272
GILJO_API_KEY=giljo_lan_YOUR_KEY
```

---

### You're Connected!

**What You Can Do:**
- Browse projects and agents in dashboard
- Create new projects
- Spawn agents for tasks
- Monitor agent activity in real-time
- View system health and metrics

**Need Help?**
- Check browser console (F12) for errors
- Ask admin to check server logs
- Review full documentation: `docs/deployment/LAN_DEPLOYMENT_RUNBOOK.md`

---

## Common Commands Reference

### Server Administrator Commands

**Start Services:**
```bash
# API
python api/run_api.py

# Frontend
cd frontend && npm run dev
```

**Stop Services:**
- Press CTRL+C in each terminal

**Check Status:**
```bash
# API health
curl http://127.0.0.1:7272/health

# Services listening
netstat -an | grep 7272
netstat -an | grep 7274
```

**View Logs:**
```bash
# API logs
tail -f logs/giljo_mcp.log

# Filter for errors
tail -f logs/giljo_mcp.log | grep ERROR
```

**Generate API Key:**
```bash
python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"
```

**Verify Firewall:**
```powershell
netsh advfirewall firewall show rule name="GiljoAI MCP API"
netsh advfirewall firewall show rule name="GiljoAI MCP Frontend"
```

**Database Access:**
```bash
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -d giljo_mcp
```

### End User Commands

**Test Connectivity:**
```bash
# Ping server
ping SERVER_IP

# Test API
curl http://SERVER_IP:7272/health
```

**API Request with Authentication:**
```bash
# Get projects
curl -H "X-API-Key: YOUR_KEY" http://SERVER_IP:7272/api/v1/projects

# Get agents
curl -H "X-API-Key: YOUR_KEY" http://SERVER_IP:7272/api/v1/agents
```

**Browser Access:**
```
http://SERVER_IP:7274
```

---

## Troubleshooting Quick Fixes

### Issue: Cannot connect from LAN

**Quick Checks:**
```bash
# 1. Is API running?
netstat -an | grep 7272

# 2. Is API bound to 0.0.0.0?
grep "host:" config.yaml

# 3. Are firewall rules enabled?
netsh advfirewall firewall show rule name="GiljoAI MCP API"

# 4. Can you ping the server?
ping SERVER_IP
```

**Quick Fix:**
1. Restart API server: `python api/run_api.py`
2. Verify output says: `http://0.0.0.0:7272`
3. Recreate firewall rules (Step 5 above)

### Issue: CORS errors in browser

**Quick Fix:**
1. Check frontend `.env.production` has correct server IP
2. Check `config.yaml` CORS section includes your server IP
3. Restart API server
4. Clear browser cache and refresh

### Issue: 401 Unauthorized errors

**Quick Fix:**
1. Verify you're using the correct API key
2. Include header: `X-API-Key: YOUR_KEY`
3. Check server is in server mode: `grep "mode:" config.yaml`

### Issue: Frontend loads but no data

**Quick Checks:**
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for failed requests
4. Verify API server is running

**Quick Fix:**
1. Verify `.env.production` API URL is correct
2. Restart frontend: `npm run dev`
3. Test API directly: `curl http://SERVER_IP:7272/health`

### Issue: Database connection failed

**Quick Fix:**
```bash
# 1. Check PostgreSQL is running
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l

# 2. Verify database exists
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l | grep giljo_mcp

# 3. Recreate database if needed
python installer/cli/install.py
```

---

## Health Check Script

**Save as `health_check.sh` or `health_check.bat`:**

```bash
#!/bin/bash
# Quick health check for GiljoAI MCP

echo "===== GiljoAI MCP Health Check ====="
echo ""

# API Health
echo "1. API Server:"
API_RESPONSE=$(curl -s http://127.0.0.1:7272/health)
if [ -n "$API_RESPONSE" ]; then
    echo "   ✅ API is responding"
    echo "   Status: $(echo $API_RESPONSE | jq -r .status)"
else
    echo "   ❌ API is not responding"
fi
echo ""

# Frontend
echo "2. Frontend:"
FRONTEND_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7274)
if [ "$FRONTEND_CODE" = "200" ]; then
    echo "   ✅ Frontend is serving"
else
    echo "   ❌ Frontend is not accessible (HTTP $FRONTEND_CODE)"
fi
echo ""

# Database
echo "3. Database:"
DB_TEST=$(PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -d giljo_mcp -c "SELECT 1;" 2>&1)
if echo "$DB_TEST" | grep -q "1 row"; then
    echo "   ✅ Database is connected"
else
    echo "   ❌ Database connection failed"
fi
echo ""

# Firewall
echo "4. Firewall Rules:"
FW_API=$(netsh advfirewall firewall show rule name="GiljoAI MCP API" 2>&1)
if echo "$FW_API" | grep -q "Enabled.*Yes"; then
    echo "   ✅ API firewall rule enabled"
else
    echo "   ❌ API firewall rule missing or disabled"
fi
echo ""

echo "===== Health Check Complete ====="
```

**Run with:**
```bash
bash health_check.sh
```

---

## Getting More Help

**Full Documentation:**
- Complete Deployment Runbook: `docs/deployment/LAN_DEPLOYMENT_RUNBOOK.md`
- Security Details: `docs/deployment/SECURITY_FIXES_REPORT.md`
- Network Configuration: `docs/deployment/NETWORK_DEPLOYMENT_CHECKLIST.md`
- Test Results: `docs/deployment/LAN_TEST_REPORT.md`

**Common Resources:**
- Installation Guide: `docs/manuals/INSTALL.md`
- MCP Tools Manual: `docs/manuals/MCP_TOOLS_MANUAL.md`
- Technical Architecture: `docs/TECHNICAL_ARCHITECTURE.md`

**Still Stuck?**
1. Check logs: `logs/giljo_mcp.log`
2. Review troubleshooting section in full runbook
3. Run health check script above
4. Contact your system administrator

---

**Quick Start Guide Version:** 1.0
**Last Updated:** 2025-10-05
**For Full Details:** See `LAN_DEPLOYMENT_RUNBOOK.md`
