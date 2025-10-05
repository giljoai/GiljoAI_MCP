# Firewall Configuration for LAN Mode

**Version**: 2.0.0
**Last Updated**: October 5, 2025
**Applies To**: LAN and WAN deployment modes

## Overview

When running GiljoAI MCP in LAN or WAN mode, you must configure your firewall to allow incoming connections on the API and Dashboard ports. This guide provides step-by-step instructions for Windows, Linux, and macOS.

## Ports to Configure

| Port | Service | Purpose | Required For |
|------|---------|---------|--------------|
| **7272** | API Backend | REST API, MCP server communication | All modes |
| **7274** | Dashboard | Web interface | All modes |
| **5432** | PostgreSQL | Database (only if remote access needed) | Optional |

**Note**: Port 5432 (PostgreSQL) should typically NOT be exposed on the network for security reasons. GiljoAI API handles all database access.

## Quick Setup

### Automated Setup (Setup Wizard)

The GiljoAI Setup Wizard (Phase 0) provides platform-specific commands and automated testing:

1. Run installer: `python install.py`
2. Select LAN or WAN deployment mode
3. Wizard displays firewall commands for your OS
4. Copy and run the commands
5. Click "Test Connectivity" to verify

### Manual Setup

Follow the instructions below for your operating system.

---

## Windows Configuration

### Method 1: PowerShell (Recommended)

**Prerequisites**:
- PowerShell running as Administrator
- Windows Defender Firewall enabled

**Commands**:

```powershell
# Allow API port (7272)
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -Protocol TCP -LocalPort 7272 -Action Allow -Profile Domain,Private

# Allow Dashboard port (7274)
New-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard" -Direction Inbound -Protocol TCP -LocalPort 7274 -Action Allow -Profile Domain,Private
```

**Explanation**:
- `DisplayName`: Name shown in firewall rules list
- `Direction Inbound`: Allows incoming connections
- `Protocol TCP`: Uses TCP protocol
- `LocalPort`: The port number to open
- `Action Allow`: Permits traffic
- `Profile Domain,Private`: Applies to domain and private networks (not public)

**Verify Rules Created**:

```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"}
```

Expected output:
```
Name                  DisplayName           Enabled  Direction  Action
----                  -----------           -------  ---------  ------
{GUID}                GiljoAI MCP API       True     Inbound    Allow
{GUID}                GiljoAI MCP Dashboard True     Inbound    Allow
```

**Remove Rules** (if needed):

```powershell
Remove-NetFirewallRule -DisplayName "GiljoAI MCP API"
Remove-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard"
```

---

### Method 2: Windows Defender Firewall GUI

**Step-by-Step**:

1. **Open Windows Defender Firewall**:
   - Press `Win + R`
   - Type: `wf.msc`
   - Press Enter

2. **Create Inbound Rule for API (Port 7272)**:
   - Click "Inbound Rules" in left sidebar
   - Click "New Rule" in right sidebar
   - Select "Port" → Click "Next"
   - Select "TCP" → Select "Specific local ports" → Enter: `7272` → Click "Next"
   - Select "Allow the connection" → Click "Next"
   - Check "Domain" and "Private" (uncheck "Public" for security) → Click "Next"
   - Name: `GiljoAI MCP API` → Click "Finish"

3. **Create Inbound Rule for Dashboard (Port 7274)**:
   - Click "New Rule" again
   - Select "Port" → Click "Next"
   - Select "TCP" → Select "Specific local ports" → Enter: `7274` → Click "Next"
   - Select "Allow the connection" → Click "Next"
   - Check "Domain" and "Private" → Click "Next"
   - Name: `GiljoAI MCP Dashboard` → Click "Finish"

4. **Verify Rules**:
   - In "Inbound Rules" list, scroll to find "GiljoAI MCP API" and "GiljoAI MCP Dashboard"
   - Both should show:
     - Enabled: Yes
     - Action: Allow
     - Profile: Domain, Private

