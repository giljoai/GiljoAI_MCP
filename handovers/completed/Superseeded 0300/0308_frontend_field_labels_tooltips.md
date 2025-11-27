# Handover 0308: Frontend Field Labels & Tooltips

**Feature**: Human-Readable Field Labels and Descriptive Tooltips
**Status**: Not Started
**Priority**: P2 - MEDIUM
**Estimated Duration**: 4-5 hours
**Agent Budget**: 90K tokens
**Depends On**: Handover 0307 (Backend Default Field Priorities)
**Blocks**: Handover 0309 (Token Estimation Improvements)
**Created**: 2025-11-16
**Tool**: CCW (Frontend component changes, UI/UX improvements)

---

## Executive Summary

The frontend currently displays 13 field badges using raw field paths (e.g., "tech_stack.languages") instead of human-readable labels (e.g., "Programming Languages"). Users must decipher technical field names and have no tooltips explaining what each field controls or how it affects agent missions.

**Why This Matters**: Users need clear, intuitive labels and helpful tooltips to understand the field priority system. Following the pattern established in `mission_planner.py` (lines 90-104), we'll create a comprehensive `FIELD_LABELS` mapping and tooltip system that makes the priority UI accessible to non-technical users.

**Impact**: Dramatically improves UX for field priority management, reduces user confusion, provides inline help without requiring documentation lookups.

---

## Problem Statement

### Current Behavior

**Frontend Field Display** (assumed from typical Vue component):
```vue
<v-chip v-for="field in fields" :key="field">
  {{ field }}  <!-- Displays: "tech_stack.languages" -->
</v-chip>
```

**Issues**:
1. Raw field paths displayed: "tech_stack.languages" (not user-friendly)
2. No human-readable labels: Users don't know what "test_config.strategy" means
3. No tooltips: No explanation of what each field controls
4. No context: Users don't understand impact of priority changes
5. Inconsistent with backend: Backend has `FIELD_LABELS` (mission_planner.py:90-104)

### Desired Behavior

**Enhanced Field Display**:
```vue
<v-chip v-for="field in fields" :key="field">
  <v-tooltip location="top">
    <template #activator="{ props }">
      <span v-bind="props">{{ getFieldLabel(field) }}</span>
    </template>
    <div class="tooltip-content">
      <strong>{{ getFieldLabel(field) }}</strong>
      <p>{{ getFieldDescription(field) }}</p>
      <em>Priority {{ getFieldPriority(field) }}: {{ getPriorityDescription(field) }}</em>
    </div>
  </v-tooltip>
</v-chip>
```

**Example Tooltip**:
```
Programming Languages
Controls which programming languages appear in agent missions.

Priority 1: Full language list with version requirements
Priority 2: Primary languages only
Priority 3: Language names only (no versions)
Unassigned: Languages excluded from mission context
```

---

## Objectives

### Primary Goals
1. Create `FIELD_LABELS` mapping for all 15 fields (13 product config + 2 context)
2. Create `FIELD_DESCRIPTIONS` mapping explaining each field's purpose
3. Create `PRIORITY_LEVEL_DESCRIPTIONS` explaining what each priority tier means
4. Update field priority UI component to use labels instead of raw paths
5. Add tooltips with field descriptions and priority explanations

### Success Criteria
- ✅ All 15 fields have human-readable labels
- ✅ All 15 fields have descriptive tooltips
- ✅ Tooltips explain both field purpose and priority impact
- ✅ Labels match backend pattern (mission_planner.py:90-104)
- ✅ Tooltips are accessible (keyboard navigation, screen reader compatible)
- ✅ No regressions in field priority drag-and-drop functionality
- ✅ Visual design matches Vuetify theme and existing UI patterns

---

## TDD Specifications

