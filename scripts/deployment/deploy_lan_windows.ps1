# GiljoAI MCP - Windows LAN Deployment Script
# Version: 1.0
# Date: 2025-10-04
# Purpose: Automated LAN deployment for Windows Server

<#
.SYNOPSIS
    Automated LAN deployment script for GiljoAI MCP on Windows Server.

.DESCRIPTION
    This script automates the deployment of GiljoAI MCP in LAN mode on Windows Server.
    It handles PostgreSQL installation, firewall configuration, service creation, and validation.

.PARAMETER InstallPath
    Installation directory for GiljoAI MCP (default: C:\GiljoAI-MCP)

.PARAMETER PostgreSQLPassword
    PostgreSQL superuser password (will prompt if not provided)

.PARAMETER APIKey
    API key for server mode (will generate if not provided)

.PARAMETER ServerIP
    Server LAN IP address (will auto-detect if not provided)

.PARAMETER SkipPostgreSQL
    Skip PostgreSQL installation if already installed

.PARAMETER SkipFirewall
    Skip firewall configuration

.PARAMETER DryRun
    Preview actions without making changes

.EXAMPLE
    .\deploy_lan_windows.ps1

.EXAMPLE
    .\deploy_lan_windows.ps1 -InstallPath "D:\GiljoAI" -SkipPostgreSQL

.EXAMPLE
    .\deploy_lan_windows.ps1 -DryRun

.NOTES
    Requires: Administrator privileges, PowerShell 5.1+, Internet connection
    Run as Administrator: Right-click -> "Run as administrator"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "C:\GiljoAI-MCP",

    [Parameter(Mandatory=$false)]
    [string]$PostgreSQLPassword,

    [Parameter(Mandatory=$false)]
    [string]$APIKey,

    [Parameter(Mandatory=$false)]
    [string]$ServerIP,

    [Parameter(Mandatory=$false)]
    [switch]$SkipPostgreSQL,

    [Parameter(Mandatory=$false)]
    [switch]$SkipFirewall,

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Set strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Script configuration
$script:LogFile = "$env:TEMP\giljo-mcp-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$script:PostgreSQLVersion = "18"
$script:PostgreSQLPort = 5432
$script:APIPort = 7272
$script:WebSocketPort = 6003
$script:DashboardPort = 7274

#region Helper Functions

function Write-Log {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,

        [Parameter(Mandatory=$false)]
        [ValidateSet('Info', 'Warning', 'Error', 'Success')]
        [string]$Level = 'Info'
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logMessage = "[$timestamp] [$Level] $Message"

    # Write to log file
    Add-Content -Path $script:LogFile -Value $logMessage

    # Write to console with color
    switch ($Level) {
        'Info'    { Write-Host $Message -ForegroundColor Cyan }
        'Warning' { Write-Host $Message -ForegroundColor Yellow }
        'Error'   { Write-Host $Message -ForegroundColor Red }
        'Success' { Write-Host $Message -ForegroundColor Green }
    }
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-InternetConnection {
    try {
        $result = Test-NetConnection -ComputerName www.google.com -InformationLevel Quiet -ErrorAction SilentlyContinue
        return $result
    } catch {
        return $false
    }
}

function Get-LocalIPAddress {
    try {
        $adapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
            $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual"
        }
        return $adapters[0].IPAddress
    } catch {
        return "127.0.0.1"
    }
}

