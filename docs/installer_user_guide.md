# GiljoAI MCP Installer User Guide (CLI Edition)

## Overview

The GiljoAI MCP installer provides a comprehensive CLI-based installation system supporting automated component management for developers and system administrators.

## Quick Start

### 1. Recommended Installation

Single command for all platforms:

```bash
python install.py
```

The CLI installer will:
- Detect your operating system
- Check system requirements
- Install PostgreSQL 18
- Configure localhost database
- Setup GiljoAI MCP services

### 2. Installation Modes

#### CLI Installation

- Command-line interface
- Automated deployment
- Localhost-focused configuration
- Server and development-friendly

## Profiles

### Developer Profile (Default)

- PostgreSQL 18 database
- Localhost access
- Minimal resource usage
- Hot reload enabled
- Local development mode

## Installation Components

### Core Components

- **Profile System**: Automated configuration detection
- **Health Checker**: System validation
- **Service Manager**: Cross-platform service control

### Database System

- **PostgreSQL 18**: Primary database
- Localhost configuration
- Minimal setup requirements

## CLI Installation Options

```bash
# Interactive CLI installation
python install.py

# Specify custom configuration
python install.py --config config.yaml

# Non-interactive mode
python install.py --non-interactive
```

## Configuration Files

### `config.yaml`

Main application configuration:

```yaml
profile: developer
database:
  type: postgresql
  version: 18
  host: localhost
  port: 5432
server:
  host: localhost
  port: 8000
```

## Service Management

### Service Controls

- **Start/Stop/Restart**: Basic lifecycle management
- **Status Monitoring**: Service health checks

## Troubleshooting

### Common Issues

#### PostgreSQL Installation

1. Verify PostgreSQL 18 is installed
2. Check user permissions
3. Confirm port 5432 is available

### Health Checks

```bash
# Run comprehensive health check
python -m giljo_mcp.health

# Check PostgreSQL specifically
python -m giljo_mcp.database --check
```

### Log Files

Installation logs are stored in:

- Windows: `%USERPROFILE%\.giljo-mcp\logs\installer.log`
- Mac/Linux: `~/.giljo-mcp/logs/installer.log`

## Post-Installation

### Starting GiljoAI MCP

```bash
# Start the application
python -m giljo_mcp start

# Check status
python -m giljo_mcp status
```

## Updating and Maintenance

```bash
# Update components
python install.py --update

# Backup configuration
python install.py --backup

# Uninstall
python install.py --uninstall
```

## Support

- GitHub Issues: https://github.com/GiljoAI/mcp/issues
- Documentation: https://docs.giljo-mcp.com

## Advanced Configuration

```bash
# Custom configuration
python install.py --config custom_config.yaml
```
