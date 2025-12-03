# Handover 0094: Token-Efficient MCP Downloads for Slash Commands & Agent Templates (Superseded)

**Date:** 2025-01-03
**From Agent:** Planning Session
**To Agent:** Implementation Team (TDD-Implementor + Backend-Tester + Frontend-Tester)
**Priority:** High
**Estimated Complexity:** 2-3 Days
**Status:** Superseded by Handover 0101 (Completed)

Superseded by: `handovers/completed/harmonized/0101_token_efficient_mcp_downloads-C.md`

---

## Task Summary

Replace the current token-heavy file writing approach for slash command and agent template installation with a **97% more token-efficient download system**. Instead of Claude Code writing 15,000+ tokens of file content directly, we'll provide download endpoints that return ZIP files, reducing token cost to ~500 tokens per operation.

**Current Problem:**
- `/gil_import_productagents` writes ~15,000 tokens (3 agent template .md files)
- `/gil_import_personalagents` writes ~15,000 tokens (same files)
- `setup_slash_commands` writes ~3,000 tokens (3 slash command .md files)
- Total: ~33,000 tokens for basic setup operations

**Solution:**
- Provide download endpoints that return ZIP files
- MCP tools download and extract (HTTP request = ~500 tokens)
- Manual fallback: Users download ZIP + run install script
- Dynamic content: ZIPs reflect current agent template state

---

## Context and Background

