---
Handover 0062: Enhanced Agent Cards with Project Context
Date: 2025-10-27
Status: Ready for Implementation
Priority: CRITICAL
Complexity: MEDIUM
Duration: 8-10 hours
---

# Executive Summary

The GiljoAI MCP Server's agent management UI currently displays agent cards with basic information but lacks project-specific context. This handover enhances agent cards to show project-specific jobs, provide copyable project instructions, and display which agents are working on which projects - all within a clean, intuitive interface.

**Key Principle**: Agent cards should provide immediate visibility into what each agent is working on, with easy access to project-specific instructions for manual coordination.

The system will display active jobs per agent per project, provide one-click instruction copying, and show real-time job status updates via WebSocket integration.

---

# Problem Statement

## Current State

Agent cards exist but lack project context:
- Basic agent information displayed (name, type, status)
- No visibility into what projects each agent is working on
- No way to see project-specific jobs assigned to agents
- No copyable instructions for manual agent coordination
- Can't tell which agents are busy vs available

## Gaps Without This Implementation

1. **No Job Visibility**: Users can't see what agents are actively working on
2. **Manual Coordination Difficult**: No easy way to get project instructions for external agents
3. **Resource Planning**: Can't identify available agents for new work
4. **Context Loss**: Users don't know which agents have project context
5. **Poor UX**: Must navigate to multiple views to understand agent workload

---

# Implementation Plan

## Overview

This implementation enhances existing agent cards with project-specific sections, job lists, and copyable instructions. Backend adds new endpoints to fetch agent jobs by project and generate project instructions.

**Total Estimated Lines of Code**: ~500 lines across 6 files

## Phase 1: Backend - Agent Jobs by Project Endpoint (2 hours)

**File**: `api/endpoints/agent_jobs.py`

**Add Endpoint**:

```python
@router.get("/by-agent-and-project", response_model=List[Dict[str, Any]])
async def get_agent_jobs_by_project(
    agent_id: str = Query(...),
    project_id: str = Query(None),
    status: str = Query(None),
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get agent jobs for a specific agent, optionally filtered by project and status.

    Returns jobs grouped by project with job details.
    """
    from sqlalchemy import select, func
    from src.giljo_mcp.models import MCPAgentJob, Project

    # Build query
    query = select(MCPAgentJob).where(
        MCPAgentJob.agent_id == agent_id,
        MCPAgentJob.tenant_key == tenant_key
    )

    if project_id:
        query = query.where(MCPAgentJob.project_id == project_id)

    if status:
        query = query.where(MCPAgentJob.status == status)

    # Order by created_at descending (most recent first)
    query = query.order_by(MCPAgentJob.created_at.desc())

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Group jobs by project
    jobs_by_project = {}
    for job in jobs:
        # Fetch project info
        project_result = await db.execute(
            select(Project).where(Project.id == job.project_id)
        )
        project = project_result.scalar_one_or_none()

        if not project:
            continue

        project_key = str(project.id)
        if project_key not in jobs_by_project:
            jobs_by_project[project_key] = {
                "project_id": str(project.id),
                "project_name": project.name,
                "product_id": str(project.product_id),
                "jobs": []
            }

        jobs_by_project[project_key]["jobs"].append({
            "job_id": str(job.id),
            "mission": job.mission,
            "status": job.status,
            "priority": job.priority,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "acknowledged_at": job.acknowledged_at.isoformat() if job.acknowledged_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        })

    return list(jobs_by_project.values())
```

**File**: `api/endpoints/projects.py`

**Add Endpoint**:

```python
@router.get("/{project_id}/instructions")
async def get_project_instructions(
    project_id: str,
    agent_id: str = Query(None),
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get copyable instructions for a project, optionally tailored to a specific agent.

    Returns formatted instructions including:
    - Project overview
    - Active tasks
    - Agent-specific context (if agent_id provided)
    - Field priority settings
    - Product vision summary
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import Project, Product, Task, MCPAgent

    # Fetch project
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_key == tenant_key
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch product
    product_result = await db.execute(
        select(Product).where(Product.id == project.product_id)
    )
    product = product_result.scalar_one_or_none()

    # Fetch active tasks
    tasks_result = await db.execute(
        select(Task).where(
            Task.project_id == project_id,
            Task.status.in_(['pending', 'in_progress'])
        ).order_by(Task.priority.desc())
    )
    tasks = tasks_result.scalars().all()

    # Build instructions
    instructions = f"""# Project: {project.name}

## Overview
{project.description or 'No description provided'}

## Product Context
Product: {product.name if product else 'Unknown'}
"""

    if product and product.config_data:
        field_priority = product.config_data.get('field_priority', {})
        if field_priority:
            instructions += f"""
## Field Priority Configuration
{json.dumps(field_priority, indent=2)}
"""

    if agent_id:
        # Fetch agent info
        agent_result = await db.execute(
            select(MCPAgent).where(MCPAgent.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        if agent:
            instructions += f"""
## Agent Context
Agent: {agent.name}
Type: {agent.agent_type}
Capabilities: {', '.join(agent.capabilities or [])}
"""

    # Add tasks
    if tasks:
        instructions += """
## Active Tasks
"""
        for i, task in enumerate(tasks, 1):
            instructions += f"""
### Task {i}: {task.title}
- Status: {task.status}
- Priority: {task.priority}
- Description: {task.description or 'No description'}
"""

    instructions += f"""
## Instructions
1. Review the project overview and product context
2. Understand the field priority configuration (defines what's important)
3. Work through active tasks in priority order
4. Report progress and blockers via agent communication queue
5. Mark tasks complete when finished

## Getting Started
To begin work on this project, acknowledge the job assignment and start with the highest priority task.
"""

    return {
        "project_id": project_id,
        "project_name": project.name,
        "instructions": instructions,
        "task_count": len(tasks),
        "agent_specific": agent_id is not None
    }
```

## Phase 2: Frontend - Enhanced Agent Card Component (3-4 hours)

**File**: `frontend/src/components/agents/EnhancedAgentCard.vue` (MODIFY EXISTING)

**Add Project Jobs Section**:

```vue
<template>
  <v-card class="agent-card">
    <!-- Existing agent info header -->
    <v-card-title>
      <v-avatar :color="agentStatusColor" size="40" class="mr-3">
        <v-icon color="white">{{ agentIcon }}</v-icon>
      </v-avatar>
      <div>
        <div class="text-h6">{{ agent.name }}</div>
        <div class="text-caption text-grey">{{ agent.agent_type }}</div>
      </div>
    </v-card-title>

    <!-- NEW: Project Jobs Section -->
    <v-card-text>
      <v-expansion-panels v-if="projectJobs.length > 0">
        <v-expansion-panel
          v-for="projectGroup in projectJobs"
          :key="projectGroup.project_id"
        >
          <v-expansion-panel-title>
            <v-row no-gutters align="center">
              <v-col>
                <v-icon class="mr-2">mdi-folder</v-icon>
                {{ projectGroup.project_name }}
              </v-col>
              <v-col cols="auto">
                <v-chip
                  size="small"
                  :color="getJobStatusColor(projectGroup.jobs)"
                >
                  {{ projectGroup.jobs.length }} job{{ projectGroup.jobs.length !== 1 ? 's' : '' }}
                </v-chip>
              </v-col>
            </v-row>
          </v-expansion-panel-title>

          <v-expansion-panel-text>
            <!-- Job List -->
            <v-list density="compact">
              <v-list-item
                v-for="job in projectGroup.jobs"
                :key="job.job_id"
                class="mb-2"
              >
                <template v-slot:prepend>
                  <v-icon :color="getStatusColor(job.status)">
                    {{ getStatusIcon(job.status) }}
                  </v-icon>
                </template>

                <v-list-item-title>
                  {{ truncate(job.mission, 60) }}
                </v-list-item-title>

                <v-list-item-subtitle>
                  <div class="d-flex align-center mt-1">
                    <v-chip size="x-small" :color="getStatusColor(job.status)" class="mr-2">
                      {{ job.status }}
                    </v-chip>
                    <span class="text-caption text-grey">
                      Priority: {{ job.priority }}
                    </span>
                  </div>

                  <!-- Progress bar for in_progress jobs -->
                  <v-progress-linear
                    v-if="job.status === 'in_progress'"
                    :model-value="job.progress"
                    height="4"
                    color="primary"
                    class="mt-2"
                  />
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-btn
                    icon
                    size="small"
                    variant="text"
                    @click="viewJobDetails(job)"
                  >
                    <v-icon>mdi-open-in-new</v-icon>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>

            <!-- Project Instructions Button -->
            <v-divider class="my-3" />

            <v-btn
              block
              variant="outlined"
              color="primary"
              @click="copyProjectInstructions(projectGroup.project_id)"
              :loading="loadingInstructions[projectGroup.project_id]"
            >
              <v-icon class="mr-2">mdi-content-copy</v-icon>
              Copy Project Instructions
            </v-btn>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- No jobs message -->
      <v-alert
        v-else
        type="info"
        variant="tonal"
        density="compact"
      >
        No active jobs for this agent
      </v-alert>
    </v-card-text>

    <!-- Existing agent actions -->
    <v-card-actions>
      <v-btn icon @click="editAgent(agent)">
        <v-icon>mdi-pencil</v-icon>
      </v-btn>
      <v-btn icon @click="viewAgentDetails(agent)">
        <v-icon>mdi-information</v-icon>
      </v-btn>
      <v-spacer />
      <v-chip :color="agentStatusColor" size="small">
        {{ agent.status }}
      </v-chip>
    </v-card-actions>

    <!-- Instructions Copied Snackbar -->
    <v-snackbar
      v-model="showCopiedSnackbar"
      timeout="2000"
      color="success"
    >
      <v-icon class="mr-2">mdi-check</v-icon>
      Project instructions copied to clipboard
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/services/api'
import { useWebSocket } from '@/composables/useWebSocket'

const props = defineProps({
  agent: {
    type: Object,
    required: true
  }
})

const projectJobs = ref([])
const loadingInstructions = ref({})
const showCopiedSnackbar = ref(false)

const agentStatusColor = computed(() => {
  switch (props.agent.status) {
    case 'active': return 'success'
    case 'busy': return 'warning'
    case 'offline': return 'grey'
    default: return 'info'
  }
})

const agentIcon = computed(() => {
  switch (props.agent.agent_type) {
    case 'claude': return 'mdi-robot'
    case 'codex': return 'mdi-code-braces'
    case 'gemini': return 'mdi-google'
    default: return 'mdi-robot-outline'
  }
})

function getStatusColor(status) {
  switch (status) {
    case 'pending': return 'grey'
    case 'acknowledged': return 'info'
    case 'in_progress': return 'primary'
    case 'completed': return 'success'
    case 'failed': return 'error'
    default: return 'grey'
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'pending': return 'mdi-clock-outline'
    case 'acknowledged': return 'mdi-check'
    case 'in_progress': return 'mdi-play-circle'
    case 'completed': return 'mdi-check-circle'
    case 'failed': return 'mdi-alert-circle'
    default: return 'mdi-help-circle'
  }
}

function getJobStatusColor(jobs) {
  if (jobs.some(j => j.status === 'in_progress')) return 'primary'
  if (jobs.some(j => j.status === 'failed')) return 'error'
  if (jobs.every(j => j.status === 'completed')) return 'success'
  return 'grey'
}

function truncate(text, length) {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

async function fetchAgentJobs() {
  try {
    const response = await api.agentJobs.getByAgentAndProject({
      agent_id: props.agent.id,
      status: 'pending,acknowledged,in_progress'  // Only active jobs
    })
    projectJobs.value = response.data
  } catch (error) {
    console.error('[AGENT CARD] Error fetching jobs:', error)
  }
}

async function copyProjectInstructions(projectId) {
  loadingInstructions.value[projectId] = true

  try {
    const response = await api.projects.getInstructions(projectId, props.agent.id)
    const instructions = response.data.instructions

    // Copy to clipboard
    await navigator.clipboard.writeText(instructions)

    showCopiedSnackbar.value = true
  } catch (error) {
    console.error('[AGENT CARD] Error copying instructions:', error)
  } finally {
    loadingInstructions.value[projectId] = false
  }
}

function viewJobDetails(job) {
  // Navigate to job details view or open dialog
  console.log('View job:', job)
}

// WebSocket integration for real-time job updates
const { socket } = useWebSocket()

watch(socket, (newSocket) => {
  if (newSocket) {
    newSocket.on('job:status_changed', handleJobUpdate)
    newSocket.on('job:completed', handleJobUpdate)
    newSocket.on('job:failed', handleJobUpdate)
  }
})

function handleJobUpdate(data) {
  // Refresh jobs if this agent is affected
  if (data.agent_id === props.agent.id) {
    fetchAgentJobs()
  }
}

onMounted(() => {
  fetchAgentJobs()
})
</script>

<style scoped>
.agent-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
```

