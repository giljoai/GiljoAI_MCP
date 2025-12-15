# Handover 0350c: Frontend 3-Tier UI + Field Rename

**Date**: 2025-12-15
**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 6-7 hours (1 full day)
**Series**: 0350 (Context Management On-Demand Architecture)
**Integrates**: Former Handover 0349 (field rename project_context → project_description)

## Objective

**Two combined goals:**

1. **3-Tier UI Labels**: Simplify priority system from numeric (1, 2, 3, 4) to descriptive (CRITICAL / IMPORTANT / REFERENCE / OFF)
2. **Field Rename**: Rename `project_context` → `project_description` everywhere for consistency with MCP output

## Why Combined?

Both changes touch `ContextPriorityConfig.vue` - doing them together avoids touching the same file twice.

## Current State (4-Tier Numeric)

**Frontend UI** (`ContextPriorityConfig.vue`):
- Priority options: `1`, `2`, `3` (unlabeled dropdown)
- User sees numeric values without semantic meaning
- No clear indication of what each priority level means

**Backend** (`defaults.py`):
- Priority 1 = CRITICAL (always fetch, highest priority)
- Priority 2 = IMPORTANT (fetch if budget allows)
- Priority 3 = NICE_TO_HAVE (fetch if budget remaining)
- Priority 4 = EXCLUDED (never fetch, toggle OFF)

**Mission Planner** (`mission_planner.py`):
- Priority 1: "**CRITICAL: {section_name}** (Priority 1) - REQUIRED FOR ALL OPERATIONS"
- Priority 2: "**IMPORTANT: {section_name}** (Priority 2) - High priority context"
- Priority 3: "**{section_name}** (Priority 3 - REFERENCE) - Supplemental information"
- Priority 4: Excluded entirely (0 bytes)

## Target State (3-Tier + OFF Descriptive)

**Frontend UI Changes**:
```javascript
const priorityOptions = [
  {
    value: 1,
    title: 'CRITICAL',
    subtitle: 'Orchestrator MUST call this MCP tool'
  },
  {
    value: 2,
    title: 'IMPORTANT',
    subtitle: 'Orchestrator SHOULD call this tool if budget allows'
  },
  {
    value: 3,
    title: 'REFERENCE',
    subtitle: 'Orchestrator MAY call if project scope requires'
  },
  {
    value: 4,
    title: 'OFF',
    subtitle: 'Tool not mentioned in orchestrator instructions'
  }
]
```

**Backend Defaults** (updated with new semantic meanings):
```python
DEFAULT_FIELD_PRIORITIES = {
    "product_core": 1,        # CRITICAL - Product name, description, core features
    "project_context": 1,     # CRITICAL - Current project metadata (locked)
    "memory_360": 1,          # CRITICAL - Cumulative project history
    "tech_stack": 2,          # IMPORTANT - Tech stack configuration
    "git_history": 2,         # IMPORTANT - Recent commits (if GitHub enabled)
    "vision_documents": 3,    # REFERENCE - Vision document chunks
    "architecture": 3,        # REFERENCE - Architecture patterns
    "agent_templates": 3,     # REFERENCE - Agent template library
    "testing": 3,             # REFERENCE - Quality standards
}
```

## Rationale

### User Comprehension Problem

**Current UI**: User sees "Priority 1, 2, 3" with no labels
- Unclear if higher number = higher priority (3 > 1?)
- No indication of what each priority level means
- Requires reading documentation to understand

**New UI**: User sees "CRITICAL / IMPORTANT / REFERENCE / OFF" with descriptions
- Self-documenting: Clear semantic meaning
- Matches orchestrator instruction framing
- No external documentation needed

### Alignment with Orchestrator Framing

The new labels match the framing language used in `mission_planner.py`:

| Priority | UI Label | Mission Planner Framing | MCP Tool Framing |
|----------|----------|-------------------------|------------------|
| 1 | CRITICAL | "REQUIRED FOR ALL OPERATIONS" | "Orchestrator MUST call" |
| 2 | IMPORTANT | "High priority context" | "Orchestrator SHOULD call" |
| 3 | REFERENCE | "Supplemental information" | "Orchestrator MAY call" |
| 4 | OFF | (excluded entirely) | "Not mentioned" |

