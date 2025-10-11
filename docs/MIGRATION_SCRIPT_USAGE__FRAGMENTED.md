# Migration Script Usage Guide

## Overview

The `migrate_to_v3.py` script automates the migration from GiljoAI MCP v2.x to v3.0. It handles configuration updates, database migrations, and user creation with automatic backups.

## What Gets Migrated

### Configuration Changes
- **Removes**: Deployment mode field (LOCAL/LAN/WAN)
- **Updates**: Network binding to `0.0.0.0` (firewall controls access)
- **Adds**: Version `3.0.0`, feature flags, deployment context
- **Preserves**: All custom settings, ports, database configuration

### Database Changes
- Runs Alembic migrations to latest schema
- Creates `localhost` system user for auto-login
- Preserves all existing data and users

### Backup
- Automatic backup of `config.yaml` → timestamped backup directory
- Backup of `.env` if present
- Backup location: `./backups/YYYYMMDD_HHMMSS/`

## Prerequisites

1. **Python 3.13+** installed
2. **GiljoAI MCP v2.x** installation
3. **PostgreSQL** database accessible
4. **Alembic** installed (from requirements.txt)

## Usage

### Basic Migration

```bash
# Navigate to project root
cd /path/to/GiljoAI_MCP

# Run migration (interactive - asks for confirmation)
python scripts/migrate_to_v3.py
```

### Options

```bash
# Dry run - preview changes without applying
python scripts/migrate_to_v3.py --dry-run

# Specify custom config path
python scripts/migrate_to_v3.py --config /path/to/config.yaml

# Skip confirmation prompt
python scripts/migrate_to_v3.py --yes

# Combine options
python scripts/migrate_to_v3.py --config custom.yaml --dry-run
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to config.yaml (default: `./config.yaml`) |
| `--dry-run` | Preview changes without applying them |
| `--yes` | Skip confirmation prompt (useful for automation) |
| `--help` | Show help message |

## Migration Process

The script follows these steps:

### 1. Detection
```
🔍 Detecting installation version...
   ✓ Detected v2.x installation (version: 2.x)
   ✓ Current mode: local
```

### 2. Backup
```
💾 Creating backup...
   ✓ Config backed up: ./backups/20251009_120000/config.yaml
   ✓ .env backed up: ./backups/20251009_120000/.env

   📁 Backup location: ./backups/20251009_120000
```

### 3. Configuration Migration
```
⚙️  Migrating configuration...
   ✓ Removed mode: local
   ✓ Added version: 3.0.0
   ✓ Updated network binding: 0.0.0.0
   ✓ Enabled features: authentication, auto_login_localhost
```

### 4. Database Migration
```
🗄️  Migrating database...
   Running migrations...
   ✓ Migrations applied
   Creating localhost user...
   ✓ Localhost user: localhost
   ✓ API Key: abcd1234efgh5678...
```

### 5. Completion Report
```
============================================================
  ✅ Migration Complete!
============================================================

📋 Summary:
   • v2.x mode 'local' → v3.0 unified architecture
   • Network binding: 0.0.0.0 (firewall controls access)
   • Authentication: Always enabled
   • Localhost auto-login: Enabled

📁 Backup location:
   ./backups/20251009_120000

🔄 Rollback instructions:
   cp ./backups/20251009_120000/config.yaml ./config.yaml
   git checkout retired_multi_network_architecture
   alembic downgrade -1

📚 Documentation:
   docs/MIGRATION_GUIDE_V3.md
   docs/sessions/phase1_core_architecture_consolidation.md

⚠️  Manual steps (if needed):
   1. Configure OS firewall for localhost-only access
   2. Restart GiljoAI MCP services
   3. Test localhost access: http://127.0.0.1:7272

============================================================
```

## After Migration

### 1. Restart Services

```bash
# If running as service
sudo systemctl restart giljo-mcp

# Or restart manually
python scripts/launch_giljo_mcp.py
```

### 2. Verify Access

```bash
# Test localhost access (auto-login should work)
curl http://127.0.0.1:7272/api/health

