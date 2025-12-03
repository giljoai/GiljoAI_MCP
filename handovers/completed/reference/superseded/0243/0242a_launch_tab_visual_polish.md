# Handover 0242a: Launch Tab Visual Polish

**Status**: 🟡 Pending
**Priority**: P1 (High)
**Estimated Effort**: 4-6 hours
**Tool**: CCW (Cloud) - Pure Vue/CSS refinements
**Subagent**: tdd-implementor (test-driven development)
**Dependencies**: None (first in 0242 series)

---

## Executive Summary

Refine `LaunchTab.vue` to pixel-perfect match the Nicepage design specification (`Launch Tab.jpg` screenshot). This is an **incremental refinement**, NOT a rewrite. Preserve all working WebSocket reactivity, clipboard handling, and agent tracking logic from the 0241 implementation.

**Focus Areas**:
1. Layout structure (unified container, 3-panel grid)
2. Color precision (border rgba values, background colors)
3. Top action bar positioning (left/center/right)
4. Orchestrator card styling (avatar colors, pill shape)

**What NOT to Touch**:
- `<script>` section logic (WebSocket handlers, reactive refs, clipboard code)
- Agent tracking Set (prevents duplicates)
- Mission text reactivity
- Claude Code CLI toggle logic

---

## Reference Materials

**Primary Screenshot**: `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Launch Tab.jpg`
**Nicepage HTML**: `F:\Nicepage\MCP Server\index.html`
**Current Implementation**: `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue`
**Archived Handover**: `F:\GiljoAI_MCP\handovers\completed\0241_emergency_gui_fix_match_screenshots-C.md`

---

## Detailed Tasks

### Task 1: Unified Container Border (1 hour)

**Current State**: Container may have inconsistent border styling.

**Required Changes**:
```vue
<style scoped>
.unified-container {
  border: 2px solid rgba(255, 255, 255, 0.2);  /* Exact rgba from screenshot */
  border-radius: 16px;                         /* Exact pixel value */
  padding: 30px;                               /* Internal spacing */
  background: rgba(14, 28, 45, 0.5);          /* Dark blue translucent */
  margin-bottom: 24px;
}
</style>
```

**Verification**:
- Inspect element in DevTools
- Border should be 2px solid with exact rgba(255, 255, 255, 0.2)
- Border-radius exactly 16px
- Padding exactly 30px on all sides

---

### Task 2: Three-Panel Grid Layout (1 hour)

**Current State**: Panels may not have exact proportions or spacing.

**Required Changes**:
```vue
<template>
  <div class="three-panel-grid">
    <!-- Panel 1: Project Description -->
    <div class="panel">
      <div class="panel-header">Project Description</div>
      <div class="panel-content">{{ projectDescription }}</div>
    </div>

    <!-- Panel 2: Orchestrator Mission -->
    <div class="panel">
      <div class="panel-header">Orchestrator Mission</div>
      <div class="panel-content">
        <!-- Empty state: Document icon -->
        <div v-if="!missionText" class="empty-state">
          <v-icon size="80" color="rgba(255, 255, 255, 0.15)">
            mdi-file-document-outline
          </v-icon>
        </div>
        <!-- Mission text -->
        <div v-else class="mission-text">{{ missionText }}</div>
      </div>
    </div>

    <!-- Panel 3: Agent Team -->
    <div class="panel">
      <div class="panel-header">Agent Team</div>
      <div class="panel-content">
        <!-- Agent cards render here -->
      </div>
    </div>
  </div>
</template>

<style scoped>
.three-panel-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;  /* Equal width columns */
  gap: 24px;                           /* Exact spacing between panels */
}

.panel {
  display: flex;
  flex-direction: column;
}

.panel-header {
  font-size: 14px;
  color: #ccc;
  margin-bottom: 16px;
  /* DO NOT use text-transform: uppercase */
}

.panel-content {
  min-height: 400px;  /* Ensures consistent panel heights */
  flex: 1;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
</style>
```

**Verification**:
- Measure column widths in DevTools (should be equal)
- Gap between panels exactly 24px
- Panel headers NOT uppercase (remove text-transform if present)
- Panel content min-height 400px

---

### Task 3: Top Action Bar (1 hour)

