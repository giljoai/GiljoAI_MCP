---
Handover 0065: Mission Launch Summary Component
Date: 2025-10-27
Status: Ready for Implementation
Priority: HIGH
Complexity: MEDIUM
Duration: 6-8 hours
---

# Executive Summary

The GiljoAI MCP Server's orchestrator launch workflow (Handover 0061) launches missions immediately upon clicking "Launch Orchestrator". This handover adds a pre-launch review component that summarizes the generated mission plan, selected agents, estimated token usage, and workflow structure before committing to execution.

**Key Principle**: Users should review and approve mission plans before launching agent workflows, ensuring alignment with expectations and catching potential issues early.

The system will display a comprehensive summary dialog with mission details, agent assignments, token estimates, and workflow visualization before starting the orchestrator.

---

# Problem Statement

## Current State

Orchestrator launches without user review:
- No preview of generated missions
- Can't see agent assignments before execution
- No token usage estimate before launch
- No workflow structure preview
- Can't cancel after clicking Launch
- No opportunity to adjust before execution

## Gaps Without This Implementation

1. **No Mission Preview**: Users don't see what missions will be generated
2. **No Agent Preview**: Can't review which agents are selected
3. **No Token Estimate**: Unknown if mission fits within budget
4. **No Workflow Preview**: Don't know execution order or parallelization
5. **No Cancel Option**: Can't abort after clicking launch
6. **Poor Planning**: Can't adjust product/project based on preview

---

# Implementation Plan

## Overview

This implementation modifies the orchestrator launch workflow to generate the plan first, show a summary dialog with all details, and only execute upon user confirmation. Backend adds a "preview" mode to orchestrator endpoint.

**Total Estimated Lines of Code**: ~450 lines across 4 files

## Phase 1: Backend - Preview Mode (2 hours)

**File**: `api/endpoints/orchestrator.py`

**Modify Launch Endpoint to Support Preview Mode**:

```python
class LaunchOrchestratorRequest(BaseModel):
    """Request to launch orchestrator for a product."""
    product_id: str
    workflow_type: str = "waterfall"
    auto_start: bool = True
    preview_only: bool = False  # NEW: Only generate plan, don't execute


@router.post("/launch")
async def launch_orchestrator(
    request: LaunchOrchestratorRequest,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Launch (or preview) the orchestrator workflow for a product.

    If preview_only=True:
    - Analyzes vision documents
    - Generates mission plan
    - Selects agents
    - Creates workflow structure
    - Returns summary WITHOUT starting jobs

    If preview_only=False:
    - Performs all preview steps
    - Starts agent jobs
    - Returns workflow ID
    """
    # ... existing validation code ...

    try:
        # ... existing initialization and stages 1-4 ...

        # Generate full plan
        mission_planner = MissionPlanner(db)
        agent_selector = AgentSelector(db)
        workflow_engine = WorkflowEngine(db)

        # Analyze, generate, select, create workflow (existing code)
        vision_analysis = await mission_planner.analyze_vision_documents(
            product_id=request.product_id,
            tenant_key=tenant_key
        )

        mission_plan = await mission_planner.generate_mission_plan(
            product_id=request.product_id,
            vision_analysis=vision_analysis,
            tenant_key=tenant_key
        )

        selected_agents = await agent_selector.select_agents_for_missions(
            missions=mission_plan.get("missions", []),
            product_id=request.product_id,
            tenant_key=tenant_key
        )

        workflow = await workflow_engine.create_workflow(
            product_id=request.product_id,
            missions=mission_plan.get("missions", []),
            agents=selected_agents,
            workflow_type=request.workflow_type,
            tenant_key=tenant_key,
            commit=not request.preview_only  # NEW: Don't commit if preview only
        )

        # Calculate token estimates
        token_estimate = calculate_token_estimate(
            vision_analysis=vision_analysis,
            mission_plan=mission_plan,
            selected_agents=selected_agents
        )

        # If preview only, return summary without starting
        if request.preview_only:
            return {
                "preview": True,
                "session_id": session_id,
                "product_id": request.product_id,
                "product_name": product.name,
                "mission_plan": mission_plan,
                "selected_agents": selected_agents,
                "workflow": workflow,
                "token_estimate": token_estimate,
                "workflow_type": request.workflow_type
            }

        # Otherwise, start workflow (existing code)
        if request.auto_start:
            await workflow_engine.start_workflow(workflow["id"])

        return {
            "success": True,
            "session_id": session_id,
            "workflow_id": workflow["id"],
            "mission_plan": mission_plan,
            "selected_agents": selected_agents,
            "workflow": workflow,
            "token_estimate": token_estimate
        }

    except Exception as e:
        # ... existing error handling ...


def calculate_token_estimate(
    vision_analysis: Dict,
    mission_plan: Dict,
    selected_agents: List[Dict]
) -> Dict[str, Any]:
    """
    Calculate estimated token usage for mission execution.

    Returns:
        {
            "vision_tokens": 5000,
            "mission_tokens": 2000,
            "estimated_agent_tokens": 8000,
            "total_estimate": 15000,
            "budget_available": 2000,
            "within_budget": True,
            "utilization_percent": 87.5
        }
    """
    vision_tokens = vision_analysis.get("total_tokens", 0)
    mission_tokens = mission_plan.get("condensed_tokens", 0)

    # Estimate agent tokens (mission tokens * number of agents * 2x multiplier)
    estimated_agent_tokens = mission_tokens * len(selected_agents) * 2

    total_estimate = vision_tokens + mission_tokens + estimated_agent_tokens

    # Field priority budget (from Handover 0048)
    budget_available = 2000

    return {
        "vision_tokens": vision_tokens,
        "mission_tokens": mission_tokens,
        "estimated_agent_tokens": estimated_agent_tokens,
        "total_estimate": total_estimate,
        "budget_available": budget_available,
        "within_budget": total_estimate <= budget_available,
        "utilization_percent": round((mission_tokens / budget_available) * 100, 1)
    }
```

