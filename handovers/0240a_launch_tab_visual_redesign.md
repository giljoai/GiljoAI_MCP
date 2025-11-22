# Handover 0240a: Launch Tab Visual Redesign

**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 6-8 hours
**Dependencies**: None
**Part of**: GUI Redesign Series (0240a-0240d)
**Tool**: 🌐 CCW (Cloud)
**Parallel Execution**: ✅ Yes (Group 1 - can run with 0240b)

---

## Before You Begin

**REQUIRED READING** (Critical for TDD discipline and architectural alignment):
1. **F:\GiljoAI_MCP\handovers\QUICK_LAUNCH.txt**
2. **F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md**
3. **F:\GiljoAI_MCP\handovers\code_review_nov18.md**

**Vision Document Reference**:
- **F:\GiljoAI_MCP\handovers\Launch-Jobs_panels2\Refactor visuals for launch and implementation.pdf** (Slides 2-9)

**Execute in order**: Red (failing tests) → Green (minimal implementation) → Refactor (cleanup)

---

## 🎯 Objective

Redesign the Launch Tab visual appearance to match the PDF vision document (slides 2-9) while preserving all existing functionality. This is a **pure visual/styling overhaul** with zero functional changes.

---

## ⚠️ Problem Statement

**What's Broken/Missing**:
- Current Launch Tab uses default Vuetify card elevations and standard styling
- PDF vision document shows a refined dark theme with custom borders, spacing, and typography
- Mission panel needs custom scrollbars and monospace font
- Agent cards need info/lock icons
- "Stage Project" and "Launch Jobs" buttons need visual prominence

**Evidence**:
- Current UI at `http://10.1.0.164:7274/projects/{id}?via=jobs` shows old styling
- User feedback: "I still see the old UI in the 'launch' vue tab"

**User Impact**:
- Lack of visual polish reduces perceived professionalism
- Difficult to distinguish interactive elements
- Mission text harder to read without monospace font

**Why This Needs Fixing**:
- Visual consistency with product vision document
- Improved UX through better visual hierarchy
- Professional appearance for production deployment

---

## ✅ Solution Approach

**High-Level Strategy**:
1. Update panel styling (borders, backgrounds, spacing) to match PDF dark theme
2. Apply custom scrollbars to Project Description and Mission panels
3. Add monospace font to Orchestrator Mission panel
4. Enhance button styling ("Stage Project" yellow border, "Launch Jobs" yellow fill)
5. Add info/lock icons to agent cards
6. Refine typography (panel headers uppercase, adjusted weights)
7. Update empty state icons

**Key Principles**:
- **No functional changes** - all interactions remain identical
- **Preserve existing Vuetify components** - only modify styling props and CSS
- **Maintain responsiveness** - ensure mobile/tablet compatibility
- **Keep WebSocket updates working** - no changes to reactive data

---

## 📝 Implementation Tasks

### Task 1: Panel Styling Overhaul (2 hours)

**File**: `frontend/src/components/projects/LaunchTab.vue` (MODIFY)

**What to Build**:
Replace default `v-card` elevations with custom border styling matching PDF design.

**Current Code Pattern** (lines ~50-150):
```vue
<v-card class="mb-4" elevation="2">
  <v-card-title>Project Description</v-card-title>
  <v-card-text>{{ project.description }}</v-card-text>
</v-card>
```

**New Code Pattern**:
```vue
<v-card class="launch-panel mb-4" flat>
  <v-card-title class="panel-header">PROJECT DESCRIPTION</v-card-title>
  <v-card-text class="panel-content scrollable-panel">
    {{ project.description }}
  </v-card-text>
</v-card>

<style scoped>
.launch-panel {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
}

.panel-header {
  text-transform: uppercase;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.7);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 16px;
}

.panel-content {
  padding: 16px;
  color: rgba(255, 255, 255, 0.9);
}

.scrollable-panel {
  max-height: 300px;
  overflow-y: auto;
}

/* Custom scrollbar styling */
.scrollable-panel::-webkit-scrollbar {
  width: 8px;
}

.scrollable-panel::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.scrollable-panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.scrollable-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
```

**Apply to**:
- Project Description panel
- Orchestrator Mission panel (see Task 2 for additional monospace styling)
- Default Agent (Orchestrator) card

---

### Task 2: Orchestrator Mission Panel Typography (1 hour)

