---
Handover 0066: Agent Kanban Dashboard with Self-Navigation & Slack Communication
Date: 2025-10-28
Status: SUPERSEDED BY PROJECT 0073
Priority: DEPRECATED
Complexity: HIGH
Duration: 12-16 hours

IMPORTANT: This project has been SUPERSEDED by Project 0073 (Static Agent Grid with Enhanced Messaging)
See: handovers/0073_static_agent_grid_enhanced_messaging.md
See: handovers/0073_SUPERSEDES_0062_0066.md

The Kanban approach described below is DEPRECATED. The new vision uses a static agent grid
with status badges instead of columns, unified MCP messaging, and proper multi-tool support.
---

# Executive Summary

The GiljoAI MCP Server currently has a Messages page that displays agent communications in a table format. This handover transforms that into a **Kanban-style Agent Job Dashboard** with integrated Slack-style communication, providing real-time visibility into agent work progress and inter-agent messaging.

**Key Principle**: Developers need to see agent jobs as a visual workflow, track job status in real-time, and monitor agent communication without switching contexts. Agents self-navigate between columns via MCP communication.

The system replaces the Messages navigation item with a Kanban board (accessible as Tab 2 in Project Launch Panel) showing job cards grouped by status (Pending → Active → Completed → BLOCKED), with a Slack-style side panel for agent messaging.

**CRITICAL**: Agents move themselves between columns using MCP tools. No manual drag-drop. Developers can send messages to agents but cannot move job cards.

---

# Problem Statement

## Current State

Messages page exists at `/messages` showing agent communications in table format:
- Basic message listing with priority and status
- No visual workflow representation
- No connection between jobs and messages
- Cannot see agent workload at a glance
- Cannot track job progression through stages

## Gaps Without This Implementation

1. **No Workflow Visibility**: Cannot see job progression through stages
2. **Poor Context**: Messages disconnected from jobs
3. **Manual Status Tracking**: No visual kanban for agent work
4. **No Real-Time Updates**: Table doesn't show live job status changes
5. **Isolated Communication**: Messages separate from job context
6. **Resource Planning**: Cannot identify which agents are busy vs available

---

# Architecture & Data Model

## Database Schema (Depends on Handover 0062)

**PREREQUISITE**: Handover 0062 must be completed first (adds `project_id` to MCPAgentJob)

**Agent Model** (src/giljo_mcp/models.py):
```python
class Agent(Base):
    id = String(36)                    # UUID
    tenant_key = String(36)            # Multi-tenant isolation
    project_id = String(36)            # FK to projects (REQUIRED)
    name = String(200)                 # Agent name
    role = String(200)                 # orchestrator, analyzer, implementer, tester
    status = String(50)                # active | idle | working | decommissioned
    mission = Text                     # Optional mission description
    job_id = String(36)                # Links to MCPAgentJob
    mode = String(20)                  # claude | codex | gemini
    context_used = Integer
    last_active = DateTime
```

**MCPAgentJob Model** (src/giljo_mcp/models.py):
```python
class MCPAgentJob(Base):
    id = Integer                       # PK autoincrement
    tenant_key = String(36)            # Multi-tenant isolation
    job_id = String(36)                # UUID unique identifier
    project_id = String(36)            # FK to projects (ADDED IN 0062)
    agent_type = String(100)           # orchestrator, analyzer, implementer, etc.
    mission = Text                     # Job instructions/mission
    status = String(50)                # pending | active | completed | blocked
    spawned_by = String(36)            # Optional parent job_id
    context_chunks = JSON              # Array of context chunk IDs
    messages = JSONB                   # Agent communication messages
    acknowledged = Boolean
    started_at = DateTime
    completed_at = DateTime
    created_at = DateTime
```

**BLOCKED Status**: Encompasses both failed jobs and jobs waiting for feedback/human input

**Message Model** (src/giljo_mcp/models.py):
```python
class Message(Base):
    id = String(36)                    # UUID
    tenant_key = String(36)
    project_id = String(36)            # FK to projects
    from_agent_id = String(36)         # FK to agents (nullable)
    to_agents = JSON                   # List of target agent names
    status = String(50)                # pending | acknowledged | completed | failed
    priority = String(20)              # low | normal | high | critical
    content = Text
    created_at = DateTime
    acknowledged_at = DateTime
    acknowledged_by = JSON             # List of agent IDs
```

## Data Flow

```
Developer activates Project
    ↓
Developer copies orchestrator prompt → pastes to Claude Code
    ↓
Orchestrator reads project instructions via MCP
    ↓
Orchestrator creates MCPAgentJobs (breaks project into tasks)
    ↓
Orchestrator spawns Agents from skill pool
    ↓
Agent.job_id links to MCPAgentJob.job_id
    ↓
Jobs appear on Kanban board (grouped by status)
    ↓
Agents communicate via MCPAgentJob.messages (JSONB array)
    ↓
Developer monitors via Kanban + Slack panel
```

