#Requires -Version 5.1

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

<#
.SYNOPSIS
    GiljoAI MCP -- Windows One-Liner Installer

.DESCRIPTION
    Downloads, verifies, and installs GiljoAI MCP from the latest GitHub release.
    Handles prerequisite checking/installation, SHA256 verification, environment
    setup, and first-run launch.

    Quick install:
        irm giljo.ai/install.ps1 | iex

    Customized install:
        .\install.ps1 -InstallDir "D:\GiljoAI" -SkipPrereqs

.PARAMETER InstallDir
    Installation directory. Defaults to $HOME\GiljoAI_MCP.

.PARAMETER SkipPrereqs
    Skip prerequisite checks and installation.

.PARAMETER Update
    Update an existing installation to the latest version.
#>

param(
    [string]$InstallDir = "",
    [switch]$SkipPrereqs,
    [switch]$Update
)

$ErrorActionPreference = 'Stop'

# Disable PowerShell's IWR/IRM progress bar — it slows downloads 5-10x on Win PS 5.1
$ProgressPreference = 'SilentlyContinue'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

$script:GITHUB_REPO       = "giljoai/GiljoAI_MCP"
$script:GITHUB_API_URL    = "https://api.github.com/repos/$script:GITHUB_REPO/releases/latest"
$script:DEFAULT_INSTALL   = $PWD.Path
$script:MIN_PYTHON_MAJOR  = 3
$script:MIN_PYTHON_MINOR  = 12
$script:MIN_NODE_MAJOR    = 22
$script:SERVER_PORT       = 7272
$script:BRAND_COLOR       = "Yellow"
$script:SUCCESS_COLOR     = "Green"
$script:ERROR_COLOR       = "Red"
$script:INFO_COLOR        = "Cyan"
$script:MUTED_COLOR       = "Gray"

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

function Write-Banner {
    Write-Host ""
    Write-Host "    GiljoAI MCP Community Edition" -ForegroundColor Yellow
    Write-Host "    Windows Installer" -ForegroundColor $script:MUTED_COLOR
    Write-Host ""
}

function Write-Phase {
    param([string]$Number, [string]$Title)
    Write-Host ""
    Write-Host "  [$Number/5] $Title" -ForegroundColor $script:BRAND_COLOR
    Write-Host "  $('-' * (6 + $Title.Length))" -ForegroundColor $script:MUTED_COLOR
}

function Write-Step {
    param([string]$Message)
    Write-Host "    > $Message" -ForegroundColor $script:INFO_COLOR
}

function Write-Ok {
    param([string]$Message)
    Write-Host "    [OK] $Message" -ForegroundColor $script:SUCCESS_COLOR
}

function Write-Warn {
    param([string]$Message)
    Write-Host "    [!] $Message" -ForegroundColor $script:BRAND_COLOR
}

function Write-Fail {
    param([string]$Message)
    Write-Host "    [FAIL] $Message" -ForegroundColor $script:ERROR_COLOR
}

function Exit-WithError {
    param([string]$Message)
    Write-Host ""
    Write-Fail $Message
    Write-Host ""
    throw $Message
}

