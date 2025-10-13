# LAN Authentication - Migration Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-07
**Audience:** System Administrators, DevOps Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Migration Checklist](#pre-migration-checklist)
4. [Migration Steps](#migration-steps)
5. [Post-Migration Verification](#post-migration-verification)
6. [Updating MCP Clients](#updating-mcp-clients)
7. [Rollback Procedure](#rollback-procedure)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This guide walks you through migrating from **localhost mode** (development, no authentication) to **LAN mode** (production, authentication required).

### What Changes

| Aspect | Localhost Mode (Before) | LAN Mode (After) |
|--------|------------------------|------------------|
| **Authentication** | None (bypass) | Required (JWT + API keys) |
| **API Binding** | 127.0.0.1 | 0.0.0.0 (all interfaces) |
| **Network Access** | Local machine only | LAN/WAN accessible |
| **User Management** | N/A | User accounts with roles |
| **MCP Access** | Direct connection | API key authentication |
| **Security** | Minimal | Full authentication + CORS + rate limiting |

### Migration Timeline

**Estimated Time:** 30-45 minutes

**Downtime:** ~10 minutes (during service restart)

**Planning Window:** Schedule during low-usage period

---

## Prerequisites

### System Requirements

✅ **PostgreSQL 18** installed and running
✅ **Python 3.11+** with venv activated
✅ **GiljoAI MCP** installed and working in localhost mode
✅ **Admin access** to server and database
✅ **Backup tools** available (pg_dump, tar)

### Knowledge Requirements

✅ Basic PostgreSQL administration
✅ Linux/Windows command line familiarity
✅ Understanding of authentication concepts
✅ Access to server firewall configuration

---

## Pre-Migration Checklist

### Step 1: Backup Current System

**Database Backup:**
```bash
# Create backup directory
mkdir -p ~/giljo-backups/$(date +%Y-%m-%d)
cd ~/giljo-backups/$(date +%Y-%m-%d)

# Backup PostgreSQL database
pg_dump -U postgres -d giljo_mcp > giljo_mcp_pre_auth.sql

# Verify backup
ls -lh giljo_mcp_pre_auth.sql
head -20 giljo_mcp_pre_auth.sql  # Should show database structure
```

**Configuration Backup:**
```bash
# Backup config files
cp F:/GiljoAI_MCP/config.yaml config.yaml.backup
cp F:/GiljoAI_MCP/.env .env.backup  # If exists

# Backup entire installation (optional)
tar -czf giljo_mcp_full_backup.tar.gz \
  -C F:/GiljoAI_MCP \
  --exclude=venv \
  --exclude=node_modules \
  --exclude=data \
  .
```

### Step 2: Verify Current State

**Check Services:**
```bash
# API server running?
curl http://127.0.0.1:7272/api/health
# Should return: {"status":"healthy"}

# Frontend accessible?
curl http://127.0.0.1:7274
# Should return HTML
```

**Check Database:**
```bash
# Database accessible?
psql -U postgres -d giljo_mcp -c "SELECT count(*) FROM projects;"

# Check current mode
grep "mode:" config.yaml
# Should show: mode: localhost
```

### Step 3: Document Current State

**Active Projects:**
```bash
psql -U postgres -d giljo_mcp -c "
  SELECT id, name, status
  FROM projects
  WHERE status = 'active';
"
```

**Active Agents:**
```bash
psql -U postgres -d giljo_mcp -c "
  SELECT id, name, role
  FROM agents
  WHERE status = 'active';
"
```

**Active Tasks:**
```bash
psql -U postgres -d giljo_mcp -c "
  SELECT id, title, status
  FROM tasks
  WHERE status IN ('pending', 'in_progress');
"
```

**Save output for post-migration comparison.**

---

## Migration Steps

### Step 1: Stop Services

```bash
# Stop API server
# (If running as systemd service)
sudo systemctl stop giljo-api

# Or if running manually
pkill -f "python api/run_api.py"

# Stop frontend dev server (if running)
pkill -f "npm run dev"

# Verify stopped
netstat -tuln | grep 7272  # Should show nothing
netstat -tuln | grep 7274  # Should show nothing
```

### Step 2: Run Database Migration

**Check Current Migration:**
```bash
cd F:/GiljoAI_MCP
source venv/bin/activate  # Windows: venv\Scripts\activate

alembic current
# Should show previous migration
```

**Apply Auth Migration:**
```bash
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade ... -> 11b1e4318444, add user and apikey tables for lan auth
```

**Verify Tables Created:**
```bash
psql -U postgres -d giljo_mcp -c "\dt"
```

**Should show:**
```
 users
 api_keys
 [... other tables ...]
```

### Step 3: Update Configuration

**Edit config.yaml:**
```yaml
# Change mode
installation:
  mode: lan  # Changed from: localhost

# Update API binding
services:
  api:
    host: 0.0.0.0  # Changed from: 127.0.0.1
    port: 7272

# Configure CORS
security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      - http://YOUR_SERVER_IP:7274  # Add your server's IP

# Enable authentication
security:
  api_keys:
    require_for_modes:
      - lan
      - server
      - wan

# Optional: Rate limiting
security:
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

**Set Environment Variables:**
```bash
# Generate strong JWT secret (32+ characters)
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Save to .env file
cat >> .env <<EOF
JWT_SECRET=$JWT_SECRET
DATABASE_URL=postgresql://giljo_user:YOUR_PASSWORD@localhost:5432/giljo_mcp
EOF

# Secure .env file
chmod 600 .env
```

### Step 4: Create First Admin User

**Option A: Via Python Script (Recommended)**

```python
# create_admin.py
import asyncio
from datetime import datetime, timezone
from passlib.hash import bcrypt
import asyncpg

async def create_admin():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='4010',  # Your PostgreSQL password
        database='giljo_mcp'
    )

    # Generate UUID
    import uuid
    user_id = str(uuid.uuid4())

    # Hash password
    password_hash = bcrypt.hash("your_secure_admin_password")

    # Insert admin user
    await conn.execute('''
        INSERT INTO users (id, tenant_key, username, email, password_hash, full_name, role, is_active, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ''', user_id, 'default', 'admin', 'admin@example.com', password_hash,
         'System Administrator', 'admin', True, datetime.now(timezone.utc))

    print(f"Admin user created successfully!")
    print(f"Username: admin")
    print(f"Password: your_secure_admin_password")
    print(f"Role: admin")

    await conn.close()

asyncio.run(create_admin())
```

**Run script:**
```bash
python create_admin.py
```

**Option B: Direct SQL**

```bash
psql -U postgres -d giljo_mcp <<'EOF'
INSERT INTO users (
    id, tenant_key, username, email, password_hash, full_name, role, is_active, created_at
) VALUES (
    gen_random_uuid()::text,
    'default',
    'admin',
    'admin@example.com',
    '$2b$12$YOUR_BCRYPT_HASH_HERE',  -- Generate with: python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))"
    'System Administrator',
    'admin',
    true,
    NOW()
);
EOF
```

**Verify User Created:**
```bash
psql -U postgres -d giljo_mcp -c "SELECT id, username, role FROM users WHERE username='admin';"
```

### Step 5: Configure Firewall

**Linux (ufw):**
```bash
# Allow API port
sudo ufw allow 7272/tcp comment 'GiljoAI MCP API'

# Allow Frontend port
sudo ufw allow 7274/tcp comment 'GiljoAI MCP Frontend'

# Ensure PostgreSQL is NOT exposed
sudo ufw deny 5432/tcp

# Reload firewall
sudo ufw reload

# Verify rules
sudo ufw status numbered
```

**Windows Firewall:**
```powershell
# Allow API port
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -LocalPort 7272 -Protocol TCP -Action Allow

# Allow Frontend port
New-NetFirewallRule -DisplayName "GiljoAI MCP Frontend" -Direction Inbound -LocalPort 7274 -Protocol TCP -Action Allow
```

### Step 6: Restart Services

**Start API Server:**
```bash
cd F:/GiljoAI_MCP
source venv/bin/activate

python api/run_api.py
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7272
```

**Start Frontend (Development):**
```bash
cd frontend
npm run dev
```

**Or configure systemd services for production:**

```ini
# /etc/systemd/system/giljo-api.service
[Unit]
Description=GiljoAI MCP API Server
After=network.target postgresql.service

[Service]
Type=simple
User=giljo
WorkingDirectory=/path/to/GiljoAI_MCP
Environment="PATH=/path/to/GiljoAI_MCP/venv/bin"
Environment="JWT_SECRET=your_secret_here"
ExecStart=/path/to/GiljoAI_MCP/venv/bin/python api/run_api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable giljo-api
sudo systemctl start giljo-api
sudo systemctl status giljo-api
```

---

## Post-Migration Verification

### Test 1: API Health Check

**From Server (Localhost):**
```bash
curl http://127.0.0.1:7272/api/health
# Should return: {"status":"healthy"}
```

**From LAN Client:**
```bash
curl http://YOUR_SERVER_IP:7272/api/health
# Should return: {"status":"healthy"}
```

### Test 2: Authentication Required

**Unauthenticated Request (Should Fail):**
```bash
curl http://YOUR_SERVER_IP:7272/api/projects
# Should return: 401 Unauthorized
```

### Test 3: Login Works

```bash
curl -X POST http://YOUR_SERVER_IP:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_secure_admin_password"}' \
  -c cookies.txt -v

# Should return:
# {"message":"Login successful","username":"admin","role":"admin",...}

# And set cookie:
# Set-Cookie: access_token=eyJ...; HttpOnly; Path=/; SameSite=Lax
```

### Test 4: Authenticated Request Works

```bash
curl http://YOUR_SERVER_IP:7272/api/auth/me -b cookies.txt
# Should return user profile
```

### Test 5: Data Integrity

**Verify Projects:**
```bash
psql -U postgres -d giljo_mcp -c "
  SELECT id, name, status
  FROM projects
  WHERE status = 'active';
"
# Should match pre-migration output
```

**Verify Agents:**
```bash
psql -U postgres -d giljo_mcp -c "
  SELECT id, name, role
  FROM agents
  WHERE status = 'active';
"
# Should match pre-migration output
```

### Test 6: Frontend Access

**Open Browser:**
```
http://YOUR_SERVER_IP:7274
```

**Should show:**
- Login page
- Username/password fields
- No errors in console

**Log in:**
- Enter admin credentials
- Should redirect to dashboard
- Should show username in top-right

---

## Updating MCP Clients

After migration, MCP clients need API keys for authentication.

### Step 1: Generate API Key (Web Dashboard)

1. **Log in to dashboard:** http://YOUR_SERVER_IP:7274
2. **Navigate to:** Settings → API Keys
3. **Click:** "Generate New Key"
4. **Enter:** Name (e.g., "Claude Desktop"), Permissions (["*"])
5. **Copy key immediately** (shown only once)

Example key:
```
gk_xJ4kL9mN2pQ7rS8tU1vW3xY5zAbCdEfGhIjKlMnOpQrStUvWxYz
```

### Step 2: Update Claude Desktop Config

**Location:**
- **Windows:** `C:\Users\<username>\.claude.json`
- **Mac/Linux:** `~/.claude.json`

**Update configuration:**
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "F:\\GiljoAI_MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_MCP_HOME": "F:/GiljoAI_MCP",
        "GILJO_SERVER_URL": "http://YOUR_SERVER_IP:7272",
        "GILJO_API_KEY": "gk_xJ4kL9mN2pQ7rS8tU1vW3xY5zAbCdEfGhIjKlMnOpQrStUvWxYz"
      }
    }
  }
}
```

**Changes:**
- Added `GILJO_SERVER_URL` (LAN IP, not localhost)
- Added `GILJO_API_KEY` (generated API key)

### Step 3: Test MCP Connection

**Restart Claude Desktop**

**Test MCP tools in conversation:**
```
Can you list my GiljoAI projects?
```

**Should:**
- Connect to server via LAN
- Authenticate with API key
- Return project list

**Troubleshooting:**
```bash
# Check API key is valid
curl -H "X-API-Key: gk_your_key" http://YOUR_SERVER_IP:7272/api/projects

# Check MCP logs
# Windows: %APPDATA%\Claude\logs
# Mac: ~/Library/Logs/Claude
```

---

## Rollback Procedure

If migration fails or issues occur:

### Step 1: Stop Services

```bash
sudo systemctl stop giljo-api
# Or: pkill -f "python api/run_api.py"
```

### Step 2: Restore Database

```bash
cd ~/giljo-backups/$(date +%Y-%m-%d)

# Drop current database
psql -U postgres -c "DROP DATABASE giljo_mcp;"

# Recreate database
psql -U postgres -c "CREATE DATABASE giljo_mcp OWNER postgres;"

# Restore backup
psql -U postgres -d giljo_mcp < giljo_mcp_pre_auth.sql

# Verify restore
psql -U postgres -d giljo_mcp -c "\dt"
# Should NOT show users/api_keys tables
```

### Step 3: Restore Configuration

```bash
cd ~/giljo-backups/$(date +%Y-%m-%d)
cp config.yaml.backup F:/GiljoAI_MCP/config.yaml
cp .env.backup F:/GiljoAI_MCP/.env  # If exists
```

### Step 4: Restart in Localhost Mode

```bash
cd F:/GiljoAI_MCP
source venv/bin/activate
python api/run_api.py
```

**Verify localhost access:**
```bash
curl http://127.0.0.1:7272/api/projects
# Should work WITHOUT authentication
```

---

## Troubleshooting

### Issue 1: Migration Fails

**Error:** `relation "users" already exists`

**Cause:** Migration was partially run before

**Solution:**
```bash
# Check migration status
alembic current

# If stuck, manually drop tables and retry
psql -U postgres -d giljo_mcp -c "DROP TABLE IF EXISTS users CASCADE;"
psql -U postgres -d giljo_mcp -c "DROP TABLE IF EXISTS api_keys CASCADE;"

# Re-run migration
alembic upgrade head
```

### Issue 2: Cannot Log In

**Error:** 401 Unauthorized

**Solutions:**
1. Verify admin user exists:
   ```bash
   psql -U postgres -d giljo_mcp -c "SELECT username, role FROM users WHERE username='admin';"
   ```

2. Verify password hash:
   ```bash
   python3 -c "from passlib.hash import bcrypt; print(bcrypt.verify('your_password', '\$2b\$12\$...'))"
   # Should print: True
   ```

3. Check JWT secret is set:
   ```bash
   echo $JWT_SECRET
   # Should print secret key
   ```

### Issue 3: API Keys Not Working

**Error:** 401 with API key

**Solutions:**
1. Verify key format:
   ```bash
   echo "gk_..." | grep "^gk_"
   # Should match
   ```

2. Check key in database:
   ```bash
   psql -U postgres -d giljo_mcp -c "SELECT name, is_active FROM api_keys WHERE key_prefix='gk_first12ch';"
   # Should show: is_active = true
   ```

3. Test key authentication:
   ```bash
   curl -v -H "X-API-Key: gk_..." http://YOUR_SERVER_IP:7272/api/projects
   # Check response headers for auth errors
   ```

### Issue 4: Frontend Cannot Connect

**Error:** Network error or CORS error

**Solutions:**
1. Verify CORS config:
   ```yaml
   security:
     cors:
       allowed_origins:
         - http://YOUR_SERVER_IP:7274
   ```

2. Check API binding:
   ```bash
   netstat -tuln | grep 7272
   # Should show: 0.0.0.0:7272 (not 127.0.0.1:7272)
   ```

3. Test CORS:
   ```bash
   curl -H "Origin: http://YOUR_SERVER_IP:7274" \
        -H "Access-Control-Request-Method: GET" \
        -X OPTIONS \
        http://YOUR_SERVER_IP:7272/api/health
   # Should return CORS headers
   ```

---

## Post-Migration Recommendations

### Security

✅ Change default admin password
✅ Create individual user accounts (don't share admin)
✅ Enable HTTPS with reverse proxy
✅ Configure firewall rules
✅ Set up automated backups
✅ Enable audit logging

### User Management

✅ Create user accounts for team members
✅ Assign appropriate roles (admin/developer/viewer)
✅ Generate API keys for each user's MCP clients
✅ Document key naming conventions

### Monitoring

✅ Set up health check monitoring
✅ Configure log aggregation
✅ Monitor failed login attempts
✅ Track API key usage
✅ Set up alerts for service downtime

---

## Additional Resources

- **[User Guide](LAN_AUTH_USER_GUIDE.md)** - End-user documentation
- **[Architecture](LAN_AUTH_ARCHITECTURE.md)** - Technical design
- **[API Reference](LAN_AUTH_API_REFERENCE.md)** - API documentation
- **[Deployment Checklist](LAN_AUTH_DEPLOYMENT_CHECKLIST.md)** - Production setup
- **[Quick Reference](LAN_AUTH_QUICK_REFERENCE.md)** - One-page cheat sheet

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-07
**Maintained By:** Documentation Manager Agent
