# Quick Implementation Guide: Agent Info Buttons

**Document**: Implementation quick reference
**Status**: Ready for implementation
**Estimated Time**: 10-30 minutes (depending on scope)

---

## Overview

Current LaunchTab has info buttons (ℹ️) for Orchestrator and Agent Team cards. These buttons open AgentDetailsModal which displays:
- **Agent Templates**: From `/api/v1/templates/{template_id}/`
- **Orchestrator Prompt**: From `/api/v1/system/orchestrator-prompt`

---

## Current Implementation Details

### Components

```
LaunchTab.vue
├── Orchestrator Card
│   └── Info Icon (mdi-information, line 53)
│       └── Click → handleOrchestratorInfo() [line 331]
│
├── Agent Team Cards
│   └── Info Icon (mdi-information, line 80)
│       └── Click → handleAgentInfo(agent) [line 343]
│
└── AgentDetailsModal [line 91-94]
    ├── Detects: agent_type === 'orchestrator'?
    ├── If YES: Fetch from /api/v1/system/orchestrator-prompt
    └── If NO: Fetch from /api/v1/templates/{template_id}/
```

### File Paths

- **LaunchTab**: `frontend/src/components/projects/LaunchTab.vue`
- **Modal**: `frontend/src/components/projects/AgentDetailsModal.vue`
- **API**: `frontend/src/services/api.js`

---

## Implementation Options

### Option 1: Minimal (Lock → Eye Icons)

**File**: `frontend/src/components/projects/LaunchTab.vue`

**Change 1** (Line 44 - Orchestrator lock icon):
```vue
<!-- BEFORE -->
<v-icon size="small" class="lock-icon">mdi-lock</v-icon>

<!-- AFTER -->
<v-icon size="small" class="eye-icon">mdi-eye</v-icon>
```

**Change 2** (Line 71 - Agent team lock icon):
```vue
<!-- BEFORE -->
<v-icon size="small" class="lock-icon">mdi-lock</v-icon>

<!-- AFTER -->
<v-icon size="small" class="eye-icon">mdi-eye</v-icon>
```

**Change 3** (Lines 582-595 - Update CSS):
```scss
/* BEFORE */
.orchestrator-card {
  .lock-icon {
    color: $color-text-tertiary;
    flex-shrink: 0;
  }

  .info-icon {
    color: $color-text-tertiary;
    flex-shrink: 0;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
      color: $color-text-highlight;
    }
  }
}

/* AFTER */
.orchestrator-card {
  .eye-icon {
    color: $color-text-tertiary;
    flex-shrink: 0;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
      color: $color-text-highlight;
    }
  }

  .info-icon {
    color: $color-text-tertiary;
    flex-shrink: 0;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
      color: $color-text-highlight;
    }
  }
}
```

**Change 4** (Lines 664-680 - Update agent team CSS):
```scss
/* BEFORE */
.agent-slim-card {
  .lock-icon {
    color: $color-text-secondary;

    &:hover {
      color: $color-text-primary;
    }
  }

  .info-icon {
    color: $color-text-secondary;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
      color: $color-text-highlight;
    }
  }
}

/* AFTER */
.agent-slim-card {
  .eye-icon {
    color: $color-text-secondary;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
      color: $color-text-highlight;
    }
  }

  .info-icon {
    color: $color-text-secondary;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
      color: $color-text-highlight;
    }
  }
}
```

**Time**: ~10 minutes

---

### Option 2: Extended (With Edit Pencil Icon)

All changes from Option 1, plus:

**Change 5** (After Line 81 - Add edit icon for agents):
```vue
<!-- Inside .agent-slim-card, after info-icon -->
<v-icon
  size="small"
  class="edit-icon"
  role="button"
  tabindex="0"
  @click="handleAgentEdit(agent)"
  @keydown.enter="handleAgentEdit(agent)"
>
  mdi-pencil
</v-icon>
```

**Change 6** (Lines 672-690 - Add edit icon styling):
```scss
.agent-slim-card {
  .edit-icon {
    color: $color-text-secondary;
    cursor: pointer;
    transition: color 0.2s ease;
    flex-shrink: 0;

    &:hover {
      color: $color-text-highlight;
    }
  }
}
```

**Change 7** (After Line 349 - Add handler):
```javascript
/**
 * Handle Edit icon click for Agent Team members
 */
function handleAgentEdit(agent) {
  // TODO: Implement edit mission logic
  // For now, just show a placeholder
  console.log('[LaunchTab] Edit agent:', agent)

  // If implementing mission editing:
  // emit('edit-agent-mission', agent)
}
```

**Change 8** (Lines 141-145 - Update emits if needed):
```javascript
// If implementing edit functionality
const emit = defineEmits([
  'edit-description',
  'edit-mission',
  'edit-agent-mission',  // Already exists
  // 'edit-agent-modal' // Only add if new feature
])
```

**Time**: ~30 minutes

---

