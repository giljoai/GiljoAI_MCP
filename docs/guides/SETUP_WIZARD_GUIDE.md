# GiljoAI MCP Setup Wizard Guide

**Version**: 2.0.0
**Last Updated**: October 5, 2025
**Status**: Phase 0 Implementation (Planned)

## Overview

The GiljoAI MCP Setup Wizard is a web-based configuration interface that guides you through completing your installation after running the CLI installer. It handles deployment mode selection, database configuration, AI tool integration, and system verification.

### What the Setup Wizard Does

The Setup Wizard handles configuration tasks that require:
- User interaction and decision-making
- Detection of user-installed tools
- Real-time validation and testing
- Writing to user-specific configuration files

### When Does It Run?

The Setup Wizard automatically launches after the CLI installer completes:

1. Run `install.bat` (Windows) or `python install.py` (cross-platform)
2. CLI installer completes core setup (PostgreSQL, dependencies, services)
3. Dashboard opens automatically at `http://localhost:7274`
4. If first-time setup detected, wizard appears automatically
5. Complete wizard steps to finish configuration

## Installation Flow

```
┌──────────────────────────────────────┐
│  CLI Installer (install.bat)         │
│  - Detect OS and requirements        │
│  - Install PostgreSQL 18             │
│  - Create Python virtual environment │
│  - Install dependencies              │
│  - Create system services            │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│  Dashboard Opens                     │
│  http://localhost:7274               │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│  Setup Wizard (if first run)         │
│  - Database connection test          │
│  - Deployment mode selection         │
│  - Admin account setup (if LAN/WAN)  │
│  - AI tool detection & registration  │
│  - Firewall configuration (if LAN)   │
│  - Final verification                │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│  Ready to Use!                       │
│  Start creating projects             │
└──────────────────────────────────────┘
```

## Step-by-Step Walkthrough

### Step 1: Welcome & Database Connection

**What You'll See**:
- Welcome message
- Database connection status indicator
- Option to test database connection

**What To Do**:
1. Review the welcome message
2. Click "Test Database Connection"
3. Verify green checkmark appears
4. Click "Continue"

**Troubleshooting**:
- **Red X - Connection Failed**:
  - Check PostgreSQL 18 is running (see [PostgreSQL Troubleshooting](../troubleshooting/POSTGRES_TROUBLESHOOTING.txt))
  - Verify default credentials (user: postgres, password: set during installation)
  - Check firewall isn't blocking port 5432
- **Yellow Warning - Slow Connection**:
  - Connection works but is slow (>2 seconds)
  - May indicate network issues
  - Safe to continue, but investigate if persists

**Screenshot Description**:
*Welcome screen with GiljoAI logo at top, database status indicator showing green checkmark with "Connected to PostgreSQL 18" message, and blue "Continue" button at bottom right.*

---

### Step 2: Deployment Mode Selection

**What You'll See**:
- Three deployment mode options with descriptions
- Recommendation based on your environment

**Deployment Modes Explained**:

| Mode | Best For | Network Access | Authentication | Database Location |
|------|----------|----------------|----------------|-------------------|
| **Localhost** | Individual developers | This PC only | None (single user) | localhost:5432 |
| **LAN** | Teams on local network | Local network only | API key required | Server IP:5432 |
| **WAN** | Remote teams, internet access | Internet accessible | API key + HTTPS | Server IP:5432 |

**What To Do**:
1. Read the descriptions carefully
2. Select the mode that matches your needs
3. Click "Continue"

**Recommendations**:
- **Choose Localhost** if:
  - You're a solo developer
  - Working on personal projects
  - Don't need team collaboration
  - Want simplest setup

- **Choose LAN** if:
  - Working with a team in same office/building
  - Need to share projects with colleagues
  - Want better performance than WAN
  - Have local network infrastructure

- **Choose WAN** if:
  - Team members work remotely
  - Need internet-accessible deployment
  - Have public domain/IP address
  - Require HTTPS security

**Important Notes**:
- You can change deployment mode later in Settings
- Changing modes may require reconfiguration
- LAN/WAN modes require additional security setup

