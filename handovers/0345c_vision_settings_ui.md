# Handover 0345c: Vision Settings UI

**Date:** 2025-12-11
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor / Frontend Tester
**Priority:** Medium
**Estimated Complexity:** 1 day
**Status:** Not Started

---

## Task Summary

Add user controls in Settings for vision document handling: vision summarization toggle (Integrations tab) and vision document depth selector (Context tab).

**Why:** Users need UI controls to enable/disable Sumy LSA summarization and configure vision document depth levels (none/light/moderate/heavy).

**Expected Outcome:** Two new settings controls that persist via backend API and affect vision document handling behavior.

---

## Context and Background

### Dependencies
This handover depends on:
- **0345a** (Lean Orchestrator Instructions) - MUST be complete first
- **0345b** (Sumy LSA Integration) - RECOMMENDED but not required

### Architecture Context
GiljoAI uses a 2-dimensional context management model:
- **Priority Dimension** (WHAT to fetch): Priority 1-4 (CRITICAL → EXCLUDED)
- **Depth Dimension** (HOW MUCH detail): Field-specific depth levels

Vision documents currently have priority configuration but lack depth controls. This handover adds:
1. **Toggle**: Enable/disable Sumy LSA summarization at upload time
2. **Depth Selector**: Control how much vision content to fetch (none/light/moderate/heavy)

### Existing Patterns to Follow
- **Git Integration Toggle**: `frontend/src/components/settings/integrations/GitIntegrationCard.vue`
  - System-level toggle with WebSocket updates
  - State managed in `UserSettings.vue` parent component

- **Context Depth Controls**: `frontend/src/components/settings/ContextPriorityConfig.vue`
  - Depth selectors for Tech Stack, Architecture, Testing, etc.
  - Props-based communication with parent

---

## Technical Details

### Files to Modify

#### 1. `frontend/src/views/UserSettings.vue` - Integrations Tab

**Current State** (lines 264-294):
```vue
<!-- Integrations -->
<v-window-item value="integrations">
  <v-card>
    <v-card-title>Integrations</v-card-title>
    <v-card-subtitle>Configure MCP tools and integrations</v-card-subtitle>
    <v-card-text>
      <!-- GiljoAI MCP Integration -->
      <McpIntegrationCard />

      <!-- Slash Command Setup -->
      <SlashCommandSetup />

      <!-- Claude Code Agent Export -->
      <ClaudeCodeExport />

      <!-- Serena MCP Integration -->
      <SerenaIntegrationCard ... />

      <!-- Git + 360 Memory Integration -->
      <GitIntegrationCard ... />
    </v-card-text>
  </v-card>
</v-window-item>
```

**Required Changes:**
```vue
<!-- ADD AFTER Git Integration Card -->
<VisionSummarizationCard
  :enabled="visionSummarizationEnabled"
  :loading="togglingVisionSummarization"
  @update:enabled="toggleVisionSummarization"
/>
```

**Add State Variables** (around line 336):
```javascript
const visionSummarizationEnabled = ref(false)
const togglingVisionSummarization = ref(false)
```

**Add Methods** (around line 477):
```javascript
async function checkVisionSummarizationStatus() {
  try {
    const settings = await api.get('/api/settings/general')
    visionSummarizationEnabled.value = settings.data.settings.vision_summarization_enabled || false
    console.log('[USER SETTINGS] Vision summarization status:', visionSummarizationEnabled.value)
  } catch (error) {
    console.error('[USER SETTINGS] Failed to check vision summarization status:', error)
    visionSummarizationEnabled.value = false
  }
}

async function toggleVisionSummarization(enabled) {
  console.log('[USER SETTINGS] Vision summarization toggled:', enabled)
  togglingVisionSummarization.value = true

  try {
    const result = await api.put('/api/settings/general', {
      settings: { vision_summarization_enabled: enabled }
    })
    visionSummarizationEnabled.value = result.data.settings.vision_summarization_enabled
    console.log('[USER SETTINGS] Vision summarization toggle result:', result.data)
  } catch (error) {
    console.error('[USER SETTINGS] Vision summarization toggle failed:', error)
    // Revert on error
    visionSummarizationEnabled.value = !enabled
  } finally {
    togglingVisionSummarization.value = false
  }
}
```