# Dashboard should be accessible
# http://127.0.0.1:7274
```

### 3. Configure Firewall (Optional)

For localhost-only access:

**Windows Firewall:**
```powershell
# Block external access to ports
New-NetFirewallRule -DisplayName "GiljoAI - Block External" `
  -Direction Inbound -LocalPort 7272,7274,7273 -Protocol TCP `
  -Action Block -Profile Any
```

**Linux (ufw):**
```bash
# Allow only localhost
sudo ufw deny 7272
sudo ufw deny 7273
sudo ufw deny 7274
```

## Rollback

If you need to rollback to v2.x:

### 1. Restore Configuration
```bash
# Find your backup
ls -la ./backups/

# Restore config
cp ./backups/YYYYMMDD_HHMMSS/config.yaml ./config.yaml
```

### 2. Revert Git Branch
```bash
git checkout retired_multi_network_architecture
```

### 3. Downgrade Database
```bash
alembic downgrade -1
```

### 4. Restart Services
```bash
python scripts/launch_giljo_mcp.py
```

## Troubleshooting

### Migration Fails at Detection

**Problem**: "No v2.x installation detected"

**Solution**:
- Verify config.yaml exists in current directory
- Check if already migrated (version: 3.0.0 in config)
- Use `--config` to specify correct path

### Backup Fails

**Problem**: "Backup failed - aborting"

**Solution**:
- Check disk space
- Verify write permissions on project directory
- Ensure backup directory is not locked

### Config Migration Fails

**Problem**: "Config migration failed"

**Solution**:
- Verify config.yaml is valid YAML
- Check file permissions (read/write)
- Review backup and try manual migration

### Database Migration Fails

**Problem**: "Database migration failed"

**Solution**:
- Verify PostgreSQL is running
- Check database connection in config
- Ensure Alembic is installed: `pip install alembic`
- Run migrations manually: `alembic upgrade head`

### Localhost User Creation Fails

**Problem**: Error creating localhost user

**Solution**:
- Check database connectivity
- Verify migrations completed: `alembic current`
- Create user manually using `scripts/create_admin_user.py`

## Advanced Usage

### Automated Migration (CI/CD)

```bash
# Non-interactive migration
python scripts/migrate_to_v3.py --yes

# With error handling
if python scripts/migrate_to_v3.py --yes; then
    echo "Migration successful"
    systemctl restart giljo-mcp
else
    echo "Migration failed - see logs"
    exit 1
fi
```

### Multiple Installations

```bash
# Migrate specific installation
python scripts/migrate_to_v3.py \
  --config /opt/giljo-instance1/config.yaml \
  --yes

python scripts/migrate_to_v3.py \
  --config /opt/giljo-instance2/config.yaml \
  --yes
```

### Dry Run First (Recommended)

```bash
# Always dry run first to preview changes
python scripts/migrate_to_v3.py --dry-run

# Review output, then run for real
python scripts/migrate_to_v3.py --yes
```

## Best Practices

1. **Always run dry-run first** to preview changes
2. **Backup manually** before migration (in addition to automatic backup)
3. **Stop services** before migration to avoid conflicts
4. **Test localhost access** after migration
5. **Keep backup** for at least a week after migration
6. **Document** any custom configuration changes

## Support

For issues or questions:
- Check migration guide: `docs/MIGRATION_GUIDE_V3.md`
- Review session docs: `docs/sessions/phase1_core_architecture_consolidation.md`
- Check GitHub issues: https://github.com/yourusername/GiljoAI_MCP/issues

## Version Compatibility

| Script Version | Migrates From | Migrates To |
|----------------|---------------|-------------|
| 1.0 | v2.x (LOCAL/LAN/WAN) | v3.0.0 (unified) |

## Change Log

### Version 1.0 (2025-10-09)
- Initial release
- Support for LOCAL/LAN/WAN mode migration
- Automatic backup creation
- Database schema migration
- Localhost user creation
- Dry-run mode
- CLI with confirmation
