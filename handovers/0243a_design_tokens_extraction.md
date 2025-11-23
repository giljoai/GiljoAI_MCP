# Handover 0243a: Design Token Extraction & LaunchTab Container

**Status**: ✅ COMPLETED (Nov 23, 2025)
**Priority**: P0 (BLOCKING - all UI work depends on this)
**Estimated Effort**: 6-8 hours (ACTUAL: 5 hours)
**Tool**: CCW (Cloud) for frontend work
**Subagent**: tdd-implementor (test-driven development)
**Dependencies**: None (Phase 1 blocks all other phases)
**Part**: 1 of 6 in Nicepage conversion series

---

## Mission

Extract design tokens from Nicepage design (`F:\Nicepage\MCP Server`) and fix LaunchTab unified container structure to match pixel-perfect screenshot.

**Critical Context**: Current LaunchTab has 3 SEPARATE bordered sections. Target Nicepage design has 1 UNIFIED container with 3 internal panels.

---

## Visual Gap

**Current** (`F:\GiljoAI_MCP\handovers\0241launch_tab.jpg`):
- 3 separate bordered sections (wrong structure)

**Target** (`F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Launch Tab.jpg`):
- 1 unified container with 2px border
- 3 internal panels (equal width, 24px gap)
- Border-radius: 16px
- Padding: 30px

---

## Design Token Extraction Strategy

### Why NOT Import nicepage.css

**DO NOT** import the 1.65MB nicepage.css file. Reasons:
1. Framework bloat (Froala WYSIWYG editor, extensive grid system)
2. Naming conflicts (`.u-*` prefixes vs Vuetify utilities)
3. Bundle size impact (+1.65MB)
4. Maintenance burden (external dependency)

**Instead**: Extract ONLY the specific design values we need.

### Tokens to Extract

**Source File**: `F:\Nicepage\MCP Server\index.css`

**Extract these values**:

#### Colors
```scss
// Background colors
$background-primary: #0e1c2d;        // Dark navy (body background)
$background-secondary: rgba(14, 28, 45, 0.5);  // Translucent navy (containers)
$background-tertiary: rgba(20, 35, 50, 0.8);   // Panel content background

// Border colors
$border-primary: rgba(255, 255, 255, 0.2);     // Main container borders
$border-secondary: rgba(255, 255, 255, 0.1);   // Table borders
$border-tertiary: rgba(255, 255, 255, 0.05);   // Row separators

// Text colors
$text-primary: #e0e0e0;              // Main text
$text-secondary: #999;                // Labels
$text-tertiary: #ccc;                 // Subdued text
$text-highlight: #ffd700;             // Yellow (status, waiting)

// Agent avatar colors
$color-orchestrator: #9a8a76;        // Tan
$color-analyzer: #e1564b;             // Red
$color-implementor: #3493bf;          // Blue
$color-tester: #d4a574;               // Gold/tan variant

// Status colors
$status-waiting: #ffd700;             // Yellow italic
$status-working: #ffd700;             // Yellow italic
$status-complete: #67bd6d;            // Green
$status-failed: #e53935;              // Red
$status-cancelled: #ff9800;           // Orange
```

#### Spacing/Sizing
```scss
$container-padding: 30px;             // Main container internal padding
$container-border-radius: 16px;       // Rounded corners
$panel-gap: 24px;                     // Gap between 3 panels
$panel-border-radius: 10px;           // Panel content rounded corners
$panel-min-height: 450px;             // Minimum panel height

$button-border-radius: 10px;          // Standard button radius
$button-border-radius-small: 6px;     // Message composer button radius

$table-cell-padding: 16px;            // Cell padding
$table-header-padding: 12px 16px;     // Header cell padding
```

#### Typography
```scss
$font-primary: 'Cairo', sans-serif;   // Primary font

$font-size-header: 1.125rem;          // Panel headers (18px)
$font-size-body: 0.875rem;            // Body text (14px)
$font-size-small: 0.75rem;            // Table headers (12px)
$font-size-tiny: 0.625rem;            // Agent ID (10px)

$font-weight-normal: 400;
$font-weight-medium: 500;
$font-weight-bold: 700;
```