**Screenshot Description**:
*Three large cards arranged horizontally: "Localhost" (blue border), "LAN" (orange border), "WAN" (green border). Each card shows icon, title, description, and key features list.*

---

### Step 3: Admin Account Setup (LAN/WAN Only)

**What You'll See** (Localhost mode skips this step):
- Admin username input field
- Password input field with strength indicator
- Password confirmation field
- Optional email field

**What To Do**:
1. Enter desired admin username (3-30 characters, alphanumeric + underscore)
2. Create a strong password:
   - Minimum 12 characters
   - Include uppercase, lowercase, numbers, and symbols
   - Avoid common words or patterns
3. Confirm password (must match exactly)
4. Optionally enter email for password recovery
5. Click "Create Admin Account"

**Password Strength Indicator**:
- **Weak** (Red): Too short or simple - not accepted
- **Medium** (Yellow): Acceptable but could be stronger
- **Strong** (Green): Excellent password - recommended

**Security Notes**:
- This account has full system access
- Store credentials securely (password manager recommended)
- Cannot be recovered without database access
- First account created = system administrator

**Troubleshooting**:
- **"Username already exists"**: Choose a different username
- **"Passwords don't match"**: Re-enter password carefully
- **"Password too weak"**: Use longer password with more variety
- **"Invalid email format"**: Check email address format

**Screenshot Description**:
*Form with four input fields vertically stacked. Password field shows green strength bar at "Strong". Blue "Create Admin Account" button at bottom. Small info icon next to password field with tooltip about requirements.*

---

### Step 4: AI Tool Integration

**What You'll See**:
- List of detected AI coding tools
- Status indicator for each tool (installed / not found)
- "Configure" button for each detected tool
- Link to manual setup instructions

**Supported AI Tools**:

| Tool | Configuration File | Detection Method |
|------|-------------------|------------------|
| **Claude Code** | `~/.claude.json` | Check for .claude.json file |
| **Cline** | VS Code extension settings | Check VS Code extensions directory |
| **Cursor** | Cursor IDE settings | Check Cursor installation directory |

**What To Do**:

1. **Review Detected Tools**:
   - Green checkmark = Tool detected and ready
   - Gray X = Tool not installed (safe to ignore)

2. **Configure Each Tool** (one at a time):
   - Click "Configure" button for a detected tool
   - Configuration preview dialog appears
   - Review the MCP server configuration
   - Click "Apply Configuration"
   - Wait for success confirmation
   - Click "Test Connection"
   - Verify green "Connected" status

3. **Test All Configurations**:
   - After configuring all tools, click "Test All Connections"
   - Verify all show green checkmarks
   - If any fail, click "Troubleshoot" for specific guidance

4. **Click "Continue"** when satisfied

**Configuration Preview Example** (Claude Code):

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "C:\\Projects\\GiljoAI_MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_API_URL": "http://localhost:7272",
        "GILJO_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**What This Does**:
- Registers GiljoAI MCP server with your AI coding tool
- Creates or updates tool's configuration file
- Backs up existing configuration (if present)
- Enables your AI tool to use GiljoAI MCP tools

**Safety Features**:
- **Automatic Backup**: Existing config saved as `.backup_YYYYMMDD_HHMMSS`
- **Merge Existing**: Preserves other MCP servers you may have configured
- **Non-Destructive**: Only adds/updates `giljo-mcp` entry
- **Reversible**: Can restore from backup if needed

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| **Tool not detected** | Not installed or non-standard location | Click "Manual Setup" for instructions |
| **Configuration failed** | Permission denied | Run as administrator or check file permissions |
| **Test connection failed** | MCP server not running | Check backend service status in Settings |
| **"Config file not writable"** | File locked or read-only | Close AI tool, remove read-only attribute |

**Manual Setup** (if tool not detected):
1. Click "Manual Setup Instructions"
2. Follow tool-specific guide
3. Copy provided configuration
4. Paste into tool's config file manually
5. Restart your AI tool
6. Return to wizard and click "Skip" to proceed