**Current State**: Button positioning may not match screenshot layout.

**Required Changes**:
```vue
<template>
  <div class="top-action-bar">
    <!-- LEFT: Stage project button -->
    <v-btn
      outlined
      class="stage-button"
      @click="handleStageProject"
    >
      Stage project
    </v-btn>

    <!-- CENTER: Waiting status -->
    <div class="waiting-status">
      Waiting: {{ waitingFor }}
    </div>

    <!-- RIGHT: Launch jobs button -->
    <v-btn
      :disabled="!canLaunch"
      :class="canLaunch ? 'launch-enabled' : 'launch-disabled'"
      @click="handleLaunchJobs"
    >
      Launch jobs
    </v-btn>
  </div>
</template>

<style scoped>
.top-action-bar {
  display: flex;
  justify-content: space-between;  /* LEFT, CENTER, RIGHT positioning */
  align-items: center;
  margin-bottom: 24px;
  padding: 16px 0;
}

.stage-button {
  border: 2px solid #ffd700;    /* Yellow outlined */
  background: transparent !important;
  color: #ffd700;
}

.waiting-status {
  color: #ffd700;               /* Yellow text */
  font-style: italic;           /* Italic style */
  font-size: 18px;
  text-align: center;
  flex: 1;                      /* Takes center space */
}

.launch-disabled {
  background: #666 !important;  /* Grey when disabled */
  color: #ccc;
}

.launch-enabled {
  background: #ffd700 !important;  /* Yellow when enabled */
  color: #000;                     /* Black text on yellow */
}
</style>
```

**Verification**:
- Stage button: TOP LEFT, yellow outlined border, transparent background
- Waiting status: CENTER, yellow italic text
- Launch button: TOP RIGHT, grey when disabled, yellow when enabled
- Flexbox `justify-content: space-between` ensures correct positioning

---

### Task 4: Orchestrator Mission Panel (0.5 hour)

**Current State**: Empty state may not show correct icon.

**Required Changes**:
```vue
<template>
  <div class="panel">
    <div class="panel-header">Orchestrator Mission</div>
    <div class="panel-content">
      <!-- Empty state: Document icon -->
      <div v-if="!missionText" class="empty-state">
        <v-icon size="80" color="rgba(255, 255, 255, 0.15)">
          mdi-file-document-outline
        </v-icon>
      </div>

      <!-- Mission text (when available) -->
      <div v-else class="mission-text-container">
        <pre class="mission-text">{{ missionText }}</pre>
        <v-btn
          small
          outlined
          @click="handleCopyPrompt"
          class="copy-button"
        >
          <v-icon small left>mdi-content-copy</v-icon>
          Copy
        </v-btn>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  min-height: 400px;
}

.mission-text-container {
  position: relative;
}

.mission-text {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #e0e0e0;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: rgba(0, 0, 0, 0.3);
  padding: 16px;
  border-radius: 8px;
}

.copy-button {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.5);
}
</style>
```

**Verification**:
- When `missionText` is empty: Document icon centered, size 80, color `rgba(255, 255, 255, 0.15)`
- When `missionText` has value: Text displays in monospace, copy button appears
- Icon uses `mdi-file-document-outline` (outline variant)

---

### Task 5: Orchestrator Card Styling (0.5 hour)

**Current State**: Orchestrator card may have incorrect avatar color or border-radius.

**Required Changes**:
```vue
<template>
  <div class="orchestrator-card">
    <!-- Avatar -->
    <v-avatar
      size="48"
      class="orchestrator-avatar"
    >
      Or
    </v-avatar>

    <!-- Card content -->
    <div class="card-content">
      <div class="card-title">Orchestrator</div>
      <div class="card-id">{{ orchestratorId }}</div>
    </div>

    <!-- Lock icon (right side) -->
    <v-icon size="20" color="#999">mdi-lock</v-icon>

    <!-- Info icon (right side) -->
    <v-icon size="20" color="#999">mdi-information</v-icon>
  </div>
</template>

<style scoped>
.orchestrator-card {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);  /* Subtle background */
  border-radius: 24px;                    /* Pill shape */
  margin-bottom: 12px;
  gap: 12px;
}

.orchestrator-avatar {
  background: #d4a574 !important;  /* Tan color (NOT 'tan' keyword) */
  color: #000;
  font-weight: bold;
  font-size: 16px;
}

.card-content {
  flex: 1;
}

.card-title {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

.card-id {
  font-size: 12px;
  color: #999;
  font-family: 'Courier New', monospace;
}
</style>
```

