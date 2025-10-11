# GiljoAI MCP PostgreSQL Configuration Restoration Script for Windows
# This is a template - actual scripts are generated during installation
#
# INSTRUCTIONS:
# 1. Open PowerShell as Administrator
# 2. Navigate to the directory containing this script
# 3. Run: .\restore_pg_config.ps1
#
# This script will:
# - Stop PostgreSQL service
# - Restore postgresql.conf from backup
# - Restore pg_hba.conf from backup
# - Restart PostgreSQL service

param(
    [Parameter(Mandatory=$false)]
    [string]$BackupDir,

    [Parameter(Mandatory=$false)]
    [string]$ConfigDir
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "   GiljoAI MCP - PostgreSQL Configuration Restoration" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

# Function to find PostgreSQL service
function Get-PostgreSQLService {
    $services = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($services) {
        return $services | Select-Object -First 1
    }
    return $null
}

# Function to find backup directory
function Find-BackupDirectory {
    $installerBackups = "installer\backups\postgresql"

    if (Test-Path $installerBackups) {
        $latestBackup = Get-ChildItem -Path $installerBackups -Directory |
                        Sort-Object Name -Descending |
                        Select-Object -First 1

        if ($latestBackup) {
            return $latestBackup.FullName
        }
    }

    return $null
}

# Function to find PostgreSQL config directory
function Find-PostgreSQLConfigDir {
    $candidatePaths = @(
        "$env:PROGRAMFILES\PostgreSQL\18\data",
        "$env:PROGRAMFILES\PostgreSQL\17\data",
        "$env:PROGRAMFILES\PostgreSQL\16\data",
        "$env:PROGRAMFILES\PostgreSQL\15\data",
        "$env:PROGRAMFILES\PostgreSQL\14\data",
        "C:\PostgreSQL\data"
    )

    foreach ($path in $candidatePaths) {
        if ((Test-Path $path) -and (Test-Path "$path\postgresql.conf")) {
            return $path
        }
    }

    return $null
}

# Determine backup directory
if (-not $BackupDir) {
    Write-Host "Searching for backup directory..." -ForegroundColor Yellow
    $BackupDir = Find-BackupDirectory

    if (-not $BackupDir) {
        Write-Host "ERROR: No backup directory found!" -ForegroundColor Red
        Write-Host "Please specify backup directory with -BackupDir parameter" -ForegroundColor Red
        exit 1
    }

    Write-Host "  Found backup: $BackupDir" -ForegroundColor Green
}

# Determine config directory
if (-not $ConfigDir) {
    Write-Host "Searching for PostgreSQL configuration directory..." -ForegroundColor Yellow
    $ConfigDir = Find-PostgreSQLConfigDir

    if (-not $ConfigDir) {
        Write-Host "ERROR: PostgreSQL configuration directory not found!" -ForegroundColor Red
        Write-Host "Please specify config directory with -ConfigDir parameter" -ForegroundColor Red
        exit 1
    }

    Write-Host "  Found config: $ConfigDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Backup directory: $BackupDir" -ForegroundColor Gray
Write-Host "  Config directory: $ConfigDir" -ForegroundColor Gray
Write-Host ""

# Verify backup files exist
$postgresqlBackup = Join-Path $BackupDir "postgresql.conf"
$hbaBackup = Join-Path $BackupDir "pg_hba.conf"

if (-not (Test-Path $postgresqlBackup)) {
    Write-Host "ERROR: postgresql.conf backup not found at $postgresqlBackup" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $hbaBackup)) {
    Write-Host "ERROR: pg_hba.conf backup not found at $hbaBackup" -ForegroundColor Red
    exit 1
}

# Verify config directory exists
if (-not (Test-Path $ConfigDir)) {
    Write-Host "ERROR: Configuration directory not found: $ConfigDir" -ForegroundColor Red
    exit 1
}

# Confirm restoration
Write-Host "WARNING: This will restore PostgreSQL configuration files to their backed-up state." -ForegroundColor Yellow
Write-Host "         Current server mode settings will be lost." -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Do you want to proceed? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Restoration cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Stopping PostgreSQL service..." -ForegroundColor Yellow

$pgService = Get-PostgreSQLService

if ($pgService) {
    try {
        Stop-Service -Name $pgService.Name -Force
        Start-Sleep -Seconds 2
        Write-Host "  Service '$($pgService.Name)' stopped" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING: Could not stop service automatically: $_" -ForegroundColor Yellow
        Write-Host "  Please stop PostgreSQL service manually via services.msc" -ForegroundColor Yellow
        Read-Host "Press Enter when PostgreSQL is stopped"
    }
} else {
    Write-Host "  WARNING: PostgreSQL service not found" -ForegroundColor Yellow
    Write-Host "  Please ensure PostgreSQL is stopped before continuing" -ForegroundColor Yellow
    Read-Host "Press Enter when PostgreSQL is stopped"
}

Write-Host ""
Write-Host "Restoring configuration files..." -ForegroundColor Yellow

# Create backup of current files (before restoration)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$preRestoreBackup = Join-Path $BackupDir "pre_restore_$timestamp"
New-Item -ItemType Directory -Path $preRestoreBackup -Force | Out-Null

$currentPostgresql = Join-Path $ConfigDir "postgresql.conf"
$currentHba = Join-Path $ConfigDir "pg_hba.conf"

if (Test-Path $currentPostgresql) {
    Copy-Item -Path $currentPostgresql -Destination (Join-Path $preRestoreBackup "postgresql.conf") -Force
    Write-Host "  Current postgresql.conf backed up" -ForegroundColor Gray
}

if (Test-Path $currentHba) {
    Copy-Item -Path $currentHba -Destination (Join-Path $preRestoreBackup "pg_hba.conf") -Force
    Write-Host "  Current pg_hba.conf backed up" -ForegroundColor Gray
}

# Restore files
try {
    Copy-Item -Path $postgresqlBackup -Destination $currentPostgresql -Force
    Write-Host "  Restored postgresql.conf" -ForegroundColor Green

    Copy-Item -Path $hbaBackup -Destination $currentHba -Force
    Write-Host "  Restored pg_hba.conf" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to restore configuration files: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting PostgreSQL service..." -ForegroundColor Yellow

if ($pgService) {
    try {
        Start-Service -Name $pgService.Name
        Start-Sleep -Seconds 2
        Write-Host "  Service '$($pgService.Name)' started" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING: Could not start service automatically: $_" -ForegroundColor Yellow
        Write-Host "  Please start PostgreSQL service manually via services.msc" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Please start PostgreSQL service manually via services.msc" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "   Configuration Restoration Complete!" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "PostgreSQL configuration files have been restored." -ForegroundColor Gray
Write-Host "Pre-restoration backup saved to: $preRestoreBackup" -ForegroundColor Gray
Write-Host ""
