# Database Connection Troubleshooting

Quick guide to resolve common PostgreSQL database connection issues.

## Quick Checks

### 1. Is PostgreSQL Running?

**Windows:**
```bash
# Check service status
Get-Service -Name "postgresql*"

# Start if stopped
Start-Service -Name "postgresql-x64-18"
```

**Linux/macOS:**
```bash
# Check status
sudo systemctl status postgresql

# Start if stopped
sudo systemctl start postgresql
```

### 2. Test Connection Manually

**Windows:**
```bash
psql -U postgres -h localhost -p 5432
```

**Linux/macOS:**
```bash
sudo -u postgres psql
```

If this works, the PostgreSQL server is running correctly.

## Common Issues

### "Connection Refused" or "Could not connect"

**Cause:** PostgreSQL service is not running

**Solution:**
1. Check service status (see Quick Checks above)
2. Start the service
3. Verify it's running on port 5432:
   ```bash
   # Windows
   netstat -ano | findstr :5432

   # Linux/macOS
   sudo lsof -i :5432
   ```

### "Password authentication failed"

**Cause:** Incorrect password or credentials

**Solution:**
1. Verify credentials in `.env` file match your PostgreSQL setup
2. Default username: `postgres`
3. Password: Set during PostgreSQL installation

**If you forgot the password:**
- See [detailed password reset guide](POSTGRES_TROUBLESHOOTING.txt#step-5-verify-and-reset-credentials)
- Or re-run the GiljoAI installer with new credentials

### "Database does not exist"

**Cause:** The `giljo_mcp` database hasn't been created

**Solution:**
```bash
# Connect as postgres user
psql -U postgres

# Create database
CREATE DATABASE giljo_mcp OWNER postgres;

# Exit
\q
```

Or simply re-run the installer:
```bash
python installer/cli/install.py
```

### Port 5432 Already in Use

**Cause:** Another application is using PostgreSQL's default port

**Solution:**
1. Find what's using the port:
   ```bash
   # Windows
   netstat -ano | findstr :5432

   # Linux/macOS
   sudo lsof -i :5432
   ```

2. Either:
   - Stop the conflicting application, OR
   - Change PostgreSQL port in `postgresql.conf`
   - Update `DATABASE_PORT` in `.env` file

## Database Settings in GiljoAI

Database configuration is locked and managed by the installer to prevent accidental misconfiguration.

**To change database settings:**

1. Re-run the installer:
   ```bash
   python installer/cli/install.py
   ```

2. **Warning:** Re-running with different database settings will reset the application to factory defaults.

## Configuration Files

**PostgreSQL Settings:**
- Windows: `C:\Program Files\PostgreSQL\18\data\postgresql.conf`
- Linux: `/etc/postgresql/18/main/postgresql.conf`
- macOS: `/usr/local/var/postgresql@18/postgresql.conf`

**GiljoAI Settings:**
- `.env` - Database credentials
- `config.yaml` - Application configuration

## Default Connection Settings

```
Host: localhost
Port: 5432
Database: giljo_mcp
Username: postgres
Password: (set during installation)
```

## Verify PostgreSQL Version

GiljoAI requires PostgreSQL 18.x:

```bash
psql --version
```

Expected output: `psql (PostgreSQL) 18.x`

Other versions are **not supported**.

## Still Having Issues?

For detailed troubleshooting covering:
- Service startup failures
- Permission issues
- Firewall configuration
- Network access (LAN mode)
- Complete reinstallation

See the [complete PostgreSQL troubleshooting guide](POSTGRES_TROUBLESHOOTING.txt)

## Get Help

If the issue persists:

1. Check PostgreSQL logs:
   - Windows: `C:\Program Files\PostgreSQL\18\data\log\`
   - Linux: `/var/log/postgresql/`
   - macOS: `/usr/local/var/log/postgresql@18.log`

2. Check GiljoAI logs:
   - `logs/backend.log`
   - `install_logs/install.log`

3. Open a GitHub issue:
   - Include error messages
   - Include PostgreSQL version
   - Include relevant log snippets
