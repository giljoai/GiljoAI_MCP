# GiljoAI MCP Installer - User Guide

## Overview

The GiljoAI MCP installer provides a comprehensive installation system with both GUI and CLI interfaces, supporting multiple deployment profiles and automated component management.

## Quick Start

### 1. Universal Bootstrap

Single entry point for all platforms:

```bash
python bootstrap.py
```

The bootstrap will:

- Detect your OS and GUI capability
- Launch the appropriate installer (GUI or CLI)
- Check and install dependencies
- Configure services and create launchers

### 2. Installation Modes

#### GUI Installation (Recommended)

- Full interactive wizard
- Profile-based configuration
- Visual progress tracking
- Service management controls

#### CLI Installation

- Command-line interface
- Automated deployment options
- Server/headless-friendly

## Profiles

### Developer Profile

- SQLite database (local development)
- Localhost only access
- Minimal resource usage
- Hot reload enabled

### Team Profile

- PostgreSQL database
- LAN access enabled
- Redis caching
- Docker support

### Enterprise Profile

- PostgreSQL with replication
- Full security features
- OAuth integration
- Container deployment

### Research Profile

- High-performance configuration
- Advanced analytics
- Custom tool integrations
- Jupyter notebook support

## Installation Components

### Core Components

- **Profile System**: Project type detection and configuration
- **Configuration Manager**: Automated config file generation
- **Health Checker**: System validation and monitoring
- **Service Manager**: Cross-platform service control

### Database Systems

- **PostgreSQL**: Primary database for multi-user deployments
- **Redis**: Caching and session management
- **SQLite**: Local development database

### Container Support

- **Docker**: Containerized deployment support
- **Docker Desktop**: Windows/Mac installation automation
- **Docker Engine**: Linux installation and configuration

## Using the Installer

### GUI Installation Flow

1. **Profile Selection**

   - Choose your deployment profile
   - Configure basic settings
   - Review component requirements

2. **Dependency Installation**

   - Parallel installation of components
   - Real-time progress monitoring
   - Error handling and rollback

3. **Service Configuration**

   - Automatic service detection
   - Start/stop/restart controls
   - Auto-start configuration

4. **Final Validation**
   - End-to-end health checks
   - Configuration validation
   - Launch script creation

### CLI Installation Options

```bash
# Interactive CLI installation
python setup.py --cli

# Automated installation with profile
python setup.py --profile developer --auto

# Custom configuration
python setup.py --config config.yaml
```

## Configuration Files

The installer generates several configuration files:

### `config.yaml`

Main application configuration based on your profile:

```yaml
profile: developer
database:
  type: sqlite
  path: data/giljo.db
server:
  host: localhost
  port: 8000
```

### `.env`

Environment variables for your deployment:

```bash
GILJO_MCP_DB=data/giljo.db
GILJO_MCP_HOST=localhost
GILJO_MCP_PORT=8000
```

## Service Management

### Automatic Service Detection

The installer detects and configures:

- PostgreSQL (if required by profile)
- Redis (if enabled)
- Docker daemon
- GiljoAI MCP application

### Service Controls

- **Start/Stop/Restart**: Full lifecycle control
- **Auto-start**: Boot-time startup configuration
- **Status Monitoring**: Real-time service health
- **Dependency Ordering**: Automatic startup sequencing

## Troubleshooting

### Common Issues

#### PostgreSQL Installation Fails

1. Check if PostgreSQL is already installed
2. Verify user has admin privileges
3. Check port availability (default: 5432)

#### Redis Connection Issues

1. Verify Redis service is running
2. Check firewall settings
3. Validate Redis configuration

#### Docker Detection Fails

1. Install Docker Desktop (Windows/Mac)
2. Install Docker Engine (Linux)
3. Ensure Docker daemon is running
4. Check user permissions for Docker group

### Health Check Failures

The installer includes comprehensive health checks:

```bash
# Run health check manually
python -m installer.core.health

# Check specific component
python -m installer.dependencies.postgresql --check
python -m installer.dependencies.redis --check
python -m installer.dependencies.docker --check
```

### Log Files

Installation logs are stored in:

- Windows: `%APPDATA%\GiljoAI\logs\installer.log`
- Mac: `~/Library/Logs/GiljoAI/installer.log`
- Linux: `~/.local/share/giljo-ai/logs/installer.log`

## Post-Installation

### Starting GiljoAI MCP

#### Windows

```bash
# Using launcher script
start_giljo.bat

# Or using service
sc start "GiljoAI MCP"
```

#### Mac/Linux

```bash
# Using launcher script
./start_giljo.sh

# Or using systemd (Linux)
systemctl start giljo-mcp
```

### Platform Integration

#### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "src.giljo_mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/giljo/src",
        "GILJO_MCP_DB": "/path/to/data/giljo.db"
      }
    }
  }
}
```

#### VS Code with Continue

Add to Continue config.json:

```json
{
  "customCommands": [
    {
      "name": "giljo-mcp",
      "command": "python -m src.giljo_mcp.server",
      "cwd": "/path/to/giljo"
    }
  ]
}
```

## Updating and Maintenance

### Updating Components

```bash
# Update all components
python bootstrap.py --update

# Update specific component
python -m installer.dependencies.postgresql --update
```

### Backup Configuration

```bash
# Backup current configuration
python -m installer.config.config_manager --backup

# Restore from backup
python -m installer.config.config_manager --restore backup.tar.gz
```

### Uninstallation

```bash
# Remove services and configuration
python bootstrap.py --uninstall

# Complete removal including data
python bootstrap.py --uninstall --purge
```

## Support

For issues and questions:

- GitHub Issues: https://github.com/yourusername/giljo-mcp/issues
- Documentation: https://docs.giljo-mcp.com
- Community: https://discord.gg/giljo-mcp

## Advanced Configuration

### Custom Profiles

Create your own profile by copying an existing template:

```bash
cp installer/config/templates/.env.developer .env.custom
# Edit .env.custom with your settings
python setup.py --env .env.custom
```

### Integration with CI/CD

```bash
# Automated deployment
python bootstrap.py --profile team --auto --config ci-config.yaml
```

### Container Deployment

```bash
# Generate Docker configuration
python -m installer.docker.generate --profile enterprise

# Deploy with Docker Compose
docker-compose up -d
```
