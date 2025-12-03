# Handover 0323 - Context Management Simplification

**Date**: 2025-11-18
**Status**: READY FOR IMPLEMENTATION
**Priority**: HIGH
**Estimated Time**: 1-2 days
**Dependencies**: Handover 0319 complete

---

## Executive Summary

**Significant simplification** of the Context Management UI. Consolidate two separate sections into one clean "Context Priority Configuration" list. Remove all token estimation complexity.

---

## Problem Statement

The current Context tab has:
- Two separate sections (Field Priority Configuration + Depth Configuration)
- Complex token estimation logic that uses static values (not actual data)
- Field-level checkboxes that add unnecessary complexity
- Descriptions and token badges cluttering the UI

**User Feedback**: "This is confusing. I just want to toggle contexts on/off and set priority."

---

## Solution: One Clean List

### Target UI

```
┌─────────────────────────────────────────────────────────────┐
│ Context Priority Configuration                               │
├─────────────────────────────────────────────────────────────┤
│ 🔒 Project Context                          [Always High]    │
│                                                              │
│ Product Description   (●)                   [Priority ▼]     │
│ Vision Documents      (●)  [moderate ▼]     [Priority ▼]     │
│ Tech Stack            (●)                   [Priority ▼]     │
│ Architecture          (●)                   [Priority ▼]     │
│ Testing               (●)                   [Priority ▼]     │
│ Agent Templates       (●)  [type_only ▼]    [Priority ▼]     │
│ 360 Memory            (●)  [3 projects ▼]   [Priority ▼]     │
│ Git History           (●)  [15 commits ▼]   [Priority ▼]     │
└─────────────────────────────────────────────────────────────┘
```

### Control Definitions

| Control | Meaning |
|---------|---------|
| Toggle ON | Include this context when fetching |
| Toggle OFF | Never fetch (excluded) |
| Priority High | CRITICAL - always include first |
| Priority Medium | IMPORTANT - include if budget allows |
| Priority Low | NICE_TO_HAVE - include last |

### Contexts with Unique Dropdowns

| Context | Dropdown Options |
|---------|------------------|
| Vision Documents | none / light / moderate / heavy |
| Agent Templates | type_only / full |
| 360 Memory | 1 / 3 / 5 / 10 projects |
| Git History | 0 / 5 / 15 / 25 commits |

---

## What Gets Removed

### Frontend Files to DELETE

```
frontend/src/components/settings/FieldCheckboxGroup.vue
frontend/src/components/settings/DepthConfiguration.vue
frontend/src/services/depthTokenEstimator.ts
frontend/tests/unit/components/settings/FieldCheckboxGroup.spec.js
```

### Backend Files to DELETE

```
src/giljo_mcp/services/depth_token_estimator.py
src/giljo_mcp/context/field_metadata.py
src/giljo_mcp/context/__init__.py
```

### Logic to Remove

- All token estimation calculations
- Field-level selection (tech_stack_fields, architecture_fields, testing_fields)
- Token budget display
- Per-source token breakdowns

---

## What Remains

### Data Schema (Simplified)

```python
# User's context configuration
{
    "contexts": {
        "product_description": {"enabled": true, "priority": "high"},
        "vision_documents": {"enabled": true, "priority": "medium", "depth": "moderate"},
        "tech_stack": {"enabled": true, "priority": "medium"},
        "architecture": {"enabled": true, "priority": "medium"},
        "testing": {"enabled": true, "priority": "low"},
        "agent_templates": {"enabled": true, "priority": "medium", "depth": "type_only"},
        "memory_360": {"enabled": true, "priority": "low", "count": 3},
        "git_history": {"enabled": true, "priority": "low", "count": 15}
    }
}
```

### Priority Mapping

```python
PRIORITY_MAP = {
    "high": 1,      # CRITICAL
    "medium": 2,    # IMPORTANT
    "low": 3        # NICE_TO_HAVE
}
# Toggle OFF = priority 4 (EXCLUDED / never fetch)
```

---

## Implementation Tasks

### Phase 1: Frontend Simplification

#### Task 1.1: Create New Component

**File**: `frontend/src/components/settings/ContextPriorityConfig.vue`

Simple list component with:
- Project Context (locked at top)
- 8 context rows with toggle + optional dropdown + priority dropdown

```vue
<template>
  <v-card>
    <v-card-title>Context Priority Configuration</v-card-title>
    <v-card-text>
      <!-- Locked Project Context -->
      <div class="context-row">
        <v-icon>mdi-lock</v-icon>
        <span>Project Context</span>
        <v-chip>Always High</v-chip>
      </div>

      <!-- Configurable Contexts -->
      <div v-for="ctx in contexts" :key="ctx.key" class="context-row">
        <span>{{ ctx.label }}</span>
        <v-switch v-model="config[ctx.key].enabled" />
        <v-select v-if="ctx.options" v-model="config[ctx.key].depth" :items="ctx.options" />
        <v-select v-model="config[ctx.key].priority" :items="priorityOptions" />
      </div>
    </v-card-text>
  </v-card>
</template>
```

