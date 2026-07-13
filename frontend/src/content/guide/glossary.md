## Glossary

Quick definitions for the terms used throughout GiljoAI MCP. Terms are grouped by what they describe.

**The hierarchy — how your work is organized:**

| Term | Meaning |
|---|---|
| **Product** | The software you are building. A product is the top-level container: every project, task, agent, and memory belongs to one product. It holds your context — description, tech stack, architecture, testing strategy — which agents read at the start of each session. Only one product is active at a time. |
| **Project** | A focused unit of work inside a product, such as a feature, a refactor, or a bug fix. A project is the thing you run: it has a description, an agent team, a mission, and a closeout that writes a 360 Memory entry. |
| **Task** | A note about work you have identified but not yet scheduled. Tasks live on the Task Board and are for capturing ideas, technical debt, and follow-ups. A task does not run agents; convert it to a project when you are ready to build it. |
| **Job** | A single agent's assignment within a running project — its role, mission, and to-do list. The Jobs page shows one row per job so you can watch each agent's status and progress. |

**The agents — who does the work:**

| Term | Meaning |
|---|---|
| **Agent** | An AI worker that connects through your own AI coding tool (Claude Code CLI, Claude Desktop, Codex CLI, Gemini CLI, or any MCP-compatible tool) and does the actual reasoning and coding. GiljoAI assigns each agent its role and context; your tool and subscription do the work. |
| **Orchestrator** | The lead agent for a project. It reads your product context and 360 Memory, plans the mission, spawns the specialist agents, and coordinates them until the project closes out. |
| **Conductor** | The coordinator that drives a chain of projects — also called the chain orchestrator or master orchestrator. Unlike a project orchestrator, the conductor owns no project of its own; it only runs the chain in order, launching each project and advancing to the next. |

**Chains — running several projects together:**

| Term | Meaning |
|---|---|
| **Chain** | Several projects linked together and run one after another under a single overarching goal. A chain holds 2 to 5 projects and is multi-project, single-user. See the **Chain Projects** chapter. |
| **Chain mission** | The overarching goal for a whole chain — the single objective all the linked projects serve together. Distinct from each project's own per-project mission. |

**Goals and memory:**

| Term | Meaning |
|---|---|
| **Mission** | What an agent or project is trying to achieve. A project's mission is planned by its orchestrator from your description and context; each agent then works its own part of that mission. |
| **360 Memory** | The record written automatically at the end of each project: what was built, key decisions, patterns discovered, and outcomes. Your next project starts with this accumulated history available to the agent team, so context carries forward instead of starting blank each time. |
