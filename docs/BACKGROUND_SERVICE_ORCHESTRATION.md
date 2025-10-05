# Background Service Orchestration Strategy

## Question: Can We Auto-Spawn Claude Code Terminals?

**User's Vision**: Instead of manually pasting prompts, use Claude Code's background service capability to:
1. Run a background orchestrator service in the first Claude Code window
2. This service monitors MCP for new agents
3. When agents are created, automatically spawn NEW Claude Code terminal windows
4. Inject agent-specific prompts into those new terminals
5. Monitor messages and coordinate across terminals programmatically

---

## Technical Feasibility Analysis

### What Claude Code Background Services CAN Do

Based on research (as of 2025):

✅ **Run Long-Lived Processes**:
```bash
# Claude Code can run this in background
Bash(run_in_background=true, command="python monitor_service.py")
```

✅ **Monitor Logs in Real-Time**:
- Background processes output to logs
- Claude Code can read logs with `BashOutput` tool
- Can react to log events

✅ **Persist Across Sessions**:
- Background tasks continue even if you switch contexts
- Task state preserved

✅ **Execute OS Commands**:
```bash
# Background service can run any bash/cmd command
python script.py
curl http://api.example.com
npm run dev
```

### What Claude Code Background Services CANNOT Do (Limitations)

❌ **Spawn New Claude Code Instances**:
- Claude Code doesn't expose an API to spawn new terminal windows
- `claude code` CLI doesn't accept prompt injection via stdin/args
- No programmatic interface to create new Claude sessions

❌ **Inject Prompts into New Windows**:
- No mechanism to pass text to a new Claude Code instance
- No IPC (inter-process communication) for Claude terminals

❌ **Control Other Claude Code Terminals**:
- Each Claude Code session is isolated
- No cross-terminal communication built-in

### Alternative: What We CAN Automate

While we **can't spawn new Claude Code terminals programmatically**, we CAN:

✅ **Background Orchestrator Service** that:
1. Monitors MCP database for new agents
2. Generates ready-to-paste prompts
3. Saves prompts to files or shows in dashboard
4. Notifies user when prompts are ready
5. Coordinates agent status via MCP

✅ **Manual Terminal Opening with Auto-Paste**:
- User opens N terminal windows manually (one-time)
- Each runs a "listening agent" that polls MCP
- When work is assigned, agent auto-activates
- Similar to old multi-terminal setup but cleaner

---

## Proposed Architecture: Hybrid Approach

### Option 1: Background Orchestrator + Dashboard Prompt Queue (RECOMMENDED)

**How It Works**:

```
┌─────────────────────────────────────────────┐
│ Terminal 1: Claude Code (Orchestrator)      │
│                                             │
│ > python start_orchestrator.py              │
│                                             │
│ [Background Service Running]                │
│ • Monitors MCP for new agents               │
│ • Generates agent prompts                   │
│ • Saves to MCP message queue                │
│ • Updates dashboard                         │
└─────────────────────────────────────────────┘
         │
         │ (writes prompts to MCP)
         ↓
┌─────────────────────────────────────────────┐
│ GiljoAI MCP Dashboard                       │
│                                             │
│ 📋 Ready Prompts (5)                        │
│                                             │
│ ┌─────────────────────────────────────┐   │
│ │ Agent: Database Expert               │   │
│ │ Status: Ready                        │   │
│ │ [Copy Prompt] [Mark as Spawned]     │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ ┌─────────────────────────────────────┐   │
│ │ Agent: Backend Developer             │   │
│ │ Status: Ready                        │   │
│ │ [Copy Prompt]                        │   │
│ └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         │
         │ (user copies prompts)
         ↓
┌─────────────────────────────────────────────┐
│ Terminal 2: Claude Code (Database Agent)    │
│ > [User pastes prompt]                      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Terminal 3: Claude Code (Backend Agent)     │
│ > [User pastes prompt]                      │
└─────────────────────────────────────────────┘
```