#### Task 1.2: Update UserSettings.vue

- Remove import of DepthConfiguration
- Remove import of old priority components
- Replace with single ContextPriorityConfig component
- Update Context tab to show only this one section

#### Task 1.3: Delete Old Files

```bash
rm frontend/src/components/settings/FieldCheckboxGroup.vue
rm frontend/src/components/settings/DepthConfiguration.vue
rm frontend/src/services/depthTokenEstimator.ts
rm frontend/tests/unit/components/settings/FieldCheckboxGroup.spec.js
```

---

### Phase 2: Backend Cleanup

#### Task 2.1: Simplify API Response

**File**: `api/endpoints/users.py`

Remove token estimation from responses:

```python
# Before
return {
    "depth_config": config,
    "token_estimate": {...}  # REMOVE
}

# After
return {
    "context_config": config
}
```

#### Task 2.2: Update Context Tools

The 9 MCP context tools should:
- Check if context is enabled (toggle)
- Respect priority ordering
- Use depth/count values where applicable
- Remove field-level filtering (fetch full content)

#### Task 2.3: Delete Unused Files

```bash
rm src/giljo_mcp/services/depth_token_estimator.py
rm -r src/giljo_mcp/context/
```

---

### Phase 3: Test Updates

#### Task 3.1: Remove Token Tests

Delete or update tests that test token estimation:
- `tests/unit/test_context_field_selection.py` - DELETE (no longer needed)
- `tests/integration/test_handover_0319_integration.py` - UPDATE (remove token tests)

#### Task 3.2: Add New Tests

Create tests for simplified config:
- Toggle enables/disables context fetch
- Priority affects ordering
- Depth/count values respected

---

## Migration Strategy

### Existing User Settings

```python
def migrate_to_simplified(old_config: dict) -> dict:
    """Migrate v3.0 field-based config to simplified toggle+priority."""

    new_config = {"contexts": {}}

    for badge_key, old_value in old_config.get("badges", {}).items():
        # Map old priority numbers to new strings
        priority_num = old_value.get("priority", 2)
        priority_str = "high" if priority_num == 1 else "medium" if priority_num == 2 else "low"

        # Check if any fields were enabled (if not, toggle off)
        enabled = True
        if "fields" in old_value:
            enabled = any(old_value["fields"].values())
        elif "enabled" in old_value:
            enabled = old_value["enabled"]

        new_config["contexts"][badge_key] = {
            "enabled": enabled,
            "priority": priority_str
        }

        # Copy depth/count if present
        if "depth" in old_value:
            new_config["contexts"][badge_key]["depth"] = old_value["depth"]
        if "count" in old_value:
            new_config["contexts"][badge_key]["count"] = old_value["count"]

    return new_config
```

---

## Files Summary

### Delete (Clean Removal)

| File | Reason |
|------|--------|
| `FieldCheckboxGroup.vue` | Field-level selection removed |
| `DepthConfiguration.vue` | Replaced by ContextPriorityConfig |
| `depthTokenEstimator.ts` | Token estimation removed |
| `depth_token_estimator.py` | Token estimation removed |
| `field_metadata.py` | Field metadata no longer needed |
| `test_context_field_selection.py` | Tests obsolete functionality |

### Create

| File | Purpose |
|------|---------|
| `ContextPriorityConfig.vue` | New simplified config component |

### Modify

| File | Changes |
|------|---------|
| `UserSettings.vue` | Use new component, remove old sections |
| `api/endpoints/users.py` | Remove token responses, simplify schema |
| Context tools | Remove field filtering, respect toggle/priority |

---

## Success Criteria

- [ ] Single "Context Priority Configuration" section in UI
- [ ] No token estimates anywhere
- [ ] Clean toggle + priority + optional dropdown for each context
- [ ] Project Context locked at top
- [ ] Product Description (renamed from Product Core)
- [ ] Existing user settings migrated
- [ ] All tests passing
- [ ] Frontend builds successfully

---

## Code Quality (per 013A)

- **Delete unused code** - Don't comment out, delete completely
- **TDD** - Write tests for new component before implementation
- **Reuse patterns** - Follow existing Vue/Vuetify patterns
- **Clean code** - No TODOs, no zombie code

---

## Risk Assessment

**Risk Level**: LOW

**Mitigations**:
- Removing complexity, not adding
- Migration preserves user intent
- Backup branch exists (`Context_backup_branch_nov`)

---

*Created*: 2025-11-18
*Author*: Claude (orchestrator)
*Status*: Ready for implementation

---

## Implementation Summary

**Date Completed**: 2025-11-19
**Status**: ✅ Completed
**Agent**: Claude Code (TDD workflow)

### What Was Built

**New Component Created**:
- `ContextPriorityConfig.vue` (318 lines) - Single clean component replacing two complex sections
  - Locked Project Context row (always high priority)
  - 8 configurable context rows (toggle + depth dropdown + priority dropdown)
  - Auto-save on change
  - No token estimation complexity

