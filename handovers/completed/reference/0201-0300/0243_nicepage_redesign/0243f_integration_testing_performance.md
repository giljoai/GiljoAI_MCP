# Handover 0243f: Integration Testing & Performance Optimization

**Status**: 🔵 Ready for Implementation
**Priority**: P1 (High - Validation before production)
**Estimated Effort**: 12-16 hours
**Tool**: CCW (Cloud) for frontend testing
**Subagent**: frontend-tester (testing specialist)
**Dependencies**: ALL previous phases (0243a, 0243b, 0243c, 0243d, 0243e)
**Part**: 6 of 6 (FINAL) in Nicepage conversion series

---

## Mission

**Part A**: E2E integration testing for complete user workflows (8-10 hours)
**Part B**: Performance optimization and bundle size validation (4-6 hours)

**CRITICAL**: This is the final validation phase before production deployment.

---

## Part A: Integration Testing (E2E Workflow Validation)

### Test Scope

**3 Complete User Journeys**:
1. Launch Tab Workflow (staging project)
2. Implement Tab Workflow (agent management)
3. Multi-Tenant Isolation (security validation)

### Test Framework

**Playwright E2E Tests** (browser automation):
```bash
npm install --save-dev @playwright/test
npx playwright install
```

**Configuration**: `playwright.config.ts`
```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:7272',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    }
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:7272',
    reuseExistingServer: !process.env.CI
  }
})
```

### E2E Test 1: Launch Tab Workflow

**File**: `tests/e2e/launch-tab-workflow.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test.describe('Launch Tab Workflow (Job Staging)', () => {
  test.beforeEach(async ({ page }) => {
    // Login as test user
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')

    // Wait for navigation to complete
    await page.waitForURL('/projects')

    // Navigate to test project
    await page.click('[data-testid="projects-menu"]')
    await page.click('[data-testid="project-test-project"]')

    // Navigate to Launch tab
    await page.click('[data-testid="launch-tab"]')
    await page.waitForLoadState('networkidle')
  })

  test('User stages project and generates mission', async ({ page }) => {
    // Step 1: Verify unified container structure
    const container = page.locator('.main-container')
    await expect(container).toBeVisible()

    const containerStyles = await container.evaluate(el => {
      const styles = window.getComputedStyle(el)
      return {
        border: styles.border,
        borderRadius: styles.borderRadius,
        padding: styles.padding
      }
    })

    // Verify Nicepage design system applied
    expect(containerStyles.border).toContain('2px')
    expect(containerStyles.border).toContain('rgba(255, 255, 255, 0.2)')
    expect(containerStyles.borderRadius).toBe('16px')
    expect(containerStyles.padding).toBe('30px')

    // Step 2: Verify three equal-width panels
    const panels = page.locator('.panel')
    await expect(panels).toHaveCount(3)

    // Verify equal widths (each panel ~33.33%)
    const panelWidths = await panels.evaluateAll(elements =>
      elements.map(el => el.getBoundingClientRect().width)
    )
    const tolerance = 2 // Allow 2px difference for rounding
    expect(Math.abs(panelWidths[0] - panelWidths[1])).toBeLessThan(tolerance)
    expect(Math.abs(panelWidths[1] - panelWidths[2])).toBeLessThan(tolerance)

    // Step 3: Click "Stage Project" button
    const stageBtn = page.locator('.stage-button')
    await expect(stageBtn).toBeVisible()
    await expect(stageBtn).toContainText('Stage Project')
    await stageBtn.click()

    // Step 4: Verify toast notification
    const toast = page.locator('.v-snackbar')
    await expect(toast).toBeVisible({ timeout: 3000 })
    await expect(toast).toContainText('Orchestrator prompt copied')

    // Step 5: Wait for mission to appear (WebSocket event)
    const missionContent = page.locator('.mission-content')
    await expect(missionContent).toBeVisible({ timeout: 5000 })

    // Verify mission text is not empty
    const missionText = await missionContent.textContent()
    expect(missionText).toBeTruthy()
    expect(missionText!.length).toBeGreaterThan(50)

    // Step 6: Verify agent cards appear (WebSocket events)
    const agentCards = page.locator('.agent-card')
    await expect(agentCards).toHaveCount(3, { timeout: 5000 })

    // Verify each agent card has required elements
    for (let i = 0; i < 3; i++) {
      const card = agentCards.nth(i)
      await expect(card.locator('.agent-name')).toBeVisible()
      await expect(card.locator('.agent-type')).toBeVisible()
      await expect(card.locator('.agent-status')).toBeVisible()
    }

    // Step 7: Verify "Launch jobs" button enabled
    const launchBtn = page.locator('.launch-button')
    await expect(launchBtn).toBeVisible()
    await expect(launchBtn).toBeEnabled()
    await expect(launchBtn).toContainText('Launch jobs')

    // Step 8: Click "Launch jobs"
    await launchBtn.click()

    // Step 9: Verify navigation to Implement tab
    await page.waitForURL(/.*implement/, { timeout: 3000 })
    await expect(page).toHaveURL(/.*implement/)

    const selectedTab = page.locator('.v-tab--selected')
    await expect(selectedTab).toContainText('Implement')
  })

  test('Verify panel responsiveness on resize', async ({ page }) => {
    // Initial viewport: desktop
    await page.setViewportSize({ width: 1920, height: 1080 })

    const panels = page.locator('.panel')
    await expect(panels).toHaveCount(3)

    // Verify horizontal layout (flex-direction: row)
    const containerFlex = await page.locator('.main-container').evaluate(el =>
      window.getComputedStyle(el).flexDirection
    )
    expect(containerFlex).toBe('row')

    // Resize to tablet
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.waitForTimeout(500) // Allow CSS transition

    // Verify panels still visible (may stack vertically)
    await expect(panels).toHaveCount(3)

    // Resize to mobile
    await page.setViewportSize({ width: 375, height: 667 })
    await page.waitForTimeout(500)

    // Verify panels stack vertically
    const mobileContainerFlex = await page.locator('.main-container').evaluate(el =>
      window.getComputedStyle(el).flexDirection
    )
    expect(mobileContainerFlex).toBe('column')
  })

  test('Verify visual consistency with Nicepage design', async ({ page }) => {
    // Check gradient background
    const gradientBg = await page.locator('body').evaluate(el =>
      window.getComputedStyle(el).background
    )
    expect(gradientBg).toContain('linear-gradient')
    expect(gradientBg).toContain('111, 66, 193') // #7042C1 RGB

    // Check font family
    const fontFamily = await page.locator('.main-container').evaluate(el =>
      window.getComputedStyle(el).fontFamily
    )
    expect(fontFamily).toContain('Roboto')

    // Check button styling
    const stageBtn = page.locator('.stage-button')
    const btnStyles = await stageBtn.evaluate(el => {
      const styles = window.getComputedStyle(el)
      return {
        borderRadius: styles.borderRadius,
        textTransform: styles.textTransform,
        fontWeight: styles.fontWeight
      }
    })

    expect(btnStyles.borderRadius).toBe('30px')
    expect(btnStyles.textTransform).toBe('uppercase')
    expect(parseInt(btnStyles.fontWeight)).toBeGreaterThanOrEqual(500)
  })
})
```

