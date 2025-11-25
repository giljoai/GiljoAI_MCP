# Handover 0239: Deployment Strategy & Feature Flag

**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 2 hours
**Dependencies**: Handovers 0225-0238 (all implementation complete)
**Part of**: Visual Refactor Series (0225-0239)

---

## Objective

Implement safe production deployment with feature flag, zero-downtime rollout strategy, and rollback capability. Enable gradual migration from card-only view to dual-view (card/table toggle) with performance monitoring and user feedback tracking.

**CRITICAL**: Per QUICK_LAUNCH.txt line 28 - "No zombie code, no commented-out blocks (delete, don't comment)". Cleanup is IMMEDIATE (Week 4), not "Future".

---

## TDD Approach

### Test-First Development Order

1. **Write failing tests for feature flag endpoint**
   - Test endpoint returns correct flag state
   - Test flag respects environment variable
   - Test flag defaults to `false` (safe default)

2. **Implement feature flag endpoint**

3. **Write failing tests for frontend flag check**
   - Test component renders old UI when flag disabled
   - Test component renders new UI when flag enabled
   - Test flag fetch error handling

4. **Implement frontend feature flag integration**

5. **Write failing tests for rollback scenario**
   - Test data integrity when toggling flag
   - Test no state corruption on rollback

6. **Refactor** for clarity

**Key Principle**: Write tests that verify SAFE DEPLOYMENT, not just feature functionality.

---

## Current State Analysis

### Current Jobs/Implement Tabs Implementation

**Location**: `frontend/src/components/orchestration/AgentCardGrid.vue`

**Current Rendering**:
- Default: Card view only
- New (post-0228): Card/table toggle within AgentCardGrid component

**No Parallel Systems**:
- AgentCardGrid remains the ONLY agent display component
- Table view is integrated via toggle, not separate component
- View mode stored in local component state

**No Breaking Changes**: Card view remains default when flag disabled.

---

## Implementation Plan

### 1. Backend Feature Flag Endpoint

**File**: `api/endpoints/features.py` (NEW)

```python
"""
Feature flag endpoints for gradual rollout of new features.

Flags controlled via environment variables for simple on/off control.
"""

from fastapi import APIRouter
from pydantic import BaseModel
import os

router = APIRouter()


class FeatureFlagResponse(BaseModel):
    """Response model for feature flag status"""

    enabled: bool
    feature: str
    rollout_stage: str | None = None  # 'internal', 'beta', 'production'


@router.get("/dual-view-toggle", response_model=FeatureFlagResponse)
async def get_dual_view_toggle_flag():
    """
    Get status of dual-view toggle feature flag.

    Feature: Card/Table view toggle in AgentCardGrid vs card-only view

    Control via environment variable:
    - ENABLE_DUAL_VIEW_TOGGLE=true → Toggle button visible
    - ENABLE_DUAL_VIEW_TOGGLE=false (or unset) → Card-only (safe default)

    Returns:
        FeatureFlagResponse: Flag status and rollout stage
    """

    # Read environment variable (safe default: false)
    enabled = os.getenv('ENABLE_DUAL_VIEW_TOGGLE', 'false').lower() == 'true'

    # Determine rollout stage (currently just on/off)
    rollout_stage = 'production' if enabled else None

    return FeatureFlagResponse(
        enabled=enabled,
        feature='dual-view-toggle',
        rollout_stage=rollout_stage,
    )


@router.get("/flags", response_model=list[FeatureFlagResponse])
async def list_all_feature_flags():
    """
    List all available feature flags.

    Useful for admin dashboard or debugging.

    Returns:
        list[FeatureFlagResponse]: All feature flags with current status
    """

    flags = []

    # Dual-view toggle flag
    dual_view_enabled = os.getenv('ENABLE_DUAL_VIEW_TOGGLE', 'false').lower() == 'true'
    flags.append(
        FeatureFlagResponse(
            enabled=dual_view_enabled,
            feature='dual-view-toggle',
            rollout_stage='production' if dual_view_enabled else None,
        )
    )

    return flags
```