function New-StrongAPIKey {
    $bytes = New-Object Byte[] 32
    [Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
    $base64 = [Convert]::ToBase64String($bytes)
    return "giljo_lan_$($base64.Replace('+', '').Replace('/', '').Substring(0, 32))"
}

function New-StrongPassword {
    param([int]$Length = 20)

    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    $password = -join ((1..$Length) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    return $password
}

#endregion

#region Validation

function Test-Prerequisites {
    Write-Log "===========================================================" -Level Info
    Write-Log "  GiljoAI MCP - Windows LAN Deployment" -Level Info
    Write-Log "===========================================================" -Level Info
    Write-Log ""

    # Check administrator privileges
    Write-Log "Checking administrator privileges..." -Level Info
    if (-not (Test-Administrator)) {
        Write-Log "ERROR: This script requires administrator privileges." -Level Error
        Write-Log "Please run PowerShell as Administrator and try again." -Level Error
        exit 1
    }
    Write-Log "✓ Running as Administrator" -Level Success

    # Check PowerShell version
    Write-Log "Checking PowerShell version..." -Level Info
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -lt 5) {
        Write-Log "ERROR: PowerShell 5.1 or later is required. Current version: $($psVersion.ToString())" -Level Error
        exit 1
    }
    Write-Log "✓ PowerShell version: $($psVersion.ToString())" -Level Success

    # Check internet connection
    Write-Log "Checking internet connection..." -Level Info
    if (-not (Test-InternetConnection)) {
        Write-Log "WARNING: No internet connection detected. Downloads may fail." -Level Warning
    } else {
        Write-Log "✓ Internet connection available" -Level Success
    }

    # Check available disk space
    Write-Log "Checking available disk space..." -Level Info
    $drive = (Get-Item $InstallPath -ErrorAction SilentlyContinue).PSDrive.Name
    if (-not $drive) {
        $drive = $InstallPath.Substring(0, 1)
    }
    $disk = Get-PSDrive -Name $drive
    $freeSpaceGB = [math]::Round($disk.Free / 1GB, 2)
    if ($freeSpaceGB -lt 10) {
        Write-Log "WARNING: Low disk space on ${drive}: ($freeSpaceGB GB). 10GB+ recommended." -Level Warning
    } else {
        Write-Log "✓ Available disk space: $freeSpaceGB GB" -Level Success
    }

    # Check if Git is installed
    Write-Log "Checking for Git..." -Level Info
    try {
        $gitVersion = git --version 2>&1
        Write-Log "✓ Git is installed: $gitVersion" -Level Success
    } catch {
        Write-Log "WARNING: Git not found. Manual repository clone may be required." -Level Warning
    }

    # Check if Python is installed
    Write-Log "Checking for Python 3.8+..." -Level Info
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -eq 3 -and $minor -ge 8) {
                Write-Log "✓ Python installed: $pythonVersion" -Level Success
            } else {
                Write-Log "WARNING: Python 3.8+ required. Current: $pythonVersion" -Level Warning
            }
        }
    } catch {
        Write-Log "WARNING: Python not found. Will be installed if needed." -Level Warning
    }

    Write-Log ""
    Write-Log "Prerequisites check completed." -Level Success
    Write-Log ""
}

#endregion

#region PostgreSQL Installation