**File**: `frontend/src/components/projects/LaunchTab.vue` (MODIFY)

**What to Build**:
Add monospace font to Orchestrator Mission panel for better code/prompt readability.

**New Code Pattern**:
```vue
<v-card class="launch-panel mission-panel mb-4" flat>
  <v-card-title class="panel-header">ORCHESTRATOR GENERATED MISSION</v-card-title>
  <v-card-text class="panel-content scrollable-panel mission-text">
    {{ orchestratorMission || 'Mission will appear after staging...' }}
  </v-card-text>
</v-card>

<style scoped>
.mission-text {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
```

**Success Check**:
- Mission text uses monospace font
- Long prompts wrap correctly
- Custom scrollbar appears when content exceeds max-height

---

### Task 3: Button Styling Enhancement (1 hour)

**File**: `frontend/src/components/projects/LaunchTab.vue` (MODIFY)

**What to Build**:
Update "Stage Project" and "Launch Jobs" button styling for visual prominence.

**Current Code Pattern** (lines ~200-250):
```vue
<v-btn @click="stageProject" color="primary">Stage Project</v-btn>
<v-btn @click="switchToImplement" color="success">Launch Jobs</v-btn>
```

**New Code Pattern**:
```vue
<v-btn
  @click="stageProject"
  variant="outlined"
  color="yellow-darken-2"
  size="large"
  class="stage-project-btn"
  :loading="stagingInProgress"
>
  <v-icon left>mdi-clipboard-text</v-icon>
  Stage Project
</v-btn>

<v-btn
  @click="switchToImplement"
  variant="flat"
  color="yellow-darken-2"
  size="large"
  class="launch-jobs-btn"
  :disabled="!projectStaged"
>
  <v-icon left>mdi-rocket-launch</v-icon>
  Launch Jobs
</v-btn>

<style scoped>
.stage-project-btn {
  border-width: 2px;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
}

.launch-jobs-btn {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  color: rgba(0, 0, 0, 0.87) !important;
}

.launch-jobs-btn:disabled {
  opacity: 0.4;
}
</style>
```

**Success Check**:
- "Stage Project" has yellow outlined border
- "Launch Jobs" has yellow filled background
- Icons appear to left of text
- Disabled state works correctly

---

### Task 4: Agent Card Icons (1.5 hours)

**File**: `frontend/src/components/projects/LaunchTab.vue` (MODIFY)

**What to Build**:
Add info button and lock icon to Default Agent (Orchestrator) card.

**Current Code Pattern** (lines ~300-350):
```vue
<v-card class="agent-card">
  <v-card-title>Orchestrator</v-card-title>
  <v-card-text>Default agent coordinating workflow</v-card-text>
</v-card>
```

**New Code Pattern**:
```vue
<v-card class="launch-panel agent-card" flat>
  <v-card-title class="d-flex align-center justify-space-between">
    <div class="d-flex align-center">
      <v-icon class="mr-2" color="primary">mdi-account-tie</v-icon>
      <span>Orchestrator</span>
      <v-icon class="ml-2" size="small" color="grey">mdi-lock</v-icon>
    </div>
    <v-btn
      icon
      size="small"
      variant="text"
      @click="showOrchestratorInfo"
    >
      <v-icon size="small">mdi-information-outline</v-icon>
    </v-btn>
  </v-card-title>
  <v-card-text class="panel-content">
    Default agent coordinating workflow
  </v-card-text>
</v-card>

<script setup>
const showOrchestratorInfo = () => {
  // Open modal showing uneditable orchestrator template
  // Implementation can reuse existing modal logic
  console.log('Show orchestrator template info');
};
</script>

<style scoped>
.agent-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: all 0.3s ease;
}

.agent-card:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.2);
}
</style>
```

**Success Check**:
- Lock icon appears next to Orchestrator name
- Info button (ℹ️) appears on right side
- Hover state shows subtle background change
- Info button click triggers console log (modal implementation in 0240b)

---

### Task 5: Agent Team Cards Styling (1 hour)

**File**: `frontend/src/components/projects/LaunchTab.vue` (MODIFY)

**What to Build**:
Apply consistent styling to Agent Team cards in horizontal scroll section.