### Test 1: All Fields Have Human-Readable Labels
```javascript
// tests/unit/FieldPriorityLabels.spec.js
import { describe, it, expect } from 'vitest';
import { FIELD_LABELS } from '@/constants/fieldPriorityLabels';

describe('FIELD_LABELS mapping', () => {
  it('should have labels for all 15 fields', () => {
    const expectedFields = [
      // Product config fields (13)
      'tech_stack.languages',
      'tech_stack.backend',
      'tech_stack.frontend',
      'tech_stack.database',
      'tech_stack.infrastructure',
      'architecture.pattern',
      'architecture.api_style',
      'architecture.design_patterns',
      'architecture.notes',
      'features.core',
      'test_config.strategy',
      'test_config.frameworks',
      'test_config.coverage_target',
      // Context fields (2)
      'codebase_summary',
      'architecture_overview',
    ];

    expectedFields.forEach(field => {
      expect(FIELD_LABELS[field]).toBeDefined();
      expect(typeof FIELD_LABELS[field]).toBe('string');
      expect(FIELD_LABELS[field].length).toBeGreaterThan(0);
    });

    expect(Object.keys(FIELD_LABELS).length).toBe(15);
  });

  it('should use title case for labels', () => {
    Object.values(FIELD_LABELS).forEach(label => {
      // Labels should start with capital letter
      expect(label[0]).toBe(label[0].toUpperCase());
      // Labels should not be all caps (except acronyms)
      expect(label).not.toBe(label.toUpperCase());
    });
  });

  it('should not include technical jargon in labels', () => {
    Object.values(FIELD_LABELS).forEach(label => {
      // Labels should be user-friendly
      expect(label).not.toContain('config');
      expect(label).not.toContain('_');
      expect(label).not.toContain('.');
    });
  });
});
```

### Test 2: All Fields Have Descriptive Tooltips
```javascript
// tests/unit/FieldPriorityDescriptions.spec.js
import { describe, it, expect } from 'vitest';
import { FIELD_DESCRIPTIONS } from '@/constants/fieldPriorityLabels';

describe('FIELD_DESCRIPTIONS mapping', () => {
  it('should have descriptions for all 15 fields', () => {
    const expectedFields = [
      'tech_stack.languages', 'tech_stack.backend', 'tech_stack.frontend',
      'tech_stack.database', 'tech_stack.infrastructure',
      'architecture.pattern', 'architecture.api_style', 'architecture.design_patterns',
      'architecture.notes', 'features.core',
      'test_config.strategy', 'test_config.frameworks', 'test_config.coverage_target',
      'codebase_summary', 'architecture_overview',
    ];

    expectedFields.forEach(field => {
      expect(FIELD_DESCRIPTIONS[field]).toBeDefined();
      expect(typeof FIELD_DESCRIPTIONS[field]).toBe('string');
      expect(FIELD_DESCRIPTIONS[field].length).toBeGreaterThan(20); // Meaningful description
    });
  });

  it('should explain field purpose and impact', () => {
    // Descriptions should answer: "What does this field control?"
    const languagesDesc = FIELD_DESCRIPTIONS['tech_stack.languages'];

    expect(languagesDesc.toLowerCase()).toContain('language');
    expect(languagesDesc.toLowerCase()).toMatch(/agent|mission|context/);
  });

  it('should be concise (under 150 characters)', () => {
    Object.values(FIELD_DESCRIPTIONS).forEach(description => {
      expect(description.length).toBeLessThan(150);
    });
  });
});
```

### Test 3: Field Labels Display in UI Component
```javascript
// tests/components/FieldPriorityManager.spec.js
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import FieldPriorityManager from '@/components/FieldPriorityManager.vue';
import { vuetify } from '@/plugins/vuetify';

describe('FieldPriorityManager Component', () => {
  it('should display human-readable labels instead of field paths', () => {
    const wrapper = mount(FieldPriorityManager, {
      global: {
        plugins: [vuetify],
      },
      props: {
        fields: {
          'tech_stack.languages': 1,
          'tech_stack.backend': 1,
          'codebase_summary': 2,
        },
      },
    });

    // Should show "Programming Languages", not "tech_stack.languages"
    expect(wrapper.text()).toContain('Programming Languages');
    expect(wrapper.text()).toContain('Backend Stack');
    expect(wrapper.text()).toContain('Codebase Summary');

    // Should NOT show raw field paths
    expect(wrapper.text()).not.toContain('tech_stack.languages');
    expect(wrapper.text()).not.toContain('tech_stack.backend');
  });

  it('should display tooltips on hover', async () => {
    const wrapper = mount(FieldPriorityManager, {
      global: {
        plugins: [vuetify],
      },
      props: {
        fields: { 'tech_stack.languages': 1 },
      },
    });

    // Find tooltip activator
    const chip = wrapper.find('.field-chip');
    expect(chip.exists()).toBe(true);

    // Tooltip component should exist
    const tooltip = wrapper.findComponent({ name: 'VTooltip' });
    expect(tooltip.exists()).toBe(true);
  });
});
```