**Benefits**:
- ✅ Uses background service for monitoring/coordination
- ✅ Dashboard shows ready-to-paste prompts (1-click copy)
- ✅ User opens terminals as needed (not all at once)
- ✅ Cleaner than old manual workflow
- ✅ Works within Claude Code limitations

**User Experience**:
1. Activate project in dashboard → orchestrator background service starts
2. Dashboard shows "5 agents ready" with copy buttons
3. User opens Terminal 2, clicks "Copy Prompt" for Database Agent, pastes
4. User opens Terminal 3, clicks "Copy Prompt" for Backend Agent, pastes
5. Agents auto-coordinate via MCP messages

**Implementation**:

```python
# start_orchestrator.py (runs in background)

import time
from giljo_mcp import get_db_session
from giljo_mcp.models import Project, Agent
from giljo_mcp.tools.prompt_generator import generate_agent_prompt

def orchestrator_background_service(project_id):
    """
    Background service that monitors MCP and generates agent prompts.
    """
    print(f"🚀 Orchestrator service started for project {project_id}")

    while True:
        with get_db_session() as session:
            # Check for agents that need prompts generated
            agents = session.query(Agent).filter_by(
                project_id=project_id,
                status="pending_prompt"  # New status
            ).all()

            for agent in agents:
                print(f"📝 Generating prompt for {agent.name}")

                # Generate prompt
                prompt = generate_agent_prompt(agent)

                # Save to agent metadata
                agent.meta_data = agent.meta_data or {}
                agent.meta_data['generated_prompt'] = prompt
                agent.status = "prompt_ready"

                session.commit()

                print(f"✓ Prompt ready for {agent.name}")

                # Notify dashboard via WebSocket
                notify_dashboard(agent.id, "prompt_ready")

        time.sleep(5)  # Poll every 5 seconds

if __name__ == "__main__":
    import sys
    project_id = sys.argv[1]
    orchestrator_background_service(project_id)
```

**Dashboard Component**:

```vue
<!-- AgentPromptQueue.vue -->
<template>
  <v-card>
    <v-card-title>Ready Agent Prompts</v-card-title>
    <v-card-text>
      <v-list>
        <v-list-item
          v-for="agent in readyAgents"
          :key="agent.id"
        >
          <v-list-item-title>{{ agent.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ agent.role }}</v-list-item-subtitle>

          <template v-slot:append>
            <v-btn
              icon="mdi-content-copy"
              @click="copyPrompt(agent)"
              color="primary"
            >
              Copy Prompt
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  computed: {
    readyAgents() {
      return this.$store.state.agents.filter(
        a => a.status === 'prompt_ready'
      )
    }
  },

  methods: {
    copyPrompt(agent) {
      const prompt = agent.meta_data.generated_prompt
      navigator.clipboard.writeText(prompt)

      // Show toast
      this.$toast.success(`Prompt copied for ${agent.name}`)

      // Optionally mark as "spawned" so it moves to another section
      this.markAsSpawned(agent.id)
    }
  }
}
</script>
```

---

### Option 2: Pre-Spawned Listening Agents (Advanced)

**How It Works**:

User opens 5 Claude Code terminals at session start. Each runs a "listening agent" that polls MCP for assigned work.

```
Terminal 1: Orchestrator (active)
Terminal 2: Listener Agent 1 (idle, polling MCP)
Terminal 3: Listener Agent 2 (idle, polling MCP)
Terminal 4: Listener Agent 3 (idle, polling MCP)
Terminal 5: Listener Agent 4 (idle, polling MCP)
```

**When orchestrator creates work**:
1. Orchestrator writes agent mission to MCP
2. Listener Agent 2 sees: "I'm assigned Database work"
3. Listener Agent 2 auto-activates and starts working
4. Reports back to MCP

**Implementation**:

