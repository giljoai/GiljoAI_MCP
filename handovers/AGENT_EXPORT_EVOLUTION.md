# Agent Export Evolution: `/gil_get_agents`

**Status:** Proposal — Pending CE post-launch sprint  
**Supersedes:** Current Claude Code-only agent export in My Settings → Integrations  
**Audience:** Coding agents implementing the change, project contributors  
**Date:** 2026-03-22

---

## Summary

Rename `/gil_get_claude_agents` to `/gil_get_agents`. The command becomes platform-aware: it exports agent templates from the GiljoAI MCP server in the correct format for whichever CLI tool the developer is using (Claude Code, Codex CLI, or Gemini CLI). The MCP backend pre-assembles files where possible; the LLM handles only platform-specific questions the server cannot answer.

---

## Why This Change

The original `/gil_get_claude_agents` was written when only Claude Code CLI supported subagents via the Task tool. As of March 2026, all three major CLI tools now ship native subagent systems:

- **Claude Code** — Stable. Agent definitions as `.md` files in `.claude/agents/`. Spawned via Agent/Task tool.
- **Codex CLI** — GA (March 2026). Agent definitions as `.toml` files in `~/.codex/agents/` + entries in `config.toml`. Spawned via `spawn_agent`.
- **Gemini CLI** — Experimental. Agent definitions as `.md` files in `.gemini/agents/`. Spawned via `delegate_to_agent`. Parallel execution on roadmap.

GiljoAI already manages agent templates as platform-neutral data (role, name, description, expertise). The export pipeline needs to format this data correctly per platform, not be locked to one CLI.

---

## Architecture: Server Pre-Assembles, LLM Confirms

### Design Principle

The MCP backend does the heavy lifting. The LLM at the CLI asks only what the server genuinely cannot know.

**Server handles:**
- Agent template content (role identity, description, expertise — the "Role and Expertise" body)
- Agent naming (`{Role}_{CustomSuffix}` convention)
- Platform-specific formatting (YAML frontmatter for Claude/Gemini, TOML for Codex)
- Known defaults (dashboard-assigned colors, tool permissions, GiljoAI protocol injection points)
- File packaging (ZIP for Claude/Gemini, structured data for Codex)

**LLM handles:**
- Asking which model to use per agent (Claude: haiku/sonnet/opus; Codex: model string; Gemini: model string)
- Any platform-specific customization the server doesn't store (rare edge cases)
- Writing files to the correct directory with user confirmation
- Codex-specific: merging agent entries into the user's existing `config.toml` (requires reading current config first)

### Why Not Fully Interactive?

Trusting three different LLMs (Claude, GPT, Gemini) to correctly generate TOML vs YAML Markdown frontmatter from instructions alone is fragile. Each model interprets formatting instructions differently. Server-side assembly guarantees correct formatting.

### Why Not Fully Pre-Assembled?

Two reasons:
1. **Model selection is a developer preference per environment.** A developer might use Opus on their main machine and Sonnet on a CI runner. The server doesn't know this.
2. **Codex CLI requires `config.toml` modification.** The server cannot safely merge into the user's existing TOML config — only the LLM running locally can read and modify that file responsibly.

---

## Installation Paths: Consolidation

### Current State (Claude Code Only)

Today there are three ways to install agent templates, all scoped to Claude Code:

1. **Copy-Paste Prompt (Personal)** — Button in UI copies a natural language instruction with a 15-minute time-limited ZIP URL. User pastes into CLI. LLM downloads, extracts to `~/.claude/agents/`.
2. **Copy-Paste Prompt (Product)** — Same mechanism, targets `.claude/agents/` in the current project folder.
3. **Manual ZIP Download** — Direct download link from the UI. User self-installs using bundled `agent_instructions.md`.

Slash commands (`/gil_get_claude_agents`, `/gil_add`) have a separate but identical installation mechanism: a copy-paste prompt with a time-limited ZIP URL pointing to `~/.claude/commands/`.