## Implementation Plan

### Phase 1: Frontend UI Update

**File**: `frontend/src/components/settings/ContextPriorityConfig.vue`

#### 1.1: Update Priority Options (Lines 236-240)

**Current**:
```javascript
const priorityOptions = [
  { title: 'Critical', value: 1 },
  { title: 'Important', value: 2 },
  { title: 'Reference', value: 3 },
]
```

**Replace with**:
```javascript
const priorityOptions = [
  {
    value: 1,
    title: 'CRITICAL',
    subtitle: 'Orchestrator MUST call this MCP tool',
    color: 'red-darken-2'
  },
  {
    value: 2,
    title: 'IMPORTANT',
    subtitle: 'Orchestrator SHOULD call if budget allows',
    color: 'orange-darken-2'
  },
  {
    value: 3,
    title: 'REFERENCE',
    subtitle: 'Orchestrator MAY call if project scope requires',
    color: 'blue-darken-2'
  },
  {
    value: 4,
    title: 'OFF',
    subtitle: 'Tool not mentioned in orchestrator instructions',
    color: 'grey'
  }
]
```

#### 1.2: Update v-select to Show Subtitles

**Current v-select** (Lines 67-78, 141-152):
```vue
<v-select
  :model-value="config[context.key]?.priority"
  @update:model-value="updatePriority(context.key, $event)"
  :items="priorityOptions"
  density="compact"
  variant="outlined"
  hide-details
  :aria-label="`${context.label} priority setting`"
  :data-testid="`priority-${context.key.replace('_', '-')}`"
  class="priority-select"
  :disabled="!config[context.key]?.enabled"
/>
```

**Replace with** (add item-title, item-value, item-subtitle props):
```vue
<v-select
  :model-value="config[context.key]?.priority"
  @update:model-value="updatePriority(context.key, $event)"
  :items="priorityOptions"
  item-title="title"
  item-value="value"
  item-subtitle="subtitle"
  density="compact"
  variant="outlined"
  hide-details
  :aria-label="`${context.label} priority setting`"
  :data-testid="`priority-${context.key.replace('_', '-')}`"
  class="priority-select"
  :disabled="!config[context.key]?.enabled"
/>
```

**Note**: Apply this change to BOTH v-select instances (priority-only contexts at line 67, depth-controlled contexts at line 141).

#### 1.3: Update Priority Toggle Logic (Lines 277-291)

**Current**:
```javascript
function toggleContext(key: string) {
  const newEnabled = !config.value[key].enabled
  config.value[key].enabled = newEnabled

  // If enabling from EXCLUDED, set to Reference (priority 3)
  if (newEnabled && config.value[key].priority === 4) {
    config.value[key].priority = 3  // Reference (NICE_TO_HAVE)
  }
  // If disabling, set to EXCLUDED (priority 4)
  else if (!newEnabled) {
    config.value[key].priority = 4
  }

  saveConfig() // Auto-save
}
```

**No change needed** - Logic already handles priority 4 (OFF) correctly:
- Enabling from OFF → Sets to priority 3 (REFERENCE)
- Disabling → Sets to priority 4 (OFF)

#### 1.4: Update Locked Project Context Chip (Line 34)

**Current**:
```vue
<v-chip size="small" color="primary" variant="flat"> Always Critical </v-chip>
```

**Replace with**:
```vue
<v-chip size="small" color="red-darken-2" variant="flat">
  CRITICAL (Locked)
</v-chip>
```

**Note**: This locked chip indicates that Project Description is NOT user-configurable. It must remain at Priority 1 (CRITICAL) at all times because the orchestrator needs to know the current project context before fetching any other context fields.

#### 1.5: Update Styles for Wider Priority Select (Lines 621-634)

**Current**:
```css
.priority-select {
  max-width: 100px;
  min-width: 90px;
}
```

**Replace with** (wider to accommodate longer labels):
```css
.priority-select {
  max-width: 140px;
  min-width: 120px;
}

.priority-select :deep(.v-select__selection-text) {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}
```

### Phase 2: Backend Defaults Update

