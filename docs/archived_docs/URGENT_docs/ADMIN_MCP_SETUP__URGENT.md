# Admin Guide: MCP Integration Setup

**Last Updated:** 2025-10-09  
**Version:** 3.0  
**Audience:** Team Administrators and IT Staff

---

## Overview

This guide helps team administrators deploy GiljoAI MCP integration to their development teams. Whether you're onboarding a small team or managing enterprise-wide deployment, this guide covers distribution strategies, security best practices, and troubleshooting.

### Administrator Responsibilities

- Generate and distribute installer scripts
- Manage API keys and access control
- Monitor successful installations
- Provide technical support to team members
- Maintain security and compliance standards

### Deployment Scenarios

This guide covers:
- **Small Teams (2-10 developers):** Share link distribution via email
- **Medium Teams (10-50 developers):** Centralized installer hosting
- **Large Organizations (50+ developers):** Automated deployment pipelines

---

## Prerequisites

### System Requirements

- **GiljoAI MCP Server:** Installed and running
- **Admin Account:** Dashboard access with appropriate permissions
- **Network Access:** Team members can reach the server
- **Python 3.11+:** Available on all developer machines

### Access Requirements

**Localhost Mode:**
- Direct access to dashboard at `http://localhost:7274`
- No API key management needed

**LAN Mode:**
- Network-accessible dashboard (e.g., `http://10.1.0.164:7274`)
- API key generation capability
- User management permissions

**WAN Mode:**
- Public-facing dashboard with HTTPS
- OAuth provider configured
- Rate limiting configured
- API key management system

---

## Generating Installer Scripts

### Method 1: Via Dashboard (Recommended)

The easiest way to generate installer scripts for distribution.

#### Step-by-Step

1. **Login to Dashboard**
   ```
   http://localhost:7274  # Localhost
   http://10.1.0.164:7274 # LAN
   https://your-domain.com # WAN
   ```

2. **Navigate to MCP Integration**
   - Click **Settings** in sidebar
   - Select **MCP Integration** tab
   - You'll see download options

3. **Choose Download Method**

   **Option A: Direct Download (For Immediate Use)**
   - Click "Download for Windows" → saves `giljo-mcp-setup.bat`
   - Click "Download for macOS/Linux" → saves `giljo-mcp-setup.sh`
   - Script contains your credentials pre-embedded
   - Share file directly with team members

   **Option B: Generate Share Link (Recommended)**
   - Click "Generate Share Link"
   - Receive URLs for both platforms:
     ```
     Windows: http://localhost:7272/download/mcp/{token}/windows
     Unix: http://localhost:7272/download/mcp/{token}/unix
     ```
   - Share links expire after 7 days
   - Team members download fresh scripts with their own credentials

4. **Distribute to Team**
   - Email share links (see email template below)
   - Post in team chat (Slack, Teams, etc.)
   - Add to onboarding documentation

### Method 2: Via API (Programmatic)

For automated workflows and CI/CD integration.

#### Generate Share Link

```bash
# Using curl
curl -X POST "http://localhost:7272/api/mcp-installer/share-link" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Response
{
  "windows_url": "http://localhost:7272/download/mcp/{token}/windows",
  "unix_url": "http://localhost:7272/download/mcp/{token}/unix",
  "expires_at": "2025-10-16T14:30:22Z",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Direct Download

```bash
# Windows installer
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:7272/api/mcp-installer/windows \
  -o giljo-mcp-setup.bat

# Unix installer
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:7272/api/mcp-installer/unix \
  -o giljo-mcp-setup.sh
```

See [MCP Installer API Reference](../api/MCP_INSTALLER_API.md) for complete API documentation.

---

## Distribution Methods

### Method 1: Email Distribution (Small Teams)

**Best for:** 2-10 developers, manual onboarding

**Advantages:**
- Personal touch
- Track individual installations
- Easy to provide support

**Process:**

1. Generate share link via dashboard
2. Use email template (see below)
3. Send to each team member
4. Follow up to confirm installation
5. Provide support as needed

**Email Template:**

```
Subject: GiljoAI MCP Setup - Action Required

