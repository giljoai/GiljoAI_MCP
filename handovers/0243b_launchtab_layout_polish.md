# Handover 0243b: LaunchTab Three-Panel Layout Polish

**Status**: 🔵 Ready for Implementation
**Priority**: P1 (High - Visual polish)
**Estimated Effort**: 4-6 hours
**Tool**: CCW (Cloud) for frontend work
**Subagent**: ux-designer (UI/UX specialist)
**Dependencies**: 0243a (design-tokens.scss must exist)
**Part**: 2 of 6 in Nicepage conversion series

---

## Mission

Polish LaunchTab three-panel layout to pixel-perfect match Nicepage design. Focus on equal panel widths, content styling, orchestrator card, and empty state.

**Prerequisite**: 0243a MUST be complete (design-tokens.scss file exists).

---

## Visual Reference

**Target Screenshot**: `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Launch Tab.jpg`

**Key Elements**:
- Three equal-width panels (1fr 1fr 1fr grid)
- Panel gap: 24px
- Panel headers: "Project", "Orchestrator mission", "Default Agent"
- Panel content: min-height 450px, border-radius 10px
- Orchestrator card: Pill-shaped border (border-radius 24px), tan avatar (#9a8a76)
- Empty state: Document icon (80px, rgba(255,255,255,0.15)) when mission is null

---

## Panel Grid System

### Current Issue

LaunchTab may have unequal panel widths or incorrect gap spacing.

### Required Implementation

**Template** (`LaunchTab.vue`):
```vue
<v-row class="three-panels" no-gutters>
  <v-col cols="12" md="4" class="panel">
    <!-- Panel 1: Project Description -->
  </v-col>
  <v-col cols="12" md="4" class="panel">
    <!-- Panel 2: Orchestrator Mission -->
  </v-col>
  <v-col cols="12" md="4" class="panel">
    <!-- Panel 3: Default Agent + Agent Team -->
  </v-col>
</v-row>
```

**Styles**:
```scss
@import '@/styles/design-tokens.scss';

.three-panels {
  gap: $panel-gap;  // 24px from design tokens

  .panel {
    // Equal width via Vuetify cols="4" (md breakpoint)
    // Flex: 1 1 0% ensures equal distribution
  }
}
```

---

## Panel Content Styling

### Panel 1: Project Description

**Template**:
```vue
<v-col cols="12" md="4" class="panel">
  <div class="panel-header">Project</div>
  <div class="panel-content">
    <p class="description-text">{{ project.description }}</p>
    <v-btn
      icon="mdi-pencil"
      size="small"
      class="edit-icon"
      color="yellow-darken-2"
      @click="editDescription"
    />
  </div>
</v-col>
```

**Styles**:
```scss
.panel-content {
  background: $background-tertiary;  // rgba(20, 35, 50, 0.8)
  border-radius: $panel-border-radius;  // 10px
  padding: 20px;
  min-height: $panel-min-height;  // 450px
  position: relative;

  .description-text {
    color: $text-primary;  // #e0e0e0
    font-size: $font-size-body;  // 0.875rem
    line-height: 1.5;
    margin-bottom: 40px;  // Space for edit icon
  }

  .edit-icon {
    position: absolute;
    bottom: 16px;
    right: 16px;
  }
}
```

### Panel 2: Orchestrator Mission (Empty State OR Mission Text)

**Template**:
```vue
<v-col cols="12" md="4" class="panel">
  <div class="panel-header">Orchestrator mission</div>
  <div class="panel-content">
    <!-- Empty state (when mission is null) -->
    <div v-if="!missionText" class="empty-state">
      <v-icon
        size="80"
        color="rgba(255, 255, 255, 0.15)"
      >
        mdi-file-document-outline
      </v-icon>
    </div>

    <!-- Mission text (when mission exists) -->
    <pre v-else class="mission-content">{{ missionText }}</pre>
  </div>
</v-col>
```

**Styles**:
```scss
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  min-height: $panel-min-height;
}

.mission-content {
  font-family: 'Courier New', monospace;
  color: $text-primary;
  font-size: $font-size-body;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
}
```

### Panel 3: Default Agent + Agent Team

**Template**:
```vue
<v-col cols="12" md="4" class="panel">
  <!-- Default Agent Section -->
  <div class="panel-header">Default Agent</div>
  <div class="panel-content">
    <!-- Orchestrator card (pill-shaped) -->
    <div class="orchestrator-card">
      <div class="agent-avatar" :style="{ background: '#9a8a76' }">
        Or
      </div>
      <span class="agent-name">Orchestrator</span>
      <v-icon size="small" color="#ccc">mdi-lock</v-icon>
      <v-icon size="small" color="white" @click="showOrchestratorInfo">mdi-information</v-icon>
    </div>

    <!-- Agent Team Section -->
    <div class="agent-team-section">
      <div class="panel-header">Agent Team</div>
      <div v-for="agent in agents" :key="agent.id" class="agent-card-mini">
        <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
          {{ getAgentAbbreviation(agent.agent_type) }}
        </div>
        <span class="agent-name">{{ agent.agent_type }}</span>
        <v-icon size="small" color="yellow-darken-2" @click="editAgentMission(agent)">mdi-pencil</v-icon>
        <v-icon size="small" color="white" @click="showAgentInfo(agent)">mdi-information</v-icon>
      </div>
    </div>
  </div>
</v-col>
```

**Styles**:
```scss
.orchestrator-card {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 2px solid $text-highlight;  // #ffd700
  border-radius: $border-radius-pill;  // 24px (pill shape)
  padding: 12px 20px;
  margin-bottom: 20px;

  .agent-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: $font-weight-bold;
    font-size: 14px;
  }

  .agent-name {
    flex: 1;
    color: $text-primary;
    font-size: $font-size-body;
  }
}

.agent-team-section {
  margin-top: 20px;

  .panel-header {
    margin-bottom: 12px;
  }

  .agent-card-mini {
    display: flex;
    align-items: center;
    gap: 12px;
    border: 2px solid $text-highlight;
    border-radius: $border-radius-medium;  // 10px
    padding: 10px 16px;
    margin-bottom: 12px;

    .agent-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: $font-weight-bold;
      font-size: 12px;
    }

    .agent-name {
      flex: 1;
      color: $text-primary;
      font-size: $font-size-body;
      text-transform: capitalize;
    }
  }
}
```

---

## Agent Avatar Colors

**Script** (`LaunchTab.vue`):
```javascript
const getAgentColor = (agentType) => {
  const colors = {
    orchestrator: '#9a8a76',  // Tan
    analyzer: '#e1564b',       // Red
    implementor: '#3493bf',    // Blue
    tester: '#d4a574'          // Gold
  }
  return colors[agentType] || '#666'
}

const getAgentAbbreviation = (agentType) => {
  const abbrevs = {
    orchestrator: 'Or',
    analyzer: 'An',
    implementor: 'Im',
    tester: 'Te'
  }
  return abbrevs[agentType] || '??'
}
```

---

## Panel Header Styling

**All panel headers** should use consistent styling:

```scss
.panel-header {
  font-size: $font-size-heading;  // 1.125rem (18px)
  font-weight: $font-weight-semibold;  // 600
  color: $text-secondary;  // #999
  margin-bottom: 16px;
  text-transform: capitalize;
}
```

**Apply to**:
- "Project" header
- "Orchestrator mission" header
- "Default Agent" header
- "Agent Team" header (nested)

---

## TDD Workflow

### RED: Write Failing Tests

**File**: `tests/unit/LaunchTab-layout.spec.js`

```javascript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LaunchTab from '@/components/projects/LaunchTab.vue'

describe('LaunchTab three-panel layout (Phase 2)', () => {
  const mockProject = {
    id: 'project-uuid',
    name: 'Test Project',
    description: 'Test description with long text...',
    mission: null
  }

  it('renders three panels with equal widths', () => {
    const wrapper = mount(LaunchTab, { props: { project: mockProject } })
    const panels = wrapper.findAll('.panel')

    expect(panels).toHaveLength(3)
    panels.forEach(panel => {
      // Vuetify cols="4" generates flex: 1 1 0%
      expect(panel.attributes('class')).toContain('v-col-md-4')
    })
  })

  it('renders 24px gap between panels', () => {
    const wrapper = mount(LaunchTab, { props: { project: mockProject } })
    const grid = wrapper.find('.three-panels')
    const styles = window.getComputedStyle(grid.element)

    expect(styles.gap).toBe('24px')
  })

  it('shows empty state icon when mission is null', () => {
    const wrapper = mount(LaunchTab, { props: { project: mockProject } })
    const emptyIcon = wrapper.find('.empty-state v-icon')

    expect(emptyIcon.exists()).toBe(true)
    expect(emptyIcon.attributes('size')).toBe('80')
    expect(emptyIcon.attributes('color')).toBe('rgba(255, 255, 255, 0.15)')
  })

  it('shows mission text when mission exists', () => {
    const projectWithMission = { ...mockProject, mission: 'Test mission...' }
    const wrapper = mount(LaunchTab, { props: { project: projectWithMission } })

    expect(wrapper.find('.empty-state').exists()).toBe(false)
    expect(wrapper.find('.mission-content').exists()).toBe(true)
    expect(wrapper.find('.mission-content').text()).toBe('Test mission...')
  })

  it('renders orchestrator card with tan avatar and pill shape', () => {
    const wrapper = mount(LaunchTab, { props: { project: mockProject } })
    const card = wrapper.find('.orchestrator-card')

    expect(card.exists()).toBe(true)

    const avatar = card.find('.agent-avatar')
    expect(avatar.element.style.background).toBe('rgb(154, 138, 118)')  // #9a8a76
    expect(avatar.text()).toBe('Or')

    const styles = window.getComputedStyle(card.element)
    expect(styles.borderRadius).toBe('24px')  // Pill shape
  })

  it('renders panel headers with correct font and color', () => {
    const wrapper = mount(LaunchTab, { props: { project: mockProject } })
    const headers = wrapper.findAll('.panel-header')

    expect(headers.length).toBeGreaterThanOrEqual(3)

    headers.forEach(header => {
      const styles = window.getComputedStyle(header.element)
      expect(styles.fontSize).toBe('18px')  // 1.125rem
      expect(styles.color).toBe('rgb(153, 153, 153)')  // #999
    })
  })

  it('renders panel content with min-height 450px', () => {
    const wrapper = mount(LaunchTab, { props: { project: mockProject } })
    const contents = wrapper.findAll('.panel-content')

    contents.forEach(content => {
      const styles = window.getComputedStyle(content.element)
      expect(styles.minHeight).toBe('450px')
      expect(styles.borderRadius).toBe('10px')
    })
  })

  it('renders agent team with correct avatars and colors', () => {
    const mockAgents = [
      { id: '1', agent_type: 'analyzer' },
      { id: '2', agent_type: 'implementor' },
      { id: '3', agent_type: 'tester' }
    ]

    const wrapper = mount(LaunchTab, {
      props: { project: mockProject },
      data() {
        return { agents: mockAgents }
      }
    })

    const agentCards = wrapper.findAll('.agent-card-mini')
    expect(agentCards).toHaveLength(3)

    // Verify analyzer avatar
    const analyzerAvatar = agentCards[0].find('.agent-avatar')
    expect(analyzerAvatar.element.style.background).toBe('rgb(225, 86, 75)')  // #e1564b
    expect(analyzerAvatar.text()).toBe('An')

    // Verify implementor avatar
    const implementorAvatar = agentCards[1].find('.agent-avatar')
    expect(implementorAvatar.element.style.background).toBe('rgb(52, 147, 191)')  // #3493bf
    expect(implementorAvatar.text()).toBe('Im')

    // Verify tester avatar
    const testerAvatar = agentCards[2].find('.agent-avatar')
    expect(testerAvatar.element.style.background).toBe('rgb(212, 165, 116)')  // #d4a574
    expect(testerAvatar.text()).toBe('Te')
  })

  it('positions edit icon in bottom-right of description panel', () => {
    const wrapper = mount(LaunchTab, { props: { project: mockProject } })
    const editIcon = wrapper.find('.edit-icon')

    expect(editIcon.exists()).toBe(true)
    const styles = window.getComputedStyle(editIcon.element)
    expect(styles.position).toBe('absolute')
    expect(styles.bottom).toBe('16px')
    expect(styles.right).toBe('16px')
  })
})
```

### GREEN: Implement Minimum Code

**Tasks**:
1. Update LaunchTab.vue template (three panels, empty state, orchestrator card)
2. Update LaunchTab.vue styles using design tokens from 0243a
3. Add getAgentColor() and getAgentAbbreviation() methods
4. Run tests: `npm run test:unit -- LaunchTab-layout.spec.js`

**Implementation Checklist**:
- [ ] Import design-tokens.scss in LaunchTab.vue
- [ ] Update template to use three-column grid (cols="12" md="4")
- [ ] Add .three-panels class with gap: $panel-gap
- [ ] Implement empty state with mdi-file-document-outline icon
- [ ] Add mission-content pre element with Courier New font
- [ ] Style orchestrator-card with pill border (border-radius 24px)
- [ ] Add getAgentColor() method to script
- [ ] Add getAgentAbbreviation() method to script
- [ ] Style panel-header with consistent font and color
- [ ] Set panel-content min-height to 450px

### REFACTOR: Polish Code

**Tasks**:
1. Extract agent color mapping to composable if reused elsewhere
2. Verify all hardcoded colors replaced with design tokens
3. Clean up unused code
4. Run coverage: `npm run test:unit -- --coverage`

**Refactoring Opportunities**:
- Consider creating `composables/useAgentColors.js` if colors are used in other components
- Extract agent avatar component if pattern repeats across multiple files
- Ensure no magic numbers in styles (all values from design tokens)

---

## Design Token Usage

**Required imports** in LaunchTab.vue:

```scss
<style lang="scss" scoped>
@import '@/styles/design-tokens.scss';

// Use tokens instead of hardcoded values:
// ✅ gap: $panel-gap
// ❌ gap: 24px

// ✅ background: $background-tertiary
// ❌ background: rgba(20, 35, 50, 0.8)

// ✅ color: $text-primary
// ❌ color: #e0e0e0
</style>
```

**Key tokens to use**:
- `$panel-gap` - Panel spacing (24px)
- `$panel-min-height` - Panel content height (450px)
- `$panel-border-radius` - Panel corners (10px)
- `$border-radius-pill` - Orchestrator card (24px)
- `$border-radius-medium` - Agent cards (10px)
- `$background-tertiary` - Panel backgrounds
- `$text-primary` - Main text color
- `$text-secondary` - Header text color
- `$text-highlight` - Border accent color
- `$font-size-heading` - Panel headers (1.125rem)
- `$font-size-body` - Body text (0.875rem)
- `$font-weight-semibold` - Header weight (600)
- `$font-weight-bold` - Avatar text (700)

---

## Visual QA Checklist

**Before marking complete**, verify these visual details:

### Panel Grid
- [ ] Three panels are exactly equal width
- [ ] Gap between panels is exactly 24px
- [ ] Panels stack vertically on mobile (cols="12")
- [ ] Panels are side-by-side on desktop (md="4")

### Panel Content
- [ ] All panel-content divs have min-height 450px
- [ ] All panel-content divs have border-radius 10px
- [ ] Panel backgrounds use rgba(20, 35, 50, 0.8)
- [ ] Panel padding is 20px on all sides

### Panel Headers
- [ ] All headers use font-size 18px (1.125rem)
- [ ] All headers use color #999
- [ ] All headers use font-weight 600
- [ ] Header margin-bottom is 16px

### Empty State (Mission Panel)
- [ ] Document icon is exactly 80px
- [ ] Icon color is rgba(255, 255, 255, 0.15)
- [ ] Icon is centered vertically and horizontally
- [ ] Empty state only shows when mission is null

### Mission Text
- [ ] Uses Courier New monospace font
- [ ] Text color is #e0e0e0
- [ ] White-space: pre-wrap (preserves formatting)
- [ ] Line-height is 1.6

### Orchestrator Card
- [ ] Border-radius is exactly 24px (pill shape)
- [ ] Border is 2px solid #ffd700
- [ ] Avatar background is #9a8a76 (tan)
- [ ] Avatar displays "Or" text
- [ ] Avatar is 40px circle
- [ ] Lock icon and info icon are present

### Agent Cards
- [ ] Border-radius is 10px
- [ ] Border is 2px solid #ffd700
- [ ] Avatar backgrounds match agent types:
  - Analyzer: #e1564b (red)
  - Implementor: #3493bf (blue)
  - Tester: #d4a574 (gold)
- [ ] Avatar sizes are 36px circles
- [ ] Pencil and info icons are present
- [ ] Agent names are capitalized

### Edit Icon (Description Panel)
- [ ] Positioned absolute bottom-right
- [ ] Bottom offset is 16px
- [ ] Right offset is 16px
- [ ] Icon color is yellow-darken-2

---

## Browser DevTools Verification

**Use Chrome DevTools** to verify exact pixel values:

```javascript
// Open DevTools Console and run:

// Check panel gap
const grid = document.querySelector('.three-panels')
getComputedStyle(grid).gap  // Should be "24px"

// Check panel widths (should be equal)
const panels = document.querySelectorAll('.panel')
panels.forEach(p => console.log(getComputedStyle(p).width))

// Check orchestrator card border-radius
const orchCard = document.querySelector('.orchestrator-card')
getComputedStyle(orchCard).borderRadius  // Should be "24px"

// Check panel min-height
const panelContent = document.querySelectorAll('.panel-content')
panelContent.forEach(p => console.log(getComputedStyle(p).minHeight))  // Should be "450px"

// Check header font size
const headers = document.querySelectorAll('.panel-header')
headers.forEach(h => console.log(getComputedStyle(h).fontSize))  // Should be "18px"
```

---

## Deliverables

**Files to Modify**:
- ✅ `frontend/src/components/projects/LaunchTab.vue` (template + styles + script)
- ✅ `tests/unit/LaunchTab-layout.spec.js` (new test file)

**Files to Reference**:
- ✅ `frontend/src/styles/design-tokens.scss` (from 0243a)
- ✅ `handovers/Launch-Jobs_panels2/Launch Tab.jpg` (visual reference)

**Success Criteria**:
- [ ] Three equal-width panels (Vuetify cols="4")
- [ ] Panel gap: Exact 24px
- [ ] Panel content: min-height 450px, border-radius 10px
- [ ] Empty state icon: 80px, rgba(255,255,255,0.15) when mission is null
- [ ] Mission text: Courier New font, pre-wrap, when mission exists
- [ ] Orchestrator card: Tan avatar (#9a8a76), pill shape (border-radius 24px)
- [ ] Agent cards: Correct colors per type, 10px border-radius
- [ ] Panel headers: 18px font, #999 color, 600 weight
- [ ] Edit icon: Positioned bottom-right (16px offsets)
- [ ] Test coverage: >80%
- [ ] All tests passing (npm run test:unit)

---

## Integration Points

### Dependencies (Must be Complete First)
- **0243a**: Design tokens SCSS file must exist at `frontend/src/styles/design-tokens.scss`

### Blocks (Cannot Start Until This is Complete)
- **0243f**: Integration testing waits for all component polish to finish

### Parallel Work (Can Work Simultaneously)
- **0243c**: JobsTab dynamic status fix (independent component)
- **0243d**: Action icons refinement (separate component)

---

## Common Issues & Solutions

### Issue: Panels Not Equal Width

**Symptom**: Panels have different widths on desktop view

**Solution**:
```vue
<!-- Ensure md="4" is set (not just cols="12") -->
<v-col cols="12" md="4" class="panel">
```

### Issue: Gap Not Showing

**Symptom**: Panels are touching with no space between

**Solution**:
```vue
<!-- Add no-gutters to v-row -->
<v-row class="three-panels" no-gutters>
  <!-- ... -->
</v-row>
```

```scss
// Add gap in SCSS
.three-panels {
  gap: $panel-gap;  // 24px
}
```

### Issue: Empty State Not Centered

**Symptom**: Document icon appears in top-left corner

**Solution**:
```scss
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  min-height: $panel-min-height;  // Must match panel-content
}
```

### Issue: Orchestrator Card Not Pill-Shaped

**Symptom**: Card has square corners instead of rounded ends

**Solution**:
```scss
.orchestrator-card {
  border-radius: $border-radius-pill;  // 24px (not 10px)
  // Pill shape requires larger radius than panel content
}
```

### Issue: Avatar Colors Not Showing

**Symptom**: All avatars are gray instead of type-specific colors

**Solution**:
```vue
<!-- Use inline style binding for dynamic colors -->
<div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
  {{ getAgentAbbreviation(agent.agent_type) }}
</div>
```

---

## Next Steps

**After This Handover**:
1. **Parallel work**: Start 0243c (JobsTab dynamic status fix)
2. **Visual QA**: Compare rendered UI to `Launch Tab.jpg` screenshot
3. **Screenshot comparison**: Take before/after screenshots for documentation
4. **Report discrepancies**: Document any visual differences that cannot be matched

**Integration Testing** (0243f):
- Wait for 0243b, 0243c, 0243d to complete
- Full E2E test of Launch/Jobs tabs
- Cross-browser verification
- Responsive design validation

---

## Estimated Timeline

**Total**: 4-6 hours

**Breakdown**:
- Panel grid system setup: 1 hour
- Panel content styling (3 panels): 2 hours
- Orchestrator card refinement: 1 hour
- Agent team styling: 0.5 hour
- Test writing + validation: 1-2 hours
- Visual QA + DevTools verification: 0.5 hour

**Checkpoints**:
- Hour 2: Panel grid complete, tests passing
- Hour 4: All panel content styled, orchestrator card refined
- Hour 6: All tests passing, visual QA complete

---

## Agent Instructions

**You are a ux-designer agent**. Your mission is pixel-perfect visual match:

### Phase 1: Analyze (30 minutes)
1. Open screenshot: `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Launch Tab.jpg`
2. Measure exact dimensions using image editor (spacing, fonts, colors)
3. Read design tokens from `frontend/src/styles/design-tokens.scss`
4. Read current LaunchTab.vue to understand existing structure

### Phase 2: Test-Driven Development (2 hours)
1. Write failing tests in `tests/unit/LaunchTab-layout.spec.js`
2. Run tests to verify they fail: `npm run test:unit -- LaunchTab-layout.spec.js`
3. Implement minimum code to pass tests
4. Verify tests pass

### Phase 3: Implement (2 hours)
1. Update LaunchTab.vue template (three panels, headers, content)
2. Import design-tokens.scss at top of style block
3. Add panel grid styles (.three-panels, .panel)
4. Style panel headers (.panel-header)
5. Style panel content (.panel-content, .description-text, .edit-icon)
6. Add empty state (.empty-state with v-icon)
7. Add mission content (.mission-content with pre element)
8. Style orchestrator card (.orchestrator-card, pill shape)
9. Style agent team (.agent-team-section, .agent-card-mini)
10. Add getAgentColor() method to script
11. Add getAgentAbbreviation() method to script

### Phase 4: Visual QA (1 hour)
1. Run dev server: `npm run dev`
2. Open browser to LaunchTab
3. Use DevTools to verify exact pixel values (gap, min-height, border-radius)
4. Compare rendered UI to screenshot side-by-side
5. Take screenshots for before/after comparison
6. Document any discrepancies

### Phase 5: Report (30 minutes)
1. Run final tests with coverage: `npm run test:unit -- --coverage`
2. Verify >80% coverage
3. Create summary report:
   - Test coverage percentage
   - Screenshot comparison results
   - Any visual discrepancies found
   - Any blockers encountered
4. Commit changes with descriptive message

### Success Metrics
- [ ] All tests passing (100%)
- [ ] Test coverage >80%
- [ ] Visual match to screenshot (>95% accuracy)
- [ ] Design tokens used (no hardcoded values)
- [ ] DevTools verification complete
- [ ] Report submitted with screenshots

**Remember**: Pixel-perfect means EXACT. Use DevTools to verify every measurement. If screenshot shows 24px, code must produce 24px (not 25px, not 20px).