### The Problem

Adding `/gil_get_agents` as a fourth installation path creates redundancy. Paths 1 and 2 do the same job as `/gil_get_agents` but less reliably — they depend on a time-limited URL and require the user to visit the dashboard, click a button, and paste a prompt every time they want to update agents. Multiply this by three platforms and the combinatorial complexity becomes unmanageable.

### Consolidated Design: Three Paths by Purpose

**Path A: `/gil_get_agents` — Primary (Day-to-Day)**

The recommended path for all agent template installs and updates. The slash command/skill is already installed on the developer's machine. It calls the MCP server directly — no time-limited URLs, no ZIPs, no dashboard visit required. Handles personal vs product install, model selection, backup, and platform-specific formatting. This is the path to document, promote, and optimize.

**Path B: Bootstrap Prompt — One-Time Onboarding**

A single copy-paste prompt that handles first-time setup: installs BOTH slash commands AND agent templates in one operation. This is the only copy-paste prompt a user ever needs. After this, all future agent updates go through Path A (`/gil_get_agents`).

The bootstrap prompt replaces today's separate "Install Slash Commands" and "Install Agents" copy-paste buttons with a single combined flow. See "Bootstrap Prompt Spec" below for details.

**Path C: Manual ZIP Download — Escape Hatch**

Direct ZIP download for users who want manual control, are behind restrictive networks, or prefer to inspect files before installing. Clearly labeled as the advanced/manual option in the UI. Not presented as a peer to Path A.

### What Gets Removed

- The separate "Personal Agents" and "Product Agents" copy-paste prompt buttons. The personal-vs-product question is asked inside `/gil_get_agents` and inside the bootstrap prompt — it doesn't need two separate UI buttons generating two separate time-limited URLs.
- The "Generic" tool option in the template creation UI (covered in companion doc).

### What Gets Kept

- The time-limited URL + ZIP mechanism on the backend. It's still used by the bootstrap prompt (Path B) and manual download (Path C). The mechanism is fine; we're reducing how many UI entry points trigger it.
- The manual download link. Relabeled per platform.

---

## Bootstrap Prompt: One-Time Onboarding

### Purpose

The bootstrap prompt is what a brand-new user pastes into their CLI after connecting MCP. It installs everything they need in one shot: slash commands + agent templates. After this, they never need to paste a prompt again — all future operations use the installed slash commands.

### Bootstrap Prompt Spec (Claude Code)

The Integrations page shows ONE "Setup GiljoAI" button. When clicked, it:
1. Generates a time-limited ZIP containing slash commands (`gil_get_agents.md`, `gil_add.md`)
2. Generates a time-limited ZIP containing active agent templates (pre-assembled `.md` files)
3. Copies a single prompt to clipboard:

```
Install the GiljoAI CLI integration from the MCP server. This is a one-time setup.

Step 1 — Install slash commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.claude/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Step 2 — Install agent templates:
Download: {AGENT_TEMPLATES_URL}
Extract to: ~/.claude/agents/ (create if needed)
If existing agents are present, back them up to ~/.claude/agents/backup_YYYYMMDD_HHMMSS/ first.
Delete the downloaded zip.

Adapt all commands for the OS platform you are currently running on.
After both installs complete, instruct the user to restart Claude Code.
After restart, the user will have access to /gil_get_agents and /gil_add commands,
and agent templates will appear with the /agents command.

Note: Download links expire in 15 minutes.
```

### Bootstrap Prompt Spec (Gemini CLI)

Same pattern, different paths and file formats:
- Slash commands → `.toml` files → `~/.gemini/commands/`
- Agent templates → `.md` files → `~/.gemini/agents/`
- Restart instruction: `/agents reload` or restart Gemini CLI

### Bootstrap Prompt Spec (Codex CLI)