### Test 4: Priority Level Descriptions Available
```javascript
// tests/unit/PriorityLevelDescriptions.spec.js
import { describe, it, expect } from 'vitest';
import { PRIORITY_LEVEL_DESCRIPTIONS } from '@/constants/fieldPriorityLabels';

describe('PRIORITY_LEVEL_DESCRIPTIONS mapping', () => {
  it('should have descriptions for all priority levels', () => {
    expect(PRIORITY_LEVEL_DESCRIPTIONS[1]).toBeDefined();
    expect(PRIORITY_LEVEL_DESCRIPTIONS[2]).toBeDefined();
    expect(PRIORITY_LEVEL_DESCRIPTIONS[3]).toBeDefined();
    expect(PRIORITY_LEVEL_DESCRIPTIONS.unassigned).toBeDefined();
  });

  it('should explain token budget impact', () => {
    const priority1Desc = PRIORITY_LEVEL_DESCRIPTIONS[1];
    const priority2Desc = PRIORITY_LEVEL_DESCRIPTIONS[2];
    const priority3Desc = PRIORITY_LEVEL_DESCRIPTIONS[3];

    // Priority 1: Full detail
    expect(priority1Desc.toLowerCase()).toMatch(/full|always|complete/);

    // Priority 2: Summary
    expect(priority2Desc.toLowerCase()).toMatch(/summary|high|important/);

    // Priority 3: Minimal
    expect(priority3Desc.toLowerCase()).toMatch(/minimal|medium|basic/);

    // Unassigned: Excluded
    expect(PRIORITY_LEVEL_DESCRIPTIONS.unassigned.toLowerCase()).toMatch(/exclude|omit|not include/);
  });
});
```

### Test 5: Tooltip Accessibility
```javascript
// tests/components/FieldPriorityTooltip.a11y.spec.js
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import FieldChipWithTooltip from '@/components/FieldChipWithTooltip.vue';
import { axe } from 'vitest-axe';

describe('FieldChipWithTooltip Accessibility', () => {
  it('should have proper ARIA attributes', () => {
    const wrapper = mount(FieldChipWithTooltip, {
      props: {
        field: 'tech_stack.languages',
        priority: 1,
      },
    });

    const activator = wrapper.find('[role="button"]');
    expect(activator.exists()).toBe(true);

    // Tooltip should be described by aria-describedby
    expect(activator.attributes('aria-describedby')).toBeDefined();
  });

  it('should be keyboard navigable', async () => {
    const wrapper = mount(FieldChipWithTooltip, {
      props: {
        field: 'tech_stack.languages',
        priority: 1,
      },
    });

    const activator = wrapper.find('.field-chip');

    // Focus on element
    await activator.trigger('focus');

    // Tooltip should appear on focus (not just hover)
    // (Vuetify VTooltip handles this automatically)
    expect(activator.attributes('tabindex')).toBe('0');
  });

  it('should pass axe accessibility tests', async () => {
    const wrapper = mount(FieldChipWithTooltip, {
      props: {
        field: 'tech_stack.languages',
        priority: 1,
      },
    });

    const results = await axe(wrapper.html());
    expect(results.violations).toHaveLength(0);
  });
});
```

---

## Implementation Plan

### Step 1: Create Field Labels Constants File
**File**: `frontend/src/constants/fieldPriorityLabels.js` (NEW FILE)

