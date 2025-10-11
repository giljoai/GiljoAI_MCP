# Migration Guide: v2.x to v3.0

**From**: GiljoAI MCP v2.x (any 2.x release)
**To**: GiljoAI MCP v3.0.0
**Migration Time**: 30-60 minutes
**Difficulty**: Medium
**Risk Level**: Low (rollback available)

## Executive Summary

GiljoAI MCP v3.0.0 represents a major architectural shift from a three-mode deployment system (LOCAL/LAN/WAN) to a unified single-product architecture. This migration is **required** for all v2.x users and introduces **breaking changes** that necessitate configuration updates and firewall reconfiguration.

### What's Changing

**Removed**:
- DeploymentMode enum (LOCAL/LAN/WAN modes)
- Mode-based network binding
- Mode-based authentication toggling
- `installation.mode` configuration field

**New**:
- Unified network binding (always `0.0.0.0`)
- Auto-login for localhost clients (127.0.0.1, ::1)
- Firewall-controlled access (replaces mode-based binding)
- Simplified configuration structure

### Why This Matters

The v2.x architecture maintained three separate deployment modes with 87% code duplication. v3.0 consolidates this into a single, unified architecture where:
- The application always binds to all interfaces
- Your operating system firewall controls who can access it
- Authentication is always enabled (but auto-grants for localhost)

This provides better security (defense in depth), simpler maintenance, and consistent behavior across all deployment contexts.

---

## Pre-Migration Checklist

Before beginning migration, complete these steps:

- [ ] **Backup your database**
  ```bash
  pg_dump -U postgres giljo_mcp > giljo_mcp_backup_$(date +%Y%m%d).sql
  ```

- [ ] **Export current configuration**
  ```bash
  cp config.yaml config.yaml.v2_backup
  cp .env .env.v2_backup
  ```

- [ ] **Document custom modifications**
  - List any custom code changes
  - Note any non-standard configurations
  - Record any third-party integrations

- [ ] **Test on staging environment**
  - If possible, test migration on non-production system first
  - Validate rollback procedures work

- [ ] **Review breaking changes** (see below)

- [ ] **Schedule maintenance window**
  - Migration requires 30-60 minutes
  - Services will be offline during migration
  - Plan for rollback time if needed

---

## Breaking Changes

### 1. DeploymentMode Enum Removed

**v2.x Code**:
```python
from giljo_mcp.config_manager import DeploymentMode

if config.deployment.mode == DeploymentMode.LOCAL:
    # localhost-specific logic
elif config.deployment.mode == DeploymentMode.LAN:
    # LAN-specific logic
```

**v3.0 Code**:
```python
# DeploymentMode no longer exists
# Use feature detection instead

from giljo_mcp.config_manager import config

# Check if request is from localhost
if request.client.host in ("127.0.0.1", "::1"):
    # Auto-authenticated localhost client
    pass
else:
    # Network client - requires authentication
    pass
```

**Impact**: Code importing `DeploymentMode` will fail with `ImportError`

**Migration**: Remove mode-checking logic, use IP-based detection or feature flags

---

### 2. Network Binding Always `0.0.0.0`

**v2.x Behavior**:
- LOCAL mode: Binds to `127.0.0.1` (localhost only)
- LAN mode: Binds to `0.0.0.0` (all interfaces)
- WAN mode: Binds to `127.0.0.1` (expects reverse proxy)

**v3.0 Behavior**:
- Always binds to `0.0.0.0` (all interfaces)
- Firewall controls who can connect
- No mode-based binding changes

**Impact**:
- Services now listen on all network interfaces by default
- **CRITICAL**: Without firewall configuration, services are network-accessible

**Migration**:
1. Application binding requires no changes (automatically `0.0.0.0`)
2. **MUST** configure firewall to control access (see Firewall Configuration section)

---

### 3. Auto-Login for Localhost Clients

**v2.x Behavior**:
- LOCAL mode: No authentication required
- LAN mode: Authentication required for all clients
- WAN mode: Authentication required for all clients

**v3.0 Behavior**:
- Authentication always enabled
- Localhost clients (127.0.0.1, ::1) auto-authenticated as "localhost" user
- Network clients require JWT or API key authentication