**Verification**:
- Avatar background: Exact hex `#d4a574` (NOT CSS keyword `tan`)
- Card border-radius: Exactly 24px (pill shape)
- Lock icon: `mdi-lock`, grey color
- Info icon: `mdi-information`, grey color
- Background: `rgba(255, 255, 255, 0.05)`

---

### Task 6: Testing (1 hour)

Create comprehensive test suite: `frontend/tests/unit/components/projects/LaunchTab.0242a.spec.js`

**Test Structure** (29 tests total):

```javascript
import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import LaunchTab from '@/components/projects/LaunchTab.vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({ components, directives })

describe('LaunchTab.vue - 0242a Visual Polish', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(LaunchTab, {
      global: {
        plugins: [vuetify],
      },
      props: {
        projectId: 'test-project-123',
        projectDescription: 'Test project description',
      },
    })
  })

  describe('Unified Container Border', () => {
    it('should have exact border styling', () => {
      const container = wrapper.find('.unified-container')
      const styles = window.getComputedStyle(container.element)
      expect(styles.border).toContain('2px')
      expect(styles.borderRadius).toBe('16px')
      expect(styles.padding).toBe('30px')
    })

    it('should have correct background color', () => {
      const container = wrapper.find('.unified-container')
      const styles = window.getComputedStyle(container.element)
      expect(styles.background).toContain('rgba(14, 28, 45, 0.5)')
    })
  })

  describe('Three-Panel Grid Layout', () => {
    it('should render three panels', () => {
      const panels = wrapper.findAll('.panel')
      expect(panels).toHaveLength(3)
    })

    it('should use CSS Grid with equal columns', () => {
      const grid = wrapper.find('.three-panel-grid')
      const styles = window.getComputedStyle(grid.element)
      expect(styles.display).toBe('grid')
      expect(styles.gridTemplateColumns).toBe('1fr 1fr 1fr')
    })

    it('should have 24px gap between panels', () => {
      const grid = wrapper.find('.three-panel-grid')
      const styles = window.getComputedStyle(grid.element)
      expect(styles.gap).toBe('24px')
    })

    it('should NOT uppercase panel headers', () => {
      const header = wrapper.find('.panel-header')
      const styles = window.getComputedStyle(header.element)
      expect(styles.textTransform).not.toBe('uppercase')
    })

    it('should have min-height 400px for panel content', () => {
      const content = wrapper.find('.panel-content')
      const styles = window.getComputedStyle(content.element)
      expect(styles.minHeight).toBe('400px')
    })
  })

  describe('Top Action Bar', () => {
    it('should render all three sections', () => {
      const actionBar = wrapper.find('.top-action-bar')
      expect(actionBar.exists()).toBe(true)
      expect(wrapper.find('.stage-button').exists()).toBe(true)
      expect(wrapper.find('.waiting-status').exists()).toBe(true)
      expect(wrapper.findAll('button')).toHaveLength(2) // Stage + Launch
    })

    it('should position elements with space-between', () => {
      const actionBar = wrapper.find('.top-action-bar')
      const styles = window.getComputedStyle(actionBar.element)
      expect(styles.justifyContent).toBe('space-between')
    })

    it('should style Stage button correctly', () => {
      const stageBtn = wrapper.find('.stage-button')
      const styles = window.getComputedStyle(stageBtn.element)
      expect(styles.border).toContain('2px solid #ffd700')
      expect(styles.background).toBe('transparent')
    })

    it('should style Waiting status correctly', () => {
      const status = wrapper.find('.waiting-status')
      const styles = window.getComputedStyle(status.element)
      expect(styles.color).toContain('255, 215, 0') // #ffd700 in rgb
      expect(styles.fontStyle).toBe('italic')
      expect(styles.fontSize).toBe('18px')
    })

    it('should show grey Launch button when disabled', async () => {
      await wrapper.setData({ canLaunch: false })
      const launchBtn = wrapper.find('.launch-disabled')
      const styles = window.getComputedStyle(launchBtn.element)
      expect(styles.background).toContain('102, 102, 102') // #666 in rgb
    })

    it('should show yellow Launch button when enabled', async () => {
      await wrapper.setData({ canLaunch: true })
      const launchBtn = wrapper.find('.launch-enabled')
      const styles = window.getComputedStyle(launchBtn.element)
      expect(styles.background).toContain('255, 215, 0') // #ffd700 in rgb
    })
  })

  describe('Orchestrator Mission Panel', () => {
    it('should show document icon when mission empty', async () => {
      await wrapper.setData({ missionText: '' })
      const icon = wrapper.find('.empty-state v-icon')
      expect(icon.exists()).toBe(true)
      expect(icon.attributes('size')).toBe('80')
    })

    it('should use correct icon name', async () => {
      await wrapper.setData({ missionText: '' })
      const icon = wrapper.find('.empty-state v-icon')
      expect(icon.text()).toContain('mdi-file-document-outline')
    })

    it('should show mission text when available', async () => {
      await wrapper.setData({ missionText: 'Test mission content' })
      expect(wrapper.find('.mission-text').exists()).toBe(true)
      expect(wrapper.find('.mission-text').text()).toBe('Test mission content')
    })

    it('should show copy button with mission text', async () => {
      await wrapper.setData({ missionText: 'Test mission content' })
      expect(wrapper.find('.copy-button').exists()).toBe(true)
    })
  })

  describe('Orchestrator Card Styling', () => {
    it('should have pill-shaped border-radius', () => {
      const card = wrapper.find('.orchestrator-card')
      const styles = window.getComputedStyle(card.element)
      expect(styles.borderRadius).toBe('24px')
    })

    it('should have correct avatar background color', () => {
      const avatar = wrapper.find('.orchestrator-avatar')
      const styles = window.getComputedStyle(avatar.element)
      expect(styles.background).toContain('212, 165, 116') // #d4a574 in rgb
    })

    it('should render lock icon', () => {
      const lockIcon = wrapper.find('v-icon[icon="mdi-lock"]')
      expect(lockIcon.exists()).toBe(true)
      expect(lockIcon.attributes('color')).toBe('#999')
    })

    it('should render info icon', () => {
      const infoIcon = wrapper.find('v-icon[icon="mdi-information"]')
      expect(infoIcon.exists()).toBe(true)
      expect(infoIcon.attributes('color')).toBe('#999')
    })

    it('should have subtle background', () => {
      const card = wrapper.find('.orchestrator-card')
      const styles = window.getComputedStyle(card.element)
      expect(styles.background).toContain('rgba(255, 255, 255, 0.05)')
    })
  })

  describe('WebSocket Reactivity (Preserved)', () => {
    it('should update missionText on mission_updated event', async () => {
      const socket = wrapper.vm.$socket
      socket.emit('mission_updated', { mission: 'New mission text' })
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.missionText).toBe('New mission text')
    })

    it('should add agents on agent:created event', async () => {
      const socket = wrapper.vm.$socket
      socket.emit('agent:created', { id: 'agent-1', name: 'Analyzer' })
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.agents).toHaveLength(1)
      expect(wrapper.vm.agentIds.has('agent-1')).toBe(true)
    })

    it('should prevent duplicate agents', async () => {
      const socket = wrapper.vm.$socket
      socket.emit('agent:created', { id: 'agent-1', name: 'Analyzer' })
      socket.emit('agent:created', { id: 'agent-1', name: 'Analyzer' }) // Duplicate
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.agents).toHaveLength(1) // Only one agent
    })
  })

  describe('Clipboard Handling (Preserved)', () => {
    it('should copy mission text to clipboard', async () => {
      await wrapper.setData({ missionText: 'Test mission' })
      const copyBtn = wrapper.find('.copy-button')

      // Mock clipboard API
      const writeTextMock = vi.fn().mockResolvedValue()
      Object.assign(navigator, {
        clipboard: { writeText: writeTextMock },
      })

      await copyBtn.trigger('click')
      expect(writeTextMock).toHaveBeenCalledWith('Test mission')
    })

    it('should handle clipboard errors gracefully', async () => {
      await wrapper.setData({ missionText: 'Test mission' })
      const copyBtn = wrapper.find('.copy-button')

      // Mock clipboard API failure
      const writeTextMock = vi.fn().mockRejectedValue(new Error('Clipboard error'))
      Object.assign(navigator, {
        clipboard: { writeText: writeTextMock },
      })

      await copyBtn.trigger('click')
      // Should not throw, fallback logic handles error
      expect(writeTextMock).toHaveBeenCalled()
    })
  })

  describe('Agent Tracking (Preserved)', () => {
    it('should maintain Set of agent IDs', () => {
      expect(wrapper.vm.agentIds).toBeInstanceOf(Set)
    })

    it('should track agents array reactively', async () => {
      const initialLength = wrapper.vm.agents.length
      wrapper.vm.agents.push({ id: 'new-agent', name: 'New Agent' })
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.agents).toHaveLength(initialLength + 1)
    })
  })
})
```