**Screenshot Description**:
*List view showing three rows:
Row 1 - Claude Code: Green checkmark, "Version 1.2.3", blue "Configure" button
Row 2 - Cline: Green checkmark, "Version 2.0.1", blue "Configure" button
Row 3 - Cursor: Gray X, "Not installed", gray disabled button
Bottom: "Test All Connections" button and "Manual Setup Instructions" link*

---

### Step 5: LAN Configuration (LAN Mode Only)

**What You'll See** (Localhost/WAN modes skip this step):
- Your server's LAN IP address
- Firewall configuration instructions
- Platform-specific setup commands
- Test connectivity button

**Detected Information**:
```
Server IP Address: 192.168.1.100
API Port: 7272
Dashboard Port: 7274
Database Port: 5432
```

**What To Do**:

#### Windows Users:

1. **Open PowerShell as Administrator**:
   - Right-click Start menu → Windows PowerShell (Admin)

2. **Run Firewall Commands** (provided in wizard):
   ```powershell
   # Allow API port
   New-NetFirewallRule -DisplayName "GiljoAI API" -Direction Inbound -Protocol TCP -LocalPort 7272 -Action Allow

   # Allow Dashboard port
   New-NetFirewallRule -DisplayName "GiljoAI Dashboard" -Direction Inbound -Protocol TCP -LocalPort 7274 -Action Allow
   ```

3. **Verify Rules Created**:
   - Open Windows Defender Firewall
   - Click "Advanced settings"
   - Check "Inbound Rules" for "GiljoAI API" and "GiljoAI Dashboard"

4. **Return to wizard** and click "Test Connectivity"

#### Linux Users:

1. **Open Terminal**

2. **Ubuntu/Debian** (using ufw):
   ```bash
   sudo ufw allow 7272/tcp comment 'GiljoAI API'
   sudo ufw allow 7274/tcp comment 'GiljoAI Dashboard'
   sudo ufw reload
   ```

3. **RHEL/CentOS** (using firewalld):
   ```bash
   sudo firewall-cmd --permanent --add-port=7272/tcp
   sudo firewall-cmd --permanent --add-port=7274/tcp
   sudo firewall-cmd --reload
   ```

4. **Return to wizard** and click "Test Connectivity"

#### macOS Users:

1. **Open System Preferences** → Security & Privacy → Firewall

2. **Click "Firewall Options"**

3. **Click "+"** and add Python/GiljoAI application

4. **Allow incoming connections**

5. **Return to wizard** and click "Test Connectivity"

**Connectivity Test**:
- Wizard will attempt to access server from network perspective
- Shows which ports are accessible from LAN
- Green checkmark = Port accessible
- Red X = Port blocked (firewall issue)

**Troubleshooting**:
- **All ports blocked**: Firewall rules not applied or firewall disabled
- **Some ports blocked**: Partial firewall configuration
- **"Network unreachable"**: Check network connectivity
- **"Permission denied"**: Run commands as administrator/sudo

**Screenshot Description**:
*Information panel showing detected IP and ports. Below: tabbed interface with "Windows", "Linux", "macOS" tabs. Windows tab active showing PowerShell commands in code block. Green "Test Connectivity" button at bottom with three port status indicators (all green checkmarks).*

---

### Step 6: Complete & Verification

**What You'll See**:
- Comprehensive system status check
- Green checkmarks for successful components
- Summary of your configuration
- "Start Using GiljoAI" button

**Final Verification Checklist**:

```
✓ Database: Connected (PostgreSQL 18)
✓ Backend API: Running (http://localhost:7272)
✓ Frontend Dashboard: Running (http://localhost:7274)
✓ MCP Server: Healthy
✓ WebSocket: Active
✓ Claude Code: Configured & Connected
✓ Deployment Mode: Localhost
✓ Configuration: Saved
```

**Configuration Summary**:

| Setting | Value |
|---------|-------|
| Deployment Mode | Localhost / LAN / WAN |
| Database | PostgreSQL 18 (localhost:5432) |
| API URL | http://localhost:7272 |
| Dashboard URL | http://localhost:7274 |
| AI Tools Configured | Claude Code, Cline |
| Firewall | Configured (LAN only) |

**What To Do**:
1. Review all checkmarks are green
2. Note your configuration details
3. Click "Start Using GiljoAI"
4. Dashboard loads with sample project