**Current Code Pattern** (lines ~400-500):
```vue
<div v-for="agent in agentTeam" :key="agent.id">
  <v-card>
    <v-card-title>{{ agent.type }}</v-card-title>
    <v-btn icon @click="editAgent(agent)">
      <v-icon>mdi-pencil</v-icon>
    </v-btn>
  </v-card>
</div>
```

**New Code Pattern**:
```vue
<div class="agent-team-scroll">
  <v-card
    v-for="agent in agentTeam"
    :key="agent.id"
    class="launch-panel agent-team-card"
    flat
  >
    <v-card-title class="d-flex align-center justify-space-between">
      <div class="d-flex align-center">
        <v-icon class="mr-2" :color="getAgentColor(agent.type)">
          {{ getAgentIcon(agent.type) }}
        </v-icon>
        <span>{{ agent.type }}</span>
      </div>
      <v-btn
        icon
        size="small"
        variant="text"
        @click="editAgent(agent)"
      >
        <v-icon size="small">mdi-pencil</v-icon>
      </v-btn>
    </v-card-title>
    <v-card-text class="panel-content text-caption">
      {{ agent.description }}
    </v-card-text>
  </v-card>
</div>

<style scoped>
.agent-team-scroll {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.agent-team-card {
  min-width: 280px;
  flex-shrink: 0;
}

.agent-team-scroll::-webkit-scrollbar {
  height: 6px;
}

.agent-team-scroll::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.agent-team-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}
</style>
```

**Success Check**:
- Horizontal scroll works smoothly
- Cards have consistent spacing (16px gap)
- Edit button appears on hover
- Icons show correct color per agent type

---

### Task 6: Empty States Update (0.5 hours)

**File**: `frontend/src/components/projects/LaunchTab.vue` (MODIFY)

**What to Build**:
Update empty state icons and text styling.

**Current Code Pattern**:
```vue
<div v-if="!orchestratorMission">
  <v-icon>mdi-file</v-icon>
  <p>Mission will appear after staging...</p>
</div>
```

**New Code Pattern**:
```vue
<div v-if="!orchestratorMission" class="empty-state">
  <v-icon size="48" color="grey-darken-1">mdi-file-document-outline</v-icon>
  <p class="text-caption mt-2 text-grey-darken-1">
    Mission will appear after staging...
  </p>
</div>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  opacity: 0.6;
}
</style>
```

**Apply to**:
- Orchestrator Mission panel empty state
- Agent Team section empty state
- Project Description empty state (if applicable)

---

### Task 7: Responsive Design Refinements (1 hour)

**File**: `frontend/src/components/projects/LaunchTab.vue` (MODIFY)

**What to Build**:
Ensure all styling works on mobile/tablet/desktop viewports.

**New Code Pattern**:
```vue
<style scoped>
/* Mobile (< 600px) */
@media (max-width: 599px) {
  .launch-panel {
    margin-bottom: 12px;
  }

  .panel-header {
    font-size: 0.7rem;
    padding: 10px 12px;
  }

  .panel-content {
    padding: 12px;
  }

  .stage-project-btn,
  .launch-jobs-btn {
    width: 100%;
    margin-bottom: 8px;
  }

  .agent-team-card {
    min-width: 240px;
  }
}

/* Tablet (600px - 960px) */
@media (min-width: 600px) and (max-width: 959px) {
  .agent-team-card {
    min-width: 260px;
  }
}

/* Desktop (> 960px) */
@media (min-width: 960px) {
  .scrollable-panel {
    max-height: 400px;
  }
}
</style>
```

**Success Check**:
- Mobile: Buttons stack vertically, panels have reduced padding
- Tablet: Agent cards are medium width
- Desktop: Panels use larger max-height for scrollable areas

---

## 🧪 Testing Strategy

### Unit Tests

**File**: `frontend/tests/unit/components/projects/LaunchTab.0240a.spec.js` (NEW)

