# First Launch Experience

**Document Version**: 10_13_2025
**Status**: Single Source of Truth
**Last Updated**: October 13, 2025

---

## Overview

The GiljoAI MCP v3.0 first launch experience is designed as a **smooth, guided onboarding** that takes users from fresh installation to productive multi-agent orchestration. The process consists of installation, first-admin account creation during setup wizard, and user self-configuration through settings.

### First Launch Sequence

1. **Installation Complete** (`python install.py`)
2. **Setup Wizard Opens** (http://localhost:7274/setup)
3. **First Admin Creation** (user sets admin username and password)
4. **MCP & Integration Setup** (2 additional steps)
5. **Dashboard Access** (full system ready, authenticated)

### v3.0 Authentication Requirements

**CRITICAL**: GiljoAI MCP v3.0 has **secure first-admin creation** during setup:
- ✅ **User-Defined Credentials** - Admin sets username/password during first run
- ✅ **ONE authentication flow** - Same for localhost, LAN, WAN
- ✅ **No default credentials** - Each installation is unique and secure
- ✅ **JWT-based sessions** - Unified authentication system

---

## Step-by-Step First Launch Guide

### Step 1: Installation Complete

After running `python install.py`, you'll see the installation summary:

```
═══════════════════════════════════════════════════════════════════════
🎉 GiljoAI MCP v3.0 Installation Complete!
═══════════════════════════════════════════════════════════════════════

📍 Installation Directory: F:\GiljoAI_MCP
🗄️  Database: PostgreSQL (giljo_mcp)
🔐 Admin Account: Created during setup wizard

🌐 Access URLs:
   Setup Wizard: http://localhost:7274/setup
   Dashboard:    http://localhost:7274
   API Docs:     http://localhost:7272/docs
   Health:       http://localhost:7272/health

⚠️  IMPORTANT FIRST STEPS:
   1. Complete setup wizard (create admin account)
   2. Configure AI coding agents via Avatar → My Settings → API & Integrations
   3. Configure firewall if needed for network access

Happy orchestrating! 🤖✨
═══════════════════════════════════════════════════════════════════════
```

**What Just Happened**:
- PostgreSQL database created with tables
- API server started on port 7272
- Frontend server started on port 7274
- Setup wizard ready for first-admin account creation
- Browser automatically opened to http://localhost:7274/setup

### Step 2: Setup Wizard - First Admin Creation

**URL Access**: Visit http://localhost:7274/setup (automatic on first run)

**Router Navigation Guard** (automatic):
```javascript
// Frontend router checks setup state
router.beforeEach(async (to, from, next) => {
  const setupStatus = await api.get('/api/setup/status')

  if (!setupStatus.data.admin_created) {
    // Force redirect to setup wizard
    if (to.path !== '/setup') {
      return next('/setup')
    }
  }

  next()
})
```

**Result**: Automatic redirect to `/setup` wizard for first-admin creation

### Step 3: Admin Account Creation

**First Admin Creation Screen**:

```
┌─────────────────────────────────────────────────────────┐
│               🔐 Create First Admin Account             │
│                                                         │
│  Welcome to GiljoAI MCP v3.0!                         │
│                                                         │
│  Set up your admin credentials to secure the system.   │
│                                                         │
│  Admin Username: [                      ]              │
│  Password:       [                      ]              │
│  Confirm:        [                      ]              │
│                                                         │
│  Password Requirements:                                 │
│  ✓ Minimum 12 characters                              │
│  ✓ At least 1 uppercase letter (A-Z)                  │
│  ✓ At least 1 lowercase letter (a-z)                  │
│  ✓ At least 1 digit (0-9)                             │
│  ✓ At least 1 special character (!@#$%^&*...)         │
│                                                         │
│  [ Create Admin Account ]                              │
└─────────────────────────────────────────────────────────┘
```

**Interactive Password Strength Meter**:
- Real-time validation as user types
- Visual strength indicator (Weak/Fair/Good/Strong)
- Live checking of each requirement
- Confirmation field must match

**Form Validation**:
- Username cannot be empty (default suggestion: "admin")
- Password must meet complexity requirements
- Confirmation must match password
- **Cannot skip this step** - required for system security

**Backend Processing**:
```python
# POST /api/auth/create-first-admin
@router.post("/create-first-admin")
async def create_first_admin(request: CreateFirstAdminRequest):
    # Check no admin exists yet
    existing_admin = await session.execute(
        select(User).where(User.role == 'admin')
    )
    if existing_admin.scalars().first():
        raise HTTPException(400, "Admin user already exists")

    # Validate password complexity
    if not validate_password_complexity(request.password):
        raise HTTPException(400, "Password does not meet requirements")

    # Create first admin user
    admin_user = User(
        id=str(uuid.uuid4()),
        tenant_key='default',
        username=request.username,
        password_hash=hash_password(request.password),
        role='admin',
        is_active=True,
        is_system_user=False
    )
    session.add(admin_user)

    # Mark admin as created
    setup_state.admin_created = True
    setup_state.admin_created_at = datetime.utcnow()
    
    # Generate JWT token for immediate login
    access_token = create_access_token(user.id, user.tenant_key)
    
    return {
        "message": "Password changed successfully",
        "access_token": access_token,
        "redirect_url": "/setup"
    }
```

**After Successful Change**:
- JWT token issued and stored in localStorage
- User automatically logged in
- Redirect to `/dashboard` (main application)

### Step 4: Setup Wizard (3 Steps)

**Setup Wizard Overview**:

```
Setup Wizard Progress: [■■■□] Step 1 of 3

┌─────────────────────────────────────────────────────────┐
│                    🛠️ Setup Wizard                      │
│                                                         │
│  Configure your GiljoAI MCP installation               │
│                                                         │
│  Steps:                                                 │
│  1. MCP Configuration        ← Current                  │
│  2. Serena Activation                                   │
│  3. Complete                                            │
│                                                         │
│  You can skip any step and configure later.            │
└─────────────────────────────────────────────────────────┘
```

#### Step 4a: MCP Configuration (Optional)

**MCP Integration Setup**:

```
┌─────────────────────────────────────────────────────────┐
│               🔗 MCP Protocol Integration               │
│                                                         │
│  Model Context Protocol (MCP) lets AI assistants       │
│  communicate with GiljoAI MCP for orchestration.       │
│                                                         │
│  ☐ Enable MCP Integration                              │
│                                                         │
│  Available Configurations:                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 📋 Claude Desktop (claude.json)                │   │
│  │ Download configuration                          │   │
│  │ [Download Setup File]                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🔧 VS Code (settings.json)                     │   │
│  │ Development environment integration             │   │
│  │ [Download Setup File]                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 💻 CLI Integration                              │   │
│  │ Command-line MCP server setup                   │   │
│  │ [Download Setup Script]                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [ Skip ]                              [ Next Step ]   │
└─────────────────────────────────────────────────────────┘
```

**MCP Configuration Downloads**:

When user clicks "Download Setup File", they receive:

**Claude Desktop Configuration** (`claude_mcp_config.json`):
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_MCP_HOME": "F:/GiljoAI_MCP",
        "GILJO_SERVER_URL": "http://localhost:7272"
      }
    }
  }
}
```

**VS Code Configuration** (`.vscode/settings.json`):
```json
{
  "mcp.servers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_MCP_HOME": "F:/GiljoAI_MCP",
        "GILJO_SERVER_URL": "http://localhost:7272"
      }
    }
  }
}
```

**CLI Setup Script** (`setup_mcp_cli.py`):
```python
#!/usr/bin/env python3
"""
GiljoAI MCP CLI Integration Setup
Configures MCP server for command-line usage
"""