Hi [Developer Name],

Welcome to the team! To set up your development environment with 
GiljoAI MCP integration, please follow these steps:

1. Download the installer for your operating system:
   - Windows: [WINDOWS_SHARE_LINK]
   - macOS/Linux: [UNIX_SHARE_LINK]

2. Run the installer script:
   
   Windows:
   - Double-click the downloaded .bat file
   - OR open Command Prompt and run: giljo-mcp-setup.bat
   
   macOS/Linux:
   - Open Terminal
   - Run: chmod +x giljo-mcp-setup.sh
   - Run: ./giljo-mcp-setup.sh

3. Restart your development tools (Claude Code, Cursor, or Windsurf)

4. Verify installation by checking for GiljoAI MCP tools

IMPORTANT: These links expire on [EXPIRY_DATE]. If you need a new 
link after expiration, please contact me.

Need help? Check the user guide: [LINK_TO_MCP_INTEGRATION_GUIDE.md]
Or reach out to me directly.

Server Details:
- Dashboard: http://[SERVER_IP]:7274
- API: http://[SERVER_IP]:7272
- Your Username: [USERNAME]

Best regards,
[Your Name]
[Your Title]
```

### Method 2: Shared File Server (Medium Teams)

**Best for:** 10-50 developers, centralized management

**Advantages:**
- Single source of truth
- Easy to update scripts
- Self-service installation
- Audit trail

**Setup:**

1. **Create shared folder on file server**
   ```
   \\fileserver\shared\giljo-mcp\
   ├── installers\
   │   ├── windows\
   │   │   └── giljo-mcp-setup.bat
   │   └── unix\
   │       └── giljo-mcp-setup.sh
   ├── README.txt
   └── USER_GUIDE.pdf
   ```

2. **Set permissions**
   - Read-only access for all developers
   - Write access for IT/admin team

3. **Update onboarding docs**
   ```markdown
   ## GiljoAI MCP Setup
   
   1. Navigate to: \\fileserver\shared\giljo-mcp\
   2. Download installer for your OS
   3. Run the installer
   4. Restart development tools
   ```

4. **Maintain scripts**
   - Regenerate weekly (before expiry)
   - Update README when server details change
   - Monitor access logs

### Method 3: Automated Deployment (Large Organizations)

**Best for:** 50+ developers, enterprise environments

**Advantages:**
- Zero-touch deployment
- Consistent configuration
- Centralized monitoring
- Policy enforcement

**Deployment Options:**

#### A. Group Policy (Windows Enterprise)

```powershell
# Deploy via GPO startup script
# Location: \\domain.com\NETLOGON\giljo-mcp-deploy.ps1

# Download latest installer
$installerUrl = "http://giljo-server:7272/api/mcp-installer/windows"
$installerPath = "$env:TEMP\giljo-mcp-setup.bat"
$apiKey = "ENTERPRISE_API_KEY"  # Use service account key

Invoke-WebRequest -Uri $installerUrl `
    -Headers @{"Authorization" = "Bearer $apiKey"} `
    -OutFile $installerPath

# Run installer silently
Start-Process -FilePath $installerPath -Wait -NoNewWindow

