---
Handover 0061: Orchestrator Launch UI Workflow
Date: 2025-10-27
Status: Ready for Implementation
Priority: CRITICAL
Complexity: MEDIUM
Duration: 6-8 hours
---

# Executive Summary

The GiljoAI MCP Server's ProductsView currently displays product information but lacks a direct way to launch the orchestrator for a product. This handover adds a "Launch Orchestrator" button that initiates the mission planning workflow, including vision document analysis, mission plan generation, agent selection, and workflow coordination.

**Key Principle**: Users should be able to launch the full orchestrator workflow with a single click, with real-time progress updates and clear visibility into what the orchestrator is doing.

The system will integrate with the existing MissionPlanner, AgentSelector, and WorkflowEngine components (Handover 0020) and provide real-time WebSocket updates for progress tracking.

---

# Problem Statement

## Current State

The orchestrator infrastructure exists but has no UI entry point:
- `src/giljo_mcp/mission_planner.py` - Mission generation from vision docs
- `src/giljo_mcp/agent_selector.py` - Smart agent selection
- `src/giljo_mcp/workflow_engine.py` - Workflow execution
- No "Launch" button in ProductsView
- No progress tracking UI
- Manual orchestrator invocation only

## Gaps Without This Implementation

1. **No UI Entry Point**: Users can't launch orchestrator from dashboard
2. **No Progress Visibility**: No way to see what orchestrator is doing
3. **Poor UX**: Users must use CLI or API directly
4. **No Error Feedback**: Orchestrator failures invisible to users
5. **No Status Tracking**: Can't tell if orchestrator is running or stuck

---

# Implementation Plan

## Overview

This implementation adds a launch button, progress dialog, and WebSocket integration for real-time updates. Backend adds a new orchestrator launch endpoint that coordinates the full workflow.

**Total Estimated Lines of Code**: ~450 lines across 5 files

## Phase 1: Backend - Orchestrator Launch Endpoint (2-3 hours)

**File**: `api/endpoints/orchestrator.py` (NEW)

**Endpoint**: POST /api/v1/orchestrator/launch

**Implementation**:

```python
"""
Orchestrator Launch Endpoint

Handles launching the full orchestrator workflow for a product.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio

from api.dependencies import get_current_active_user, get_tenant_key, get_db
from src.giljo_mcp.models import User, Product
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.agent_selector import AgentSelector
from src.giljo_mcp.workflow_engine import WorkflowEngine
from api.websockets import broadcast_to_tenant

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


class LaunchOrchestratorRequest(BaseModel):
    """Request to launch orchestrator for a product."""
    product_id: str
    workflow_type: str = "waterfall"  # waterfall or parallel
    auto_start: bool = True  # Auto-start agent jobs


class OrchestratorProgressUpdate(BaseModel):
    """Progress update during orchestrator launch."""
    stage: str  # analyzing_vision, generating_mission, selecting_agents, creating_workflow
    progress: int  # 0-100
    message: str
    details: Optional[Dict[str, Any]] = None


@router.post("/launch")
async def launch_orchestrator(
    request: LaunchOrchestratorRequest,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Launch the orchestrator workflow for a product.

    Steps:
    1. Validate product is active
    2. Analyze vision documents
    3. Generate condensed mission plan
    4. Select optimal agents
    5. Create workflow (waterfall or parallel)
    6. Optionally start agent jobs

    Returns orchestrator session ID for tracking.
    """
    from sqlalchemy import select
    from datetime import datetime
    import uuid

    # Validate product exists and is active
    result = await db.execute(
        select(Product).where(
            Product.id == request.product_id,
            Product.tenant_key == tenant_key
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Product '{product.name}' is not active. Activate it before launching orchestrator."
        )

    # Check if product has vision documents
    if not product.vision_path:
        raise HTTPException(
            status_code=400,
            detail="Product has no vision documents. Upload vision documents before launching orchestrator."
        )

    # Generate orchestrator session ID
    session_id = str(uuid.uuid4())

    # Send initial progress update
    await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
        "session_id": session_id,
        "stage": "starting",
        "progress": 0,
        "message": "Launching orchestrator...",
        "product_id": request.product_id
    })

    try:
        # Initialize components
        mission_planner = MissionPlanner(db)
        agent_selector = AgentSelector(db)
        workflow_engine = WorkflowEngine(db)

        # Stage 1: Analyze vision documents
        await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
            "session_id": session_id,
            "stage": "analyzing_vision",
            "progress": 20,
            "message": f"Analyzing vision documents for {product.name}...",
            "product_id": request.product_id
        })

        vision_analysis = await mission_planner.analyze_vision_documents(
            product_id=request.product_id,
            tenant_key=tenant_key
        )

        # Stage 2: Generate mission plan
        await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
            "session_id": session_id,
            "stage": "generating_mission",
            "progress": 40,
            "message": "Generating condensed mission plan...",
            "product_id": request.product_id,
            "details": {
                "vision_doc_count": vision_analysis.get("document_count", 0),
                "total_tokens": vision_analysis.get("total_tokens", 0)
            }
        })

        mission_plan = await mission_planner.generate_mission_plan(
            product_id=request.product_id,
            vision_analysis=vision_analysis,
            tenant_key=tenant_key
        )

        # Stage 3: Select agents
        await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
            "session_id": session_id,
            "stage": "selecting_agents",
            "progress": 60,
            "message": "Selecting optimal agents for mission...",
            "product_id": request.product_id,
            "details": {
                "mission_count": len(mission_plan.get("missions", [])),
                "condensed_tokens": mission_plan.get("condensed_tokens", 0)
            }
        })

        selected_agents = await agent_selector.select_agents_for_missions(
            missions=mission_plan.get("missions", []),
            product_id=request.product_id,
            tenant_key=tenant_key
        )

        # Stage 4: Create workflow
        await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
            "session_id": session_id,
            "stage": "creating_workflow",
            "progress": 80,
            "message": f"Creating {request.workflow_type} workflow...",
            "product_id": request.product_id,
            "details": {
                "agent_count": len(selected_agents),
                "agents": [{"id": a["id"], "name": a["name"]} for a in selected_agents]
            }
        })

        workflow = await workflow_engine.create_workflow(
            product_id=request.product_id,
            missions=mission_plan.get("missions", []),
            agents=selected_agents,
            workflow_type=request.workflow_type,
            tenant_key=tenant_key
        )

        # Stage 5: Optionally start jobs
        if request.auto_start:
            await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
                "session_id": session_id,
                "stage": "starting_jobs",
                "progress": 90,
                "message": "Starting agent jobs...",
                "product_id": request.product_id
            })

            await workflow_engine.start_workflow(workflow["id"])

        # Complete
        await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
            "session_id": session_id,
            "stage": "complete",
            "progress": 100,
            "message": "Orchestrator launched successfully",
            "product_id": request.product_id,
            "details": {
                "workflow_id": workflow["id"],
                "mission_count": len(mission_plan.get("missions", [])),
                "agent_count": len(selected_agents),
                "workflow_type": request.workflow_type,
                "auto_started": request.auto_start
            }
        })

        return {
            "success": True,
            "session_id": session_id,
            "workflow_id": workflow["id"],
            "mission_plan": mission_plan,
            "selected_agents": selected_agents,
            "workflow": workflow
        }

    except Exception as e:
        # Send error update
        await broadcast_to_tenant(tenant_key, "orchestrator:progress", {
            "session_id": session_id,
            "stage": "error",
            "progress": 0,
            "message": f"Orchestrator launch failed: {str(e)}",
            "product_id": request.product_id,
            "error": str(e)
        })

        raise HTTPException(
            status_code=500,
            detail=f"Orchestrator launch failed: {str(e)}"
        )
```

**Register Router**: Add to `api/app.py`:

```python
from api.endpoints import orchestrator
app.include_router(orchestrator.router, prefix="/api/v1")
```

## Phase 2: Frontend - Launch Button Component (2-3 hours)

**File**: `frontend/src/components/products/OrchestratorLaunchButton.vue` (NEW)

**Implementation**:

```vue
<template>
  <v-btn
    color="primary"
    variant="elevated"
    :loading="isLaunching"
    :disabled="!canLaunch"
    @click="launchOrchestrator"
  >
    <v-icon class="mr-2">mdi-rocket-launch</v-icon>
    Launch Orchestrator
  </v-btn>

  <!-- Progress Dialog -->
  <v-dialog v-model="showProgress" max-width="700" persistent>
    <v-card>
      <v-card-title class="text-h5">
        <v-icon class="mr-2" :color="progressIconColor">{{ progressIcon }}</v-icon>
        Orchestrator Launch Progress
      </v-card-title>

      <v-card-text>
        <div class="my-4">
          <v-progress-linear
            :model-value="progress"
            :color="progressColor"
            height="25"
            rounded
          >
            <template v-slot:default>
              <strong>{{ progress }}%</strong>
            </template>
          </v-progress-linear>
        </div>

        <v-alert
          :type="progressAlertType"
          variant="tonal"
          class="mb-4"
        >
          {{ progressMessage }}
        </v-alert>

        <!-- Stage Details -->
        <v-expansion-panels v-if="progressDetails" class="mb-4">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon class="mr-2">mdi-information</v-icon>
              Stage Details
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <pre class="text-caption">{{ JSON.stringify(progressDetails, null, 2) }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Stage Timeline -->
        <v-timeline density="compact" side="end">
          <v-timeline-item
            v-for="stage in completedStages"
            :key="stage.name"
            dot-color="success"
            size="small"
          >
            <template v-slot:icon>
              <v-icon size="small">mdi-check</v-icon>
            </template>
            <div>
              <div class="text-subtitle-2">{{ stage.label }}</div>
              <div class="text-caption text-grey">{{ stage.message }}</div>
            </div>
          </v-timeline-item>

          <v-timeline-item
            v-if="currentStage"
            dot-color="primary"
            size="small"
          >
            <template v-slot:icon>
              <v-progress-circular
                indeterminate
                size="16"
                width="2"
              />
            </template>
            <div>
              <div class="text-subtitle-2">{{ currentStage.label }}</div>
              <div class="text-caption text-grey">{{ currentStage.message }}</div>
            </div>
          </v-timeline-item>
        </v-timeline>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          v-if="isComplete || isError"
          @click="closeProgress"
          :color="isError ? 'error' : 'primary'"
          variant="elevated"
        >
          {{ isError ? 'Close' : 'View Workflow' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/services/api'
import { useWebSocket } from '@/composables/useWebSocket'

const props = defineProps({
  product: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['launched', 'error'])

const isLaunching = ref(false)
const showProgress = ref(false)
const progress = ref(0)
const progressMessage = ref('')
const progressDetails = ref(null)
const currentStage = ref(null)
const completedStages = ref([])
const sessionId = ref(null)
const isComplete = ref(false)
const isError = ref(false)

const canLaunch = computed(() => {
  return props.product.is_active && props.product.has_vision && !isLaunching.value
})

const progressIcon = computed(() => {
  if (isError.value) return 'mdi-alert-circle'
  if (isComplete.value) return 'mdi-check-circle'
  return 'mdi-rocket-launch'
})

const progressIconColor = computed(() => {
  if (isError.value) return 'error'
  if (isComplete.value) return 'success'
  return 'primary'
})

const progressColor = computed(() => {
  if (isError.value) return 'error'
  if (isComplete.value) return 'success'
  return 'primary'
})

const progressAlertType = computed(() => {
  if (isError.value) return 'error'
  if (isComplete.value) return 'success'
  return 'info'
})

const stageLabels = {
  starting: 'Initializing',
  analyzing_vision: 'Analyzing Vision Documents',
  generating_mission: 'Generating Mission Plan',
  selecting_agents: 'Selecting Agents',
  creating_workflow: 'Creating Workflow',
  starting_jobs: 'Starting Agent Jobs',
  complete: 'Complete',
  error: 'Error'
}

// WebSocket integration
const { socket } = useWebSocket()

watch(socket, (newSocket) => {
  if (newSocket) {
    newSocket.on('orchestrator:progress', handleProgressUpdate)
  }
})

function handleProgressUpdate(data) {
  // Only process updates for our session
  if (data.session_id !== sessionId.value) return

  progress.value = data.progress
  progressMessage.value = data.message
  progressDetails.value = data.details || null

  const stageLabel = stageLabels[data.stage] || data.stage

  if (data.stage === 'error') {
    isError.value = true
    isLaunching.value = false
    return
  }

  if (data.stage === 'complete') {
    isComplete.value = true
    isLaunching.value = false
    emit('launched', data.details)
    return
  }

  // Track current stage
  currentStage.value = {
    name: data.stage,
    label: stageLabel,
    message: data.message
  }

  // Add to completed stages if progress increased
  if (data.progress > 0 && !completedStages.value.find(s => s.name === data.stage)) {
    completedStages.value.push({
      name: data.stage,
      label: stageLabel,
      message: data.message
    })
  }
}

async function launchOrchestrator() {
  isLaunching.value = true
  showProgress.value = true
  progress.value = 0
  progressMessage.value = 'Initializing orchestrator...'
  completedStages.value = []
  currentStage.value = null
  isComplete.value = false
  isError.value = false

  try {
    const response = await api.orchestrator.launch({
      product_id: props.product.id,
      workflow_type: 'waterfall',
      auto_start: true
    })

    sessionId.value = response.data.session_id
  } catch (error) {
    console.error('[ORCHESTRATOR] Launch error:', error)
    progressMessage.value = error.response?.data?.detail || 'Failed to launch orchestrator'
    isError.value = true
    isLaunching.value = false
    emit('error', error)
  }
}

function closeProgress() {
  showProgress.value = false
  if (isComplete.value) {
    // Navigate to workflow view or refresh product data
    emit('launched')
  }
}
</script>
```

