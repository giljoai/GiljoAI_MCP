# Firewall Configuration Guide - GiljoAI MCP v3.0

**Version**: 3.0.0
**Last Updated**: 2025-10-09
**Applies To**: All deployment contexts (localhost, LAN, WAN)

## Overview

GiljoAI MCP v3.0 uses a unified architecture where the application always binds to `0.0.0.0` (all network interfaces), and the operating system firewall controls who can access the services. This provides defense-in-depth security while maintaining flexibility for different deployment contexts.

### Why Firewall Configuration Matters

- **Localhost Development**: Firewall blocks external access while allowing same-machine connections
- **Team LAN**: Firewall allows specific LAN IP ranges while blocking internet access
- **Internet (WAN)**: Firewall combined with reverse proxy provides enterprise-grade security

### Key Principle

**Network binding is NOT security.** GiljoAI MCP always binds to `0.0.0.0`, but your firewall ensures only authorized clients can connect.

---

## Port Requirements

| Port | Service | Purpose | Required For |
|------|---------|---------|--------------|
| 7272 | API Server | REST API endpoints, MCP server communication | All deployments |
| 7274 | Frontend Dashboard | Vue.js web interface | All deployments |
| 6001 | WebSocket | Real-time agent updates | All deployments |
| 5432 | PostgreSQL | Database (NEVER expose to network) | Localhost only |

**CRITICAL**: PostgreSQL (port 5432) should NEVER be accessible from the network. The API server connects via localhost (`127.0.0.1`) only.

---

## Deployment Context Overview

### Localhost Developer (Default)

**Goal**: Block all external access, allow same-machine only

**Firewall Rules**:
- Block incoming connections to ports 7272, 7274, 6001 from all external IPs
- Allow connections from 127.0.0.1 (localhost)
- Allow connections from ::1 (IPv6 localhost)

**Authentication**: Auto-login for localhost clients (no password required)

**Use Case**: Individual developer working on local machine

---

### Team LAN

**Goal**: Allow specific LAN IP ranges, block internet

**Firewall Rules**:
- Allow incoming connections to ports 7272, 7274, 6001 from LAN subnet (e.g., 192.168.1.0/24)
- Block connections from all other IPs
- Optionally: Restrict to specific team member IPs

**Authentication**: JWT + API keys required for network clients

**Use Case**: Team on local network sharing orchestrator

---

### Internet (WAN)

**Goal**: Public access with enterprise security

**Firewall Rules**:
- Reverse proxy (nginx/Apache) handles HTTPS
- Firewall allows connections to reverse proxy only
- GiljoAI MCP accessed via localhost from reverse proxy
- Rate limiting and DDoS protection at proxy layer

**Authentication**: JWT + API keys + TLS encryption required

**Use Case**: Public-facing service, remote team access

---

## Windows Configuration

### Prerequisites

- Windows 10/11 with Windows Defender Firewall
- PowerShell 5.1 or later
- Administrator privileges

---

### Localhost Developer Configuration

**Goal**: Block external access, allow localhost only

#### Using PowerShell (Recommended)

Run PowerShell as Administrator:

```powershell
# Block external access to API port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - Block External API" `
    -Direction Inbound `
    -Action Block `
    -Protocol TCP `
    -LocalPort 7272 `
    -RemoteAddress Any `
    -Profile Domain,Private,Public

# Allow localhost access to API port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - Allow Localhost API" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 7272 `
    -RemoteAddress 127.0.0.1,::1 `
    -Profile Domain,Private,Public

# Block external access to Dashboard port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - Block External Dashboard" `
    -Direction Inbound `
    -Action Block `
    -Protocol TCP `
    -LocalPort 7274 `
    -RemoteAddress Any `
    -Profile Domain,Private,Public

# Allow localhost access to Dashboard port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - Allow Localhost Dashboard" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 7274 `
    -RemoteAddress 127.0.0.1,::1 `
    -Profile Domain,Private,Public

# Block external access to WebSocket port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - Block External WebSocket" `
    -Direction Inbound `
    -Action Block `
    -Protocol TCP `
    -LocalPort 6001 `
    -RemoteAddress Any `
    -Profile Domain,Private,Public

# Allow localhost access to WebSocket port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - Allow Localhost WebSocket" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 6001 `
    -RemoteAddress 127.0.0.1,::1 `
    -Profile Domain,Private,Public
```

