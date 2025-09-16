# Vue Component Testing Plan for GiljoAI MCP

## Overview
This document outlines the testing strategy for Vue 3 components in the GiljoAI MCP dashboard, focusing on the reported issues and general component quality.

## Testing Framework Setup

### Required Dependencies
```json
{
  "devDependencies": {
    "@vue/test-utils": "^2.4.0",
    "@vitest/ui": "^0.34.0",
    "vitest": "^0.34.0",
    "jsdom": "^22.1.0",
    "@testing-library/vue": "^7.0.0"
  }
}
```

### Vitest Configuration
```javascript
// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.js'
  }
})
```

## Priority Test Areas

### 1. Event Handling Issues (Dashboard Popups)
**Issue**: Missing @click.stop on popup dialogs causing event bubbling

**Test Strategy**:
- Test event propagation on all modal/dialog components
- Verify click outside to close functionality
- Ensure nested clicks don't bubble to parent handlers

**Example Test**:
```javascript
import { mount } from '@vue/test-utils'
import PopupDialog from '@/components/PopupDialog.vue'

describe('PopupDialog', () => {
  it('should stop click propagation on dialog content', async () => {
    const parentClickHandler = vi.fn()
    const wrapper = mount(PopupDialog, {
      global: {
        stubs: ['v-dialog', 'v-card']
      }
    })
    
    // Mount with parent container
    const parent = mount({
      template: `
        <div @click="parentClickHandler">
          <PopupDialog />
        </div>
      `,
      components: { PopupDialog },
      methods: { parentClickHandler }
    })
    
    // Click on dialog content
    await parent.find('.dialog-content').trigger('click')
    
    // Parent handler should not be called
    expect(parentClickHandler).not.toHaveBeenCalled()
  })
})
```

### 2. Vuetify 3 Component Integration
**Components to Test**:
- VDataTable (agent list)
- VDialog (modals)
- VBtn (action buttons)
- VProgressLinear (progress indicators)
- VThemeProvider (dark/light mode)

**Test Focus**:
- Props validation
- Event emissions
- Slot content rendering
- Theme switching

### 3. WebSocket Real-time Updates
**Test Strategy**:
- Mock WebSocket connections
- Test component reactivity to incoming messages
- Verify state updates propagate correctly

**Example Test**:
```javascript
import { mount } from '@vue/test-utils'
import AgentStatus from '@/components/AgentStatus.vue'
import { vi } from 'vitest'

describe('AgentStatus WebSocket Updates', () => {
  let mockWebSocket
  
  beforeEach(() => {
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn()
    }
    global.WebSocket = vi.fn(() => mockWebSocket)
  })
  
  it('should update agent status on WebSocket message', async () => {
    const wrapper = mount(AgentStatus)
    
    // Simulate WebSocket message
    const messageHandler = mockWebSocket.addEventListener.mock.calls
      .find(call => call[0] === 'message')[1]
    
    messageHandler({
      data: JSON.stringify({
        type: 'agent_update',
        agent: 'tester',
        status: 'active'
      })
    })
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('.agent-status').text()).toContain('active')
  })
})
```

### 4. Cross-Platform Path Display
**Test Focus**:
- Ensure paths display with forward slashes
- Test path truncation for long paths
- Verify clickable paths work correctly

### 5. Accessibility Testing
**Requirements**:
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- Color contrast in themes

**Test Example**:
```javascript
import { mount } from '@vue/test-utils'
import { axe } from 'jest-axe'
import Dashboard from '@/components/Dashboard.vue'

describe('Dashboard Accessibility', () => {
  it('should be accessible', async () => {
    const wrapper = mount(Dashboard)
    const results = await axe(wrapper.element)
    expect(results).toHaveNoViolations()
  })
  
  it('should support keyboard navigation', async () => {
    const wrapper = mount(Dashboard)
    
    // Tab through interactive elements
    await wrapper.trigger('keydown.tab')
    expect(document.activeElement).toBe(wrapper.find('button').element)
  })
})
```

## Test Organization

### Directory Structure
```
frontend/
├── tests/
│   ├── unit/
│   │   ├── components/
│   │   │   ├── AgentList.spec.js
│   │   │   ├── ProjectManager.spec.js
│   │   │   ├── MessageRouter.spec.js
│   │   │   └── PopupDialog.spec.js
│   │   ├── stores/
│   │   │   └── agent.spec.js
│   │   └── utils/
│   │       └── pathResolver.spec.js
│   ├── integration/
│   │   ├── websocket.spec.js
│   │   └── api.spec.js
│   ├── e2e/
│   │   └── dashboard.spec.js
│   └── setup.js
```

## Component Test Checklist

### For Each Component:
- [ ] Props validation and defaults
- [ ] Event emissions with correct payloads
- [ ] Computed properties update correctly
- [ ] Methods handle edge cases
- [ ] Slots render properly
- [ ] Vuetify components integrate correctly
- [ ] Error states display appropriately
- [ ] Loading states show/hide correctly
- [ ] Accessibility requirements met
- [ ] Theme switching works

## Specific Issue Tests

### 1. PopupDialog Click Stop Test
```javascript
// tests/unit/components/PopupDialog.spec.js
import { mount } from '@vue/test-utils'
import PopupDialog from '@/components/PopupDialog.vue'

describe('PopupDialog Event Handling', () => {
  it('should have @click.stop on dialog container', () => {
    const wrapper = mount(PopupDialog)
    const dialog = wrapper.find('[data-test="dialog-container"]')
    
    // Check for stop modifier in component
    const clickListeners = wrapper.vm.$options.components.VDialog?.emits?.click
    expect(clickListeners).toContain('stop')
  })
})
```

### 2. Path Display Test
```javascript
// tests/unit/utils/pathDisplay.spec.js
import { formatPath } from '@/utils/pathDisplay'

describe('Path Display Formatting', () => {
  it('should convert backslashes to forward slashes', () => {
    const windowsPath = 'C:\\Users\\test\\Documents'
    const formatted = formatPath(windowsPath)
    expect(formatted).toBe('C:/Users/test/Documents')
  })
})
```

## Testing Commands

```json
// package.json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "test:watch": "vitest --watch",
    "test:components": "vitest tests/unit/components",
    "test:a11y": "vitest tests/accessibility"
  }
}
```

## Continuous Testing Strategy

1. **Pre-commit**: Run unit tests for changed components
2. **Pre-push**: Run full test suite
3. **CI/CD**: Run all tests including E2E
4. **Monitoring**: Track test coverage metrics

## Test Coverage Goals

- Unit Tests: 80% coverage minimum
- Integration Tests: Critical paths covered
- E2E Tests: Main user workflows
- Accessibility: All interactive components

## Implementation Priority

1. **Immediate** (Fixes for reported issues):
   - PopupDialog event handling
   - Path display formatting
   - WebSocket message handling

2. **High** (Core functionality):
   - Agent management components
   - Project navigation
   - Message routing display

3. **Medium** (UI polish):
   - Theme switching
   - Animation performance
   - Error boundaries

4. **Low** (Nice to have):
   - Visual regression tests
   - Performance benchmarks
   - Storybook integration

## Notes for Fixer Agent

When implementing fixes:
1. Always add corresponding tests
2. Run tests before committing
3. Update test documentation
4. Maintain test coverage above 80%

## Resources

- [Vue Test Utils Documentation](https://test-utils.vuejs.org/)
- [Vitest Documentation](https://vitest.dev/)
- [Testing Library Vue](https://testing-library.com/docs/vue-testing-library/intro/)
- [Vuetify Testing Guide](https://vuetifyjs.com/en/getting-started/unit-testing/)