# GiljoAI MCP Coding Orchestrator - One-Liner Installation Script
# For Windows (PowerShell)
# Usage: irm https://install.giljo.ai/install.ps1 | iex

# Requires PowerShell 5.1 or higher

$ErrorActionPreference = "Stop"

# Configuration
$GITHUB_REPO = "giljoai/GiljoAI_MCP"
$DEFAULT_INSTALL_DIR = "C:\GiljoAI_MCP"
$MIN_PYTHON_VERSION = [Version]"3.11"
$MIN_NODE_VERSION = 18
$MIN_DISK_SPACE_MB = 2048
$LOG_FILE = "$env:USERPROFILE\giljoai_install.log"

# Function to print colored messages
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to log messages
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] $Message" | Out-File -FilePath $LOG_FILE -Append
}

# Display banner
function Show-Banner {
    Write-Host ""
    Write-Host "╔═════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║       GiljoAI MCP Coding Orchestrator - Installation                ║" -ForegroundColor Cyan
    Write-Host "║       Multi-Agent Orchestration Platform                            ║" -ForegroundColor Cyan
    Write-Host "╚═════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# Check if command exists
function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Check Python version
function Test-Python {
    Write-Info "Checking Python installation..."
    Write-Log "Checking Python installation"
    
    if (-not (Test-CommandExists "python")) {
        Write-Error-Custom "Python is not installed"
        Write-Host ""
        Write-Host "Please install Python 3.11 or higher:"
        Write-Host "  Download: https://www.python.org/downloads/"
        Write-Host "  Note: Check 'Add Python to PATH' during installation"
        Write-Host ""
        Write-Log "ERROR: Python not found"
        exit 1
    }
    
    $pythonVersionOutput = python --version 2>&1
    $versionMatch = $pythonVersionOutput -match "Python (\d+\.\d+\.\d+)"
    
    if (-not $versionMatch) {
        Write-Error-Custom "Could not determine Python version"
        Write-Log "ERROR: Could not parse Python version"
        exit 1
    }
    
    $pythonVersion = [Version]$matches[1]
    
    if ($pythonVersion -lt $MIN_PYTHON_VERSION) {
        Write-Error-Custom "Python $pythonVersion is installed, but version $MIN_PYTHON_VERSION or higher is required"
        Write-Host ""
        Write-Host "Please upgrade Python:"
        Write-Host "  https://www.python.org/downloads/"
        Write-Host ""
        Write-Log "ERROR: Python version $pythonVersion < $MIN_PYTHON_VERSION"
        exit 1
    }
    
    Write-Success "Python $pythonVersion detected"
    Write-Log "Python $pythonVersion detected"
}

# Prompt for PostgreSQL settings (password + db name) before install
function Get-PostgreSQLSettings {
    Write-Host ""
    Write-Host "  [PostgreSQL Configuration]" -ForegroundColor Cyan
    Write-Host ""

    # A) Admin password
    Write-Host "  Choose a password for the PostgreSQL 'postgres' admin user."
    Write-Host "  This will be used during installation and by the application." -ForegroundColor Gray
    Write-Host ""
    do {
        $script:PG_PASSWORD = Read-Host "  PostgreSQL admin password" -AsSecureString
        $script:PG_PASSWORD_CONFIRM = Read-Host "  Confirm password" -AsSecureString

        $pw1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($script:PG_PASSWORD))
        $pw2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($script:PG_PASSWORD_CONFIRM))

        if ([string]::IsNullOrWhiteSpace($pw1)) {
            Write-Warning "Password cannot be empty."
            $passwordOk = $false
        }
        elseif ($pw1 -ne $pw2) {
            Write-Warning "Passwords do not match. Try again."
            $passwordOk = $false
        }
        else {
            $passwordOk = $true
        }
    } while (-not $passwordOk)

    $script:PG_PASSWORD_PLAIN = $pw1
    Write-Success "PostgreSQL password set"
    Write-Log "PostgreSQL password configured"

    # B) Database name
    Write-Host ""
    Write-Host "  Choose the database name for GiljoAI MCP."
    Write-Host "  Change this only if running multiple installations on the same server." -ForegroundColor Gray
    $dbInput = Read-Host "  Database name [giljo_mcp]"
    if ([string]::IsNullOrWhiteSpace($dbInput)) {
        $script:PG_DB_NAME = "giljo_mcp"
    }
    else {
        $script:PG_DB_NAME = $dbInput
    }
    Write-Success "Database name: $script:PG_DB_NAME"
    Write-Log "Database name: $script:PG_DB_NAME"
}