**Impact**:
- Localhost users see instant access (no login screen) - **same as v2.x LOCAL mode**
- Network users must authenticate - **same as v2.x LAN/WAN modes**
- Database always includes user management tables (no schema differences by mode)

**Migration**: No code changes needed - behavior is backward-compatible

---

### 4. Configuration File Structure Changed

**v2.x config.yaml**:
```yaml
installation:
  mode: local  # or 'lan', 'wan'

server:
  api_host: 127.0.0.1  # Changes based on mode
  api_port: 7272

security:
  authentication_enabled: false  # Disabled in LOCAL mode
```

**v3.0 config.yaml**:
```yaml
installation:
  version: 3.0.0
  deployment_context: localhost  # Descriptive only, not functional

server:
  api_host: 0.0.0.0  # Always all interfaces
  api_port: 7272

security:
  authentication_enabled: true  # Always enabled
  auto_login_localhost: true  # New feature
```

**Impact**:
- `installation.mode` field removed
- `server.api_host` must be `0.0.0.0`
- `security.authentication_enabled` must be `true`

**Migration**: See Configuration Migration section below

---

### 5. Database Schema Changes

**New Column**: `users.is_system_user` (boolean)

**Purpose**: Marks auto-created "localhost" user as system-managed

**Impact**: Existing databases need migration

**Migration**: Alembic migration automatically applies this change

---

## Migration Steps

### Step 1: Stop Services

Stop all GiljoAI MCP services before migration:

**Windows**:
```bash
# If using service scripts
stop_giljo.bat

# Or manually stop processes
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *giljo*"
```

**Linux/macOS**:
```bash
# If using systemd
sudo systemctl stop giljoai-api
sudo systemctl stop giljoai-dashboard

# Or manually
pkill -f "giljo_mcp"
```

Verify services stopped:
```bash
# No output means services stopped
netstat -ano | findstr "7272 7274"  # Windows
netstat -tlnp | grep -E "7272|7274"  # Linux/macOS
```

---

### Step 2: Backup Current State

**Database**:
```bash
# Full database backup
pg_dump -U postgres giljo_mcp > giljo_mcp_backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup created
ls -lh giljo_mcp_backup_*.sql
```

**Configuration**:
```bash
# Backup config files
cp config.yaml config.yaml.v2_backup
cp .env .env.v2_backup

# Backup entire installation (optional but recommended)
tar -czf giljoai_backup_$(date +%Y%m%d).tar.gz \
    config.yaml .env data/ logs/
```

---

### Step 3: Upgrade GiljoAI MCP

**Using pip**:
```bash
cd F:/GiljoAI_MCP

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Upgrade to v3.0.0
pip install --upgrade giljo-mcp==3.0.0

# Verify version
python -m giljo_mcp --version
# Expected output: 3.0.0
```

**Using git** (if installed from source):
```bash
cd F:/GiljoAI_MCP

# Fetch latest changes
git fetch origin

# Checkout v3.0.0 tag
git checkout v3.0.0

# Install updated dependencies
pip install -r requirements.txt
```

---

### Step 4: Migrate Configuration

Use the provided migration script:

```bash
python scripts/migrate_config_v3.py config.yaml
```

Or manually update `config.yaml`:

**Remove these fields**:
```yaml
installation:
  mode: local  # DELETE THIS LINE
```

**Add/Update these fields**:
```yaml
installation:
  version: 3.0.0  # ADD THIS
  deployment_context: localhost  # ADD THIS (descriptive only)

server:
  api_host: 0.0.0.0  # CHANGE FROM 127.0.0.1 TO 0.0.0.0

security:
  authentication_enabled: true  # MUST BE TRUE
  auto_login_localhost: true  # ADD THIS
```

**Example before/after**:

**v2.x config.yaml**:
```yaml
installation:
  mode: local
  version: 2.9.0

server:
  api_host: 127.0.0.1
  api_port: 7272
  api_key: null

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp

security:
  authentication_enabled: false
```

**v3.0 config.yaml**:
```yaml
installation:
  version: 3.0.0
  deployment_context: localhost

server:
  api_host: 0.0.0.0  # CHANGED
  api_port: 7272
  # api_key field removed (now per-user)

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp

security:
  authentication_enabled: true  # CHANGED
  auto_login_localhost: true  # NEW
```

