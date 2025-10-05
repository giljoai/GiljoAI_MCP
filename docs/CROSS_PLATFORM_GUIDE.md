# Cross-Platform Compatibility Guide

**GiljoAI MCP Multi-Platform Deployment Reference**

Generated: 2025-10-04

---

## Overview

GiljoAI MCP is designed to run seamlessly across Windows, Linux, and macOS. This guide covers platform-specific considerations, installation differences, and deployment best practices.

**Supported Platforms:**
- Windows 10/11, Windows Server 2019/2022  
- Ubuntu 20.04/22.04 LTS, Debian 11/12  
- RHEL 8/9, CentOS Stream, Fedora 38+  
- macOS 12+ (Monterey, Ventura, Sonoma)

---

## Platform-Specific Differences

### File Systems & Paths

| Aspect | Windows | Linux | macOS |
|--------|---------|-------|-------|
| Path Separator | `\` (backslash) | `/` (forward slash) | `/` (forward slash) |
| Case Sensitivity | No | Yes | No (default) |
| Root | Drive letters (C:, D:) | `/` | `/` |
| Max Path | 260 chars | No limit | No limit |
| Line Endings | CRLF | LF | LF |

**GiljoAI MCP Solution:**
- All code uses `pathlib.Path()` for cross-platform compatibility
- `PathResolver` utility (`src/giljo_mcp/utils/path_resolver.py`)
- `.gitattributes` handles line ending conversion

### Environment Variables

**Windows (PowerShell):**
```powershell
$env:GILJO_API_PORT = "7272"
```

**Linux/macOS (Bash):**
```bash
export GILJO_API_PORT=7272
```

**GiljoAI MCP:** Uses `.env` files (cross-platform via python-dotenv)

### Process Management

| Feature | Windows | Linux/macOS |
|---------|---------|-------------|
| Signals | Limited | Full POSIX |
| Service Manager | NSSM/Windows Services | systemd/launchd |
| Kill Command | taskkill | kill |

---

## Installation Requirements

### PostgreSQL 18

**Windows:**
```powershell
# Option 1: EDB Installer
# https://www.postgresql.org/download/windows/

# Option 2: winget
winget install PostgreSQL.PostgreSQL.18
```

**Ubuntu/Debian:**
```bash
# Add repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Install
sudo apt update
sudo apt install postgresql-18 postgresql-client-18
```

**macOS:**
```bash
brew install postgresql@18
brew services start postgresql@18
```

### Python 3.11+

**Windows:**
```powershell
winget install Python.Python.3.13
```

**Ubuntu/Debian:**
```bash
sudo apt install python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install python@3.13
```

### Node.js 18+

**Windows:**
```powershell
winget install OpenJS.NodeJS.LTS
```

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs
```

**macOS:**
```bash
brew install node@18
```

---

## Service Management

### Windows (NSSM - Recommended)

```powershell
# Install NSSM
winget install NSSM.NSSM

# Create service
nssm install GiljoAI_MCP "C:\Python313\python.exe" "C:\path	o\start_giljo.py"
nssm set GiljoAI_MCP AppDirectory "C:\path	o\GiljoAI_MCP"
nssm set GiljoAI_MCP Start SERVICE_AUTO_START

# Manage
nssm start GiljoAI_MCP
nssm stop GiljoAI_MCP
```

### Linux (systemd)

Create `/etc/systemd/system/giljo-mcp.service`:
```ini
[Unit]
Description=GiljoAI MCP Orchestrator
After=network.target postgresql.service

[Service]
Type=simple
User=giljo
WorkingDirectory=/opt/giljo_mcp
ExecStart=/usr/bin/python3 /opt/giljo_mcp/start_giljo.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Manage service:
```bash
sudo systemctl enable giljo-mcp
sudo systemctl start giljo-mcp
sudo systemctl status giljo-mcp
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.giljo.mcp.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.giljo.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/opt/giljo_mcp/start_giljo.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Manage:
```bash
launchctl load ~/Library/LaunchAgents/com.giljo.mcp.plist
launchctl start com.giljo.mcp
```

---

## Firewall Configuration

**Required Ports (Server Mode):**
- 7272: API Server
- 7274: Dashboard
- 5432: PostgreSQL (only if remote access needed)

### Windows

**Automated:**
```powershell
.\installer\scriptsirewall\configure_windows_firewall.ps1
```

**Manual:**
```powershell
New-NetFirewallRule -DisplayName "GiljoAI MCP API" `
    -Direction Inbound -LocalPort 7272 -Protocol TCP -Action Allow
```

### Linux

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 7272/tcp
sudo ufw allow 7274/tcp
sudo ufw enable
```

**firewalld (RHEL/CentOS):**
```bash
sudo firewall-cmd --permanent --add-port=7272/tcp
sudo firewall-cmd --permanent --add-port=7274/tcp
sudo firewall-cmd --reload
```

### macOS

System Preferences → Security & Privacy → Firewall → Add Python

---

## Known Issues & Workarounds

### Windows

**Path Length Limit:**
```powershell
# Enable long paths
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### Linux

**Port Permission (<1024):**
```bash
# Use ports >=1024 (default) or grant capability
sudo setcap CAP_NET_BIND_SERVICE=+eip /usr/bin/python3
```

### macOS

**Gatekeeper:**
```bash
xattr -d com.apple.quarantine start_giljo.py
```

---

## Best Practices

### Code Portability

```python
# Use pathlib.Path
from pathlib import Path
config = Path("config.yaml")

# Platform detection
import platform
system = platform.system()  # 'Windows', 'Linux', 'Darwin'

# Environment variables
import os
port = os.environ.get("GILJO_API_PORT", "7272")
```

### Security

1. **Firewall:** Only open necessary ports
2. **Database:** Never expose PostgreSQL to network
3. **API Keys:** Always enable in server mode
4. **File Permissions:** Restrict config files (chmod 600)

---

## Quick Reference

**Platform Detection:**
```python
import sys
is_windows = sys.platform == "win32"
is_linux = sys.platform.startswith("linux")
is_macos = sys.platform == "darwin"
```

**Network Binding:**
- Localhost mode: `127.0.0.1` (development)
- Server mode: `0.0.0.0` (production)

---

## Additional Resources

- Technical Architecture: `docs/TECHNICAL_ARCHITECTURE.md`
- Platform Testing Matrix: `docs/PLATFORM_TESTING_MATRIX.md`
- Installation Scripts: `scripts/install_dependencies_*.{ps1,sh}`
- Unified Deployment: `scripts/deploy.py`

---

**Last Updated:** 2025-10-04  
**Maintained By:** GiljoAI MCP Architecture Team