**Register Router** (`api/app.py`):

```python
# Add import
from api.endpoints.features import router as features_router

# Register router
app.include_router(
    features_router,
    prefix="/api/features",
    tags=["features"],
)
```

---

### 2. Frontend Feature Flag Service

**File**: `frontend/src/services/featureFlags.js` (NEW)

```javascript
/**
 * Feature flag service for gradual feature rollout.
 *
 * Fetches feature flags from backend and provides reactive state.
 */

import { ref } from 'vue'

// Feature flag cache (reactive)
const flags = ref({
  dualViewToggle: false,
})

// Loading state
const loading = ref(false)
const lastFetch = ref(null)

/**
 * Fetch all feature flags from backend
 */
export async function fetchFeatureFlags() {
  loading.value = true

  try {
    const response = await fetch('/api/features/flags', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch feature flags: ${response.statusText}`)
    }

    const data = await response.json()

    // Update flag cache
    data.forEach(flag => {
      if (flag.feature === 'dual-view-toggle') {
        flags.value.dualViewToggle = flag.enabled
      }
    })

    lastFetch.value = new Date().toISOString()

    return flags.value
  } catch (error) {
    console.error('Failed to fetch feature flags:', error)

    // Safe default: all flags disabled
    flags.value.dualViewToggle = false

    throw error
  } finally {
    loading.value = false
  }
}

/**
 * Check if dual-view toggle is enabled
 */
export function useDualViewToggle() {
  return flags.value.dualViewToggle
}

/**
 * Get all feature flags
 */
export function useFeatureFlags() {
  return {
    flags,
    loading,
    lastFetch,
    fetchFeatureFlags,
  }
}
```

---

### 3. Frontend Component Integration

**File**: `frontend/src/components/orchestration/AgentCardGrid.vue`

**Modify view toggle visibility**:

```vue
<template>
  <div class="agent-display-container">
    <!-- View Mode Toggle (CONDITIONAL on feature flag) -->
    <v-row v-if="showViewToggle" class="mb-4">
      <v-col cols="auto">
        <v-btn-toggle
          v-model="viewMode"
          mandatory
          color="primary"
          density="compact"
        >
          <v-btn value="cards" icon>
            <v-icon>mdi-view-grid</v-icon>
            <v-tooltip activator="parent" location="top">Card View</v-tooltip>
          </v-btn>
          <v-btn value="table" icon>
            <v-icon>mdi-table</v-icon>
            <v-tooltip activator="parent" location="top">Table View</v-tooltip>
          </v-btn>
        </v-btn-toggle>
      </v-col>
    </v-row>

    <!-- Card View (ALWAYS AVAILABLE) -->
    <div v-if="viewMode === 'cards'" class="agent-card-grid">
      <AgentCard
        v-for="agent in sortedAgents"
        :key="agent.job_id"
        :agent="agent"
        :mode="mode"
        @launch-agent="$emit('launch-agent', $event)"
        @view-details="$emit('view-details', $event)"
      />
    </div>

    <!-- Table View (ONLY IF TOGGLE ENABLED) -->
    <AgentTableView
      v-else-if="showViewToggle"
      :agents="sortedAgents"
      :mode="mode"
      @row-click="$emit('view-details', $event)"
      @launch-agent="$emit('launch-agent', $event)"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchFeatureFlags, useDualViewToggle } from '@/services/featureFlags'
import { useAgentData } from '@/composables/useAgentData'
import AgentCard from '@/components/AgentCard.vue'
import AgentTableView from '@/components/orchestration/AgentTableView.vue'

const props = defineProps({
  agents: Array,
  mode: String
})

const emit = defineEmits(['view-changed', 'launch-agent', 'view-details'])

// Use shared composable
const { sortedAgents } = useAgentData(computed(() => props.agents))

// Feature flag state
const showViewToggle = ref(false)

// View mode state (always defaults to cards)
const viewMode = ref('cards')

