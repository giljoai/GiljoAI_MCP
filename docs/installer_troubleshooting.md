# GiljoAI MCP Installer - Troubleshooting Guide

## Common Installation Issues

### Bootstrap Issues

#### Python Version Problems

**Error**: "Python 3.8+ required (found 3.7)"

```bash
# Solution: Install newer Python version
# Windows: Download from python.org
# Mac: brew install python@3.11
# Linux: sudo apt install python3.11
```

#### GUI Detection Failures

**Error**: "GUI test failed: no display"

```bash
# Linux solution: Install GUI libraries
sudo apt install python3-tk

# SSH session solution: Force CLI mode
python bootstrap.py --cli
```

#### Import Errors

**Error**: "ImportError: No module named 'installer'"

```bash
# Solution: Ensure proper Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python bootstrap.py
```

### Profile System Issues

#### Profile Creation Fails

**Error**: "Failed to create profile: validation error"

**Diagnosis**:

```python
# Check profile validation
from installer.core.profile import ProfileManager, ProfileType

profile_mgr = ProfileManager()
try:
    profile = profile_mgr.create_profile("test", ProfileType.DEVELOPER)
    print("Profile creation: OK")
except Exception as e:
    print(f"Profile error: {e}")
```

**Solutions**:

- Verify profile type is valid
- Check profile configuration syntax
- Ensure required fields are provided

#### Profile Dependencies Missing

**Error**: "Profile dependencies not satisfied"

**Check dependencies**:

```bash
# Run dependency check for specific profile
python -c "
from installer.core.profile import ProfileManager, ProfileType
pm = ProfileManager()
profile = pm.get_profile_template(ProfileType.TEAM)
print('Dependencies:', profile.dependencies)
"
```

### PostgreSQL Installation Issues

#### PostgreSQL Not Found

**Error**: "PostgreSQL not found on system"

**Diagnosis**:

```python
from installer.dependencies.postgresql import PostgreSQLInstaller

pg = PostgreSQLInstaller()
print(f"PostgreSQL installed: {pg.is_installed()}")
print(f"Installation paths checked: {pg.get_installation_paths()}")
```

**Solutions**:

1. **Windows**: Install PostgreSQL from official installer
2. **Mac**: `brew install postgresql@15`
3. **Linux**: `sudo apt install postgresql postgresql-contrib`

#### PostgreSQL Service Issues

**Error**: "Cannot connect to PostgreSQL server"

**Check service status**:

```bash
# Windows
sc query postgresql-x64-15

# Mac
brew services list | grep postgresql

# Linux
systemctl status postgresql
```

**Solutions**:

```bash
# Start PostgreSQL service
# Windows
net start postgresql-x64-15

# Mac
brew services start postgresql@15

# Linux
sudo systemctl start postgresql
```

#### Connection Authentication

**Error**: "password authentication failed for user"

**Fix authentication**:

```bash
# Reset PostgreSQL password (Linux/Mac)
sudo -u postgres psql
ALTER USER postgres PASSWORD 'newpassword';

# Windows: Use pgAdmin or SQL Shell
```

### Redis Installation Issues

#### Redis Installation Fails (Windows)

**Error**: "Redis installation failed: download error"

**Manual installation**:

1. Download Redis from official GitHub releases
2. Extract to `C:\Redis`
3. Run `redis-server.exe` to test
4. Install as Windows service

**Alternative solution**:

```bash
# Use Windows Subsystem for Linux
wsl --install
wsl
sudo apt install redis-server
```

#### Redis Service Won't Start

**Error**: "Redis service failed to start"

**Check configuration**:

```bash
# Check Redis config
redis-cli config get "*"

# Test Redis connection
redis-cli ping
```

**Common fixes**:

1. Check port 6379 is available
2. Verify Redis configuration file
3. Check file permissions
4. Look at Redis logs

#### Redis Memory Issues

**Error**: "Can't save in background: fork: Cannot allocate memory"

**Solutions**:

```bash
# Increase virtual memory (Linux)
echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl vm.overcommit_memory=1

# Reduce Redis memory usage
redis-cli config set maxmemory 128mb
redis-cli config set maxmemory-policy allkeys-lru
```

### Docker Installation Issues

#### Docker Desktop Installation

**Error**: "Docker Desktop installation failed"

**Windows solutions**:

1. Enable Hyper-V: `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All`
2. Enable WSL 2: `wsl --install`
3. Download Docker Desktop from official site
4. Run as administrator

**Mac solutions**:

1. Check system requirements (macOS 10.15+)
2. Download Docker Desktop for Mac
3. Install and start Docker Desktop

#### Docker Daemon Not Running

**Error**: "Cannot connect to the Docker daemon"