**File**: `src/giljo_mcp/config/defaults.py`

#### 2.1: Update DEFAULT_FIELD_PRIORITIES (Lines 75-93)

**Current**:
```python
DEFAULT_FIELD_PRIORITY: Dict[str, Any] = {
    "version": "2.0",
    "priorities": {
        # Priority 1 (CRITICAL): Always fetch, highest priority
        # Core technical foundation and active agent configurations
        "product_core": 1,  # description, tech_stack (languages, backend, frontend, database, infrastructure)
        "agent_templates": 1,  # Active agent behavior configurations
        # Priority 2 (IMPORTANT): Fetch if budget allows
        # Product vision and current project context
        "vision_documents": 2,  # Chunked vision document uploads
        "project_context": 2,  # project description, user notes, architecture notes
        # Priority 3 (NICE_TO_HAVE): Fetch if budget remaining
        # Cumulative project history
        "memory_360": 3,  # Sequential project history, outcomes, decisions
        # Priority 4 (EXCLUDED): Never fetch by default
        # Recent commit history (optional, can be enabled per user)
        "git_history": 4,  # Recent commits from git integration
    },
}
```

**Replace with**:
```python
DEFAULT_FIELD_PRIORITY: Dict[str, Any] = {
    "version": "2.0",
    "priorities": {
        # Priority 1 (CRITICAL): Orchestrator MUST call these MCP tools
        # These tools are mentioned with mandatory framing in instructions
        "product_core": 1,        # Product name, description, core features
        "project_context": 1,     # Current project metadata (locked - always CRITICAL)
        "memory_360": 1,          # Cumulative project history (sequential closeouts)

        # Priority 2 (IMPORTANT): Orchestrator SHOULD call if budget allows
        # These tools are mentioned with strong recommendation in instructions
        "tech_stack": 2,          # Tech stack configuration (languages, frameworks, databases)
        "git_history": 2,         # Recent commits from git integration (if enabled)

        # Priority 3 (REFERENCE): Orchestrator MAY call if project scope requires
        # These tools are mentioned as optional supplemental context
        "vision_documents": 3,    # Chunked vision document uploads (paginated)
        "architecture": 3,        # Architecture patterns, API style, design patterns
        "agent_templates": 3,     # Agent template library (for task assignment)
        "testing": 3,             # Quality standards, testing strategy, frameworks
    },
}
```

**Key Changes**:
- Updated comments to match new UI framing (MUST / SHOULD / MAY)
- Reorganized fields by new priority tiers:
  - **CRITICAL (1)**: product_core, project_context, memory_360
  - **IMPORTANT (2)**: tech_stack, git_history
  - **REFERENCE (3)**: vision_documents, architecture, agent_templates, testing
- Added explicit comment for project_context (locked field)
- Changed git_history from priority 4 (OFF) to priority 2 (IMPORTANT) - reflects importance when GitHub integration is enabled

#### 2.2: Update Module Docstring (Lines 1-70)

**Update lines 13-36** to reflect new tier meanings:

```python
Priority Tiers (v2.0):
    Priority 1 (CRITICAL - Orchestrator MUST call):
        - product_core: Product name, description, core features
        - project_context: Current project metadata (locked field)
        - memory_360: Cumulative project history (sequential closeouts)

        These MCP tools are mentioned with MANDATORY framing in orchestrator
        instructions. Orchestrator is expected to call these tools every time.

    Priority 2 (IMPORTANT - Orchestrator SHOULD call):
        - tech_stack: Tech stack configuration (languages, frameworks, databases)
        - git_history: Recent commits from git integration (if enabled)

        These MCP tools are mentioned with STRONG RECOMMENDATION in orchestrator
        instructions. Orchestrator should call unless budget is constrained.

    Priority 3 (REFERENCE - Orchestrator MAY call):
        - vision_documents: Chunked vision document uploads (paginated)
        - architecture: Architecture patterns, API style, design patterns
        - agent_templates: Agent template library (for task assignment)
        - testing: Quality standards, testing strategy, frameworks

        These MCP tools are mentioned as OPTIONAL SUPPLEMENTAL context in
        orchestrator instructions. Orchestrator calls if project scope requires.

    Priority 4 (OFF - Not mentioned):
        No default fields set to OFF. Users can toggle any field to OFF via UI.

        These MCP tools are NOT MENTIONED in orchestrator instructions. They
        are excluded entirely from context assembly.
```