---

# Implementation Plan

## Phase 1: Database Migration - Add project_id to MCPAgentJob (2 hours)

**File**: `src/giljo_mcp/models.py`

**Modify MCPAgentJob Model**:

```python
class MCPAgentJob(Base):
    """
    MCP Agent Job model - tracks agent jobs separately from user tasks.

    Handover 0066: Added project_id for project-scoped job tracking.
    Jobs are work assignments created by orchestrator within a project.
    """

    __tablename__ = 'mcp_agent_jobs'

    # ... existing fields

    # NEW FIELD - Project association
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)

    # ... existing fields

    # NEW RELATIONSHIP
    project = relationship("Project", back_populates="agent_jobs")

    __table_args__ = (
        # ... existing indexes
        Index("idx_mcp_agent_jobs_project", "project_id"),
        Index("idx_mcp_agent_jobs_tenant_project", "tenant_key", "project_id"),
        # ... existing constraints
    )
```

**Update Project Model** (add back_populates):

```python
class Project(Base):
    # ... existing fields

    # NEW RELATIONSHIP
    agent_jobs = relationship("MCPAgentJob", back_populates="project", cascade="all, delete-orphan")
```

**Migration Script**: `migrations/add_project_id_to_agent_jobs.py`

```python
"""
Add project_id to mcp_agent_jobs table.

Handover 0066: Agent Kanban Dashboard requires project-scoped jobs.
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add project_id column (nullable initially)
    op.add_column('mcp_agent_jobs',
        sa.Column('project_id', sa.String(36), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_agent_jobs_project',
        'mcp_agent_jobs', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add indexes
    op.create_index('idx_mcp_agent_jobs_project', 'mcp_agent_jobs', ['project_id'])
    op.create_index('idx_mcp_agent_jobs_tenant_project', 'mcp_agent_jobs',
                    ['tenant_key', 'project_id'])

    # TODO: Backfill existing jobs with project_id from Agent.project_id
    # For now, jobs without project_id will be orphaned (acceptable in dev)

    # Make project_id NOT NULL after backfill
    op.alter_column('mcp_agent_jobs', 'project_id', nullable=False)


def downgrade():
    op.drop_index('idx_mcp_agent_jobs_tenant_project', 'mcp_agent_jobs')
    op.drop_index('idx_mcp_agent_jobs_project', 'mcp_agent_jobs')
    op.drop_constraint('fk_agent_jobs_project', 'mcp_agent_jobs', type_='foreignkey')
    op.drop_column('mcp_agent_jobs', 'project_id')
```

---

## Phase 2: Backend API Endpoints (3 hours)

**File**: `api/endpoints/agent_jobs.py`

**Add Kanban Endpoint**:

```python
@router.get("/kanban/{project_id}", response_model=KanbanBoardResponse)
async def get_kanban_board(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get Kanban board data for a project.

    Returns jobs grouped by status with agent details.

    Handover 0066: Agent Kanban Dashboard data endpoint.
    """
    from sqlalchemy import select, func
    from src.giljo_mcp.models import MCPAgentJob, Agent, Project

    # Verify project access
    project_stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == current_user.tenant_key
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Query jobs with agent details
    jobs_stmt = select(MCPAgentJob, Agent).outerjoin(
        Agent, Agent.job_id == MCPAgentJob.job_id
    ).where(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    ).order_by(MCPAgentJob.created_at.desc())

    result = await db.execute(jobs_stmt)
    jobs_with_agents = result.all()

    # Group by status
    kanban_data = {
        "pending": [],
        "active": [],
        "completed": [],
        "failed": []
    }

    for job, agent in jobs_with_agents:
        # Count unread messages
        unread_count = 0
        if job.messages:
            unread_count = sum(
                1 for msg in job.messages
                if msg.get('status') == 'pending'
            )

        job_data = {
            "job_id": job.job_id,
            "agent_id": agent.id if agent else None,
            "agent_name": agent.name if agent else job.agent_type,
            "agent_type": job.agent_type,
            "agent_mode": agent.mode if agent else "claude",
            "mission": job.mission,
            "status": job.status,
            "priority": "normal",  # Default, can enhance later
            "progress": 0,  # Can calculate from context
            "unread_messages": unread_count,
            "total_messages": len(job.messages) if job.messages else 0,
            "acknowledged": job.acknowledged,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "spawned_by": job.spawned_by
        }

        kanban_data[job.status].append(job_data)

    logger.info(f"Retrieved Kanban board for project {project_id}: "
                f"{len(jobs_with_agents)} jobs")

    return KanbanBoardResponse(
        project_id=project_id,
        project_name=project.name,
        columns=kanban_data,
        total_jobs=len(jobs_with_agents)
    )
```

**Add Message Thread Endpoint**:

```python
@router.get("/{job_id}/message-thread", response_model=MessageThreadResponse)
async def get_job_message_thread(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get message thread for a job (Slack-style conversation view).

    Handover 0066: Agent communication panel data endpoint.
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import MCPAgentJob

    # Fetch job
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not can_access_job(job, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Return messages in chronological order
    messages = job.messages or []

    # Sort by timestamp
    sorted_messages = sorted(messages, key=lambda m: m.get('timestamp', ''))

    return MessageThreadResponse(
        job_id=job_id,
        agent_type=job.agent_type,
        mission=job.mission,
        messages=sorted_messages,
        total_messages=len(sorted_messages)
    )
```

**Add Update Job Status Endpoint** (for drag-drop):

```python
@router.patch("/{job_id}/status", response_model=JobResponse)
async def update_job_status(
    job_id: str,
    status_update: JobStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update job status (for Kanban drag-drop).

    Handover 0066: Kanban status transitions.
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import MCPAgentJob
    from api.app import state

    # Fetch job
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not can_modify_job(job, current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate status transition
    valid_statuses = ["pending", "active", "completed", "failed"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid: {valid_statuses}"
        )

    # Update status
    old_status = job.status
    job.status = status_update.status

    # Update timestamps
    if status_update.status == "active" and not job.started_at:
        job.started_at = func.now()
    elif status_update.status in ["completed", "failed"]:
        job.completed_at = func.now()

    await db.commit()
    await db.refresh(job)

    # Broadcast WebSocket event
    if state.websocket_manager:
        await state.websocket_manager.broadcast(
            event_type="job:status_changed",
            data={
                "job_id": job_id,
                "old_status": old_status,
                "new_status": job.status,
                "project_id": job.project_id,
                "tenant_key": current_user.tenant_key
            },
            tenant_key=current_user.tenant_key
        )

    logger.info(f"Job {job_id} status changed: {old_status} → {job.status}")

    return job_to_response(job)
```

**Add Pydantic Models** (top of file):

```python
class KanbanBoardResponse(BaseModel):
    project_id: str
    project_name: str
    columns: Dict[str, List[Dict[str, Any]]]  # status -> jobs
    total_jobs: int

class MessageThreadResponse(BaseModel):
    job_id: str
    agent_type: str
    mission: str
    messages: List[Dict[str, Any]]
    total_messages: int

class JobStatusUpdate(BaseModel):
    status: str = Field(..., description="New job status")
```

---

## Phase 3: Frontend Kanban View (6 hours)

**File**: `frontend/src/views/KanbanView.vue` (NEW)