**Verify Rules**:

```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"} | Format-Table DisplayName, Enabled, Direction, Action
```

Expected output:
```
DisplayName                              Enabled Direction Action
-----------                              ------- --------- ------
GiljoAI MCP - Block External API         True    Inbound   Block
GiljoAI MCP - Allow Localhost API        True    Inbound   Allow
GiljoAI MCP - Block External Dashboard   True    Inbound   Block
GiljoAI MCP - Allow Localhost Dashboard  True    Inbound   Allow
GiljoAI MCP - Block External WebSocket   True    Inbound   Block
GiljoAI MCP - Allow Localhost WebSocket  True    Inbound   Allow
```

---

### Team LAN Configuration

**Goal**: Allow LAN subnet (e.g., 192.168.1.0/24), block others

#### Using PowerShell

Replace `192.168.1.0/24` with your actual LAN subnet:

```powershell
# Allow LAN access to API port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - LAN API Access" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 7272 `
    -RemoteAddress 192.168.1.0/24 `
    -Profile Domain,Private

# Allow LAN access to Dashboard port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - LAN Dashboard Access" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 7274 `
    -RemoteAddress 192.168.1.0/24 `
    -Profile Domain,Private

# Allow LAN access to WebSocket port
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - LAN WebSocket Access" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 6001 `
    -RemoteAddress 192.168.1.0/24 `
    -Profile Domain,Private

# Block public network access
New-NetFirewallRule `
    -DisplayName "GiljoAI MCP - Block Public Access" `
    -Direction Inbound `
    -Action Block `
    -Protocol TCP `
    -LocalPort 7272,7274,6001 `
    -Profile Public
```

**Note**: The `Profile` parameter is crucial. `Domain,Private` applies to trusted networks, while `Public` applies to untrusted networks (coffee shops, airports).

---

### Windows Defender Firewall GUI Method

For those who prefer a graphical interface:

1. Press `Win + R`, type `wf.msc`, press Enter
2. Click "Inbound Rules" in left sidebar
3. Click "New Rule" in right sidebar
4. Select "Port", click "Next"
5. Select "TCP", enter port "7272", click "Next"
6. Select "Block the connection" or "Allow the connection" based on context
7. Select appropriate profiles (Domain/Private/Public)
8. Name: "GiljoAI MCP - [Purpose]"
9. Click "Finish"
10. Repeat for ports 7274 and 6001

---

### Testing Windows Firewall Rules

**From the Server**:

```powershell
# Check ports are listening
netstat -ano | findstr "7272 7274 6001"
```

**From a LAN Client**:

```powershell
# Test connectivity (replace with server IP)
Test-NetConnection -ComputerName 192.168.1.100 -Port 7272
Test-NetConnection -ComputerName 192.168.1.100 -Port 7274
```

Expected result: `TcpTestSucceeded : True` if firewall configured correctly

---

### Removing Windows Firewall Rules

```powershell
# List all GiljoAI rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"} | Select-Object DisplayName

# Remove specific rule
Remove-NetFirewallRule -DisplayName "GiljoAI MCP - Block External API"

# Remove all GiljoAI rules at once
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"} | Remove-NetFirewallRule
```

---

## Linux Configuration

### Prerequisites

- Ubuntu 20.04+, Debian 11+, RHEL 8+, CentOS 8+, or compatible
- Root or sudo access
- Firewall service installed (ufw, firewalld, or iptables)

---

### Ubuntu / Debian (using UFW)

UFW (Uncomplicated Firewall) is the default on Ubuntu and Debian systems.

#### Localhost Developer Configuration

