# Gemini “Agents” and MCP — What Exists and What’s Possible

This guide surveys official Google documentation and repositories to explain how to use Gemini in agentic workflows today, and how to achieve “subagent” behavior with or without the Model Context Protocol (MCP). It also flags what does not exist (as of this writing) to set clear expectations.

## Scope & Primary Sources

- Google Gen AI SDK (official JavaScript/TypeScript SDK): googleapis/js-genai: README.md
- Gemini Developer API docs: ai.google.dev/gemini-api/docs
- Gemini function calling (aka tools): ai.google.dev/gemini-api/docs/function-calling
- Vertex AI Agent Builder overview (Google Cloud “agents”): cloud.google.com/vertex-ai/generative-ai/docs/agent-builder/overview

Note: There is no official “Gemini CLI” published by Google that parallels OpenAI’s Codex CLI. Third‑party CLIs exist (e.g., eliben/gemini-cli) but they are not official and do not advertise MCP support.

## What Exists Officially

- SDKs, not a CLI
  - The official way to use Gemini is via SDKs/APIs (server‑side strongly recommended). For JavaScript/TypeScript, use `@google/genai` (Google Gen AI SDK). Repo: github.com/googleapis/js-genai
  - The prior “generative-ai-js” SDK was deprecated and replaced by `@google/genai`.

- Function Calling (“Tools”)
  - The Gemini Developer API supports function calling so models can request tool invocations you implement. This is the canonical way to let Gemini call out to external capabilities in agentic flows.
  - Reference: ai.google.dev/gemini-api/docs/function-calling

- Vertex AI Agent Builder (Agents on Google Cloud)
  - Google Cloud offers “Agent Builder” for building task‑oriented agents within Vertex AI (LLM routing, grounding, retrieval, etc.). This is Google’s primary “agents” product—distinct from any CLI. Reference: Vertex AI Agent Builder overview (link above).
  - This does not expose MCP directly; it’s a managed service with Google Cloud primitives.

## What Does Not Exist (as of today)

- An official “Gemini CLI” from Google with built‑in multi‑agent orchestration
- Official MCP support or first‑party docs stating that Gemini runs as an MCP client or server

Because these don’t exist, “subagent” setups with Gemini require light engineering glue. Below are practical options.

## Practical Ways To Achieve “Subagents” With Gemini

1) Wrap Gemini in an MCP Server (recommended for MCP ecosystems)
- Build a small MCP server in Node/TypeScript using the Google Gen AI SDK (`@google/genai`).
- Expose tools like `gemini.generate` and `gemini.reply` that internally call the Gemini API.
- Run and test with the MCP Inspector (`npx @modelcontextprotocol/inspector node build/index.js`).
- Any MCP client (Codex, Claude Code, etc.) can then treat Gemini as a tool/subagent.
- Transport: stdio or streamable HTTP; publish tool schemas in the MCP server.

Minimal shape for a stdio launcher entry (mcp.json):
```json
{
  "mcpServers": {
    "gemini-subagent": {
      "command": "node",
      "args": ["build/gemini-mcp-server.js"],
      "env": {
        "GOOGLE_API_KEY": "your-api-key"
      }
    }
  }
}
```

2) Orchestrate Multiple Gemini “Subagents” As Processes
- Treat each subagent as a separate Node process that uses `@google/genai` with its own persona and context directory.
- Emit structured logs/JSON to stdout; your orchestrator supervises processes, collects outputs, and routes messages.
- This mirrors “process‑level subagents” and works regardless of MCP.

3) Use Function Calling to Implement Tools and Role Split
- Implement your tool surface (filesystem ops, repo search, test runner, etc.) and register those functions with the Gemini conversation.
- Split responsibilities across runs (Implementer, Reviewer, Tester) by changing system prompts/personas and the allowed tool set.
- This operates inside the Gemini API without MCP; orchestration logic lives in your app.

4) Vertex AI Agent Builder (Managed Agents)
- If you’re on Google Cloud, consider building agents with Vertex AI Agent Builder and invoking Gemini through that framework.
- This provides managed retrieval, routing, safety, and enterprise integrations, but is not MCP‑native. It’s an alternative to rolling your own orchestrator.

## Observability and Safety Considerations

- API Keys: Keep keys server‑side; avoid exposing Google API keys in client apps (called out in `@google/genai` README).
- Logging: Standardize JSON logs for each subagent process to make aggregation and debugging simpler.
- Rate limits and quotas: Gemini API quotas apply to all approaches.
- Safety: Apply filtering/grounding in Vertex AI when using Agent Builder; for DIY, enforce tool allowlists and validation before side‑effects.

## Minimal Patterns & Snippets

- Node MCP server skeleton (conceptual):
```ts
import { GoogleGenAI } from '@google/genai'
import { createMcpServer } from 'your-mcp-lib' // e.g., an MCP helper scaffold

const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY! })

createMcpServer({
  tools: {
    'gemini.generate': async ({ prompt, model = 'gemini-2.0-flash-001' }) => {
      const res = await ai.models.generateContent({ model, contents: prompt })
      return { text: res.text }
    }
  }
}).listenStdio()
```

- Function calling (tools) with Gemini API: see ai.google.dev/gemini-api/docs/function-calling for official patterns to register and handle functions.

## Summary

- There is no official “Gemini CLI” with built‑in multi‑agent orchestration or MCP integration.
- You can still achieve “subagent” behavior today by:
  - Wrapping Gemini as an MCP server (so it becomes a first‑class tool in MCP clients)
  - Running multiple Gemini personas as supervised processes
  - Using function calling to build tools and orchestrate roles
  - Using Vertex AI Agent Builder for managed agents on Google Cloud

## References (Official)

- Gemini API docs: https://ai.google.dev/gemini-api/docs
- Function calling: https://ai.google.dev/gemini-api/docs/function-calling
- Google Gen AI SDK (JS/TS): https://github.com/googleapis/js-genai
- Vertex AI Agent Builder overview: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-builder/overview

(Non‑official example)
- Third‑party `gemini-cli`: https://github.com/eliben/gemini-cli (not MCP‑enabled and not an official Google project)