# Log installation
$logPath = "\\fileserver\logs\giljo-mcp-installations.csv"
Add-Content -Path $logPath -Value "$env:USERNAME,$env:COMPUTERNAME,$(Get-Date)"
```

#### B. Configuration Management (Ansible, Puppet, Chef)

**Ansible Playbook Example:**

```yaml
---
- name: Deploy GiljoAI MCP Integration
  hosts: developer_workstations
  tasks:
    - name: Download Unix installer
      get_url:
        url: "http://giljo-server:7272/api/mcp-installer/unix"
        dest: "/tmp/giljo-mcp-setup.sh"
        headers:
          Authorization: "Bearer {{ giljo_api_key }}"
        mode: '0755'
      
    - name: Run installer
      shell: /tmp/giljo-mcp-setup.sh
      args:
        creates: ~/.claude.json
      
    - name: Verify installation
      shell: jq '.mcpServers."giljo-mcp"' ~/.claude.json
      register: verification
      failed_when: verification.stdout == "null"
      
    - name: Clean up
      file:
        path: /tmp/giljo-mcp-setup.sh
        state: absent
```

#### C. Docker/Container Environments

```dockerfile
# Development container with GiljoAI MCP pre-configured
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    jq \
    curl

# Download and run installer
ARG GILJO_API_KEY
RUN curl -H "Authorization: Bearer ${GILJO_API_KEY}" \
    http://giljo-server:7272/api/mcp-installer/unix \
    -o /tmp/giljo-mcp-setup.sh && \
    chmod +x /tmp/giljo-mcp-setup.sh && \
    /tmp/giljo-mcp-setup.sh && \
    rm /tmp/giljo-mcp-setup.sh

# Continue with dev environment setup...
```

---

## Team Onboarding Workflow

### Step 1: Pre-Installation Checklist

Before distributing installers, ensure:

- [ ] GiljoAI MCP server is running and accessible
- [ ] Network connectivity verified from developer machines
- [ ] Python 3.11+ available on all workstations
- [ ] Supported tools (Claude Code, Cursor, Windsurf) are installed
- [ ] User accounts created in GiljoAI dashboard
- [ ] API keys generated (for LAN/WAN modes)
- [ ] Documentation accessible to team

### Step 2: Distribution

Choose appropriate method:
- **Small team:** Email distribution
- **Medium team:** Shared file server
- **Large org:** Automated deployment

### Step 3: Installation Support

**Monitor installation progress:**

```bash
# Check dashboard for connected clients
# Navigate to: Statistics → Connected Clients

# Look for new connections matching team members
```

**Common support scenarios:**

| Issue | Solution | Documentation |
|-------|----------|---------------|
| Python not found | Install Python 3.11+ | [Prerequisites](MCP_INTEGRATION_GUIDE.md#prerequisites) |
| Permission denied | Run as admin / with sudo | [Troubleshooting](MCP_INTEGRATION_GUIDE.md#troubleshooting) |
| Tool not detected | Manual configuration | [Manual Config](MCP_INTEGRATION_GUIDE.md#manual-configuration) |
| Server unreachable | Check network/firewall | [Network Config](../deployment/LAN_DEPLOYMENT.md) |
| jq not found (Unix) | Install jq package | [Prerequisites](MCP_INTEGRATION_GUIDE.md#prerequisites) |

### Step 4: Verification

**Individual Verification:**
Ask developers to confirm:
1. Script ran without errors
2. Development tool restarted
3. GiljoAI MCP tools visible in IDE
4. Can execute basic MCP command (e.g., list_projects)

**Centralized Verification:**
Check dashboard metrics:
- Connected clients count matches team size
- No authentication errors in logs
- API request activity from new clients

### Step 5: Training

**Basic Training Session (30 minutes):**
1. Introduction to MCP tools (10 min)
2. Creating first project demo (10 min)
3. Spawning agents walkthrough (5 min)
4. Q&A and troubleshooting (5 min)

**Resources to Share:**
- [MCP Integration User Guide](MCP_INTEGRATION_GUIDE.md)
- [MCP Tools Manual](../manuals/MCP_TOOLS_MANUAL.md)
- [Quick Start Guide](../manuals/QUICK_START.md)
- Dashboard URL and credentials

---

## Security Best Practices

### API Key Management

#### Localhost Mode
- API keys optional (auto-login enabled)
- Suitable for individual developers only
- No network exposure

#### LAN Mode
- **Generate unique API keys** for each developer
- Set reasonable expiration (30-90 days)
- Rotate keys quarterly
- Revoke immediately when team member leaves

```bash
# Generate API key for developer
curl -X POST "http://localhost:7272/api/auth/api-keys" \
  -H "Authorization: Bearer ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "developer123",
    "name": "Dev Workstation - John Doe",
    "expires_in_days": 90
  }'
