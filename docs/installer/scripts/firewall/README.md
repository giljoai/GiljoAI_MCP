# GiljoAI MCP Firewall Configuration

Generated: 2025-10-02T05:22:24.782875
Platform: Windows
Mode: server

## Required Ports

| Service | Port | Description |
|---------|------|-------------|
| API Server | 8000 | REST API and HTTP endpoints |
| WebSocket | 8001 | Real-time WebSocket connections |
| Dashboard | 3000 | Web-based dashboard UI |
| PostgreSQL | 5432 | Database server (if remote access needed) |

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
   - PostgreSQL port (5432) should only be opened if remote database access is required
   - Consider using SSH tunneling instead of direct PostgreSQL exposure

4. **Regular Audits**:
   - Review firewall rules periodically
   - Remove rules when services are decommissioned
   - Monitor for unauthorized access attempts

## Manual Configuration

If automatic scripts don't work, use these manual commands:

### Windows (PowerShell)
```powershell
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "GiljoAI MCP WebSocket" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

### Linux (UFW)
```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 3000/tcp
```

### macOS (pf)
Add to `/etc/pf.conf`:
```
pass in proto tcp from any to any port 8000
pass in proto tcp from any to any port 8001
pass in proto tcp from any to any port 3000
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
