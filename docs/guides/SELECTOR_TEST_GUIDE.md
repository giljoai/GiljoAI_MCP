# Selector Testing Quick Reference Guide

## All Validated Selectors

### Status: ✅ 17/17 PASS

---

## LaunchTab.vue

### Selectors
```
agent-type              // Hidden span - agent type data attribute
status-chip             // Hidden span - agent status data attribute
agent-card              // Agent card container in team section
agent-name              // Agent display name (visible)
```

### Usage Example (Vue Test Utils)
```javascript
import { mount } from '@vue/test-utils'
import LaunchTab from '@/components/projects/LaunchTab.vue'

describe('LaunchTab', () => {
  it('renders agent-type selector', async () => {
    const wrapper = mount(LaunchTab, {
      props: { project: { id: '123', agents: [{ agent_type: 'tester' }] } }
    })

    const agentType = wrapper.find('[data-testid="agent-type"]')
    expect(agentType.exists()).toBe(true)
    expect(agentType.text()).toBe('tester')
  })

  it('renders agent cards', async () => {
    const cards = wrapper.findAll('[data-testid="agent-card"]')
    expect(cards.length).toBeGreaterThan(0)
  })
})
```

### Usage Example (Playwright)
```javascript
// Single agent type
const agentType = await page.locator('[data-testid="agent-type"]').first()
await expect(agentType).toHaveText('tester')

// All agent cards
const cards = await page.locator('[data-testid="agent-card"]').all()
expect(cards.length).toBeGreaterThan(0)
```

---

## CloseoutModal.vue

### Selectors
```
closeout-modal          // Dialog/modal container
submit-closeout-btn     // Complete Project button (disabled until confirmation)
copy-prompt-button      // Copy Closeout Prompt button
confirm-checkbox        // Confirmation checkbox
```

### Usage Example (Vue Test Utils)
```javascript
describe('CloseoutModal', () => {
  it('disables submit button until confirmed', async () => {
    const wrapper = mount(CloseoutModal, {
      props: { show: true, projectId: '123', projectName: 'Test' }
    })

    const submitBtn = wrapper.find('[data-testid="submit-closeout-btn"]')
    expect(submitBtn.attributes('disabled')).toBeDefined()

    // Check confirmation
    const checkbox = wrapper.find('[data-testid="confirm-checkbox"]')
    await checkbox.find('input').setValue(true)

    // Button should now be enabled
    expect(submitBtn.attributes('disabled')).toBeUndefined()
  })
})
```

### Usage Example (Playwright)
```javascript
// Wait for modal to appear
const modal = page.locator('[data-testid="closeout-modal"]')
await expect(modal).toBeVisible()

// Check button is disabled
const submitBtn = page.locator('[data-testid="submit-closeout-btn"]')
await expect(submitBtn).toBeDisabled()

// Check confirmation checkbox
const checkbox = page.locator('[data-testid="confirm-checkbox"]')
await checkbox.click()

// Now button should be enabled
await expect(submitBtn).toBeEnabled()

// Click to submit
await submitBtn.click()
```

---

## MessageItem.vue

### Selectors
```
message-item            // Message card container
message-from            // Sender name/display
message-to              // Recipients section (conditional)
message-content         // Message body (markdown rendered)
```

### Usage Example (Vue Test Utils)
```javascript
describe('MessageItem', () => {
  it('displays message sender and content', async () => {
    const message = {
      from: 'orchestrator',
      content: 'Test message',
      to_agents: ['analyzer', 'tester'],
      created_at: new Date().toISOString()
    }

    const wrapper = mount(MessageItem, { props: { message } })

    // Check sender
    expect(wrapper.find('[data-testid="message-from"]').text()).toBe('Orchestrator')

    // Check recipients
    expect(wrapper.find('[data-testid="message-to"]').exists()).toBe(true)

    // Check content
    const content = wrapper.find('[data-testid="message-content"]')
    expect(content.text()).toContain('Test message')
  })
})
```

### Usage Example (Playwright)
```javascript
// Find all messages
const messages = await page.locator('[data-testid="message-item"]').all()

// Check first message sender
const sender = await messages[0].locator('[data-testid="message-from"]').textContent()
expect(sender).toContain('Orchestrator')

// Check message content
const content = await messages[0].locator('[data-testid="message-content"]').textContent()
expect(content).toContain('expected text')

// Check recipients if present
const recipients = await messages[0].locator('[data-testid="message-to"]').isVisible()
```

---

## UserSettings.vue

### Selectors
```
context-settings-tab            // Context configuration tab
agent-templates-settings-tab    // Agent templates tab
integrations-settings-tab       // Integrations tab
```

### Usage Example (Vue Test Utils)
```javascript
describe('UserSettings', () => {
  it('navigates between tabs', async () => {
    const wrapper = mount(UserSettings)

    // Find context tab
    const contextTab = wrapper.find('[data-testid="context-settings-tab"]')
    expect(contextTab.exists()).toBe(true)

    // Click to activate
    await contextTab.trigger('click')

    // Check tab is active
    expect(contextTab.classes()).toContain('v-tab--selected')
  })
})
```