```

#### WAN Mode
- **OAuth + API keys** required
- Enforce MFA for admin accounts
- Use service accounts for automation
- Monitor API key usage patterns
- Alert on suspicious activity

### Share Link Security

**Token Expiration:**
- Default: 7 days
- Adjust based on organizational policy
- For security-sensitive deployments: 24-48 hours

**Token Rotation:**
```bash
# Revoke old token and generate new
curl -X DELETE "http://localhost:7272/api/mcp-installer/tokens/{old_token}" \
  -H "Authorization: Bearer ADMIN_JWT"

curl -X POST "http://localhost:7272/api/mcp-installer/share-link" \
  -H "Authorization: Bearer ADMIN_JWT"
```

**Monitoring:**
- Log all token generations
- Track downloads per token
- Alert on unusual download patterns

### Network Security

**Firewall Configuration:**

```bash
# Allow GiljoAI ports from developer subnet
# API server: 7272
# Dashboard: 7274

# Example: iptables (Linux)
iptables -A INPUT -p tcp -s 10.1.0.0/24 --dport 7272 -j ACCEPT
iptables -A INPUT -p tcp -s 10.1.0.0/24 --dport 7274 -j ACCEPT

# Example: Windows Firewall
New-NetFirewallRule -DisplayName "GiljoAI API" `
  -Direction Inbound -Protocol TCP -LocalPort 7272 `
  -RemoteAddress 10.1.0.0/24 -Action Allow
```

**TLS/SSL (WAN Mode):**

```yaml
# config.yaml
services:
  api:
    host: 0.0.0.0
    port: 443
    ssl:
      enabled: true
      cert_file: /etc/ssl/certs/giljo-mcp.crt
      key_file: /etc/ssl/private/giljo-mcp.key
```

### Access Control

**Role-Based Permissions:**

| Role | Permissions | Use Case |
|------|-------------|----------|
| Admin | Full access, user management, key generation | IT administrators |
| Team Lead | Create projects, assign agents, view team metrics | Development leads |
| Developer | Create personal projects, spawn agents | Individual developers |
| Viewer | Read-only dashboard access | Managers, stakeholders |

**Audit Logging:**
```bash
# Enable comprehensive logging
# config.yaml
logging:
  level: INFO
  audit:
    enabled: true
    log_file: /var/log/giljo-mcp/audit.log
    events:
      - user_login
      - api_key_generation
      - installer_download
      - project_creation
      - agent_spawn
```

---

## Monitoring and Maintenance

### Health Checks

**Dashboard Monitoring:**
- **Statistics → System Health**
  - API response times
  - Database connection pool
  - Active connections
  - Error rates

**Automated Monitoring:**

```bash
# Prometheus metrics endpoint
curl http://localhost:7272/metrics

# Key metrics to monitor:
# - giljo_api_requests_total
# - giljo_connected_clients
# - giljo_active_agents
# - giljo_database_connections
# - giljo_error_count
```

### Regular Maintenance Tasks

**Daily:**
- [ ] Check dashboard for error spikes
- [ ] Verify all services running
- [ ] Review authentication failures

**Weekly:**
- [ ] Regenerate share links (before 7-day expiry)
- [ ] Review API key expiration list
- [ ] Check disk space and log rotation
- [ ] Update installer scripts if config changed

**Monthly:**
- [ ] Review and revoke unused API keys
- [ ] Rotate service account credentials
- [ ] Update dependencies and security patches
- [ ] Backup configuration and database
- [ ] Review user access and permissions

**Quarterly:**
- [ ] Conduct security audit
- [ ] Review and update documentation
- [ ] Team training refresher
- [ ] Performance optimization review

### Backup and Disaster Recovery

**Configuration Backup:**
```bash
# Backup config.yaml and .env
cp config.yaml config.yaml.backup.$(date +%Y%m%d)
cp .env .env.backup.$(date +%Y%m%d)

