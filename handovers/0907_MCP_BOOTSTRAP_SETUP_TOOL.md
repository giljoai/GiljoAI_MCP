# Handover 0907: MCP Bootstrap Setup Tool (`giljo_setup`)

**Date:** 2026-04-04
**Priority:** High
**Status:** Not Started
**Edition Scope:** CE
**Estimated Complexity:** 4-6 hours (1 session)

---

## Task Summary

Create a single MCP tool `giljo_setup` that provisions slash commands AND agent templates in one step, eliminating the browser from the first-time setup flow. The tool stages a combined ZIP and returns a download URL + platform-specific extract/config instructions. The agent downloads and extracts the ZIP (binary transfer, no hallucination risk), applies any required config edits, and reports completion.

**Why:** The current first-time setup requires 6 steps across browser and terminal with 2+ CLI reboots. This reduces it to: paste MCP attach command → restart → "run giljo_setup" → restart → done. The browser is completely removed from the critical path for first-time setup.

**What stays:** Slash commands persist on disk after install. Users re-run `/gil_get_agents` (or platform equivalent) in the future to pull updated agent templates. The browser setup wizard remains functional as a GUI alternative. The existing token + staging infrastructure is reused.

---

## Current Flow (what we're replacing)

```
1. Browser: Setup wizard → copies bootstrap prompt (token-secured download URL baked in)
2. User pastes prompt into CLI → agent downloads slash commands ZIP, extracts
3. CLI restart #1
4. User runs /gil_get_agents → MCP tool returns template content as text → agent writes files
   (hallucination risk: agent processes template content before writing)
5. Gemini: agent patches settings.json | Codex: agent merges config.toml
6. CLI restart #2 → operational
```

**Problems:**
- Browser required for initial setup
- Two separate download/install steps (slash commands, then agent templates)
- Agent templates delivered as text through the LLM — risk of hallucination/modification
- 2+ CLI reboots
- 3 copy-paste operations

## New Flow (with `giljo_setup`)

```
1. User pastes MCP attach command into CLI → restart #1
2. User says "run giljo_setup" (or agent discovers it on connect)
   → MCP tool stages combined ZIP (slash commands + agent templates)
   → Returns: download URL + extract instructions + config edit instructions
   → Agent runs curl (binary transfer — no hallucination)
   → Agent extracts ZIP to correct platform paths
   → Agent applies config edits (Gemini: settings.json, Codex: config.toml)
3. CLI restart #2 → fully operational
```

**Improvements:**
- No browser in the critical path
- 1 step instead of 3 (single tool call provisions everything)
- Binary ZIP transfer — agent never sees or processes template content
- Slash commands installed on disk for future `/gil_get_agents` runs
- Same 2 reboots (unavoidable — MCP config + file discovery)

---

## Technical Design

### The MCP Tool: `giljo_setup`

**Registration:** `api/endpoints/mcp_sdk_server.py`

```python
@mcp.tool(
    name="giljo_setup",
    description=(
        "First-time setup: installs slash commands and agent templates for your CLI tool. "
        "Downloads a ZIP and extracts to the correct paths. Run once after connecting. "
        "Platform is auto-detected or can be specified: claude_code, codex_cli, gemini_cli."
    ),
)
async def giljo_setup(
    platform: str = "auto",
    install_location: str = "user",
    ctx: Context = None,
) -> dict:
```

**Parameters:**
- `platform`: `"auto"` (detect from MCP handshake), `"claude_code"`, `"codex_cli"`, `"gemini_cli"`
- `install_location`: `"user"` (home directory) or `"project"` (CWD). Default `"user"`.

**Returns:** A structured dict with:
```json
{
  "download_url": "https://host:7272/api/download/temp/{token}/giljo_setup.zip",
  "expires_in_minutes": 15,
  "platform": "claude_code",
  "install_instructions": {
    "download": "Download the ZIP from the URL above using curl or wget",
    "extract_path": "~/.claude/",
    "extract_command": "unzip -o giljo_setup.zip -d ~/.claude/",
    "config_edits": [],
    "cleanup": "rm giljo_setup.zip",
    "post_install": "Restart your CLI tool to activate slash commands and agent templates."
  },
  "contents_summary": {
    "slash_commands": ["gil_get_agents", "gil_add"],
    "agent_templates": ["orchestrator", "analyzer", "implementer", "documenter", "reviewer", "tester"],
    "total_files": 8
  }
}
```

### Platform-Specific Instructions

**Claude Code:**
```json
{
  "extract_path": "~/.claude/",
  "extract_command": "unzip -o giljo_setup.zip -d ~/.claude/",
  "config_edits": []
}
```
ZIP structure: `commands/gil_get_agents.md`, `commands/gil_add.md`, `agents/*.md`