**Screenshots** (what you should see):
- *Inbound Rules screen showing two rules: "GiljoAI MCP API" (Port 7272) and "GiljoAI MCP Dashboard" (Port 7274), both enabled with green checkmarks*

---

### Method 3: Command Prompt (netsh)

**Run Command Prompt as Administrator**, then:

```cmd
REM API port
netsh advfirewall firewall add rule name="GiljoAI MCP API" dir=in action=allow protocol=TCP localport=7272 profile=domain,private

REM Dashboard port
netsh advfirewall firewall add rule name="GiljoAI MCP Dashboard" dir=in action=allow protocol=TCP localport=7274 profile=domain,private
```

**Verify**:

```cmd
netsh advfirewall firewall show rule name=all | findstr /C:"GiljoAI"
```

**Remove** (if needed):

```cmd
netsh advfirewall firewall delete rule name="GiljoAI MCP API"
netsh advfirewall firewall delete rule name="GiljoAI MCP Dashboard"
```

---

## Linux Configuration

### Ubuntu / Debian (using UFW)

UFW (Uncomplicated Firewall) is the default firewall on Ubuntu and Debian.

**Check UFW Status**:

```bash
sudo ufw status
```

If UFW is inactive, enable it:

```bash
sudo ufw enable
```

**Add Firewall Rules**:

```bash
# Allow API port
sudo ufw allow 7272/tcp comment 'GiljoAI MCP API'

# Allow Dashboard port
sudo ufw allow 7274/tcp comment 'GiljoAI MCP Dashboard'
```

**Reload Firewall**:

```bash
sudo ufw reload
```

**Verify Rules**:

```bash
sudo ufw status numbered
```

Expected output:
```
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 7272/tcp                   ALLOW IN    Anywhere                   # GiljoAI MCP API
[ 2] 7274/tcp                   ALLOW IN    Anywhere                   # GiljoAI MCP Dashboard
```

**Remove Rules** (if needed):

```bash
sudo ufw delete allow 7272/tcp
sudo ufw delete allow 7274/tcp
```

Or by number (from numbered status):

```bash
sudo ufw delete 1  # Delete rule #1
sudo ufw delete 2  # Delete rule #2
```

---

### RHEL / CentOS / Fedora (using firewalld)

Firewalld is the default firewall on RHEL-based distributions.

**Check Firewalld Status**:

```bash
sudo systemctl status firewalld
```

If not running:

```bash
sudo systemctl start firewalld
sudo systemctl enable firewalld
```

**Add Firewall Rules**:

```bash
# Allow API port
sudo firewall-cmd --permanent --add-port=7272/tcp --zone=public

# Allow Dashboard port
sudo firewall-cmd --permanent --add-port=7274/tcp --zone=public
```

**Reload Firewall**:

```bash
sudo firewall-cmd --reload
```

**Verify Rules**:

```bash
sudo firewall-cmd --list-ports
```

Expected output:
```
7272/tcp 7274/tcp
```

**Remove Rules** (if needed):

```bash
sudo firewall-cmd --permanent --remove-port=7272/tcp
sudo firewall-cmd --permanent --remove-port=7274/tcp
sudo firewall-cmd --reload
```

---

### Linux (using iptables)

For systems using iptables directly (older or minimal installations).

**Add Rules**:

```bash
# Allow API port
sudo iptables -A INPUT -p tcp --dport 7272 -j ACCEPT

# Allow Dashboard port
sudo iptables -A INPUT -p tcp --dport 7274 -j ACCEPT
```

**Save Rules** (Debian/Ubuntu):

