# GiljoAI MCP Server Mode - Quick Start Guide

## Overview

Server mode enables GiljoAI MCP to be deployed on a network, accessible by multiple users and remote clients. This guide covers installation and configuration.

## Prerequisites

- Python 3.8+
- PostgreSQL 18
- Administrator/root access for firewall configuration
- SSL certificates (optional, can be auto-generated)

## Installation Options

### Option 1: Interactive Installation (Recommended)

```bash
python installer/cli/install.py --mode server
```

The installer will guide you through:
1. PostgreSQL configuration
2. Service port selection
3. Network binding (bind address)
4. SSL setup (self-signed or existing certificates)
5. Admin user creation
6. API key generation

### Option 2: Batch Installation (Automation)

**Minimal Server Setup:**
```bash
python installer/cli/install.py \
  --mode server \
  --batch \
  --pg-password YOUR_PG_PASSWORD \
  --bind 0.0.0.0 \
  --admin-username admin \
  --admin-password YOUR_ADMIN_PASSWORD
```

**With SSL (Self-Signed):**
```bash
python installer/cli/install.py \
  --mode server \
  --batch \
  --pg-password YOUR_PG_PASSWORD \
  --bind 0.0.0.0 \
  --enable-ssl \
  --admin-username admin \
  --admin-password YOUR_ADMIN_PASSWORD \
  --generate-api-key
```

**With Existing SSL Certificates:**
```bash
python installer/cli/install.py \
  --mode server \
  --batch \
  --pg-password YOUR_PG_PASSWORD \
  --bind 0.0.0.0 \
  --enable-ssl \
  --ssl-cert /path/to/server.crt \
  --ssl-key /path/to/server.key \
  --admin-username admin \
  --admin-password YOUR_ADMIN_PASSWORD \
  --generate-api-key
```

## Post-Installation: Firewall Configuration

**CRITICAL**: Firewall rules must be applied manually for security.

### Windows (Run as Administrator)

```powershell
cd installer\scripts\firewall
powershell -ExecutionPolicy Bypass -File configure_windows_firewall.ps1
```

### Linux (Ubuntu/Debian - UFW)

```bash
cd installer/scripts/firewall
sudo bash configure_ufw_firewall.sh
```

### Linux (RHEL/CentOS - iptables)

```bash
cd installer/scripts/firewall
sudo bash configure_iptables_firewall.sh
```

### macOS

```bash
cd installer/scripts/firewall
sudo bash configure_macos_firewall.sh
```

## Starting the Server

After installation and firewall configuration:

```bash
python launchers/start_giljo.py
```

Or use platform-specific launchers:
- Windows: `launchers\start_giljo.bat`
- Unix: `./launchers/start_giljo.sh`

## Accessing the Server

### Local Access
- Dashboard: `https://localhost:7274` (or `http://` if SSL disabled)
- API: `https://localhost:7272/docs`
- WebSocket: `wss://localhost:7272/ws`

### Remote Access
- Dashboard: `https://SERVER_IP:7274`
- API: `https://SERVER_IP:7272/docs`
- WebSocket: `wss://SERVER_IP:7272/ws`

Replace `SERVER_IP` with your server's IP address or hostname.

## Configuration Files

After installation, you'll find:

```
.env                        # Environment variables
config.yaml                 # Installation configuration
.admin_credentials          # Admin user credentials (keep secure!)
api_keys.json              # API keys (if generated)
certs/server.crt           # SSL certificate (if SSL enabled)
certs/server.key           # SSL private key (if SSL enabled)
firewall_rules.txt         # Firewall summary
```

## Security Checklist

### Before Going Live

- [ ] SSL/TLS enabled for production
- [ ] Firewall rules applied and verified
- [ ] Strong admin password set (12+ characters)
- [ ] API keys generated and securely stored
- [ ] PostgreSQL listening on correct interface
- [ ] Services binding to intended address
- [ ] Security warnings reviewed and addressed

### Production Best Practices

