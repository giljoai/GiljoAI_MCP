# GiljoAI MCP: Product Overview

*Last updated: 2026-04-07*

## What Is GiljoAI MCP

GiljoAI MCP is a context engineering platform for AI-assisted software development. It stores product knowledge, generates focused prompts, and coordinates agents via the Model Context Protocol (MCP). It does not write code or reason about your codebase. Your AI coding tool does that work using your own subscription.

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

---

## The Six Pillars

### Your Tools, Your Subscription

GiljoAI never touches your AI credits. You bring your own Claude Code, Codex CLI, Gemini CLI, or any MCP-compatible tool, each with your own subscription. GiljoAI acts as a passive MCP server: your tool connects over HTTP, reads context and coordination data, and does all the reasoning and coding itself. You can connect multiple tools simultaneously, each with its own API key.

### Define Your Product

Create a Product to represent the software you are building. Fill in context fields: description, tech stack, architecture, testing strategy, and more. You can enter context manually, or upload a vision document and use a pre-generated prompt that lets your AI coding tool suggest what to include. Context settings let you toggle fields on or off and adjust depth per source, keeping prompts lean for simple tasks or fully detailed for complex missions.

### Projects and Missions

Projects are focused units of work inside a product, such as a feature, sprint, or scaffolding effort. The workflow:

1. Create a project and describe what needs to be done.
2. Activate the project. GiljoAI assembles a bootstrap prompt from your product context, 360 Memory, and project description.
3. Paste the prompt into your CLI tool. The orchestrator agent connects to GiljoAI and plans the mission.
4. The orchestrator spawns subagents from your templates. Each receives its role, expertise, and chain strategy from GiljoAI.
5. Agents report status back in real time. You monitor progress on the Jobs page.
6. When the project completes, GiljoAI writes a 360 Memory entry. The next project inherits that accumulated context.

### Skills and Agent Templates

Two skills are installed on your machine during setup. Use them from your CLI without breaking flow:

| Skill | Claude Code | Codex CLI | Gemini CLI | What it does |
|---|---|---|---|---|
| **Add task or project** | `/gil_add` | `$gil-add` | `/gil_add` | Capture tasks, create projects, or log ideas mid-session |
| **Fetch agent templates** | `/gil_get_agents` | `$gil-get-agents` | `/gil_get_agents` | Download agent profiles into your workspace for subagent spawning |

The Agent Template Manager in the dashboard lets you browse, customize, and create agent profiles with roles, expertise, and chain strategies. Templates export automatically in the correct format for your connected platform.

### 360 Memory

Each completed project writes to 360 Memory automatically: what was built, key decisions, patterns discovered, and what worked. This is not a plugin or integration; it is a core product behavior. Your next project starts with accumulated context from previous ones. The orchestrator reads past memories alongside your product context to plan each mission. You control how many memories back agents read through the context settings. Optionally enrich memory with git commit history for the complete development timeline.

### Dashboard and Monitoring

The Products, Projects, Tasks, and Jobs pages let you manage your work and track technical debt across all products. The Jobs page is where staging begins and agents execute. Watch their planning, to-do lists, and messages in real time. A message composer lets you talk directly to the orchestrator or broadcast to the entire agent team. All messages are logged in the MCP message system for auditability.

---

## How to Get Started

Install GiljoAI MCP by following the steps in [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md). After installation, run the in-app Setup Wizard to connect your AI coding tools, install the skills on your machine, and configure your first product.