function Test-CommandExists {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Get-ParsedVersion {
    <#
    .SYNOPSIS
        Parses a version string like "Python 3.12.4" or "v20.11.0" and returns
        major, minor as integers.
    #>
    param([string]$VersionString)

    if ($VersionString -match '(\d+)\.(\d+)') {
        return @{
            Major = [int]$Matches[1]
            Minor = [int]$Matches[2]
        }
    }
    return $null
}

function Refresh-PathEnv {
    <#
    .SYNOPSIS
        Reloads PATH from the registry so newly installed tools are visible
        without restarting the shell.
    #>
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path    = "$machinePath;$userPath"
}

# ---------------------------------------------------------------------------
# Phase 1 -- Prerequisites
# ---------------------------------------------------------------------------

function Test-Prerequisites {
    Write-Phase "1" "Checking prerequisites"

    $missing = @()

    # -- Python --
    Write-Step "Checking Python..."
    if (Test-CommandExists "python") {
        $pyVersionRaw = & python --version 2>&1
        $pyVersion = Get-ParsedVersion $pyVersionRaw
        if ($pyVersion -and
            ($pyVersion.Major -gt $script:MIN_PYTHON_MAJOR -or
            ($pyVersion.Major -eq $script:MIN_PYTHON_MAJOR -and $pyVersion.Minor -ge $script:MIN_PYTHON_MINOR))) {
            Write-Ok "Python $($pyVersion.Major).$($pyVersion.Minor) found"
        } else {
            Write-Warn "Python found but version too old: $pyVersionRaw (need $($script:MIN_PYTHON_MAJOR).$($script:MIN_PYTHON_MINOR)+)"
            $missing += "python"
        }
    } else {
        Write-Warn "Python not found"
        $missing += "python"
    }

    # -- Node.js --
    Write-Step "Checking Node.js..."
    if (Test-CommandExists "node") {
        $nodeVersionRaw = & node --version 2>&1
        $nodeVersion = Get-ParsedVersion $nodeVersionRaw
        if ($nodeVersion -and $nodeVersion.Major -ge $script:MIN_NODE_MAJOR) {
            Write-Ok "Node.js $($nodeVersion.Major).$($nodeVersion.Minor) found"
        } else {
            Write-Warn "Node.js found but version too old: $nodeVersionRaw (need $($script:MIN_NODE_MAJOR)+)"
            $missing += "node"
        }
    } else {
        Write-Warn "Node.js not found"
        $missing += "node"
    }

    # -- Git --
    Write-Step "Checking Git..."
    if (Test-CommandExists "git") {
        $gitVersionRaw = & git --version 2>&1
        Write-Ok "Git found: $gitVersionRaw"
    } else {
        Write-Warn "Git not found"
        $missing += "git"
    }

    # -- PostgreSQL --
    Write-Step "Checking PostgreSQL..."
    $pgFound = $false
    if (Test-CommandExists "pg_isready") {
        Write-Ok "PostgreSQL found (pg_isready available)"
        $pgFound = $true
    } else {
        # Check if PostgreSQL service is running
        $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        if ($pgService) {
            Write-Ok "PostgreSQL service found: $($pgService.DisplayName)"
            $pgFound = $true
        }
    }
    if (-not $pgFound) {
        Write-Warn "PostgreSQL not detected"
        $missing += "postgresql"
    }

    if ($missing.Count -eq 0) {
        Write-Ok "All prerequisites satisfied"
        return
    }

    # -- Install missing prerequisites --
    Write-Host ""
    Write-Step "Missing prerequisites: $($missing -join ', ')"

    $hasWinget = Test-CommandExists "winget"

    # Handle non-PostgreSQL items via winget
    $wingetItems = $missing | Where-Object { $_ -ne "postgresql" }

    if ($wingetItems.Count -gt 0) {
        if (-not $hasWinget) {
            Exit-WithError "winget is required to install missing prerequisites ($($wingetItems -join ', ')). Please install them manually or install winget first."
        }

        Write-Step "Installing missing packages via winget..."

        $wingetMap = @{
            "python" = "Python.Python.3.12"
            "node"   = "OpenJS.NodeJS.LTS"
            "git"    = "Git.Git"
        }

        foreach ($item in $wingetItems) {
            $packageId = $wingetMap[$item]
            Write-Step "Installing $packageId..."
            try {
                & winget install --id $packageId --accept-package-agreements --accept-source-agreements --silent 2>&1 | Out-Null
                Write-Ok "$item installed"
            } catch {
                Exit-WithError "Failed to install $item via winget. Please install manually and re-run this script."
            }
        }

        # Refresh PATH so newly installed tools are visible
        Refresh-PathEnv
        Write-Step "PATH refreshed after installations"
    }

    # Handle PostgreSQL via winget with user-provided settings
    if ($missing -contains "postgresql") {
        Write-Host ""
        Write-Host "    -------------------------------------------------------" -ForegroundColor $script:BRAND_COLOR
        Write-Host "    PostgreSQL will be installed automatically via winget." -ForegroundColor $script:BRAND_COLOR
        Write-Host "    -------------------------------------------------------" -ForegroundColor $script:BRAND_COLOR
        Write-Host ""

        if (-not $hasWinget) {
            Exit-WithError "winget is required to install PostgreSQL. Please install PostgreSQL manually from https://www.postgresql.org/download/windows/ and re-run this script."
        }

        # A) Prompt for admin password
        Write-Host "    Choose a password for the PostgreSQL 'postgres' admin user." -ForegroundColor $script:INFO_COLOR
        Write-Host "    You will need this password again during application setup." -ForegroundColor $script:MUTED_COLOR
        Write-Host ""
        do {
            $pgSecure1 = Read-Host "    PostgreSQL admin password" -AsSecureString
            $pgSecure2 = Read-Host "    Confirm password" -AsSecureString

            $pgPw1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pgSecure1))
            $pgPw2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pgSecure2))

            if ([string]::IsNullOrWhiteSpace($pgPw1)) {
                Write-Warn "Password cannot be empty."
                $pgPwOk = $false
            } elseif ($pgPw1 -ne $pgPw2) {
                Write-Warn "Passwords do not match. Try again."
                $pgPwOk = $false
            } else {
                $pgPwOk = $true
            }
        } while (-not $pgPwOk)
        Write-Ok "PostgreSQL password set"

        # B) Prompt for database name
        Write-Host ""
        Write-Host "    Choose the database name for GiljoAI MCP." -ForegroundColor $script:INFO_COLOR
        Write-Host "    Change this only if running multiple installations on the same server." -ForegroundColor $script:MUTED_COLOR
        $pgDbInput = Read-Host "    Database name [giljo_mcp]"
        if ([string]::IsNullOrWhiteSpace($pgDbInput)) {
            $script:PG_DB_NAME = "giljo_mcp"
        } else {
            $script:PG_DB_NAME = $pgDbInput
        }
        Write-Ok "Database name: $script:PG_DB_NAME"

        # Install PostgreSQL via winget
        Write-Step "Installing PostgreSQL via winget..."
        try {
            # Build override as a single string for the EDB PostgreSQL installer.
            # Winget's --override passes this verbatim to the installer executable.
            $escapedPw = $pgPw1 -replace '"', '\"'
            $pgArgs = @(
                "install"
                "PostgreSQL.PostgreSQL.18"
                "--silent"
                "--accept-source-agreements"
                "--accept-package-agreements"
                "--override"
            )
            # Use Start-Process with a single-line ArgumentList string so the
            # override value (which contains spaces) stays as one token.
            $argLine = ($pgArgs -join " ") + " `"--mode unattended --unattendedmodeui none --superpassword $escapedPw --serverport 5432 --enable-components server,commandlinetools --disable-components pgAdmin,stackbuilder`""
            Write-Host ""
            Write-Host "    ╔══════════════════════════════════════════════════════════╗" -ForegroundColor $script:BRAND_COLOR
            Write-Host "    ║  PostgreSQL is installing silently — this takes 3-5      ║" -ForegroundColor $script:BRAND_COLOR
            Write-Host "    ║  minutes. Microsoft C++ dependencies may also install.   ║" -ForegroundColor $script:BRAND_COLOR
            Write-Host "    ║  Please wait and do not close this window.               ║" -ForegroundColor $script:BRAND_COLOR
            Write-Host "    ╚══════════════════════════════════════════════════════════╝" -ForegroundColor $script:BRAND_COLOR
            Write-Host ""
            $pgProc = Start-Process -FilePath "winget" -ArgumentList $argLine -Wait -PassThru -NoNewWindow
            if ($pgProc.ExitCode -ne 0) {
                throw "winget exited with code $($pgProc.ExitCode)"
            }
            Write-Ok "PostgreSQL installed"
        } catch {
            Exit-WithError "PostgreSQL installation failed: $_`nPlease install manually from https://www.postgresql.org/download/windows/ and re-run this script."
        }

        # Add PostgreSQL bin to PATH for this session
        $pgBinPaths = @(
            "C:\Program Files\PostgreSQL\18\bin",
            "C:\Program Files\PostgreSQL\17\bin",
            "C:\Program Files\PostgreSQL\16\bin"
        )
        foreach ($p in $pgBinPaths) {
            if (Test-Path $p) {
                $env:PATH = "$p;$env:PATH"
                break
            }
        }

        Refresh-PathEnv

        # Verify PostgreSQL is now available
        $pgNow = (Test-CommandExists "pg_isready") -or
                 (Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue)
        if (-not $pgNow) {
            Exit-WithError "PostgreSQL was installed but is not detected. Try restarting your terminal and re-running this script."
        }
        Write-Ok "PostgreSQL detected after install"
    }

    # Final verification of winget-installed items
    foreach ($item in $wingetItems) {
        $cmd = switch ($item) {
            "python" { "python" }
            "node"   { "node" }
            "git"    { "git" }
        }
        if (-not (Test-CommandExists $cmd)) {
            Exit-WithError "$item was installed but is not on PATH. Please close and reopen your terminal, then re-run this script."
        }
    }

    Write-Ok "All prerequisites satisfied after installation"
}

