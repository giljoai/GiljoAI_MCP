# Handover: Streamlined CLI Installation & One-Command Setup

**Date:** 2026-04-03
**From Agent:** Architecture session (install flow redesign)
**To Agent:** Installation Flow Agent + TDD Implementor
**Priority:** Medium (post-CE-launch improvement)
**Edition Scope:** CE
**Estimated Complexity:** 12-16 hours (2 sessions)
**Status:** Not Started

---

## Task Summary

Replace the current multi-context installation flow (download repo → `python install.py` → browser wizard → copy-paste MCP commands → restart CLI → export agents) with a streamlined CLI-first experience that keeps the user in their terminal. The goal is `pip install giljo-mcp` → `giljo-mcp init` → paste one MCP command → done.

**Why it matters:** The current flow crosses between terminal and browser 3+ times, requires 6+ manual steps, and assumes the user knows how to configure MCP servers by hand. Every context switch is a drop-off point. CLI tool users expect CLI-first setup.

**Expected outcome:** A developer with PostgreSQL installed can go from zero to a working GiljoAI orchestrator connected to their AI coding tool in under 5 minutes, without opening a browser during setup.

**Relationship to 0409:** This handover supersedes 0409 (Unified Client Quick Setup, DEFERRED). 0409 proposed bundling existing browser wizard steps into a copy-paste prompt. This handover eliminates the browser wizard requirement entirely by moving setup to the CLI. The template conversion logic from 0409 (Claude→Codex→Gemini formats) remains relevant and should be reused.

---

## Context and Background

### Current Installation Flow (6+ steps, 2 contexts)

```
Terminal                              Browser
───────                               ───────
1. git clone / download               
2. python install.py                  
   (interactive: PG password,         
    network mode, HTTPS)              
3.                                    → Open http://localhost:7272
4.                                    → Create admin account (/welcome)
5.                                    → AiToolConfigWizard: copy MCP command
6. Paste MCP command into CLI         
7.                                    → SlashCommandSetup: download ZIP
8. Restart CLI                        
9.                                    → Export agent templates (Claude only)
10. Restart CLI again                 
```

### Proposed Flow (3 steps, 1 context)

```
Terminal
───────
1. pip install giljo-mcp              # or: uvx giljo-mcp
2. giljo-mcp init                     # interactive CLI: DB, admin account, HTTPS
   → prints MCP connection command
3. Paste MCP command into CLI          # slash commands + agents auto-provision
```

### Dependency: 0902 Single-Port Frontend Serving

This handover builds on 0902. After 0902 lands:
- Production runs on one port (7272) — the MCP connection URL is unambiguous
- `install.py` already has production/dev mode detection
- `startup.py` has `--dev` flag for developers
- Frontend port references are dynamic (`window.location.port || '7272'`)
- `frontend/dist/` is the production build artifact

This handover assumes 0902 is complete. The single-port architecture simplifies the MCP connection command (no port confusion) and means the CLI init can start the server immediately after setup without needing a separate frontend process.

### What install.py Does Today (for reference)

The current `install.py` (~126KB) handles: bootstrap deps → welcome screen → network mode prompt → PostgreSQL discovery (multi-method fallback) → Node.js discovery → venv creation → pip install → pre-commit hooks → NLTK data → config.yaml generation → database creation (roles, schema) → Alembic migrations → seed data → npm install → HTTPS/mkcert setup → desktop shortcuts. It is thorough but tied to a git-clone workflow.

---

## Technical Details

### Architecture Decision: Wrapper CLI, Not a Rewrite

Do NOT rewrite `install.py`. Instead, create a thin CLI entry point (`giljo_mcp/cli.py`) that:
1. Delegates heavy lifting to existing `installer/` modules
2. Adds the missing pieces (admin account creation, MCP command generation, auto-provisioning)
3. Provides a `pip install`-compatible entry point

This respects the "fold, don't reinvent" principle. The installer modules (`installer/core/database.py`, `installer/core/config.py`, `installer/platforms/`) are battle-tested. Wrap them, don't replace them.

