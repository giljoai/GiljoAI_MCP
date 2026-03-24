# Multi-CLI Agent Integration Analysis

**Status:** Active analysis, pre-implementation
**Edition Scope:** CE
**Related:** `Subagent_CLLItool_maturity.md` (companion audit)

---

## 1. Current State

### 1.1 Execution Modes Today

Two radio buttons on the staging interface:

| Mode | UI Behavior | How It Works |
|---|---|---|
| `claude_code_cli` | Single play button next to orchestrator | Orchestrator prompt says "you have these agents, use Task tool to spawn them." Agent templates pre-installed in `.claude/agents/`. One terminal. |
| `multi_terminal_generic` | Play/copy button per agent | Each agent gets its own terminal. User pastes prompt. Agent connects to MCP, fetches mission, works independently. CLI-agnostic. |

The "mode" is really a **prompt framing strategy + UI behavior toggle**, not a different orchestration engine. In both modes, the GiljoAI MCP server is the brain. The AI coding agent is just the runtime.

### 1.2 Agent Template Structure (Claude Code Export)

Exported `.claude/agents/*.md` files use YAML frontmatter + markdown body. Examining all 5 exported agent templates (implementer, reviewer, analyzer, tester, documenter), the content breaks down:

| Section | Content Type | Identical across all agents? |
|---|---|---|
| YAML frontmatter (`name`, `description`, `model`, `color`) | Role identity | No -- unique per agent |
| `## Technical Environment` | GiljoAI protocol | Yes |
| `## Agent Guidelines` | GiljoAI protocol | Yes |
| `## If Blocked or Unclear` | GiljoAI protocol | Yes |
| `## MCP Tool Usage` | GiljoAI protocol | Yes |
| `### REQUESTING BROADER CONTEXT` | GiljoAI protocol | Yes |
| `## CHECK-IN PROTOCOL` | GiljoAI protocol | Yes |
| `## MESSAGING` | GiljoAI protocol | Yes |
| `## Behavioral Rules` (4 bullets) | Role identity | No -- unique per agent |
| `## Success Criteria` (4 bullets) | Role identity | No -- unique per agent |

**Result: ~85% protocol boilerplate, ~15% role identity.** Out of ~108 lines per file, only ~18 lines are role-specific.

### 1.3 Protocol Double-Injection

Protocols are injected into agents from **two separate sources**:

1. **Baked into the `.md` template** -- Claude Code loads this as the subagent's system instructions at spawn time. Contains MCP tool usage, check-in protocol, messaging prefixes, blocker escalation, context requesting.

2. **Fetched via `get_agent_mission()` -> `full_protocol`** -- The server-side `_generate_agent_protocol()` in `protocol_builder.py` generates a comprehensive 5-phase lifecycle protocol returned as `full_protocol`.

The templates even acknowledge this duplication -- the CHECK-IN and MESSAGING sections contain "Full protocol in `full_protocol` from `get_agent_mission()`", meaning the template says "here's a summary, the real version is elsewhere."

### 1.4 The `user_instructions` Export Gap

The `AgentTemplate` DB model has a dual-field system (Handover 0106):

- **`system_instructions`** -- Protected, non-editable by users. Contains MCP protocol sections. This is what gets exported to `.md` files.
- **`user_instructions`** -- Editable by users. Contains role-specific prose ("You are an implementation specialist..."). **This is NOT exported** to `.md` files.

The `template_renderer.render_claude_agent()` function only puts `system_instructions` into the markdown body. The only role-specific content that reaches the `.md` files are `behavioral_rules` and `success_criteria` (short JSON lists rendered as bullet points).

This means the role prose that users can edit in the UI never makes it into the exported agent definitions.

### 1.5 Export Pipeline Architecture

There are three export paths, all producing `.claude/agents/*.md`:

| Path | Endpoint | Renderer | Notes |
|---|---|---|---|
| ZIP download | `GET /api/download/agent-templates.zip` | `template_renderer.render_claude_agent()` | Primary path. Max 8 templates. |
| Filesystem export | `POST /api/export/claude-code` | Inline composition (own frontmatter fn) | Writes directly to disk. Has its own `generate_yaml_frontmatter()`. |
| Token download | `POST /api/download/generate-token` | `template_renderer.render_claude_agent()` | Via `FileStaging.stage_agent_templates()`. |

All paths exclude orchestrator templates (`SYSTEM_MANAGED_ROLES`).

### 1.6 Server-Side Protocol Architecture

The orchestrator and agents receive protocols from different server-side sources:

**Orchestrator** (via `get_orchestrator_instructions()`):
- 5-chapter protocol from `protocol_builder._build_orchestrator_protocol()` (mission, startup, spawning rules, error handling, reference)
- Orchestrator identity from `template_seeder.get_orchestrator_identity_content()`
- Context fetch instructions from `mission_planner._build_fetch_instructions()`