### User Requirements
1. **MCP-First Approach**: Primary method is automated download via MCP tools
2. **Manual Fallback**: Direct ZIP download + cross-platform install scripts
3. **Security**: Use existing `$GILJO_API_KEY` environment variable (no new secrets)
4. **Paths**: Current working directory for product agents, `~/.claude/agents/` for personal
5. **Backups**: ZIP + database archive before agent template updates
6. **Scope**:
   - Slash commands: All three CLI tools (Claude Code, Codex, Gemini)
   - Agent templates: Claude Code only (Codex/Gemini don't support `.claude/agents/`)

### Security Model (From Research)
- **API Key Storage**: Claude Code stores API keys in `~/.claude.json` as plain text or environment variables
- **Recommended Pattern**: `"X-API-Key": "${GILJO_API_KEY}"` (environment variable reference)
- **Current State**: API key already set in environment during MCP server setup
- **Install Scripts**: Should use `$GILJO_API_KEY` environment variable (not parse config files)
- **File Permissions**: Claude Code configs have 600 permissions (owner-only)

### Existing Infrastructure (Leverage Points)
- `api/endpoints/claude_export.py` - ZIP generation logic (Handover 0075)
- `src/giljo_mcp/template_manager.py` - Template export with backup system
- `api/endpoints/mcp_installer.py` - Download endpoint pattern (Response + headers)
- `src/giljo_mcp/slash_commands/import_agents.py` - Agent import handlers
- `src/giljo_mcp/tools/slash_command_templates.py` - Slash command content

---

## Technical Details

### Backend Changes

#### 1. New Download Endpoints (`api/endpoints/downloads.py`)

**New File:** `F:\GiljoAI_MCP\api\endpoints\downloads.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pathlib import Path
import zipfile
import io
from datetime import datetime

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.template_manager import TemplateManager

router = APIRouter(prefix="/api/download", tags=["downloads"])

@router.get("/slash-commands.zip")
async def download_slash_commands(
    current_user: User = Depends(get_current_active_user)
):
    """Download slash command templates as ZIP file"""
    # Implementation here

@router.get("/agent-templates.zip")
async def download_agent_templates(
    current_user: User = Depends(get_current_active_user),
    active_only: bool = True
):
    """Download agent templates as ZIP file (dynamic content)"""
    # Implementation here

@router.get("/install-script.{extension}")
async def download_install_script(
    extension: str,  # sh, ps1, bat
    script_type: str,  # slash-commands, agent-templates
    current_user: User = Depends(get_current_active_user)
):
    """Download cross-platform install script"""
    # Implementation here
```

**Authentication:** API key via header (`X-API-Key`) - existing pattern from `mcp_installer.py`

#### 2. ZIP Generation Logic

**Pattern (from `claude_export.py`):**
```python
def create_zip_archive(files: dict[str, str]) -> bytes:
    """
    Create ZIP archive from file dictionary

    Args:
        files: {filename: content} mapping

    Returns:
        ZIP file bytes
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename, content in files.items():
            zipf.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.read()
```

#### 3. Modified MCP Tools

**Files to Update:**
- `src/giljo_mcp/tools/tool_accessor.py` (lines 2305-2371)
  - `gil_import_productagents()` - Change to download approach
  - `gil_import_personalagents()` - Change to download approach
  - `setup_slash_commands()` - Return download instructions (already returns content, keep as-is)

**New Behavior:**
```python
@mcp.tool()
async def gil_import_productagents(project_id: str = None):
    """
    Download and install agent templates to current project.

    New approach: Downloads ZIP via HTTP and extracts locally.
    97% context prioritization vs writing files directly.
    """
    # 1. Verify API key in environment
    api_key = os.environ.get('GILJO_API_KEY')
    if not api_key:
        return {
            'success': False,
            'error': 'GILJO_API_KEY environment variable not set',
            'instructions': [
                'Configure GiljoAI MCP first from Settings → Integrations',
                'This sets up the required environment variable'
            ]
        }

    # 2. Get server URL from MCP context or config
    server_url = get_server_url_from_mcp_config()

    # 3. Download ZIP file
    download_url = f"{server_url}/api/download/agent-templates.zip"

    try:
        # 4. Download via HTTP (Claude Code makes request)
        response = await http_client.get(
            download_url,
            headers={"X-API-Key": api_key}
        )

        # 5. Extract to current directory
        target_dir = Path.cwd() / ".claude" / "agents"
        target_dir.mkdir(parents=True, exist_ok=True)

        # 6. Extract ZIP
        with zipfile.ZipFile(io.BytesIO(response.content)) as zipf:
            zipf.extractall(target_dir)

        return {
            'success': True,
            'message': f'Installed {len(zipf.namelist())} agent templates',
            'location': str(target_dir),
            'files': zipf.namelist()
        }

    except Exception as e:
        # Fallback to manual instructions
        return {
            'success': False,
            'error': str(e),
            'manual_fallback': {
                'download_url': download_url,
                'install_script_url': f"{server_url}/api/download/install-script.sh?type=agent-templates",
                'instructions': [
                    f'1. Download: curl -H "X-API-Key: $GILJO_API_KEY" {download_url} -o templates.zip',
                    f'2. Extract: unzip -o templates.zip -d .claude/agents/',
                    f'3. Or run install script: curl {install_script_url} | bash'
                ]
            }
        }
```

#### 4. Backup System for Updates

**Integration with existing `TemplateManager` backup:**
```python
# In downloads.py - before generating agent template ZIP
async def create_backup_if_update(current_user: User):
    """Create ZIP backup before template update"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path('data') / 'backups' / current_user.tenant_key
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_dir / f"agents_backup_{timestamp}.zip"

    # Use existing export logic
    template_manager = TemplateManager(tenant_key=current_user.tenant_key)
    await template_manager.create_zip_backup(backup_path)

    return backup_path
```

### Frontend Changes

#### 1. Update Integrations Tab (`frontend/src/views/UserSettings.vue`)

**Location:** Lines 470-551 (current Slash Command Setup and Claude Code Export sections)

**New UI Structure:**
```vue
<!-- Slash Command Setup Section -->
<v-card variant="outlined" class="mb-4">
  <v-card-title>Slash Command Installation</v-card-title>

  <!-- MCP Method (Recommended) -->
  <v-card variant="tonal" class="mb-2">
    <v-card-text>
      <div class="text-subtitle-2 mb-2">For MCP Clients (Automated)</div>
      <div class="text-caption mb-3">
        Works with Claude Code, Codex CLI, and Gemini CLI
      </div>

      <v-text-field
        :value="slashCommandInstallPrompt"
        readonly
        append-icon="mdi-content-copy"
        @click:append="copyToClipboard(slashCommandInstallPrompt)"
      />

      <v-chip size="small" color="success">
        <v-icon start size="small">mdi-check</v-icon>
        Zero token cost
      </v-chip>
    </v-card-text>
  </v-card>

  <!-- Manual Method (Fallback) -->
  <v-expansion-panels>
    <v-expansion-panel>
      <v-expansion-panel-title>Manual Installation</v-expansion-panel-title>
      <v-expansion-panel-text>
        <div class="d-flex gap-2 mb-3">
          <v-btn
            variant="outlined"
            @click="downloadSlashCommands"
            prepend-icon="mdi-download"
          >
            Download slash-commands.zip
          </v-btn>

          <v-btn
            variant="outlined"
            @click="downloadInstallScript('slash-commands', 'sh')"
            prepend-icon="mdi-script-text"
          >
            Download install.sh
          </v-btn>

          <v-btn
            variant="outlined"
            @click="downloadInstallScript('slash-commands', 'ps1')"
            prepend-icon="mdi-powershell"
          >
            Download install.ps1
          </v-btn>
        </div>

        <v-alert type="info" variant="tonal">
          <div class="text-subtitle-2 mb-1">Installation Steps</div>
          <ol class="text-caption">
            <li>Download the ZIP file and install script for your OS</li>
            <li>Run the script: <code>bash install.sh</code> or <code>powershell install.ps1</code></li>
            <li>Restart your CLI tool to load the commands</li>
          </ol>
        </v-alert>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</v-card>

<!-- Agent Template Installation Section -->
<v-card variant="outlined" class="mb-4">
  <v-card-title>Agent Template Installation</v-card-title>

  <v-alert type="info" variant="tonal" class="mb-3">
    <v-icon start>mdi-information</v-icon>
    Claude Code only - Codex and Gemini CLI do not support agent templates yet
  </v-alert>

  <!-- Choice: Product vs Personal -->
  <v-btn-toggle v-model="agentImportType" mandatory class="mb-3">
    <v-btn value="product">
      <v-icon start>mdi-folder-outline</v-icon>
      Product Agents
      <v-tooltip activator="parent" location="bottom">
        Install to current project: .claude/agents/
      </v-tooltip>
    </v-btn>
    <v-btn value="personal">
      <v-icon start>mdi-account-outline</v-icon>
      Personal Agents
      <v-tooltip activator="parent" location="bottom">
        Install to home directory: ~/.claude/agents/
      </v-tooltip>
    </v-btn>
  </v-btn-toggle>

  <!-- MCP Method -->
  <v-card variant="tonal" class="mb-2">
    <v-card-text>
      <div class="text-subtitle-2 mb-2">MCP Installation (Recommended)</div>

      <v-text-field
        :value="agentInstallPrompt"
        readonly
        append-icon="mdi-content-copy"
        @click:append="copyToClipboard(agentInstallPrompt)"
      />

      <div class="d-flex gap-2">
        <v-chip size="small" color="success">
          <v-icon start size="small">mdi-speedometer</v-icon>
          ~500 tokens (97% savings)
        </v-chip>
        <v-chip size="small" color="info">
          <v-icon start size="small">mdi-backup-restore</v-icon>
          Auto-backup enabled
        </v-chip>
      </div>
    </v-card-text>
  </v-card>

  <!-- Manual Method -->
  <v-expansion-panels>
    <v-expansion-panel>
      <v-expansion-panel-title>Manual Installation</v-expansion-panel-title>
      <v-expansion-panel-text>
        <div class="d-flex gap-2 mb-3">
          <v-btn
            variant="outlined"
            @click="downloadAgentTemplates"
            prepend-icon="mdi-download"
          >
            Download agent-templates.zip
          </v-btn>

          <v-btn
            variant="outlined"
            @click="downloadInstallScript('agent-templates', 'sh')"
            prepend-icon="mdi-script-text"
          >
            Download install.sh
          </v-btn>

          <v-btn
            variant="outlined"
            @click="downloadInstallScript('agent-templates', 'ps1')"
            prepend-icon="mdi-powershell"
          >
            Download install.ps1
          </v-btn>
        </div>

        <v-alert type="warning" variant="tonal" class="mb-2">
          <v-icon start>mdi-backup-restore</v-icon>
          Backup will be created automatically before installation
        </v-alert>

        <v-alert type="info" variant="tonal">
          <div class="text-subtitle-2 mb-1">Installation Paths</div>
          <ul class="text-caption">
            <li><strong>Product:</strong> Current working directory <code>.claude/agents/</code></li>
            <li><strong>Personal:</strong> Home directory <code>~/.claude/agents/</code></li>
          </ul>
        </v-alert>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</v-card>
```

#### 2. New Vue Methods

```javascript
export default {
  data() {
    return {
      agentImportType: 'product', // or 'personal'
      serverUrl: '', // Loaded from config
    }
  },

  computed: {
    slashCommandInstallPrompt() {
      return 'Download and install slash commands from GiljoAI MCP server'
    },

    agentInstallPrompt() {
      const type = this.agentImportType
      return type === 'product'
        ? 'Download and install agent templates to current project'
        : 'Download and install agent templates to personal folder'
    }
  },

  methods: {
    async downloadSlashCommands() {
      try {
        const response = await fetch(`${this.serverUrl}/api/download/slash-commands.zip`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        })

        const blob = await response.blob()
        this.triggerDownload(blob, 'slash-commands.zip')

        this.$emit('show-snackbar', {
          message: 'Downloaded slash-commands.zip',
          color: 'success'
        })
      } catch (error) {
        this.$emit('show-snackbar', {
          message: 'Download failed: ' + error.message,
          color: 'error'
        })
      }
    },

    async downloadAgentTemplates() {
      const endpoint = `${this.serverUrl}/api/download/agent-templates.zip?active_only=true`
      // Similar to downloadSlashCommands()
    },

    async downloadInstallScript(scriptType, extension) {
      const endpoint = `${this.serverUrl}/api/download/install-script.${extension}?type=${scriptType}`
      // Similar to downloadSlashCommands()
    },

    triggerDownload(blob, filename) {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    },

    async copyToClipboard(text) {
      // Existing implementation from SlashCommandSetup.vue
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(text)
        } else {
          // Fallback
          const ta = document.createElement('textarea')
          ta.value = text
          ta.style.position = 'absolute'
          ta.style.left = '-9999px'
          document.body.appendChild(ta)
          ta.select()
          document.execCommand('copy')
          document.body.removeChild(ta)
        }

        this.$emit('show-snackbar', {
          message: 'Copied to clipboard',
          color: 'success'
        })
      } catch (error) {
        this.$emit('show-snackbar', {
          message: 'Copy failed',
          color: 'error'
        })
      }
    }
  }
}
```

### Install Script Templates

#### 1. Slash Commands Install Script (Unix/macOS)

**File:** `installer/templates/install_slash_commands.sh`

```bash
#!/bin/bash
# GiljoAI Slash Command Installer
# Cross-platform installation script for slash commands

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "GiljoAI Slash Command Installer"
echo "================================"
echo ""

# Check for API key
if [ -z "$GILJO_API_KEY" ]; then
  echo -e "${RED}Error: GILJO_API_KEY environment variable not set${NC}"
  echo ""
  echo "Please configure GiljoAI MCP first:"
  echo "  Settings → Integrations → MCP Configuration"
  echo ""
  echo "This will set up the required environment variable."
  exit 1
fi

# Server URL (templated by backend)
SERVER_URL="{{SERVER_URL}}"

# Download URL
DOWNLOAD_URL="${SERVER_URL}/api/download/slash-commands.zip"

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${YELLOW}Downloading slash commands...${NC}"
curl -H "X-API-Key: $GILJO_API_KEY" \
  "$DOWNLOAD_URL" \
  -o "$TEMP_DIR/commands.zip" \
  --fail --silent --show-error

# Target directory
TARGET_DIR="$HOME/.claude/commands"
mkdir -p "$TARGET_DIR"

echo -e "${YELLOW}Installing to $TARGET_DIR...${NC}"
unzip -o "$TEMP_DIR/commands.zip" -d "$TARGET_DIR" > /dev/null

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "Installed commands:"
ls -1 "$TARGET_DIR"/gil_*.md | sed 's/.*\//  - /'
echo ""
echo "Restart your CLI tool to load the commands."
```

#### 2. Agent Templates Install Script (Unix/macOS)

**File:** `installer/templates/install_agent_templates.sh`

```bash
#!/bin/bash
# GiljoAI Agent Template Installer

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "GiljoAI Agent Template Installer"
echo "================================="
echo ""

# Check for API key
if [ -z "$GILJO_API_KEY" ]; then
  echo -e "${RED}Error: GILJO_API_KEY environment variable not set${NC}"
  echo "Configure GiljoAI MCP first: Settings → Integrations"
  exit 1
fi

# Installation type (product or personal)
INSTALL_TYPE="${1:-product}"

# Determine target directory
if [ "$INSTALL_TYPE" = "personal" ]; then
  TARGET_DIR="$HOME/.claude/agents"
else
  TARGET_DIR="$(pwd)/.claude/agents"
fi

# Server URL (templated)
SERVER_URL="{{SERVER_URL}}"
DOWNLOAD_URL="${SERVER_URL}/api/download/agent-templates.zip?active_only=true"

# Create backup if directory exists
if [ -d "$TARGET_DIR" ] && [ "$(ls -A $TARGET_DIR)" ]; then
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_DIR="${TARGET_DIR}_backup_${TIMESTAMP}"

  echo -e "${YELLOW}Creating backup: $BACKUP_DIR${NC}"
  cp -r "$TARGET_DIR" "$BACKUP_DIR"
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${YELLOW}Downloading agent templates...${NC}"
curl -H "X-API-Key: $GILJO_API_KEY" \
  "$DOWNLOAD_URL" \
  -o "$TEMP_DIR/templates.zip" \
  --fail --silent --show-error

# Create target directory
mkdir -p "$TARGET_DIR"

echo -e "${YELLOW}Installing to $TARGET_DIR...${NC}"
unzip -o "$TEMP_DIR/templates.zip" -d "$TARGET_DIR" > /dev/null

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "Installed templates:"
ls -1 "$TARGET_DIR"/*.md | sed 's/.*\//  - /'
echo ""
echo "Target: $TARGET_DIR"
```

#### 3. Windows PowerShell Scripts

**Similar structure with PowerShell syntax:**
- `install_slash_commands.ps1`
- `install_agent_templates.ps1`

---

## Implementation Plan

### Phase 1: Backend Download Endpoints (Day 1)
**Recommended Agent:** `tdd-implementor`

1. Create `api/endpoints/downloads.py`
   - Implement `/api/download/slash-commands.zip`
   - Implement `/api/download/agent-templates.zip`
   - Implement `/api/download/install-script.{extension}`

2. Add ZIP generation utility
   - Function: `create_zip_archive(files: dict) -> bytes`
   - Integration with existing `TemplateManager`

3. Add backup system
   - Function: `create_backup_before_update(user)`
   - Integration with existing backup logic

4. Register router in `api/app.py`

**Testing:**
- Unit tests for ZIP generation
- Integration tests for download endpoints
- Multi-tenant isolation tests
- Backup system tests

### Phase 2: Update MCP Tools (Day 1-2)
**Recommended Agent:** `tdd-implementor`

1. Modify `src/giljo_mcp/tools/tool_accessor.py`
   - Update `gil_import_productagents()` - download approach
   - Update `gil_import_personalagents()` - download approach
   - Keep `setup_slash_commands()` as-is (already returns content)

2. Add HTTP client utility
   - Function: `download_file(url, api_key) -> bytes`
   - Error handling and retries

3. Add extraction utility
   - Function: `extract_zip_to_directory(zip_bytes, target_dir)`

**Testing:**
- Unit tests for download logic
- Integration tests for MCP tool execution
- Error handling tests (network failures)
- Fallback instruction tests

### Phase 3: Install Script Templates (Day 2)
**Recommended Agent:** `installation-flow-agent`

1. Create script templates
   - `installer/templates/install_slash_commands.sh`
   - `installer/templates/install_slash_commands.ps1`
   - `installer/templates/install_agent_templates.sh`
   - `installer/templates/install_agent_templates.ps1`

2. Add template rendering
   - Function: `render_install_script(template, server_url) -> str`
   - Variable substitution ({{SERVER_URL}})

3. Cross-platform testing
   - Test on Windows PowerShell
   - Test on macOS/Linux bash
   - Test on Git Bash (Windows)

**Testing:**
- Manual testing on all platforms
- Script syntax validation
- Error handling (missing API key)

### Phase 4: Frontend UI Updates (Day 2-3)
**Recommended Agent:** `ux-designer` + `frontend-tester`

1. Update `frontend/src/views/UserSettings.vue`
   - Replace lines 470-551 with new UI structure
   - Add download methods
   - Add copy-to-clipboard utility

2. Add API integration
   - `api.downloads.slashCommands()`
   - `api.downloads.agentTemplates(active_only)`
   - `api.downloads.installScript(type, extension)`

3. Update `frontend/src/services/api.js`
   - Add downloads module

**Testing:**
- Manual UI testing (all download buttons)
- Copy-to-clipboard on all browsers
- Error handling (failed downloads)
- Snackbar notifications

### Phase 5: Integration Testing (Day 3)
**Recommended Agent:** `backend-tester` + `frontend-tester`

1. End-to-end testing
   - Download slash commands via UI
   - Download agent templates via UI
   - Install via scripts on Windows
   - Install via scripts on macOS/Linux

2. MCP tool testing
   - Test `/gil_import_productagents` in Claude Code
   - Test `/gil_import_personalagents` in Claude Code
   - Test manual fallback instructions

3. Security testing
   - Test API key authentication
   - Test multi-tenant isolation
   - Test backup creation

**Testing:**
- 80%+ test coverage
- All tests passing
- Cross-platform verification

---

## Testing Requirements

### Unit Tests

**File:** `tests/test_downloads.py`
```python
def test_create_zip_archive():
    """Test ZIP archive creation from file dict"""

def test_download_slash_commands_endpoint(client, auth_headers):
    """Test slash commands download endpoint"""

def test_download_agent_templates_endpoint(client, auth_headers):
    """Test agent templates download endpoint"""

def test_download_install_script_endpoint(client, auth_headers):
    """Test install script download endpoint"""

def test_backup_creation_before_update():
    """Test backup system creates ZIP before template update"""
```

**File:** `tests/test_mcp_tools_download.py`
```python
def test_gil_import_productagents_download():
    """Test product agent import via download"""

def test_gil_import_personalagents_download():
    """Test personal agent import via download"""

def test_download_fallback_instructions():
    """Test fallback to manual instructions on HTTP error"""
```

### Integration Tests

**File:** `tests/integration/test_download_workflow.py`
```python
def test_full_slash_command_download_workflow():
    """Test complete slash command download and extraction"""

def test_full_agent_template_download_workflow():
    """Test complete agent template download with backup"""

def test_multi_tenant_isolation_downloads():
    """Test tenant isolation in download endpoints"""
```

### Manual Testing Checklist

- [ ] Download slash-commands.zip from UI (Windows)
- [ ] Download slash-commands.zip from UI (macOS)
- [ ] Download agent-templates.zip from UI (Windows)
- [ ] Download agent-templates.zip from UI (macOS)
- [ ] Run install.sh for slash commands (macOS)
- [ ] Run install.ps1 for slash commands (Windows)
- [ ] Run install.sh for agent templates (macOS)
- [ ] Run install.ps1 for agent templates (Windows)
- [ ] Test `/gil_import_productagents` in Claude Code
- [ ] Test `/gil_import_personalagents` in Claude Code
- [ ] Verify backup creation before agent update
- [ ] Test manual fallback instructions when HTTP fails

---

## Dependencies and Blockers

### Dependencies
- ✅ Existing `TemplateManager` with backup system (Handover 0041)
- ✅ Existing `claude_export.py` with ZIP generation (Handover 0075)
- ✅ Existing `mcp_installer.py` download pattern
- ✅ Existing slash command templates (Handover 0093)

### Known Blockers
- None identified

### Questions for User
- None at this time

---

## Success Criteria

### Definition of Done

1. **Backend:**
   - [ ] 3 download endpoints implemented and tested
   - [ ] ZIP generation working for slash commands and agent templates
   - [ ] Backup system creates ZIP before template updates
   - [ ] Multi-tenant isolation verified
   - [ ] API key authentication working

2. **MCP Tools:**
   - [ ] `gil_import_productagents` downloads and extracts
   - [ ] `gil_import_personalagents` downloads and extracts
   - [ ] Fallback instructions provided on HTTP errors
   - [ ] Token usage reduced to ~500 tokens per operation

3. **Install Scripts:**
   - [ ] 4 cross-platform scripts created (sh, ps1 for each type)
   - [ ] Scripts work on Windows, macOS, and Linux
   - [ ] Scripts use `$GILJO_API_KEY` environment variable
   - [ ] Backup created before installation

4. **Frontend:**
   - [ ] UI updated with download buttons
   - [ ] MCP command copy-to-clipboard working
   - [ ] Manual download working for ZIP files
   - [ ] Manual download working for install scripts
   - [ ] Error handling and user feedback

5. **Testing:**
   - [ ] 80%+ unit test coverage
   - [ ] All integration tests passing
   - [ ] Manual testing completed on Windows and macOS
   - [ ] Security testing passed (API key auth, multi-tenant)

6. **Documentation:**
   - [ ] User guide updated with new download approach
   - [ ] API documentation updated
   - [ ] Handover summary written (max 1000 words)

### Performance Metrics
- **Token Reduction:** 97% (from 15,000 to ~500 tokens)
- **Download Time:** < 2 seconds for ZIP files
- **Extraction Time:** < 1 second for typical template count

---

## Rollback Plan

### If Things Go Wrong

1. **Revert MCP Tools:**
   ```bash
   git checkout HEAD -- src/giljo_mcp/tools/tool_accessor.py
   ```

2. **Remove Download Endpoints:**
   ```bash
   rm api/endpoints/downloads.py
   # Remove router registration from api/app.py
   ```

3. **Restore Old UI:**
   ```bash
   git checkout HEAD -- frontend/src/views/UserSettings.vue
   ```

4. **Old behavior still works:**
   - Existing `setup_slash_commands` MCP tool unchanged
   - Template manager export still functional
   - No database changes, safe rollback

---

## Additional Resources

### Related Handovers
- [Handover 0041: Agent Template Management](0041_agent_template_management.md) - Template system
- [Handover 0075: Agent Template Backup System](../docs/handovers/0041/) - ZIP backup logic
- [Handover 0084b: Agent Import Commands](../docs/devlog/) - Slash command handlers
- [Handover 0092: Bearer Token Support](0092_bearer_token_mcp_http.md) - API key authentication
- [Handover 0093: Slash Command Setup](../docs/devlog/) - Setup command tool

### Documentation References
- [MCP Tool Development Guide](../docs/guides/mcp_tool_development_guide.md)
- [API Endpoint Patterns](../docs/guides/api_endpoint_patterns.md)
- [Cross-Platform Development](../CLAUDE.md#cross-platform-coding-standards)
- [Security Best Practices](../docs/guides/security_best_practices.md)

### External Resources
- [Claude Code MCP Configuration](https://docs.claude.com/en/docs/claude-code/mcp)
- [FastAPI File Downloads](https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse)
- [Python zipfile Module](https://docs.python.org/3/library/zipfile.html)

---

## File Inventory

### New Files
- `api/endpoints/downloads.py` (350 lines) - Download endpoints
- `installer/templates/install_slash_commands.sh` (60 lines)
- `installer/templates/install_slash_commands.ps1` (70 lines)
- `installer/templates/install_agent_templates.sh` (80 lines)
- `installer/templates/install_agent_templates.ps1` (90 lines)
- `tests/test_downloads.py` (200 lines) - Unit tests
- `tests/test_mcp_tools_download.py` (150 lines) - MCP tool tests
- `tests/integration/test_download_workflow.py` (250 lines) - Integration tests

### Modified Files
- `src/giljo_mcp/tools/tool_accessor.py` (lines 2305-2371) - MCP tools
- `frontend/src/views/UserSettings.vue` (lines 470-551) - UI update
- `frontend/src/services/api.js` - Add downloads module
- `api/app.py` - Register downloads router

### Total Code Changes
- **New Code:** ~1,250 lines
- **Modified Code:** ~200 lines
- **Tests:** ~600 lines
- **Total:** ~2,050 lines

---

## Implementation Notes

### Security Considerations
1. **API Key Storage:** Use existing `$GILJO_API_KEY` environment variable
2. **File Permissions:** Set 600 on downloaded configs (Unix/macOS)
3. **Multi-Tenant:** All queries filter by `tenant_key`
4. **Audit Logging:** Log all download requests with IP/timestamp

### Cross-Platform Considerations
1. **Paths:** Use `pathlib.Path()` for all file operations
2. **Scripts:** Test on Windows PowerShell, Git Bash, macOS zsh, Linux bash
3. **Line Endings:** Ensure CRLF (Windows) vs LF (Unix) compatibility
4. **Temp Directories:** Use `mktemp -d` (Unix) vs `New-TemporaryFile` (PowerShell)

### Performance Considerations
1. **ZIP Compression:** Use `ZIP_DEFLATED` for smaller files
2. **Streaming:** Consider streaming for large template sets
3. **Caching:** Consider caching ZIP files for 5 minutes (if content unchanged)
4. **Concurrent Downloads:** Test multiple simultaneous downloads

---

**Ready for Implementation:** All planning complete, no blockers identified.

**Recommended Approach:** Use TDD workflow - write tests first, then implement.

**Expected Timeline:** 2-3 days with comprehensive testing.
