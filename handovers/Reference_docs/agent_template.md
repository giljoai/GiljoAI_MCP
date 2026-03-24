# Agent Template System — Research & State Analysis

**Status:** Research document, pre-implementation
**Edition Scope:** CE
**Related:** `agent_analysis.md` (multi-CLI strategy), `Subagent_CLLItool_maturity.md` (platform audit), Handover 0813 (context separation — COMPLETE)

---

## 1. Current State After 0813

Handover 0813 completed the backend separation of template content into three contexts:

| Context | What | Where |
|---|---|---|
| **Role Identity** | WHO — expertise prose, behavioral rules, success criteria | `user_instructions` (DB) → template file body |
| **Operating Protocols** | HOW — 5-phase lifecycle, messaging, MCP usage | `full_protocol` via `get_agent_mission()` |
| **Work Order** | WHAT — team context, tasks, dependencies | `mission` via `get_agent_mission()` |

`system_instructions` now contains a slim MCP bootstrap (~10 lines) from `_get_mcp_bootstrap_section()` in `template_seeder.py:686-711`. The `render_claude_agent()` function in `template_renderer.py:81-145` was updated to compose: YAML frontmatter + bootstrap + user_instructions + behavioral_rules + success_criteria.

---

## 2. Frontend Bugs (Template Manager UI)

### BUG 1: Every template update returns 403 (HIGH)

**Root cause chain:**
1. `TemplateManager.vue:1002` loads templates: `template: t.system_instructions` (maps `system_instructions` to internal `template` field)
2. User edits the textarea labeled "System Prompt" (line 457-472)
3. `TemplateManager.vue:1166` saves: `system_instructions: editingTemplate.value.template`
4. `crud.py:258-263` blocks it: `if "system_instructions" in update_data: raise HTTPException(403)`

**Every existing template update fails silently.** The frontend sends `system_instructions` on every PUT, which the backend correctly blocks (system_instructions is read-only after 0813).

**Fix:** The textarea should edit `user_instructions`, not `system_instructions`. The update payload should send `user_instructions` instead.

### BUG 2: No user_instructions editor exists (HIGH)

The `user_instructions` field — the user-editable role identity prose that 0813 explicitly made the centerpiece of template customization — has **zero UI representation**. There is no input, no textarea, no mention of it in the Template Manager dialog. The user has no way to write or edit the content that actually defines their agent's expertise.

### BUG 3: No MCP bootstrap injection on create (MEDIUM)

`crud.py:137-225` `create_template()` accepts `system_instructions` verbatim from the request body and stores it directly. There is no injection of the canonical MCP bootstrap from `_get_mcp_bootstrap_section()`. User-created templates lack the startup protocol that seeded templates have.

### BUG 4: Stale reset fallback (MEDIUM)

`template_service.py:923-944` `reset_system_instructions()` hardcodes a stale 5-line fallback:
```
# System Instructions
Use report_progress() to send updates.
Use complete_job() when the task is finished.
Use receive_messages() to check for orchestrator messages.
```
This does NOT match the canonical `_get_mcp_bootstrap_section()` bootstrap from 0813. A reset produces a broken template.

---

## 3. Export Pipeline

### Three Export Paths + Slash Command

| Path | Endpoint | Renderer | Notes |
|---|---|---|---|
| ZIP download | `GET /api/download/agent-templates.zip` | `template_renderer.render_claude_agent()` | Primary path. Max 8 templates via `select_templates_for_packaging()`. Includes install.sh + install.ps1. |
| Filesystem export | `POST /api/export/claude-code` | **Own `generate_yaml_frontmatter()`** (claude_export.py:75) | Writes to disk. Different renderer! No 8-template cap. Creates backups. |
| Token download | `POST /api/download/generate-token` | `template_renderer.render_claude_agent()` | Via `file_staging.stage_agent_templates()`. Token-based. No install scripts. |
| Slash command | `/gil_get_claude_agents` | Token download path | Calls `generate_download_token()` MCP tool → token endpoint → `render_claude_agent()` |

### Renderer Inconsistency

Two `generate_yaml_frontmatter()` functions exist:
- `downloads.py:83` — **DEAD CODE** (zero references). Uses `mcp__giljo_mcp__*` (underscore).
- `claude_export.py:75` — **ACTIVE** (filesystem export path). Uses `mcp__giljo-mcp__*` (hyphen). Hardcodes `tools: ["mcp__giljo-mcp__*"]` instead of using template's `tools` field.

The filesystem export path (`claude_export.py`) does NOT use `render_claude_agent()`, producing different output than the ZIP and token paths. It ignores template colors, doesn't include user_instructions, and hardcodes the tools field.

