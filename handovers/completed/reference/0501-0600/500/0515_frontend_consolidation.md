---
**Document Type:** Handover
**Handover ID:** 0515
**Title:** Frontend Consolidation - Component Cleanup & API Centralization
**Version:** 1.0
**Created:** 2025-11-12
**Status:** Ready for Execution
**Duration:** 1-2 days
**Scope:** Merge duplicate components (0130c), centralize API calls (0130d)
**Priority:** 🔴 P0 CRITICAL
**Tool:** ☁️ CCW
**Parallel Execution:** ❌ No (Sequential - Complex refactoring)
**Parent Project:** Projectplan_500.md
---

# Handover 0515: Frontend Consolidation - Component Cleanup & API Centralization

## 🎯 Mission Statement
Complete frontend consolidation deferred from Handover 0130: merge duplicate components (AgentCard variants), centralize API calls (30+ components → api.js), improve maintainability.

## 📋 Prerequisites
- ✅ All previous handovers complete (0500-0514)
- ✅ Frontend tests passing
- ✅ API client updated (0507)

## ⚠️ Problem Statement

### Issue 1: Duplicate AgentCard Components (Handover 0130c)
**Evidence**: Projectplan_500.md line 99
- `AgentCard.vue` (original)
- `AgentCardEnhanced.vue` (new, with succession features)
- `OrchestratorCard.vue` (orchestrator-specific)
- **Impact**: 3 components doing similar work, inconsistent UI

### Issue 2: Scattered API Calls (Handover 0130d)
**Evidence**: Projectplan_500.md line 100
- 30+ components make direct API calls
- Inconsistent error handling
- Duplicate code for same endpoints
- **Impact**: Hard to maintain, inconsistent UX

## ✅ Solution Approach

### Part A: Component Consolidation (0130c)
Merge 3 AgentCard variants into single AgentCard.vue with props:
```vue
<agent-card
  :job="job"
  :enhanced="true"  <!-- Show succession features -->
  :type="job.agent_type"  <!-- Different styles for orchestrator -->
/>
```

### Part B: API Call Centralization (0130d)
Create composables for API operations:
```javascript
// frontend/src/composables/useProducts.js
export function useProducts() {
  const { toast } = useToast()

  const createProduct = async (data) => {
    try {
      const product = await api.products.create(data)
      toast.success('Product created')
      return product
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create product')
      throw error
    }
  }

  // ... other product operations
}
```

## 📝 Implementation Tasks

### Task 1: Audit Component Duplicates (2 hours)
**Search for duplicates**:
```bash
# Find similar component names
find frontend/src/components -name "*Card*.vue"
find frontend/src/components -name "*Modal*.vue"
find frontend/src/components -name "*Dialog*.vue"

# Find components with similar props/logic
grep -r "agent_type" frontend/src/components/*.vue
```

**Create consolidation plan**:
- AgentCard + AgentCardEnhanced + OrchestratorCard → AgentCard.vue
- Other duplicates found

### Task 2: Merge AgentCard Variants (4 hours)
**File**: `frontend/src/components/orchestration/AgentCard.vue` (update)

**Strategy**:
1. Start with AgentCardEnhanced.vue (most features)
2. Add type prop for orchestrator-specific styling
3. Make succession features conditional (only for orchestrators)
4. Migrate all usages to unified component

**Implementation**:
```vue
<template>
  <v-card
    :class="cardClasses"
    :variant="variant"
  >
    <v-card-title>
      <v-chip :color="statusColor" size="small">{{ job.status }}</v-chip>
      {{ job.agent_name }}

      <!-- Orchestrator-specific: Instance badge -->
      <v-chip v-if="isOrchestrator && job.instance_number" size="small" class="ml-2">
        Instance {{ job.instance_number }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Common fields -->
      <div class="text-body-2">
        <strong>Type:</strong> {{ job.agent_type }}
      </div>

      <!-- Orchestrator-specific: Context bar -->
      <div v-if="isOrchestrator && enhanced" class="mt-2">
        <div class="text-caption">Context Usage</div>
        <v-progress-linear
          :model-value="contextPercentage"
          :color="contextColor"
          height="20"
        >
          <template #default="{ value }">{{ Math.round(value) }}%</template>
        </v-progress-linear>
      </div>

      <!-- Enhanced features: Succession timeline -->
      <succession-timeline
        v-if="isOrchestrator && enhanced"
        :project-id="job.project_id"
        class="mt-4"
      />
    </v-card-text>

    <v-card-actions>
      <!-- Common actions -->
      <v-btn @click="viewDetails">View Details</v-btn>

      <!-- Orchestrator-specific: Hand Over button -->
      <launch-successor-dialog
        v-if="isOrchestrator && enhanced && job.status === 'working'"
        :job-id="job.id"
        :current-job="job"
      >
        <template #activator="{ props }">
          <v-btn v-bind="props" color="warning">Hand Over</v-btn>
        </template>
      </launch-successor-dialog>
    </v-card-actions>
  </v-card>
</template>

<script>
import { computed } from 'vue'
import SuccessionTimeline from '../projects/SuccessionTimeline.vue'
import LaunchSuccessorDialog from '../projects/LaunchSuccessorDialog.vue'

export default {
  name: 'AgentCard',

  components: {
    SuccessionTimeline,
    LaunchSuccessorDialog
  },

  props: {
    job: {
      type: Object,
      required: true
    },
    enhanced: {
      type: Boolean,
      default: false
    },
    variant: {
      type: String,
      default: 'outlined'
    }
  },

  setup(props) {
    const isOrchestrator = computed(() => props.job.agent_type === 'orchestrator')

    const cardClasses = computed(() => ({
      'agent-card': true,
      'agent-card--orchestrator': isOrchestrator.value,
      'agent-card--enhanced': props.enhanced
    }))

    const statusColor = computed(() => {
      const colors = {
        pending: 'grey',
        active: 'success',
        working: 'primary',
        completed: 'success',
        failed: 'error'
      }
      return colors[props.job.status] || 'grey'
    })

    const contextPercentage = computed(() => {
      if (!props.job.context_budget || !props.job.context_used) return 0
      return (props.job.context_used / props.job.context_budget) * 100
    })

    const contextColor = computed(() => {
      const pct = contextPercentage.value
      if (pct >= 90) return 'error'
      if (pct >= 70) return 'warning'
      return 'success'
    })

    return {
      isOrchestrator,
      cardClasses,
      statusColor,
      contextPercentage,
      contextColor
    }
  }
}
</script>
```