### Phase 1: Package Distribution — Make `pip install giljo-mcp` Work

**Goal:** A user can `pip install giljo-mcp` from PyPI (or from the repo) and get a `giljo-mcp` CLI command.

#### 1A. Fix `pyproject.toml` entry point

Current state (line 90): `# Entry points intentionally omitted`

Add:
```toml
[project.scripts]
giljo-mcp = "giljo_mcp.cli:main"
```

#### 1B. Package the installer modules

The `installer/` directory is currently excluded from the package (`tool.setuptools` only packages `src/giljo_mcp`). Two options:

**Option A (preferred):** Move installer logic into `src/giljo_mcp/installer/` so it ships with the package. The standalone `install.py` becomes a thin shim that imports from `giljo_mcp.installer`.

**Option B:** Keep `installer/` separate, make `install.py` the git-clone path and `giljo-mcp init` the pip-install path. Both call the same core logic via shared modules.

Option A is cleaner — one source of truth, one distribution method. But it requires careful import restructuring. Option B is faster to ship but creates two parallel install paths.

**Recommendation:** Start with Option B for the initial release (lower risk, `install.py` keeps working for existing users), migrate to Option A in a follow-up.

#### 1C. Include pre-built frontend

For `pip install` to work without Node.js, the package must include `frontend/dist/`. Options:

1. **Build and include in sdist/wheel** — add `frontend/dist/` to `package-data`. Requires a build step before `python -m build`.
2. **Separate download** — `giljo-mcp init` downloads a pre-built frontend tarball from a release asset.
3. **Make frontend optional** — API-only mode works without frontend. User can install Node.js and build later.

**Recommendation:** Option 3 for initial release. The MCP server works without a dashboard — users who want the UI can run `giljo-mcp build-frontend` (which wraps `npm install && npm run build`). This avoids bloating the pip package and removes the Node.js dependency for CLI-only users.

#### 1D. Config storage for pip installs

Current: `config.yaml` and `.env` live in project root (CWD).

For pip installs, use a dedicated config directory:
```
~/.giljoai/
  ├── config.yaml
  ├── .env
  ├── certs/           # mkcert certificates
  ├── data/            # uploads, temp files
  └── logs/
```

The CLI must detect which mode it's running in:
- If CWD contains `install.py` → git-clone mode, use CWD paths (backward compatible)
- Otherwise → pip-install mode, use `~/.giljoai/`

### Phase 2: `giljo-mcp init` — Interactive CLI Setup

**File:** `src/giljo_mcp/cli.py` (NEW)

```python
import click
from pathlib import Path

@click.group()
def main():
    """GiljoAI MCP - AI Agent Orchestration Platform"""
    pass

@main.command()
@click.option('--db-password', prompt='PostgreSQL password', hide_input=True)
@click.option('--network', type=click.Choice(['localhost', 'lan']), default='localhost')
@click.option('--admin-user', prompt='Admin username', default='admin')
@click.option('--admin-password', prompt='Admin password', hide_input=True, confirmation_prompt=True)
@click.option('--port', default=7272, help='API/MCP server port')
@click.option('--headless', is_flag=True, help='Non-interactive mode (all options via flags)')
def init(db_password, network, admin_user, admin_password, port, headless):
    """Initialize GiljoAI MCP: database, config, admin account, server start."""
    # 1. PostgreSQL discovery (reuse installer/core/database.py)
    # 2. Create database + roles + run migrations
    # 3. Generate config.yaml + .env
    # 4. HTTPS setup if network == 'lan' (reuse mkcert logic)
    # 5. Create admin user account (NEW — currently browser-only)
    # 6. Generate API key for CLI connection
    # 7. Start server (background or foreground)
    # 8. Print MCP connection commands for all supported CLIs
    pass
```

#### 2A. Admin account creation from CLI (NEW capability)

Currently, the admin account is created via the `/welcome` browser page. The backend logic exists in `api/endpoints/auth.py` (the registration endpoint). Extract and reuse:

```python
# In giljo_mcp/cli.py init command:
from giljo_mcp.services.user_service import UserService

user_service = UserService(db_session)
admin = user_service.create_user(
    username=admin_user,
    password=admin_password,
    role="admin",
    tenant_key=tenant_key
)
```

Search for the existing user creation logic — do not duplicate it. The service layer should already handle password hashing, tenant assignment, and validation.

#### 2B. Print MCP connection commands

After successful init, print ready-to-paste commands:

```
═══════════════════════════════════════════════════
  GiljoAI MCP is running on http://localhost:7272
═══════════════════════════════════════════════════

Connect your AI tool (copy-paste one command):

  Claude Code:
    claude mcp add --transport http giljo-mcp http://localhost:7272/mcp/sse --header "X-API-Key: sk_ce_abc123"

  Codex CLI:
    codex mcp add giljo-mcp --transport http --header "X-API-Key: sk_ce_abc123" -- http://localhost:7272/mcp/sse

  Gemini CLI:
    gemini mcp add -t sse giljo-mcp http://localhost:7272/mcp/sse -H "X-API-Key: sk_ce_abc123"

Then restart your CLI tool. Slash commands install automatically on first connection.
```

The API key (`sk_ce_abc123`) is generated during init and embedded in the output. The URL uses the configured host/port (respecting HTTPS if LAN mode).

#### 2C. Additional CLI commands

```python
@main.command()
def start():
    """Start the GiljoAI MCP server."""
    # Wraps startup.py logic

@main.command()
def stop():
    """Stop the running server."""

@main.command()
def status():
    """Show server status, connected clients, active jobs."""

@main.command()
def build_frontend():
    """Build the frontend dashboard (requires Node.js)."""
    # npm install && npm run build in frontend/
```

### Phase 3: MCP Bootstrap Tool — Auto-Provision on First Connect

**Goal:** When a CLI tool first connects via MCP, automatically install slash commands and agent templates without the user doing anything.

#### 3A. New MCP tool: `giljo_bootstrap`

**File:** `src/giljo_mcp/tools/bootstrap_tool.py` (NEW)

This tool is registered in the MCP server and called automatically (or via a one-time slash command prompt). It:

1. Detects the client type from the MCP connection metadata (Claude Code, Codex, Gemini)
2. Determines the correct file paths (`~/.claude/commands/`, `~/.codex/skills/`, `~/.gemini/agents/`)
3. Writes slash command files in the correct format (reuse `slash_command_templates.py`)
4. Writes agent template files (Claude Code only, reuse existing template logic)
5. Returns a confirmation message telling the user to restart their CLI

```python
@mcp_tool(name="giljo_bootstrap", description="Auto-configure slash commands and agent templates for your CLI tool")
async def bootstrap(client_type: str = "auto") -> str:
    """Detect CLI client and install slash commands + agent templates.

    Args:
        client_type: "claude", "codex", "gemini", or "auto" (detect from connection)
    """
    # 1. Detect or validate client_type
    # 2. Get templates from slash_command_templates.py
    # 3. Write files to correct locations
    # 4. Return success message with restart instructions
```

#### 3B. Client detection

The MCP protocol includes client metadata in the initialization handshake. Check `implementation.name` in the MCP init message to auto-detect:
- `"claude-code"` → Claude Code
- `"codex-cli"` → Codex
- `"gemini-cli"` → Gemini

If detection fails, prompt the user to specify.

#### 3C. File writing considerations

- Check for existing files before overwriting — back up to `*.bak` if found
- Use `pathlib.Path.home()` for cross-platform home directory resolution
- Handle Windows vs Unix path separators
- Validate write permissions before attempting (fail gracefully with manual instructions)

### Phase 4: Backward Compatibility

#### 4A. `install.py` keeps working

The git-clone workflow (`python install.py`) must continue to work identically. No behavioral changes. It remains the primary path for developers who clone the repo.

#### 4B. Browser wizard keeps working

The `AiToolConfigWizard.vue`, `SlashCommandSetup.vue`, and agent export flows remain functional. They serve users who prefer the GUI and are useful for reconfiguration after initial setup.