```bash
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

**Save Rules** (RHEL/CentOS):

```bash
sudo service iptables save
```

**Verify Rules**:

```bash
sudo iptables -L -n | grep -E "7272|7274"
```

Expected output:
```
ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0            tcp dpt:7272
ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0            tcp dpt:7274
```

**Remove Rules** (if needed):

```bash
sudo iptables -D INPUT -p tcp --dport 7272 -j ACCEPT
sudo iptables -D INPUT -p tcp --dport 7274 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4  # Save changes
```

---

## macOS Configuration

### Method 1: System Preferences (GUI)

**macOS Monterey and later**:

1. Open **System Settings**
2. Click **Network**
3. Click **Firewall**
4. If firewall is off, click **Turn On**
5. Click **Options**
6. Click **+** (plus button)
7. Navigate to and select the Python binary:
   - Typical location: `/usr/local/bin/python3` or application bundle
   - Or select "GiljoAI MCP" if it appears in applications
8. Select **Allow incoming connections**
9. Click **OK**

**macOS Big Sur and earlier**:

1. Open **System Preferences**
2. Click **Security & Privacy**
3. Click **Firewall** tab
4. Click the lock icon and authenticate
5. Click **Firewall Options**
6. Click **+** (plus button)
7. Add Python or GiljoAI application
8. Set to **Allow incoming connections**
9. Click **OK**

---

### Method 2: Command Line (pf)

macOS uses `pf` (packet filter) for advanced firewall configuration.

**Create PF Anchor**:

1. Create rules file:

```bash
sudo nano /etc/pf.anchors/giljoai
```

2. Add these rules:

```
# GiljoAI MCP Firewall Rules
pass in proto tcp from any to any port 7272 keep state
pass in proto tcp from any to any port 7274 keep state
```

3. Save and exit (Ctrl+X, Y, Enter)

4. Edit main pf configuration:

```bash
sudo nano /etc/pf.conf
```

5. Add at the end:

```
# Load GiljoAI anchor
anchor "giljoai"
load anchor "giljoai" from "/etc/pf.anchors/giljoai"
```

6. Save and exit

7. Enable and reload pf:

```bash
sudo pfctl -e  # Enable pf
sudo pfctl -f /etc/pf.conf  # Reload configuration
```

**Verify Rules**:

```bash
sudo pfctl -s rules | grep 7272
sudo pfctl -s rules | grep 7274
```

**Disable GiljoAI Rules** (if needed):

Edit `/etc/pf.conf`, remove the anchor lines, then:

```bash
sudo pfctl -f /etc/pf.conf
```

---

## Testing Firewall Configuration

### From the Server Itself

**Test ports are listening**:

Windows:
```powershell
netstat -ano | findstr "7272 7274"
```

Linux/macOS:
```bash
sudo netstat -tlnp | grep -E "7272|7274"
# or
sudo lsof -i :7272
sudo lsof -i :7274
```

Expected output shows Python/uvicorn listening on these ports.

---

### From a Client Machine (LAN)

**Prerequisites**:
- Know server IP address (e.g., 192.168.1.100)
- Client and server on same network

**Test with browser**:

1. On client machine, open web browser
2. Navigate to: `http://192.168.1.100:7274`
3. Should see GiljoAI Dashboard

If Dashboard doesn't load:
- Firewall blocking connection
- Wrong IP address
- Server not running
- Network routing issue

**Test with curl** (command line):

```bash
# Test Dashboard port
curl -v http://192.168.1.100:7274

# Test API port
curl -v http://192.168.1.100:7272/health
```

Expected response:
- Dashboard: HTML content
- API: `{"status": "healthy"}`

If connection refused:
- Firewall blocking
- Server not running on that IP

If connection timeout:
- Network routing issue
- Server on different network

**Test with telnet**:

Windows:
```cmd
telnet 192.168.1.100 7272
```

Linux/macOS:
```bash
telnet 192.168.1.100 7272
```

If connected successfully: "Connected to..."
If refused: Firewall or service not running
If timeout: Network routing issue

---

### Using Setup Wizard

The Setup Wizard (Phase 0) includes automated connectivity testing:

1. Complete firewall configuration steps
2. Click "Test Connectivity" button in wizard
3. Wizard performs:
   - Port accessibility check from server perspective
   - Service availability verification
   - Network routing validation

Results show:
- ✓ Green: Port accessible
- ✗ Red: Port blocked (firewall issue)

---

## Advanced Configuration