**Call in onMounted** (around line 489):
```javascript
await checkVisionSummarizationStatus()
```

#### 2. `frontend/src/components/settings/integrations/VisionSummarizationCard.vue` - NEW FILE

**Create Component** (follow GitIntegrationCard.vue pattern):
```vue
<template>
  <v-card class="mb-4" variant="outlined">
    <v-card-title class="d-flex align-center">
      <v-icon start color="primary">mdi-text-box-multiple</v-icon>
      Vision Summarization (Sumy LSA)
    </v-card-title>
    <v-card-subtitle>
      Compress large vision documents at upload time using Sumy LSA extraction
    </v-card-subtitle>
    <v-card-text>
      <v-alert type="info" variant="tonal" density="compact" class="mb-3">
        When enabled, vision documents are automatically summarized to reduce token usage while preserving key information.
      </v-alert>

      <v-switch
        :model-value="enabled"
        @update:model-value="$emit('update:enabled', $event)"
        :loading="loading"
        :disabled="loading"
        label="Enable vision summarization at upload"
        color="primary"
        hide-details
        data-testid="vision-summarization-toggle"
      />
    </v-card-text>
  </v-card>
</template>

<script setup>
defineProps({
  enabled: {
    type: Boolean,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:enabled'])
</script>
```

#### 3. `frontend/src/components/settings/ContextPriorityConfig.vue` - Context Tab

**Locate Depth Configuration Section** (around line 84-100):
```vue
<!-- Section: Depth Configuration -->
<div>
  <div class="text-subtitle-2 font-weight-medium mb-2">
    Depth Configuration (How Much Detail)
  </div>
  <v-alert type="info" variant="tonal" density="compact" class="mb-3">
    Control the level of detail for context fields with adjustable depth.
  </v-alert>

  <!-- Depth-controlled Context Rows -->
  <div
    v-for="context in depthControlledContexts"
    :key="context.key"
    class="context-row d-flex justify-space-between align-center py-2"
  >
    ...
  </div>
</div>
```

**Add to `depthControlledContexts` array** (in script section):
```javascript
const depthControlledContexts = ref([
  // ... existing contexts (Tech Stack, Architecture, Testing, etc.)
  {
    key: 'vision_documents',
    label: 'Vision Documents',
    depthOptions: [
      { title: 'None', value: 'none' },
      { title: 'Light (10K tokens)', value: 'light' },
      { title: 'Moderate (17.5K tokens)', value: 'moderate' },
      { title: 'Heavy (24K tokens)', value: 'heavy' }
    ]
  }
])
```

**No additional code changes needed** - existing component logic handles:
- Priority toggle
- Depth dropdown
- Save/reset functionality
- Backend API calls

#### 4. `api/endpoints/settings.py` - Backend API

**Add Settings Fields** (in SettingsService):
```python
# No code changes needed if these settings are already handled generically
# The existing PUT /api/settings/general endpoint accepts any settings dict

# Verify these keys are handled:
# - "vision_summarization_enabled" (boolean)
# - "vision_document_depth" (string: none|light|moderate|heavy)
```

**If validation is needed, add to SettingsUpdate model:**
```python
class VisionSettings(BaseModel):
    """Vision document settings"""
    vision_summarization_enabled: bool = False
    vision_document_depth: str = "moderate"  # none|light|moderate|heavy
```

---

## UI Layout

### Settings > Integrations Tab
```
┌─────────────────────────────────────────────┐
│ GiljoAI MCP Integration           [Card]    │
│ Slash Command Setup               [Card]    │
│ Claude Code Agent Export          [Card]    │
│ Serena MCP Integration            [Toggle]  │
│ Git + 360 Memory Integration      [Toggle]  │
│ Vision Summarization (Sumy LSA)   [Toggle]  │ ← NEW
│   └─ "Compress large vision documents..."  │
└─────────────────────────────────────────────┘
```

