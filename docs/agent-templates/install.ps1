# GiljoAI Agent Template Installer (PowerShell)
# Cross-platform installation script for agent templates

param(
    [string]$InstallType = "product"
)

$ErrorActionPreference = "Stop"

Write-Host "GiljoAI Agent Template Installer" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check for API key
if (-not $env:GILJO_API_KEY) {
    Write-Host "Error: GILJO_API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Configure GiljoAI MCP first: Settings â†’ Integrations"
    exit 1
}

# Determine target directory
if ($InstallType -eq "personal") {
    $TARGET_DIR = Join-Path $env:USERPROFILE ".claude\agents"
} else {
    $TARGET_DIR = Join-Path (Get-Location) ".claude\agents"
}

# Server URL (templated)
$SERVER_URL = "http://10.1.0.164:7272"
$DOWNLOAD_URL = "$SERVER_URL/api/download/agent-templates.zip?active_only=true"

# Create backup if directory exists and has files
if ((Test-Path $TARGET_DIR) -and (Get-ChildItem $TARGET_DIR -ErrorAction SilentlyContinue)) {
    $TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
    $BACKUP_DIR = "${TARGET_DIR}_backup_${TIMESTAMP}"

    Write-Host "Creating backup: $BACKUP_DIR" -ForegroundColor Yellow
    Copy-Item -Path $TARGET_DIR -Destination $BACKUP_DIR -Recurse
}

# Create temp directory
$TEMP_DIR = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null

try {
    Write-Host "Downloading agent templates..." -ForegroundColor Yellow

    # Download ZIP file
    $ZIP_PATH = Join-Path $TEMP_DIR "templates.zip"
    $headers = @{
        "X-API-Key" = $env:GILJO_API_KEY
    }

    Invoke-WebRequest -Uri $DOWNLOAD_URL -Headers $headers -OutFile $ZIP_PATH

    # Create target directory
    New-Item -ItemType Directory -Path $TARGET_DIR -Force | Out-Null

    Write-Host "Installing to $TARGET_DIR..." -ForegroundColor Yellow

    # Extract ZIP
    Expand-Archive -Path $ZIP_PATH -DestinationPath $TARGET_DIR -Force

    Write-Host ""
    Write-Host "âœ… Installation complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installed templates:"
    Get-ChildItem -Path $TARGET_DIR -Filter "*.md" | ForEach-Object {
        Write-Host "  - $($_.Name)"
    }
    Write-Host ""
    Write-Host "Target: $TARGET_DIR"

} finally {
    # Clean up temp directory
    Remove-Item -Path $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
}