```vue
<template>
  <v-container fluid class="kanban-container">
    <!-- Project Header -->
    <v-row class="mb-4">
      <v-col cols="12" md="8">
        <h1 class="text-h4">
          <v-icon class="mr-2">mdi-view-column</v-icon>
          Agent Job Dashboard
        </h1>
        <p class="text-subtitle-1 text-grey">
          Project: {{ projectName || 'Loading...' }}
          <v-chip size="small" color="primary" class="ml-2">
            {{ totalJobs }} jobs
          </v-chip>
        </p>
      </v-col>
      <v-col cols="12" md="4" class="text-right">
        <v-btn
          color="primary"
          prepend-icon="mdi-refresh"
          @click="refreshBoard"
          :loading="loading"
        >
          Refresh
        </v-btn>
      </v-col>
    </v-row>

    <!-- Kanban Board -->
    <v-row class="kanban-board">
      <!-- Pending Column -->
      <v-col cols="12" md="3">
        <kanban-column
          title="Pending"
          status="pending"
          icon="mdi-clock-outline"
          color="grey"
          :jobs="columns.pending"
          @drop="onJobDrop"
          @view-job="openJobDetails"
          @view-messages="openMessageThread"
        />
      </v-col>

      <!-- Active Column -->
      <v-col cols="12" md="3">
        <kanban-column
          title="In Progress"
          status="active"
          icon="mdi-play-circle"
          color="primary"
          :jobs="columns.active"
          @drop="onJobDrop"
          @view-job="openJobDetails"
          @view-messages="openMessageThread"
        />
      </v-col>

      <!-- Completed Column -->
      <v-col cols="12" md="3">
        <kanban-column
          title="Completed"
          status="completed"
          icon="mdi-check-circle"
          color="success"
          :jobs="columns.completed"
          @drop="onJobDrop"
          @view-job="openJobDetails"
          @view-messages="openMessageThread"
        />
      </v-col>

      <!-- Failed Column -->
      <v-col cols="12" md="3">
        <kanban-column
          title="Failed"
          status="failed"
          icon="mdi-alert-circle"
          color="error"
          :jobs="columns.failed"
          @drop="onJobDrop"
          @view-job="openJobDetails"
          @view-messages="openMessageThread"
        />
      </v-col>
    </v-row>

    <!-- Slack-Style Message Panel (Side Drawer) -->
    <v-navigation-drawer
      v-model="messageDrawer"
      location="right"
      width="400"
      temporary
      class="message-drawer"
    >
      <message-thread-panel
        v-if="selectedJobId"
        :job-id="selectedJobId"
        @close="messageDrawer = false"
      />
    </v-navigation-drawer>

    <!-- Job Details Dialog -->
    <v-dialog v-model="jobDetailsDialog" max-width="800">
      <job-details-card
        v-if="selectedJob"
        :job="selectedJob"
        @close="jobDetailsDialog = false"
        @update="refreshBoard"
      />
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useWebSocketStore } from '@/stores/websocket'
import api from '@/services/api'
import KanbanColumn from '@/components/kanban/KanbanColumn.vue'
import MessageThreadPanel from '@/components/kanban/MessageThreadPanel.vue'
import JobDetailsCard from '@/components/kanban/JobDetailsCard.vue'

const route = useRoute()
const websocketStore = useWebSocketStore()

// Data
const loading = ref(false)
const projectId = ref(null)
const projectName = ref('')
const columns = ref({
  pending: [],
  active: [],
  completed: [],
  failed: []
})
const totalJobs = ref(0)
const messageDrawer = ref(false)
const selectedJobId = ref(null)
const jobDetailsDialog = ref(false)
const selectedJob = ref(null)

// Computed
const activeProjectId = computed(() => {
  // Get from route or store
  return projectId.value || route.query.project_id
})

// Methods
async function fetchKanbanData() {
  if (!activeProjectId.value) {
    console.warn('[KANBAN] No active project selected')
    return
  }

  loading.value = true

  try {
    const response = await api.agentJobs.getKanbanBoard(activeProjectId.value)

    projectName.value = response.data.project_name
    columns.value = response.data.columns
    totalJobs.value = response.data.total_jobs

    console.log('[KANBAN] Loaded board:', response.data)
  } catch (error) {
    console.error('[KANBAN] Error loading board:', error)
  } finally {
    loading.value = false
  }
}

async function onJobDrop(event) {
  const { jobId, newStatus } = event

  try {
    await api.agentJobs.updateStatus(jobId, newStatus)
    console.log('[KANBAN] Job status updated:', jobId, newStatus)

    // Refresh board to reflect changes
    await fetchKanbanData()
  } catch (error) {
    console.error('[KANBAN] Error updating job status:', error)
    // Revert drag on error
    await fetchKanbanData()
  }
}

function openMessageThread(jobId) {
  selectedJobId.value = jobId
  messageDrawer.value = true
}

function openJobDetails(job) {
  selectedJob.value = job
  jobDetailsDialog.value = true
}

function refreshBoard() {
  fetchKanbanData()
}

// WebSocket handlers
function setupWebSocketListeners() {
  websocketStore.on('job:status_changed', handleJobStatusChange)
  websocketStore.on('job:completed', handleJobComplete)
  websocketStore.on('job:failed', handleJobFail)
  websocketStore.on('message:received', handleMessageReceived)
}

function handleJobStatusChange(data) {
  console.log('[KANBAN] Job status changed:', data)
  fetchKanbanData() // Refresh board
}

function handleJobComplete(data) {
  console.log('[KANBAN] Job completed:', data)
  fetchKanbanData()
}

function handleJobFail(data) {
  console.log('[KANBAN] Job failed:', data)
  fetchKanbanData()
}

function handleMessageReceived(data) {
  console.log('[KANBAN] New message:', data)
  // Update unread count on affected job card
  fetchKanbanData()
}

// Lifecycle
onMounted(async () => {
  await fetchKanbanData()
  setupWebSocketListeners()
})
</script>

<style scoped>
.kanban-container {
  height: calc(100vh - 100px);
  overflow: hidden;
}

.kanban-board {
  height: calc(100% - 80px);
  overflow-x: auto;
}

.message-drawer {
  border-left: 1px solid rgba(0, 0, 0, 0.12);
}
</style>
```

---

## Phase 4: Kanban Column Component (3 hours)

**File**: `frontend/src/components/kanban/KanbanColumn.vue` (NEW)