**Diagnosis**:

```bash
# Check Docker daemon status
docker info
docker version

# Check Docker service
# Linux
systemctl status docker

# Windows/Mac - ensure Docker Desktop is running
```

**Solutions**:

```bash
# Start Docker service (Linux)
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

#### Docker Permission Issues

**Error**: "permission denied while trying to connect to the Docker daemon socket"

**Solution (Linux)**:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Or run with sudo
sudo docker info
```

### Service Manager Issues

#### Service Installation Fails

**Error**: "Service installation failed: insufficient permissions"

**Solutions**:

- Run installer as administrator (Windows)
- Use `sudo` for service installation (Linux/Mac)
- Check service name conflicts

#### Service Won't Start

**Error**: "Service failed to start"

**Diagnosis**:

```python
from installer.services.service_manager import ServiceManager

sm = ServiceManager()
status = sm.get_service_status("giljo-mcp")
print(f"Service status: {status}")

# Check service logs
logs = sm.get_service_logs("giljo-mcp")
print("Service logs:", logs)
```

**Common causes**:

1. Incorrect executable path
2. Missing dependencies
3. Port conflicts
4. Configuration errors

#### Service Auto-Start Issues

**Error**: "Service doesn't start on boot"

**Windows solution**:

```bash
# Set service to automatic startup
sc config "GiljoAI MCP" start= auto
```

**Linux solution**:

```bash
# Enable systemd service
sudo systemctl enable giljo-mcp
```

### Configuration Manager Issues

#### Config Generation Fails

**Error**: "Configuration generation failed"

**Debug configuration**:

```python
from installer.config.config_manager import ConfigurationManager

cm = ConfigurationManager()
try:
    result = cm.generate_config(
        profile_type='developer',
        user_inputs={'host': 'localhost', 'port': 8000},
        output_dir='.'
    )
    print(f"Config generation: {result}")
except Exception as e:
    print(f"Config error: {e}")
    import traceback
    traceback.print_exc()
```

#### Template Missing

**Error**: "Configuration template not found"

**Check templates**:

```bash
# List available templates
ls -la installer/config/templates/
```

**Solution**: Ensure all template files are present:

- `.env.developer`
- `.env.team`
- `.env.enterprise`
- `.env.research`
- `config.yaml.template`

#### Environment Variables Not Set

**Error**: "Environment variable GILJO_MCP_DB not set"

**Set variables manually**:

```bash
# Windows
set GILJO_MCP_DB=data\giljo.db
set GILJO_MCP_HOST=localhost

# Linux/Mac
export GILJO_MCP_DB=data/giljo.db
export GILJO_MCP_HOST=localhost
```

### Health Check Issues

#### Health Check Failures

**Error**: "Health check failed for component X"

**Run individual health checks**:

```python
from installer.core.health import HealthChecker

health = HealthChecker()

# Test specific components
results = {
    'database': health.check_database_connection(),
    'redis': health.check_redis_connection(),
    'docker': health.check_docker_daemon(),
    'services': health.check_services_status()
}

for component, status in results.items():
    print(f"{component}: {'✓' if status else '✗'}")
```

#### Network Health Issues

**Error**: "Network connectivity check failed"

**Diagnose network issues**:

```bash
# Check port availability
netstat -an | grep :8000
netstat -an | grep :5432
netstat -an | grep :6379

# Test connectivity
telnet localhost 8000
curl -v http://localhost:8000/health
```

### GUI Installer Issues

#### GUI Won't Start

**Error**: "GUI installer failed to launch"

**Solutions**:

1. Check tkinter installation: `python -c "import tkinter"`
2. Install GUI libraries (Linux): `sudo apt install python3-tk`
3. Use CLI mode: `python setup.py --cli`

#### GUI Hangs During Installation

**Issue**: GUI becomes unresponsive

**Solutions**:

1. Check process in Task Manager/Activity Monitor
2. Look for error dialogs behind main window
3. Check log files for stuck operations
4. Kill process and retry with CLI

### Performance Issues

#### Slow Installation

**Issue**: Installation takes very long

**Diagnosis**:

- Check network connectivity for downloads
- Monitor disk I/O during installation
- Check if antivirus is scanning installer

**Solutions**:

- Use faster network connection
- Temporarily disable real-time antivirus
- Use local package mirrors
- Install dependencies manually first

#### High Memory Usage

**Issue**: Installer uses too much memory

**Solutions**:

- Close other applications
- Use CLI installer instead of GUI
- Install components individually
- Increase system virtual memory

### Platform-Specific Issues

#### Windows-Specific

**WSL Issues**:

```bash
# Enable WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Install WSL 2
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

**PowerShell Execution Policy**:

```powershell
# Allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### macOS-Specific

