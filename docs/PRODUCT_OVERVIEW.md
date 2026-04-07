# GiljoAI MCP: Product Overview

*Last updated: 2026-04-06*

## What Is GiljoAI MCP

GiljoAI MCP is a context engineering platform for AI-assisted software development. It acts as a passive context server: it stores product knowledge, generates focused prompts, and coordinates agents via the Model Context Protocol (MCP). It does not write code or reason about your codebase. Your AI coding tool does that work using your own subscription. GiljoAI provides the orchestration layer that keeps every agent session aligned with your product.

Your AI tool connects to GiljoAI as an MCP server over HTTP. GiljoAI returns structured context, agent templates, and coordination data. The tool then uses that information to plan missions, spawn subagents, and track progress.

## Who It Is For

| User | What they get |
|---|---|
| Solo developer using Claude Code, Codex CLI, or Gemini CLI | Multi-agent workflows without manual prompt engineering |
| Developer building production software across many sessions | Persistent product context and 360 Memory across projects |
| Team wanting agent coordination and audit trails | Shared product definitions, task boards, and message logs |

GiljoAI MCP is for developers who already use AI coding CLIs and want a structured orchestration layer on top of them.

## Core Value Proposition

Define your product once. Every agent that connects starts with the full picture.

Without GiljoAI, each AI session starts blank. You re-explain your tech stack, constraints, architecture decisions, and prior work each time. GiljoAI solves this by storing that knowledge permanently and injecting it automatically at session start.

The platform also coordinates multi-agent teams. Rather than running one large context window, GiljoAI distributes context to the right agent for each role: an implementer gets code-relevant context, a reviewer gets quality-relevant context, a documenter gets specification context. Each agent gets exactly what it needs for its role.

## How It Works

```
CLI tool --> MCP server (GiljoAI) --> FastAPI --> PostgreSQL
```

1. Connect your AI coding tool to GiljoAI using an API key generated during setup.
2. Define a Product (what you are building) and create Projects (units of work inside that product).
3. Activate a project. GiljoAI generates a bootstrap prompt.
4. Paste that prompt into your CLI tool. The tool connects to GiljoAI and reads context, agent templates, and project instructions via MCP.
5. The orchestrator agent plans the mission and spawns subagents. Each subagent receives its role, expertise, and chain strategy from GiljoAI.
6. Agents report status back to GiljoAI in real time. You monitor progress on the Jobs page.
7. When the project completes, GiljoAI writes a 360 Memory entry. The next project inherits that accumulated context.

## The Six Pillars

### How GiljoAI Works

GiljoAI MCP is a passive context server. Your AI coding tool does all reasoning and coding using your own subscription. GiljoAI stores product knowledge, generates focused prompts, and serves coordination data so your agents stay aligned. Your AI tool connects to GiljoAI as an MCP server over HTTP, and each tool gets its own API key and connection. You can use Claude Code, Codex CLI, Gemini CLI, or any MCP-compatible tool simultaneously.

### Define Your Product

Create a Product to represent the software you are building. Fill in context fields: description, tech stack, architecture, testing strategy, constraints, and more. You can enter context manually, or use a pre-generated prompt that lets your AI coding tool suggest what to include based on a vision document or product proposal. Context settings let you toggle fields on or off and adjust depth per source, keeping prompts lean for simple tasks or fully detailed for complex missions.

### Projects and Missions

Create Projects inside a product. Each project is a focused unit of work such as a feature, sprint, or scaffolding effort. You stage a series of projects and activate one at a time. Activating a project causes GiljoAI to generate a bootstrap prompt. Paste that prompt into your CLI tool to start the orchestrator, which plans the mission and assigns agents from your templates. Context is assembled per session from your product fields, 360 Memory, and optional integrations. Each agent receives exactly what it needs for its role.

### Skills and Agent Templates

Two skills are installed on your machine during setup. For Claude Code and Gemini CLI: `/gil_add` and `/gil_get_agents`. For Codex CLI: `$gil-add` and `$gil-get-agents`. Use `/gil_add` to capture tasks or create projects mid-session without breaking flow. Use `/gil_get_agents` to fetch agent templates into your workspace for subagent spawning. The Agent Template Manager lets you browse, customize, and create agent profiles with roles, expertise, and chain strategies. Templates export automatically in the correct format for your platform.

### 360 Memory

Each completed project writes to 360 Memory automatically: what was built, key decisions, patterns discovered, and what worked. This is not a plugin or integration; it is a core product behavior. Your next project starts with accumulated context from previous ones. The orchestrator reads past memories alongside your product context and project description to plan each mission. You control how many memories back agents read through the context settings. Optionally enrich memory with git commit history for the complete development timeline.

### Dashboard and Monitoring

The Products, Projects, Tasks, and Jobs pages let you manage your work and track technical debt across all products. The Jobs page is where staging begins and agents execute. Watch their planning, to-do lists, and messages in real time. A message composer lets you talk directly to the orchestrator or broadcast to the entire agent team. All messages are logged in the MCP message system for auditability.

## Supported AI Tools

| Tool | Provider | Skill syntax |
|---|---|---|
| Claude Code | Anthropic | `/gil_add`, `/gil_get_agents` |
| Codex CLI | OpenAI | `$gil-add`, `$gil-get-agents` |
| Gemini CLI | Google | `/gil_add`, `/gil_get_agents` |
| Any MCP-compatible tool | Various | Depends on tool |

GiljoAI accepts any tool that can connect to an MCP server over HTTP.

## How to Get Started

Install GiljoAI MCP by following the steps in [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md). After installation, run the in-app Setup Wizard to connect your AI coding tools, install the skills on your machine, and configure your first product.
