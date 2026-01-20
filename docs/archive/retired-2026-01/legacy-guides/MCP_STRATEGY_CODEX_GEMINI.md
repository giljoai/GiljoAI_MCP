# MCP Strategy: Codex CLI and Gemini

Purpose: Document concrete, production‑ready ways for this MCP server to interoperate with Codex CLI and Gemini, including recommended paths, viable alternatives, and minimal changes needed on our side.

## Current Capabilities (this MCP server)

- MCP over HTTP endpoint: JSON‑RPC 2.0 at `/mcp` with initialize, tools/list, tools/call
- Session + tenant isolation via API key header; PostgreSQL‑backed sessions
- Rich tool surface for project, agent, task, message, context ops (tool_map in the HTTP handler)
- Internal multi‑agent engine: AgentJobManager, AgentCommunicationQueue, JobCoordinator (spawn/parallel/chains, messaging, aggregation)

These let external clients act as “orchestrators” while our server remains the source of truth for jobs, agents, messages, and artifacts.

## Codex CLI Integration

### A) Codex as MCP client over streamable HTTP (recommended)

- Server change (small): Accept `Authorization: Bearer <token>` in addition to current `X-API-Key` header for `/mcp`. Keep X‑API‑Key for backward compatibility.
- Client config (user `~/.codex/config.toml`):

```toml
# Optional: try the new Rust MCP client
# experimental_use_rmcp_client = true

[mcp_servers.giljo]
url = "https://YOUR_HOST/mcp"          # streamable HTTP MCP endpoint
bearer_token_env_var = "GILJO_API_KEY"  # exported in the shell
# optional hardening / UX
startup_timeout_sec = 20
tool_timeout_sec = 90
enabled = true
```

- Workflow
  - Codex connects, lists our tools, and calls them as needed.
  - Use AGENTS.md to teach Codex orchestration patterns: spawn agents, create tasks, send/receive/ack messages, get context summaries, etc.
  - Our job + queue subsystems provide “subagent” coordination; Codex is just the client driving those tools.

Why this works well
- Zero new infra; Codex supports streamable HTTP MCP.
- Our server persists state; Codex can come and go.
- Maps cleanly to our existing tool surface and message queue.

### B) Codex process‑level subagents with `codex exec`

- Treat each persona (Implementer, Reviewer, Tester, Orchestrator) as its own `codex exec --json` run.
- Each process uses our MCP tools for state and messaging; the parent script aggregates JSONL events and forwards messages via our queue.
- Pros: no persistent interactive TUI, easy to supervise; Cons: more glue on the user side.

### C) Codex as an MCP server (optional, not required)

- Codex can run as an MCP server exposing `codex` / `codex-reply` tools.
- Only relevant if an upstream multi‑agent system wants to call Codex itself as a sub‑tool. Our primary need is Codex→this MCP, so this is optional.

## Gemini Integration (realistic paths)

Ground truth today
- There is no official “Gemini CLI” with MCP support.
- Official integration is via SDKs (e.g., `@google/genai`) or Google Cloud’s Vertex AI Agent Builder (managed agents, not MCP‑native).

Viable options to enable “subagents” with Gemini:

1) Build a thin Gemini CLI that is an MCP client
- A small Node/TS CLI uses `@google/genai` for LLM and an MCP client to connect to our `/mcp`.
- The CLI behaves like a “Gemini agent” locally but persists work and collaboration through our MCP tools (spawn_agent, send_message, etc.).
- Our existing “AI Tool Configuration Management” can generate a simple `.gemini.json` pointing this CLI at our `/mcp`.

2) Wrap Gemini as an MCP server (for multi‑agent ecosystems)
- Separate service exposing tools like `gemini.generate`. Codex/Claude (as MCP clients) can then call Gemini as a subagent tool.
- Useful if teams want Gemini available as a callable tool inside Codex sessions. Not required for Gemini→our MCP.

3) Process‑level subagents via SDK
- Run multiple Node processes (personas) using `@google/genai`. Each process posts progress and messages via our tools; our server orchestrates as the hub.

4) Vertex AI Agent Builder (managed)
- If on Google Cloud, build agents with Agent Builder and integrate with our server over HTTP/REST for state sync or via custom connectors. Not MCP‑native but a viable enterprise path.

## Minimal server changes (to unblock Codex now)

- Accept Bearer tokens at `/mcp` in addition to `X-API-Key`.
- Optional: Generate a live “MCP Tools” doc page from `tools/list` so client users can browse schemas.
- Ensure reasonable per‑tool timeouts; long‑running ops should stream intermediate state via our messaging tools.

## Config generation updates

- Codex: add a TOML generator variant that outputs a `[mcp_servers.<id>]` block with `url`, `bearer_token_env_var`, `tool_timeout_sec`, `enabled`.
- Gemini: ship a minimal CLI scaffold (Node) and generate a `.gemini.json` that contains `{ "mcpUrl": "https://YOUR_HOST/mcp", "apiKeyEnv": "GEMINI_API_KEY" }` (or similar) for the wrapper.

## Testing & validation

- Codex (streamable HTTP):
  - Initialize → tools/list → tools/call happy path
  - Negative tests: invalid token, expired session, unknown tool
  - Long‑running tool: verify Codex UX remains responsive and results are returned
- MCP Inspector: point to our `/mcp` to validate schemas and invocations interactively
- Process‑level orchestration: run two parallel personas, validate our queue and dashboard reflect interactions

## Safety & observability

- Auth: Bearer or X‑API‑Key only (no cookies); rotate keys per tenant; keep sessions expiring
- Sandbox: Codex approvals/sandboxing are client‑side; our side should validate tool inputs and enforce tenant scoping
- Logs: expose clear MCP traces in `logs/api.log`; add request ids to correlate initialize → list → call

## Roadmap (actionable)

1. Add Bearer token support to `/mcp` (keep X‑API‑Key)
2. Expose Codex TOML config generator in the existing AI Tools Config API
3. Add a short “MCP Tools” auto‑doc page driven by `tools/list`
4. Publish a minimal Gemini CLI wrapper (Node) as MCP client + `@google/genai`
5. Optional: Gemini MCP server for teams who want Gemini callable from Codex

## References

- This MCP server
  - HTTP MCP endpoint, tools list/call, session auth
  - Agent orchestration (jobs, queue, coordinator)
- Codex CLI
  - Streamable HTTP MCP client with `url` + `bearer_token_env_var`
  - JSONL `codex exec --json` for process‑level subagents
- Gemini
  - No official MCP client CLI; use SDK wrapper or managed Agent Builder

