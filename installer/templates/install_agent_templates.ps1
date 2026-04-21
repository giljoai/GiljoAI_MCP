# GiljoAI Agent Template Installer (PowerShell)
# Cross-platform installation script for agent templates
# Supports: Claude Code, Gemini CLI, Codex CLI

param(
    [ValidateSet("claude_code", "gemini_cli", "codex_cli")]
    [string]$Platform = "claude_code",

    [string]$Model = "",

    [ValidateSet("project", "user")]
    [string]$Scope = "project"
)

$ErrorActionPreference = "Stop"

Write-Host "GiljoAI Agent Template Installer" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "  Platform: $Platform"
Write-Host "  Scope:    $Scope"
if ($Model) {
    Write-Host "  Model:    $Model"
}
Write-Host ""

# ---------------------------------------------------------------------------
# Check for API key
# ---------------------------------------------------------------------------
if (-not $env:GILJO_API_KEY) {
    Write-Host "Error: GILJO_API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Configure GiljoAI MCP first: Settings -> Integrations"
    exit 1
}

# ---------------------------------------------------------------------------
# Derive target directory from platform + scope
# ---------------------------------------------------------------------------
switch ($Platform) {
    "claude_code" { $AgentsSubdir = ".claude\agents" }
    "gemini_cli"  { $AgentsSubdir = ".gemini\agents" }
    "codex_cli"   { $AgentsSubdir = ".codex\agents" }
}

if ($Scope -eq "user") {
    $TARGET_DIR = Join-Path $env:USERPROFILE $AgentsSubdir
} else {
    $TARGET_DIR = Join-Path (Get-Location) $AgentsSubdir
}

# ---------------------------------------------------------------------------
# Server URL (templated at export time)
# ---------------------------------------------------------------------------
$SERVER_URL = "{{SERVER_URL}}"
$DOWNLOAD_URL = "$SERVER_URL/api/download/agent-templates.zip?platform=$Platform&active_only=true"

# ---------------------------------------------------------------------------
# Backup existing agent files
# ---------------------------------------------------------------------------
if ((Test-Path $TARGET_DIR) -and (Get-ChildItem $TARGET_DIR -ErrorAction SilentlyContinue)) {
    $TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
    $BACKUP_DIR = "${TARGET_DIR}_backup_${TIMESTAMP}"

    Write-Host "Creating backup: $BACKUP_DIR" -ForegroundColor Yellow
    Copy-Item -Path $TARGET_DIR -Destination $BACKUP_DIR -Recurse
}

# ---------------------------------------------------------------------------
# Download and extract
# ---------------------------------------------------------------------------
$TEMP_DIR = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null

try {
    Write-Host "Downloading agent templates..." -ForegroundColor Yellow

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

    # Remove bundled install scripts from target (they belong in installer/, not agents/)
    Remove-Item -Path (Join-Path $TARGET_DIR "install.sh") -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $TARGET_DIR "install.ps1") -Force -ErrorAction SilentlyContinue

    # -----------------------------------------------------------------------
    # Patch model in extracted files (if -Model was provided)
    # -----------------------------------------------------------------------
    if ($Model) {
        Write-Host "Patching model to: $Model" -ForegroundColor Yellow
        # Markdown files (Claude Code, Gemini CLI): model: VALUE in YAML frontmatter
        Get-ChildItem -Path $TARGET_DIR -Filter "*.md" -ErrorAction SilentlyContinue | ForEach-Object {
            $content = (Get-Content $_.FullName -Raw)
            $content = $content -replace '(?m)^model: .*', "model: $Model"
            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($_.FullName, $content, $utf8NoBom)
        }
        # TOML files (Codex CLI): model = "VALUE"
        Get-ChildItem -Path $TARGET_DIR -Filter "*.toml" -ErrorAction SilentlyContinue | ForEach-Object {
            $content = (Get-Content $_.FullName -Raw)
            $content = $content -replace '(?m)^model = .*', "model = `"$Model`""
            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($_.FullName, $content, $utf8NoBom)
        }
    }

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    Write-Host ""
    Write-Host "Installation complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installed templates:"
    Get-ChildItem -Path $TARGET_DIR -File | ForEach-Object {
        Write-Host "  - $($_.Name)"
    }
    Write-Host ""
    Write-Host "Target: $TARGET_DIR"

    # -----------------------------------------------------------------------
    # Platform-specific post-install instructions
    # -----------------------------------------------------------------------
    Write-Host ""
    switch ($Platform) {
        "claude_code" {
            Write-Host "Restart Claude Code to load agents."
        }
        "gemini_cli" {
            Write-Host "Ensure experimental.enableAgents is true in ~/.gemini/settings.json."
            Write-Host "Restart Gemini CLI to load agents."
        }
        "codex_cli" {
            Write-Host "Register agents in ~/.codex/config.toml under [agents.gil-*] sections."
            Write-Host "Enable [features] multi_agent = true."
            Write-Host "Restart Codex CLI to load agents."
        }
    }

} finally {
    # Clean up temp directory
    Remove-Item -Path $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
}