**Content**:
```javascript
/**
 * Human-readable labels for field priority configuration fields.
 *
 * Follows the pattern from backend src/giljo_mcp/mission_planner.py (lines 90-104).
 *
 * @type {Record<string, string>}
 */
export const FIELD_LABELS = {
  // Tech Stack Fields
  'tech_stack.languages': 'Programming Languages',
  'tech_stack.backend': 'Backend Stack',
  'tech_stack.frontend': 'Frontend Stack',
  'tech_stack.database': 'Databases',
  'tech_stack.infrastructure': 'Infrastructure',

  // Architecture Fields
  'architecture.pattern': 'Architecture Pattern',
  'architecture.api_style': 'API Style',
  'architecture.design_patterns': 'Design Patterns',
  'architecture.notes': 'Architecture Notes',

  // Feature Fields
  'features.core': 'Core Features',

  // Test Configuration Fields
  'test_config.strategy': 'Testing Strategy',
  'test_config.frameworks': 'Testing Frameworks',
  'test_config.coverage_target': 'Coverage Target',

  // Context Fields (added in Handover 0307)
  'codebase_summary': 'Codebase Summary',
  'architecture_overview': 'Architecture Overview',
};

/**
 * Descriptive tooltips for each field explaining purpose and impact.
 *
 * @type {Record<string, string>}
 */
export const FIELD_DESCRIPTIONS = {
  // Tech Stack Fields
  'tech_stack.languages':
    'Programming languages used in the project. Controls language-specific context in agent missions.',
  'tech_stack.backend':
    'Backend frameworks and runtime environment. Guides agent implementation decisions.',
  'tech_stack.frontend':
    'Frontend frameworks and UI libraries. Helps agents understand UI component architecture.',
  'tech_stack.database':
    'Database systems and configuration. Ensures agents use correct database patterns.',
  'tech_stack.infrastructure':
    'Deployment, hosting, and infrastructure details. Provides context for deployment-related tasks.',

  // Architecture Fields
  'architecture.pattern':
    'Core architectural pattern (MVC, microservices, etc.). Fundamental to agent understanding.',
  'architecture.api_style':
    'API architecture approach (REST, GraphQL, etc.). Guides API implementation consistency.',
  'architecture.design_patterns':
    'Specific design patterns in use. Helps agents follow established code patterns.',
  'architecture.notes':
    'Additional architectural context and decisions. Provides historical context.',

  // Feature Fields
  'features.core':
    'Essential product features and capabilities. Helps agents understand product scope.',

  // Test Configuration Fields
  'test_config.strategy':
    'Testing approach and methodology (TDD, BDD, etc.). Guides test implementation.',
  'test_config.frameworks':
    'Testing frameworks and tools (pytest, Jest, etc.). Ensures correct test syntax.',
  'test_config.coverage_target':
    'Code coverage requirements. Sets quality standards for agent-written tests.',

  // Context Fields
  'codebase_summary':
    'Overview of existing codebase structure. Helps agents avoid duplication and maintain consistency.',
  'architecture_overview':
    'System architecture and component relationships. Guides agents in maintaining architectural integrity.',
};

/**
 * Descriptions for each priority level explaining detail level and token impact.
 *
 * @type {Record<number|string, string>}
 */
export const PRIORITY_LEVEL_DESCRIPTIONS = {
  1: 'Full detail - Always included regardless of token budget. Critical for agent understanding.',
  2: 'Summary detail - Included unless token budget is severely constrained. Important context.',
  3: 'Minimal detail - Included when token budget permits. Additional context and best practices.',
  unassigned: 'Excluded - This field will not be included in agent mission context.',
};

/**
 * Helper function to get human-readable label for a field.
 *
 * @param {string} fieldPath - Dot-notation field path (e.g., 'tech_stack.languages')
 * @returns {string} Human-readable label
 */
export function getFieldLabel(fieldPath) {
  return FIELD_LABELS[fieldPath] || fieldPath;
}

/**
 * Helper function to get description for a field.
 *
 * @param {string} fieldPath - Dot-notation field path
 * @returns {string} Field description
 */
export function getFieldDescription(fieldPath) {
  return FIELD_DESCRIPTIONS[fieldPath] || 'No description available.';
}

/**
 * Helper function to get priority level description.
 *
 * @param {number|null} priority - Priority level (1, 2, 3, or null for unassigned)
 * @returns {string} Priority level description
 */
export function getPriorityDescription(priority) {
  if (priority === null || priority === undefined) {
    return PRIORITY_LEVEL_DESCRIPTIONS.unassigned;
  }
  return PRIORITY_LEVEL_DESCRIPTIONS[priority] || 'Unknown priority level.';
}
```

### Step 2: Create Reusable Tooltip Component
**File**: `frontend/src/components/FieldChipWithTooltip.vue` (NEW FILE)

