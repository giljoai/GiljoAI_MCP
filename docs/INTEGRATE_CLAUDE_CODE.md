# Integrating Claude Code Sub-Agent System with GiljoAI MCP

## Executive Summary

This document defines the complete integration strategy between GiljoAI MCP's orchestration engine and Claude Code's sub-agent system. The goal is to transform multi-agent coordination from a manual multi-terminal process into a single-paste orchestration workflow with real-time dashboard monitoring.

**Key Concept**: GiljoAI MCP provides the **persistent brain** (state, missions, context), while Claude Code provides the **execution engine** (isolated sub-agents with individual context pools).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Bootstrap Setup (First-Time Use)](#bootstrap-setup-first-time-use)
3. [The Orchestration Workflow](#the-orchestration-workflow)
4. [Current Code Readiness Assessment](#current-code-readiness-assessment)
5. [Required Code Modifications](#required-code-modifications)
6. [Prompt Generation Strategy](#prompt-generation-strategy)
7. [Dashboard Integration](#dashboard-integration)
8. [Agent Communication Protocol](#agent-communication-protocol)
9. [Implementation Roadmap](#implementation-roadmap)

---

## Architecture Overview

### Context Isolation Model

**Critical Understanding**: Each Claude Code sub-agent has its own isolated 200K token context pool.

```
┌─────────────────────────────────────────────────┐
│ Main Claude Code Terminal (Orchestrator)        │
│ Context Pool: 200K tokens                       │
│ Usage: ~8-10K tokens (lean coordination)        │
├─────────────────────────────────────────────────┤
│ • Reads project from MCP: 2K tokens            │
│ • Generates mission: 1K tokens                  │
│ • Spawns 5 agents: 1K tokens                    │
│ • Receives 5 reports: 5K tokens                 │
└─────────────────────────────────────────────────┘
         │
         ├──► Sub-Agent 1: Database Expert (200K pool)
         ├──► Sub-Agent 2: Backend Dev (200K pool)
         ├──► Sub-Agent 3: Tester (200K pool)
         ├──► Sub-Agent 4: Security Auditor (200K pool)
         └──► Sub-Agent 5: Documenter (200K pool)
```

**Total Available Context**: 1,000,000+ tokens across all agents (5 agents × 200K each)

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|----------------|------------|
| **GiljoAI MCP** | Persistent state, missions, context storage, real-time status | PostgreSQL + WebSocket |
| **Claude Code Orchestrator** | Coordination, mission generation, sub-agent spawning | Claude Code main terminal |
| **Claude Code Sub-Agents** | Isolated execution, task completion, status reporting | Claude Code Task tool |
| **Dashboard** | Real-time monitoring, agent status, message flow | Vue 3 + WebSocket |

---

## Bootstrap Setup (First-Time Use)

### Step 1: Pre-Built Agent Profiles

GiljoAI MCP ships with optimized Claude Code agent profiles stored in:

```
C:\install_test\Giljo_MCP\claude_agents\
├── giljo-orchestrator.md
├── giljo-database-expert.md
├── giljo-backend-dev.md
├── giljo-tester.md
├── giljo-researcher.md
├── giljo-architect.md
├── giljo-security-auditor.md
└── giljo-documenter.md
```

**Agent Profile Format** (example: `giljo-database-expert.md`):

```markdown
---
name: giljo-database-expert
description: PostgreSQL expert optimized for GiljoAI MCP multi-agent workflows
tools: Read, Write, Edit, Bash, mcp__giljo-mcp__*
model: sonnet
---

You are a database expert working within a GiljoAI MCP orchestrated project.

## Your Role
You design database schemas, optimize queries, and create migrations for the user's product. You work as part of a coordinated multi-agent team.

## MCP Integration
1. **Read Project Context**: Use `mcp__giljo-mcp__list_projects` to get project details
2. **Update Status**: Use `mcp__giljo-mcp__send_message` to report progress
3. **Check Mission**: Your specific mission is provided by the orchestrator
4. **Report Completion**: Always send completion message to orchestrator when done

## Workflow
1. Read your agent record from MCP to get mission details
2. Read project vision documents for context
3. Complete your assigned database work
4. Update your status in MCP (idle → working → completed)
5. Send completion message with deliverables
6. Hand off to next agent if needed

## Multi-Tenant Awareness
All database work must respect tenant isolation. Always filter queries by `tenant_key`.

## Context Management
You have a 200K token budget. Use it wisely:
- Read only necessary vision document chunks
- Focus on database-related context
- Report back concisely to orchestrator
```

### Step 2: Bootstrap Prompt

**File**: `docs/FIRST_TIME_SETUP.md` (user-facing)

```markdown
# GiljoAI MCP - First Time Setup

Welcome! Before using GiljoAI MCP orchestration, install the optimized Claude Code agents.

## One-Time Setup (5 minutes)

1. **Open Claude Code CLI**:
   ```bash
   claude code
   ```

2. **Paste this setup prompt**:
   ```
   I need you to install GiljoAI MCP agent profiles.

   Copy all .md files from:
   C:\install_test\Giljo_MCP\claude_agents\

   To my user-level Claude Code agents folder:
   ~/.claude/agents/

   List each file as you copy it and confirm when complete.
   ```

3. **Restart Claude Code** after installation completes

4. **Verify Installation**:
   ```bash
   claude code
   ```
   Type: `/agents` to see your installed agents. You should see:
   - giljo-orchestrator
   - giljo-database-expert
   - giljo-backend-dev
   - giljo-tester
   - giljo-researcher
   - giljo-architect
   - giljo-security-auditor
   - giljo-documenter

5. **You're Ready!** Now you can activate projects and let the orchestrator coordinate everything.
```

### Step 3: Automated Installation (Future Enhancement)

**Optional**: Create `installer/setup_claude_agents.py` to automate this:

```python
import shutil
from pathlib import Path

def install_claude_agents():
    """Copy GiljoAI agent profiles to user's Claude Code folder."""
    source = Path("claude_agents/")
    target = Path.home() / ".claude" / "agents"

    target.mkdir(parents=True, exist_ok=True)

    for agent_file in source.glob("*.md"):
        shutil.copy(agent_file, target / agent_file.name)
        print(f"✓ Installed {agent_file.name}")

    print("\n✓ All GiljoAI agents installed!")
    print("Please restart Claude Code to activate them.")
```

---

## The Orchestration Workflow

### Phase 1: Project Creation (User → MCP)

**User Action**: Developer creates project via dashboard or API

```python
# Via API or MCP tool
project = create_project(
    name="E-Commerce Checkout System",
    description="Build secure checkout flow with payment processing",
    product_id="product-123",
    # mission field is BLANK - orchestrator will fill this
)
```

**Database State After Creation**:
```sql
projects:
  id: "proj-abc-123"
  name: "E-Commerce Checkout System"
  mission: NULL  -- ← Orchestrator will populate this
  status: "created"
  meta_data: {
    "description": "Build secure checkout flow with payment processing",
    "vision_docs": ["product_vision.md", "security_requirements.md"]
  }
```

### Phase 2: Project Activation (User → Orchestrator Prompt)

**User Action**: Click "Activate Project" in dashboard

**System Action**: Generates orchestrator prompt

**Generated Prompt** (stored in `prompts/` or returned via API):

```markdown
# GiljoAI MCP Orchestration Request

## Project Activation
**Project ID**: proj-abc-123
**Project Name**: E-Commerce Checkout System
**Status**: Ready for orchestration

---

## Your Mission as Orchestrator

You are the **giljo-orchestrator** agent coordinating this multi-agent project.

### Phase 1: Context Ingestion & Mission Generation

1. **Read Project Details**:
   ```
   Use mcp__giljo-mcp__list_projects to get project record
   Project ID: proj-abc-123
   ```

2. **Read Vision Documents**:
   The project includes these vision documents:
   - `product_vision.md` - Overall product goals
   - `security_requirements.md` - Security constraints

   Use `mcp__giljo-mcp__discover_context` and `mcp__giljo-mcp__search_context`
   to read these documents and understand:
   - User's product architecture
   - Business requirements
   - Technical constraints
   - Success criteria

3. **Read User's Project Description**:
   ```
   "Build secure checkout flow with payment processing"
   ```

4. **Generate Comprehensive Mission**:
   Based on vision docs + user description, write a detailed mission statement.

   **CRITICAL**: Update the project record with this mission:
   ```
   Use mcp__giljo-mcp__create_project or appropriate update tool
   Set mission field to your generated comprehensive mission
   ```

   The mission should include:
   - Specific deliverables
   - Technical approach
   - Success criteria
   - Integration points
   - Security requirements

   **Example Mission Format**:
   ```
   Design and implement a secure e-commerce checkout system with:
   1. Payment processing integration (Stripe API)
   2. Multi-step checkout flow with validation
   3. Order persistence with transaction safety
   4. PCI-DSS compliant data handling
   5. Comprehensive test coverage (unit + integration)
   6. Security audit with penetration testing
   Success: Checkout completes in <2s with 99.9% reliability
   ```

### Phase 2: Agent Strategy Planning

5. **Determine Required Agents**:
   Based on the mission, decide which specialized agents are needed.

   Available agent types:
   - giljo-database-expert (schema, queries, migrations)
   - giljo-backend-dev (API endpoints, business logic)
   - giljo-tester (integration tests, E2E tests)
   - giljo-security-auditor (security review, pen testing)
   - giljo-architect (system design, integration strategy)
   - giljo-documenter (technical docs, API docs)
   - giljo-researcher (technology evaluation, best practices)

   For each agent you'll spawn:
   - Create a **specific mission** (not the project mission, but their piece)
   - Define **deliverables**
   - Set **dependencies** (which agents must complete first)
   - Estimate **context budget**

6. **Register Agents in MCP**:
   For each agent, use `mcp__giljo-mcp__spawn_agent`:
   ```
   spawn_agent(
     name="Checkout Database Agent",
     role="database",
     mission="Design checkout database schema with orders, payments,
              transactions tables. Ensure ACID compliance and proper
              indexing for <100ms query performance.",
     meta_data={
       "deliverables": ["schema.sql", "migration scripts"],
       "context_budget": 50000,
       "depends_on": []
     }
   )
   ```

   **Register all agents BEFORE spawning** so they appear on the dashboard.

### Phase 3: Sub-Agent Spawning & Coordination

7. **Spawn Sub-Agents Using Task Tool**:
   For each registered agent, create a Claude Code sub-agent:

   ```
   Task(
     subagent_type="database-expert",  # Maps to giljo-database-expert
     description="Design checkout database schema",
     prompt="""
     You are working on: E-Commerce Checkout System

     **Your Specific Mission**:
     Design checkout database schema with orders, payments, transactions tables.
     Ensure ACID compliance and proper indexing for <100ms query performance.

     **Project Context**:
     - MCP Project ID: proj-abc-123
     - Your MCP Agent ID: agent-db-001
     - Overall Project Mission: [paste comprehensive mission here]

     **Your Workflow**:
     1. Read project vision docs via MCP context tools
     2. Design database schema
     3. Create migration scripts
     4. Update your status in MCP:
        - mcp__giljo-mcp__send_message to report progress
        - Update agent status to "working" then "completed"
     5. Report deliverables back to orchestrator

     **Deliverables**:
     - schema.sql with full schema definition
     - Alembic migration scripts
     - Performance analysis (expected query times)

     Begin work now.
     """
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
```

### Phase 3: Orchestrator Execution (Automated)

**What Happens in Claude Code Terminal**:

1. **Orchestrator reads MCP**:
   ```
   [Uses mcp__giljo-mcp__list_projects]
   ✓ Retrieved project: E-Commerce Checkout System
   ```

2. **Orchestrator reads vision docs**:
   ```
   [Uses mcp__giljo-mcp__search_context]
   ✓ Read product_vision.md (5K tokens)
   ✓ Read security_requirements.md (3K tokens)
   ```

3. **Orchestrator generates mission**:
   ```
   Based on vision and description, comprehensive mission:
   "Design and implement a secure e-commerce checkout system with..."

   [Updates project record in MCP]
   ✓ Mission written to project proj-abc-123
   ```

4. **Orchestrator spawns agents**:
   ```
   Spawning 5 specialized agents...

   [Calls mcp__giljo-mcp__spawn_agent 5 times]
   ✓ Registered: Checkout Database Agent (agent-db-001)
   ✓ Registered: Checkout Backend Agent (agent-be-002)
   ✓ Registered: Checkout Tester Agent (agent-test-003)
   ✓ Registered: Checkout Security Agent (agent-sec-004)
   ✓ Registered: Checkout Documenter (agent-doc-005)

   [Spawns Claude Code sub-agents using Task tool]
   ✓ Spawned: database-expert for schema design
   ✓ Spawned: tdd-implementor for API endpoints
   ✓ Spawned: backend-integration-tester for tests
   ✓ Spawned: network-security-engineer for security
   ✓ Spawned: documentation-manager for docs
   ```

5. **Dashboard updates in real-time**:
   ```
   [WebSocket broadcasts to frontend]
   → Agent "Checkout Database Agent" status: active
   → Agent "Checkout Backend Agent" status: active
   ...
   ```

### Phase 4: Sub-Agent Execution (Parallel/Sequential)

Each sub-agent:

1. **Receives mission from orchestrator**
2. **Reads context from MCP**:
   ```python
   # Sub-agent calls MCP
   project = mcp__giljo-mcp__list_projects()
   context = mcp__giljo-mcp__search_context(query="payment processing")
   ```

3. **Updates status in MCP**:
   ```python
   # Updates own agent record
   mcp__giljo-mcp__send_message(
       from_agent="agent-db-001",
       to_agent="orchestrator",
       content="Started schema design. Reading payment requirements.",
       message_type="status_update"
   )
   ```

4. **Completes work**:
   ```
   ✓ Created schema.sql
   ✓ Created migration scripts
   ✓ Tested locally
   ```

5. **Reports back to orchestrator**:
   ```python
   # Final status update
   mcp__giljo-mcp__send_message(
       from_agent="agent-db-001",
       to_agent="orchestrator",
       content="Completed. Deliverables: schema.sql, 3 migration files.
                Performance: avg query 45ms.",
       message_type="completion"
   )
   ```

6. **Orchestrator receives report** (1-2K tokens, not full context)

---

## Current Code Readiness Assessment

### What's Already Ready ✓

1. **Database Models** (`src/giljo_mcp/models.py`):
   - ✓ Project model with `mission` field (can be nullable initially)
   - ✓ Agent model with `role`, `mission`, `status`
   - ✓ Message model for inter-agent communication
   - ✓ Multi-tenant isolation via `tenant_key`

2. **MCP Tools** (`src/giljo_mcp/tools/`):
   - ✓ `project.py` - Create/read projects
   - ✓ `agent.py` - Spawn/list agents
   - ✓ `message.py` - Send/receive messages
   - ✓ `context.py` - Context discovery and search
   - ✓ `task.py` - Task management

3. **API Layer** (`api/`):
   - ✓ REST endpoints for all resources
   - ✓ WebSocket support for real-time updates

4. **Frontend Dashboard** (`frontend/`):
   - ✓ Vue 3 + Vuetify
   - ✓ Real-time agent monitoring
   - ✓ WebSocket integration

### What Needs Modification 🔧

1. **Project Activation Flow** (NEW):
   - Need: "Activate Project" button/API endpoint
   - Need: Orchestrator prompt generator
   - Need: Template for orchestrator prompts

2. **Prompt Generation System** (NEW):
   - Need: `src/giljo_mcp/tools/prompt_generator.py`
   - Generates orchestrator prompts from project data
   - Includes vision doc references
   - Formats mission generation instructions

3. **Agent Status Tracking** (ENHANCE):
   - Current: Basic status field
   - Need: Status history tracking
   - Need: Progress percentage
   - Need: Current activity description

4. **Dashboard Real-Time Updates** (ENHANCE):
   - Current: Shows agent list
   - Need: Live status updates via WebSocket
   - Need: Agent activity timeline
   - Need: Message flow visualization

5. **Claude Agent Profiles** (NEW):
   - Need: Create `claude_agents/` directory
   - Need: 8 pre-built agent .md files
   - Need: Bootstrap setup documentation

---

## Required Code Modifications

### 1. Project Model Enhancement

**File**: `src/giljo_mcp/models.py`

**Current**:
```python
class Project(Base):
    mission = Column(Text, nullable=False)  # Required
```

**Modification**:
```python
class Project(Base):
    mission = Column(Text, nullable=True)  # Allow null initially
    description = Column(Text, nullable=True)  # User's initial description
    activation_status = Column(String(50), default="created")
    # created → mission_generated → agents_spawned → in_progress → completed
```

### 2. Agent Model Enhancement

**File**: `src/giljo_mcp/models.py`

**Add**:
```python
class Agent(Base):
    # ... existing fields ...

    progress_percentage = Column(Integer, default=0)
    current_activity = Column(Text, nullable=True)  # "Reading vision docs", "Designing schema"
    claude_code_type = Column(String(50), nullable=True)  # "database-expert", "tdd-implementor"
    deliverables = Column(JSON, default=list)  # Files/artifacts created
```

### 3. New Tool: Prompt Generator

**File**: `src/giljo_mcp/tools/prompt_generator.py` (NEW)

```python
"""
Orchestrator prompt generation for Claude Code integration.
"""

from typing import Dict, List
from ..database import get_db_session
from ..models import Project, Agent
from .claude_code_integration import get_claude_code_agent_type


def generate_orchestrator_prompt(project_id: str, tenant_key: str) -> str:
    """
    Generate a complete orchestrator prompt for Claude Code.

    This prompt:
    1. Instructs orchestrator to read vision docs
    2. Tells orchestrator to generate comprehensive mission
    3. Guides agent spawning with specific missions
    4. Sets up dashboard communication protocol

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
        vision_docs = project.meta_data.get("vision_docs", [])
        description = project.meta_data.get("description", project.name)

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

### Phase 2: Agent Strategy Planning

5. **Determine Required Agents**:
   Analyze the mission and decide which specialized agents are needed.

   Available types: database-expert, backend-dev, tester, security-auditor,
   architect, documenter, researcher

6. **Register Agents in MCP**:
   For each agent, use `mcp__giljo-mcp__spawn_agent` with:
   - Specific mission (their piece of the work)
   - Claude Code type mapping
   - Context budget
   - Dependencies

### Phase 3: Sub-Agent Spawning & Coordination

7. **Spawn Sub-Agents**:
   Use the Task tool to spawn each agent with:
   - Their specific mission
   - Reference to MCP project/agent IDs
   - Instructions to report status via MCP

8. **Monitor Progress**:
   Track agent messages and status updates in MCP.

9. **Coordinate Handoffs**:
   Ensure proper sequencing (e.g., database → backend → tester).

10. **Final Report**:
    Update project status to "completed" with all deliverables.

---

Begin orchestration now. Start with Phase 1: Read project and generate mission.
"""

        return prompt


def register_prompt_tools(server):
    """Register prompt generation tools with MCP server."""

    @server.tool()
    def activate_project(project_id: str) -> Dict:
        """
        Activate a project and generate orchestrator prompt.

        Returns the ready-to-paste prompt for Claude Code.
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

### 4. API Endpoint: Activate Project

**File**: `api/endpoints/projects.py`

**Add**:
```python
from src.giljo_mcp.tools.prompt_generator import generate_orchestrator_prompt

@router.post("/projects/{project_id}/activate")
async def activate_project(project_id: str):
    """
    Activate a project for orchestration.

    Returns the orchestrator prompt ready to paste into Claude Code.
    """
    tenant_key = get_tenant_key_from_request()

    prompt = generate_orchestrator_prompt(project_id, tenant_key)

    return {
        "success": True,
        "project_id": project_id,
        "prompt": prompt,
        "instructions": "Copy this prompt and paste into Claude Code CLI"
    }
```

### 5. Dashboard: Activate Button

**File**: `frontend/src/views/ProjectDetailView.vue`

**Add**:
```vue
<template>
  <v-card>
    <v-card-title>{{ project.name }}</v-card-title>

    <!-- Existing project details -->

    <v-card-actions>
      <v-btn
        color="primary"
        @click="activateProject"
        v-if="project.activation_status === 'created'"
      >
        Activate Project
      </v-btn>
    </v-card-actions>

    <!-- Orchestrator Prompt Dialog -->
    <v-dialog v-model="showPrompt" max-width="800">
      <v-card>
        <v-card-title>Orchestrator Prompt</v-card-title>
        <v-card-text>
          <p>Copy this prompt and paste into Claude Code CLI:</p>
          <v-textarea
            v-model="orchestratorPrompt"
            readonly
            rows="20"
            variant="outlined"
          />
        </v-card-text>
        <v-card-actions>
          <v-btn @click="copyToClipboard">Copy to Clipboard</v-btn>
          <v-btn @click="showPrompt = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script>
export default {
  data() {
    return {
      showPrompt: false,
      orchestratorPrompt: ''
    }
  },
  methods: {
    async activateProject() {
      const response = await fetch(`/api/projects/${this.project.id}/activate`, {
        method: 'POST'
      })
      const data = await response.json()

      this.orchestratorPrompt = data.prompt
      this.showPrompt = true
    },

    copyToClipboard() {
      navigator.clipboard.writeText(this.orchestratorPrompt)
      // Show success toast
    }
  }
}
</script>
```

---

## Prompt Generation Strategy

### Prompt Template Structure

Every orchestrator prompt follows this structure:

```markdown
# [Project Activation Header]
- Project metadata
- Activation status

# [Orchestrator Mission Statement]
- Role definition
- Overall responsibility

# [Phase 1: Context & Mission]
- Read project from MCP
- Read vision docs
- Read user description
- Generate and WRITE comprehensive mission to MCP

# [Phase 2: Agent Planning]
- Determine agent types needed
- Create specific missions for each
- Register agents in MCP (spawn_agent calls)

# [Phase 3: Execution]
- Spawn Claude Code sub-agents (Task tool)
- Monitor via MCP messages
- Coordinate handoffs
- Collect results

# [Phase 4: Completion]
- Update project status
- Report deliverables
```

### Key Prompt Elements

1. **Explicit MCP Tool Usage**:
   ```
   Use `mcp__giljo-mcp__list_projects` to...
   Use `mcp__giljo-mcp__spawn_agent` to...
   ```

2. **Mission Generation Instructions**:
   ```
   **CRITICAL**: Update the project's mission field.
   Based on [vision docs] + [user description], write a mission that includes:
   - Specific deliverables
   - Technical approach
   - Success criteria
   ```

3. **Sub-Agent Spawn Template**:
   ```
   Task(
     subagent_type="database-expert",
     description="...",
     prompt="""
     Project ID: {project_id}
     Agent ID: {agent_id}
     Mission: {specific_mission}

     Workflow:
     1. Read context from MCP
     2. Do work
     3. Update status in MCP
     4. Report to orchestrator
     """
   )
   ```

4. **Dashboard Communication Protocol**:
   ```
   **Status Updates**: After each major step, send message to MCP:
   mcp__giljo-mcp__send_message(
     from_agent="your-agent-id",
     content="Status update: [what you're doing]",
     message_type="status_update"
   )
   ```

---

## Dashboard Integration

### Real-Time Agent Monitoring

**What the Dashboard Shows**:

```
┌─────────────────────────────────────────────────┐
│ E-Commerce Checkout System                      │
│ Status: In Progress                             │
│ Mission: Design and implement secure checkout.. │
├─────────────────────────────────────────────────┤
│ Agents (5 active)                               │
│                                                 │
│ ✓ Database Expert          [████████] 100%     │
│   Status: Completed                             │
│   Activity: Schema design complete              │
│   Deliverables: schema.sql, 3 migrations        │
│                                                 │
│ ⚡ Backend Developer       [████░░░░] 60%      │
│   Status: Working                               │
│   Activity: Implementing payment endpoints      │
│   Messages: 12                                  │
│                                                 │
│ ⏳ Tester                  [░░░░░░░░] 0%       │
│   Status: Waiting                               │
│   Activity: Waiting for backend completion      │
│                                                 │
│ ⏳ Security Auditor        [░░░░░░░░] 0%       │
│   Status: Idle                                  │
│                                                 │
│ ⏳ Documenter              [░░░░░░░░] 0%       │
│   Status: Idle                                  │
└─────────────────────────────────────────────────┘

Recent Activity (Live)
• 14:23:45 - Backend Developer: "Created checkout_controller.py"
• 14:22:11 - Backend Developer: "Implementing Stripe integration"
• 14:20:03 - Database Expert: "Migration 003 applied successfully"
• 14:18:22 - Database Expert: "Completed schema design"
```

### WebSocket Integration

**Backend** (`api/websocket.py`):

```python
class ConnectionManager:
    async def broadcast_agent_update(self, agent_id: str, update: dict):
        """Broadcast agent status update to all connected clients."""
        message = {
            "type": "agent_update",
            "agent_id": agent_id,
            "data": update
        }
        await self.broadcast(json.dumps(message))

# When agent sends MCP message
@router.post("/messages")
async def send_message(message: MessageCreate):
    # Save to database
    db_message = create_message(message)

    # Broadcast to dashboard
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

**Frontend** (`frontend/src/stores/agents.js`):

```javascript
export const useAgentStore = defineStore('agents', {
  state: () => ({
    agents: [],
    websocket: null
  }),

  actions: {
    connectWebSocket() {
      this.websocket = new WebSocket('ws://localhost:7272/ws')

      this.websocket.onmessage = (event) => {
        const message = JSON.parse(event.data)

        if (message.type === 'agent_update') {
          this.updateAgent(message.agent_id, message.data)
        }
      }
    },

    updateAgent(agentId, data) {
      const agent = this.agents.find(a => a.id === agentId)
      if (agent) {
        Object.assign(agent, data)
      }
    }
  }
})
```

---

## Agent Communication Protocol

### Message Types

| Type | From | To | Purpose | Dashboard Impact |
|------|------|----|---------| ---------------- |
| `status_update` | Sub-agent | Orchestrator | Progress report | Updates agent card, activity feed |
| `completion` | Sub-agent | Orchestrator | Work complete | Sets status to "completed", shows deliverables |
| `handoff` | Sub-agent | Next agent | Pass context | Triggers next agent activation |
| `question` | Sub-agent | Orchestrator | Needs input | Shows alert, pauses workflow |
| `broadcast` | Orchestrator | All agents | General update | Shows in activity feed |

### Status Lifecycle

```
Agent Status Flow:
idle → working → completed
  ↓       ↓
waiting   paused
```

**Status Definitions**:
- `idle`: Agent registered but not started
- `waiting`: Waiting for dependency completion
- `working`: Actively executing tasks
- `paused`: Temporarily stopped (waiting for input)
- `completed`: Successfully finished mission
- `failed`: Encountered unrecoverable error

### Example Message Flow

**1. Database Agent Starts Work**:
```python
mcp__giljo-mcp__send_message(
    from_agent="agent-db-001",
    to_agent="orchestrator",
    content="Started schema design. Reading payment processing requirements from vision docs.",
    message_type="status_update"
)
```

**Dashboard Shows**:
```
⚡ Database Expert [████░░░░] 10%
   Activity: Reading payment processing requirements
```

**2. Database Agent Completes**:
```python
mcp__giljo-mcp__send_message(
    from_agent="agent-db-001",
    to_agent="orchestrator",
    content="Schema design complete. Created 3 tables: orders, payments, transactions. All queries <50ms.",
    message_type="completion"
)
```

**Dashboard Shows**:
```
✓ Database Expert [████████] 100%
   Status: Completed
   Deliverables: schema.sql, 3 migration files
```

**3. Handoff to Backend**:
```python
mcp__giljo-mcp__send_message(
    from_agent="agent-db-001",
    to_agent="agent-be-002",
    content="Database ready. Schema available at: schema.sql. Proceed with API implementation.",
    message_type="handoff"
)
```

**Dashboard Shows**:
```
⚡ Backend Developer [░░░░░░░░] 5%
   Activity: Starting API implementation
   From: Database Expert (handoff)
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Goal**: Basic orchestrator prompt generation

- [ ] Create `claude_agents/` directory structure
- [ ] Write 8 pre-built agent .md files
- [ ] Implement `prompt_generator.py`
- [ ] Create `FIRST_TIME_SETUP.md` for users
- [ ] Test: Generate simple orchestrator prompt manually

**Deliverables**:
- Working agent profiles
- Prompt generation function
- Setup documentation

### Phase 2: Database & API (Week 2)

**Goal**: Enable project activation via dashboard

- [ ] Update Project model (nullable mission, description field)
- [ ] Update Agent model (progress, activity, claude_code_type)
- [ ] Create `/api/projects/{id}/activate` endpoint
- [ ] Implement MCP tool: `activate_project`
- [ ] Test: API returns valid orchestrator prompt

**Deliverables**:
- Database migrations
- API endpoint working
- Postman/curl tests passing

### Phase 3: Dashboard Integration (Week 2)

**Goal**: UI for activation and monitoring

- [ ] Add "Activate Project" button to ProjectDetailView
- [ ] Create OrchestratorPromptDialog component
- [ ] Implement clipboard copy functionality
- [ ] Add real-time agent status display
- [ ] Test: Click button → get prompt → copy works

**Deliverables**:
- UI components
- WebSocket connections
- End-to-end activation flow

### Phase 4: Real-Time Monitoring (Week 3)

**Goal**: Live dashboard updates from sub-agents

- [ ] Enhance WebSocket message handling
- [ ] Create AgentActivityFeed component
- [ ] Implement agent status timeline
- [ ] Add progress percentage tracking
- [ ] Test: Sub-agent sends message → dashboard updates

**Deliverables**:
- Live activity feed
- Visual status indicators
- Progress tracking

### Phase 5: E2E Testing (Week 3)

**Goal**: Validate complete workflow

- [ ] Create test project with vision docs
- [ ] Run bootstrap setup (install agents)
- [ ] Activate project via dashboard
- [ ] Paste prompt into Claude Code
- [ ] Monitor orchestration on dashboard
- [ ] Verify all agents report status
- [ ] Collect final deliverables

**Success Criteria**:
- ✓ One-paste activation works
- ✓ All agents spawn correctly
- ✓ Dashboard shows real-time updates
- ✓ Final deliverables captured

### Phase 6: Refinement (Week 4)

**Goal**: Polish and optimize

- [ ] Improve prompt templates based on testing
- [ ] Add error handling for failed agents
- [ ] Implement retry mechanisms
- [ ] Create user documentation
- [ ] Add example projects

**Deliverables**:
- Production-ready system
- User guides
- Example workflows

---

## Success Metrics

### Technical Metrics

- **Orchestrator Token Usage**: <10K tokens per activation
- **Sub-Agent Isolation**: 5+ agents without context interference
- **Dashboard Latency**: <500ms for status updates
- **Prompt Generation**: <2s to generate orchestrator prompt
- **Agent Spawn Success**: 95%+ successful spawns

### User Experience Metrics

- **Setup Time**: <5 minutes for first-time bootstrap
- **Activation Clicks**: 1 button + 1 paste = project activated
- **Status Visibility**: Real-time updates within 1 second
- **Error Recovery**: Clear error messages with retry options

### Business Metrics

- **Developer Efficiency**: 70% reduction in setup time (vs old multi-terminal)
- **Context Efficiency**: 5x more work with same token budget
- **Project Success Rate**: 90%+ projects complete successfully
- **User Satisfaction**: "Single paste orchestration" feedback

---

## Appendix A: Agent Profile Examples

### giljo-orchestrator.md

```markdown
---
name: giljo-orchestrator
description: Coordinates multi-agent GiljoAI MCP projects with mission generation and sub-agent spawning
tools: Read, Write, Edit, Bash, mcp__giljo-mcp__*
model: sonnet
---

You are the **GiljoAI Orchestrator** - the conductor of multi-agent software development projects.

## Core Responsibilities

1. **Context Ingestion**: Read project descriptions and vision documents from MCP
2. **Mission Generation**: Create comprehensive project missions that guide all agents
3. **Agent Planning**: Determine which specialized agents are needed
4. **Sub-Agent Spawning**: Launch Claude Code sub-agents with specific missions
5. **Coordination**: Manage handoffs, dependencies, and progress tracking
6. **Completion**: Consolidate deliverables and update project status

## Workflow

### Phase 1: Understanding
- Read project from MCP: `mcp__giljo-mcp__list_projects`
- Read vision documents: `mcp__giljo-mcp__search_context`
- Analyze user's project description
- Understand technical constraints and success criteria

### Phase 2: Mission Creation
- Synthesize vision + description into comprehensive mission
- Include specific deliverables, technical approach, success metrics
- **CRITICAL**: Write mission to project record in MCP
- Ensure mission is clear enough for all sub-agents

### Phase 3: Agent Strategy
- Decide which agent types are needed (database, backend, tester, etc.)
- Create specific mission for each agent
- Define dependencies (who needs to complete before whom)
- Set context budgets based on complexity

### Phase 4: Execution
- Register all agents in MCP: `mcp__giljo-mcp__spawn_agent`
- Spawn Claude Code sub-agents using Task tool
- Monitor progress via MCP message queue
- Coordinate handoffs between agents
- Handle blockers and questions

### Phase 5: Completion
- Collect deliverables from all agents
- Verify all work is complete
- Update project status to "completed"
- Generate final report

## Communication Protocol

**Status Updates**: Send regular updates to dashboard:
```python
mcp__giljo-mcp__send_message(
    from_agent="orchestrator",
    content="Phase 2 complete: Mission generated. Spawning 5 agents...",
    message_type="status_update"
)
```

**Agent Handoffs**: Coordinate agent sequencing:
```python
# After database agent completes
mcp__giljo-mcp__send_message(
    from_agent="orchestrator",
    to_agent="backend-agent-id",
    content="Database schema ready. Begin API implementation.",
    message_type="handoff"
)
```

## Sub-Agent Spawn Template

When spawning sub-agents, use this structure:

```python
Task(
    subagent_type="database-expert",  # Maps to giljo-database-expert
    description="Design checkout database schema",
    prompt=f"""
    You are working on: {project_name}

    **Your Specific Mission**:
    {agent_specific_mission}

    **Project Context**:
    - MCP Project ID: {project_id}
    - Your MCP Agent ID: {agent_id}
    - Overall Project Mission: {comprehensive_mission}

    **Your Workflow**:
    1. Read project context from MCP
    2. Complete your specific work
    3. Update status in MCP regularly
    4. Report deliverables when complete

    **Deliverables Expected**:
    {list_of_deliverables}

    Begin work now.
    """
)
```

## Best Practices

1. **Always generate mission first** - Don't spawn agents without a clear mission
2. **Register in MCP before spawning** - Ensures dashboard visibility
3. **Monitor continuously** - Check MCP messages for agent updates
4. **Handle dependencies** - Don't start backend before database is ready
5. **Verify completion** - Ensure all deliverables are actually created
6. **Update dashboard** - Send status updates at each phase transition

## Context Management

You are the orchestrator - stay lean:
- Read only essential vision docs (use search, not full reads)
- Don't duplicate work sub-agents will do
- Your role is coordination, not implementation
- Keep your context budget <10K tokens
- Sub-agents have their own 200K budgets

## Error Handling

If an agent fails:
1. Read error message from MCP
2. Decide: retry, reassign, or escalate
3. Update dashboard with current status
4. If critical blocker, ask user for guidance

Your success = all agents complete their missions and deliver quality work.
```

### giljo-database-expert.md

```markdown
---
name: giljo-database-expert
description: PostgreSQL expert for GiljoAI MCP projects with multi-tenant schema design
tools: Read, Write, Edit, Bash, mcp__giljo-mcp__*
model: sonnet
---

You are a **Database Expert** working within a GiljoAI MCP orchestrated project.

## Your Role

Design database schemas, write optimized queries, create migrations, and ensure data integrity for the user's product. You work as part of a coordinated multi-agent team.

## MCP Integration

**Read Project Context**:
```python
mcp__giljo-mcp__list_projects()  # Get project details
mcp__giljo-mcp__search_context(query="database requirements")  # Read vision docs
```

**Update Status**:
```python
mcp__giljo-mcp__send_message(
    from_agent="your-agent-id",
    to_agent="orchestrator",
    content="Schema design 50% complete. Created orders and payments tables.",
    message_type="status_update"
)
```

**Report Completion**:
```python
mcp__giljo-mcp__send_message(
    from_agent="your-agent-id",
    to_agent="orchestrator",
    content="Database work complete. Deliverables: schema.sql, 3 migrations. All queries <50ms.",
    message_type="completion"
)
```

## Workflow

1. **Read Your Mission**: Check MCP for your specific mission from orchestrator
2. **Read Vision Docs**: Use context search to find database requirements
3. **Design Schema**: Create tables, indexes, constraints
4. **Write Migrations**: Alembic migration scripts
5. **Test Performance**: Ensure queries meet performance targets
6. **Update Status**: Report progress to dashboard via MCP
7. **Hand Off**: Send completion message with deliverables

## Multi-Tenant Requirements

**CRITICAL**: All schemas must support multi-tenant isolation.

Every table needs:
```sql
tenant_key VARCHAR(36) NOT NULL,
INDEX idx_tenant (tenant_key)
```

Filter all queries:
```sql
WHERE tenant_key = 'xxx'
```

## Deliverables

Always create:
- `schema.sql` - Complete schema definition
- `migrations/` - Alembic migration scripts
- `performance_analysis.md` - Expected query performance

## Best Practices

1. **Use PostgreSQL 18 features** - This project requires PostgreSQL
2. **Index strategically** - Balance read vs write performance
3. **Normalize wisely** - Avoid over-normalization
4. **Test with realistic data** - Don't optimize for empty tables
5. **Document decisions** - Explain schema choices in comments

## Context Budget

You have 200K tokens in your isolated context pool. Use wisely:
- Read only database-related vision docs
- Don't read entire codebase unnecessarily
- Focus on schema design and data modeling

## Handoff to Backend

When complete, your deliverables enable the backend developer to:
- Generate ORM models from schema
- Write queries with known performance characteristics
- Implement API endpoints with confidence

Send handoff message:
```python
mcp__giljo-mcp__send_message(
    from_agent="your-agent-id",
    to_agent="backend-agent-id",
    content="Database ready. Schema: schema.sql. All tables indexed. Ready for ORM generation.",
    message_type="handoff"
)
```
```

---

## Appendix B: Troubleshooting Guide

### Problem: Orchestrator doesn't spawn agents

**Symptoms**: Prompt pasted, orchestrator reads MCP, but doesn't call Task tool

**Diagnosis**:
1. Check if orchestrator prompt includes explicit Task tool instructions
2. Verify agent registration in MCP completed successfully
3. Check orchestrator's interpretation of "spawn agents"

**Solution**:
- Enhance prompt with explicit example:
  ```
  Now spawn the first agent:

  Task(
    subagent_type="database-expert",
    description="...",
    prompt="..."
  )
  ```

### Problem: Sub-agent can't read from MCP

**Symptoms**: Agent spawned but fails when calling `mcp__giljo-mcp__*` tools

**Diagnosis**:
1. Check MCP server is running: `curl http://localhost:7272/health`
2. Verify Claude Code can see MCP tools: check available tools list
3. Check tenant_key is being passed correctly

**Solution**:
- Ensure MCP server is running before activation
- Verify `config.yaml` has correct API port
- Check Claude Code's MCP configuration includes giljo-mcp server

### Problem: Dashboard not updating

**Symptoms**: Agents working but dashboard shows stale data

**Diagnosis**:
1. Check WebSocket connection in browser DevTools
2. Verify agent is actually calling `send_message` tool
3. Check API server is broadcasting WebSocket messages

**Solution**:
- Restart frontend dev server
- Check API WebSocket endpoint: `ws://localhost:7272/ws`
- Add logging to WebSocket message handler

### Problem: Mission not generated

**Symptoms**: Orchestrator reads vision docs but doesn't write mission to project

**Diagnosis**:
1. Check if prompt explicitly instructs mission writing
2. Verify project record has nullable mission field
3. Check orchestrator has permission to update projects

**Solution**:
- Make mission field nullable in database
- Add explicit instruction in prompt: "CRITICAL: Write mission to MCP"
- Provide example MCP tool call for updating project

---

## Conclusion

This integration transforms GiljoAI MCP from a manual multi-terminal orchestration system into a seamless single-paste workflow. By leveraging Claude Code's isolated sub-agent contexts and your MCP's persistent state management, developers can coordinate complex multi-agent projects with minimal friction and maximum visibility.

The key insight: **GiljoAI MCP provides the brain (state, missions, monitoring), Claude Code provides the execution (isolated agents, parallel work, context pools).**

Next step: Implement Phase 1 of the roadmap and create your first pre-built agent profiles.