## Phase 3: API Service Integration (1 hour)

**File**: `frontend/src/services/api.js`

**Add Methods**:

```javascript
agentJobs: {
  // ... existing methods
  getByAgentAndProject: (params) => apiClient.get('/api/v1/agent-jobs/by-agent-and-project', { params })
},
projects: {
  // ... existing methods
  getInstructions: (projectId, agentId = null) => {
    const params = agentId ? { agent_id: agentId } : {}
    return apiClient.get(`/api/v1/projects/${projectId}/instructions`, { params })
  }
}
```

## Phase 4: Testing (2 hours)

**Test Coverage**:

1. **Backend Tests**:
   - Test get_agent_jobs_by_project with various filters
   - Test get_project_instructions with and without agent_id
   - Test multi-tenant isolation
   - Test error cases (invalid IDs, no permission)

2. **Frontend Tests**:
   - Test EnhancedAgentCard renders correctly
   - Test job list displays and updates
   - Test copy instructions functionality
   - Test WebSocket updates trigger refresh
   - Test empty state (no jobs)

3. **Integration Tests**:
   - Create job → Verify appears in agent card
   - Update job status → Verify card updates
   - Complete job → Verify card updates
   - Copy instructions → Verify clipboard contains correct content

---

# Files to Modify

1. **api/endpoints/agent_jobs.py** (+60 lines)
   - Add get_agent_jobs_by_project endpoint
   - Group jobs by project

2. **api/endpoints/projects.py** (+80 lines)
   - Add get_project_instructions endpoint
   - Generate formatted instructions

3. **frontend/src/components/agents/EnhancedAgentCard.vue** (+250 lines)
   - Add project jobs section
   - Add copy instructions functionality
   - WebSocket integration

4. **frontend/src/services/api.js** (+10 lines)
   - Add getByAgentAndProject method
   - Add getInstructions method

5. **tests/api/test_agent_jobs_endpoints.py** (+50 lines)
   - Test new endpoints

6. **tests/frontend/test_enhanced_agent_card.spec.js** (~50 lines, NEW FILE)
   - Component tests

**Total**: ~500 lines across 6 files (1 new, 5 modified)

---

# Success Criteria

## Functional Requirements
- Agent cards display project-specific jobs
- Jobs grouped by project with expandable sections
- Job status displayed with color coding and icons
- Progress bars shown for in_progress jobs
- One-click copy of project instructions
- Instructions include project context, tasks, and field priority
- Real-time job updates via WebSocket
- Multi-tenant isolation enforced

## User Experience Requirements
- Clean, intuitive card layout
- Smooth expand/collapse animations
- Clear visual hierarchy
- Loading states for async operations
- Success feedback for copy action
- Empty state when no jobs

## Technical Requirements
- Efficient querying (no N+1 problems)
- Proper clipboard API usage
- WebSocket listeners properly cleaned up
- Responsive design
- Accessible (ARIA labels, keyboard navigation)

---

# Related Handovers

- **Handover 0019**: Agent Job Management (DEPENDS ON)
  - Provides job infrastructure

- **Handover 0048**: Field Priority Configuration (DEPENDS ON)
  - Instructions include field priority settings

- **Handover 0050**: Single Active Product Architecture (RELATES TO)
  - Jobs scoped to active product

- **Handover 0063**: Per-Agent Tool Selection UI (COMPLEMENTS)
  - Shows which tool each agent uses

---

# Risk Assessment

**Complexity**: MEDIUM (complex UI, WebSocket coordination)
**Risk**: LOW (additive changes only)
**Breaking Changes**: None
**Performance Impact**: Minimal (queries optimized)

---

# Timeline Estimate

**Phase 1**: 2 hours (Backend endpoints)
**Phase 2**: 3-4 hours (Enhanced card component)
**Phase 3**: 1 hour (API integration)
**Phase 4**: 2 hours (Testing)

**Total**: 8-10 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: CRITICAL (improves agent visibility and coordination)

---

**End of Handover 0062**