```python
# agent_listener.py (paste into each idle terminal)

import time
from giljo_mcp import get_db_session
from giljo_mcp.models import Agent

def agent_listener(agent_id):
    """
    Polls MCP for work assigned to this agent.
    When work appears, auto-activates.
    """
    print(f"👂 Listening agent {agent_id} started. Waiting for work...")

    while True:
        with get_db_session() as session:
            agent = session.query(Agent).filter_by(id=agent_id).first()

            if agent.status == "assigned_work":
                print(f"🎯 Work assigned! Mission: {agent.mission}")

                # Auto-activate by calling Claude Code's sub-agent system
                # Actually, we can't programmatically trigger Claude...
                # So instead, print the prompt for user to see

                print("\n" + "="*60)
                print("AGENT ACTIVATED - PROMPT BELOW:")
                print("="*60)
                print(agent.meta_data['generated_prompt'])
                print("="*60)

                # Update status
                agent.status = "activated"
                session.commit()

                break  # Exit listener, agent is now active

        time.sleep(3)

if __name__ == "__main__":
    import sys
    agent_id = sys.argv[1]
    agent_listener(agent_id)
```

**Problem**: This still requires user to read/paste the prompt. Can't auto-inject into Claude.

---

### Option 3: Terminal Multiplexer (tmux/screen) with Scripted Panes

**Concept**: Use `tmux` or Windows Terminal's automation features to:
1. Create multiple panes programmatically
2. Send text to each pane
3. Each pane runs Claude Code

**Linux/Mac Example (tmux)**:

```bash
#!/bin/bash
# spawn_agents.sh

# Create tmux session with multiple panes
tmux new-session -d -s giljo_orchestration

# Split into 5 panes
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

# Pane 0: Orchestrator
tmux send-keys -t giljo_orchestration:0.0 "claude code" C-m
sleep 2
tmux send-keys -t giljo_orchestration:0.0 "I am the orchestrator for project XYZ..." C-m

# Pane 1: Database Agent
tmux send-keys -t giljo_orchestration:0.1 "claude code" C-m
sleep 2
tmux send-keys -t giljo_orchestration:0.1 "I am the database agent..." C-m

# Pane 2: Backend Agent
tmux send-keys -t giljo_orchestration:0.2 "claude code" C-m
sleep 2
tmux send-keys -t giljo_orchestration:0.2 "I am the backend agent..." C-m

# Attach to session
tmux attach-session -t giljo_orchestration
```

**Windows Terminal Example (JSON config)**:

```json
// profiles.json (Windows Terminal)
{
  "profiles": {
    "list": [
      {
        "name": "GiljoAI Orchestrator",
        "commandline": "claude code",
        "startingDirectory": "C:\\Projects\\MyProduct",
        "tabTitle": "Orchestrator"
      },
      {
        "name": "GiljoAI Database Agent",
        "commandline": "claude code",
        "tabTitle": "DB Agent"
      }
    ]
  },
  "actions": [
    {
      "command": {
        "action": "sendInput",
        "input": "Paste orchestrator prompt here..."
      },
      "keys": "ctrl+shift+1"
    }
  ]
}
```

**Challenge**:
- ❌ `claude code` doesn't accept prompt via stdin or --prompt flag
- ❌ Sending text to Claude Code terminal doesn't work (it's interactive, not stdin)

---

## The Reality: What We Can Actually Automate

Given Claude Code's current architecture (2025), here's what's **actually possible**:

### ✅ Fully Automated:

1. **Background Orchestrator Service**:
   - Monitors MCP for project activation
   - Generates comprehensive mission
   - Creates agent records in database
   - Generates ready-to-paste prompts
   - Updates dashboard in real-time

2. **Dashboard Prompt Queue**:
   - Shows list of agents with "Copy Prompt" buttons
   - One-click copy to clipboard
   - Tracks which agents have been spawned
   - Shows agent status (ready → spawned → working → completed)

3. **Agent Coordination via MCP**:
   - Agents send messages through MCP
   - Dashboard shows live activity
   - Handoffs automated via message queue
   - No manual coordination needed