**Running Tests**:
```bash
cd frontend
npm test -- LaunchTab.0242a.spec.js
```

**Expected Output**:
```
✓ LaunchTab.vue - 0242a Visual Polish (29 tests)
  ✓ Unified Container Border (2 tests)
  ✓ Three-Panel Grid Layout (5 tests)
  ✓ Top Action Bar (6 tests)
  ✓ Orchestrator Mission Panel (4 tests)
  ✓ Orchestrator Card Styling (5 tests)
  ✓ WebSocket Reactivity (Preserved) (3 tests)
  ✓ Clipboard Handling (Preserved) (2 tests)
  ✓ Agent Tracking (Preserved) (2 tests)

Test Files  1 passed (1)
     Tests  29 passed (29)
```

---

## Files to Modify

### Primary File
- **`frontend/src/components/projects/LaunchTab.vue`**
  - Modify: `<template>` section (layout, structure, classes)
  - Modify: `<style scoped>` section (colors, spacing, borders)
  - **DO NOT MODIFY**: `<script>` section (preserve all logic)

### New Test File
- **`frontend/tests/unit/components/projects/LaunchTab.0242a.spec.js`** (CREATE)
  - 29 comprehensive tests
  - Covers visual styling, layout, preserved reactivity

---

## Files NOT to Modify