### Task 3: Create API Composables (6 hours)
**Files**: `frontend/src/composables/` (create new files)

**useProducts.js**:
```javascript
import { ref } from 'vue'
import api from '@/services/api'
import { useToast } from './useToast'

export function useProducts() {
  const { toast } = useToast()
  const loading = ref(false)
  const error = ref(null)

  const createProduct = async (data) => {
    loading.value = true
    error.value = null
    try {
      const product = await api.products.create(data)
      toast.success('Product created successfully')
      return product
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create product'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  const activateProduct = async (productId) => {
    loading.value = true
    try {
      const response = await api.products.activate(productId)
      toast.success('Product activated')
      return response
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to activate product'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ... other operations

  return {
    loading,
    error,
    createProduct,
    activateProduct,
    // ... other methods
  }
}
```

**useProjects.js**, **useAgentJobs.js**, **useSettings.js** - similar pattern

### Task 4: Migrate Components to Use Composables (6 hours)
**Example**: Update ProductsView.vue

**Before**:
```vue
<script>
export default {
  methods: {
    async createProduct(data) {
      try {
        const response = await api.products.create(data)
        this.$toast.success('Product created')
        this.fetchProducts()
      } catch (error) {
        this.$toast.error('Failed to create product')
      }
    }
  }
}
</script>
```

**After**:
```vue
<script>
import { useProducts } from '@/composables/useProducts'

export default {
  setup() {
    const { createProduct, loading, error } = useProducts()

    const handleCreate = async (data) => {
      await createProduct(data)
      // Auto-refreshes, shows toast, handles errors
    }

    return {
      handleCreate,
      loading,
      error
    }
  }
}
</script>
```

### Task 5: Update All Component Usages (4 hours)
**Find all AgentCard usages**:
```bash
grep -r "AgentCardEnhanced" frontend/src/
grep -r "OrchestratorCard" frontend/src/
```

**Replace with unified AgentCard**:
```vue
<!-- Before -->
<agent-card-enhanced :job="job" />
<orchestrator-card :job="orchestratorJob" />

<!-- After -->
<agent-card :job="job" :enhanced="true" />
<agent-card :job="orchestratorJob" :enhanced="true" />
```

### Task 6: Remove Deprecated Components (1 hour)
```bash
git rm frontend/src/components/orchestration/AgentCardEnhanced.vue
git rm frontend/src/components/orchestration/OrchestratorCard.vue
# Remove other deprecated duplicates
```

### Task 7: Testing & Validation (2 hours)
- [ ] Visual regression testing (compare before/after)
- [ ] All pages load without errors
- [ ] Agent cards display correctly
- [ ] API calls work via composables
- [ ] Error handling consistent

## ✅ Success Criteria
- [ ] AgentCard variants merged (3 → 1 component)
- [ ] API calls centralized in composables
- [ ] All components migrated to use composables
- [ ] Deprecated components removed
- [ ] No visual regressions
- [ ] Consistent error handling
- [ ] Toast notifications work everywhere
- [ ] Code duplication reduced by 50%+

## 🔄 Rollback Plan
1. `git checkout HEAD~1 -- frontend/src/components/orchestration/`
2. `git checkout HEAD~1 -- frontend/src/composables/`
3. Restore deleted components from backup

## 📚 Related Handovers
**Depends on**: All previous handovers (0500-0514)
**Related**: Handover 0130c-d (original consolidation tasks)

## 🛠️ Tool Justification
**Why CCW**: Pure Vue/JS refactoring, no backend changes
**Why Sequential**: Complex refactoring, high risk of breaking changes

## 📊 Parallel Execution
**❌ Cannot parallelize** - Sequential execution required due to complexity

---
**Status:** Ready for Execution
**Estimated Effort:** 1-2 days
**Archive Location:** `handovers/completed/0515_frontend_consolidation-COMPLETE.md`