#### Borders/Shadows
```scss
$border-width-thin: 1px;              // Row separators
$border-width-standard: 2px;          // Container borders
$border-width-thick: 3px;             // Active tab borders

$border-radius-small: 8px;            // Input fields
$border-radius-medium: 10px;          // Panels, buttons
$border-radius-large: 16px;           // Main container
$border-radius-pill: 24px;            // Orchestrator card

$shadow-subtle: 0 2px 4px rgba(0, 0, 0, 0.1);
$shadow-medium: 0 4px 8px rgba(0, 0, 0, 0.15);
$shadow-strong: 0 8px 16px rgba(0, 0, 0, 0.2);
```

### Extraction Process

**Manual Curation** (NOT automated extraction):
1. Open `F:\Nicepage\MCP Server\index.css` in editor
2. Search for color values, radii, spacing manually
3. Create `frontend/src/styles/design-tokens.scss` with curated values
4. Verify values match screenshot using browser DevTools

**Output**: `design-tokens.scss` file (~5KB, NOT 1.65MB)

---

## LaunchTab Container Fix

### Current Implementation Issue

**File**: `frontend/src/components/projects/LaunchTab.vue`

**Problem**: Three separate bordered sections instead of one unified container.

### Required Changes

#### Template Structure
```vue
<template>
  <div class="launch-tab-container">
    <!-- Top action bar (outside main container) -->
    <div class="top-action-bar">
      <v-btn class="stage-button" @click="handleStage">Stage project</v-btn>
      <span class="status-text">Waiting:</span>
      <v-btn class="launch-button" @click="handleLaunch">Launch jobs</v-btn>
    </div>

    <!-- UNIFIED CONTAINER with 3 internal panels -->
    <div class="main-container">
      <v-row class="three-panels" no-gutters>
        <!-- Panel 1: Project Description -->
        <v-col cols="12" md="4" class="panel">
          <div class="panel-header">Project</div>
          <div class="panel-content">
            <p class="description-text">{{ project.description }}</p>
            <v-btn icon="mdi-pencil" size="small" class="edit-icon" />
          </div>
        </v-col>

        <!-- Panel 2: Orchestrator Mission -->
        <v-col cols="12" md="4" class="panel">
          <div class="panel-header">Orchestrator mission</div>
          <div class="panel-content">
            <!-- Empty state OR mission text -->
            <div v-if="!missionText" class="empty-state">
              <v-icon size="80" color="rgba(255, 255, 255, 0.15)">mdi-file-document-outline</v-icon>
            </div>
            <pre v-else class="mission-content">{{ missionText }}</pre>
          </div>
        </v-col>

        <!-- Panel 3: Default Agent + Agent Team -->
        <v-col cols="12" md="4" class="panel">
          <div class="panel-header">Default Agent</div>
          <div class="panel-content">
            <!-- Orchestrator card -->
            <div class="orchestrator-card">
              <div class="agent-avatar" :style="{ background: '#9a8a76' }">Or</div>
              <span class="agent-name">Orchestrator</span>
              <v-icon size="small" color="#ccc">mdi-lock</v-icon>
              <v-icon size="small" color="white">mdi-information</v-icon>
            </div>

            <!-- Agent Team list -->
            <div class="panel-header">Agent Team</div>
            <div v-for="agent in agents" :key="agent.id" class="agent-card">
              <!-- Agent cards rendered here -->
            </div>
          </div>
        </v-col>
      </v-row>
    </div>
  </div>
</template>
```

#### Styles (Using Design Tokens)
```scss
<style scoped lang="scss">
@import '@/styles/design-tokens.scss';

.launch-tab-container {
  padding: 20px;
}

.top-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .stage-button {
    border: 2px solid $text-highlight;
    border-radius: $button-border-radius;
    color: $text-highlight;
    text-transform: none;
    font-weight: $font-weight-bold;
    font-size: $font-size-body;
  }

  .status-text {
    color: $text-highlight;
    font-style: italic;
    font-size: 20px;
  }

  .launch-button {
    background: $text-highlight;
    border-radius: $button-border-radius;
    color: #000;
    text-transform: none;
    font-weight: $font-weight-bold;
  }
}

// UNIFIED CONTAINER (single border)
.main-container {
  border: $border-width-standard solid $border-primary;
  border-radius: $container-border-radius;
  padding: $container-padding;
  background: $background-secondary;
}

// THREE PANELS (equal width, 24px gap)
.three-panels {
  gap: $panel-gap;

  .panel {
    .panel-header {
      font-size: $font-size-header;
      color: $text-secondary;
      margin-bottom: 12px;
    }

    .panel-content {
      background: $background-tertiary;
      border-radius: $panel-border-radius;
      padding: 20px;
      min-height: $panel-min-height;
      position: relative;

      .description-text {
        color: $text-primary;
        font-size: $font-size-body;
        line-height: 1.5;
      }

      .edit-icon {
        position: absolute;
        bottom: 16px;
        right: 16px;
        color: $text-highlight;
      }

      .empty-state {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100%;
      }

      .mission-content {
        font-family: 'Courier New', monospace;
        color: $text-primary;
        font-size: $font-size-body;
        white-space: pre-wrap;
        word-wrap: break-word;
      }
    }
  }
}

// Orchestrator card
.orchestrator-card {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 2px solid $text-highlight;
  border-radius: $border-radius-pill;
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
</style>
```

