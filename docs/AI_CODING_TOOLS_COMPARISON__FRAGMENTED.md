# AI Coding Tools: Multi-Agent Capability Comparison (2025)

## Executive Summary

**You're absolutely right** - you need BOTH architectures because different AI coding tools have different multi-agent capabilities.

| Tool | Multi-Agent Support | Architecture Needed |
|------|---------------------|---------------------|
| **Claude Code** | ✅ Full sub-agent system | Sub-Agent (INTEGRATE_CLAUDE_CODE.md) |
| **Gemini CLI** | ✅ Sub-agent system | Sub-Agent |
| **Cursor** | ✅ Parallel agents | Sub-Agent or Hybrid |
| **Continue.dev** | ✅ Background workflows | Sub-Agent or Hybrid |
| **Windsurf** | ⚠️ Multi-model backend, single interface | Background Service (BACKGROUND_SERVICE_ORCHESTRATION.md) |
| **Codex CLI** | ❌ Single agent | Background Service |
| **Aider** | ❌ Single agent | Background Service |

---

## Detailed Analysis by Tool

### 1. Claude Code ✅ (Full Sub-Agent Support)

**Multi-Agent Capabilities:**
- Native `Task` tool for spawning sub-agents
- Each sub-agent gets isolated 200K token context
- Up to 10+ concurrent sub-agents
- Built-in coordination and handoff mechanisms
- Specialized agent types (database-expert, tdd-implementor, etc.)

**Architecture to Use:**
```
✅ Sub-Agent System (INTEGRATE_CLAUDE_CODE.md)
- 1 terminal (orchestrator)
- Spawns N internal sub-agents via Task tool
- Auto-coordination via Claude Code's system
```

**Example:**
```python
# In Claude Code orchestrator terminal
Task(
    subagent_type="database-expert",
    description="Design schema",
    prompt="Mission: Design checkout database schema..."
)
```

**Performance:**
- SWE-bench: 72.5%
- 10x parallel task execution
- Context: 1 main + N sub-agents (each 200K)

---

### 2. Gemini CLI ✅ (Sub-Agent System)

**Multi-Agent Capabilities:**
- Pull Request #4883 introduces sub-agent features
- `/subagents` CLI command for management
- Task delegation and parallel execution
- Independent context per sub-agent
- Specialized agents (code review, documentation, etc.)

**Community Workaround:**
- Developers spawn new `gemini-cli` instances via shell commands
- Each instance runs in `--yolo` mode for auto-approval
- Prompts construct and execute these spawns

**Architecture to Use:**
```
✅ Sub-Agent System (similar to Claude Code)
OR
✅ Hybrid: Background service spawns gemini-cli processes

Option 1 (Native):
  gemini-cli → /subagents create reviewer "Review code..."

Option 2 (Scripted):
  Background service → spawn multiple gemini-cli --yolo instances
```

**Example:**
```bash
# Native sub-agents (when PR #4883 merges)
gemini-cli
> /subagents create database "Design schema for checkout"
> /subagents create backend "Implement API endpoints"
> /subagents list

# Community workaround (current)
# Background service spawns:
gemini-cli --yolo --agent database < db_prompt.txt &
gemini-cli --yolo --agent backend < backend_prompt.txt &
```

---

### 3. Cursor ✅ (Parallel Agents)

**Multi-Agent Capabilities:**
- Cursor CLI for parallel execution
- Background agents running in cloud
- Multiple agents in terminal or remote
- Git worktrees for parallel work on different branches
- Composer for multi-file editing

**Architecture to Use:**
```
✅ Sub-Agent compatible (if using Claude Code integration)
OR
✅ Hybrid: Multiple Cursor instances via git worktrees

Option 1 (With Claude Code):
  cursor → Uses Claude Code sub-agents natively

Option 2 (Native Cursor):
  Background service → Manages multiple Cursor sessions via git worktrees
```