## Phase 2: Frontend - Mission Summary Dialog (3-4 hours)

**File**: `frontend/src/components/orchestrator/MissionLaunchSummaryDialog.vue` (NEW)

```vue
<template>
  <v-dialog v-model="isOpen" max-width="900" persistent scrollable>
    <v-card>
      <v-card-title class="text-h5 bg-primary">
        <v-icon class="mr-2">mdi-clipboard-check</v-icon>
        Mission Launch Summary
      </v-card-title>

      <v-card-text class="pa-6">
        <!-- Product Info -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-package</v-icon>
            Product
          </v-card-title>
          <v-card-text>
            <div class="text-h6">{{ summary.product_name }}</div>
            <div class="text-caption text-grey">
              {{ summary.product_id }}
            </div>
          </v-card-text>
        </v-card>

        <!-- Token Estimate -->
        <v-card
          variant="outlined"
          class="mb-4"
          :color="tokenBudgetColor"
        >
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-gauge</v-icon>
            Token Budget Analysis
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="6">
                <div class="text-caption text-grey">Mission Tokens</div>
                <div class="text-h6">{{ summary.token_estimate.mission_tokens }}</div>
              </v-col>
              <v-col cols="6">
                <div class="text-caption text-grey">Budget Available</div>
                <div class="text-h6">{{ summary.token_estimate.budget_available }}</div>
              </v-col>
            </v-row>

            <v-progress-linear
              :model-value="summary.token_estimate.utilization_percent"
              :color="tokenBudgetColor"
              height="25"
              rounded
              class="mt-3"
            >
              <template v-slot:default>
                <strong>{{ summary.token_estimate.utilization_percent }}%</strong>
              </template>
            </v-progress-linear>

            <v-alert
              v-if="!summary.token_estimate.within_budget"
              type="warning"
              variant="tonal"
              density="compact"
              class="mt-3"
            >
              Warning: Mission may exceed token budget. Consider reducing mission scope.
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- Mission Plan -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-file-document</v-icon>
            Mission Plan ({{ missions.length }} missions)
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item
                v-for="(mission, index) in missions"
                :key="index"
                class="mb-2"
              >
                <template v-slot:prepend>
                  <v-avatar color="primary" size="32">
                    {{ index + 1 }}
                  </v-avatar>
                </template>

                <v-list-item-title>
                  {{ mission.title }}
                </v-list-item-title>

                <v-list-item-subtitle>
                  {{ truncate(mission.description, 100) }}
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-chip size="small" :color="getPriorityColor(mission.priority)">
                    Priority {{ mission.priority }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Selected Agents -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-robot</v-icon>
            Selected Agents ({{ agents.length }} agents)
          </v-card-title>
          <v-card-text>
            <v-chip-group column>
              <v-chip
                v-for="agent in agents"
                :key="agent.id"
                :prepend-icon="getAgentIcon(agent.type)"
                color="primary"
                variant="outlined"
              >
                {{ agent.name }}
              </v-chip>
            </v-chip-group>

            <v-list density="compact" class="mt-3">
              <v-list-item
                v-for="agent in agents"
                :key="agent.id"
              >
                <template v-slot:prepend>
                  <v-icon :color="getAgentColor(agent.type)">
                    {{ getAgentIcon(agent.type) }}
                  </v-icon>
                </template>

                <v-list-item-title>{{ agent.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ agent.capabilities.join(', ') }}
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-chip size="small">
                    {{ agent.assigned_missions }} mission{{ agent.assigned_missions !== 1 ? 's' : '' }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Workflow Structure -->
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2">mdi-graph</v-icon>
            Workflow Structure
          </v-card-title>
          <v-card-text>
            <v-chip
              :color="workflowTypeColor"
              :prepend-icon="workflowTypeIcon"
              class="mb-3"
            >
              {{ summary.workflow_type }}
            </v-chip>

            <div class="text-body-2 text-grey">
              {{ workflowDescription }}
            </div>

            <!-- Workflow stages visualization -->
            <v-timeline density="compact" side="end" class="mt-4">
              <v-timeline-item
                v-for="(stage, index) in workflowStages"
                :key="index"
                :dot-color="stage.color"
                size="small"
              >
                <div>
                  <div class="text-subtitle-2">{{ stage.name }}</div>
                  <div class="text-caption text-grey">
                    {{ stage.agents.join(', ') }}
                  </div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-card>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-btn
          @click="cancel"
          variant="text"
          :disabled="loading"
        >
          Cancel
        </v-btn>
        <v-spacer />
        <v-btn
          @click="confirm"
          color="primary"
          variant="elevated"
          :loading="loading"
          size="large"
        >
          <v-icon class="mr-2">mdi-rocket-launch</v-icon>
          Launch Mission
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  summary: {
    type: Object,
    required: true,
    validator: (val) => {
      return val && val.mission_plan && val.selected_agents && val.workflow
    }
  }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const loading = ref(false)

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const missions = computed(() => props.summary.mission_plan?.missions || [])
const agents = computed(() => props.summary.selected_agents || [])
const workflowStages = computed(() => props.summary.workflow?.stages || [])

const tokenBudgetColor = computed(() => {
  const utilization = props.summary.token_estimate?.utilization_percent || 0
  if (utilization > 100) return 'error'
  if (utilization > 80) return 'warning'
  return 'success'
})

const workflowTypeColor = computed(() => {
  return props.summary.workflow_type === 'waterfall' ? 'primary' : 'secondary'
})

const workflowTypeIcon = computed(() => {
  return props.summary.workflow_type === 'waterfall' ? 'mdi-waterfall' : 'mdi-network'
})

const workflowDescription = computed(() => {
  if (props.summary.workflow_type === 'waterfall') {
    return 'Sequential execution - missions completed in order, each stage waits for previous to complete'
  }
  return 'Parallel execution - missions executed simultaneously where possible'
})

function getPriorityColor(priority) {
  if (priority >= 8) return 'error'
  if (priority >= 5) return 'warning'
  return 'success'
}

function getAgentIcon(type) {
  switch (type) {
    case 'claude': return 'mdi-robot'
    case 'codex': return 'mdi-code-braces'
    case 'gemini': return 'mdi-google'
    default: return 'mdi-robot-outline'
  }
}

function getAgentColor(type) {
  switch (type) {
    case 'claude': return 'primary'
    case 'codex': return 'secondary'
    case 'gemini': return 'accent'
    default: return 'grey'
  }
}

function truncate(text, length) {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

function confirm() {
  emit('confirm')
}

function cancel() {
  emit('cancel')
  isOpen.value = false
}
</script>
```