**Next Steps After Setup**:
- Explore the dashboard interface
- Review the Quick Start tutorial (optional)
- Create your first project
- Invite team members (LAN/WAN modes)
- Configure AI tool integration in your IDE

**Troubleshooting**:
- **Any red X's**: Click on the failed item for specific troubleshooting
- **"Configuration incomplete"**: Return to previous steps to complete setup
- **"Cannot save configuration"**: Check file system permissions

**Screenshot Description**:
*Clean verification screen with large checklist in center. Each item has green checkmark icon. Configuration summary table below checklist. Large green "Start Using GiljoAI" button at bottom center. Small "Review Settings" link in corner.*

---

## Troubleshooting

### Common Issues

#### Issue: Setup Wizard Doesn't Appear

**Symptoms**: Dashboard loads but no wizard appears

**Causes**:
1. Setup already completed previously
2. Configuration file exists from previous installation
3. Wizard dismissed and "Don't show again" clicked

**Solutions**:
1. Check `config.yaml` exists - if yes, setup already complete
2. Delete `config.yaml` to trigger wizard again
3. Access wizard manually: `http://localhost:7274/setup`
4. Check browser console for JavaScript errors

---

#### Issue: Database Connection Test Fails

**Symptoms**: Red X on database connection test

**Causes**:
1. PostgreSQL not running
2. Wrong database credentials
3. Firewall blocking port 5432
4. PostgreSQL not installed

**Solutions**:
1. **Windows**: Check services.msc → PostgreSQL service status
2. **Linux**: Run `sudo systemctl status postgresql`
3. **macOS**: Run `brew services list | grep postgres`
4. Verify credentials in `.env` file
5. See [PostgreSQL Troubleshooting Guide](../troubleshooting/POSTGRES_TROUBLESHOOTING.txt)

---

#### Issue: AI Tool Not Detected

**Symptoms**: Tool shows "Not installed" despite being installed

**Causes**:
1. Non-standard installation location
2. Tool installed after wizard started
3. Configuration file in unexpected location
4. Portable/custom installation

**Solutions**:
1. Close and restart wizard
2. Use "Manual Setup" option instead
3. Check tool's actual config file location
4. Manually edit config file (see Manual Setup section)

---

#### Issue: MCP Configuration Fails

**Symptoms**: "Configuration failed" error when applying MCP config

**Causes**:
1. Configuration file is read-only
2. Insufficient permissions
3. File locked by running application
4. Disk full or quota exceeded

**Solutions**:
1. Close your AI tool completely
2. Check file permissions: `ls -l ~/.claude.json`
3. Remove read-only attribute (Windows): `attrib -r ~/.claude.json`
4. Run with administrator privileges
5. Check disk space: `df -h` (Linux/macOS) or `dir` (Windows)

---

#### Issue: Firewall Test Fails (LAN Mode)

**Symptoms**: Connectivity test shows ports blocked

**Causes**:
1. Firewall rules not applied
2. Third-party firewall software
3. Router/gateway blocking
4. Network isolation

**Solutions**:
1. Verify firewall rules were created:
   - Windows: `Get-NetFirewallRule | findstr GiljoAI`
   - Linux: `sudo ufw status` or `sudo firewall-cmd --list-ports`
2. Check third-party firewall (Norton, McAfee, etc.)
3. Temporarily disable firewall to test (re-enable after!)
4. Check router port forwarding settings (WAN mode)
5. See [Firewall Configuration Guide](../deployment/FIREWALL_SETUP.md)

---

#### Issue: "Configuration Cannot Be Saved"

**Symptoms**: Error when clicking "Complete Setup"

**Causes**:
1. No write permission to installation directory
2. Disk full
3. Antivirus blocking file modification
4. File system error

**Solutions**:
1. Check installation directory permissions
2. Run installer as administrator (Windows) or with sudo (Linux)
3. Check antivirus logs for blocked operations
4. Verify disk space available
5. Check file system integrity: `chkdsk` (Windows) or `fsck` (Linux)

---

### Getting Additional Help

