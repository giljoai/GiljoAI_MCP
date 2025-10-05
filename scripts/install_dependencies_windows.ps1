# GiljoAI MCP - Windows Dependency Installer
# Automated installation of PostgreSQL, Python, and Node.js on Windows
# Run as Administrator

param(
    [switch]$SkipPostgreSQL,
    [switch]$SkipPython,
    [switch]$SkipNodeJS,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================================="  -ForegroundColor Cyan
Write-Host "  GiljoAI MCP - Windows Dependency Installer" -ForegroundColor Cyan
Write-Host "=========================================================="  -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Some operations may fail without admin privileges" -ForegroundColor Yellow
    Write-Host ""
}

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to check if winget is available
function Test-Winget {
    return Test-Command "winget"
}

# PostgreSQL Installation
if (-not $SkipPostgreSQL) {
    Write-Host "Checking PostgreSQL..." -ForegroundColor Green
    
    if (Test-Command "psql") {
        $version = psql --version
        Write-Host "  PostgreSQL already installed: $version" -ForegroundColor Gray
    } else {
        Write-Host "  PostgreSQL not found. Installing..." -ForegroundColor Yellow
        
        if (Test-Winget) {
            if (-not $DryRun) {
                Write-Host "  Installing via winget..." -ForegroundColor Gray
                winget install --id PostgreSQL.PostgreSQL.18 --silent --accept-package-agreements --accept-source-agreements
            } else {
                Write-Host "  [DRY RUN] Would install: winget install PostgreSQL.PostgreSQL.18" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ERROR: winget not available" -ForegroundColor Red
            Write-Host "  Please install PostgreSQL manually from:" -ForegroundColor Red
            Write-Host "  https://www.postgresql.org/download/windows/" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Python Installation
if (-not $SkipPython) {
    Write-Host "Checking Python..." -ForegroundColor Green
    
    if (Test-Command "python") {
        $version = python --version
        Write-Host "  Python already installed: $version" -ForegroundColor Gray
        
        # Check if Python 3.11+
        $pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $major, $minor = $pythonVersion.Split('.')
        if ([int]$major -eq 3 -and [int]$minor -ge 11) {
            Write-Host "  Python version is compatible (>=3.11)" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Python 3.11+ required, found $pythonVersion" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Python not found. Installing..." -ForegroundColor Yellow
        
        if (Test-Winget) {
            if (-not $DryRun) {
                Write-Host "  Installing via winget..." -ForegroundColor Gray
                winget install --id Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
            } else {
                Write-Host "  [DRY RUN] Would install: winget install Python.Python.3.13" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ERROR: winget not available" -ForegroundColor Red
            Write-Host "  Please install Python manually from:" -ForegroundColor Red
            Write-Host "  https://www.python.org/downloads/" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Node.js Installation
if (-not $SkipNodeJS) {
    Write-Host "Checking Node.js..." -ForegroundColor Green
    
    if (Test-Command "node") {
        $version = node --version
        Write-Host "  Node.js already installed: $version" -ForegroundColor Gray
    } else {
        Write-Host "  Node.js not found. Installing..." -ForegroundColor Yellow
        
        if (Test-Winget) {
            if (-not $DryRun) {
                Write-Host "  Installing via winget..." -ForegroundColor Gray
                winget install --id OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
            } else {
                Write-Host "  [DRY RUN] Would install: winget install OpenJS.NodeJS.LTS" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ERROR: winget not available" -ForegroundColor Red
            Write-Host "  Please install Node.js manually from:" -ForegroundColor Red
            Write-Host "  https://nodejs.org/" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Final verification
Write-Host "=========================================================="  -ForegroundColor Cyan
Write-Host "  Verifying Installations" -ForegroundColor Cyan
Write-Host "=========================================================="  -ForegroundColor Cyan
Write-Host ""

$allGood = $true

if (-not $SkipPostgreSQL) {
    if (Test-Command "psql") {
        $pgVersion = psql --version
        Write-Host "[OK] PostgreSQL: $pgVersion" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] PostgreSQL not found" -ForegroundColor Red
        $allGood = $false
    }
}

if (-not $SkipPython) {
    if (Test-Command "python") {
        $pyVersion = python --version
        Write-Host "[OK] Python: $pyVersion" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Python not found" -ForegroundColor Red
        $allGood = $false
    }
}

if (-not $SkipNodeJS) {
    if (Test-Command "node") {
        $nodeVersion = node --version
        $npmVersion = npm --version
        Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
        Write-Host "[OK] npm: v$npmVersion" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Node.js not found" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""

if ($allGood) {
    Write-Host "All dependencies installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Restart your terminal to refresh PATH" -ForegroundColor Gray
    Write-Host "  2. Run: python installer/cli/install.py" -ForegroundColor Gray
    Write-Host ""
    exit 0
} else {
    Write-Host "Some dependencies failed to install" -ForegroundColor Red
    Write-Host "Please install missing dependencies manually" -ForegroundColor Red
    Write-Host ""
    exit 1
}
