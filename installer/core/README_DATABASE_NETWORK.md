# Database Network Configuration Module

## Quick Reference

**Module:** `installer.core.database_network`
**Purpose:** Enable PostgreSQL remote access for GiljoAI MCP server mode
**Status:** Production Ready
**Phase:** Phase 2 - Server Mode

## Files Delivered

| File | Lines | Purpose |
|------|-------|---------|
| `database_network.py` | 821 | Core network configuration module |
| `restore_pg_config.ps1` | 219 | Windows restoration script |
| `restore_pg_config.sh` | 270 | Linux/macOS restoration script |
| `test_database_network.py` | 322 | Unit tests |
| `database_network_usage.py` | 420 | Usage examples |
| `DATABASE_NETWORK_IMPLEMENTATION.md` | 500 | Implementation guide |

**Total:** 2,552 lines of code and documentation

## Quick Start

### Server Mode Setup

```python
from installer.core import DatabaseInstaller, DatabaseNetworkConfig

settings = {
    'pg_host': 'localhost',
    'pg_port': 5432,
    'pg_user': 'postgres',
    'pg_password': 'admin_password',
    'mode': 'server',
    'bind': '0.0.0.0',
    'ssl_enabled': True,
    'batch': False
}

# Phase 1: Create database
db = DatabaseInstaller(settings)
db.setup()

# Phase 2: Enable remote access
net = DatabaseNetworkConfig(settings)
net.setup_remote_access()
```

### Restore Original Config

**Windows:**
```powershell
.\installer\scripts\restore_pg_config.ps1
```

**Linux/macOS:**
```bash
sudo bash installer/scripts/restore_pg_config.sh
```

## What It Does

### PostgreSQL Configuration Changes

1. **postgresql.conf**
   - Changes `listen_addresses` from 'localhost' to '*' (or specific IP)
   - Optimizes connection settings for network use
   - Tunes memory settings (shared_buffers, effective_cache_size)

2. **pg_hba.conf**
   - Adds network access rules for private networks
   - Configures strong authentication (scram-sha-256)
   - Optional SSL enforcement
   - Restricts access to giljo_mcp database only

### Backup System

- Automatically backs up original configurations before changes
- Creates timestamped backup directories
- Generates restoration scripts with embedded paths
- Creates pre-restoration safety backups

### Security Features

- Explicit user consent required for network exposure
- Default to private network ranges only (RFC 1918)
- Optional SSL/TLS enforcement
- Strong authentication (scram-sha-256)
- Clear warnings about security implications

## Configuration Options

### Required Settings

```python
settings = {
    'pg_host': 'localhost',     # PostgreSQL host
    'pg_port': 5432,            # PostgreSQL port
    'pg_user': 'postgres',      # Admin user
    'pg_password': 'password',  # Admin password
    'mode': 'server'            # Must be 'server' for network access
}
```

### Optional Settings

```python
settings = {
    'bind': '0.0.0.0',          # Bind address (default: '0.0.0.0')
    'ssl_enabled': True,        # Require SSL (default: False)
    'allowed_networks': [       # Network ranges (default: private networks)
        '192.168.0.0/16',
        '10.0.0.0/8',
        '172.16.0.0/12'
    ],
    'batch': False              # Interactive mode (default: False)
}
```

## Network Access Rules

### Default Allowed Networks (Private Networks Only)

- `192.168.0.0/16` - Private class B network
- `10.0.0.0/8` - Private class A network
- `172.16.0.0/12` - Private class B network range

### Custom Network Ranges

Restrict to specific subnet:
```python
settings['allowed_networks'] = ['192.168.1.0/24']
```

Allow specific remote network:
```python
settings['allowed_networks'] = [
    '192.168.1.0/24',    # Local subnet
    '10.20.30.0/24'      # Specific remote subnet
]
```

## Security Best Practices

### Recommended for Production

1. **Enable SSL/TLS**
   ```python
   settings['ssl_enabled'] = True
   ```