```javascript
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import LaunchTab from '@/components/projects/LaunchTab.vue';

describe('LaunchTab Visual Redesign (0240a)', () => {
  it('applies custom panel styling with borders', () => {
    const wrapper = mount(LaunchTab, {
      props: { project: { description: 'Test project' } }
    });

    const panel = wrapper.find('.launch-panel');
    expect(panel.exists()).toBe(true);
    expect(panel.classes()).toContain('launch-panel');
  });

  it('renders panel headers in uppercase', () => {
    const wrapper = mount(LaunchTab, {
      props: { project: { description: 'Test' } }
    });

    const header = wrapper.find('.panel-header');
    expect(header.text()).toMatch(/^[A-Z\s]+$/); // All uppercase
  });

  it('applies monospace font to mission text', () => {
    const wrapper = mount(LaunchTab, {
      props: { orchestratorMission: 'Test mission prompt...' }
    });

    const missionText = wrapper.find('.mission-text');
    expect(missionText.exists()).toBe(true);
  });

  it('renders Stage Project button with yellow outline', () => {
    const wrapper = mount(LaunchTab);

    const stageBtn = wrapper.find('.stage-project-btn');
    expect(stageBtn.exists()).toBe(true);
    expect(stageBtn.attributes('variant')).toBe('outlined');
  });

  it('renders Launch Jobs button with yellow fill', () => {
    const wrapper = mount(LaunchTab);

    const launchBtn = wrapper.find('.launch-jobs-btn');
    expect(launchBtn.exists()).toBe(true);
    expect(launchBtn.attributes('variant')).toBe('flat');
  });

  it('shows lock icon on Orchestrator card', () => {
    const wrapper = mount(LaunchTab);

    const lockIcon = wrapper.find('.agent-card .mdi-lock');
    expect(lockIcon.exists()).toBe(true);
  });

  it('shows info button on Orchestrator card', () => {
    const wrapper = mount(LaunchTab);

    const infoBtn = wrapper.find('.agent-card .mdi-information-outline');
    expect(infoBtn.exists()).toBe(true);
  });

  it('applies custom scrollbar to scrollable panels', () => {
    const wrapper = mount(LaunchTab, {
      props: { project: { description: 'Long text...'.repeat(100) } }
    });

    const scrollable = wrapper.find('.scrollable-panel');
    expect(scrollable.exists()).toBe(true);
  });

  it('renders empty state with document icon', () => {
    const wrapper = mount(LaunchTab, {
      props: { orchestratorMission: null }
    });

    const emptyState = wrapper.find('.empty-state');
    const icon = emptyState.find('.mdi-file-document-outline');
    expect(icon.exists()).toBe(true);
  });

  it('preserves all existing functionality', async () => {
    const wrapper = mount(LaunchTab);

    // Test Stage Project button click
    const stageBtn = wrapper.find('.stage-project-btn');
    await stageBtn.trigger('click');
    expect(wrapper.emitted('stage-project')).toBeTruthy();

    // Test Launch Jobs button click
    const launchBtn = wrapper.find('.launch-jobs-btn');
    await launchBtn.trigger('click');
    expect(wrapper.emitted('switch-to-implement')).toBeTruthy();
  });
});
```

**Coverage Target**: >80% (focus on visual element presence, not CSS values)

---

### Integration Tests

**Manual Validation Steps**:

1. **Navigate to Launch Tab** (`http://10.1.0.164:7274/projects/{id}?via=jobs`)
2. **Verify Panel Styling**:
   - [ ] Project Description panel has rounded border
   - [ ] Orchestrator Mission panel has rounded border
   - [ ] Mission text uses monospace font
   - [ ] Custom scrollbars appear when content overflows
3. **Verify Button Styling**:
   - [ ] "Stage Project" has yellow outlined border
   - [ ] "Launch Jobs" has yellow filled background
   - [ ] Icons appear to left of button text
4. **Verify Agent Cards**:
   - [ ] Orchestrator card shows lock icon
   - [ ] Info button appears on Orchestrator card
   - [ ] Agent Team cards have consistent styling
   - [ ] Horizontal scroll works smoothly
5. **Verify Empty States**:
   - [ ] Empty mission panel shows document icon
   - [ ] Empty text is centered and styled correctly
6. **Verify Responsive Design**:
   - [ ] Mobile: Buttons stack vertically
   - [ ] Tablet: Panels adjust appropriately
   - [ ] Desktop: All elements properly sized

**Browser Testing**:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Edge (latest)

---

## ✅ Success Criteria

**Must Have**:
- [ ] All panels use custom border styling (no default elevations)
- [ ] Panel headers are uppercase with reduced font size
- [ ] Orchestrator Mission panel uses monospace font
- [ ] Custom scrollbars appear on all scrollable panels
- [ ] "Stage Project" button has yellow outlined border
- [ ] "Launch Jobs" button has yellow filled background
- [ ] Orchestrator card shows lock icon and info button
- [ ] Agent Team cards have consistent styling with edit button
- [ ] Empty states use updated icons and text styling
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] All existing functionality preserved (no regressions)
- [ ] Unit tests pass (>80% coverage)
- [ ] Visual appearance matches PDF slides 2-9

