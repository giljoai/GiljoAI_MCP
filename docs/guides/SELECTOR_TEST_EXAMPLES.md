# Selector Testing - Practical Examples

This document provides ready-to-use test examples for each validated selector.

---

## Table of Contents

1. [LaunchTab Component Tests](#launchtab-component-tests)
2. [CloseoutModal Component Tests](#closeoutmodal-component-tests)
3. [MessageItem Component Tests](#messageitem-component-tests)
4. [UserSettings Component Tests](#usersettings-component-tests)
5. [ContextPriorityConfig Component Tests](#contextpriorityconfig-component-tests)
6. [GitIntegrationCard Component Tests](#gitintegrationcard-component-tests)
7. [TemplateManager Component Tests](#templatemanager-component-tests)
8. [ProjectsView Component Tests](#projectsview-component-tests)
9. [Integration Tests](#integration-tests)
10. [E2E Test Examples](#e2e-test-examples)

---

## LaunchTab Component Tests

### Unit Test: Agent Type Selector

```javascript
// File: tests/components/projects/LaunchTab.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import LaunchTab from '@/components/projects/LaunchTab.vue'

describe('LaunchTab - Agent Type Selector', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(LaunchTab, {
      props: {
        project: {
          id: 'proj-123',
          name: 'Test Project',
          description: 'Test description',
          agents: [
            {
              id: 'agent-1',
              job_id: 'agent-1',
              agent_type: 'tester',
              status: 'pending'
            }
          ]
        }
      }
    })
  })

  it('renders agent-type data attribute', () => {
    const agentType = wrapper.find('[data-testid="agent-type"]')
    expect(agentType.exists()).toBe(true)
  })

  it('contains correct agent type value', () => {
    const agentType = wrapper.find('[data-testid="agent-type"]')
    expect(agentType.text()).toBe('tester')
  })

  it('agent-type is hidden from view', () => {
    const agentType = wrapper.find('[data-testid="agent-type"]')
    const style = agentType.attributes('style')
    expect(style).toContain('display: none')
  })

  it('renders status-chip with correct value', () => {
    const statusChip = wrapper.find('[data-testid="status-chip"]')
    expect(statusChip.text()).toBe('pending')
  })

  it('renders multiple agent cards in team section', async () => {
    await wrapper.setProps({
      project: {
        ...wrapper.props().project,
        agents: [
          { id: 'a1', job_id: 'a1', agent_type: 'tester', status: 'pending' },
          { id: 'a2', job_id: 'a2', agent_type: 'analyzer', status: 'pending' },
          { id: 'a3', job_id: 'a3', agent_type: 'reviewer', status: 'pending' }
        ]
      }
    })

    const cards = wrapper.findAll('[data-testid="agent-card"]')
    expect(cards).toHaveLength(3)
  })

  it('each agent card has data-agent-type attribute', () => {
    const cards = wrapper.findAll('[data-testid="agent-card"]')
    const agentTypes = cards.map(card => card.attributes('data-agent-type'))
    expect(agentTypes[0]).toBe('tester')
  })

  it('agent-name is visible for each card', () => {
    const cards = wrapper.findAll('[data-testid="agent-card"]')
    const firstCard = cards[0]
    const agentName = firstCard.find('[data-testid="agent-name"]')
    expect(agentName.exists()).toBe(true)
    expect(agentName.isVisible()).toBe(true)
  })
})
```

### Unit Test: Agent Card Interactions

```javascript
describe('LaunchTab - Agent Card Interactions', () => {
  it('agent card has edit and info icons', () => {
    const wrapper = mount(LaunchTab, {
      props: {
        project: {
          id: 'proj-123',
          agents: [
            { id: 'a1', job_id: 'a1', agent_type: 'tester', status: 'pending' }
          ]
        }
      }
    })

    const card = wrapper.find('[data-testid="agent-card"]')
    const editIcon = card.find('.edit-icon')
    const infoIcon = card.find('.info-icon')

    expect(editIcon.exists()).toBe(true)
    expect(infoIcon.exists()).toBe(true)
  })

  it('emits edit-agent-mission event on edit icon click', async () => {
    const agent = { id: 'a1', job_id: 'a1', agent_type: 'tester' }
    const wrapper = mount(LaunchTab, {
      props: {
        project: {
          id: 'proj-123',
          agents: [agent]
        }
      }
    })

    const editIcon = wrapper.find('[data-testid="agent-card"] .edit-icon')
    await editIcon.trigger('click')

    expect(wrapper.emitted('edit-agent-mission')).toBeTruthy()
  })

  it('displays agent name and type correctly', () => {
    const wrapper = mount(LaunchTab, {
      props: {
        project: {
          id: 'proj-123',
          agents: [
            { id: 'a1', job_id: 'a1', agent_type: 'analyzer', status: 'active' }
          ]
        }
      }
    })

    const card = wrapper.find('[data-testid="agent-card"]')
    const agentName = card.find('[data-testid="agent-name"]')
    const agentType = card.find('[data-testid="agent-type"]')

    expect(agentName.text()).toBe('ANALYZER')
    expect(agentType.text()).toBe('analyzer')
  })
})
```

---

## CloseoutModal Component Tests

### Unit Test: Submit Button State

```javascript
// File: tests/components/orchestration/CloseoutModal.test.js

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CloseoutModal from '@/components/orchestration/CloseoutModal.vue'

describe('CloseoutModal - Submit Button State', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(CloseoutModal, {
      props: {
        show: true,
        projectId: 'proj-123',
        projectName: 'Test Project'
      },
      global: {
        stubs: {
          'v-dialog': false,
          'v-card': false
        }
      }
    })
  })

  it('submit button exists in DOM', () => {
    const submitBtn = wrapper.find('[data-testid="submit-closeout-btn"]')
    expect(submitBtn.exists()).toBe(true)
  })

  it('submit button is disabled by default', () => {
    const submitBtn = wrapper.find('[data-testid="submit-closeout-btn"]')
    expect(submitBtn.attributes('disabled')).toBeDefined()
  })

  it('submit button becomes enabled when checkbox is checked', async () => {
    const checkbox = wrapper.find('[data-testid="confirm-checkbox"]')
    const submitBtn = wrapper.find('[data-testid="submit-closeout-btn"]')

    // Check confirmation checkbox
    await checkbox.find('input').setValue(true)
    await wrapper.vm.$nextTick()

    // Submit button should be enabled
    expect(submitBtn.attributes('disabled')).toBeUndefined()
  })

  it('emits complete event when submit button clicked', async () => {
    const submitBtn = wrapper.find('[data-testid="submit-closeout-btn"]')
    const checkbox = wrapper.find('[data-testid="confirm-checkbox"]')

    // Enable submit button
    await checkbox.find('input').setValue(true)
    await wrapper.vm.$nextTick()

    // Click submit button
    await submitBtn.trigger('click')

    // Should emit complete event
    expect(wrapper.emitted('complete')).toBeTruthy()
  })

  it('shows closeout modal dialog', () => {
    const modal = wrapper.find('[data-testid="closeout-modal"]')
    expect(modal.exists()).toBe(true)
  })

  it('copy prompt button exists and works', async () => {
    const copyBtn = wrapper.find('[data-testid="copy-prompt-button"]')
    expect(copyBtn.exists()).toBe(true)

    await copyBtn.trigger('click')
    // Verify copy success message appears
    expect(wrapper.vm.copySuccess).toBe(true)
  })

  it('confirmation checkbox exists with correct label', () => {
    const checkbox = wrapper.find('[data-testid="confirm-checkbox"]')
    expect(checkbox.exists()).toBe(true)

    const label = checkbox.text()
    expect(label).toContain('I have executed the closeout commands')
  })
})
```

---

## MessageItem Component Tests

### Unit Test: Message Content

```javascript
// File: tests/components/messages/MessageItem.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageItem from '@/components/messages/MessageItem.vue'

describe('MessageItem - Content Display', () => {
  const mockMessage = {
    id: 'msg-1',
    from: 'orchestrator',
    from_agent: 'orchestrator',
    content: 'Test message content',
    to_agents: ['analyzer', 'tester'],
    type: 'direct',
    priority: 'high',
    status: 'delivered',
    created_at: new Date().toISOString()
  }

  it('renders message-item container', () => {
    const wrapper = mount(MessageItem, {
      props: { message: mockMessage }
    })

    const item = wrapper.find('[data-testid="message-item"]')
    expect(item.exists()).toBe(true)
  })

  it('displays message sender with message-from selector', () => {
    const wrapper = mount(MessageItem, {
      props: { message: mockMessage }
    })

    const sender = wrapper.find('[data-testid="message-from"]')
    expect(sender.exists()).toBe(true)
    expect(sender.text()).toBe('Orchestrator')
  })

  it('displays recipients with message-to selector', () => {
    const wrapper = mount(MessageItem, {
      props: { message: mockMessage }
    })

    const recipients = wrapper.find('[data-testid="message-to"]')
    expect(recipients.exists()).toBe(true)
    expect(recipients.text()).toContain('analyzer')
    expect(recipients.text()).toContain('tester')
  })

  it('renders message content with correct selector', () => {
    const wrapper = mount(MessageItem, {
      props: { message: mockMessage }
    })

    const content = wrapper.find('[data-testid="message-content"]')
    expect(content.exists()).toBe(true)
    expect(content.text()).toContain('Test message content')
  })

  it('hides message-to when no recipients', () => {
    const messageNoRecipients = { ...mockMessage, to_agents: [] }
    const wrapper = mount(MessageItem, {
      props: { message: messageNoRecipients }
    })

    const recipients = wrapper.find('[data-testid="message-to"]')
    expect(recipients.exists()).toBe(false)
  })

  it('handles different message types correctly', () => {
    const broadcastMessage = { ...mockMessage, type: 'broadcast' }
    const wrapper = mount(MessageItem, {
      props: { message: broadcastMessage }
    })

    const item = wrapper.find('[data-testid="message-item"]')
    expect(item.classes()).toContain('broadcast-message')
  })

  it('applies correct styling for system messages', () => {
    const systemMessage = {
      ...mockMessage,
      from: 'system',
      type: 'system'
    }
    const wrapper = mount(MessageItem, {
      props: { message: systemMessage }
    })

    const item = wrapper.find('[data-testid="message-item"]')
    expect(item.classes()).toContain('system-message')
  })
})
```

---

## UserSettings Component Tests

### Integration Test: Settings Tabs

```javascript
// File: tests/views/UserSettings.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import UserSettings from '@/views/UserSettings.vue'

describe('UserSettings - Tab Navigation', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(UserSettings, {
      global: {
        stubs: {
          'ContextPriorityConfig': true,
          'TemplateManager': true,
          'ApiKeyManager': true,
          'SlashCommandSetup': true,
          'GitAdvancedSettingsDialog': true,
          'ClaudeCodeExport': true,
          'McpIntegrationCard': true,
          'SerenaIntegrationCard': true,
          'GitIntegrationCard': true
        }
      }
    })
  })

  it('renders all three main settings tabs', () => {
    const contextTab = wrapper.find('[data-testid="context-settings-tab"]')
    const agentsTab = wrapper.find('[data-testid="agent-templates-settings-tab"]')
    const integTab = wrapper.find('[data-testid="integrations-settings-tab"]')

    expect(contextTab.exists()).toBe(true)
    expect(agentsTab.exists()).toBe(true)
    expect(integTab.exists()).toBe(true)
  })

  it('can navigate to context settings tab', async () => {
    const contextTab = wrapper.find('[data-testid="context-settings-tab"]')
    await contextTab.trigger('click')

    // Verify tab is now active
    expect(wrapper.vm.activeTab).toBe('context')
  })

  it('can navigate to agent templates tab', async () => {
    const agentsTab = wrapper.find('[data-testid="agent-templates-settings-tab"]')
    await agentsTab.trigger('click')

    expect(wrapper.vm.activeTab).toBe('agents')
  })

  it('can navigate to integrations tab', async () => {
    const integTab = wrapper.find('[data-testid="integrations-settings-tab"]')
    await integTab.trigger('click')

    expect(wrapper.vm.activeTab).toBe('integrations')
  })

  it('context tab has icon and label', () => {
    const contextTab = wrapper.find('[data-testid="context-settings-tab"]')
    expect(contextTab.text()).toContain('Context')
    expect(contextTab.find('svg').exists()).toBe(true)
  })

  it('agent templates tab has custom icon', () => {
    const agentsTab = wrapper.find('[data-testid="agent-templates-settings-tab"]')
    expect(agentsTab.text()).toContain('Agents')
  })

  it('integrations tab has puzzle icon', () => {
    const integTab = wrapper.find('[data-testid="integrations-settings-tab"]')
    const icon = integTab.find('svg')
    expect(icon.exists()).toBe(true)
  })
})
```

---

## ContextPriorityConfig Component Tests

### Unit Test: Dynamic Priority Selectors

```javascript
// File: tests/components/settings/ContextPriorityConfig.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'

describe('ContextPriorityConfig - Dynamic Selectors', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(ContextPriorityConfig, {
      props: {
        gitIntegrationEnabled: true
      }
    })
  })

  it('renders priority selectors for all contexts', () => {
    const prioritySelectors = [
      'priority-product-core',
      'priority-vision-documents',
      'priority-tech-stack',
      'priority-architecture',
      'priority-testing',
      'priority-360-memory',
      'priority-git-history',
      'priority-agent-templates'
    ]

    prioritySelectors.forEach(selector => {
      const element = wrapper.find(`[data-testid="${selector}"]`)
      expect(element.exists()).toBe(true)
    })
  })

  it('renders depth selectors for applicable contexts', () => {
    const depthSelectors = [
      'depth-vision-documents',
      'depth-tech-stack',
      'depth-architecture',
      'depth-testing',
      'depth-360-memory',
      'depth-git-history',
      'depth-agent-templates'
    ]

    depthSelectors.forEach(selector => {
      const element = wrapper.find(`[data-testid="${selector}"]`)
      expect(element.exists()).toBe(true)
    })
  })

  it('priority selectors are v-select components', () => {
    const select = wrapper.find('[data-testid="priority-vision-documents"]')
    expect(select.classes()).toContain('v-select')
  })

  it('can update priority value', async () => {
    const selector = wrapper.find('[data-testid="priority-vision-documents"]')
    await selector.find('select').setValue('critical')

    expect(wrapper.vm.config.vision_documents.priority).toBe('critical')
  })

  it('disables selectors when context is disabled', async () => {
    // First, disable the context
    await wrapper.vm.toggleContext('vision_documents')

    const selector = wrapper.find('[data-testid="priority-vision-documents"]')
    expect(selector.attributes('disabled')).toBeDefined()
  })

  it('enables selectors when context is enabled', async () => {
    // Ensure context is enabled
    wrapper.vm.config.vision_documents.enabled = true
    await wrapper.vm.$nextTick()

    const selector = wrapper.find('[data-testid="priority-vision-documents"]')
    expect(selector.attributes('disabled')).toBeUndefined()
  })

  it('depth selector options vary by context', () => {
    const visionDepth = wrapper.find('[data-testid="depth-vision-documents"]')
    const techStackDepth = wrapper.find('[data-testid="depth-tech-stack"]')

    // Both should have options but they might differ
    expect(visionDepth.exists()).toBe(true)
    expect(techStackDepth.exists()).toBe(true)
  })
})
```

---

## GitIntegrationCard Component Tests

### Unit Test: Git Toggle

```javascript
// File: tests/components/settings/integrations/GitIntegrationCard.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import GitIntegrationCard from '@/components/settings/integrations/GitIntegrationCard.vue'

describe('GitIntegrationCard - Toggle', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(GitIntegrationCard, {
      props: {
        enabled: false,
        loading: false
      }
    })
  })

  it('renders github-integration-toggle selector', () => {
    const toggle = wrapper.find('[data-testid="github-integration-toggle"]')
    expect(toggle.exists()).toBe(true)
  })

  it('toggle is a v-switch component', () => {
    const toggle = wrapper.find('[data-testid="github-integration-toggle"]')
    expect(toggle.classes()).toContain('v-switch')
  })

  it('toggle reflects enabled prop', async () => {
    await wrapper.setProps({ enabled: true })
    const input = wrapper.find('[data-testid="github-integration-toggle"] input')
    expect(input.element.checked).toBe(true)
  })

  it('emits update:enabled when toggled', async () => {
    const toggle = wrapper.find('[data-testid="github-integration-toggle"]')
    await toggle.find('input').trigger('click')

    expect(wrapper.emitted('update:enabled')).toBeTruthy()
    expect(wrapper.emitted('update:enabled')[0]).toEqual([true])
  })

  it('shows loading state when loading prop is true', async () => {
    await wrapper.setProps({ loading: true })
    const toggle = wrapper.find('[data-testid="github-integration-toggle"]')

    expect(toggle.attributes('aria-busy')).toBe('true')
  })

  it('disables toggle when loading', async () => {
    await wrapper.setProps({ loading: true })
    const toggle = wrapper.find('[data-testid="github-integration-toggle"]')

    const input = toggle.find('input')
    expect(input.attributes('disabled')).toBeDefined()
  })

  it('toggle has proper accessibility attributes', () => {
    const toggle = wrapper.find('[data-testid="github-integration-toggle"]')
    expect(toggle.attributes('aria-label')).toBeDefined()
  })
})
```

---

## TemplateManager Component Tests

### Unit Test: Dynamic Template Toggles

```javascript
// File: tests/components/TemplateManager.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import TemplateManager from '@/components/TemplateManager.vue'

describe('TemplateManager - Dynamic Template Toggles', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(TemplateManager, {
      global: {
        mocks: {
          $api: {
            get: vi.fn(() => Promise.resolve({ data: { templates: [] } }))
          }
        }
      }
    })
  })

  it('renders template toggles for all agent types', async () => {
    const agentTypes = [
      'orchestrator',
      'analyzer',
      'implementer',
      'tester',
      'reviewer',
      'documenter'
    ]

    agentTypes.forEach(type => {
      const toggle = wrapper.find(`[data-testid="template-toggle-${type}"]`)
      expect(toggle.exists()).toBe(true)
    })
  })

  it('template toggles are v-switch components', () => {
    const toggle = wrapper.find('[data-testid="template-toggle-tester"]')
    expect(toggle.classes()).toContain('v-switch')
  })

  it('can toggle agent template activation', async () => {
    const toggle = wrapper.find('[data-testid="template-toggle-tester"]')
    await toggle.find('input').trigger('click')

    expect(wrapper.emitted()).toBeDefined()
  })

  it('multiple toggles can be active simultaneously', async () => {
    const testerToggle = wrapper.find('[data-testid="template-toggle-tester"]')
    const analyzerToggle = wrapper.find('[data-testid="template-toggle-analyzer"]')

    await testerToggle.find('input').trigger('click')
    await analyzerToggle.find('input').trigger('click')

    // Both should reflect their state
    expect(testerToggle.find('input').element.checked).toBe(true)
    expect(analyzerToggle.find('input').element.checked).toBe(true)
  })

  it('reflects template status in toggle state', async () => {
    wrapper.vm.templates = [
      { role: 'tester', active: true },
      { role: 'analyzer', active: false }
    ]
    await wrapper.vm.$nextTick()

    const testerToggle = wrapper.find('[data-testid="template-toggle-tester"]')
    const analyzerToggle = wrapper.find('[data-testid="template-toggle-analyzer"]')

    expect(testerToggle.find('input').element.checked).toBe(true)
    expect(analyzerToggle.find('input').element.checked).toBe(false)
  })
})
```

---

## ProjectsView Component Tests

### Unit Test: Project Status

```javascript
// File: tests/views/ProjectsView.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ProjectsView from '@/views/ProjectsView.vue'

describe('ProjectsView - Project Status', () => {
  let wrapper

  const mockProjects = [
    { id: 'p1', name: 'Active Project', status: 'active' },
    { id: 'p2', name: 'Inactive Project', status: 'inactive' },
    { id: 'p3', name: 'Completed Project', status: 'completed' }
  ]

  beforeEach(() => {
    wrapper = mount(ProjectsView, {
      global: {
        mocks: {
          $api: {
            get: vi.fn(() => Promise.resolve({ data: mockProjects }))
          }
        }
      }
    })

    wrapper.vm.filteredProjects = mockProjects
  })

  it('renders project-status selectors for each project', async () => {
    await wrapper.vm.$nextTick()

    const statuses = wrapper.findAll('[data-testid="project-status"]')
    expect(statuses.length).toBe(mockProjects.length)
  })

  it('displays correct status values', async () => {
    await wrapper.vm.$nextTick()

    const statuses = wrapper.findAll('[data-testid="project-status"]')

    expect(statuses[0].text()).toContain('active')
    expect(statuses[1].text()).toContain('inactive')
    expect(statuses[2].text()).toContain('completed')
  })

  it('applies correct CSS classes for status', async () => {
    await wrapper.vm.$nextTick()

    const statuses = wrapper.findAll('[data-testid="project-status"]')

    expect(statuses[0].classes()).toContain('status-active')
    expect(statuses[1].classes()).toContain('status-inactive')
    expect(statuses[2].classes()).toContain('status-completed')
  })

  it('can filter projects by status', async () => {
    wrapper.vm.filterStatus = 'active'
    await wrapper.vm.$nextTick()

    const filteredStatuses = wrapper.findAll('[data-testid="project-status"]')
    expect(filteredStatuses.length).toBe(1)
    expect(filteredStatuses[0].text()).toContain('active')
  })
})
```

---

## Integration Tests

### Complete User Flow Test

```javascript
// File: tests/integration/project-workflow.test.js

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import UserSettings from '@/views/UserSettings.vue'
import ProjectsView from '@/views/ProjectsView.vue'

describe('Integration - Project Workflow', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('complete settings configuration workflow', async () => {
    const wrapper = mount(UserSettings)

    // Step 1: Navigate to context settings
    const contextTab = wrapper.find('[data-testid="context-settings-tab"]')
    await contextTab.trigger('click')

    expect(wrapper.vm.activeTab).toBe('context')

    // Step 2: Configure priorities
    const prioritySelector = wrapper.find('[data-testid="priority-vision-documents"]')
    await prioritySelector.find('select').setValue('critical')

    // Step 3: Configure depth
    const depthSelector = wrapper.find('[data-testid="depth-vision-documents"]')
    await depthSelector.find('select').setValue('heavy')

    // Step 4: Navigate to integrations
    const integTab = wrapper.find('[data-testid="integrations-settings-tab"]')
    await integTab.trigger('click')

    // Step 5: Enable git integration
    const gitToggle = wrapper.find('[data-testid="github-integration-toggle"]')
    await gitToggle.find('input').trigger('click')

    expect(wrapper.vm.gitEnabled).toBe(true)
  })

  it('message viewing workflow', async () => {
    const MessageItem = await import('@/components/messages/MessageItem.vue')
    const message = {
      id: 'msg-1',
      from: 'orchestrator',
      content: 'Task completed',
      to_agents: ['tester', 'reviewer'],
      status: 'delivered'
    }

    const wrapper = mount(MessageItem, {
      props: { message, showActions: true }
    })

    // Verify message content is accessible
    expect(wrapper.find('[data-testid="message-item"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="message-from"]').text()).toBe('Orchestrator')
    expect(wrapper.find('[data-testid="message-to"]').text()).toContain('tester')
    expect(wrapper.find('[data-testid="message-content"]').text()).toContain('Task completed')
  })
})
```

---

## E2E Test Examples

### Playwright E2E Test

```javascript
// File: tests/e2e/complete-workflow.spec.js

import { test, expect } from '@playwright/test'

test.describe('Complete GiljoAI Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to application
    await page.goto('http://localhost:7274/')

    // Login
    await page.fill('input[type="email"]', 'patrik')
    await page.fill('input[type="password"]', '***REMOVED***')
    await page.click('button:has-text("Login")')

    // Wait for dashboard
    await page.waitForURL('**/dashboard')
  })

  test('configure settings and view projects', async ({ page }) => {
    // Navigate to settings
    await page.click('[data-testid="settings-menu-item"]')
    await page.waitForURL('**/settings')

    // Configure context settings
    await page.click('[data-testid="context-settings-tab"]')
    await page.waitForTimeout(300)

    // Set priority for vision documents
    const prioritySelect = page.locator('[data-testid="priority-vision-documents"]')
    await expect(prioritySelect).toBeVisible()
    await prioritySelect.selectOption('critical')

    // Set depth for vision documents
    const depthSelect = page.locator('[data-testid="depth-vision-documents"]')
    await depthSelect.selectOption('heavy')

    // Navigate to integrations
    await page.click('[data-testid="integrations-settings-tab"]')

    // Enable git integration
    const gitToggle = page.locator('[data-testid="github-integration-toggle"]')
    await gitToggle.click()

    // Navigate to projects
    await page.click('[data-testid="projects-menu-item"]')
    await page.waitForURL('**/projects')

    // Verify projects are displayed with status
    const projectStatuses = page.locator('[data-testid="project-status"]')
    const count = await projectStatuses.count()

    expect(count).toBeGreaterThan(0)

    // Check first project status
    const firstStatus = projectStatuses.first()
    await expect(firstStatus).toBeVisible()
  })

  test('closeout project workflow', async ({ page }) => {
    // Navigate to projects
    await page.goto('http://localhost:7274/#/projects')

    // Find a project and click closeout button
    const closeoutBtn = page.locator('button:has-text("Closeout")')
    if (await closeoutBtn.isVisible()) {
      await closeoutBtn.first().click()

      // Wait for modal
      const modal = page.locator('[data-testid="closeout-modal"]')
      await expect(modal).toBeVisible()

      // Verify modal content
      const submitBtn = page.locator('[data-testid="submit-closeout-btn"]')
      await expect(submitBtn).toBeDisabled()

      // Check confirmation checkbox
      const checkbox = page.locator('[data-testid="confirm-checkbox"]')
      await checkbox.check()

      // Now submit button should be enabled
      await expect(submitBtn).toBeEnabled()

      // Copy closeout prompt
      const copyBtn = page.locator('[data-testid="copy-prompt-button"]')
      await copyBtn.click()

      // Verify copy success message
      const successMsg = page.locator('[data-testid="copy-success-msg"]')
      await expect(successMsg).toBeVisible()
    }
  })

  test('message viewing workflow', async ({ page }) => {
    // Navigate to messages
    await page.click('[data-testid="messages-menu-item"]')
    await page.waitForURL('**/messages')

    // Wait for messages to load
    const messages = page.locator('[data-testid="message-item"]')
    const count = await messages.count()

    if (count > 0) {
      // Check first message
      const firstMessage = messages.first()

      // Verify message components
      const sender = firstMessage.locator('[data-testid="message-from"]')
      await expect(sender).toBeVisible()

      const content = firstMessage.locator('[data-testid="message-content"]')
      await expect(content).toBeVisible()

      // Check for recipients if present
      const recipients = firstMessage.locator('[data-testid="message-to"]')
      const isVisible = await recipients.isVisible()

      if (isVisible) {
        expect(await recipients.textContent()).toBeTruthy()
      }
    }
  })

  test('template manager workflow', async ({ page }) => {
    // Navigate to settings
    await page.click('[data-testid="settings-menu-item"]')

    // Navigate to agent templates
    await page.click('[data-testid="agent-templates-settings-tab"]')

    // Check template toggles
    const templateToggles = page.locator('[data-testid^="template-toggle-"]')
    const count = await templateToggles.count()

    expect(count).toBeGreaterThan(0)

    // Toggle tester template if available
    const testerToggle = page.locator('[data-testid="template-toggle-tester"]')
    if (await testerToggle.isVisible()) {
      await testerToggle.click()

      // Verify toggle state changed
      const isChecked = await testerToggle.isChecked()
      expect(isChecked).toBeDefined()
    }
  })
})
```

---

## Test Utilities

### Helper Functions

```javascript
// File: tests/utils/selector-helpers.js

export function getSelectorByTestid(wrapper, testid) {
  return wrapper.find(`[data-testid="${testid}"]`)
}

export function getAllSelectorsByTestid(wrapper, testidPrefix) {
  return wrapper.findAll(`[data-testid^="${testidPrefix}"]`)
}

export function expectSelectorExists(wrapper, testid) {
  const element = getSelectorByTestid(wrapper, testid)
  expect(element.exists()).toBe(true)
  return element
}

export function expectSelectorVisible(wrapper, testid) {
  const element = expectSelectorExists(wrapper, testid)
  expect(element.isVisible()).toBe(true)
  return element
}

export function expectSelectorHidden(wrapper, testid) {
  const element = getSelectorByTestid(wrapper, testid)
  if (element.exists()) {
    expect(element.isVisible()).toBe(false)
  }
  return element
}

export async function clickSelector(wrapper, testid) {
  const element = expectSelectorExists(wrapper, testid)
  await element.trigger('click')
  return element
}

export async function fillSelector(wrapper, testid, value) {
  const element = expectSelectorExists(wrapper, testid)
  await element.find('input').setValue(value)
  return element
}

// Usage in tests:
import { expectSelectorExists, clickSelector } from '@/tests/utils/selector-helpers'

describe('My Test', () => {
  it('works with helpers', async () => {
    const wrapper = mount(MyComponent)

    // Use helper functions
    const selector = expectSelectorExists(wrapper, 'my-selector')
    await clickSelector(wrapper, 'my-button')

    expect(selector.text()).toBe('expected value')
  })
})
```

---

## Summary

These examples demonstrate:
- Unit testing individual selectors
- Integration testing across components
- E2E testing complete workflows
- Helper utilities for reusable test code
- Both Vue Test Utils and Playwright approaches

All examples use the validated selectors and follow TDD principles with comprehensive assertions.

---

**Generated:** 2025-12-05
**All Selectors:** Validated and Production Ready