Save the file after editing.

---

### Step 5: Update Environment Variables

Edit `.env` file:

**Remove**:
```bash
GILJO_MCP_MODE=local  # DELETE THIS
```

**Add** (if not present):
```bash
GILJO_AUTO_LOGIN_LOCALHOST=true
GILJO_NETWORK_BINDING=0.0.0.0
```

**Verify** `.env` contents:
```bash
cat .env | grep -E "GILJO_AUTO_LOGIN|GILJO_NETWORK_BINDING"
```

---

### Step 6: Run Database Migration

Apply Alembic migrations to add new schema changes:

```bash
cd F:/GiljoAI_MCP

# Check current migration version
alembic current

# Apply all pending migrations
alembic upgrade head

# Verify migration successful
alembic current
# Should show: 003_system_user (head), 2ff9170e5524 (head)
```

**Verify database changes**:
```bash
psql -U postgres -d giljo_mcp -c "\d users"
```

Expected output should include:
```
 is_system_user | boolean | not null | default false
```

---

### Step 7: Configure Firewall

**CRITICAL**: v3.0 always binds to `0.0.0.0`, so you must configure your firewall to control access.

#### For Localhost Development (Block External Access)

**Windows PowerShell (as Administrator)**:
```powershell
# Block external connections
New-NetFirewallRule -DisplayName "GiljoAI MCP - Block External API" `
    -Direction Inbound -Action Block -Protocol TCP -LocalPort 7272 `
    -RemoteAddress Any -Profile Domain,Private,Public

# Allow localhost connections
New-NetFirewallRule -DisplayName "GiljoAI MCP - Allow Localhost API" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272 `
    -RemoteAddress 127.0.0.1,::1 -Profile Domain,Private,Public

# Repeat for Dashboard (7274) and WebSocket (6001)
```

**Linux (UFW)**:
```bash
sudo ufw deny 7272/tcp
sudo ufw deny 7274/tcp
sudo ufw deny 6001/tcp
sudo ufw reload
# Localhost connections bypass UFW by default
```

**macOS (pf)**:
```bash
# Create /etc/pf.anchors/giljoai with rules
# See FIREWALL_CONFIGURATION.md for details
sudo pfctl -f /etc/pf.conf
```

#### For Team LAN (Allow Specific Subnet)

Replace `192.168.1.0/24` with your actual LAN subnet:

**Windows**:
```powershell
New-NetFirewallRule -DisplayName "GiljoAI MCP - LAN Access" `
    -Direction Inbound -Action Allow -Protocol TCP `
    -LocalPort 7272,7274,6001 `
    -RemoteAddress 192.168.1.0/24 -Profile Domain,Private
```

**Linux (UFW)**:
```bash
sudo ufw allow from 192.168.1.0/24 to any port 7272 proto tcp
sudo ufw allow from 192.168.1.0/24 to any port 7274 proto tcp
sudo ufw allow from 192.168.1.0/24 to any port 6001 proto tcp
sudo ufw reload
```

**See**: `docs/guides/FIREWALL_CONFIGURATION.md` for comprehensive firewall setup instructions.

---

### Step 8: Create Localhost User (If Fresh Install)

For fresh v3.0 installs, the localhost user is auto-created on first startup.

For migrations, verify the user exists:

```bash
psql -U postgres -d giljo_mcp -c "SELECT username, is_system_user FROM users WHERE username='localhost';"
```

If not present, create manually:

```sql
INSERT INTO users (username, email, is_system_user, created_at)
VALUES ('localhost', 'localhost@local', true, NOW());
```

---

### Step 9: Start Services

Start GiljoAI MCP services:

**Windows**:
```bash
start_giljo.bat
```

**Linux/macOS**:
```bash
# Using systemd
sudo systemctl start giljoai-api
sudo systemctl start giljoai-dashboard

# Or directly
python api/run_api.py &
npm run dev --prefix frontend &
```

**Verify services started**:
```bash
# Check processes
netstat -ano | findstr "7272 7274"  # Windows
netstat -tlnp | grep -E "7272|7274"  # Linux/macOS

# Test API
curl http://localhost:7272/health
# Expected: {"status": "healthy"}
```

---

### Step 10: Verify Migration