**Example:**
```bash
# Git worktrees approach
git worktree add ../checkout-db feature/database
git worktree add ../checkout-api feature/backend

# Terminal 1: Cursor in checkout-db worktree (Database work)
# Terminal 2: Cursor in checkout-api worktree (Backend work)
# Background service coordinates via MCP
```

**Performance:**
- 40-60% cost savings through intelligent orchestration
- 3-4x token consumption in multi-agent mode

---

### 4. Continue.dev ✅ (Background Workflows)

**Multi-Agent Capabilities:**
- **Workflows**: Background agents running continuously
- Agent mode for complex tasks
- Fixes bugs while you architect
- Builds features using your patterns
- Can open PRs autonomously

**Core Modes:**
- Chat
- Autocomplete
- Edit
- Agent (integrated with Chat)

**Architecture to Use:**
```
✅ Hybrid: Background workflows + MCP coordination

Continue.dev Workflows:
  - Bug fixer (continuous background)
  - Feature builder (on-demand)
  - PR opener (after completion)

GiljoAI MCP Integration:
  - Spawns workflows via Continue API/CLI
  - Monitors progress via Continue's status
  - Coordinates handoffs via MCP messages
```

**Example:**
```json
// .continue/config.json
{
  "workflows": [
    {
      "name": "database-agent",
      "trigger": "manual",
      "steps": [
        "Read MCP project context",
        "Design database schema",
        "Create migrations",
        "Report to MCP"
      ]
    },
    {
      "name": "backend-agent",
      "trigger": "on-database-complete",
      "steps": [
        "Read schema from MCP",
        "Implement API endpoints",
        "Write tests",
        "Report to MCP"
      ]
    }
  ]
}
```

---

### 5. Windsurf ⚠️ (Multi-Model Backend, Single Agent Interface)

**Multi-Agent Capabilities:**
- **Backend**: Multiple models working together
  - Custom models for low-latency features
  - GPT-4.1-level reasoning models
  - Proprietary retrieval systems
- **Frontend**: Single "Cascade" agent interface

**Cascade Features:**
- Deep reasoning on codebase
- Multi-step editing across files
- Access to terminal commands
- Omniscient of user actions

**Architecture to Use:**
```
⚠️ Background Service (BACKGROUND_SERVICE_ORCHESTRATION.md)

Why: Windsurf presents as single agent despite multi-model backend
Users can't directly spawn multiple Windsurf agents

Solution:
  - Background orchestrator generates prompts
  - Dashboard shows clipboard queue
  - User opens multiple Windsurf editors (one per workspace/branch)
  - Each Windsurf instance handles one agent's work
```

**Example:**
```
Terminal 1: Windsurf in workspace-database/
  (Handles database agent work)

Terminal 2: Windsurf in workspace-backend/
  (Handles backend agent work)

Background Service: Coordinates via MCP
Dashboard: Shows status of both
```

---

### 6. Codex CLI ❌ (Single Agent)

**Multi-Agent Capabilities:**
- **None detected**
- Single agent runs everywhere (terminal, IDE, cloud)
- Task isolation (separate environments per task)
- But NOT multi-agent coordination

**Task Isolation ≠ Multi-Agent:**
- Each task runs in isolated sandbox
- But tasks are sequential, not parallel agents
- No coordination between tasks

**Architecture to Use:**
```
❌ Background Service (BACKGROUND_SERVICE_ORCHESTRATION.md)

Must use clipboard/multi-terminal approach:
  - Background orchestrator generates prompts
  - Dashboard shows ready agents
  - User opens N terminals with codex CLI
  - Each terminal handles one agent's work
  - Coordination via MCP messages
```

**Example:**
```bash
# Terminal 1
codex
> [Paste database agent prompt from dashboard]

# Terminal 2
codex
> [Paste backend agent prompt from dashboard]

# MCP coordinates handoffs
```

**Note:** Codex supports MCP servers, so integration with GiljoAI MCP is possible:
```toml
# ~/.codex/config.toml
[mcp_servers]
giljo = { command = "python", args = ["-m", "giljo_mcp"] }
```