2. **Restrict Network Access**
   ```python
   settings['allowed_networks'] = ['192.168.1.0/24']
   ```

3. **Use Specific Bind Address**
   ```python
   settings['bind'] = '192.168.1.10'  # Specific interface
   ```

4. **Configure Firewall**
   - Only allow port 5432 from trusted networks
   - Use firewall helper from Phase 2
   - Monitor connection logs

### Security Warnings

The module warns users about:
- Network exposure implications
- SSL status (warns if disabled)
- Allowed network ranges
- Firewall configuration requirements
- Strong password importance

## Testing Remote Connection

### From Remote Client

**Using psql:**
```bash
psql -h YOUR_SERVER_IP -U giljo_user -d giljo_mcp
```

**Using Python:**
```python
import psycopg2

conn = psycopg2.connect(
    host='YOUR_SERVER_IP',
    port=5432,
    database='giljo_mcp',
    user='giljo_user',
    password='YOUR_PASSWORD'
)
print('Connected successfully!')
conn.close()
```

**With SSL:**
```python
conn = psycopg2.connect(
    host='YOUR_SERVER_IP',
    port=5432,
    database='giljo_mcp',
    user='giljo_user',
    password='YOUR_PASSWORD',
    sslmode='require'
)
```

## Troubleshooting

### Remote Connection Fails

1. **Verify PostgreSQL restarted**
   ```bash
   # Linux
   sudo systemctl status postgresql

   # Windows
   # Check Services (services.msc)
   ```

2. **Check Firewall**
   - Ensure port 5432 is open
   - Verify client IP is allowed
   - Check both host and client firewalls

3. **Verify Configuration**
   - Check postgresql.conf for listen_addresses
   - Review pg_hba.conf for network rules
   - Ensure client IP is in allowed ranges

4. **Review Logs**
   ```bash
   # Linux
   sudo tail -f /var/log/postgresql/postgresql-*.log

   # Windows
   # Check: C:\Program Files\PostgreSQL\{version}\data\log
   ```

### Cannot Find Config Directory

Manual configuration guide provided by module:
1. Locate postgresql.conf and pg_hba.conf
2. Edit listen_addresses in postgresql.conf
3. Add network rules to pg_hba.conf
4. Restart PostgreSQL

Common locations:
- Windows: `C:\Program Files\PostgreSQL\{version}\data`
- Linux: `/etc/postgresql/{version}/main`
- macOS: `/usr/local/var/postgres`

### Restoration Needed

If something goes wrong, use restoration scripts:

**Windows:**
```powershell
cd installer\scripts
.\restore_pg_config.ps1
```

**Linux/macOS:**
```bash
cd installer/scripts
sudo bash restore_pg_config.sh
```

## Integration with Other Modules

### Phase 1 Integration

Works seamlessly with Phase 1 DatabaseInstaller:
```python
# Phase 1: Local database creation
from installer.core import DatabaseInstaller
db = DatabaseInstaller(settings)
db_result = db.setup()

# Phase 2: Network access (server mode only)
from installer.core import DatabaseNetworkConfig
if settings['mode'] == 'server':
    net = DatabaseNetworkConfig(settings)
    net_result = net.setup_remote_access()
```

### Phase 2 Coordination

Coordinates with other Phase 2 modules:

- **Network Module:** Bind address coordination
- **Firewall Module:** PostgreSQL port (5432) rules
- **Security Module:** SSL certificate paths
- **ServerInstaller:** Orchestration of all Phase 2 setup

## API Reference

### DatabaseNetworkConfig Class

#### Constructor
```python
DatabaseNetworkConfig(settings: Dict[str, Any])
```

**Parameters:**
- `settings`: Configuration dictionary with pg_host, pg_port, mode, bind, etc.

#### Main Methods

**setup_remote_access()**
```python
def setup_remote_access() -> Dict[str, Any]
```
Main workflow for enabling remote database access.