// Fetch feature flags on mount
onMounted(async () => {
  try {
    await fetchFeatureFlags()
    showViewToggle.value = useDualViewToggle()
  } catch (error) {
    console.error('Failed to load feature flags, hiding toggle:', error)
    showViewToggle.value = false  // Safe fallback
  }
})
</script>
```

**Impact**: 15 lines added (feature flag check)

---

## Three-Phase Rollout Plan

### Phase 1: Internal Testing (Week 1)

**Environment**: Development/Staging

**Target Audience**: Development team only

**Configuration**:
```bash
# .env (dev/staging)
ENABLE_DUAL_VIEW_TOGGLE=true
```

**Success Criteria**:
- No errors in console
- Toggle button appears correctly
- Table view renders with real data
- Card view still works
- View switching preserves data
- WebSocket events update both views
- No performance degradation (<100ms response times)

**Rollback Trigger**:
- Any critical bug discovered
- Performance degradation >10%
- WebSocket errors

---

### Phase 2: Beta Rollout (Week 2)

**Environment**: Production

**Target Audience**: All users (100% - simplified rollout)

**Configuration**:
```bash
# .env (production)
ENABLE_DUAL_VIEW_TOGGLE=true
```

**Success Criteria**:
- <5% increase in error rate
- <10% increase in API response times
- <10 user complaints in first 24 hours
- Positive feedback from users

**Monitoring**:
- Error tracking (logs)
- API response times (logs)
- User feedback (support tickets)

**Rollback Trigger**:
- Error rate >5% increase
- Response time >2x baseline
- >10 critical bugs reported

---

### Phase 3: Full Rollout (Week 3) + IMMEDIATE Cleanup (Week 4)

**Environment**: Production

**Target Audience**: All users (100%)

#### Week 3: Monitor Stability

**Configuration**:
```bash
# .env (production)
ENABLE_DUAL_VIEW_TOGGLE=true
```

**Success Criteria**:
- Stable error rates (<1% increase)
- Stable response times (<5% increase)
- Positive user feedback
- No critical bugs reported for 1 week

#### Week 4: IMMEDIATE Cleanup (NOT "Future")

**CRITICAL**: Per QUICK_LAUNCH.txt line 28, zombie code policy requires immediate cleanup.

**Cleanup Steps**:

1. **Remove Feature Flag Code** (Day 1-2):

   ```vue
   <!-- AgentCardGrid.vue - BEFORE cleanup -->
   <v-row v-if="showViewToggle" class="mb-4">
     <!-- Toggle button -->
   </v-row>

   <!-- AgentCardGrid.vue - AFTER cleanup -->
   <v-row class="mb-4">
     <!-- Toggle button (always visible) -->
   </v-row>
   ```

   **Changes**:
   - Remove `showViewToggle` computed property
   - Remove feature flag fetch logic
   - Remove conditional `v-if="showViewToggle"` from toggle
   - Remove conditional `v-else-if="showViewToggle"` from AgentTableView

2. **Remove Backend Feature Flag Endpoint** (Day 1-2):

   ```python
   # api/endpoints/features.py - DELETE entire file
   # OR deprecate endpoint if other flags exist

   # api/app.py - Remove router registration
   # app.include_router(features_router, ...)  # DELETE THIS LINE
   ```

3. **Remove Frontend Feature Flag Service** (Day 1-2):

   ```bash
   # frontend/src/services/featureFlags.js - DELETE entire file

   # Remove imports from AgentCardGrid.vue:
   # import { fetchFeatureFlags, useDualViewToggle } from '@/services/featureFlags'  # DELETE
   ```

4. **Verify Zero Zombie Code** (Day 2):

   ```bash
   # Check for commented code
   grep -r "# OLD:" frontend/src/components/
   grep -r "// OLD:" frontend/src/components/

   # Check for unused imports
   cd frontend && npm run lint

   # Check for orphaned files
   find frontend/src/ -name "*.vue.old" -o -name "*.vue.backup"
   find frontend/src/ -name "*.js.old" -o -name "*.js.backup"

   # Verify feature flag references removed
   grep -r "ENABLE_DUAL_VIEW_TOGGLE" .
   grep -r "showViewToggle" frontend/src/
   grep -r "useDualViewToggle" frontend/src/
   ```

   **Expected**: All searches return zero results

5. **Update Documentation** (Day 2):

   - Mark Handover 0239 as "Complete - Feature Flag Removed"
   - Update CHANGELOG.md
   - Update component docs (remove feature flag references)

**Timeline**: 2 days (Week 4, Days 1-2)

**Rollback Window**: Keep `.git` history for 30 days (version control rollback only)

---

## Rollback Procedure

**When to Rollback**:

```
IF error_rate > 5% increase THEN rollback immediately
IF response_time > 2x baseline THEN rollback immediately
IF critical bug reported THEN investigate, rollback if needed
IF user complaints > 10 in 1 hour THEN investigate, rollback if user-facing issue
```

**Rollback Steps**:

1. **Disable Feature Flag** (environment variable):
   ```bash
   # .env (production)
   ENABLE_DUAL_VIEW_TOGGLE=false
   ```

2. **Restart API Server**:
   ```bash
   # Graceful restart (zero-downtime)
   systemctl restart giljo-mcp-api

   # Or Docker (if containerized)
   docker-compose restart api
   ```

3. **Verify Rollback**:
   ```bash
   # Check flag status
   curl http://localhost:7272/api/features/dual-view-toggle

   # Expected response:
   # {"enabled": false, "feature": "dual-view-toggle", "rollout_stage": null}
   ```

4. **Verify UI**:
   - Users should see card view only (no toggle button)
   - Existing card view should work normally
   - No errors in browser console

5. **Monitor for 24 Hours**:
   - Error rates should return to baseline
   - User complaints should stop
   - Card view should render correctly

**No Data Loss**: Feature flag only affects UI rendering, not data storage. All job data, messages, and state remain intact during rollback.

---

## Testing Criteria

### 1. Feature Flag Endpoint Tests

**File**: `tests/api/test_feature_flags.py`

```python
import pytest
import os

