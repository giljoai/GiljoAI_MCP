# GiljoAI MCP CLI Installer

Professional installation system for GiljoAI MCP with zero post-install configuration.

## Architecture

### Core Components

```
installer/
├── cli/
│   └── install.py              # Main CLI entry point (Click framework)
├── core/
│   ├── installer.py            # BaseInstaller, LocalhostInstaller, ServerInstaller
│   ├── database.py             # PostgreSQL setup with fallback scripts
│   ├── config.py               # .env and config.yaml generation
│   └── validator.py            # Pre/Post installation validation
├── scripts/                    # Generated elevation scripts
│   ├── create_db.ps1          # Windows PowerShell
│   └── create_db.sh           # Unix/Linux/macOS bash
├── credentials/               # Database credentials (secure)
│   └── db_credentials_*.txt
└── requirements.txt           # Installer dependencies
```

### Launcher System

```
launchers/
├── start_giljo.py             # Universal Python launcher
├── start_giljo.bat            # Windows wrapper
└── start_giljo.sh             # Unix/Linux/macOS wrapper
```

## Features

### ✓ Zero Post-Install Configuration
- Database created during installation
- All config files generated
- Services start immediately
- No manual steps required

### ✓ Cross-Platform Support
- Windows (PowerShell scripts, .bat launcher)
- Linux (bash scripts, systemd service)
- macOS (Homebrew-aware, bash scripts)

### ✓ Intelligent Database Setup
- PostgreSQL version detection (14-18 supported)
- Direct creation with admin credentials
- Automatic fallback script generation
- Secure password generation
- Idempotent operations (safe to re-run)

### ✓ Professional CLI
- Click framework for robust CLI
- Interactive and batch modes
- Config file support
- Clear error messages
- No emojis (professional output)

### ✓ Comprehensive Validation
- Pre-installation checks (Python, PostgreSQL, ports, disk space)
- Post-installation verification (config files, database, launchers)
- Port availability validation
- Service health checks

## Installation Modes

### Localhost Mode (Default)
```bash
python installer/cli/install.py --mode localhost
```

**Features:**
- Binds to 127.0.0.1 (local only)
- No authentication required
- Auto-opens browser
- Debug logging
- Single worker

**Use Case:** Developer workstation

### Server Mode
```bash
python installer/cli/install.py --mode server
```

**Features:**
- Binds to 0.0.0.0 (network accessible)
- API key authentication
- Optional SSL/TLS
- Firewall rule generation
- Multi-user support
- Production logging

**Use Case:** Team server, remote access

## Usage

### Interactive Installation (Recommended)
```bash
cd C:\Projects\GiljoAI_MCP
pip install -r installer/requirements.txt
python installer/cli/install.py
```

### Batch Installation
```bash
python installer/cli/install.py \
    --mode localhost \
    --batch \
    --pg-password secret123 \
    --api-port 8000 \
    --ws-port 8001 \
    --dashboard-port 3000
```

### Config File Installation
```bash
# Generate template
python installer/cli/install.py --generate-config

# Edit install_config.yaml

# Run installation
python installer/cli/install.py --config install_config.yaml
```

### Launch Services
```bash
# Windows
.\launchers\start_giljo.bat

# Unix/Linux/macOS
./launchers/start_giljo.sh

# Python (universal)
python launchers/start_giljo.py
```

## Database Setup

### Direct Creation (Preferred)
The installer attempts to create the database directly using provided PostgreSQL credentials.

**Requirements:**
- PostgreSQL admin (postgres) password
- Sufficient privileges

**What happens:**
1. Connects to PostgreSQL as admin
2. Creates roles (giljo_owner, giljo_user)
3. Creates database (giljo_mcp)
4. Sets up permissions
5. Saves credentials securely

### Fallback Scripts (When Elevated)
If direct creation fails due to permissions, the installer generates elevation scripts.

**Windows:**
```powershell
# Generated script: installer/scripts/create_db.ps1
# Run as Administrator:
.\installer\scripts\create_db.ps1
```

**Unix/Linux/macOS:**
```bash
# Generated script: installer/scripts/create_db.sh
# Run with appropriate privileges:
bash installer/scripts/create_db.sh
```

**Scripts include:**
- All necessary SQL commands
- Clear instructions
- Error handling
- Verification flags

## Configuration Files

### .env (Environment Variables)
Generated automatically with:
- Database credentials (auto-generated passwords)
- Service ports and binding
- Security keys (auto-generated)
- Feature flags
- Performance settings

**Security:**
- Restrictive permissions (chmod 600 on Unix)
- Never committed to version control
- Passwords are cryptographically secure

### config.yaml (Application Config)
Generated automatically with:
- Installation metadata
- Database settings
- Service configuration
- Feature toggles
- Logging configuration
- Installation status

### Credentials File
Database credentials saved to:
```
installer/credentials/db_credentials_YYYYMMDD_HHMMSS.txt
```

**Contains:**
- Database name and connection details
- Owner role credentials
- User role credentials
- Connection strings (ready to use)

