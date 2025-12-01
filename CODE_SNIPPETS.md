# Real-Time Git Integration Sync - Code Snippets

## File 1: ContextPriorityConfig.vue - Core Implementation

### Location
`F:\GiljoAI_MCP\frontend\src\components\settings\ContextPriorityConfig.vue`

### Import Section (Lines 96-107)
```typescript
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import setupService from '@/services/setupService'
import { useWebSocketV2 } from '@/composables/useWebSocket'

// Router for navigation
const router = useRouter()

// WebSocket for real-time updates
const { on, off } = useWebSocketV2()
```

### Handler Function (Lines 260-281)
```typescript
/**
 * Handle real-time Git integration updates from WebSocket
 * Called when Git integration is toggled in Integrations tab
 * @param {Object} data - WebSocket event data
 * @param {string} data.product_id - Product ID
 * @param {Object} data.settings - Git integration settings
 * @param {boolean} data.settings.enabled - Whether git integration is enabled
 */
function handleGitIntegrationUpdate(data) {
  if (!data || !data.settings) {
    console.warn('[CONTEXT PRIORITY CONFIG] Received invalid git integration update:', data)
    return
  }

  const newState = data.settings.enabled || false
  gitIntegrationEnabled.value = newState

  console.log('[CONTEXT PRIORITY CONFIG] Git integration updated via WebSocket:', {
    enabled: newState,
    timestamp: new Date().toISOString(),
  })

  // If Git integration was just enabled, Git History should become available immediately
  // If it was disabled, Git History controls should become disabled immediately
  if (newState) {
    console.log('[CONTEXT PRIORITY CONFIG] Git History context is now available')
  } else {
    console.log('[CONTEXT PRIORITY CONFIG] Git History context is now disabled')
  }
}
```

### Lifecycle Hooks (Lines 365-381)
```typescript
// Lifecycle
onMounted(async () => {
  // Check Git integration status first
  await checkGitIntegration()
  // Then fetch context config
  fetchConfig()

  // Listen for real-time Git integration changes via WebSocket
  on('product:git:settings:changed', handleGitIntegrationUpdate)
  console.log('[CONTEXT PRIORITY CONFIG] WebSocket listener registered for git integration updates')
})

onUnmounted(() => {
  // Clean up WebSocket listener to prevent memory leaks
  off('product:git:settings:changed', handleGitIntegrationUpdate)
  console.log('[CONTEXT PRIORITY CONFIG] WebSocket listener cleaned up')
})
```

### Expose for Testing (Line 429)
```typescript
// Expose for testing
defineExpose({
  contexts,
  priorityOptions,
  config,
  loading,
  saving,
  gitIntegrationEnabled,
  toggleContext,
  updatePriority,
  updateDepth,
  saveConfig,
  isContextDisabled,
  navigateToIntegrations,
  checkGitIntegration,
  handleGitIntegrationUpdate,  // <-- NEW
})
```

## File 2: Test Suite - Complete Test Coverage

### Location
`F:\GiljoAI_MCP\frontend\tests\unit\components\settings\ContextPriorityConfig.websocket-realtime.spec.js`

### Test Structure
```javascript
describe('ContextPriorityConfig.vue - WebSocket Real-Time Sync', () => {
  // Setup and teardown

  describe('Git Integration Real-Time Updates', () => {
    // 9 core tests
  })

  describe('Complete User Workflow', () => {
    // 1 integration test covering full user journey
  })
})
```

### Sample Test: WebSocket Event Handling
```javascript
it('should handle git integration enabled event from WebSocket', async () => {
  setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

  wrapper = mount(ContextPriorityConfig, {
    global: {
      plugins: [vuetify, pinia],
    },
  })

  await flushPromises()

  // Initially disabled
  expect(wrapper.vm.gitIntegrationEnabled).toBe(false)

  // Simulate WebSocket event: Git integration enabled
  const eventData = {
    product_id: 'product-123',
    settings: {
      enabled: true,
      commit_limit: 20,
      default_branch: 'main',
    },
  }

  wrapper.vm.handleGitIntegrationUpdate(eventData)

  // State should update immediately
  expect(wrapper.vm.gitIntegrationEnabled).toBe(true)
})
```

### Sample Test: Control Disabling Logic
```javascript
it('should enable Git History controls when integration is toggled ON', async () => {
  setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

  wrapper = mount(ContextPriorityConfig, {
    global: {
      plugins: [vuetify, pinia],
    },
  })

  await flushPromises()

  // Git History should be disabled initially
  expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)

  // Simulate WebSocket event: Git integration enabled
  wrapper.vm.handleGitIntegrationUpdate({
    product_id: 'product-123',
    settings: { enabled: true },
  })

  // Git History should now be enabled
  expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)
})
```

### Sample Test: Error Handling
```javascript
it('should handle missing or invalid WebSocket event data gracefully', async () => {
  setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

  wrapper = mount(ContextPriorityConfig, {
    global: {
      plugins: [vuetify, pinia],
    },
  })

  await flushPromises()

  // Test with null data
  wrapper.vm.handleGitIntegrationUpdate(null)
  expect(wrapper.vm.gitIntegrationEnabled).toBe(false) // Should not change

  // Test with missing settings
  wrapper.vm.handleGitIntegrationUpdate({ product_id: 'product-123' })
  expect(wrapper.vm.gitIntegrationEnabled).toBe(false) // Should not change

  // Test with undefined enabled field
  wrapper.vm.handleGitIntegrationUpdate({
    product_id: 'product-123',
    settings: { commit_limit: 20 },
  })
  expect(wrapper.vm.gitIntegrationEnabled).toBe(false) // Should default to false
})
```

