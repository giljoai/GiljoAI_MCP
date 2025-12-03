# Handover 0319 - Context Management v3.0: Granular Field Selection

**⚠️ SUPERSEDED by Handover 0323 (2025-11-19)**

**IMPORTANT**: This handover was fully implemented on 2025-11-18 but then completely REVERSED the next day by Handover 0323, which chose a simplified approach over granular field selection based on user feedback.

**Original Date**: 2025-11-18
**Status**: ❌ SUPERSEDED - Implemented then deleted in favor of simplification
**Implementation**: Commit 4dda6171 (added 3,795 lines)
**Reversal**: Commit f12deeb7 (deleted all 3,795 lines)
**Reason**: User feedback: "This is confusing. I just want to toggle contexts on/off and set priority."

---

## Architectural Decision

This handover represents a path not taken. While technically sound, the granular field selection approach was deemed over-engineered compared to the simple toggle + priority approach implemented in 0323. The implementation was properly completed with TDD before being reversed, demonstrating good engineering discipline even in pivot decisions.

**Lesson**: Sometimes the best feature is the one you delete. Simplification won in this case.

---

## Original Summary

**Date**: 2025-11-18
**Status**: ~~READY FOR IMPLEMENTATION~~ SUPERSEDED
**Priority**: ~~HIGH~~ N/A
**Estimated Time**: ~~3-4 days~~ Actually took 1 day, then deleted in 1 day
**Dependencies**: Handovers 0312-0316 complete (v2.0 foundation)

---

## Executive Summary

Refactor context management from **dropdown-based depth controls** to **granular checkbox field selection**. This solves the core problem: users can't know what fields exist when they select a depth level.

**Key Changes**:
1. **Project Context** locked at top (always Priority 1, no controls)
2. **8 configurable badges** with granular field checkboxes
3. **New badge order** reflecting importance hierarchy
4. **Reorderable badges** via drag-and-drop

---

## Problem Statement

### Current Issue (v2.0)

```python
# User selects: architecture_depth = "overview"
# Returns only 2 fields:
{
    "primary_pattern": "Microservices",
    "api_style": "RESTful"
}
# User doesn't know security_considerations field even EXISTS!
```

### User Feedback

> "How do you know what fields you are missing?"

The v2.0 depth dropdown gives users **control** but not **visibility**. Users can exclude fields but don't know what they're excluding.

---

## Solution Architecture

### v3.0 Design: Granular Field Selection

Instead of abstract depth levels, users see **checkboxes for each field**:

```
┌─────────────────────────────────────────────────────────────┐
│ CONTEXT PRIORITY MANAGEMENT                                  │
├─────────────────────────────────────────────────────────────┤
│ 🔒 Project Context    [Always Priority 1] [Always Included] │  ← LOCKED
│                                                              │
│ 1. Product Core       [Priority ▼] [Enabled ☑]              │
│ 2. Vision Documents   [Priority ▼] [Depth: light ▼]         │
│ 3. Tech Stack         [Priority ▼] [☑☑☑☑] 4 fields         │  ← CHECKBOXES
│ 4. Architecture       [Priority ▼] [☑☑☐☐☑☐] 6 fields       │  ← CHECKBOXES
│ 5. Testing            [Priority ▼] [☑☐☑] 3 fields          │  ← CHECKBOXES
│ 6. Agent Templates    [Priority ▼] [type_only ▼]            │
│ 7. 360 Memory         [Priority ▼] [Count: 3 ▼]             │
│ 8. Git History        [Priority ▼] [Count: 15 ▼]            │
└─────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### 1. Project Context - PRIME DIRECTIVE

**Decision**: Project Context is ALWAYS included, ALWAYS Priority 1, NO user controls.

**Rationale**:
- This is literally what the orchestrator needs to do its job
- Contains project description (human intent) and mission (AI-generated plan)
- Without this, there's no project to orchestrate

**Implementation**:
- Remove from configurable badge list
- Display at top with "locked" visual indicator
- Backend always fetches regardless of user settings

### 2. Badge Order

**New order** (user can reorder via drag-and-drop):
1. Product Core
2. Vision Documents
3. Tech Stack
4. Architecture
5. Testing
6. Agent Templates
7. 360 Memory
8. Git History

### 3. Control Types by Badge

| Badge | Control Type | Options |
|-------|--------------|---------|
| Product Core | Toggle | Enabled/Disabled |
| Vision Documents | Dropdown | none/light/moderate/heavy |
| Tech Stack | Checkboxes | languages, frameworks, databases, dependencies |
| Architecture | Checkboxes | primary_pattern, api_style, design_patterns, architecture_notes, security_considerations, scalability_notes |
| Testing | Checkboxes | quality_standards, testing_strategy, testing_frameworks |
| Agent Templates | Dropdown | type_only (name + type), full (complete templates) |
| 360 Memory | Dropdown | 1/3/5/10 projects |
| Git History | Dropdown | 0/5/15/25 commits |

### 4. Default Field Selections

**All checkboxes checked by default** (2-A decision). Users see everything and can deselect what they don't need.

### 5. Field Discovery

**Show all possible fields** (1-B decision), even if empty for current product. Users learn what fields exist across all their products.

---

## Data Schema

### Current v2.0 Format

```python
{
    "product_core": {"priority": 1, "depth": "enabled"},
    "vision_documents": {"priority": 2, "depth": "light"},
    "tech_stack": {"priority": 2, "depth": "required"},
    "architecture": {"priority": 2, "depth": "overview"},
    "testing": {"priority": 3, "depth": "basic"},
    "agent_templates": {"priority": 2, "depth": "standard"},
    "360_memory": {"priority": 3, "depth": 3},
    "git_history": {"priority": 4, "depth": 25},
    "project_context": {"priority": 1, "depth": "enabled"}
}
```

### New v3.0 Format

```python
{
    "schema_version": "3.0",
    "order": ["product_core", "vision_documents", "tech_stack", "architecture", "testing", "agent_templates", "360_memory", "git_history"],
    "badges": {
        "product_core": {
            "priority": 1,
            "enabled": true
        },
        "vision_documents": {
            "priority": 2,
            "depth": "light"  # none/light/moderate/heavy
        },
        "tech_stack": {
            "priority": 2,
            "fields": {
                "languages": true,
                "frameworks": true,
                "databases": true,
                "dependencies": true
            }
        },
        "architecture": {
            "priority": 3,
            "fields": {
                "primary_pattern": true,
                "api_style": true,
                "design_patterns": true,
                "architecture_notes": true,
                "security_considerations": true,
                "scalability_notes": true
            }
        },
        "testing": {
            "priority": 3,
            "fields": {
                "quality_standards": true,
                "testing_strategy": true,
                "testing_frameworks": true
            }
        },
        "agent_templates": {
            "priority": 2,
            "depth": "type_only"  # type_only/full
        },
        "360_memory": {
            "priority": 3,
            "count": 3  # 1/3/5/10
        },
        "git_history": {
            "priority": 4,
            "count": 15  # 0/5/15/25
        }
    }
}
```

### Migration Strategy

```python
def migrate_v2_to_v3(old_config: dict) -> dict:
    """Migrate v2.0 context_priorities to v3.0 format."""

    new_config = {
        "schema_version": "3.0",
        "order": ["product_core", "vision_documents", "tech_stack",
                  "architecture", "testing", "agent_templates",
                  "360_memory", "git_history"],
        "badges": {}
    }

    # Map old depth values to new field selections
    depth_to_fields = {
        "tech_stack": {
            "required": {"languages": True, "frameworks": True, "databases": False, "dependencies": False},
            "all": {"languages": True, "frameworks": True, "databases": True, "dependencies": True}
        },
        "architecture": {
            "overview": {"primary_pattern": True, "api_style": True, ...},
            "detailed": {"primary_pattern": True, "api_style": True, "design_patterns": True, ...}
        },
        # ... similar for testing
    }

    # Migrate each badge
    for badge_key, old_value in old_config.items():
        if badge_key == "project_context":
            continue  # Skip - no longer configurable

        # ... migration logic

    return new_config
