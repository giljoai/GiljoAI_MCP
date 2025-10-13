# GiljoAI MCP - Single Product Recalibration

**Project:** Consolidate LOCAL/LAN/WAN modes into unified product architecture
**Status:** Planning Phase
**Target Release:** v3.0
**Backup Branch:** `retired_multi_network_architecture`
**Estimated Duration:** 3-4 weeks

---

## Executive Summary

### Current State: Three-Mode Architecture (Technical Debt)

The current architecture maintains three deployment modes (LOCAL, LAN, WAN) with 87% code duplication:

```
Current Architecture (Fragmented)
├─ LOCAL Mode
│  ├─ Network: 127.0.0.1 binding
│  ├─ Auth: Disabled
│  ├─ Users: None (empty schema)
│  └─ MCP: Direct file injection
├─ LAN Mode
│  ├─ Network: 0.0.0.0 binding
│  ├─ Auth: JWT + API keys
│  ├─ Users: Multi-user with isolation
│  └─ MCP: Manual copy-paste
└─ WAN Mode
   ├─ Network: 127.0.0.1 (reverse proxy)
   ├─ Auth: JWT + API keys + TLS
   ├─ Users: Multi-user with isolation
   └─ MCP: Manual copy-paste
```

**Problems:**
- Multi-tenant code runs in LOCAL mode (unused, performance waste)
- Mode-switching logic scattered across 15+ files
- 3x test matrix complexity
- Inconsistent feature availability
- User confusion ("Which mode do I need?")

### Target State: Unified Product Architecture

```
Unified Architecture (Consolidated)
├─ Single Codebase
│  ├─ Network: 0.0.0.0 binding (firewall controls access)
│  ├─ Auth: Always enabled (auto-login for 127.0.0.1)
│  ├─ Users: Always active (1 localhost user default)
│  └─ MCP: Downloadable scripts (all platforms)
│
├─ Deployment Contexts (not modes)
│  ├─ Localhost Developer
│  │  ├─ Firewall: Blocks external access
│  │  ├─ Auth: Auto-login via IP detection
│  │  └─ UX: Zero-click access
│  │
│  ├─ Team LAN
│  │  ├─ Firewall: Allows LAN IPs
│  │  ├─ Auth: JWT + API keys
│  │  └─ UX: Login required
│  │
│  └─ Internet (WAN)
│     ├─ Firewall: Reverse proxy + strict rules
│     ├─ Auth: JWT + API keys + TLS
│     └─ UX: Login required
│
└─ Hosted SaaS (Separate Product)
   └─ Different infrastructure entirely
```

**Benefits:**
- Remove ~500 lines of mode-switching logic
- Single test matrix
- Consistent feature parity
- Better security (defense in depth)
- Clearer user experience

---

## Strategic Vision

### Product Positioning

**Self-Hosted (This Project):**
- User owns infrastructure
- User manages firewall/network
- Free, unlimited scale
- Single installation, any deployment context

**Hosted SaaS (Future Product):**
- Platform-managed infrastructure
- Subscription billing model
- SLA guarantees
- Multi-customer isolation

**Decision:** Consolidate self-hosted variants, keep hosted SaaS separate.

---

## Phase Breakdown

### Phase 0: Preparation & Backup ✅

**Status:** COMPLETE

- [x] Create backup branch: `retired_multi_network_architecture`
- [x] Commit current state with clear message
- [x] Document current architecture
- [x] Write this consolidation plan

**Branch Status:**
```bash
git branch retired_multi_network_architecture  # Backup created
git checkout master                            # Ready for changes
```

---

### Phase 1: Core Architecture Consolidation (Week 1-2)

**Goal:** Remove DeploymentMode enum, unify authentication, implement auto-login

#### 1.1 Authentication Consolidation

**Files to Modify:**
- `src/giljo_mcp/config_manager.py`
- `api/middleware/auth.py`
- `api/dependencies/auth.py`

**Changes:**

1. **Remove DeploymentMode Enum**
```python
# BEFORE (config_manager.py)
class DeploymentMode(Enum):
    LOCAL = "local"
    LAN = "lan"
    WAN = "wan"

# AFTER
# Remove enum entirely, replace with feature flags
@dataclass
class ServerConfig:
    authentication_enabled: bool = True  # Always true
    network_binding: str = "0.0.0.0"    # Always all interfaces
```

2. **Implement Auto-Login Middleware**
```python
# NEW (api/middleware/auto_login.py)
class AutoLoginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Auto-login for localhost clients
        if request.client.host in ("127.0.0.1", "::1"):
            request.state.user = await get_or_create_localhost_user()
            request.state.authenticated = True
        else:
            # Network access requires real authentication
            await validate_jwt_or_api_key(request)

        return await call_next(request)
```

