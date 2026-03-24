# Testing Guide - Fresh Install & CLI Downloads

**What You're Testing**: Fresh installation flow + multi-AI coding agent/slash command downloads

**Prerequisites**:
- Laptop for fresh install (Windows/Mac/Linux)
- Another PC with Claude Code, Codex CLI, and Gemini CLI installed
- PostgreSQL 14+ installed on laptop
- Python 3.11+ on laptop

---

## Part 1: Fresh Install Test (Laptop)

**Goal**: Verify install.py creates database, runs migrations, and starts services.

**Steps**:
1. Download project: `git clone https://github.com/patrik-giljoai/GiljoAI-MCP`
2. Run installer: `cd GiljoAI-MCP && python install.py`
3. **Watch for**: "Running database migrations" step (Step 7 of 9)
4. **Expected**: Migration `6adac1467121` applies successfully
5. Access dashboard: `http://localhost:7274`
6. Create first admin user via /welcome flow
7. Create API key in Settings → API Keys

---

## Part 2: CLI Download Test (Other PC)

**Goal**: Verify slash commands and agent templates download from UI.

**Setup**:
1. Access laptop from other PC: `http://<laptop-ip>:7274`
2. Login with admin credentials from Part 1
3. Navigate to Settings → MCP Configuration tab

**Test A: Slash Commands**:
1. Click "Copy Install Command" under Slash Commands
2. **Expected**: PowerShell command with correct server URL
3. Run command in Claude Code/Codex/Gemini terminal
4. **Expected**: `/gil_handover` command available

**Test B: Agent Templates**:
1. Go to Settings → Agent Template Manager
2. Create test agent (role: implementer, CLI: claude)
3. Click "Download Agent Templates" button
4. **Expected**: agent_templates.zip downloads (max 8 .md files)
5. Extract and verify YAML frontmatter format
6. Click "Copy Install Command" for Claude Code
7. Run in Claude Code: `claude-code mcp add`
8. **Expected**: Agents appear in Claude Code agent list

---

## Success Criteria

✅ Fresh install completes all 9 steps
✅ Migration step shows "Applied 1 migration(s)"
✅ Dashboard accessible from other PC
✅ Download buttons work (slash commands + agents)
✅ ZIP files contain expected content
✅ Install commands have correct URLs
✅ Claude Code/Codex/Gemini detect agents

---

**Expected Time**: 30-45 minutes total

**Report Issues**: Document errors with screenshots, console output, and migration logs

---

Last updated: 2025-11-05