# ---------------------------------------------------------------------------
# Phase 2 -- Download and verify
# ---------------------------------------------------------------------------

function Get-LatestRelease {
    Write-Phase "2" "Downloading latest release"

    # Fetch release metadata
    Write-Step "Fetching latest release info from GitHub..."
    try {
        $releaseInfo = Invoke-RestMethod -Uri $script:GITHUB_API_URL -UseBasicParsing
    } catch {
        Exit-WithError "Failed to fetch release info from GitHub. Check your internet connection."
    }

    $version = $releaseInfo.tag_name -replace '^v', ''
    Write-Ok "Latest version: $version"

    # Find version-manifest.json asset
    $manifestAsset = $releaseInfo.assets | Where-Object { $_.name -eq "version-manifest.json" }
    if (-not $manifestAsset) {
        Exit-WithError "Release is missing version-manifest.json. This release may be malformed."
    }

    # Download and parse the manifest
    Write-Step "Downloading version manifest..."
    $manifestUrl = $manifestAsset.browser_download_url
    $manifestContent = Invoke-RestMethod -Uri $manifestUrl -UseBasicParsing

    $tarballUrl = $manifestContent.tarball_url
    $expectedSha = $manifestContent.sha256

    if (-not $tarballUrl -or -not $expectedSha) {
        Exit-WithError "Version manifest is incomplete (missing tarball_url or sha256)."
    }

    # Download tarball
    $tarballName = "giljoai-mcp-$version.tar.gz"
    $tempDir     = Join-Path ([System.IO.Path]::GetTempPath()) "giljoai-install"
    if (-not (Test-Path $tempDir)) {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    }
    $tarballPath = Join-Path $tempDir $tarballName

    Write-Step "Downloading $tarballName..."
    try {
        Invoke-WebRequest -Uri $tarballUrl -OutFile $tarballPath -UseBasicParsing
    } catch {
        Exit-WithError "Failed to download tarball from $tarballUrl"
    }
    Write-Ok "Downloaded to $tarballPath"

    # Verify SHA256
    Write-Step "Verifying SHA256 checksum..."
    $actualHash = (Get-FileHash -Path $tarballPath -Algorithm SHA256).Hash.ToLower()
    $expectedHash = $expectedSha.ToLower()

    if ($actualHash -ne $expectedHash) {
        Remove-Item -Path $tarballPath -Force -ErrorAction SilentlyContinue
        Exit-WithError "SHA256 mismatch! Expected: $expectedHash, Got: $actualHash. The download may be corrupted or tampered with."
    }
    Write-Ok "SHA256 verified: $actualHash"

    return @{
        Version     = $version
        TarballPath = $tarballPath
        TempDir     = $tempDir
    }
}