# Install PostgreSQL via winget
function Install-PostgreSQL {
    Write-Info "Installing PostgreSQL via winget..."
    Write-Log "Installing PostgreSQL via winget"

    # Check winget is available
    if (-not (Test-CommandExists "winget")) {
        Write-Error-Custom "winget is not available on this system"
        Write-Host ""
        Write-Host "  Please install PostgreSQL manually:"
        Write-Host "    https://www.postgresql.org/download/windows/"
        Write-Host ""
        Write-Log "ERROR: winget not found, cannot auto-install PostgreSQL"
        exit 1
    }

    # Install with the user-provided superuser password
    try {
        $installArgs = @(
            "install", "PostgreSQL.PostgreSQL.17",
            "--silent",
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--override", "--superpassword `"$script:PG_PASSWORD_PLAIN`" --serverport 5432 --enable-components server,commandlinetools"
        )
        $proc = Start-Process -FilePath "winget" -ArgumentList $installArgs -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -ne 0) {
            throw "winget exited with code $($proc.ExitCode)"
        }
        Write-Success "PostgreSQL installed successfully"
        Write-Log "PostgreSQL winget install completed"
    }
    catch {
        Write-Error-Custom "PostgreSQL installation failed: $_"
        Write-Host ""
        Write-Host "  You can install manually from:"
        Write-Host "    https://www.postgresql.org/download/windows/"
        Write-Host ""
        Write-Log "ERROR: PostgreSQL install failed - $_"
        exit 1
    }

    # Add PostgreSQL bin to PATH for this session
    $pgPaths = @(
        "C:\Program Files\PostgreSQL\17\bin",
        "C:\Program Files\PostgreSQL\16\bin",
        "C:\Program Files\PostgreSQL\15\bin"
    )
    foreach ($pgPath in $pgPaths) {
        if (Test-Path $pgPath) {
            $env:PATH = "$pgPath;$env:PATH"
            Write-Log "Added $pgPath to session PATH"
            break
        }
    }
}

# Check PostgreSQL
function Test-PostgreSQL {
    Write-Info "Checking PostgreSQL installation..."
    Write-Log "Checking PostgreSQL installation"

    if (-not (Test-CommandExists "psql")) {
        Write-Warning "PostgreSQL not found — will install automatically"
        Write-Log "PostgreSQL not found, prompting for settings before install"

        # Collect settings first, then install
        Get-PostgreSQLSettings
        Install-PostgreSQL

        # Verify it's now available
        if (-not (Test-CommandExists "psql")) {
            Write-Error-Custom "PostgreSQL was installed but psql is not in PATH"
            Write-Host ""
            Write-Host "  Try restarting your terminal and running the installer again."
            Write-Host ""
            Write-Log "ERROR: psql still not found after install"
            exit 1
        }
    }

    $pgVersionOutput = psql --version 2>&1
    $versionMatch = $pgVersionOutput -match "(\d+)\.(\d+)"

    if (-not $versionMatch) {
        Write-Error-Custom "Could not determine PostgreSQL version"
        Write-Log "ERROR: Could not parse PostgreSQL version"
        exit 1
    }

    $pgMajorVersion = [int]$matches[1]

    if ($pgMajorVersion -lt 14) {
        Write-Error-Custom "PostgreSQL $pgMajorVersion is installed, but version 14 or higher is required"
        Write-Host ""
        Write-Host "  Please upgrade PostgreSQL:"
        Write-Host "    https://www.postgresql.org/download/windows/"
        Write-Host ""
        Write-Log "ERROR: PostgreSQL version $pgMajorVersion < 14"
        exit 1
    }

    Write-Success "PostgreSQL $pgMajorVersion detected"
    Write-Log "PostgreSQL $pgMajorVersion detected"
}