```bash
# Enable UFW if not already enabled
sudo ufw enable

# Deny incoming connections by default
sudo ufw default deny incoming

# Allow outgoing connections
sudo ufw default allow outgoing

# Allow localhost connections (UFW doesn't restrict localhost by default)
# No additional rules needed for localhost access

# Deny from external interfaces
sudo ufw deny from any to any port 7272 proto tcp comment 'GiljoAI MCP - Block external API'
sudo ufw deny from any to any port 7274 proto tcp comment 'GiljoAI MCP - Block external Dashboard'
sudo ufw deny from any to any port 6001 proto tcp comment 'GiljoAI MCP - Block external WebSocket'

# Reload firewall
sudo ufw reload

# Check status
sudo ufw status numbered
```

#### Team LAN Configuration

Replace `192.168.1.0/24` with your LAN subnet:

```bash
# Enable UFW
sudo ufw enable

# Allow from LAN subnet
sudo ufw allow from 192.168.1.0/24 to any port 7272 proto tcp comment 'GiljoAI MCP - LAN API'
sudo ufw allow from 192.168.1.0/24 to any port 7274 proto tcp comment 'GiljoAI MCP - LAN Dashboard'
sudo ufw allow from 192.168.1.0/24 to any port 6001 proto tcp comment 'GiljoAI MCP - LAN WebSocket'

# Deny from all other sources
sudo ufw deny from any to any port 7272 proto tcp
sudo ufw deny from any to any port 7274 proto tcp
sudo ufw deny from any to any port 6001 proto tcp

# Reload
sudo ufw reload

# Verify rules
sudo ufw status numbered
```

Expected output:
```
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 7272/tcp                   ALLOW IN    192.168.1.0/24    # GiljoAI MCP - LAN API
[ 2] 7274/tcp                   ALLOW IN    192.168.1.0/24    # GiljoAI MCP - LAN Dashboard
[ 3] 6001/tcp                   ALLOW IN    192.168.1.0/24    # GiljoAI MCP - LAN WebSocket
[ 4] 7272/tcp                   DENY IN     Anywhere
[ 5] 7274/tcp                   DENY IN     Anywhere
[ 6] 6001/tcp                   DENY IN     Anywhere
```

#### Removing UFW Rules

```bash
# List rules with numbers
sudo ufw status numbered

# Delete by number (replace N with actual number)
sudo ufw delete N

# Or delete by rule specification
sudo ufw delete allow from 192.168.1.0/24 to any port 7272
```

---

### RHEL / CentOS / Fedora (using firewalld)

Firewalld is the default on Red Hat-based distributions.

#### Localhost Developer Configuration

```bash
# Start and enable firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Set default zone to drop
sudo firewall-cmd --set-default-zone=drop

# Allow from localhost (lo interface)
sudo firewall-cmd --permanent --zone=trusted --add-interface=lo

# Reload firewall
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-all-zones | grep -A 10 trusted
```

#### Team LAN Configuration

```bash
# Create custom zone for LAN
sudo firewall-cmd --permanent --new-zone=giljoai-lan

# Add LAN subnet to zone
sudo firewall-cmd --permanent --zone=giljoai-lan --add-source=192.168.1.0/24

# Allow GiljoAI ports in LAN zone
sudo firewall-cmd --permanent --zone=giljoai-lan --add-port=7272/tcp
sudo firewall-cmd --permanent --zone=giljoai-lan --add-port=7274/tcp
sudo firewall-cmd --permanent --zone=giljoai-lan --add-port=6001/tcp

# Block in public zone
sudo firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" port port="7272" protocol="tcp" drop'
sudo firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" port port="7274" protocol="tcp" drop'
sudo firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" port port="6001" protocol="tcp" drop'

# Reload firewall
sudo firewall-cmd --reload

# Verify zones
sudo firewall-cmd --list-all-zones | grep -A 10 giljoai-lan
```

#### Removing firewalld Rules

```bash
# List all zones
sudo firewall-cmd --get-zones

# Remove specific rule
sudo firewall-cmd --permanent --zone=giljoai-lan --remove-port=7272/tcp

# Delete custom zone
sudo firewall-cmd --permanent --delete-zone=giljoai-lan

# Reload
sudo firewall-cmd --reload
```

