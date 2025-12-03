# Codex Subagent Communication — Authoritative Breakdown

This guide synthesizes OpenAI’s Codex CLI documentation to explain the practical ways Codex communicates with “subagents” and how to integrate it into multi‑agent systems. Sources referenced below are all from the official `openai/codex` repository.

## Scope & Sources

- Repo overview and docs index: openai/codex: README.md (Model Context Protocol, config, exec)
- AGENTS.md discovery and precedence: docs/agents_md.md
- MCP server mode and Agents SDK integration: docs/advanced.md#mcp-server
- Non‑interactive runs and JSONL event stream: docs/exec.md
- MCP client configuration (connecting external tools/agents): docs/config.md (mcp_servers)

## Mental Model

Codex itself is a single agent runtime that can participate in multi‑agent systems in three primary ways:

1) Codex as a Subagent (MCP server mode)
- Run Codex as a Model Context Protocol server using `codex mcp-server`.
- An external orchestrator (e.g., OpenAI Agents SDK) treats Codex like a tool/agent it can message.
- Communication occurs via MCP tool calls: start a new conversation with the `codex` tool and continue it with `codex-reply` using the returned `conversationId`.
- Reference: docs/advanced.md#mcp-server

2) Codex calling Subagents (MCP client mode)
- Codex, when running interactively or via `codex exec`, can connect to external MCP servers that expose tools. Those servers can themselves be agents (i.e., “subagents”) surfaced as tools.
- Communication occurs through MCP tool invocations. Codex emits `mcp_tool_call` events (see JSONL below) when it calls tools on configured MCP servers.
- Configure these under `mcp_servers.<id>` in `~/.codex/config.toml`.
- Reference: docs/config.md#mcp-integration, docs/exec.md (event types)

3) Codex runs as Process‑Level Subagents (codex exec)
- Treat each `codex exec` run as an isolated subagent process. Coordinate multiple runs from your orchestrator script or CI runner.
- Communication happens over stdout as JSON Lines when `--json` is used, providing structured events for turns, items, tool calls, and final messages.
- You can resume a prior run’s context via `codex exec resume <SESSION_ID>`.
- Reference: docs/exec.md

## Communication Surfaces

1) MCP Server Mode (Codex as subagent)
- Start a Codex MCP server:
  - `npx @modelcontextprotocol/inspector codex mcp-server` (quickstart for local testing)
- Tools exposed by Codex MCP server:
  - `codex`: start a new Codex session.
    - Properties include: `prompt` (required), `approval-policy`, `base-instructions`, `config` (overrides), `cwd`, `model`, `profile`, `sandbox`.
  - `codex-reply`: continue an existing session.
    - Properties: `prompt` (required), `conversationId` (required).
- Orchestration pattern: The orchestrator calls `codex` to spawn a subagent, stores `conversationId`, and later calls `codex-reply` to send follow‑ups and receive responses.
- Reference: docs/advanced.md#using-codex-as-an-mcp-server

2) MCP Client Mode (Codex calling subagents/tools)
- Configure external MCP servers in `~/.codex/config.toml` under `[mcp_servers.<id>]`:
  - For stdio servers: `command`, `args`, `env`, timeouts, and tool allow/deny lists.
  - For streamable HTTP servers: `url`, optional `bearer_token_env_var`.
- When Codex chooses to use those tools, it issues MCP calls and the event stream will include `mcp_tool_call` items.
- Reference: docs/config.md (mcp_servers), docs/advanced.md#model-context-protocol, docs/exec.md (event types)

3) Non‑interactive JSONL Stream (codex exec)
- `codex exec --json` emits a stream of JSON Lines events that you can parse to coordinate subagents programmatically.
- Key event types (docs/exec.md):
  - `thread.started`, `turn.started`, `turn.completed`, `turn.failed`
  - `item.*` (e.g., `agent_message`, `reasoning`, `command_execution`, `file_change`, `mcp_tool_call`, `web_search`, `todo_list`)
- The final agent message for a turn is usually an `item.completed` with `type = agent_message`.
- Reference: docs/exec.md (JSON output mode)

## Context, Memory, and Personas (AGENTS.md)