**Gemini CLI:**
```json
{
  "extract_path": "~/.gemini/",
  "extract_command": "unzip -o giljo_setup.zip -d ~/.gemini/",
  "config_edits": [
    {
      "file": "~/.gemini/settings.json",
      "action": "merge_json",
      "value": {"experimental": {"enableAgents": true}},
      "reason": "Required for Gemini CLI to discover custom agents"
    }
  ]
}
```
ZIP structure: `commands/gil_get_agents.toml`, `commands/gil_add.toml`, `agents/*.md`

**Codex CLI:**
```json
{
  "extract_path": "~/.codex/",
  "extract_command": "unzip -o giljo_setup.zip -d ~/.codex/",
  "config_edits": [
    {
      "file": "~/.codex/config.toml",
      "action": "merge_toml",
      "value": {"features": {"default_mode_request_user_input": true}},
      "reason": "Required for interactive skill menus"
    },
    {
      "file": "~/.codex/config.toml",
      "action": "add_agent_registrations",
      "agents": [
        {"name": "gil-orchestrator", "config_file": "agents/gil-orchestrator.toml"},
        {"name": "gil-analyzer", "config_file": "agents/gil-analyzer.toml"}
      ],
      "reason": "Register agent templates so Codex CLI discovers them"
    }
  ]
}
```
ZIP structure: `skills/gil-get-agents/SKILL.md`, `skills/gil-add/SKILL.md`, `agents/gil-*.toml`

### Combined ZIP Staging

**New method:** `FileStaging.stage_combined_setup(staging_path, platform, tenant_key, db_manager)`

This method:
1. Calls existing `get_all_templates(platform)` for slash command content
2. Calls existing `AgentTemplateAssembler.assemble(templates, platform)` for agent template content
3. Structures them into a single ZIP with platform-correct directory layout
4. The ZIP extracts directly into the platform's home directory root

**ZIP layout per platform:**

Claude Code:
```
commands/
  gil_get_agents.md
  gil_add.md
agents/
  orchestrator.md
  analyzer.md
  implementer.md
  ...
```

Gemini CLI:
```
commands/
  gil_get_agents.toml
  gil_add.toml
agents/
  orchestrator.md
  analyzer.md
  ...
```

Codex CLI:
```
skills/
  gil-get-agents/
    SKILL.md
  gil-add/
    SKILL.md
agents/
  gil-orchestrator.toml
  gil-analyzer.toml
  ...
```

### Platform Auto-Detection

The MCP protocol's `initialize` handshake includes `clientInfo.name`. Check `ctx.session` or equivalent for:
- `"claude-code"` or `"Claude Code"` → `claude_code`
- `"codex"` or `"codex-cli"` → `codex_cli`
- `"gemini"` or `"gemini-cli"` → `gemini_cli`

If detection fails, fall back to requiring the `platform` parameter explicitly. Search `mcp_sdk_server.py` for how `ctx` exposes session/client metadata — the MCP Python SDK may surface this via `ctx.client_info` or similar.

If the SDK doesn't expose client info yet, the tool works fine with explicit `platform` parameter — the agent knows what platform it's running on.

### WebSocket Events

Emit `setup:bootstrap_complete` on successful staging (reuse the existing pattern from `setup:commands_installed` and `setup:agents_downloaded`). The frontend setup wizard can listen for this to update its checklist if the user has the browser open.

---

## What to Reuse (DO NOT duplicate)

| Existing code | Where | Use in giljo_setup |
|---|---|---|
| `get_all_templates(platform)` | `slash_command_templates.py` | Slash command file content |
| `AgentTemplateAssembler.assemble()` | `agent_template_assembler.py` | Agent template file content |
| `render_claude_agent/gemini/codex()` | `template_renderer.py` | Already called by assembler |
| `TokenManager.generate_token()` | `download_tokens.py` | Token creation + lifecycle |
| `FileStaging.create_staging_directory()` | `file_staging.py` | Staging dir setup |
| `ToolAccessor._call_tool()` pattern | `tool_accessor.py` | Tenant-aware tool delegation |
| Download endpoint | `downloads.py:712` | `GET /api/download/temp/{token}/{filename}` — no changes needed |

### New Code (3 touch points)

1. **`file_staging.py`** — Add `stage_combined_setup()` method
2. **`tool_accessor.py`** — Add `bootstrap_setup()` method that orchestrates token + staging
3. **`mcp_sdk_server.py`** — Register `giljo_setup` MCP tool

---

## Relationship to Existing Flows