### Results

| Metric | Before | After | Achievement |
|--------|--------|-------|-------------|
| **UserSettings.vue** | 1,410 lines | **826 lines** | 41% reduction ✅ |
| **Context Components** | 2 components (DepthConfiguration + FieldCheckboxGroup) | **1 component** (ContextPriorityConfig) | Simplified ✅ |
| **Backend Files Deleted** | - | 2,134 lines removed | Massive cleanup ✅ |
| **Frontend Files Deleted** | - | 1,661 lines removed | Simplified architecture ✅ |

### Files Deleted (Clean Removal)

**Backend** (2,134 lines removed):
- `src/giljo_mcp/services/depth_token_estimator.py` - Token estimation logic removed
- `src/giljo_mcp/context/field_metadata.py` - Field metadata no longer needed
- `src/giljo_mcp/context/__init__.py` - Entire context directory removed
- `tests/api/test_depth_controls.py` - Obsolete depth control tests
- `tests/integration/test_handover_0319_integration.py` - 839 lines of token tests
- `tests/unit/test_context_field_selection.py` - 603 lines of field selection tests

**Frontend** (1,661 lines removed):
- `frontend/src/components/settings/DepthConfiguration.vue` (466 lines)
- `frontend/src/components/settings/FieldCheckboxGroup.vue` (155 lines)
- `frontend/src/services/depthTokenEstimator.ts` (287 lines)
- `frontend/tests/unit/components/settings/FieldCheckboxGroup.spec.js` (172 lines)
- Removed from UserSettings.vue: drag-and-drop logic, token estimation state, complex watchers (581 lines cleaned up)

### Key Files Modified

**Backend**:
- `api/endpoints/users.py` - Removed token_estimate from responses, simplified schema
- `src/giljo_mcp/tools/context_tools/get_tech_stack.py` - Removed selected_fields parameter
- `src/giljo_mcp/tools/context_tools/get_architecture.py` - Removed field filtering
- `src/giljo_mcp/tools/context_tools/get_testing.py` - Removed field filtering

**Frontend**:
- `frontend/src/views/UserSettings.vue` - Replaced complex sections with single ContextPriorityConfig
- `frontend/src/components/settings/ContextPriorityConfig.vue` - New simplified component

### Git Commits (Related to 0323)

Core implementation commits:
- `2d11389` - test: Add tests for ContextPriorityConfig component (TDD RED phase)
- `abef575` - feat: Implement simplified Context Priority Configuration UI
- `f12deeb` - refactor: Remove token estimation and simplify backend for context management
- `d2b9765` - docs: Add Handover 0323 - Context Management Simplification

Follow-up improvements:
- `2356969` - style(ui): Compact context management UI with horizontal toggles
- `49f89a2` - fix(ui): Auto-save context settings on change

### What Was Simplified

**Removed Complexity**:
- ❌ Two separate UI sections → One clean list
- ❌ Token estimation logic (frontend + backend)
- ❌ Field-level checkboxes (tech_stack_fields, architecture_fields, testing_fields)
- ❌ Token budget display and per-source breakdown
- ❌ Complex drag-and-drop priority ordering
- ❌ Static token estimation metadata

**What Remains (Clean)**:
- ✅ Simple toggle: ON = include, OFF = excluded
- ✅ Priority dropdown: High / Medium / Low
- ✅ Depth dropdowns where applicable (Vision, Templates, 360 Memory, Git History)
- ✅ Auto-save functionality
- ✅ Clean data schema: `{enabled, priority, depth?, count?}`

### Testing

**Tests Created**:
- `frontend/tests/unit/components/settings/ContextPriorityConfig.spec.js` - Comprehensive tests for new component

**Tests Deleted** (obsolete functionality):
- 603 lines of field selection tests
- 839 lines of token estimation integration tests
- 97 lines of depth control API tests
- 172 lines of FieldCheckboxGroup tests

**Build Status**: ✅ All tests passing, frontend builds successfully

### User Impact

**Before**: "This is confusing. I just want to toggle contexts on/off and set priority."

**After**: Single clean list with toggle + priority + optional depth. No token estimation clutter.

### Installation Impact

None - frontend/backend refactor only. No database changes, no new dependencies.

### Code Quality Achievement

Per handover 013A standards:
- ✅ **Delete unused code** - 3,795 lines completely removed (not commented out)
- ✅ **TDD workflow** - Tests written first, then implementation
- ✅ **Reuse patterns** - Followed existing Vue/Vuetify patterns
- ✅ **Clean code** - No TODOs, no zombie code, no commented blocks

### Lessons Learned

- Removing complexity is often more valuable than adding features
- Token estimation added cognitive load without providing real value (static estimates)
- Field-level granularity was over-engineering - users want simple toggle + priority
- Deleting 3,795 lines felt better than writing 3,795 new lines
- Simplification revealed that two separate sections were solving the same problem