---

### Linux (using iptables directly)

For systems using iptables without a frontend.

#### Localhost Developer Configuration

```bash
# Allow localhost connections (default, typically no action needed)
# Localhost traffic doesn't go through INPUT chain filters

# Block external connections
sudo iptables -A INPUT -p tcp --dport 7272 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 7272 -j DROP
sudo iptables -A INPUT -p tcp --dport 7274 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 7274 -j DROP
sudo iptables -A INPUT -p tcp --dport 6001 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6001 -j DROP

# Save rules (Debian/Ubuntu)
sudo iptables-save | sudo tee /etc/iptables/rules.v4

# Save rules (RHEL/CentOS)
sudo service iptables save
```

#### Team LAN Configuration

```bash
# Allow from LAN subnet
sudo iptables -A INPUT -p tcp --dport 7272 -s 192.168.1.0/24 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 7274 -s 192.168.1.0/24 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6001 -s 192.168.1.0/24 -j ACCEPT

# Deny from all others
sudo iptables -A INPUT -p tcp --dport 7272 -j DROP
sudo iptables -A INPUT -p tcp --dport 7274 -j DROP
sudo iptables -A INPUT -p tcp --dport 6001 -j DROP

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

#### Testing Linux Firewall Rules

```bash
# Check ports are listening
sudo netstat -tlnp | grep -E "7272|7274|6001"

# Or using ss
sudo ss -tlnp | grep -E "7272|7274|6001"

# Or using lsof
sudo lsof -i :7272
sudo lsof -i :7274
sudo lsof -i :6001
```

---

## macOS Configuration

### Prerequisites

- macOS 11 (Big Sur) or later
- Administrator privileges

---

### Method 1: System Settings GUI

**macOS Monterey (12) and later**:

1. Open System Settings
2. Click Network
3. Click Firewall
4. If firewall is off, click Turn On
5. Click Options
6. Click the + (plus) button
7. Navigate to and select the Python binary running GiljoAI:
   - Typical location: `/usr/local/bin/python3`
   - Or use "Browse" to find the `giljo_mcp` process
8. Select "Allow incoming connections"
9. Click OK

**macOS Big Sur and earlier**:

1. Open System Preferences
2. Click Security & Privacy
3. Click Firewall tab
4. Click the lock icon and enter password
5. Click Firewall Options
6. Click the + (plus) button
7. Add Python or GiljoAI application
8. Set to "Allow incoming connections"
9. Click OK

---

### Method 2: Command Line (pf - Packet Filter)

macOS uses `pf` (packet filter) for advanced firewall configuration.

#### Localhost Developer Configuration

1. Create rules file:

```bash
sudo mkdir -p /etc/pf.anchors
sudo nano /etc/pf.anchors/giljoai
```

2. Add these rules:

```
# GiljoAI MCP Firewall Rules - Localhost Only
# Block external access
block in proto tcp from any to any port 7272
block in proto tcp from any to any port 7274
block in proto tcp from any to any port 6001

# Allow localhost
pass in proto tcp from 127.0.0.1 to any port 7272 keep state
pass in proto tcp from 127.0.0.1 to any port 7274 keep state
pass in proto tcp from 127.0.0.1 to any port 6001 keep state
pass in proto tcp from ::1 to any port 7272 keep state
pass in proto tcp from ::1 to any port 7274 keep state
pass in proto tcp from ::1 to any port 6001 keep state
```

3. Save and exit (Control+X, Y, Enter)

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
sudo pfctl -e  # Enable pf (may already be enabled)
sudo pfctl -f /etc/pf.conf  # Reload configuration
```

#### Team LAN Configuration

Modify `/etc/pf.anchors/giljoai`:

```
# GiljoAI MCP Firewall Rules - LAN Access
# Allow from LAN subnet
pass in proto tcp from 192.168.1.0/24 to any port 7272 keep state
pass in proto tcp from 192.168.1.0/24 to any port 7274 keep state
pass in proto tcp from 192.168.1.0/24 to any port 6001 keep state

# Block from all others
block in proto tcp from any to any port 7272
block in proto tcp from any to any port 7274
block in proto tcp from any to any port 6001
```