```vue
<template>
  <div class="kanban-column">
    <!-- Column Header -->
    <v-card class="column-header mb-2" elevation="0">
      <v-card-title class="d-flex align-center">
        <v-icon :color="color" class="mr-2">{{ icon }}</v-icon>
        <span>{{ title }}</span>
        <v-spacer />
        <v-chip size="small" :color="color">
          {{ jobs.length }}
        </v-chip>
      </v-card-title>
    </v-card>

    <!-- Draggable Job Cards -->
    <div class="column-content">
      <draggable
        v-model="localJobs"
        :group="{ name: 'jobs', pull: true, put: true }"
        item-key="job_id"
        class="draggable-area"
        @change="onDragChange"
      >
        <template #item="{ element }">
          <job-card
            :job="element"
            :color="color"
            @view-details="$emit('view-job', element)"
            @view-messages="$emit('view-messages', element.job_id)"
          />
        </template>
      </draggable>

      <!-- Empty State -->
      <v-card v-if="jobs.length === 0" class="empty-state" elevation="0" variant="outlined">
        <v-card-text class="text-center text-grey">
          <v-icon size="48" color="grey-lighten-1">mdi-package-variant</v-icon>
          <p class="mt-2">No {{ title.toLowerCase() }} jobs</p>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'
import JobCard from './JobCard.vue'

const props = defineProps({
  title: { type: String, required: true },
  status: { type: String, required: true },
  icon: { type: String, required: true },
  color: { type: String, required: true },
  jobs: { type: Array, default: () => [] }
})

const emit = defineEmits(['drop', 'view-job', 'view-messages'])

const localJobs = ref([...props.jobs])

// Watch for external updates
watch(() => props.jobs, (newJobs) => {
  localJobs.value = [...newJobs]
}, { deep: true })

function onDragChange(event) {
  // Handle job dropped into this column
  if (event.added) {
    const job = event.added.element
    emit('drop', {
      jobId: job.job_id,
      newStatus: props.status,
      oldStatus: job.status
    })
  }
}
</script>

<style scoped>
.kanban-column {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.column-header {
  background: rgba(var(--v-theme-surface), 0.8);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.column-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  background: rgba(var(--v-theme-surface), 0.4);
  border-radius: 8px;
  min-height: 400px;
}

.draggable-area {
  min-height: 200px;
}

.empty-state {
  margin-top: 20px;
}
</style>
```

---

## Phase 5: Job Card Component (2 hours)

**File**: `frontend/src/components/kanban/JobCard.vue` (NEW)

```vue
<template>
  <v-card
    class="job-card mb-3"
    :class="{ 'job-card-dragging': isDragging }"
    elevation="2"
    @click="$emit('view-details')"
  >
    <!-- Agent Header -->
    <v-card-title class="d-flex align-center pa-3">
      <v-avatar :color="agentColor" size="32" class="mr-2">
        <v-icon color="white" size="small">{{ agentIcon }}</v-icon>
      </v-avatar>
      <div class="flex-grow-1">
        <div class="text-subtitle-2">{{ job.agent_name }}</div>
        <div class="text-caption text-grey">{{ job.agent_type }}</div>
      </div>
      <v-chip size="x-small" :color="modeColor">
        {{ job.agent_mode }}
      </v-chip>
    </v-card-title>

    <v-divider />

    <!-- Mission Preview -->
    <v-card-text class="pa-3">
      <p class="text-body-2 mission-text">
        {{ truncatedMission }}
      </p>

      <!-- Job Metadata -->
      <div class="d-flex align-center mt-2">
        <v-chip size="x-small" variant="outlined" class="mr-1">
          <v-icon start size="x-small">mdi-clock</v-icon>
          {{ relativeTime }}
        </v-chip>

        <!-- Message Badge -->
        <v-chip
          v-if="job.total_messages > 0"
          size="x-small"
          :color="job.unread_messages > 0 ? 'error' : 'grey'"
          @click.stop="$emit('view-messages')"
        >
          <v-icon start size="x-small">
            {{ job.unread_messages > 0 ? 'mdi-message-badge' : 'mdi-message' }}
          </v-icon>
          {{ job.unread_messages > 0 ? job.unread_messages : job.total_messages }}
        </v-chip>
      </div>

      <!-- Progress Bar (for active jobs) -->
      <v-progress-linear
        v-if="job.status === 'active'"
        :model-value="job.progress || 0"
        color="primary"
        height="4"
        class="mt-2"
      />
    </v-card-text>

    <!-- Actions -->
    <v-card-actions class="pa-2">
      <v-btn
        size="small"
        variant="text"
        icon
        @click.stop="$emit('view-details')"
      >
        <v-icon>mdi-open-in-new</v-icon>
      </v-btn>
      <v-spacer />
      <v-chip
        v-if="job.acknowledged"
        size="x-small"
        color="success"
        variant="tonal"
      >
        <v-icon start size="x-small">mdi-check</v-icon>
        Ack
      </v-chip>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { computed, ref } from 'vue'
import { formatDistanceToNow, parseISO } from 'date-fns'

const props = defineProps({
  job: { type: Object, required: true },
  color: { type: String, default: 'primary' }
})

defineEmits(['view-details', 'view-messages'])

const isDragging = ref(false)

const agentIcon = computed(() => {
  const typeMap = {
    'orchestrator': 'mdi-brain',
    'analyzer': 'mdi-magnify',
    'implementer': 'mdi-code-braces',
    'tester': 'mdi-test-tube',
    'ux-designer': 'mdi-palette',
    'backend': 'mdi-server',
    'frontend': 'mdi-monitor'
  }
  return typeMap[props.job.agent_type] || 'mdi-robot'
})

const agentColor = computed(() => {
  const colorMap = {
    'orchestrator': 'purple',
    'analyzer': 'blue',
    'implementer': 'green',
    'tester': 'orange',
    'ux-designer': 'pink',
    'backend': 'teal',
    'frontend': 'indigo'
  }
  return colorMap[props.job.agent_type] || 'grey'
})

const modeColor = computed(() => {
  const modeMap = {
    'claude': 'deep-purple',
    'codex': 'blue',
    'gemini': 'light-blue'
  }
  return modeMap[props.job.agent_mode] || 'grey'
})

const truncatedMission = computed(() => {
  const maxLength = 120
  return props.job.mission.length > maxLength
    ? props.job.mission.substring(0, maxLength) + '...'
    : props.job.mission
})

const relativeTime = computed(() => {
  try {
    return formatDistanceToNow(parseISO(props.job.created_at), { addSuffix: true })
  } catch {
    return 'Unknown'
  }
})
</script>

<style scoped>
.job-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 4px solid v-bind(color);
}

.job-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

.job-card-dragging {
  opacity: 0.5;
  transform: rotate(2deg);
}

.mission-text {
  line-height: 1.4;
  color: rgba(var(--v-theme-on-surface), 0.87);
}
</style>
```

