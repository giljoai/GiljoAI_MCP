# GiljoAI MCP Installer Troubleshooting Guide (CLI Edition)

## Overview

This guide provides comprehensive troubleshooting steps for the GiljoAI MCP CLI installer, covering common installation and configuration issues.

## Diagnostic Tools

### Health Check Command

```bash
python -m giljo_mcp.health --verbose
```

Checks:
- System compatibility
- PostgreSQL 18 installation
- Python environment
- Dependencies
- Network configuration

### Logging

Logs stored in:
- Windows: `%USERPROFILE%\.giljo-mcp\logs\`
- Mac/Linux: `~/.giljo-mcp/logs/`

Recommended log files:
- `installer.log`: Installation process
- `health.log`: System health checks
- `postgresql.log`: Database-specific issues

## Common Installation Issues

### 1. PostgreSQL Connection Failures

**Symptoms:**
- Unable to connect to database
- "Connection refused" errors
- Authentication failures

**Troubleshooting Steps:**
1. Verify PostgreSQL 18 is running
   ```bash
   pg_isready  # Check PostgreSQL service status
   ```

2. Check PostgreSQL configuration
   ```bash
   python -m giljo_mcp.database --check-config
   ```

3. Verify connection parameters in `config.yaml`
   - Correct host (localhost/127.0.0.1)
   - Correct port (default: 5432)
   - Valid username and password

### 2. Python Environment Problems

**Symptoms:**
- Dependency import errors
- Version incompatibility
- Missing packages

**Troubleshooting Steps:**
1. Check Python version
   ```bash
   python --version  # Should be 3.9+
   ```

2. Verify virtual environment
   ```bash
   python -m venv --help  # Confirm venv is available
   ```

3. Reinstall dependencies
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

### 3. Permission Issues

**Symptoms:**
- "Permission denied" errors
- Unable to write log files
- Database configuration failures

**Troubleshooting Steps:**
1. Check user permissions
   ```bash
   # Windows: Run as Administrator
   # Mac/Linux: Use sudo for system-level operations
   python install.py --elevate
   ```

2. Verify file and directory permissions
   ```bash
   python -m giljo_mcp.health --check-permissions
   ```

### 4. Network and Firewall Problems

**Symptoms:**
- Unable to download dependencies
- Connection timeouts
- Blocked database ports

**Troubleshooting Steps:**
1. Check internet connectivity
   ```bash
   python -m giljo_mcp.network --test
   ```

2. Verify firewall settings
   - Allow Python and PostgreSQL through firewall
   - Open port 5432 for PostgreSQL
   - Allow outbound connections for pip/package managers

### 5. Incomplete or Failed Installation

**Symptoms:**
- Partial installation
- Unexpected errors during setup
- Incomplete configuration

**Recovery Steps:**
1. Clean installation
   ```bash
   python install.py --uninstall
   python install.py --clean
   ```

2. Force reinstallation
   ```bash
   python install.py --force
   ```

3. Manual configuration reset
   ```bash
   python install.py --reset-config
   ```

## Advanced Troubleshooting

### Verbose Installation Mode

```bash
python install.py --verbose
python install.py --debug
```

Provides detailed logs and debugging information.

### Generating Diagnostic Report

```bash
python -m giljo_mcp.health --report
```

Creates comprehensive system diagnostic report.

## Emergency Recovery

If all else fails:
1. Backup your `config.yaml`
2. Complete uninstallation
3. Reinstall from scratch

```bash
python install.py --uninstall
python install.py
```

## Support Resources

- GitHub Issues: https://github.com/GiljoAI/mcp/issues
- Community Forum: https://forum.giljo-mcp.com
- Support Email: support@giljo-mcp.com

## Version and Compatibility

Always include the following information when seeking support:
- OS Version
- Python Version
- PostgreSQL Version
- GiljoAI MCP Version
- Detailed error logs
