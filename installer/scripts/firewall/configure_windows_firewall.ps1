# GiljoAI MCP - Windows Firewall Configuration
# Generated: 2025-10-02T05:22:24.781558
# Run as Administrator: Right-click -> "Run as administrator"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  GiljoAI MCP - Windows Firewall Configuration" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click the script and select 'Run as administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "Configuring firewall rules for GiljoAI MCP services..." -ForegroundColor Green
Write-Host ""

# Define services and ports
$services = @(
    @{Name="GiljoAI MCP API"; Port=8000},
    @{Name="GiljoAI MCP WebSocket"; Port=8001},
    @{Name="GiljoAI MCP Dashboard"; Port=3000},
    @{Name="GiljoAI MCP PostgreSQL"; Port=5432}
)

foreach ($service in $services) {
    $ruleName = $service.Name
    $port = $service.Port

    # Remove existing rule if present
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

    # Create inbound rule
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Direction Inbound `
        -LocalPort $port `
        -Protocol TCP `
        -Action Allow `
        -Profile Domain,Private `
        -ErrorAction Stop

    Write-Host "  [OK] Created rule: $ruleName (port $port)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Firewall configuration completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "SECURITY REMINDER:" -ForegroundColor Yellow
Write-Host "  - Review rules in Windows Defender Firewall" -ForegroundColor Yellow
Write-Host "  - Consider limiting access to specific IP ranges" -ForegroundColor Yellow
Write-Host "  - Enable SSL/TLS for production use" -ForegroundColor Yellow
Write-Host ""
pause