3. **Create Localhost User at Startup**
```python
# NEW (api/startup.py)
async def ensure_localhost_user():
    """Create default localhost user if not exists"""
    user = await db.query(User).filter(
        User.username == "localhost"
    ).first()

    if not user:
        user = User(
            username="localhost",
            email="localhost@local",
            password_hash=None,  # No password
            api_key=generate_api_key("gk_localhost_"),
            role="admin",
            is_system_user=True
        )
        db.add(user)
        await db.commit()

    return user
```

**Testing Requirements:**
- [ ] Localhost access (127.0.0.1) auto-authenticates
- [ ] Network access (192.168.x.x) requires login
- [ ] API endpoints work with auto-login user
- [ ] WebSocket connections authenticate properly

**Success Criteria:**
- Localhost users see instant access (no login screen)
- Network users see login prompt
- No mode-checking logic in auth flow

---

#### 1.2 Configuration System Simplification

**Files to Modify:**
- `src/giljo_mcp/config_manager.py`
- `installer/core/config.py`
- `config.yaml` (structure change)

**Changes:**

1. **Simplify config.yaml Structure**
```yaml
# BEFORE
installation:
  mode: local  # or lan, wan

# AFTER
installation:
  version: 3.0.0
  deployment_context: localhost  # Descriptive only, not functional

features:
  authentication: true          # Always enabled
  auto_login_localhost: true    # IP-based auto-login
  firewall_configured: false    # Installer sets this
```

2. **Remove Mode-Specific Logic**
```python
# BEFORE (config_manager.py)
def _apply_mode_settings(self):
    if self.server.mode == DeploymentMode.LOCAL:
        self.server.api_host = "127.0.0.1"
        self.server.api_key = None
    elif self.server.mode == DeploymentMode.LAN:
        self.server.api_host = "0.0.0.0"
        if not self.server.api_key:
            self.server.api_key = secrets.token_urlsafe(32)

# AFTER
# Remove method entirely, use fixed values:
self.server.api_host = "0.0.0.0"  # Always bind all interfaces
# API keys always generated (including localhost user)
```

3. **Update Environment Variables**
```bash
# BEFORE (.env)
GILJO_MCP_MODE=local  # or lan, wan

# AFTER (.env)
# Remove GILJO_MCP_MODE entirely
GILJO_AUTO_LOGIN_LOCALHOST=true
GILJO_NETWORK_BINDING=0.0.0.0
```

**Migration Script:**
```python
# scripts/migrate_config_v3.py
def migrate_config_v2_to_v3(config_path: Path):
    """Migrate v2.x config to v3.0 unified format"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Detect old mode
    old_mode = config.get('installation', {}).get('mode', 'local')

    # Remove mode, add new structure
    config['installation']['version'] = '3.0.0'
    config['installation']['deployment_context'] = old_mode
    del config['installation']['mode']

    # Add feature flags
    config['features']['authentication'] = True
    config['features']['auto_login_localhost'] = True

    # Write back
    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    print(f"✅ Migrated config from {old_mode} mode to v3.0 unified")
```

**Testing Requirements:**
- [ ] Config migration script works for all v2.x configs
- [ ] New installations generate v3.0 config
- [ ] Config validation catches old mode values
- [ ] Environment variables load correctly

---

#### 1.3 Database Schema Updates

**Files to Modify:**
- `src/giljo_mcp/models/user.py`
- `api/migrations/` (new migration)

**Changes:**

1. **Add System User Flag**
```python
# src/giljo_mcp/models/user.py
class User(Base):
    __tablename__ = "users"

    # Existing fields...

    # NEW: Mark localhost user as system-managed
    is_system_user: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="True for auto-created localhost user"
    )
```

2. **Migration Script**
```python
# api/migrations/versions/003_add_system_user_flag.py
def upgrade():
    op.add_column('users', sa.Column(
        'is_system_user',
        sa.Boolean(),
        nullable=False,
        server_default='false'
    ))

    # Mark existing localhost user if exists
    op.execute("""
        UPDATE users
        SET is_system_user = true
        WHERE username = 'localhost'
    """)

def downgrade():
    op.drop_column('users', 'is_system_user')
```

**Testing Requirements:**
- [ ] Migration runs successfully on existing databases
- [ ] Localhost user gets system flag
- [ ] New installations create localhost user correctly
- [ ] System users cannot be deleted via UI

---

#### 1.4 Update Installer

**Files to Modify:**
- `installer/cli/install.py`
- `installer/core/config.py`
- `installer/core/installer.py`

**Changes:**