### Restricting Access by IP Address

For enhanced security, limit connections to specific IP addresses or ranges.

**Windows PowerShell**:

```powershell
# Allow only from specific IP
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -Protocol TCP -LocalPort 7272 -RemoteAddress 192.168.1.0/24 -Action Allow
```

`RemoteAddress 192.168.1.0/24` = Only allow from 192.168.1.0-192.168.1.255

**Linux UFW**:

```bash
# Allow only from specific IP range
sudo ufw allow from 192.168.1.0/24 to any port 7272 proto tcp
sudo ufw allow from 192.168.1.0/24 to any port 7274 proto tcp
```

**Linux firewalld**:

```bash
# Create rich rule for IP restriction
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port port="7272" protocol="tcp" accept'
sudo firewall-cmd --reload
```

---

### Rate Limiting

Protect against abuse by limiting connection rate.

**Linux iptables**:

```bash
# Limit to 10 connections per minute per IP
sudo iptables -A INPUT -p tcp --dport 7272 -m state --state NEW -m recent --set
sudo iptables -A INPUT -p tcp --dport 7272 -m state --state NEW -m recent --update --seconds 60 --hitcount 10 -j DROP
sudo iptables -A INPUT -p tcp --dport 7272 -j ACCEPT
```

**Linux firewalld**:

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" port port="7272" protocol="tcp" limit value="10/m" accept'
sudo firewall-cmd --reload
```

---

### Logging Connections

Log firewall activity for security monitoring.

**Windows**:

```powershell
Set-NetFirewallRule -DisplayName "GiljoAI MCP API" -LogBlocked True -LogAllowed True
```

Logs location: `%SystemRoot%\System32\LogFiles\Firewall\pfirewall.log`

**Linux UFW**:

```bash
sudo ufw logging on
```

Logs location: `/var/log/ufw.log`

**Linux firewalld**:

```bash
sudo firewall-cmd --set-log-denied=all
```

Logs location: `/var/log/messages` or `journalctl -u firewalld`

---

## Troubleshooting

### Firewall Rules Not Working

**Symptoms**: Ports still blocked after adding rules

**Solutions**:

1. **Verify rules created correctly**:
   - Windows: Check `wf.msc` GUI
   - Linux: Run status commands shown above

2. **Check rule priority**:
   - Earlier DENY rules may override ALLOW rules
   - Move GiljoAI rules higher in priority

3. **Verify correct network profile** (Windows):
   - Rules must apply to active profile (Domain/Private/Public)
   - Check: Control Panel → Network and Sharing Center

4. **Restart firewall service**:
   - Windows: `Restart-Service mpssvc`
   - Linux UFW: `sudo ufw reload`
   - Linux firewalld: `sudo firewall-cmd --reload`

---

### Third-Party Firewall Software

**Symptoms**: Rules added but still blocked

**Cause**: Third-party firewall (Norton, McAfee, Kaspersky, etc.) overriding system firewall

**Solutions**:

1. **Check third-party firewall settings**:
   - Open security software
   - Find firewall/network protection settings
   - Add exceptions for ports 7272 and 7274

2. **Temporarily disable to test**:
   - Disable third-party firewall
   - Test connectivity
   - If works, configure third-party firewall
   - Re-enable

3. **Common products**:
   - **Norton**: Settings → Firewall → Program Control → Add
   - **McAfee**: Settings → Firewall → Ports and System Services
   - **Kaspersky**: Settings → Protection → Firewall → Configure
   - **Windows Security**: Already covered above

---

### Network Router/Gateway Blocking

**Symptoms**: Firewall configured but external clients can't connect

**Cause**: Router firewall or network segmentation

**Solutions**:

1. **Check router firewall**:
   - Access router admin panel (usually http://192.168.1.1)
   - Look for firewall or security settings
   - Add exceptions for ports if needed

2. **Check network segmentation**:
   - VLANs may prevent inter-network communication
   - Guest networks often isolated from main network
   - Contact network administrator

3. **Port forwarding** (WAN mode only):
   - Configure router to forward external ports to server IP
   - External port → Internal port 7272/7274

---

### Firewall Disabled But Still Blocked

**Symptoms**: Firewall completely disabled but can't connect

**Causes**:

1. **Service not running**:
   - Check GiljoAI services are actually running
   - Test with `curl localhost:7272/health` on server

2. **Binding to wrong interface**:
   - Application must bind to `0.0.0.0` (all interfaces) not `127.0.0.1` (localhost only)
   - Check `config.yaml` → `server.host` setting

3. **Antivirus network protection**:
   - Some antivirus software has network protection separate from firewall
   - Check antivirus settings

---

## Security Best Practices

### For LAN Deployments

1. **Use API Keys**: Always enable API key authentication in LAN mode
2. **Restrict IP Ranges**: Use IP-based firewall rules to limit access
3. **Private Network Only**: Apply rules to "Private" network profile only (Windows)
4. **Monitor Access**: Enable firewall logging and review regularly
5. **Don't Expose Database**: Never open port 5432 to network

### For WAN Deployments

1. **HTTPS Required**: Use HTTPS reverse proxy (nginx, Apache)
2. **Strong Authentication**: Require strong passwords and API keys
3. **Rate Limiting**: Implement connection rate limiting
4. **DDoS Protection**: Consider Cloudflare or similar service
5. **Regular Updates**: Keep GiljoAI and dependencies updated
6. **Monitoring**: Implement intrusion detection (fail2ban, etc.)

### General Recommendations

1. **Principle of Least Privilege**: Open only necessary ports
2. **Regular Audits**: Review firewall rules quarterly
3. **Document Changes**: Keep record of firewall modifications
4. **Test After Changes**: Always test connectivity after rule changes
5. **Backup Configurations**: Save firewall rule exports

---

## Quick Reference Commands

### Windows PowerShell

```powershell
# Add rules
New-NetFirewallRule -DisplayName "GiljoAI MCP API" -Direction Inbound -Protocol TCP -LocalPort 7272 -Action Allow -Profile Domain,Private
New-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard" -Direction Inbound -Protocol TCP -LocalPort 7274 -Action Allow -Profile Domain,Private

