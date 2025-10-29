# Backend Integration Remediation - Implementation Roadmap
## Project 0067 Task 4 - Remediation Planning

**Document**: Implementation roadmap for closing the 4 critical gaps identified in backend validation

---

## 1. CRITICAL PRIORITY: Broadcast to ALL Agents

### 1.1 Database/Schema Changes
**No database changes needed** - JSONB message storage already supports

### 1.2 Backend Implementation

#### New Endpoint: POST /api/agent-jobs/broadcast

**File**: `api/endpoints/agent_jobs.py`

**Location**: Add after `send_developer_message()` function (around line 1100)

```python
@router.post("/broadcast", response_model=BroadcastResponse, status_code=status.HTTP_201_CREATED)
async def broadcast_message(
    broadcast_request: BroadcastMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> BroadcastResponse:
    """
    Broadcast message to ALL agents in a project.
    
    Sends the same message to all jobs for the specified project.
    
    Args:
        broadcast_request: Message content and project_id
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        BroadcastResponse with job_ids that received message
    """
    from datetime import datetime, timezone
    
    # Validate content
    if not broadcast_request.content or not broadcast_request.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )
    
    # Verify project exists and user has access
    project_stmt = select(Project).where(
        Project.id == broadcast_request.project_id,
        Project.tenant_key == current_user.tenant_key
    )
    result = await db.execute(project_stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get all jobs for project
    jobs_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == broadcast_request.project_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(jobs_stmt)
    jobs = result.scalars().all()
    
    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No agents found for project"
        )
    
    # Create broadcast message
    message = {
        "from": "developer",
        "content": broadcast_request.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "broadcast": True  # Mark as broadcast message
    }
    
    # Add message to each job
    job_ids = []
    for job in jobs:
        job.messages = (job.messages or []) + [message]
        job_ids.append(job.job_id)
    
    await db.commit()
    
    # Broadcast via WebSocket
    if state.websocket_manager:
        await state.websocket_manager.broadcast_json(
            {
                "type": "message:broadcast",
                "project_id": broadcast_request.project_id,
                "job_ids": job_ids,
                "content": broadcast_request.content,
                "timestamp": message["timestamp"]
            }
        )
    
    logger.info(f"Broadcast message to {len(job_ids)} jobs in project {broadcast_request.project_id}")
    
    return BroadcastResponse(
        broadcast_id=str(uuid4()),
        project_id=broadcast_request.project_id,
        job_ids=job_ids,
        message_content=broadcast_request.content,
        timestamp=message["timestamp"],
        job_count=len(job_ids)
    )
```

#### New Pydantic Schema

**File**: `api/schemas/agent_job.py`

**Add after `SendMessageResponse` class**:

```python
class BroadcastMessageRequest(BaseModel):
    """Request to broadcast message to all agents in project"""
    project_id: str = Field(..., description="Project ID to broadcast to")
    content: str = Field(..., description="Message content to broadcast")


class BroadcastResponse(BaseModel):
    """Response from broadcast message endpoint"""
    broadcast_id: str = Field(..., description="Unique broadcast message ID")
    project_id: str = Field(..., description="Project ID")
    job_ids: List[str] = Field(..., description="Job IDs that received message")
    message_content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Timestamp of broadcast")
    job_count: int = Field(..., description="Number of jobs that received message")
```

### 1.3 WebSocket Event Handler

**File**: `api/websocket_service.py`

**Add to WebSocketService class**:

```python
async def notify_broadcast_message(
    self,
    project_id: str,
    job_ids: List[str],
    content: str,
    timestamp: str
):
    """Notify all clients of broadcast message to agents"""
    message = {
        "type": "message:broadcast",
        "project_id": project_id,
        "job_ids": job_ids,
        "content": content,
        "timestamp": timestamp,
        "job_count": len(job_ids)
    }
    
    # Broadcast to all connected clients for this project
    await self.broadcast_json(message)
```