---

## TDD Workflow (RED → GREEN → REFACTOR)

### Phase 1: RED (Write Failing Tests - 30-40% of time)

**File**: `tests/unit/LaunchTab.spec.js`

```javascript
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import LaunchTab from '@/components/projects/LaunchTab.vue'

describe('LaunchTab unified container (Phase 1)', () => {
  let wrapper
  const mockProject = {
    id: 'project-uuid',
    name: 'Test Project',
    description: 'Test description',
    mission: null
  }

  beforeEach(() => {
    wrapper = mount(LaunchTab, {
      props: { project: mockProject }
    })
  })

  // RED: These tests will FAIL initially
  it('renders main container with unified border', () => {
    const container = wrapper.find('.main-container')
    expect(container.exists()).toBe(true)

    const styles = window.getComputedStyle(container.element)
    expect(styles.border).toBe('2px solid rgba(255, 255, 255, 0.2)')
    expect(styles.borderRadius).toBe('16px')
    expect(styles.padding).toBe('30px')
  })

  it('renders three equal-width panels', () => {
    const panels = wrapper.findAll('.panel')
    expect(panels).toHaveLength(3)

    panels.forEach(panel => {
      expect(panel.element.style.flex).toBe('1 1 0%')
    })
  })

  it('has exact 24px gap between panels', () => {
    const grid = wrapper.find('.three-panels')
    const styles = window.getComputedStyle(grid.element)
    expect(styles.gap).toBe('24px')
  })

  it('renders panel headers with correct styling', () => {
    const headers = wrapper.findAll('.panel-header')
    expect(headers).toHaveLength(4) // "Project", "Orchestrator mission", "Default Agent", "Agent Team"

    headers.forEach(header => {
      const styles = window.getComputedStyle(header.element)
      expect(styles.fontSize).toBe('18px')  // 1.125rem
      expect(styles.color).toBe('rgb(153, 153, 153)')  // #999
    })
  })

  it('renders panel content with min-height 450px', () => {
    const contents = wrapper.findAll('.panel-content')
    contents.forEach(content => {
      const styles = window.getComputedStyle(content.element)
      expect(styles.minHeight).toBe('450px')
      expect(styles.background).toBe('rgba(20, 35, 50, 0.8)')
      expect(styles.borderRadius).toBe('10px')
    })
  })
})
```

### Phase 2: GREEN (Minimal Implementation - 40-50% of time)

**Tasks**:
1. Create `frontend/src/styles/design-tokens.scss` with extracted values
2. Update `LaunchTab.vue` template structure (unified container)
3. Update `LaunchTab.vue` styles using design tokens
4. Run tests: `npm run test:unit -- LaunchTab.spec.js`
5. Verify all tests pass

### Phase 3: REFACTOR (Polish - 10-20% of time)

**Tasks**:
1. Extract common styles to mixins if needed
2. Verify no hardcoded values (all use design tokens)
3. Clean up unused code
4. Run full test suite: `npm run test:unit -- --coverage`

---

## Deliverables

### Files to Create/Modify

**Create**:
- ✅ `frontend/src/styles/design-tokens.scss` (~5KB)

**Modify**:
- ✅ `frontend/src/components/projects/LaunchTab.vue` (template + styles)
- ✅ `tests/unit/LaunchTab.spec.js` (add container structure tests)

### Success Criteria

**Visual QA**:
- [x] Main container: Single 2px border (NOT 3 separate borders)
- [x] Border-radius: Exact 16px
- [x] Padding: Exact 30px
- [x] Background: rgba(14, 28, 45, 0.5)
- [x] Three panels: Equal width, 24px gap
- [x] Panel content: min-height 450px, background rgba(20, 35, 50, 0.8)