import os
import json
from pathlib import Path

def setup_mcp_cli():
    config = {
        "server_url": "http://localhost:7272",
        "api_key": None,  # Set if using API key auth
        "timeout": 30
    }
    
    config_dir = Path.home() / '.giljoai'
    config_dir.mkdir(exist_ok=True)
    
    with open(config_dir / 'mcp_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ MCP CLI configuration saved to ~/.giljoai/mcp_config.json")
    
if __name__ == "__main__":
    setup_mcp_cli()
```

**Backend Processing**:
```python
# POST /api/setup/mcp-config
async def configure_mcp(request: MCPConfigRequest):
    # Save MCP configuration to database
    setup_state = await get_setup_state(tenant_key="default")
    setup_state.mcp_enabled = request.enabled
    setup_state.mcp_configured_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": "MCP configuration saved"}
```

#### Step 4b: Serena Activation (Optional)

**Serena MCP Server Setup**:

```
┌─────────────────────────────────────────────────────────┐
│                🧠 Serena MCP Server                     │
│                                                         │
│  Serena provides advanced code analysis and symbolic   │
│  navigation for agent orchestration.                   │
│                                                         │
│  Features:                                              │
│  • Semantic code search                                 │
│  • Symbol navigation                                    │
│  • Advanced refactoring                                 │
│  • Context-aware suggestions                            │
│                                                         │
│  ☐ Enable Serena MCP Server                           │
│                                                         │
│  Installation Methods:                                  │
│                                                         │
│  🚀 Quick Install (Recommended):                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ uvx install serena-mcp                          │   │
│  │ [Copy Command]                                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  💻 Local Development:                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ git clone https://github.com/serena/serena-mcp │   │
│  │ cd serena-mcp && pip install -e .              │   │
│  │ [Copy Commands]                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [ Skip ]                              [ Next Step ]   │
└─────────────────────────────────────────────────────────┘
```

**Installation Guidance**:
- **uvx install** (recommended for most users)
- **Local development** (for contributors)
- **Docker option** (for containerized environments)

**Backend Processing**:
```python
# POST /api/setup/serena-config  
async def configure_serena(request: SerenaConfigRequest):
    setup_state = await get_setup_state(tenant_key="default")
    setup_state.serena_enabled = request.enabled
    setup_state.serena_configured_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": "Serena configuration saved"}
```

#### Step 4c: Setup Complete

**Setup Summary Screen**:

```
┌─────────────────────────────────────────────────────────┐
│                   ✅ Setup Complete!                    │
│                                                         │
│  Your GiljoAI MCP installation is ready for use.       │
│                                                         │
│  Configuration Summary:                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🔗 MCP Integration:     ✅ Enabled            │   │
│  │ 🧠 Serena MCP Server:   ✅ Enabled            │   │
│  │ 🗄️  Database:            ✅ Connected          │   │
│  │ 🔐 Authentication:       ✅ Configured         │   │
│  │ 🚀 Services:            ✅ Running            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Next Steps:                                            │
│  • Explore the dashboard                                │
│  • Create your first project                            │
│  • Learn about agent orchestration                      │
│                                                         │
│  Documentation:                                         │
│  📚 Getting Started Guide                              │
│  📖 API Documentation                                   │
│  🎯 Agent Orchestration Tutorial                       │
│                                                         │
│  [ Go to Dashboard ]                                    │
└─────────────────────────────────────────────────────────┘
```

**Backend Completion**:
```python
# POST /api/setup/complete
async def complete_setup():
    setup_state = await get_setup_state(tenant_key="default")
    setup_state.setup_completed = True
    setup_state.setup_completed_at = datetime.utcnow()
    
    await session.commit()
    
    # Return success and redirect
    return {
        "message": "Setup completed successfully",
        "redirect_url": "/dashboard"
    }
```

### Step 5: Dashboard Introduction

**Dashboard Landing**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🤖 GiljoAI MCP Dashboard                        👤 admin [▼]           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  🎉 Welcome to GiljoAI MCP v3.0!                                      │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │   📦 Products    │  │   🎯 Projects    │  │   🤖 Agents      │    │
│  │                  │  │                  │  │                  │    │
│  │  Create your     │  │  Start a new     │  │  No active       │    │
│  │  first product   │  │  development     │  │  agents yet      │    │
│  │                  │  │  project         │  │                  │    │
│  │ [+ New Product]  │  │ [+ New Project]  │  │                  │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘    │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                        📊 System Status                          │ │
│  │                                                                  │ │
│  │  API Server:     ✅ Healthy     Database:    ✅ Connected      │ │
│  │  WebSocket:      ✅ Active      Memory Usage: 📊 125 MB       │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                      🚀 Quick Actions                            │ │
│  │                                                                  │ │
│  │  [🎯 Create First Project]  [📚 View Documentation]            │ │
│  │  [🧠 Learn Orchestration]   [⚙️ System Settings]               │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Dashboard Features**:
- **Products Overview** - Top-level organizational units
- **Projects Dashboard** - Active development projects
- **Agent Monitoring** - Real-time agent status and coordination
- **System Health** - API, database, WebSocket connection status
- **Quick Actions** - Common workflows and documentation links

**WebSocket Connection**:
Upon dashboard load, the frontend establishes a WebSocket connection:

```javascript
// Frontend WebSocket initialization
const token = localStorage.getItem('auth_token')
const ws = new WebSocket(`ws://localhost:7272/ws/dashboard?token=${token}`)

ws.onopen = () => {
  console.log('✅ WebSocket connected - real-time updates enabled')
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  // Update dashboard with real-time agent status, project updates
}
```

---

## Common First Launch Scenarios

### Scenario 1: Localhost Development (Default)

**Access**: http://localhost:7274

**Experience**:
1. Admin account setup (user-defined credentials)
2. Setup wizard (optional steps can be skipped)
3. Dashboard with localhost-only access
4. All services running locally

**Configuration**:
```yaml
services:
  api:
    host: 0.0.0.0          # Binds all interfaces
    external_host: localhost # How clients connect
  
database:
  host: localhost           # Always localhost
```

### Scenario 2: LAN Access Setup

**Access**: http://192.168.1.100:7274 (network IP)

**Experience**:
1. Same authentication flow (no auto-login)
2. Password change required from any IP
3. Setup wizard includes network configuration
4. Dashboard accessible from LAN

**Additional Setup**:
```bash
# Configure firewall for LAN access
# Windows PowerShell
New-NetFirewallRule -DisplayName "GiljoAI MCP LAN" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272,7274 `
    -RemoteAddress 192.168.1.0/24
```

**Configuration Update**:
```yaml
security:
  cors:
    allowed_origins:
      - "http://127.0.0.1:7274"
      - "http://localhost:7274"  
      - "http://192.168.1.100:7274"  # LAN access
```

### Scenario 3: WAN/Production Setup

**Access**: https://yourdomain.com (with reverse proxy)

**Experience**:
1. HTTPS-only access
2. Same authentication flow (no shortcuts)
3. Enhanced security warnings
4. Production-grade configuration

**Additional Requirements**:
- Reverse proxy (nginx, Caddy, Apache)
- SSL/TLS certificates
- Enhanced firewall configuration
- Monitoring and logging

---

## Troubleshooting First Launch

### Common Issues & Solutions

**Issue: Browser doesn't open automatically**
```bash
# Manual access
open http://localhost:7274          # macOS
start http://localhost:7274         # Windows
xdg-open http://localhost:7274      # Linux

# Or visit URL directly in any browser
```

**Issue: "Connection refused" error**
```bash
# Check if services are running
netstat -tulpn | grep 7272  # API server
netstat -tulpn | grep 7274  # Frontend server

# Restart services if needed
python startup.py
```

**Issue: Cannot change password**
```bash
# Check database connection
psql -U postgres -h localhost -d giljo_mcp -c "SELECT 1;"

# Check default user exists
psql -U postgres -h localhost -d giljo_mcp -c "SELECT username FROM users WHERE username='admin';"

# Reset if needed (advanced)
psql -U postgres -h localhost -d giljo_mcp -c "UPDATE setup_state SET default_password_active=true WHERE tenant_key='default';"
```

**Issue: Setup wizard not loading**
```bash
# Check API health
curl http://localhost:7272/health

# Check setup endpoints
curl http://localhost:7272/api/setup/status

# Clear browser cache and cookies
# Try incognito/private browsing mode
```

**Issue: WebSocket connection failed**
```bash
# Check JWT token validity (browser console)
const token = localStorage.getItem('auth_token')
console.log('Token:', token)

# Check WebSocket endpoint directly
wscat -c "ws://localhost:7272/ws/test?token=YOUR_TOKEN"

# Restart services if needed
```

### Recovery Procedures

**Reset Password Change Flag**:
```sql
-- If password change got stuck, reset the flag
UPDATE setup_state 
SET default_password_active = true 
WHERE tenant_key = 'default';
```

**Reset Setup Wizard**:
```sql
-- Reset setup wizard to start from beginning
UPDATE setup_state 
SET setup_completed = false,
    mcp_enabled = false,
    serena_enabled = false
WHERE tenant_key = 'default';
```

**Complete Fresh Start**:
```bash
# Stop services
# Ctrl+C in terminal

# Drop database and restart
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"
python install.py
```

---

## Next Steps After First Launch

### Immediate Actions

1. **Create First Product**:
   - Click "New Product" on dashboard
   - Name: e.g., "My Web Application"
   - Description: Brief project overview

2. **Create First Project**:
   - Click "New Project" within product
   - Define project scope and goals
   - Upload or link vision documents

3. **Explore Agent Templates**:
   - Review available agent roles
   - Understand orchestration concepts
   - Try example workflows

### Learning Resources

**Built-in Documentation**:
- 📚 **API Documentation**: http://localhost:7272/docs
- 🎯 **Interactive API**: http://localhost:7272/redoc  
- 📊 **System Health**: http://localhost:7272/health

**Local Documentation** (created during installation):
- `docs/README_FIRST.md` - Navigation hub
- `docs/GILJOAI_MCP_PURPOSE.md` - System overview
- `docs/USER_STRUCTURES_TENANTS.md` - Multi-tenant understanding
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - Technical details

**Example Workflows**:
1. **Simple Task**: Create a basic web page with agent coordination
2. **Multi-Agent Project**: Build a REST API with database and tests
3. **Complex Orchestration**: Full-stack application with multiple specialized agents

### Advanced Configuration

**Network Access** (if needed):
1. Configure firewall rules
2. Update CORS origins in config.yaml
3. Test LAN accessibility
4. Consider reverse proxy for WAN

**Development Tools**:
1. Install MCP integrations (Claude Desktop, VS Code)
2. Set up Serena MCP server
3. Configure git workflows
4. Add custom agent templates

**Production Preparation**:
1. Change admin username (optional)
2. Set up additional users
3. Configure backup procedures
4. Implement monitoring

---

## First Launch Success Checklist

After completing first launch, verify:

- [ ] **Admin Created**: First admin account setup completed
- [ ] **Dashboard Accessible**: Can access http://localhost:7274
- [ ] **API Responding**: http://localhost:7272/health returns healthy
- [ ] **Database Connected**: No database errors in logs
- [ ] **WebSocket Active**: Real-time updates working in dashboard
- [ ] **Setup Complete**: Setup wizard marked as completed
- [ ] **Services Running**: Both API and frontend servers active
- [ ] **JWT Working**: Authentication persists across browser refresh

**Optional Verifications**:
- [ ] **MCP Configured**: If enabled in setup wizard
- [ ] **Serena Active**: If Serena MCP server installed
- [ ] **LAN Access**: If network access configured
- [ ] **Documentation Accessible**: Local docs readable

---

**See Also**:
- [Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md) - Complete installation procedures
- [User Structures & Tenants](USER_STRUCTURES_TENANTS.md) - Understanding the multi-tenant system
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - Technical implementation details
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE.md) - System overview and capabilities

---

*This document provides comprehensive first launch guidance and troubleshooting as the single source of truth for the October 13, 2025 documentation harmonization.*