# Check Node.js
function Test-NodeJS {
    Write-Info "Checking Node.js installation..."
    Write-Log "Checking Node.js installation"
    
    if (-not (Test-CommandExists "node")) {
        Write-Error-Custom "Node.js is not installed"
        Write-Host ""
        Write-Host "Please install Node.js 18 or higher:"
        Write-Host "  Download: https://nodejs.org/"
        Write-Host "  Recommended: LTS version"
        Write-Host ""
        Write-Log "ERROR: Node.js not found"
        exit 1
    }
    
    $nodeVersionOutput = node --version 2>&1
    $versionMatch = $nodeVersionOutput -match "v(\d+)\.(\d+)\.(\d+)"
    
    if (-not $versionMatch) {
        Write-Error-Custom "Could not determine Node.js version"
        Write-Log "ERROR: Could not parse Node.js version"
        exit 1
    }
    
    $nodeMajorVersion = [int]$matches[1]
    
    if ($nodeMajorVersion -lt $MIN_NODE_VERSION) {
        Write-Error-Custom "Node.js v$nodeMajorVersion is installed, but v$MIN_NODE_VERSION or higher is required"
        Write-Host ""
        Write-Host "Please upgrade Node.js:"
        Write-Host "  https://nodejs.org/"
        Write-Host ""
        Write-Log "ERROR: Node.js version $nodeMajorVersion < $MIN_NODE_VERSION"
        exit 1
    }
    
    Write-Success "Node.js $(node --version) detected"
    Write-Log "Node.js $(node --version) detected"
}

# Check disk space
function Test-DiskSpace {
    Write-Info "Checking available disk space..."
    Write-Log "Checking disk space"
    
    $drive = (Get-Item $env:USERPROFILE).PSDrive
    $availableSpaceMB = [math]::Round($drive.Free / 1MB)
    
    if ($availableSpaceMB -lt $MIN_DISK_SPACE_MB) {
        Write-Error-Custom "Insufficient disk space: ${availableSpaceMB}MB available, ${MIN_DISK_SPACE_MB}MB required"
        Write-Host ""
        Write-Host "Please free up disk space and try again"
        Write-Host ""
        Write-Log "ERROR: Insufficient disk space: ${availableSpaceMB}MB < ${MIN_DISK_SPACE_MB}MB"
        exit 1
    }
    
    Write-Success "Sufficient disk space: ${availableSpaceMB}MB available"
    Write-Log "Disk space: ${availableSpaceMB}MB available"
}

# Check internet connectivity
function Test-Internet {
    Write-Info "Checking internet connectivity..."
    Write-Log "Checking internet connectivity"
    
    try {
        $response = Invoke-WebRequest -Uri "https://github.com" -Method Head -TimeoutSec 5 -UseBasicParsing
        Write-Success "Internet connection verified"
        Write-Log "Internet connection verified"
    }
    catch {
        Write-Error-Custom "Cannot reach GitHub. Please check your internet connection"
        Write-Host ""
        Write-Log "ERROR: No internet connectivity"
        exit 1
    }
}

# Prompt for installation directory
function Get-InstallDirectory {
    Write-Host ""
    Write-Info "Select installation directory"
    $userInput = Read-Host "Install directory [default: $DEFAULT_INSTALL_DIR]"
    
    if ([string]::IsNullOrWhiteSpace($userInput)) {
        $script:INSTALL_DIR = $DEFAULT_INSTALL_DIR
    }
    else {
        $script:INSTALL_DIR = $userInput
    }
    
    # Check if directory already exists
    if (Test-Path $script:INSTALL_DIR) {
        Write-Warning "Directory already exists: $script:INSTALL_DIR"
        $overwrite = Read-Host "Overwrite existing installation? [y/N]"
        
        if ($overwrite -notmatch '^[Yy]$') {
            Write-Info "Installation cancelled"
            exit 0
        }
        
        Write-Info "Removing existing installation..."
        Remove-Item -Path $script:INSTALL_DIR -Recurse -Force
    }
    
    Write-Success "Installation directory: $script:INSTALL_DIR"
    Write-Log "Installation directory: $script:INSTALL_DIR"
}

