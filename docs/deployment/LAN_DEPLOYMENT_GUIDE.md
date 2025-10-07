# GiljoAI MCP - LAN Deployment Guide

**Version:** 1.0
**Date:** 2025-10-04
**Target:** Phase 1 - Local Area Network Deployment
**Status:** Production Ready

---

## Table of Contents

1. [Quick Start (Wizard Method - Recommended)](#quick-start-wizard-method---recommended)
2. [Overview](#overview)
3. [Prerequisites](#prerequisites)
4. [Architecture Overview](#architecture-overview)
5. [Cross-Platform Installation](#cross-platform-installation)
6. [LAN-Specific Configuration](#lan-specific-configuration)
7. [Manual Setup (Advanced)](#manual-setup-advanced)
8. [Security Hardening](#security-hardening)
9. [Testing and Validation](#testing-and-validation)
10. [Troubleshooting](#troubleshooting)
11. [Platform-Specific Commands](#platform-specific-commands)

---

## Quick Start (Wizard Method - Recommended)

The fastest way to enable LAN mode is through the Setup Wizard:

### Prerequisites
- PostgreSQL 18 installed and running
- GiljoAI MCP services running
- Browser access to http://localhost:7274

### Steps

1. **Access Setup Wizard**
   - Navigate to http://localhost:7274/setup
   - Or click "Setup Wizard" in Settings page

2. **Complete Wizard**
   - Step 1: Welcome
   - Step 2: Tool Attachment (optional: enable Serena MCP)
   - **Step 3: Network Configuration**
     - Select "LAN" mode
     - Auto-detect or manually enter server IP
     - Create admin account (username + password)
     - Confirm firewall configuration
   - Step 4: Completion + API Key modal + Restart instructions

3. **Post-Setup**
   - API key displayed once (save it!)
   - Restart services as instructed
   - config.yaml automatically updated:
     - `installation.mode: lan`
     - `services.api.host: 0.0.0.0`
     - `security.cors.allowed_origins` includes LAN IP

### What the Wizard Does Automatically

**Backend Updates:**
- Generates cryptographically secure API key (`gk_` prefix, 43 chars)
- Stores encrypted API key in `~/.giljo-mcp/api_keys.json`
- Hashes admin password (bcrypt) and stores in `~/.giljo-mcp/admin_account.json`
- Updates CORS origins to include server IP and hostname
- Saves LAN configuration to config.yaml

**Security Measures:**
- API key encrypted with Fernet cipher
- Admin password hashed with bcrypt (rounds=12)
- Database binding remains localhost-only
- CORS origins explicitly configured (no wildcards)

---

## Overview

### What is LAN Deployment Mode?

LAN (Local Area Network) deployment mode enables GiljoAI MCP to be accessible across your trusted internal network, allowing multiple team members to collaborate using a centralized orchestration server.

**Key Characteristics:**

- Network-accessible within your organization
- API key authentication required
- Designed for trusted network environments
- Optimized for low-latency local network access
- Supports 20+ concurrent agents per deployment
- Perfect for team environments and office networks

### Use Cases

- Development teams sharing a coding orchestrator
- Internal company network deployments
- Office/lab environments with controlled access
- Educational institutions within campus networks
- Small to medium team collaboration (5-50 users)

### Security Model

LAN mode assumes a **trusted network environment**:

- Network perimeter security (firewall at edge)
- API key authentication for access control
- TLS/SSL recommended but optional
- Database network access within LAN
- Logging and monitoring for accountability

**Note:** For internet-facing deployments (WAN), see the separate WAN Deployment Guide.

---

## Prerequisites

### System Requirements

**Server (API + Database):**

- **CPU:** 4+ cores recommended
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 50GB+ SSD for database
- **Network:** Gigabit Ethernet recommended
- **OS:** Windows Server 2019+, Ubuntu 20.04+, macOS 12+

**Client Machines:**

- Any modern OS with network access
- Web browser (for dashboard)
- Python 3.8+ (for CLI tools)

### Software Requirements

[All Platforms]

- **PostgreSQL 18+** (required)
- **Python 3.8+** (for API server)
- **Node.js 16+** (for frontend build)
- **Git** (for version control)

[Platform-Specific]

- **Windows:** PowerShell 5.1+, .NET Framework 4.8+
- **Linux:** systemd, iptables or ufw
- **macOS:** Homebrew, launchd

### Network Requirements

- **Fixed IP address** for server (static or DHCP reservation)
- **Ports available:**
  - 7272 (API)
  - 6003 (WebSocket)
  - 7274 (Dashboard)
  - 5432 (PostgreSQL - internal)
- **Firewall:** Configure to allow above ports within LAN
- **DNS:** Optional but recommended for friendly names

---

## Architecture Overview

### LAN Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAN Network (Trusted)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐│
│  │   Client 1   │     │   Client 2   │     │   Client N   ││
│  │  (Desktop)   │     │  (Laptop)    │     │  (Workstation││
│  └───────┬──────┘     └───────┬──────┘     └───────┬──────┘│
│          │                    │                     │        │
│          └────────────────────┼─────────────────────┘        │
│                               │                              │
│                      ┌────────▼────────┐                     │
│                      │  GiljoAI Server │                     │
│                      │  (0.0.0.0:7272) │                     │
│                      │                 │                     │
│                      │  ┌───────────┐  │                     │
│                      │  │   API     │  │                     │
│                      │  │  Server   │  │                     │
│                      │  └───────────┘  │                     │
│                      │  ┌───────────┐  │                     │
│                      │  │PostgreSQL │  │                     │
│                      │  │ Database  │  │                     │
│                      │  └───────────┘  │                     │
│                      └─────────────────┘                     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
         │                                            │
         └────────────────────────────────────────────┘
                    Firewall (Edge Protection)
```

### Component Roles

**Server Components:**

- **API Server:** Handles orchestration requests (port 7272)
- **WebSocket Server:** Real-time updates (port 6003)
- **Dashboard:** Web UI for monitoring (port 7274)
- **PostgreSQL:** Persistent storage (port 5432, internal)

**Client Components:**

- **CLI Tools:** Command-line interaction
- **Web Browser:** Dashboard access
- **MCP Integration:** Claude Code connection

---

## Cross-Platform Installation

### Installation Workflow

The installation process is consistent across all platforms:

1. **System Validation**
2. **Dependency Installation**
3. **Server Configuration**
4. **Network Setup**
5. **Security Configuration**
6. **Service Installation**
7. **Validation and Testing**

### Platform Selection

Choose your platform:

- [Windows Server Installation](#windows-server-installation)
- [Linux Installation (Ubuntu/Debian)](#linux-installation)
- [macOS Installation](#macos-installation)
- [Docker Deployment (All Platforms)](#docker-deployment)

---

## Windows Server Installation

### Step 1: System Preparation

[Windows]

```powershell
# Run PowerShell as Administrator

# Check system requirements
Write-Host "System Requirements Check" -ForegroundColor Cyan
Write-Host "OS: $((Get-WmiObject Win32_OperatingSystem).Caption)"
Write-Host "RAM: $([Math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory/1GB, 2)) GB"
Write-Host "CPU Cores: $((Get-WmiObject Win32_Processor).NumberOfCores)"

# Enable required Windows features
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole -All
```

### Step 2: Install PostgreSQL 18

[Windows]

```powershell
# Download PostgreSQL 18 installer
$pgUrl = "https://get.enterprisedb.com/postgresql/postgresql-18.0-1-windows-x64.exe"
$installer = "$env:TEMP\postgresql-18-installer.exe"

Invoke-WebRequest -Uri $pgUrl -OutFile $installer

# Silent installation with LAN configuration
Start-Process -FilePath $installer -ArgumentList `
    "--mode", "unattended", `
    "--unattendedmodeui", "minimal", `
    "--superpassword", "YourSecurePassword", `
    "--serverport", "5432", `
    "--enable-components", "server,commandlinetools" `
    -Wait

# Configure PostgreSQL for network access
$pgConfPath = "C:\Program Files\PostgreSQL\18\data\postgresql.conf"
$pgHbaPath = "C:\Program Files\PostgreSQL\18\data\pg_hba.conf"

# Edit postgresql.conf
Add-Content -Path $pgConfPath -Value "`nlisten_addresses = '0.0.0.0'"
Add-Content -Path $pgConfPath -Value "max_connections = 100"

# Edit pg_hba.conf for LAN access
Add-Content -Path $pgHbaPath -Value "`nhost all all 192.168.0.0/16 scram-sha-256"

# Restart PostgreSQL service
Restart-Service -Name postgresql-x64-18

Write-Host "PostgreSQL configured for LAN access" -ForegroundColor Green
```

### Step 3: Install Python and Dependencies

[Windows]

```powershell
# Install Python 3.11 (if not installed)
winget install Python.Python.3.11

# Verify Python installation
python --version

# Clone GiljoAI MCP repository
cd C:\
git clone https://github.com/giljoai/mcp-orchestrator.git
cd mcp-orchestrator

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure for LAN Mode

[Windows]

```powershell
# Run installer in server mode
python installer\cli\install.py --mode server

# The installer will prompt for:
# - Database password
# - API port (default: 7272)
# - Network binding (0.0.0.0 for LAN)
# - API key generation

# Edit config.yaml manually if needed
notepad config.yaml
```

**config.yaml (LAN Configuration):**

```yaml
installation:
  mode: server

services:
  api:
    host: 0.0.0.0  # Bind to all network interfaces
    port: 7272
  websocket:
    port: 6003
  frontend:
    port: 7274

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp
  user: giljo_user
  # password set in .env file

security:
  api_key_required: true
  rate_limiting: true
  max_requests_per_minute: 100

features:
  ssl: false  # Optional for LAN (can enable later)
```

### Step 5: Configure Windows Firewall

[Windows]

```powershell
# Allow API port
New-NetFirewallRule -DisplayName "GiljoAI MCP API" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 7272 `
    -Action Allow `
    -Profile Domain,Private

# Allow WebSocket port
New-NetFirewallRule -DisplayName "GiljoAI MCP WebSocket" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 6003 `
    -Action Allow `
    -Profile Domain,Private

# Allow Dashboard port
New-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 7274 `
    -Action Allow `
    -Profile Domain,Private

Write-Host "Firewall rules configured" -ForegroundColor Green
```

### Step 6: Create Windows Service

[Windows]

```powershell
# Create Windows service for auto-start
$serviceName = "GiljoAI-MCP"
$serviceDescription = "GiljoAI MCP Orchestration Server"
$pythonExe = "C:\mcp-orchestrator\venv\Scripts\python.exe"
$scriptPath = "C:\mcp-orchestrator\api\run_api.py"

# Install service using NSSM (Non-Sucking Service Manager)
# Download NSSM: https://nssm.cc/download
nssm install $serviceName $pythonExe $scriptPath
nssm set $serviceName Description $serviceDescription
nssm set $serviceName Start SERVICE_AUTO_START
nssm set $serviceName AppDirectory "C:\mcp-orchestrator"

# Start service
nssm start $serviceName

Write-Host "Service installed and started" -ForegroundColor Green
```

### Step 7: Validation

[Windows]

```powershell
# Test API endpoint
Invoke-WebRequest -Uri "http://localhost:7272/health" | Select-Object -ExpandProperty Content

# Test from network IP
$localIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias Ethernet).IPAddress
Invoke-WebRequest -Uri "http://$localIP:7272/health" | Select-Object -ExpandProperty Content

# Check service status
Get-Service -Name "GiljoAI-MCP"

Write-Host "Validation complete" -ForegroundColor Green
```

---

## Linux Installation

### Step 1: System Preparation

[Linux]

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y curl wget git build-essential

# Check system requirements
echo "System Requirements Check"
echo "OS: $(lsb_release -d | awk -F'\t' '{print $2}')"
echo "RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "CPU Cores: $(nproc)"
```

### Step 2: Install PostgreSQL 18

[Linux]

```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Install PostgreSQL 18
sudo apt update
sudo apt install -y postgresql-18 postgresql-contrib-18

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configure PostgreSQL for LAN access
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'YourSecurePassword';"
sudo -u postgres psql -c "CREATE DATABASE giljo_mcp;"
sudo -u postgres psql -c "CREATE USER giljo_user WITH PASSWORD 'YourSecurePassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE giljo_mcp TO giljo_user;"

# Edit postgresql.conf
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/18/main/postgresql.conf

# Edit pg_hba.conf for LAN access
echo "host all all 192.168.0.0/16 scram-sha-256" | sudo tee -a /etc/postgresql/18/main/pg_hba.conf

# Restart PostgreSQL
sudo systemctl restart postgresql

echo "PostgreSQL configured for LAN access"
```

### Step 3: Install Python and Dependencies

[Linux]

```bash
# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Clone repository
cd /opt
sudo git clone https://github.com/giljoai/mcp-orchestrator.git
cd mcp-orchestrator

# Set permissions
sudo chown -R $USER:$USER /opt/mcp-orchestrator

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure for LAN Mode

[Linux]

```bash
# Run installer in server mode
python installer/cli/install.py --mode server

# Edit config.yaml if needed
nano config.yaml
```

### Step 5: Configure Firewall (UFW)

[Linux]

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Allow GiljoAI MCP ports
sudo ufw allow 7272/tcp comment 'GiljoAI MCP API'
sudo ufw allow 6003/tcp comment 'GiljoAI MCP WebSocket'
sudo ufw allow 7274/tcp comment 'GiljoAI MCP Dashboard'

# Check firewall status
sudo ufw status

echo "Firewall configured"
```

**Alternative: iptables**

[Linux]

```bash
# For systems using iptables directly
sudo iptables -A INPUT -p tcp --dport 7272 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6003 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 7274 -j ACCEPT

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### Step 6: Create systemd Service

[Linux]

```bash
# Create service file
sudo tee /etc/systemd/system/giljo-mcp.service > /dev/null << 'EOF'
[Unit]
Description=GiljoAI MCP Orchestration Server
After=network.target postgresql.service

[Service]
Type=simple
User=giljo
Group=giljo
WorkingDirectory=/opt/mcp-orchestrator
Environment="PATH=/opt/mcp-orchestrator/venv/bin"
ExecStart=/opt/mcp-orchestrator/venv/bin/python api/run_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create service user (optional but recommended)
sudo useradd -r -s /bin/false giljo
sudo chown -R giljo:giljo /opt/mcp-orchestrator

# Reload systemd, enable and start service
sudo systemctl daemon-reload
sudo systemctl enable giljo-mcp.service
sudo systemctl start giljo-mcp.service

# Check service status
sudo systemctl status giljo-mcp.service

echo "Service installed and started"
```

### Step 7: Validation

[Linux]

```bash
# Test API endpoint (localhost)
curl http://localhost:7272/health

# Get LAN IP address
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Server LAN IP: $LOCAL_IP"

# Test from LAN IP
curl http://$LOCAL_IP:7272/health

# Check service logs
sudo journalctl -u giljo-mcp.service -f

echo "Validation complete"
```

---

## macOS Installation

### Step 1: System Preparation

[macOS]

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Update Homebrew
brew update

# Check system requirements
echo "System Requirements Check"
echo "OS: $(sw_vers -productName) $(sw_vers -productVersion)"
echo "RAM: $(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}')"
echo "CPU Cores: $(sysctl -n hw.ncpu)"
```

### Step 2: Install PostgreSQL 18

[macOS]

```bash
# Install PostgreSQL via Homebrew
brew install postgresql@18

# Start PostgreSQL service
brew services start postgresql@18

# Create database and user
createdb giljo_mcp
psql postgres -c "CREATE USER giljo_user WITH PASSWORD 'YourSecurePassword';"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE giljo_mcp TO giljo_user;"

# Configure for LAN access
PG_CONF="/opt/homebrew/var/postgresql@18/postgresql.conf"
PG_HBA="/opt/homebrew/var/postgresql@18/pg_hba.conf"

# Edit postgresql.conf
echo "listen_addresses = '*'" >> $PG_CONF
echo "max_connections = 100" >> $PG_CONF

# Edit pg_hba.conf for LAN
echo "host all all 192.168.0.0/16 scram-sha-256" >> $PG_HBA

# Restart PostgreSQL
brew services restart postgresql@18

echo "PostgreSQL configured for LAN access"
```

### Step 3: Install Python and Dependencies

[macOS]

```bash
# Install Python 3.11 via Homebrew
brew install python@3.11

# Clone repository
cd /usr/local
sudo git clone https://github.com/giljoai/mcp-orchestrator.git
cd mcp-orchestrator

# Set permissions
sudo chown -R $(whoami):staff /usr/local/mcp-orchestrator

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure for LAN Mode

[macOS]

```bash
# Run installer in server mode
python installer/cli/install.py --mode server

# Edit config.yaml if needed
nano config.yaml
```

### Step 5: Configure Firewall (pf)

[macOS]

```bash
# macOS uses pf (packet filter) firewall
# Create pf rules file
sudo tee /etc/pf.anchors/giljo-mcp > /dev/null << 'EOF'
# GiljoAI MCP - LAN Access Rules
pass in proto tcp from 192.168.0.0/16 to any port 7272
pass in proto tcp from 192.168.0.0/16 to any port 6003
pass in proto tcp from 192.168.0.0/16 to any port 7274
EOF

# Load pf anchor
echo "anchor \"giljo-mcp\"" | sudo tee -a /etc/pf.conf
echo "load anchor \"giljo-mcp\" from \"/etc/pf.anchors/giljo-mcp\"" | sudo tee -a /etc/pf.conf

# Enable and reload pf
sudo pfctl -e
sudo pfctl -f /etc/pf.conf

echo "Firewall configured"
```

**Alternative: macOS Application Firewall**

[macOS]

```bash
# Allow Python through application firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/mcp-orchestrator/venv/bin/python3.11
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/local/mcp-orchestrator/venv/bin/python3.11
```

### Step 6: Create launchd Service

[macOS]

```bash
# Create launchd plist file
sudo tee /Library/LaunchDaemons/com.giljoai.mcp.plist > /dev/null << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.giljoai.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/mcp-orchestrator/venv/bin/python</string>
        <string>api/run_api.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/usr/local/mcp-orchestrator</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/usr/local/mcp-orchestrator/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/usr/local/mcp-orchestrator/logs/stderr.log</string>
</dict>
</plist>
EOF

# Load and start service
sudo launchctl load /Library/LaunchDaemons/com.giljoai.mcp.plist
sudo launchctl start com.giljoai.mcp

# Check service status
sudo launchctl list | grep giljo

echo "Service installed and started"
```

### Step 7: Validation

[macOS]

```bash
# Test API endpoint (localhost)
curl http://localhost:7272/health

# Get LAN IP address
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
echo "Server LAN IP: $LOCAL_IP"

# Test from LAN IP
curl http://$LOCAL_IP:7272/health

# Check service logs
tail -f /usr/local/mcp-orchestrator/logs/stdout.log

echo "Validation complete"
```

---

## Docker Deployment

### Cross-Platform Docker Installation

[All Platforms]

```bash
# Pull latest GiljoAI MCP image
docker pull giljoai/mcp-orchestrator:latest

# Create network
docker network create giljo-network

# Run PostgreSQL container
docker run -d \
  --name giljo-postgres \
  --network giljo-network \
  -e POSTGRES_DB=giljo_mcp \
  -e POSTGRES_USER=giljo_user \
  -e POSTGRES_PASSWORD=YourSecurePassword \
  -v giljo-pg-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:18

# Run GiljoAI MCP container
docker run -d \
  --name giljo-mcp \
  --network giljo-network \
  -e MODE=server \
  -e DATABASE_URL=postgresql://giljo_user:YourSecurePassword@giljo-postgres:5432/giljo_mcp \
  -p 7272:7272 \
  -p 6003:6003 \
  -p 7274:7274 \
  giljoai/mcp-orchestrator:latest

# Verify containers running
docker ps

echo "Docker deployment complete"
```

### Docker Compose (Recommended)

[All Platforms]

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:18
    container_name: giljo-postgres
    environment:
      POSTGRES_DB: giljo_mcp
      POSTGRES_USER: giljo_user
      POSTGRES_PASSWORD: YourSecurePassword
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - giljo-network
    restart: always

  giljo-mcp:
    image: giljoai/mcp-orchestrator:latest
    container_name: giljo-mcp
    environment:
      MODE: server
      DATABASE_URL: postgresql://giljo_user:YourSecurePassword@postgres:5432/giljo_mcp
      API_HOST: 0.0.0.0
      API_PORT: 7272
    ports:
      - "7272:7272"
      - "6003:6003"
      - "7274:7274"
    depends_on:
      - postgres
    networks:
      - giljo-network
    restart: always

volumes:
  postgres-data:

networks:
  giljo-network:
    driver: bridge
```

**Start services:**

```bash
docker-compose up -d
docker-compose logs -f giljo-mcp
```

---

## LAN-Specific Configuration

### Network Binding

**Critical:** Server must bind to `0.0.0.0` to be accessible on LAN.

config.yaml:

```yaml
services:
  api:
    host: 0.0.0.0  # All network interfaces
    port: 7272
```

.env:

```bash
API_HOST=0.0.0.0
API_PORT=7272
```

### Static IP Configuration

**Recommended:** Use static IP or DHCP reservation for the server.

[Windows]

```powershell
# Set static IP
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.1.100 -PrefixLength 24 -DefaultGateway 192.168.1.1
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses "8.8.8.8","8.8.4.4"
```

[Linux]

```bash
# Edit netplan configuration
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply
```

[macOS]

```bash
# Use System Preferences > Network
# Or via command line:
sudo networksetup -setmanual "Ethernet" 192.168.1.100 255.255.255.0 192.168.1.1
sudo networksetup -setdnsservers "Ethernet" 8.8.8.8 8.8.4.4
```

### API Key Configuration

**Required for LAN mode security.**

config.yaml:

```yaml
security:
  api_key_required: true
  rate_limiting: true
  max_requests_per_minute: 100
```

**Generate API key:**

[All Platforms]

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\Activate.ps1  # Windows

# Generate API key
python -c "import secrets; print(f'giljo_lan_{secrets.token_urlsafe(32)}')"

# Example output: giljo_lan_Xy9z8W7vU6tS5rQ4pO3nM2lK1jH0gF9e8D7c6B5a4
```

**Store in .env:**

```bash
API_KEY=giljo_lan_Xy9z8W7vU6tS5rQ4pO3nM2lK1jH0gF9e8D7c6B5a4
```

**Distribute to clients:**

Create `.giljo-mcp-config` in user home directory:

```yaml
server: http://192.168.1.100:7272
api_key: giljo_lan_Xy9z8W7vU6tS5rQ4pO3nM2lK1jH0gF9e8D7c6B5a4
```

---

## Manual Setup (Advanced)

If you need to configure LAN mode manually without the wizard, follow these steps:

### Phase 1: Server Configuration

1. **Install PostgreSQL** (see platform-specific instructions)
2. **Configure PostgreSQL for LAN access** (listen_addresses, pg_hba.conf)
3. **Create database and user**
4. **Restart PostgreSQL service**

### Phase 2: Application Installation

1. **Clone repository**
2. **Create virtual environment**
3. **Install Python dependencies**
4. **Run installer with --mode server**
5. **Edit config.yaml for LAN settings**

### Phase 3: Network Configuration

1. **Configure firewall rules** (allow ports 7272, 6003, 7274)
2. **Set static IP or DHCP reservation**
3. **Test network accessibility from another machine**

### Phase 4: Security Setup

1. **Generate API key**
2. **Configure rate limiting**
3. **Set up logging**
4. **Create admin user (optional)**

### Phase 5: Service Installation

1. **Create OS service** (Windows service, systemd, launchd)
2. **Configure auto-start**
3. **Start service**
4. **Verify service status**

### Phase 6: Testing

1. **Test localhost access**
2. **Test LAN IP access from server**
3. **Test from client machine on LAN**
4. **Verify API key authentication**
5. **Load testing (optional)**

---

## Security Hardening

### API Key Management

**Best Practices:**

- Generate strong keys (32+ characters)
- Use different keys for different clients/teams
- Rotate keys periodically (every 90 days)
- Store keys securely (password manager, secrets vault)
- Never commit keys to version control

**Key Rotation Procedure:**

1. Generate new API key
2. Distribute to clients
3. Set grace period (7 days)
4. Deactivate old key
5. Update logs and monitoring

### Rate Limiting

config.yaml:

```yaml
security:
  rate_limiting: true
  max_requests_per_minute: 100
  burst_size: 20
```

### Logging and Monitoring

**Enable comprehensive logging:**

config.yaml:

```yaml
logging:
  level: INFO
  file: /var/log/giljo-mcp/api.log
  max_size_mb: 100
  backup_count: 10
  access_log: true
  security_events: true
```

**Monitor logs:**

[Windows]

```powershell
Get-Content -Path "C:\mcp-orchestrator\logs\api.log" -Tail 50 -Wait
```

[Linux/macOS]

```bash
tail -f /var/log/giljo-mcp/api.log
```

### Database Security

**PostgreSQL hardening:**

postgresql.conf:

```conf
# Connection settings
max_connections = 100
password_encryption = scram-sha-256

# Logging
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# Security
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

pg_hba.conf:

```conf
# LAN access with strong authentication
host all all 192.168.0.0/16 scram-sha-256

# Reject everything else
host all all 0.0.0.0/0 reject
```

### Backup Procedures

**Automated PostgreSQL backups:**

[Linux/macOS]

```bash
#!/bin/bash
# /opt/backups/backup-giljo.sh

BACKUP_DIR="/opt/backups/giljo-mcp"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/giljo_mcp_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U giljo_user -h localhost giljo_mcp | gzip > $BACKUP_FILE

# Keep last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

**Schedule with cron:**

```bash
# Run daily at 2 AM
0 2 * * * /opt/backups/backup-giljo.sh
```

[Windows]

```powershell
# backup-giljo.ps1
$BackupDir = "C:\Backups\GiljoMCP"
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = "$BackupDir\giljo_mcp_$Date.sql"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir
}

# Backup database
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U giljo_user -h localhost giljo_mcp > $BackupFile

# Compress
Compress-Archive -Path $BackupFile -DestinationPath "$BackupFile.zip"
Remove-Item $BackupFile

# Keep last 7 days
Get-ChildItem -Path $BackupDir -Filter "*.zip" | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | Remove-Item

Write-Host "Backup completed: $BackupFile.zip"
```

**Schedule with Task Scheduler:**

```powershell
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Backups\backup-giljo.ps1"
$Trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "GiljoAI-MCP-Backup" -Action $Action -Trigger $Trigger
```

---

## Testing and Validation

### Network Accessibility Tests

**From Server:**

[All Platforms]

```bash
# Test localhost
curl http://localhost:7272/health

# Test LAN IP (replace with your IP)
curl http://192.168.1.100:7272/health
```

**From Client Machine:**

```bash
# Test API
curl http://192.168.1.100:7272/health

# Test with API key
curl -H "X-API-Key: your_api_key_here" http://192.168.1.100:7272/api/v1/projects/

# Test WebSocket (using wscat)
npm install -g wscat
wscat -c ws://192.168.1.100:6003/ws
```

### Performance Testing

**Latency Test:**

```bash
#!/bin/bash
# Test network latency to API

for i in {1..20}; do
    curl -w "@curl-format.txt" -o /dev/null -s http://192.168.1.100:7272/health
done
```

curl-format.txt:

```
time_total: %{time_total}s\n
```

**Expected Results (LAN):**

- Average latency: < 50ms
- Max latency: < 100ms
- Success rate: > 99%

### Load Testing

**Using Python:**

```python
#!/usr/bin/env python3
# load_test.py

import asyncio
import httpx
import time

async def test_endpoint(client, api_key):
    headers = {"X-API-Key": api_key}
    response = await client.get("/health", headers=headers)
    return response.status_code == 200

async def load_test(num_clients=50, duration_seconds=60):
    base_url = "http://192.168.1.100:7272"
    api_key = "your_api_key_here"

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        start_time = time.time()
        requests = 0
        successes = 0

        while time.time() - start_time < duration_seconds:
            tasks = [test_endpoint(client, api_key) for _ in range(num_clients)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            requests += len(results)
            successes += sum(1 for r in results if r is True)

            await asyncio.sleep(1)  # 1 second interval

        duration = time.time() - start_time
        success_rate = (successes / requests * 100) if requests > 0 else 0

        print(f"Load Test Results:")
        print(f"Duration: {duration:.2f}s")
        print(f"Total Requests: {requests}")
        print(f"Successful: {successes}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Requests/sec: {requests/duration:.2f}")

if __name__ == "__main__":
    asyncio.run(load_test())
```

**Run load test:**

```bash
python load_test.py
```

---

## Troubleshooting

### Wizard Issues

**Problem:** "Auto-Detect IP" button doesn't work
**Solution:**
- Backend endpoint may be unavailable
- Check API server is running: `http://localhost:7272/health`
- Wizard falls back to WebRTC detection automatically
- Or enter IP manually (find with `ipconfig` / `ifconfig`)

**Problem:** API key modal doesn't appear
**Solution:**
- Check browser console for errors
- Verify `/api/setup/complete` endpoint returns `api_key` field
- Check mode is set to "lan" (not "localhost")

**Problem:** Services don't restart properly
**Solution:**
- Manually run: `stop_giljo.bat && start_giljo.bat` (Windows)
- Check ports not in use: `netstat -ano | findstr :7272`
- Verify config.yaml updated with LAN settings

### Network Access Issues

**Problem:** Can't access from LAN device
**Solution:**
1. Verify server IP in CORS origins:
   ```yaml
   # config.yaml
   security:
     cors:
       allowed_origins:
         - http://192.168.1.50:7274  # Your server IP
   ```
2. Ensure API key in request header:
   ```bash
   curl -H "X-API-Key: gk_your_key" http://192.168.1.50:7272/health
   ```
3. Check firewall allows ports 7272, 7274

**Problem:** CORS errors in browser
**Solution:**
- Settings → Network tab → Add LAN client IP to CORS origins
- Restart services after CORS change
- Clear browser cache

### API Key Issues

**Problem:** Lost API key
**Solution:**
- Option 1: Re-run Setup Wizard (generates new key, invalidates old)
- Option 2: Regenerate via Settings (future feature)
- Option 3: Manual regeneration:
  ```python
  from giljo_mcp.auth import AuthManager
  auth = AuthManager()
  new_key = auth.generate_api_key("manual-key")
  print(f"New API key: {new_key}")
  ```

**Problem:** API key authentication fails
**Solution:**
- Verify header name: `X-API-Key` (not `Authorization`)
- Check key format: starts with `gk_`
- Confirm mode is `lan` in config.yaml
- Check `~/.giljo-mcp/api_keys.json` exists and contains key

---

### Issue: Cannot access server from LAN

**Symptoms:**

- `curl: (7) Failed to connect`
- Connection timeout

**Diagnosis:**

```bash
# Check if server is listening on correct interface
[Windows]
netstat -an | findstr 7272

[Linux/macOS]
netstat -an | grep 7272
ss -tulpn | grep 7272
```

**Expected:** `0.0.0.0:7272` or `*:7272` (NOT `127.0.0.1:7272`)

**Solutions:**

1. Verify config.yaml has `host: 0.0.0.0`
2. Restart API service
3. Check firewall rules
4. Verify client is on same network segment

### Issue: Firewall blocking connections

**Symptoms:**

- Local access works
- LAN access fails
- `curl: (7) Failed to connect`

**Diagnosis:**

[Windows]

```powershell
# Check firewall rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Giljo*"}

# Test port
Test-NetConnection -ComputerName 192.168.1.100 -Port 7272
```

[Linux]

```bash
# Check UFW status
sudo ufw status

# Check iptables rules
sudo iptables -L -n | grep 7272
```

[macOS]

```bash
# Check pf rules
sudo pfctl -s rules | grep 7272

# Check application firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps
```

**Solutions:**

1. Verify firewall rules are present
2. Re-run firewall configuration scripts
3. Temporarily disable firewall for testing (NOT recommended in production)
4. Check for additional security software (antivirus, etc.)

### Issue: PostgreSQL not accepting network connections

**Symptoms:**

- `psql: could not connect to server`
- API fails to connect to database

**Diagnosis:**

```bash
# Check PostgreSQL listening
[Windows]
netstat -an | findstr 5432

[Linux/macOS]
netstat -an | grep 5432
```

**Expected:** `0.0.0.0:5432` or `*:5432`

**Solutions:**

1. Verify postgresql.conf has `listen_addresses = '*'`
2. Verify pg_hba.conf has host entry for your LAN subnet
3. Restart PostgreSQL service
4. Check PostgreSQL logs for errors

### Issue: API key authentication failing

**Symptoms:**

- `401 Unauthorized`
- `Invalid API key`

**Diagnosis:**

```bash
# Test with explicit API key
curl -H "X-API-Key: your_key" -v http://192.168.1.100:7272/api/v1/projects/
```

**Solutions:**

1. Verify API key is correct (check .env file)
2. Ensure API key header is `X-API-Key` (case-sensitive)
3. Check that API key authentication is enabled in config.yaml
4. Regenerate API key if corrupted

### Issue: Slow performance on LAN

**Symptoms:**

- High latency (> 200ms)
- Timeouts

**Diagnosis:**

```bash
# Ping test
ping 192.168.1.100

# Network speed test
iperf3 -c 192.168.1.100

# Check server load
[Linux/macOS]
top
htop

[Windows]
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
```

**Solutions:**

1. Check server CPU/memory usage
2. Verify network cable/switch quality
3. Check for network congestion
4. Optimize PostgreSQL connection pooling
5. Enable database query caching

---

## Platform-Specific Commands

### Windows Commands Summary

```powershell
# Service Management
Start-Service -Name GiljoAI-MCP
Stop-Service -Name GiljoAI-MCP
Restart-Service -Name GiljoAI-MCP
Get-Service -Name GiljoAI-MCP

# Firewall Management
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Giljo*"}
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -Protocol TCP -LocalPort 7272 -Action Allow
Remove-NetFirewallRule -DisplayName "GiljoAI MCP API"

# Network Configuration
Get-NetIPAddress
Test-NetConnection -ComputerName 192.168.1.100 -Port 7272
netstat -an | findstr 7272

# PostgreSQL
Restart-Service -Name postgresql-x64-18
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U giljo_user giljo_mcp > backup.sql

# Logs
Get-Content -Path "C:\mcp-orchestrator\logs\api.log" -Tail 50 -Wait
```

### Linux Commands Summary

```bash
# Service Management
sudo systemctl start giljo-mcp.service
sudo systemctl stop giljo-mcp.service
sudo systemctl restart giljo-mcp.service
sudo systemctl status giljo-mcp.service
sudo journalctl -u giljo-mcp.service -f

# Firewall Management (UFW)
sudo ufw status
sudo ufw allow 7272/tcp
sudo ufw delete allow 7272/tcp

# Firewall Management (iptables)
sudo iptables -L -n
sudo iptables -A INPUT -p tcp --dport 7272 -j ACCEPT
sudo iptables -D INPUT -p tcp --dport 7272 -j ACCEPT

# Network Configuration
ip addr show
ss -tulpn | grep 7272
netstat -an | grep 7272
nc -zv 192.168.1.100 7272

# PostgreSQL
sudo systemctl restart postgresql
sudo -u postgres psql
sudo -u postgres pg_dump giljo_mcp > backup.sql

# Logs
tail -f /var/log/giljo-mcp/api.log
sudo journalctl -u postgresql -f
```

### macOS Commands Summary

```bash
# Service Management
sudo launchctl load /Library/LaunchDaemons/com.giljoai.mcp.plist
sudo launchctl unload /Library/LaunchDaemons/com.giljoai.mcp.plist
sudo launchctl start com.giljoai.mcp
sudo launchctl stop com.giljoai.mcp
sudo launchctl list | grep giljo

# Firewall Management (pf)
sudo pfctl -s rules
sudo pfctl -f /etc/pf.conf
sudo pfctl -e
sudo pfctl -d

# Application Firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/mcp-orchestrator/venv/bin/python

# Network Configuration
ifconfig
netstat -an | grep 7272
nc -zv 192.168.1.100 7272

# PostgreSQL
brew services restart postgresql@18
psql postgres
pg_dump -U giljo_user giljo_mcp > backup.sql

# Logs
tail -f /usr/local/mcp-orchestrator/logs/stdout.log
tail -f /usr/local/mcp-orchestrator/logs/stderr.log
```

---

## Next Steps

After successful LAN deployment:

1. **Team Onboarding:**
   - Distribute API keys to team members
   - Share server IP address and documentation
   - Provide client configuration examples

2. **Monitoring Setup:**
   - Configure log aggregation
   - Set up alerting for service failures
   - Create performance dashboards

3. **Backup Strategy:**
   - Implement automated backups
   - Test restore procedures
   - Document disaster recovery plan

4. **Security Audit:**
   - Review firewall rules
   - Audit API key usage
   - Check for unauthorized access attempts

5. **WAN Deployment (Optional):**
   - If internet-facing access is needed, see WAN Deployment Guide
   - Additional security measures required
   - SSL/TLS mandatory

---

## Summary

This guide covered:

- LAN deployment architecture and use cases
- Cross-platform installation (Windows, Linux, macOS)
- Network configuration for LAN access
- Security hardening with API keys
- Service installation and management
- Testing and validation procedures
- Comprehensive troubleshooting

**Key Takeaways:**

- LAN mode provides network access within trusted environments
- API key authentication is required for security
- Firewall configuration is platform-specific but straightforward
- PostgreSQL must be configured for network access
- Testing from client machines is essential
- Monitoring and backups ensure reliability

**Document Status:** Production Ready
**Next Review:** After WAN deployment guide completion

---

**Questions or Issues?**

- Check the LAN Security Checklist (LAN_SECURITY_CHECKLIST.md)
- Review Server Mode Testing Strategy (tests/SERVER_MODE_TESTING_STRATEGY.md)
- Consult Technical Architecture (docs/TECHNICAL_ARCHITECTURE.md)
- Contact support or file an issue on GitHub

**End of LAN Deployment Guide**
