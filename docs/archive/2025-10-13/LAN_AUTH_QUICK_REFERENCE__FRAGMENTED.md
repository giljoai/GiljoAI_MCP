# LAN Authentication - Quick Reference

**Version:** 1.0.0 | **Last Updated:** 2025-10-07

---

## Authentication URLs

| Service | URL |
|---------|-----|
| **API Server** | http://YOUR_SERVER_IP:7272 |
| **API Docs** | http://YOUR_SERVER_IP:7272/docs |
| **Dashboard** | http://YOUR_SERVER_IP:7274 |
| **Login Page** | http://YOUR_SERVER_IP:7274/login |

---

## Authentication Methods

### JWT Cookie (Web Users)
```bash
# Login
curl -X POST http://YOUR_IP:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"pass"}' \
  -c cookies.txt

# Use cookie
curl http://YOUR_IP:7272/api/auth/me -b cookies.txt
```

### API Key (MCP Tools)
```bash
curl http://YOUR_IP:7272/api/projects \
  -H "X-API-Key: gk_your_api_key_here"
```

### Localhost Bypass (Development)
```bash
# Works only on 127.0.0.1 when mode=localhost
curl http://127.0.0.1:7272/api/projects
# No authentication needed
```

---

## API Endpoints

### Login/Logout
```bash
# Login
POST /api/auth/login
Body: {"username": "admin", "password": "pass123"}

# Logout
POST /api/auth/logout

# Get current user
GET /api/auth/me
```

### API Key Management
```bash
# List keys
GET /api/auth/api-keys

# Generate key
POST /api/auth/api-keys
Body: {"name": "My Key", "permissions": ["*"]}

# Revoke key
DELETE /api/auth/api-keys/{id}
```

### User Management (Admin Only)
```bash
# Register user
POST /api/auth/register
Body: {
  "username": "newuser",
  "password": "pass123",
  "email": "user@example.com",
  "role": "developer"
}
```

---

## API Key Format

```
gk_<32-byte-urlsafe-token>
```

**Example:**
```
gk_xJ4kL9mN2pQ7rS8tU1vW3xY5zAbCdEfGhIjKlMnOpQrStUvWxYz
```

**Prefix (display only):**
```
gk_xJ4kL9mN...
```

---

## User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full access, user management |
| **developer** | Create/edit projects, agents, tasks |
| **viewer** | Read-only access |

---

## Configuration

### config.yaml
```yaml
installation:
  mode: lan  # or localhost, server, wan

services:
  api:
    host: 0.0.0.0  # LAN: 0.0.0.0, Localhost: 127.0.0.1
    port: 7272

security:
  cors:
    allowed_origins:
      - http://YOUR_SERVER_IP:7274
  api_keys:
    require_for_modes:
      - lan
      - server
      - wan
```

### Environment Variables
```bash
# JWT secret (32+ chars)
JWT_SECRET=your_very_long_random_secret_key_here

# Database URL
DATABASE_URL=postgresql://giljo_user:PASSWORD@localhost:5432/giljo_mcp
```

---

## MCP Client Setup

### Claude Desktop (.claude.json)
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

---

## Database Commands

### Check Migration Status
```bash
alembic current
alembic history
```

### Apply Migration
```bash
alembic upgrade head
```

### Verify Tables
```bash
psql -U postgres -d giljo_mcp -c "\dt"
# Should show: users, api_keys
```

### Create Admin User (SQL)
```sql
INSERT INTO users (
    id, tenant_key, username, email, password_hash,
    full_name, role, is_active, created_at
) VALUES (
    gen_random_uuid()::text,
    'default',
    'admin',
    'admin@example.com',
    '$2b$12$...',  -- bcrypt hash
    'Administrator',
    'admin',
    true,
    NOW()
);
```

### Check Users
```bash
psql -U postgres -d giljo_mcp -c "
  SELECT id, username, role, is_active, last_login
  FROM users
  ORDER BY created_at DESC;
"
```

### Check API Keys
```bash
psql -U postgres -d giljo_mcp -c "
  SELECT id, name, key_prefix, is_active, last_used
  FROM api_keys
  ORDER BY created_at DESC;
"
```

---

## Common Tasks

### Generate API Key (CLI)
```python
import secrets
from passlib.hash import bcrypt

# Generate key
api_key = f"gk_{secrets.token_urlsafe(32)}"
key_hash = bcrypt.hash(api_key)
key_prefix = api_key[:12]

print(f"API Key: {api_key}")
print(f"Hash (store): {key_hash}")
print(f"Prefix (display): {key_prefix}...")
```