### E2E Test 2: Implement Tab Workflow

**File**: `tests/e2e/implement-tab-workflow.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test.describe('Implement Tab Workflow (Job Implementation)', () => {
  test.beforeEach(async ({ page }) => {
    // Login and navigate to Implement tab
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'testpassword')
    await page.click('[data-testid="login-button"]')

    // Navigate to test project Implement tab
    await page.waitForURL('/projects')
    await page.goto('/projects/test-project?tab=implement')
    await page.waitForLoadState('networkidle')
  })

  test('User manages agents and sends messages', async ({ page }) => {
    // Step 1: Verify agent table displays
    const table = page.locator('.agents-table')
    await expect(table).toBeVisible()

    // Verify table headers
    const headers = table.locator('thead th')
    await expect(headers).toContainText(['Agent Name', 'Type', 'Status', 'Health', 'Actions'])

    // Step 2: Verify dynamic status (NOT hardcoded "Waiting.")
    const statusCells = page.locator('.status-cell')
    const firstStatus = await statusCells.first().textContent()

    // Status should be one of valid states
    const validStatuses = ['Waiting.', 'Working...', 'Complete', 'Cancelled', 'Error']
    expect(validStatuses.some(status => firstStatus?.includes(status))).toBeTruthy()

    // Step 3: Verify 5 action buttons (conditional display)
    const firstRow = page.locator('.agents-table tbody tr').first()
    const actionButtons = firstRow.locator('.actions-cell v-btn')
    const buttonCount = await actionButtons.count()

    // Should have at least 3 buttons (folder, info, play/cancel)
    expect(buttonCount).toBeGreaterThanOrEqual(3)
    expect(buttonCount).toBeLessThanOrEqual(5)

    // Step 4: Click "Play" button (if waiting)
    const playBtn = firstRow.locator('[icon="mdi-play"]')
    const isPlayVisible = await playBtn.isVisible()

    if (isPlayVisible) {
      await playBtn.click()

      // Verify toast notification
      const toast = page.locator('.v-snackbar')
      await expect(toast).toBeVisible({ timeout: 3000 })
      await expect(toast).toContainText('Launch prompt copied')
    }

    // Step 5: Send message to orchestrator
    const messageInput = page.locator('.message-input input')
    await expect(messageInput).toBeVisible()
    await messageInput.fill('Test message from E2E test')

    const sendBtn = page.locator('.send-btn')
    await expect(sendBtn).toBeEnabled()
    await sendBtn.click()

    // Verify message sent toast
    const messageSentToast = page.locator('.v-snackbar')
    await expect(messageSentToast).toContainText('Message sent', { timeout: 3000 })

    // Step 6: Verify message count updated
    const messagesCell = page.locator('.messages-sent-cell').first()
    await expect(messagesCell).toContainText('1', { timeout: 5000 })

    // Step 7: Cancel agent (if working)
    const cancelBtn = firstRow.locator('.cancel-btn')
    const isCancelVisible = await cancelBtn.isVisible()

    if (isCancelVisible) {
      await cancelBtn.click()

      // Verify confirmation dialog
      const dialog = page.locator('.v-dialog')
      await expect(dialog).toBeVisible({ timeout: 3000 })
      await expect(dialog).toContainText('Cancel Agent')

      // Confirm cancellation
      const confirmBtn = dialog.locator('.v-btn[color="error"]')
      await confirmBtn.click()

      // Verify cancellation toast
      const cancelToast = page.locator('.v-snackbar')
      await expect(cancelToast).toContainText('cancelled', { timeout: 3000 })

      // Wait for status update via WebSocket
      await expect(statusCells.first()).toContainText('Cancelled', { timeout: 5000 })
    }
  })

  test('Verify health status indicators', async ({ page }) => {
    // Verify health chip displays
    const healthChips = page.locator('.health-chip')
    await expect(healthChips.first()).toBeVisible()

    // Check health chip colors
    const healthChip = healthChips.first()
    const chipColor = await healthChip.evaluate(el =>
      window.getComputedStyle(el).backgroundColor
    )

    // Should be one of: green (Healthy), yellow (Stale), red (Critical)
    const validColors = [
      'rgb(76, 175, 80)',   // green
      'rgb(255, 235, 59)',  // yellow
      'rgb(244, 67, 54)'    // red
    ]
    expect(validColors.some(color => chipColor === color)).toBeTruthy()
  })

  test('Verify action buttons conditional display', async ({ page }) => {
    const rows = page.locator('.agents-table tbody tr')
    const rowCount = await rows.count()

    for (let i = 0; i < rowCount; i++) {
      const row = rows.nth(i)
      const status = await row.locator('.status-cell').textContent()

      // Check conditional button visibility
      if (status?.includes('Waiting.')) {
        // Should show: folder, info, play
        await expect(row.locator('[icon="mdi-folder"]')).toBeVisible()
        await expect(row.locator('[icon="mdi-information"]')).toBeVisible()
        await expect(row.locator('[icon="mdi-play"]')).toBeVisible()

        // Should NOT show: cancel, handover
        await expect(row.locator('[icon="mdi-cancel"]')).not.toBeVisible()
        await expect(row.locator('[icon="mdi-hand-back-right"]')).not.toBeVisible()
      } else if (status?.includes('Working...')) {
        // Should show: folder, info, cancel
        await expect(row.locator('[icon="mdi-folder"]')).toBeVisible()
        await expect(row.locator('[icon="mdi-information"]')).toBeVisible()
        await expect(row.locator('[icon="mdi-cancel"]')).toBeVisible()

        // Should NOT show: play
        await expect(row.locator('[icon="mdi-play"]')).not.toBeVisible()
      }
    }
  })

  test('Verify WebSocket real-time updates', async ({ page }) => {
    // Get initial status
    const firstRow = page.locator('.agents-table tbody tr').first()
    const initialStatus = await firstRow.locator('.status-cell').textContent()

    // Simulate status change (requires backend running)
    // This test validates WebSocket listener is active

    // Wait for potential WebSocket event (5 seconds)
    await page.waitForTimeout(5000)

    // Get updated status
    const updatedStatus = await firstRow.locator('.status-cell').textContent()

    // Status may or may not change depending on backend state
    // Key validation: no console errors during WebSocket events
    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    expect(consoleErrors).toHaveLength(0)
  })
})
```