**Content**:
```vue
<template>
  <v-tooltip location="top" max-width="400">
    <template #activator="{ props }">
      <v-chip
        v-bind="props"
        :color="chipColor"
        :variant="variant"
        :size="size"
        class="field-chip"
        tabindex="0"
      >
        <slot>{{ fieldLabel }}</slot>
      </v-chip>
    </template>

    <div class="tooltip-content">
      <div class="tooltip-header">{{ fieldLabel }}</div>
      <p class="tooltip-description">{{ fieldDescription }}</p>
      <div v-if="priority !== undefined" class="tooltip-priority">
        <strong>Priority {{ priorityDisplay }}:</strong>
        {{ priorityDescription }}
      </div>
    </div>
  </v-tooltip>
</template>

<script setup>
import { computed } from 'vue';
import { getFieldLabel, getFieldDescription, getPriorityDescription } from '@/constants/fieldPriorityLabels';

const props = defineProps({
  field: {
    type: String,
    required: true,
  },
  priority: {
    type: Number,
    default: undefined,
  },
  color: {
    type: String,
    default: 'primary',
  },
  variant: {
    type: String,
    default: 'flat',
  },
  size: {
    type: String,
    default: 'default',
  },
});

const fieldLabel = computed(() => getFieldLabel(props.field));
const fieldDescription = computed(() => getFieldDescription(props.field));
const priorityDescription = computed(() => getPriorityDescription(props.priority));
const priorityDisplay = computed(() => {
  if (props.priority === null || props.priority === undefined) {
    return 'Unassigned';
  }
  return props.priority;
});

const chipColor = computed(() => {
  if (props.priority === 1) return 'error';
  if (props.priority === 2) return 'warning';
  if (props.priority === 3) return 'success';
  return 'default';
});
</script>

<style scoped>
.field-chip {
  cursor: help;
}

.field-chip:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

.tooltip-content {
  padding: 8px 0;
}

.tooltip-header {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
}

.tooltip-description {
  font-size: 13px;
  line-height: 1.4;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.9);
}

.tooltip-priority {
  font-size: 12px;
  font-style: italic;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}
</style>
```

### Step 3: Update Field Priority Manager Component
**File**: `frontend/src/components/FieldPriorityManager.vue` (assumed to exist)

**Before**:
```vue
<v-chip v-for="field in priority1Fields" :key="field">
  {{ field }}  <!-- Raw field path -->
</v-chip>
```

**After**:
```vue
<template>
  <div class="field-priority-manager">
    <h3>Priority 1 (Always Included)</h3>
    <draggable
      v-model="priority1Fields"
      group="fields"
      @change="handleDragChange"
      class="priority-zone"
    >
      <FieldChipWithTooltip
        v-for="field in priority1Fields"
        :key="field"
        :field="field"
        :priority="1"
      />
    </draggable>

    <h3>Priority 2 (High Priority)</h3>
    <draggable
      v-model="priority2Fields"
      group="fields"
      @change="handleDragChange"
      class="priority-zone"
    >
      <FieldChipWithTooltip
        v-for="field in priority2Fields"
        :key="field"
        :field="field"
        :priority="2"
      />
    </draggable>

    <h3>Priority 3 (Medium Priority)</h3>
    <draggable
      v-model="priority3Fields"
      group="fields"
      @change="handleDragChange"
      class="priority-zone"
    >
      <FieldChipWithTooltip
        v-for="field in priority3Fields"
        :key="field"
        :field="field"
        :priority="3"
      />
    </draggable>

    <h3>Unassigned (Excluded)</h3>
    <draggable
      v-model="unassignedFields"
      group="fields"
      @change="handleDragChange"
      class="priority-zone unassigned"
    >
      <FieldChipWithTooltip
        v-for="field in unassignedFields"
        :key="field"
        :field="field"
        :priority="null"
      />
    </draggable>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import draggable from 'vuedraggable';
import FieldChipWithTooltip from '@/components/FieldChipWithTooltip.vue';

// ... existing component logic ...
</script>
```

### Step 4: Add Unit Tests
**File**: `frontend/tests/unit/FieldPriorityLabels.spec.js` (NEW FILE)

**Add the 5 test suites defined in TDD Specifications section above**

### Step 5: Add Component Tests
**File**: `frontend/tests/components/FieldPriorityManager.spec.js` (NEW FILE)

**Add component integration tests from TDD Specifications**

---

## Files to Modify

### Frontend (5 files)
1. **`frontend/src/constants/fieldPriorityLabels.js`** (NEW FILE)
   - Add FIELD_LABELS mapping (15 fields)
   - Add FIELD_DESCRIPTIONS mapping (15 fields)
   - Add PRIORITY_LEVEL_DESCRIPTIONS (4 levels)
   - Add helper functions