# Store securely (encrypted)
tar czf giljo-config-backup-$(date +%Y%m%d).tar.gz \
  config.yaml.backup.* .env.backup.*

openssl enc -aes-256-cbc -salt \
  -in giljo-config-backup-$(date +%Y%m%d).tar.gz \
  -out giljo-config-backup-$(date +%Y%m%d).tar.gz.enc
```

**Database Backup:**
```bash
# PostgreSQL backup
pg_dump -U giljo_user giljo_mcp > giljo_mcp_backup_$(date +%Y%m%d).sql

# Restore if needed
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"
psql -U postgres -c "CREATE DATABASE giljo_mcp OWNER giljo_user;"
psql -U giljo_user -d giljo_mcp < giljo_mcp_backup_20251009.sql
```

---

## Troubleshooting Team Issues

### Scenario 1: Multiple Developers Can't Connect

**Symptoms:**
- Several team members report connection failures
- "Server unreachable" errors
- Dashboard inaccessible

**Diagnosis:**
```bash
# Check if server is running
systemctl status giljo-mcp  # Linux with systemd

# Check port availability
netstat -an | grep 7272
netstat -an | grep 7274

# Test from client machine
curl http://SERVER_IP:7272/health
```

**Solutions:**
1. **Server not running:** Restart GiljoAI services
2. **Firewall blocking:** Add firewall rules (see Security section)
3. **Network issue:** Check switch/router configuration
4. **DNS problem:** Use IP address instead of hostname

### Scenario 2: API Key Authentication Failures

**Symptoms:**
- "Invalid API key" errors
- Successful installation but tools can't connect
- Intermittent authentication failures

**Diagnosis:**
```bash
# Verify API key in database
psql -U postgres -d giljo_mcp -c \
  "SELECT id, name, is_active, expires_at FROM api_keys WHERE key = 'USER_KEY';"

# Check logs for auth errors
tail -f logs/giljo-mcp.log | grep "authentication"
```

**Solutions:**
1. **Expired key:** Regenerate API key
2. **Typo in key:** Re-download installer with fresh key
3. **Key not activated:** Activate in dashboard
4. **User account disabled:** Re-enable user account

### Scenario 3: Installer Script Fails on Windows

**Symptoms:**
- "PowerShell execution policy" errors
- JSON parsing failures
- Backup creation failures

**Diagnosis:**
```cmd
REM Check PowerShell execution policy
powershell -Command "Get-ExecutionPolicy"

REM Test JSON config manually
powershell -Command "Get-Content %USERPROFILE%\.claude.json | ConvertFrom-Json"
```

**Solutions:**

**PowerShell Execution Policy:**
```cmd
REM Temporarily allow script execution
powershell -ExecutionPolicy Bypass -File giljo-mcp-setup.bat

REM OR set permanently (requires admin)
powershell -Command "Set-ExecutionPolicy RemoteSigned"
```

**JSON Syntax Issues:**
```cmd
REM Restore from backup
copy %USERPROFILE%\.claude.json.backup.* %USERPROFILE%\.claude.json

REM Validate JSON
python -m json.tool < %USERPROFILE%\.claude.json
```

### Scenario 4: Unix Installer Missing jq

**Symptoms:**
- "jq: command not found"
- Script aborts early

**Solutions:**

Provide platform-specific installation instructions:

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y jq

# CentOS/RHEL
sudo yum install -y jq

# Fedora
sudo dnf install -y jq

# Alpine Linux
sudo apk add jq

# After installation, re-run installer
./giljo-mcp-setup.sh
```