### E2E Test 3: Multi-Tenant Isolation

**File**: `tests/e2e/multi-tenant-isolation.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test.describe('Multi-Tenant Isolation (Security)', () => {
  test('User A cannot see User B projects/agents', async ({ browser }) => {
    // Create two browser contexts (two users)
    const contextA = await browser.newContext()
    const contextB = await browser.newContext()

    const pageA = await contextA.newPage()
    const pageB = await contextB.newPage()

    // Login as User A (tenant1)
    await pageA.goto('/login')
    await pageA.fill('[data-testid="email-input"]', 'user-a@example.com')
    await pageA.fill('[data-testid="password-input"]', 'password')
    await pageA.click('[data-testid="login-button"]')
    await pageA.waitForURL('/projects')

    // Login as User B (tenant2)
    await pageB.goto('/login')
    await pageB.fill('[data-testid="email-input"]', 'user-b@example.com')
    await pageB.fill('[data-testid="password-input"]', 'password')
    await pageB.click('[data-testid="login-button"]')
    await pageB.waitForURL('/projects')

    // User A creates project
    await pageA.click('[data-testid="create-project"]')
    await pageA.fill('[data-testid="project-name"]', 'Tenant1 Project')
    await pageA.fill('[data-testid="project-description"]', 'Test isolation')
    await pageA.click('[data-testid="save-project"]')

    // Wait for project creation
    await pageA.waitForTimeout(2000)

    // User B should NOT see Tenant1 Project
    await pageB.goto('/projects')
    await pageB.waitForLoadState('networkidle')

    const projectsList = pageB.locator('.projects-list')
    await expect(projectsList).not.toContainText('Tenant1 Project')

    // User A stages project and spawns agents
    await pageA.click('[data-testid="project-tenant1-project"]')
    await pageA.click('[data-testid="launch-tab"]')
    await pageA.click('.stage-button')

    // Wait for agents to spawn
    const agentCards = pageA.locator('.agent-card')
    await expect(agentCards).toHaveCount(3, { timeout: 5000 })

    // Get agent IDs from User A
    const agentIds = await agentCards.evaluateAll(cards =>
      cards.map(card => card.getAttribute('data-agent-id'))
    )

    // User B navigates to Implement tab - should see ZERO agents
    await pageB.goto('/projects')

    // User B creates their own project
    await pageB.click('[data-testid="create-project"]')
    await pageB.fill('[data-testid="project-name"]', 'Tenant2 Project')
    await pageB.fill('[data-testid="project-description"]', 'Test isolation')
    await pageB.click('[data-testid="save-project"]')
    await pageB.waitForTimeout(2000)

    // Navigate to User B's project Implement tab
    await pageB.click('[data-testid="project-tenant2-project"]')
    await pageB.click('[data-testid="implement-tab"]')
    await pageB.waitForLoadState('networkidle')

    // Verify User B sees NO agents (or only their own)
    const userBAgents = pageB.locator('.agents-table tbody tr')
    const userBAgentCount = await userBAgents.count()

    // If User B has agents, verify none match User A's agent IDs
    if (userBAgentCount > 0) {
      const userBAgentIds = await userBAgents.evaluateAll(rows =>
        rows.map(row => row.getAttribute('data-agent-id'))
      )

      // No overlap between User A and User B agents
      const overlap = agentIds.filter(id => userBAgentIds.includes(id))
      expect(overlap).toHaveLength(0)
    } else {
      // User B has no agents (expected if fresh project)
      expect(userBAgentCount).toBe(0)
    }

    // Cleanup
    await contextA.close()
    await contextB.close()
  })

  test('WebSocket events isolated by tenant', async ({ browser }) => {
    // Create two browser contexts
    const contextA = await browser.newContext()
    const contextB = await browser.newContext()

    const pageA = await contextA.newPage()
    const pageB = await contextB.newPage()

    // Login both users
    await pageA.goto('/login')
    await pageA.fill('[data-testid="email-input"]', 'user-a@example.com')
    await pageA.fill('[data-testid="password-input"]', 'password')
    await pageA.click('[data-testid="login-button"]')

    await pageB.goto('/login')
    await pageB.fill('[data-testid="email-input"]', 'user-b@example.com')
    await pageB.fill('[data-testid="password-input"]', 'password')
    await pageB.click('[data-testid="login-button"]')

    // User A navigates to Implement tab
    await pageA.goto('/projects/tenant1-project?tab=implement')
    await pageA.waitForLoadState('networkidle')

    // User B navigates to Implement tab
    await pageB.goto('/projects/tenant2-project?tab=implement')
    await pageB.waitForLoadState('networkidle')

    // Track WebSocket events on User B's page
    const userBEvents: string[] = []
    pageB.on('websocket', ws => {
      ws.on('framereceived', event => {
        userBEvents.push(event.payload.toString())
      })
    })

    // User A triggers action (should NOT appear in User B's events)
    await pageA.click('.stage-button')

    // Wait for WebSocket events to propagate
    await pageA.waitForTimeout(3000)

    // Verify User B did NOT receive User A's events
    const userATenantEvents = userBEvents.filter(event =>
      event.includes('tenant1-project') || event.includes('user-a')
    )
    expect(userATenantEvents).toHaveLength(0)

    // Cleanup
    await contextA.close()
    await contextB.close()
  })

  test('API endpoints enforce tenant isolation', async ({ request }) => {
    // Login as User A
    const loginA = await request.post('/api/auth/login', {
      data: {
        email: 'user-a@example.com',
        password: 'password'
      }
    })
    const tokenA = (await loginA.json()).access_token

    // Login as User B
    const loginB = await request.post('/api/auth/login', {
      data: {
        email: 'user-b@example.com',
        password: 'password'
      }
    })
    const tokenB = (await loginB.json()).access_token

    // User A creates project
    const projectA = await request.post('/api/products/projects', {
      headers: { 'Authorization': `Bearer ${tokenA}` },
      data: {
        name: 'Tenant1 Project API',
        description: 'Test API isolation'
      }
    })
    const projectAId = (await projectA.json()).id

    // User B attempts to access User A's project (should fail)
    const unauthorizedAccess = await request.get(`/api/products/projects/${projectAId}`, {
      headers: { 'Authorization': `Bearer ${tokenB}` }
    })

    // Should return 403 Forbidden or 404 Not Found
    expect([403, 404]).toContain(unauthorizedAccess.status())

    // User B lists projects (should NOT include User A's project)
    const userBProjects = await request.get('/api/products/projects', {
      headers: { 'Authorization': `Bearer ${tokenB}` }
    })
    const projectsList = await userBProjects.json()

    const userAProjectInList = projectsList.find((p: any) => p.id === projectAId)
    expect(userAProjectInList).toBeUndefined()
  })
})
```