### Phase 3: Documentation Updates

#### 3.1: Update User Guide

**File**: `docs/user_guides/context_configuration.md` (if exists)

Add section explaining new priority system:

```markdown
## Priority Tiers Explained

GiljoAI uses a 3-tier priority system plus OFF to control which MCP tools
the orchestrator calls during project staging:

### CRITICAL (Priority 1) - MUST CALL
**Framing**: "Orchestrator MUST call this MCP tool"

The orchestrator is instructed with mandatory framing to call these tools
every time. These provide essential context for all operations.

**Default CRITICAL fields**:
- Product Core (product name, description, features)
- Project Context (current project metadata) - **locked**
- 360 Memory (cumulative project history)

### IMPORTANT (Priority 2) - SHOULD CALL
**Framing**: "Orchestrator SHOULD call if budget allows"

The orchestrator is strongly recommended to call these tools unless token
budget is severely constrained. These provide critical product context.

**Default IMPORTANT fields**:
- Tech Stack (languages, frameworks, databases)
- Git History (recent commits - if GitHub integration enabled)

### REFERENCE (Priority 3) - MAY CALL
**Framing**: "Orchestrator MAY call if project scope requires"

The orchestrator is informed these tools are available as optional
supplemental context. Called only if project scope requires.

**Default REFERENCE fields**:
- Vision Documents (product vision, features, roadmap)
- Architecture (architecture patterns, API style)
- Agent Templates (agent behavior configurations)
- Testing (quality standards, testing strategy)

### OFF (Priority 4) - NOT MENTIONED
**Framing**: "Tool not mentioned in orchestrator instructions"

These MCP tools are excluded entirely from orchestrator instructions.
Use this to completely hide a context field.

## Changing Priority Levels

Navigate to **My Settings → Context → Field Priority Configuration**:

1. Each context field shows a toggle switch and priority dropdown
2. Toggle OFF → Field set to priority 4 (excluded)
3. Toggle ON → Field set to priority 3 (REFERENCE) by default
4. Change dropdown to upgrade to IMPORTANT (2) or CRITICAL (1)
5. Changes save automatically

**Note**: Project Context is locked to CRITICAL and cannot be changed.
```

#### 3.2: Update CLAUDE.md

**File**: `CLAUDE.md` (Lines 38-67)

Update the Context Management section to reflect new tier names:

```markdown
**Priority Dimension** (WHAT to fetch):
- Priority 1 (CRITICAL) - Orchestrator MUST call (mandatory)
- Priority 2 (IMPORTANT) - Orchestrator SHOULD call (recommended)
- Priority 3 (REFERENCE) - Orchestrator MAY call (optional)
- Priority 4 (OFF) - Not mentioned (excluded)
```

### Phase 4: Testing

#### 4.1: Visual Testing

**Test Plan**:
1. Navigate to My Settings → Context → Field Priority Configuration
2. Verify priority dropdowns show 4 options:
   - CRITICAL (with subtitle)
   - IMPORTANT (with subtitle)
   - REFERENCE (with subtitle)
   - OFF (with subtitle)
3. Verify Project Context shows "CRITICAL (Locked)" chip
4. Verify dropdowns are wide enough to show full labels (140px)
5. Test toggle OFF → dropdown should show OFF
6. Test toggle ON from OFF → dropdown should show REFERENCE
7. Change priority from REFERENCE → IMPORTANT → CRITICAL
8. Verify changes persist after page refresh

#### 4.2: API Testing