### 1.4 Frontend Integration

**File**: `frontend/src/services/api.js`

**Add to agentJobs object**:

```javascript
broadcastMessage: (projectId, content) =>
  apiClient.post(`/api/agent-jobs/broadcast`, {
    project_id: projectId,
    content: content
  })
```

### 1.5 Testing

Create test file: `tests/test_broadcast_endpoint.py`

```python
@pytest.mark.asyncio
async def test_broadcast_message_to_all_agents(client: AsyncClient, tenant_key: str):
    """Test broadcasting message to all agents in project"""
    # Create project
    project = await create_test_project(tenant_key)
    
    # Create multiple jobs
    job1 = await create_test_job(project.id, tenant_key)
    job2 = await create_test_job(project.id, tenant_key)
    
    # Broadcast message
    response = await client.post(
        "/api/agent-jobs/broadcast",
        json={
            "project_id": project.id,
            "content": "Broadcast test message"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["job_count"] == 2
    assert len(data["job_ids"]) == 2

@pytest.mark.asyncio
async def test_broadcast_message_multi_tenant_isolation(client: AsyncClient):
    """Test broadcast respects multi-tenant isolation"""
    # Create project for tenant A
    project_a = await create_test_project("tenant_a")
    job_a = await create_test_job(project_a.id, "tenant_a")
    
    # Create project for tenant B
    project_b = await create_test_project("tenant_b")
    job_b = await create_test_job(project_b.id, "tenant_b")
    
    # Broadcast to project A should not affect project B
    response = await client.post(
        "/api/agent-jobs/broadcast",
        json={
            "project_id": project_a.id,
            "content": "Test"
        },
        headers={"X-Tenant-Key": "tenant_a"}
    )
    
    # Verify only job_a got message
    assert response.status_code == 201
    data = response.json()
    assert data["job_count"] == 1
    assert data["job_ids"][0] == job_a.job_id
```

---

## 2. CRITICAL PRIORITY: Project Closeout Workflow

### 2.1 Database/Schema Changes

**File**: `src/giljo_mcp/models.py`

**Modify Project model to add closeout support**:

```python
class Project(Base):
    # ... existing fields ...
    
    # NEW: Closeout workflow fields
    closeout_status = Column(String(50), default="pending")  # pending, in_progress, completed
    closeout_started_at = Column(DateTime(timezone=True), nullable=True)
    closeout_completed_at = Column(DateTime(timezone=True), nullable=True)
    closeout_result = Column(JSON, default=dict)  # {steps: {...}, success: bool, error: str}
```

### 2.2 Backend Implementation

#### New Endpoint: POST /api/projects/{project_id}/closeout

**File**: `api/endpoints/projects.py`

**Add new closeout endpoint**:

```python
@router.post("/{project_id}/closeout", response_model=ProjectCloseoutResponse)
async def closeout_project(
    project_id: str,
    closeout_request: ProjectCloseoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> ProjectCloseoutResponse:
    """
    Execute project closeout procedure.
    
    Implements closeout workflow:
    1. Commit code changes
    2. Push changes to repository
    3. Document completion
    4. Mark project as completed
    5. Retire agents
    
    Args:
        project_id: Project to closeout
        closeout_request: Closeout parameters
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        ProjectCloseoutResponse with execution details
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    
    # Fetch project
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status == "completed":
        raise HTTPException(status_code=400, detail="Project already completed")
    
    # Start closeout
    project.closeout_status = "in_progress"
    project.closeout_started_at = datetime.now(timezone.utc)
    
    await db.flush()
    
    # Execute closeout steps
    closeout_steps = {}
    
    try:
        # Step 1: Commit code
        if closeout_request.commit_message:
            closeout_steps["commit"] = {
                "status": "completed",
                "message": closeout_request.commit_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Step 2: Push changes
        if closeout_request.should_push:
            closeout_steps["push"] = {
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Step 3: Document completion
        if closeout_request.documentation:
            closeout_steps["documentation"] = {
                "status": "completed",
                "content": closeout_request.documentation,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Step 4: Mark project as completed
        project.status = "completed"
        project.completed_at = datetime.now(timezone.utc)
        closeout_steps["mark_complete"] = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Step 5: Retire agents
        if closeout_request.retire_agents:
            agents_stmt = select(Agent).where(Agent.project_id == project_id)
            agents_result = await db.execute(agents_stmt)
            agents = agents_result.scalars().all()
            
            retired_agents = []
            for agent in agents:
                agent.status = "retired"
                retired_agents.append(agent.id)
            
            closeout_steps["retire_agents"] = {
                "status": "completed",
                "agent_ids": retired_agents,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Mark closeout successful
        project.closeout_status = "completed"
        project.closeout_completed_at = datetime.now(timezone.utc)
        project.closeout_result = {
            "success": True,
            "steps": closeout_steps
        }
        
        await db.commit()
        
        # Broadcast completion
        if state.websocket_manager:
            await state.websocket_manager.broadcast_json({
                "type": "project:closeout",
                "project_id": project_id,
                "status": "completed",
                "steps": closeout_steps
            })
        
        logger.info(f"Project {project_id} closeout completed by {current_user.username}")
        
        return ProjectCloseoutResponse(
            project_id=project.id,
            status="completed",
            closeout_steps=closeout_steps,
            agents_retired=len(closeout_steps.get("retire_agents", {}).get("agent_ids", [])),
            timestamp=project.closeout_completed_at
        )
    
    except Exception as e:
        # Mark closeout failed
        project.closeout_status = "failed"
        project.closeout_result = {
            "success": False,
            "error": str(e)
        }
        await db.commit()
        
        logger.error(f"Project {project_id} closeout failed: {e}")
        
        raise HTTPException(status_code=500, detail=f"Closeout failed: {str(e)}")
```

#### New Pydantic Schemas

**File**: `api/schemas/projects.py`

```python
class ProjectCloseoutRequest(BaseModel):
    """Request to closeout a project"""
    commit_message: Optional[str] = Field(None, description="Git commit message")
    should_push: bool = Field(False, description="Should push changes to repository")
    documentation: Optional[str] = Field(None, description="Completion documentation")
    retire_agents: bool = Field(True, description="Should retire project agents")


class ProjectCloseoutResponse(BaseModel):
    """Response from project closeout"""
    project_id: str = Field(..., description="Project ID")
    status: str = Field(..., description="Closeout status: completed/failed")
    closeout_steps: Dict[str, Any] = Field(..., description="Details of each closeout step")
    agents_retired: int = Field(0, description="Number of agents retired")
    timestamp: datetime = Field(..., description="Completion timestamp")
```

### 2.3 WebSocket Event Handlers

**File**: `api/websocket_service.py`

```python
async def notify_project_closeout(
    self,
    project_id: str,
    status: str,
    steps: Dict[str, Any]
):
    """Notify clients of project closeout progress"""
    message = {
        "type": "project:closeout",
        "project_id": project_id,
        "status": status,
        "steps": steps
    }
    
    await self.broadcast_json(message)
```

### 2.4 Frontend Integration

**File**: `frontend/src/services/api.js`

```javascript
projects: {
    // ... existing methods ...
    closeout: (id, data) => apiClient.post(`/api/projects/${id}/closeout`, data)
}
```

### 2.5 Testing

```python
@pytest.mark.asyncio
async def test_project_closeout_workflow(client: AsyncClient, tenant_key: str):
    """Test complete project closeout workflow"""
    project = await create_test_project(tenant_key)
    
    response = await client.post(
        f"/api/projects/{project.id}/closeout",
        json={
            "commit_message": "Final commit - project complete",
            "should_push": True,
            "documentation": "Project successfully completed",
            "retire_agents": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "commit" in data["closeout_steps"]
    assert "push" in data["closeout_steps"]
    assert "documentation" in data["closeout_steps"]
    assert "retire_agents" in data["closeout_steps"]
```

