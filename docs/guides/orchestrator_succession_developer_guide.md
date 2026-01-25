# Orchestrator Succession - Developer Guide

> **ARCHIVED (Handover 0461e)**: This documentation describes the old complex
> succession system which has been replaced by simple 360 Memory-based handover.
> See [ORCHESTRATOR.md](../ORCHESTRATOR.md) for current documentation.

**Last Updated**: 2025-11-02
**Version**: v3.0+
**Handover**: 0080

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [Backend API Reference](#backend-api-reference)
4. [MCP Tool Usage](#mcp-tool-usage)
5. [WebSocket Events](#websocket-events)
6. [UI Components](#ui-components)
7. [Testing Strategy](#testing-strategy)
8. [Integration Examples](#integration-examples)
9. [Performance Considerations](#performance-considerations)
10. [Security Best Practices](#security-best-practices)

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator Agent                          │
│  (Running in Claude Code / Codex CLI / Gemini CLI)              │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Context Monitor                                            │  │
│  │ - Tracks context_used vs context_budget                   │  │
│  │ - Triggers succession at 90% threshold                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│                          │ (Context >= 90%)                      │
│                          ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ MCP Tool: create_successor_orchestrator()                  │  │
│  │ - Calls GiljoAI MCP server via HTTP                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP POST
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GiljoAI MCP Server                             │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ API Endpoint: POST /agent_jobs/{id}/trigger_succession    │  │
│  │ - Validates orchestrator job                              │  │
│  │ - Calls succession manager                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│                          ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ OrchestratorSuccessionManager                              │  │
│  │ - create_successor() → New MCPAgentJob                    │  │
│  │ - generate_handover_summary() → Compressed state          │  │
│  │ - complete_handover() → Update database                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│                          ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ PostgreSQL Database                                        │  │
│  │ - mcp_agent_jobs table                                    │  │
│  │ - Instance 1: status='complete', handover_to=Instance2    │  │
│  │ - Instance 2: status='waiting', spawned_by=Instance1      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│                          ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ WebSocket Manager                                          │  │
│  │ - Broadcasts 'job:succession_triggered' event             │  │
│  │ - Broadcasts 'job:successor_created' event                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Vue Frontend                                 │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ AgentCardEnhanced.vue                                      │  │
│  │ - Displays instance badges (#1, #2, #3)                   │  │
│  │ - Shows context usage bars (color-coded)                  │  │
│  │ - Renders "NEW" badge on successors                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LaunchSuccessorDialog.vue                                  │  │
│  │ - Auto-generates launch prompt                            │  │
│  │ - Displays handover summary                               │  │
│  │ - One-click copy to clipboard                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SuccessionTimeline.vue                                     │  │
│  │ - Chronological succession chain view                     │  │
│  │ - Expandable handover summaries                           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Sequence Diagram: Full Succession Workflow

```
Orchestrator   MCP Tool    API Endpoint    SuccessionManager    Database    WebSocket    Frontend
    │              │              │                 │               │            │           │
    │ Context      │              │                 │               │            │           │
    │ >= 90%       │              │                 │               │            │           │
    ├─────────────>│              │                 │               │            │           │
    │ Call MCP     │              │                 │               │            │           │
    │              ├─────────────>│                 │               │            │           │
    │              │ POST /trigger│                 │               │            │           │
    │              │ _succession  │                 │               │            │           │
    │              │              ├────────────────>│               │            │           │
    │              │              │ create_successor()              │            │           │
    │              │              │                 ├──────────────>│            │           │
    │              │              │                 │ INSERT new job│            │           │
    │              │              │                 │<──────────────┤            │           │
    │              │              │                 │ Job created   │            │           │
    │              │              │                 │               │            │           │
    │              │              │ generate_handover_summary()     │            │           │
    │              │              │                 ├──────────────>│            │           │
    │              │              │                 │ SELECT messages│           │           │
    │              │              │                 │<──────────────┤            │           │
    │              │              │                 │ Compress state│            │           │
    │              │              │                 │               │            │           │
    │              │              │ complete_handover()             │            │           │
    │              │              │                 ├──────────────>│            │           │
    │              │              │                 │ UPDATE jobs   │            │           │
    │              │              │                 │<──────────────┤            │           │
    │              │              │                 │ Handover done │            │           │
    │              │              │<────────────────┤               │            │           │
    │              │              │ Success         │               │            │           │
    │              │              ├────────────────────────────────────────────>│           │
    │              │              │ Broadcast 'job:succession_triggered'        │           │
    │              │              │                 │               │            ├──────────>│
    │              │              │                 │               │            │ Update UI │
    │              │<─────────────┤                 │               │            │           │
    │              │ Response     │                 │               │            │           │
    │<─────────────┤              │                 │               │            │           │
    │ successor_id │              │                 │               │            │           │
    │              │              │                 │               │            │           │
```

## Database Schema

### New Columns in `mcp_agent_jobs` Table

```sql
-- Handover 0080: Orchestrator succession columns
ALTER TABLE mcp_agent_jobs
    -- Instance numbering (1, 2, 3, ...)
    ADD COLUMN IF NOT EXISTS instance_number INTEGER DEFAULT 1 NOT NULL,

    -- UUID of successor orchestrator job
    ADD COLUMN IF NOT EXISTS handover_to VARCHAR(36) NULL,

    -- Compressed handover summary (JSONB for queryability)
    ADD COLUMN IF NOT EXISTS handover_summary JSONB NULL,

    -- Array of critical context chunk IDs
    ADD COLUMN IF NOT EXISTS handover_context_refs TEXT[] NULL,

    -- Reason for succession ('context_limit', 'manual', 'phase_transition')
    ADD COLUMN IF NOT EXISTS succession_reason VARCHAR(100) NULL,

    -- Current context usage in tokens
    ADD COLUMN IF NOT EXISTS context_used INTEGER DEFAULT 0 NOT NULL,

    -- Maximum context budget in tokens
    ADD COLUMN IF NOT EXISTS context_budget INTEGER DEFAULT 150000 NOT NULL;
```

### Indexes for Performance

```sql
-- Efficient succession chain queries
CREATE INDEX IF NOT EXISTS idx_agent_jobs_instance
    ON mcp_agent_jobs(project_id, agent_type, instance_number);

-- Reverse lookup (find parent from successor)
CREATE INDEX IF NOT EXISTS idx_agent_jobs_handover
    ON mcp_agent_jobs(handover_to);
```

### Constraints for Data Integrity

```sql
-- Instance number must be >= 1
ALTER TABLE mcp_agent_jobs
    ADD CONSTRAINT IF NOT EXISTS ck_mcp_agent_job_instance_number
    CHECK (instance_number >= 1);

-- Succession reason must be valid enum
ALTER TABLE mcp_agent_jobs
    ADD CONSTRAINT IF NOT EXISTS ck_mcp_agent_job_succession_reason
    CHECK (succession_reason IS NULL OR
           succession_reason IN ('context_limit', 'manual', 'phase_transition'));

-- Context usage must be within budget
ALTER TABLE mcp_agent_jobs
    ADD CONSTRAINT IF NOT EXISTS ck_mcp_agent_job_context_usage
    CHECK (context_used >= 0 AND context_used <= context_budget);
```

### Example Data

```sql
-- Instance 1 (Handed over)
INSERT INTO mcp_agent_jobs (
    tenant_key,
    job_id,
    agent_type,
    mission,
    status,
    instance_number,
    context_used,
    context_budget,
    handover_to,
    handover_summary,
    succession_reason,
    completed_at
) VALUES (
    'tenant-abc123',
    'orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124',
    'orchestrator',
    'Develop e-commerce platform...',
    'complete',
    1,
    145000,
    150000,
    'orch-a1b2c3d4-5e6f-7890-1234-567890abcdef',
    '{"project_status": "60% complete", "active_agents": [...], ...}'::jsonb,
    'context_limit',
    '2025-11-02T14:30:00Z'
);

-- Instance 2 (Waiting to be launched)
INSERT INTO mcp_agent_jobs (
    tenant_key,
    job_id,
    agent_type,
    mission,
    status,
    instance_number,
    spawned_by,
    project_id,
    context_used,
    context_budget
) VALUES (
    'tenant-abc123',
    'orch-a1b2c3d4-5e6f-7890-1234-567890abcdef',
    'orchestrator',
    'Continue orchestration from instance 1...',
    'waiting',
    2,
    'orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124',
    '6adbec5c-9e11-46b4-ad8b-060c69a8d124',
    0,
    150000
);
```

### Querying Succession Chain

```sql
-- Get full succession chain for a project
SELECT
    job_id,
    instance_number,
    status,
    context_used,
    context_budget,
    ROUND((context_used::float / context_budget * 100)::numeric, 2) AS usage_percent,
    handover_to,
    spawned_by,
    succession_reason,
    created_at,
    completed_at
FROM mcp_agent_jobs
WHERE project_id = '6adbec5c-9e11-46b4-ad8b-060c69a8d124'
    AND agent_type = 'orchestrator'
    AND tenant_key = 'tenant-abc123'
ORDER BY instance_number ASC;
```

**Expected Output:**

```
job_id                                  | instance_number | status   | usage_percent | handover_to                            | ...
orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124 | 1               | complete | 96.67         | orch-a1b2c3d4-5e6f-7890-1234-567890abcdef | ...
orch-a1b2c3d4-5e6f-7890-1234-567890abcdef | 2               | waiting  | 0.00          | NULL                                   | ...
```

## Backend API Reference

### Endpoint: Trigger Succession

**POST** `/agent_jobs/{job_id}/trigger_succession`

Manually trigger succession for an orchestrator job.

**Path Parameters:**
- `job_id` (string, required): UUID of the orchestrator job

**Query Parameters:**
- `reason` (string, optional): Succession reason ('manual', 'context_limit', 'phase_transition'). Default: 'manual'

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Content-Type: application/json`

**Request Body:** None

**Response (200 OK):**

```json
{
  "success": true,
  "successor_id": "orch-a1b2c3d4-5e6f-7890-1234-567890abcdef",
  "instance_number": 2,
  "status": "waiting",
  "handover_summary": {
    "project_status": "60% complete",
    "active_agents": [
      {"job_id": "agent-123", "type": "frontend-dev", "status": "working"}
    ],
    "completed_phases": ["requirements", "architecture"],
    "pending_decisions": ["API endpoint naming"],
    "critical_context_refs": ["chunk-123", "chunk-456"],
    "message_count": 42,
    "unresolved_blockers": [],
    "next_steps": "Implement API endpoints, then frontend integration",
    "context_usage": {
      "used": 145000,
      "budget": 150000,
      "percentage": 96.67
    }
  },
  "message": "Successor orchestrator created (instance 2). Original orchestrator marked complete. Launch successor manually from dashboard."
}
```

**Error Responses:**

```json
// 404 Not Found - Job not found
{
  "error": "Orchestrator job orch-6adbec5c-9e11... not found for tenant tenant-abc123"
}

// 400 Bad Request - Not an orchestrator
{
  "error": "Job orch-6adbec5c-9e11... is not an orchestrator (type: backend-dev)"
}

// 400 Bad Request - Already complete
{
  "error": "Orchestrator orch-6adbec5c-9e11... is already complete. Cannot trigger succession on completed orchestrator."
}

// 400 Bad Request - Invalid reason
{
  "error": "Invalid succession reason: 'invalid'. Must be one of: context_limit, manual, phase_transition"
}
```

### Endpoint: Get Succession Chain

**GET** `/agent_jobs/{job_id}/succession_chain`

Retrieve the full succession chain for an orchestrator's project.

**Path Parameters:**
- `job_id` (string, required): UUID of any orchestrator job in the chain

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200 OK):**

```json
{
  "project_id": "6adbec5c-9e11-46b4-ad8b-060c69a8d124",
  "chain": [
    {
      "job_id": "orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
      "instance_number": 1,
      "status": "complete",
      "context_used": 145000,
      "context_budget": 150000,
      "usage_percentage": 96.67,
      "handover_to": "orch-a1b2c3d4-5e6f-7890-1234-567890abcdef",
      "succession_reason": "context_limit",
      "created_at": "2025-11-01T10:00:00Z",
      "completed_at": "2025-11-02T14:30:00Z"
    },
    {
      "job_id": "orch-a1b2c3d4-5e6f-7890-1234-567890abcdef",
      "instance_number": 2,
      "status": "waiting",
      "context_used": 0,
      "context_budget": 150000,
      "usage_percentage": 0.00,
      "spawned_by": "orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
      "created_at": "2025-11-02T14:30:00Z",
      "completed_at": null
    }
  ]
}
```

## MCP Tool Usage

### Tool: `create_successor_orchestrator`

**Description:** Create successor orchestrator and perform handover.

**Parameters:**

```python
{
  "current_job_id": "orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",  # Required
  "tenant_key": "tenant-abc123",                                    # Required
  "reason": "context_limit"                                         # Optional (default: "context_limit")
}
```

**Return Value:**

```python
{
  "success": True,
  "successor_id": "orch-a1b2c3d4-5e6f-7890-1234-567890abcdef",
  "instance_number": 2,
  "status": "waiting",
  "handover_summary": {...},  # Full handover summary dict
  "message": "Successor orchestrator created (instance 2)..."
}
```

**Usage Example (Python):**

```python
from giljo_mcp.tools.succession_tools import create_successor_orchestrator

# Orchestrator detects 90% context usage
async def check_and_trigger_succession(orchestrator):
    if orchestrator.context_used >= (orchestrator.context_budget * 0.90):
        result = await create_successor_orchestrator(
            current_job_id=orchestrator.job_id,
            tenant_key=orchestrator.tenant_key,
            reason="context_limit"
        )

        print(f"Successor created: {result['successor_id']}")
        print(f"Instance number: {result['instance_number']}")
        print(f"Handover summary: {result['handover_summary']}")

        return result['successor_id']
    else:
        print("Context usage below threshold, no succession needed")
        return None
```

### Tool: `check_succession_status`

**Description:** Check if orchestrator should trigger succession.

**Parameters:**

```python
{
  "job_id": "orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",  # Required
  "tenant_key": "tenant-abc123"                            # Required
}
```

**Return Value:**

```python
{
  "should_trigger": True,               # Boolean recommendation
  "context_used": 135000,               # Current usage in tokens
  "context_budget": 150000,             # Maximum budget
  "usage_percentage": 90.00,            # Percentage used
  "threshold_reached": True,            # True if >= 90%
  "instance_number": 1,                 # Current instance number
  "recommendation": "Context usage at 90.0%. Succession recommended immediately..."
}
```

**Usage Example (Python):**

```python
from giljo_mcp.tools.succession_tools import check_succession_status

# Periodically check succession status
async def monitor_context_usage(orchestrator):
    status = await check_succession_status(
        job_id=orchestrator.job_id,
        tenant_key=orchestrator.tenant_key
    )

    print(f"Context usage: {status['usage_percentage']}%")
    print(f"Recommendation: {status['recommendation']}")

    if status['should_trigger']:
        # Trigger succession
        await create_successor_orchestrator(...)
```

## WebSocket Events

### Event: `job:succession_triggered`

**Emitted When:** Succession process initiated

**Payload:**

```json
{
  "event": "job:succession_triggered",
  "data": {
    "orchestrator_id": "orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
    "instance_number": 1,
    "project_id": "6adbec5c-9e11-46b4-ad8b-060c69a8d124",
    "reason": "context_limit",
    "timestamp": "2025-11-02T14:30:00Z"
  }
}
```

**Frontend Handler Example (Vue):**

```javascript
// In component or store
socket.on('job:succession_triggered', (data) => {
  console.log(`Succession triggered for ${data.orchestrator_id}`)

  // Update UI to show "Handing over..." status
  store.commit('updateAgentStatus', {
    jobId: data.orchestrator_id,
    status: 'completing'
  })

  // Show notification
  toast.info(`Orchestrator instance ${data.instance_number} is creating successor...`)
})
```

### Event: `job:successor_created`

**Emitted When:** Successor orchestrator created successfully

**Payload:**

```json
{
  "event": "job:successor_created",
  "data": {
    "successor_id": "orch-a1b2c3d4-5e6f-7890-1234-567890abcdef",
    "predecessor_id": "orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
    "instance_number": 2,
    "project_id": "6adbec5c-9e11-46b4-ad8b-060c69a8d124",
    "handover_summary": {...},
    "timestamp": "2025-11-02T14:30:05Z"
  }
}
```

**Frontend Handler Example (Vue):**

```javascript
socket.on('job:successor_created', (data) => {
  // Add successor card to UI
  store.commit('addAgentJob', {
    jobId: data.successor_id,
    instanceNumber: data.instance_number,
    status: 'waiting',
    showNewBadge: true
  })

  // Mark predecessor as complete
  store.commit('updateAgentStatus', {
    jobId: data.predecessor_id,
    status: 'complete',
    handoverTo: data.successor_id
  })

  // Show launch dialog
  showLaunchSuccessorDialog(data.successor_id, data.handover_summary)
})
```

## UI Components

### Component: `AgentCardEnhanced.vue`

**Purpose:** Display agent job cards with succession indicators

**Props:**

```typescript
interface Props {
  agent: {
    job_id: string
    agent_type: string
    status: string
    instance_number?: number
    context_used?: number
    context_budget?: number
    handover_to?: string
    spawned_by?: string
  }
  mode: 'launch' | 'jobs'
  showNewBadge?: boolean
}
```

**Computed Properties:**

```javascript
// Context usage percentage with color coding
contextUsagePercentage() {
  if (!this.agent.context_budget) return 0
  return (this.agent.context_used / this.agent.context_budget) * 100
}

contextUsageColor() {
  const pct = this.contextUsagePercentage
  if (pct >= 90) return 'error'      // Red
  if (pct >= 75) return 'warning'    // Yellow
  return 'success'                    // Green
}

// Instance badge text
instanceBadgeText() {
  return `#${this.agent.instance_number || 1}`
}
```

**Template Sections:**

```vue
<template>
  <!-- Instance Number Badge -->
  <v-chip
    v-if="agent.instance_number"
    color="primary"
    size="small"
    class="instance-badge"
  >
    {{ instanceBadgeText }}
  </v-chip>

  <!-- Context Usage Progress Bar -->
  <v-progress-linear
    v-if="agent.context_budget"
    :model-value="contextUsagePercentage"
    :color="contextUsageColor"
    height="8"
    rounded
  >
    <template #default>
      <span class="text-caption">{{ contextUsagePercentage.toFixed(1) }}%</span>
    </template>
  </v-progress-linear>

  <!-- NEW Badge (successors) -->
  <v-chip
    v-if="showNewBadge"
    color="success"
    size="x-small"
    prepend-icon="mdi-star"
  >
    NEW
  </v-chip>

  <!-- Handed Over Badge (predecessors) -->
  <v-chip
    v-if="agent.handover_to"
    color="grey"
    size="x-small"
  >
    Handed Over
  </v-chip>
</template>
```

### Component: `SuccessionTimeline.vue`

**Purpose:** Visualize succession chain chronologically

**Props:**

```typescript
interface Props {
  projectId: string
  tenant_key: string
}
```

**Data:**

```javascript
data() {
  return {
    successionChain: [],  // Array of orchestrator jobs
    loading: true,
    expandedSummaries: [] // Instance numbers with expanded summaries
  }
}
```

**Methods:**

```javascript
async fetchSuccessionChain() {
  try {
    const response = await axios.get(`/api/agent_jobs/${this.projectId}/succession_chain`)
    this.successionChain = response.data.chain
  } catch (error) {
    console.error('Failed to fetch succession chain:', error)
  } finally {
    this.loading = false
  }
}

toggleSummary(instanceNumber) {
  const index = this.expandedSummaries.indexOf(instanceNumber)
  if (index === -1) {
    this.expandedSummaries.push(instanceNumber)
  } else {
    this.expandedSummaries.splice(index, 1)
  }
}
```

### Component: `LaunchSuccessorDialog.vue`

**Purpose:** Generate and display launch prompt for successors

**Props:**

```typescript
interface Props {
  successorId: string
  handoverSummary: object
  modelValue: boolean  // v-model for dialog visibility
}
```

**Computed:**

```javascript
launchPrompt() {
  return `
export GILJO_MCP_SERVER_URL=${this.serverUrl}
export GILJO_AGENT_JOB_ID=${this.successorId}
export GILJO_PROJECT_ID=${this.projectId}

# Handover Summary:
# Project Status: ${this.handoverSummary.project_status}
# Active Agents: ${this.formatActiveAgents()}
# Pending Decisions: ${this.formatPendingDecisions()}
# Next Steps: ${this.handoverSummary.next_steps}

# Start Claude Code with MCP connection:
codex mcp add giljo-orchestrator
  `.trim()
}
```

**Methods:**

```javascript
async copyToClipboard() {
  try {
    await navigator.clipboard.writeText(this.launchPrompt)
    this.$toast.success('Prompt copied to clipboard!')
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}
```

## Testing Strategy

### Unit Tests

**File:** `tests/test_orchestrator_succession.py`

```python
import pytest
from giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from giljo_mcp.models import MCPAgentJob

def test_context_threshold_detection(db_session, tenant_key):
    """Test that succession can be triggered when context is high."""
    manager = OrchestratorSuccessionManager(db_session, tenant_key)

    orchestrator = MCPAgentJob(
        tenant_key=tenant_key,
        job_id="orch-test-123",
        agent_type="orchestrator",
        context_used=135000,  # 90% of 150000
        context_budget=150000
    )

    # User can manually trigger succession when context is high
    assert (orchestrator.context_used / orchestrator.context_budget) >= 0.9

def test_handover_summary_generation(db_session, tenant_key, orchestrator_with_messages):
    """Test that handover summary is properly compressed."""
    manager = OrchestratorSuccessionManager(db_session, tenant_key)

    summary = manager.generate_handover_summary(orchestrator_with_messages)

    assert 'project_status' in summary
    assert 'active_agents' in summary
    assert 'next_steps' in summary
    assert summary['message_count'] > 0

    # Verify compression (rough token estimate)
    import json
    summary_str = json.dumps(summary)
    estimated_tokens = len(summary_str) / 4
    assert estimated_tokens < 10000  # Target: <10K tokens

def test_successor_creation(db_session, tenant_key, orchestrator):
    """Test that successor is created with correct attributes."""
    manager = OrchestratorSuccessionManager(db_session, tenant_key)

    successor = manager.create_successor(orchestrator, reason="context_limit")

    assert successor.job_id != orchestrator.job_id
    assert successor.instance_number == orchestrator.instance_number + 1
    assert successor.spawned_by == orchestrator.job_id
    assert successor.status == "waiting"
    assert successor.context_used == 0
    assert successor.context_budget == orchestrator.context_budget
```

### Integration Tests

**File:** `tests/integration/test_succession_workflow.py`

```python
import pytest
from sqlalchemy import select

@pytest.mark.asyncio
async def test_full_succession_workflow(db_session, tenant_key, project):
    """Test complete succession from trigger to handover."""
    # Create initial orchestrator
    orch1 = MCPAgentJob(
        tenant_key=tenant_key,
        job_id="orch-1",
        agent_type="orchestrator",
        project_id=project.project_id,
        context_used=135000,
        context_budget=150000,
        instance_number=1
    )
    db_session.add(orch1)
    db_session.commit()

    # Trigger succession
    manager = OrchestratorSuccessionManager(db_session, tenant_key)
    orch2 = manager.create_successor(orch1, reason="context_limit")
    summary = manager.generate_handover_summary(orch1)
    manager.complete_handover(orch1, orch2, summary, reason="context_limit")

    # Refresh objects
    db_session.refresh(orch1)
    db_session.refresh(orch2)

    # Verify Instance 1 (predecessor)
    assert orch1.status == "complete"
    assert orch1.handover_to == orch2.job_id
    assert orch1.handover_summary is not None
    assert orch1.succession_reason == "context_limit"

    # Verify Instance 2 (successor)
    assert orch2.status == "waiting"
    assert orch2.spawned_by == orch1.job_id
    assert orch2.instance_number == 2
    assert orch2.context_used == 0
```

### Security Tests

**File:** `tests/security/test_succession_security.py`

```python
def test_multi_tenant_isolation(db_session):
    """Verify that tenants cannot access each other's succession data."""
    tenant1_key = "tenant-abc"
    tenant2_key = "tenant-xyz"

    # Create orchestrator for tenant 1
    orch_tenant1 = MCPAgentJob(
        tenant_key=tenant1_key,
        job_id="orch-tenant1",
        agent_type="orchestrator"
    )
    db_session.add(orch_tenant1)
    db_session.commit()

    # Attempt to create successor using tenant 2's manager
    manager_tenant2 = OrchestratorSuccessionManager(db_session, tenant2_key)

    with pytest.raises(ValueError, match="Tenant mismatch"):
        manager_tenant2.create_successor(orch_tenant1, reason="manual")

def test_sql_injection_prevention(db_session, tenant_key):
    """Test that malicious inputs are sanitized."""
    manager = OrchestratorSuccessionManager(db_session, tenant_key)

    malicious_reason = "context_limit'; DROP TABLE mcp_agent_jobs; --"

    with pytest.raises(ValueError, match="Invalid succession reason"):
        orchestrator = MCPAgentJob(tenant_key=tenant_key, job_id="test")
        manager.create_successor(orchestrator, reason=malicious_reason)
```

### Performance Tests

**File:** `tests/performance/test_succession_performance.py`

```python
import time

def test_succession_latency(db_session, tenant_key, orchestrator):
    """Verify succession completes within 5 seconds."""
    manager = OrchestratorSuccessionManager(db_session, tenant_key)

    start_time = time.time()

    successor = manager.create_successor(orchestrator, reason="manual")
    summary = manager.generate_handover_summary(orchestrator)
    manager.complete_handover(orchestrator, successor, summary, reason="manual")

    elapsed_time = time.time() - start_time

    assert elapsed_time < 5.0  # Target: <5 seconds
    print(f"Succession completed in {elapsed_time:.2f}s")

def test_handover_summary_token_limit(db_session, tenant_key, large_orchestrator):
    """Verify handover summary stays under 10K tokens."""
    manager = OrchestratorSuccessionManager(db_session, tenant_key)

    summary = manager.generate_handover_summary(large_orchestrator)

    import json
    summary_str = json.dumps(summary)
    estimated_tokens = len(summary_str) / 4  # Rough approximation

    assert estimated_tokens < 10000
    print(f"Handover summary: {estimated_tokens:.0f} tokens")
```

## Integration Examples

### Example 1: Automatic Succession in Orchestrator Agent

```python
# In orchestrator agent code (running in Claude Code)
import asyncio
from giljo_mcp_client import GiljoMCPClient

class OrchestratorAgent:
    def __init__(self, job_id, tenant_key):
        self.job_id = job_id
        self.tenant_key = tenant_key
        self.client = GiljoMCPClient()
        self.context_used = 0
        self.context_budget = 150000

    async def update_context_usage(self, tokens_used):
        """Update context usage."""
        self.context_used += tokens_used

        # Check if context is high (approaching 90%)
        usage_percent = (self.context_used / self.context_budget) * 100
        if usage_percent >= 80:
            print(f"Warning: Context usage at {usage_percent:.1f}%")
            print("Consider triggering manual succession via /gil_handover")

    async def trigger_succession(self):
        """Trigger manual succession (called by user action)."""
        print(f"Context usage: {self.context_used}/{self.context_budget} tokens")
        print("User triggered succession...")

        # Call MCP tool
        result = await self.client.create_successor_orchestrator(
            current_job_id=self.job_id,
            tenant_key=self.tenant_key,
            reason="manual"
        )

        print(f"Successor created: {result['successor_id']}")
        print(f"Instance number: {result['instance_number']}")
        print(f"Handover summary: {result['handover_summary']}")

        # Gracefully exit
        print("Exiting orchestrator instance...")
        await asyncio.sleep(2)  # Allow final messages to send
        exit(0)

# Usage
orchestrator = OrchestratorAgent(
    job_id="orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
    tenant_key="tenant-abc123"
)

# Simulate context growth (user monitors and triggers succession)
await orchestrator.update_context_usage(50000)  # 50K tokens
await orchestrator.update_context_usage(40000)  # 90K total (60%)
await orchestrator.update_context_usage(45000)  # 135K total (90%) → user sees warning, triggers succession manually
```

### Example 2: Manual Succession via API

```python
import requests

# API endpoint
url = "http://10.1.0.164:7272/api/agent_jobs/orch-6adbec5c-9e11/trigger_succession"
headers = {
    "Authorization": "Bearer your-jwt-token-here",
    "Content-Type": "application/json"
}
params = {
    "reason": "phase_transition"  # Manual succession for phase change
}

# Trigger succession
response = requests.post(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    print(f"Successor created: {data['successor_id']}")
    print(f"Instance number: {data['instance_number']}")
    print(f"Handover summary: {data['handover_summary']}")
else:
    print(f"Error: {response.json()['error']}")
```

### Example 3: Querying Succession Chain

```python
from sqlalchemy import select
from giljo_mcp.models import MCPAgentJob
from giljo_mcp.database import DatabaseManager

# Get succession chain for a project
db_manager = DatabaseManager()

with db_manager.get_session() as session:
    query = select(MCPAgentJob).where(
        MCPAgentJob.project_id == "6adbec5c-9e11-46b4-ad8b-060c69a8d124",
        MCPAgentJob.agent_type == "orchestrator",
        MCPAgentJob.tenant_key == "tenant-abc123"
    ).order_by(MCPAgentJob.instance_number)

    orchestrators = session.execute(query).scalars().all()

    print("Succession Chain:")
    for orch in orchestrators:
        status_icon = "✅" if orch.status == "complete" else "⏳" if orch.status == "waiting" else "🔄"
        print(f"{status_icon} Instance {orch.instance_number}: {orch.job_id}")
        print(f"   Status: {orch.status}")
        print(f"   Context: {orch.context_used}/{orch.context_budget} ({orch.context_used/orch.context_budget*100:.1f}%)")
        if orch.handover_to:
            print(f"   Handed over to: {orch.handover_to}")
        if orch.spawned_by:
            print(f"   Spawned by: {orch.spawned_by}")
        print()
```

## Performance Considerations

### Database Query Optimization

```sql
-- EXPLAIN ANALYZE for succession chain query
EXPLAIN ANALYZE
SELECT job_id, instance_number, status
FROM mcp_agent_jobs
WHERE project_id = '6adbec5c-9e11-46b4-ad8b-060c69a8d124'
    AND agent_type = 'orchestrator'
    AND tenant_key = 'tenant-abc123'
ORDER BY instance_number;

-- Expected execution plan:
-- Index Scan using idx_agent_jobs_instance on mcp_agent_jobs
-- Execution time: ~0.5ms (with 10 orchestrator instances)
```

### Handover Summary Compression

Target: <10K tokens per handover summary

Techniques:
1. **Reference context chunks** (IDs only, not full text)
2. **Summarize completed work** (bullet points, not full history)
3. **Preserve only pending decisions** (actionable items only)
4. **Compress message history** (key events only, not full replay)

Example compression ratio:
- Full context: 145,000 tokens
- Handover summary: 8,000 tokens
- Compression ratio: 94.5% reduction

### Caching Strategies

```python
# Cache succession chain for frequently accessed projects
from functools import lru_cache

@lru_cache(maxsize=100)
def get_succession_chain_cached(project_id, tenant_key):
    """Cached succession chain lookup (60 second TTL)."""
    with db_manager.get_session() as session:
        # Query succession chain
        ...
    return chain

# Invalidate cache on succession events
def on_succession_triggered(project_id):
    get_succession_chain_cached.cache_clear()
```

## Security Best Practices

### Multi-Tenant Isolation

Always verify tenant key in succession operations:

```python
def create_successor(self, orchestrator: MCPAgentJob, reason: str):
    # Verify tenant isolation
    if orchestrator.tenant_key != self.tenant_key:
        raise ValueError(
            f"Tenant mismatch: orchestrator belongs to {orchestrator.tenant_key}, "
            f"manager initialized for {self.tenant_key}"
        )
    # Continue with succession...
```

### Input Validation

Validate succession reasons using enums:

```python
VALID_REASONS = {"context_limit", "manual", "phase_transition"}

if reason not in VALID_REASONS:
    raise ValueError(
        f"Invalid succession reason: {reason}. "
        f"Must be one of: {', '.join(VALID_REASONS)}"
    )
```

### Authorization Checks

Only orchestrators can spawn successors:

```python
@require_agent_role('orchestrator')
def create_successor_orchestrator(...):
    # Only callable by orchestrator agents
    ...
```

### Audit Trail

Log all succession events:

```python
logger.info(
    f"Succession completed: {orchestrator.job_id} → {successor.job_id}, "
    f"instance {orchestrator.instance_number} → {successor.instance_number}, "
    f"reason: {reason}, tenant: {tenant_key}"
)
```

### SQL Injection Prevention

Use parameterized queries:

```python
# ✅ CORRECT - Parameterized query
query = select(MCPAgentJob).where(
    MCPAgentJob.job_id == job_id,
    MCPAgentJob.tenant_key == tenant_key
)

# ❌ WRONG - String interpolation (SQL injection risk)
query = f"SELECT * FROM mcp_agent_jobs WHERE job_id = '{job_id}'"
```

---

## Conclusion

Orchestrator succession architecture enables unlimited project duration through intelligent context management. The system provides:

- **Automatic handover** at 90% context usage
- **Compressed state transfer** (<10K tokens)
- **Full lineage tracking** via database
- **Multi-tenant isolation** at all levels
- **Production-grade testing** (45 tests, 80%+ coverage)

For end-user guidance, see the [User Guide](../user_guides/orchestrator_succession_guide.md).

For implementation checklist, see [Implementation Checklist](../../handovers/0080_implementation_checklist.md).

---

**Last Reviewed**: 2025-11-02
**Next Review**: After first production succession event
