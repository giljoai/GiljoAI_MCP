# Agent Templates Guide

*Last updated: 2026-04-21*

## Where Agent Templates Live

Agent templates are stored at the **project level**, relative to the directory you launch your AI CLI from:

```
.claude/agents/     # Claude Code agent templates
.gemini/agents/     # Gemini CLI agent templates
.codex/agents/      # Codex CLI agent templates
```

These directories are created when you run `/gil_get_agents` inside your AI CLI session.

---

## Launch from the Product Root

**Always launch your AI CLI from the root of the product you are working on.**

`.claude/agents/` (and equivalent) are resolved relative to your current working directory. If you launch from the wrong directory, the templates will not be found.

- Launch from `my-app/` to use `my-app/.claude/agents/`
- Launch from `my-app/backend/` to use `my-app/backend/.claude/agents/`

---

## Monorepos

In a monorepo each sub-project can have its own agent templates:

```
monorepo/
  frontend/
    .claude/agents/      # Frontend-specific agents
  backend/
    .claude/agents/      # Backend-specific agents
  .claude/agents/        # Shared agents (root-level)
```

To use frontend agents, launch Claude Code from `monorepo/frontend/`. To use backend agents, launch from `monorepo/backend/`. To use shared agents, launch from `monorepo/`.

There is no automatic merging of parent and child `.claude/agents/` directories — only the directory relative to your CWD is loaded.

---

## Should You Commit `.claude/agents/` to Git?

**Yes. Commit it.**

Agent templates are product configuration, not personal settings. They encode how AI tools should behave when working on your codebase. Committing them means:

- All team members get the same agents automatically after `git pull`
- Templates are version-controlled alongside the code they support
- Reviews and rollbacks work the same as any other config change

**Exception:** If a template contains a secret (API key, credential), do not commit it. Add that specific file to `.gitignore`. Templates should not contain secrets — use environment variables instead.

Recommended `.gitignore` entry if you need to exclude a specific template:

```
.claude/agents/my-secret-agent.md
```

Do not add `.claude/agents/` as a blanket ignore — that defeats the purpose of project-level templates.

---

## Installing Templates

Use the `/gil_get_agents` slash command inside your AI CLI session. It connects to the GiljoAI MCP server and downloads templates for the active product to `.claude/agents/` (or the equivalent for your CLI).

For first-time setup, run `giljo_setup` to install the GiljoAI slash commands and bootstrap your environment.