---

### 7. Aider ❌ (Single Agent)

**Multi-Agent Capabilities:**
- **None**
- Single conversational agent
- Multi-file editing but single context
- Sequential workflow (one task at a time)

**Strengths:**
- Git-focused (auto-commits with good messages)
- Multi-model support (Claude, OpenAI, DeepSeek, local models)
- Codebase mapping
- Voice input support

**Architecture to Use:**
```
❌ Background Service (BACKGROUND_SERVICE_ORCHESTRATION.md)

Multi-terminal approach:
  - Each terminal = one Aider instance = one agent
  - Background service generates prompts
  - Dashboard clipboard queue
  - Manual coordination via MCP
```

**Example:**
```bash
# Terminal 1: Database Agent
aider --model claude-3.7-sonnet
> [Paste database agent prompt]

# Terminal 2: Backend Agent
aider --model deepseek-chat-v3
> [Paste backend agent prompt]

# Agents report progress to MCP via embedded instructions:
# "After completing schema, run: curl -X POST http://localhost:7272/api/messages ..."
```

---

## Universal Architecture: GiljoAI MCP as Multi-Tool Orchestrator

### The Vision

**GiljoAI MCP should support ALL AI coding tools**, not just Claude Code!

```
┌─────────────────────────────────────────────────┐
│           GiljoAI MCP Orchestrator              │
│         (Universal Coordination Layer)          │
├─────────────────────────────────────────────────┤
│ • Project management                            │
│ • Mission generation                            │
│ • Agent planning                                │
│ • Prompt generation (tool-specific)             │
│ • Dashboard monitoring                          │
│ • Cross-agent coordination                      │
└─────────────────────────────────────────────────┘
         │
         │ Adapts to tool capabilities
         ↓
┌──────────────┬──────────────┬─────────────────┐
│              │              │                 │
│ Claude Code  │  Gemini CLI  │   Cursor        │  ← Sub-Agent Tools
│ Continue.dev │              │                 │
│              │              │                 │
│ [Task tool]  │ [/subagents] │ [Parallel CLI]  │
│              │              │                 │
│ 1 terminal   │ 1 terminal   │ Git worktrees   │
│ N sub-agents │ N sub-agents │ N sessions      │
└──────────────┴──────────────┴─────────────────┘

┌──────────────┬──────────────┬─────────────────┐
│              │              │                 │
│ Windsurf     │  Codex CLI   │   Aider         │  ← Single-Agent Tools
│              │              │                 │
│ [Single UI]  │ [Single CLI] │ [Single conv]   │
│              │              │                 │
│ N terminals  │ N terminals  │ N terminals     │
│ Clipboard    │ Clipboard    │ Clipboard       │
└──────────────┴──────────────┴─────────────────┘
```

### Dual Architecture Implementation

**1. Sub-Agent Architecture** (for Claude Code, Gemini CLI, Cursor, Continue.dev)

```python
# Tool-specific orchestrator
if tool == "claude_code":
    # Use Task tool
    spawn_subagent("database-expert", mission)

elif tool == "gemini_cli":
    # Use /subagents command or spawn instances
    run_command("/subagents create database " + mission)

elif tool == "cursor":
    # Use git worktrees + Cursor CLI
    create_worktree("feature/database")
    spawn_cursor_in_worktree(worktree_path, mission)

elif tool == "continue":
    # Use Workflows
    trigger_workflow("database-agent", mission)
```

**2. Background Service Architecture** (for Windsurf, Codex, Aider)

```python
# Dashboard clipboard queue
if tool in ["windsurf", "codex", "aider"]:
    # Generate prompt
    prompt = generate_tool_specific_prompt(tool, agent, mission)

    # Save to dashboard
    save_to_clipboard_queue(agent.id, prompt)

    # User manually opens terminal and pastes
    # Agent reports back via MCP tools or embedded curl commands
```

---

## Recommended Implementation: Tool Detection

