# Getting Started

*For users already logged into the GiljoAI MCP dashboard.*

This guide walks through the five steps to run your first project: configure your tools, create a product, create and stage a project, execute the prompt in your CLI tool, and monitor to completion.

---

## Quick Setup

The Setup Wizard opens automatically on first login. It walks through four steps:

| Step | Label | What happens |
|---|---|---|
| 0 | Choose Tools | Select your AI coding tool (Claude Code, Codex CLI, Gemini CLI) |
| 1 | Connect | Generate an API key and copy the MCP configuration snippet into your tool |
| 2 | Install | Install the slash command skills (`/gil_add`, `/gil_get_agents`) on your machine |
| 3 | Launch | Confirm setup and receive your first bootstrap prompt |

After the Connect step, verify the MCP connection from your CLI tool:

```
/mcp
# You should see "giljo_mcp" listed as Connected
```

To add tools later or generate additional API keys: click your avatar (bottom left), open **My Settings**, and go to the **API Keys** tab.

To rerun the wizard at any time: **My Settings** > **Startup** tab > Setup Wizard.

---

## Create a Product

Navigate to **Products** in the left sidebar. A Product is the context container for everything you build. All projects and agents draw context from it.

Click **+ New Product** and fill in the tabs:

| Tab | Fields |
|---|---|
| **Product Setup** | Product name (required); upload vision documents (.md, .txt) |
| **Product Info** | Codebase folder path, description, core features, brand guidelines |
| **Tech Stack** | Programming languages, frontend frameworks, backend frameworks, databases, infrastructure, target platforms |
| **Architecture** | Primary pattern, design patterns, API style, architecture notes, coding conventions |
| **Testing** | Quality standards, testing strategy, coverage target, testing frameworks |

You do not need to fill every field before saving. Start with the name and description; add more context over time.

**Vision Documents:** Upload `.md` or `.txt` files describing your architecture, API design, or product spec. After upload, you can choose to have your AI coding agent analyze the document and populate the product fields automatically (select "Use AI coding agent" on the Product Setup tab).

Only one product can be active at a time. Activating a new product shows a confirmation dialog.

---

## Create and Stage a Project

Navigate to **Projects** in the left sidebar. A Project represents a unit of work: a feature, a refactor, a bugfix.

1. Click **+ New Project**
2. Write a **Name** and **Description** in plain language — what you want built, requirements, constraints
3. Set the **Project Type** for the taxonomy badge (e.g. BE, FE, API)
4. Save the project

Then navigate to **Jobs** in the left sidebar and choose your **Execution Mode**:

- **Multi-Terminal:** Each agent gets its own prompt. Run agents in separate terminal sessions.
- **Subagent mode:** One main agent spawns subagents within a single session. Works with Claude Code CLI, Codex CLI, Gemini CLI, or any MCP-enabled tool.

Click **Stage Project**. GiljoAI MCP assembles a structured prompt from your product context, 360 Memory entries, project description, and agent templates. The prompt is copied to your clipboard.

---

## Paste and Execute

1. Open your AI coding tool in a terminal
2. Paste the staged prompt
3. Your agent connects to GiljoAI MCP and generates the mission plan
4. Switch to the **Implementation** tab on the Jobs page
5. Copy the implementation prompt and paste it back into your terminal
6. Execution begins — agents read their assigned jobs, create todo lists, and coordinate through MCP message queues

GiljoAI MCP does not call any AI model. It assembles context and protocol. Your AI coding tool does the thinking.

---

## Monitor and Close Out

The **Jobs** page shows real-time agent activity for the running project:

- Agent status (waiting, working, blocked, sleeping, complete — see the User Guide for the full status list)
- Step progress (e.g. 6/6, 8/8)
- Duration per agent
- Messages waiting count

You can send messages to agents via **Broadcast** (all agents) or direct message (individual agent). Messages are delivered through the MCP message queue.

When work is complete, click **Close Out Project**. The system:

- Captures the orchestrator's summary
- Records git commits (if git integration is enabled in My Settings > Integrations)
- Writes a **360 Memory** entry: what was built, key decisions, patterns, outcomes

Your next project starts with this accumulated context automatically.

---

## What's Next

**Tune product context** — If context fields drift from the actual codebase, use the Tune button on a product card. Select sections to retune, generate a prompt, and paste it into your CLI tool. The agent scans the codebase and updates the fields directly. See the User Guide for details.

**Customize agent templates** — Go to **My Settings > Agents**. Edit role instructions or add specializations. Fetch templates from the CLI:

```
/gil_get_agents   # Claude Code, Gemini CLI
$gil_get_agents   # Codex CLI
```

**Capture tasks** — Use the **Tasks** page to log ideas and technical debt. Create tasks from the CLI:

```
/gil_add a task for the last three things we discussed, mark them high priority
```

**Create projects from the CLI:**

```
/gil_add a project for the authentication gaps, mark it as backend work
```

---

## Troubleshooting

**"Connection refused" when the AI tool tries to reach MCP:**
- Verify GiljoAI MCP is running (`python startup.py`)
- Check the API key is correct in your tool's MCP configuration
- Confirm port 7272 is not blocked by your firewall

**Setup Wizard won't launch:**
- Run `python startup.py --setup` to force the wizard
- Run `python startup.py --verbose` to see startup logs
- Check that port 7272 is available

**Database connection errors:**
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in your `.env` file (generated during installation)

**Agent shows "Silent" status:**
- The Auto Check-In slider on the Jobs page sends periodic check-in messages to sleeping agents. Set it to an interval (5-60 minutes) that matches your workflow.

**Jobs page is not updating:**
- Check the WebSocket status indicator in the top navigation. A red icon means the connection was lost. Click it to open the debug panel and use the Force Reconnect button.

**Need help?** Email: infoteam@giljo.ai