function Install-PostgreSQL {
    if ($SkipPostgreSQL) {
        Write-Log "Skipping PostgreSQL installation (--SkipPostgreSQL flag)" -Level Info
        return
    }

    Write-Log "===========================================================" -Level Info
    Write-Log "  PostgreSQL $script:PostgreSQLVersion Installation" -Level Info
    Write-Log "===========================================================" -Level Info
    Write-Log ""

    # Check if PostgreSQL is already installed
    $pgService = Get-Service -Name "postgresql-x64-$script:PostgreSQLVersion" -ErrorAction SilentlyContinue
    if ($pgService) {
        Write-Log "PostgreSQL $script:PostgreSQLVersion is already installed." -Level Info
        $response = Read-Host "Reconfigure PostgreSQL for LAN access? (y/n)"
        if ($response -ne 'y') {
            Write-Log "Skipping PostgreSQL configuration." -Level Info
            return
        }
    } else {
        # Prompt for PostgreSQL password
        if (-not $PostgreSQLPassword) {
            $securePassword = Read-Host "Enter PostgreSQL superuser (postgres) password" -AsSecureString
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
            $PostgreSQLPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        }

        if ($DryRun) {
            Write-Log "[DRY RUN] Would download and install PostgreSQL $script:PostgreSQLVersion" -Level Info
            return
        }

        # Download PostgreSQL installer
        Write-Log "Downloading PostgreSQL $script:PostgreSQLVersion installer..." -Level Info
        $installerUrl = "https://get.enterprisedb.com/postgresql/postgresql-$script:PostgreSQLVersion.0-1-windows-x64.exe"
        $installerPath = "$env:TEMP\postgresql-$script:PostgreSQLVersion-installer.exe"

        try {
            Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
            Write-Log "✓ PostgreSQL installer downloaded" -Level Success
        } catch {
            Write-Log "ERROR: Failed to download PostgreSQL installer: $_" -Level Error
            exit 1
        }

        # Install PostgreSQL silently
        Write-Log "Installing PostgreSQL $script:PostgreSQLVersion (this may take several minutes)..." -Level Info
        $installArgs = @(
            "--mode", "unattended",
            "--unattendedmodeui", "minimal",
            "--superpassword", $PostgreSQLPassword,
            "--serverport", "$script:PostgreSQLPort",
            "--enable-components", "server,commandlinetools"
        )

        try {
            Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -NoNewWindow
            Write-Log "✓ PostgreSQL installed successfully" -Level Success
        } catch {
            Write-Log "ERROR: PostgreSQL installation failed: $_" -Level Error
            exit 1
        }

        # Clean up installer
        Remove-Item -Path $installerPath -Force -ErrorAction SilentlyContinue
    }

    # Configure PostgreSQL for LAN access
    Write-Log "Configuring PostgreSQL for LAN access..." -Level Info

    $pgDataDir = "C:\Program Files\PostgreSQL\$script:PostgreSQLVersion\data"
    $pgConfPath = Join-Path $pgDataDir "postgresql.conf"
    $pgHbaPath = Join-Path $pgDataDir "pg_hba.conf"

    if ($DryRun) {
        Write-Log "[DRY RUN] Would configure postgresql.conf: listen_addresses = '0.0.0.0'" -Level Info
        Write-Log "[DRY RUN] Would configure pg_hba.conf for LAN access" -Level Info
        return
    }

    # Backup configuration files
    Copy-Item -Path $pgConfPath -Destination "$pgConfPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
    Copy-Item -Path $pgHbaPath -Destination "$pgHbaPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force

    # Edit postgresql.conf
    $pgConfContent = Get-Content -Path $pgConfPath
    $pgConfContent = $pgConfContent -replace "#listen_addresses = 'localhost'", "listen_addresses = '0.0.0.0'"
    $pgConfContent = $pgConfContent -replace "listen_addresses = 'localhost'", "listen_addresses = '0.0.0.0'"
    Add-Content -Path $pgConfPath -Value "`nmax_connections = 100"
    Set-Content -Path $pgConfPath -Value $pgConfContent

    # Edit pg_hba.conf for LAN access
    Add-Content -Path $pgHbaPath -Value "`n# GiljoAI MCP - LAN access"
    Add-Content -Path $pgHbaPath -Value "host all all 192.168.0.0/16 scram-sha-256"
    Add-Content -Path $pgHbaPath -Value "host all all 10.0.0.0/8 scram-sha-256"

    Write-Log "✓ PostgreSQL configured for LAN access" -Level Success

    # Restart PostgreSQL service
    Write-Log "Restarting PostgreSQL service..." -Level Info
    try {
        Restart-Service -Name "postgresql-x64-$script:PostgreSQLVersion" -Force
        Start-Sleep -Seconds 3
        Write-Log "✓ PostgreSQL service restarted" -Level Success
    } catch {
        Write-Log "WARNING: Failed to restart PostgreSQL service: $_" -Level Warning
    }

    # Create GiljoAI database and user
    Write-Log "Creating GiljoAI database and user..." -Level Info

    $psqlPath = "C:\Program Files\PostgreSQL\$script:PostgreSQLVersion\bin\psql.exe"
    $env:PGPASSWORD = $PostgreSQLPassword

    try {
        & $psqlPath -U postgres -c "CREATE DATABASE giljo_mcp;" 2>&1 | Out-Null
        & $psqlPath -U postgres -c "CREATE USER giljo_user WITH PASSWORD '$PostgreSQLPassword';" 2>&1 | Out-Null
        & $psqlPath -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE giljo_mcp TO giljo_user;" 2>&1 | Out-Null
        Write-Log "✓ Database and user created" -Level Success
    } catch {
        Write-Log "WARNING: Database/user creation may have failed (might already exist): $_" -Level Warning
    }

    Remove-Item Env:\PGPASSWORD

    Write-Log ""
}

