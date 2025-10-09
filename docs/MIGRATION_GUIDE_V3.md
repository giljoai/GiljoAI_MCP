# GiljoAI MCP v3.0 Migration Guide

**Version:** v3.0.0
**Status:** DRAFT
**Date:** 2025-10-09
**Target Audience:** Users upgrading from v2.x to v3.0

---

## Overview

GiljoAI MCP v3.0 represents a significant architectural simplification, consolidating the three-mode system (LOCAL/LAN/WAN) into a unified single-product architecture with firewall-based access control and automatic localhost authentication.

**Key Changes:**
- Deployment modes removed (LOCAL/LAN/WAN → unified architecture)
- Auto-login for localhost connections
- Firewall-based network access control
- Simplified configuration
- Automatic configuration migration

**Impact:** This is a **non-breaking upgrade** with automatic configuration migration. Your existing v2.x installation will continue to work, with deprecation warnings guiding you to the new approach.

---

## What Changed in v3.0

### 1. Unified Architecture

**Before (v2.x):** Three separate deployment modes
```
LOCAL Mode:  127.0.0.1 binding, no auth
LAN Mode:    0.0.0.0 binding, JWT auth
WAN Mode:    0.0.0.0 binding, JWT auth + TLS
```

**After (v3.0):** Single unified architecture
```
Unified:     0.0.0.0 binding, auto-login for localhost + JWT for network
             Firewall controls external access
```

### 2. Authentication Changes

**Before (v2.x):**
- LOCAL mode: No authentication
- LAN mode: JWT + API keys required
- WAN mode: JWT + API keys + TLS required

**After (v3.0):**
- Localhost (127.0.0.1): Auto-login (zero friction)
- Network access: JWT + API keys required
- TLS: Configured via reverse proxy (recommended for internet)

### 3. Configuration Format

**Before (v2.x config.yaml):**
```yaml
installation:
  mode: local  # or lan, wan

services:
  api:
    host: 127.0.0.1  # Changes based on mode
```

**After (v3.0 config.yaml):**
```yaml
installation:
  version: "3.0.0"
  deployment_context: "localhost"  # Metadata only

services:
  api:
    host: 0.0.0.0  # Always listens on all interfaces
```

### 4. Security Model

**Before (v2.x):**
- Security enforced at application layer
- Mode selection determines authentication
- Network binding varies by mode

**After (v3.0):**
- Security enforced at multiple layers (defense in depth)
- OS firewall blocks external access by default
- Application authenticates network clients
- Auto-login for localhost (trusted environment)

---

## Upgrade Process

### Option 1: Automatic Migration (Recommended)

The v3.0 system automatically migrates v2.x configurations on startup.

**Steps:**
1. **Backup your configuration**
   ```bash
   cp ~/.giljo-mcp/config.yaml ~/.giljo-mcp/config.yaml.backup
   ```

2. **Update to v3.0**
   ```bash
   git pull origin master
   pip install --upgrade giljo-mcp
   ```

3. **Start the server**
   ```bash
   giljo-mcp start
   ```

4. **Review deprecation warnings**
   ```
   WARNING: Config field 'installation.mode: local' is deprecated
            in v3.0 and will be ignored. Network access is now
            controlled by your firewall.
   ```