**Agents** (via `get_agent_mission()`):
- Team context header from `protocol_builder._generate_team_context_header()` (identity, team roster, dependencies, coordination)
- 5-phase lifecycle protocol from `protocol_builder._generate_agent_protocol()` (startup, execution, progress, completion, error handling)
- Mission text (work order from orchestrator, optionally wrapped with template expertise in multi-terminal mode)

---

## 2. Key Finding: The Separation Already Exists But Is Leaky

The DB has the right separation: `system_instructions` (protocols) vs `user_instructions` (role). But the architecture leaks in both directions:

1. **Protocols leak INTO the template export** -- `system_instructions` (all protocol) is the body of the exported `.md` file, making templates 85% boilerplate
2. **Role identity leaks OUT OF the export** -- `user_instructions` (the actual role prose) is not exported, so the agent's role identity in the `.md` file comes only from `behavioral_rules` and `success_criteria` bullet lists
3. **Protocols are delivered TWICE** -- once in the `.md` template (pre-loaded at spawn) and once in `full_protocol` (fetched on turn 1)

### Implications for Multi-Platform Export

If we export to Codex TOML or Gemini MD today, we'd be replicating 90 lines of GiljoAI-specific protocol into each platform's format. Any protocol update would require re-generating exports across all formats.

If we fix the separation first, templates become ~20-30 lines of role identity, trivially portable across CLI formats. The protocol is delivered once, server-side, via `get_agent_mission()` -- platform-agnostic.

---

## 3. Three-Context Architecture (Recommended)

Three distinct concerns need clean homes:

| Context | What It Contains | Where It Should Live | Why |
|---|---|---|---|
| **Role Identity** | WHO -- expertise, behavioral rules, success criteria, role prose | Template file (`.md` / `.toml`) | Static per agent type. User-customizable. Portable across CLI formats. |
| **Operating Protocols** | HOW -- 5-phase lifecycle, MCP tool usage, messaging, check-ins, blocker escalation | `get_agent_mission()` -> `full_protocol` | Already exists server-side in `protocol_builder.py`. Single source of truth. Changes propagate without re-export. |
| **Work Order** | WHAT -- team context, assigned tasks, dependencies, job-specific instructions | `get_agent_mission()` -> `mission` | Fully dynamic per project/mission. |

### What a Cleaned-Up Template Looks Like

```yaml
---
name: implementer
description: Implementation specialist for writing production-grade code
model: sonnet
color: blue
---

You are an implementation specialist. You write production-grade code
following project coding standards with cross-platform compatibility.

## Behavioral Rules
- Follow project coding standards
- Ensure cross-platform compatibility
- Never hardcode paths
- Use pathlib for file operations

## Success Criteria
- Passes all linting checks
- Matches specification
- No breaking changes
- Proper error handling
```

Plus a lightweight bootstrap section (~5 lines) telling the agent it's part of a GiljoAI MCP system and to call `get_agent_mission()` on startup.

The agent can already see MCP tools in its tool list on AI coding agent load. It doesn't need 90 lines explaining MCP tool usage, messaging prefixes, and context requesting protocols. Those come from `full_protocol` on turn 1.

### Why Protocols Belong in the Fetch, Not the Template

1. `protocol_builder._generate_agent_protocol()` already generates the complete 5-phase lifecycle -- having it also in the template is duplication
2. Protocol updates propagate instantly without re-exporting templates
3. Templates stay small and portable across AI coding agents
4. Users editing templates can't accidentally break the protocol contract
5. The counter-argument ("system prompt = stronger behavioral influence") is valid but low-risk: the agent calls `get_agent_mission()` on turn 1, before any real work -- instructions received that early are followed with near-system-prompt fidelity

---

## 4. Multi-Platform Strategy

### 4.1 Execution Mode Vision

Four radio buttons on the staging interface:

| Mode | Spawn Mechanism | Template Format | Terminal UX |
|---|---|---|---|
| Multi-terminal | Manual paste per agent | N/A (prompt includes everything) | Button per agent |
| Claude Code subagents | `Task` tool (model-invoked) | `.claude/agents/*.md` (YAML frontmatter) | Single orchestrator button |
| Codex CLI subagents | `spawn_agent` tool (model-invoked) | `config.toml` + `*.toml` per role | Single orchestrator button |
| Gemini CLI subagents | `delegate_to_agent` tool (model-invoked) | `.gemini/agents/*.md` (YAML frontmatter) | Single orchestrator button |

All single-terminal modes follow the same recipe: pre-install agent definitions in the CLI's native format, then frame the orchestrator prompt to use the CLI's native spawn mechanism.

### 4.2 Template Export per Platform

