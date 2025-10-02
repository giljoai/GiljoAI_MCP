"""
Firewall rule generation for GiljoAI MCP server mode
Generates platform-specific firewall rules (DO NOT auto-apply)
"""

import platform
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class FirewallManager:
    """Generate firewall configuration scripts for manual application"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.mode = settings.get('mode', 'localhost')
        self.logger = logging.getLogger(self.__class__.__name__)

        # Port configuration
        self.ports = {
            'API': settings.get('api_port', 8000),
            'WebSocket': settings.get('ws_port', 8001),
            'Dashboard': settings.get('dashboard_port', 3000),
            'PostgreSQL': settings.get('pg_port', 5432)
        }

        # Bind address for network rules
        self.bind_address = settings.get('bind', '0.0.0.0')

    def generate_firewall_rules(self) -> Dict[str, Any]:
        """Generate platform-specific firewall rules"""
        result = {'success': False, 'errors': [], 'files': []}

        try:
            # Skip firewall rules for localhost mode
            if self.mode == 'localhost':
                self.logger.info("Localhost mode - firewall rules not needed")
                result['success'] = True
                result['message'] = "Firewall rules not required for localhost mode"
                return result

            # Create firewall scripts directory
            scripts_dir = Path("installer/scripts/firewall")
            scripts_dir.mkdir(parents=True, exist_ok=True)

            system = platform.system()

            # Generate platform-specific rules
            if system == "Windows":
                files = self.generate_windows_rules(scripts_dir)
                result['files'].extend(files)
            elif system == "Linux":
                files = self.generate_linux_rules(scripts_dir)
                result['files'].extend(files)
            elif system == "Darwin":
                files = self.generate_macos_rules(scripts_dir)
                result['files'].extend(files)
            else:
                result['errors'].append(f"Unsupported platform: {system}")
                return result

            # Generate summary file
            summary_file = self.generate_summary_file(scripts_dir)
            result['files'].append(summary_file)

            # Generate main firewall_rules.txt
            rules_file = self.generate_rules_txt()
            result['files'].append(rules_file)

            result['success'] = True
            result['platform'] = system
            result['message'] = "Firewall rules generated (manual application required)"

            self.logger.info(f"Firewall rules generated for {system}")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Firewall rule generation failed: {e}")
            return result

    def generate_windows_rules(self, scripts_dir: Path) -> List[str]:
        """Generate Windows firewall rules (PowerShell and netsh)"""
        files = []

        # PowerShell script
        ps_script = scripts_dir / "configure_windows_firewall.ps1"
        ps_content = f'''# GiljoAI MCP - Windows Firewall Configuration
# Generated: {datetime.now().isoformat()}
# Run as Administrator: Right-click -> "Run as administrator"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  GiljoAI MCP - Windows Firewall Configuration" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {{
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click the script and select 'Run as administrator'" -ForegroundColor Yellow
    pause
    exit 1
}}

Write-Host "Configuring firewall rules for GiljoAI MCP services..." -ForegroundColor Green
Write-Host ""

# Define services and ports
$services = @(
    @{{Name="GiljoAI MCP API"; Port={self.ports['API']}}},
    @{{Name="GiljoAI MCP WebSocket"; Port={self.ports['WebSocket']}}},
    @{{Name="GiljoAI MCP Dashboard"; Port={self.ports['Dashboard']}}},
    @{{Name="GiljoAI MCP PostgreSQL"; Port={self.ports['PostgreSQL']}}}
)

foreach ($service in $services) {{
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
}}

Write-Host ""
Write-Host "Firewall configuration completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "SECURITY REMINDER:" -ForegroundColor Yellow
Write-Host "  - Review rules in Windows Defender Firewall" -ForegroundColor Yellow
Write-Host "  - Consider limiting access to specific IP ranges" -ForegroundColor Yellow
Write-Host "  - Enable SSL/TLS for production use" -ForegroundColor Yellow
Write-Host ""
pause
'''
        ps_script.write_text(ps_content)
        files.append(str(ps_script.absolute()))
        self.logger.info(f"Generated PowerShell script: {ps_script}")

        # Batch file for netsh (alternative method)
        bat_script = scripts_dir / "configure_windows_firewall.bat"
        bat_content = f'''@echo off
REM GiljoAI MCP - Windows Firewall Configuration (netsh)
REM Generated: {datetime.now().isoformat()}
REM Run as Administrator

echo ==========================================================
echo   GiljoAI MCP - Windows Firewall Configuration
echo ==========================================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click the script and select "Run as administrator"
    pause
    exit /b 1
)

echo Configuring firewall rules for GiljoAI MCP services...
echo.

REM API Server
netsh advfirewall firewall delete rule name="GiljoAI MCP API" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP API" ^
    dir=in action=allow ^
    protocol=TCP localport={self.ports['API']} ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP API (port {self.ports['API']})

REM WebSocket Server
netsh advfirewall firewall delete rule name="GiljoAI MCP WebSocket" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP WebSocket" ^
    dir=in action=allow ^
    protocol=TCP localport={self.ports['WebSocket']} ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP WebSocket (port {self.ports['WebSocket']})

REM Dashboard
netsh advfirewall firewall delete rule name="GiljoAI MCP Dashboard" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP Dashboard" ^
    dir=in action=allow ^
    protocol=TCP localport={self.ports['Dashboard']} ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP Dashboard (port {self.ports['Dashboard']})

REM PostgreSQL
netsh advfirewall firewall delete rule name="GiljoAI MCP PostgreSQL" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP PostgreSQL" ^
    dir=in action=allow ^
    protocol=TCP localport={self.ports['PostgreSQL']} ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP PostgreSQL (port {self.ports['PostgreSQL']})

echo.
echo Firewall configuration completed successfully!
echo.
echo SECURITY REMINDER:
echo   - Review rules in Windows Defender Firewall
echo   - Consider limiting access to specific IP ranges
echo   - Enable SSL/TLS for production use
echo.
pause
'''
        bat_script.write_text(bat_content)
        files.append(str(bat_script.absolute()))
        self.logger.info(f"Generated batch script: {bat_script}")

        return files

    def generate_linux_rules(self, scripts_dir: Path) -> List[str]:
        """Generate Linux firewall rules (UFW and iptables)"""
        files = []

        # UFW script (Ubuntu/Debian)
        ufw_script = scripts_dir / "configure_ufw_firewall.sh"
        ufw_content = f'''#!/bin/bash
# GiljoAI MCP - Ubuntu/Debian Firewall Configuration (UFW)
# Generated: {datetime.now().isoformat()}
# Run with: sudo bash configure_ufw_firewall.sh

echo "=========================================================="
echo "  GiljoAI MCP - UFW Firewall Configuration"
echo "=========================================================="
echo ""

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Check if UFW is installed
if ! command -v ufw &> /dev/null; then
    echo "ERROR: UFW is not installed"
    echo "Install with: sudo apt-get install ufw"
    exit 1
fi

echo "Configuring firewall rules for GiljoAI MCP services..."
echo ""

# API Server
ufw allow {self.ports['API']}/tcp comment 'GiljoAI MCP API'
echo "  [OK] Allowed port {self.ports['API']}/tcp (API)"

# WebSocket Server
ufw allow {self.ports['WebSocket']}/tcp comment 'GiljoAI MCP WebSocket'
echo "  [OK] Allowed port {self.ports['WebSocket']}/tcp (WebSocket)"

# Dashboard
ufw allow {self.ports['Dashboard']}/tcp comment 'GiljoAI MCP Dashboard'
echo "  [OK] Allowed port {self.ports['Dashboard']}/tcp (Dashboard)"

# PostgreSQL
ufw allow {self.ports['PostgreSQL']}/tcp comment 'GiljoAI MCP PostgreSQL'
echo "  [OK] Allowed port {self.ports['PostgreSQL']}/tcp (PostgreSQL)"

# Enable UFW if not already enabled
if ! ufw status | grep -q "Status: active"; then
    echo ""
    echo "UFW is currently inactive. Enable it? (y/n)"
    read -r response
    if [[ "$response" == "y" || "$response" == "Y" ]]; then
        ufw --force enable
        echo "  [OK] UFW enabled"
    fi
fi

# Reload UFW
ufw reload

echo ""
echo "Firewall configuration completed successfully!"
echo ""
echo "SECURITY REMINDER:"
echo "  - Review rules with: sudo ufw status verbose"
echo "  - Consider limiting access to specific IP ranges"
echo "  - Enable SSL/TLS for production use"
echo ""
'''
        ufw_script.write_text(ufw_content)
        ufw_script.chmod(0o755)
        files.append(str(ufw_script.absolute()))
        self.logger.info(f"Generated UFW script: {ufw_script}")

        # iptables script (RHEL/CentOS/generic)
        iptables_script = scripts_dir / "configure_iptables_firewall.sh"
        iptables_content = f'''#!/bin/bash
# GiljoAI MCP - iptables Firewall Configuration
# Generated: {datetime.now().isoformat()}
# Run with: sudo bash configure_iptables_firewall.sh

echo "=========================================================="
echo "  GiljoAI MCP - iptables Firewall Configuration"
echo "=========================================================="
echo ""

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

echo "Configuring firewall rules for GiljoAI MCP services..."
echo ""

# API Server
iptables -A INPUT -p tcp --dport {self.ports['API']} -j ACCEPT -m comment --comment "GiljoAI MCP API"
echo "  [OK] Added rule for port {self.ports['API']}/tcp (API)"

# WebSocket Server
iptables -A INPUT -p tcp --dport {self.ports['WebSocket']} -j ACCEPT -m comment --comment "GiljoAI MCP WebSocket"
echo "  [OK] Added rule for port {self.ports['WebSocket']}/tcp (WebSocket)"

# Dashboard
iptables -A INPUT -p tcp --dport {self.ports['Dashboard']} -j ACCEPT -m comment --comment "GiljoAI MCP Dashboard"
echo "  [OK] Added rule for port {self.ports['Dashboard']}/tcp (Dashboard)"

# PostgreSQL
iptables -A INPUT -p tcp --dport {self.ports['PostgreSQL']} -j ACCEPT -m comment --comment "GiljoAI MCP PostgreSQL"
echo "  [OK] Added rule for port {self.ports['PostgreSQL']}/tcp (PostgreSQL)"

# Save rules (method depends on distribution)
if command -v iptables-save &> /dev/null; then
    if [ -d /etc/iptables ]; then
        iptables-save > /etc/iptables/rules.v4
        echo "  [OK] Rules saved to /etc/iptables/rules.v4"
    elif command -v netfilter-persistent &> /dev/null; then
        netfilter-persistent save
        echo "  [OK] Rules saved with netfilter-persistent"
    fi
elif command -v firewall-cmd &> /dev/null; then
    # Use firewalld if available
    firewall-cmd --permanent --add-port={self.ports['API']}/tcp
    firewall-cmd --permanent --add-port={self.ports['WebSocket']}/tcp
    firewall-cmd --permanent --add-port={self.ports['Dashboard']}/tcp
    firewall-cmd --permanent --add-port={self.ports['PostgreSQL']}/tcp
    firewall-cmd --reload
    echo "  [OK] Rules saved with firewalld"
fi

echo ""
echo "Firewall configuration completed successfully!"
echo ""
echo "SECURITY REMINDER:"
echo "  - Review rules with: sudo iptables -L -n -v"
echo "  - Consider limiting access to specific IP ranges"
echo "  - Enable SSL/TLS for production use"
echo ""
'''
        iptables_script.write_text(iptables_content)
        iptables_script.chmod(0o755)
        files.append(str(iptables_script.absolute()))
        self.logger.info(f"Generated iptables script: {iptables_script}")

        return files

    def generate_macos_rules(self, scripts_dir: Path) -> List[str]:
        """Generate macOS firewall rules (pfctl)"""
        files = []

        # pf.conf additions
        pf_script = scripts_dir / "configure_macos_firewall.sh"
        pf_content = f'''#!/bin/bash
# GiljoAI MCP - macOS Firewall Configuration (pfctl)
# Generated: {datetime.now().isoformat()}
# Run with: sudo bash configure_macos_firewall.sh

echo "=========================================================="
echo "  GiljoAI MCP - macOS Firewall Configuration"
echo "=========================================================="
echo ""

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Create custom pf rules file
PF_RULES="/etc/pf.anchors/giljo_mcp"

echo "Creating firewall rules for GiljoAI MCP services..."
echo ""

cat > "$PF_RULES" << 'EOF'
# GiljoAI MCP Firewall Rules
# Generated: {datetime.now().isoformat()}

# Allow API Server
pass in proto tcp from any to any port {self.ports['API']} keep state

# Allow WebSocket Server
pass in proto tcp from any to any port {self.ports['WebSocket']} keep state

# Allow Dashboard
pass in proto tcp from any to any port {self.ports['Dashboard']} keep state

# Allow PostgreSQL
pass in proto tcp from any to any port {self.ports['PostgreSQL']} keep state
EOF

echo "  [OK] Created rules file: $PF_RULES"

# Add anchor to main pf.conf if not already present
if ! grep -q "giljo_mcp" /etc/pf.conf; then
    echo "" >> /etc/pf.conf
    echo "# GiljoAI MCP anchor" >> /etc/pf.conf
    echo "anchor giljo_mcp" >> /etc/pf.conf
    echo "load anchor giljo_mcp from \\"$PF_RULES\\"" >> /etc/pf.conf
    echo "  [OK] Added anchor to /etc/pf.conf"
fi

# Load the rules
pfctl -f /etc/pf.conf 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  [OK] Loaded firewall rules"
else
    echo "  [WARNING] Could not load rules automatically"
    echo "  Load manually with: sudo pfctl -f /etc/pf.conf"
fi

# Enable pf if not already enabled
if ! pfctl -s info 2>/dev/null | grep -q "Status: Enabled"; then
    echo ""
    echo "pf is currently disabled. Enable it? (y/n)"
    read -r response
    if [[ "$response" == "y" || "$response" == "Y" ]]; then
        pfctl -e 2>/dev/null
        echo "  [OK] Enabled pf"
    fi
fi

echo ""
echo "Firewall configuration completed successfully!"
echo ""
echo "SECURITY REMINDER:"
echo "  - Review rules with: sudo pfctl -s rules"
echo "  - Consider limiting access to specific IP ranges"
echo "  - Enable SSL/TLS for production use"
echo ""
echo "macOS also has an application firewall. Configure it in:"
echo "  System Preferences > Security & Privacy > Firewall"
echo ""
'''
        pf_script.write_text(pf_content)
        pf_script.chmod(0o755)
        files.append(str(pf_script.absolute()))
        self.logger.info(f"Generated macOS pf script: {pf_script}")

        return files

    def generate_summary_file(self, scripts_dir: Path) -> str:
        """Generate firewall configuration summary"""
        summary_file = scripts_dir / "README.md"
        summary_content = f'''# GiljoAI MCP Firewall Configuration

Generated: {datetime.now().isoformat()}
Platform: {platform.system()}
Mode: {self.mode}

## Required Ports

| Service | Port | Description |
|---------|------|-------------|
| API Server | {self.ports['API']} | REST API and HTTP endpoints |
| WebSocket | {self.ports['WebSocket']} | Real-time WebSocket connections |
| Dashboard | {self.ports['Dashboard']} | Web-based dashboard UI |
| PostgreSQL | {self.ports['PostgreSQL']} | Database server (if remote access needed) |

## Platform-Specific Instructions

### Windows

**Option 1: PowerShell (Recommended)**
1. Right-click `configure_windows_firewall.ps1`
2. Select "Run with PowerShell"
3. Confirm administrator elevation

**Option 2: Command Prompt (netsh)**
1. Right-click `configure_windows_firewall.bat`
2. Select "Run as administrator"

### Linux

**Ubuntu/Debian (UFW)**
```bash
sudo bash configure_ufw_firewall.sh
```

**RHEL/CentOS/Other (iptables)**
```bash
sudo bash configure_iptables_firewall.sh
```

### macOS

**Packet Filter (pf)**
```bash
sudo bash configure_macos_firewall.sh
```

## Security Considerations

1. **Network Exposure**: These rules allow incoming connections from any IP
   - Consider restricting to specific IP ranges for production
   - Use `-s <IP/subnet>` in iptables/pf rules to limit source IPs

2. **SSL/TLS**: Always enable SSL for network-exposed deployments
   - Prevents credential interception
   - Protects API keys and sensitive data

3. **Port Security**:
   - PostgreSQL port ({self.ports['PostgreSQL']}) should only be opened if remote database access is required
   - Consider using SSH tunneling instead of direct PostgreSQL exposure

4. **Regular Audits**:
   - Review firewall rules periodically
   - Remove rules when services are decommissioned
   - Monitor for unauthorized access attempts

## Manual Configuration

If automatic scripts don't work, use these manual commands:

### Windows (PowerShell)
```powershell
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -LocalPort {self.ports['API']} -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "GiljoAI MCP WebSocket" -Direction Inbound -LocalPort {self.ports['WebSocket']} -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard" -Direction Inbound -LocalPort {self.ports['Dashboard']} -Protocol TCP -Action Allow
```

### Linux (UFW)
```bash
sudo ufw allow {self.ports['API']}/tcp
sudo ufw allow {self.ports['WebSocket']}/tcp
sudo ufw allow {self.ports['Dashboard']}/tcp
```

### macOS (pf)
Add to `/etc/pf.conf`:
```
pass in proto tcp from any to any port {self.ports['API']}
pass in proto tcp from any to any port {self.ports['WebSocket']}
pass in proto tcp from any to any port {self.ports['Dashboard']}
```

Then reload: `sudo pfctl -f /etc/pf.conf`

## Verification

After configuration, verify rules are active:

- **Windows**: `Get-NetFirewallRule -DisplayName "GiljoAI*"`
- **Linux (UFW)**: `sudo ufw status verbose`
- **Linux (iptables)**: `sudo iptables -L -n -v`
- **macOS**: `sudo pfctl -s rules`

## Troubleshooting

1. **Rules not applying**: Ensure you have administrator/root privileges
2. **Service still blocked**: Check if another firewall is active (Windows Defender, third-party)
3. **Port conflicts**: Verify ports are not already in use by other services
'''
        summary_file.write_text(summary_content)
        self.logger.info(f"Generated firewall summary: {summary_file}")

        return str(summary_file.absolute())

    def generate_rules_txt(self) -> str:
        """Generate simple firewall_rules.txt in project root"""
        rules_file = Path("firewall_rules.txt")
        content = f'''# GiljoAI MCP Firewall Rules
# Generated: {datetime.now().isoformat()}
# Platform: {platform.system()}

IMPORTANT: These rules must be applied manually by running the appropriate script
           in installer/scripts/firewall/

Required Ports:
  - API Server:     {self.ports['API']}/tcp
  - WebSocket:      {self.ports['WebSocket']}/tcp
  - Dashboard:      {self.ports['Dashboard']}/tcp
  - PostgreSQL:     {self.ports['PostgreSQL']}/tcp (only if remote access needed)

Platform-Specific Scripts:
  Windows:   installer/scripts/firewall/configure_windows_firewall.ps1
  Linux:     installer/scripts/firewall/configure_ufw_firewall.sh
  macOS:     installer/scripts/firewall/configure_macos_firewall.sh

For detailed instructions, see:
  installer/scripts/firewall/README.md

WARNING: Firewall rules are NOT automatically applied for security reasons.
         You must manually run the appropriate script for your platform.
'''
        rules_file.write_text(content)
        self.logger.info(f"Generated firewall rules summary: {rules_file}")

        return str(rules_file.absolute())

    def print_firewall_instructions(self) -> str:
        """Generate formatted firewall setup instructions for CLI output"""
        if self.mode == 'localhost':
            return ""

        system = platform.system()
        instructions = "\n" + "=" * 70 + "\n"
        instructions += "  FIREWALL CONFIGURATION REQUIRED\n"
        instructions += "=" * 70 + "\n\n"
        instructions += "  Server mode requires firewall rules to allow incoming connections.\n"
        instructions += "  For security, rules must be applied MANUALLY.\n\n"

        instructions += "  Required Ports:\n"
        for service, port in self.ports.items():
            instructions += f"    - {service:12s}: {port}/tcp\n"

        instructions += "\n  Configuration Scripts:\n"

        if system == "Windows":
            instructions += "    PowerShell: installer\\scripts\\firewall\\configure_windows_firewall.ps1\n"
            instructions += "    Batch:      installer\\scripts\\firewall\\configure_windows_firewall.bat\n"
            instructions += "\n  Run as Administrator (right-click -> Run as administrator)\n"
        elif system == "Linux":
            instructions += "    UFW:        installer/scripts/firewall/configure_ufw_firewall.sh\n"
            instructions += "    iptables:   installer/scripts/firewall/configure_iptables_firewall.sh\n"
            instructions += "\n  Run with sudo: sudo bash <script_name>\n"
        elif system == "Darwin":
            instructions += "    macOS:      installer/scripts/firewall/configure_macos_firewall.sh\n"
            instructions += "\n  Run with sudo: sudo bash <script_name>\n"

        instructions += "\n  See firewall_rules.txt for quick reference\n"
        instructions += "  See installer/scripts/firewall/README.md for detailed instructions\n"
        instructions += "\n" + "=" * 70 + "\n"

        return instructions