### Phase 1: Tool Configuration

**In config.yaml:**
```yaml
ai_coding_tool:
  primary: claude_code  # User's preferred tool

  capabilities:
    claude_code:
      multi_agent: true
      method: task_tool
      terminals_needed: 1

    gemini_cli:
      multi_agent: true
      method: subagents_command
      terminals_needed: 1

    cursor:
      multi_agent: true
      method: git_worktrees
      terminals_needed: variable

    continue:
      multi_agent: true
      method: workflows
      terminals_needed: 1

    windsurf:
      multi_agent: false
      method: clipboard_queue
      terminals_needed: per_agent

    codex:
      multi_agent: false
      method: clipboard_queue
      terminals_needed: per_agent
      mcp_support: true

    aider:
      multi_agent: false
      method: clipboard_queue
      terminals_needed: per_agent
```

### Phase 2: Adaptive Prompt Generation

```python
# src/giljo_mcp/tools/universal_prompt_generator.py

def generate_orchestrator_prompt(project_id: str, tool: str) -> str:
    """
    Generate tool-specific orchestrator prompt.
    """
    if tool in ["claude_code", "gemini_cli", "cursor", "continue"]:
        return generate_subagent_prompt(project_id, tool)
    else:
        return generate_clipboard_prompt(project_id, tool)


def generate_subagent_prompt(project_id: str, tool: str) -> str:
    """
    For tools with native sub-agent support.
    """
    prompt = f"""# GiljoAI MCP Orchestration - {tool.upper()}

## Phase 1: Read Project
mcp__giljo-mcp__list_projects to get {project_id}

## Phase 2: Spawn Sub-Agents
"""

    if tool == "claude_code":
        prompt += """
Use Task tool to spawn agents:

Task(
    subagent_type="database-expert",
    description="Design schema",
    prompt="[mission from MCP]"
)
"""
    elif tool == "gemini_cli":
        prompt += """
Use /subagents command:

/subagents create database "Design schema based on MCP mission..."
/subagents create backend "Implement API based on MCP mission..."
"""
    elif tool == "cursor":
        prompt += """
Create git worktrees and spawn Cursor instances:

Bash: git worktree add ../db-work feature/database
Bash: cursor ../db-work
[In new Cursor: load database agent mission]
"""
    elif tool == "continue":
        prompt += """
Trigger Continue.dev workflows:

[Configure workflows in .continue/config.json]
Trigger each workflow with MCP mission
"""

    return prompt


def generate_clipboard_prompt(project_id: str, tool: str) -> str:
    """
    For tools without native sub-agent support.

    Returns instructions to check dashboard clipboard queue.
    """
    return f"""# GiljoAI MCP Orchestration - {tool.upper()}

## Background Service Running

A background orchestrator has generated agent-specific prompts.

## Next Steps

1. Open the GiljoAI Dashboard: http://localhost:7274
2. Navigate to "Agent Prompt Queue"
3. You'll see {tool}-specific prompts for each agent
4. For each ready agent:
   - Click "Copy Prompt"
   - Open new terminal: `{tool}`
   - Paste prompt
   - Agent will auto-coordinate via MCP

Agents will report progress to dashboard automatically.
"""
```

### Phase 3: Dashboard Tool Selector

