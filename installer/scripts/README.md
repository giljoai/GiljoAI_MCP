# GiljoAI MCP Database Setup Scripts

This directory contains fallback scripts for PostgreSQL database creation when the installer cannot create the database directly (typically due to insufficient privileges).

## Overview

The installer attempts to create the PostgreSQL database automatically. If this fails due to permission issues, it will generate customized versions of these scripts with pre-filled passwords and configuration.

## Scripts

### create_db.ps1 (Windows PowerShell)

**Purpose**: Create the GiljoAI MCP database on Windows systems

**Requirements**:
- PostgreSQL 14-18 installed and running
- PowerShell 5.1 or later
- Administrator privileges
- PostgreSQL admin (postgres) password

**Usage**:
```powershell
# 1. Open PowerShell as Administrator
#    - Press Win+X, select "Windows PowerShell (Admin)"
#    - Or right-click Start, select "Windows Terminal (Admin)"

# 2. Navigate to the installer/scripts directory
cd C:\Projects\GiljoAI_MCP\installer\scripts

# 3. Run the script
.\create_db.ps1
```

**What it does**:
1. Prompts for PostgreSQL admin password
2. Tests connection to PostgreSQL
3. Creates `giljo_owner` role (database owner)
4. Creates `giljo_user` role (application user)
5. Creates `giljo_mcp` database
6. Sets up all required permissions
7. Creates a verification flag for the installer

### create_db.sh (Linux/macOS Bash)

**Purpose**: Create the GiljoAI MCP database on Linux/macOS systems

**Requirements**:
- PostgreSQL 14-18 installed and running
- Bash shell
- PostgreSQL admin (postgres) password
- May require sudo on some Linux distributions

**Usage**:
```bash
# 1. Navigate to the installer/scripts directory
cd /path/to/GiljoAI_MCP/installer/scripts

# 2. Make the script executable (if not already)
chmod +x create_db.sh

# 3. Run the script
bash create_db.sh

# On some Linux systems, you may need sudo
sudo bash create_db.sh
```

**What it does**:
1. Prompts for PostgreSQL admin password
2. Tests connection to PostgreSQL
3. Creates `giljo_owner` role (database owner)
4. Creates `giljo_user` role (application user)
5. Creates `giljo_mcp` database
6. Sets up all required permissions
7. Creates a verification flag for the installer

## Database Schema

### Roles

**giljo_owner**:
- Database owner role
- Used for running migrations
- Has full privileges on the database
- Can create tables, indexes, etc.

**giljo_user**:
- Application runtime role
- Limited privileges (least privilege principle)
- Can read/write data but not modify schema
- Used by the GiljoAI MCP application

### Database

**giljo_mcp**:
- Main application database
- Owned by `giljo_owner`
- Schema managed via Alembic migrations
- Multi-tenant ready (single-tenant enforced in Phase 1)

## Security Considerations

### Password Generation