**Test Localhost Access**:

1. Open browser: `http://localhost:7274`
2. Should auto-login as "localhost" user (no login screen)
3. Dashboard should load normally

**Test API Access**:

```bash
# Health check
curl http://localhost:7272/health

# API endpoint (should auto-authenticate)
curl http://localhost:7272/api/projects
```

**Test Network Access** (if LAN configured):

From another machine on your network:

```bash
# Replace with server IP
curl http://192.168.1.100:7272/health
```

Should require authentication (401 Unauthorized if not authenticated).

**Check Firewall Blocking**:

From an external IP (or simulate by blocking your IP):

```bash
# Should be blocked (connection timeout or refused)
curl http://YOUR_PUBLIC_IP:7272/health
```

---

## Feature Flag Mapping

If you had custom code checking deployment mode, here's how to migrate:

### v2.x LOCAL Mode

**Old Code**:
```python
if config.deployment.mode == DeploymentMode.LOCAL:
    api_key_required = False
    network_binding = "127.0.0.1"
```

**v3.0 Code**:
```python
# Auto-login middleware handles localhost detection
# No mode checking needed
# Check request IP if custom logic required:
if request.client.host in ("127.0.0.1", "::1"):
    # Localhost client - auto-authenticated
    pass
```

---

### v2.x LAN Mode

**Old Code**:
```python
if config.deployment.mode == DeploymentMode.LAN:
    api_key_required = True
    network_binding = "0.0.0.0"
    cors_origins = ["http://192.168.1.0/24"]
```

**v3.0 Code**:
```python
# Authentication always enabled
# Network binding always 0.0.0.0
# Configure CORS in config.yaml:
security:
  cors:
    allowed_origins:
      - http://192.168.1.100:7274
      - http://192.168.1.101:7274
```

---

### v2.x WAN Mode

**Old Code**:
```python
if config.deployment.mode == DeploymentMode.WAN:
    require_https = True
    api_key_required = True
    rate_limiting_enabled = True
```

**v3.0 Code**:
```python
# Use feature flags instead of mode:
from giljo_mcp.config_manager import config

if config.security.require_https:
    # HTTPS enforcement
    pass

if config.security.rate_limiting.enabled:
    # Rate limiting
    pass
```

---

## API Endpoint Changes

### Removed Endpoints

None. All v2.x API endpoints remain functional in v3.0.

### New Endpoints

**MCP Installer** (Phase 2 feature):
- `GET /api/mcp-installer/windows` - Download Windows installer script
- `GET /api/mcp-installer/unix` - Download Unix installer script
- `POST /api/mcp-installer/share-link` - Generate secure download links
- `GET /download/mcp/{token}/{platform}` - Public download via token

---

## Testing Your Migration

### Smoke Test Checklist

- [ ] **Services Running**: Verify API and Dashboard processes active
- [ ] **Localhost Access**: Open `http://localhost:7274`, auto-login works
- [ ] **API Health**: `curl http://localhost:7272/health` returns 200 OK
- [ ] **Database Connection**: API can query database successfully
- [ ] **Firewall Blocking**: External access blocked (test from another device)
- [ ] **LAN Access** (if configured): Team members can access via LAN IP
- [ ] **Authentication**: Network clients require API key/JWT
- [ ] **WebSocket**: Real-time updates work in Dashboard
- [ ] **Existing Projects**: All projects load correctly
- [ ] **Existing Agents**: Agent history preserved

### Integration Test

Run the test suite:

```bash
pytest tests/ -v --tb=short
```

Expected results:
- Unit tests: 18-21 passing (86-100%)
- Template tests: 47 passing (100%)
- Integration tests: May be blocked (see KNOWN_ISSUES.md)

### Load Test (Optional)

```bash
# Test API can handle load
ab -n 1000 -c 10 http://localhost:7272/health
```

---

## Rollback Procedures

If migration fails or issues arise, rollback to v2.x:

### Step 1: Stop v3.0 Services

```bash
# Stop services
stop_giljo.bat  # Windows
sudo systemctl stop giljoai-*  # Linux
```

### Step 2: Restore Database