function Install-Release {
    param(
        [hashtable]$Release,
        [string]$TargetDir,
        [bool]$IsUpdate
    )

    # Ask for install directory if not provided
    if (-not $TargetDir) {
        $TargetDir = $script:DEFAULT_INSTALL
        Write-Host ""
        Write-Host "    Install directory [$TargetDir]: " -ForegroundColor $script:INFO_COLOR -NoNewline
        $userInput = Read-Host
        if ($userInput) {
            $TargetDir = $userInput
        }
    }

    # Resolve to absolute path
    $TargetDir = [System.IO.Path]::GetFullPath($TargetDir)

    # Back up config files before extraction if updating
    $backupDir = $null
    if ($IsUpdate) {
        Write-Step "Backing up configuration files..."
        $backupDir = Join-Path $Release.TempDir "config-backup"
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

        $configFiles = @(".env", "config.yaml")
        foreach ($f in $configFiles) {
            $src = Join-Path $TargetDir $f
            if (Test-Path $src) {
                Copy-Item -Path $src -Destination (Join-Path $backupDir $f) -Force
                Write-Ok "Backed up $f"
            }
        }
    }

    # Create or verify target directory
    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
        Write-Ok "Created directory: $TargetDir"
    }

    # Extract tarball
    Write-Step "Extracting release to $TargetDir..."
    try {
        & tar -xzf $Release.TarballPath -C $TargetDir 2>&1 | Out-Null
    } catch {
        Exit-WithError "Failed to extract tarball. Ensure 'tar' is available (Windows 10+ includes it)."
    }
    Write-Ok "Extraction complete"

    # Restore backed-up config files
    if ($IsUpdate -and $backupDir) {
        Write-Step "Restoring configuration files..."
        $configFiles = @(".env", "config.yaml")
        foreach ($f in $configFiles) {
            $backup = Join-Path $backupDir $f
            if (Test-Path $backup) {
                Copy-Item -Path $backup -Destination (Join-Path $TargetDir $f) -Force
                Write-Ok "Restored $f"
            }
        }
    }

    # Write VERSION file
    $Release.Version | Out-File -FilePath (Join-Path $TargetDir "VERSION") -Encoding UTF8 -NoNewline

    # Clean up temp files
    Remove-Item -Path $Release.TarballPath -Force -ErrorAction SilentlyContinue | Out-Null

    # IMPORTANT: only return the string — no other pipeline output
    return $TargetDir
}