### Default Merging

`render_claude_agent()` applies these defaults when template fields are null/empty:
- `description` → `"Subagent for {role}"`
- `model` → `"sonnet"` (unless explicitly `"inherit"`)
- `tools` → omitted from YAML (inherits all from parent session)
- `color` → mapped via `hex_to_claude_color()` from `background_color`

`select_templates_for_packaging()` selects up to 8 active, non-orchestrator templates sorted by: `is_default` DESC → `updated_at` DESC → `name` ASC.

---

## 4. CLI-Specific Fields (From Primary Sources)

Per-platform frontmatter schemas verified against `Subagent_CLLItool_maturity.md`:

### Claude Code (`.claude/agents/*.md`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | Yes | Agent slug |
| `description` | string | Yes | Used for routing decisions |
| `model` | string | No | `sonnet`, `opus`, `haiku` |
| `color` | string | No | Named color |
| `tools` | string | No | Comma-separated; omit to inherit all |
| `permissionMode` | string | No | `default`, `bypassPermissions`, etc. |
| `isolation` | string | No | `worktree` for git worktree isolation |
| `background` | boolean | No | Always run in background |
| `skills` | list | No | Skill bundles to inject |
| `memory` | string | No | Persistent knowledge directory |

### Codex CLI (`config.toml` + per-role `.toml`)
| Field | Location | Notes |
|---|---|---|
| `description` | `[agents.<name>]` in config.toml | Role description |
| `config_file` | `[agents.<name>]` in config.toml | Path to role-specific .toml |
| `nickname_candidates` | `[agents.<name>]` in config.toml | Display name pool |
| `model` | Per-role .toml | Overrides parent |
| `model_reasoning_effort` | Per-role .toml | Reasoning intensity |
| `developer_instructions` | Per-role .toml | System prompt content |
| `max_threads` | `[agents]` global | Default 6 |
| `max_depth` | `[agents]` global | Nesting depth, default 1 |

### Gemini CLI (`.gemini/agents/*.md`)
| Field | Type | Notes |
|---|---|---|
| `name` | string | Unique slug (lowercase, hyphens, underscores) |
| `description` | string | Visible to main agent for routing |
| `kind` | string | `local` (default) or `remote` |
| `model` | string | e.g. `gemini-2.5-pro`; defaults to `inherit` |
| `temperature` | number | 0.0–2.0 |
| `max_turns` | number | Default 15 |
| `timeout_mins` | number | Default 5 |
| `tools` | array | Restricted tool list |

---

## 5. Agent Card Design System

### Canonical Roles and Colors

Six canonical roles with locked colors (`frontend/src/config/agentColors.js`):

| Role | Hex | Usage |
|---|---|---|
| orchestrator | #D4A574 | System-managed, hidden from UI |
| implementer | #3498DB | Blue |
| tester | #FFC300 | Yellow |
| analyzer | #E74C3C | Red |
| reviewer | #9B59B6 | Purple |
| documenter | #27AE60 | Green |

### Naming Convention

Templates use a `role + custom_suffix` naming pattern:
- `create_template()` in `crud.py` generates: `slugify_name(role, custom_suffix)` → e.g., `implementer-backend`
- Validated with regex: `^[a-z0-9]+(-[a-z0-9]+)*$`, max 100 chars
- Role badge is locked (one of the 6 canonical roles), suffix is user-editable

### Synonym Mapping

`AGENT_SYNONYMS` in `agentColors.js` maps custom names back to canonical roles for color assignment. E.g., "coder" → "implementer", "validator" → "tester".

---

## 6. Multi-Terminal Mode (No Template File)

In multi-terminal mode, agents have no `.md` template file. Role identity is delivered differently:

1. `_resolve_spawn_template()` (`orchestration_service.py:804-894`) queries `AgentTemplate` by `agent_name`
2. Concatenates: `system_instructions + "\n\n" + user_instructions`
3. Bakes the result into `AgentJob.mission` at spawn time
4. Agent fetches mission via `get_agent_mission()` → receives combined role + work order in `mission`, plus `full_protocol` separately

This means changes to `system_instructions` and `user_instructions` content directly affect multi-terminal agent behavior without any file export step.

---

## 7. Proposed Template Manager Redesign

Replace the single "System Prompt" textarea with a structured 5-section dialog:

### Section 1: Identity
- Role dropdown (locked to 6 canonical roles)
- Custom suffix input (e.g., "backend", "security")
- Generated name preview (e.g., `implementer-backend`)
- Color swatch (auto-assigned from role, read-only)

### Section 2: Role Editor (the user's creative space)
- Textarea editing `user_instructions` — "Define this agent's expertise and personality"
- This is where users describe what makes their agent unique