```bash
# Drop v3.0 database
dropdb -U postgres giljo_mcp

# Restore v2.x backup
createdb -U postgres giljo_mcp
psql -U postgres -d giljo_mcp < giljo_mcp_backup_YYYYMMDD.sql
```

### Step 3: Restore Configuration

```bash
# Restore config files
cp config.yaml.v2_backup config.yaml
cp .env.v2_backup .env
```

### Step 4: Downgrade Application

```bash
# If using pip
pip install giljo-mcp==2.9.0

# If using git
git checkout v2.9.0
pip install -r requirements.txt
```

### Step 5: Remove Firewall Rules

**Windows**:
```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"} | Remove-NetFirewallRule
```

**Linux**:
```bash
sudo ufw delete allow 7272/tcp
sudo ufw delete deny 7272/tcp
# Repeat for other ports
```

### Step 6: Restart v2.x Services

```bash
start_giljo.bat  # Windows
sudo systemctl start giljoai-*  # Linux
```

### Step 7: Verify v2.x Functional

Test v2.x works as expected:

```bash
curl http://localhost:7272/health
```

Open Dashboard: `http://localhost:7274`

---

## Common Migration Issues

### Issue 1: "DeploymentMode not found" Import Error

**Error**:
```python
ImportError: cannot import name 'DeploymentMode' from 'giljo_mcp.config_manager'
```

**Cause**: Custom code still importing `DeploymentMode` enum

**Solution**:
1. Search codebase for `DeploymentMode` imports:
   ```bash
   grep -r "DeploymentMode" src/
   ```
2. Remove or replace with IP-based detection
3. Restart services

---

### Issue 2: Services Accessible from Internet (Security Risk)

**Symptoms**: Services accessible from public internet after migration

**Cause**: Firewall not configured, application bound to `0.0.0.0`

**Solution**:
1. **IMMEDIATELY** stop services:
   ```bash
   stop_giljo.bat
   ```
2. Configure firewall (see Step 7 above)
3. Verify firewall blocks external access:
   ```bash
   # From external IP
   curl http://YOUR_PUBLIC_IP:7272/health
   # Should timeout or refuse connection
   ```
4. Restart services only after firewall configured

---

### Issue 3: Localhost Auto-Login Not Working

**Symptoms**: Login screen appears when accessing `http://localhost:7274`

**Causes**:
1. `auto_login_localhost: true` not in config.yaml
2. Accessing via network IP instead of localhost
3. Browser cached old session

**Solutions**:
1. Verify config.yaml has `security.auto_login_localhost: true`
2. Access via `http://localhost:7274` (not `http://127.0.0.1:7274` or IP)
3. Clear browser cache and cookies
4. Restart API server

---

### Issue 4: Database Migration Fails

**Error**:
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxxxx'
```

**Cause**: Migration history inconsistency

**Solution**:
1. Check current migration:
   ```bash
   alembic current
   ```
2. Manually stamp to latest revision:
   ```bash
   alembic stamp head
   ```
3. Try migration again:
   ```bash
   alembic upgrade head
   ```
4. If still failing, check migration files in `alembic/versions/`

---

### Issue 5: Network Clients Get 401 Unauthorized

**Symptoms**: LAN clients cannot access API, receive 401 errors

**Causes**:
1. API key not provided in request
2. JWT token expired
3. User doesn't have valid API key

**Solutions**:
1. Generate API key for user:
   ```sql
   UPDATE users SET api_key = 'gk_user_xxx' WHERE username = 'alice';
   ```
2. Include API key in requests:
   ```bash
   curl -H "X-API-Key: gk_user_xxx" http://192.168.1.100:7272/api/projects
   ```
3. Or use JWT authentication (login first)

---

## Migration Verification Checklist

After completing migration, verify all items:

### Functionality
- [ ] Dashboard loads at `http://localhost:7274`
- [ ] Auto-login works (no login screen for localhost)
- [ ] API responds to health check
- [ ] Database connection successful
- [ ] Existing projects visible
- [ ] Agent history preserved
- [ ] WebSocket updates work
- [ ] Can create new project
- [ ] Can spawn new agent

### Security
- [ ] External access blocked (firewall configured)
- [ ] Localhost access allowed
- [ ] LAN access works (if configured)
- [ ] Network clients require authentication
- [ ] PostgreSQL not accessible from network (port 5432 blocked)
- [ ] API keys work correctly
- [ ] JWT authentication functional