**Returns:**
- `success`: bool - Overall success status
- `errors`: list - Error messages if any
- `warnings`: list - Warning messages
- `backups`: list - Backup file information
- `backup_dir`: str - Backup directory path
- `restore_scripts`: list - Generated restoration script paths
- `restart_required`: bool - Whether PostgreSQL restart needed
- `restart_completed`: bool - Whether restart was successful

**find_pg_config_dir()**
```python
def find_pg_config_dir() -> Dict[str, Any]
```
Locate PostgreSQL configuration directory.

**backup_configs()**
```python
def backup_configs() -> Dict[str, Any]
```
Backup PostgreSQL configuration files.

**configure_postgresql_conf()**
```python
def configure_postgresql_conf() -> Dict[str, Any]
```
Modify postgresql.conf for network listening.

**configure_pg_hba_conf()**
```python
def configure_pg_hba_conf() -> Dict[str, Any]
```
Modify pg_hba.conf for client authentication.

**restore_configs()**
```python
def restore_configs() -> Dict[str, Any]
```
Restore original configurations from backup.

**generate_restore_scripts()**
```python
def generate_restore_scripts() -> Dict[str, Any]
```
Generate platform-specific restoration scripts.

## Examples

See `examples/database_network_usage.py` for comprehensive examples:

1. Localhost mode (no network config)
2. Server mode - basic network access
3. Server mode - SSL enforced
4. Server mode - restricted network access
5. Configuration restoration
6. Batch mode deployment
7. Testing remote connectivity

## Testing

### Run Unit Tests

```bash
cd tests
python test_database_network.py
```

### Test Coverage

- Module initialization
- Configuration file backup/restore
- postgresql.conf modification
- pg_hba.conf modification
- Restoration script generation
- User consent handling
- Batch mode operation
- Configuration detection
- Error handling

## Documentation

### Complete Documentation

- **Implementation Guide:** `DATABASE_NETWORK_IMPLEMENTATION.md`
- **Delivery Report:** `PHASE2_DATABASE_NETWORK_DELIVERY.md`
- **This README:** `README_DATABASE_NETWORK.md`

### Key Topics Covered

- Architecture and design
- Configuration changes explained
- Backup and restoration system
- Security considerations
- Integration patterns
- Troubleshooting guide
- Performance tuning
- Future enhancements

## Maintenance

### Regular Tasks

1. **Keep Backups**
   - Backup directories are in `installer/backups/postgresql/`
   - Keep multiple generations for safety
   - Test restoration periodically

2. **Review Security**
   - Audit allowed network ranges
   - Review authentication methods
   - Check SSL/TLS configuration
   - Monitor connection logs

3. **Update for New PostgreSQL Versions**
   - Add new version paths to detection logic
   - Verify configuration compatibility
   - Test with new PostgreSQL features

## Support

### Getting Help

1. Review implementation guide: `DATABASE_NETWORK_IMPLEMENTATION.md`
2. Check usage examples: `examples/database_network_usage.py`
3. Review troubleshooting section above
4. Check PostgreSQL logs for specific errors
5. Consult PostgreSQL documentation for network configuration

### Common Issues

- **Connection refused:** Check PostgreSQL is running and restarted
- **Permission denied:** Verify password and pg_hba.conf rules
- **Config not found:** Use manual configuration guide
- **Firewall blocks:** Configure firewall to allow port 5432

## Version Information

- **Module Version:** 1.0.0
- **PostgreSQL Support:** 14, 15, 16, 17, 18
- **Python Requirements:** 3.8+
- **Platforms:** Windows, Linux, macOS

## License

Part of GiljoAI MCP project.

## Contributing

When modifying this module:
1. Maintain security-first approach
2. Preserve backward compatibility
3. Add tests for new functionality
4. Update documentation
5. Test on all supported platforms

---

**For detailed implementation information, see:** `DATABASE_NETWORK_IMPLEMENTATION.md`
**For usage examples, see:** `examples/database_network_usage.py`
**For delivery details, see:** `PHASE2_DATABASE_NETWORK_DELIVERY.md`
