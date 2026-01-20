# Multi-Tool Agent Orchestration - Developer Guide

**Version**: 3.1.0
**Last Updated**: 2025-10-25
**Audience**: Software Engineers, System Architects, Technical Contributors

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Adding New AI Tools](#adding-new-ai-tools)
4. [MCP Tool Development](#mcp-tool-development)
5. [Template Customization](#template-customization)
6. [Testing Strategy](#testing-strategy)
7. [Database Schema](#database-schema)
8. [API Endpoints](#api-endpoints)
9. [Extension Points](#extension-points)
10. [Performance Optimization](#performance-optimization)

---

## Architecture Overview

### System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         User / Dashboard                      │
└───────────────┬───────────────────────────────┬──────────────┘
                │ REST API                      │ WebSocket
                ▼                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      FastAPI Server (Port 7272)               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  API Endpoints                                         │  │
│  │  - /api/v1/agents                                      │  │
│  │  - /api/v1/templates                                   │  │
│  │  - /api/v1/jobs                                        │  │
│  │  - /mcp/* (7 coordination tools)                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                               │                               │
│                               ▼                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  ProjectOrchestrator (Multi-Tool Routing Logic)        │  │
│  │  - _get_agent_template() → Resolve template            │  │
│  │  - _spawn_claude_code_agent() → Hybrid mode            │  │
│  │  - _spawn_generic_agent() → CLI mode (Codex/Gemini)     │  │
│  │  - _generate_mcp_instructions() → MCP integration      │  │
│  │  - _generate_cli_prompt() → CLI prompt generation      │  │
│  └────────────┬───────────────────────────────────────────┘  │
│               │                                               │
│               ▼                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  AgentJobManager (Job Lifecycle Management)            │  │
│  │  - create_job() → Create MCPAgentJob record            │  │
│  │  - acknowledge_job() → Status: waiting → in_progress   │  │
│  │  - update_job_progress() → Update progress %           │  │
│  │  - complete_job() → Status: in_progress → completed    │  │
│  │  - fail_job() → Status: in_progress → failed           │  │
│  └────────────┬───────────────────────────────────────────┘  │
│               │                                               │
│               ▼                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  AgentCommunicationQueue (Messaging Layer)             │  │
│  │  - send_message() → Agent-to-agent messaging           │  │
│  │  - get_pending_messages() → Retrieve messages          │  │
│  │  - acknowledge_message() → Mark as read                │  │
│  └────────────┬───────────────────────────────────────────┘  │
│               │                                               │
└───────────────┼───────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                         │
│  - agents (job_id, mode fields added)                        │
│  - mcp_agent_jobs (status, progress tracking)                │
│  - agent_templates (preferred_tool field)                    │
└──────────────────────────────────────────────────────────────┘
                │
                │ (Event-Driven Sync)
                ▼
┌──────────────────────────────────────────────────────────────┐
│                    Agent Processes                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Claude Code  │  │   Codex CLI  │  │  Gemini CLI  │       │
│  │ (Hybrid)     │  │  (Legacy)    │  │  (Legacy)    │       │
│  │              │  │              │  │              │       │
│  │ Auto MCP ✓   │  │ Manual MCP   │  │ Manual MCP   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                           │                                   │
│                  MCP Tools (HTTP API)                         │
│                  - acknowledge_job                            │
│                  - report_progress                            │
│                  - complete_job                               │
│                  - send_message                               │
│                  - get_next_instruction                       │
│                  - report_error                               │
│                  - get_pending_jobs                           │
└──────────────────────────────────────────────────────────────┘
```

### Routing Decision Tree

```
Agent Spawn Request
  │
  ├─ Get Template (template_id or role)
  │   │
  │   └─ Template Resolution Cascade:
  │       1. Product-specific template (highest priority)
  │       2. Tenant-specific template
  │       3. System default template
  │       4. Legacy fallback (always succeeds)
  │
  ├─ Extract preferred_tool from Template
  │   │
  │   ├─ preferred_tool = "claude"
  │   │   └─> Call _spawn_claude_code_agent()
  │   │       - Create Agent record (mode = "claude")
  │   │       - Create MCPAgentJob (status = "in_progress")
  │   │       - Link: Agent.job_id = job.id
  │   │       - Generate mission with MCP instructions
  │   │       - Spawn in Claude Code (automatic)
  │   │       - Return agent_id
  │   │
  │   ├─ preferred_tool = "codex"
  │   │   └─> Call _spawn_generic_agent(tool="codex")
  │   │       - Create Agent record (mode = "codex")
  │   │       - Create MCPAgentJob (status = "waiting_acknowledgment")
  │   │       - Link: Agent.job_id = job.id
  │   │       - Generate CLI prompt with MCP instructions
  │   │       - Store prompt in agent.meta_data["cli_prompt"]
  │   │       - Return agent_id (user copies prompt manually)
  │   │
  │   └─ preferred_tool = "gemini"
  │       └─> Call _spawn_generic_agent(tool="gemini")
  │           - Create Agent record (mode = "gemini")
  │           - Create MCPAgentJob (status = "waiting_acknowledgment")
  │           - Link: Agent.job_id = job.id
  │           - Generate CLI prompt with MCP instructions
  │           - Store prompt in agent.meta_data["cli_prompt"]
  │           - Return agent_id (user copies prompt manually)
  │
  └─ Event-Driven Status Sync:
      - Agent status change → Update MCPAgentJob.status
      - MCPAgentJob.status change → Update Agent.status
      - WebSocket broadcast → Dashboard updates in real-time
```

### Agent-Job Relationship

**Database Schema**:
```sql
-- Agent model
CREATE TABLE agents (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL,
    name VARCHAR(200) NOT NULL,
    role VARCHAR(200) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    -- Multi-tool orchestration fields (Handover 0045)
    job_id VARCHAR(36) NULL,           -- Links to mcp_agent_jobs.id
    mode VARCHAR(20) DEFAULT 'claude', -- claude | codex | gemini
    ...
);

-- MCPAgentJob model
CREATE TABLE mcp_agent_jobs (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    agent_id VARCHAR(36) NULL,         -- Links to agents.id
    mission TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'waiting_acknowledgment',
    progress INTEGER DEFAULT 0,
    ...
);

-- Relationship: Agent.job_id → MCPAgentJob.id (one-to-one)
CREATE INDEX idx_agent_job_id ON agents(job_id);
```

**Lifecycle**:
```
1. Agent spawned → Create Agent + MCPAgentJob
2. Agent.job_id = MCPAgentJob.id (link established)
3. Agent acknowledges → MCPAgentJob.status = "in_progress"
4. Agent reports progress → MCPAgentJob.progress updated
5. Agent completes → MCPAgentJob.status = "completed"
6. Event-driven sync → Agent.status = "decommissioned"
```

### MCP Coordination Layer

**Purpose**: Universal coordination protocol for agents across different AI tools.

**Components**:
1. **MCP Tools** (7 total): HTTP endpoints agents call to coordinate
2. **AgentJobManager**: Backend service managing job lifecycle
3. **AgentCommunicationQueue**: Message passing between agents
4. **WebSocket Events**: Real-time status updates to dashboard

**Flow**:
```
Agent (any tool)
  ↓ HTTP POST
MCP Endpoint (/mcp/acknowledge_job)
  ↓
AgentJobManager.acknowledge_job()
  ↓
Database Update (MCPAgentJob.status = "in_progress")
  ↓
WebSocket Event (job:status_changed)
  ↓
Dashboard (status badge updates instantly)
```

---

## Core Components

### 1. ProjectOrchestrator (Routing Logic)

**File**: `src/giljo_mcp/orchestrator.py`

**Responsibility**: Route agent spawning to appropriate tool based on template configuration.

#### Key Methods

**_get_agent_template(role: str, product_id: Optional[str]) → AgentTemplate**

```python
async def _get_agent_template(
    self, role: str, product_id: Optional[str] = None
) -> AgentTemplate:
    """
    Resolve agent template using cascade:
    1. Product-specific template (if product_id provided)
    2. Tenant-specific template
    3. System default template
    4. Legacy fallback (hard-coded)

    Returns:
        AgentTemplate with preferred_tool field set
    """
    tenant_key = self.db_manager.tenant_manager.get_current_tenant()

    # Try product-specific first
    if product_id:
        template = await self.template_manager.get_template(
            role=role,
            tenant_key=tenant_key,
            product_id=product_id
        )
        if template:
            return template

    # Try tenant-specific
    template = await self.template_manager.get_template(
        role=role,
        tenant_key=tenant_key
    )
    if template:
        return template

    # Try system default
    template = await self.template_manager.get_template(
        role=role,
        tenant_key="system"
    )
    if template:
        return template

    # Legacy fallback (always succeeds)
    return self._get_legacy_template(role)
```

**_spawn_claude_code_agent(agent_name, mission, template) → str**

```python
async def _spawn_claude_code_agent(
    self,
    agent_name: str,
    mission: str,
    template: AgentTemplate,
    project_id: str
) -> str:
    """
    Spawn agent in Claude Code (hybrid mode).

    Workflow:
    1. Create Agent record (mode = "claude")
    2. Create MCPAgentJob (status = "in_progress" - automatic acknowledgment)
    3. Link: Agent.job_id = job.id
    4. Generate mission prompt with MCP instructions
    5. Spawn in Claude Code via claude_code_integration.py
    6. Return agent_id

    Args:
        agent_name: Agent name (e.g., "Implementer-001")
        mission: Mission description
        template: Resolved agent template
        project_id: Project ID

    Returns:
        agent_id: UUID of created agent
    """
    tenant_key = self.db_manager.tenant_manager.get_current_tenant()

    # 1. Create Agent record
    agent = Agent(
        id=generate_uuid(),
        tenant_key=tenant_key,
        project_id=project_id,
        name=agent_name,
        role=template.role,
        status="active",
        mission=mission,
        mode="claude"  # Hybrid mode
    )

    # 2. Create MCPAgentJob
    job = await self.agent_job_manager.create_job(
        tenant_key=tenant_key,
        agent_id=agent.id,
        mission=mission,
        priority="normal",
        status="in_progress"  # Auto-acknowledged for hybrid mode
    )

    # 3. Link Agent → Job
    agent.job_id = job.id

    # 4. Save to database
    async with self.db_manager.get_session_async() as session:
        session.add(agent)
        await session.commit()

    # 5. Generate mission with MCP instructions
    mcp_instructions = self._generate_mcp_instructions(
        job_id=job.id,
        agent_id=agent.id,
        tenant_key=tenant_key,
        mode="hybrid"
    )

    full_mission = f"{template.content}\n\n{mcp_instructions}\n\n{mission}"

    # 6. Spawn in Claude Code
    await self.claude_code_integration.spawn_agent(
        agent_id=agent.id,
        mission=full_mission
    )

    # 7. WebSocket broadcast
    await self.websocket_manager.broadcast_agent_update(
        agent_id=agent.id,
        agent_name=agent_name,
        project_id=project_id,
        tenant_key=tenant_key,
        status="active",
        mode="claude"
    )

    return agent.id
```

**_spawn_generic_agent(agent_name, mission, template, tool) → str**

```python
async def _spawn_generic_agent(
    self,
    agent_name: str,
    mission: str,
    template: AgentTemplate,
    tool: str,  # "codex" or "gemini"
    project_id: str
) -> str:
    """
    Spawn agent in legacy CLI mode (Codex or Gemini).

    Workflow:
    1. Create Agent record (mode = tool)
    2. Create MCPAgentJob (status = "waiting_acknowledgment")
    3. Link: Agent.job_id = job.id
    4. Generate CLI prompt with MCP instructions
    5. Store prompt in agent.meta_data["cli_prompt"]
    6. Return agent_id (user copies prompt manually)

    Args:
        agent_name: Agent name (e.g., "Tester-001")
        mission: Mission description
        template: Resolved agent template
        tool: "codex" or "gemini"
        project_id: Project ID

    Returns:
        agent_id: UUID of created agent
    """
    tenant_key = self.db_manager.tenant_manager.get_current_tenant()

    # 1. Create Agent record
    agent = Agent(
        id=generate_uuid(),
        tenant_key=tenant_key,
        project_id=project_id,
        name=agent_name,
        role=template.role,
        status="active",
        mission=mission,
        mode=tool  # "codex" or "gemini"
    )

    # 2. Create MCPAgentJob
    job = await self.agent_job_manager.create_job(
        tenant_key=tenant_key,
        agent_id=agent.id,
        mission=mission,
        priority="normal",
        status="waiting_acknowledgment"  # Requires manual acknowledgment
    )

    # 3. Link Agent → Job
    agent.job_id = job.id

    # 4. Generate CLI prompt
    cli_prompt = self._generate_cli_prompt(
        job_id=job.id,
        agent_id=agent.id,
        tenant_key=tenant_key,
        template=template,
        mission=mission,
        tool=tool
    )

    # 5. Store prompt in metadata
    agent.meta_data = {
        "cli_prompt": cli_prompt,
        "tool": tool,
        "requires_manual_start": True
    }

    # 6. Save to database
    async with self.db_manager.get_session_async() as session:
        session.add(agent)
        await session.commit()

    # 7. WebSocket broadcast
    await self.websocket_manager.broadcast_agent_update(
        agent_id=agent.id,
        agent_name=agent_name,
        project_id=project_id,
        tenant_key=tenant_key,
        status="waiting_cli",
        mode=tool
    )

    return agent.id
```

**_generate_mcp_instructions(job_id, agent_id, tenant_key, mode) → str**

```python
def _generate_mcp_instructions(
    self,
    job_id: str,
    agent_id: str,
    tenant_key: str,
    mode: str  # "hybrid" or "legacy"
) -> str:
    """
    Generate MCP coordination instructions for agent mission.

    Args:
        job_id: MCPAgentJob ID
        agent_id: Agent ID
        tenant_key: Tenant key for isolation
        mode: "hybrid" (automatic) or "legacy" (manual)

    Returns:
        Markdown-formatted MCP instructions
    """
    if mode == "hybrid":
        return f"""
## MCP Coordination (Hybrid Mode - Automatic)

You are running in **Hybrid Mode** with automatic MCP coordination.

**Automatic Features**:
- Job acknowledged automatically on spawn
- Progress reported automatically every 10 minutes
- Status synchronized automatically (Agent ↔ Job)
- Completion tracked automatically

**Manual MCP Tools** (available if needed):
- `send_message`: Communicate with other agents
- `get_next_instruction`: Request updated instructions
- `report_error`: Escalate critical errors
- `report_progress`: Force immediate progress update

**Your Job**:
- Job ID: {job_id}
- Agent ID: {agent_id}
- Tenant: {tenant_key}

Work normally - MCP coordination is automatic!
"""
    else:  # legacy mode
        return f"""
## MCP Coordination (Legacy CLI Mode - Manual)

You are running in **Legacy CLI Mode** with manual MCP coordination.

**CRITICAL: You MUST call MCP tools to track your work!**

**Required MCP Tools**:

1. **acknowledge_job** (FIRST ACTION):
```python
# Call this immediately to confirm you've started
acknowledge_job(
    job_id="{job_id}",
    agent_id="{agent_id}",
    tenant_key="{tenant_key}"
)
```

2. **report_progress** (Every 15 minutes):
```python
# Report current progress percentage and status
report_progress(
    job_id="{job_id}",
    progress_data={{
        "percentage": 50,  # 0-100
        "message": "Current milestone description",
        "details": "What you've accomplished so far"
    }}
)
```

3. **complete_job** (LAST ACTION):
```python
# Mark job as completed when done
complete_job(
    job_id="{job_id}",
    summary="Completed successfully. Summary of work done.",
    tenant_key="{tenant_key}"
)
```

**Optional MCP Tools**:

4. **send_message** (Ask questions):
```python
# Send message to Orchestrator or other agents
send_message(
    from_agent_id="{agent_id}",
    to_agent_id="<recipient_agent_id>",
    message="Your question or update",
    priority="normal",
    tenant_key="{tenant_key}"
)
```

5. **get_next_instruction** (Get updates):
```python
# Retrieve latest instruction from Orchestrator
get_next_instruction(
    job_id="{job_id}",
    tenant_key="{tenant_key}"
)
```

6. **report_error** (Critical errors):
```python
# Report unrecoverable error
report_error(
    job_id="{job_id}",
    error_details={{
        "error_type": "dependency_missing",
        "message": "Error description",
        "recovery_suggestion": "How to fix"
    }},
    tenant_key="{tenant_key}"
)
```

**Your Job**:
- Job ID: {job_id}
- Agent ID: {agent_id}
- Tenant: {tenant_key}

⚠️ WITHOUT MCP CALLS, YOUR WORK WILL NOT BE TRACKED!

**Workflow**:
1. Call acknowledge_job (FIRST)
2. Do your work
3. Call report_progress every 15 minutes
4. Call complete_job when done (LAST)
"""
```

**_generate_cli_prompt(job_id, agent_id, tenant_key, template, mission, tool) → str**

```python
def _generate_cli_prompt(
    self,
    job_id: str,
    agent_id: str,
    tenant_key: str,
    template: AgentTemplate,
    mission: str,
    tool: str
) -> str:
    """
    Generate complete CLI prompt for copy-paste into Codex/Gemini.

    Includes:
    - Agent role and identity
    - Template content (behavioral rules, success criteria)
    - MCP coordination instructions (legacy mode)
    - Mission details
    - Tool-specific formatting

    Returns:
        Complete CLI prompt (Markdown formatted)
    """
    mcp_instructions = self._generate_mcp_instructions(
        job_id=job_id,
        agent_id=agent_id,
        tenant_key=tenant_key,
        mode="legacy"
    )

    tool_specific_header = ""
    if tool == "codex":
        tool_specific_header = "# OpenAI Codex Agent - GiljoAI MCP Integration\n\n"
    elif tool == "gemini":
        tool_specific_header = "# Google Gemini Agent - GiljoAI MCP Integration\n\n"

    return f"""{tool_specific_header}
{template.content}

---

{mcp_instructions}

---

## Your Mission

{mission}

---

## Getting Started

1. **FIRST**: Call `acknowledge_job` to confirm you've started
2. **WORK**: Complete your mission following the behavioral rules above
3. **PROGRESS**: Call `report_progress` every 15 minutes with status update
4. **QUESTIONS**: Call `send_message` if you need clarification from Orchestrator
5. **LAST**: Call `complete_job` when finished

Good luck! 🚀
"""
```

### 2. AgentJobManager Integration

**File**: `src/giljo_mcp/agent_job_manager.py`

**Responsibility**: Manage job lifecycle, sync with Agent model.

**Key Methods**:

```python
class AgentJobManager:
    async def create_job(
        self,
        tenant_key: str,
        agent_id: str,
        mission: str,
        priority: str = "normal",
        status: str = "waiting_acknowledgment"
    ) -> MCPAgentJob:
        """
        Create new job record.

        Status:
        - "waiting_acknowledgment": Hybrid mode auto-acknowledges, legacy mode waits for manual ack
        - "in_progress": Agent acknowledged and working
        - "completed": Agent finished successfully
        - "failed": Agent encountered unrecoverable error
        """
        ...

    async def acknowledge_job(
        self,
        job_id: str,
        agent_id: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Acknowledge job (manual for legacy mode, automatic for hybrid mode).

        Updates:
        - MCPAgentJob.status: "waiting_acknowledgment" → "in_progress"
        - MCPAgentJob.acknowledged_at: current timestamp

        Events:
        - WebSocket: job:status_changed
        - WebSocket: agent:status_changed
        """
        ...

    async def update_job_progress(
        self,
        job_id: str,
        progress_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update job progress.

        progress_data:
        - percentage: int (0-100)
        - message: str (milestone description)
        - details: str (optional, detailed status)

        Events:
        - WebSocket: job:progress_updated
        """
        ...

    async def complete_job(
        self,
        job_id: str,
        summary: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Mark job as completed.

        Updates:
        - MCPAgentJob.status: "in_progress" → "completed"
        - MCPAgentJob.completed_at: current timestamp
        - MCPAgentJob.summary: completion summary
        - Agent.status: "active" → "decommissioned"

        Events:
        - WebSocket: job:completed
        - WebSocket: agent:status_changed
        """
        ...

    async def fail_job(
        self,
        job_id: str,
        error_details: Dict[str, Any],
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Mark job as failed.

        Updates:
        - MCPAgentJob.status: "in_progress" → "failed"
        - MCPAgentJob.error_details: error information
        - Agent.status: "active" → "decommissioned"

        Events:
        - WebSocket: job:failed
        - WebSocket: agent:status_changed
        """
        ...
```

### 3. AgentCommunicationQueue

**File**: `src/giljo_mcp/agent_communication_queue.py`

**Responsibility**: Inter-agent messaging.

**Key Methods**:

```python
class AgentCommunicationQueue:
    async def send_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message: str,
        priority: str,
        tenant_key: str
    ) -> str:
        """
        Send message from one agent to another.

        JSONB Storage:
        - message_id: UUID
        - from_agent_id: sender
        - to_agent_id: recipient
        - message: content
        - priority: low | normal | high
        - acknowledged: False (until recipient reads)

        Events:
        - WebSocket: message:sent (to recipient)
        """
        ...

    async def get_pending_messages(
        self,
        agent_id: str,
        tenant_key: str
    ) -> List[Dict[str, Any]]:
        """
        Get unread messages for agent.

        Returns:
        - List of messages ordered by priority (high first), then timestamp
        """
        ...

    async def acknowledge_message(
        self,
        message_id: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Mark message as read.

        Updates:
        - message.acknowledged: True
        - message.acknowledged_at: current timestamp
        """
        ...
```

---

## Adding New AI Tools

Want to add support for a new AI coding tool? Follow this guide.

### Step 1: Add Tool to AgentTemplate.tool Enum

**File**: `src/giljo_mcp/models.py`

```python
class AgentTemplate(Base):
    """
    Agent template model
    """
    __tablename__ = "agent_templates"

    # Existing fields...

    # Preferred tool (multi-tool orchestration)
    preferred_tool = Column(
        Enum("claude", "codex", "gemini", "cursor", "windsurf", name="tool_enum"),
        #                                  ^^^^^^  ^^^^^^^^^ (NEW TOOLS)
        default="claude"
    )
```

**Migration**:
```sql
-- Add new tool to enum
ALTER TYPE tool_enum ADD VALUE 'cursor';
ALTER TYPE tool_enum ADD VALUE 'windsurf';
```

### Step 2: Implement Routing Logic

**File**: `src/giljo_mcp/orchestrator.py`

Add tool-specific spawning method:

```python
async def _spawn_cursor_agent(
    self,
    agent_name: str,
    mission: str,
    template: AgentTemplate,
    project_id: str
) -> str:
    """
    Spawn agent in Cursor IDE (hybrid mode).

    Similar to _spawn_claude_code_agent, but Cursor-specific.
    """
    tenant_key = self.db_manager.tenant_manager.get_current_tenant()

    # 1. Create Agent record (mode = "cursor")
    agent = Agent(
        id=generate_uuid(),
        tenant_key=tenant_key,
        project_id=project_id,
        name=agent_name,
        role=template.role,
        status="active",
        mission=mission,
        mode="cursor"  # NEW MODE
    )

    # 2. Create MCPAgentJob (status = "in_progress" for hybrid mode)
    job = await self.agent_job_manager.create_job(
        tenant_key=tenant_key,
        agent_id=agent.id,
        mission=mission,
        priority="normal",
        status="in_progress"  # Auto-acknowledged
    )

    # 3. Link Agent → Job
    agent.job_id = job.id

    # 4. Save to database
    async with self.db_manager.get_session_async() as session:
        session.add(agent)
        await session.commit()

    # 5. Generate mission with MCP instructions
    mcp_instructions = self._generate_mcp_instructions(
        job_id=job.id,
        agent_id=agent.id,
        tenant_key=tenant_key,
        mode="hybrid"  # Cursor supports hybrid mode
    )

    full_mission = f"{template.content}\n\n{mcp_instructions}\n\n{mission}"

    # 6. Spawn in Cursor (integrate with Cursor API/CLI)
    await self.cursor_integration.spawn_agent(
        agent_id=agent.id,
        mission=full_mission
    )

    # 7. WebSocket broadcast
    await self.websocket_manager.broadcast_agent_update(
        agent_id=agent.id,
        agent_name=agent_name,
        project_id=project_id,
        tenant_key=tenant_key,
        status="active",
        mode="cursor"
    )

    return agent.id
```

Update `spawn_agent()` routing:

```python
async def spawn_agent(
    self,
    project_id: str,
    agent_name: str,
    role: str,
    mission: str
) -> str:
    """
    Spawn agent using template-configured tool.
    """
    # 1. Get template
    template = await self._get_agent_template(role, project_id)

    # 2. Route based on preferred_tool
    if template.preferred_tool == "claude":
        return await self._spawn_claude_code_agent(
            agent_name, mission, template, project_id
        )
    elif template.preferred_tool == "codex":
        return await self._spawn_generic_agent(
            agent_name, mission, template, "codex", project_id
        )
    elif template.preferred_tool == "gemini":
        return await self._spawn_generic_agent(
            agent_name, mission, template, "gemini", project_id
        )
    elif template.preferred_tool == "cursor":  # NEW TOOL
        return await self._spawn_cursor_agent(
            agent_name, mission, template, project_id
        )
    elif template.preferred_tool == "windsurf":  # NEW TOOL
        return await self._spawn_windsurf_agent(
            agent_name, mission, template, project_id
        )
    else:
        raise ValueError(f"Unsupported tool: {template.preferred_tool}")
```

### Step 3: Create Tool Integration Module

**File**: `src/giljo_mcp/tools/cursor_integration.py` (new file)

```python
"""
Cursor IDE integration for agent spawning.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CursorIntegration:
    """
    Integration with Cursor IDE for hybrid mode agent spawning.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Cursor integration.

        Args:
            config: Configuration dict with Cursor API credentials
        """
        self.config = config
        self.cursor_api_endpoint = config.get("cursor_api_endpoint")
        self.cursor_api_key = config.get("cursor_api_key")

    async def spawn_agent(
        self,
        agent_id: str,
        mission: str
    ) -> Dict[str, Any]:
        """
        Spawn agent in Cursor IDE.

        Args:
            agent_id: Agent ID
            mission: Full mission prompt (includes MCP instructions)

        Returns:
            Result dict with spawn status
        """
        try:
            # Call Cursor API to spawn agent
            # This is tool-specific - implement based on Cursor's API

            response = await self._call_cursor_api(
                endpoint="/spawn_agent",
                payload={
                    "agent_id": agent_id,
                    "mission": mission,
                    "api_key": self.cursor_api_key
                }
            )

            logger.info(f"Spawned Cursor agent {agent_id}")

            return {
                "success": True,
                "agent_id": agent_id,
                "tool": "cursor",
                "mode": "hybrid"
            }

        except Exception as e:
            logger.error(f"Failed to spawn Cursor agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _call_cursor_api(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Cursor API endpoint.

        Implement based on Cursor's API documentation.
        """
        # TODO: Implement Cursor API calls
        pass
```

### Step 4: Add UI Components

**File**: `frontend/src/components/AgentCard.vue`

Add tool logo and badge:

```vue
<template>
  <v-card>
    <!-- Agent card content -->

    <!-- Tool Logo -->
    <v-img
      v-if="agent.mode === 'cursor'"
      src="/assets/cursor-logo.svg"
      width="24"
      height="24"
      class="tool-logo"
    />

    <!-- Mode Badge -->
    <v-chip
      v-if="agent.mode === 'cursor'"
      color="purple"
      size="small"
    >
      Cursor (Hybrid)
    </v-chip>

    <!-- Copy Prompt Button (if legacy CLI mode) -->
    <v-btn
      v-if="agent.mode === 'cursor' && agent.meta_data.requires_manual_start"
      @click="copyPrompt"
      variant="outlined"
    >
      Copy Prompt
    </v-btn>
  </v-card>
</template>

<script setup>
// Component logic
const copyPrompt = () => {
  const prompt = agent.meta_data.cli_prompt
  navigator.clipboard.writeText(prompt)
  // Show toast notification
}
</script>
```

**File**: `frontend/src/components/TemplateManager.vue`

Add tool to dropdown:

```vue
<template>
  <v-dialog v-model="editDialog">
    <v-card>
      <v-card-title>Edit Template</v-card-title>

      <v-card-text>
        <!-- Preferred Tool Dropdown -->
        <v-select
          v-model="template.preferred_tool"
          :items="availableTools"
          label="Preferred AI Tool"
          hint="Select which AI tool agents should use"
          persistent-hint
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
const availableTools = [
  { title: 'Claude Code (Hybrid)', value: 'claude' },
  { title: 'Codex (Legacy CLI)', value: 'codex' },
  { title: 'Gemini (Legacy CLI)', value: 'gemini' },
  { title: 'Cursor (Hybrid)', value: 'cursor' },        // NEW
  { title: 'Windsurf (Legacy CLI)', value: 'windsurf' } // NEW
]
</script>
```

### Step 5: Add Integration Tests

**File**: `tests/integration/test_cursor_agent_spawning.py` (new file)

```python
"""
Integration tests for Cursor agent spawning.
"""

import pytest
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.models import AgentTemplate


@pytest.mark.asyncio
async def test_spawn_cursor_agent_hybrid_mode(
    db_manager, template_manager, orchestrator
):
    """
    Test spawning Cursor agent in hybrid mode.
    """
    # 1. Create template with preferred_tool = "cursor"
    template = AgentTemplate(
        tenant_key="test_tenant",
        name="Implementer",
        role="implementer",
        category="role",
        preferred_tool="cursor",
        content="Test template content"
    )

    async with db_manager.get_session_async() as session:
        session.add(template)
        await session.commit()

    # 2. Spawn agent
    agent_id = await orchestrator.spawn_agent(
        project_id="test_project",
        agent_name="Implementer-001",
        role="implementer",
        mission="Test mission"
    )

    # 3. Verify agent created with correct mode
    async with db_manager.get_session_async() as session:
        agent = await session.get(Agent, agent_id)
        assert agent.mode == "cursor"
        assert agent.status == "active"
        assert agent.job_id is not None

    # 4. Verify job created
    async with db_manager.get_session_async() as session:
        job = await session.get(MCPAgentJob, agent.job_id)
        assert job.status == "in_progress"  # Auto-acknowledged for hybrid mode
        assert job.agent_id == agent_id


@pytest.mark.asyncio
async def test_cursor_agent_mcp_coordination(
    db_manager, agent_job_manager, orchestrator
):
    """
    Test MCP coordination for Cursor agent.
    """
    # 1. Spawn Cursor agent
    agent_id = await orchestrator.spawn_agent(
        project_id="test_project",
        agent_name="Tester-001",
        role="tester",
        mission="Write unit tests"
    )

    # 2. Agent reports progress (simulated)
    async with db_manager.get_session_async() as session:
        agent = await session.get(Agent, agent_id)
        job_id = agent.job_id

    result = await agent_job_manager.update_job_progress(
        job_id=job_id,
        progress_data={
            "percentage": 50,
            "message": "Half of tests written",
            "details": "10 out of 20 tests completed"
        }
    )

    assert result["success"] is True

    # 3. Verify progress updated
    async with db_manager.get_session_async() as session:
        job = await session.get(MCPAgentJob, job_id)
        assert job.progress == 50

    # 4. Agent completes job
    result = await agent_job_manager.complete_job(
        job_id=job_id,
        summary="All tests written successfully",
        tenant_key="test_tenant"
    )

    assert result["success"] is True

    # 5. Verify job completed
    async with db_manager.get_session_async() as session:
        job = await session.get(MCPAgentJob, job_id)
        assert job.status == "completed"

        agent = await session.get(Agent, agent_id)
        assert agent.status == "decommissioned"
```

---

## MCP Tool Development

Extend MCP coordination with new tools.

### Creating New MCP Tools

**File**: `src/giljo_mcp/tools/agent_coordination.py`

Structure:

```python
"""
MCP coordination tools for agent orchestration.
"""

import logging
from typing import Dict, Any, List
from src.giljo_mcp.agent_job_manager import AgentJobManager
from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

logger = logging.getLogger(__name__)


def register_agent_coordination_tools(mcp_server):
    """
    Register MCP coordination tools with server.

    Args:
        mcp_server: MCP server instance
    """

    # Tool 1: get_pending_jobs
    @mcp_server.tool()
    async def get_pending_jobs(
        agent_id: str,
        tenant_key: str
    ) -> List[Dict[str, Any]]:
        """
        Get jobs waiting to be acknowledged by agent.

        Args:
            agent_id: Agent ID
            tenant_key: Tenant key (multi-tenant isolation)

        Returns:
            List of pending jobs ordered by priority
        """
        try:
            job_manager = AgentJobManager(db_manager=mcp_server.db_manager)

            jobs = await job_manager.get_pending_jobs(
                agent_id=agent_id,
                tenant_key=tenant_key
            )

            logger.info(f"Retrieved {len(jobs)} pending jobs for agent {agent_id}")

            return jobs

        except Exception as e:
            logger.error(f"Error retrieving pending jobs: {e}")
            return []

    # Tool 2: acknowledge_job
    @mcp_server.tool()
    async def acknowledge_job(
        job_id: str,
        agent_id: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Acknowledge job and start working.

        Args:
            job_id: Job ID
            agent_id: Agent ID
            tenant_key: Tenant key

        Returns:
            Result dict with success status
        """
        try:
            job_manager = AgentJobManager(db_manager=mcp_server.db_manager)

            result = await job_manager.acknowledge_job(
                job_id=job_id,
                agent_id=agent_id,
                tenant_key=tenant_key
            )

            logger.info(f"Agent {agent_id} acknowledged job {job_id}")

            return result

        except Exception as e:
            logger.error(f"Error acknowledging job: {e}")
            return {"success": False, "error": str(e)}

    # Tool 3: report_progress
    @mcp_server.tool()
    async def report_progress(
        job_id: str,
        progress_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Report progress checkpoint.

        Args:
            job_id: Job ID
            progress_data: Progress info (percentage, message, details)

        Returns:
            Result dict with success status
        """
        try:
            job_manager = AgentJobManager(db_manager=mcp_server.db_manager)

            result = await job_manager.update_job_progress(
                job_id=job_id,
                progress_data=progress_data
            )

            logger.info(
                f"Job {job_id} progress updated: {progress_data.get('percentage')}%"
            )

            return result

        except Exception as e:
            logger.error(f"Error reporting progress: {e}")
            return {"success": False, "error": str(e)}

    # Tool 4: get_next_instruction
    @mcp_server.tool()
    async def get_next_instruction(
        job_id: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Get latest instruction from Orchestrator.

        Args:
            job_id: Job ID
            tenant_key: Tenant key

        Returns:
            Instruction dict or None if no updates
        """
        try:
            comm_queue = AgentCommunicationQueue(db_manager=mcp_server.db_manager)

            # Get agent ID from job
            async with mcp_server.db_manager.get_session_async() as session:
                job = await session.get(MCPAgentJob, job_id)
                agent_id = job.agent_id

            # Get pending messages for agent
            messages = await comm_queue.get_pending_messages(
                agent_id=agent_id,
                tenant_key=tenant_key
            )

            if messages:
                # Return latest high-priority message
                return messages[0]
            else:
                return {"message": "No new instructions"}

        except Exception as e:
            logger.error(f"Error getting next instruction: {e}")
            return {"error": str(e)}

    # Tool 5: complete_job
    @mcp_server.tool()
    async def complete_job(
        job_id: str,
        summary: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Mark job as completed.

        Args:
            job_id: Job ID
            summary: Completion summary
            tenant_key: Tenant key

        Returns:
            Result dict with success status
        """
        try:
            job_manager = AgentJobManager(db_manager=mcp_server.db_manager)

            result = await job_manager.complete_job(
                job_id=job_id,
                summary=summary,
                tenant_key=tenant_key
            )

            logger.info(f"Job {job_id} marked as completed")

            return result

        except Exception as e:
            logger.error(f"Error completing job: {e}")
            return {"success": False, "error": str(e)}

    # Tool 6: report_error
    @mcp_server.tool()
    async def report_error(
        job_id: str,
        error_details: Dict[str, Any],
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Report critical error and fail job.

        Args:
            job_id: Job ID
            error_details: Error information
            tenant_key: Tenant key

        Returns:
            Result dict with success status
        """
        try:
            job_manager = AgentJobManager(db_manager=mcp_server.db_manager)

            result = await job_manager.fail_job(
                job_id=job_id,
                error_details=error_details,
                tenant_key=tenant_key
            )

            logger.error(f"Job {job_id} failed: {error_details.get('message')}")

            return result

        except Exception as e:
            logger.error(f"Error reporting error: {e}")
            return {"success": False, "error": str(e)}

    # Tool 7: send_message
    @mcp_server.tool()
    async def send_message(
        from_agent_id: str,
        to_agent_id: str,
        message: str,
        priority: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Send message to another agent.

        Args:
            from_agent_id: Sender agent ID
            to_agent_id: Recipient agent ID
            message: Message content
            priority: low | normal | high
            tenant_key: Tenant key

        Returns:
            Result dict with message_id
        """
        try:
            comm_queue = AgentCommunicationQueue(db_manager=mcp_server.db_manager)

            message_id = await comm_queue.send_message(
                from_agent_id=from_agent_id,
                to_agent_id=to_agent_id,
                message=message,
                priority=priority,
                tenant_key=tenant_key
            )

            logger.info(
                f"Message sent from {from_agent_id} to {to_agent_id}: {message_id}"
            )

            return {
                "success": True,
                "message_id": message_id
            }

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
```

### Tool Registration

**File**: `src/giljo_mcp/tools/__init__.py`

```python
"""
MCP tools package initialization.
"""

from .agent_coordination import register_agent_coordination_tools


def register_all_tools(mcp_server):
    """
    Register all MCP tools with server.

    Args:
        mcp_server: MCP server instance
    """
    register_agent_coordination_tools(mcp_server)
    # Register other tool categories...
```

### Multi-Tenant Isolation Enforcement

**All MCP tools MUST enforce tenant isolation**:

```python
@mcp_server.tool()
async def acknowledge_job(
    job_id: str,
    agent_id: str,
    tenant_key: str
) -> Dict[str, Any]:
    """
    Acknowledge job with tenant isolation.
    """
    try:
        # 1. Get current tenant from context
        current_tenant = mcp_server.tenant_manager.get_current_tenant()

        # 2. Verify tenant_key matches current tenant
        if tenant_key != current_tenant:
            logger.warning(
                f"Tenant mismatch: provided={tenant_key}, current={current_tenant}"
            )
            return {
                "success": False,
                "error": "Tenant key mismatch (403 Forbidden)"
            }

        # 3. Verify job belongs to tenant
        async with mcp_server.db_manager.get_session_async() as session:
            job = await session.get(MCPAgentJob, job_id)

            if not job:
                return {"success": False, "error": "Job not found (404)"}

            if job.tenant_key != tenant_key:
                logger.warning(
                    f"Cross-tenant access attempt: job.tenant={job.tenant_key}, "
                    f"provided={tenant_key}"
                )
                return {
                    "success": False,
                    "error": "Permission denied (403 Forbidden)"
                }

        # 4. Proceed with operation (tenant verified)
        job_manager = AgentJobManager(db_manager=mcp_server.db_manager)
        return await job_manager.acknowledge_job(job_id, agent_id, tenant_key)

    except Exception as e:
        logger.error(f"Error in acknowledge_job: {e}")
        return {"success": False, "error": str(e)}
```

### Error Handling Patterns

**Standard error response**:

```python
@mcp_server.tool()
async def some_mcp_tool(param: str) -> Dict[str, Any]:
    """
    MCP tool with standard error handling.
    """
    try:
        # Tool implementation
        result = await perform_operation(param)

        return {
            "success": True,
            "data": result
        }

    except ValueError as e:
        # Invalid input (400 Bad Request)
        logger.warning(f"Invalid input: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_code": "invalid_input"
        }

    except PermissionError as e:
        # Permission denied (403 Forbidden)
        logger.warning(f"Permission denied: {e}")
        return {
            "success": False,
            "error": "Permission denied",
            "error_code": "forbidden"
        }

    except KeyError as e:
        # Resource not found (404 Not Found)
        logger.warning(f"Resource not found: {e}")
        return {
            "success": False,
            "error": f"Resource not found: {e}",
            "error_code": "not_found"
        }

    except Exception as e:
        # Internal server error (500)
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Internal server error",
            "error_code": "internal_error"
        }
```

---

## Template Customization

Deep dive into template structure and customization.

### Template Structure

Templates are Markdown documents with special sections:

```markdown
# Agent Role: {role}

**Identity**:
- Role: {role}
- Specialization: {specialization}
- Preferred Tool: {preferred_tool}

---

## Behavioral Rules

1. **Rule 1**: Description (MUST/MUST NOT language)
2. **Rule 2**: Description
3. **Rule 3**: Description
...

---

## Success Criteria

1. **Criterion 1**: Measurable outcome
2. **Criterion 2**: Quality standard
3. **Criterion 3**: Validation requirement
...

---

## Variables

- `{project_name}`: Name of the project
- `{mission}`: Specific mission assigned to agent
- `{custom_augmentation}`: Additional context
- `{tool_specific_var}`: Tool-specific variable
...

---

## Mission Template

{mission}

**Project**: {project_name}

**Additional Context**: {custom_augmentation}

---

## Tool-Specific Instructions

[Tool-specific guidance based on preferred_tool]
```

### Variable Substitution

Variables are replaced at mission generation time:

```python
def generate_mission(
    template: AgentTemplate,
    variables: Dict[str, Any]
) -> str:
    """
    Generate mission by substituting variables in template.

    Args:
        template: Agent template with placeholders
        variables: Variable values to substitute

    Returns:
        Rendered mission content
    """
    content = template.content

    # Substitute each variable
    for var_name, var_value in variables.items():
        placeholder = f"{{{var_name}}}"
        content = content.replace(placeholder, str(var_value))

    # Check for unsubstituted variables (error)
    import re
    unsubstituted = re.findall(r"\{([^}]+)\}", content)

    if unsubstituted:
        logger.warning(
            f"Unsubstituted variables in template: {unsubstituted}"
        )

    return content
```

### MCP Instruction Injection

MCP instructions are appended to template content:

```python
def inject_mcp_instructions(
    template_content: str,
    mcp_instructions: str
) -> str:
    """
    Inject MCP coordination instructions into template.

    Args:
        template_content: Original template content
        mcp_instructions: Generated MCP instructions

    Returns:
        Combined content
    """
    return f"""
{template_content}

---

# MCP COORDINATION PROTOCOL

{mcp_instructions}

---

**IMPORTANT**: Follow the MCP workflow above to ensure your work is tracked and coordinated with other agents.
"""
```

### Tool-Specific Behaviors

Templates can include conditional sections based on `preferred_tool`:

```markdown
## Tool-Specific Instructions

{{#if preferred_tool == "claude"}}
### Claude Code (Hybrid Mode)

You are running in Claude Code with automatic MCP coordination.

**Automatic Features**:
- Job acknowledgment: Automatic
- Progress tracking: Automatic
- Subagent spawning: Available (use when needed)
{{/if}}

{{#if preferred_tool == "codex"}}
### Codex (Legacy CLI Mode)

You are running in Codex CLI with manual MCP coordination.

**Required Actions**:
1. Call `acknowledge_job` FIRST
2. Call `report_progress` every 15 minutes
3. Call `complete_job` when done
{{/if}}

{{#if preferred_tool == "gemini"}}
### Gemini (Legacy CLI Mode)

You are running in Gemini CLI with manual MCP coordination.

**Speed Optimization**:
- Use parallel execution when possible
- Checkpoint frequently (every 10 minutes)
- Leverage Gemini's fast iteration speed
{{/if}}
```

---

## Testing Strategy

Comprehensive testing approach for multi-tool orchestration.

### Unit Tests (Orchestrator Routing)

**File**: `tests/unit/test_orchestrator_routing.py`

```python
"""
Unit tests for ProjectOrchestrator routing logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.models import AgentTemplate


@pytest.mark.asyncio
async def test_route_to_claude_code_agent(orchestrator):
    """
    Test routing to Claude Code when template.preferred_tool = "claude".
    """
    # Mock template with preferred_tool = "claude"
    template = AgentTemplate(
        tenant_key="test_tenant",
        role="implementer",
        preferred_tool="claude",
        content="Test template"
    )

    orchestrator._get_agent_template = AsyncMock(return_value=template)
    orchestrator._spawn_claude_code_agent = AsyncMock(return_value="agent_001")

    # Spawn agent
    agent_id = await orchestrator.spawn_agent(
        project_id="proj_001",
        agent_name="Implementer-001",
        role="implementer",
        mission="Test mission"
    )

    # Verify Claude Code spawning called
    orchestrator._spawn_claude_code_agent.assert_called_once()
    assert agent_id == "agent_001"


@pytest.mark.asyncio
async def test_route_to_codex_agent(orchestrator):
    """
    Test routing to Codex when template.preferred_tool = "codex".
    """
    template = AgentTemplate(
        tenant_key="test_tenant",
        role="tester",
        preferred_tool="codex",
        content="Test template"
    )

    orchestrator._get_agent_template = AsyncMock(return_value=template)
    orchestrator._spawn_generic_agent = AsyncMock(return_value="agent_002")

    agent_id = await orchestrator.spawn_agent(
        project_id="proj_001",
        agent_name="Tester-001",
        role="tester",
        mission="Test mission"
    )

    # Verify legacy agent spawning called with tool="codex"
    orchestrator._spawn_generic_agent.assert_called_once_with(
        "Tester-001",
        "Test mission",
        template,
        "codex",
        "proj_001"
    )
    assert agent_id == "agent_002"
```

### Integration Tests (Multi-Tool Scenarios)

**File**: `tests/integration/test_multi_tool_orchestration.py`

```python
"""
Integration tests for multi-tool orchestration scenarios.
"""

import pytest
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.models import Agent, MCPAgentJob, AgentTemplate


@pytest.mark.asyncio
async def test_mixed_tool_project(db_manager, orchestrator):
    """
    Test project with agents using different tools.

    Scenario:
    - Orchestrator: Claude Code
    - Implementer: Codex
    - Tester: Gemini
    """
    # 1. Create templates for different tools
    templates = [
        AgentTemplate(
            tenant_key="test_tenant",
            role="orchestrator",
            preferred_tool="claude",
            content="Orchestrator template"
        ),
        AgentTemplate(
            tenant_key="test_tenant",
            role="implementer",
            preferred_tool="codex",
            content="Implementer template"
        ),
        AgentTemplate(
            tenant_key="test_tenant",
            role="tester",
            preferred_tool="gemini",
            content="Tester template"
        )
    ]

    async with db_manager.get_session_async() as session:
        for template in templates:
            session.add(template)
        await session.commit()

    # 2. Spawn agents
    orchestrator_id = await orchestrator.spawn_agent(
        project_id="proj_001",
        agent_name="Orchestrator-001",
        role="orchestrator",
        mission="Coordinate project"
    )

    implementer_id = await orchestrator.spawn_agent(
        project_id="proj_001",
        agent_name="Implementer-001",
        role="implementer",
        mission="Implement features"
    )

    tester_id = await orchestrator.spawn_agent(
        project_id="proj_001",
        agent_name="Tester-001",
        role="tester",
        mission="Write tests"
    )

    # 3. Verify agents created with correct modes
    async with db_manager.get_session_async() as session:
        orchestrator_agent = await session.get(Agent, orchestrator_id)
        assert orchestrator_agent.mode == "claude"

        implementer_agent = await session.get(Agent, implementer_id)
        assert implementer_agent.mode == "codex"

        tester_agent = await session.get(Agent, tester_id)
        assert tester_agent.mode == "gemini"

    # 4. Verify jobs created with correct statuses
    async with db_manager.get_session_async() as session:
        orchestrator_job = await session.get(MCPAgentJob, orchestrator_agent.job_id)
        assert orchestrator_job.status == "in_progress"  # Hybrid mode auto-ack

        implementer_job = await session.get(MCPAgentJob, implementer_agent.job_id)
        assert implementer_job.status == "waiting_acknowledgment"  # Legacy CLI

        tester_job = await session.get(MCPAgentJob, tester_agent.job_id)
        assert tester_job.status == "waiting_acknowledgment"  # Legacy CLI
```

### Security Tests (Tenant Isolation)

**File**: `tests/security/test_multi_tool_tenant_isolation.py`

```python
"""
Security tests for multi-tenant isolation in multi-tool orchestration.
"""

import pytest
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.agent_job_manager import AgentJobManager


@pytest.mark.asyncio
async def test_cross_tenant_job_access_forbidden(
    db_manager, agent_job_manager
):
    """
    Test that tenant A cannot access tenant B's jobs.
    """
    # 1. Create job for tenant A
    job_a = await agent_job_manager.create_job(
        tenant_key="tenant_a",
        agent_id="agent_a_001",
        mission="Tenant A mission",
        priority="normal"
    )

    # 2. Attempt to acknowledge job_a from tenant B context
    db_manager.tenant_manager.set_current_tenant("tenant_b")

    result = await agent_job_manager.acknowledge_job(
        job_id=job_a.id,
        agent_id="agent_b_001",
        tenant_key="tenant_b"  # Wrong tenant!
    )

    # 3. Verify access denied
    assert result["success"] is False
    assert "forbidden" in result["error"].lower()

    # 4. Verify job status unchanged
    async with db_manager.get_session_async() as session:
        job = await session.get(MCPAgentJob, job_a.id)
        assert job.status == "waiting_acknowledgment"  # Unchanged


@pytest.mark.asyncio
async def test_cross_tenant_template_isolation(
    db_manager, template_manager
):
    """
    Test that tenant A's templates are not accessible to tenant B.
    """
    # 1. Create tenant A template
    template_a = AgentTemplate(
        tenant_key="tenant_a",
        role="implementer",
        preferred_tool="claude",
        content="Tenant A template"
    )

    async with db_manager.get_session_async() as session:
        session.add(template_a)
        await session.commit()

    # 2. Switch to tenant B context
    db_manager.tenant_manager.set_current_tenant("tenant_b")

    # 3. Attempt to retrieve tenant A's template
    template = await template_manager.get_template(
        role="implementer",
        tenant_key="tenant_b"  # Wrong tenant
    )

    # 4. Verify template not found (returns system default or None)
    assert template is None or template.tenant_key != "tenant_a"
```

### Performance Tests (Concurrent Spawning)

**File**: `tests/performance/test_concurrent_agent_spawning.py`

```python
"""
Performance tests for concurrent agent spawning across tools.
"""

import pytest
import asyncio
import time
from src.giljo_mcp.orchestrator import ProjectOrchestrator


@pytest.mark.asyncio
async def test_concurrent_spawning_performance(
    db_manager, orchestrator
):
    """
    Test concurrent spawning of 100 agents across 3 tools.

    Target: < 10 seconds for 100 agents (10 agents/second)
    """
    # 1. Create templates for 3 tools
    templates = [
        AgentTemplate(
            tenant_key="test_tenant",
            role=f"role_{i % 3}",
            preferred_tool=["claude", "codex", "gemini"][i % 3],
            content=f"Template {i}"
        )
        for i in range(3)
    ]

    async with db_manager.get_session_async() as session:
        for template in templates:
            session.add(template)
        await session.commit()

    # 2. Spawn 100 agents concurrently
    start_time = time.time()

    tasks = [
        orchestrator.spawn_agent(
            project_id="perf_test_proj",
            agent_name=f"Agent-{i:03d}",
            role=f"role_{i % 3}",
            mission=f"Mission {i}"
        )
        for i in range(100)
    ]

    agent_ids = await asyncio.gather(*tasks)

    elapsed_time = time.time() - start_time

    # 3. Verify performance target
    assert elapsed_time < 10.0, f"Spawning too slow: {elapsed_time:.2f}s"

    # 4. Verify all agents created
    assert len(agent_ids) == 100
    assert len(set(agent_ids)) == 100  # All unique

    # 5. Verify distribution across tools
    async with db_manager.get_session_async() as session:
        agents = await session.execute(
            select(Agent).filter(Agent.project_id == "perf_test_proj")
        )
        agents = agents.scalars().all()

        modes = [agent.mode for agent in agents]
        assert modes.count("claude") > 0
        assert modes.count("codex") > 0
        assert modes.count("gemini") > 0
```

---

## Database Schema

Complete schema for multi-tool orchestration.

### Agent Model (Enhanced)

```sql
CREATE TABLE agents (
    -- Primary key
    id VARCHAR(36) PRIMARY KEY,

    -- Multi-tenant isolation
    tenant_key VARCHAR(36) NOT NULL,

    -- Project relationship
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),

    -- Agent identity
    name VARCHAR(200) NOT NULL,
    role VARCHAR(200) NOT NULL,  -- orchestrator, implementer, etc.

    -- Agent status
    status VARCHAR(50) DEFAULT 'active',  -- active, idle, working, decommissioned
    mission TEXT NULL,
    context_used INTEGER DEFAULT 0,

    -- Timestamps
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decommissioned_at TIMESTAMP WITH TIME ZONE NULL,

    -- Multi-tool orchestration (Handover 0045)
    job_id VARCHAR(36) NULL,              -- Links to mcp_agent_jobs.id
    mode VARCHAR(20) DEFAULT 'claude',    -- claude | codex | gemini | cursor | windsurf

    -- Metadata (JSONB for flexibility)
    meta_data JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT uq_agent_project_name UNIQUE (project_id, name)
);

-- Indexes for performance
CREATE INDEX idx_agent_tenant ON agents(tenant_key);
CREATE INDEX idx_agent_project ON agents(project_id);
CREATE INDEX idx_agent_status ON agents(status);
CREATE INDEX idx_agent_job_id ON agents(job_id);  -- NEW (Handover 0045)
CREATE INDEX idx_agent_mode ON agents(mode);      -- NEW (Handover 0045)
```

### MCPAgentJob Model

```sql
CREATE TABLE mcp_agent_jobs (
    -- Primary key
    id VARCHAR(36) PRIMARY KEY,

    -- Multi-tenant isolation
    tenant_key VARCHAR(36) NOT NULL,

    -- Agent relationship
    agent_id VARCHAR(36) NULL,  -- Links to agents.id (NULL if not yet assigned)

    -- Job details
    mission TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'waiting_acknowledgment',
    priority VARCHAR(20) DEFAULT 'normal',  -- low, normal, high
    progress INTEGER DEFAULT 0,             -- 0-100

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,

    -- Results
    summary TEXT NULL,  -- Completion summary
    error_details JSONB NULL,  -- Error info if failed

    -- Job hierarchy (parent-child relationships)
    parent_job_id VARCHAR(36) NULL REFERENCES mcp_agent_jobs(id),

    -- Metadata
    meta_data JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX idx_job_tenant ON mcp_agent_jobs(tenant_key);
CREATE INDEX idx_job_agent ON mcp_agent_jobs(agent_id);
CREATE INDEX idx_job_status ON mcp_agent_jobs(status);
CREATE INDEX idx_job_priority ON mcp_agent_jobs(priority);
CREATE INDEX idx_job_parent ON mcp_agent_jobs(parent_job_id);
```

### AgentTemplate Model (Enhanced)

```sql
CREATE TABLE agent_templates (
    -- Primary key
    id VARCHAR(36) PRIMARY KEY,

    -- Multi-tenant isolation
    tenant_key VARCHAR(36) NOT NULL,  -- "system" for defaults

    -- Product-specific (optional)
    product_id VARCHAR(36) NULL REFERENCES products(id),

    -- Template identity
    name VARCHAR(255) NOT NULL,
    role VARCHAR(200) NOT NULL,
    category VARCHAR(100) DEFAULT 'role',

    -- Multi-tool orchestration (Handover 0045)
    preferred_tool VARCHAR(20) DEFAULT 'claude',  -- claude | codex | gemini | cursor | windsurf

    -- Template content
    content TEXT NOT NULL,

    -- Metadata
    description TEXT NULL,
    behavioral_rules JSONB DEFAULT '[]'::jsonb,
    success_criteria JSONB DEFAULT '[]'::jsonb,
    variables JSONB DEFAULT '{}'::jsonb,

    -- Versioning
    version VARCHAR(50) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_template_tenant_role_product UNIQUE (tenant_key, role, product_id)
);

-- Indexes
CREATE INDEX idx_template_tenant ON agent_templates(tenant_key);
CREATE INDEX idx_template_role ON agent_templates(role);
CREATE INDEX idx_template_product ON agent_templates(product_id);
CREATE INDEX idx_template_tool ON agent_templates(preferred_tool);  -- NEW
```

### Migration Procedures

**Migration Script** (Add multi-tool fields to existing database):

```sql
-- Migration: Add multi-tool orchestration fields to agents table
-- Date: 2025-10-25
-- Handover: 0045

BEGIN;

-- 1. Add job_id column
ALTER TABLE agents
ADD COLUMN job_id VARCHAR(36) NULL;

-- 2. Add mode column
ALTER TABLE agents
ADD COLUMN mode VARCHAR(20) DEFAULT 'claude';

-- 3. Create index on job_id
CREATE INDEX idx_agent_job_id ON agents(job_id);

-- 4. Create index on mode
CREATE INDEX idx_agent_mode ON agents(mode);

-- 5. Add preferred_tool to agent_templates if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_templates'
        AND column_name = 'preferred_tool'
    ) THEN
        ALTER TABLE agent_templates
        ADD COLUMN preferred_tool VARCHAR(20) DEFAULT 'claude';

        CREATE INDEX idx_template_tool ON agent_templates(preferred_tool);
    END IF;
END $$;

-- 6. Update existing agents to mode='claude' (default)
UPDATE agents
SET mode = 'claude'
WHERE mode IS NULL;

COMMIT;
```

**Rollback Script** (if needed):

```sql
-- Rollback: Remove multi-tool orchestration fields
-- Date: 2025-10-25

BEGIN;

-- 1. Drop indexes
DROP INDEX IF EXISTS idx_agent_job_id;
DROP INDEX IF EXISTS idx_agent_mode;
DROP INDEX IF EXISTS idx_template_tool;

-- 2. Drop columns
ALTER TABLE agents DROP COLUMN IF EXISTS job_id;
ALTER TABLE agents DROP COLUMN IF EXISTS mode;
ALTER TABLE agent_templates DROP COLUMN IF EXISTS preferred_tool;

COMMIT;
```

---

## API Endpoints

Complete API reference for multi-tool orchestration.

### Agent Endpoints

**POST /api/v1/agents**

Create agent (automatically routes to correct tool).

Request:
```json
{
  "project_id": "proj_001",
  "agent_name": "Implementer-001",
  "role": "implementer",
  "mission": "Implement user authentication"
}
```

Response:
```json
{
  "id": "agent_abc123",
  "name": "Implementer-001",
  "project_id": "proj_001",
  "role": "implementer",
  "status": "active",
  "mode": "codex",
  "job_id": "job_xyz789",
  "mission": "Implement user authentication",
  "created_at": "2025-10-25T10:30:00Z",
  "health": {
    "status": "healthy",
    "context_used": 0
  }
}
```

**GET /api/v1/agents/{id}/cli-prompt**

Get CLI prompt for legacy mode agents.

Response:
```json
{
  "agent_id": "agent_abc123",
  "mode": "codex",
  "tool": "codex",
  "cli_prompt": "# OpenAI Codex Agent...\n\n[Full prompt content]",
  "requires_manual_start": true
}
```

**GET /api/v1/agents/{id}**

Get agent details.

Response:
```json
{
  "id": "agent_abc123",
  "name": "Implementer-001",
  "project_id": "proj_001",
  "role": "implementer",
  "status": "active",
  "mode": "codex",
  "job_id": "job_xyz789",
  "mission": "Implement user authentication",
  "context_used": 1500,
  "last_active": "2025-10-25T11:45:00Z",
  "created_at": "2025-10-25T10:30:00Z",
  "meta_data": {
    "cli_prompt": "[prompt content]",
    "tool": "codex",
    "requires_manual_start": true
  }
}
```

### Job Endpoints

**GET /api/v1/jobs**

List all jobs with filtering.

Query Parameters:
- `status`: Filter by status (waiting_acknowledgment, in_progress, completed, failed)
- `tool`: Filter by tool (claude, codex, gemini)
- `agent_id`: Filter by agent

Response:
```json
{
  "jobs": [
    {
      "id": "job_xyz789",
      "agent_id": "agent_abc123",
      "agent_name": "Implementer-001",
      "tool": "codex",
      "mode": "legacy_cli",
      "status": "in_progress",
      "progress": 65,
      "mission": "Implement user authentication",
      "created_at": "2025-10-25T10:30:00Z",
      "acknowledged_at": "2025-10-25T10:32:00Z",
      "last_update": "2025-10-25T11:45:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**GET /api/v1/jobs/{job_id}**

Get job details.

Response:
```json
{
  "id": "job_xyz789",
  "tenant_key": "tenant_abc",
  "agent_id": "agent_abc123",
  "agent_name": "Implementer-001",
  "tool": "codex",
  "mode": "legacy_cli",
  "mission": "Implement user authentication",
  "status": "in_progress",
  "priority": "normal",
  "progress": 65,
  "created_at": "2025-10-25T10:30:00Z",
  "acknowledged_at": "2025-10-25T10:32:00Z",
  "completed_at": null,
  "summary": null,
  "error_details": null,
  "parent_job_id": null,
  "meta_data": {}
}
```

**GET /api/v1/jobs/{job_id}/messages**

Get messages for job.

Response:
```json
{
  "messages": [
    {
      "message_id": "msg_001",
      "from_agent_id": "agent_abc123",
      "from_agent_name": "Implementer-001",
      "to_agent_id": "agent_xyz789",
      "to_agent_name": "Orchestrator-001",
      "message": "Question: Should token expiration be configurable?",
      "priority": "normal",
      "acknowledged": true,
      "created_at": "2025-10-25T11:20:00Z",
      "acknowledged_at": "2025-10-25T11:22:00Z"
    }
  ],
  "total": 1
}
```

**GET /api/v1/jobs/statistics**

Get job statistics.

Response:
```json
{
  "total_jobs": 42,
  "by_status": {
    "waiting_acknowledgment": 3,
    "in_progress": 8,
    "completed": 30,
    "failed": 1
  },
  "by_tool": {
    "claude": {
      "total": 15,
      "avg_completion_time_minutes": 45,
      "success_rate": 0.93
    },
    "codex": {
      "total": 18,
      "avg_completion_time_minutes": 30,
      "success_rate": 0.89
    },
    "gemini": {
      "total": 9,
      "avg_completion_time_minutes": 25,
      "success_rate": 0.88
    }
  },
  "avg_completion_time_minutes": 35,
  "overall_success_rate": 0.90
}
```

### Template Endpoints

**PATCH /api/v1/templates/{id}**

Update template (including preferred_tool).

Request:
```json
{
  "preferred_tool": "codex",
  "content": "Updated template content",
  "behavioral_rules": ["Rule 1", "Rule 2"],
  "success_criteria": ["Criterion 1", "Criterion 2"]
}
```

Response:
```json
{
  "id": "template_001",
  "tenant_key": "tenant_abc",
  "name": "Implementer",
  "role": "implementer",
  "preferred_tool": "codex",
  "content": "Updated template content",
  "version": "1.1.0",
  "updated_at": "2025-10-25T12:00:00Z"
}
```

**POST /api/v1/templates/export/claude-code**

Export templates for Claude Code.

Request:
```json
{
  "tenant_key": "tenant_abc",
  "include_product_specific": true
}
```

Response:
```json
{
  "export_id": "export_001",
  "download_url": "/api/v1/exports/export_001/download",
  "templates_count": 6,
  "created_at": "2025-10-25T12:00:00Z"
}
```

### MCP Tool Endpoints

**POST /mcp/get_pending_jobs**

Get jobs waiting for agent.

Request:
```json
{
  "agent_id": "agent_abc123",
  "tenant_key": "tenant_abc"
}
```

Response:
```json
{
  "jobs": [
    {
      "job_id": "job_xyz789",
      "mission": "Implement user authentication",
      "priority": "high",
      "created_at": "2025-10-25T10:30:00Z"
    }
  ]
}
```

**POST /mcp/acknowledge_job**

Acknowledge job.

Request:
```json
{
  "job_id": "job_xyz789",
  "agent_id": "agent_abc123",
  "tenant_key": "tenant_abc"
}
```

Response:
```json
{
  "success": true,
  "message": "Job acknowledged, status updated to in_progress",
  "job_id": "job_xyz789",
  "status": "in_progress"
}
```

**POST /mcp/report_progress**

Report progress.

Request:
```json
{
  "job_id": "job_xyz789",
  "progress_data": {
    "percentage": 50,
    "message": "JWT token generation implemented",
    "details": "Created signing and verification logic"
  }
}
```

Response:
```json
{
  "success": true,
  "message": "Progress reported successfully",
  "job_id": "job_xyz789",
  "progress": 50
}
```

**POST /mcp/get_next_instruction**

Get latest instruction.

Request:
```json
{
  "job_id": "job_xyz789",
  "tenant_key": "tenant_abc"
}
```

Response:
```json
{
  "instruction": "Updated requirement: Token expiration configurable via env var",
  "from_agent": "Orchestrator-001",
  "timestamp": "2025-10-25T11:25:00Z"
}
```

**POST /mcp/complete_job**

Complete job.

Request:
```json
{
  "job_id": "job_xyz789",
  "summary": "User authentication implemented successfully. All tests passing.",
  "tenant_key": "tenant_abc"
}
```

Response:
```json
{
  "success": true,
  "message": "Job marked as completed",
  "job_id": "job_xyz789",
  "status": "completed",
  "completed_at": "2025-10-25T12:00:00Z"
}
```

**POST /mcp/report_error**

Report critical error.

Request:
```json
{
  "job_id": "job_xyz789",
  "error_details": {
    "error_type": "dependency_missing",
    "message": "jsonwebtoken package not found",
    "recovery_suggestion": "Add jsonwebtoken to package.json"
  },
  "tenant_key": "tenant_abc"
}
```

Response:
```json
{
  "success": true,
  "message": "Error reported, job marked as failed",
  "job_id": "job_xyz789",
  "status": "failed"
}
```

**POST /mcp/send_message**

Send message to another agent.

Request:
```json
{
  "from_agent_id": "agent_abc123",
  "to_agent_id": "agent_xyz789",
  "message": "Question: Should token expiration be configurable?",
  "priority": "normal",
  "tenant_key": "tenant_abc"
}
```

Response:
```json
{
  "success": true,
  "message_id": "msg_001",
  "message": "Message sent successfully"
}
```

### WebSocket Events

**agent:status_changed**

Broadcast when agent status changes.

Event:
```json
{
  "event": "agent:status_changed",
  "data": {
    "agent_id": "agent_abc123",
    "agent_name": "Implementer-001",
    "project_id": "proj_001",
    "status": "active",
    "mode": "codex",
    "timestamp": "2025-10-25T10:30:00Z"
  }
}
```

**job:status_changed**

Broadcast when job status changes.

Event:
```json
{
  "event": "job:status_changed",
  "data": {
    "job_id": "job_xyz789",
    "agent_id": "agent_abc123",
    "status": "in_progress",
    "previous_status": "waiting_acknowledgment",
    "timestamp": "2025-10-25T10:32:00Z"
  }
}
```

**job:completed**

Broadcast when job completes.

Event:
```json
{
  "event": "job:completed",
  "data": {
    "job_id": "job_xyz789",
    "agent_id": "agent_abc123",
    "summary": "User authentication implemented successfully",
    "completed_at": "2025-10-25T12:00:00Z"
  }
}
```

**job:failed**

Broadcast when job fails.

Event:
```json
{
  "event": "job:failed",
  "data": {
    "job_id": "job_xyz789",
    "agent_id": "agent_abc123",
    "error_details": {
      "error_type": "dependency_missing",
      "message": "jsonwebtoken package not found"
    },
    "failed_at": "2025-10-25T11:50:00Z"
  }
}
```

---

## Extension Points

Where to hook in custom functionality.

### Custom Tool Routing

Override routing logic for custom tools:

```python
# src/giljo_mcp/orchestrator_extensions.py

from src.giljo_mcp.orchestrator import ProjectOrchestrator


class CustomOrchestrator(ProjectOrchestrator):
    """
    Extended orchestrator with custom tool routing.
    """

    async def spawn_agent(
        self,
        project_id: str,
        agent_name: str,
        role: str,
        mission: str
    ) -> str:
        """
        Custom routing logic based on project metadata.
        """
        # Get template
        template = await self._get_agent_template(role, project_id)

        # Custom routing based on project
        project = await self.get_project(project_id)

        if project.meta_data.get("force_tool"):
            # Override template tool with project preference
            tool = project.meta_data["force_tool"]
        else:
            # Use template tool
            tool = template.preferred_tool

        # Route to appropriate spawning method
        if tool == "claude":
            return await self._spawn_claude_code_agent(
                agent_name, mission, template, project_id
            )
        elif tool in ["codex", "gemini"]:
            return await self._spawn_generic_agent(
                agent_name, mission, template, tool, project_id
            )
        elif tool == "custom_tool":
            # Custom tool integration
            return await self._spawn_custom_tool_agent(
                agent_name, mission, template, project_id
            )
        else:
            raise ValueError(f"Unsupported tool: {tool}")
```

### Custom MCP Tools

Add custom coordination tools:

```python
# src/giljo_mcp/tools/custom_coordination.py

def register_custom_coordination_tools(mcp_server):
    """
    Register custom MCP coordination tools.
    """

    @mcp_server.tool()
    async def custom_checkpoint(
        job_id: str,
        checkpoint_data: Dict[str, Any],
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Custom checkpoint tool with additional metadata.
        """
        try:
            # Standard progress update
            await mcp_server.agent_job_manager.update_job_progress(
                job_id=job_id,
                progress_data=checkpoint_data
            )

            # Custom: Save checkpoint to external storage
            await mcp_server.external_storage.save_checkpoint(
                job_id=job_id,
                data=checkpoint_data
            )

            return {"success": True}

        except Exception as e:
            logger.error(f"Custom checkpoint failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp_server.tool()
    async def request_human_feedback(
        job_id: str,
        question: str,
        tenant_key: str
    ) -> Dict[str, Any]:
        """
        Request human feedback during job execution.
        """
        try:
            # Create feedback request
            feedback_id = await mcp_server.feedback_manager.create_request(
                job_id=job_id,
                question=question,
                tenant_key=tenant_key
            )

            # Notify via email/Slack
            await mcp_server.notification_service.send_feedback_request(
                feedback_id=feedback_id,
                question=question
            )

            return {
                "success": True,
                "feedback_id": feedback_id,
                "message": "Feedback request created, waiting for human response"
            }

        except Exception as e:
            logger.error(f"Feedback request failed: {e}")
            return {"success": False, "error": str(e)}
```

### Custom Templates

Programmatically generate templates:

```python
# src/giljo_mcp/custom_templates.py

from src.giljo_mcp.models import AgentTemplate


class CustomTemplateGenerator:
    """
    Generate custom templates based on project requirements.
    """

    def generate_template(
        self,
        role: str,
        project_metadata: Dict[str, Any]
    ) -> AgentTemplate:
        """
        Generate template tailored to project.
        """
        # Determine preferred tool based on project tech stack
        tech_stack = project_metadata.get("tech_stack", [])

        if "react" in tech_stack or "angular" in tech_stack:
            preferred_tool = "gemini"  # Frontend optimization
        elif "python" in tech_stack and "ml" in project_metadata.get("keywords", []):
            preferred_tool = "codex"  # ML/data science
        else:
            preferred_tool = "claude"  # Default: best reasoning

        # Generate content based on role and tech stack
        content = self._generate_content(role, tech_stack)

        # Create template
        return AgentTemplate(
            tenant_key=project_metadata["tenant_key"],
            role=role,
            preferred_tool=preferred_tool,
            content=content,
            meta_data={
                "auto_generated": True,
                "tech_stack": tech_stack
            }
        )

    def _generate_content(
        self,
        role: str,
        tech_stack: List[str]
    ) -> str:
        """
        Generate template content.
        """
        base_content = f"# {role.capitalize()} Agent\n\n"

        # Add tech-stack-specific rules
        if "typescript" in tech_stack:
            base_content += """
## TypeScript-Specific Rules
1. Always use TypeScript strict mode
2. Define interfaces for all data structures
3. Use functional programming patterns
"""

        if "react" in tech_stack:
            base_content += """
## React-Specific Rules
1. Use React Hooks (avoid class components)
2. Follow React 18 best practices
3. Use TypeScript for prop typing
"""

        return base_content
```

### Custom UI Components

Add custom dashboard widgets:

```vue
<!-- frontend/src/components/CustomAgentWidget.vue -->

<template>
  <v-card>
    <v-card-title>Custom Agent Metrics</v-card-title>

    <v-card-text>
      <!-- Custom metrics visualization -->
      <v-row>
        <v-col cols="4">
          <div class="metric">
            <div class="metric-label">Cost Savings</div>
            <div class="metric-value">${{ costSavings }}</div>
            <div class="metric-change">vs all-Claude baseline</div>
          </div>
        </v-col>

        <v-col cols="4">
          <div class="metric">
            <div class="metric-label">Avg Speed</div>
            <div class="metric-value">{{ avgSpeed }} min</div>
            <div class="metric-change">per job completion</div>
          </div>
        </v-col>

        <v-col cols="4">
          <div class="metric">
            <div class="metric-label">Tool Mix</div>
            <div class="metric-value">{{ toolMixRatio }}</div>
            <div class="metric-change">Claude:Codex:Gemini</div>
          </div>
        </v-col>
      </v-row>

      <!-- Tool-specific breakdown -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-chip-group column>
            <v-chip
              v-for="tool in toolStats"
              :key="tool.name"
              :color="tool.color"
              label
            >
              {{ tool.name }}: {{ tool.count }} jobs ({{ tool.percentage }}%)
            </v-chip>
          </v-chip-group>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '@/services/api'

// Reactive state
const jobs = ref([])
const costSavings = ref(0)
const avgSpeed = ref(0)

// Computed properties
const toolStats = computed(() => {
  // Calculate tool statistics
  const stats = {}

  jobs.value.forEach(job => {
    if (!stats[job.tool]) {
      stats[job.tool] = { count: 0, color: getToolColor(job.tool) }
    }
    stats[job.tool].count++
  })

  const total = jobs.value.length

  return Object.keys(stats).map(tool => ({
    name: tool,
    count: stats[tool].count,
    percentage: ((stats[tool].count / total) * 100).toFixed(1),
    color: stats[tool].color
  }))
})

const toolMixRatio = computed(() => {
  const claude = toolStats.value.find(t => t.name === 'claude')?.count || 0
  const codex = toolStats.value.find(t => t.name === 'codex')?.count || 0
  const gemini = toolStats.value.find(t => t.name === 'gemini')?.count || 0

  return `${claude}:${codex}:${gemini}`
})

// Methods
const getToolColor = (tool) => {
  const colors = {
    claude: 'purple',
    codex: 'green',
    gemini: 'blue'
  }
  return colors[tool] || 'grey'
}

const fetchJobStats = async () => {
  try {
    const response = await api.get('/api/v1/jobs/statistics')
    jobs.value = response.data.jobs
    costSavings.value = calculateCostSavings(response.data)
    avgSpeed.value = response.data.avg_completion_time_minutes
  } catch (error) {
    console.error('Failed to fetch job stats:', error)
  }
}

const calculateCostSavings = (data) => {
  // Calculate savings vs all-Claude baseline
  // Example: Claude = $2/job, Codex = $1/job, Gemini = $0/job
  const baseline = data.total_jobs * 2  // All Claude
  const actual = (
    (data.by_tool.claude?.total || 0) * 2 +
    (data.by_tool.codex?.total || 0) * 1 +
    (data.by_tool.gemini?.total || 0) * 0
  )

  return (baseline - actual).toFixed(2)
}

// Lifecycle
onMounted(() => {
  fetchJobStats()
})
</script>

<style scoped>
.metric {
  text-align: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

.metric-label {
  font-size: 12px;
  text-transform: uppercase;
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  color: rgba(0, 0, 0, 0.87);
}

.metric-change {
  font-size: 11px;
  color: rgba(0, 0, 0, 0.6);
  margin-top: 4px;
}
</style>
```

---

## Performance Optimization

Strategies for optimizing multi-tool orchestration.

### Caching Strategy

Three-layer caching for templates (similar to Handover 0041):

```python
# src/giljo_mcp/template_cache_multi_tool.py

from typing import Optional, Dict, Any
import redis
import json
import logging

logger = logging.getLogger(__name__)


class MultiToolTemplateCache:
    """
    Three-layer cache for agent templates with tool-specific optimization.

    Layers:
    1. Memory (LRU) - < 1ms - Hot templates
    2. Redis - < 2ms - Warm templates
    3. Database - < 10ms - Cold templates
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        db_manager,
        memory_cache_size: int = 100
    ):
        self.redis_client = redis_client
        self.db_manager = db_manager
        self.memory_cache = {}  # Simple dict cache (production: use LRU)
        self.memory_cache_size = memory_cache_size

    async def get_template(
        self,
        role: str,
        tenant_key: str,
        product_id: Optional[str] = None
    ) -> Optional[AgentTemplate]:
        """
        Get template with three-layer caching.
        """
        cache_key = self._generate_cache_key(role, tenant_key, product_id)

        # Layer 1: Memory cache
        if cache_key in self.memory_cache:
            logger.debug(f"Template cache HIT (memory): {cache_key}")
            return self.memory_cache[cache_key]

        # Layer 2: Redis cache
        redis_value = self.redis_client.get(cache_key)
        if redis_value:
            logger.debug(f"Template cache HIT (redis): {cache_key}")
            template_data = json.loads(redis_value)
            template = self._deserialize_template(template_data)

            # Promote to memory cache
            self._set_memory_cache(cache_key, template)

            return template

        # Layer 3: Database
        logger.debug(f"Template cache MISS: {cache_key}")
        template = await self._fetch_from_database(role, tenant_key, product_id)

        if template:
            # Cache in Redis (TTL: 1 hour)
            self.redis_client.setex(
                cache_key,
                3600,
                json.dumps(self._serialize_template(template))
            )

            # Cache in memory
            self._set_memory_cache(cache_key, template)

        return template

    def invalidate(
        self,
        role: str,
        tenant_key: str,
        product_id: Optional[str] = None
    ):
        """
        Invalidate cache for template.
        """
        cache_key = self._generate_cache_key(role, tenant_key, product_id)

        # Invalidate memory cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]

        # Invalidate Redis cache
        self.redis_client.delete(cache_key)

        logger.info(f"Invalidated cache for: {cache_key}")

    def _generate_cache_key(
        self,
        role: str,
        tenant_key: str,
        product_id: Optional[str]
    ) -> str:
        """
        Generate cache key.
        """
        if product_id:
            return f"template:{tenant_key}:{role}:{product_id}"
        else:
            return f"template:{tenant_key}:{role}"

    def _set_memory_cache(
        self,
        key: str,
        value: AgentTemplate
    ):
        """
        Set memory cache with LRU eviction.
        """
        # Simple implementation (production: use collections.OrderedDict)
        if len(self.memory_cache) >= self.memory_cache_size:
            # Evict oldest
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]

        self.memory_cache[key] = value

    async def _fetch_from_database(
        self,
        role: str,
        tenant_key: str,
        product_id: Optional[str]
    ) -> Optional[AgentTemplate]:
        """
        Fetch template from database.
        """
        async with self.db_manager.get_session_async() as session:
            query = select(AgentTemplate).filter(
                AgentTemplate.role == role,
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            )

            if product_id:
                query = query.filter(AgentTemplate.product_id == product_id)

            result = await session.execute(query)
            return result.scalar_one_or_none()

    def _serialize_template(self, template: AgentTemplate) -> Dict[str, Any]:
        """
        Serialize template for Redis storage.
        """
        return {
            "id": template.id,
            "tenant_key": template.tenant_key,
            "role": template.role,
            "preferred_tool": template.preferred_tool,
            "content": template.content,
            # ... other fields
        }

    def _deserialize_template(self, data: Dict[str, Any]) -> AgentTemplate:
        """
        Deserialize template from Redis.
        """
        return AgentTemplate(**data)
```

### Database Query Optimization

Optimize queries for multi-tool scenarios:

```python
# Inefficient: N+1 queries
agents = await session.execute(select(Agent).filter(Agent.project_id == project_id))
agents = agents.scalars().all()

for agent in agents:
    job = await session.get(MCPAgentJob, agent.job_id)  # N+1 queries!
    print(agent.name, job.status)


# Efficient: Single query with join
agents = await session.execute(
    select(Agent)
    .options(selectinload(Agent.jobs))  # Eager load jobs
    .filter(Agent.project_id == project_id)
)
agents = agents.scalars().all()

for agent in agents:
    print(agent.name, agent.jobs[0].status if agent.jobs else "N/A")


# Even more efficient: Direct join
results = await session.execute(
    select(Agent, MCPAgentJob)
    .join(MCPAgentJob, Agent.job_id == MCPAgentJob.id)
    .filter(Agent.project_id == project_id)
)

for agent, job in results:
    print(agent.name, job.status)
```

### Concurrent Agent Spawning

Optimize parallel agent spawning:

```python
# src/giljo_mcp/orchestrator_optimized.py

import asyncio
from typing import List, Dict, Any


class OptimizedOrchestrator(ProjectOrchestrator):
    """
    Orchestrator with optimized concurrent spawning.
    """

    async def spawn_agents_batch(
        self,
        project_id: str,
        agent_specs: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Spawn multiple agents concurrently.

        Args:
            project_id: Project ID
            agent_specs: List of agent specifications
                [{
                    "agent_name": "Implementer-001",
                    "role": "implementer",
                    "mission": "..."
                }, ...]

        Returns:
            List of agent IDs
        """
        # 1. Fetch all templates concurrently (avoid N+1 queries)
        roles = [spec["role"] for spec in agent_specs]
        templates = await self._fetch_templates_batch(roles, project_id)

        # 2. Spawn agents in parallel
        spawn_tasks = [
            self._spawn_agent_with_template(
                project_id=project_id,
                agent_name=spec["agent_name"],
                role=spec["role"],
                mission=spec["mission"],
                template=templates[spec["role"]]
            )
            for spec in agent_specs
        ]

        agent_ids = await asyncio.gather(*spawn_tasks)

        # 3. Broadcast batch update (single WebSocket message)
        await self._broadcast_batch_spawn(project_id, agent_ids)

        return agent_ids

    async def _fetch_templates_batch(
        self,
        roles: List[str],
        project_id: str
    ) -> Dict[str, AgentTemplate]:
        """
        Fetch multiple templates in single query.
        """
        async with self.db_manager.get_session_async() as session:
            query = select(AgentTemplate).filter(
                AgentTemplate.role.in_(roles),
                AgentTemplate.tenant_key == self.tenant_key
            )

            results = await session.execute(query)
            templates = results.scalars().all()

            # Map by role
            return {template.role: template for template in templates}

    async def _spawn_agent_with_template(
        self,
        project_id: str,
        agent_name: str,
        role: str,
        mission: str,
        template: AgentTemplate
    ) -> str:
        """
        Spawn agent with pre-fetched template.
        """
        # Route based on template.preferred_tool
        if template.preferred_tool == "claude":
            return await self._spawn_claude_code_agent(
                agent_name, mission, template, project_id
            )
        elif template.preferred_tool in ["codex", "gemini"]:
            return await self._spawn_generic_agent(
                agent_name, mission, template, template.preferred_tool, project_id
            )
        else:
            raise ValueError(f"Unsupported tool: {template.preferred_tool}")

    async def _broadcast_batch_spawn(
        self,
        project_id: str,
        agent_ids: List[str]
    ):
        """
        Broadcast batch spawn event (single WebSocket message).
        """
        await self.websocket_manager.broadcast_event(
            event="agents:batch_spawned",
            data={
                "project_id": project_id,
                "agent_ids": agent_ids,
                "count": len(agent_ids),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            tenant_key=self.tenant_key
        )
```

### WebSocket Optimization

Optimize WebSocket broadcasting for high-frequency updates:

```python
# src/giljo_mcp/websocket_optimized.py

import asyncio
from collections import defaultdict
from typing import Dict, List, Any


class OptimizedWebSocketManager:
    """
    WebSocket manager with batching and throttling.
    """

    def __init__(self):
        self.connections = defaultdict(list)  # tenant_key -> [connections]
        self.pending_events = defaultdict(list)  # tenant_key -> [events]
        self.batch_interval = 0.5  # Batch events every 500ms
        self._batch_task = None

    async def start_batching(self):
        """
        Start background task for batching events.
        """
        self._batch_task = asyncio.create_task(self._batch_loop())

    async def stop_batching(self):
        """
        Stop batching task.
        """
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass

    async def _batch_loop(self):
        """
        Background loop that batches and sends events.
        """
        while True:
            await asyncio.sleep(self.batch_interval)

            # Send batched events for each tenant
            for tenant_key, events in self.pending_events.items():
                if events:
                    await self._send_batch(tenant_key, events)
                    events.clear()

    async def queue_event(
        self,
        event: str,
        data: Dict[str, Any],
        tenant_key: str
    ):
        """
        Queue event for batching.
        """
        self.pending_events[tenant_key].append({
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def _send_batch(
        self,
        tenant_key: str,
        events: List[Dict[str, Any]]
    ):
        """
        Send batched events to all connections for tenant.
        """
        connections = self.connections.get(tenant_key, [])

        if not connections:
            return

        # Combine events into single message
        batch_message = {
            "type": "batch",
            "events": events,
            "count": len(events)
        }

        # Send to all connections
        send_tasks = [
            connection.send_json(batch_message)
            for connection in connections
        ]

        await asyncio.gather(*send_tasks, return_exceptions=True)
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Next**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