### Sample Test: Complete User Workflow
```javascript
it('should complete full workflow: disabled -> toggle -> enabled', async () => {
  // Step 1: User opens Context tab with Git disabled
  setupServiceMock.getGitSettings.mockResolvedValue({ enabled: false })

  wrapper = mount(ContextPriorityConfig, {
    global: {
      plugins: [vuetify, pinia],
    },
  })

  await flushPromises()

  // Verify initial state
  expect(wrapper.vm.gitIntegrationEnabled).toBe(false)
  expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)
  console.log('Step 1: Git integration disabled, Git History controls disabled')

  // Step 2: Simulate user toggling Git integration in Integrations tab
  console.log('Step 2: User toggles Git integration in Integrations tab')
  wrapper.vm.handleGitIntegrationUpdate({
    product_id: 'product-123',
    settings: {
      enabled: true,
      commit_limit: 20,
      default_branch: 'main',
    },
  })

  await wrapper.vm.$nextTick()

  // Step 3: Verify Context tab immediately reflects the change
  expect(wrapper.vm.gitIntegrationEnabled).toBe(true)
  expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)
  console.log('Step 3: Context tab updated WITHOUT page refresh')
  console.log('Step 4: Git History controls are now enabled')

  // Verify Git History config can be modified
  expect(wrapper.vm.config.git_history.enabled).toBe(true)
})
```

## How It All Works Together

### Flow Diagram
```
User opens Settings
    |
    +-- Opens Context tab
    |   - Calls checkGitIntegration()
    |   - Fetches current state from API
    |   - Registers WebSocket listener: on('product:git:settings:changed', handleGitIntegrationUpdate)
    |
    +-- User navigates to Integrations tab
    |   - User toggles Git integration ON/OFF
    |
    +-- Backend processes toggle
    |   - Updates ProductService.git_integration
    |   - Emits WebSocket event: { product_id, settings: { enabled: true/false } }
    |
    +-- Context tab receives WebSocket event
    |   - handleGitIntegrationUpdate() called
    |   - gitIntegrationEnabled.value updated reactively
    |   - Vue template re-evaluates v-if and :disabled directives
    |   - Alert appears/disappears
    |   - Git History controls enable/disable
    |
    +-- NO PAGE REFRESH NEEDED
```

### Key Reactive Properties
```typescript
// State that reacts to WebSocket updates
const gitIntegrationEnabled = ref(false)  // Updated by WebSocket event

// Computed property that uses gitIntegrationEnabled
function isContextDisabled(contextKey: string): boolean {
  return contextKey === 'git_history' && !gitIntegrationEnabled.value
}

// Template uses the computed property
// v-if="!gitIntegrationEnabled"  - Alert shows when disabled
// :disabled="isContextDisabled('git_history')"  - Controls disabled when Git is off
```

## Testing the Implementation

### Unit Test Execution
```bash
cd frontend
npm run test:run -- tests/unit/components/settings/ContextPriorityConfig.websocket-realtime.spec.js
```

### Expected Output
```
✓ tests/unit/components/settings/ContextPriorityConfig.websocket-realtime.spec.js (10 tests)
  ✓ ContextPriorityConfig.vue - WebSocket Real-Time Sync
    ✓ Git Integration Real-Time Updates
      ✓ should display alert when Git integration is disabled on mount
      ✓ should register WebSocket listener for git integration updates on mount
      ✓ should handle git integration enabled event from WebSocket
      ✓ should handle git integration disabled event from WebSocket
      ✓ should enable Git History controls when integration is toggled ON
      ✓ should disable Git History controls when integration is toggled OFF
      ✓ should handle missing or invalid WebSocket event data gracefully
      ✓ should log appropriate messages when Git integration state changes
      ✓ should update alert visibility reactively when Git integration changes
    ✓ Complete User Workflow
      ✓ should complete full workflow: disabled -> toggle in Integrations -> enabled in Context

Test Files  1 passed (1)
Tests  10 passed (10)
Duration  908ms
```

## Key Implementation Features

### Memory Leak Prevention
```typescript
onUnmounted(() => {
  // Clean up to prevent memory leaks
  off('product:git:settings:changed', handleGitIntegrationUpdate)
  console.log('[CONTEXT PRIORITY CONFIG] WebSocket listener cleaned up')
})
```

### Error Handling
```typescript
function handleGitIntegrationUpdate(data) {
  if (!data || !data.settings) {
    console.warn('[CONTEXT PRIORITY CONFIG] Received invalid git integration update:', data)
    return  // Gracefully handle invalid data
  }
  // Process valid data
}
```

### Reactive Updates
```typescript
// These automatically trigger template updates when gitIntegrationEnabled changes
gitIntegrationEnabled.value = newState  // Reactive assignment
isContextDisabled('git_history')  // Recomputed when dependency changes
```

## Absolute File Paths (For Reference)

**Modified Files**:
- F:\GiljoAI_MCP\frontend\src\components\settings\ContextPriorityConfig.vue

**New Test File**:
- F:\GiljoAI_MCP\frontend\tests\unit\components\settings\ContextPriorityConfig.websocket-realtime.spec.js

**Related Files (Not Modified)**:
- F:\GiljoAI_MCP\frontend\src\composables\useWebSocket.js (WebSocket composable)
- F:\GiljoAI_MCP\src\giljo_mcp\services\product_service.py (Backend service, emits event)