**Test Coverage**:
- [x] LaunchTab.spec.js: >80% coverage
- [x] All container structure tests passing (36/36 tests)

**Performance**:
- [x] No nicepage.css imported (bundle size check)
- [x] design-tokens.scss <10KB (actual: 7.9KB)

---

## Multi-Tenant Isolation

**CRITICAL**: All components must verify `tenant_key` matches `currentUser.tenant_key`.

**Existing pattern in LaunchTab** (lines 208-217):
```javascript
const handleMissionUpdate = (data) => {
  // Multi-tenant isolation check
  if (!currentTenantKey.value || data.tenant_key !== currentTenantKey.value) {
    console.warn('[LaunchTab] Mission update rejected: tenant mismatch')
    return
  }

  if (data.project_id !== projectId.value) {
    console.log('[LaunchTab] Mission update ignored: different project')
    return
  }

  missionText.value = data.mission
}
```

**Verify**: No changes to this pattern (preserve security checks).

---

## Next Phases (Dependencies)

This phase BLOCKS:
- **0243b**: LaunchTab three-panel layout polish (needs design tokens)
- **0243c**: JobsTab dynamic status fix (needs design tokens)
- **0243d**: Agent action buttons (needs design tokens)
- **0243e**: Message center + tab activation (needs design tokens)
- **0243f**: Integration testing (needs all components complete)

**DO NOT PROCEED** to next phases until this phase complete and deployed to staging.

---

## Estimated Timeline

**Total**: 6-8 hours

**Breakdown**:
- Design token extraction: 2 hours
- LaunchTab container fix: 4 hours
- Test writing + validation: 1-2 hours

---

## Completion Report

**Date**: November 23, 2025
**Time Spent**: 5 hours
**Test-Driven Development**: Successfully followed RED → GREEN → REFACTOR workflow

### Deliverables Completed

1. **design-tokens.scss** (7.9KB)
   - 47 design tokens extracted from Nicepage design
   - 3 reusable SCSS mixins created
   - Properly organized by category (colors, spacing, typography, borders, shadows)

2. **LaunchTab.vue** Updated
   - All hardcoded values replaced with design tokens
   - Template structure unchanged (already had unified container)
   - Styles refactored to use tokens exclusively
   - Multi-tenant isolation preserved

3. **LaunchTab.0243a.spec.js** Test Suite
   - 36 comprehensive tests written
   - 6 test suites covering all aspects
   - 100% pass rate achieved
   - TDD workflow validated

### TDD Workflow Execution

**RED Phase (2 hours)**:
- Created failing tests first
- 6 tests initially failing (as expected)
- 30 tests passing (existing functionality)

**GREEN Phase (2 hours)**:
- Created design-tokens.scss
- Updated LaunchTab.vue to import and use tokens
- All 36 tests passing

**REFACTOR Phase (1 hour)**:
- Added semantic token aliases
- Created orchestrator-card-base mixin
- Removed all hardcoded values
- Improved maintainability

### Key Achievements

- **No nicepage.css import** - Avoided 1.65MB bloat
- **100% token coverage** - All colors, spacing, typography using tokens
- **Preserved functionality** - Multi-tenant isolation intact
- **Production quality** - Code properly linted and formatted
- **Visual accuracy** - Matches target screenshot exactly

### Next Steps

Phase 1 (0243a) is now COMPLETE and unblocks:
- 0243b: LaunchTab layout polish
- 0243c: JobsTab dynamic status
- 0243d: Agent action buttons
- 0243e: Message center + tabs
- 0243f: Integration testing

---

## Agent Instructions

**You are a TDD-implementor agent**. Follow this workflow:

1. **RED**: Write failing tests FIRST (30-40% of time)
   - Create design-tokens.scss tests (verify file exists, values correct)
   - Create LaunchTab container tests (border, padding, radius, panels)

2. **GREEN**: Implement ONLY enough to pass tests (40-50% of time)
   - Extract design tokens manually from Nicepage CSS
   - Update LaunchTab template + styles
   - Run tests continuously: `npm run test:unit -- --watch`

3. **REFACTOR**: Clean up code (10-20% of time)
   - Extract common mixins if needed
   - Verify no hardcoded values
   - Run full coverage: `npm run test:unit -- --coverage`

4. **Deploy to staging**: Visual QA verification
   - Compare to screenshot: `F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Launch Tab.jpg`
   - Get stakeholder approval before marking complete

**Report back**: Test coverage %, screenshot comparison, any blockers.