---

## Part B: Performance Optimization

### Performance Metrics

**Target Benchmarks**:
- Bundle size: <500KB gzipped
- LaunchTab initial render: <100ms
- JobsTab initial render: <100ms
- Status update render: <50ms
- Memory usage: <30MB per tab

### Bundle Size Optimization

**Analysis**:
```bash
npm run build
npm run analyze  # webpack-bundle-analyzer
```

**Package Updates** (`package.json`):
```json
{
  "scripts": {
    "analyze": "vite-bundle-visualizer --open"
  },
  "devDependencies": {
    "vite-bundle-visualizer": "^1.0.3"
  }
}
```

**Verification**:
```bash
# Check gzipped bundle size
ls -lh dist/assets/*.js | awk '{print $5, $9}'

# Expected output:
# 120K main-abc123.js.gz
# 80K vendor-def456.js.gz
# 50K LaunchTab-ghi789.js.gz
# Total: ~250KB gzipped ✅
```

**Optimization Tasks**:
1. ✅ Verify NO nicepage.css imported (would add 1.65MB)
2. ✅ Tree-shake unused Vuetify components
3. ✅ Code-split large components (lazy loading)
4. ✅ Optimize images (WebP format, lazy loading)

**Tree-Shaking Vuetify** (`vite.config.ts`):
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