### Scenario 5: Configuration Not Persisting

**Symptoms:**
- Installer succeeds but config reverts
- Tools don't show GiljoAI MCP after restart
- Backups show correct config

**Possible Causes:**
1. Tool syncing settings from cloud/profile
2. File permissions preventing write
3. Multiple config file locations
4. Tool using different config path

**Diagnosis:**
```bash
# Find all possible config locations
find ~ -name ".claude.json" 2>/dev/null
find ~ -name "mcp.json" 2>/dev/null

# Check file permissions
ls -la ~/.claude.json

# Monitor file changes
# macOS
sudo fs_usage | grep claude.json

# Linux
inotifywait -m ~/.claude.json
```

**Solutions:**
1. Disable cloud settings sync
2. Fix file permissions: `chmod 644 ~/.claude.json`
3. Configure correct config path in tool preferences
4. Lock config file (advanced): `chattr +i ~/.claude.json` (Linux)

---

## Programmatic Deployment Examples

### Python Script for Bulk Deployment

```python
#!/usr/bin/env python3
"""
Bulk MCP installer distribution for team onboarding.
Generates share links for all developers and sends emails.
"""

import requests
from datetime import datetime
from typing import List, Dict

GILJO_API_BASE = "http://localhost:7272"
ADMIN_JWT = "your_admin_jwt_token_here"

def generate_share_link(user_id: str) -> Dict[str, str]:
    """Generate share link for a user."""
    response = requests.post(
        f"{GILJO_API_BASE}/api/mcp-installer/share-link",
        headers={"Authorization": f"Bearer {ADMIN_JWT}"}
    )
    response.raise_for_status()
    return response.json()

def send_onboarding_email(email: str, name: str, links: Dict[str, str]):
    """Send onboarding email with installer links."""
    # Use your email service (SendGrid, SES, etc.)
    subject = "GiljoAI MCP Setup - Welcome to the Team!"
    
    body = f"""
    Hi {name},
    
    Welcome! Please set up your development environment:
    
    Windows: {links['windows_url']}
    macOS/Linux: {links['unix_url']}
    
    Links expire: {links['expires_at']}
    
    Need help? Check the user guide or reach out to IT.
    
    Best regards,
    IT Team
    """
    
    # Send email (implementation depends on your email service)
    print(f"Email sent to {email}")

def bulk_deploy(developers: List[Dict[str, str]]):
    """Deploy to multiple developers."""
    for dev in developers:
        print(f"Processing: {dev['name']}")
        
        try:
            # Generate share link
            links = generate_share_link(dev['user_id'])
            
            # Send email
            send_onboarding_email(
                email=dev['email'],
                name=dev['name'],
                links=links
            )
            
            print(f"  ✓ Share link generated and sent")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")

if __name__ == "__main__":
    # Load developer list from CSV, database, or define here
    developers = [
        {"user_id": "dev001", "name": "Alice Smith", "email": "alice@example.com"},
        {"user_id": "dev002", "name": "Bob Johnson", "email": "bob@example.com"},
        # ... more developers
    ]
    
    print(f"Starting bulk deployment for {len(developers)} developers...")
    bulk_deploy(developers)
    print("Deployment complete!")
```

### Bash Script for Scheduled Updates

