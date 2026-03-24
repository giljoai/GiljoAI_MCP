# Multi-agent capabilities across AI coding agents: a primary-source audit

**All three major AI coding agents — OpenAI Codex CLI, Google Gemini CLI, and Anthropic Claude Code — now ship native subagent systems, but they differ dramatically in maturity, architecture, and configuration approach.** Codex CLI offers the most complete orchestration toolkit with CSV-based batch spawning and configurable concurrency. Claude Code provides the cleanest agent definition format with the richest per-agent customization. Gemini CLI has the broadest built-in agent roster but still lacks parallel execution. Every system marks its multi-agent features as experimental. This report validates each claim against official GitHub repositories and documentation sites only.

---

## Codex CLI ships the most powerful orchestration primitives

OpenAI's Codex CLI (latest stable **v0.110.0**, March 5, 2026; alpha v0.112.0 in prerelease) implements multi-agent collaboration through a set of internal tool calls the model can invoke: **`spawn_agent`, `send_input`, `resume_agent`, `wait`, `close_agent`**, and `spawn_agents_on_csv`. These are collectively called "collab tools" and are gated behind the **`multi_agent` feature flag**, which must be explicitly enabled either through `/experimental` in the TUI or by adding `multi_agent = true` under `[features]` in `~/.codex/config.toml`.

Agent roles are defined directly in config.toml using TOML table syntax. The full configuration surface, confirmed from the official sample config and config reference at developers.openai.com, is:

```toml
[agents]
max_threads = 6              # Max concurrent agent threads (default: 6)
max_depth = 1                # Max nesting depth, root = 0 (default: 1)
job_max_runtime_seconds = 1800  # Per-worker timeout for CSV jobs

[agents.reviewer]
description = "Find correctness, security, and test risks in code."
config_file = "./agents/reviewer.toml"   # Relative to config.toml
nickname_candidates = ["Athena", "Ada"]  # Display names for spawned agents
```

Each role's `config_file` points to a separate TOML file that can override **model**, **model_reasoning_effort**, **developer_instructions**, sandbox settings, and other config keys. The official docs state: "The agent inherits any configuration that the role doesn't set from the parent session." Codex rejects unknown fields in `[agents.<name>]`, enforcing a strict schema.

The official docs confirm two built-in roles: **explorer** (read-only codebase exploration, referenced since v0.92.0) and **monitor** (tuned for long-running polling workflows with wait windows up to 1 hour). The docs explicitly state: "For long-running commands or polling workflows, Codex can also use the built-in monitor role." Roles named "default" or "worker" were not found as named built-in roles in any primary source, though users can define arbitrary custom roles.

**`spawn_agents_on_csv`** is a distinct batch-processing tool that implements map-reduce style workflows. It takes `csv_path`, `id_column`, `instruction` (with `{column}` template variables), `output_csv_path`, and `output_schema` parameters. It spawns one sub-agent per CSV row, each of which must call `report_agent_job_result` exactly once. Failed workers are marked with errors in the exported CSV. The progress bar with ETA is shown on stderr during `codex exec` runs.

For MCP inheritance, subagents inherit the parent session's live turn state including provider, approval policy, sandbox, and working directory. The v0.99.0 release explicitly added "connector capabilities to sub-agents." However, **per-agent MCP server binding does not exist** — open issues #12047 and #12460 propose this as a feature request. Subagents inherit the parent's sandbox policy but run with **non-interactive approvals**; if a sub-agent attempts an action requiring new approval, that action fails and the error surfaces to the parent.

The **`/agent`** slash command (added in v0.110.0) lets users switch between active agent threads and inspect ongoing work. A `/multiagent` alias also exists.

## Gemini CLI has the widest built-in agent roster but no parallel execution

Google's Gemini CLI (latest stable **v0.32.1**, March 2026; preview v0.33.0) implements subagents as first-class tools through a `DelegateToAgentTool` that exposes each registered agent as a callable tool. The feature is documented at geminicli.com/docs/core/subagents/ with the 🔬 experimental marker. Custom subagents require explicit opt-in via `settings.json`:

```json
{
  "experimental": { "enableAgents": true }
}
```

Gemini CLI ships **four built-in subagents**, each implemented in TypeScript within the core package:

- **`codebase_investigator`** — Deep codebase analysis and reverse engineering. Enabled by default. Configurable model, max turns (default 20), and thinking budget via `experimental.codebaseInvestigatorSettings` in settings.json.
- **`cli_help`** — Expert knowledge about Gemini CLI commands and configuration. Enabled by default.
- **`generalist_agent`** — An "exact copy of the main agent" that inherits all tools and model settings, used for task routing. Enabled by default since v0.32.0.
- **`browser_agent`** — Experimental web automation using Chrome's accessibility tree via `chrome-devtools-mcp`. Disabled by default; requires Chrome 144+ and explicit enablement in `agents.overrides.browser_agent.enabled`.