# View rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"}

# Remove rules
Remove-NetFirewallRule -DisplayName "GiljoAI MCP API"
Remove-NetFirewallRule -DisplayName "GiljoAI MCP Dashboard"
```

### Linux (UFW)

```bash
# Add rules
sudo ufw allow 7272/tcp comment 'GiljoAI MCP API'
sudo ufw allow 7274/tcp comment 'GiljoAI MCP Dashboard'
sudo ufw reload

# View rules
sudo ufw status numbered

# Remove rules
sudo ufw delete allow 7272/tcp
sudo ufw delete allow 7274/tcp
```

### Linux (firewalld)

```bash
# Add rules
sudo firewall-cmd --permanent --add-port=7272/tcp
sudo firewall-cmd --permanent --add-port=7274/tcp
sudo firewall-cmd --reload

# View rules
sudo firewall-cmd --list-ports

# Remove rules
sudo firewall-cmd --permanent --remove-port=7272/tcp
sudo firewall-cmd --permanent --remove-port=7274/tcp
sudo firewall-cmd --reload
```

---

## Related Documentation

- **[Setup Wizard Guide](../guides/SETUP_WIZARD_GUIDE.md)** - Automated firewall setup
- **[LAN Quick Start](LAN_QUICK_START.md)** - LAN deployment guide
- **[LAN Deployment Runbook](LAN_DEPLOYMENT_RUNBOOK.md)** - Complete LAN operations
- **[Security Fixes Report](SECURITY_FIXES_REPORT.md)** - Security implementation details
- **[Network Deployment Checklist](NETWORK_DEPLOYMENT_CHECKLIST.md)** - Pre-deployment checklist

---

**Last Updated**: October 5, 2025
**Version**: 2.0.0
**Maintained By**: Documentation Manager Agent
