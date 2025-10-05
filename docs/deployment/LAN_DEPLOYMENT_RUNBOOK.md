# LAN Deployment Runbook - GiljoAI MCP

**Version:** 1.0
**Last Updated:** 2025-10-05
**Deployment Mode:** Server (LAN)
**Platform:** Windows (Cross-platform compatible)

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Step-by-Step Deployment Procedure](#step-by-step-deployment-procedure)
3. [Configuration Reference](#configuration-reference)
4. [Troubleshooting Guide](#troubleshooting-guide)
5. [Operational Procedures](#operational-procedures)
6. [Rollback Procedures](#rollback-procedures)

---

## Pre-Deployment Checklist

### System Requirements Verification

**Hardware Requirements:**
- [ ] CPU: 4+ cores recommended
- [ ] RAM: 8GB minimum, 16GB recommended
- [ ] Disk: 10GB free space minimum
- [ ] Network: Gigabit Ethernet recommended

**Software Requirements:**
- [ ] Python 3.11 or higher installed
- [ ] PostgreSQL 18 installed and running
- [ ] Node.js 18+ and npm installed (for frontend)
- [ ] Git installed (for repository management)

**Network Prerequisites:**
- [ ] Server has static IP address on LAN (e.g., 10.1.0.118)
- [ ] Ports 7272 and 7274 available
- [ ] Firewall allows inbound connections on required ports
- [ ] Client devices on same subnet (e.g., 10.1.0.0/24)

**Access Credentials Needed:**
- [ ] PostgreSQL admin password (default: 4010)
- [ ] Server machine admin access (for firewall configuration)
- [ ] Generated API key for authentication
- [ ] Git credentials (if pulling from repository)

**Documentation Required:**
- [ ] Server IP address documented
- [ ] Subnet configuration documented
- [ ] List of authorized client devices/IPs
- [ ] API key storage location determined

---

## Step-by-Step Deployment Procedure

### Phase 1: Server Preparation

#### Step 1: Verify PostgreSQL Installation

```bash
# Windows - Check PostgreSQL is running
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -c "SELECT version();"

# Expected: PostgreSQL version information displayed

# Verify giljo_mcp database exists
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l | grep giljo_mcp
```

**Success Criteria:**
- PostgreSQL responds with version information
- giljo_mcp database listed

**If Failed:**
- Install PostgreSQL 18: https://www.postgresql.org/download/
- Run installer: `python installer/cli/install.py`

#### Step 2: Verify Repository and Dependencies

```bash
# Navigate to project directory
cd C:\Projects\GiljoAI_MCP

# Verify git status
git status

# Pull latest changes
git pull origin master

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

**Success Criteria:**
- All dependencies installed without errors
- No missing packages reported

#### Step 3: Determine Server Network Configuration

```bash
# Windows - Find server IP address
ipconfig | grep "IPv4 Address"

# Note your server's LAN IP (e.g., 10.1.0.118)
# This will be used in configuration
```

**Document:**
- Server IP: _________________
- Subnet mask: _________________
- Subnet CIDR: _________________ (e.g., 10.1.0.0/24)

---

### Phase 2: Configuration Changes

#### Step 4: Update config.yaml for Server Mode

**File:** `C:\Projects\GiljoAI_MCP\config.yaml`

**Required Changes:**

```yaml
installation:
  mode: server  # Change from 'localhost'

services:
  api:
    host: 0.0.0.0  # Change from '127.0.0.1'

security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://YOUR_SERVER_IP:7274  # Add your server IP
      - http://YOUR_SUBNET.*:7274   # Add wildcard for subnet

  api_keys:
    require_for_modes:
      - server
      - lan
      - wan

  rate_limiting:
    enabled: true
    requests_per_minute: 60

network:
  bind_all_interfaces: true
  server_ip: YOUR_SERVER_IP       # Your LAN IP
  subnet: YOUR_SUBNET/24           # Your subnet CIDR
  ports:
    api: 7272
    frontend: 7274
    database: 5432
```

**Example (for server 10.1.0.118):**
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

**Validation:**
```bash
# Verify config.yaml syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Expected: No errors
```

#### Step 5: Create Frontend Production Environment

**File:** `C:\Projects\GiljoAI_MCP\frontend\.env.production`

**Create with content:**
```env
VITE_API_URL=http://YOUR_SERVER_IP:7272
VITE_WS_URL=ws://YOUR_SERVER_IP:7272
```

**Example:**
```env
VITE_API_URL=http://10.1.0.118:7272
VITE_WS_URL=ws://10.1.0.118:7272
```

**Important:** Do NOT commit this file to git.

#### Step 6: Generate API Key

```bash
# Generate secure API key
python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"
```

**Output Example:**
```
giljo_lan_XtrYofhJjr0Mw-qQHzA7py9bzVZbMjKaXfnvGjWBK94
```

**Store Securely:**

**Option 1: Environment Variable** (Recommended)
```bash
# Add to .env file (NOT in git)
echo "GILJO_API_KEY=giljo_lan_YOUR_KEY_HERE" >> .env
```

**Option 2: Configuration File**
- Store in password manager
- Document location for team members
- Rotate every 90 days

**IMPORTANT:** Never commit API keys to git!

---

### Phase 3: Firewall Setup

#### Step 7: Configure Windows Firewall

**Create API Server Firewall Rule:**
```powershell
# Open PowerShell as Administrator
netsh advfirewall firewall add rule ^
  name="GiljoAI MCP API" ^
  dir=in ^
  action=allow ^
  protocol=TCP ^
  localport=7272 ^
  profile=domain,private
```

**Create Frontend Firewall Rule:**
```powershell
netsh advfirewall firewall add rule ^
  name="GiljoAI MCP Frontend" ^
  dir=in ^
  action=allow ^
  protocol=TCP ^
  localport=7274 ^
  profile=domain,private
```

**Verification:**
```powershell
# Verify API rule created
netsh advfirewall firewall show rule name="GiljoAI MCP API"

# Verify Frontend rule created
netsh advfirewall firewall show rule name="GiljoAI MCP Frontend"
```

**Success Criteria:**
- Both rules listed as "Enabled: Yes"
- Direction: In
- Profiles: Domain,Private
- Action: Allow

**Security Note:** Rules are restricted to domain and private networks only. Public networks are blocked.

---

### Phase 4: Security Validation

#### Step 8: Verify PostgreSQL Security

**Check PostgreSQL Host-Based Authentication:**
```bash
# Windows - Check pg_hba.conf
cat "/c/Program Files/PostgreSQL/18/data/pg_hba.conf" | grep -v "^#" | grep -v "^$"
```

**Expected Configuration:**
```
local   all   all                     scram-sha-256
host    all   all   127.0.0.1/32      scram-sha-256
host    all   all   ::1/128           scram-sha-256
```

**Verify:**
- Database only accepts localhost connections (127.0.0.1 and ::1)
- NO network access allowed
- Scram-sha-256 authentication required

**If network access is configured:**
```bash
# Edit pg_hba.conf to remove network access
# Restart PostgreSQL service
```

#### Step 9: Validate Configuration Files

**Run validation checks:**
```bash
cd C:\Projects\GiljoAI_MCP

# Check config.yaml deployment mode
grep "mode:" config.yaml
# Expected: mode: server

# Check API host binding
grep "host:" config.yaml | head -1
# Expected: host: 0.0.0.0

# Verify network section exists
grep -A5 "network:" config.yaml
# Expected: server_ip and subnet configured

# Check CORS origins include server IP
grep -A5 "allowed_origins:" config.yaml
# Expected: Server IP listed

# Verify frontend production env
cat frontend/.env.production
# Expected: VITE_API_URL with server IP
```

**Success Criteria:**
- All configuration files contain correct values
- No syntax errors
- Server IP consistently used across all files

---

### Phase 5: Service Startup

#### Step 10: Start API Server

```bash
cd C:\Projects\GiljoAI_MCP

# Start API server
python api/run_api.py
```

**Expected Console Output:**
```
INFO: Started server process [PID]
INFO: Waiting for application startup.
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:7272 (Press CTRL+C to quit)
```

**Verify Binding:**
```bash
# In new terminal - Check API is bound to 0.0.0.0
netstat -an | grep 7272
# Expected: 0.0.0.0:7272 LISTENING
```

**Success Criteria:**
- Server starts without errors
- Bound to 0.0.0.0:7272 (all interfaces)
- No port conflicts

**If Failed:**
- Check port 7272 not in use: `netstat -an | grep 7272`
- Verify PostgreSQL running
- Check logs: `tail -f logs/giljo_mcp.log`

#### Step 11: Start Frontend Server

```bash
# Open new terminal
cd C:\Projects\GiljoAI_MCP\frontend

# Start frontend development server
npm run dev
```

**Expected Console Output:**
```
VITE vX.X.X  ready in XXX ms

➜  Local:   http://localhost:7274/
➜  Network: http://10.1.0.118:7274/
➜  press h to show help
```

**Success Criteria:**
- Frontend builds successfully
- Accessible on port 7274
- Network URL shows server IP

---

### Phase 6: Runtime Testing

#### Step 12: Localhost Health Checks

**Test API Health Endpoint:**
```bash
curl http://127.0.0.1:7272/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "deployment_mode": "server",
  "database": "connected"
}
```

**Test Frontend Access:**
```bash
# Open browser to:
http://127.0.0.1:7274

# Expected: Dashboard loads successfully
```

**Verify Security Headers:**
```bash
curl -I http://127.0.0.1:7272/health | grep -E "(X-Frame|X-Content|X-XSS)"
```

**Expected Headers:**
```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
```

#### Step 13: LAN Connectivity Testing

**From Server Machine:**
```bash
# Test API via LAN IP
curl http://YOUR_SERVER_IP:7272/health

# Example:
curl http://10.1.0.118:7272/health
```

**Expected:** Same health response as localhost

**Test CORS Headers:**
```bash
curl -H "Origin: http://YOUR_SERVER_IP:7274" -I http://127.0.0.1:7272/health | grep "Access-Control"
```

**Expected:**
```
Access-Control-Allow-Origin: http://YOUR_SERVER_IP:7274
Access-Control-Allow-Credentials: true
```

#### Step 14: API Authentication Testing

**Test without API key (should fail in server mode):**
```bash
curl http://127.0.0.1:7272/api/v1/projects
```

**Expected Response:**
```json
{
  "detail": "API key required for server deployment mode"
}
```

**Test with valid API key:**
```bash
curl -H "X-API-Key: YOUR_API_KEY" http://127.0.0.1:7272/api/v1/projects
```

**Expected:** JSON list of projects or empty array

#### Step 15: Rate Limiting Validation

```bash
# Send 65 requests to test rate limiting (limit is 60/min)
for i in {1..65}; do
  echo "Request $i: $(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7272/health)"
done
```

**Expected Behavior:**
- Requests 1-60: 200 OK
- Requests 61-65: 429 Too Many Requests

**If all return 200:** Rate limiting may not be enabled. Check config.yaml.

---

### Phase 7: Client Device Connection

#### Step 16: Client Device Prerequisites

**On Client Device (another machine on LAN):**

- [ ] Connected to same network as server
- [ ] Can ping server IP: `ping YOUR_SERVER_IP`
- [ ] Firewall allows outbound HTTP connections
- [ ] Modern web browser installed

#### Step 17: Test Client API Access

**From Client Device:**
```bash
# Test connectivity
ping 10.1.0.118

# Test API health
curl http://10.1.0.118:7272/health

# Expected: Health check JSON response
```

**If connection refused:**
1. Verify server firewall rules active
2. Check API server is running on server machine
3. Verify client and server on same subnet
4. Check network firewall/router settings

#### Step 18: Test Client Frontend Access

**From Client Device Browser:**

1. Navigate to: `http://YOUR_SERVER_IP:7274`
2. Dashboard should load
3. Open Browser DevTools (F12)
4. Check Console tab for errors
5. Verify WebSocket connection: Should see "Connected to ws://YOUR_SERVER_IP:7272"

**If CORS errors appear:**
1. Verify server IP in config.yaml CORS allowed_origins
2. Restart API server after config changes
3. Clear browser cache and retry

#### Step 19: Test Authenticated API Calls from Client

**From Client Device:**
```bash
# Test with API key
curl -H "X-API-Key: YOUR_API_KEY" http://10.1.0.118:7272/api/v1/projects
```

**Expected:** JSON response with project data

**Share API Key with Client Users:**
- Store API key in client environment variables
- Or configure in client application settings
- Do NOT hardcode in client-side JavaScript

---

## Configuration Reference

### config.yaml Settings for LAN Mode

**Complete Server Mode Configuration:**
```yaml
installation:
  mode: server

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp
  user: giljo_user
  owner: giljo_owner

services:
  api:
    host: 0.0.0.0          # Bind all interfaces
    port: 7272
  frontend:
    port: 7274

security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://YOUR_SERVER_IP:7274
      - http://YOUR_SUBNET.*:7274

  api_keys:
    require_for_modes:
      - server
      - lan
      - wan

  rate_limiting:
    enabled: true
    requests_per_minute: 60

network:
  bind_all_interfaces: true
  server_ip: YOUR_SERVER_IP
  subnet: YOUR_SUBNET/24
  ports:
    api: 7272
    frontend: 7274
    database: 5432
```

### .env.production for Frontend

**Location:** `frontend/.env.production`

```env
VITE_API_URL=http://YOUR_SERVER_IP:7272
VITE_WS_URL=ws://YOUR_SERVER_IP:7272
```

### Firewall Rules Summary

**Windows Firewall Rules:**

| Rule Name | Port | Protocol | Direction | Profiles | Action |
|-----------|------|----------|-----------|----------|--------|
| GiljoAI MCP API | 7272 | TCP | Inbound | Domain, Private | Allow |
| GiljoAI MCP Frontend | 7274 | TCP | Inbound | Domain, Private | Allow |

**View Rules:**
```powershell
netsh advfirewall firewall show rule name="GiljoAI MCP API"
netsh advfirewall firewall show rule name="GiljoAI MCP Frontend"
```

**Delete Rules (if needed):**
```powershell
netsh advfirewall firewall delete rule name="GiljoAI MCP API"
netsh advfirewall firewall delete rule name="GiljoAI MCP Frontend"
```

### PostgreSQL Security Settings

**Host-Based Authentication (pg_hba.conf):**
```
# TYPE  DATABASE  USER  ADDRESS        METHOD
local   all       all                  scram-sha-256
host    all       all   127.0.0.1/32   scram-sha-256
host    all       all   ::1/128        scram-sha-256
```

**Location (Windows):**
```
C:\Program Files\PostgreSQL\18\data\pg_hba.conf
```

**After Editing:** Restart PostgreSQL service

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: API Server Cannot Start - Port Already in Use

**Symptoms:**
```
OSError: [WinError 10048] Only one usage of each socket address is permitted
```

**Diagnosis:**
```bash
# Check what is using port 7272
netstat -ano | findstr :7272
```

**Solutions:**
1. Kill the process using the port
2. Change port in config.yaml to alternative (e.g., 7273)
3. Restart server after port conflict resolved

#### Issue 2: LAN Clients Cannot Connect - Connection Refused

**Symptoms:**
- `curl http://SERVER_IP:7272/health` returns connection refused
- Browser shows "Unable to connect"

**Diagnosis Checklist:**
- [ ] Is API server running? `netstat -an | grep 7272`
- [ ] Is API bound to 0.0.0.0? Check server console output
- [ ] Are firewall rules active? `netsh advfirewall firewall show rule name="GiljoAI MCP API"`
- [ ] Can client ping server? `ping SERVER_IP`
- [ ] Are client and server on same subnet?

**Solutions:**
1. Verify API running: `python api/run_api.py`
2. Check host binding in config.yaml: `host: 0.0.0.0`
3. Recreate firewall rules (see Phase 3, Step 7)
4. Check network connectivity: `ping`, `traceroute`
5. Disable Windows public firewall temporarily to test

#### Issue 3: CORS Errors in Browser Console

**Symptoms:**
```
Access to fetch at 'http://SERVER_IP:7272/api/projects' from origin
'http://SERVER_IP:7274' has been blocked by CORS policy
```

**Diagnosis:**
```bash
# Check CORS configuration
grep -A5 "allowed_origins:" config.yaml
```

**Solutions:**
1. Add client origin to config.yaml:
   ```yaml
   security:
     cors:
       allowed_origins:
         - http://CLIENT_IP:7274
   ```
2. Restart API server
3. Clear browser cache
4. Use wildcard for subnet: `http://10.1.0.*:7274`

#### Issue 4: API Returns 401 Unauthorized

**Symptoms:**
```json
{"detail": "API key required for server deployment mode"}
```

**Diagnosis:**
```bash
# Check deployment mode
grep "mode:" config.yaml

# Check API key requirement
grep -A5 "api_keys:" config.yaml
```

**Solutions:**
1. Include API key in request header:
   ```bash
   curl -H "X-API-Key: YOUR_KEY" http://SERVER_IP:7272/api/projects
   ```
2. Verify API key is correct
3. For development, switch to localhost mode:
   ```yaml
   installation:
     mode: localhost
   ```

#### Issue 5: Database Connection Failed

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Diagnosis:**
```bash
# Test PostgreSQL connection
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l

# Check if giljo_mcp database exists
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l | grep giljo_mcp
```

**Solutions:**
1. Start PostgreSQL service
2. Verify credentials in config.yaml
3. Create database if missing: `python installer/cli/install.py`
4. Check PostgreSQL logs for errors

#### Issue 6: Rate Limiting - 429 Too Many Requests

**Symptoms:**
```json
{"detail": "Rate limit exceeded. Please try again later."}
```

**Diagnosis:**
- Occurs after 60 requests per minute from same IP
- Expected behavior for protection against abuse

**Solutions:**
1. **Temporary:** Wait 60 seconds for rate limit to reset
2. **Configuration:** Increase limit in config.yaml:
   ```yaml
   security:
     rate_limiting:
       requests_per_minute: 120  # Double the limit
   ```
3. **Application:** Implement request batching
4. **Development:** Disable rate limiting:
   ```yaml
   security:
     rate_limiting:
       enabled: false
   ```

#### Issue 7: Frontend Loads but API Calls Fail

**Symptoms:**
- Frontend dashboard loads
- API requests fail in Network tab
- Console shows "Failed to fetch" errors

**Diagnosis:**
```bash
# Check frontend .env.production
cat frontend/.env.production

# Verify API URL is correct
```

**Solutions:**
1. Update frontend/.env.production with correct server IP
2. Rebuild frontend: `cd frontend && npm run build`
3. Restart frontend dev server: `npm run dev`
4. Check API server is running: `curl http://SERVER_IP:7272/health`

#### Issue 8: WebSocket Connection Failed

**Symptoms:**
- Browser console: "WebSocket connection to 'ws://SERVER_IP:7272' failed"
- Real-time updates not working

**Diagnosis:**
```bash
# Check WebSocket URL in frontend
cat frontend/.env.production | grep WS_URL

# Test WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://SERVER_IP:7272/ws
```

**Solutions:**
1. Verify VITE_WS_URL in .env.production
2. Check firewall allows WebSocket connections (same port as API)
3. Restart API server
4. Test from browser console:
   ```javascript
   const ws = new WebSocket('ws://SERVER_IP:7272/ws');
   ws.onopen = () => console.log('Connected!');
   ```

### Diagnostic Commands

**Check Service Status:**
```bash
# API server running
netstat -an | grep 7272

# Frontend server running
netstat -an | grep 7274

# PostgreSQL running
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -c "SELECT 1;"
```

**View Logs:**
```bash
# API server logs
tail -f logs/giljo_mcp.log

# PostgreSQL logs (Windows)
tail -f "C:\Program Files\PostgreSQL\18\data\log\postgresql-*.log"
```

**Network Diagnostics:**
```bash
# Test connectivity
ping SERVER_IP

# Trace route
tracert SERVER_IP

# Check open ports
nmap -p 7272,7274 SERVER_IP
```

---

## Operational Procedures

### How to Start/Stop Services

#### Starting Services

**Method 1: Windows Batch Scripts**
```batch
# Start API + Frontend
start_giljo.bat

# Or individually:
start_backend.bat   # API only
start_frontend.bat  # Frontend only
```

**Method 2: Manual Start**
```bash
# Terminal 1: Start API
cd C:\Projects\GiljoAI_MCP
python api/run_api.py

# Terminal 2: Start Frontend
cd C:\Projects\GiljoAI_MCP\frontend
npm run dev
```

**Method 3: Background Processes (Linux/Mac)**
```bash
# Start API in background
nohup python api/run_api.py > logs/api.log 2>&1 &

# Start Frontend in background
cd frontend && nohup npm run dev > ../logs/frontend.log 2>&1 &
```

#### Stopping Services

**Windows:**
```powershell
# Stop API
taskkill /F /IM python.exe /FI "WINDOWTITLE eq api*"

# Stop Frontend
taskkill /F /IM node.exe /FI "WINDOWTITLE eq npm*"

# Or use batch script:
stop_giljo.bat
```

**Manual:**
- Press CTRL+C in each terminal window running services

### How to Monitor System Health

#### Real-Time Monitoring

**API Health Check:**
```bash
# Continuous health monitoring
watch -n 5 'curl -s http://127.0.0.1:7272/health | jq'
```

**Log Monitoring:**
```bash
# Watch API logs
tail -f logs/giljo_mcp.log

# Filter for errors
tail -f logs/giljo_mcp.log | grep ERROR

# Filter for authentication failures
tail -f logs/giljo_mcp.log | grep "401\|403"
```

**Service Status Dashboard:**
```bash
# Check all services
echo "API: $(curl -s http://127.0.0.1:7272/health | jq -r .status)"
echo "Frontend: $(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7274)"
echo "Database: $(PGPASSWORD=4010 psql -U postgres -d giljo_mcp -c "SELECT 1;" > /dev/null 2>&1 && echo "OK" || echo "FAIL")"
```

#### Metrics to Monitor

**System Metrics:**
- CPU usage: `top` or Task Manager
- Memory usage: `free -h` or Task Manager
- Disk space: `df -h` or File Explorer
- Network traffic: `nethogs` or Resource Monitor

**Application Metrics:**
- Active connections: `netstat -an | grep 7272 | grep ESTABLISHED | wc -l`
- Request rate: Monitor logs for request timestamps
- Error rate: `grep ERROR logs/giljo_mcp.log | tail -n 20`
- Database connections: PostgreSQL `pg_stat_activity`

**Health Check Script:**
```bash
#!/bin/bash
# health_check.sh

API_HEALTH=$(curl -s http://127.0.0.1:7272/health)
API_STATUS=$(echo $API_HEALTH | jq -r .status)

if [ "$API_STATUS" == "healthy" ]; then
    echo "✅ System healthy"
    exit 0
else
    echo "❌ System unhealthy"
    echo $API_HEALTH
    exit 1
fi
```

### How to Add New LAN Clients

#### Step 1: Verify Client Network Access

```bash
# From client device, test connectivity
ping SERVER_IP

# Test API accessibility
curl http://SERVER_IP:7272/health
```

#### Step 2: Update CORS Configuration (if needed)

**If client IP is outside current subnet:**

Edit `config.yaml`:
```yaml
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://10.1.0.118:7274
      - http://10.1.0.*:7274        # Existing subnet
      - http://192.168.1.*:7274     # New subnet
```

**Restart API server** after changes.

#### Step 3: Provide Client Access Information

**Share with client:**
- API URL: `http://SERVER_IP:7272`
- Frontend URL: `http://SERVER_IP:7274`
- API Key: `giljo_lan_YOUR_KEY`
- WebSocket URL: `ws://SERVER_IP:7272`

**Client setup instructions:**
```bash
# Set environment variable
export GILJO_API_URL=http://SERVER_IP:7272
export GILJO_API_KEY=giljo_lan_YOUR_KEY

# Or in .env file
echo "GILJO_API_URL=http://SERVER_IP:7272" >> .env
echo "GILJO_API_KEY=giljo_lan_YOUR_KEY" >> .env
```

#### Step 4: Test Client Connectivity

**From client device:**
```bash
# Test API with authentication
curl -H "X-API-Key: YOUR_API_KEY" http://SERVER_IP:7272/api/v1/projects

# Expected: JSON response with project list
```

**Browser test:**
1. Navigate to: `http://SERVER_IP:7274`
2. Open DevTools (F12)
3. Verify no CORS errors in console
4. Verify WebSocket connected

### How to Generate/Distribute API Keys

#### Generating New API Keys

**Method 1: Python Command**
```bash
python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"
```

**Method 2: API Endpoint (Future)**
```bash
# Requires admin authentication
curl -X POST -H "X-API-Key: ADMIN_KEY" \
  http://SERVER_IP:7272/api/v1/config/generate-api-key \
  -d '{"name": "client_device_1", "permissions": ["read", "write"]}'
```

#### Storing API Keys

**Server-Side Storage:**
- Keys encrypted at rest: `~/.giljo-mcp/api_keys.json`
- Encryption key: `~/.giljo-mcp/encryption_key`
- Never commit to git

**Client Distribution:**
1. **Secure sharing:** Use password manager or encrypted channel
2. **Environment variables:** Store in client .env file
3. **Configuration file:** Client application config
4. **DO NOT:** Email, Slack, or commit to repositories

#### Revoking API Keys

**Manual Revocation:**
1. Edit encrypted key file: `~/.giljo-mcp/api_keys.json`
2. Remove key from list
3. Restart API server
4. Notify affected clients

**Future API Endpoint:**
```bash
curl -X DELETE -H "X-API-Key: ADMIN_KEY" \
  http://SERVER_IP:7272/api/v1/config/revoke-api-key/KEY_ID
```

#### API Key Rotation Policy

**Recommended Schedule:**
- **Critical systems:** Every 30 days
- **Standard deployment:** Every 90 days
- **Development:** Every 180 days

**Rotation Process:**
1. Generate new API key
2. Distribute to all clients
3. Set overlap period (e.g., 7 days)
4. Revoke old key after overlap
5. Verify all clients updated

### How to Check Security Status

#### Security Audit Checklist

**Run Complete Security Check:**
```bash
# Check deployment mode
grep "mode:" config.yaml

# Verify API bound to correct interface
grep "host:" config.yaml

# Check API key requirement
grep -A3 "api_keys:" config.yaml

# Verify CORS configuration
grep -A5 "cors:" config.yaml

# Check rate limiting enabled
grep -A3 "rate_limiting:" config.yaml

# Verify PostgreSQL restricted to localhost
cat "/c/Program Files/PostgreSQL/18/data/pg_hba.conf" | grep -v "^#" | grep "host"

# Check firewall rules active
netsh advfirewall firewall show rule name="GiljoAI MCP API"
netsh advfirewall firewall show rule name="GiljoAI MCP Frontend"
```

**Expected Results:**
- Mode: server
- API host: 0.0.0.0
- API keys required: true
- CORS: Specific origins only (no wildcards)
- Rate limiting: enabled
- PostgreSQL: 127.0.0.1/32 and ::1/128 only
- Firewall: Rules enabled with domain/private profiles

#### Security Headers Validation

```bash
# Check all security headers
curl -I http://127.0.0.1:7272/health

# Expected headers:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: default-src 'self'
# Referrer-Policy: strict-origin-when-cross-origin
```

#### Authentication Testing

```bash
# Test API key requirement (should fail without key)
curl http://127.0.0.1:7272/api/v1/projects

# Test with valid key (should succeed)
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:7272/api/v1/projects
```

#### Penetration Testing

**Rate Limiting Test:**
```bash
# Should block after 60 requests/minute
for i in {1..70}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:7272/health
done
```

**CORS Bypass Test:**
```bash
# Should fail from unauthorized origin
curl -H "Origin: http://evil.com" http://127.0.0.1:7272/api/v1/projects
```

**Database Access Test:**
```bash
# Should fail from network (non-localhost)
PGPASSWORD=4010 psql -h SERVER_IP -U postgres -d giljo_mcp -c "SELECT 1;"
# Expected: Connection refused or authentication failed
```

---

## Rollback Procedures

### Scenario 1: Rollback to Localhost Mode

**When to Use:**
- LAN deployment not working
- Security concerns
- Need to return to development mode

**Procedure:**

#### Step 1: Backup Current Configuration
```bash
cd C:\Projects\GiljoAI_MCP

# Backup config files
cp config.yaml config.yaml.lan.backup
cp frontend/.env.production frontend/.env.production.backup
```

#### Step 2: Update config.yaml
```yaml
installation:
  mode: localhost  # Change from 'server'

services:
  api:
    host: 127.0.0.1  # Change from '0.0.0.0'

# CORS can remain as-is (localhost will still work)
```

#### Step 3: Remove/Disable Firewall Rules
```powershell
# Disable (don't delete) firewall rules
netsh advfirewall firewall set rule name="GiljoAI MCP API" new enable=no
netsh advfirewall firewall set rule name="GiljoAI MCP Frontend" new enable=no
```

#### Step 4: Restart Services
```bash
# Stop current services (CTRL+C in terminals)

# Start in localhost mode
python api/run_api.py
# Should now bind to 127.0.0.1:7272

cd frontend && npm run dev
```

#### Step 5: Verify Localhost Operation
```bash
# Test localhost access
curl http://127.0.0.1:7272/health

# Verify NOT accessible from network
curl http://SERVER_IP:7272/health
# Expected: Connection refused (correct for localhost mode)
```

### Scenario 2: Configuration Corruption Recovery

**When to Use:**
- config.yaml syntax errors
- Service won't start
- Unknown configuration state

**Procedure:**

#### Step 1: Restore from Backup
```bash
# If you have a backup
cp config.yaml.backup config.yaml
cp frontend/.env.production.backup frontend/.env.production
```

#### Step 2: Regenerate from Template (if no backup)
```bash
# Copy default configuration
cp installer/templates/config.yaml.template config.yaml

# Manually configure required sections
nano config.yaml
```

#### Step 3: Validate Configuration
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Run configuration test
python installer/cli/install.py --validate-config
```

#### Step 4: Restart Services
```bash
# Restart with validated configuration
python api/run_api.py
```

### Scenario 3: Database Recovery

**When to Use:**
- Database connection lost
- Data corruption
- Need to reset database

**Procedure:**

#### Step 1: Backup Existing Database
```bash
# Windows - Backup database
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/pg_dump.exe" \
  -U postgres giljo_mcp > giljo_mcp_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 2: Drop and Recreate Database
```bash
# Drop database
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres \
  -c "DROP DATABASE IF EXISTS giljo_mcp;"

# Recreate database
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres \
  -c "CREATE DATABASE giljo_mcp OWNER giljo_owner;"
```

#### Step 3: Run Migrations
```bash
# Apply database schema
python installer/cli/install.py --setup-database
```

#### Step 4: Restore Data (if needed)
```bash
# Restore from backup
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
  -U postgres giljo_mcp < giljo_mcp_backup_TIMESTAMP.sql
```

### Scenario 4: Network Isolation (Emergency)

**When to Use:**
- Security breach suspected
- Unauthorized access detected
- Need immediate network isolation

**Immediate Actions:**

#### Step 1: Disable Firewall Rules
```powershell
# Disable API access
netsh advfirewall firewall set rule name="GiljoAI MCP API" new enable=no

# Disable Frontend access
netsh advfirewall firewall set rule name="GiljoAI MCP Frontend" new enable=no
```

#### Step 2: Change API Binding
```bash
# Quick edit config.yaml
sed -i 's/host: 0.0.0.0/host: 127.0.0.1/' config.yaml
```

#### Step 3: Restart API Server
```bash
# Stop API (CTRL+C)

# Restart with localhost binding
python api/run_api.py
```

#### Step 4: Revoke All API Keys
```bash
# Clear API keys
rm ~/.giljo-mcp/api_keys.json

# Generate new encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > ~/.giljo-mcp/encryption_key
```

#### Step 5: Audit Logs
```bash
# Check for suspicious activity
grep "401\|403\|429" logs/giljo_mcp.log | tail -n 50

# Check failed authentication attempts
grep "API key" logs/giljo_mcp.log | grep -i "fail\|invalid"
```

### Full System Reset

**Nuclear Option - Complete Fresh Start:**

```bash
# 1. Backup current state
cp config.yaml config.yaml.pre-reset
PGPASSWORD=4010 pg_dump -U postgres giljo_mcp > full_backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Stop all services
taskkill /F /IM python.exe
taskkill /F /IM node.exe

# 3. Reset database
PGPASSWORD=4010 psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# 4. Reset configuration
rm config.yaml
rm frontend/.env.production
rm ~/.giljo-mcp/api_keys.json

# 5. Reinstall
python installer/cli/install.py

# 6. Reconfigure for LAN (follow deployment procedure from beginning)
```

---

## Quick Reference

### Essential URLs

**Localhost Access:**
- API: http://127.0.0.1:7272
- Frontend: http://127.0.0.1:7274
- API Docs: http://127.0.0.1:7272/docs
- Health: http://127.0.0.1:7272/health

**LAN Access (Example: 10.1.0.118):**
- API: http://10.1.0.118:7272
- Frontend: http://10.1.0.118:7274
- API Docs: http://10.1.0.118:7272/docs
- Health: http://10.1.0.118:7272/health

### Essential Commands

```bash
# Start services
python api/run_api.py              # API server
cd frontend && npm run dev         # Frontend

# Check status
curl http://127.0.0.1:7272/health  # API health
netstat -an | grep 7272            # API listening

# View logs
tail -f logs/giljo_mcp.log         # API logs

# Generate API key
python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"

# Database access
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -d giljo_mcp
```

### Key Files

- Configuration: `config.yaml`
- Frontend Environment: `frontend/.env.production`
- API Keys: `~/.giljo-mcp/api_keys.json` (encrypted)
- Encryption Key: `~/.giljo-mcp/encryption_key`
- Logs: `logs/giljo_mcp.log`
- PostgreSQL Config: `C:\Program Files\PostgreSQL\18\data\pg_hba.conf`

---

## Support and Resources

### Documentation

- **Security Report:** `docs/deployment/SECURITY_FIXES_REPORT.md`
- **Network Checklist:** `docs/deployment/NETWORK_DEPLOYMENT_CHECKLIST.md`
- **Access URLs:** `docs/deployment/LAN_ACCESS_URLS.md`
- **Test Report:** `docs/deployment/LAN_TEST_REPORT.md`
- **Runtime Testing:** `docs/deployment/RUNTIME_TESTING_QUICKSTART.md`

### Troubleshooting Resources

1. Check logs: `logs/giljo_mcp.log`
2. Review test report: See Phase 3 validation results
3. Consult security checklist: `docs/deployment/LAN_SECURITY_CHECKLIST.md`
4. Verify configuration: Run validation commands in this runbook

### Emergency Contacts

- **System Administrator:** [Your team contact]
- **Security Issues:** [Security team contact]
- **Database Administrator:** [DBA contact]

---

**Runbook Version:** 1.0
**Last Updated:** 2025-10-05
**Maintainer:** Documentation Manager Agent
**Next Review:** 2025-11-05