1. **Always use SSL/TLS** - Never expose unencrypted HTTP to the network
2. **Strong Passwords** - Use password managers for admin credentials
3. **API Key Security** - Treat API keys like passwords, never commit to git
4. **Regular Updates** - Keep certificates, dependencies, and OS updated
5. **Access Logs** - Monitor access logs for suspicious activity
6. **Backup Credentials** - Store admin credentials and API keys securely
7. **Network Segmentation** - Use VLANs or subnets to isolate services
8. **Reverse Proxy** - Consider nginx/Apache for additional security

## Common Ports

| Service | Default Port | Protocol | Purpose |
|---------|-------------|----------|---------|
| API | 7272 | TCP | REST API endpoints |
| WebSocket | 7272 | TCP | Real-time connections (same as API) |
| Dashboard | 7274 | TCP | Web UI |
| PostgreSQL | 5432 | TCP | Database (optional network access) |

## Troubleshooting

### Cannot Access Server Remotely

1. **Check firewall rules:**
   - Windows: `Get-NetFirewallRule -DisplayName "GiljoAI*"`
   - Linux (UFW): `sudo ufw status verbose`
   - Linux (iptables): `sudo iptables -L -n -v`
   - macOS: `sudo pfctl -s rules`

2. **Verify services are listening:**
   ```bash
   netstat -tuln | grep LISTEN  # Linux/macOS
   netstat -an | findstr LISTENING  # Windows
   ```

3. **Check bind address in config.yaml:**
   Should be `0.0.0.0` for network access, not `127.0.0.1`

4. **Test port connectivity:**
   ```bash
   telnet SERVER_IP 7272
   # or
   nc -zv SERVER_IP 7272
   ```

### SSL Certificate Issues

1. **Self-signed certificate warnings in browser:**
   - Normal for self-signed certificates
   - Add exception in browser or install certificate in system trust store
   - For production, use Let's Encrypt or commercial CA

2. **Certificate generation failed:**
   - Install cryptography library: `pip install cryptography`
   - Or ensure OpenSSL is available: `openssl version`

3. **Certificate expired:**
   - Self-signed certificates are valid for 365 days
   - Regenerate with: `python -c "from installer.core.network import NetworkManager; ..."`

### Admin Login Issues

1. **Forgot admin password:**
   - Check `.admin_credentials` file (JSON format)
   - Password is hashed, cannot be recovered
   - Create new admin user manually in database

2. **API key not working:**
   - Check `api_keys.json` for active keys
   - Ensure key is prefixed with `gai_`
   - Verify key is marked as `active: true`

### Database Connection Issues

1. **PostgreSQL not accessible:**
   - Verify PostgreSQL is running
   - Check `pg_hba.conf` for network access rules
   - Ensure PostgreSQL is listening on correct interface

2. **Connection refused:**
   - Check `.env` file for correct connection details
   - Verify database `giljo_mcp` exists
   - Test connection: `psql -h HOST -U giljo_user -d giljo_mcp`

## Advanced Configuration

### Custom Ports

Edit `config.yaml` after installation and restart services:

```yaml
services:
  bind: 0.0.0.0
  api_port: 9000      # Change from 7272
  dashboard_port: 4000  # Change from 7274
```

### IP Whitelisting (Future)

Currently, firewall rules allow all IPs. To restrict:

**Windows (PowerShell):**
```powershell
New-NetFirewallRule -DisplayName "GiljoAI API Restricted" `
  -Direction Inbound -LocalPort 7272 -Protocol TCP -Action Allow `
  -RemoteAddress 192.168.1.0/24
```

**Linux (iptables):**
```bash
iptables -A INPUT -p tcp --dport 7272 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 7272 -j DROP
```

### Using a Reverse Proxy

Example nginx configuration in `installer/configs/nginx.conf.example` after installation.

## Getting Help

1. **Documentation:** See `docs/` directory
2. **Firewall Help:** `installer/scripts/firewall/README.md`
3. **Installation Logs:** `install_logs/install_server_TIMESTAMP.log`
4. **Service Logs:** `logs/giljo.log`

## Security Disclosure

Found a security issue? Please report to security@giljoai.com (do not create public issues for security vulnerabilities).

---

**Remember:** Server mode exposes services to the network. Always prioritize security!