**Homebrew Issues**:

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Fix permissions
sudo chown -R $(whoami) /usr/local/share/zsh
```

**Xcode Command Line Tools**:

```bash
xcode-select --install
```

#### Linux-Specific

**Package Manager Issues**:

```bash
# Update package lists
sudo apt update

# Fix broken packages
sudo apt --fix-broken install

# Alternative package managers
# CentOS/RHEL: yum or dnf
# Arch: pacman
```

**Systemd Issues**:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Check systemd status
systemctl status
```

## Debugging Tools

### Log Analysis

#### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
```

#### Log Locations

- **Windows**: `%APPDATA%\GiljoAI\logs\`
- **Mac**: `~/Library/Logs/GiljoAI/`
- **Linux**: `~/.local/share/giljo-ai/logs/`

### System Information Collection

```python
# Collect system info for debugging
import platform
import sys
from pathlib import Path

def collect_debug_info():
    info = {
        'platform': platform.platform(),
        'python_version': sys.version,
        'python_executable': sys.executable,
        'current_directory': str(Path.cwd()),
        'environment': dict(os.environ)
    }

    # Check installer components
    try:
        from installer.core.profile import ProfileManager
        info['profile_system'] = 'OK'
    except Exception as e:
        info['profile_system'] = f'ERROR: {e}'

    return info

debug_info = collect_debug_info()
import json
print(json.dumps(debug_info, indent=2))
```

### Network Debugging

```bash
# Test network connectivity
ping google.com
nslookup postgresql.org
curl -I https://download.redis.io/

# Check local services
curl -v http://localhost:8000
nc -zv localhost 5432
nc -zv localhost 6379
```

### Process Monitoring

```bash
# Monitor installation processes
# Windows
tasklist | findstr python
wmic process where "name='python.exe'" get ProcessId,CommandLine

# Linux/Mac
ps aux | grep python
lsof -i :8000
```

## Recovery Procedures

### Rollback Installation

```python
# Manual rollback
from installer.core.health import HealthChecker

def rollback_installation():
    """Rollback failed installation"""
    print("Starting rollback...")

    # Stop services
    try:
        from installer.services.service_manager import ServiceManager
        sm = ServiceManager()
        sm.stop_service("giljo-mcp")
    except:
        pass

    # Remove configuration
    import os
    config_files = ['config.yaml', '.env']
    for file in config_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Removed {file}")

    print("Rollback complete")
```

### Clean Reinstallation

```bash
# Complete clean installation
python bootstrap.py --clean --reinstall

# Or manual cleanup
rm -rf data/ logs/ config.yaml .env
python bootstrap.py
```

### Reset to Factory State

```python
def factory_reset():
    """Reset installation to factory state"""
    import shutil
    from pathlib import Path

    # Remove all generated files
    paths_to_remove = [
        'data/',
        'logs/',
        'config.yaml',
        '.env',
        'venv/'
    ]

    for path in paths_to_remove:
        if Path(path).exists():
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                Path(path).unlink()

    print("Factory reset complete")
```

## Getting Help

### Information to Collect

When reporting issues, include:

1. **System Information**:

   - Operating system and version
   - Python version
   - Architecture (x64, ARM, etc.)

2. **Installation Details**:

   - Installation method (GUI/CLI)
   - Selected profile
   - Installation logs

3. **Error Information**:

   - Complete error message
   - Stack trace
   - Steps to reproduce

4. **Environment**:
   - Existing software (PostgreSQL, Redis, Docker)
   - Network configuration
   - Firewall settings

### Support Channels

- **GitHub Issues**: https://github.com/yourusername/giljo-mcp/issues
- **Discord Community**: https://discord.gg/giljo-mcp
- **Documentation**: https://docs.giljo-mcp.com

### Emergency Contacts

For critical production issues:

- Email: support@giljo-mcp.com
- Emergency hotline: Available to enterprise customers

## Prevention Tips

### Pre-Installation Checklist

- [ ] Verify system requirements
- [ ] Check available disk space (minimum 2GB)
- [ ] Ensure stable internet connection
- [ ] Run as administrator/sudo when required
- [ ] Close unnecessary applications
- [ ] Backup existing configurations

### Best Practices

1. **Regular Updates**: Keep installer components updated
2. **Backup Configurations**: Backup configs before major changes
3. **Monitor Health**: Regular health check monitoring
4. **Log Rotation**: Configure log rotation to prevent disk issues
5. **Resource Monitoring**: Monitor system resources during operation

### Maintenance Schedule

- **Weekly**: Health check review
- **Monthly**: Update components and dependencies
- **Quarterly**: Review and backup configurations
- **Annually**: Full system review and optimization
