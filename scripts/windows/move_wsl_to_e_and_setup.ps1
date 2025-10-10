# Moves a WSL distro to E: (stores ext4.vhdx on E:) and bootstraps
# a fast dev environment inside WSL (ext4) for GiljoAI_MCP.
#
# Usage (PowerShell, as Administrator):
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   F:\GiljoAI_MCP\scripts\windows\move_wsl_to_e_and_setup.ps1 -DistroName Ubuntu -TargetDrive E -LinuxUser giljo -CopyOllamaCache
#
# Notes:
# - This exports your selected distro, unregisters it, then imports it onto E:.
#   This is destructive for that distro instance if you haven't exported; the script exports first.
# - After import, the distro's default user is root. We create a user and set it as default via /etc/wsl.conf.
# - Then we create a Python venv on ext4 and optionally copy this repo and Ollama models into the distro.

param(
  [Parameter(Mandatory=$false)][string]$DistroName,
  [Parameter(Mandatory=$false)][ValidatePattern('^[A-Za-z]$')][string]$TargetDrive = 'E',
  [Parameter(Mandatory=$false)][string]$LinuxUser = 'giljo',
  [switch]$CopyOllamaCache,
  [switch]$SkipRepoCopy,
  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Assert-Admin {
  $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell (Run as Administrator)."
  }
}

function Get-WSLDistros {
  $out = & wsl --list --verbose 2>$null | Out-String
  $lines = $out -split "`r?`n" | Where-Object { $_ -and -not ($_ -match '^NAME\s+STATE\s+VERSION') }
  $result = @()
  foreach ($line in $lines) {
    # Lines look like: "* Ubuntu-22.04           Stopped         2" or "Ubuntu Stopped 2"
    $isDefault = $line.TrimStart().StartsWith('*')
    $clean = $line.TrimStart().TrimStart('*').Trim()
    if ($clean) {
      $parts = ($clean -replace '\s{2,}', '|').Split('|')
      if ($parts.Count -ge 3) {
        $result += [pscustomobject]@{
          Name = $parts[0].Trim()
          State = $parts[1].Trim()
          Version = $parts[2].Trim()
          Default = $isDefault
        }
      }
    }
  }
  return $result
}

function Convert-ToWslPath([string]$WinPath) {
  $path = $WinPath -replace '\\','/'
  if ($path -match '^(?<drive>[A-Za-z]):/(.*)$') {
    return "/mnt/$($Matches['drive'].ToLower())/$($Matches[2])"
  }
  return $path
}

function Invoke-WSL([string]$Distro, [string]$User, [string]$Command) {
  Write-Host "[WSL:$Distro@$User] $Command" -ForegroundColor DarkCyan
  & wsl -d $Distro -u $User -- bash -lc $Command
}