### ❌ NOT Possible (Without Claude Code API Changes):

1. **Programmatically spawning new Claude Code terminals**
2. **Auto-injecting prompts into Claude Code sessions**
3. **Cross-terminal Claude Code communication**

---

## Recommended Implementation: "Smart Clipboard Workflow"

Combine the best of automation with realistic constraints:

### Step 1: Orchestrator Generates Everything

```python
# In Claude Code Terminal 1 (background service)
Bash(
    command="python orchestrator_service.py --project-id=abc-123",
    run_in_background=true
)

# Orchestrator:
# 1. Reads project vision docs
# 2. Generates mission → writes to MCP
# 3. Creates 5 agent records in MCP
# 4. Generates 5 agent-specific prompts
# 5. Saves prompts to MCP + notifies dashboard
```

### Step 2: Dashboard Shows Clipboard Queue

```
┌──────────────────────────────────────────────────┐
│ GiljoAI Dashboard - Ready Agents                 │
├──────────────────────────────────────────────────┤
│                                                  │
│ 🟢 Database Expert        [Copy Prompt] [Done]  │
│    Mission: Design checkout schema...            │
│    Status: Prompt Ready                          │
│                                                  │
│ 🟡 Backend Developer      [Copy Prompt]         │
│    Mission: Implement payment API...             │
│    Status: Waiting for Database                  │
│                                                  │
│ ⚪ Integration Tester     [Copy Prompt]         │
│    Mission: Test checkout flow...                │
│    Status: Waiting for Backend                   │
│                                                  │
│ ⚪ Security Auditor       [Copy Prompt]         │
│ ⚪ Documenter             [Copy Prompt]         │
└──────────────────────────────────────────────────┘
```

### Step 3: User Opens Terminals as Needed

**Scenario**: Database work is ready

1. User sees 🟢 Database Expert is ready
2. Clicks **[Copy Prompt]** → copied to clipboard
3. Opens new terminal: `claude code`
4. Pastes prompt (Ctrl+V)
5. Database agent starts working
6. Clicks **[Done]** → agent marked as "spawned"

**Scenario**: Backend work becomes ready after database completes

1. Dashboard shows 🟢 Backend Developer (was 🟡 waiting)
2. User clicks **[Copy Prompt]**
3. Opens Terminal 3, pastes
4. Backend agent starts

### Step 4: Agents Auto-Coordinate

Each agent:
- Reads context from MCP
- Executes work
- Reports status via `mcp__giljo-mcp__send_message`
- Dashboard updates in real-time
- No manual coordination needed

---

## Code Example: Complete Smart Clipboard Workflow

### 1. Orchestrator Background Service