Reload:

```bash
sudo pfctl -f /etc/pf.conf
```

#### Verifying macOS pf Rules

```bash
# Show all rules
sudo pfctl -s rules

# Show rules for GiljoAI ports
sudo pfctl -s rules | grep -E "7272|7274|6001"

# Show active states
sudo pfctl -s states | grep -E "7272|7274|6001"
```

#### Removing macOS pf Rules

1. Edit `/etc/pf.conf`:

```bash
sudo nano /etc/pf.conf
```

2. Remove these lines:

```
anchor "giljoai"
load anchor "giljoai" from "/etc/pf.anchors/giljoai"
```

3. Reload pf:

```bash
sudo pfctl -f /etc/pf.conf
```

4. Optionally delete anchor file:

```bash
sudo rm /etc/pf.anchors/giljoai
```

---

## Cloud Provider Security Groups

### AWS Security Groups

Security groups act as virtual firewalls for EC2 instances.

#### Creating Security Group

```bash
# Create security group
aws ec2 create-security-group \
    --group-name giljoai-mcp-sg \
    --description "GiljoAI MCP security group" \
    --vpc-id vpc-xxxxxxxx

# Allow SSH (for administration)
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0

# Allow API port from specific IPs
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 7272 \
    --cidr 192.168.1.0/24

# Allow Dashboard port from specific IPs
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 7274 \
    --cidr 192.168.1.0/24

# Allow WebSocket port
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 6001 \
    --cidr 192.168.1.0/24
```

#### AWS Console Method

1. Navigate to EC2 Dashboard
2. Click "Security Groups" in left sidebar
3. Click "Create security group"
4. Name: "giljoai-mcp-sg"
5. Description: "GiljoAI MCP security group"
6. VPC: Select your VPC
7. Add Inbound Rules:
   - Type: Custom TCP, Port: 7272, Source: Custom (192.168.1.0/24)
   - Type: Custom TCP, Port: 7274, Source: Custom (192.168.1.0/24)
   - Type: Custom TCP, Port: 6001, Source: Custom (192.168.1.0/24)
8. Click "Create security group"

---

### Azure Network Security Groups (NSG)

#### Creating NSG via Azure CLI

```bash
# Create NSG
az network nsg create \
    --resource-group giljoai-rg \
    --name giljoai-mcp-nsg \
    --location eastus

# Allow API port
az network nsg rule create \
    --resource-group giljoai-rg \
    --nsg-name giljoai-mcp-nsg \
    --name AllowAPI \
    --priority 100 \
    --source-address-prefixes 192.168.1.0/24 \
    --destination-port-ranges 7272 \
    --protocol Tcp \
    --access Allow

# Allow Dashboard port
az network nsg rule create \
    --resource-group giljoai-rg \
    --nsg-name giljoai-mcp-nsg \
    --name AllowDashboard \
    --priority 110 \
    --source-address-prefixes 192.168.1.0/24 \
    --destination-port-ranges 7274 \
    --protocol Tcp \
    --access Allow

# Allow WebSocket port
az network nsg rule create \
    --resource-group giljoai-rg \
    --nsg-name giljoai-mcp-nsg \
    --name AllowWebSocket \
    --priority 120 \
    --source-address-prefixes 192.168.1.0/24 \
    --destination-port-ranges 6001 \
    --protocol Tcp \
    --access Allow

# Associate NSG with VM network interface
az network nic update \
    --resource-group giljoai-rg \
    --name giljoai-vm-nic \
    --network-security-group giljoai-mcp-nsg
```

#### Azure Portal Method

1. Navigate to Azure Portal
2. Search for "Network security groups"
3. Click "Create"
4. Select Resource Group, Name, Region
5. Click "Review + create"
6. After creation, click the NSG name
7. Click "Inbound security rules"
8. Add rules for ports 7272, 7274, 6001

---

### GCP Firewall Rules

#### Creating Firewall Rules via gcloud CLI