**Critical**: DO NOT modify these sections of `LaunchTab.vue`:

```vue
<script>
// ❌ DO NOT TOUCH THIS SCRIPT SECTION ❌

// Preserve reactive refs
const missionText = ref('')  // WebSocket reactive
const agents = ref([])       // Agent tracking
const agentIds = new Set()   // Duplicate prevention
const usingClaudeCodeSubagents = ref(false)

// Preserve WebSocket handlers
socket.on('mission_updated', (data) => {
  missionText.value = data.mission
})

socket.on('agent:created', (agentData) => {
  if (!agentIds.has(agentData.id)) {
    agents.value.push(agentData)
    agentIds.add(agentData.id)
  }
})

// Preserve clipboard handling
const handleCopyPrompt = async () => {
  try {
    await navigator.clipboard.writeText(missionText.value)
    // Success feedback
  } catch (err) {
    // Fallback logic for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = missionText.value
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
  }
}

// ❌ END DO NOT TOUCH ❌
</script>
```

---

## Success Criteria

### Visual Validation
- ✅ Side-by-side comparison with `Launch Tab.jpg` shows pixel-perfect match
- ✅ Unified container border: 2px solid rgba(255, 255, 255, 0.2), radius 16px
- ✅ Three panels: Equal width, 24px gap, headers not uppercase
- ✅ Top action bar: Stage left, Waiting center, Launch right
- ✅ Orchestrator avatar: Exact hex #d4a574 (tan), NOT CSS keyword

### Functional Validation
- ✅ All 29 tests passing
- ✅ WebSocket `mission_updated` event updates missionText
- ✅ WebSocket `agent:created` event adds agents without duplicates
- ✅ Clipboard copy works (with fallback)
- ✅ Agent tracking Set prevents duplicate cards

### Code Quality
- ✅ No console errors in browser DevTools
- ✅ No linting errors (`npm run lint`)
- ✅ `<script>` section unchanged from 0241 implementation
- ✅ All reactive logic preserved