### Reset Admin Password
```python
from passlib.hash import bcrypt
import psycopg2

new_password = "new_secure_password"
password_hash = bcrypt.hash(new_password)

conn = psycopg2.connect(
    host="localhost",
    database="giljo_mcp",
    user="postgres",
    password="4010"
)
cur = conn.cursor()
cur.execute(
    "UPDATE users SET password_hash = %s WHERE username = 'admin'",
    (password_hash,)
)
conn.commit()
print("Password reset successfully")
```

### Test Authentication
```bash
# Test login
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  -c cookies.txt

# Test API key
curl http://localhost:7272/api/projects \
  -H "X-API-Key: gk_your_key"

# Test unauthenticated (should fail on LAN)
curl http://YOUR_SERVER_IP:7272/api/projects
# Expected: 401 Unauthorized
```

---

## Troubleshooting Commands

### Check Service Status
```bash
# API server running?
netstat -tuln | grep 7272

# PostgreSQL running?
systemctl status postgresql

# Check processes
ps aux | grep "python api/run_api.py"
```

### View Logs
```bash
# API logs
tail -f /var/log/giljo-mcp/api.log

# Failed logins
grep "Login failed" /var/log/giljo-mcp/api.log

# API key usage
grep "API key" /var/log/giljo-mcp/api.log
```

### Test Network Connectivity
```bash
# From server
curl http://127.0.0.1:7272/api/health

# From LAN client
curl http://YOUR_SERVER_IP:7272/api/health

# Check firewall
sudo ufw status | grep 7272
```

### Database Connectivity
```bash
# Test connection
psql -U postgres -d giljo_mcp -c "SELECT 1;"

# Check active connections
psql -U postgres -c "
  SELECT count(*)
  FROM pg_stat_activity
  WHERE datname = 'giljo_mcp';
"
```

---

## Error Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| **200** | OK | Success |
| **201** | Created | Resource created |
| **401** | Unauthorized | Invalid/missing auth |
| **403** | Forbidden | Insufficient permissions |
| **404** | Not Found | Resource doesn't exist |
| **422** | Validation Error | Invalid input |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Server Error | Internal error |

---

## Security Best Practices

### Passwords
✅ Min 12 characters
✅ Mix uppercase, lowercase, numbers, symbols
✅ Use password manager
✅ Rotate every 90 days

### API Keys
✅ Generate separate keys per application
✅ Use descriptive names
✅ Store in environment variables
✅ Never commit to version control
✅ Revoke unused keys

### Network
✅ Use HTTPS in production (reverse proxy)
✅ Configure firewall rules
✅ Restrict PostgreSQL to localhost
✅ Use strong CORS configuration
✅ Enable rate limiting

---

## Firewall Rules

### Linux (ufw)
```bash
# Allow API
sudo ufw allow 7272/tcp

# Allow Frontend
sudo ufw allow 7274/tcp

# Deny PostgreSQL external access
sudo ufw deny 5432/tcp

# Check rules
sudo ufw status numbered
```

### Windows
```powershell
New-NetFirewallRule `
  -DisplayName "GiljoAI MCP API" `
  -Direction Inbound `
  -LocalPort 7272 `
  -Protocol TCP `
  -Action Allow

New-NetFirewallRule `
  -DisplayName "GiljoAI MCP Frontend" `
  -Direction Inbound `
  -LocalPort 7274 `
  -Protocol TCP `
  -Action Allow
```

---

## Mode Switching

### Localhost → LAN
```yaml
# config.yaml
installation:
  mode: lan  # Changed from localhost

services:
  api:
    host: 0.0.0.0  # Changed from 127.0.0.1

# Then:
# 1. Run migration: alembic upgrade head
# 2. Create admin user
# 3. Restart API server
```

### LAN → Localhost
```yaml
# config.yaml
installation:
  mode: localhost

services:
  api:
    host: 127.0.0.1

# Then restart API server
# Authentication will be bypassed on 127.0.0.1
```

---

## Backup & Restore

### Backup Database
```bash
pg_dump -U postgres -d giljo_mcp > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
psql -U postgres -d giljo_mcp < backup_20251007.sql
```

### Backup Config
```bash
tar -czf config_backup.tar.gz config.yaml .env
```

---

## Additional Resources

**Full Documentation:**
- [User Guide](LAN_AUTH_USER_GUIDE.md)
- [Architecture](LAN_AUTH_ARCHITECTURE.md)
- [API Reference](LAN_AUTH_API_REFERENCE.md)
- [Deployment Checklist](LAN_AUTH_DEPLOYMENT_CHECKLIST.md)
- [Migration Guide](LAN_AUTH_MIGRATION_GUIDE.md)

**Online:**
- API Docs: http://YOUR_SERVER_IP:7272/docs
- ReDoc: http://YOUR_SERVER_IP:7272/redoc

---

**Document Version:** 1.0.0
**Maintained By:** Documentation Manager Agent