```bash
# Create firewall rule for API port
gcloud compute firewall-rules create giljoai-api \
    --network=default \
    --action=ALLOW \
    --rules=tcp:7272 \
    --source-ranges=192.168.1.0/24 \
    --target-tags=giljoai-instance

# Create firewall rule for Dashboard port
gcloud compute firewall-rules create giljoai-dashboard \
    --network=default \
    --action=ALLOW \
    --rules=tcp:7274 \
    --source-ranges=192.168.1.0/24 \
    --target-tags=giljoai-instance

# Create firewall rule for WebSocket port
gcloud compute firewall-rules create giljoai-websocket \
    --network=default \
    --action=ALLOW \
    --rules=tcp:6001 \
    --source-ranges=192.168.1.0/24 \
    --target-tags=giljoai-instance

# List firewall rules
gcloud compute firewall-rules list | grep giljoai
```

#### GCP Console Method

1. Navigate to GCP Console
2. Go to VPC Network > Firewall
3. Click "Create Firewall Rule"
4. Name: "giljoai-api"
5. Network: default
6. Direction: Ingress
7. Action: Allow
8. Targets: Specified target tags
9. Target tags: giljoai-instance
10. Source IP ranges: 192.168.1.0/24
11. Protocols and ports: tcp:7272
12. Click "Create"
13. Repeat for ports 7274 and 6001

---

## Testing Firewall Configuration

### Server-Side Testing

**Verify ports are listening**:

Windows:
```powershell
netstat -ano | findstr "7272 7274 6001"
```

Linux/macOS:
```bash
sudo netstat -tlnp | grep -E "7272|7274|6001"
# or
sudo ss -tlnp | grep -E "7272|7274|6001"
# or
sudo lsof -i :7272 && sudo lsof -i :7274 && sudo lsof -i :6001
```

Expected: Shows processes listening on these ports

---

### Client-Side Testing

Replace `<SERVER_IP>` with your server's IP address.

#### Using curl

```bash
# Test API health endpoint
curl -v http://<SERVER_IP>:7272/health

# Test Dashboard
curl -v http://<SERVER_IP>:7274

# Test WebSocket (will fail with HTTP but confirms port is open)
curl -v http://<SERVER_IP>:6001
```

Expected responses:
- API: `{"status": "healthy"}`
- Dashboard: HTML content
- WebSocket: Connection upgrade error (normal - WebSocket requires upgrade)

#### Using telnet

```bash
# Test API port
telnet <SERVER_IP> 7272

# Test Dashboard port
telnet <SERVER_IP> 7274

# Test WebSocket port
telnet <SERVER_IP> 6001
```

Expected: "Connected to..." if firewall allows, "Connection refused" if blocked

#### Using nmap (if installed)

```bash
nmap -p 7272,7274,6001 <SERVER_IP>
```

Expected output:
```
PORT     STATE    SERVICE
7272/tcp open     unknown
7274/tcp open     unknown
6001/tcp open     unknown
```

---

### Automated Testing Script

Save as `test-firewall.sh`:

```bash
#!/bin/bash

SERVER_IP=${1:-localhost}

echo "Testing GiljoAI MCP firewall configuration..."
echo "Server: $SERVER_IP"
echo ""

# Test API port
echo -n "Testing API port (7272)... "
if curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP:7272/health | grep -q "200"; then
    echo "OK"
else
    echo "FAILED"
fi

# Test Dashboard port
echo -n "Testing Dashboard port (7274)... "
if curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP:7274 | grep -q "200"; then
    echo "OK"
else
    echo "FAILED"
fi

# Test WebSocket port (will get 426 upgrade required, which is good)
echo -n "Testing WebSocket port (6001)... "
if curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP:6001 | grep -q "426"; then
    echo "OK (Upgrade required - normal)"
else
    echo "FAILED"
fi

echo ""
echo "Testing complete."
```

Usage:

```bash
chmod +x test-firewall.sh
./test-firewall.sh <SERVER_IP>
```

---

## Troubleshooting

### Ports Still Blocked After Configuration