---

## Testing Commands

```bash
# Frontend directory
cd frontend

# Install dependencies (if needed)
npm install

# Run specific test file
npm test -- LaunchTab.0242a.spec.js

# Run with coverage
npm test -- LaunchTab.0242a.spec.js --coverage

# Lint check
npm run lint

# Build verification
npm run build
```

---

## Manual Verification Steps

1. **Start Backend Server**:
   ```bash
   python startup.py
   ```

2. **Start Frontend Dev Server**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Navigate to Launch Tab**:
   - Open: `http://10.1.0.164:7274/projects/{project-id}?via=launch`

4. **Visual Inspection**:
   - Open `Launch Tab.jpg` screenshot side-by-side
   - Compare:
     - Unified container border (2px, rgba, 16px radius)
     - Three-panel grid (equal widths, 24px gap)
     - Top action bar (left/center/right positioning)
     - Button colors (Stage yellow outlined, Launch grey/yellow)
     - Orchestrator avatar (#d4a574 tan)

5. **Functional Testing**:
   - Click "Stage project" → Verify clipboard copy modal
   - Verify mission text appears in middle panel (WebSocket event)
   - Verify "Launch jobs" button turns yellow
   - Open DevTools → Console → Check for errors (should be none)

6. **DevTools Inspection**:
   - Right-click unified container → Inspect
   - Verify computed styles:
     - Border: `2px solid rgba(255, 255, 255, 0.2)`
     - Border-radius: `16px`
     - Padding: `30px`
   - Right-click three-panel-grid → Inspect
   - Verify computed styles:
     - Display: `grid`
     - Grid-template-columns: `1fr 1fr 1fr`
     - Gap: `24px`

---

## Rollback Plan

If issues arise during implementation:

1. **Git Stash Changes**:
   ```bash
   git stash save "0242a in-progress work"
   ```

2. **Return to 0241 State**:
   ```bash
   git checkout handovers/completed/0241_emergency_gui_fix_match_screenshots-C.md
   git checkout frontend/src/components/projects/LaunchTab.vue
   ```

3. **Document Issues**:
   - Create issue in GitHub: `GUI 0242a Rollback - [describe problem]`
   - Tag with `gui-redesign`, `0242-series`, `needs-investigation`

---

## Next Steps

**Upon Completion of 0242a**:
1. ✅ All 29 tests passing
2. ✅ Visual validation complete (pixel-perfect match)
3. ✅ Manual testing complete (no console errors)
4. ✅ Git commit created:
   ```bash
   git add frontend/src/components/projects/LaunchTab.vue
   git add frontend/tests/unit/components/projects/LaunchTab.0242a.spec.js
   git commit -m "feat: Launch Tab visual polish (0242a)

   - Unified container border (2px rgba, 16px radius)
   - Three-panel grid (equal widths, 24px gap)
   - Top action bar (left/center/right positioning)
   - Orchestrator card styling (tan avatar, pill shape)
   - 29 comprehensive tests
   - Preserved WebSocket reactivity and clipboard handling

   Handover: 0242a
   Tests: 29 passing
   Status: Ready for 0242b ✅"
   ```

5. **Proceed to Handover 0242b**: Implement Tab table refinement

---

## Notes for TDD-Implementor Subagent

**Your Mission**:
- Focus exclusively on `<template>` and `<style>` sections
- Match screenshot pixel-perfect (use DevTools to measure)
- Run tests frequently (TDD approach: write test → implement → verify)
- DO NOT refactor `<script>` logic (that's out of scope)
- Preserve all WebSocket handlers and reactive refs

**Communication**:
- Report progress after each task (1-6)
- Share screenshots of before/after comparisons
- Run `npm test` after every change to catch regressions early
- Ask questions if screenshot is ambiguous (better to clarify than guess)

**Quality Checklist Before Marking Complete**:
- [ ] All 29 tests passing
- [ ] No console errors in DevTools
- [ ] No linting errors
- [ ] Side-by-side screenshot comparison shows pixel-perfect match
- [ ] Manual clipboard copy test works
- [ ] Manual WebSocket event test works (Stage project → mission appears)