## Testing Checklist

After implementation, verify:

- [ ] Click info icon on Orchestrator → Modal opens with orchestrator prompt
- [ ] Click info icon on Agent → Modal opens with agent template
- [ ] Click close button → Modal closes
- [ ] Press Escape key → Modal closes
- [ ] Tab through icons → Icons get focus (outline visible)
- [ ] Press Enter on focused icon → Handler executes
- [ ] Hover on eye icon → Color changes
- [ ] Copy button in modal → Text copied to clipboard
- [ ] Error state → Error message displays properly
- [ ] Loading state → Spinner appears while loading
- [ ] Responsive → Works on mobile (375px), tablet (768px), desktop (1920px)
- [ ] Accessibility → Screen reader announces buttons correctly

---

## No-Brainer Checks

**Before** implementing icon changes:
1. ✅ Backup file: `git status`
2. ✅ Check for snapshot tests that might reference old icon names
3. ✅ Verify no other components reference `.lock-icon` class

**After** implementing:
1. ✅ Run `npm run lint` to check for style issues
2. ✅ Run tests: `npm run test` (if available)
3. ✅ Build check: `npm run build`
4. ✅ Visual test: Open in browser, test all interactions

---

## Icon Reference

| Icon Name | SVG | Use Case |
|-----------|-----|----------|
| `mdi-lock` | 🔒 | Locked/read-only (current) |
| `mdi-eye` | 👁️ | View/read template (proposed) |
| `mdi-information` | ℹ️ | Info/details (current) |
| `mdi-pencil` | ✎ | Edit/modify (optional) |

---

## API Endpoints

**For Agent Templates**:
```
GET /api/v1/templates/{template_id}/
Response: {
  description: string,
  model: string,
  variables: string[],
  tools: string[],
  template_content: string
}
```

**For Orchestrator Prompt**:
```
GET /api/v1/system/orchestrator-prompt
Response: {
  content: string,
  is_override: boolean
}
```

---

## Code Patterns

### Handler Pattern (for reuse)
```javascript
function handleOrchestratorInfo() {
  selectedAgent.value = {
    agent_type: 'orchestrator',
    agent_name: 'Orchestrator',
    id: 'orchestrator',
  }
  showDetailsModal.value = true
}
```

### Icon Styling Pattern (for consistency)
```scss
.icon-class {
  color: $color-text-secondary;
  cursor: pointer;
  transition: color 0.2s ease;
  flex-shrink: 0;

  &:hover {
    color: $color-text-highlight;
  }
}
```

---

## Common Issues & Solutions

**Issue**: Icon doesn't render
- **Solution**: Check icon name spelling (mdi-eye, not mdi-eyes)
- **Verify**: Vuetify icons are available (included in project)

**Issue**: Click handler not firing
- **Solution**: Check @click binding is correct
- **Verify**: Function is declared in script setup

**Issue**: Modal doesn't open
- **Solution**: Check v-model binding on modal
- **Verify**: showDetailsModal is reactive ref

**Issue**: Data doesn't load in modal
- **Solution**: Check API endpoint URL
- **Verify**: Template ID exists (for agents)
- **Check**: Orchestrator detected correctly (agent_type === 'orchestrator')

---

## Optional Enhancements

After basic implementation, consider:

1. **Copy Button**: Already implemented in modal - works out of box
2. **Edit Button**: Add pencil icon + handler (Option 2 above)
3. **Mission Export**: Export template to file
4. **Template Preview**: Show live preview before applying
5. **Diff View**: Show template changes/overrides
6. **Info in JobsTab**: Add info button to ActionIcons component

---

## Integration Points

**Modal can be reused in**:
- ActionIcons component (StatusBoard)
- JobsTab details view
- Agent management pages
- Settings for orchestrator prompt

**No changes needed to modal** - it auto-detects agent vs orchestrator

---

## Validation

Before committing changes:

```bash
# Syntax check
npm run lint frontend/src/components/projects/LaunchTab.vue

# Type check (if using TS)
npm run type-check

# Build validation
npm run build

# Test run
npm run test
```

---

## Success Criteria

✅ Icons display correctly
✅ Click handlers work
✅ Modal opens/closes properly
✅ Template data loads
✅ Error states handle gracefully
✅ Keyboard navigation functional
✅ No console errors
✅ Tests pass
✅ Build succeeds
✅ Responsive on all screen sizes

---

## When to Reach Out

Need clarification on:
- ❓ How template_id is populated
- ❓ What orchestrator prompt should display
- ❓ If edit functionality is needed
- ❓ Whether to modify ActionIcons
- ❓ Custom styling requirements

---

## Summary

**Minimal approach**: Update 2 icon names + CSS (10 min)
**Extended approach**: Add edit button + handler (30 min)
**Risk level**: LOW - cosmetic changes only
**Testing**: Visual + interaction testing
**Rollback**: Easy - revert file to previous version

---

End of Quick Implementation Guide