## Launcher Features

### Service Management
- Starts services in correct order
- Waits for each service to be ready
- Monitors service health
- Restarts on failure (optional)
- Graceful shutdown (SIGINT/SIGTERM)

### Health Checks
- Port availability validation
- Service readiness checks
- Database connectivity verification
- Configuration file validation

### Logging
- Separate log file per service
- Launcher activity log
- Structured logging format
- Log rotation support

### Browser Integration
- Auto-opens dashboard (configurable)
- Waits for services to be ready
- Only opens on localhost binding

## CLI Options Reference

### Installation Options
```bash
--mode [localhost|server]     # Installation mode (default: localhost)
--batch                        # Non-interactive batch mode
--pg-host HOST                 # PostgreSQL host (default: localhost)
--pg-port PORT                 # PostgreSQL port (default: 5432)
--pg-password PASSWORD         # PostgreSQL admin password
--config PATH                  # Load configuration from file
--generate-config              # Generate config template and exit
--api-port PORT                # API service port (default: 8000)
--ws-port PORT                 # WebSocket port (default: 8001)
--dashboard-port PORT          # Dashboard port (default: 3000)
--version                      # Show version and exit
--help                         # Show help message
```

### Examples
```bash
# Interactive with custom ports
python installer/cli/install.py --api-port 9000

# Batch mode with all options
python installer/cli/install.py \
    --mode server \
    --batch \
    --pg-host db.example.com \
    --pg-port 5432 \
    --pg-password secret \
    --api-port 8000

# Generate and use config file
python installer/cli/install.py --generate-config
python installer/cli/install.py --config install_config.yaml
```

## Troubleshooting

### PostgreSQL Not Found
The installer checks for PostgreSQL and provides installation instructions:

**Windows:** https://www.postgresql.org/download/windows/
**Linux:** `sudo apt-get install postgresql-18`
**macOS:** `brew install postgresql@18`

### Port Already in Use
The installer validates port availability and shows which ports are in use.

**Solution:** Stop conflicting services or choose different ports.

### Database Creation Failed
If direct creation fails, the installer generates fallback scripts.

**Action Required:**
1. Run the generated script with elevated privileges
2. Return to installer and press Enter

### Services Won't Start
Check the logs for details:
```bash
# Installation logs
cat install_logs/install_*.log

# Service logs
cat logs/api_server_stdout.log
cat logs/websocket_server_stdout.log
cat logs/dashboard_stdout.log

# Launcher logs
cat logs/launcher_*.log
```

## Dependencies

### Required
- Python 3.8+
- PostgreSQL 18 (or 14-18)
- click >= 8.1.0
- pyyaml >= 6.0
- python-dotenv >= 1.0.0
- psycopg2-binary >= 2.9.9

### Optional
- colorama >= 0.4.6 (Windows terminal colors)

Install all dependencies:
```bash
pip install -r installer/requirements.txt
```

## Security

### Passwords
- Auto-generated using `secrets` module
- 20+ character alphanumeric
- Cryptographically secure
- Never logged or displayed

### File Permissions
- .env: chmod 600 (Unix)
- Credentials: chmod 600 (Unix)
- Scripts: chmod 755 (Unix)

### Network Binding
- Localhost mode: 127.0.0.1 only
- Server mode: Explicit 0.0.0.0 with warnings

### API Keys (Server Mode)
- Auto-generated secure tokens
- Stored hashed
- Displayed once during installation

## Performance

### Installation Time
- Localhost: < 5 minutes
- Server: < 10 minutes

### Launch Time
- All services: < 30 seconds
- Includes health checks

### Resource Usage
- Memory: < 500MB
- Disk: ~100MB (without logs)

## Testing

Run tests from project root:
```bash
# Unit tests
python -m pytest installer/tests/

# Integration tests
python -m pytest installer/tests/integration/

# Specific test
python -m pytest installer/tests/test_localhost_install.py -v
```

## Development

### Project Structure
```
installer/
├── cli/                 # CLI interface
├── core/               # Core installation logic
├── scripts/            # Generated scripts
├── credentials/        # Secure credentials
├── tests/             # Test suite
└── requirements.txt   # Dependencies
```

### Adding New Features
1. Update relevant core module
2. Add tests
3. Update documentation
4. Test on all platforms

### Code Standards
- Use pathlib.Path for all file operations
- Type hints for all functions
- Comprehensive error handling
- Logging for all operations
- Platform-specific code clearly marked

## Support

### Log Files
- Installation: `install_logs/install_*.log`
- Services: `logs/*.log`
- Launcher: `logs/launcher_*.log`

### Credentials
- Database: `installer/credentials/db_credentials_*.txt`

### Configuration
- Environment: `.env`
- Application: `config.yaml`
- API Keys: `api_keys.yaml` (server mode)

## License

See LICENSE file in project root.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

---

**Phase 1 Implementation Complete** ✓

For detailed implementation notes, see `PHASE1_IMPLEMENTATION_COMPLETE.md`