1. **Remove Mode Selection**
```python
# BEFORE (installer/cli/install.py)
@click.option('--mode',
              type=click.Choice(['local', 'server']),
              default='local')

# AFTER
# Remove option entirely
# Default behavior: Create localhost user + configure firewall
```

2. **Always Create Localhost User**
```python
# installer/core/installer.py
def setup_database(self):
    """Create database and default localhost user"""
    # Create database
    self.create_database()

    # Run migrations
    self.run_migrations()

    # Create localhost user (always)
    self.create_localhost_user()

    print("✅ Database configured with localhost user")
```

3. **Add Firewall Configuration**
```python
# NEW (installer/core/firewall.py)
class FirewallConfigurator:
    """Configure OS firewall for localhost-only access"""

    def configure_localhost_only(self):
        """Block external access, allow localhost"""
        if platform.system() == "Windows":
            self._configure_windows_firewall()
        elif platform.system() == "Linux":
            self._configure_linux_firewall()
        elif platform.system() == "Darwin":
            self._configure_macos_firewall()

    def _configure_windows_firewall(self):
        """Add Windows Firewall rule"""
        subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            "name=GiljoAI MCP - Block External",
            "dir=in",
            "action=block",
            "protocol=TCP",
            "localport=7272,7274",
            "remoteip=any",
            "enable=yes"
        ])

        subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            "name=GiljoAI MCP - Allow Localhost",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            "localport=7272,7274",
            "remoteip=127.0.0.1",
            "enable=yes"
        ])
```

**Testing Requirements:**
- [ ] Installer runs without mode selection
- [ ] Localhost user created automatically
- [ ] Firewall rules configured correctly
- [ ] External access blocked by default
- [ ] Localhost access works

---

### Phase 2: MCP Integration System (Week 2-3)

**Goal:** Implement downloadable script generation for multi-tool MCP configuration

#### 2.1 Backend: Script Generator API

**New Files to Create:**
- `api/endpoints/mcp_installer.py`
- `installer/templates/giljo-mcp-setup.bat.template`
- `installer/templates/giljo-mcp-setup.sh.template`

**Implementation:**

1. **API Endpoints**
```python
# api/endpoints/mcp_installer.py
from fastapi import APIRouter, Depends, Response
from datetime import datetime, timedelta
import secrets

router = APIRouter(prefix="/api/mcp-installer", tags=["MCP Integration"])

@router.get("/windows")
async def download_windows_installer(
    current_user: User = Depends(get_current_user)
):
    """Generate Windows .bat installer with embedded credentials"""

    # Load template
    template_path = Path("installer/templates/giljo-mcp-setup.bat.template")
    template = template_path.read_text()

    # Embed user configuration
    script = template.format(
        server_url=get_server_url(),
        api_key=current_user.api_key,
        username=current_user.username,
        organization=current_user.organization.name if current_user.organization else "Personal",
        timestamp=datetime.now().isoformat()
    )

    return Response(
        content=script,
        media_type="application/bat",
        headers={
            "Content-Disposition": "attachment; filename=giljo-mcp-setup.bat"
        }
    )

@router.get("/unix")
async def download_unix_installer(
    current_user: User = Depends(get_current_user)
):
    """Generate macOS/Linux .sh installer with embedded credentials"""

    template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
    template = template_path.read_text()

    script = template.format(
        server_url=get_server_url(),
        api_key=current_user.api_key,
        username=current_user.username,
        organization=current_user.organization.name if current_user.organization else "Personal",
        timestamp=datetime.now().isoformat()
    )

    return Response(
        content=script,
        media_type="application/x-sh",
        headers={
            "Content-Disposition": "attachment; filename=giljo-mcp-setup.sh"
        }
    )

@router.post("/share-link")
async def generate_share_link(
    current_user: User = Depends(get_current_user)
):
    """Generate secure URLs for script download (email-friendly)"""

    # Generate token (7 day expiration)
    token = generate_secure_token(
        user_id=current_user.id,
        expires_in=7*24*3600
    )

    base_url = get_server_url()

    return {
        "windows_url": f"{base_url}/download/mcp/{token}/windows",
        "unix_url": f"{base_url}/download/mcp/{token}/unix",
        "expires_at": datetime.now() + timedelta(days=7),
        "token": token
    }

@router.get("/download/{token}/{platform}")
async def download_via_token(token: str, platform: str):
    """Public download endpoint using secure token"""

    # Validate token
    user_info = validate_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Load user
    user = await get_user_by_id(user_info["user_id"])

    # Generate script (reuse above logic)
    if platform == "windows":
        return await download_windows_installer(user)
    elif platform == "unix":
        return await download_unix_installer(user)
    else:
        raise HTTPException(status_code=400, detail="Invalid platform")
```