2. **`frontend/src/components/FieldChipWithTooltip.vue`** (NEW FILE)
   - Create reusable chip component with tooltip
   - Implement accessibility features
   - Style with Vuetify theme

3. **`frontend/src/components/FieldPriorityManager.vue`** (UPDATE)
   - Replace raw field paths with FieldChipWithTooltip component
   - Ensure drag-and-drop still works

4. **`frontend/tests/unit/FieldPriorityLabels.spec.js`** (NEW FILE)
   - Add 3 test suites from TDD specifications

5. **`frontend/tests/components/FieldPriorityManager.spec.js`** (NEW FILE)
   - Add 2 component test suites from TDD specifications

---

## Design Mockup

### Field Chip with Tooltip (Desktop)
```
┌─────────────────────────────────────────────┐
│         Programming Languages                │  ← Chip (hoverable)
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │ Programming Languages                  │ │  ← Tooltip Header
│  │                                        │ │
│  │ Programming languages used in the      │ │  ← Description
│  │ project. Controls language-specific    │ │
│  │ context in agent missions.             │ │
│  │ ────────────────────────────────────── │ │
│  │ Priority 1: Full detail - Always      │ │  ← Priority Info
│  │ included regardless of token budget.   │ │
│  │ Critical for agent understanding.      │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Priority Zones Layout
```
┌──────────────────────────────────────────────┐
│ Priority 1 (Always Included)                 │
├──────────────────────────────────────────────┤
│ [Programming Languages] [Backend Stack]      │
│ [Frontend Stack] [Architecture Pattern]      │
│ [Core Features]                              │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ Priority 2 (High Priority)                   │
├──────────────────────────────────────────────┤
│ [Databases] [API Style] [Testing Strategy]   │
│ [Agent Templates] [Codebase Summary]         │
│ [Architecture Overview]                      │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ Priority 3 (Medium Priority)                 │
├──────────────────────────────────────────────┤
│ [Infrastructure] [Design Patterns]           │
│ [Architecture Notes] [Testing Frameworks]    │
│ [Coverage Target]                            │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ Unassigned (Excluded)                        │
├──────────────────────────────────────────────┤
│ (empty - drag fields here to exclude)        │
└──────────────────────────────────────────────┘
```

---

## Validation Checklist

- [ ] Unit tests pass: `npm run test:unit`
- [ ] Component tests pass: `npm run test:components`
- [ ] All 15 fields have human-readable labels
- [ ] All 15 fields have descriptive tooltips
- [ ] Tooltips appear on hover and focus (accessibility)
- [ ] Drag-and-drop still works with new chip component
- [ ] Visual design matches Vuetify theme
- [ ] Labels match backend FIELD_LABELS (mission_planner.py:90-104)
- [ ] No console errors or warnings
- [ ] Accessibility audit passes (axe-core)

---

## Dependencies

### External
- Vuetify 3.x (VTooltip component)
- vuedraggable (drag-and-drop functionality)

### Internal
- Handover 0307: Backend Default Field Priorities (defines complete field list)

---

## Notes

### Label Writing Guidelines

**Good Labels**:
- ✅ "Programming Languages" (clear, concise)
- ✅ "Backend Stack" (familiar terminology)
- ✅ "Testing Strategy" (descriptive)

**Bad Labels**:
- ❌ "Tech Stack Languages" (redundant)
- ❌ "config_data.test_config.strategy" (technical jargon)
- ❌ "Test Stuff" (vague)

### Description Writing Guidelines

**Good Descriptions**:
- Start with field's purpose ("Controls...", "Guides...", "Helps...")
- Explain agent impact ("Ensures agents use correct...")
- Keep under 150 characters
- Use active voice

**Bad Descriptions**:
- Generic ("This is a configuration field")
- Too technical ("Serialized JSONB column data")
- Too long (>150 characters)

### Priority Description Guidelines

**Purpose**: Help users understand token budget impact

**Structure**:
1. Detail level (full, summary, minimal)
2. Token impact (always included, conditional, dropped first)
3. Use case (critical for X, helpful for Y)

---

**Status**: Ready for execution
**Estimated Time**: 4-5 hours (constants: 1h, component: 2h, tests: 1.5h, integration: 30min)
**Agent Budget**: 90K tokens
**Next Handover**: 0309 (Token Estimation Improvements)