The installer generates strong random passwords for both roles:
- 20 characters minimum
- Alphanumeric characters only (no special chars to avoid connection string issues)
- Cryptographically secure (uses Python's `secrets` module)

### Credential Storage

Credentials are saved to:
```
installer/credentials/db_credentials_<timestamp>.txt
```

**Important**:
- This file contains sensitive passwords
- File permissions are set to 600 on Unix systems (owner read/write only)
- Keep this file secure and backed up
- Needed for .env file generation

### Permission Model

The scripts implement least privilege:
- `giljo_user` can only read/write data
- `giljo_user` cannot create/drop tables
- `giljo_owner` used only for migrations
- Application runs with `giljo_user` credentials

## Troubleshooting

### PostgreSQL Not Running

**Error**: "Cannot connect to PostgreSQL"

**Solution**:
```bash
# Check PostgreSQL status
# Windows
sc query postgresql-x64-18

# Linux (systemd)
sudo systemctl status postgresql

# macOS (Homebrew)
brew services list
```

### Wrong Password

**Error**: "Password authentication failed"

**Solution**:
- Verify you're using the correct admin password
- On fresh PostgreSQL installs, the postgres user may have no password
- You may need to reset the password using pg_hba.conf trust method

### Port Not Available

**Error**: "Connection refused on port 5432"

**Solution**:
- Verify PostgreSQL is listening on the correct port
- Check postgresql.conf for `port` setting
- Ensure firewall allows connections

### psql Not Found

**Error**: "psql: command not found"

**Solution**:
- Add PostgreSQL bin directory to PATH
- Windows: Usually `C:\Program Files\PostgreSQL\18\bin`
- Linux: Usually `/usr/bin` (installed via package manager)
- macOS: Usually `/usr/local/opt/postgresql@18/bin` (Homebrew)

### Database Already Exists

**Warning**: "Database 'giljo_mcp' already exists"

**Note**: This is not an error. The script is idempotent and will:
- Update role passwords
- Keep existing database
- Re-apply permissions
- Continue successfully

### Permission Denied

**Error**: "Permission denied to create database"

**Solution**:
- Ensure you're running as administrator/sudo
- Verify the postgres user has CREATEDB privilege
- Check that you're connecting with the correct admin user

## Integration with Installer

### Normal Flow (Direct Creation)

1. Installer attempts direct database creation
2. If successful, continues with installation
3. No manual intervention needed

### Fallback Flow (Script Generation)

1. Installer detects permission error
2. Generates customized scripts with:
   - Pre-filled configuration
   - Generated passwords
   - Your connection settings
3. Displays clear instructions
4. Waits for you to run the script
5. Verifies database creation via flag file
6. Continues with installation

### After Script Execution

The script creates a flag file:
```
database_created.flag
```

This signals the installer that the database is ready. The installer will:
1. Verify the database is accessible
2. Load the saved credentials
3. Continue with migrations
4. Generate .env configuration
5. Complete installation

## Files Generated

### Credentials File
```
installer/credentials/db_credentials_<timestamp>.txt
```

Contains:
- Database connection details
- Role names and passwords
- Connection URLs for both roles

### Flag File
```
database_created.flag
```

Simple verification file created by the script to signal completion.

## Manual Database Creation

If you prefer to create the database manually or have an existing setup:

```sql
-- Connect as postgres or admin user
CREATE ROLE giljo_owner LOGIN PASSWORD 'your_owner_password';
CREATE ROLE giljo_user LOGIN PASSWORD 'your_user_password';

CREATE DATABASE giljo_mcp OWNER giljo_owner;

\c giljo_mcp

GRANT CONNECT ON DATABASE giljo_mcp TO giljo_user;
GRANT USAGE, CREATE ON SCHEMA public TO giljo_owner;
GRANT USAGE ON SCHEMA public TO giljo_user;

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO giljo_user;

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO giljo_user;
```

Then provide the credentials to the installer when prompted.

## Version Compatibility

### Supported PostgreSQL Versions

- **Recommended**: PostgreSQL 18
- **Supported**: PostgreSQL 14, 15, 16, 17, 18
- **Minimum**: PostgreSQL 14

### Why PostgreSQL 18?

- Latest stable release
- Best performance
- Security updates
- JSON improvements
- Better concurrent performance

### Older Versions

If you must use an older version:
- PostgreSQL 14-17 are fully supported
- Installer will show a warning for versions < 18
- All features will work correctly
- Consider upgrading for best performance

## Support

For issues with database setup:

1. Check PostgreSQL logs
   - Windows: `C:\Program Files\PostgreSQL\18\data\log\`
   - Linux: `/var/log/postgresql/`
   - macOS: `/usr/local/var/log/` (Homebrew)

2. Verify PostgreSQL version
   ```bash
   psql --version
   ```

3. Test connection manually
   ```bash
   psql -h localhost -p 5432 -U postgres -d postgres
   ```

4. Review installer logs
   ```
   installer/logs/install_<timestamp>.log
   ```

## Migration to Production

These scripts are designed for localhost development. For production:

1. Use dedicated PostgreSQL server
2. Configure pg_hba.conf for network access
3. Enable SSL/TLS connections
4. Set up regular backups
5. Configure connection pooling
6. Monitor performance

See Phase 2 documentation for server deployment.