No `docs_expert` built-in subagent was found in any primary source.

Custom agents use **Markdown files with YAML frontmatter** placed in `.gemini/agents/*.md` (project-level) or `~/.gemini/agents/*.md` (user-level). The confirmed schema from official documentation:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique slug used as tool name (lowercase, hyphens, underscores) |
| `description` | string | Yes | Visible to main agent for routing decisions |
| `kind` | string | No | `local` (default) or `remote` |
| `tools` | array | No | Restricted tool list; defaults inherit from parent |
| `model` | string | No | e.g. `gemini-2.5-pro`; defaults to `inherit` |
| `temperature` | number | No | 0.0–2.0 |
| `max_turns` | number | No | Default: 15 |
| `timeout_mins` | number | No | Default: 5 |

**Parallel execution does not exist natively.** The official SubAgent issue (#3132) explicitly states the system is "intended to be blocking, in that the calling thread blocks until SubAgent execution is finished." Issue #19430 (Agent Teams feature request) confirms: "no true parallel work." However, the v0.33.0-preview changelog includes a PR for "concurrency safety guidance for subagent delegation," and the system prompt instructs agents to run multiple read-only subagents in parallel when tasks are independent — suggesting the infrastructure is being prepared but not yet shipped.

Subagents operate in **"YOLO mode"** — they execute tools without individual user confirmation. This is an explicit warning in the official docs. MCP tool integration exists but has required multiple bug fixes: subagents must use **qualified/prefixed MCP tool names** (e.g., `ServerName__tool_name`), and PRs #20801 and #21425 addressed naming inconsistencies.

The **A2A (Agent-to-Agent) protocol** enables Gemini CLI to delegate to remote AI agents discovered via `.well-known/agent.json`. The A2A client is integrated into the agent registry, with recent work adding HTTP authentication and authenticated agent card discovery. An official RFC (Discussion #7822) proposes standardizing on A2A as the protocol for all Gemini CLI integrations, noting it is "under the Linux Foundation" as an industry standard.

## Claude Code offers the most refined per-agent customization

Anthropic's Claude Code CLI uses the **Agent tool** (renamed from "Task"; the old name still works as an alias) to spawn subagents. The tool accepts these parameters, confirmed from the SDK TypeScript reference at docs.anthropic.com:

- **`description`** (required) — Task description
- **`prompt`** (required) — Instructions for the subagent
- **`subagent_type`** (required) — Identifies which agent definition to use
- **`model`** — `"sonnet"`, `"opus"`, or `"haiku"`
- **`run_in_background`** — Boolean for background execution
- **`max_turns`** — Turn limit
- **`name`** — Display name
- **`team_name`** — For Agent Teams coordination
- **`mode`** — `"acceptEdits"`, `"bypassPermissions"`, `"default"`, `"dontAsk"`, `"plan"`
- **`isolation`** — `"worktree"` for git worktree isolation
- **`resume`** — Resume a previous subagent session

Agent definitions use **Markdown with YAML frontmatter** in `.claude/agents/*.md` (project) or `~/.claude/agents/*.md` (user). The frontmatter fields are the richest of the three platforms:

```yaml
---
name: your-sub-agent-name        # Required
description: When to use this    # Required
tools: Read, Glob, Grep          # Optional comma-separated; inherits all if omitted
model: sonnet                    # Optional (sonnet/opus/haiku)
permissionMode: default          # Optional
isolation: worktree              # Optional - git worktree isolation
background: true                 # Optional - always background
skills:                          # Optional - inject skill content
  - api-conventions
memory: <directory>              # Optional - persistent knowledge across sessions
---
System prompt in Markdown body.
```

Two features distinguish Claude Code. First, the **`skills`** and **`memory`** fields allow subagents to carry persistent knowledge and reusable instruction bundles — neither Codex nor Gemini offer this. Second, the **`isolation: worktree`** option runs each subagent in a temporary git worktree, providing true filesystem isolation that goes beyond sandbox policy inheritance.

MCP tools are fully inherited: "When the tools field is omitted, subagents inherit all MCP tools available to the main thread." When tools are explicitly listed, MCP tools can be included by name. A critical constraint: **subagents cannot spawn other subagents** — the Agent tool inside subagent definitions has no effect, enforcing a flat hierarchy.

**No hard-coded maximum concurrent subagent limit** appears in official documentation. GitHub issues reference users running 7–10 concurrent subagents, with practical limits set by API rate limits and resource usage rather than a software cap.

The **Agent Teams** feature is a separate, more powerful coordination system requiring `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Where subagents work within a single session, agent teams coordinate across **separate Claude instances**, each with independent context windows, communicating via a mailbox system. Teams spawn via **tmux** (or iTerm2 split panes) and consume approximately **7× more tokens** than standard sessions. The changelog records fixes for teammates failing on Bedrock/Vertex/Foundry due to environment variable propagation issues.

## How the three platforms compare head-to-head

| Capability | Codex CLI | Gemini CLI | Claude Code |
|---|---|---|---|
| **Config format** | TOML (`config.toml` + per-role `.toml`) | JSON (`settings.json`) + MD/YAML (`.gemini/agents/*.md`) | MD/YAML (`.claude/agents/*.md`) |
| **Agent definition** | `[agents.<name>]` in config.toml | Markdown + YAML frontmatter | Markdown + YAML frontmatter |
| **Spawn mechanism** | Model tool calls (`spawn_agent`) | Model tool call (`delegate_to_agent`) | Model tool call (Agent/Task) |
| **Parallel execution** | **Yes** — `max_threads` default 6 | **No** — blocking only | **Yes** — no documented limit |
| **Batch processing** | **`spawn_agents_on_csv`** with progress bar | Not available | Not available |
| **Built-in agents** | explorer, monitor | codebase_investigator, cli_help, generalist, browser | None (user-defined only) |
| **MCP inheritance** | Full inheritance; no per-agent filtering | Full inheritance; qualified names required | Full inheritance; per-agent tool lists supported |
| **Nesting depth** | Configurable (`max_depth`, default 1) | Single level (blocking) | Flat only (subagents can't spawn subagents) |
| **Agent isolation** | Sandbox policy inheritance + role overrides | YOLO mode (no per-step confirmation) | Git worktree isolation option |
| **Remote agents** | Not available natively | **A2A protocol** (Linux Foundation standard) | Not available natively |
| **Persistent memory** | Not available | Not available | **`memory` field** for cross-session knowledge |
| **Feature flag** | `multi_agent = true` | `experimental.enableAgents = true` | Always available (Teams: env var) |
| **Latest version** | v0.110.0 (March 5, 2026) | v0.32.1 (March 2026) | ~v2.1.33+ |
| **Maturity** | Experimental | Experimental | Stable (subagents); Research Preview (Teams) |

The configuration portability story is poor. Codex's TOML-based role definitions with separate config file layering are fundamentally incompatible with the Markdown+YAML frontmatter approach shared by Gemini and Claude Code. Even between Gemini and Claude Code, the frontmatter schemas differ: Gemini uses `kind`, `temperature`, `max_turns`, and `timeout_mins` while Claude Code uses `permissionMode`, `isolation`, `background`, `skills`, and `memory`. No cross-tool agent definition standard exists.

## The real differentiators are orchestration depth and safety models

Codex CLI's **`spawn_agents_on_csv`** is unique among the three platforms and represents the most sophisticated batch orchestration primitive. It turns Codex into a map-reduce engine where each CSV row becomes an independent worker with structured result reporting. Combined with configurable `max_threads` (up to the user's chosen limit, default 6), `max_depth` for nesting control, and `job_max_runtime_seconds` timeouts, Codex provides the most production-ready multi-agent infrastructure.

Gemini CLI's **A2A protocol** is the only platform offering federated, remote agent delegation — a fundamentally different architecture that connects to external AI agents via HTTP rather than spawning local processes. This positions Gemini CLI uniquely for distributed agent ecosystems, though the feature is experimental and still receiving authentication and streaming fixes.

Claude Code's **safety model is the most granular**. The `tools` field in agent definitions enables precise tool whitelisting per subagent — something neither Codex nor Gemini currently supports (both are full-inheritance with no per-agent filtering, though Codex has this as an open feature request). The `permissionMode` override, combined with the rule that `bypassPermissions` always takes priority from parent, creates a clear security hierarchy. The flat-only spawning constraint (subagents cannot create subagents) is also a deliberate safety decision that neither competitor enforces.

All three platforms are iterating rapidly on their multi-agent systems. Codex has shipped multi-agent changes in every release from v0.92.0 through v0.110.0 (January–March 2026). Gemini CLI added the generalist agent, concurrency guidance, and MCP tool naming fixes in its v0.32.x series. Claude Code continues refining Agent Teams alongside subagent improvements. The space is moving fast enough that any comparison will need updating within weeks.

## Conclusion

The three AI coding agents have converged on remarkably similar high-level architectures — model-invoked tool calls that spawn child agents with inherited context — while diverging significantly in implementation details. **Codex CLI leads in orchestration power** with CSV batch processing, configurable concurrency, and the deepest configuration surface. **Claude Code leads in per-agent customization and safety** with tool whitelisting, worktree isolation, persistent memory, and skill injection. **Gemini CLI leads in ecosystem connectivity** through A2A remote agents and ships the most useful built-in agents out of the box, but remains the only platform without native parallel execution. None of these systems have stabilized beyond experimental status, and cross-tool agent definition portability does not exist. Teams building multi-agent workflows today should expect breaking changes across all three platforms.