Codex uses Skills instead of slash commands, and agents require `config.toml` integration. The bootstrap is heavier:
- Skills → `SKILL.md` directories → `~/.codex/skills/`
- Agent templates → structured data (NOT a simple ZIP extract). The bootstrap prompt for Codex should install the skills, then instruct the user: "Now run `$gil-get-agents` to install your agent templates with proper config.toml integration."

This two-step approach for Codex is intentional: the skill installation is a simple file extract, but the agent template installation requires the interactive `config.toml` merge that the skill handles properly.

### Dashboard UI: Integrations Page (Revised)

**Before:** Separate sections for MCP Config, Slash Commands (with copy prompt + manual download), and Agent Export (with personal/product copy prompts + manual download).

**After:**

```
┌─────────────────────────────────────────────────┐
│ 1. MCP Connection                               │
│    [Copy MCP Config for Claude Code]             │
│    [Copy MCP Config for Codex CLI]               │
│    [Copy MCP Config for Gemini CLI]              │
│                                                  │
│ 2. One-Time Setup (paste into your CLI)          │
│    [Setup GiljoAI for Claude Code]    ← combined │
│    [Setup GiljoAI for Codex CLI]      ← combined │
│    [Setup GiljoAI for Gemini CLI]     ← combined │
│                                                  │
│ 3. Manual Downloads (advanced)                   │
│    Slash Commands: [Download ZIP]                │
│    Agent Templates: [Download ZIP] ← per platform│
│                                                  │
│ 4. After Setup                                   │
│    Use /gil_get_agents to update agent templates │
│    Use /gil_add to create tasks and projects     │
└─────────────────────────────────────────────────┘
```

The "After Setup" section is informational — it reminds the user that once bootstrapped, they operate from the CLI, not the dashboard.

---

## Platform-Specific Export Behavior

### Claude Code CLI

**Format:** Markdown with YAML frontmatter  
**Target:** `.claude/agents/` (project) or `~/.claude/agents/` (user)  
**Approach:** Full server pre-assembly

The server generates one `.md` file per active agent template:

```yaml
---
name: implementer-frontend
description: "Implements frontend features following established patterns and component architecture"
model: sonnet
tools: Read, Write, Glob, Grep, Bash, mcp__giljo-mcp__*
color: "#3B82F6"
---
[Role and Expertise content from template]

[GiljoAI operating protocols injected at export time]
```

**LLM interaction:** Ask user for model preference per agent (default: sonnet). Ask project-level vs user-level install. Backup existing agents before overwriting.

**No change from current flow except:** The slash command name changes, and the LLM now asks which model before writing (previously hardcoded).

### Gemini CLI

**Format:** Markdown with YAML frontmatter  
**Target:** `.gemini/agents/` (project) or `~/.gemini/agents/` (user)  
**Approach:** Full server pre-assembly

The server generates one `.md` file per active agent template. Gemini's frontmatter schema differs from Claude's:

```yaml
---
name: implementer-frontend
description: "Implements frontend features following established patterns and component architecture"
kind: agent
model: gemini-2.5-pro
max_turns: 50
tools:
  - shell
  - read_file
  - write_file
  - mcp_*
---
[Role and Expertise content from template]

[GiljoAI operating protocols injected at export time]
```

**LLM interaction:** Ask user for model preference (default: gemini-2.5-pro). Ask project-level vs user-level install. Note that parallel subagent execution is still on Gemini's roadmap — agents work sequentially today.