---

## 3. HIGH PRIORITY: Terminal Prompt Generation

### 3.1 Prompt Template Storage

**File**: `src/giljo_mcp/prompt_templates.py` (NEW)

```python
"""Prompt templates for agent terminal execution"""

CODEX_PROMPT_TEMPLATE = """
[CODEX Terminal Initialization]

Project: {project_name}
Mission: {project_mission}
Project ID: {project_id}

INSTRUCTIONS FOR CODEX:
1. Copy this entire prompt into your CODEX terminal
2. Replace {{variables}} with actual values
3. Execute step by step
4. Report progress back to GiljoAI dashboard

CODEX INSTRUCTIONS:
{codex_instructions}

When complete, return to GiljoAI dashboard and mark mission as complete.
"""

GEMINI_PROMPT_TEMPLATE = """
[GEMINI Terminal Initialization]

Project: {project_name}
Mission: {project_mission}
Project ID: {project_id}

INSTRUCTIONS FOR GEMINI:
1. Copy this entire prompt into your GEMINI terminal
2. Replace {{variables}} with actual values
3. Execute step by step
4. Report progress back to GiljoAI dashboard

GEMINI INSTRUCTIONS:
{gemini_instructions}

When complete, return to GiljoAI dashboard and mark mission as complete.
"""
```

### 3.2 Backend Implementation

**File**: `api/endpoints/projects.py`

```python
@router.get("/{project_id}/prompt/{agent_type}", response_model=PromptResponse)
async def get_agent_prompt(
    project_id: str,
    agent_type: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> PromptResponse:
    """
    Get copy-paste prompt for agent terminal execution.
    
    Supports: codex, gemini, claude-code
    """
    # Fetch project
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if agent_type not in ["codex", "gemini", "claude-code"]:
        raise HTTPException(status_code=400, detail="Invalid agent type")
    
    # Get appropriate template
    if agent_type == "codex":
        prompt = CODEX_PROMPT_TEMPLATE.format(
            project_name=project.name,
            project_mission=project.mission,
            project_id=project.id,
            codex_instructions=project.mission
        )
    elif agent_type == "gemini":
        prompt = GEMINI_PROMPT_TEMPLATE.format(
            project_name=project.name,
            project_mission=project.mission,
            project_id=project.id,
            gemini_instructions=project.mission
        )
    else:  # claude-code
        prompt = f"Claude Code - Execute this mission: {project.mission}"
    
    return PromptResponse(
        agent_type=agent_type,
        prompt=prompt,
        project_id=project.id
    )
```

### 3.3 Pydantic Schema

```python
class PromptResponse(BaseModel):
    """Response with agent terminal prompt"""
    agent_type: str = Field(..., description="Agent type: codex, gemini, claude-code")
    prompt: str = Field(..., description="Copy-paste prompt for agent terminal")
    project_id: str = Field(..., description="Project ID")
```

### 3.4 Frontend Integration

```javascript
projects: {
    // ... existing ...
    getCodexPrompt: (id) => apiClient.get(`/api/projects/${id}/prompt/codex`),
    getGeminiPrompt: (id) => apiClient.get(`/api/projects/${id}/prompt/gemini`),
    getClaudeCodePrompt: (id) => apiClient.get(`/api/projects/${id}/prompt/claude-code`)
}
```

---

## 4. MEDIUM PRIORITY: Agent Reactivation

### 4.1 Backend Implementation

**File**: `api/endpoints/agent_jobs.py`

```python
@router.post("/{job_id}/reactivate", response_model=JobResponse)
async def reactivate_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> JobResponse:
    """Reactivate a completed or blocked job for continued work"""
    from datetime import datetime, timezone
    
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in ["completed", "failed", "blocked"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reactivate job with status: {job.status}"
        )
    
    # Reactivate job
    job.status = "active"
    job.acknowledged = True
    job.started_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(job)
    
    logger.info(f"Reactivated job {job_id} for continued work")
    
    return job_to_response(job)
```