## Phase 3: Integration with Launch Button (1 hour)

**File**: `frontend/src/components/products/OrchestratorLaunchButton.vue`

**Modify Launch Flow**:

```javascript
import MissionLaunchSummaryDialog from '@/components/orchestrator/MissionLaunchSummaryDialog.vue'

const showSummary = ref(false)
const missionSummary = ref(null)

async function launchOrchestrator() {
  isLaunching.value = true
  progressMessage.value = 'Generating mission preview...'

  try {
    // Step 1: Generate preview
    const previewResponse = await api.orchestrator.launch({
      product_id: props.product.id,
      workflow_type: 'waterfall',
      auto_start: false,
      preview_only: true  // NEW: Preview mode
    })

    // Show summary dialog
    missionSummary.value = previewResponse.data
    showSummary.value = true
    isLaunching.value = false

  } catch (error) {
    console.error('[ORCHESTRATOR] Preview error:', error)
    progressMessage.value = error.response?.data?.detail || 'Failed to generate preview'
    isError.value = true
    isLaunching.value = false
    emit('error', error)
  }
}

async function confirmLaunch() {
  // User confirmed - actually launch
  showSummary.value = false
  isLaunching.value = true
  showProgress.value = true

  try {
    const response = await api.orchestrator.launch({
      product_id: props.product.id,
      workflow_type: 'waterfall',
      auto_start: true,
      preview_only: false  // Actually execute
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

function cancelLaunch() {
  showSummary.value = false
  missionSummary.value = null
}
```