```python
# src/giljo_mcp/orchestrator_service.py

import asyncio
from giljo_mcp import get_db_session
from giljo_mcp.models import Project, Agent
from giljo_mcp.tools.prompt_generator import generate_agent_prompt
from giljo_mcp.websocket_client import broadcast_update

async def orchestrator_service(project_id: str):
    """
    Background orchestrator that:
    1. Generates project mission
    2. Creates agents
    3. Generates prompts for clipboard
    4. Monitors agent completion
    5. Triggers dependent agents
    """
    print(f"🎯 Starting orchestrator for project {project_id}")

    # Phase 1: Mission Generation
    print("Phase 1: Reading vision docs and generating mission...")
    mission = await generate_project_mission(project_id)

    with get_db_session() as session:
        project = session.query(Project).filter_by(id=project_id).first()
        project.mission = mission
        project.activation_status = "mission_generated"
        session.commit()

    await broadcast_update("project_updated", {"mission": mission})
    print(f"✓ Mission generated: {mission[:100]}...")

    # Phase 2: Agent Planning
    print("Phase 2: Planning agent strategy...")
    agent_plan = plan_agents_for_mission(mission)

    for agent_spec in agent_plan:
        with get_db_session() as session:
            agent = Agent(
                project_id=project_id,
                name=agent_spec['name'],
                role=agent_spec['role'],
                mission=agent_spec['mission'],
                status="prompt_pending",
                meta_data={'dependencies': agent_spec.get('depends_on', [])}
            )
            session.add(agent)
            session.commit()
            agent_id = agent.id

        print(f"✓ Planned agent: {agent_spec['name']}")

    # Phase 3: Generate Prompts
    print("Phase 3: Generating agent prompts for clipboard...")

    with get_db_session() as session:
        agents = session.query(Agent).filter_by(
            project_id=project_id,
            status="prompt_pending"
        ).all()

        for agent in agents:
            prompt = generate_agent_prompt(agent)

            agent.meta_data = agent.meta_data or {}
            agent.meta_data['generated_prompt'] = prompt

            # Check dependencies
            deps = agent.meta_data.get('dependencies', [])
            if not deps:
                agent.status = "prompt_ready"  # Ready to spawn
            else:
                agent.status = "waiting"  # Waiting for dependencies

            session.commit()

            await broadcast_update("agent_prompt_ready", {
                "agent_id": agent.id,
                "agent_name": agent.name,
                "status": agent.status
            })

            print(f"✓ Prompt ready: {agent.name}")

    print("✓ All prompts generated. Dashboard updated.")

    # Phase 4: Monitor and Release Waiting Agents
    print("Phase 4: Monitoring agent completion...")

    while True:
        await asyncio.sleep(5)

        with get_db_session() as session:
            # Check for completed agents
            completed = session.query(Agent).filter_by(
                project_id=project_id,
                status="completed"
            ).all()

            completed_names = {a.name for a in completed}

            # Check waiting agents
            waiting = session.query(Agent).filter_by(
                project_id=project_id,
                status="waiting"
            ).all()

            for agent in waiting:
                deps = agent.meta_data.get('dependencies', [])

                # Check if all dependencies are complete
                if all(dep in completed_names for dep in deps):
                    agent.status = "prompt_ready"
                    session.commit()

                    await broadcast_update("agent_unblocked", {
                        "agent_id": agent.id,
                        "agent_name": agent.name
                    })

                    print(f"✓ Agent unblocked: {agent.name}")

            # Check if all agents complete
            all_agents = session.query(Agent).filter_by(
                project_id=project_id
            ).all()

            if all(a.status == "completed" for a in all_agents):
                print("🎉 All agents completed! Project done.")
                project = session.query(Project).filter_by(id=project_id).first()
                project.status = "completed"
                session.commit()
                break

if __name__ == "__main__":
    import sys
    asyncio.run(orchestrator_service(sys.argv[1]))
```

### 2. Dashboard Component