**Symptoms**: Cannot connect even after adding firewall rules

**Solutions**:

1. **Verify rules exist**:
   - Windows: `Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"}`
   - Linux UFW: `sudo ufw status numbered`
   - Linux firewalld: `sudo firewall-cmd --list-all`
   - macOS: `sudo pfctl -s rules | grep -E "7272|7274|6001"`

2. **Check rule order/priority**:
   - DENY rules may be taking precedence over ALLOW rules
   - Move ALLOW rules higher in priority

3. **Verify correct network profile (Windows)**:
   - Check: Settings > Network & Internet > Status > Properties
   - Ensure profile matches firewall rule profile (Domain/Private/Public)

4. **Reload firewall**:
   - Windows: `Restart-Service mpssvc` (PowerShell as Admin)
   - Linux UFW: `sudo ufw reload`
   - Linux firewalld: `sudo firewall-cmd --reload`
   - macOS: `sudo pfctl -f /etc/pf.conf`

5. **Test with firewall temporarily disabled**:
   - Windows: `Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled False`
   - Linux UFW: `sudo ufw disable`
   - Linux firewalld: `sudo systemctl stop firewalld`
   - If works without firewall, issue is with firewall rules

---

### Third-Party Security Software Conflicts

**Symptoms**: System firewall rules correct but still blocked

**Cause**: Third-party firewall/antivirus overriding system firewall

**Solutions**:

**Check for third-party software**:
- Norton, McAfee, Kaspersky, Bitdefender, Avast, AVG, etc.
- Corporate endpoint protection (Symantec, Trend Micro, etc.)

**Configure exceptions**:
- Norton: Settings > Firewall > Program Control > Add Python
- McAfee: Settings > Firewall > Ports and System Services > Add ports
- Kaspersky: Settings > Protection > Firewall > Configure > Add application

**Temporarily disable to test**:
1. Disable third-party security software
2. Test connectivity
3. If works, issue is with third-party software
4. Re-enable and configure exceptions

---

### Application Not Binding to Correct Interface

**Symptoms**: Firewall disabled, still cannot connect from network

**Cause**: Application bound to `127.0.0.1` instead of `0.0.0.0`

**Solution**:

Check `config.yaml`:

```yaml
server:
  api_host: 0.0.0.0  # Must be 0.0.0.0 for network access
  api_port: 7272
```

**Not** `127.0.0.1` or `localhost`.

After changing, restart GiljoAI MCP services.

---

### Network Router Blocking Connections

**Symptoms**: Firewall configured, localhost works, LAN clients cannot connect

**Cause**: Router firewall or VLAN segmentation

**Solutions**:

1. **Check router firewall**:
   - Access router admin panel (usually http://192.168.1.1)
   - Look for firewall/security settings
   - Add exceptions if needed

2. **Check VLAN segmentation**:
   - Ensure server and clients on same VLAN
   - Guest networks often isolated from main network
   - Contact network administrator

3. **Check VPN/Proxy**:
   - Corporate VPNs may block local network access
   - Try disabling VPN temporarily to test

---

### Port Already in Use

**Symptoms**: Services fail to start, "address already in use" error

**Solutions**:

**Find what's using the port**:

Windows:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 7272).OwningProcess
```

Linux/macOS:
```bash
sudo lsof -i :7272
```

**Options**:
1. Stop conflicting service
2. Change GiljoAI MCP port in `config.yaml`
3. Kill process using port (use caution)

---

### IPv6 Connectivity Issues

**Symptoms**: IPv4 works, IPv6 does not

**Solution**:

Ensure firewall rules include both IPv4 and IPv6:

Windows:
```powershell
# Include ::1 for localhost
-RemoteAddress 127.0.0.1,::1
```

Linux UFW:
```bash
# UFW handles IPv6 automatically if enabled in /etc/default/ufw
IPV6=yes
```

Linux iptables:
```bash
# Use ip6tables for IPv6
sudo ip6tables -A INPUT -p tcp --dport 7272 -j ACCEPT
```

macOS pf:
```
# Add IPv6 rules
pass in proto tcp from ::1 to any port 7272 keep state
```

---

## Security Best Practices

### Localhost Developer Context

1. **Block all external access**: Use Block rules for external IPs
2. **Allow localhost only**: Explicitly allow 127.0.0.1 and ::1
3. **Database security**: NEVER expose PostgreSQL (5432) to network
4. **Regular updates**: Keep OS firewall and GiljoAI MCP updated

### Team LAN Context

1. **Use API keys**: Enforce authentication for network clients
2. **Restrict IP ranges**: Allow only specific LAN subnets (e.g., 192.168.1.0/24)
3. **Private network profile**: Use Domain/Private profiles, not Public (Windows)
4. **Monitor access**: Enable firewall logging and review regularly
5. **Don't expose database**: PostgreSQL should only accept localhost connections
6. **Principle of least privilege**: Grant access only to necessary IPs

### Internet (WAN) Context

1. **Use HTTPS reverse proxy**: nginx or Apache with TLS certificates
2. **Firewall + Proxy**: Firewall allows reverse proxy only, proxy forwards to GiljoAI
3. **Strong authentication**: Require complex passwords and API keys
4. **Rate limiting**: Implement connection rate limiting at proxy layer
5. **DDoS protection**: Consider Cloudflare or AWS Shield
6. **Regular security audits**: Review firewall rules and access logs quarterly
7. **Monitoring**: Implement intrusion detection (fail2ban, etc.)
8. **Keep updated**: Apply security patches promptly

### General Recommendations

1. **Principle of least privilege**: Open only necessary ports
2. **Defense in depth**: Combine firewall + authentication + encryption
3. **Regular audits**: Review firewall rules quarterly
4. **Document changes**: Keep record of all firewall modifications
5. **Test after changes**: Always verify connectivity after rule changes
6. **Backup configurations**: Save firewall rule exports before making changes
7. **Use logging**: Enable firewall logging for security monitoring
8. **Stay informed**: Subscribe to security advisories for GiljoAI MCP

---

## Quick Reference

### Port Summary

| Port | Service | Localhost | LAN | WAN |
|------|---------|-----------|-----|-----|
| 7272 | API Server | Allow 127.0.0.1 | Allow LAN subnet | Via reverse proxy |
| 7274 | Dashboard | Allow 127.0.0.1 | Allow LAN subnet | Via reverse proxy |
| 6001 | WebSocket | Allow 127.0.0.1 | Allow LAN subnet | Via reverse proxy |
| 5432 | PostgreSQL | Localhost only | NEVER expose | NEVER expose |

### Common Commands Cheat Sheet

**Windows PowerShell**:
```powershell
# List rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*GiljoAI*"}

# Test connectivity
Test-NetConnection -ComputerName <IP> -Port 7272
```

**Linux UFW**:
```bash
# Status
sudo ufw status numbered

# Allow port
sudo ufw allow 7272/tcp

# Deny port
sudo ufw deny 7272/tcp
```

**Linux firewalld**:
```bash
# Status
sudo firewall-cmd --list-all

# Add port
sudo firewall-cmd --permanent --add-port=7272/tcp

# Reload
sudo firewall-cmd --reload
```

**macOS pf**:
```bash
# Show rules
sudo pfctl -s rules

# Reload config
sudo pfctl -f /etc/pf.conf
```

---

## Related Documentation

- **Migration Guide**: `docs/MIGRATION_GUIDE_V3.md` - Upgrading from v2.x
- **Production Deployment**: `docs/deployment/PRODUCTION_DEPLOYMENT_V3.md` - Deployment procedures
- **Known Issues**: `docs/KNOWN_ISSUES.md` - Known issues and workarounds
- **Release Notes**: `docs/RELEASE_NOTES_V3.0.0.md` - What's new in v3.0
- **Troubleshooting**: `docs/deployment/TROUBLESHOOTING_GUIDE.md` - General troubleshooting

---

**Maintained By**: Documentation Manager Agent
**Version**: 3.0.0
**Last Updated**: 2025-10-09
**Next Review**: v3.1.0 release