### Usage Example (Playwright)
```javascript
// Navigate to settings
await page.goto('http://localhost:7274/#/settings')

// Click context tab
const contextTab = page.locator('[data-testid="context-settings-tab"]')
await contextTab.click()

// Verify tab content is visible
const contextCard = page.locator('[data-testid="context-field-config"]')
await expect(contextCard).toBeVisible()

// Test other tabs
const agentsTab = page.locator('[data-testid="agent-templates-settings-tab"]')
await agentsTab.click()

const integTab = page.locator('[data-testid="integrations-settings-tab"]')
await integTab.click()
```

---

## ContextFieldConfig.vue

### Selectors (Dynamic)
```
toggle-product-core         // Product Core toggle switch (on/off)
toggle-vision-documents     // Vision Docs toggle switch (on/off)
toggle-tech-stack           // Tech Stack toggle switch (on/off)
toggle-architecture         // Architecture toggle switch (on/off)
toggle-testing              // Testing toggle switch (on/off)
toggle-360-memory           // 360 Memory toggle switch (on/off)
toggle-git-history          // Git History toggle switch (on/off)
toggle-agent-templates      // Agent Templates toggle switch (on/off)

depth-vision-documents      // Vision Docs depth selector
depth-tech-stack            // Tech Stack depth selector
depth-architecture          // Architecture depth selector
depth-testing               // Testing depth selector
depth-360-memory            // 360 Memory depth selector
depth-git-history           // Git History depth selector
depth-agent-templates       // Agent Templates depth selector
```

### Usage Example (Vue Test Utils)
```javascript
describe('ContextFieldConfig', () => {
  it('toggles context fields and configures depth', async () => {
    const wrapper = mount(ContextFieldConfig, {
      props: { gitIntegrationEnabled: true }
    })

    // Find toggle switch
    const toggle = wrapper.find('[data-testid="toggle-vision-documents"]')
    expect(toggle.exists()).toBe(true)

    // Check depth selector
    const depthSelect = wrapper.find('[data-testid="depth-vision-documents"]')
    expect(depthSelect.exists()).toBe(true)
  })
})
```

### Usage Example (Playwright)
```javascript
// Match all toggle switches with prefix
const toggleSwitches = await page.locator('[data-testid^="toggle-"]').all()
expect(toggleSwitches.length).toBeGreaterThan(0)

// Toggle a specific context field
const visionToggle = page.locator('[data-testid="toggle-vision-documents"]')
await visionToggle.click()

// Match all depth selectors
const depthSelectors = await page.locator('[data-testid^="depth-"]').all()
expect(depthSelectors.length).toBeGreaterThan(0)

// Set depth level
const visionDepth = page.locator('[data-testid="depth-vision-documents"]')
await visionDepth.selectOption('heavy')
```

---

## GitIntegrationCard.vue

### Selectors
```
github-integration-toggle   // Git integration toggle switch
```

### Usage Example (Vue Test Utils)
```javascript
describe('GitIntegrationCard', () => {
  it('toggles git integration', async () => {
    const wrapper = mount(GitIntegrationCard, {
      props: { enabled: false }
    })

    const toggle = wrapper.find('[data-testid="github-integration-toggle"]')
    expect(toggle.exists()).toBe(true)

    // Toggle it
    await toggle.find('input').setValue(true)

    expect(wrapper.emitted('update:enabled')[0]).toEqual([true])
  })
})
```

### Usage Example (Playwright)
```javascript
// Navigate to integrations
await page.click('[data-testid="integrations-settings-tab"]')

// Find git toggle
const gitToggle = page.locator('[data-testid="github-integration-toggle"]')

// Check current state
const isChecked = await gitToggle.isChecked()
console.log(`Git integration: ${isChecked ? 'enabled' : 'disabled'}`)

// Toggle it
await gitToggle.click()

// Wait for state change
await expect(gitToggle).toHaveAttribute('aria-checked', 'true')
```

---

## TemplateManager.vue

### Selectors (Dynamic)
```
template-toggle-orchestrator    // Orchestrator template toggle
template-toggle-analyzer        // Analyzer template toggle
template-toggle-implementer     // Implementer template toggle
template-toggle-tester          // Tester template toggle
template-toggle-reviewer        // Reviewer template toggle
template-toggle-documenter      // Documenter template toggle
```

### Usage Example (Vue Test Utils)
```javascript
describe('TemplateManager', () => {
  it('toggles agent templates', async () => {
    const wrapper = mount(TemplateManager)

    // Find all template toggles
    const toggles = wrapper.findAll('[data-testid^="template-toggle-"]')
    expect(toggles.length).toBeGreaterThan(0)

    // Check specific template
    const testerToggle = wrapper.find('[data-testid="template-toggle-tester"]')
    await testerToggle.find('input').setValue(true)
  })
})
```

