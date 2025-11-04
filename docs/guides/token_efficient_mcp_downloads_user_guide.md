# Token-Efficient MCP Downloads - User Guide

**Version:** 1.0
**Last Updated:** 2025-01-03
**Handover:** 0101

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Method 1: MCP Tools (Automated)](#method-1-mcp-tools-automated)
4. [Method 2: UI Downloads (Manual)](#method-2-ui-downloads-manual)
5. [Method 3: Command-Line Scripts](#method-3-command-line-scripts)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Overview

### What is Token-Efficient MCP Downloads?

GiljoAI MCP now provides **HTTP download endpoints** for slash commands and agent templates, reducing AI API costs by **97%**. Instead of writing 15,000+ tokens of file content, the system downloads ZIP files via HTTP, consuming only ~500 tokens.

### Why Use Downloads?

**Old Approach (Token-Heavy):**
- Writing agent templates: **15,000 tokens**
- Writing slash commands: **3,000 tokens**
- Total setup: **33,000 tokens**
- Cost: High (depending on AI model pricing)

**New Approach (Download):**
- Downloading ZIP files: **~500 tokens total**
- Token reduction: **97%**
- Cost: Minimal (HTTP request overhead only)

### What Can You Download?

1. **Slash Commands** - CLI shortcuts for GiljoAI operations
   - `gil_import_productagents.md` - Import templates to project
   - `gil_import_personalagents.md` - Import templates to home directory
   - `gil_handover.md` - Orchestrator succession trigger

2. **Agent Templates** - AI agent behavior definitions
   - Orchestrator, Implementor, Tester, Reviewer, Documenter, QA
   - Dynamic content from your GiljoAI database
   - Includes behavioral rules and success criteria

---

## Quick Start

### Prerequisites

1. **GiljoAI MCP Server** running (v3.0+)
2. **API Key** set in environment: `$GILJO_API_KEY`
3. **AI Tool** installed: Claude Code, Codex CLI, or Gemini CLI

### 30-Second Setup

**For Slash Commands (All AI Tools):**
```bash
# Set API key (if not already set)
export GILJO_API_KEY="your_api_key_here"

# Option A: Use MCP tool (automated)
# In Claude Code: Type /gil_import_personalagents

# Option B: Manual download
curl -H "X-API-Key: $GILJO_API_KEY" \
     http://localhost:7272/api/download/slash-commands.zip \
     -o commands.zip
unzip commands.zip -d ~/.claude/commands/
```

**For Agent Templates (Claude Code Only):**
```bash
# Option A: Use MCP tool (automated)
# In Claude Code: Type /gil_import_productagents

# Option B: Manual download
curl -H "X-API-Key: $GILJO_API_KEY" \
     http://localhost:7272/api/download/agent-templates.zip \
     -o templates.zip
unzip templates.zip -d .claude/agents/
```

---

## Method 1: MCP Tools (Automated)

### Recommended for Most Users

MCP tools provide **fully automated** installation with progress tracking and error handling.

### Prerequisites

- GiljoAI MCP server configured in your AI tool
- API key set in environment variable: `$GILJO_API_KEY`
- MCP connection active

### Step 1: Import Agent Templates to Project

**Use Case:** Install templates for the current project only

**Command:**
```
/gil_import_productagents
```

**What Happens:**
1. MCP tool connects to GiljoAI server
2. Downloads `agent-templates.zip` via HTTP
3. Extracts to `.claude/agents/` in current directory
4. Creates backup of existing templates
5. Reports success with file count

**Example Output:**
```
✅ Successfully imported 6 agent templates to project:
   - orchestrator.md
   - implementor.md
   - tester.md
   - reviewer.md
   - documenter.md
   - qa.md

📁 Location: .claude/agents/
💾 Backup: .claude/agents.backup-20250103-143022/
```

### Step 2: Import Agent Templates to Home Directory

**Use Case:** Install templates globally (available to all projects)

**Command:**
```
/gil_import_personalagents
```

**What Happens:**
1. Downloads `agent-templates.zip` via HTTP
2. Extracts to `~/.claude/agents/` (home directory)
3. Creates backup of existing templates
4. Templates available to all Claude Code sessions

**Example Output:**
```
✅ Successfully imported 6 agent templates to personal folder:
   - orchestrator.md
   - implementor.md
   - tester.md
   - reviewer.md
   - documenter.md
   - qa.md

📁 Location: ~/.claude/agents/
💾 Backup: ~/.claude/agents.backup-20250103-143055/
```

### Token Savings with MCP Tools

**Traditional Approach:**
- Claude Code writes 6 agent template files
- ~2,500 tokens per file
- Total: **15,000 tokens**

**Download Approach:**
- HTTP download request
- ZIP extraction
- Total: **~500 tokens**

**Savings:** 97% reduction (14,500 tokens saved)

---

## Method 2: UI Downloads (Manual)

### When to Use Manual Downloads

- Troubleshooting MCP connection issues
- Installing on a different machine
- Prefer visual interface over CLI
- Need to inspect files before installation

### Step 1: Access Integrations Tab

1. Open GiljoAI dashboard: `http://localhost:7274`
2. Navigate to **Avatar Menu** → **My Settings**
3. Select **API and Integrations** tab
4. Scroll to **MCP Tools** section

### Step 2: Download Slash Commands

**Section:** Slash Commands for Claude Code / Codex / Gemini

1. Click **"Download ZIP"** button
   - File downloads: `slash-commands.zip` (~5-10 KB)
2. **Or** click **"Download Install Script"** dropdown
   - Select your platform: **Unix/macOS (.sh)** or **Windows (.ps1)**
   - Script downloads: `install-slash-commands.sh` or `.ps1`

### Step 3: Download Agent Templates

**Section:** Agent Templates for Claude Code

1. Click **"Download ZIP"** button
   - File downloads: `agent-templates.zip` (size varies)
2. **Or** click **"Download Install Script"** dropdown
   - Select your platform: **Unix/macOS (.sh)** or **Windows (.ps1)**
   - Script downloads: `install-agent-templates.sh` or `.ps1`

### Step 4: Extract Files

**Option A: Manual Extraction (ZIP)**

**macOS / Linux:**
```bash
# Slash commands
unzip slash-commands.zip -d ~/.claude/commands/

# Agent templates (project)
unzip agent-templates.zip -d .claude/agents/

# Agent templates (personal)
unzip agent-templates.zip -d ~/.claude/agents/
```

**Windows (PowerShell):**
```powershell
# Slash commands
Expand-Archive -Path slash-commands.zip -DestinationPath "$HOME\.claude\commands\"

# Agent templates (project)
Expand-Archive -Path agent-templates.zip -DestinationPath ".claude\agents\"

# Agent templates (personal)
Expand-Archive -Path agent-templates.zip -DestinationPath "$HOME\.claude\agents\"
```

**Option B: Run Install Script**

**macOS / Linux:**
```bash
chmod +x install-slash-commands.sh
./install-slash-commands.sh

# Or for agent templates
chmod +x install-agent-templates.sh
./install-agent-templates.sh
```

**Windows (PowerShell):**
```powershell
# Allow script execution (first time only)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

.\install-slash-commands.ps1

# Or for agent templates
.\install-agent-templates.ps1
```

---

## Method 3: Command-Line Scripts

### Advanced Users: Direct HTTP Downloads

**Prerequisites:**
- `curl` or `wget` installed (Unix/macOS)
- `Invoke-WebRequest` available (Windows PowerShell)
- `GILJO_API_KEY` environment variable set

### Download Slash Commands

**macOS / Linux:**
```bash
# Download ZIP
curl -H "X-API-Key: $GILJO_API_KEY" \
     http://localhost:7272/api/download/slash-commands.zip \
     -o slash-commands.zip

# Extract
unzip slash-commands.zip -d ~/.claude/commands/
```

**Windows (PowerShell):**
```powershell
# Download ZIP
Invoke-WebRequest -Uri "http://localhost:7272/api/download/slash-commands.zip" `
                  -Headers @{"X-API-Key"=$env:GILJO_API_KEY} `
                  -OutFile "slash-commands.zip"

# Extract
Expand-Archive -Path slash-commands.zip -DestinationPath "$HOME\.claude\commands\"
```

### Download Agent Templates

**macOS / Linux:**
```bash
# Download ZIP (active templates only)
curl -H "X-API-Key: $GILJO_API_KEY" \
     "http://localhost:7272/api/download/agent-templates.zip?active_only=true" \
     -o agent-templates.zip

# Extract to project
unzip agent-templates.zip -d .claude/agents/

# Or extract to home
unzip agent-templates.zip -d ~/.claude/agents/
```

**Windows (PowerShell):**
```powershell
# Download ZIP
Invoke-WebRequest -Uri "http://localhost:7272/api/download/agent-templates.zip?active_only=true" `
                  -Headers @{"X-API-Key"=$env:GILJO_API_KEY} `
                  -OutFile "agent-templates.zip"

# Extract to project
Expand-Archive -Path agent-templates.zip -DestinationPath ".claude\agents\"

# Or extract to home
Expand-Archive -Path agent-templates.zip -DestinationPath "$HOME\.claude\agents\"
```

### Download Install Scripts

**macOS / Linux:**
```bash
# Download slash commands install script
curl -H "X-API-Key: $GILJO_API_KEY" \
     "http://localhost:7272/api/download/install-script.sh?script_type=slash-commands" \
     -o install-slash-commands.sh

chmod +x install-slash-commands.sh
./install-slash-commands.sh
```

**Windows (PowerShell):**
```powershell
# Download slash commands install script
Invoke-WebRequest -Uri "http://localhost:7272/api/download/install-script.ps1?script_type=slash-commands" `
                  -Headers @{"X-API-Key"=$env:GILJO_API_KEY} `
                  -OutFile "install-slash-commands.ps1"

.\install-slash-commands.ps1
```

---

## Troubleshooting

### Error: "Authentication required"

**Cause:** API key not set or invalid

**Solution:**
1. Check API key in environment:
   ```bash
   echo $GILJO_API_KEY  # Unix/macOS
   echo $env:GILJO_API_KEY  # Windows
   ```

2. Generate new API key:
   - Dashboard → Avatar Menu → My Settings → API and Integrations
   - Section: **Personal API Keys**
   - Click **"Generate New Key"**
   - Copy key to clipboard

3. Set environment variable:
   ```bash
   export GILJO_API_KEY="gk_user_xxx..."  # Unix/macOS
   $env:GILJO_API_KEY="gk_user_xxx..."  # Windows
   ```

### Error: "No templates found"

**Cause:** Database has no agent templates

**Solution:**
1. Go to Dashboard → Templates tab
2. Click **"Reset to Defaults"** button
3. Verify 6 default templates created
4. Retry download

### Error: "Connection refused"

**Cause:** GiljoAI server not running

**Solution:**
```bash
# Start GiljoAI server
python startup.py

# Verify server running
curl http://localhost:7272/health
```

### Error: "ZIP file is corrupted"

**Cause:** Incomplete download or network interruption

**Solution:**
1. Delete corrupted ZIP file
2. Retry download with verbose output:
   ```bash
   curl -v -H "X-API-Key: $GILJO_API_KEY" \
        http://localhost:7272/api/download/slash-commands.zip \
        -o slash-commands.zip
   ```
3. Check file size (should be >0 bytes)

### Error: "Permission denied" (Unix/macOS)

**Cause:** Missing execute permissions on install script

**Solution:**
```bash
chmod +x install-slash-commands.sh
chmod +x install-agent-templates.sh
```

### Error: "Execution policy" (Windows)

**Cause:** PowerShell execution policy blocks scripts

**Solution:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## FAQ

### Q: Which method should I use?

**A:** Use **MCP tools** (Method 1) for best experience:
- Fully automated
- Progress tracking
- Automatic backups
- Error handling

Use **UI downloads** (Method 2) for troubleshooting or manual control.

Use **Command-line scripts** (Method 3) for advanced workflows or CI/CD.

### Q: Where are files installed?

**A:**

**Slash Commands:**
- Location: `~/.claude/commands/`
- Files: `gil_import_productagents.md`, `gil_import_personalagents.md`, `gil_handover.md`

**Agent Templates (Project):**
- Location: `.claude/agents/` (current directory)
- Scope: Current project only

**Agent Templates (Personal):**
- Location: `~/.claude/agents/`
- Scope: All projects (global)

### Q: What's the difference between product and personal agents?

**A:**

**Product Agents** (`/gil_import_productagents`):
- Installed to `.claude/agents/` in current directory
- Scoped to current project only
- Useful for project-specific agent behavior

**Personal Agents** (`/gil_import_personalagents`):
- Installed to `~/.claude/agents/` (home directory)
- Available to all Claude Code sessions
- Useful for standard agents used across all projects

### Q: Are backups created automatically?

**A:** Yes, for agent template updates:
- Backup location: `.claude/agents.backup-YYYYMMDD-HHMMSS/`
- Contains previous templates
- Restore manually if needed

### Q: Can I customize templates before installation?

**A:** Yes:
1. Download ZIP via UI (Method 2)
2. Extract to temporary location
3. Edit markdown files as needed
4. Manually copy to `.claude/agents/` or `~/.claude/commands/`

### Q: How do I verify installation?

**A:**

**Slash Commands:**
```bash
ls -la ~/.claude/commands/
# Should show: gil_import_productagents.md, gil_import_personalagents.md, gil_handover.md
```

**Agent Templates:**
```bash
ls -la .claude/agents/
# Should show: orchestrator.md, implementor.md, tester.md, etc.
```

### Q: What if I need to reinstall?

**A:** Simply run the download again:
- MCP tools create backups automatically
- Manual downloads overwrite existing files
- Previous versions preserved in backup folders

### Q: Do downloads work offline?

**A:** No, downloads require:
- GiljoAI server running
- Network connection to server
- Valid API key

For offline usage, download ZIPs in advance and extract manually.

### Q: Can I automate downloads in CI/CD?

**A:** Yes, use command-line scripts (Method 3):
1. Set `GILJO_API_KEY` in CI environment
2. Use `curl` or `wget` to download ZIPs
3. Extract to desired locations
4. Verify file existence

Example (GitHub Actions):
```yaml
- name: Download GiljoAI templates
  env:
    GILJO_API_KEY: ${{ secrets.GILJO_API_KEY }}
  run: |
    curl -H "X-API-Key: $GILJO_API_KEY" \
         http://localhost:7272/api/download/agent-templates.zip \
         -o agent-templates.zip
    unzip agent-templates.zip -d .claude/agents/
```

---

## Next Steps

1. **Set up API key** (if not already done)
   - Dashboard → My Settings → API and Integrations → Personal API Keys

2. **Choose installation method**
   - MCP tools for automation
   - UI downloads for manual control
   - Command-line for advanced workflows

3. **Install slash commands and agent templates**
   - Follow steps in Quick Start section

4. **Verify installation**
   - Check `.claude/commands/` and `.claude/agents/` directories

5. **Start using templates**
   - Claude Code automatically loads agents from `.claude/agents/`
   - Use slash commands: Type `/` in Claude Code to see available commands

---

**Need Help?**

- **Documentation:** See technical guide for developer details
- **Support:** Contact GiljoAI support team
- **Issues:** Report bugs on GitHub repository

---

**Last Updated:** 2025-01-03
**Version:** 1.0
**Handover:** 0101