@pytest.mark.asyncio
async def test_feature_flag_defaults_to_false(async_client):
    """Test safe default: flag disabled when env var not set"""

    os.environ.pop('ENABLE_DUAL_VIEW_TOGGLE', None)

    response = await async_client.get('/api/features/dual-view-toggle')

    assert response.status_code == 200
    assert response.json()['enabled'] is False


@pytest.mark.asyncio
async def test_feature_flag_enabled_when_env_true(async_client, monkeypatch):
    """Test flag enabled when env var = 'true'"""

    monkeypatch.setenv('ENABLE_DUAL_VIEW_TOGGLE', 'true')

    response = await async_client.get('/api/features/dual-view-toggle')

    assert response.status_code == 200
    assert response.json()['enabled'] is True


@pytest.mark.asyncio
async def test_list_all_flags(async_client):
    """Test listing all feature flags"""

    response = await async_client.get('/api/features/flags')

    assert response.status_code == 200
    flags = response.json()

    assert isinstance(flags, list)
    assert len(flags) >= 1

    # Verify dual-view-toggle flag present
    toggle_flag = next(f for f in flags if f['feature'] == 'dual-view-toggle')
    assert toggle_flag is not None
    assert 'enabled' in toggle_flag
```

### 2. Frontend Integration Tests

**File**: `tests/integration/feature-flag-integration.spec.js`

```javascript
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import AgentCardGrid from '@/components/orchestration/AgentCardGrid.vue'
import { fetchFeatureFlags } from '@/services/featureFlags'