#endregion

#region Firewall Configuration

function Configure-Firewall {
    if ($SkipFirewall) {
        Write-Log "Skipping firewall configuration (--SkipFirewall flag)" -Level Info
        return
    }

    Write-Log "===========================================================" -Level Info
    Write-Log "  Windows Firewall Configuration" -Level Info
    Write-Log "===========================================================" -Level Info
    Write-Log ""

    if ($DryRun) {
        Write-Log "[DRY RUN] Would create firewall rules for ports: $script:APIPort, $script:WebSocketPort, $script:DashboardPort" -Level Info
        return
    }

    # API Port
    Write-Log "Configuring firewall rule for API (port $script:APIPort)..." -Level Info
    try {
        Remove-NetFirewallRule -DisplayName "GiljoAI MCP API" -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName "GiljoAI MCP API" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $script:APIPort `
            -Action Allow `
            -Profile Domain,Private `
            -Description "GiljoAI MCP API Server" | Out-Null
        Write-Log "✓ Firewall rule created: API port $script:APIPort" -Level Success
    } catch {
        Write-Log "ERROR: Failed to create API firewall rule: $_" -Level Error
    }

    # WebSocket Port
    Write-Log "Configuring firewall rule for WebSocket (port $script:WebSocketPort)..." -Level Info
    try {
        Remove-NetFirewallRule -DisplayName "GiljoAI MCP WebSocket" -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName "GiljoAI MCP WebSocket" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $script:WebSocketPort `
            -Action Allow `
            -Profile Domain,Private `
            -Description "GiljoAI MCP WebSocket Server" | Out-Null
        Write-Log "✓ Firewall rule created: WebSocket port $script:WebSocketPort" -Level Success
    } catch {
        Write-Log "ERROR: Failed to create WebSocket firewall rule: $_" -Level Error
    }

    # Dashboard Port
    Write-Log "Configuring firewall rule for Dashboard (port $script:DashboardPort)..." -Level Info
    try {
        Remove-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard" -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $script:DashboardPort `
            -Action Allow `
            -Profile Domain,Private `
            -Description "GiljoAI MCP Web Dashboard" | Out-Null
        Write-Log "✓ Firewall rule created: Dashboard port $script:DashboardPort" -Level Success
    } catch {
        Write-Log "ERROR: Failed to create Dashboard firewall rule: $_" -Level Error
    }

    Write-Log ""
    Write-Log "Firewall configuration completed." -Level Success
    Write-Log ""
}

#endregion

#region Application Installation

function Install-GiljoAI {
    Write-Log "===========================================================" -Level Info
    Write-Log "  GiljoAI MCP Application Installation" -Level Info
    Write-Log "===========================================================" -Level Info
    Write-Log ""

    # Create installation directory
    if (-not (Test-Path $InstallPath)) {
        Write-Log "Creating installation directory: $InstallPath" -Level Info
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
            Write-Log "✓ Installation directory created" -Level Success
        } else {
            Write-Log "[DRY RUN] Would create directory: $InstallPath" -Level Info
        }
    } else {
        Write-Log "Installation directory already exists: $InstallPath" -Level Info
    }

    # Clone repository or copy files
    $repoPath = Join-Path $InstallPath "mcp-orchestrator"
    if (-not (Test-Path $repoPath)) {
        Write-Log "Cloning GiljoAI MCP repository..." -Level Info
        if (-not $DryRun) {
            try {
                git clone https://github.com/giljoai/mcp-orchestrator.git $repoPath 2>&1 | Out-Null
                Write-Log "✓ Repository cloned" -Level Success
            } catch {
                Write-Log "ERROR: Failed to clone repository. Please clone manually." -Level Error
                Write-Log "  git clone https://github.com/giljoai/mcp-orchestrator.git $repoPath" -Level Info
                exit 1
            }
        } else {
            Write-Log "[DRY RUN] Would clone repository to: $repoPath" -Level Info
        }
    } else {
        Write-Log "Repository already exists: $repoPath" -Level Info
    }

    # Create Python virtual environment
    $venvPath = Join-Path $repoPath "venv"
    if (-not (Test-Path $venvPath)) {
        Write-Log "Creating Python virtual environment..." -Level Info
        if (-not $DryRun) {
            Push-Location $repoPath
            try {
                python -m venv venv
                Write-Log "✓ Virtual environment created" -Level Success
            } catch {
                Write-Log "ERROR: Failed to create virtual environment: $_" -Level Error
                exit 1
            }
            Pop-Location
        } else {
            Write-Log "[DRY RUN] Would create virtual environment at: $venvPath" -Level Info
        }
    } else {
        Write-Log "Virtual environment already exists" -Level Info
    }

    # Install Python dependencies
    Write-Log "Installing Python dependencies..." -Level Info
    if (-not $DryRun) {
        Push-Location $repoPath
        try {
            & "$venvPath\Scripts\pip.exe" install --upgrade pip | Out-Null
            & "$venvPath\Scripts\pip.exe" install -r requirements.txt | Out-Null
            Write-Log "✓ Python dependencies installed" -Level Success
        } catch {
            Write-Log "ERROR: Failed to install dependencies: $_" -Level Error
            exit 1
        }
        Pop-Location
    } else {
        Write-Log "[DRY RUN] Would install Python dependencies" -Level Info
    }

    Write-Log ""
}