### Settings > Context Tab > Depth Configuration
```
┌─────────────────────────────────────────────┐
│ Product Core                    [Dropdown]  │
│ Tech Stack                      [Dropdown]  │
│ Architecture                    [Dropdown]  │
│ Testing                         [Dropdown]  │
│ 360 Memory                      [Dropdown]  │
│ Git History                     [Dropdown]  │
│ Agent Templates                 [Dropdown]  │
│ Vision Documents                [Dropdown]  │ ← NEW
│   └─ none|light|moderate|heavy             │
└─────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: TDD Setup (1-2 hours)
Write tests first using Vue Test Utils + Vitest:

```javascript
// tests/components/settings/integrations/VisionSummarizationCard.spec.js
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import VisionSummarizationCard from '@/components/settings/integrations/VisionSummarizationCard.vue'

describe('VisionSummarizationCard', () => {
  it('renders toggle switch', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: { enabled: false }
    })
    expect(wrapper.find('[data-testid="vision-summarization-toggle"]').exists()).toBe(true)
  })

  it('emits update:enabled when toggled', async () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: { enabled: false }
    })
    await wrapper.find('[data-testid="vision-summarization-toggle"]').trigger('click')
    expect(wrapper.emitted('update:enabled')).toBeTruthy()
    expect(wrapper.emitted('update:enabled')[0]).toEqual([true])
  })

  it('shows loading state', () => {
    const wrapper = mount(VisionSummarizationCard, {
      props: { enabled: false, loading: true }
    })
    const toggle = wrapper.find('[data-testid="vision-summarization-toggle"]')
    expect(toggle.attributes('disabled')).toBeDefined()
  })
})
```

```javascript
// tests/views/UserSettings.spec.js (additions)
describe('UserSettings - Vision Summarization', () => {
  it('loads vision summarization status on mount', async () => {
    const mockApi = {
      get: vi.fn().mockResolvedValue({
        data: { settings: { vision_summarization_enabled: true } }
      })
    }
    // ... mount component with mocked api
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.visionSummarizationEnabled).toBe(true)
  })

  it('toggles vision summarization via API', async () => {
    const mockApi = {
      put: vi.fn().mockResolvedValue({
        data: { settings: { vision_summarization_enabled: true } }
      })
    }
    // ... mount component
    await wrapper.vm.toggleVisionSummarization(true)
    expect(mockApi.put).toHaveBeenCalledWith('/api/settings/general', {
      settings: { vision_summarization_enabled: true }
    })
  })
})
```

```javascript
// tests/components/settings/ContextPriorityConfig.spec.js (additions)
describe('ContextPriorityConfig - Vision Documents Depth', () => {
  it('includes vision documents in depth controls', () => {
    const wrapper = mount(ContextPriorityConfig, {
      props: { gitIntegrationEnabled: true }
    })
    const contexts = wrapper.vm.depthControlledContexts
    expect(contexts.some(c => c.key === 'vision_documents')).toBe(true)
  })

  it('vision depth selector has 4 options', () => {
    const wrapper = mount(ContextPriorityConfig, {
      props: { gitIntegrationEnabled: true }
    })
    const visionContext = wrapper.vm.depthControlledContexts
      .find(c => c.key === 'vision_documents')
    expect(visionContext.depthOptions).toHaveLength(4)
    expect(visionContext.depthOptions.map(o => o.value))
      .toEqual(['none', 'light', 'moderate', 'heavy'])
  })
})
```

### Phase 2: Frontend Implementation (3-4 hours)
1. Create `VisionSummarizationCard.vue` component
2. Update `UserSettings.vue` to integrate new card
3. Add vision depth control to `ContextPriorityConfig.vue`
4. Test UI interactions manually
5. Run unit tests until all pass

### Phase 3: Backend Verification (1 hour)
1. Verify `PUT /api/settings/general` handles new settings keys
2. Add validation if needed
3. Test settings persistence via API calls

### Phase 4: Integration Testing (1-2 hours)
1. Start server with `python startup.py --dev`
2. Navigate to Settings > Integrations
3. Toggle vision summarization - verify saves
4. Navigate to Settings > Context
5. Change vision depth - verify saves
6. Reload page - verify settings persist
7. Check browser DevTools network tab for correct API calls

---

## Testing Requirements

### Unit Tests
- [ ] `VisionSummarizationCard` renders correctly
- [ ] Toggle emits `update:enabled` event
- [ ] Loading state disables toggle
- [ ] `UserSettings` loads vision summarization status on mount
- [ ] `UserSettings.toggleVisionSummarization()` calls API correctly
- [ ] Vision depth control appears in `ContextPriorityConfig`
- [ ] Vision depth has 4 options (none/light/moderate/heavy)

### Integration Tests
- [ ] Settings persist across page reloads
- [ ] Toggle state syncs with backend
- [ ] Depth selector value syncs with backend
- [ ] API errors revert toggle state

### Manual Testing
1. **Vision Summarization Toggle:**
   - Navigate to Settings > Integrations
   - Toggle "Vision Summarization (Sumy LSA)"
   - Verify loading spinner appears briefly
   - Verify toggle state persists after reload

2. **Vision Depth Selector:**
   - Navigate to Settings > Context
   - Locate "Vision Documents" in Depth Configuration
   - Change depth level (none → light → moderate → heavy)
   - Click "Save Changes"
   - Reload page - verify selection persists

3. **API Calls:**
   - Open browser DevTools > Network tab
   - Toggle vision summarization
   - Verify `PUT /api/settings/general` with correct payload
   - Change vision depth
   - Verify settings API called with new depth value

---

## Dependencies and Blockers

### Dependencies
- **0345a (Lean Orchestrator Instructions)** - MUST be complete
  - Ensures vision handling is properly refactored before UI changes
  - Without this, settings won't affect actual behavior

- **0345b (Sumy LSA Integration)** - RECOMMENDED
  - UI toggle controls Sumy LSA backend feature
  - Can proceed without 0345b (toggle just won't do anything yet)

### Known Blockers
- None

---

## Success Criteria

- [ ] Vision summarization toggle appears in Integrations tab
- [ ] Toggle persists state via `/api/settings/general` API
- [ ] Vision depth selector appears in Context tab
- [ ] Depth selector has 4 options: none/light/moderate/heavy
- [ ] Depth persists via existing context settings API
- [ ] All unit tests pass
- [ ] Manual testing confirms settings persist across reloads
- [ ] No console errors or warnings
- [ ] UI follows existing patterns (Git Integration, Context Depth)

---

## Rollback Plan

**If Things Go Wrong:**

1. **Remove VisionSummarizationCard component:**
   ```bash
   rm frontend/src/components/settings/integrations/VisionSummarizationCard.vue
   ```

2. **Revert UserSettings.vue changes:**
   ```bash
   git checkout HEAD -- frontend/src/views/UserSettings.vue
   ```

3. **Revert ContextPriorityConfig.vue changes:**
   ```bash
   git checkout HEAD -- frontend/src/components/settings/ContextPriorityConfig.vue
   ```

4. **No backend rollback needed** - generic settings API doesn't break if frontend doesn't send these keys

---

## Related Handovers

- **0345a**: Lean Orchestrator Instructions (DEPENDENCY)
- **0345b**: Sumy LSA Integration (RECOMMENDED)
- **0336**: Vision chunking rollback (background context)
- **0312-0316**: Context Management v2.0 (architecture foundation)

---

## Recommended Agent

**Frontend Tester** - This task requires:
1. Vue 3 component development
2. Vuetify UI patterns
3. Frontend unit testing (Vitest + Vue Test Utils)
4. Settings API integration
5. Manual UI testing

**Alternative:** **TDD Implementor** if backend validation changes are needed

---

## Additional Resources

### Reference Components
- `frontend/src/components/settings/integrations/GitIntegrationCard.vue` - Toggle pattern
- `frontend/src/components/settings/integrations/SerenaIntegrationCard.vue` - Simple toggle
- `frontend/src/components/settings/ContextPriorityConfig.vue` - Depth selector pattern

### API Documentation
- `api/endpoints/settings.py` - Settings endpoints reference
- `docs/SERVICES.md` - Service layer documentation

### Testing Patterns
- `frontend/tests/components/` - Existing component tests for patterns
- `frontend/tests/views/` - Existing view tests for integration patterns