**Test API roundtrip**:
```bash
# 1. Fetch current priorities
curl -X GET http://localhost:7272/api/v1/users/me/field-priority \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. Update priority for vision_documents to CRITICAL (1)
curl -X PUT http://localhost:7272/api/v1/users/me/field-priority \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "2.0",
    "priorities": {
      "product_core": 1,
      "project_context": 1,
      "memory_360": 1,
      "tech_stack": 2,
      "git_history": 2,
      "vision_documents": 1,
      "architecture": 3,
      "agent_templates": 3,
      "testing": 3
    }
  }'

# 3. Verify update persisted
curl -X GET http://localhost:7272/api/v1/users/me/field-priority \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected**: `vision_documents` priority changes from 3 → 1

#### 4.3: Integration Testing

**Test orchestrator instruction generation**:

1. Create new project with updated priorities
2. Launch orchestrator
3. Verify get_orchestrator_instructions() returns correct framing:
   - Priority 1 fields: "**CRITICAL: {field}** (Priority 1) - REQUIRED FOR ALL OPERATIONS"
   - Priority 2 fields: "**IMPORTANT: {field}** (Priority 2) - High priority context"
   - Priority 3 fields: "**{field}** (Priority 3 - REFERENCE) - Supplemental information"
   - Priority 4 fields: Excluded entirely (not present)

#### 4.4: Regression Testing

**Run existing tests**:
```bash
# Priority configuration tests
pytest tests/unit/test_priority_framing.py -v
pytest tests/unit/test_field_key_mismatches.py -v
pytest tests/integration/test_orchestrator_priority_filtering.py -v
pytest tests/integration/test_orchestrator_field_priorities.py -v