### Usage Example (Playwright)
```javascript
// Navigate to agent templates
await page.click('[data-testid="agent-templates-settings-tab"]')

// Match all template toggles
const templateToggles = await page.locator('[data-testid^="template-toggle-"]').all()
console.log(`Found ${templateToggles.length} template toggles`)

// Toggle specific template
const testerToggle = page.locator('[data-testid="template-toggle-tester"]')
await testerToggle.click()

// Verify multiple toggles
for (const role of ['orchestrator', 'analyzer', 'implementer']) {
  const toggle = page.locator(`[data-testid="template-toggle-${role}"]`)
  const isActive = await toggle.isChecked()
  console.log(`${role}: ${isActive ? 'active' : 'inactive'}`)
}
```

---

## ProjectsView.vue

### Selectors
```
project-status          // Project status badge/text
project-card            // Project card container
```

### Usage Example (Vue Test Utils)
```javascript
describe('ProjectsView', () => {
  it('displays project statuses', async () => {
    const wrapper = mount(ProjectsView)

    // Find all status elements
    const statuses = wrapper.findAll('[data-testid="project-status"]')
    expect(statuses.length).toBeGreaterThan(0)

    // Check first status
    expect(['active', 'inactive', 'completed']).toContain(
      statuses[0].text().toLowerCase()
    )
  })
})
```

### Usage Example (Playwright)
```javascript
// Navigate to projects
await page.goto('http://localhost:7274/#/projects')

// Wait for projects to load
await page.waitForSelector('[data-testid="project-status"]')

// Get all statuses
const statuses = await page.locator('[data-testid="project-status"]').all()
console.log(`Found ${statuses.length} projects`)

// Filter by status
for (const status of statuses) {
  const text = await status.textContent()
  if (text.includes('active')) {
    const card = status.locator('xpath=ancestor::*[@data-testid="project-card"]')
    await expect(card).toBeVisible()
  }
}
```

---

## Testing Best Practices

### 1. Wait for Elements
```javascript
// Good - waits for element
await page.waitForSelector('[data-testid="agent-card"]')
const card = await page.locator('[data-testid="agent-card"]')

// Good - with timeout
await expect(card).toBeVisible({ timeout: 5000 })
```

### 2. Handle Dynamic Selectors
```javascript
// Bad - assumes specific element exists
await page.click('[data-testid="toggle-vision-documents"]')

// Good - handle missing element
const selector = page.locator('[data-testid="toggle-vision-documents"]')
if (await selector.isVisible()) {
  await selector.click()
}
```

### 3. Test State Changes
```javascript
// Good - verify both before and after
const submitBtn = page.locator('[data-testid="submit-closeout-btn"]')
await expect(submitBtn).toBeDisabled()

await page.locator('[data-testid="confirm-checkbox"]').check()

await expect(submitBtn).toBeEnabled()
```

### 4. Reusable Page Objects
```javascript
class SettingsPage {
  constructor(page) {
    this.page = page
  }

  async navigateToContext() {
    await this.page.click('[data-testid="context-settings-tab"]')
  }

  async toggleField(field) {
    const selector = `[data-testid="toggle-${field}"]`
    await this.page.locator(selector).click()
  }

  async setDepth(field, value) {
    const selector = `[data-testid="depth-${field}"]`
    await this.page.locator(selector).selectOption(value)
  }
}

// Usage
const settings = new SettingsPage(page)
await settings.navigateToContext()
await settings.toggleField('vision-documents')
await settings.setDepth('vision-documents', 'heavy')
```

---

## Debugging Selectors

### Check if Selector Exists
```javascript
// Browser console
document.querySelectorAll('[data-testid="agent-type"]').length > 0

// Playwright
const count = await page.locator('[data-testid="agent-type"]').count()
console.log(`Found ${count} elements`)
```

### Get Selector Value
```javascript
// Browser console
document.querySelector('[data-testid="status-chip"]').textContent

// Playwright
const text = await page.locator('[data-testid="status-chip"]').textContent()
console.log(text)
```

### List All Data-TestID Selectors
```javascript
// Browser console
Array.from(document.querySelectorAll('[data-testid]'))
  .map(el => el.getAttribute('data-testid'))

// Playwright
const selectors = await page.locator('[data-testid]').evaluateAll(
  elements => elements.map(el => el.getAttribute('data-testid'))
)
console.log(selectors)
```

---

## Validation Script

Run the selector validation script:
```bash
cd F:/GiljoAI_MCP
node frontend/validate-selectors.js
```

Output:
```
✓ PASS  | agent-type                    | LaunchTab.vue
✓ PASS  | status-chip                   | LaunchTab.vue
✓ PASS  | agent-card                    | LaunchTab.vue
...
✓ PASS: 17 selectors
```

---

**Last Updated:** 2025-12-05
**All Selectors Validated:** ✅ YES