```bash
#!/bin/bash
# update_installers.sh
# Run weekly via cron to refresh share links

GILJO_API="http://localhost:7272"
ADMIN_JWT="your_admin_jwt_token"
SHARED_DIR="/mnt/fileserver/giljo-mcp/installers"

echo "Updating installer scripts: $(date)"

# Generate new Windows installer
curl -H "Authorization: Bearer $ADMIN_JWT" \
  "$GILJO_API/api/mcp-installer/windows" \
  -o "$SHARED_DIR/windows/giljo-mcp-setup.bat"

# Generate new Unix installer
curl -H "Authorization: Bearer $ADMIN_JWT" \
  "$GILJO_API/api/mcp-installer/unix" \
  -o "$SHARED_DIR/unix/giljo-mcp-setup.sh"

# Make Unix script executable
chmod +x "$SHARED_DIR/unix/giljo-mcp-setup.sh"

# Update README with generation timestamp
cat > "$SHARED_DIR/README.txt" <<EOF
GiljoAI MCP Installers
Generated: $(date)
Valid until: $(date -d "+7 days")

Windows: windows/giljo-mcp-setup.bat
Unix: unix/giljo-mcp-setup.sh

Instructions: See docs/guides/MCP_INTEGRATION_GUIDE.md
EOF

echo "Update complete!"

# Add to crontab:
# 0 2 * * 1 /usr/local/bin/update_installers.sh >> /var/log/giljo-updates.log 2>&1
```

---

## Advanced Topics

### Multi-Server Deployment

For organizations with multiple GiljoAI instances:

```json
{
  "mcpServers": {
    "giljo-mcp-dev": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://dev-server:7272",
        "GILJO_API_KEY": "dev_api_key"
      }
    },
    "giljo-mcp-staging": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://staging-server:7272",
        "GILJO_API_KEY": "staging_api_key"
      }
    },
    "giljo-mcp-prod": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "https://prod.example.com",
        "GILJO_API_KEY": "prod_api_key"
      }
    }
  }
}
```

### Custom Installer Templates

To create custom installer templates for your organization:

1. Copy base template:
   ```bash
   cp installer/templates/giljo-mcp-setup.sh.template \
      installer/templates/custom-setup.sh.template
   ```

2. Modify template:
   - Add corporate branding
   - Include additional tools
   - Add compliance checks
   - Customize output messages

3. Update API endpoint to use custom template:
   ```python
   # api/endpoints/mcp_installer.py
   template_path = Path(__file__).parent.parent.parent / \
                   "installer" / "templates" / "custom-setup.sh.template"
   ```

### Integration with Identity Providers

For enterprise SSO integration:

```python
# Example: Azure AD integration
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_api_key_from_vault(user_email: str) -> str:
    """Retrieve user's API key from Azure Key Vault."""
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url="https://your-vault.vault.azure.net/", 
                          credential=credential)
    
    secret_name = f"giljo-api-key-{user_email.replace('@', '-at-')}"
    secret = client.get_secret(secret_name)
    return secret.value
```

---

## Compliance and Governance

### Data Privacy

**GDPR Considerations:**
- API keys are personal data → secure storage required
- Right to erasure → implement key revocation
- Data portability → export user's project data
- Audit logs → track all data access

**Implementation:**
```python
# Automated API key cleanup
def cleanup_expired_keys():
    """Remove expired API keys and log deletion."""
    from giljo_mcp.database import get_db
    from giljo_mcp.models import APIKey
    
    db = get_db()
    expired = db.query(APIKey).filter(
        APIKey.expires_at < datetime.utcnow()
    ).all()
    
    for key in expired:
        # Log before deletion (audit trail)
        log_audit_event(
            event="api_key_deleted",
            user_id=key.user_id,
            reason="expiration",
            key_id=key.id
        )
        
        db.delete(key)
    
    db.commit()
```

### License Compliance

Ensure all team members:
- Have valid licenses for tools (Claude Code, Cursor, Windsurf)
- Accept GiljoAI terms of service
- Comply with organization's acceptable use policy

### Security Compliance

**SOC 2 / ISO 27001:**
- [ ] Encrypt API keys at rest
- [ ] Use TLS for all network communications
- [ ] Implement access logging and monitoring
- [ ] Regular security audits
- [ ] Incident response procedures
- [ ] Data backup and recovery testing

---

## Support and Escalation

### Support Tiers