# ---------------------------------------------------------------------------
# Phase 3 -- Environment setup
# ---------------------------------------------------------------------------

function Initialize-Environment {
    param([string]$TargetDir)

    Write-Phase "3" "Setting up environment"

    $venvDir = Join-Path $TargetDir "venv"
    $venvPython = Join-Path $venvDir "Scripts" "python.exe"
    $venvPip    = Join-Path $venvDir "Scripts" "pip.exe"

    # Create venv if it does not exist
    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating Python virtual environment..."
        & python -m venv $venvDir
        Write-Ok "Virtual environment created"
    } else {
        Write-Ok "Virtual environment already exists"
    }

    # Upgrade pip
    Write-Step "Upgrading pip..."
    & $venvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null
    Write-Ok "pip upgraded"

    # Install Python dependencies
    $requirementsPath = Join-Path $TargetDir "requirements.txt"
    if (Test-Path $requirementsPath) {
        Write-Step "Installing Python dependencies (this may take a few minutes)..."
        & $venvPip install -r $requirementsPath --quiet 2>&1 | Out-Null
        Write-Ok "Python dependencies installed"
    } else {
        Write-Warn "requirements.txt not found -- skipping pip install"
    }

    # Register giljo_mcp as importable package (editable install, idempotent)
    $pyprojectPath = Join-Path $TargetDir "pyproject.toml"
    if (Test-Path $pyprojectPath) {
        try {
            & $venvPip install -e $TargetDir --quiet 2>&1 | Out-Null
            Write-Ok "Package registered (editable install)"
        } catch {
            Write-Warn "Editable install skipped (non-fatal): $_"
        }
    }

    # Build frontend — use Start-Process to avoid irm|iex pipeline mangling npm
    $frontendDir = Join-Path $TargetDir "frontend"
    if (Test-Path (Join-Path $frontendDir "package.json")) {
        Write-Step "Installing frontend dependencies..."
        $npmPath = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
        if (-not $npmPath) { $npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source }
        if ($npmPath) {
            $npmLog = Join-Path $TargetDir "npm-build.log"
            $proc1 = Start-Process -FilePath $npmPath -ArgumentList "install" -WorkingDirectory $frontendDir -Wait -PassThru -NoNewWindow -RedirectStandardOutput $npmLog -RedirectStandardError (Join-Path $TargetDir "npm-build-err.log")
            if ($proc1.ExitCode -eq 0) {
                Write-Ok "Frontend dependencies installed"
                Write-Step "Building frontend (this may take a minute)..."
                $proc2 = Start-Process -FilePath $npmPath -ArgumentList "run build" -WorkingDirectory $frontendDir -Wait -PassThru -NoNewWindow -RedirectStandardOutput $npmLog -RedirectStandardError (Join-Path $TargetDir "npm-build-err.log")
                if ($proc2.ExitCode -eq 0 -and (Test-Path (Join-Path $frontendDir "dist" "index.html"))) {
                    Write-Ok "Frontend built"
                } else {
                    Write-Warn "Frontend build failed — see npm-build.log for details"
                }
            } else {
                Write-Warn "npm install failed — startup.py will handle this on first run"
            }
        } else {
            Write-Warn "npm not found — startup.py will handle frontend on first run"
        }
    }
}