#endregion

#region Configuration

function Configure-GiljoAI {
    Write-Log "===========================================================" -Level Info
    Write-Log "  GiljoAI MCP Configuration" -Level Info
    Write-Log "===========================================================" -Level Info
    Write-Log ""

    $repoPath = Join-Path $InstallPath "mcp-orchestrator"
    $configPath = Join-Path $repoPath "config.yaml"
    $envPath = Join-Path $repoPath ".env"

    # Auto-detect server IP if not provided
    if (-not $ServerIP) {
        $ServerIP = Get-LocalIPAddress
        Write-Log "Auto-detected server LAN IP: $ServerIP" -Level Info
    }

    # Generate API key if not provided
    if (-not $APIKey) {
        $APIKey = New-StrongAPIKey
        Write-Log "Generated API key: $APIKey" -Level Success
    }

    if ($DryRun) {
        Write-Log "[DRY RUN] Would create config.yaml and .env files" -Level Info
        Write-Log "[DRY RUN] Server IP: $ServerIP" -Level Info
        Write-Log "[DRY RUN] API Key: $APIKey" -Level Info
        return
    }

    # Create config.yaml
    Write-Log "Creating config.yaml..." -Level Info
    $configContent = @"
installation:
  mode: server

services:
  api:
    host: 0.0.0.0
    port: $script:APIPort
  websocket:
    port: $script:WebSocketPort
  frontend:
    port: $script:DashboardPort

database:
  type: postgresql
  host: localhost
  port: $script:PostgreSQLPort
  name: giljo_mcp
  user: giljo_user

security:
  api_key_required: true
  rate_limiting: true
  max_requests_per_minute: 100

features:
  ssl: false
"@

    Set-Content -Path $configPath -Value $configContent
    Write-Log "✓ config.yaml created" -Level Success

    # Create .env file
    Write-Log "Creating .env file..." -Level Info
    $envContent = @"
# GiljoAI MCP Environment Configuration
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

MODE=server
DATABASE_URL=postgresql://giljo_user:$PostgreSQLPassword@localhost:$script:PostgreSQLPort/giljo_mcp
API_HOST=0.0.0.0
API_PORT=$script:APIPort
API_KEY=$APIKey
SERVER_IP=$ServerIP
"@

    Set-Content -Path $envPath -Value $envContent

    # Set secure permissions on .env file
    $acl = Get-Acl $envPath
    $acl.SetAccessRuleProtection($true, $false)
    $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("BUILTIN\Administrators", "FullControl", "Allow")
    $acl.SetAccessRule($adminRule)
    Set-Acl -Path $envPath -AclObject $acl

    Write-Log "✓ .env file created with restricted permissions" -Level Success

    # Save API key to separate file for distribution
    $apiKeyFile = Join-Path $InstallPath "api_key.txt"
    Set-Content -Path $apiKeyFile -Value $APIKey
    Write-Log "✓ API key saved to: $apiKeyFile" -Level Success

    Write-Log ""
    Write-Log "===========================================================" -Level Success
    Write-Log "  Configuration Summary" -Level Success
    Write-Log "===========================================================" -Level Success
    Write-Log ""
    Write-Log "Server LAN IP: $ServerIP" -Level Info
    Write-Log "API Port: $script:APIPort" -Level Info
    Write-Log "WebSocket Port: $script:WebSocketPort" -Level Info
    Write-Log "Dashboard Port: $script:DashboardPort" -Level Info
    Write-Log "API Key: $APIKey" -Level Info
    Write-Log ""
    Write-Log "Configuration files:" -Level Info
    Write-Log "  - $configPath" -Level Info
    Write-Log "  - $envPath" -Level Info
    Write-Log "  - $apiKeyFile" -Level Info
    Write-Log ""
}