2. **Windows Script Template**
```batch
# installer/templates/giljo-mcp-setup.bat.template
@echo off
REM ============================================================
REM GiljoAI MCP Tool Integration Installer
REM Generated for: {organization}
REM User: {username}
REM Server: {server_url}
REM Generated: {timestamp}
REM ============================================================

echo.
echo ============================================================
echo   GiljoAI MCP - Tool Integration Installer
echo ============================================================
echo.
echo This script will detect your development tools and configure
echo them to use GiljoAI Agent Orchestration MCP Server.
echo.
echo Server: {server_url}
echo User: {username}
echo.
pause

REM Configuration
set GILJO_SERVER={server_url}
set GILJO_API_KEY={api_key}
set GILJO_USER={username}

echo.
echo Scanning for supported development tools...
echo.

REM ============================================================
REM Detect Claude Code
REM ============================================================
set CLAUDE_CONFIG=%APPDATA%\.claude.json
if exist "%CLAUDE_CONFIG%" (
    echo [FOUND] Claude Code: %CLAUDE_CONFIG%
    call :configure_claude
) else (
    echo [SKIP] Claude Code not detected
)

REM ============================================================
REM Detect Cursor
REM ============================================================
set CURSOR_CONFIG=%APPDATA%\Cursor\User\globalStorage\mcp.json
if exist "%CURSOR_CONFIG%" (
    echo [FOUND] Cursor: %CURSOR_CONFIG%
    call :configure_cursor
) else (
    echo [SKIP] Cursor not detected
)

REM ============================================================
REM Detect Windsurf
REM ============================================================
set WINDSURF_CONFIG=%APPDATA%\Windsurf\config.json
if exist "%WINDSURF_CONFIG%" (
    echo [FOUND] Windsurf: %WINDSURF_CONFIG%
    call :configure_windsurf
) else (
    echo [SKIP] Windsurf not detected
)

REM ============================================================
REM Summary
REM ============================================================
echo.
echo ============================================================
echo   Configuration Complete!
echo ============================================================
echo.
echo Configured tools:
if defined CLAUDE_CONFIGURED echo   - Claude Code
if defined CURSOR_CONFIGURED echo   - Cursor
if defined WINDSURF_CONFIGURED echo   - Windsurf
echo.
echo Server: %GILJO_SERVER%
echo User: %GILJO_USER%
echo.
echo Please restart your development tools for changes to take effect.
echo.
pause
exit /b 0

REM ============================================================
REM Function: Configure Claude Code
REM ============================================================
:configure_claude
    echo   Configuring Claude Code...

    REM Create backup
    copy "%CLAUDE_CONFIG%" "%CLAUDE_CONFIG%.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%" >nul

    REM Use PowerShell to merge JSON safely
    powershell -Command ^
        "$config = if (Test-Path '%CLAUDE_CONFIG%') { Get-Content '%CLAUDE_CONFIG%' -Raw | ConvertFrom-Json } else { @{} }; ^
         if (-not $config.mcpServers) { $config | Add-Member -Type NoteProperty -Name mcpServers -Value @{} -Force }; ^
         $config.mcpServers.'giljo-mcp' = @{ ^
             command = 'python'; ^
             args = @('-m', 'giljo_mcp.mcp_adapter'); ^
             env = @{ ^
                 GILJO_SERVER_URL = '%GILJO_SERVER%'; ^
                 GILJO_API_KEY = '%GILJO_API_KEY%' ^
             } ^
         }; ^
         $config | ConvertTo-Json -Depth 10 | Set-Content '%CLAUDE_CONFIG%'"

    if %errorlevel% equ 0 (
        echo   [OK] Claude Code configured successfully
        set CLAUDE_CONFIGURED=1
    ) else (
        echo   [ERROR] Failed to configure Claude Code
    )
    goto :eof

REM ============================================================
REM Function: Configure Cursor
REM ============================================================
:configure_cursor
    echo   Configuring Cursor...

    REM Create config directory if not exists
    if not exist "%APPDATA%\Cursor\User\globalStorage" mkdir "%APPDATA%\Cursor\User\globalStorage"

    REM Write MCP config
    powershell -Command ^
        "$config = if (Test-Path '%CURSOR_CONFIG%') { Get-Content '%CURSOR_CONFIG%' -Raw | ConvertFrom-Json } else { @{} }; ^
         if (-not $config.mcpServers) { $config | Add-Member -Type NoteProperty -Name mcpServers -Value @{} -Force }; ^
         $config.mcpServers.'giljo-mcp' = @{ ^
             command = 'python'; ^
             args = @('-m', 'giljo_mcp.mcp_adapter'); ^
             env = @{ ^
                 GILJO_SERVER_URL = '%GILJO_SERVER%'; ^
                 GILJO_API_KEY = '%GILJO_API_KEY%' ^
             } ^
         }; ^
         $config | ConvertTo-Json -Depth 10 | Set-Content '%CURSOR_CONFIG%'"

    if %errorlevel% equ 0 (
        echo   [OK] Cursor configured successfully
        set CURSOR_CONFIGURED=1
    ) else (
        echo   [ERROR] Failed to configure Cursor
    )
    goto :eof

REM ============================================================
REM Function: Configure Windsurf
REM ============================================================
:configure_windsurf
    echo   Configuring Windsurf...

    REM Similar logic for Windsurf

    set WINDSURF_CONFIGURED=1
    goto :eof
```