# ---------------------------------------------------------------------------
# Phase 4 -- Database and configuration via install.py
# ---------------------------------------------------------------------------

function Invoke-InstallPy {
    param([string]$TargetDir)

    Write-Phase "4" "Database and configuration setup"

    $venvPython = Join-Path $TargetDir "venv" "Scripts" "python.exe"
    $installPy  = Join-Path $TargetDir "install.py"

    if (-not (Test-Path $installPy)) {
        Exit-WithError "install.py not found in $TargetDir. The release may be incomplete."
    }

    Write-Step "Running install.py for database setup, config generation, and template seeding..."
    Write-Host ""

    Push-Location $TargetDir
    try {
        & $venvPython $installPy --setup-only
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            Exit-WithError "install.py exited with code $LASTEXITCODE. Check the output above for details."
        }
    } finally {
        Pop-Location
    }

    Write-Ok "Database and configuration setup complete"
}

# ---------------------------------------------------------------------------
# Phase 5 -- Shortcuts and launcher
# ---------------------------------------------------------------------------

function Install-Shortcuts {
    param([string]$TargetDir, [string]$Version)

    Write-Phase "5" "Creating shortcuts and launcher"

    # Create start-giljoai.bat
    $batPath = Join-Path $TargetDir "start-giljoai.bat"
    $batContent = @"
@echo off
title GiljoAI MCP Server
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m api.run_api
pause
"@
    Set-Content -Path $batPath -Value $batContent -Encoding ASCII
    Write-Ok "Created start-giljoai.bat"

    # Resolve icon path — Start.ico ships in frontend/public/
    $iconPath = Join-Path $TargetDir "frontend" "public" "Start.ico"
    if (-not (Test-Path $iconPath)) {
        $iconPath = Join-Path $TargetDir "frontend" "public" "favicon.ico"
    }

    # Create Start Menu shortcut
    $startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $shortcutPath = Join-Path $startMenuDir "GiljoAI MCP.lnk"

    try {
        $wshShell = New-Object -ComObject WScript.Shell
        $shortcut = $wshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $batPath
        $shortcut.WorkingDirectory = $TargetDir
        $shortcut.Description = "GiljoAI MCP Server v$Version"
        if (Test-Path $iconPath) { $shortcut.IconLocation = "$iconPath, 0" }
        $shortcut.Save()
        Write-Ok "Start Menu shortcut created"
    } catch {
        Write-Warn "Could not create Start Menu shortcut: $_"
    }

    # Desktop shortcut
    $desktopPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "GiljoAI MCP.lnk"
    try {
        $wshShell2 = New-Object -ComObject WScript.Shell
        $desktopShortcut = $wshShell2.CreateShortcut($desktopPath)
        $desktopShortcut.TargetPath = $batPath
        $desktopShortcut.WorkingDirectory = $TargetDir
        $desktopShortcut.Description = "GiljoAI MCP Server v$Version"
        if (Test-Path $iconPath) { $desktopShortcut.IconLocation = "$iconPath, 0" }
        $desktopShortcut.Save()
        Write-Ok "Desktop shortcut created"
    } catch {
        Write-Warn "Could not create desktop shortcut: $_"
    }
}

# ---------------------------------------------------------------------------
# Phase 6 -- Done
# ---------------------------------------------------------------------------