**Key differences from Claude format:**
- `kind: agent` required in frontmatter
- `tools` is a YAML list, not comma-separated string
- `color` field not supported (omit)
- `max_turns` and `timeout_mins` available (Claude doesn't have these)
- No `permissionMode`, `isolation`, `skills`, or `memory` fields

### Codex CLI

**Format:** TOML agent file + `config.toml` entries  
**Target:** `~/.codex/agents/` (agent files) + `~/.codex/config.toml` (registry entries)  
**Approach:** Server provides structured data + format reference; LLM assembles with user guidance

Codex is architecturally different. It requires both:

**1. A standalone `.toml` agent file** per agent:

```toml
# ~/.codex/agents/implementer-frontend.toml
model = "gpt-5.2-codex"
model_reasoning_effort = "medium"

developer_instructions = """
[Role and Expertise content from template]

[GiljoAI operating protocols injected at export time]
"""
```

**2. A registration entry** in the user's `config.toml`:

```toml
[agents.implementer-frontend]
description = "Implements frontend features following established patterns and component architecture"
config_file = "./agents/implementer-frontend.toml"
nickname_candidates = ["Implementer"]
```

**LLM interaction is heavier here:**
1. Ask user for model preference (default: gpt-5.2-codex) and reasoning effort (default: medium)
2. Read user's existing `~/.codex/config.toml` to understand current state
3. Write individual `.toml` agent files to `~/.codex/agents/`
4. Merge `[agents.*]` entries into `config.toml` without overwriting unrelated config
5. Confirm changes with user before writing

**Why the LLM does more for Codex:** The `config.toml` merge is invasive. The server cannot safely pre-assemble a config.toml because it doesn't know what else is in it. The LLM must read the existing file, merge surgically, and get user confirmation.

**The server still provides:** The structured agent data (name, description, developer_instructions content, recommended model) and the exact TOML format reference so the LLM doesn't need to web search.

---

## MCP Endpoint Changes

### New Endpoint: `get_agent_templates_for_export`

**Parameters:**
- `tenant_key` (required) — Standard tenant isolation
- `platform` (required) — `claude_code` | `codex_cli` | `gemini_cli`
- `format` (optional) — `preassembled` (default for Claude/Gemini) | `structured` (default for Codex)

**Returns for `preassembled` (Claude Code / Gemini CLI):**
```json
{
  "platform": "claude_code",
  "agents": [
    {
      "filename": "implementer-frontend.md",
      "content": "---\nname: implementer-frontend\n...",
      "role": "implementer",
      "color": "#3B82F6"
    }
  ],
  "install_paths": {
    "project": ".claude/agents/",
    "user": "~/.claude/agents/"
  },
  "format_version": "1.0"
}
```

**Returns for `structured` (Codex CLI):**
```json
{
  "platform": "codex_cli",
  "agents": [
    {
      "agent_name": "implementer-frontend",
      "description": "Implements frontend features...",
      "role": "implementer",
      "developer_instructions": "[Role and Expertise content]\n\n[Protocols]",
      "suggested_model": "gpt-5.2-codex",
      "suggested_reasoning_effort": "medium"
    }
  ],
  "install_paths": {
    "agent_files": "~/.codex/agents/",
    "config_file": "~/.codex/config.toml"
  },
  "toml_format_reference": "[Exact TOML schema documentation embedded here]",
  "format_version": "1.0"
}
```

### Existing Endpoint Behavior

The current `generate_download_token` + ZIP download flow continues to work for backward compatibility. The new endpoint can be called alongside or as a replacement.

### Platform Detection

The slash command instructions should tell the LLM which platform it is. In the current architecture, the user already selects the CLI tool in the MCP configurator. The `/gil_get_agents` slash command file is already platform-specific (one `.md` for Claude, one `.toml` for Gemini, one for Codex), so the platform is implicitly known.

---

## Slash Command: `/gil_get_agents`

### Claude Code Version (`.claude/commands/gil_get_agents.md`)

```yaml
---
name: gil_get_agents
description: Download and install GiljoAI agent templates from the MCP server
allowed-tools: mcp__giljo-mcp__*, Bash, Read, Write
---
```

```
You are the GiljoAI agent template installer for Claude Code.

## Your job
1. Call `mcp__giljo-mcp__get_agent_templates_for_export` with platform="claude_code"
2. For each agent in the response, ask the user which model they prefer:
   - haiku (fast, cost-effective)
   - sonnet (balanced — recommended default)
   - opus (maximum capability)
   Show a summary table of all agents with their roles before asking.
   The user can set one model for all or pick per-agent.
3. Ask: Install as project agents (.claude/agents/) or user agents (~/.claude/agents/)?
4. Backup existing agents: rename any existing .claude/agents/*.md files
   to .claude/agents/*.md.bak.YYYYMMDD_HHMMSS
5. Write each agent file with the user's model selection applied
6. Report what was installed and instruct the user to restart Claude Code

## Rules
- Do NOT modify the agent name, description, or Role and Expertise content
- Do NOT modify the GiljoAI protocol sections
- The ONLY user-configurable field is model selection
- Colors are pre-assigned by the server — do not change them
```

### Gemini CLI Version (`.gemini/commands/gil_get_agents.toml`)

```toml
description = "Download and install GiljoAI agent templates from the MCP server"

prompt = """
You are the GiljoAI agent template installer for Gemini CLI.

## Your job
1. Call the GiljoAI MCP tool `get_agent_templates_for_export` with platform="gemini_cli"
2. For each agent, ask the user which model they prefer (default: gemini-2.5-pro)
3. Ask: Install as project agents (.gemini/agents/) or user agents (~/.gemini/agents/)?
4. Backup existing agents before overwriting
5. Write each agent file with the user's model selection applied
6. Remind user: parallel subagent execution is experimental in Gemini CLI.
   Agents will work but may execute sequentially.
7. Instruct user to run /agents reload or restart Gemini CLI

## Rules
- Do NOT modify agent name, description, or Role and Expertise content
- Do NOT modify GiljoAI protocol sections
- User-configurable: model selection, max_turns (default 50)
- Colors are NOT supported in Gemini agent frontmatter — omit them
"""
```

### Codex CLI Version (Codex Skill: `~/.codex/skills/gil-get-agents/SKILL.md`)

Since Codex deprecated custom prompts in favor of Skills, the installer is delivered as a Skill rather than a slash command:

```yaml
---
name: gil-get-agents
description: "Download and install GiljoAI agent templates from the MCP server into Codex CLI. Use when the user says 'install giljo agents', 'get agents', or 'gil_get_agents'."
---
```

```
You are the GiljoAI agent template installer for Codex CLI.

## Your job
1. Call the GiljoAI MCP tool `get_agent_templates_for_export` with platform="codex_cli"
2. The response includes structured agent data and a TOML format reference.
3. For each agent, ask the user which model to use (default: gpt-5.2-codex)
   and reasoning effort (low/medium/high, default: medium)
4. Read the user's existing ~/.codex/config.toml to understand current config
5. For each agent, create a .toml file in ~/.codex/agents/:
   - Use the exact TOML format from the format_reference in the response
   - Embed the developer_instructions field as a multi-line TOML string
6. Merge [agents.*] entries into config.toml:
   - Do NOT overwrite existing [agents] settings unrelated to GiljoAI
   - Add or update only the GiljoAI agent entries
   - Show the user a diff of config.toml changes before writing
7. Instruct the user to restart Codex CLI

## Rules
- Do NOT modify agent names, descriptions, or developer_instructions content
- Do NOT modify GiljoAI protocol sections within developer_instructions
- User-configurable: model, model_reasoning_effort, nickname_candidates
- ALWAYS show config.toml diff before writing — this file affects the user's entire Codex setup
- If config.toml has existing [agents.*] entries, preserve them
```

---

## Backward Compatibility & Migration

### What Changes for Existing Claude Code Users

Existing users who already have `/gil_get_claude_agents` installed will see it still work. The command should be kept as a deprecated alias for one release cycle, displaying: "This command has been renamed to /gil_get_agents. Please run the Setup GiljoAI prompt from the dashboard to update your slash commands."

### Backend Mechanisms Preserved

- The `generate_download_token` + time-limited ZIP download mechanism is NOT removed. It continues to power the bootstrap prompt (Path B) and manual download (Path C).
- The agent template ZIP assembly logic is preserved and extended with platform-aware formatting.

### What Gets Retired (After Migration Period)

- Separate "Personal Agents" and "Product Agents" copy-paste prompt buttons — replaced by the combined bootstrap prompt and the `/gil_get_agents` command which asks this question interactively.
- Separate "Install Slash Commands" copy-paste prompt button — merged into the combined bootstrap prompt.
- The `/gil_get_claude_agents` alias — removed after one release cycle.

### Migration Path

1. Existing Claude Code users: Dashboard shows a notice — "Your slash commands need updating. Click Setup GiljoAI to reinstall."
2. The bootstrap prompt overwrites old slash commands with new ones (backup first).
3. Agent templates are re-exported with the updated format (model field now configurable).
4. After restart, the user has `/gil_get_agents` and `/gil_add` ready to use.

---

## Implementation Sequence

### Phase 1: Backend (Pre-launch or Sprint 1)
1. Add `get_agent_templates_for_export` MCP endpoint with platform-aware assembly
2. Add Gemini frontmatter formatter and Codex TOML formatter to export pipeline
3. Ensure color assignments are stored per-role and included in Claude exports

### Phase 2: Slash Commands, Skills, and Bootstrap (Sprint 1)
4. Create `/gil_get_agents` slash command for Claude Code (rename + add model prompt)
5. Create `/gil_get_agents.toml` command for Gemini CLI
6. Create `gil-get-agents/SKILL.md` skill for Codex CLI
7. Create combined bootstrap prompt generator (slash commands + agents in one ZIP per platform)
8. Keep `/gil_get_claude_agents` as deprecated alias with migration notice

### Phase 3: Dashboard UI Consolidation (Sprint 1-2)
9. Redesign Integrations page: MCP Config → One-Time Setup → Manual Downloads → After Setup
10. Replace separate Personal/Product agent export buttons with single combined bootstrap
11. Replace separate slash command install button — merged into bootstrap
12. Add per-platform Setup buttons that generate the combined bootstrap prompt
13. Add per-platform manual download ZIP links (agent templates formatted per platform)

### Phase 4: Validation & Docs (Sprint 2)
14. Integration test: full bootstrap flow for each platform (MCP connect → paste → restart → verify)
15. Integration test: `/gil_get_agents` update flow for each platform
16. Update README, onboarding guide, and CONTRIBUTING.md
17. Remove deprecated alias after one release cycle

---

## User Journey (End State)

### First-Time Setup (Once)
1. User creates account, logs in to GiljoAI dashboard
2. Agent templates auto-seeded (6 defaults). User optionally customizes via Agent Template Manager
3. User goes to Integrations, copies MCP config for their CLI tool, connects MCP
4. User clicks "Setup GiljoAI for [CLI Tool]" — copies ONE bootstrap prompt
5. User pastes prompt into CLI — installs slash commands + agent templates in one shot
6. User restarts CLI. Done.

### Day-to-Day Usage
- `/gil_get_agents` — Update agent templates when roles change or new agents are added
- `/gil_add` — Create tasks and projects on the MCP server directly from CLI conversations
- Dashboard Agent Template Manager — Edit roles, expertise, toggle agents active/inactive
- No further copy-paste prompts needed. Everything operates via installed commands.

### When Agent Templates Change
User modifies templates in dashboard → runs `/gil_get_agents` in CLI → updated agents installed. No dashboard prompt copying, no time-limited URLs. The command calls MCP directly.

---

## References

- `Subagent_CLLItool_maturity.md` — Authoritative format comparison across all three platforms
- `handovers/start_to_finish_agent_FLOW.md` — Current agent export flow details
- `Simple_Vision.md` — Agent template system architecture, 8-role limit, export mechanisms
- Claude Code agent docs: `code.claude.com/docs/en/sub-agents`
- Codex CLI subagent docs: `developers.openai.com/codex/subagents`
- Gemini CLI subagent docs: `geminicli.com/docs/core/subagents/`
