# GiljoAI MCP Distribution Package Creator
# Creates a clean distribution package ready for users

param(
    [string]$OutputDir = ".\dist",
    [string]$PackageName = "giljo-mcp",
    [switch]$IncludeDevTools = $false
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "GiljoAI MCP Distribution Package Creator" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Create timestamp for package version
$timestamp = Get-Date -Format "yyyyMMdd-HHmm"
$packageDir = Join-Path $OutputDir "$PackageName-$timestamp"

Write-Host "[1/6] Creating distribution directory..." -ForegroundColor Yellow
if (Test-Path $packageDir) {
    Remove-Item -Path $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null

Write-Host "[2/6] Copying core application files..." -ForegroundColor Yellow

# Core directories
$coreDirs = @("src", "api", "frontend", "tests", "scripts", "examples")
foreach ($dir in $coreDirs) {
    if (Test-Path $dir) {
        Write-Host "  - Copying $dir/"
        Copy-Item -Path $dir -Destination $packageDir -Recurse -Force `
            -Exclude "__pycache__", "*.pyc", ".pytest_cache", "node_modules", ".git"
    }
}

Write-Host "[3/6] Copying configuration files..." -ForegroundColor Yellow

# Essential files
$essentialFiles = @(
    "config.yaml.example",
    ".env.example",
    "requirements.txt",
    "setup.py",
    "pyproject.toml",
    "INSTALL.md",
    "README.md",
    "quickstart.bat",
    "quickstart.sh",
    "MANIFEST.txt"
)

foreach ($file in $essentialFiles) {
    if (Test-Path $file) {
        Write-Host "  - Copying $file"
        Copy-Item -Path $file -Destination $packageDir -Force
    }
}

# Optional files
if (Test-Path "alembic.ini") {
    Copy-Item -Path "alembic.ini" -Destination $packageDir -Force
}

if ($IncludeDevTools) {
    Write-Host "[4/6] Including development tools..." -ForegroundColor Yellow
    $devFiles = @(".ruff.toml", ".eslintrc.json", ".prettierrc", "mypy.ini")
    foreach ($file in $devFiles) {
        if (Test-Path $file) {
            Write-Host "  - Including $file"
            Copy-Item -Path $file -Destination $packageDir -Force
        }
    }
} else {
    Write-Host "[4/6] Skipping development tools (use -IncludeDevTools to include)" -ForegroundColor Gray
}

Write-Host "[5/6] Cleaning up package..." -ForegroundColor Yellow

# Remove Python cache directories
Get-ChildItem -Path $packageDir -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force
Get-ChildItem -Path $packageDir -Filter "*.pyc" -Recurse | Remove-Item -Force
Get-ChildItem -Path $packageDir -Filter ".pytest_cache" -Recurse -Directory | Remove-Item -Recurse -Force

# Remove any accidentally included local files
$excludePatterns = @("*.log", "*.db", "*.db-shm", "*.db-wal", ".env", "config.yaml")
foreach ($pattern in $excludePatterns) {
    Get-ChildItem -Path $packageDir -Filter $pattern -Recurse | Remove-Item -Force
}

Write-Host "[6/6] Creating ZIP archive..." -ForegroundColor Yellow
$zipPath = Join-Path $OutputDir "$PackageName-$timestamp.zip"

# Create ZIP file
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($packageDir, $zipPath)

# Calculate package size
$zipSize = (Get-Item $zipPath).Length / 1MB
$formattedSize = "{0:N2}" -f $zipSize

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "Distribution Package Created Successfully!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Package: $zipPath" -ForegroundColor White
Write-Host "Size: $formattedSize MB" -ForegroundColor White
Write-Host ""
Write-Host "Distribution directory: $packageDir" -ForegroundColor Gray
Write-Host ""
Write-Host "To test the package:" -ForegroundColor Cyan
Write-Host "1. Extract $zipPath to a new location" -ForegroundColor White
Write-Host "2. Run quickstart.bat (Windows) or quickstart.sh (Mac/Linux)" -ForegroundColor White
Write-Host "3. Follow the instructions in INSTALL.md" -ForegroundColor White
Write-Host ""