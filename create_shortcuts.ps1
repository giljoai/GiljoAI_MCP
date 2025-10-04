# Create Desktop Shortcuts for GiljoAI MCP
# This script creates Windows shortcuts with icons on the user's desktop

$projectPath = "C:\Projects\GiljoAI_MCP"

# Determine desktop path (OneDrive or local)
$desktopPath = [Environment]::GetFolderPath("Desktop")
$oneDriveDesktop = Join-Path $env:USERPROFILE "OneDrive\Desktop"

if (Test-Path $oneDriveDesktop) {
    $desktopPath = $oneDriveDesktop
    Write-Host "Using OneDrive Desktop: $desktopPath"
} else {
    Write-Host "Using Local Desktop: $desktopPath"
}

Write-Host ""
Write-Host "==============================================="
Write-Host "   Creating GiljoAI MCP Desktop Shortcuts"
Write-Host "==============================================="
Write-Host ""

# Function to create shortcut with icon
function Create-Shortcut {
    param(
        [string]$Name,
        [string]$TargetPath,
        [string]$IconPath,
        [string]$Description
    )

    try {
        $WScriptShell = New-Object -ComObject WScript.Shell
        $shortcutPath = Join-Path $desktopPath "$Name.lnk"
        $shortcut = $WScriptShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $TargetPath
        $shortcut.WorkingDirectory = $projectPath
        $shortcut.Description = $Description

        # Set icon if provided and exists
        if ($IconPath -and (Test-Path $IconPath)) {
            $shortcut.IconLocation = $IconPath
        }

        $shortcut.Save()
        Write-Host "[OK] Created: $Name"
        return $true
    }
    catch {
        Write-Host "[ERROR] Failed to create: $Name"
        Write-Host "        Error: $($_.Exception.Message)"
        return $false
    }
}

# Validate icon files exist
$startIcon = Join-Path $projectPath "frontend\public\Start.ico"
$stopIcon = Join-Path $projectPath "frontend\public\Stop.ico"
$frontendIcon = Join-Path $projectPath "frontend\public\Fontend.ico"

Write-Host "Validating icon files..."
if (Test-Path $startIcon) { Write-Host "  [OK] Start.ico" } else { Write-Host "  [WARN] Start.ico not found" }
if (Test-Path $stopIcon) { Write-Host "  [OK] Stop.ico" } else { Write-Host "  [WARN] Stop.ico not found" }
if (Test-Path $frontendIcon) { Write-Host "  [OK] Fontend.ico" } else { Write-Host "  [WARN] Fontend.ico not found" }
Write-Host ""

# Create shortcuts
$created = 0
$failed = 0

Write-Host "Creating shortcuts..."

if (Create-Shortcut -Name "GiljoAI - Start All" `
    -TargetPath "$projectPath\start_giljo.bat" `
    -IconPath $startIcon `
    -Description "Start GiljoAI MCP Backend API Server") {
    $created++
} else {
    $failed++
}

if (Create-Shortcut -Name "GiljoAI - Stop All" `
    -TargetPath "$projectPath\stop_giljo.bat" `
    -IconPath $stopIcon `
    -Description "Stop GiljoAI MCP Backend API Server") {
    $created++
} else {
    $failed++
}

if (Create-Shortcut -Name "GiljoAI - Start Frontend" `
    -TargetPath "$projectPath\start_frontend.bat" `
    -IconPath $frontendIcon `
    -Description "Start GiljoAI Frontend Development Server") {
    $created++
} else {
    $failed++
}

if (Create-Shortcut -Name "GiljoAI - Stop Frontend" `
    -TargetPath "$projectPath\stop_frontend.bat" `
    -IconPath $stopIcon `
    -Description "Stop GiljoAI Frontend Development Server") {
    $created++
} else {
    $failed++
}

if (Create-Shortcut -Name "GiljoAI - Start Backend" `
    -TargetPath "$projectPath\start_backend.bat" `
    -IconPath $startIcon `
    -Description "Start GiljoAI Backend API Server") {
    $created++
} else {
    $failed++
}

if (Create-Shortcut -Name "GiljoAI - Stop Backend" `
    -TargetPath "$projectPath\stop_backend.bat" `
    -IconPath $stopIcon `
    -Description "Stop GiljoAI Backend API Server") {
    $created++
} else {
    $failed++
}

Write-Host ""
Write-Host "==============================================="
Write-Host "   Summary"
Write-Host "==============================================="
Write-Host "Desktop Path:  $desktopPath"
Write-Host "Created:       $created shortcuts"
Write-Host "Failed:        $failed shortcuts"
Write-Host ""

if ($created -gt 0) {
    Write-Host "Shortcuts successfully created on your desktop!"
    Write-Host ""
    Write-Host "Available shortcuts:"
    Write-Host "  - GiljoAI - Start All.lnk"
    Write-Host "  - GiljoAI - Stop All.lnk"
    Write-Host "  - GiljoAI - Start Frontend.lnk"
    Write-Host "  - GiljoAI - Stop Frontend.lnk"
    Write-Host "  - GiljoAI - Start Backend.lnk"
    Write-Host "  - GiljoAI - Stop Backend.lnk"
}

if ($failed -gt 0) {
    Write-Host ""
    Write-Host "Warning: Some shortcuts failed to create. Check errors above."
    exit 1
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