```

---

## Implementation Tasks

### Phase 1: Backend - Field Metadata & Extraction (Day 1-2)

#### Task 1.1: Define Field Metadata

**File**: `src/giljo_mcp/context/field_metadata.py` (NEW)

```python
FIELD_METADATA = {
    "tech_stack": {
        "fields": [
            {"key": "languages", "label": "Programming Languages", "tokens": 50},
            {"key": "frameworks", "label": "Frameworks", "tokens": 100},
            {"key": "databases", "label": "Databases", "tokens": 50},
            {"key": "dependencies", "label": "Dependencies", "tokens": 100}
        ]
    },
    "architecture": {
        "fields": [
            {"key": "primary_pattern", "label": "Primary Pattern", "tokens": 50},
            {"key": "api_style", "label": "API Style", "tokens": 50},
            {"key": "design_patterns", "label": "Design Patterns", "tokens": 150},
            {"key": "architecture_notes", "label": "Architecture Notes", "tokens": 500},
            {"key": "security_considerations", "label": "Security Considerations", "tokens": 300},
            {"key": "scalability_notes", "label": "Scalability Notes", "tokens": 200}
        ]
    },
    "testing": {
        "fields": [
            {"key": "quality_standards", "label": "Quality Standards", "tokens": 100},
            {"key": "testing_strategy", "label": "Testing Strategy", "tokens": 150},
            {"key": "testing_frameworks", "label": "Testing Frameworks", "tokens": 100}
        ]
    }
}
```

#### Task 1.2: Update Context Extraction

**Files to modify**:
- `src/giljo_mcp/tools/context_tools/fetch_tech_stack.py`
- `src/giljo_mcp/tools/context_tools/fetch_architecture.py`
- `src/giljo_mcp/tools/context_tools/fetch_testing_config.py`

**Change**: Add `selected_fields` parameter to filter output.

```python
async def fetch_tech_stack(
    tenant_key: str,
    product_id: str,
    selected_fields: Optional[List[str]] = None  # NEW
) -> dict:
    """Fetch tech stack context with optional field filtering."""

    result = await _get_full_tech_stack(tenant_key, product_id)

    if selected_fields:
        result = {k: v for k, v in result.items() if k in selected_fields}

    return result
```

#### Task 1.3: Schema Migration

**File**: `api/endpoints/user_settings.py`

**Change**: Add migration on settings retrieval.

```python
async def get_user_settings(user_id: str) -> dict:
    settings = await _fetch_from_db(user_id)

    # Migrate if needed
    if settings.get("context_priorities", {}).get("schema_version") != "3.0":
        settings["context_priorities"] = migrate_v2_to_v3(settings["context_priorities"])
        await _save_to_db(user_id, settings)

    return settings
```

#### Task 1.4: Update MCP Tools

**Files to modify**:
- All 9 context tools in `src/giljo_mcp/tools/context_tools/`

**Change**: Read user's field selections and pass to extraction functions.

---

### Phase 2: Frontend - Checkbox UI (Day 2-3)

#### Task 2.1: Create FieldCheckboxGroup Component

**File**: `frontend/src/components/settings/FieldCheckboxGroup.vue` (NEW)

```vue
<template>
  <div class="field-checkbox-group">
    <div class="field-row" v-for="field in fields" :key="field.key">
      <v-checkbox
        v-model="selectedFields[field.key]"
        :label="field.label"
        hide-details
        density="compact"
        @update:modelValue="emitChange"
      />
      <span class="token-estimate">~{{ field.tokens }} tokens</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  fields: Array,
  modelValue: Object
})

const emit = defineEmits(['update:modelValue'])

const selectedFields = ref({ ...props.modelValue })

const emitChange = () => {
  emit('update:modelValue', { ...selectedFields.value })
}
</script>
```

#### Task 2.2: Refactor DepthConfiguration.vue

**File**: `frontend/src/components/settings/DepthConfiguration.vue`

**Changes**:
1. Remove Project Context from list (it's locked)
2. Replace dropdown controls with FieldCheckboxGroup for tech_stack, architecture, testing
3. Keep dropdowns for vision_documents, agent_templates, 360_memory, git_history
4. Add drag-and-drop badge reordering

#### Task 2.3: Update Token Estimator

**File**: `frontend/src/services/depthTokenEstimator.ts`

**Change**: Calculate tokens based on selected fields, not depth level.

```typescript
export function estimateTokens(config: ContextConfig): number {
  let total = 0

  // Project Context always included (~200 tokens)
  total += 200

  // Tech Stack - sum selected fields
  if (config.badges.tech_stack) {
    const fields = config.badges.tech_stack.fields
    if (fields.languages) total += 50
    if (fields.frameworks) total += 100
    if (fields.databases) total += 50
    if (fields.dependencies) total += 100
  }

  // ... similar for other badges

  return total
}
```

#### Task 2.4: Update UserSettings.vue

**File**: `frontend/src/views/UserSettings.vue`

**Changes**:
1. Add locked Project Context visual at top of Context tab
2. Update badge order in template
3. Wire up new FieldCheckboxGroup components

---

### Phase 3: Integration Testing (Day 3-4)

#### Task 3.1: Unit Tests

**File**: `tests/unit/test_context_field_selection.py` (NEW)

```python
def test_tech_stack_filters_by_selected_fields():
    """Tech stack returns only selected fields."""
    result = await fetch_tech_stack(
        tenant_key="test",
        product_id="123",
        selected_fields=["languages", "frameworks"]
    )

    assert "languages" in result
    assert "frameworks" in result
    assert "databases" not in result
    assert "dependencies" not in result