| Platform | Format | Mapping | Effort |
|---|---|---|---|
| Claude Code | MD + YAML frontmatter (`name`, `description`, `model`, `color`, `tools`) | Direct -- already exists | Done |
| Gemini CLI | MD + YAML frontmatter (`name`, `description`, `model`, `max_turns`, `timeout_mins`) | Close to Claude -- different frontmatter schema | Low (4-8 hrs) |
| Codex CLI | TOML (`[agents.<role>]` block + separate `<role>.toml` with `developer_instructions`) | Fundamentally different format, lossy mapping | Medium (12-16 hrs) |

With the three-context separation, all exports become: "take role identity from DB, format frontmatter for target platform, add lightweight bootstrap, done." The 90 lines of protocol are no longer in the export.

### 4.3 Full Bake vs Thin Shell + Fetch

Two approaches for how much goes into the template file:

| Approach | Template Contains | Agent Fetches | Tradeoffs |
|---|---|---|---|
| **Full Bake** | Role + protocols + everything | Only job/work order | No cold-start, works if MCP hiccups at spawn. But stale if user edits templates mid-session. |
| **Thin Shell + Fetch** | Role + bootstrap only | Protocols + job/work order | Always current, tiny templates, portable. But costs tokens for fetch on turn 1. |

**Recommendation: Thin Shell + Fetch** (with role baked in). This is actually what the thin prompt architecture already does -- `spawn_agent_job()` returns a minimal prompt saying "call `get_agent_mission()`". The `.md` template provides role identity, the fetch provides protocols and work order.

### 4.4 Orchestrator Prompt Framing per AI Coding Agent

The orchestrator needs different framing based on execution mode:

| Mode | Key Framing Instruction |
|---|---|
| Claude Code | "You have these agents available via Task tool: [list]. Use `subagent_type` to spawn them." |
| Codex CLI | "You have these agent roles defined in config.toml: [list]. Use `spawn_agent` with role names to spawn them." |
| Gemini CLI | "You have these agents available as delegatable tools: [list]. Use `delegate_to_agent` to spawn them." |
| Multi-terminal | "Agents will be launched manually in separate terminals. Create jobs via `spawn_agent_job()` and provide the thin prompt to the user." |

---

## 5. Implementation Approach

### Phase 1: Protocol Separation (Claude Code only)

Fix the current system before expanding to other platforms:

1. **Move protocol content out of `system_instructions`** -- Keep `system_instructions` for a lightweight MCP bootstrap (~5 lines: "you're in a GiljoAI system, call `get_agent_mission()`")
2. **Include `user_instructions` in the export** -- Fix `render_claude_agent()` to compose: frontmatter + user_instructions (role prose) + behavioral_rules + success_criteria + bootstrap
3. **Update `template_seeder`** -- Rebuild default templates with protocols removed from `system_instructions`
4. **Update `refresh_tenant_template_instructions()`** -- New version regenerates the slimmed-down `system_instructions`
5. **Test with Claude Code** -- Verify agents still receive and follow protocols via `full_protocol` from `get_agent_mission()`

### Phase 2: Multi-Platform Export

After Phase 1 validates with Claude Code:

1. Add Gemini `.md` renderer (different frontmatter schema, same role body)
2. Add Codex TOML renderer (config.toml block + per-role .toml generation)
3. Add mode radio buttons to staging UI
4. Add orchestrator prompt framing per mode
5. Update export UI with per-platform tabs/options

### Phase 3: Orchestrator Framing

1. Build orchestrator prompt framing variants per AI coding agent
2. Wire mode selection to prompt generation in `thin_prompt_generator.py`
3. Test end-to-end with each AI coding agent

---

## 6. Open Questions

1. **User base composition** -- How many early CE users will be Codex-primary vs Claude-primary vs Gemini-primary? Drives urgency.
2. **CE launch timing** -- Should multi-CLI support be a CE launch differentiator or a post-launch sprint?
3. **Codex CSV batch mode** -- Could the orchestrator generate a CSV as an alternative execution path? (v2 consideration)
4. **Export UI design** -- Tabs per AI coding agent? Dropdown? Affects Integration page layout.
5. **Protocol fidelity testing** -- How well do Codex/Gemini subagents follow dense protocol instructions received via fetch vs baked-in? Needs empirical testing.

---

## Appendix: Platform Comparison Summary

(Full details in `Subagent_CLLItool_maturity.md`)

| Capability | Codex CLI (v0.110.0) | Gemini CLI (v0.32.1) | Claude Code (~v2.1.33+) |
|---|---|---|---|
| Config format | TOML | JSON + MD/YAML | MD/YAML |
| Parallel execution | Yes (max_threads=6) | No (blocking only) | Yes (no documented limit) |
| Built-in agents | explorer, monitor | codebase_investigator, cli_help, generalist, browser | None (user-defined only) |
| MCP inheritance | Full; no per-agent filtering | Full; qualified names | Full; per-agent tool lists |
| Agent isolation | Sandbox inheritance | YOLO mode | Git worktree option |
| Remote agents | No | A2A protocol | No |
| Persistent memory | No | No | `memory` field |
| Maturity | Experimental | Experimental | Stable (subagents) |