#endregion

#region Service Installation

function Install-Service {
    Write-Log "===========================================================" -Level Info
    Write-Log "  Windows Service Installation" -Level Info
    Write-Log "===========================================================" -Level Info
    Write-Log ""

    $repoPath = Join-Path $InstallPath "mcp-orchestrator"
    $pythonExe = Join-Path $repoPath "venv\Scripts\python.exe"
    $scriptPath = Join-Path $repoPath "api\run_api.py"
    $serviceName = "GiljoAI-MCP"

    if ($DryRun) {
        Write-Log "[DRY RUN] Would install Windows service: $serviceName" -Level Info
        return
    }

    # Check if service already exists
    $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Log "Service already exists. Stopping and removing..." -Level Info
        Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $serviceName | Out-Null
        Start-Sleep -Seconds 2
    }

    # Check for NSSM (Non-Sucking Service Manager)
    $nssmPath = "C:\nssm\nssm.exe"
    if (-not (Test-Path $nssmPath)) {
        Write-Log "NSSM not found. Downloading..." -Level Info
        try {
            $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
            $nssmZip = "$env:TEMP\nssm.zip"
            Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip -UseBasicParsing

            Expand-Archive -Path $nssmZip -DestinationPath $env:TEMP -Force
            $nssmExe = Get-ChildItem -Path $env:TEMP -Recurse -Filter "nssm.exe" | Where-Object { $_.Directory.Name -eq "win64" } | Select-Object -First 1

            if (-not $nssmExe) {
                throw "NSSM executable not found in archive"
            }

            New-Item -ItemType Directory -Path "C:\nssm" -Force | Out-Null
            Copy-Item -Path $nssmExe.FullName -Destination $nssmPath -Force

            Write-Log "✓ NSSM installed to C:\nssm\" -Level Success
        } catch {
            Write-Log "WARNING: Failed to download NSSM. Manual service creation may be required." -Level Warning
            Write-Log "Download from: https://nssm.cc/download and install to C:\nssm\" -Level Info
            return
        }
    }

    # Install service with NSSM
    Write-Log "Installing Windows service..." -Level Info
    try {
        & $nssmPath install $serviceName $pythonExe $scriptPath | Out-Null
        & $nssmPath set $serviceName Description "GiljoAI MCP Orchestration Server" | Out-Null
        & $nssmPath set $serviceName Start SERVICE_AUTO_START | Out-Null
        & $nssmPath set $serviceName AppDirectory $repoPath | Out-Null
        & $nssmPath set $serviceName AppStdout "$repoPath\logs\service.log" | Out-Null
        & $nssmPath set $serviceName AppStderr "$repoPath\logs\service-error.log" | Out-Null

        Write-Log "✓ Service installed" -Level Success

        # Start service
        Write-Log "Starting GiljoAI MCP service..." -Level Info
        Start-Service -Name $serviceName
        Start-Sleep -Seconds 3

        $service = Get-Service -Name $serviceName
        if ($service.Status -eq 'Running') {
            Write-Log "✓ Service started successfully" -Level Success
        } else {
            Write-Log "WARNING: Service installed but not running. Check logs." -Level Warning
        }
    } catch {
        Write-Log "ERROR: Service installation failed: $_" -Level Error
    }

    Write-Log ""
}