### Section 3: Protocol Notice (non-editable)
- Info banner: "GiljoAI automatically injects orchestration protocols (MCP connectivity, lifecycle management, team coordination). These are delivered at runtime."
- No textarea, no expandable details — protocols are IP

### Section 4: CLI-Specific Fields (tabbed)
- **Claude tab:** model, tools, description, permissionMode, isolation, background, skills, memory
- **Codex tab:** model_reasoning_effort, developer_instructions, nickname_candidates
- **Gemini tab:** model, temperature, max_turns, timeout_mins, kind

### Section 5: Rules & Criteria
- Behavioral rules list editor (add/remove/reorder)
- Success criteria list editor (add/remove/reorder)

---

## 8. Multi-CLI Export Roadmap (Post-0814)

0814 fixes the broken Claude Code pipeline end-to-end. The multi-CLI export vision below is a follow-up handover (0815 or later).

### The Full Lifecycle

```
SEED → CUSTOMIZE → EXPORT → STAGE → EXECUTE
  │        │           │        │        │
  │   Template UI   Per-CLI   Mode    Agent gets
  │   edits role    format    radio   role+protocol
  │   + behavior    output    button  +work order
  │                   │
  │            ┌──────┼──────┐
  │          Claude  Codex  Gemini
  │          .md     .toml   .md
  │         (YAML)  (TOML)  (YAML)
```

Templates are defined once in the UI. At export time, they are rendered into the target CLI's native format. At staging time, the mode radio button determines how agents are spawned. At execution time, `get_agent_mission()` delivers protocols and work order regardless of AI coding agent.

### Export UX: Two Approaches

| Approach | How It Works | Slash Command | ZIP |
|---|---|---|---|
| **Per-template binding** | Each template has `cli_tool` field. Export renders each in its own format. One ZIP could contain mixed formats. | `/gil_get_agents` reads each template's `cli_tool` | Single ZIP, mixed formats |
| **Per-export selection** | Templates are CLI-agnostic. User picks target CLI at export time. All rendered in that format. | `/gil_get_agents` → "Claude, Codex, or Gemini?" → exports in selected format | 3 buttons: "Download for Claude" / "Download for Codex" / "Download for Gemini" |

**Recommendation:** Per-export selection is cleaner. Users define agents once, export to whichever CLI they use. The `cli_tool` field on templates could become the default suggestion rather than a hard binding.

### Slash Command Evolution

Current: `/gil_get_claude_agents` — hardcoded to Claude export path.

Future: `/gil_get_agents` — prompts the agent "Which AI coding agent are you using?" or reads from the orchestrator's execution mode. Routes to the appropriate renderer:
- Claude → `render_claude_agent()` (exists)
- Codex → `render_codex_agent()` (to build — produces `config.toml` + per-role `.toml`)
- Gemini → `render_gemini_agent()` (to build — produces `.gemini/agents/*.md` with Gemini-specific YAML frontmatter)

### New Renderers Needed

| Renderer | Output | Key Differences from Claude |
|---|---|---|
| `render_codex_agent()` | TOML: `[agents.<name>]` block + separate `<role>.toml` | Fundamentally different format. `developer_instructions` replaces markdown body. Config layering instead of flat file. |
| `render_gemini_agent()` | MD + YAML frontmatter (`.gemini/agents/*.md`) | Similar to Claude but different schema: `kind`, `temperature`, `max_turns`, `timeout_mins` instead of `permissionMode`, `isolation`, `skills`, `memory`. |

### Staging Mode Radio Buttons (Future)

Current: Two radio buttons — "Multi-terminal" / "Claude Code subagents"

Future: Four options — "Multi-terminal" / "Claude Code subagents" / "Codex CLI subagents" / "Gemini CLI subagents"

Each mode changes:
1. **Orchestrator prompt framing** — tells the orchestrator which spawn mechanism to use
2. **Export format** — pre-installs templates in the CLI's native format
3. **Agent spawn tool** — `Task` (Claude), `spawn_agent` (Codex), `delegate_to_agent` (Gemini)

### What 0814 Establishes for Multi-CLI

0814 is the foundation. After it ships:
- Template data model is correct (role in `user_instructions`, bootstrap in `system_instructions`)
- `render_claude_agent()` is the single Claude renderer (filesystem export unified)
- Dead code cleaned up (`generate_yaml_frontmatter` in downloads.py)
- `template_renderer.py` is the dispatch point — adding `render_codex_agent()` and `render_gemini_agent()` is additive
- CLI-specific fields in the UI are stubbed with placeholders, ready to wire when renderers exist