| Flow | Impact |
|---|---|
| **Setup wizard (browser)** | Unchanged. Remains as GUI alternative. Users who prefer the browser still use SetupStep3Commands. |
| **`/gil_get_agents` slash command** | Unchanged. Installed by `giljo_setup` on disk. Users run it in the future to pull updated agent templates. |
| **`/gil_add` slash command** | Unchanged. Installed by `giljo_setup`. |
| **AgentExport.vue (dashboard)** | Unchanged. Manual download path for users who want ZIPs directly. |
| **Bootstrap prompt flow** | Still works. `giljo_setup` is an additional path, not a replacement. |
| **Direct ZIP endpoints** | Unchanged. `/api/download/slash-commands.zip` and `/api/download/agent-templates.zip` remain. |

---

## Why Binary ZIP, Not Text Response

The existing `/gil_get_agents` flow returns agent template content as text in the MCP tool response. The LLM then writes it to disk. This creates hallucination risk — the agent may:
- Add comments or annotations to YAML frontmatter
- "Fix" formatting it doesn't understand
- Drop fields it considers unnecessary
- Inject helpful additions

The ZIP approach eliminates this entirely. The agent runs `curl` + `unzip` — binary operations that don't pass through the LLM's generation layer. The only LLM-mediated writes are config edits (small, specific, verifiable JSON/TOML patches).

---

## Testing Requirements

### Unit Tests (`tests/test_0907_bootstrap_setup.py`)

- `test_stage_combined_setup_claude_code` — ZIP contains `commands/*.md` + `agents/*.md`
- `test_stage_combined_setup_gemini_cli` — ZIP contains `commands/*.toml` + `agents/*.md`
- `test_stage_combined_setup_codex_cli` — ZIP contains `skills/*/SKILL.md` + `agents/*.toml`
- `test_giljo_setup_returns_download_url` — Response includes valid URL with token
- `test_giljo_setup_returns_platform_instructions` — Config edits correct per platform
- `test_giljo_setup_auto_detect_platform` — Falls back to explicit when detection unavailable
- `test_zip_extracts_to_correct_structure` — Verify extract produces correct file tree
- `test_token_expires_after_15_minutes` — Reuse existing token lifecycle tests

### Manual Testing Checklist

- [ ] `giljo_setup` appears in MCP tool list after connecting
- [ ] Claude Code: agent downloads ZIP, extracts to `~/.claude/`, commands + agents work after restart
- [ ] Gemini CLI: same + `settings.json` patched with `enableAgents`
- [ ] Codex CLI: same + `config.toml` patched with feature flag + agent registrations
- [ ] Existing setup wizard still works (no regressions)
- [ ] `/gil_get_agents` still works for template updates after initial `giljo_setup`
- [ ] Token expires after 15 minutes, download fails gracefully

---

## Success Criteria

1. User can go from MCP attach → `giljo_setup` → restart → fully operational (no browser)
2. Slash commands persist on disk for future `/gil_get_agents` runs
3. All template content delivered via binary ZIP (no hallucination risk)
4. Config edits (Gemini settings.json, Codex config.toml) applied correctly
5. Existing flows (browser wizard, AgentExport, direct ZIP) unaffected
6. Works for all 3 platforms: Claude Code, Codex CLI, Gemini CLI

---

## Files to Create/Modify

**Modify (3 files):**
- `src/giljo_mcp/file_staging.py` — Add `stage_combined_setup()` method
- `src/giljo_mcp/tools/tool_accessor.py` — Add `bootstrap_setup()` method
- `api/endpoints/mcp_sdk_server.py` — Register `giljo_setup` MCP tool

**Create (1 file):**
- `tests/test_0907_bootstrap_setup.py` — Unit tests

**Do NOT modify:**
- `slash_command_templates.py` — consumed as-is
- `agent_template_assembler.py` — consumed as-is
- `template_renderer.py` — consumed as-is
- `download_tokens.py` — consumed as-is
- `downloads.py` — existing temp download endpoint handles the ZIP delivery
- Setup wizard Vue components — remain as GUI alternative

---

## Out of Scope

- Replacing the browser setup wizard (it stays as an alternative)
- Auto-running `giljo_setup` on first connect (user must invoke it explicitly)
- PyPI distribution / `pip install` flow (that's 0903)
- Modifying the token system or download endpoints
- Removing the existing `/gil_get_agents` slash command flow

---

## Relationship to Other Handovers

| Handover | Relationship |
|----------|-------------|
| **0903** (Streamlined CLI Install) | Independent. 0903 adds `pip install` + `giljo-mcp init`. `giljo_setup` handles post-connect provisioning regardless of how the server was installed. They compose well together. |
| **0855a-g** (Setup Wizard) | Unchanged. `giljo_setup` is a parallel path, not a replacement. The wizard's WebSocket events gain a new `setup:bootstrap_complete` event. |
| **0836a-e** (Multi-Platform Export) | Builds on. Uses the same assembler + renderer infrastructure created in 0836. |
| **0846a-c** (MCP SDK Migration) | Builds on. Tool registration uses the MCP SDK patterns from 0846. |