3. **Unix Script Template** (similar structure, see full code in final implementation)

**Testing Requirements:**
- [ ] Windows script detects Claude Code, Cursor, Windsurf
- [ ] Unix script detects tools on macOS/Linux
- [ ] JSON merging preserves existing config
- [ ] Backup files created before modification
- [ ] Scripts work with embedded credentials
- [ ] Error handling for missing PowerShell/jq

---

#### 2.2 Frontend: Admin MCP Settings

**New Files to Create:**
- `frontend/src/views/admin/McpIntegration.vue`
- `frontend/src/components/admin/McpScriptDownload.vue`
- `frontend/src/components/admin/McpShareLink.vue`

**Implementation:**

1. **Main MCP Integration View**
```vue
<!-- frontend/src/views/admin/McpIntegration.vue -->
<template>
  <div class="mcp-integration-page">
    <PageHeader
      title="MCP Tool Integration"
      subtitle="Configure development tools to use GiljoAI Agent Orchestrator"
    />

    <!-- Download Section -->
    <Card title="Download Installer Scripts" class="mb-6">
      <p class="text-gray-600 mb-4">
        Download a pre-configured script that will automatically detect and
        configure your development tools (Claude Code, Cursor, Windsurf).
      </p>

      <div class="download-buttons flex gap-4">
        <Button
          @click="downloadScript('windows')"
          icon="windows"
          size="large"
          variant="primary"
        >
          Download for Windows (.bat)
        </Button>

        <Button
          @click="downloadScript('unix')"
          icon="apple"
          size="large"
          variant="primary"
        >
          Download for macOS/Linux (.sh)
        </Button>
      </div>

      <Alert type="info" class="mt-4">
        <strong>Instructions:</strong>
        <ol class="mt-2 ml-4 list-decimal">
          <li>Download the appropriate script for your operating system</li>
          <li>Right-click → "Run as Administrator" (Windows) or run <code>bash giljo-mcp-setup.sh</code> (Unix)</li>
          <li>The script will auto-detect and configure your development tools</li>
          <li>Restart your IDE to apply changes</li>
        </ol>
      </Alert>
    </Card>

    <!-- Share Link Section -->
    <Card title="Share with Team Members" class="mb-6">
      <p class="text-gray-600 mb-4">
        Generate secure download links to share with your team. Links expire
        after 7 days and avoid email attachment blocking.
      </p>

      <Button
        @click="generateShareLink"
        icon="link"
        :loading="generatingLink"
      >
        Generate Share Links
      </Button>

      <div v-if="shareLinks" class="share-links mt-6">
        <Alert type="success" class="mb-4">
          Share links generated! Valid until {{ formatDate(shareLinks.expires_at) }}
        </Alert>

        <div class="link-group mb-4">
          <label class="font-semibold text-sm text-gray-700 mb-2 block">
            Windows Link
          </label>
          <CodeBlock
            :code="shareLinks.windows_url"
            language="text"
            copyable
          />
        </div>

        <div class="link-group mb-4">
          <label class="font-semibold text-sm text-gray-700 mb-2 block">
            macOS/Linux Link
          </label>
          <CodeBlock
            :code="shareLinks.unix_url"
            language="text"
            copyable
          />
        </div>

        <details class="mt-4">
          <summary class="cursor-pointer text-blue-600 hover:text-blue-800">
            View Email Template
          </summary>
          <CodeBlock
            :code="emailTemplate"
            language="text"
            copyable
            class="mt-2"
          />
        </details>
      </div>
    </Card>

    <!-- Manual Configuration (Fallback) -->
    <Card title="Manual Configuration" class="mb-6">
      <details>
        <summary class="cursor-pointer text-blue-600 hover:text-blue-800">
          Advanced: Manual JSON Configuration
        </summary>

        <p class="text-gray-600 mt-4 mb-2">
          If automatic configuration doesn't work, you can manually add this
          configuration to your tool's config file:
        </p>

        <CodeBlock
          :code="manualConfig"
          language="json"
          copyable
        />

        <div class="config-paths mt-4">
          <p class="font-semibold text-sm text-gray-700 mb-2">Config file locations:</p>
          <ul class="ml-4 list-disc text-sm text-gray-600">
            <li><strong>Claude Code:</strong> <code>~/.claude.json</code> (Unix) or <code>%APPDATA%\.claude.json</code> (Windows)</li>
            <li><strong>Cursor:</strong> <code>~/.config/Cursor/User/globalStorage/mcp.json</code></li>
            <li><strong>Windsurf:</strong> <code>~/.config/Windsurf/config.json</code></li>
          </ul>
        </div>
      </details>
    </Card>

    <!-- Troubleshooting -->
    <Card title="Troubleshooting">
      <Accordion>
        <AccordionItem title="Script fails with 'Permission Denied'">
          <p>Make sure you're running the script with administrator/root privileges:</p>
          <ul class="ml-4 list-disc mt-2">
            <li><strong>Windows:</strong> Right-click → "Run as Administrator"</li>
            <li><strong>macOS/Linux:</strong> <code>sudo bash giljo-mcp-setup.sh</code></li>
          </ul>
        </AccordionItem>

        <AccordionItem title="Tool not detected by script">
          <p>The script looks for config files in standard locations. If your tool is installed in a custom location:</p>
          <ol class="ml-4 list-decimal mt-2">
            <li>Use the "Manual Configuration" section above</li>
            <li>Copy the JSON configuration</li>
            <li>Add it to your tool's config file manually</li>
          </ol>
        </AccordionItem>

        <AccordionItem title="Configuration not working after script">
          <p>Try these steps:</p>
          <ol class="ml-4 list-decimal mt-2">
            <li>Completely restart your IDE (not just reload)</li>
            <li>Check that Python is in your PATH: <code>python --version</code></li>
            <li>Verify network connectivity to: <strong>{{ serverUrl }}</strong></li>
            <li>Check your API key is valid in Account Settings</li>
          </ol>
        </AccordionItem>
      </Accordion>
    </Card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useAuth } from '@/composables/useAuth'
import { formatDate } from '@/utils/date'

const api = useApi()
const { currentUser } = useAuth()

const generatingLink = ref(false)
const shareLinks = ref(null)
const manualConfig = ref(null)

const serverUrl = computed(() => window.location.origin)

const emailTemplate = computed(() => {
  if (!shareLinks.value) return ''

  return `Subject: GiljoAI MCP Tool Integration Setup