---

## Phase 6: Slack-Style Message Thread Panel (4 hours)

**File**: `frontend/src/components/kanban/MessageThreadPanel.vue` (NEW)

```vue
<template>
  <div class="message-thread-panel">
    <!-- Header -->
    <v-toolbar color="primary" dark density="compact">
      <v-toolbar-title>
        <v-icon class="mr-2">mdi-message-text</v-icon>
        {{ agentType }} Messages
      </v-toolbar-title>
      <v-spacer />
      <v-btn icon @click="$emit('close')">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <!-- Mission Summary -->
    <v-card class="ma-3" variant="tonal" color="primary">
      <v-card-text>
        <p class="text-caption text-grey">Mission</p>
        <p class="text-body-2">{{ mission }}</p>
      </v-card-text>
    </v-card>

    <!-- Message Thread (Slack-style) -->
    <div class="message-list" ref="messageList">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message-bubble"
        :class="{ 'message-sent': message.from === 'user', 'message-received': message.from !== 'user' }"
      >
        <!-- Sender Info -->
        <div class="message-header">
          <v-avatar size="24" :color="getSenderColor(message.from)" class="mr-2">
            <span class="text-caption white--text">
              {{ getSenderInitials(message.from) }}
            </span>
          </v-avatar>
          <span class="text-subtitle-2">{{ message.from }}</span>
          <v-spacer />
          <span class="text-caption text-grey">{{ formatTime(message.timestamp) }}</span>
        </div>

        <!-- Message Content -->
        <div class="message-content">
          <p>{{ message.content }}</p>
        </div>

        <!-- Message Status -->
        <div class="message-footer">
          <v-chip
            v-if="message.status === 'acknowledged'"
            size="x-small"
            color="success"
            variant="tonal"
          >
            <v-icon start size="x-small">mdi-check-all</v-icon>
            Read
          </v-chip>
          <v-chip
            v-else-if="message.status === 'pending'"
            size="x-small"
            color="grey"
            variant="tonal"
          >
            <v-icon start size="x-small">mdi-check</v-icon>
            Sent
          </v-chip>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="messages.length === 0" class="empty-messages">
        <v-icon size="64" color="grey-lighten-1">mdi-message-off</v-icon>
        <p class="text-grey mt-2">No messages yet</p>
      </div>
    </div>

    <!-- Message Input -->
    <v-card class="message-input" elevation="2">
      <v-card-text>
        <v-textarea
          v-model="newMessage"
          placeholder="Send message to agent..."
          rows="3"
          variant="outlined"
          density="compact"
          hide-details
        />
        <v-btn
          color="primary"
          block
          class="mt-2"
          :disabled="!newMessage.trim()"
          @click="sendMessage"
        >
          <v-icon start>mdi-send</v-icon>
          Send
        </v-btn>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { format, parseISO } from 'date-fns'
import api from '@/services/api'

const props = defineProps({
  jobId: { type: String, required: true }
})

defineEmits(['close'])

const agentType = ref('')
const mission = ref('')
const messages = ref([])
const newMessage = ref('')
const messageList = ref(null)

async function fetchMessages() {
  try {
    const response = await api.agentJobs.getMessageThread(props.jobId)

    agentType.value = response.data.agent_type
    mission.value = response.data.mission
    messages.value = response.data.messages

    // Scroll to bottom
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('[MESSAGE THREAD] Error fetching messages:', error)
  }
}

async function sendMessage() {
  if (!newMessage.value.trim()) return

  try {
    await api.agentJobs.sendMessage(props.jobId, {
      content: newMessage.value,
      from: 'user',
      timestamp: new Date().toISOString()
    })

    newMessage.value = ''
    await fetchMessages()
  } catch (error) {
    console.error('[MESSAGE THREAD] Error sending message:', error)
  }
}

function getSenderColor(sender) {
  // Hash sender name to color
  const colors = ['blue', 'green', 'purple', 'orange', 'teal', 'pink']
  const hash = sender.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
}

function getSenderInitials(sender) {
  return sender
    .split(/[-_\s]/)
    .map(part => part[0])
    .join('')
    .toUpperCase()
    .substring(0, 2)
}

function formatTime(timestamp) {
  try {
    return format(parseISO(timestamp), 'h:mm a')
  } catch {
    return ''
  }
}

function scrollToBottom() {
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}

onMounted(() => {
  fetchMessages()
})

// Watch for new messages (WebSocket updates)
watch(() => props.jobId, () => {
  fetchMessages()
})
</script>

<style scoped>
.message-thread-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message-bubble {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(var(--v-theme-surface), 0.8);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.message-sent {
  background: rgba(var(--v-theme-primary), 0.1);
  border-left: 3px solid rgb(var(--v-theme-primary));
}

.message-received {
  background: rgba(var(--v-theme-surface), 1);
}

.message-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.message-content {
  margin-left: 32px;
  margin-bottom: 8px;
}

.message-footer {
  margin-left: 32px;
}

.empty-messages {
  text-align: center;
  padding: 48px 16px;
}

.message-input {
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>
```