#endregion

#region Validation

function Test-Deployment {
    Write-Log "===========================================================" -Level Info
    Write-Log "  Deployment Validation" -Level Info
    Write-Log "===========================================================" -Level Info
    Write-Log ""

    if ($DryRun) {
        Write-Log "[DRY RUN] Would validate deployment" -Level Info
        return
    }

    $serverIP = Get-LocalIPAddress

    # Test localhost API
    Write-Log "Testing API endpoint (localhost)..." -Level Info
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$script:APIPort/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Log "✓ API accessible on localhost" -Level Success
        } else {
            Write-Log "WARNING: API returned status code: $($response.StatusCode)" -Level Warning
        }
    } catch {
        Write-Log "ERROR: API not accessible on localhost: $_" -Level Error
    }

    # Test LAN IP API
    Write-Log "Testing API endpoint (LAN IP: $serverIP)..." -Level Info
    try {
        $response = Invoke-WebRequest -Uri "http://${serverIP}:$script:APIPort/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Log "✓ API accessible on LAN IP" -Level Success
        } else {
            Write-Log "WARNING: API returned status code: $($response.StatusCode)" -Level Warning
        }
    } catch {
        Write-Log "ERROR: API not accessible on LAN IP: $_" -Level Error
        Write-Log "  Check firewall rules and network configuration" -Level Info
    }

    # Test service status
    Write-Log "Checking service status..." -Level Info
    try {
        $service = Get-Service -Name "GiljoAI-MCP"
        Write-Log "Service Status: $($service.Status)" -Level Info
        if ($service.Status -eq 'Running') {
            Write-Log "✓ Service is running" -Level Success
        } else {
            Write-Log "WARNING: Service is not running: $($service.Status)" -Level Warning
        }
    } catch {
        Write-Log "WARNING: Unable to check service status: $_" -Level Warning
    }

    # Test PostgreSQL
    Write-Log "Checking PostgreSQL service..." -Level Info
    try {
        $pgService = Get-Service -Name "postgresql-x64-$script:PostgreSQLVersion"
        Write-Log "PostgreSQL Status: $($pgService.Status)" -Level Info
        if ($pgService.Status -eq 'Running') {
            Write-Log "✓ PostgreSQL is running" -Level Success
        } else {
            Write-Log "WARNING: PostgreSQL is not running: $($pgService.Status)" -Level Warning
        }
    } catch {
        Write-Log "WARNING: Unable to check PostgreSQL status: $_" -Level Warning
    }

    Write-Log ""
}

#endregion

#region Main Execution

function Main {
    try {
        # Create log file
        New-Item -ItemType File -Path $script:LogFile -Force | Out-Null

        # Run deployment steps
        Test-Prerequisites
        Install-PostgreSQL
        Configure-Firewall
        Install-GiljoAI
        Configure-GiljoAI
        Install-Service
        Test-Deployment

        # Final summary
        Write-Log "===========================================================" -Level Success
        Write-Log "  Deployment Complete!" -Level Success
        Write-Log "===========================================================" -Level Success
        Write-Log ""
        Write-Log "Next Steps:" -Level Info
        Write-Log "1. Access the dashboard: http://$(Get-LocalIPAddress):$script:DashboardPort" -Level Info
        Write-Log "2. Distribute API key to team members (see: $InstallPath\api_key.txt)" -Level Info
        Write-Log "3. Update client configurations with server IP" -Level Info
        Write-Log "4. Test from another machine on the LAN" -Level Info
        Write-Log "5. Review security checklist (docs/deployment/LAN_SECURITY_CHECKLIST.md)" -Level Info
        Write-Log ""
        Write-Log "Log file: $script:LogFile" -Level Info
        Write-Log ""
        Write-Log "For support, see: https://github.com/giljoai/mcp-orchestrator/issues" -Level Info
        Write-Log ""

    } catch {
        Write-Log "FATAL ERROR: Deployment failed: $_" -Level Error
        Write-Log "Check log file for details: $script:LogFile" -Level Error
        exit 1
    }
}

# Execute main function
Main

#endregion