Hi team,

To integrate your development tools with our GiljoAI Agent Orchestration server, please download and run the setup script:

Windows users: ${shareLinks.value.windows_url}
macOS/Linux users: ${shareLinks.value.unix_url}

Instructions:
1. Download the appropriate script for your OS
2. Right-click → "Run as Administrator" (Windows) or run "bash giljo-mcp-setup.sh" (macOS/Linux)
3. The script will auto-detect and configure your tools (Claude Code, Cursor, Windsurf)
4. Restart your IDE

The script will configure:
- Server: ${serverUrl.value}
- Your personal API key (embedded in script)

Links expire: ${formatDate(shareLinks.value.expires_at)}

Questions? Contact me or check our docs: ${serverUrl.value}/docs/mcp-integration

Thanks!`
})

async function downloadScript(platform) {
  try {
    const endpoint = platform === 'windows'
      ? '/api/mcp-installer/windows'
      : '/api/mcp-installer/unix'

    const response = await api.get(endpoint, { responseType: 'blob' })

    // Trigger download
    const url = window.URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = platform === 'windows'
      ? 'giljo-mcp-setup.bat'
      : 'giljo-mcp-setup.sh'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Download failed:', error)
    alert('Failed to download script. Please try again.')
  }
}

async function generateShareLink() {
  generatingLink.value = true
  try {
    const response = await api.post('/api/mcp-installer/share-link')
    shareLinks.value = response.data
  } catch (error) {
    console.error('Failed to generate share link:', error)
    alert('Failed to generate share link. Please try again.')
  } finally {
    generatingLink.value = false
  }
}

async function loadManualConfig() {
  try {
    const response = await api.post('/api/setup/generate-mcp-config')
    manualConfig.value = JSON.stringify(response.data, null, 2)
  } catch (error) {
    console.error('Failed to load manual config:', error)
  }
}

// Load manual config on mount
loadManualConfig()
</script>
```