**Nice to Have**:
- [ ] Smooth animations/transitions on hover states
- [ ] Accessibility improvements (ARIA labels, focus states)
- [ ] Dark mode theme variables extracted to CSS custom properties

---

## 🔄 Rollback Plan

If implementation causes issues:

1. **Revert LaunchTab.vue changes**:
   ```bash
   git checkout HEAD~1 -- frontend/src/components/projects/LaunchTab.vue
   ```

2. **Remove new test file**:
   ```bash
   git rm frontend/tests/unit/components/projects/LaunchTab.0240a.spec.js
   ```

3. **Rebuild frontend**:
   ```bash
   cd frontend
   npm run build
   ```

**No database changes** - pure frontend styling, safe to revert.

---

## Cleanup Checklist

**Old Code Removed**:
- [ ] No commented-out blocks remaining
- [ ] No orphaned imports (old icon names, unused utilities)
- [ ] No unused CSS classes
- [ ] No TODOs without tickets

**Integration Verified**:
- [ ] Existing Vuetify components reused (no custom replacements)
- [ ] No duplicate styling (DRY principle)
- [ ] Shared styles extracted to scoped <style> block
- [ ] No zombie code (unreachable branches)

**Testing**:
- [ ] All imports resolved
- [ ] No linting errors (`npm run lint`)
- [ ] No console errors in browser
- [ ] Coverage maintained (>80%)

---

## 📚 Related Handovers

**Depends on**: None (independent task)
**Blocks**: None
**Related**:
- **0240b**: Implement Tab Component Refactor (parallel execution)
- **0240c**: GUI Redesign Integration Testing (sequential after merge)
- **0240d**: GUI Redesign Documentation (parallel with 0240c)

**Part of Series**: GUI Redesign (0240a-0240d)

---

## 🛠️ Tool Justification: Why CCW?

**CCW Suitability**:
- ✅ **Pure frontend code** - No database access required
- ✅ **Independent task** - No dependencies on 0240b
- ✅ **Can run in parallel** - Different files than 0240b
- ✅ **Single component focus** - Modifies only `LaunchTab.vue`
- ✅ **No backend integration testing** - Visual changes only

**Why NOT CLI**:
- ❌ No database operations needed
- ❌ No integration testing required (saved for 0240c)
- ❌ No file system operations beyond code edits

**Parallel Execution Strategy**:
- Run 0240a (this handover) and 0240b simultaneously in separate CCW sessions
- Both create separate branches
- User merges both PRs after completion
- 0240c (CLI) runs integration testing on merged code

---

## 🎯 Execution Notes for AI Agent

**Key Implementation Priorities**:
1. **Start with panel styling** (Task 1) - establishes visual foundation
2. **Add monospace font** (Task 2) - improves mission readability
3. **Update buttons** (Task 3) - high visual impact
4. **Add agent icons** (Task 4) - completes card design
5. **Polish details** (Tasks 5-7) - refinements and responsiveness

**Common Pitfalls to Avoid**:
- Don't remove existing Vue event handlers (`@click`, `@input`, etc.)
- Don't change reactive data properties (only styling)
- Don't modify WebSocket subscription logic
- Don't hardcode colors (use Vuetify theme variables where possible)

**Testing Reminders**:
- Write tests FIRST (TDD discipline)
- Focus on element presence, not exact CSS values
- Test responsive breakpoints with viewport resizing
- Verify no console errors after changes

---

## 📝 Completion Summary (To be filled after execution)

**Status**: ⏳ Ready for Implementation
**Completed**: [Date]
**Actual Effort**: [X hours vs 6-8 estimated]

**Files Modified**:
- `frontend/src/components/projects/LaunchTab.vue` ([X lines changed])
- `frontend/tests/unit/components/projects/LaunchTab.0240a.spec.js` (NEW - [X lines])

**Test Results**: [X/X passing]
**Coverage**: [X%]

**Key Decisions**:
- [Any deviations from plan]
- [Design choices made]

**Next Steps**:
→ Merge with **0240b** (Implement Tab Components)
→ Proceed to **0240c** (Integration Testing)