export default defineConfig({
  plugins: [
    vue(),
    vuetify({
      autoImport: true,
      styles: { configFile: 'src/styles/settings.scss' }
    })
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'vuetify': ['vuetify'],
          'chart': ['chart.js']
        }
      }
    },
    chunkSizeWarningLimit: 500
  }
})
```

**Lazy Loading Example** (`router/index.ts`):
```typescript
// Before (eager loading)
import LaunchTab from '@/components/projects/LaunchTab.vue'
import JobsTab from '@/components/projects/JobsTab.vue'

// After (lazy loading)
const LaunchTab = () => import('@/components/projects/LaunchTab.vue')
const JobsTab = () => import('@/components/projects/JobsTab.vue')

const routes = [
  {
    path: '/projects/:id',
    component: () => import('@/views/ProjectDetail.vue'),
    children: [
      { path: 'launch', component: LaunchTab },
      { path: 'implement', component: JobsTab }
    ]
  }
]
```

**Image Optimization** (`LaunchTab.vue`):
```vue
<template>
  <div class="panel">
    <!-- Lazy load images -->
    <img
      src="@/assets/logo.webp"
      alt="Logo"
      loading="lazy"
      width="120"
      height="120"
    />
  </div>
</template>
```

### Render Performance

**Lighthouse Audit**:
```bash
# Start production build
npm run build
npm run preview

# Run Lighthouse in Chrome DevTools
# Or use CLI:
npx lighthouse http://localhost:7272/projects/test-project --view
```

**Target Scores**:
- Performance: >90
- First Contentful Paint: <1.5s
- Time to Interactive: <3.5s
- Largest Contentful Paint: <2.5s

**Optimization Tasks**:
1. ✅ Virtualize agent table (if >20 agents)
2. ✅ Debounce WebSocket event handlers
3. ✅ Use v-memo directive for static content
4. ✅ Optimize re-renders with computed properties

**Virtual Scrolling** (`JobsTab.vue`):
```vue
<template>
  <v-virtual-scroll
    :items="agents"
    :item-height="72"
    height="600"
  >
    <template v-slot:default="{ item }">
      <AgentTableRow :agent="item" />
    </template>
  </v-virtual-scroll>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAgentsStore } from '@/stores/agents'

const agentsStore = useAgentsStore()
const agents = computed(() => agentsStore.agents)
</script>
```

**Debounced WebSocket Handler** (`JobsTab.vue`):
```typescript
import { debounce } from 'lodash-es'