**Tier 1: Self-Service**
- User guide and documentation
- FAQ and troubleshooting
- Dashboard health checks

**Tier 2: IT Help Desk**
- Installation support
- Network connectivity issues
- API key resets
- Tool configuration

**Tier 3: Administrator**
- Server configuration
- Security incidents
- Performance issues
- Advanced troubleshooting

### Creating Support Tickets

**Template for Developer Support Tickets:**

```
Issue Type: MCP Integration

Reporter: [Developer Name]
Date: [YYYY-MM-DD]

Problem Description:
[Detailed description of the issue]

Environment:
- OS: [Windows 10 / macOS 14 / Ubuntu 22.04]
- Tool: [Claude Code / Cursor / Windsurf]
- Python Version: [python --version output]
- Server: [localhost / IP address]

Steps to Reproduce:
1. [First step]
2. [Second step]
3. [...]

Expected Behavior:
[What should happen]

Actual Behavior:
[What actually happens]

Error Messages:
[Paste any error messages]

Attempted Solutions:
[What troubleshooting steps were tried]

Additional Info:
[Logs, screenshots, config files (with sensitive data redacted)]
```

---

## Next Steps

### For Administrators

- **Review API Documentation:** [MCP Installer API](../api/MCP_INSTALLER_API.md)
- **Security Hardening:** [Security Checklist](../deployment/SECURITY_CHECKLIST.md)
- **Network Setup:** [LAN Deployment Guide](../deployment/LAN_DEPLOYMENT.md)
- **Monitoring:** [Operations Guide](../manuals/OPERATIONS.md)

### For Developers

After successful deployment, point your team to:
- **User Guide:** [MCP Integration Guide](MCP_INTEGRATION_GUIDE.md)
- **MCP Tools Reference:** [MCP Tools Manual](../manuals/MCP_TOOLS_MANUAL.md)
- **Quick Start:** [Quick Start Guide](../manuals/QUICK_START.md)

---

## Appendix

### Useful Commands Reference

```bash
# Generate share link
curl -X POST http://localhost:7272/api/mcp-installer/share-link \
  -H "Authorization: Bearer $JWT"

# Download Windows installer
curl -H "Authorization: Bearer $JWT" \
  http://localhost:7272/api/mcp-installer/windows \
  -o giljo-mcp-setup.bat

# Download Unix installer
curl -H "Authorization: Bearer $JWT" \
  http://localhost:7272/api/mcp-installer/unix \
  -o giljo-mcp-setup.sh

# Check server health
curl http://localhost:7272/health

# Verify PostgreSQL
psql -U postgres -c "\l" | grep giljo_mcp

# Check connected clients
curl http://localhost:7272/api/statistics/connected-clients \
  -H "Authorization: Bearer $JWT"

# View recent API activity
tail -f logs/giljo-mcp.log | grep "api_request"

# Backup database
pg_dump -U giljo_user giljo_mcp > backup_$(date +%Y%m%d).sql

# Restart services (systemd)
sudo systemctl restart giljo-mcp

# Check service status
sudo systemctl status giljo-mcp
```

### Directory Structure Reference

```
installer/
├── templates/
│   ├── giljo-mcp-setup.bat.template  # Windows installer template
│   └── giljo-mcp-setup.sh.template   # Unix installer template
├── cli/
│   └── install.py                     # Main installer CLI
└── scripts/
    └── [utility scripts]

docs/
├── guides/
│   ├── MCP_INTEGRATION_GUIDE.md      # End-user documentation
│   ├── ADMIN_MCP_SETUP.md            # This guide
│   └── [other guides]
└── api/
    └── MCP_INSTALLER_API.md          # API reference

api/
└── endpoints/
    └── mcp_installer.py               # Installer API endpoints
```

---

**Last Updated:** 2025-10-09  
**Version:** 3.0.0  
**Maintainer:** Documentation Manager Agent