describe('Feature Flag Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should hide toggle when flag disabled', async () => {
    // Mock API response: flag disabled
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { feature: 'dual-view-toggle', enabled: false }
        ])
      })
    )

    const wrapper = mount(AgentCardGrid, {
      props: { agents: [], mode: 'jobs' }
    })
    await fetchFeatureFlags()
    await wrapper.vm.$nextTick()

    // Verify toggle button hidden
    expect(wrapper.find('.v-btn-toggle').exists()).toBe(false)

    // Verify card view rendered
    expect(wrapper.find('.agent-card-grid').exists()).toBe(true)
  })

  it('should show toggle when flag enabled', async () => {
    // Mock API response: flag enabled
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { feature: 'dual-view-toggle', enabled: true }
        ])
      })
    )

    const wrapper = mount(AgentCardGrid, {
      props: { agents: [], mode: 'jobs' }
    })
    await fetchFeatureFlags()
    await wrapper.vm.$nextTick()

    // Verify toggle button visible
    expect(wrapper.find('.v-btn-toggle').exists()).toBe(true)

    // Verify card view rendered by default
    expect(wrapper.find('.agent-card-grid').exists()).toBe(true)
  })

  it('should fallback to card-only on fetch error', async () => {
    // Mock API error
    global.fetch = vi.fn(() =>
      Promise.reject(new Error('Network error'))
    )

    const wrapper = mount(AgentCardGrid, {
      props: { agents: [], mode: 'jobs' }
    })

    try {
      await fetchFeatureFlags()
    } catch (error) {
      // Expected
    }

    await wrapper.vm.$nextTick()

    // Verify fallback to card-only (toggle hidden)
    expect(wrapper.find('.v-btn-toggle').exists()).toBe(false)
    expect(wrapper.find('.agent-card-grid').exists()).toBe(true)
  })
})
```

---

## Success Criteria

- ✅ Feature flag endpoint created (`/api/features/dual-view-toggle`)
- ✅ Feature flag defaults to `false` (safe default)
- ✅ Feature flag respects environment variable
- ✅ Frontend service fetches and caches flag
- ✅ Frontend conditionally shows toggle based on flag
- ✅ Frontend falls back to card-only on fetch error
- ✅ All tests pass (feature flag, integration, rollback safety)
- ✅ 3-phase rollout plan documented
- ✅ Rollback procedure tested and documented
- ✅ No data loss during flag toggle (rollback safe)
- ✅ **Week 4 cleanup completed** (feature flag removed, zero zombie code)

---

## Zombie Code Prevention Checklist

**Definition**: Zombie code = code that exists but is never executed (commented blocks, unused functions, orphaned files)

**Prevention Strategy**:
1. **Week 4**: Immediate cleanup (NOT "Future")
2. **Verification**: Grep checks for commented code, unused imports, orphaned files
3. **Automated checks**: Linting enforces no-unused-vars
4. **Manual review**: Grep for feature flag references before final commit

**CRITICAL**: Per QUICK_LAUNCH.txt line 28:
> "No zombie code, no commented-out blocks (delete, don't comment)"

**Compliance**:
- ✅ Cleanup scheduled for Week 4 (Days 1-2)
- ✅ Verification checklist provided (grep commands)
- ✅ All feature flag code removed (not commented)
- ✅ Zero orphaned files after cleanup
- ✅ Documentation updated to reflect final state

---

## Next Steps

→ **Execute Handovers 0225-0239** in sequence:

1. **0225**: Database schema enhancement (indexes)
2. **0226**: Backend API extensions (table view endpoint)
3. **0227**: Launch tab 3-panel refinement
4. **0228**: AgentCardGrid dual-view enhancement (composable + toggle)
5. **0229-0237**: Feature enhancements (message modal, sticky composer, etc.)
6. **0238**: Pinia store architecture
7. **0239**: Deployment strategy + Week 4 cleanup

**Final Validation**:
- All tests pass (unit, integration, E2E)
- Performance benchmarks met (<100ms API, <200ms frontend)
- Documentation complete
- Feature flag ready for production
- **Cleanup checklist verified** (zero zombie code post-Week 4)

---

## References

- **Architecture Principles**: `handovers/013A_code_review_architecture_status.md`
- **Zombie Code Policy**: QUICK_LAUNCH.txt line 28
- **TDD Principles**: `handovers/code_review_nov18.md`
- **Feature Flag Pattern**: Environment variable → API endpoint → Frontend check
- **Component Architecture**: Handover 0228 (AgentCardGrid dual-view)
- **Monitoring**: Existing logging infrastructure (`src/giljo_mcp/utils/logging.py`)