// Debounce status updates (avoid re-render spam)
const handleStatusUpdate = debounce((payload: any) => {
  agentsStore.updateAgentStatus(payload.agent_id, payload.status)
}, 100)

onMounted(() => {
  websocket.on('agent:status_changed', handleStatusUpdate)
})

onUnmounted(() => {
  websocket.off('agent:status_changed', handleStatusUpdate)
  handleStatusUpdate.cancel() // Cancel pending debounced calls
})
```

**v-memo Example** (`LaunchTab.vue`):
```vue
<template>
  <div
    v-for="agent in agents"
    :key="agent.id"
    v-memo="[agent.id, agent.status, agent.health]"
    class="agent-card"
  >
    <!-- Only re-render if agent.id, status, or health changes -->
    <div class="agent-name">{{ agent.name }}</div>
    <div class="agent-status">{{ agent.status }}</div>
    <HealthChip :health="agent.health" />
  </div>
</template>
```

**Computed Properties Optimization** (`JobsTab.vue`):
```typescript
// Before (re-computes on every render)
<template>
  <div>{{ agents.filter(a => a.status === 'Working...').length }}</div>
</template>

// After (cached computed property)
<script setup lang="ts">
const workingCount = computed(() =>
  agents.value.filter(a => a.status === 'Working...').length
)
</script>

<template>
  <div>{{ workingCount }}</div>