#### 4C. Migration path for existing users

Existing users who installed via `install.py` do not need to reinstall. They can optionally run `pip install -e .` from their repo to get the `giljo-mcp` CLI command, but it's not required.

---

## Implementation Plan

### Phase 1: CLI Entry Point (4-5 hours)

**Owner:** Installation Flow Agent + TDD Implementor

1. Create `src/giljo_mcp/cli.py` with Click command group
2. Add `[project.scripts]` entry point to `pyproject.toml`
3. Implement `giljo-mcp init` — delegate to existing installer modules
4. Implement admin user creation from CLI (extract from auth endpoint)
5. Implement MCP connection command generation and display
6. Add `~/.giljoai/` config directory support with git-clone fallback detection
7. Write tests: init flow, config generation, admin creation, command output

**Testing criteria:**
- `pip install -e .` creates working `giljo-mcp` command
- `giljo-mcp init` completes full setup with a fresh PostgreSQL
- Admin account works for login
- Printed MCP commands are valid and connect successfully

### Phase 2: MCP Bootstrap Tool (3-4 hours)

**Owner:** TDD Implementor

1. Create `src/giljo_mcp/tools/bootstrap_tool.py`
2. Implement client detection from MCP handshake metadata
3. Implement file writing for slash commands (all 3 CLI formats)
4. Implement agent template writing (Claude Code only)
5. Register tool in MCP server
6. Write tests: detection, file generation, backup logic, permission handling

**Testing criteria:**
- Tool writes correct files to correct locations for each client type
- Existing files are backed up before overwrite
- Permission errors produce helpful fallback instructions
- Client auto-detection works for Claude Code (primary target)

### Phase 3: Package Distribution Prep (2-3 hours)

**Owner:** Installation Flow Agent

1. Verify `python -m build` produces working sdist and wheel
2. Test `pip install` from wheel in a clean venv
3. Test `uvx giljo-mcp init` workflow
4. Document the frontend-optional flow (`giljo-mcp build-frontend`)
5. Update `README.md` with new installation instructions
6. Update `CONTRIBUTING.md` with developer setup path

**Testing criteria:**
- Clean venv + `pip install giljo-mcp-1.0.0.whl` → `giljo-mcp --help` works
- `giljo-mcp init` works without Node.js (API-only mode)
- `giljo-mcp build-frontend` works when Node.js is available

### Phase 4: Integration Testing & Documentation (2-3 hours)

**Owner:** Backend Integration Tester + Documentation Manager

1. End-to-end test: fresh machine → `pip install` → `init` → MCP connect → bootstrap → working
2. Test both paths: pip-install AND git-clone (backward compat)
3. Test HTTPS/LAN mode through CLI init
4. Update `docs/SERVER_ARCHITECTURE_TECH_STACK.md` with new install paths
5. Update handover catalogue and roadmap

**Testing criteria:**
- Both install paths produce identical running systems
- HTTPS setup works via CLI (mkcert integration)
- Documentation matches actual behavior

---

## Dependencies and Blockers

**Hard dependency:**
- **0902 (Single-Port Frontend Serving)** must be complete. This handover assumes production runs on port 7272 with FastAPI serving static files. Without 0902, the MCP connection URL and startup logic are different.

**Soft dependencies:**
- PostgreSQL must be pre-installed by the user (not automatable cross-platform)
- Node.js required only if user wants the dashboard (optional for MCP-only usage)

**Blockers:** None identified beyond 0902.

---

## Testing Requirements

### Unit Tests

**`tests/test_cli.py`** (NEW, ~15 tests):
- `test_init_creates_config_directory`
- `test_init_generates_valid_config_yaml`
- `test_init_creates_admin_user`
- `test_init_generates_api_key`
- `test_init_prints_mcp_commands_for_all_clients`
- `test_init_respects_custom_port`
- `test_init_https_mode_includes_cert_instructions`
- `test_config_dir_detection_git_clone_mode`
- `test_config_dir_detection_pip_install_mode`

