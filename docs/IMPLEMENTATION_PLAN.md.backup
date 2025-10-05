# GiljoAI MCP Implementation Plan
**Created**: October 5, 2025
**Target**: Localhost Beta Ready
**Timeline**: 2 Weeks (10 working days)

---

## Executive Summary

Based on comprehensive analysis of recent documentation (Oct 3-5), the GiljoAI MCP project has a **solid foundation** with 80% of core functionality complete. The critical 20% needed for a working localhost beta focuses on **Claude Code sub-agent integration**.

### Current State ✅
- ✅ Localhost installation working
- ✅ PostgreSQL 18 database operational
- ✅ Product/Project/Agent/Task system functional
- ✅ WebSocket real-time updates working
- ✅ Multi-tenant isolation complete
- ✅ Cross-platform installer production-ready

### Critical Gaps ⚠️
- ❌ Claude Code agent profiles not created
- ❌ Orchestrator prompt generation missing
- ❌ Project activation flow not implemented
- ❌ Tool detection wizard not built
- ❌ LAN/WAN deployment features not implemented

### Strategy
**Phase 1 (This Plan)**: Focus exclusively on Claude Code integration for localhost beta
**Phase 2 (Future)**: LAN/WAN deployment and multi-tool support

---

## Table of Contents

1. [Phase 1: Claude Code Integration (Week 1)](#phase-1-claude-code-integration-week-1)
2. [Phase 2: Dashboard & Testing (Week 2)](#phase-2-dashboard--testing-week-2)
3. [Phase 3: LAN/WAN Deployment (Future)](#phase-3-lanwan-deployment-future)
4. [Testing Strategy](#testing-strategy)
5. [Success Criteria](#success-criteria)
6. [Risk Mitigation](#risk-mitigation)
7. [Daily Execution Plan](#daily-execution-plan)

---

## Phase 1: Claude Code Integration (Week 1)

### Goal
Enable complete Claude Code sub-agent workflow: Project Activation → Orchestrator Prompt → Sub-Agent Spawning → Real-time Monitoring

### Day 1-2: Agent Profiles & Templates

#### Task 1.1: Create Agent Profile Directory Structure
**Priority**: 🔴 CRITICAL
**Estimated Time**: 30 minutes

```bash
# Create directory
mkdir -p C:/Projects/GiljoAI_MCP/claude_agents

# Verify in installer
# Ensure installer copies this to release variant
```

**Deliverables**:
- `claude_agents/` directory created
- Added to `.gitignore` exceptions (should be tracked)

---

#### Task 1.2: Write Claude Agent Profiles (8 files)
**Priority**: 🔴 CRITICAL
**Estimated Time**: 4-6 hours

**Reference**: `docs/INTEGRATE_CLAUDE_CODE.md` Appendix A

Create these files:

1. **giljo-orchestrator.md**
```markdown
---
name: giljo-orchestrator
description: Coordinates multi-agent GiljoAI MCP projects with mission generation
tools: Read, Write, Edit, Bash, mcp__giljo-mcp__*
model: sonnet
---

You are the GiljoAI Orchestrator - conductor of multi-agent projects.

## Core Responsibilities
1. Context Ingestion: Read project and vision docs from MCP
2. Mission Generation: Create comprehensive missions
3. Agent Planning: Determine agent types needed
4. Sub-Agent Spawning: Launch Claude Code sub-agents
5. Coordination: Manage handoffs and progress
6. Completion: Consolidate deliverables

## Workflow
[See docs/INTEGRATE_CLAUDE_CODE.md Appendix A for full content]
```

2. **giljo-database-expert.md** - PostgreSQL specialist
3. **giljo-backend-dev.md** - API implementation
4. **giljo-tester.md** - Integration testing
5. **giljo-security-auditor.md** - Security review
6. **giljo-architect.md** - System architecture
7. **giljo-researcher.md** - Research & discovery
8. **giljo-documenter.md** - Documentation

**Deliverables**:
- 8 complete agent .md files
- Each includes:
  - YAML frontmatter (name, description, tools, model)
  - MCP tool integration instructions
  - Workflow guidelines
  - Communication protocol
  - Best practices

**Testing**:
```bash
# Manual test: Copy one file to ~/.claude/agents/
cp claude_agents/giljo-orchestrator.md ~/.claude/agents/

# Open Claude Code, verify agent appears
claude code
# Type: /agents
# Should see: giljo-orchestrator
```

---

#### Task 1.3: Create Bootstrap Setup Documentation
**Priority**: 🟡 HIGH
**Estimated Time**: 1 hour

Create `docs/FIRST_TIME_SETUP.md`:

```markdown
# GiljoAI MCP - First Time Setup

## One-Time Agent Installation (5 minutes)

### Step 1: Open Claude Code
\`\`\`bash
claude code
\`\`\`

### Step 2: Paste Setup Command
\`\`\`
Copy all agent profiles from:
C:\\Projects\\GiljoAI_MCP\\claude_agents\\

To:
~/.claude/agents/

List each file as you copy and confirm when complete.
\`\`\`

### Step 3: Restart Claude Code

### Step 4: Verify Installation
\`\`\`bash
claude code
/agents
\`\`\`

You should see 8 giljo-* agents listed.

### Step 5: You're Ready!
Now you can activate projects and let the orchestrator coordinate everything.
```

**Deliverables**:
- `docs/FIRST_TIME_SETUP.md` created
- Clear step-by-step user instructions
- Verification commands included

---

### Day 2-3: Prompt Generation System

#### Task 1.4: Implement Orchestrator Prompt Generator
**Priority**: 🔴 CRITICAL
**Estimated Time**: 4-5 hours

Create `src/giljo_mcp/tools/prompt_generator.py`:

```python
"""
Orchestrator prompt generation for Claude Code integration.

Generates ready-to-paste prompts that:
1. Instruct orchestrator to read project from MCP
2. Tell orchestrator to read vision documents
3. Guide orchestrator to generate comprehensive mission
4. Provide agent spawning instructions
5. Setup dashboard communication protocol
"""

from typing import Dict, List
from ..database import get_db_session
from ..models import Project
from .claude_code_integration import get_claude_code_agent_type


def generate_orchestrator_prompt(project_id: str, tenant_key: str) -> str:
    """
    Generate complete orchestrator prompt for Claude Code.

    Args:
        project_id: Project to orchestrate
        tenant_key: Multi-tenant isolation key

    Returns:
        Formatted prompt ready to paste into Claude Code
    """
    with get_db_session() as session:
        project = session.query(Project).filter_by(
            id=project_id,
            tenant_key=tenant_key
        ).first()

        if not project:
            return "Error: Project not found"

        # Get vision document references
        vision_docs = project.meta_data.get("vision_docs", []) if project.meta_data else []
        description = project.meta_data.get("description", project.name) if project.meta_data else project.name

        prompt = f"""# GiljoAI MCP Orchestration Request

## Project Activation
**Project ID**: {project_id}
**Project Name**: {project.name}
**Status**: Ready for orchestration

---

## Your Mission as Orchestrator

You are the **giljo-orchestrator** agent coordinating this multi-agent project.

### Phase 1: Context Ingestion & Mission Generation

1. **Read Project Details**:
   Use `mcp__giljo-mcp__list_projects` to get project record.
   Project ID: {project_id}

2. **Read Vision Documents**:
   The project references these vision documents:
"""

        for doc in vision_docs:
            prompt += f"   - `{doc}`\n"

        prompt += f"""
   Use `mcp__giljo-mcp__discover_context` and `mcp__giljo-mcp__search_context` to:
   - Understand user's product architecture
   - Identify technical constraints
   - Extract success criteria

3. **Read User's Project Description**:
   "{description}"

4. **Generate Comprehensive Mission**:
   Based on vision docs + description, create a detailed mission statement.

   **CRITICAL**: Update the project's mission field in MCP.
   The mission should be comprehensive enough that all sub-agents understand:
   - What to build
   - Why it matters
   - How it fits into the product
   - Success criteria

   Use the appropriate MCP tool to write the mission back to the project record.

### Phase 2: Agent Strategy Planning

5. **Determine Required Agents**:
   Analyze the mission and decide which specialized agents are needed.

   Available agent types:
   - giljo-database-expert (schema, queries, migrations)
   - giljo-backend-dev (API endpoints, business logic)
   - giljo-tester (integration tests, E2E tests)
   - giljo-security-auditor (security review, pen testing)
   - giljo-architect (system design, integration strategy)
   - giljo-documenter (technical docs, API docs)
   - giljo-researcher (technology evaluation, best practices)

6. **Register Agents in MCP**:
   For each agent you'll spawn, use `mcp__giljo-mcp__spawn_agent`:

   Example:
   ```
   spawn_agent(
     name="Checkout Database Agent",
     role="database",
     mission="Design checkout database schema with orders, payments,
              transactions tables. Ensure ACID compliance and proper
              indexing for <100ms query performance.",
     meta_data={{
       "deliverables": ["schema.sql", "migration scripts"],
       "context_budget": 50000,
       "depends_on": []
     }}
   )
   ```

   **Register all agents BEFORE spawning** so they appear on the dashboard.

### Phase 3: Sub-Agent Spawning & Coordination

7. **Spawn Sub-Agents Using Task Tool**:
   For each registered agent, create a Claude Code sub-agent:

   Example:
   ```
   Task(
     subagent_type="database-expert",
     description="Design checkout database schema",
     prompt='''
     You are working on: {project.name}

     **Your Specific Mission**:
     [Agent-specific mission from step 6]

     **Project Context**:
     - MCP Project ID: {project_id}
     - Your MCP Agent ID: [agent_id from spawn_agent]
     - Overall Project Mission: [comprehensive mission from step 4]

     **Your Workflow**:
     1. Read project context via MCP tools
     2. Complete your specific work
     3. Update status in MCP regularly:
        - Use mcp__giljo-mcp__send_message to report progress
        - Update your agent status (idle → working → completed)
     4. Report deliverables when complete

     **Deliverables Expected**:
     [List from step 6]

     Begin work now.
     '''
   )
   ```

8. **Monitor Progress**:
   - Check MCP message queue for agent updates
   - Track agent status changes (idle → working → completed)
   - Coordinate handoffs (Database → Backend → Tester)

9. **Collect Results**:
   - Each sub-agent returns a final report
   - Consolidate deliverables
   - Verify all work is complete

10. **Final Report**:
    Update project status in MCP:
    ```
    Project status: "completed"
    All deliverables: [list from each agent]
    Total context used: [sum from all agents]
    ```

---

## Begin Orchestration

Start with Phase 1: Read project details and generate the comprehensive mission.
"""

        return prompt


def format_vision_docs_list(vision_docs: List[str]) -> str:
    """Format vision document list for prompt."""
    if not vision_docs:
        return "   No vision documents provided"

    return "\n".join([f"   - `{doc}`" for doc in vision_docs])


def create_agent_spawn_template(agent_type: str, mission: str, agent_id: str, project_id: str) -> str:
    """
    Generate sub-agent spawn template.

    Args:
        agent_type: Claude Code agent type (e.g., 'database-expert')
        mission: Specific mission for this agent
        agent_id: MCP agent ID
        project_id: MCP project ID

    Returns:
        Task tool template for spawning this agent
    """
    return f"""Task(
    subagent_type="{agent_type}",
    description="{mission[:100]}...",
    prompt='''
    **Your Mission**: {mission}

    **MCP Integration**:
    - Project ID: {project_id}
    - Your Agent ID: {agent_id}

    **Workflow**:
    1. Read context: mcp__giljo-mcp__search_context
    2. Do your work
    3. Report status: mcp__giljo-mcp__send_message
    4. Update your status in MCP when complete

    Begin now.
    '''
)"""


# MCP Tool Registration
def register_prompt_tools(server):
    """Register prompt generation tools with MCP server."""

    @server.tool()
    def activate_project(project_id: str) -> Dict:
        """
        Activate a project and generate orchestrator prompt.

        Returns the ready-to-paste prompt for Claude Code.

        Args:
            project_id: Project to activate
        """
        from ..tenant import get_current_tenant_key
        tenant_key = get_current_tenant_key()

        prompt = generate_orchestrator_prompt(project_id, tenant_key)

        return {
            "success": True,
            "project_id": project_id,
            "prompt": prompt,
            "instructions": "Copy this prompt and paste into Claude Code CLI to begin orchestration."
        }
```

**Deliverables**:
- `prompt_generator.py` implemented
- `generate_orchestrator_prompt()` function
- `create_agent_spawn_template()` helper
- MCP tool registration

**Testing**:
```python
# Unit tests
pytest tests/unit/test_prompt_generator.py -xvs

# Manual test
from src.giljo_mcp.tools.prompt_generator import generate_orchestrator_prompt
prompt = generate_orchestrator_prompt("proj-123", "tenant-abc")
print(prompt)
# Should output full orchestrator prompt
```

---

#### Task 1.5: Add Project Activation API Endpoint
**Priority**: 🔴 CRITICAL
**Estimated Time**: 2 hours

Update `api/endpoints/projects.py`:

```python
from src.giljo_mcp.tools.prompt_generator import generate_orchestrator_prompt

@router.post("/projects/{project_id}/activate")
async def activate_project(project_id: str, request: Request):
    """
    Activate a project for orchestration.

    Generates the orchestrator prompt ready to paste into Claude Code.

    Returns:
        {
            "success": true,
            "project_id": "proj-123",
            "prompt": "# GiljoAI MCP Orchestration Request...",
            "instructions": "Copy this prompt..."
        }
    """
    try:
        # Get tenant key from session/auth
        tenant_key = get_tenant_key_from_session(request)

        # Generate prompt
        prompt = generate_orchestrator_prompt(project_id, tenant_key)

        # Check for errors
        if prompt.startswith("Error:"):
            raise HTTPException(status_code=404, detail=prompt)

        return {
            "success": True,
            "project_id": project_id,
            "prompt": prompt,
            "instructions": "Copy this prompt and paste into Claude Code CLI to begin orchestration."
        }

    except Exception as e:
        logger.error(f"Project activation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Deliverables**:
- Activation endpoint added to `projects.py`
- Error handling implemented
- Tenant key validation

**Testing**:
```bash
# API test
curl -X POST http://localhost:7272/api/projects/proj-123/activate

# Should return prompt JSON
```

---

### Day 4: Integration Testing

#### Task 1.6: End-to-End Activation Test
**Priority**: 🔴 CRITICAL
**Estimated Time**: 3-4 hours

**Test Scenario**:
1. Create test project with vision document
2. Call activation API
3. Verify prompt generation
4. Paste prompt into Claude Code
5. Verify orchestrator can read MCP
6. Confirm sub-agent spawn capability

**Test Script**:
```python
# tests/integration/test_project_activation.py

def test_complete_activation_flow():
    """Test full project activation workflow."""

    # Step 1: Setup test project
    project = create_test_project(
        name="Test E-Commerce Checkout",
        description="Build checkout flow with payments",
        vision_docs=["product_vision.md"]
    )

    # Step 2: Activate project
    response = client.post(f"/api/projects/{project.id}/activate")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "prompt" in data
    assert len(data["prompt"]) > 1000  # Substantial prompt

    # Step 3: Verify prompt content
    prompt = data["prompt"]
    assert "giljo-orchestrator" in prompt
    assert project.id in prompt
    assert "mcp__giljo-mcp__list_projects" in prompt
    assert "Task(" in prompt  # Sub-agent spawn instructions

    # Step 4: Manual validation
    print("\n" + "="*60)
    print("COPY THIS PROMPT AND PASTE INTO CLAUDE CODE:")
    print("="*60)
    print(prompt)
    print("="*60)
```

**Manual Testing Checklist**:
```
□ Project creation works
□ Vision document upload functional
□ Activation API returns 200
□ Prompt includes project details
□ Prompt includes vision doc references
□ Prompt includes MCP tool instructions
□ Prompt includes Task tool examples
□ Copy/paste into Claude Code works
□ Orchestrator recognizes giljo-orchestrator agent
□ Orchestrator can call mcp__giljo-mcp__* tools
```

---

## Phase 2: Dashboard & Testing (Week 2)

### Day 5-6: Dashboard Activation UI

#### Task 2.1: Add Activate Project Button
**Priority**: 🟡 HIGH
**Estimated Time**: 2 hours

Update `frontend/src/views/ProjectDetailView.vue`:

```vue
<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>{{ project.name }}</v-card-title>

          <v-card-text>
            <!-- Existing project details -->
            <v-list>
              <v-list-item>
                <v-list-item-title>Status</v-list-item-title>
                <v-list-item-subtitle>{{ project.status }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <v-list-item-title>Mission</v-list-item-title>
                <v-list-item-subtitle>
                  {{ project.mission || 'Not yet generated' }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <v-list-item-title>Vision Documents</v-list-item-title>
                <v-list-item-subtitle>
                  {{ visionDocs.length }} documents
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>

          <v-card-actions>
            <v-spacer />

            <!-- NEW: Activate Button -->
            <v-btn
              color="primary"
              size="large"
              @click="activateProject"
              :loading="activating"
              :disabled="project.status === 'completed'"
            >
              <v-icon left>mdi-play-circle</v-icon>
              Activate Project
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Orchestrator Prompt Dialog -->
    <OrchestratorPromptDialog
      v-model="showPromptDialog"
      :prompt="orchestratorPrompt"
      :project-name="project.name"
      @copied="onPromptCopied"
    />
  </v-container>
</template>

<script>
import OrchestratorPromptDialog from '@/components/OrchestratorPromptDialog.vue'

export default {
  components: {
    OrchestratorPromptDialog
  },

  data() {
    return {
      activating: false,
      showPromptDialog: false,
      orchestratorPrompt: ''
    }
  },

  methods: {
    async activateProject() {
      this.activating = true

      try {
        const response = await fetch(`/api/projects/${this.project.id}/activate`, {
          method: 'POST'
        })

        if (!response.ok) {
          throw new Error('Activation failed')
        }

        const data = await response.json()

        this.orchestratorPrompt = data.prompt
        this.showPromptDialog = true

      } catch (error) {
        this.$toast.error('Failed to activate project: ' + error.message)
      } finally {
        this.activating = false
      }
    },

    onPromptCopied() {
      this.$toast.success('Orchestrator prompt copied to clipboard!')
    }
  }
}
</script>
```

**Deliverables**:
- Activate button added to project view
- Loading state during activation
- Error handling

---

#### Task 2.2: Create Orchestrator Prompt Dialog
**Priority**: 🟡 HIGH
**Estimated Time**: 3 hours

Create `frontend/src/components/OrchestratorPromptDialog.vue`:

```vue
<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    max-width="900"
    persistent
  >
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <span>Orchestrator Prompt: {{ projectName }}</span>
        <v-btn
          icon="mdi-close"
          variant="text"
          @click="$emit('update:modelValue', false)"
        />
      </v-card-title>

      <v-card-text>
        <v-alert type="info" class="mb-4">
          <strong>Next Steps:</strong>
          <ol>
            <li>Click "Copy to Clipboard" below</li>
            <li>Open Claude Code: <code>claude code</code></li>
            <li>Paste the prompt (Ctrl+V / Cmd+V)</li>
            <li>Watch the orchestrator coordinate your project!</li>
          </ol>
        </v-alert>

        <v-textarea
          :model-value="prompt"
          readonly
          rows="20"
          variant="outlined"
          class="monospace-font"
          auto-grow
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="primary"
          variant="elevated"
          @click="copyToClipboard"
          prepend-icon="mdi-content-copy"
        >
          Copy to Clipboard
        </v-btn>
        <v-btn
          variant="text"
          @click="$emit('update:modelValue', false)"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  props: {
    modelValue: Boolean,
    prompt: String,
    projectName: String
  },

  emits: ['update:modelValue', 'copied'],

  methods: {
    async copyToClipboard() {
      try {
        await navigator.clipboard.writeText(this.prompt)
        this.$emit('copied')
      } catch (error) {
        this.$toast.error('Failed to copy to clipboard')
      }
    }
  }
}
</script>

<style scoped>
.monospace-font {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
}
</style>
```

**Deliverables**:
- Dialog component created
- Clipboard copy functionality
- User instructions displayed
- Monospace font for prompt readability

---

### Day 7-8: Real-Time Agent Monitoring

#### Task 2.3: Enhance WebSocket Agent Updates
**Priority**: 🟡 HIGH
**Estimated Time**: 3 hours

Update `api/websocket.py`:

```python
class ConnectionManager:
    async def broadcast_agent_update(self, agent_id: str, update: dict):
        """
        Broadcast agent status update to all connected clients.

        Args:
            agent_id: Agent ID
            update: {
                "status": "working",
                "activity": "Designing database schema",
                "progress": 45,
                "timestamp": "2025-10-05T14:30:00Z"
            }
        """
        message = {
            "type": "agent_update",
            "agent_id": agent_id,
            "data": update
        }
        await self.broadcast(json.dumps(message))


# Hook into MCP tool calls
@router.post("/messages")
async def send_message(message: MessageCreate):
    """
    Send message and broadcast to dashboard.
    """
    # Save to database
    db_message = create_message_in_db(message)

    # Broadcast to WebSocket
    if message.message_type == "status_update":
        await websocket_manager.broadcast_agent_update(
            agent_id=message.from_agent,
            update={
                "status": "working",
                "activity": message.content,
                "timestamp": datetime.now().isoformat()
            }
        )

    return db_message
```

**Deliverables**:
- WebSocket broadcast for agent updates
- Integration with message queue
- Real-time status propagation

---

#### Task 2.4: Update Dashboard Agent Components
**Priority**: 🟡 HIGH
**Estimated Time**: 3 hours

Update `frontend/src/views/AgentsView.vue`:

```vue
<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>Active Agents</v-card-title>

          <v-card-text>
            <v-list>
              <v-list-item
                v-for="agent in agents"
                :key="agent.id"
              >
                <template v-slot:prepend>
                  <v-icon
                    :color="getStatusColor(agent.status)"
                    :icon="getStatusIcon(agent.status)"
                  />
                </template>

                <v-list-item-title>{{ agent.name }}</v-list-item-title>

                <v-list-item-subtitle>
                  <div>{{ agent.role }} - {{ agent.status }}</div>
                  <div v-if="agent.current_activity" class="text-caption">
                    {{ agent.current_activity }}
                  </div>
                </v-list-item-subtitle>

                <template v-slot:append>
                  <div v-if="agent.progress_percentage !== undefined">
                    <v-progress-circular
                      :model-value="agent.progress_percentage"
                      :color="getStatusColor(agent.status)"
                      size="60"
                    >
                      {{ agent.progress_percentage }}%
                    </v-progress-circular>
                  </div>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { useAgentStore } from '@/stores/agents'

export default {
  setup() {
    const agentStore = useAgentStore()

    // Connect WebSocket for real-time updates
    agentStore.connectWebSocket()

    return { agentStore }
  },

  computed: {
    agents() {
      return this.agentStore.agents
    }
  },

  methods: {
    getStatusColor(status) {
      const colors = {
        'idle': 'grey',
        'waiting': 'orange',
        'working': 'blue',
        'completed': 'green',
        'failed': 'red'
      }
      return colors[status] || 'grey'
    },

    getStatusIcon(status) {
      const icons = {
        'idle': 'mdi-sleep',
        'waiting': 'mdi-clock-outline',
        'working': 'mdi-cog',
        'completed': 'mdi-check-circle',
        'failed': 'mdi-alert-circle'
      }
      return icons[status] || 'mdi-help-circle'
    }
  }
}
</script>
```

**Deliverables**:
- Real-time agent status display
- Progress indicators
- Activity feed
- Auto-updating via WebSocket

---

### Day 9: Integration Testing

#### Task 2.5: Complete E2E Test Suite
**Priority**: 🔴 CRITICAL
**Estimated Time**: 4 hours

Create `tests/integration/test_e2e_orchestration.py`:

```python
"""
End-to-end orchestration test.

Simulates complete workflow:
1. Create project
2. Activate project
3. Generate orchestrator prompt
4. Manual: Paste into Claude Code
5. Verify: Agent updates appear on dashboard
"""

def test_complete_orchestration_flow():
    """Full orchestration workflow test."""

    # 1. Create test product
    product = create_product(
        name="Test Product",
        vision_path="test_vision.md"
    )

    # 2. Create project
    project = create_project(
        product_id=product.id,
        name="Authentication System",
        description="Build JWT auth with user management"
    )

    # 3. Activate project
    response = client.post(f"/api/projects/{project.id}/activate")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    prompt = data["prompt"]

    # 4. Verify prompt structure
    assert "giljo-orchestrator" in prompt
    assert "mcp__giljo-mcp__list_projects" in prompt
    assert "Task(" in prompt
    assert project.name in prompt

    # 5. Print for manual testing
    print("\n" + "="*80)
    print("MANUAL TEST: Paste this into Claude Code")
    print("="*80)
    print(prompt)
    print("="*80)

    # 6. Simulate agent creation (in real scenario, orchestrator does this)
    agent = spawn_agent(
        project_id=project.id,
        name="Database Agent",
        role="database",
        mission="Design authentication schema"
    )

    # 7. Simulate agent status update
    send_message(
        from_agent=agent.id,
        to_agent="orchestrator",
        content="Started schema design",
        message_type="status_update"
    )

    # 8. Verify dashboard receives update
    # (Requires WebSocket client test)
    time.sleep(1)

    # 9. Check agent status in database
    updated_agent = get_agent(agent.id)
    assert updated_agent.last_active is not None

    print("\n✓ E2E Test Complete")
    print("Next: Manual verification in Claude Code")
```

**Deliverables**:
- Complete E2E test suite
- Manual testing instructions
- WebSocket integration validation

---

### Day 10: Documentation & Beta Release

#### Task 2.6: Update Documentation
**Priority**: 🟡 HIGH
**Estimated Time**: 3 hours

Update these files:

1. **README.md** - Add quick start with Claude Code
2. **docs/QUICK_START.md** - Step-by-step orchestration guide
3. **docs/manuals/MCP_TOOLS_MANUAL.md** - Update with activation tool
4. **CHANGELOG.md** - Document new features

**Deliverables**:
- Documentation updated
- Screenshots added (optional)
- Video walkthrough script (optional)

---

#### Task 2.7: Localhost Beta Testing
**Priority**: 🔴 CRITICAL
**Estimated Time**: 4 hours

**Testing Checklist**:

```
Installation Testing:
□ Fresh install on clean Windows machine
□ PostgreSQL auto-installs
□ Service starts automatically
□ Dashboard accessible at http://localhost:7274
□ All dependencies installed

Agent Profile Setup:
□ Agent profiles copied to ~/.claude/agents/
□ Claude Code recognizes 8 giljo-* agents
□ Verification via /agents command works

Project Workflow:
□ Create product with vision document
□ Create project with description
□ Click "Activate Project" button
□ Prompt dialog appears
□ Copy to clipboard works
□ Paste into Claude Code successful

Orchestration Workflow:
□ Claude Code recognizes giljo-orchestrator
□ Orchestrator reads project via mcp__giljo-mcp__list_projects
□ Orchestrator reads vision documents
□ Orchestrator generates comprehensive mission
□ Orchestrator spawns sub-agents via Task tool
□ Sub-agents appear on dashboard
□ Real-time status updates work
□ Agents complete missions
□ Deliverables captured

Dashboard Monitoring:
□ WebSocket connection stable
□ Agent status updates in <1s
□ Progress indicators accurate
□ Activity feed shows messages
□ Completion tracking works

Performance:
□ Activation prompt generated in <2s
□ Dashboard responsive (<100ms)
□ No memory leaks during long sessions
□ Handles 5+ concurrent agents
```

**Bug Tracking**:
- Document all issues in `docs/BETA_BUGS.md`
- Prioritize: Critical → High → Medium → Low
- Create GitHub issues for each bug

---

## Phase 3: LAN/WAN Deployment (Future)

### Overview

**Status**: Documented but not implemented
**Timeline**: 3-4 weeks (post-beta)

**Key Documents**:
- `docs/deployment/LAN_DEPLOYMENT_GUIDE.md` (38K)
- `docs/deployment/WAN_DEPLOYMENT_GUIDE.md` (33K)
- `docs/deployment/LAN_UX_MISSION_PROMPT.md` (30K)
- `docs/deployment/WAN_MISSION_PROMPT.md` (38K)

### Phase 3.1: LAN UX Improvements (Week 3-4)

**Goal**: Make LAN deployment user-friendly

**Tasks**:
- [ ] Installer deployment mode selection (localhost/LAN)
- [ ] Network configuration wizard
- [ ] Client setup automation scripts
- [ ] IP address auto-detection
- [ ] Firewall rule automation
- [ ] LAN access URL guide
- [ ] Client discovery (mDNS/broadcast)

**Reference**: `docs/deployment/LAN_UX_MISSION_PROMPT.md`

### Phase 3.2: WAN Deployment (Week 5-7)

**Goal**: Production-ready internet deployment

**Tasks**:
- [ ] SSL/TLS certificate management (Let's Encrypt)
- [ ] JWT authentication system
- [ ] Redis session management
- [ ] Rate limiting (per-user, per-IP)
- [ ] WAF integration (ModSecurity)
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Cloud deployment automation (AWS/Azure/GCP)
- [ ] Backup and recovery
- [ ] High availability setup

**Reference**: `docs/deployment/WAN_DEPLOYMENT_GUIDE.md`

---

## Testing Strategy

### Unit Tests (Throughout Development)

**Target Coverage**: 80%+

**Priority Areas**:
```python
# High Priority
tests/unit/test_prompt_generator.py
tests/unit/test_project_activation.py
tests/unit/test_agent_profiles.py

# Medium Priority
tests/unit/test_websocket_manager.py
tests/unit/test_claude_code_integration.py

# Low Priority
tests/unit/test_dashboard_components.py
```

### Integration Tests

**Critical Paths**:
```python
# Must Pass Before Beta
tests/integration/test_e2e_orchestration.py
tests/integration/test_project_activation_flow.py
tests/integration/test_websocket_updates.py
tests/integration/test_multi_agent_coordination.py
```

### Manual Testing

**Daily Testing Protocol**:
1. Fresh database reset
2. Create test project
3. Activate project
4. Paste into Claude Code
5. Monitor dashboard
6. Document any issues

### Performance Testing

**Benchmarks**:
- Activation endpoint: <100ms (p95)
- WebSocket latency: <500ms
- Dashboard load: <200ms
- Concurrent agents: 20+ supported
- Memory usage: <2GB

---

## Success Criteria

### Functional Requirements ✅

```
Localhost Beta is successful if:
□ Installation completes in <5 minutes
□ Service starts automatically
□ Dashboard accessible immediately
□ Project creation works
□ Project activation generates valid prompt
□ Claude Code accepts prompt without errors
□ Orchestrator can read from MCP
□ Orchestrator spawns sub-agents successfully (90%+ rate)
□ Dashboard shows real-time updates (<1s latency)
□ Agents complete missions
□ Deliverables are captured and displayed
```

### Quality Requirements ✅

```
Code quality metrics:
□ Unit test coverage: >80%
□ All integration tests passing
□ No hardcoded path separators (pathlib.Path only)
□ Cross-platform compatibility (Windows/Linux/macOS)
□ Professional code (no emojis unless requested)
□ Clear error messages
□ Comprehensive logging
□ Documentation up-to-date
```

### Performance Requirements ✅

```
Performance targets:
□ API response time: <100ms (p95)
□ WebSocket latency: <500ms
□ Database queries: <50ms (p95)
□ Prompt generation: <2s
□ Dashboard rendering: <200ms
□ Memory usage: <2GB total
□ Supports 10+ concurrent projects
□ Supports 20+ concurrent agents
```

---

## Risk Mitigation

### High-Risk Items ⚠️

**Risk 1: Claude Code Sub-Agent Spawn Failures**
- **Probability**: Medium
- **Impact**: High (breaks core workflow)
- **Mitigation**:
  - Extensive prompt testing
  - Clear Task tool examples
  - Detailed error logging
  - Fallback to manual agent creation
  - User troubleshooting guide

**Risk 2: WebSocket Connection Instability**
- **Probability**: Medium
- **Impact**: Medium (degrades UX)
- **Mitigation**:
  - Auto-reconnection logic
  - Message persistence in database
  - Health monitoring
  - Fallback to HTTP polling
  - Connection status indicator

**Risk 3: Vision Document Context Overflow**
- **Probability**: Low-Medium
- **Impact**: Medium (mission quality suffers)
- **Mitigation**:
  - Smart chunking strategy
  - Context budget tracking
  - Selective document loading
  - Warning when approaching limits
  - Pagination for large docs

### Medium-Risk Items 🔧

**Risk 4: MCP Tool Integration Issues**
- **Probability**: Low
- **Impact**: High
- **Mitigation**:
  - Validate MCP tools at startup
  - Clear error messages
  - Tool availability checks
  - Graceful degradation

**Risk 5: Cross-Platform Path Issues**
- **Probability**: Low
- **Impact**: Medium
- **Mitigation**:
  - Strict pathlib.Path usage
  - Cross-platform testing
  - Path validation tests
  - Platform-specific handling

---

## Daily Execution Plan

### Week 1: Claude Code Integration

**Monday (Day 1)**
```
Morning (4h):
- Create claude_agents/ directory
- Write giljo-orchestrator.md
- Write giljo-database-expert.md
- Write giljo-backend-dev.md

Afternoon (4h):
- Write giljo-tester.md
- Write giljo-security-auditor.md
- Write giljo-architect.md
- Write giljo-researcher.md
- Write giljo-documenter.md
- Test agent loading in Claude Code
```

**Tuesday (Day 2)**
```
Morning (4h):
- Create docs/FIRST_TIME_SETUP.md
- Start src/giljo_mcp/tools/prompt_generator.py
- Implement generate_orchestrator_prompt()

Afternoon (4h):
- Complete prompt_generator.py
- Add helper functions
- Write unit tests
- Test locally
```

**Wednesday (Day 3)**
```
Morning (4h):
- Add activation endpoint to api/endpoints/projects.py
- Integrate prompt_generator
- Add error handling
- Test with curl/Postman

Afternoon (4h):
- Write integration tests
- Fix bugs
- Performance optimization
- Documentation
```

**Thursday (Day 4)**
```
All Day (8h):
- End-to-end testing
- Create test project
- Test activation flow
- Paste into Claude Code
- Verify MCP tool access
- Document issues
- Bug fixes
```

**Friday (Day 5)**
```
Morning (4h):
- Update ProjectDetailView.vue
- Add Activate button
- Add loading states
- Test UI

Afternoon (4h):
- Create OrchestratorPromptDialog.vue
- Implement clipboard copy
- Test dialog flow
- Bug fixes
```

### Week 2: Dashboard & Release

**Monday (Day 6)**
```
Morning (4h):
- Complete dialog component
- Add user instructions
- Style improvements
- Cross-browser testing

Afternoon (4h):
- Enhance WebSocket handlers
- Add agent update broadcasts
- Test real-time updates
- Performance optimization
```

**Tuesday (Day 7)**
```
Morning (4h):
- Update AgentsView.vue
- Add progress indicators
- Add activity feed
- Test WebSocket integration

Afternoon (4h):
- Add agent timeline component
- Style improvements
- Mobile responsiveness
- Cross-browser testing
```

**Wednesday (Day 8)**
```
All Day (8h):
- Integration testing
- E2E test suite
- WebSocket stress testing
- Multi-agent coordination tests
- Performance benchmarks
- Bug fixes
```

**Thursday (Day 9)**
```
Morning (4h):
- Documentation updates
- README.md
- QUICK_START.md
- MCP_TOOLS_MANUAL.md

Afternoon (4h):
- CHANGELOG.md
- Screenshot creation
- Video walkthrough script
- Release notes
```

**Friday (Day 10)**
```
All Day (8h):
- Fresh install testing
- Complete testing checklist
- Bug fixes
- Final performance validation
- Beta release preparation
- Create GitHub release
```

---

## Appendix A: File Checklist

### New Files to Create

**Agent Profiles** (8 files):
```
□ claude_agents/giljo-orchestrator.md
□ claude_agents/giljo-database-expert.md
□ claude_agents/giljo-backend-dev.md
□ claude_agents/giljo-tester.md
□ claude_agents/giljo-security-auditor.md
□ claude_agents/giljo-architect.md
□ claude_agents/giljo-researcher.md
□ claude_agents/giljo-documenter.md
```

**Backend Files**:
```
□ src/giljo_mcp/tools/prompt_generator.py
□ src/giljo_mcp/tools/claude_code_integration.py (exists, may need updates)
```

**Frontend Files**:
```
□ frontend/src/components/OrchestratorPromptDialog.vue
```

**Documentation**:
```
□ docs/FIRST_TIME_SETUP.md
□ docs/BETA_BUGS.md
```

**Tests**:
```
□ tests/unit/test_prompt_generator.py
□ tests/integration/test_project_activation.py
□ tests/integration/test_e2e_orchestration.py
```

### Files to Modify

**Backend**:
```
□ api/endpoints/projects.py (add activate endpoint)
□ api/websocket.py (enhance agent updates)
```

**Frontend**:
```
□ frontend/src/views/ProjectDetailView.vue (add activate button)
□ frontend/src/views/AgentsView.vue (enhance real-time updates)
□ frontend/src/stores/agents.js (WebSocket integration)
```

**Documentation**:
```
□ README.md (add quick start)
□ docs/QUICK_START.md (orchestration guide)
□ docs/manuals/MCP_TOOLS_MANUAL.md (activate_project tool)
□ CHANGELOG.md (new features)
```

---

## Appendix B: Key References

**Integration Guides**:
- `docs/INTEGRATE_CLAUDE_CODE.md` (46K) - Complete integration architecture
- `docs/BACKGROUND_SERVICE_ORCHESTRATION.md` (27K) - Background service approach
- `docs/TOOL_DETECTION_AND_SETUP.md` (31K) - Tool detection wizard
- `docs/AI_CODING_TOOLS_COMPARISON.md` (20K) - Multi-tool support

**Deployment Guides** (Future):
- `docs/deployment/LAN_DEPLOYMENT_GUIDE.md` (38K)
- `docs/deployment/WAN_DEPLOYMENT_GUIDE.md` (33K)
- `docs/deployment/LAN_UX_MISSION_PROMPT.md` (30K)
- `docs/deployment/WAN_MISSION_PROMPT.md` (38K)

**Technical Documentation**:
- `docs/TECHNICAL_ARCHITECTURE.md` - System architecture
- `docs/manuals/MCP_TOOLS_MANUAL.md` - MCP tools reference
- `CLAUDE.md` - Project instructions

**Recent Sessions**:
- `docs/sessions/2025-10-04_product_project_integration.md` - Product system
- `docs/sessions/2025-10-03_websocket_dashboard_implementation.md` - WebSocket
- `docs/sessions/2025-10-03_full_stack_integration.md` - Full stack

---

## Conclusion

This implementation plan focuses on delivering a **working localhost beta** with **Claude Code sub-agent orchestration** in 10 working days (2 weeks).

### Critical Path Summary:
1. **Days 1-2**: Create agent profiles (foundation)
2. **Days 2-3**: Build prompt generator (core logic)
3. **Day 4**: Integration testing (validation)
4. **Days 5-6**: Dashboard UI (user experience)
5. **Days 7-8**: Real-time monitoring (polish)
6. **Days 9-10**: Documentation and beta release

### Success Metrics:
- ✅ All 8 agent profiles created
- ✅ Activation endpoint working
- ✅ Dashboard activation UI functional
- ✅ E2E tests passing
- ✅ Documentation complete
- ✅ Beta release ready

### Next Steps:
1. **Review this plan** - Validate priorities and timeline
2. **Create GitHub issues** - Track each task
3. **Setup project board** - Kanban workflow
4. **Begin Day 1** - Create agent profiles
5. **Daily standups** - Track progress and blockers

**Let's build this!** 🚀