# Context configuration tests
pytest tests/unit/test_depth_configuration.py -v
pytest tests/integration/test_context_filtering_by_priority.py -v
```

**Expected**: All tests pass without modification (backend values unchanged, only UI labels changed)

## Files Modified

### Part A: 3-Tier UI Labels

#### Frontend Changes
1. **frontend/src/components/settings/ContextPriorityConfig.vue**
   - Lines 236-240: Update priorityOptions array (add 4th option + subtitles)
   - Lines 67-78, 141-152: Update v-select components (add item-title, item-value, item-subtitle)
   - Line 34: Update locked chip label ("Always Critical" → "CRITICAL (Locked)")
   - Lines 621-634: Update .priority-select styles (90px → 120px min-width)

#### Backend Changes
2. **src/giljo_mcp/config/defaults.py**
   - Lines 75-93: Update DEFAULT_FIELD_PRIORITIES (new priorities + comments)
   - Lines 13-36: Update module docstring (Priority Tiers section)
   - Lines 96-113: Update get_categories_by_priority() docstring (if needed)

#### Documentation Changes
3. **docs/user_guides/context_configuration.md** (if exists)
   - Add "Priority Tiers Explained" section
   - Add "Changing Priority Levels" section

4. **CLAUDE.md**
   - Lines 38-67: Update Context Management section (Priority Dimension)

### Part B: Field Rename (project_context → project_description)

#### Backend Changes
5. **src/giljo_mcp/tools/orchestration.py**
   - Line ~111: Rename field key `project_context` → `project_description`

6. **api/endpoints/users.py**
   - Lines ~140, 165, 173, 717, 768: Update docstrings and `valid_categories` set
   - Add backward compatibility migration function

7. **src/giljo_mcp/config/defaults.py** (COMBINED with #2 above)
   - Line ~85: Rename field key `project_context` → `project_description`

#### Frontend Changes
8. **frontend/src/components/settings/ContextPriorityConfig.vue** (COMBINED with #1 above)
   - Update label: "Project Context" → "Project Description"
   - Update field key references throughout component

#### Test File Changes (10 files)
9. **tests/api/endpoints/test_users_new_categories.py** (line ~78)
10. **tests/api/endpoints/test_users_category_validation.py** (lines ~8, 34)
11. **tests/api/test_priority_system.py** (multiple lines: 44, 98, 114, 144, 244, 290, 317, 356, 475)
12. **tests/unit/test_priority_framing.py** (lines ~79, 372)
13. **tests/unit/test_new_context_tools.py** (lines ~132, 162, 170)
14. **tests/unit/test_framing_helpers_validation.py** (lines ~69, 117)
15. **tests/unit/test_field_key_mismatches.py** (line ~471)
16. **tests/performance/test_token_reduction_in_real_prompts.py** (line ~206)
17. **tests/unit/test_mission_planner_vision_overview.py** (lines ~277, 312)
18. **handovers/context_test/run_context_tests.py** (lines ~54, 351, 384, 404)

#### Documentation Changes
19. **AGENTS.md** (line ~70)
20. **PHASE5_SUMMARY.md** (lines ~33, 141)
21. **docs/api/context_tools.md** (if applicable)

## Success Criteria

### Part A: 3-Tier UI Labels

- ✅ Frontend shows 4 priority options with descriptive labels (CRITICAL / IMPORTANT / REFERENCE / OFF)
- ✅ Each option shows subtitle explaining orchestrator behavior
- ✅ Dropdowns are wide enough to show full labels without truncation
- ✅ Toggle OFF sets priority to 4, toggle ON sets priority to 3
- ✅ Changes persist across page refreshes
- ✅ Backend defaults updated to reflect new tier meanings
- ✅ Documentation updated to explain new priority system
- ✅ All existing tests pass without modification
- ✅ API roundtrip test confirms priorities persist correctly

### Part B: Field Rename

- ✅ All backend code uses `project_description` instead of `project_context`
- ✅ Frontend UI displays "Project Description" instead of "Project Context"
- ✅ Field remains hardlocked to Priority 1 (CRITICAL) - CANNOT be changed by user
- ✅ UI shows "CRITICAL (Locked)" chip in red (color: red-darken-2)
- ✅ No toggle switch appears for this field (or toggle is disabled)
- ✅ No priority dropdown appears for this field (locked to CRITICAL)
- ✅ All test files updated with new field name
- ✅ MCP output `field_priorities` shows `project_description: 1`
- ✅ Context test suite (51 tests) passes with new field name
- ✅ Backward compatibility migration handles existing user configs
- ✅ Grep verification confirms no old `project_context` references remain

## Migration Notes

### Backward Compatibility

**Existing User Configurations**: No migration needed
- Backend still stores values 1-4 (unchanged)
- Frontend maps numeric values to new labels
- Existing configurations continue to work

**New Users**: Receive updated defaults
- Product Core: CRITICAL (1)
- Project Context: CRITICAL (1) - locked
- 360 Memory: CRITICAL (1)
- Tech Stack: IMPORTANT (2)
- Git History: IMPORTANT (2)
- Vision Documents: REFERENCE (3)
- Architecture: REFERENCE (3)
- Agent Templates: REFERENCE (3)
- Testing: REFERENCE (3)

### Breaking Changes

**None** - This is a UI-only change. Backend values remain 1-4.

## Part B: Field Rename (project_context → project_description)

### Problem Statement

There is a naming inconsistency in the context field system:

| Location | Current Name | Should Be |
|----------|--------------|-----------|
| UI (Context Configurator) | "Project Context" | "Project Description" |
| Field Priority Config (backend) | `project_context` | `project_description` |
| MCP Output (top-level) | `project_description` | `project_description` (correct) |
| Mission JSON | `critical.project_description` | `project_description` (correct) |

The MCP output already uses `project_description` but the UI and backend field priorities use `project_context`.

**UI Behavior**: This field is **hardlocked** to Priority 1 (CRITICAL) and cannot be toggled off. This behavior must be preserved.

### CRITICAL: "Always Critical" Locked Behavior

**MUST PRESERVE**: When renaming `project_context` to `project_description`:
- The field remains **HARDCODED** to Priority 1 (CRITICAL)
- Users **CANNOT** change priority or toggle it off
- UI must show: "Project Description - Always Critical" with a **locked chip**
- This is NOT a regular toggleable field like the others

**Why?** The orchestrator MUST know what project it's working on before fetching other context. This is the foundation field.

**UI Implementation**:
```vue
<!-- Locked chip for Project Description -->
<v-chip size="small" color="red-darken-2" variant="flat">
  CRITICAL (Locked)
</v-chip>
```

**Expected UI Display**:
- Label: "Project Description"
- Chip: Red "CRITICAL (Locked)" badge (no toggle switch)
- No priority dropdown (field is locked)

### Backend Files to Modify

#### 1. src/giljo_mcp/tools/orchestration.py (line ~111)

**Change**:
```python
# BEFORE
"project_context": {"toggle": True, "priority": 1},