5. **Configure firewall (if needed)**
   - See [Firewall Configuration](#firewall-configuration) section

**That's it!** Your v2.x config will work with deprecation warnings.

---

### Option 2: Manual Migration (Advanced)

For users who want to clean up their configuration:

**Steps:**
1. **Backup configuration**
   ```bash
   cp ~/.giljo-mcp/config.yaml ~/.giljo-mcp/config.yaml.v2.backup
   ```

2. **Run migration script** (available after Phase 1 Step 8 complete)
   ```bash
   python scripts/migrate_to_v3.py --config ~/.giljo-mcp/config.yaml
   ```

3. **Review migration report**
   ```
   ✅ Migrated config.yaml from v2.x to v3.0
   📝 Changes made:
      - Removed: installation.mode
      - Added: installation.deployment_context
      - Updated: services.api.host = 0.0.0.0
   ⚠️  Action required:
      - Configure firewall to allow/block network access
   ```

4. **Update environment variables** (if any)
   ```bash
   # Remove deprecated env vars from .env
   # GILJO_MCP_MODE=local  # ← Remove this line
   ```

5. **Configure firewall**
   - See [Firewall Configuration](#firewall-configuration) section

---

## Breaking Changes

### Configuration API

**Removed:**
- `DeploymentMode` enum
- `config.installation.mode` field
- `ConfigManager._detect_mode()` method
- `ConfigManager._apply_mode_settings()` method

**Changed:**
- `services.api.host` always set to `0.0.0.0` (was mode-dependent)

**Added:**
- `config.installation.deployment_context` (metadata field)
- `config.installation.version` (v3.0.0)

### Python API

**Removed:**
```python
# v2.x - NO LONGER VALID
from giljo_mcp.config_manager import DeploymentMode

auth = AuthManager(db=session, mode=DeploymentMode.LOCAL)
if auth.is_enabled():
    await auth.authenticate_request(request)
```

**New:**
```python
# v3.0 - CORRECT
auth = AuthManager()  # No mode parameter
await auth.authenticate_request(request)  # Always authenticates
# Auto-login handled by middleware for localhost clients
```

### Environment Variables

**Deprecated:**
- `GILJO_MCP_MODE` - Ignored with warning

**Removed:**
- Mode-specific environment variables

**No Changes:**
- Database connection variables
- API configuration variables
- Feature flags

### Command-Line Interface

**Removed:**
- `giljo-mcp install --mode <mode>` flag

**Changed:**
- `giljo-mcp start` - No longer accepts `--mode` flag

**Added:**
- Firewall configuration commands (in installer)

---

## Firewall Configuration

v3.0 uses OS-level firewall rules to control network access instead of application-level binding.

### Why Firewall-Based?

**Benefits:**
- Defense in depth (OS layer + app layer)
- Standard security practice
- More reliable than binding
- Centralized access control
- Better logging and auditing

### Default Configuration

**After fresh v3.0 install:**
- Firewall blocks external access (localhost only)
- Application binds to 0.0.0.0 (ready for network)
- Localhost clients auto-authenticate
- Network clients see connection refused

### Allow LAN Access

**Windows (PowerShell as Administrator):**
```powershell
# Allow LAN access on ports 7272 (API) and 7274 (frontend)
New-NetFirewallRule -DisplayName "GiljoAI MCP - LAN Access" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 7272,7274 `
  -RemoteAddress LocalSubnet
```

**Linux (Ubuntu/Debian with UFW):**
```bash
# Allow LAN access
sudo ufw allow from 192.168.0.0/16 to any port 7272 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 7274 proto tcp
sudo ufw reload
```

**macOS (Application Firewall):**
```bash
# Allow GiljoAI MCP through firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/python
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /path/to/python
```

### Allow Internet Access (WAN)

**Requirements:**
- Reverse proxy (nginx, caddy, traefik)
- TLS certificate (Let's Encrypt recommended)
- Rate limiting
- DDoS protection

**Not recommended to expose directly to internet.**

See `docs/FIREWALL_CONFIGURATION.md` for detailed instructions.

---

## Localhost Auto-Login

### How It Works

v3.0 introduces automatic authentication for localhost connections:

```
1. Request arrives from 127.0.0.1
2. AutoLoginMiddleware detects localhost IP
3. Middleware authenticates as "localhost" user
4. Request proceeds with full authentication
5. No login screen shown to user
```

### Security

**Is auto-login secure?**
Yes, because:
- IP detection happens at TCP layer (cannot be spoofed)
- Firewall blocks external access
- Network clients still require credentials
- Localhost access implies physical machine access

**Can I disable auto-login?**
Not recommended, but possible:
```yaml
# config.yaml
features:
  auto_login_localhost: false  # Force login even for localhost
```

### User Experience

**Before (v2.x LOCAL mode):**
- No login required
- No user concept
- Limited features

**After (v3.0 localhost):**
- Auto-login as "localhost" user
- Full user features available
- Multi-user ready (add team members)
- API key available for scripts

---

## Migration by Original Mode

### From LOCAL Mode

**v2.x Configuration:**
```yaml
installation:
  mode: local

services:
  api:
    host: 127.0.0.1
```

**Migration:**
1. Configuration auto-migrated on first start
2. Firewall configured to block external access
3. Auto-login enabled for localhost
4. Network binding changed to 0.0.0.0 (firewall controls access)

**User Impact:**
- Zero-click access maintained (auto-login)
- Can now add team members if needed
- Can expose to LAN by updating firewall

**Action Required:**
- None (works automatically)

---

### From LAN Mode

**v2.x Configuration:**
```yaml
installation:
  mode: lan

services:
  api:
    host: 0.0.0.0
```

**Migration:**
1. Configuration auto-migrated on first start
2. Firewall allows LAN access (configured by installer)
3. Auto-login for localhost, JWT for network
4. API keys continue to work

**User Impact:**
- Localhost browser gets auto-login
- Network clients still require login
- Same LAN access as before

**Action Required:**
- Update firewall rules (see [Allow LAN Access](#allow-lan-access))

---

### From WAN Mode

**v2.x Configuration:**
```yaml
installation:
  mode: wan

services:
  api:
    host: 0.0.0.0

security:
  ssl:
    enabled: true
```

**Migration:**
1. Configuration auto-migrated on first start
2. Firewall configured for reverse proxy
3. Auto-login for localhost admin access
4. Network clients require JWT + TLS

**User Impact:**
- Localhost admin gets auto-login
- Internet clients still require login + TLS
- Same security as before

**Action Required:**
- Update firewall for reverse proxy (see [Allow Internet Access](#allow-internet-access-wan))
- Verify TLS configuration

---

## Rollback Instructions

If you encounter issues with v3.0, you can rollback to v2.x:

### Option 1: Git Rollback

```bash
# Checkout the backup branch
git checkout retired_multi_network_architecture

# Reinstall dependencies
pip install -e .

# Restore v2.x config
cp ~/.giljo-mcp/config.yaml.backup ~/.giljo-mcp/config.yaml

# Restart server
giljo-mcp start --mode local  # or lan, wan
```

### Option 2: Version Rollback

```bash
# Install last v2.x release
pip install giljo-mcp==2.9.9

# Restore v2.x config
cp ~/.giljo-mcp/config.yaml.backup ~/.giljo-mcp/config.yaml

# Restart server
giljo-mcp start
```

**Database Compatibility:**
- v3.0 database schema is compatible with v2.x
- No data migration required for rollback
- Localhost user will exist but won't be used in v2.x LOCAL mode

---

## Troubleshooting

### "Config field 'installation.mode' is deprecated"

**Cause:** Using v2.x config format with v3.0

**Solution:**
- This is just a warning, not an error
- Application continues to work
- Run manual migration to clean up config (optional)

---

### "Cannot connect from network machine"

**Cause:** Firewall blocking external access (default in v3.0)

**Solution:**
1. Check firewall rules:
   ```bash
   # Windows
   Get-NetFirewallRule -DisplayName "*GiljoAI*"

   # Linux
   sudo ufw status

   # macOS
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps
   ```

2. Allow LAN access (see [Allow LAN Access](#allow-lan-access))

---

### "Localhost browser shows login screen"

**Cause:** Auto-login not working

**Solution:**
1. Check server logs for auto-login middleware:
   ```bash
   tail -f ~/.giljo-mcp/logs/server.log | grep "auto-login"
   ```

2. Verify browser is accessing via localhost:
   ```
   http://127.0.0.1:7274  ✅ (auto-login works)
   http://192.168.1.100:7274  ❌ (requires login)
   ```

3. Check config.yaml:
   ```yaml
   features:
     auto_login_localhost: true  # Should be true
   ```

---

### "API returns 401 Unauthorized"

**Cause:** Network client requires authentication

**Solution:**
1. Generate API key:
   ```bash
   giljo-mcp user create-api-key
   ```

2. Use API key in requests:
   ```bash
   curl -H "Authorization: Bearer gk_xxx" http://server:7272/api/projects
   ```

---

### "Migration script fails"

**Cause:** Corrupted config or filesystem issue

**Solution:**
1. Restore backup:
   ```bash
   cp ~/.giljo-mcp/config.yaml.backup ~/.giljo-mcp/config.yaml
   ```

2. Start server (auto-migration will run):
   ```bash
   giljo-mcp start
   ```

3. If still failing, check logs:
   ```bash
   tail -f ~/.giljo-mcp/logs/migration.log
   ```

---

## Feature Comparison

| Feature | v2.x LOCAL | v2.x LAN/WAN | v3.0 Localhost | v3.0 Network |
|---------|-----------|--------------|----------------|--------------|
| Authentication | None | Required | Auto-login | Required |
| User Management | No | Yes | Yes | Yes |
| Multi-tenant | No | Yes | Yes | Yes |
| API Keys | No | Yes | Yes | Yes |
| Network Binding | 127.0.0.1 | 0.0.0.0 | 0.0.0.0 (firewall) | 0.0.0.0 (firewall) |
| Firewall | N/A | Optional | Required | Required |
| TLS | No | Optional | Optional | Recommended |
| Zero-click Access | Yes | No | Yes (localhost) | No |

---

## Post-Migration Checklist

After upgrading to v3.0, verify:

- [ ] Server starts without errors
- [ ] Localhost browser auto-authenticates
- [ ] Network access works (if needed)
- [ ] Firewall rules configured
- [ ] API keys work for scripts
- [ ] Database migrations applied
- [ ] Deprecation warnings reviewed
- [ ] Documentation updated (if custom)

---

## Getting Help

**Documentation:**
- Full plan: `docs/SINGLEPRODUCT_RECALIBRATION.md`
- Architecture: `docs/TECHNICAL_ARCHITECTURE.md`
- Firewall config: `docs/FIREWALL_CONFIGURATION.md`

**Community:**
- GitHub Issues: https://github.com/giljoai/mcp-orchestrator/issues
- Discord: https://discord.gg/giljoai (if available)

**Support:**
- Email: support@giljo.ai (if available)
- Documentation: https://docs.giljo.ai (if available)

---

## FAQ

### Will my existing projects work?

**Yes.** Database schema is fully compatible. Projects, agents, and tasks continue to work without changes.

---

### Do I need to reconfigure my MCP clients?

**No.** MCP client configurations remain the same. API endpoints unchanged.

---

### Can I still use LOCAL mode?

**Technically yes** (via `deployment_context` metadata), but it's now a misnomer. v3.0 doesn't have modes - it has a unified architecture with firewall-based access control. Localhost access gets auto-login, network access requires authentication.

---

### What if I don't want to use the firewall?

The firewall is **strongly recommended** for security. However, if you must:
1. Leave firewall open (not recommended)
2. Application will authenticate all non-localhost clients
3. Security relies solely on application layer (less secure)

---

### How do I add team members now?

Same as before:
```bash
# Create user via CLI
giljo-mcp user create --username alice --email alice@example.com

# Or via web UI (if localhost or authenticated)
http://localhost:7274/settings/users
```

Team members access via network (firewall must allow their IPs).

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| v3.0.0 | 2025-10-09 | In Development | Unified architecture |
| v2.9.x | 2025-10-01 | Stable | Last v2.x release |
| v2.0.0 | 2025-09-01 | Legacy | Multi-mode architecture |

---

**Migration Guide Version:** v3.0.0-draft
**Last Updated:** 2025-10-09
**Next Update:** After Phase 1 completion
