# API and Backend Specifications

**Document ID**: jobs_refactor_ui/04
**Created**: 2025-11-21

---

## Table of Contents

1. [New API Endpoints](#new-api-endpoints)
2. [Database Schema Changes](#database-schema-changes)
3. [WebSocket Events](#websocket-events)
4. [Service Layer Updates](#service-layer-updates)
5. [MCP Tool Integration](#mcp-tool-integration)

---

## New API Endpoints

### 1. POST /api/projects/{project_id}/stage/prompt

**Purpose**: Get the staging prompt for clipboard copy

**Request:**
```http
POST /api/projects/a7053649-7458-4e86-8905-1fef8100cebb/stage/prompt
Authorization: Bearer {token}
Content-Type: application/json
```

**Response:**
```json
{
  "prompt": "You are the Orchestrator for project 'Project Startup and initiation'...\n\nYour task is to:\n1. Analyze the project description\n2. Create a comprehensive mission\n3. Determine required agents\n4. Assign missions to each agent\n\nProject Description:\n{project_description}\n\nPlease provide your analysis and agent assignments.",
  "project_id": "a7053649-7458-4e86-8905-1fef8100cebb"
}
```

**Implementation:**
```python
# api/endpoints/projects.py

@router.post("/{project_id}/stage/prompt")
async def get_staging_prompt(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Generate staging prompt for orchestrator"""
    project = await ProjectService.get_project(session, project_id, current_user.tenant_key)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    prompt = await PromptGeneratorService.generate_staging_prompt(project)

    return {"prompt": prompt, "project_id": str(project_id)}
```

---

### 2. POST /api/projects/{project_id}/stage

**Purpose**: Initialize staging process (orchestrator will connect and fill mission)

**Request:**
```http
POST /api/projects/a7053649-7458-4e86-8905-1fef8100cebb/stage
Authorization: Bearer {token}
Content-Type: application/json
```

**Response:**
```json
{
  "status": "staging_initiated",
  "project_id": "a7053649-7458-4e86-8905-1fef8100cebb",
  "staging_status": "Working"
}
```

**Implementation:**
```python
@router.post("/{project_id}/stage")
async def stage_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """Initialize project staging"""
    project = await ProjectService.get_project(session, project_id, current_user.tenant_key)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update project status
    project.staging_status = "Working"
    await session.commit()

    # Emit WebSocket event
    await websocket_manager.emit(
        event="project:stage_started",
        data={"project_id": str(project_id)},
        room=f"project:{project_id}"
    )

    return {
        "status": "staging_initiated",
        "project_id": str(project_id),
        "staging_status": "Working"
    }
```

---

### 3. POST /api/projects/{project_id}/launch-jobs

**Purpose**: Launch all agent jobs and initialize message queue

**Request:**
```http
POST /api/projects/a7053649-7458-4e86-8905-1fef8100cebb/launch-jobs
Authorization: Bearer {token}
Content-Type: application/json
```

**Response:**
```json
{
  "status": "jobs_launched",
  "project_id": "a7053649-7458-4e86-8905-1fef8100cebb",
  "agents_launched": 4,
  "messages_queued": 4
}
```

**Implementation:**
```python
@router.post("/{project_id}/launch-jobs")
async def launch_jobs(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """Launch all agent jobs for project"""
    project = await ProjectService.get_project(session, project_id, current_user.tenant_key)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.staging_status != "Completed!":
        raise HTTPException(status_code=400, detail="Project staging not completed")

    # Get all agents for project
    agents = await AgentJobManager.get_agents_for_project(session, project_id)

    # Initialize message queue for each agent
    for agent in agents:
        # Create initial job message
        await MessageQueueService.create_message(
            session=session,
            project_id=project_id,
            to_agent_id=agent.id,
            message_type="job",
            content=agent.mission
        )

        # Set agent status to Waiting
        agent.status = "Waiting"
        agent.messages_waiting = 1

    # Mark project as jobs_launched
    project.jobs_launched = True
    await session.commit()

    # Emit WebSocket event
    await websocket_manager.emit(
        event="project:jobs_launched",
        data={
            "project_id": str(project_id),
            "agents_launched": len(agents)
        },
        room=f"project:{project_id}"
    )

    return {
        "status": "jobs_launched",
        "project_id": str(project_id),
        "agents_launched": len(agents),
        "messages_queued": len(agents)
    }
```

---

### 4. GET /api/agents/{agent_id}/prompt

**Purpose**: Get agent-specific CLI prompt based on mode

**Request:**
```http
GET /api/agents/1c-ad97a1-e8d0-4c16/prompt?cli_mode=claude-code
Authorization: Bearer {token}
```

**Query Parameters:**
- `cli_mode` (required): `"claude-code"` | `"general"`

**Response:**
```json
{
  "prompt": "You are the Orchestrator agent for project 'Project Startup and initiation'.\n\nYour mission:\n{agent_mission}\n\nIn Claude Code CLI mode, you will coordinate subagents automatically.\n\nTo begin, acknowledge this job and start your mission.",
  "agent_id": "1c-ad97a1-e8d0-4c16",
  "agent_type": "orchestrator",
  "cli_mode": "claude-code"
}
```

**Implementation:**
```python
# api/endpoints/agents.py

@router.get("/{agent_id}/prompt")
async def get_agent_prompt(
    agent_id: UUID,
    cli_mode: str = Query(..., regex="^(claude-code|general)$"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get agent-specific CLI prompt"""
    agent = await AgentJobManager.get_agent(session, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Verify tenant access
    project = await ProjectService.get_project(session, agent.project_id, current_user.tenant_key)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    # Generate prompt based on CLI mode
    if cli_mode == "claude-code":
        prompt = await PromptGeneratorService.generate_claude_code_prompt(agent, project)
    else:
        prompt = await PromptGeneratorService.generate_general_cli_prompt(agent, project)

    return {
        "prompt": prompt,
        "agent_id": str(agent_id),
        "agent_type": agent.agent_type,
        "cli_mode": cli_mode
    }
```

---

### 5. PATCH /api/agents/{agent_id}/status

**Purpose**: Update agent status (called by agent or system)

**Request:**
```http
PATCH /api/agents/1c-ad97a1-e8d0-4c16/status
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "Working",
  "job_read": true,
  "job_acknowledged": true
}
```

**Response:**
```json
{
  "agent_id": "1c-ad97a1-e8d0-4c16",
  "status": "Working",
  "job_read": true,
  "job_acknowledged": true,
  "updated_at": "2025-11-21T10:30:00Z"
}
```

**Implementation:**
```python
@router.patch("/{agent_id}/status")
async def update_agent_status(
    agent_id: UUID,
    status_update: AgentStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """Update agent status and job tracking"""
    agent = await AgentJobManager.get_agent(session, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update fields
    if status_update.status:
        agent.status = status_update.status

        # Emit status change
        await websocket_manager.emit(
            event="agent:status_changed",
            data={
                "agent_id": str(agent_id),
                "status": status_update.status
            },
            room=f"project:{agent.project_id}"
        )

    if status_update.job_read is not None:
        agent.job_read = status_update.job_read

        if status_update.job_read:
            await websocket_manager.emit(
                event="agent:job_read",
                data={"agent_id": str(agent_id)},
                room=f"project:{agent.project_id}"
            )

    if status_update.job_acknowledged is not None:
        agent.job_acknowledged = status_update.job_acknowledged

        if status_update.job_acknowledged:
            await websocket_manager.emit(
                event="agent:job_acknowledged",
                data={"agent_id": str(agent_id)},
                room=f"project:{agent.project_id}"
            )

    agent.updated_at = datetime.utcnow()
    await session.commit()

    return {
        "agent_id": str(agent_id),
        "status": agent.status,
        "job_read": agent.job_read,
        "job_acknowledged": agent.job_acknowledged,
        "updated_at": agent.updated_at.isoformat()
    }
```

---

### 6. GET /api/agents/{agent_id}/messages

**Purpose**: Get message history for an agent

**Request:**
```http
GET /api/agents/1c-ad97a1-e8d0-4c16/messages?limit=50&offset=0
Authorization: Bearer {token}
```

**Response:**
```json
{
  "messages": [
    {
      "id": "msg-001",
      "from_agent_id": "orchestrator-id",
      "to_agent_id": "1c-ad97a1-e8d0-4c16",
      "message_type": "direct",
      "content": "Please begin analysis of project requirements.",
      "read": true,
      "created_at": "2025-11-21T10:00:00Z",
      "read_at": "2025-11-21T10:01:00Z"
    },
    {
      "id": "msg-002",
      "from_agent_id": "orchestrator-id",
      "to_agent_id": null,
      "message_type": "broadcast",
      "content": "All agents: Project staging complete. Begin implementation.",
      "read": true,
      "created_at": "2025-11-21T10:05:00Z",
      "read_at": "2025-11-21T10:06:00Z"
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**Implementation:**
```python
@router.get("/{agent_id}/messages")
async def get_agent_messages(
    agent_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get message history for agent"""
    agent = await AgentJobManager.get_agent(session, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Verify access
    project = await ProjectService.get_project(session, agent.project_id, current_user.tenant_key)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = await MessageQueueService.get_messages_for_agent(
        session, agent_id, limit, offset
    )

    total = await MessageQueueService.count_messages_for_agent(session, agent_id)

    return {
        "messages": [msg.to_dict() for msg in messages],
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

---

### 7. POST /api/agents/messages

**Purpose**: Send direct message to an agent

**Request:**
```http
POST /api/agents/messages
Authorization: Bearer {token}
Content-Type: application/json

{
  "from_agent_id": "orchestrator-id",  // optional (null = user)
  "to_agent_id": "analyzer-id",
  "message_type": "direct",
  "content": "Please provide status update."
}
```

**Response:**
```json
{
  "message": {
    "id": "msg-003",
    "from_agent_id": "orchestrator-id",
    "to_agent_id": "analyzer-id",
    "message_type": "direct",
    "content": "Please provide status update.",
    "read": false,
    "created_at": "2025-11-21T10:30:00Z",
    "read_at": null
  }
}
```

**Implementation:**
```python
@router.post("/messages")
async def send_message(
    message_data: MessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """Send message to agent"""
    # Verify agents exist and user has access
    to_agent = await AgentJobManager.get_agent(session, message_data.to_agent_id)
    if not to_agent:
        raise HTTPException(status_code=404, detail="Recipient agent not found")

    project = await ProjectService.get_project(session, to_agent.project_id, current_user.tenant_key)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create message
    message = await MessageQueueService.create_message(
        session=session,
        project_id=to_agent.project_id,
        from_agent_id=message_data.from_agent_id,
        to_agent_id=message_data.to_agent_id,
        message_type="direct",
        content=message_data.content
    )

    # Update counters
    if message_data.from_agent_id:
        from_agent = await AgentJobManager.get_agent(session, message_data.from_agent_id)
        from_agent.messages_sent += 1

    to_agent.messages_waiting += 1
    await session.commit()

    # Emit WebSocket event
    await websocket_manager.emit(
        event="agent:message_sent",
        data={"message": message.to_dict()},
        room=f"project:{to_agent.project_id}"
    )

    return {"message": message.to_dict()}
```

---

### 8. POST /api/agents/broadcast

**Purpose**: Send broadcast message to all agents

**Request:**
```http
POST /api/agents/broadcast
Authorization: Bearer {token}
Content-Type: application/json

{
  "project_id": "a7053649-7458-4e86-8905-1fef8100cebb",
  "from_agent_id": null,  // null = user broadcast
  "content": "All agents: Please pause and await further instructions."
}
```

**Response:**
```json
{
  "message": {
    "id": "msg-004",
    "from_agent_id": null,
    "to_agent_id": null,
    "message_type": "broadcast",
    "content": "All agents: Please pause and await further instructions.",
    "read": false,
    "created_at": "2025-11-21T10:35:00Z"
  },
  "recipients": 4
}
```

**Implementation:**
```python
@router.post("/broadcast")
async def send_broadcast(
    broadcast_data: BroadcastCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """Send broadcast message to all agents"""
    project = await ProjectService.get_project(
        session, broadcast_data.project_id, current_user.tenant_key
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create broadcast message
    message = await MessageQueueService.create_message(
        session=session,
        project_id=broadcast_data.project_id,
        from_agent_id=broadcast_data.from_agent_id,
        to_agent_id=None,  # None = broadcast
        message_type="broadcast",
        content=broadcast_data.content
    )

    # Update all agents' waiting count
    agents = await AgentJobManager.get_agents_for_project(session, broadcast_data.project_id)
    for agent in agents:
        if agent.id != broadcast_data.from_agent_id:
            agent.messages_waiting += 1

    if broadcast_data.from_agent_id:
        from_agent = await AgentJobManager.get_agent(session, broadcast_data.from_agent_id)
        if from_agent:
            from_agent.messages_sent += 1

    await session.commit()

    # Emit WebSocket event
    await websocket_manager.emit(
        event="agent:message_sent",
        data={"message": message.to_dict()},
        room=f"project:{broadcast_data.project_id}"
    )

    return {
        "message": message.to_dict(),
        "recipients": len(agents)
    }
```

---

## Database Schema Changes

### 1. Update mcp_agent_jobs Table

```sql
-- Add new columns for job tracking and message counters
ALTER TABLE mcp_agent_jobs ADD COLUMN IF NOT EXISTS job_read BOOLEAN DEFAULT FALSE;
ALTER TABLE mcp_agent_jobs ADD COLUMN IF NOT EXISTS job_acknowledged BOOLEAN DEFAULT FALSE;
ALTER TABLE mcp_agent_jobs ADD COLUMN IF NOT EXISTS messages_sent INTEGER DEFAULT 0;
ALTER TABLE mcp_agent_jobs ADD COLUMN IF NOT EXISTS messages_waiting INTEGER DEFAULT 0;
ALTER TABLE mcp_agent_jobs ADD COLUMN IF NOT EXISTS messages_read INTEGER DEFAULT 0;
ALTER TABLE mcp_agent_jobs ADD COLUMN IF NOT EXISTS cli_mode VARCHAR(20) DEFAULT 'general';

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_agent_jobs_project_status ON mcp_agent_jobs(project_id, status);
```

**SQLAlchemy Model Update:**

```python
# src/giljo_mcp/models.py

class MCPAgentJob(Base):
    __tablename__ = "mcp_agent_jobs"

    # ... existing fields ...

    # NEW: Job tracking fields
    job_read: Mapped[bool] = mapped_column(Boolean, default=False)
    job_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    # NEW: Message counters
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    messages_waiting: Mapped[int] = mapped_column(Integer, default=0)
    messages_read: Mapped[int] = mapped_column(Integer, default=0)

    # NEW: CLI mode tracking
    cli_mode: Mapped[str] = mapped_column(String(20), default="general")
```

---

### 2. Update mcp_projects Table

```sql
-- Add staging status and jobs launched flag
ALTER TABLE mcp_projects ADD COLUMN IF NOT EXISTS staging_status VARCHAR(20) DEFAULT 'Waiting';
ALTER TABLE mcp_projects ADD COLUMN IF NOT EXISTS jobs_launched BOOLEAN DEFAULT FALSE;
ALTER TABLE mcp_projects ADD COLUMN IF NOT EXISTS orchestrator_mission TEXT;
```

**SQLAlchemy Model Update:**

```python
class MCPProject(Base):
    __tablename__ = "mcp_projects"

    # ... existing fields ...

    # NEW: Staging tracking
    staging_status: Mapped[str] = mapped_column(String(20), default="Waiting")
    jobs_launched: Mapped[bool] = mapped_column(Boolean, default=False)
    orchestrator_mission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

---

### 3. Create agent_messages Table

```sql
CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES mcp_projects(id) ON DELETE CASCADE,
    from_agent_id UUID REFERENCES mcp_agent_jobs(id) ON DELETE SET NULL,
    to_agent_id UUID REFERENCES mcp_agent_jobs(id) ON DELETE CASCADE,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('direct', 'broadcast', 'job')),
    content TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    read_at TIMESTAMP,
    tenant_key VARCHAR(255) NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_agent_messages_to_agent ON agent_messages(to_agent_id, read);
CREATE INDEX idx_agent_messages_project ON agent_messages(project_id, created_at DESC);
CREATE INDEX idx_agent_messages_broadcast ON agent_messages(project_id, message_type) WHERE message_type = 'broadcast';
CREATE INDEX idx_agent_messages_tenant ON agent_messages(tenant_key);
```

**SQLAlchemy Model:**

```python
class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mcp_projects.id", ondelete="CASCADE"), nullable=False)
    from_agent_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("mcp_agent_jobs.id", ondelete="SET NULL"))
    to_agent_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("mcp_agent_jobs.id", ondelete="CASCADE"))
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'direct', 'broadcast', 'job'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    tenant_key: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    project: Mapped["MCPProject"] = relationship("MCPProject", back_populates="messages")
    from_agent: Mapped[Optional["MCPAgentJob"]] = relationship("MCPAgentJob", foreign_keys=[from_agent_id])
    to_agent: Mapped[Optional["MCPAgentJob"]] = relationship("MCPAgentJob", foreign_keys=[to_agent_id])

    def to_dict(self):
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "from_agent_id": str(self.from_agent_id) if self.from_agent_id else None,
            "to_agent_id": str(self.to_agent_id) if self.to_agent_id else None,
            "message_type": self.message_type,
            "content": self.content,
            "read": self.read,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None
        }
```

---

## WebSocket Events

### Event Specifications

**Event Format:**
```json
{
  "event": "event_name",
  "data": { /* event-specific data */ },
  "timestamp": "2025-11-21T10:30:00Z"
}
```

### Event Types

| Event | Trigger | Data | Room |
|-------|---------|------|------|
| `project:stage_started` | User clicks "Stage project" | `{project_id}` | `project:{id}` |
| `project:mission_chunk` | Orchestrator streams mission | `{text, chunk_index}` | `project:{id}` |
| `project:stage_completed` | Orchestrator finishes staging | `{project_id, mission, agents}` | `project:{id}` |
| `project:jobs_launched` | User clicks "Launch Jobs" | `{project_id, agents_launched}` | `project:{id}` |
| `agent:status_changed` | Agent updates status | `{agent_id, status, old_status}` | `project:{id}` |
| `agent:job_read` | Agent reads job | `{agent_id, read_at}` | `project:{id}` |
| `agent:job_acknowledged` | Agent acknowledges job | `{agent_id, acknowledged_at}` | `project:{id}` |
| `agent:message_sent` | Message sent to agent | `{message: {...}}` | `project:{id}` |
| `agent:message_read` | Agent reads message | `{agent_id, message_id, read_at}` | `project:{id}` |
| `agents:created` | Agents created after staging | `{project_id, agent_ids: [...]}` | `project:{id}` |

---

## Service Layer Updates

### 1. MessageQueueService

**File**: `src/giljo_mcp/services/message_queue_service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from ..models import AgentMessage

class MessageQueueService:
    """Service for managing agent message queue"""

    @staticmethod
    async def create_message(
        session: AsyncSession,
        project_id: UUID,
        content: str,
        message_type: str,
        tenant_key: str,
        from_agent_id: Optional[UUID] = None,
        to_agent_id: Optional[UUID] = None
    ) -> AgentMessage:
        """Create a new message"""
        message = AgentMessage(
            project_id=project_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            message_type=message_type,
            content=content,
            tenant_key=tenant_key
        )
        session.add(message)
        await session.flush()
        return message

    @staticmethod
    async def get_messages_for_agent(
        session: AsyncSession,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[AgentMessage]:
        """Get messages for specific agent (direct + broadcast)"""
        stmt = (
            select(AgentMessage)
            .where(
                or_(
                    AgentMessage.to_agent_id == agent_id,
                    AgentMessage.to_agent_id.is_(None)  # broadcasts
                )
            )
            .order_by(AgentMessage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count_messages_for_agent(
        session: AsyncSession,
        agent_id: UUID
    ) -> int:
        """Count total messages for agent"""
        stmt = (
            select(func.count())
            .select_from(AgentMessage)
            .where(
                or_(
                    AgentMessage.to_agent_id == agent_id,
                    AgentMessage.to_agent_id.is_(None)
                )
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def mark_message_read(
        session: AsyncSession,
        message_id: UUID
    ) -> AgentMessage:
        """Mark message as read"""
        stmt = select(AgentMessage).where(AgentMessage.id == message_id)
        result = await session.execute(stmt)
        message = result.scalar_one_or_none()

        if message and not message.read:
            message.read = True
            message.read_at = datetime.utcnow()
            await session.flush()

        return message
```

---

### 2. PromptGeneratorService

**File**: `src/giljo_mcp/services/prompt_generator_service.py`

```python
class PromptGeneratorService:
    """Service for generating agent prompts"""

    @staticmethod
    async def generate_staging_prompt(project: MCPProject) -> str:
        """Generate staging prompt for orchestrator"""
        return f"""You are the Orchestrator for project '{project.project_name}'.

Your task is to:
1. Analyze the project description
2. Create a comprehensive mission statement
3. Determine the required specialized agents
4. Assign specific missions to each agent

Project Description:
{project.project_description}

Please provide:
1. A detailed mission statement (500-1000 words)
2. List of required agents (Analyzer, Implementor, Tester, etc.)
3. Specific mission for each agent

Begin your analysis now."""

    @staticmethod
    async def generate_claude_code_prompt(agent: MCPAgentJob, project: MCPProject) -> str:
        """Generate prompt for Claude Code CLI mode"""
        return f"""You are the {agent.agent_type.title()} agent for project '{project.project_name}'.

Your mission:
{agent.mission}

You are running in Claude Code CLI mode. You will coordinate subagents automatically.

To begin:
1. Acknowledge this job
2. Read your mission carefully
3. Begin execution
4. Coordinate with other agents as needed

Report your progress via the message system.

Start now."""

    @staticmethod
    async def generate_general_cli_prompt(agent: MCPAgentJob, project: MCPProject) -> str:
        """Generate prompt for General CLI mode"""
        return f"""You are the {agent.agent_type.title()} agent for project '{project.project_name}'.

Your mission:
{agent.mission}

You are running in standalone CLI mode. Coordinate with other agents via the message system.

To begin:
1. Acknowledge this job
2. Execute your mission independently
3. Send status updates to the orchestrator
4. Complete your assigned tasks

Start now."""
```

---

## Next Document

[05_IMPLEMENTATION_ROADMAP.md](./05_IMPLEMENTATION_ROADMAP.md) - Detailed implementation phases and timeline

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