def test_migration_v2_to_v3():
    """V2 config migrates correctly to V3 format."""
    old_config = {
        "tech_stack": {"priority": 2, "depth": "required"},
        "architecture": {"priority": 3, "depth": "overview"}
    }

    new_config = migrate_v2_to_v3(old_config)

    assert new_config["schema_version"] == "3.0"
    assert "fields" in new_config["badges"]["tech_stack"]
    assert new_config["badges"]["tech_stack"]["fields"]["languages"] == True

def test_project_context_always_fetched():
    """Project context is always included regardless of settings."""
    # Even if user somehow has project_context disabled, it should be fetched
    ...
```

#### Task 3.2: Integration Tests

**File**: `tests/integration/test_handover_0319_integration.py` (NEW)

```python
async def test_orchestrator_receives_filtered_context():
    """Orchestrator receives only selected fields in context."""
    # Setup: User has tech_stack.databases=False
    # Action: Launch orchestrator
    # Assert: Context does not include database info

async def test_token_estimation_matches_actual():
    """Frontend estimate matches actual tokens fetched."""
    # Setup: User selects specific fields
    # Action: Calculate estimate, then fetch actual
    # Assert: Estimate within 10% of actual

async def test_badge_reorder_persists():
    """Badge order saves and loads correctly."""
    # Setup: User reorders badges
    # Action: Save, reload
    # Assert: Order matches
```

---

## Files Summary

### New Files
- `src/giljo_mcp/context/field_metadata.py`
- `frontend/src/components/settings/FieldCheckboxGroup.vue`
- `tests/unit/test_context_field_selection.py`
- `tests/integration/test_handover_0319_integration.py`

### Modified Files
- `src/giljo_mcp/tools/context_tools/fetch_tech_stack.py`
- `src/giljo_mcp/tools/context_tools/fetch_architecture.py`
- `src/giljo_mcp/tools/context_tools/fetch_testing_config.py`
- `api/endpoints/user_settings.py`
- `frontend/src/components/settings/DepthConfiguration.vue`
- `frontend/src/views/UserSettings.vue`
- `frontend/src/services/depthTokenEstimator.ts`

---

## Success Criteria

- [ ] Project Context locked at top (not configurable)
- [ ] 8 badges with correct control types (checkboxes/dropdowns)
- [ ] All checkboxes default to checked
- [ ] Badge reordering via drag-and-drop
- [ ] Token estimates match actual fetch (~10% accuracy)
- [ ] V2 → V3 migration works automatically
- [ ] All 9 MCP tools respect field selections
- [ ] Tests passing (>80% coverage for new code)
- [ ] Frontend builds successfully

---

## Risk Assessment

**Risk Level**: LOW

**Mitigations**:
- Backup branch created (`Context_backup_branch_nov`)
- V2 → V3 migration is automatic and backward compatible
- Comprehensive test coverage
- Building on solid v2.0 foundation

---

## Execution Instructions

Execute with TDD discipline (Red → Green → Refactor):

1. **Phase 1**: Backend agent (TDD Implementor)
   - Write failing tests first
   - Implement field metadata and extraction
   - Update MCP tools

2. **Phase 2**: Frontend agent (TDD Implementor)
   - Write failing tests first
   - Create FieldCheckboxGroup component
   - Refactor DepthConfiguration

3. **Phase 3**: Integration agent (Backend Tester)
   - Full E2E workflow testing
   - Token estimation validation
   - Migration testing

---

## Related Documents

- [0316b_context_condensing_discussion_summary.md](./0316b_context_condensing_discussion_summary.md) - Original discussion
- [QUICK_LAUNCH.txt](./QUICK_LAUNCH.txt) - TDD discipline requirements
- [013A_code_review_architecture_status.md](./013A_code_review_architecture_status.md) - Existing patterns to reuse

---

*Created*: 2025-11-18
*Author*: Claude (orchestrator)
*Status*: Ready for implementation