# AFTER
"project_description": {"toggle": True, "priority": 1},
```

#### 2. api/endpoints/users.py (lines ~140, 165, 173, 717, 768)

- Update docstrings mentioning `project_context`
- Update `valid_categories` set to use `project_description`

**Example changes**:
```python
# Line ~140
valid_categories = {
    "product_core",
    "project_description",  # Changed from project_context
    "vision_documents",
    # ...
}
```

#### 3. src/giljo_mcp/config/defaults.py (line ~85)

**Change**:
```python
# BEFORE
"project_context": 2,

# AFTER
"project_description": 2,
```

**Note**: This change is COMBINED with Phase 2.1 updates (priority 2 → 1).

### Frontend Files to Modify

#### 4. frontend/src/components/settings/ContextPriorityConfig.vue

**Changes**:
- Update label from "Project Context" to "Project Description"
- Update any field key references from `project_context` to `project_description`
- Update locked chip label (already covered in Phase 1.4)

**Example**:
```vue
<!-- BEFORE -->
<template>
  <div>Project Context</div>
</template>

<!-- AFTER -->
<template>
  <div>Project Description</div>
</template>
```

### Test Files to Update

All test files need field name changes from `project_context` to `project_description`:

1. **tests/api/endpoints/test_users_new_categories.py** (line ~78)
2. **tests/api/endpoints/test_users_category_validation.py** (lines ~8, 34)
3. **tests/api/test_priority_system.py** (multiple lines: 44, 98, 114, 144, 244, 290, 317, 356, 475)
4. **tests/unit/test_priority_framing.py** (lines ~79, 372)
5. **tests/unit/test_new_context_tools.py** (lines ~132, 162, 170)
6. **tests/unit/test_framing_helpers_validation.py** (lines ~69, 117)
7. **tests/unit/test_field_key_mismatches.py** (line ~471)
8. **tests/performance/test_token_reduction_in_real_prompts.py** (line ~206)
9. **tests/unit/test_mission_planner_vision_overview.py** (lines ~277, 312)
10. **handovers/context_test/run_context_tests.py** (lines ~54, 351, 384, 404)

**Pattern for updates**:
```python
# Find and replace pattern
"project_context" → "project_description"
```

### Documentation Files to Update

1. **AGENTS.md** (line ~70)
2. **PHASE5_SUMMARY.md** (lines ~33, 141)
3. **docs/api/context_tools.md** (if applicable)

### Backward Compatibility Migration

Add migration code in config loading to handle existing user settings:

**Location**: `api/endpoints/users.py` or `src/giljo_mcp/config/settings.py`

```python
def migrate_project_context_to_description(user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old 'project_context' field name to 'project_description'.

    Handles backward compatibility for existing user configurations.
    """
    if "project_context" in user_config and "project_description" not in user_config:
        user_config["project_description"] = user_config.pop("project_context")
    return user_config
```

**Apply migration in**:
- GET `/api/v1/users/me/field-priority` (when loading config)
- PUT `/api/v1/users/me/field-priority` (when saving config)

### Grep Commands for Verification

```bash
# Find all occurrences (exclude test results and handovers)
grep -rn "project_context" --include="*.py" --include="*.vue" src/ api/ frontend/src/ tests/

# After changes, verify no occurrences remain
grep -rn "project_context" --include="*.py" --include="*.vue" src/ api/ frontend/src/ tests/ | grep -v "# Historical"
```

## Related Handovers

- **Handover 0313**: Priority System Refactor (v1.0 → v2.0)
- **Handover 0314**: Depth Controls Implementation
- **Handover 0315**: MCP Thin Client Refactor
- **Handover 0347**: Vision Document 4-Level Depth System
- **Handover 0349**: Field rename (integrated into this handover)

## Implementation Checklist

### Part A: 3-Tier UI Labels

- [ ] Phase 1: Frontend UI Update
  - [ ] 1.1: Update priorityOptions array
  - [ ] 1.2: Update v-select components (both instances)
  - [ ] 1.3: Verify toggleContext logic (no changes needed)
  - [ ] 1.4: Update locked chip label
  - [ ] 1.5: Update priority-select styles
- [ ] Phase 2: Backend Defaults Update
  - [ ] 2.1: Update DEFAULT_FIELD_PRIORITIES
  - [ ] 2.2: Update module docstring
- [ ] Phase 3: Documentation Updates
  - [ ] 3.1: Update user guide (if exists)
  - [ ] 3.2: Update CLAUDE.md
- [ ] Phase 4: Testing
  - [ ] 4.1: Visual testing (manual)
  - [ ] 4.2: API testing (curl)
  - [ ] 4.3: Integration testing (orchestrator instructions)
  - [ ] 4.4: Regression testing (pytest)

### Part B: Field Rename

- [ ] Backend Changes
  - [ ] Update `src/giljo_mcp/tools/orchestration.py` (line ~111)
  - [ ] Update `api/endpoints/users.py` (lines ~140, 165, 173, 717, 768)
  - [ ] Update `src/giljo_mcp/config/defaults.py` (line ~85) - COMBINED with Phase 2.1
  - [ ] Add backward compatibility migration code
- [ ] Frontend Changes
  - [ ] Update `frontend/src/components/settings/ContextPriorityConfig.vue` (label + field keys)
  - [ ] Verify Project Description remains hardlocked to CRITICAL
  - [ ] Verify locked chip displays correctly after rename (red-darken-2 color)
  - [ ] Verify no toggle/priority dropdown for this field
  - [ ] Test that users cannot change priority for this field
- [ ] Test Updates (10 files)
  - [ ] Update all test files with field name changes (see list above)
- [ ] Documentation Updates
  - [ ] Update AGENTS.md (line ~70)
  - [ ] Update PHASE5_SUMMARY.md (lines ~33, 141)
  - [ ] Update docs/api/context_tools.md (if applicable)
- [ ] Verification
  - [ ] Run grep command to verify no old references remain
  - [ ] Run context test suite (51 tests)
  - [ ] Verify UI shows "Project Description (CRITICAL - Locked)"

## Notes for Implementer

1. **Priority 4 (OFF) is NEW in UI but NOT NEW in backend**
   - Backend already supports priority 4 (EXCLUDED)
   - Frontend toggle OFF already sets priority to 4
   - We're just exposing priority 4 as a selectable option

2. **Git History Default Changed**
   - Old default: priority 4 (OFF)
   - New default: priority 2 (IMPORTANT)
   - Rationale: When GitHub integration is enabled, git history is valuable context
   - Users can still toggle OFF if desired

3. **Vuetify v-select Subtitles**
   - Use `item-subtitle` prop to show descriptions
   - Subtitles appear in gray text below main label
   - Requires Vuetify 3.4+

4. **Testing Strategy**
   - Visual testing is critical (verify labels display correctly)
   - API testing confirms backend unchanged (1-4 values)
   - Integration testing verifies orchestrator framing matches UI
   - Regression testing ensures no existing functionality broken

## Estimated Timeline

### Part A: 3-Tier UI Labels
- **Phase 1** (Frontend UI): 1 hour
- **Phase 2** (Backend Defaults): 30 minutes
- **Phase 3** (Documentation): 30 minutes
- **Phase 4** (Testing): 1 hour

**Subtotal**: 3 hours

### Part B: Field Rename
- **Backend Changes** (3 files + migration): 1 hour
- **Frontend Changes** (1 file): 30 minutes
- **Test Updates** (10 files): 1 hour
- **Documentation Updates** (3 files): 30 minutes
- **Verification & Testing**: 1 hour

**Subtotal**: 4 hours

**Total Combined**: 6-7 hours (1 full day)

## Questions for User

1. Should git_history default to IMPORTANT (2) or remain OFF (4)?
   - **Recommendation**: IMPORTANT (2) - reflects value when GitHub enabled
   - **Alternative**: OFF (4) - maintains current default

2. Should we add color coding to priority chips in other UI components?
   - Example: StatusBoard shows "Priority 1" chip → "CRITICAL" chip (red)
   - **Recommendation**: Yes, for consistency across UI

3. Should we update existing user configurations to new defaults?
   - **Recommendation**: No - respect user choices
   - **Alternative**: Provide migration wizard in UI

---

**End of Handover 0352**