## Phase 3: Integration with ProductsView (1-2 hours)

**File**: `frontend/src/views/ProductsView.vue`

**Add Import**:

```javascript
import OrchestratorLaunchButton from '@/components/products/OrchestratorLaunchButton.vue'
```

**Add to Product Card Actions**:

```vue
<v-card-actions>
  <!-- Existing buttons -->
  <v-btn icon @click="editProduct(product)">
    <v-icon>mdi-pencil</v-icon>
  </v-btn>

  <!-- NEW: Launch Orchestrator Button -->
  <OrchestratorLaunchButton
    v-if="product.is_active"
    :product="product"
    @launched="handleOrchestratorLaunched(product)"
    @error="handleOrchestratorError"
  />

  <!-- Existing delete button -->
  <v-btn icon @click="deleteProduct(product)">
    <v-icon>mdi-delete</v-icon>
  </v-btn>
</v-card-actions>
```

**Add Handlers**:

```javascript
function handleOrchestratorLaunched(product) {
  success.value = `Orchestrator launched successfully for ${product.name}`
  // Optionally navigate to workflow view or refresh data
}

function handleOrchestratorError(error) {
  error.value = error.response?.data?.detail || 'Failed to launch orchestrator'
}
```

## Phase 4: API Service Integration (30 minutes)

**File**: `frontend/src/services/api.js`

**Add Orchestrator Methods**:

```javascript
orchestrator: {
  launch: (data) => apiClient.post('/api/v1/orchestrator/launch', data)
}
```

---

# Files to Modify

1. **api/endpoints/orchestrator.py** (~200 lines, NEW FILE)
   - Launch endpoint with full workflow coordination
   - WebSocket progress updates
   - Error handling

2. **api/app.py** (+2 lines)
   - Import and register orchestrator router

3. **frontend/src/components/products/OrchestratorLaunchButton.vue** (~180 lines, NEW FILE)
   - Launch button component
   - Progress dialog with timeline
   - WebSocket integration

4. **frontend/src/views/ProductsView.vue** (+30 lines)
   - Import and integrate launch button
   - Event handlers

5. **frontend/src/services/api.js** (+5 lines)
   - Add orchestrator.launch method

**Total**: ~417 lines across 5 files (3 new, 2 modified)

---

# Success Criteria

## Functional Requirements
- Launch button visible on active products with vision documents
- Launch button disabled if product not active or no vision documents
- Clicking button initiates full orchestrator workflow
- Real-time progress updates via WebSocket
- Progress dialog shows current stage and completed stages
- Error states properly displayed and handled
- Successful launch navigates to workflow view or refreshes data

## User Experience Requirements
- Clear progress indication (0-100%)
- Stage timeline showing completed and current stages
- Stage details expandable for technical users
- Smooth transitions between stages
- Proper loading states and disabled states
- Error messages are actionable

## Technical Requirements
- Multi-tenant isolation enforced
- WebSocket events properly scoped to session
- Backend validates product is active and has vision
- No race conditions in progress updates
- Proper cleanup of WebSocket listeners

---

# Related Handovers

- **Handover 0020**: Orchestrator Enhancement (DEPENDS ON)
  - Provides MissionPlanner, AgentSelector, WorkflowEngine

- **Handover 0050**: Single Active Product Architecture (DEPENDS ON)
  - Validates product is active before launch

- **Handover 0060**: MCP Agent Coordination Tool Exposure (DEPENDS ON)
  - Uses MCP tools for agent coordination

- **Handover 0065**: Mission Launch Summary Component (COMPLEMENTS)
  - Shows summary before launch

---

# Risk Assessment

**Complexity**: MEDIUM (WebSocket coordination, multi-stage workflow)
**Risk**: MEDIUM (depends on existing orchestrator components)
**Breaking Changes**: None
**Performance Impact**: Moderate (vision analysis can take 10-30 seconds)

---

# Timeline Estimate

**Phase 1**: 2-3 hours (Backend endpoint)
**Phase 2**: 2-3 hours (Launch button component)
**Phase 3**: 1-2 hours (ProductsView integration)
**Phase 4**: 30 minutes (API service)

**Total**: 6-8 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: CRITICAL (enables core orchestrator UI workflow)

---

**End of Handover 0061**