try {
  Assert-Admin

  Write-Host "=== WSL Relocation + Setup ===" -ForegroundColor Cyan
  Write-Host "This will export a WSL distro, move it to $TargetDrive`:\\WSL, and set up your dev env." -ForegroundColor Cyan

  $distros = Get-WSLDistros
  if (-not $distros) {
    throw "No WSL distros found. Install one first (wsl --install -d Ubuntu)."
  }

  if (-not $DistroName) {
    $default = $distros | Where-Object { $_.Default } | Select-Object -First 1
    if ($default) { $DistroName = $default.Name }
  }

  Write-Host "Available distros:" -ForegroundColor Yellow
  $distros | ForEach-Object { Write-Host (" - {0} (State: {1}, Version: {2}{3})" -f $_.Name, $_.State, $_.Version, ($(if ($_.Default) {'; Default'} else {''}))) }
  if (-not $DistroName) {
    $DistroName = Read-Host "Enter the distro name to move (exactly as shown above)"
  }

  $selected = $distros | Where-Object { $_.Name -eq $DistroName } | Select-Object -First 1
  if (-not $selected) { throw "Distro '$DistroName' not found." }
  if ($selected.Version -ne '2') {
    Write-Warning "Selected distro is not WSL 2. Importing with --version 2."
  }

  $targetRoot = "$TargetDrive`:\WSL\$DistroName"
  $null = New-Item -ItemType Directory -Force -Path $targetRoot
  $exportTar = Join-Path $targetRoot ("$DistroName-export-" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".tar")

  Write-Host "Target folder: $targetRoot" -ForegroundColor Green
  Write-Host "Export file:   $exportTar" -ForegroundColor Green

  if (-not $Force) {
    Write-Host "This will run: wsl --shutdown; export; unregister; import. BACK UP important files first!" -ForegroundColor Yellow
    $confirm = Read-Host "Continue? (type YES to proceed)"
    if ($confirm -ne 'YES') { throw "User aborted." }
  }

  Write-Host "Shutting down WSL..." -ForegroundColor Cyan
  & wsl --shutdown | Out-Null

  Write-Host "Exporting '$DistroName' to $exportTar (this can take several minutes)..." -ForegroundColor Cyan
  & wsl --export $DistroName $exportTar

  Write-Host "Unregistering old distro instance '$DistroName'..." -ForegroundColor Cyan
  & wsl --unregister $DistroName

  Write-Host "Importing '$DistroName' to $targetRoot as WSL2..." -ForegroundColor Cyan
  & wsl --import $DistroName $targetRoot $exportTar --version 2

  Write-Host "Imported. Launching distro once to finalize..." -ForegroundColor Cyan
  # Launch once to ensure rootfs is initialized
  & wsl -d $DistroName -- echo ok | Out-Null

  if (-not [string]::IsNullOrEmpty($LinuxUser)) {
    Write-Host "Creating Linux user '$LinuxUser' and setting as default..." -ForegroundColor Cyan
    Invoke-WSL $DistroName 'root' "id -u $LinuxUser >/dev/null 2>&1 || (useradd -m -s /bin/bash -G sudo $LinuxUser)"
    Invoke-WSL $DistroName 'root' "printf '[user]\ndefault=%s\n' $LinuxUser > /etc/wsl.conf"
  }

  Write-Host "Installing base packages (python3-venv, pip, rsync, curl, jq)..." -ForegroundColor Cyan
  Invoke-WSL $DistroName 'root' "apt-get update -y && apt-get install -y python3-venv python3-pip rsync curl jq"

  Write-Host "Creating Python venv on ext4 and installing LiteLLM..." -ForegroundColor Cyan
  Invoke-WSL $DistroName $LinuxUser "mkdir -p ~/.venvs && python3 -m venv ~/.venvs/llm && source ~/.venvs/llm/bin/activate && python -m pip install -U pip 'litellm[proxy]'"

  # Determine repo root (Windows path) relative to this script location
  $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
  # repo root is two levels up from scripts\windows
  $RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
  $RepoRootWSL = Convert-ToWslPath $RepoRoot.Path

  if (-not $SkipRepoCopy) {
    Write-Host "Copying repo from $($RepoRoot.Path) to /home/$LinuxUser/work/GiljoAI_MCP (may take time from /mnt/*)..." -ForegroundColor Cyan
    Invoke-WSL $DistroName $LinuxUser "mkdir -p ~/work && rsync -a --info=progress2 '$RepoRootWSL/' ~/work/GiljoAI_MCP/"
    Write-Host "Linking venv into repo path..." -ForegroundColor Cyan
    Invoke-WSL $DistroName $LinuxUser "mkdir -p ~/work/GiljoAI_MCP/venv && ln -sfn ~/.venvs/llm ~/work/GiljoAI_MCP/venv/llm"
  } else {
    Write-Host "Skipping repo copy as requested." -ForegroundColor Yellow
  }

  # Optional: copy Ollama cache from Windows into WSL ext4
  $winOllama = Join-Path $env:USERPROFILE ".ollama"
  if (-not $CopyOllamaCache.IsPresent) {
    if (Test-Path $winOllama) {
      $resp = Read-Host "Copy Windows Ollama models from $winOllama to WSL ext4 now? (y/N)"
      if ($resp -match '^[Yy]') { $CopyOllamaCache = $true }
    }
  }
  if ($CopyOllamaCache) {
    if (Test-Path $winOllama) {
      Write-Host "Copying Ollama cache to WSL ext4 (~/.ollama). This can be large and take time..." -ForegroundColor Cyan
      $winUser = $env:USERNAME
      Invoke-WSL $DistroName $LinuxUser "rsync -av --progress /mnt/c/Users/$winUser/.ollama/ ~/.ollama/"
    } else {
      Write-Host "No Windows Ollama cache found at $winOllama" -ForegroundColor Yellow
    }
  }

  Write-Host "=== Completed ===" -ForegroundColor Green
  Write-Host "Distro '$DistroName' now lives under $targetRoot (ext4.vhdx on ${TargetDrive}:)." -ForegroundColor Green
  Write-Host "Open a new WSL terminal to use the default user ($LinuxUser)." -ForegroundColor Green

  Write-Host ""; Write-Host "Useful test commands inside WSL:" -ForegroundColor Yellow
  Write-Host "  cd ~/work/GiljoAI_MCP"; 
  Write-Host "  bash start_cline_models.sh";
  Write-Host "  curl -s http://127.0.0.1:11434/api/tags | jq";
  Write-Host "  curl -s http://127.0.0.1:11436/v1/models -H 'Authorization: Bearer sk-giljo-local' | jq";
  Write-Host "";
  Write-Host "If start is slow, verify you're running from ~/work/GiljoAI_MCP (ext4), not /mnt/*." -ForegroundColor Yellow

} catch {
  Write-Error $_
  exit 1
}