</template>
```

### Memory Optimization

**DevTools Memory Profiler**:
```bash
# Chrome DevTools → Memory → Take Heap Snapshot
# 1. Before: Snapshot 1
# 2. Navigate to LaunchTab
# 3. After: Snapshot 2
# 4. Compare: Snapshot 2 - Snapshot 1
# Expected: <5MB memory increase
```

**Optimization Tasks**:
1. ✅ Cleanup WebSocket listeners on unmount
2. ✅ Clear interval timers (staleness monitor)
3. ✅ Verify no memory leaks in event handlers
4. ✅ Use WeakMap for cached data

**Cleanup WebSocket Listeners** (`JobsTab.vue`):
```typescript
import { onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

const websocket = useWebSocket()

// Store handler references for cleanup
const handlers = {
  statusChanged: (payload: any) => handleStatusUpdate(payload),
  healthUpdate: (payload: any) => handleHealthUpdate(payload),
  jobComplete: (payload: any) => handleJobComplete(payload)
}

onMounted(() => {
  websocket.on('agent:status_changed', handlers.statusChanged)
  websocket.on('agent:health_update', handlers.healthUpdate)
  websocket.on('agent:job_complete', handlers.jobComplete)
})

onUnmounted(() => {
  // Critical: Remove ALL listeners
  websocket.off('agent:status_changed', handlers.statusChanged)
  websocket.off('agent:health_update', handlers.healthUpdate)
  websocket.off('agent:job_complete', handlers.jobComplete)
})
```

**Clear Interval Timers** (`useStalenessMonitor.ts`):
```typescript
import { onUnmounted } from 'vue'

export function useStalenessMonitor(agents: Ref<Agent[]>) {
  const stalenessInterval = setInterval(() => {
    checkStaleness(agents.value)
  }, 30000) // 30 seconds

  // Critical: Clear interval on unmount
  onUnmounted(() => {
    clearInterval(stalenessInterval)
  })

  return { stalenessInterval }
}
```

**WeakMap for Cached Data** (`JobsTab.vue`):
```typescript
// Before (strong references - memory leak risk)
const agentCache = new Map<string, Agent>()

// After (weak references - auto garbage collection)
const agentCache = new WeakMap<Agent, ComputedData>()

function getComputedData(agent: Agent) {
  if (!agentCache.has(agent)) {
    agentCache.set(agent, computeExpensiveData(agent))
  }
  return agentCache.get(agent)
}
```

**Memory Leak Detection Test**:
```typescript
// tests/e2e/memory-leak.spec.ts
import { test, expect } from '@playwright/test'

test('No memory leaks on tab navigation', async ({ page }) => {
  await page.goto('/projects/test-project')

  // Get initial memory
  const initialMemory = await page.evaluate(() => {
    return (performance as any).memory.usedJSHeapSize
  })

  // Navigate between tabs 10 times
  for (let i = 0; i < 10; i++) {
    await page.click('[data-testid="launch-tab"]')
    await page.waitForTimeout(500)
    await page.click('[data-testid="implement-tab"]')
    await page.waitForTimeout(500)
  }

  // Force garbage collection (Chrome only)
  await page.evaluate(() => {
    if ((window as any).gc) {
      (window as any).gc()
    }
  })

  // Get final memory
  const finalMemory = await page.evaluate(() => {
    return (performance as any).memory.usedJSHeapSize
  })

  // Memory increase should be <10MB after 10 navigations
  const memoryIncrease = (finalMemory - initialMemory) / 1024 / 1024
  expect(memoryIncrease).toBeLessThan(10)
})
```

---

## Test Execution Plan

### Phase 1: E2E Tests (8-10 hours)

**Installation**:
```bash
npm install --save-dev @playwright/test
npx playwright install chromium firefox webkit
```

**Run E2E tests**:
```bash
# All tests
npm run test:e2e

# Specific test file
npx playwright test tests/e2e/launch-tab-workflow.spec.ts

# Headed mode (watch browser)
npx playwright test --headed

# Debug mode
npx playwright test --debug

# Generate HTML report
npx playwright show-report
```

**Expected output**:
```
Running 14 tests using 3 workers

✓ Launch Tab Workflow (5 tests) - 45s
  ✓ User stages project and generates mission - 12s
  ✓ Verify panel responsiveness on resize - 8s
  ✓ Verify visual consistency with Nicepage design - 5s

✓ Implement Tab Workflow (6 tests) - 60s
  ✓ User manages agents and sends messages - 18s
  ✓ Verify health status indicators - 8s
  ✓ Verify action buttons conditional display - 12s
  ✓ Verify WebSocket real-time updates - 10s

✓ Multi-Tenant Isolation (3 tests) - 30s
  ✓ User A cannot see User B projects/agents - 12s
  ✓ WebSocket events isolated by tenant - 10s
  ✓ API endpoints enforce tenant isolation - 8s

14 passed (2m 15s)
```

### Phase 2: Performance Validation (4-6 hours)

**Run performance benchmarks**:
```bash
# Build production bundle
npm run build

# Analyze bundle size
npm run analyze

# Start preview server
npm run preview

# Run Lighthouse (manual in Chrome DevTools)
# Navigate to: http://localhost:7272/projects/test-project
# DevTools → Lighthouse → Generate report
```

**Lighthouse CLI**:
```bash
npx lighthouse http://localhost:7272/projects/test-project \
  --only-categories=performance \
  --view
```

**Expected Lighthouse Scores**:
```
Performance: 92/100 ✅
First Contentful Paint: 1.2s ✅
Largest Contentful Paint: 2.1s ✅
Time to Interactive: 3.2s ✅
Total Blocking Time: 180ms ✅
Cumulative Layout Shift: 0.02 ✅
```

**Memory profiling**:
```bash
# Manual process:
# 1. Open Chrome DevTools → Memory
# 2. Take "Heap snapshot" (before)
# 3. Navigate to LaunchTab
# 4. Take "Heap snapshot" (after)
# 5. Compare snapshots
# Expected: <5MB increase
```

---

## Deliverables

**Files to Create**:
- ✅ `playwright.config.ts`
- ✅ `tests/e2e/launch-tab-workflow.spec.ts`
- ✅ `tests/e2e/implement-tab-workflow.spec.ts`
- ✅ `tests/e2e/multi-tenant-isolation.spec.ts`
- ✅ `tests/e2e/memory-leak.spec.ts`
- ✅ `vite.config.ts` (updated with code splitting)
- ✅ `package.json` (updated with analyze script)

**Performance Reports**:
- ✅ Bundle size analysis (`npm run analyze` screenshot)
- ✅ Lighthouse audit report (>90 performance score)
- ✅ Memory profiling results (<30MB per tab)
- ✅ E2E test results (HTML report)

**Success Criteria**:
- [ ] All E2E tests passing (14+ tests)
- [ ] Bundle size: <500KB gzipped
- [ ] Lighthouse performance: >90
- [ ] Memory usage: <30MB per tab
- [ ] No console errors in production build
- [ ] Multi-tenant isolation verified (security)
- [ ] WebSocket event handling performant (<50ms updates)
- [ ] No memory leaks detected (<10MB increase after 10 navigations)

---

## Estimated Timeline

**Total**: 12-16 hours

**Breakdown**:
- E2E test setup (Playwright config): 2 hours
- Launch Tab E2E tests: 3 hours
- Implement Tab E2E tests: 3 hours
- Multi-tenant isolation tests: 2 hours
- Bundle size optimization: 2 hours
- Render performance optimization: 2 hours
- Memory profiling + fixes: 2-4 hours

**Parallel Execution** (if multiple agents):
- Part A (E2E tests): Agent 1 (8-10 hours)
- Part B (Performance): Agent 2 (4-6 hours)
- Total time: 10 hours (parallel) vs 16 hours (sequential)

---

## Agent Instructions

**You are a frontend-tester agent**:

### Part A: E2E Testing (8-10 hours)

1. **Install Playwright**:
   ```bash
   npm install --save-dev @playwright/test
   npx playwright install
   ```

2. **Create test files**:
   - `playwright.config.ts` (base configuration)
   - `tests/e2e/launch-tab-workflow.spec.ts` (5 tests)
   - `tests/e2e/implement-tab-workflow.spec.ts` (6 tests)
   - `tests/e2e/multi-tenant-isolation.spec.ts` (3 tests)

3. **Run tests**:
   ```bash
   npx playwright test --headed
   npx playwright show-report
   ```

4. **Fix any failures**:
   - Screenshot diffs (visual QA)
   - Timeout errors (increase waits)
   - Selector errors (update selectors)
   - WebSocket errors (verify backend running)

### Part B: Performance Optimization (4-6 hours)

1. **Analyze bundle size**:
   ```bash
   npm run build
   npm run analyze
   ```
   - Verify NO nicepage.css (1.65MB)
   - Verify code splitting (vendor chunks)
   - Target: <500KB gzipped

2. **Run Lighthouse audit**:
   ```bash
   npm run preview
   npx lighthouse http://localhost:7272 --view
   ```
   - Target: >90 performance score
   - Check FCP, LCP, TTI, TBT, CLS

3. **Memory profiling**:
   - Chrome DevTools → Memory → Heap Snapshot
   - Before/after navigation comparison
   - Target: <5MB increase per navigation

4. **Apply optimizations**:
   - Lazy load components (router)
   - Debounce WebSocket handlers
   - Add v-memo directives
   - Clear intervals on unmount
   - Use WeakMap for caching

### Reporting

**Report back with**:
1. **E2E Test Results**:
   ```
   ✅ 14/14 tests passing
   ⏱️ Total time: 2m 15s
   📊 HTML report: playwright-report/index.html
   ```

2. **Bundle Size**:
   ```
   ✅ Total: 245KB gzipped
   📦 main.js: 120KB
   📦 vendor.js: 80KB
   📦 LaunchTab.js: 45KB
   ```

3. **Lighthouse Score**:
   ```
   ✅ Performance: 92/100
   🎯 FCP: 1.2s
   🎯 LCP: 2.1s
   🎯 TTI: 3.2s
   ```

4. **Memory Usage**:
   ```
   ✅ Before: 15MB
   ✅ After: 19MB
   ✅ Increase: 4MB (<5MB target)
   ```

5. **Blockers** (if any):
   - Test failures with screenshots
   - Performance bottlenecks
   - Memory leaks detected

---

## CRITICAL: Pre-Production Checklist

**Before deploying to production**:

- [ ] All E2E tests passing (100% success rate)
- [ ] Bundle size <500KB gzipped
- [ ] Lighthouse performance >90
- [ ] No console errors in production build
- [ ] Multi-tenant isolation verified (security CRITICAL)
- [ ] WebSocket handlers cleaned up (no memory leaks)
- [ ] No nicepage.css imported (bundle bloat)
- [ ] Images optimized (WebP, lazy loading)
- [ ] Code splitting verified (webpack-bundle-analyzer)
- [ ] Memory profiling clean (<10MB increase)

**STOP**: If ANY of the above fail, DO NOT deploy. Report blockers to Orchestrator.

---

## Dependencies

**Required for testing**:
- Backend server running (http://localhost:7272)
- PostgreSQL database populated (test users, projects, agents)
- WebSocket server active (real-time updates)

**Test Users** (create via API or UI):
```json
{
  "user-a": {
    "email": "user-a@example.com",
    "password": "password",
    "tenant_key": "tenant1"
  },
  "user-b": {
    "email": "user-b@example.com",
    "password": "password",
    "tenant_key": "tenant2"
  },
  "test": {
    "email": "test@example.com",
    "password": "testpassword",
    "tenant_key": "test-tenant"
  }
}
```

**Test Project** (create via API):
```json
{
  "name": "test-project",
  "description": "E2E test project",
  "tenant_key": "test-tenant"
}
```

---

## Next Steps After Completion

**If all tests pass**:
1. Archive handover 0243f as COMPLETE
2. Update main README with production status
3. Deploy to production (staging first)
4. Monitor production metrics (Lighthouse, Sentry)

**If tests fail**:
1. Report failures to Orchestrator
2. Create bug fix handover (0243g)
3. Address blockers before production

---

## Related Documentation

- [Handover 0243a](./0243a_nicepage_launchpage_conversion.md) - LaunchTab foundation
- [Handover 0243b](./0243b_nicepage_jobs_agent_management.md) - JobsTab foundation
- [Handover 0243c](./0243c_statusboard_components.md) - Reusable components
- [Handover 0243d](./0243d_nicepage_visual_qa.md) - Visual QA validation
- [Handover 0243e](./0243e_unit_testing.md) - Unit test coverage
- [Playwright Docs](https://playwright.dev/)
- [Lighthouse Docs](https://developer.chrome.com/docs/lighthouse/)
- [Vite Bundle Analyzer](https://github.com/btd/rollup-plugin-visualizer)

---

**END OF HANDOVER 0243f** (6 of 6 - FINAL)
