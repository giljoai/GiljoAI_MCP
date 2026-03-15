# Getting Started with GiljoAI MCP

**Setup time:** 6–10 minutes
**Prerequisites:** Python 3.10+, PostgreSQL 14+ (18 recommended)

---

## What You Need Before You Start

GiljoAI MCP is a **passive orchestrator** — it manages context, generates structured prompts, and coordinates agent workflows. It does not include AI model access or token credits.

**You will need:**

- **Python 3.10+** installed on your system
- **PostgreSQL 14+** running locally (18 recommended)
- **pip** (Python package manager)
- **npm** (optional, for frontend development mode)
- **A subscription to an AI coding tool:** Claude Code CLI, Codex CLI, Gemini CLI, or any MCP-compatible client

GiljoAI MCP runs entirely on your machine. No cloud account required. No data leaves your system.

---

## Step 1: Install

```bash
# Clone the repository
git clone https://github.com/giljoai/giljoai-mcp.git
cd giljoai-mcp

# One command does everything
python startup.py
```

**What happens automatically:**

- Environment check: validates Python, PostgreSQL, and dependencies
- Database setup: creates the `giljo_mcp` database and all tables
- Setup wizard launches in your browser at `http://localhost:7274/setup`
- Services start: API server (port 7272) and frontend (port 7274)

**On subsequent runs**, `python startup.py` skips the wizard and opens the dashboard directly.

**Startup options:**

```bash
python startup.py              # Normal startup (auto-detects first run)
python startup.py --setup      # Force the setup wizard to run again
python startup.py --dev        # Development mode with auto-reload
python startup.py --no-browser # Start without opening the browser
python startup.py --verbose    # Detailed logging for troubleshooting
```

---

## Step 2: Create Your Admin Account

On first run, the setup wizard opens in your browser. No default credentials exist — you create the first admin account here.

- **Username**: your choice
- **Password**: minimum 12 characters
- **Recovery PIN**: 4-digit PIN for password reset

After account creation, you're logged into the dashboard automatically.

---

## Step 3: Generate an API Key

Your AI tool needs an API key to connect to GiljoAI MCP.

1. Click your **avatar** (top right) → **My Settings**
2. Go to the **API and Integrations** tab
3. Click **Generate API Key**
4. Copy and save the key — it's shown only once

Your key will look like: `gk_xxxxxxxxxxxx`

---

## Step 4: Connect Your AI Tool

Go to **My Settings → Integrations** tab. GiljoAI provides configuration snippets for each supported tool.

**Claude Code CLI:**

```bash
claude mcp add --transport http giljo-mcp http://localhost:7272/mcp \
  --header "X-API-Key: gk_YOUR_API_KEY_HERE"
```

Verify the connection:
```bash
# Inside Claude Code, run:
/mcp
# You should see "giljo-mcp" listed as Connected
```

**Generic MCP Client Configuration (JSON-RPC 2.0):**

```json
{
  "mcpServers": {
    "giljoai": {
      "url": "http://localhost:7272/mcp",
      "headers": {
        "X-API-Key": "gk_YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Optional integrations:**

- **Serena MCP**: Enable in Settings → Integrations for deep semantic code analysis
- **GitHub Integration**: Enable in Settings → Integrations to enrich 360 Memory with git commit history

---

## Step 5: Define Your Product

A Product in GiljoAI MCP is a structured definition of the software you're building. This becomes the single source of truth that every AI agent reads from.

1. Go to **Products** in the left sidebar
2. Click **+ New Product**
3. Fill in the tabs:
   - **Basic Info**: Product name and description
   - **Vision Docs**: Upload `.md` or `.txt` files describing your product (architecture, features, API design, etc.). Large files are auto-chunked with multi-level summarization.
   - **Tech Stack**: Programming languages, frameworks, database, infrastructure
   - **Architecture**: Patterns, design decisions, API style
   - **Testing**: Strategy, coverage targets, quality standards

You can have one active product at a time. This is enforced at the database level to keep agents focused.

---

## Step 6: Create and Stage a Project

A Project is a unit of work under your Product — a feature, a refactor, a bugfix.

1. Go to **Projects** in the left sidebar
2. Click **+ New Project**
3. Write a **Project Description** in plain language: what you want done, requirements, constraints
4. Choose your **Execution Mode**:
   - **Claude Code CLI**: Single terminal, agents spawned via the Task tool
   - **Multi-Terminal**: Each agent gets its own prompt for a separate terminal session
5. Click **Stage Project**

**What staging does:**

- GiljoAI assembles your full product context (vision docs, tech stack, architecture, 360 Memory, agent templates)
- It generates a structured prompt pre-loaded with your product context and the orchestration protocol
- The prompt is copied to your clipboard

**This is the key moment: GiljoAI does not call any AI model.** It assembles the context and protocol. Your AI tool does the thinking.

---

## Step 7: Paste and Execute

1. Open your AI tool (Claude Code, Codex, Gemini) in a terminal
2. Paste the staged prompt
3. Your AI tool reads the prompt, connects to GiljoAI via MCP, and generates the mission plan
4. Agents are assigned based on the mission requirements
5. Switch to the **Implementation** tab in GiljoAI's dashboard
6. Copy the implementation prompt and paste it back into your terminal
7. Execution begins — agents coordinate through MCP message queues

---

## Step 8: Monitor and Close Out

The **Implementation tab** shows real-time agent activity:

- Agent status: waiting, working, blocked, complete
- Step progress (e.g., 6/6, 8/8)
- Duration per agent
- Message queue activity
- Broadcast and direct messaging to agents

When work is complete, click **Close Out Project**. The system:

- Captures the orchestrator's summary
- Records git commits (if GitHub integration is enabled)
- Writes a **360 Memory** entry: what was built, key decisions, patterns, outcomes

Your next project starts with this accumulated intelligence. The more you build, the richer the context your agents receive.

---

## What's Next

- **Customize agent templates**: Settings → Agents tab. Edit role instructions, add new specializations, export to your AI tool.
- **Tune context delivery**: Settings → Context tab. Control which context categories each orchestrator receives and at what depth.
- **Capture ideas**: Use the Tasks view to log ideas, then convert them to full projects when ready.

---

## Troubleshooting

**"Connection refused" when AI tool tries to reach MCP:**
- Verify GiljoAI MCP is running (`python startup.py`)
- Check the API key is correct in your tool's MCP configuration
- Confirm port 7272 is not blocked by your firewall

**Setup wizard won't launch:**
- Run `python startup.py --setup` to force the wizard
- Check that port 7274 is available

**Database connection errors:**
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in your `.env` file (auto-generated during setup)

**Need more help?**
- [GitHub Issues](https://github.com/giljoai/giljoai-mcp/issues)
- [Server Architecture Reference](SERVER_ARCHITECTURE_TECH_STACK.md)

---

## Architecture at a Glance

```
Your CLI Tool (Claude Code / Codex / Gemini)
        |
        | MCP-over-HTTP (API key auth, JSON-RPC 2.0)
        v
  GiljoAI MCP Server (port 7272)
  +--> REST API (products, projects, tasks, agents, messages)
  +--> MCP Endpoint (30+ tools for AI agent coordination)
  +--> WebSocket (real-time dashboard updates)
        |
        v
  PostgreSQL (tenant-isolated, every query filtered by tenant_key)

  Dashboard (port 7274)
  +--> Vue 3 + Vuetify 3 frontend
  +--> WebSocket live updates
  +--> Agent monitoring, prompt staging, project management
```

All components run locally. Your AI tool connects via MCP. GiljoAI assembles context and manages coordination. Your AI tool does the thinking.
