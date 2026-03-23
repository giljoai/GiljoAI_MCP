# Multi-Platform Agent Template Design

**Status:** Proposal — Pending CE post-launch sprint  
**Companion to:** `AGENT_EXPORT_EVOLUTION.md` (the `/gil_get_agents` command spec)  
**Audience:** Coding agents implementing the change, project contributors  
**Date:** 2026-03-22

---

## Summary

The GiljoAI Agent Template Manager evolves from a Claude Code-specific export system to a platform-neutral template system with format-aware export. The database stores one universal template per agent role. A server-side assembler formats templates into the correct output for each CLI tool at export time. The dashboard UI simplifies to one entry point for all agent templates, removing the "Generic" option and the platform-specific field gating.

---

## Core Principle: One Template, Multiple Export Targets

An agent template in GiljoAI defines **what** the agent is (role, expertise, personality, protocols). The CLI platform determines **how** that definition is formatted for consumption.

The user never creates "a Claude agent" or "a Codex agent." They create an **Implementer** agent with frontend specialization. When they export, the assembler formats it for their CLI of choice.

---

## Data Model

### What Does NOT Change

- **Template storage** — Templates remain in the existing database with the three-layer cache (Memory → Redis → DB)
- **Template resolution cascade** — Product-specific → Tenant-specific → System default → Legacy fallback
- **8-role active limit** — Enforced at the MCP server level. All CLI tools draw from the same pool
- **6 default templates** — orchestrator, analyzer, implementer, tester, reviewer, documenter
- **Role names** — These are GiljoAI orchestrator-facing identifiers. The orchestrator asks the server "what agents does the user want me to use?" and gets back these roles. The role names do NOT change per platform
- **Template fields** — Role, Custom Suffix, Description, Role and Expertise body

### What Changes

**Remove:** The "What tool are you building this agent for?" selector in the template creation UI.

Templates are now platform-neutral by default. Platform is an export-time concern, not a creation-time concern.

**Add:** A `color` field per role (if not already stored). This ensures consistent color identity across the dashboard UI and Claude Code exports. Colors are GiljoAI-defined, not user-configurable per-template.

**Add (optional):** A `platform_overrides` JSON field on the template model for storing per-platform customization that the user has explicitly set. This field is nullable and rarely used:

```json
{
  "claude_code": { "model": "opus", "permissionMode": "default" },
  "codex_cli": { "model": "gpt-5.2-codex", "reasoning_effort": "high" },
  "gemini_cli": { "model": "gemini-2.5-pro", "max_turns": 100 }
}
```

If `platform_overrides` is null (the common case), the export uses sensible defaults and the LLM asks the user at install time. If the user has set overrides via the dashboard, the export uses those and the LLM skips the question.

**Note:** The `platform_overrides` field is a convenience for power users who want a one-click export with no interactive prompts. It is NOT required. Most users will leave it empty and answer the model question at install time.

---

## The Assembler

The assembler is a server-side module that takes a platform-neutral template and produces a platform-specific output. It lives in the backend, not in slash command instructions.

### Assembler Responsibilities

| Responsibility | Detail |
|---|---|
| **Frontmatter generation** | Produce correct YAML (Claude/Gemini) or TOML (Codex) frontmatter from template fields |
| **Field mapping** | Map GiljoAI fields to each platform's schema. See mapping tables below |
| **Protocol injection** | Append GiljoAI operating protocols to the Role and Expertise body at export time. Protocols are separate from role identity (per Handover 0813/0825) |
| **Color embedding** | Include `color` in Claude Code frontmatter. Omit for Gemini/Codex (not supported) |
| **Name formatting** | Convert `{Role}_{CustomSuffix}` to platform-appropriate naming (lowercase-hyphenated for Claude/Gemini, snake_case or hyphenated for Codex) |
| **Default population** | Fill platform-specific fields with sensible defaults when no override exists |
| **Format validation** | Ensure output passes basic structural validation before serving to the client |

### Field Mapping: GiljoAI → Claude Code

| GiljoAI Field | Claude Code Frontmatter | Notes |
|---|---|---|
| `role` + `custom_suffix` | `name` | Formatted as `role-suffix` (lowercase, hyphenated) |
| `description` | `description` | Required. Verbatim from template |
| `platform_overrides.claude_code.model` or default | `model` | Default: `sonnet`. Can be overridden at install time |
| (hardcoded) | `tools` | `Read, Write, Glob, Grep, Bash, mcp__giljo-mcp__*` |
| `color` | `color` | Hex color from role definition. Claude-specific |
| `role_and_expertise` + protocols | Markdown body | Combined at export time |

### Field Mapping: GiljoAI → Gemini CLI