- Codex reads layered instructions from AGENTS.md files prior to the first turn:
  - Global: `~/.codex/AGENTS.md` or `AGENTS.override.md`
  - Project: from repo root down to current directory, per directory: `AGENTS.override.md`, then `AGENTS.md`, then configured fallbacks.
- Precedence: later (deeper) files override earlier ones; large files are truncated to the configured byte limit.
- Configure fallbacks and size limits in `config.toml`:
  - `project_doc_fallback_filenames`
  - `project_doc_max_bytes`
- Use AGENTS.md to encode personas and coordination rules subagents should follow, regardless of whether they’re separate Codex sessions or external MCP agents.
- Reference: docs/agents_md.md, docs/config.md (project_doc_* options)

## Orchestration Patterns

Pattern A — Agents SDK orchestrator using Codex as subagents (MCP server)
- Start a Codex MCP server (one per node or per project) and register it with your orchestrator.
- Spawn subagents by calling the `codex` tool (pass `prompt`, `cwd`, `profile`, `sandbox`, and any config overrides).
- Persist the returned `conversationId` per subagent persona.
- Exchange messages by calling `codex-reply` with the subagent’s `conversationId`.
- Share context via AGENTS.md files and by setting `cwd` and `profile` for each subagent.
- Monitor progress via the orchestrator’s MCP event handling; escalate or reroute based on tool/timeouts.

Pattern B — Codex as orchestrator calling MCP “subagent” servers (tools)
- Configure each subagent MCP server in `~/.codex/config.toml` under `[mcp_servers.<id>]`.
- Codex will determine when to call those tools; listen for `mcp_tool_call` events (in `codex exec --json`) or watch the TUI logs.
- Use `enabled_tools`/`disabled_tools` and per‑tool timeouts to shape behavior.

Pattern C — Process‑level subagents with `codex exec`
- Spawn multiple `codex exec --json` processes (e.g., Implementer, Reviewer, Tester personas) in parallel from a parent script or CI pipeline.
- Parse their JSONL streams to collect `agent_message` outputs, tool calls, and file changes.
- Resume a run with `codex exec resume --last` or by id to continue a specific subagent’s conversation.

## Approvals, Sandbox, and Safety

- Approval policy options are consistent across modes: `untrusted`, `on-failure`, `on-request`, `never`.
- Sandbox modes: `read-only`, `workspace-write`, `danger-full-access`.
- In non‑interactive (`codex exec`), defaults are conservative; opt into `--full-auto` or `--sandbox danger-full-access` only when appropriate.
- Reference: README.md (Sandbox & approvals), docs/sandbox.md

## Observability

- Interactive TUI logs: `~/.codex/log/codex-tui.log` (configure via `RUST_LOG`).
- Non‑interactive: logs stream inline to stderr; structured JSONL to stdout with `--json`.
- Reference: docs/advanced.md#tracing-verbose-logging, docs/exec.md

## Minimal Recipes

MCP Server (Codex as subagent):
1) Launch: `npx @modelcontextprotocol/inspector codex mcp-server`
2) Orchestrator calls `tools/call` for tool `codex` with `{ prompt, cwd, profile, sandbox }` → capture `conversationId`.
3) To continue: call `codex-reply` with `{ conversationId, prompt }`.

MCP Client (Codex calling subagents):
```toml
[mcp_servers.review_bot]
command = "/usr/local/bin/review-bot"
args = ["--stdio"]
enabled = true
tool_timeout_sec = 90
```
Codex will emit `mcp_tool_call` events when it uses `review_bot`’s tools.

Process‑level (codex exec subagents):
```bash
codex exec --json "Implement feature X" > impl.jsonl &
codex exec --json "Review feature X for security issues" > review.jsonl &
wait
# parse impl.jsonl and review.jsonl for agent_message items
```

## What This Is Not

- There is no special “subagent” API inside the Codex CLI beyond the patterns above.
- “Subagents” are realized via MCP integration (client or server) or by orchestrating multiple Codex runs.

## References

- README.md → Model Context Protocol, configuration, non‑interactive mode
- docs/advanced.md → “Using Codex as an MCP Server” (codex, codex‑reply tools)
- docs/config.md → `mcp_servers` configuration and project document settings
- docs/exec.md → JSONL streaming events, structured output, resume
- docs/agents_md.md → AGENTS.md discovery and precedence