---

## 5. Testing Infrastructure

### Create Comprehensive Test Suite

**File**: `tests/test_critical_gaps.py` (NEW)

```python
"""Test critical gaps remediation"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone


class TestBroadcastMessaging:
    """Tests for broadcast to all agents feature"""
    
    @pytest.mark.asyncio
    async def test_broadcast_message_endpoint_exists(self, client: AsyncClient):
        pass
    
    @pytest.mark.asyncio
    async def test_broadcast_multi_tenant_isolation(self, client: AsyncClient):
        pass


class TestProjectCloseout:
    """Tests for project closeout workflow"""
    
    @pytest.mark.asyncio
    async def test_closeout_endpoint_exists(self, client: AsyncClient):
        pass
    
    @pytest.mark.asyncio
    async def test_closeout_retires_agents(self, client: AsyncClient):
        pass


class TestPromptGeneration:
    """Tests for terminal prompt generation"""
    
    @pytest.mark.asyncio
    async def test_codex_prompt_endpoint(self, client: AsyncClient):
        pass
    
    @pytest.mark.asyncio
    async def test_gemini_prompt_endpoint(self, client: AsyncClient):
        pass


class TestAgentReactivation:
    """Tests for agent reactivation"""
    
    @pytest.mark.asyncio
    async def test_reactivate_completed_agent(self, client: AsyncClient):
        pass
```

---

## Summary Table: Implementation Checklist

| Feature | Endpoint | File | Lines | Priority | Status |
|---------|----------|------|-------|----------|--------|
| Broadcast to ALL | POST /broadcast | agent_jobs.py | 80 | CRITICAL | ⏳ TODO |
| Closeout workflow | POST /closeout | projects.py | 120 | CRITICAL | ⏳ TODO |
| CODEX prompt | GET /prompt/codex | projects.py | 40 | HIGH | ⏳ TODO |
| GEMINI prompt | GET /prompt/gemini | projects.py | 40 | HIGH | ⏳ TODO |
| Agent reactivate | POST /reactivate | agent_jobs.py | 35 | MEDIUM | ⏳ TODO |
| WebSocket events | notify_* methods | websocket_service.py | 60 | SUPPORTING | ⏳ TODO |
| Frontend API calls | agentJobs.* | api.js | 20 | SUPPORTING | ⏳ TODO |
| Schemas | *Request/Response | schemas/ | 80 | SUPPORTING | ⏳ TODO |
| Tests | test_*.py | tests/ | 200+ | VALIDATION | ⏳ TODO |
| Database migrations | (Optional) | migrations/ | 50 | OPTIONAL | ⏳ TODO |

**Total estimated code**: 700-800 lines
**Total estimated effort**: 13-18 hours
**Test coverage target**: 90%+ on new endpoints

---

## Implementation Order (Recommended)

1. **Day 1 - Core Endpoints**
   - Broadcast messaging endpoint
   - Closeout workflow endpoint
   - Unit tests for both

2. **Day 2 - Supporting Features**
   - Prompt generation endpoints (CODEX, GEMINI, Claude Code)
   - Agent reactivation endpoint
   - Feature tests

3. **Day 3 - Integration & Polish**
   - WebSocket event handlers
   - Frontend integration
   - Full integration testing
   - Code review and cleanup

---

## Success Criteria

All endpoints pass:
- ✓ Unit tests (request/response validation)
- ✓ Integration tests (multi-tenant isolation)
- ✓ WebSocket tests (event broadcasting)
- ✓ Frontend tests (API calls work)
- ✓ Manual user testing (workflow complete)

Backend compliance: 100% with handwritten specifications

---

**Prepared**: 2025-10-29
**Status**: READY FOR IMPLEMENTATION
**Next Step**: Create tickets for each endpoint and assign to developers