```vue
<!-- frontend/src/components/AgentClipboardQueue.vue -->

<template>
  <v-card>
    <v-card-title>
      Agent Prompt Queue
      <v-chip
        :color="readyCount > 0 ? 'success' : 'default'"
        class="ml-2"
      >
        {{ readyCount }} Ready
      </v-chip>
    </v-card-title>

    <v-card-text>
      <v-list>
        <v-list-item
          v-for="agent in agents"
          :key="agent.id"
          :class="getAgentClass(agent)"
        >
          <template v-slot:prepend>
            <v-icon :color="getStatusColor(agent.status)">
              {{ getStatusIcon(agent.status) }}
            </v-icon>
          </template>

          <v-list-item-title>{{ agent.name }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ agent.mission.substring(0, 100) }}...
          </v-list-item-subtitle>

          <template v-slot:append>
            <v-btn
              v-if="agent.status === 'prompt_ready'"
              color="primary"
              variant="elevated"
              @click="copyPrompt(agent)"
            >
              <v-icon left>mdi-content-copy</v-icon>
              Copy Prompt
            </v-btn>

            <v-chip
              v-else
              :color="getStatusColor(agent.status)"
              variant="flat"
            >
              {{ getStatusLabel(agent.status) }}
            </v-chip>
          </template>

          <v-expand-transition>
            <div v-if="agent.showPrompt" class="mt-2">
              <v-textarea
                :value="agent.meta_data.generated_prompt"
                readonly
                rows="10"
                variant="outlined"
                density="compact"
              />
            </div>
          </v-expand-transition>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>

<script>
import { useAgentStore } from '@/stores/agents'

export default {
  setup() {
    const agentStore = useAgentStore()
    return { agentStore }
  },

  computed: {
    agents() {
      return this.agentStore.agents
    },

    readyCount() {
      return this.agents.filter(a => a.status === 'prompt_ready').length
    }
  },

  methods: {
    async copyPrompt(agent) {
      const prompt = agent.meta_data.generated_prompt

      await navigator.clipboard.writeText(prompt)

      this.$toast.success(`Prompt copied for ${agent.name}!`)

      // Mark as spawned
      agent.status = 'spawned'
      await this.agentStore.updateAgentStatus(agent.id, 'spawned')
    },

    getStatusColor(status) {
      const colors = {
        'prompt_ready': 'success',
        'waiting': 'warning',
        'spawned': 'info',
        'working': 'primary',
        'completed': 'success'
      }
      return colors[status] || 'default'
    },

    getStatusIcon(status) {
      const icons = {
        'prompt_ready': 'mdi-check-circle',
        'waiting': 'mdi-clock-outline',
        'spawned': 'mdi-rocket-launch',
        'working': 'mdi-cog',
        'completed': 'mdi-check-all'
      }
      return icons[status] || 'mdi-help-circle'
    },

    getStatusLabel(status) {
      return status.replace('_', ' ').toUpperCase()
    },

    getAgentClass(agent) {
      return {
        'agent-ready': agent.status === 'prompt_ready',
        'agent-waiting': agent.status === 'waiting'
      }
    }
  }
}
</script>

<style scoped>
.agent-ready {
  background-color: rgba(76, 175, 80, 0.1);
}

.agent-waiting {
  opacity: 0.6;
}
</style>
```

---

## Summary: What's Possible vs. What's Not

### ✅ **POSSIBLE** (Recommended Implementation):

1. **Background orchestrator service** in Claude Code Terminal 1
2. **Auto-generation of all agent prompts** saved to MCP
3. **Dashboard with "Copy Prompt" buttons** for each agent
4. **Dependency tracking** (agents auto-unblock when deps complete)
5. **Real-time coordination** via MCP message queue
6. **Live dashboard monitoring** of all agent activity

### ❌ **NOT POSSIBLE** (Claude Code Limitations):

1. Programmatically spawning new Claude Code terminal instances
2. Auto-injecting prompts into Claude Code sessions
3. Terminal-to-terminal Claude Code communication

### 🔄 **WORKAROUND** (Best UX):

**"Smart Clipboard Workflow"**:
- Orchestrator does 90% of work (mission, planning, prompt generation)
- Dashboard shows ready-to-copy prompts with visual status
- User opens terminals and pastes (10% manual, but clean)
- Agents coordinate automatically via MCP

**User Experience**:
- Old way: 5 terminals, 5 manual prompts, manual coordination = 🤯
- New way: 1 orchestrator (auto), dashboard (auto), copy/paste prompts = 😊

---

## Future Enhancement: Claude Code API Request

If Anthropic adds these features to Claude Code:

```bash
# Wishlist API
claude code --prompt "your prompt here"  # Accept prompt via CLI
claude code --from-file prompt.txt       # Load prompt from file
claude code --daemon --listen-mcp        # Listen for MCP prompt injection
```

Then full automation becomes possible. Worth submitting feature request!

---

## Conclusion

**Short Answer**: No, we can't fully automate terminal spawning/prompt injection with current Claude Code.

**But**: We can build a "Smart Clipboard Workflow" that's 90% automated and much cleaner than manual multi-terminal orchestration.

**Recommendation**: Implement Option 1 (Background Orchestrator + Dashboard Clipboard Queue) as described above.