**Testing Requirements:**
- [ ] Download buttons generate correct scripts
- [ ] Share link generation works
- [ ] Email template renders correctly
- [ ] Manual config displays properly
- [ ] Troubleshooting accordion expands
- [ ] All links copyable

---

### Phase 3: Testing & Validation (Week 3)

#### 3.1 Unit Tests

**New Test Files:**
- `tests/unit/test_auto_login.py`
- `tests/unit/test_config_migration.py`
- `tests/unit/test_mcp_script_generator.py`

**Coverage Requirements:**
- [ ] Auto-login middleware (localhost detection)
- [ ] Localhost user creation
- [ ] Config migration (v2 → v3)
- [ ] Script generation with embedded credentials
- [ ] Token generation and validation

---

#### 3.2 Integration Tests

**Test Scenarios:**
- [ ] Fresh install creates localhost user
- [ ] Localhost access (127.0.0.1) auto-authenticates
- [ ] Network access (192.168.x.x) requires login
- [ ] MCP script downloads with correct credentials
- [ ] Share link generation and download
- [ ] Firewall rules block external access
- [ ] Migration from v2.x to v3.0

---

#### 3.3 Cross-Platform Testing

**Platforms:**
- [ ] Windows 10/11 (PowerShell 5.1+)
- [ ] macOS 12+ (zsh/bash)
- [ ] Ubuntu 22.04+ (bash)

**Tools:**
- [ ] Claude Code detection and configuration
- [ ] Cursor detection and configuration
- [ ] Windsurf detection and configuration

---

### Phase 4: Documentation & Release (Week 4)

#### 4.1 Documentation

**New Documentation:**

1. **docs/MIGRATION_GUIDE_V3.md**
   - v2.x → v3.0 migration steps
   - Breaking changes
   - Config format changes
   - Feature flag mappings

2. **docs/MCP_INTEGRATION_GUIDE.md**
   - User guide for MCP setup
   - Tool-specific instructions
   - Troubleshooting common issues

3. **docs/ADMIN_MCP_SETUP.md**
   - Admin guide for script distribution
   - Email template examples
   - Team onboarding workflow

4. **docs/FIREWALL_CONFIGURATION.md**
   - OS-specific firewall setup
   - How to enable LAN access
   - Security best practices

5. **CHANGELOG.md**
   - v3.0 release notes
   - Breaking changes
   - New features
   - Deprecations

---

#### 4.2 Release Preparation

**Checklist:**
- [ ] All tests passing (unit, integration, e2e)
- [ ] Migration script validated on real v2.x installations
- [ ] Documentation complete and reviewed
- [ ] Breaking changes documented
- [ ] Release notes finalized
- [ ] Version bumped to 3.0.0

**Release Branch:**
```bash
git checkout -b release/v3.0.0
git tag v3.0.0
git push origin release/v3.0.0 --tags
```

---

## Success Metrics

### Technical Metrics

- [ ] Code reduction: Remove ≥500 lines of mode-switching logic
- [ ] Test simplification: Single test matrix (not 3x)
- [ ] Config simplification: Remove DeploymentMode enum
- [ ] Performance: Auto-login <1ms overhead

### User Experience Metrics

- [ ] Localhost setup: 0-click (same as before)
- [ ] LAN setup: 1-command (vs manual copy-paste)
- [ ] Admin overhead: <5 minutes to onboard new team member
- [ ] Support tickets: Reduce "which mode?" questions to zero

### Architecture Metrics

- [ ] Separation of concerns: Network security moved to OS firewall
- [ ] Code maintainability: Single auth code path
- [ ] Feature parity: MCP wizard available to all users
- [ ] Scalability: Same codebase scales from 1 to N users

---

## Risk Assessment

### High Risk Items

1. **Breaking Changes for Existing Users**
   - **Risk:** Users on v2.x need migration
   - **Mitigation:** Automated migration script + clear docs
   - **Impact:** One-time effort, long-term benefit

2. **Firewall Configuration Complexity**
   - **Risk:** Users might misconfigure firewall
   - **Mitigation:** Installer auto-configures, clear error messages
   - **Impact:** Better than app-level binding (defense in depth)

### Medium Risk Items

1. **Cross-Platform Script Compatibility**
   - **Risk:** Scripts might fail on edge-case OS versions
   - **Mitigation:** Extensive testing, fallback to manual config
   - **Impact:** Graceful degradation to manual setup

2. **Auto-Login Security**
   - **Risk:** IP spoofing for localhost access
   - **Mitigation:** Local network only, firewall blocks external
   - **Impact:** Same threat model as v2.x LOCAL mode

### Low Risk Items