function Show-Completion {
    param([string]$TargetDir, [string]$Version)

    Write-Host ""
    Write-Host "    Installer finished. To start the server:" -ForegroundColor $script:INFO_COLOR
    Write-Host ""
    Write-Host "      cd $TargetDir" -ForegroundColor White
    Write-Host "      python startup.py --verbose" -ForegroundColor White
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Update detection
# ---------------------------------------------------------------------------

function Test-ExistingInstall {
    <#
    .SYNOPSIS
        Checks if a previous installation exists and returns its version.
        Returns $null if no existing install, or a hashtable with version info.
    #>
    param([string]$TargetDir)

    $versionFile = Join-Path $TargetDir "VERSION"
    if (Test-Path $versionFile) {
        $currentVersion = (Get-Content $versionFile -Raw).Trim()
        return @{ CurrentVersion = $currentVersion }
    }
    return $null
}

function Confirm-UpdateAction {
    <#
    .SYNOPSIS
        Prompts user to choose between Update, Reinstall, or Cancel when an
        existing installation is detected.
    #>
    param([string]$CurrentVersion, [string]$LatestVersion)

    Write-Host ""
    Write-Host "    Existing installation detected!" -ForegroundColor $script:BRAND_COLOR
    Write-Host "    Current version: $CurrentVersion" -ForegroundColor $script:INFO_COLOR
    Write-Host "    Latest version:  $LatestVersion" -ForegroundColor $script:INFO_COLOR
    Write-Host ""
    Write-Host "    [U] Update (preserves config and data)" -ForegroundColor $script:INFO_COLOR
    Write-Host "    [R] Reinstall (fresh install)" -ForegroundColor $script:INFO_COLOR
    Write-Host "    [C] Cancel" -ForegroundColor $script:MUTED_COLOR
    Write-Host ""
    Write-Host "    Choice [U/R/C]: " -ForegroundColor $script:BRAND_COLOR -NoNewline
    $choice = Read-Host

    switch ($choice.ToUpper()) {
        "U" { return "update" }
        "R" { return "reinstall" }
        default { return "cancel" }
    }
}

# ---------------------------------------------------------------------------
# Main entry point -- wrapped in a function to avoid variable leaks via iex
# ---------------------------------------------------------------------------

function Invoke-GiljoInstaller {
    Write-Banner

    # Resolve install directory
    $targetDir = if ($InstallDir) {
        [System.IO.Path]::GetFullPath($InstallDir)
    } else {
        $script:DEFAULT_INSTALL
    }

    # Check for existing installation
    $isUpdate = $false
    if (-not $Update) {
        $existing = Test-ExistingInstall -TargetDir $targetDir
        if ($existing) {
            # Need to fetch latest version for comparison before prompting
            try {
                $releasePreview = Invoke-RestMethod -Uri $script:GITHUB_API_URL -UseBasicParsing
                $latestVersion = $releasePreview.tag_name -replace '^v', ''
            } catch {
                $latestVersion = "(could not fetch)"
            }

            $action = Confirm-UpdateAction -CurrentVersion $existing.CurrentVersion -LatestVersion $latestVersion
            switch ($action) {
                "update"    { $isUpdate = $true }
                "reinstall" { $isUpdate = $false }
                "cancel" {
                    Write-Host "    Installation cancelled." -ForegroundColor $script:MUTED_COLOR
                    return
                }
            }
        }
    } else {
        $isUpdate = $true
    }

    # Phase 1 -- Prerequisites
    if (-not $SkipPrereqs) {
        Test-Prerequisites
    } else {
        Write-Phase "1" "Checking prerequisites"
        Write-Ok "Skipped (SkipPrereqs flag)"
    }

    # Phase 2 -- Download and verify
    $release = Get-LatestRelease

    # Phase 3 subset -- install to directory
    $targetDir = Install-Release -Release $release -TargetDir $targetDir -IsUpdate $isUpdate

    # Phase 3 -- Environment setup
    Initialize-Environment -TargetDir $targetDir

    # Phase 4 -- Database and config
    Invoke-InstallPy -TargetDir $targetDir

    # Phase 5 -- Shortcuts
    Install-Shortcuts -TargetDir $targetDir -Version $release.Version

    # Done
    Show-Completion -TargetDir $targetDir -Version $release.Version
}

# Run the installer
Invoke-GiljoInstaller