# Download latest release
function Get-LatestRelease {
    Write-Info "Downloading GiljoAI MCP Coding Orchestrator..."
    Write-Log "Downloading from GitHub: $GITHUB_REPO"
    
    $tempDir = Join-Path $env:TEMP "giljoai_install_$(Get-Random)"
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    $downloadUrl = "https://github.com/$GITHUB_REPO/archive/refs/heads/master.zip"
    $zipPath = Join-Path $tempDir "giljoai-mcp.zip"
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        Write-Success "Downloaded successfully"
        Write-Log "Download complete"
    }
    catch {
        Write-Error-Custom "Failed to download from GitHub"
        Write-Host ""
        Write-Host "Manual installation:"
        Write-Host "  git clone https://github.com/$GITHUB_REPO"
        Write-Host "  cd GiljoAI-MCP"
        Write-Host "  python install.py"
        Write-Host ""
        Write-Log "ERROR: Download failed - $_"
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        exit 1
    }
    
    # Extract archive
    Write-Info "Extracting files..."
    Write-Log "Extracting archive"
    
    try {
        Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force
        Write-Log "Archive extracted"
    }
    catch {
        Write-Error-Custom "Failed to extract archive"
        Write-Log "ERROR: Extraction failed - $_"
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        exit 1
    }
    
    # Move to installation directory
    $extractedDir = Join-Path $tempDir "GiljoAI-MCP-master"
    
    try {
        New-Item -ItemType Directory -Path $script:INSTALL_DIR -Force | Out-Null
        Copy-Item -Path "$extractedDir\*" -Destination $script:INSTALL_DIR -Recurse -Force
        Write-Success "Files extracted to $script:INSTALL_DIR"
        Write-Log "Extraction complete"
    }
    catch {
        Write-Error-Custom "Failed to copy files to installation directory"
        Write-Log "ERROR: Copy failed - $_"
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        exit 1
    }
    
    # Cleanup
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

# Verify installation
function Test-Installation {
    Write-Info "Verifying installation files..."
    Write-Log "Verifying installation"
    
    $requiredFiles = @(
        "install.py",
        "startup.py",
        "requirements.txt",
        "frontend\package.json",
        "api\app.py",
        "src\giljo_mcp\__init__.py"
    )
    
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $script:INSTALL_DIR $file
        if (-not (Test-Path $filePath)) {
            Write-Error-Custom "Missing required file: $file"
            Write-Log "ERROR: Missing file: $file"
            exit 1
        }
    }
    
    Write-Success "All required files present"
    Write-Log "Verification complete"
}

# Execute install.py
function Invoke-Installer {
    Write-Info "Starting interactive setup wizard..."
    Write-Host ""
    Write-Log "Executing install.py"
    
    Set-Location $script:INSTALL_DIR
    
    # Set environment variable to indicate scripted installation
    $env:GILJO_SCRIPTED_INSTALL = "true"

    try {
        python install.py
        Write-Log "install.py completed successfully"
    }
    catch {
        Write-Error-Custom "Installation failed during setup wizard"
        Write-Host ""
        Write-Host "Check logs:"
        Write-Host "  $LOG_FILE"
        Write-Host "  $script:INSTALL_DIR\logs\install.log"
        Write-Host ""
        Write-Log "ERROR: install.py failed - $_"
        exit 1
    }
}

# Show success message
function Show-Success {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║           Installation Complete!                        ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Success "GiljoAI MCP Coding Orchestrator installed successfully"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host ""
    Write-Host "  1. Start the server:"
    Write-Host "     cd $script:INSTALL_DIR"
    Write-Host "     python startup.py"
    Write-Host ""
    Write-Host "  2. Open your browser:"
    Write-Host "     http://localhost:7272"
    Write-Host ""
    Write-Host "  3. Complete first-time setup in the web interface"
    Write-Host ""
    Write-Host "For help: https://github.com/$GITHUB_REPO/blob/master/docs/README_FIRST.md"
    Write-Host ""
    Write-Log "Installation completed successfully"
}

# Main installation flow
function Main {
    # Initialize log file
    "GiljoAI MCP Installation Log - $(Get-Date)" | Out-File -FilePath $LOG_FILE
    
    # Show banner
    Show-Banner
    
    # Pre-flight checks
    Write-Info "Running pre-flight checks..."
    Write-Host ""
    Test-Python
    Test-PostgreSQL
    Test-NodeJS
    Test-DiskSpace
    Test-Internet
    Write-Host ""
    Write-Success "All pre-flight checks passed"
    Write-Host ""
    
    # User prompts
    Get-InstallDirectory
    
    # Download and extract
    Write-Host ""
    Get-LatestRelease
    
    # Verify installation
    Test-Installation
    
    # Execute install.py
    Write-Host ""
    Invoke-Installer
    
    # Success
    Show-Success
}

# Run main function
Main