---

## Phase 7: Router & Navigation Updates (1 hour)

**File**: `frontend/src/router/index.js`

**Replace Messages Route**:

```javascript
{
  path: '/kanban',
  name: 'Kanban',
  component: () => import('@/views/KanbanView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Agent Dashboard',
    showInNav: true,
    icon: 'mdi-view-column',
    order: 5
  }
}

// Remove old route:
// {
//   path: '/messages',
//   name: 'Messages',
//   ...
// }
```

**File**: `frontend/src/components/navigation/NavigationDrawer.vue`

**Update Navigation Item** (line ~122):

```vue
<!-- Replace Messages nav item with Kanban -->
<v-list-item
  to="/kanban"
  prepend-icon="mdi-view-column"
  title="Agent Dashboard"
/>
```

---

## Phase 8: API Service Integration (1 hour)

**File**: `frontend/src/services/api.js`

**Add Kanban Methods**:

```javascript
agentJobs: {
  // ... existing methods

  // Kanban endpoints
  getKanbanBoard: (projectId) =>
    apiClient.get(`/api/v1/agent-jobs/kanban/${projectId}`),

  updateStatus: (jobId, status) =>
    apiClient.patch(`/api/v1/agent-jobs/${jobId}/status`, { status }),

  getMessageThread: (jobId) =>
    apiClient.get(`/api/v1/agent-jobs/${jobId}/message-thread`),

  sendMessage: (jobId, message) =>
    apiClient.post(`/api/v1/agent-jobs/${jobId}/messages`, message)
}
```

---

## Phase 9: Testing (3 hours)

### Backend Tests

**File**: `tests/api/test_kanban_endpoints.py` (NEW)

```python
"""
Tests for Kanban dashboard endpoints.

Handover 0066: Agent Kanban Dashboard.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_kanban_board(client: AsyncClient, auth_headers, test_project):
    """Test fetching Kanban board data."""
    response = await client.get(
        f"/api/v1/agent-jobs/kanban/{test_project.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert "project_id" in data
    assert "project_name" in data
    assert "columns" in data
    assert "pending" in data["columns"]
    assert "active" in data["columns"]
    assert "completed" in data["columns"]
    assert "failed" in data["columns"]


@pytest.mark.asyncio
async def test_update_job_status(client: AsyncClient, auth_headers, test_job):
    """Test updating job status via drag-drop."""
    response = await client.patch(
        f"/api/v1/agent-jobs/{test_job.job_id}/status",
        headers=auth_headers,
        json={"status": "active"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_message_thread(client: AsyncClient, auth_headers, test_job):
    """Test fetching message thread for a job."""
    response = await client.get(
        f"/api/v1/agent-jobs/{test_job.job_id}/message-thread",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert "job_id" in data
    assert "messages" in data
    assert isinstance(data["messages"], list)


@pytest.mark.asyncio
async def test_kanban_multi_tenant_isolation(client: AsyncClient, auth_headers,
                                             other_tenant_project):
    """Test Kanban board respects multi-tenant isolation."""
    response = await client.get(
        f"/api/v1/agent-jobs/kanban/{other_tenant_project.id}",
        headers=auth_headers
    )

    assert response.status_code == 404  # Cannot access other tenant's project
```

### Frontend Tests

**File**: `tests/frontend/KanbanView.spec.js` (NEW)

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import KanbanView from '@/views/KanbanView.vue'
import { createVuetify } from 'vuetify'