```vue
<!-- frontend/src/views/ProjectActivation.vue -->

<template>
  <v-card>
    <v-card-title>Activate Project: {{ project.name }}</v-card-title>

    <v-card-text>
      <v-select
        v-model="selectedTool"
        :items="availableTools"
        label="AI Coding Tool"
        hint="Select your preferred AI coding assistant"
      />

      <v-alert
        v-if="toolInfo"
        :type="toolInfo.multi_agent ? 'success' : 'info'"
        class="mt-4"
      >
        <strong>{{ selectedTool }}:</strong> {{ toolInfo.description }}
        <br>
        Terminals needed: {{ toolInfo.terminals_needed }}
        <br>
        Method: {{ toolInfo.method }}
      </v-alert>
    </v-card-text>

    <v-card-actions>
      <v-btn
        color="primary"
        @click="activateProject"
      >
        Generate {{ selectedTool }} Prompt
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  data() {
    return {
      selectedTool: 'claude_code',
      availableTools: [
        { value: 'claude_code', title: 'Claude Code (Sub-Agents)' },
        { value: 'gemini_cli', title: 'Gemini CLI (Sub-Agents)' },
        { value: 'cursor', title: 'Cursor (Parallel)' },
        { value: 'continue', title: 'Continue.dev (Workflows)' },
        { value: 'windsurf', title: 'Windsurf (Cascade)' },
        { value: 'codex', title: 'Codex CLI' },
        { value: 'aider', title: 'Aider' }
      ],
      toolCapabilities: {
        claude_code: {
          multi_agent: true,
          method: 'Task tool (built-in)',
          terminals_needed: 1,
          description: 'Best choice - native sub-agents with isolated contexts'
        },
        gemini_cli: {
          multi_agent: true,
          method: '/subagents command',
          terminals_needed: 1,
          description: 'Native sub-agent support via CLI commands'
        },
        cursor: {
          multi_agent: true,
          method: 'Git worktrees + Parallel CLI',
          terminals_needed: 'Variable (per worktree)',
          description: 'Parallel execution via git worktrees'
        },
        continue: {
          multi_agent: true,
          method: 'Background workflows',
          terminals_needed: 1,
          description: 'Continuous background agents'
        },
        windsurf: {
          multi_agent: false,
          method: 'Dashboard clipboard queue',
          terminals_needed: 'One per agent',
          description: 'Manual terminal opening with smart prompts'
        },
        codex: {
          multi_agent: false,
          method: 'Dashboard clipboard queue',
          terminals_needed: 'One per agent',
          description: 'MCP-integrated, clipboard workflow'
        },
        aider: {
          multi_agent: false,
          method: 'Dashboard clipboard queue',
          terminals_needed: 'One per agent',
          description: 'Git-focused, multi-model support'
        }
      }
    }
  },

  computed: {
    toolInfo() {
      return this.toolCapabilities[this.selectedTool]
    }
  },

  methods: {
    async activateProject() {
      const response = await fetch(`/api/projects/${this.project.id}/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: this.selectedTool })
      })

      const data = await response.json()
      this.showPrompt(data.prompt)
    }
  }
}
</script>
```

---

## Summary: Why You Need Both Architectures

### ✅ Sub-Agent Architecture (INTEGRATE_CLAUDE_CODE.md)

**For:** Claude Code, Gemini CLI, Cursor, Continue.dev

**Benefits:**
- 1 terminal (or minimal terminals)
- Native multi-agent support
- Automatic coordination
- Isolated context pools
- Cleaner user experience

**Use When:** Tool has native sub-agent capabilities

---

### ✅ Background Service Architecture (BACKGROUND_SERVICE_ORCHESTRATION.md)

**For:** Windsurf, Codex CLI, Aider, future tools

**Benefits:**
- Works with ANY tool (universal)
- Smart prompt generation
- Dashboard clipboard queue
- Dependency tracking
- MCP coordination

**Use When:** Tool lacks native multi-agent support

---

## Conclusion

**Your instinct was 100% correct!** You need BOTH architectures to make GiljoAI MCP a universal orchestration platform.

### Implementation Priority:

1. **Phase 1**: Implement Sub-Agent architecture for Claude Code (most mature)
2. **Phase 2**: Implement Background Service architecture for single-agent tools
3. **Phase 3**: Add tool detection and adaptive prompt generation
4. **Phase 4**: Test with Gemini CLI, Cursor
5. **Phase 5**: Add support for Windsurf, Codex, Aider
6. **Phase 6**: Community contributions for other tools

This positions GiljoAI MCP as the **universal orchestration layer** for ANY AI coding tool, making it incredibly valuable regardless of which tool developers prefer!