| GiljoAI Field | Gemini CLI Frontmatter | Notes |
|---|---|---|
| `role` + `custom_suffix` | `name` | Formatted as `role-suffix` (lowercase, hyphenated) |
| `description` | `description` | Required. Verbatim from template |
| (hardcoded) | `kind` | Always `agent` |
| `platform_overrides.gemini_cli.model` or default | `model` | Default: `gemini-2.5-pro` |
| `platform_overrides.gemini_cli.max_turns` or default | `max_turns` | Default: `50` |
| (hardcoded) | `tools` | YAML list: `[shell, read_file, write_file, mcp_*]` |
| `role_and_expertise` + protocols | Markdown body | Combined at export time |
| — | `color` | NOT supported. Omit |
| — | `timeout_mins` | Optional. Not set by default |

### Field Mapping: GiljoAI → Codex CLI

Codex requires TWO outputs per agent:

**Agent file (`~/.codex/agents/{name}.toml`):**

| GiljoAI Field | Codex TOML Field | Notes |
|---|---|---|
| `platform_overrides.codex_cli.model` or default | `model` | Default: `gpt-5.2-codex` |
| `platform_overrides.codex_cli.reasoning_effort` or default | `model_reasoning_effort` | Default: `medium` |
| `role_and_expertise` + protocols | `developer_instructions` | Multi-line TOML string (`"""..."""`) |

**Config entry (merged into `~/.codex/config.toml`):**

| GiljoAI Field | Codex config.toml Field | Notes |
|---|---|---|
| `role` + `custom_suffix` | `[agents.{name}]` section key | Formatted as `role-suffix` (hyphenated) |
| `description` | `description` | Required. Verbatim from template |
| (generated) | `config_file` | Path to the agent's .toml file |
| `role` | `nickname_candidates` | Array with display name: `["Implementer"]` |

---

## Dashboard UI Changes

### Template Creation / Edit Flow (Simplified)

**Before (current):**
1. Select tool (Claude Code / Codex CLI / Gemini CLI / Generic)
2. Tool selection gates which fields appear
3. Pick Role
4. Optional: Custom Suffix
5. Model dropdown (Claude only)
6. Description
7. Role and Expertise (Monaco editor)

**After:**
1. Pick Role (from the 8 available types)
2. Optional: Custom Suffix
3. Description (required — now used by all platforms)
4. Role and Expertise (Monaco editor)
5. **New section (collapsed by default): "Platform Export Preferences"**
   - Claude Code: model preference, permissionMode
   - Codex CLI: model preference, reasoning effort
   - Gemini CLI: model preference, max_turns
   - All fields optional. If unset, defaults are used at export time or the LLM asks

The tool selector goes away from template creation. The platform export preferences section is a power-user feature — most users will skip it entirely and answer the model question when they run `/gil_get_agents`.

### Integrations Page Changes

**Before:** Single "Export Agents" button targeting Claude Code only.

**After:** The Integrations page shows export options per-platform:

- **Claude Code** — [Copy Command] [Manual Download] (same ZIP flow as today)
- **Codex CLI** — [Copy Command] (triggers `/gil_get_agents` skill with structured data)
- **Gemini CLI** — [Copy Command] [Manual Download] (ZIP flow, same pattern as Claude)

Each "Copy Command" button generates the appropriate slash command / skill invocation with a tokenized download URL.

The Manual Download option generates a ZIP containing pre-assembled agent files plus an `agent_instructions.md` with platform-specific installation steps.

---

## The 8-Role Limit

### Enforcement

- The MCP server enforces a maximum of **8 active agent role types** across the tenant
- This limit applies to the total number of roles, not per-platform
- If a user has 8 active roles and exports for Claude Code, those same 8 roles are what exports for Codex or Gemini
- The orchestrator's `get_available_agents` call returns these same 8 roles regardless of which CLI tool is asking
- The limit exists to protect context budgets: each agent's template description consumes tokens when loaded into the CLI tool's context at startup

### Why Not Per-Platform Limits?

The roles are the same roles doing the same jobs. An Implementer is an Implementer whether it runs as a Claude Code subagent or a Codex worker. Platform is a formatting concern. Doubling the limit for multi-platform users would defeat the context budget protection.

### SaaS Consideration

The 8-role limit is a CE default. SaaS edition may raise this limit for teams with larger context budgets or newer models with expanded context windows. This is a configuration change, not an architectural one.

---

## Protocol Injection at Export Time

Per Handover 0813 and 0825, agent identity (Role and Expertise) is separated from GiljoAI operating protocols in the data model. At export time, the assembler combines them:

```
[Agent Identity — from Role and Expertise field]
You are a senior frontend implementer specializing in Vue 3 and Vuetify...

[GiljoAI Operating Protocols — injected by assembler]
## GiljoAI MCP Communication Protocol
- Check for messages regularly via receive_messages()
- Report progress at 25%, 50%, 75%, 100% via update_job_progress()
- All work must be committed and reported before marking complete
...
```