**Add to Template**:

```vue
<!-- Add Summary Dialog -->
<MissionLaunchSummaryDialog
  v-model="showSummary"
  :summary="missionSummary"
  @confirm="confirmLaunch"
  @cancel="cancelLaunch"
/>
```

---

# Files to Modify

1. **api/endpoints/orchestrator.py** (+80 lines)
   - Add preview_only parameter
   - Add calculate_token_estimate function
   - Modify workflow creation to support preview mode

2. **frontend/src/components/orchestrator/MissionLaunchSummaryDialog.vue** (~300 lines, NEW FILE)
   - Complete summary dialog component
   - Token budget visualization
   - Mission list display
   - Agent assignments display
   - Workflow structure timeline

3. **frontend/src/components/products/OrchestratorLaunchButton.vue** (+50 lines)
   - Modify launch flow for preview-then-execute
   - Import and integrate summary dialog
   - Add confirmLaunch and cancelLaunch handlers

4. **tests/api/test_orchestrator_preview.py** (~50 lines, NEW FILE)
   - Test preview mode
   - Test token calculations
   - Test workflow creation without commit

**Total**: ~480 lines across 4 files (2 new, 2 modified)

---

# Success Criteria

## Functional Requirements
- Preview generated before execution
- Mission plan displayed with all missions
- Agent assignments shown with capabilities
- Token budget displayed with utilization percentage
- Workflow structure visualized
- Warning if over budget
- User can confirm or cancel launch
- Preview mode doesn't create jobs or commit workflow

## User Experience Requirements
- Clean, scannable summary layout
- Clear token budget visualization
- Visual workflow structure
- Smooth dialog transitions
- Confirm button prominent
- Cancel option always available

## Technical Requirements
- Preview mode doesn't persist to database
- Token calculations accurate
- Multi-tenant isolation enforced
- Proper error handling
- Performance optimized (preview < 5 seconds)

---

# Related Handovers

- **Handover 0020**: Orchestrator Enhancement (DEPENDS ON)
  - Provides mission planner, agent selector, workflow engine

- **Handover 0048**: Field Priority Configuration (RELATES TO)
  - Token budget from field priority settings

- **Handover 0061**: Orchestrator Launch UI Workflow (DEPENDS ON)
  - Enhances launch workflow with preview

---

# Risk Assessment

**Complexity**: MEDIUM (complex UI, workflow preview logic)
**Risk**: LOW (preview mode is non-destructive)
**Breaking Changes**: None
**Performance Impact**: Minimal (preview adds 2-5 seconds)

---

# Timeline Estimate

**Phase 1**: 2 hours (Backend preview mode)
**Phase 2**: 3-4 hours (Summary dialog component)
**Phase 3**: 1 hour (Integration)

**Total**: 6-8 hours for experienced developer

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Priority**: HIGH (improves mission planning UX)

---

**End of Handover 0065**
