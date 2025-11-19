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