The protocols are maintained separately and updated globally. Role identity is user-customizable per template. The assembler merges them at export. This ensures protocol updates don't require re-editing every agent template.

Platform-specific protocol variations:
- **Claude Code:** Protocols reference `mcp__giljo-mcp__` tool naming convention
- **Codex CLI:** Protocols reference MCP tools by their Codex naming convention (verify at implementation time)
- **Gemini CLI:** Protocols reference MCP tools by Gemini's qualified naming (e.g., `giljo-mcp_tool_name`)

The assembler handles this naming translation.

---

## Generic Template Mode: Disposition

The "Generic" option in the current tool selector is removed from the template creation UI.

The Generic template's function (multi-terminal mode where each terminal fetches its mission at runtime via `get_agent_mission`) is unaffected. That mode uses the `get_generic_agent_template` MCP tool at runtime, not the exported agent files. It doesn't need a template "type" in the UI — it's an execution mode, not a template format.

To be explicit: exported agent templates (`/gil_get_agents`) are for **subagent mode** where the CLI tool spawns agents from pre-installed definitions. The multi-terminal mode where agents fetch missions at runtime works with the generic template endpoint and does not use exported agent files.

---

## Implementation Sequence

### Phase 1: Backend Assembler (Pre-CE or Sprint 1)

1. Create `AgentTemplateAssembler` class with `assemble(template, platform)` method
2. Implement Claude Code formatter (closest to current export — lowest risk)
3. Implement Gemini CLI formatter
4. Implement Codex CLI structured data formatter (returns JSON, not files)
5. Add `get_agent_templates_for_export` MCP endpoint
6. Add protocol injection with platform-specific MCP tool name translation
7. Unit tests for all three formatters against known-good format specs

### Phase 2: Slash Commands and Skills (Sprint 1)

1. Create Claude Code `/gil_get_agents` slash command (rename + model prompt)
2. Create Gemini CLI `/gil_get_agents.toml` custom command
3. Create Codex CLI `gil-get-agents/SKILL.md` skill
4. Deprecation alias for `/gil_get_claude_agents`
5. Integration testing: verify full flow from MCP → CLI for each platform

### Phase 3: Dashboard UI (Sprint 1-2)

1. Remove tool selector from template creation/edit
2. Ensure `description` field is required (no longer Claude-only)
3. Add collapsed "Platform Export Preferences" section
4. Update Integrations page with per-platform export buttons
5. Keep existing Claude Code export flow as-is for backward compatibility

### Phase 4: Codex Validation (Sprint 2)

1. Test Codex CLI subagent spawning with GiljoAI-generated `.toml` files
2. Validate `config.toml` merge behavior in various user configurations
3. Verify MCP tool inheritance in Codex subagents
4. Document any Codex-specific constraints or workarounds

### Phase 5: Gemini Validation (Sprint 2-3)

1. Test Gemini CLI subagent delegation with GiljoAI-generated `.md` files
2. Track parallel execution feature progress on Gemini's roadmap
3. Validate MCP tool naming in Gemini subagent context
4. Document sequential execution limitation and expected timeline for parallel support

---

## Open Items and Risks

| Item | Risk | Mitigation |
|---|---|---|
| Codex `config.toml` merge complexity | High — LLM must modify a config file it didn't create | Show diff before writing. Provide rollback instructions. Test with various config states |
| Gemini parallel execution not shipped | Medium — Agents work but run sequentially | Document limitation. Export works regardless; parallel is a performance feature |
| Platform format schema drift | Medium — All three CLIs are evolving rapidly | The assembler centralizes format knowledge. When schemas change, update one module, not three sets of slash command instructions |
| MCP tool naming varies per platform | Low-Medium — Each CLI names MCP tools differently | Assembler handles name translation. Verify conventions at implementation time with each CLI's docs |
| `platform_overrides` field adoption | Low — Power user feature, most users skip it | Field is nullable. Dashboard section is collapsed by default. Zero impact if unused |

---

## References

- `AGENT_EXPORT_EVOLUTION.md` — Companion doc: the `/gil_get_agents` command specification
- `Subagent_CLLItool_maturity.md` — Authoritative multi-platform format comparison (in project knowledge)
- `Simple_Vision.md` — Agent template architecture, 8-role limit, export flow
- `SERVER_ARCHITECTURE_TECH_STACK.md` — Execution modes (Claude Code CLI vs Multi-Terminal Generic)
- Handover 0813 — Agent Template Context Separation (role identity vs protocols)
- Handover 0825 — Agent Identity Separation from Mission Response
- Handover 0041 — Agent Template Database Integration
- Handover 0102 — Agent Template Export System (token-based download)