describe('KanbanView', () => {
  let wrapper
  const vuetify = createVuetify()

  beforeEach(() => {
    wrapper = mount(KanbanView, {
      global: {
        plugins: [vuetify]
      }
    })
  })

  it('renders Kanban board with 4 columns', () => {
    expect(wrapper.findAll('.kanban-column')).toHaveLength(4)
  })

  it('displays job cards in correct columns', async () => {
    // Mock data
    await wrapper.setData({
      columns: {
        pending: [{ job_id: '1', mission: 'Test', status: 'pending' }],
        active: [],
        completed: [],
        failed: []
      }
    })

    const pendingColumn = wrapper.find('[status="pending"]')
    expect(pendingColumn.findAll('.job-card')).toHaveLength(1)
  })

  it('opens message drawer on message badge click', async () => {
    const messageBtn = wrapper.find('[data-test="message-badge"]')
    await messageBtn.trigger('click')

    expect(wrapper.vm.messageDrawer).toBe(true)
  })
})
```

---

# Files to Create/Modify

## Database Migration
1. **migrations/add_project_id_to_agent_jobs.py** (NEW, ~50 lines) - Add project_id column

## Backend
2. **src/giljo_mcp/models.py** (+15 lines) - Add project_id field and relationship
3. **api/endpoints/agent_jobs.py** (+180 lines) - 3 new endpoints
4. **api/schemas/agent_job.py** (+30 lines) - New response models

## Frontend
5. **frontend/src/views/KanbanView.vue** (NEW, ~250 lines) - Main Kanban dashboard
6. **frontend/src/components/kanban/KanbanColumn.vue** (NEW, ~150 lines) - Draggable column
7. **frontend/src/components/kanban/JobCard.vue** (NEW, ~200 lines) - Job card component
8. **frontend/src/components/kanban/MessageThreadPanel.vue** (NEW, ~250 lines) - Slack panel
9. **frontend/src/components/kanban/JobDetailsCard.vue** (NEW, ~150 lines) - Job details dialog
10. **frontend/src/router/index.js** (~10 lines) - Replace Messages route
11. **frontend/src/components/navigation/NavigationDrawer.vue** (~5 lines) - Update nav
12. **frontend/src/services/api.js** (+20 lines) - Kanban API methods

## Testing
13. **tests/api/test_kanban_endpoints.py** (NEW, ~100 lines) - Backend tests
14. **tests/frontend/KanbanView.spec.js** (NEW, ~80 lines) - Frontend tests

**Total**: ~1,500 lines across 14 files (5 new, 9 modified)

---

# Success Criteria

## Functional Requirements
- ✅ Kanban board displays jobs in 4 columns (Pending, Active, Completed, Failed)
- ✅ Drag-drop updates job status
- ✅ Real-time WebSocket updates for job status changes
- ✅ Slack-style message panel shows agent communication
- ✅ Message unread counts displayed on job cards
- ✅ Multi-tenant isolation enforced at all layers
- ✅ Navigation replaces Messages with Agent Dashboard

## User Experience Requirements
- ✅ Smooth drag-drop animation
- ✅ Visual feedback for job status (colors, icons)
- ✅ Message drawer slides in from right (Slack-style)
- ✅ Responsive design (works on desktop, tablet)
- ✅ Loading states for async operations
- ✅ Empty states for columns with no jobs

## Technical Requirements
- ✅ Database migration adds project_id without breaking existing data
- ✅ Efficient queries (no N+1 problems)
- ✅ WebSocket events properly scoped to tenant
- ✅ vuedraggable integrated for drag-drop
- ✅ Proper cleanup of WebSocket listeners
- ✅ Test coverage >70%

---

# Related Handovers

- **Handover 0019**: Agent Job Management (DEPENDS ON)
  - Provides MCPAgentJob infrastructure

- **Handover 0050**: Single Active Product Architecture (RELATES TO)
  - Jobs scoped to active product/project

- **Handover 0062**: Enhanced Agent Cards (SUPERSEDES)
  - Original spec replaced by Kanban vision

---

# Risk Assessment

**Complexity**: HIGH (full UI overhaul + drag-drop + real-time updates)
**Risk**: MEDIUM (database migration + navigation changes)
**Breaking Changes**: Navigation route change (/messages → /kanban)
**Performance Impact**: LOW (efficient queries with proper indexes)

---

# Timeline Estimate

**Phase 1**: 2 hours (Database migration)
**Phase 2**: 3 hours (Backend API)
**Phase 3**: 6 hours (Kanban View)
**Phase 4**: 3 hours (Kanban Column)
**Phase 5**: 2 hours (Job Card)
**Phase 6**: 4 hours (Message Panel)
**Phase 7**: 1 hour (Router/Nav)
**Phase 8**: 1 hour (API Service)
**Phase 9**: 3 hours (Testing)

**Total**: 25 hours for experienced developer

---

**Decision Recorded By**: System Architect + User
**Date**: 2025-10-28
**Priority**: CRITICAL (core workflow visibility)

---

**End of Handover 0066**