**`tests/test_bootstrap_tool.py`** (NEW, ~12 tests):
- `test_client_detection_claude_code`
- `test_client_detection_codex`
- `test_client_detection_gemini`
- `test_slash_commands_written_claude_format`
- `test_slash_commands_written_codex_format`
- `test_slash_commands_written_gemini_format`
- `test_agent_templates_written_claude_only`
- `test_existing_files_backed_up`
- `test_permission_error_returns_manual_instructions`
- `test_bootstrap_idempotent`

### Manual Testing Checklist

- [ ] Fresh venv: `pip install -e .` → `giljo-mcp --help` shows commands
- [ ] `giljo-mcp init` with fresh PostgreSQL → server starts, admin can log in
- [ ] Printed Claude Code MCP command → paste → connection works
- [ ] Printed Codex MCP command → paste → connection works
- [ ] `giljo_bootstrap` tool auto-installs slash commands for detected client
- [ ] Existing `install.py` flow still works identically (backward compat)
- [ ] Browser wizards still work for users who prefer GUI setup
- [ ] HTTPS/LAN mode works through `giljo-mcp init --network lan`
- [ ] `giljo-mcp build-frontend` works with Node.js installed
- [ ] API-only mode works without Node.js or frontend build

---

## Success Criteria

1. `pip install giljo-mcp` → `giljo-mcp init` → paste MCP command → working orchestrator in < 5 minutes
2. Existing `install.py` path unaffected — zero regressions
3. Browser setup wizards remain functional for GUI preference
4. MCP bootstrap auto-provisions slash commands on first connect
5. All new tests pass, no existing tests broken
6. Documentation updated for both install paths

---

## Rollback Plan

1. Remove `[project.scripts]` from `pyproject.toml` — `giljo-mcp` CLI disappears
2. Delete `src/giljo_mcp/cli.py` — no impact on existing functionality
3. Delete `src/giljo_mcp/tools/bootstrap_tool.py` — MCP server works without it
4. All changes are additive — the existing `install.py` + browser wizard path is never modified

---

## Files to Create/Modify

**Create (3 files):**
- `src/giljo_mcp/cli.py` — Click CLI entry point (`init`, `start`, `stop`, `status`, `build-frontend`)
- `src/giljo_mcp/tools/bootstrap_tool.py` — MCP auto-provisioning tool
- `tests/test_cli.py` — CLI command tests

**Modify (4 files):**
- `pyproject.toml` — Add `[project.scripts]` entry point, verify package includes
- `src/giljo_mcp/tools/slash_command_templates.py` — Extract reusable file-writing functions
- `README.md` — Add pip-install instructions alongside git-clone
- `CONTRIBUTING.md` — Developer setup path (`giljo-mcp init` + `--dev` flag)

**Do NOT modify:**
- `install.py` — Existing flow unchanged
- `installer/` — Modules are consumed, not changed
- Frontend wizard components — Remain as GUI alternative

---

## Out of Scope

- PyPI publication (infrastructure decision, separate from code readiness)
- Docker distribution (separate handover if needed)
- Auto-updating slash commands after initial provisioning
- Windows installer (.msi) or macOS installer (.pkg)
- Removing `install.py` or the browser wizard (both remain as alternative paths)
- Auto-installing PostgreSQL (not reliably automatable cross-platform)

---

## Relationship to Other Handovers

| Handover | Relationship |
|----------|-------------|
| **0409** (Quick Setup) | **Superseded.** 0409 proposed browser-based prompt bundling. This handover moves setup to CLI entirely. Template conversion logic from 0409 is reusable. |
| **0902** (Single Port) | **Hard dependency.** Must complete first. Provides single-port architecture that simplifies connection URLs and eliminates frontend process management. |
| **0844a-c** (Data Export/Import) | **Independent.** Export/import can use the `giljo-mcp` CLI as additional subcommands later. |
| **0847** (Tool-Aware Orchestrator) | **Independent.** Bootstrap tool is a setup utility, not an orchestrator protocol change. |
