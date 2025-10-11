# LAN Authentication User Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-07
**Audience:** System Administrators, Developers, End Users

---

## Table of Contents

1. [Overview](#overview)
2. [LAN Mode vs Localhost Mode](#lan-mode-vs-localhost-mode)
3. [Getting Started](#getting-started)
4. [First-Time Setup](#first-time-setup)
5. [Logging In to the Dashboard](#logging-in-to-the-dashboard)
6. [Managing API Keys](#managing-api-keys)
7. [Using API Keys with MCP Tools](#using-api-keys-with-mcp-tools)
8. [User Management (Admin Only)](#user-management-admin-only)
9. [Troubleshooting](#troubleshooting)
10. [Security Best Practices](#security-best-practices)

---

## Overview

GiljoAI MCP now supports secure authentication for LAN and WAN deployment modes. This guide covers:

- **Web Authentication**: Username/password login for dashboard access
- **API Key Authentication**: Secure keys for MCP tools and programmatic access
- **User Management**: Creating and managing user accounts (admin only)
- **Multi-Tenant Isolation**: Each deployment is isolated by tenant key

### Authentication Methods

| Method | Use Case | Storage | Expiration |
|--------|----------|---------|------------|
| **JWT Cookie** | Web dashboard access | httpOnly cookie | 24 hours |
| **API Key** | MCP tools, scripts | Hashed in database | Never (until revoked) |
| **Localhost Bypass** | Development on 127.0.0.1 | N/A | N/A |

---

## LAN Mode vs Localhost Mode

### Localhost Mode (Development)

- **Access**: 127.0.0.1 only (single machine)
- **Authentication**: Disabled (localhost bypass)
- **API Binding**: 127.0.0.1:7272
- **Frontend**: http://127.0.0.1:7274
- **Use Case**: Local development and testing

### LAN Mode (Production)

- **Access**: All network interfaces (0.0.0.0)
- **Authentication**: Required (JWT + API keys)
- **API Binding**: 0.0.0.0:7272 (accessible from LAN)
- **Frontend**: http://YOUR_SERVER_IP:7274
- **Use Case**: Team collaboration, multi-user environments

### Switching Between Modes

Authentication mode is determined by your `config.yaml`:

```yaml
installation:
  mode: localhost  # or 'lan', 'server', 'wan'

security:
  api_keys:
    require_for_modes:
      - server
      - lan
      - wan
```

**To enable LAN mode:**
1. Edit `config.yaml` → set `mode: lan`
2. Restart API server: `python api/run_api.py`
3. Create admin user (first-time only)

---

## Getting Started

### Prerequisites

- GiljoAI MCP installed and configured
- PostgreSQL 18 database running
- Config mode set to `lan` or `server`
- API server running on network-accessible port

### Quick Start Checklist

✅ Database migration applied (User and APIKey tables created)
✅ Config mode set to LAN/server
✅ First admin user created via setup wizard
✅ API server accessible from network
✅ Dashboard accessible from browser

---

## First-Time Setup

### Step 1: Run Database Migration

The User and APIKey tables are created automatically during installation. If upgrading:

```bash
# Check if migration is needed
alembic current

# Apply migration if needed
alembic upgrade head
```

**Migration Details:**
- File: `migrations/versions/11b1e4318444_add_user_and_apikey_tables_for_lan_auth.py`
- Tables Created: `users`, `api_keys`
- Indexes: Tenant key, username, email, API key hash

### Step 2: Create First Admin User

**Option A: Via Setup Wizard (Recommended)**

The installer automatically prompts for admin user creation:

```bash
python installer/cli/install.py
```

Follow prompts to create:
- Username (3-64 chars)
- Password (min 8 chars)
- Email (optional)
- Full name (optional)

**Option B: Via Python Script**

```python
import asyncio
from datetime import datetime, timezone
from passlib.hash import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.giljo_mcp.models import User

async def create_admin():
    engine = create_engine("postgresql://giljo_user:YOUR_PASSWORD@localhost:5432/giljo_mcp")
    Session = sessionmaker(bind=engine)
    session = Session()

    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=bcrypt.hash("your_secure_password"),
        full_name="System Administrator",
        role="admin",
        tenant_key="default",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    session.add(admin)
    session.commit()
    print(f"Admin user created: {admin.username}")
    session.close()

asyncio.run(create_admin())
```

### Step 3: Verify Setup

1. **Test API endpoint:**
   ```bash
   curl http://YOUR_SERVER_IP:7272/api/health
   ```

2. **Access dashboard:**
   Open browser: `http://YOUR_SERVER_IP:7274`

3. **Log in with admin credentials**

---

## Logging In to the Dashboard

### Web Login Process

1. **Navigate to Dashboard**
   ```
   http://YOUR_SERVER_IP:7274
   ```

2. **Enter Credentials**
   - Username: Your username (not email)
   - Password: Your password

   ![Login Screen](../assets/login-screen.png)

3. **Success Indicators**
   - Redirected to dashboard home page
   - Username displayed in top-right corner
   - Role badge shown (Admin/Developer/Viewer)

### Login Response

Upon successful login:
- **JWT token** created (24-hour expiration)
- **httpOnly cookie** set (secure, not accessible via JavaScript)
- **Session started** - automatic authentication for all subsequent requests

### Session Duration

- **Default**: 24 hours
- **Extension**: Login again to refresh
- **Manual logout**: Click user menu → Logout

### Login Errors

| Error Message | Cause | Solution |
|--------------|-------|----------|
| "Invalid credentials" | Wrong username/password | Verify credentials, check caps lock |
| "User account is inactive" | Account disabled by admin | Contact administrator |
| "Not authenticated" | Session expired | Log in again |
| "Network error" | API server not reachable | Check server status, firewall |

---

## Managing API Keys

API keys enable programmatic access for MCP tools and scripts without requiring interactive login.

### Creating an API Key

1. **Log in to Dashboard**
2. **Navigate to Settings → API Keys** (or Profile → API Keys)
3. **Click "Generate New Key"**
4. **Fill in Details:**
   - **Name**: Descriptive label (e.g., "MCP Claude Desktop", "CI/CD Pipeline")
   - **Permissions**: Select permissions (default: all)

5. **Copy the Key IMMEDIATELY**

   ⚠️ **WARNING**: The plaintext key is shown **ONLY ONCE**. Store it securely!

   Example key:
   ```
   gk_xJ4kL9mN2pQ7rS8tU1vW3xY5zAbCdEfGhIjKlMnOpQrStUvWxYz
   ```

6. **Store Securely**
   - Password manager (recommended)
   - Environment variable
   - Secure configuration file (never commit to git)

### Viewing Your API Keys

**Dashboard → Settings → API Keys** shows:

- **Name**: Your descriptive label
- **Key Prefix**: First 12 characters (e.g., `gk_xJ4kL9mN...`)
- **Permissions**: Granted permissions
- **Status**: Active or Revoked
- **Created**: Creation timestamp
- **Last Used**: Last authentication timestamp

**Note**: Full keys are NEVER displayed after creation.

### Revoking an API Key

1. **Navigate to API Keys list**
2. **Find the key to revoke**
3. **Click "Revoke" button**
4. **Confirm revocation**

**Effects:**
- Key immediately stops working
- Cannot be un-revoked (create new key if needed)
- Shows "Revoked" status with timestamp

### API Key Permissions

Current system supports wildcard permissions (`["*"]`). Future versions will support granular permissions:

```json
{
  "permissions": [
    "projects:read",
    "projects:write",
    "agents:read",
    "tasks:write"
  ]
}
```

---

## Using API Keys with MCP Tools

### MCP Server Configuration

**Claude Desktop Config** (`~/.claude.json` or `C:\Users\<username>\.claude.json`):

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_MCP_HOME": "/path/to/GiljoAI_MCP",
        "GILJO_SERVER_URL": "http://YOUR_SERVER_IP:7272",
        "GILJO_API_KEY": "gk_your_api_key_here"
      }
    }
  }
}
```

**Environment Variables:**

```bash
# Linux/Mac (.bashrc, .zshrc)
export GILJO_API_KEY="gk_your_api_key_here"
export GILJO_SERVER_URL="http://192.168.1.100:7272"

# Windows (PowerShell)
$env:GILJO_API_KEY = "gk_your_api_key_here"
$env:GILJO_SERVER_URL = "http://192.168.1.100:7272"

# Windows (Command Prompt)
set GILJO_API_KEY=gk_your_api_key_here
set GILJO_SERVER_URL=http://192.168.1.100:7272
```

### Testing API Key Authentication

**cURL:**
```bash
curl -H "X-API-Key: gk_your_api_key_here" \
     http://YOUR_SERVER_IP:7272/api/projects
```

**Python:**
```python
import requests

headers = {"X-API-Key": "gk_your_api_key_here"}
response = requests.get("http://YOUR_SERVER_IP:7272/api/projects", headers=headers)
print(response.json())
```

**Expected Response:**
```json
{
  "projects": [...]
}
```

### API Key Security

✅ **DO:**
- Store in environment variables
- Use different keys for different applications
- Rotate keys periodically
- Revoke compromised keys immediately
- Use descriptive names for tracking

❌ **DON'T:**
- Commit keys to version control
- Share keys between users
- Store in plaintext files
- Log API keys
- Use same key everywhere

---

## User Management (Admin Only)

Only users with the `admin` role can create, modify, and delete user accounts.

### User Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| **admin** | Full access, user management | System administrators |
| **developer** | Create/edit projects, agents, tasks | Development team |
| **viewer** | Read-only access | Stakeholders, observers |

### Creating a New User

1. **Log in as Admin**
2. **Navigate to Settings → Users** (admin-only section)
3. **Click "Create User"**
4. **Fill in Details:**
   - Username (3-64 chars, unique)
   - Email (optional, unique if provided)
   - Full name (optional)
   - Password (min 8 chars)
   - Role (admin/developer/viewer)
   - Tenant key (default: "default")

5. **Click "Create"**

**Via API:**
```bash
curl -X POST http://YOUR_SERVER_IP:7272/api/auth/register \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=YOUR_JWT_TOKEN" \
  -d '{
    "username": "newuser",
    "password": "secure_password123",
    "email": "newuser@example.com",
    "full_name": "New User",
    "role": "developer",
    "tenant_key": "default"
  }'
```

### Listing Users

**Dashboard**: Settings → Users

**API**:
```bash
curl -H "Cookie: access_token=YOUR_JWT_TOKEN" \
     http://YOUR_SERVER_IP:7272/api/users
```

### Deactivating a User

Deactivated users cannot log in but their data is preserved.

1. **Settings → Users**
2. **Find user**
3. **Click "Deactivate"**
4. **Confirm**

**API**:
```bash
curl -X PATCH http://YOUR_SERVER_IP:7272/api/users/{user_id} \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=YOUR_JWT_TOKEN" \
  -d '{"is_active": false}'
```

---

## Troubleshooting

### Cannot Log In

**Issue**: "Invalid credentials" error

**Solutions:**
1. Verify username (not email)
2. Check caps lock
3. Reset password if forgotten
4. Verify user account is active
5. Check database connection

**Debug:**
```bash
# Check user exists
psql -U postgres -d giljo_mcp -c "SELECT username, is_active FROM users WHERE username='admin';"

# Verify password hash exists
psql -U postgres -d giljo_mcp -c "SELECT username, LENGTH(password_hash) FROM users WHERE username='admin';"
```

### API Key Not Working

**Issue**: 401 Unauthorized with API key

**Solutions:**
1. Verify key format: `gk_...` prefix
2. Check key is active (not revoked)
3. Ensure `X-API-Key` header is set
4. Verify server URL is correct
5. Check network connectivity

**Debug:**
```bash
# Test with verbose output
curl -v -H "X-API-Key: gk_your_key" http://YOUR_SERVER_IP:7272/api/projects

# Check API key in database
psql -U postgres -d giljo_mcp -c "SELECT name, is_active, revoked_at FROM api_keys WHERE key_prefix='gk_first12ch';"
```

### Session Expired

**Issue**: Redirected to login after working session

**Cause**: JWT token expired (24 hours)

**Solution**: Log in again to refresh session

### Localhost Bypass Not Working

**Issue**: Authentication required on 127.0.0.1

**Cause**: Config mode set to LAN/server

**Solution**:
```yaml
# config.yaml
installation:
  mode: localhost  # Change from 'lan' to 'localhost'
```

Then restart API server.

### Cannot Access from Network

**Issue**: Connection refused from other machines

**Solutions:**
1. Verify config binding: `0.0.0.0` (not `127.0.0.1`)
2. Check firewall rules (port 7272, 7274)
3. Verify PostgreSQL allows network connections
4. Test with local curl first

**Debug:**
```bash
# Check API binding
netstat -an | grep 7272

# Test local access
curl http://127.0.0.1:7272/api/health

# Test network access
curl http://YOUR_SERVER_IP:7272/api/health
```

### Database Connection Errors

**Issue**: "Cannot connect to database"

**Solutions:**
1. Verify PostgreSQL is running
2. Check database credentials in config
3. Verify network connectivity to database
4. Check PostgreSQL `pg_hba.conf` for access rules

**Debug:**
```bash
# Test PostgreSQL connection
psql -U giljo_user -h localhost -d giljo_mcp

# Check PostgreSQL is listening
netstat -an | grep 5432
```

---

## Security Best Practices

### Password Security

✅ **Strong Passwords:**
- Minimum 12 characters (system minimum: 8)
- Mix of uppercase, lowercase, numbers, symbols
- Avoid common words or patterns
- Use password manager

✅ **Password Storage:**
- Stored as bcrypt hash (never plaintext)
- Cost factor 12 (industry standard)
- Unique salt per password

### API Key Security

✅ **Key Management:**
- Generate separate keys per application
- Use descriptive names for tracking
- Rotate keys every 90 days
- Revoke unused keys immediately

✅ **Key Storage:**
- Environment variables (preferred)
- Secure vault (HashiCorp Vault, AWS Secrets Manager)
- Encrypted configuration files
- Never in version control or logs

### Network Security

✅ **Firewall Configuration:**
- Restrict API port (7272) to trusted IPs
- Restrict frontend port (7274) to LAN
- Restrict PostgreSQL (5432) to localhost

✅ **HTTPS/TLS:**
- Use reverse proxy (nginx, Apache) with TLS
- Enforce HTTPS in production
- Use valid SSL certificates

### Session Security

✅ **JWT Tokens:**
- httpOnly cookies (XSS protection)
- SameSite=Lax (CSRF protection)
- 24-hour expiration
- Secure flag in production (HTTPS)

✅ **Session Management:**
- Log out after use
- Don't share sessions
- Monitor active sessions (future feature)

### Audit and Monitoring

✅ **Logging:**
- Monitor failed login attempts
- Log API key usage
- Track user creation/deletion
- Alert on suspicious activity

✅ **Regular Audits:**
- Review active users monthly
- Revoke unused API keys quarterly
- Update passwords every 90 days
- Scan for security vulnerabilities

---

## Next Steps

**For System Administrators:**
- Set up HTTPS with reverse proxy
- Configure firewall rules
- Set up automated backups
- Implement monitoring and alerting

**For Developers:**
- Generate API key for development
- Configure MCP client tools
- Test API integration
- Read API documentation: http://YOUR_SERVER_IP:7272/docs

**For End Users:**
- Request account from administrator
- Set strong password
- Generate API key if needed
- Familiarize with dashboard

---

## Additional Resources

- **[LAN Authentication Architecture](LAN_AUTH_ARCHITECTURE.md)** - Technical deep dive
- **[API Reference](LAN_AUTH_API_REFERENCE.md)** - Complete API documentation
- **[Deployment Checklist](LAN_AUTH_DEPLOYMENT_CHECKLIST.md)** - Production deployment guide
- **[Migration Guide](LAN_AUTH_MIGRATION_GUIDE.md)** - Upgrading from localhost to LAN
- **[Quick Reference](LAN_AUTH_QUICK_REFERENCE.md)** - One-page cheat sheet

---

**Questions or Issues?**
- Check [Troubleshooting](#troubleshooting) section above
- Review [LAN Test Report](LAN_AUTH_TEST_REPORT.md) for known issues
- Consult [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) for system design

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-07
**Maintained By:** Documentation Manager Agent