### Configuration
- [ ] `config.yaml` has `version: 3.0.0`
- [ ] `installation.mode` field removed
- [ ] `server.api_host` is `0.0.0.0`
- [ ] `security.authentication_enabled` is `true`
- [ ] `security.auto_login_localhost` is `true`
- [ ] `.env` file updated (no `GILJO_MCP_MODE`)

### Database
- [ ] Alembic migrations applied (`alembic current` shows heads)
- [ ] `users.is_system_user` column exists
- [ ] Localhost user created
- [ ] All existing data preserved

### Services
- [ ] API server running on port 7272
- [ ] Dashboard running on port 7274
- [ ] WebSocket running on port 6001
- [ ] PostgreSQL running on port 5432 (localhost only)
- [ ] All services auto-start on reboot (if configured)

---

## Getting Help

### Migration Support

If you encounter issues during migration:

1. **Check documentation**:
   - This migration guide
   - `docs/KNOWN_ISSUES.md`
   - `docs/guides/FIREWALL_CONFIGURATION.md`

2. **Review logs**:
   ```bash
   tail -f logs/api.log
   tail -f logs/dashboard.log
   ```

3. **Run diagnostics**:
   ```bash
   python scripts/diagnose.py
   ```

4. **Open GitHub issue**:
   - [github.com/patrik-giljoai/GiljoAI_MCP/issues](https://github.com/patrik-giljoai/GiljoAI_MCP/issues)
   - Include: GiljoAI version, OS, error logs, steps taken

### Community Resources

- **GitHub Discussions**: Community Q&A
- **Documentation**: Full docs at `docs/README_FIRST.md`
- **Issue Tracker**: Bug reports and feature requests

---

## Post-Migration Recommendations

After successful migration:

1. **Update documentation**: Document any custom configurations
2. **Test thoroughly**: Run full test suite in production environment
3. **Monitor logs**: Watch for errors or warnings in first 24 hours
4. **Update team**: Inform team members of changes (especially firewall)
5. **Review firewall rules**: Audit firewall configuration quarterly
6. **Plan for v3.0.1**: Track `docs/KNOWN_ISSUES.md` for upcoming fixes

---

## Version Comparison

### v2.x Architecture
```
User Request
    ↓
Mode Check (LOCAL/LAN/WAN)
    ↓
Conditional Binding (127.0.0.1 or 0.0.0.0)
    ↓
Conditional Authentication (on/off)
    ↓
Application Logic
```

### v3.0 Architecture
```
User Request
    ↓
Network Binding (always 0.0.0.0)
    ↓
OS Firewall Check
    ↓
Auto-Login Middleware (localhost detection)
    ↓
Authentication Layer (always active)
    ↓
Application Logic
```

---

## Summary

### Key Takeaways

1. **Mode concept removed**: No more LOCAL/LAN/WAN modes
2. **Always bind to 0.0.0.0**: Network interface binding simplified
3. **Firewall controls access**: OS firewall replaces mode-based binding
4. **Auto-login for localhost**: Seamless localhost developer experience
5. **Authentication always on**: Network clients require credentials
6. **Configuration simplified**: Fewer mode-specific settings

### Migration Effort

- **Time**: 30-60 minutes
- **Risk**: Low (rollback available)
- **Complexity**: Medium (configuration changes + firewall setup)
- **Downtime**: 30-60 minutes

### Benefits of v3.0

- **Better security**: Defense in depth (firewall + auth)
- **Simpler code**: No mode-switching logic
- **Consistent behavior**: Same code path for all deployments
- **Easier maintenance**: Single architecture to support
- **New features**: MCP integration system (Phase 2)

---

## Related Documentation

- **Firewall Configuration**: `docs/guides/FIREWALL_CONFIGURATION.md`
- **Production Deployment**: `docs/deployment/PRODUCTION_DEPLOYMENT_V3.md`
- **Known Issues**: `docs/KNOWN_ISSUES.md`
- **Release Notes**: `docs/RELEASE_NOTES_V3.0.0.md`
- **Changelog**: `CHANGELOG.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-10-09
**Maintained By**: Documentation Manager Agent
**Next Review**: v3.1.0 release