**Documentation**:
- [Installation Guide](../manuals/INSTALL.md) - Detailed installation instructions
- [PostgreSQL Troubleshooting](../troubleshooting/POSTGRES_TROUBLESHOOTING.txt) - Database-specific issues
- [Firewall Setup Guide](../deployment/FIREWALL_SETUP.md) - Network configuration help
- [Technical Architecture](../TECHNICAL_ARCHITECTURE.md) - System architecture reference

**Logs Location**:
- **Installation Log**: `C:\Projects\GiljoAI_MCP\install_logs\install.log`
- **Backend Log**: `C:\Projects\GiljoAI_MCP\logs\backend.log`
- **Frontend Log**: Browser Developer Console (F12)
- **Database Log**: PostgreSQL data directory (varies by OS)

**Support Channels**:
- GitHub Issues: https://github.com/patrik-giljoai/GiljoAI-MCP/issues
- Documentation: https://github.com/patrik-giljoai/GiljoAI-MCP/tree/master/docs
- Community Forum: (Coming soon)

---

## FAQ

### Can I skip the Setup Wizard?

No, the wizard must be completed for initial configuration. However, you can:
- Return to it later if dismissed
- Modify settings afterward in Settings page
- Re-run wizard by deleting `config.yaml`

### Can I change deployment mode after setup?

Yes, go to Settings → Deployment and select a different mode. Note:
- Changing from Localhost → LAN requires creating admin account
- Changing from LAN → Localhost will disable multi-user features
- Changing to/from WAN requires reconfiguring network settings

### Do I need to configure all AI tools?

No, configure only the tools you actually use. You can:
- Skip tools you don't have installed
- Add more tools later in Settings → Integrations
- Remove tools you no longer use

### What if I make a mistake during setup?

You can:
- Use browser "Back" button to return to previous step
- Click "Cancel" to exit wizard (can resume later)
- Delete `config.yaml` to start over completely
- Modify settings afterward in Settings page

### How do I reconfigure MCP integration later?

1. Go to Settings → Integrations
2. Click the AI tool you want to reconfigure
3. Click "Regenerate Configuration"
4. Apply the new configuration
5. Test connection

### Is my data safe during setup?

Yes:
- Existing configurations are backed up automatically
- No data is transmitted outside your network
- All credentials are stored locally encrypted
- Database is only accessible from configured hosts

### Can I use a different PostgreSQL installation?

Yes, but only PostgreSQL 18 is supported. To use existing PostgreSQL:
1. Ensure version is 18.x
2. Update database credentials in setup wizard
3. Grant necessary permissions to GiljoAI user
4. Test connection before proceeding

### What happens if setup is interrupted?

Setup is designed to be resumable:
- Progress is saved after each step
- You can close browser and return later
- Partial configurations are not applied
- System remains in "setup incomplete" state until finished

### How long does setup take?

Typical setup times:
- **Localhost mode**: 3-5 minutes
- **LAN mode**: 8-12 minutes (includes firewall setup)
- **WAN mode**: 15-20 minutes (includes security configuration)

### Can I automate the setup process?

Not currently. The wizard requires user interaction for:
- Security: Admin password creation
- Tool detection: Different for each user environment
- Validation: Real-time testing and verification

Future versions may support configuration import for bulk deployments.

---

## Related Documentation

- **[Installation Guide](../manuals/INSTALL.md)** - Pre-wizard CLI installation
- **[Quick Start Guide](../manuals/QUICK_START.md)** - Post-setup getting started
- **[PostgreSQL Troubleshooting](../troubleshooting/POSTGRES_TROUBLESHOOTING.txt)** - Database help
- **[Firewall Setup Guide](../deployment/FIREWALL_SETUP.md)** - Network configuration
- **[Wizard Developer Guide](../development/WIZARD_DEVELOPMENT.md)** - For developers
- **[Technical Architecture](../TECHNICAL_ARCHITECTURE.md)** - System design reference
- **[MCP Tools Manual](../manuals/MCP_TOOLS_MANUAL.md)** - MCP tools reference

---

**Last Updated**: October 5, 2025
**Version**: 2.0.0 (Phase 0 - Planned)
**Maintained By**: Documentation Manager Agent