1. **User Confusion on "Logged in as localhost"**
   - **Risk:** Single-user devs might be confused
   - **Mitigation:** Hide username in UI for 127.0.0.1 clients
   - **Impact:** Cosmetic only

---

## Rollback Plan

If critical issues arise post-release:

1. **Immediate Rollback**
   ```bash
   git checkout retired_multi_network_architecture
   git tag v2.9.9
   git push origin v2.9.9
   ```

2. **User Instructions**
   - Downgrade to v2.9.9
   - Restore config.yaml from backup
   - Re-run installer with `--mode local`

3. **Post-Mortem**
   - Document issues
   - Fix in v3.0.1
   - Re-release with fixes

---

## Agent Handoff Prompt

Use this prompt to delegate work to fresh agents in a new context window:

```
# GiljoAI MCP v3.0 Consolidation - Agent Task Assignment

## Context

We are consolidating the GiljoAI MCP codebase from a three-mode architecture (LOCAL/LAN/WAN) to a unified single-product architecture. The goal is to remove 87% code duplication, simplify the user experience, and improve maintainability.

**Backup Branch:** `retired_multi_network_architecture` (already created)
**Target Release:** v3.0
**Project Plan:** `docs/SINGLEPRODUCT_RECALIBRATION.md` (read this first)

## Your Mission

You are being assigned to work on **Phase [X]** of the consolidation project. Read the full plan in `docs/SINGLEPRODUCT_RECALIBRATION.md` to understand the overall strategy, then focus on your assigned phase.

### Phase Assignments

**Phase 1: Core Architecture Consolidation**
- Remove DeploymentMode enum
- Implement auto-login for localhost clients
- Consolidate authentication middleware
- Update configuration system
- Migrate database schema
- Update installer

**Phase 2: MCP Integration System**
- Implement script generator API endpoints
- Create Windows .bat and Unix .sh templates
- Build frontend admin MCP settings UI
- Add share link generation
- Create email templates

**Phase 3: Testing & Validation**
- Write unit tests for auto-login
- Write integration tests for full flow
- Test on Windows/macOS/Linux
- Test tool detection (Claude Code, Cursor, Windsurf)
- Validate migration script

**Phase 4: Documentation & Release**
- Write migration guide (v2.x → v3.0)
- Write MCP integration user guide
- Write admin setup guide
- Write firewall configuration guide
- Prepare release notes

## Instructions for Agents

1. **Read the full plan:** `docs/SINGLEPRODUCT_RECALIBRATION.md`
2. **Understand your phase:** Focus on your assigned phase section
3. **Follow the implementation details:** Code snippets and file modifications are provided
4. **Use specialized agents:**
   - `system-architect`: For architecture decisions and component dependencies
   - `database-expert`: For database schema changes and migrations
   - `tdd-implementor`: For implementing features with tests
   - `backend-integration-tester`: For testing API endpoints
   - `frontend-tester`: For testing UI components
   - `documentation-manager`: For writing docs and guides

5. **Testing is mandatory:** All code must have tests before marking as complete
6. **Update progress:** Use TodoWrite to track your progress
7. **Document decisions:** If you deviate from the plan, document why

## Success Criteria

Your phase is complete when:
- [ ] All code changes implemented per plan
- [ ] All tests written and passing
- [ ] Documentation updated (if applicable)
- [ ] Code reviewed (use system-architect for review)
- [ ] No breaking changes without migration path

## Getting Started

Read the full plan first:
```bash
cat docs/SINGLEPRODUCT_RECALIBRATION.md
```

Then announce which phase you're working on:
```
I'm working on Phase [X]: [Phase Name]
I've read the plan and understand the requirements.
Starting with [first task]...
```

## Questions?

If you encounter ambiguity or need clarification:
1. Check the full plan document
2. Review session memories in `/docs/sessions/`
3. Consult the system-architect agent
4. Ask the user for guidance

**Let's build a better architecture together!**
```

---

## Conclusion

This consolidation project represents a strategic architectural improvement that will:

1. **Simplify the codebase** - Remove 500+ lines of mode-switching logic
2. **Improve user experience** - Clearer deployment model, better onboarding
3. **Enhance security** - Defense in depth with OS firewall + app auth
4. **Enable future growth** - Single codebase scales from 1 to N users
5. **Reduce maintenance** - One test matrix, one auth path, one configuration system

The product is fundamentally the same (agent orchestration platform), but the architecture is cleaner, the user experience is better, and the maintenance burden is lower.

**We're not changing what we do - we're simplifying how we do it.**

---

**Backup Branch:** `retired_multi_network_architecture`
**Next Step:** Review this plan, get approval, then launch Phase 1
**Estimated Completion:** 3-4 weeks
**Target Release:** v3.0.0
