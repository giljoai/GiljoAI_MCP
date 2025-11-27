# Handover 0307: Backend Default Field Priorities Alignment

**Feature**: Backend Default Field Priorities Aligned with UI
**Status**: Not Started
**Priority**: P1 - HIGH
**Estimated Duration**: 3-4 hours
**Agent Budget**: 80K tokens
**Depends On**: Handover 0302 (Backend Field Priority Validation)
**Blocks**: Handover 0308 (Frontend Field Labels & Tooltips)
**Created**: 2025-11-16
**Tool**: CLI (Backend configuration changes, validation logic)

---

## Executive Summary

The backend's `DEFAULT_FIELD_PRIORITIES` in `src/giljo_mcp/config/defaults.py` is hardcoded with only 2 fields (codebase_summary=6, architecture=4), while the UI expects 13 fields organized into 3 priority tiers. This mismatch causes new users to see incomplete or incorrect priority configurations, breaking the field priority system's 3-tier design.

**Why This Matters**: New users should receive sensible defaults that match the UI's 3-tier priority system (Priority 1/2/3, Unassigned). The current hardcoded defaults don't align with the product configuration fields defined in `DEFAULT_FIELD_PRIORITY`, creating confusion and poor UX.

**Impact**: Aligns backend defaults with UI expectations, ensures new users get complete field priority configuration, eliminates hardcoded exceptions.

---

## Problem Statement

### Current Behavior

**Backend Defaults** (`src/giljo_mcp/mission_planner.py`, lines 37-40):
```python
# Hardcoded defaults that don't match UI
DEFAULT_FIELD_PRIORITIES = {
    "codebase_summary": 6,  # What does "6" mean? Not aligned with 1-2-3 system
    "architecture": 4,      # What does "4" mean? Not aligned with 1-2-3 system
}
```

**Issues**:
1. **Inconsistent Priority Values**: Uses 4 and 6, but UI uses 1, 2, 3, null
2. **Incomplete Field List**: Only 2 fields, but `DEFAULT_FIELD_PRIORITY` defines 13 fields
3. **Doesn't Match UI**: Frontend expects all 13 fields with 1-2-3 priorities
4. **Hardcoded in Wrong File**: Should use `config/defaults.py`, not `mission_planner.py`
5. **No Documentation**: Unclear what these numbers mean or why they exist

### Desired Behavior

**Unified Default System**:
```python
# src/giljo_mcp/config/defaults.py (SINGLE SOURCE OF TRUTH)
DEFAULT_FIELD_PRIORITY = {
    "version": "1.1",
    "token_budget": 2000,
    "fields": {
        # Priority 1: Critical - Always Included (5 fields)
        "tech_stack.languages": 1,
        "tech_stack.backend": 1,
        "tech_stack.frontend": 1,
        "architecture.pattern": 1,
        "features.core": 1,

        # Priority 2: High Priority (4 fields)
        "tech_stack.database": 2,
        "architecture.api_style": 2,
        "test_config.strategy": 2,
        "agent_templates": 2,  # From Handover 0306

        # Priority 3: Medium Priority (5 fields)
        "tech_stack.infrastructure": 3,
        "architecture.design_patterns": 3,
        "architecture.notes": 3,
        "test_config.frameworks": 3,
        "test_config.coverage_target": 3,

        # Context fields (not in product config, but need defaults)
        "codebase_summary": 2,  # High priority (understand existing code)
        "architecture_overview": 2,  # High priority (system structure)
    }
}
```

**User Onboarding Flow**:
1. New user signs up
2. Creates product
3. Gets `field_priority_config = None` (no custom config yet)
4. Backend applies `DEFAULT_FIELD_PRIORITY` defaults
5. Frontend displays all 13 fields in 3 priority tiers (matching defaults)
6. User can drag-and-drop to customize

---

## Objectives

### Primary Goals
1. Eliminate hardcoded `DEFAULT_FIELD_PRIORITIES` from `mission_planner.py`
2. Extend `DEFAULT_FIELD_PRIORITY` to include context fields (codebase_summary, architecture_overview)
3. Create helper function `get_effective_field_priorities()` to merge user + defaults
4. Update all services to use unified defaults from `config/defaults.py`
5. Ensure new users see all 13 fields properly initialized

### Success Criteria
- ✅ `DEFAULT_FIELD_PRIORITIES` removed from `mission_planner.py`
- ✅ `DEFAULT_FIELD_PRIORITY` includes all fields (13 product config + 2 context fields)
- ✅ New users get complete field priority config matching UI expectations
- ✅ `get_effective_field_priorities()` merges user custom + system defaults
- ✅ All services use `config/defaults.py` as single source of truth
- ✅ No regressions in existing field priority logic
- ✅ Unit tests verify default application for new users

---

## TDD Specifications

### Test 1: New User Gets Complete Default Priorities
```python
async def test_new_user_gets_complete_default_priorities(db_session):
    """
    BEHAVIOR: New users receive complete field priority configuration from defaults

    GIVEN: A new user with field_priority_config = None
    WHEN: Generating effective field priorities
    THEN: All 15 fields (13 product + 2 context) have default priorities
    """
    # ARRANGE
    from src.giljo_mcp.services.user_service import UserService
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY, get_effective_field_priorities

    user_service = UserService(db_session)

    # Create new user with no custom config
    user = await user_service.create_user(
        username="new_user",
        tenant_key="test_tenant"
    )

    assert user.field_priority_config is None

    # ACT
    effective_priorities = get_effective_field_priorities(user.field_priority_config)

    # ASSERT
    # All product config fields present
    product_fields = [
        "tech_stack.languages", "tech_stack.backend", "tech_stack.frontend",
        "tech_stack.database", "tech_stack.infrastructure",
        "architecture.pattern", "architecture.api_style", "architecture.design_patterns",
        "architecture.notes", "features.core",
        "test_config.strategy", "test_config.frameworks", "test_config.coverage_target"
    ]

    for field in product_fields:
        assert field in effective_priorities
        assert effective_priorities[field] in [1, 2, 3]

    # Context fields present
    assert "codebase_summary" in effective_priorities
    assert "architecture_overview" in effective_priorities

    # Total count correct
    assert len(effective_priorities) == 15  # 13 product + 2 context
```

### Test 2: User Custom Priorities Override Defaults
```python
async def test_user_custom_priorities_override_defaults(db_session):
    """
    BEHAVIOR: User custom priorities override system defaults while preserving unset fields

    GIVEN: A user with partial custom field_priority_config
    WHEN: Generating effective field priorities
    THEN: Custom values override defaults, unset fields use defaults
    """
    # ARRANGE
    from src.giljo_mcp.config.defaults import get_effective_field_priorities
    from src.giljo_mcp.models import User

    # Create user with partial custom config
    user = User(
        username="custom_user",
        tenant_key="test_tenant",
        field_priority_config={
            "tech_stack.languages": 3,  # Changed from default 1 → 3
            "codebase_summary": 1,      # Changed from default 2 → 1
            # Other fields not specified (should use defaults)
        }
    )

    db_session.add(user)
    await db_session.commit()

    # ACT
    effective_priorities = get_effective_field_priorities(user.field_priority_config)

    # ASSERT
    # Custom values respected
    assert effective_priorities["tech_stack.languages"] == 3
    assert effective_priorities["codebase_summary"] == 1

    # Defaults applied for unset fields
    assert effective_priorities["tech_stack.backend"] == 1  # Default Priority 1
    assert effective_priorities["tech_stack.database"] == 2  # Default Priority 2
    assert effective_priorities["tech_stack.infrastructure"] == 3  # Default Priority 3

    # All 15 fields present
    assert len(effective_priorities) == 15
```

### Test 3: DEFAULT_FIELD_PRIORITIES Removed from mission_planner.py
```python
def test_default_field_priorities_not_in_mission_planner():
    """
    BEHAVIOR: Hardcoded DEFAULT_FIELD_PRIORITIES no longer exists in mission_planner.py

    GIVEN: The mission_planner.py module
    WHEN: Importing the module
    THEN: DEFAULT_FIELD_PRIORITIES attribute does not exist
    """
    # ARRANGE & ACT
    import src.giljo_mcp.mission_planner as mission_planner_module

    # ASSERT
    assert not hasattr(mission_planner_module, "DEFAULT_FIELD_PRIORITIES"), \
        "DEFAULT_FIELD_PRIORITIES should be removed from mission_planner.py"

    # Verify it exists in correct location
    from src.giljo_mcp.config import defaults
    assert hasattr(defaults, "DEFAULT_FIELD_PRIORITY"), \
        "DEFAULT_FIELD_PRIORITY should exist in config/defaults.py"
```

### Test 4: Three-Tier Priority System Validated
```python
async def test_three_tier_priority_system_validated(db_session):
    """
    BEHAVIOR: Field priorities enforce 3-tier system (1=always, 2=high, 3=medium)

    GIVEN: DEFAULT_FIELD_PRIORITY configuration
    WHEN: Validating field priorities
    THEN: All priorities are 1, 2, or 3 (no 4, 6, or other values)
    """
    # ARRANGE
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY, validate_field_priorities

    # ACT & ASSERT
    # Validation should pass
    assert validate_field_priorities() is True

    # All priorities should be 1, 2, or 3
    for field, priority in DEFAULT_FIELD_PRIORITY["fields"].items():
        assert priority in [1, 2, 3], \
            f"Field '{field}' has invalid priority {priority}. Must be 1, 2, or 3."

    # Check distribution
    priority_1_fields = [f for f, p in DEFAULT_FIELD_PRIORITY["fields"].items() if p == 1]
    priority_2_fields = [f for f, p in DEFAULT_FIELD_PRIORITY["fields"].items() if p == 2]
    priority_3_fields = [f for f, p in DEFAULT_FIELD_PRIORITY["fields"].items() if p == 3]

    # Should have fields in each tier
    assert len(priority_1_fields) >= 3, "Priority 1 should have at least 3 critical fields"
    assert len(priority_2_fields) >= 3, "Priority 2 should have at least 3 high priority fields"
    assert len(priority_3_fields) >= 3, "Priority 3 should have at least 3 medium priority fields"
```

### Test 5: Context Fields Included in Defaults
```python
async def test_context_fields_included_in_defaults():
    """
    BEHAVIOR: Context fields (codebase_summary, architecture_overview) have default priorities

    GIVEN: DEFAULT_FIELD_PRIORITY configuration
    WHEN: Checking for context fields
    THEN: codebase_summary and architecture_overview are present with sensible defaults
    """
    # ARRANGE
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

    # ACT
    fields = DEFAULT_FIELD_PRIORITY["fields"]

    # ASSERT
    # Context fields present
    assert "codebase_summary" in fields
    assert "architecture_overview" in fields

    # Have sensible defaults (Priority 2 = high priority)
    assert fields["codebase_summary"] == 2
    assert fields["architecture_overview"] == 2

    # Rationale: Understanding existing code and structure is high priority for agents
```

---

## Implementation Plan

### Step 1: Extend DEFAULT_FIELD_PRIORITY with Context Fields
**File**: `src/giljo_mcp/config/defaults.py`
**Lines**: 74-98

**Changes**:
```python
DEFAULT_FIELD_PRIORITY: Dict[str, Any] = {
    "version": "1.1",
    "token_budget": 2000,
    "fields": {
        # Priority 1: Critical - Always Included (5 fields)
        "tech_stack.languages": 1,
        "tech_stack.backend": 1,
        "tech_stack.frontend": 1,
        "architecture.pattern": 1,
        "features.core": 1,

        # Priority 2: High Priority (6 fields)
        "tech_stack.database": 2,
        "architecture.api_style": 2,
        "test_config.strategy": 2,
        "agent_templates": 2,           # From Handover 0306
        "codebase_summary": 2,          # NEW: Context field
        "architecture_overview": 2,     # NEW: Context field

        # Priority 3: Medium Priority (5 fields)
        "tech_stack.infrastructure": 3,
        "architecture.design_patterns": 3,
        "architecture.notes": 3,
        "test_config.frameworks": 3,
        "test_config.coverage_target": 3,
    },
}
```

**Rationale for Context Field Defaults**:
- **codebase_summary**: Priority 2 (high) - Agents need to understand existing code
- **architecture_overview**: Priority 2 (high) - System structure is critical for planning

### Step 2: Create get_effective_field_priorities() Helper
**File**: `src/giljo_mcp/config/defaults.py`
**New Function**:

```python
def get_effective_field_priorities(
    user_config: Optional[dict] = None
) -> dict[str, int]:
    """
    Get effective field priorities by merging user custom config with system defaults.

    Args:
        user_config: User's custom field_priority_config (None for new users)

    Returns:
        Dictionary mapping field paths to priorities (1-3)

    Example:
        >>> # New user (no custom config)
        >>> priorities = get_effective_field_priorities(None)
        >>> print(priorities["tech_stack.languages"])
        1

        >>> # User with custom config
        >>> custom = {"tech_stack.languages": 3, "codebase_summary": 1}
        >>> priorities = get_effective_field_priorities(custom)
        >>> print(priorities["tech_stack.languages"])
        3
        >>> print(priorities["tech_stack.backend"])  # Uses default
        1
    """
    # Start with system defaults
    effective_priorities = DEFAULT_FIELD_PRIORITY["fields"].copy()

    # Override with user custom config (if any)
    if user_config:
        for field, priority in user_config.items():
            if priority is not None:  # Skip unassigned fields
                effective_priorities[field] = priority
            elif field in effective_priorities:
                # User explicitly unassigned this field
                del effective_priorities[field]

    return effective_priorities
```

### Step 3: Remove Hardcoded DEFAULT_FIELD_PRIORITIES
**File**: `src/giljo_mcp/mission_planner.py`
**Lines**: 34-40

**Remove**:
```python
# DELETE THIS ENTIRE SECTION
# Default field priorities for context building (Fix #1: Handover 0XXX)
# Applied when user has no custom field_priority_config
# Ensures meaningful context even for new users who haven't customized priorities
DEFAULT_FIELD_PRIORITIES = {
    "codebase_summary": 6,  # Moderate detail (50% context prioritization)
    "architecture": 4,      # Abbreviated detail (context prioritization and orchestration)
}
```

**Replace with**:
```python
# Import defaults from centralized config
from .config.defaults import get_effective_field_priorities
```

### Step 4: Update MissionPlanner to Use Unified Defaults
**File**: `src/giljo_mcp/mission_planner.py`
**Method**: `_build_context_string()` or similar

**Before**:
```python
def _build_context_string(self, user_priorities: Optional[dict] = None):
    # Fallback to hardcoded defaults
    priorities = user_priorities or DEFAULT_FIELD_PRIORITIES
    # ...
```

**After**:
```python
def _build_context_string(self, user_priorities: Optional[dict] = None):
    # Merge user custom with system defaults
    priorities = get_effective_field_priorities(user_priorities)
    # ...
```

### Step 5: Update UserService for New User Initialization
**File**: `src/giljo_mcp/services/user_service.py`
**Method**: `create_user()`

**Add Documentation**:
```python
async def create_user(self, username: str, tenant_key: str, **kwargs) -> User:
    """
    Create a new user.

    New users start with field_priority_config = None.
    System defaults from DEFAULT_FIELD_PRIORITY will be applied automatically
    when generating context (see get_effective_field_priorities).

    Args:
        username: User's username
        tenant_key: Tenant isolation key
        **kwargs: Additional user fields

    Returns:
        Created User instance
    """
    # Existing implementation (no changes needed)
    user = User(
        username=username,
        tenant_key=tenant_key,
        field_priority_config=None,  # Explicit: new users get defaults
        **kwargs
    )
    # ... rest of method
```

### Step 6: Update Field Priority Endpoint Documentation
**File**: `api/endpoints/users.py`
**Endpoint**: `GET /api/v1/users/me/field-priority`

**Update Docstring**:
```python
@router.get("/me/field-priority", response_model=FieldPriorityResponse)
async def get_user_field_priorities(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's field priority configuration.

    Returns effective priorities (user custom merged with system defaults).
    New users with no custom config will receive complete defaults for all 15 fields.

    System Defaults (from config/defaults.py):
    - Priority 1 (Always): tech_stack.languages, tech_stack.backend, tech_stack.frontend,
                            architecture.pattern, features.core
    - Priority 2 (High): tech_stack.database, architecture.api_style, test_config.strategy,
                         agent_templates, codebase_summary, architecture_overview
    - Priority 3 (Medium): tech_stack.infrastructure, architecture.design_patterns,
                           architecture.notes, test_config.frameworks, test_config.coverage_target

    Returns:
        FieldPriorityResponse with effective priorities
    """
    from src.giljo_mcp.config.defaults import get_effective_field_priorities

    effective_priorities = get_effective_field_priorities(current_user.field_priority_config)

    return FieldPriorityResponse(
        field_priority_config=effective_priorities,
        is_custom=current_user.field_priority_config is not None
    )
```

### Step 7: Add Unit Tests
**File**: `tests/config/test_defaults.py` (NEW FILE)

**Add the 5 test functions defined in TDD Specifications section above**

**Additional Test**:
```python
def test_default_field_priority_version_updated():
    """Verify version incremented to 1.1"""
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

    assert DEFAULT_FIELD_PRIORITY["version"] == "1.1"
```

---

## Files to Modify

### Backend (6 files)
1. **`src/giljo_mcp/config/defaults.py`** (Update + New Function)
   - Add context fields to DEFAULT_FIELD_PRIORITY
   - Increment version to 1.1
   - Add `get_effective_field_priorities()` function

2. **`src/giljo_mcp/mission_planner.py`** (Remove Hardcoded Defaults)
   - Delete DEFAULT_FIELD_PRIORITIES (lines 34-40)
   - Import `get_effective_field_priorities` from config.defaults
   - Update context building logic to use unified defaults

3. **`src/giljo_mcp/services/user_service.py`** (Documentation Update)
   - Update `create_user()` docstring to explain default behavior

4. **`api/endpoints/users.py`** (Documentation Update)
   - Update `get_user_field_priorities()` docstring with complete defaults list

5. **`tests/config/test_defaults.py`** (NEW FILE)
   - Add 6 unit tests from TDD specifications

6. **`tests/services/test_user_service.py`** (Update)
   - Add test for new user default priorities

---

## Migration Path

### For Existing Users

**No Database Migration Needed** - This is purely a code change.

**Backward Compatibility**:
1. Existing users with custom `field_priority_config` → No change (custom values preserved)
2. Existing users with `field_priority_config = None` → Now get complete defaults (improvement)
3. Hardcoded values (6, 4) never stored in database → No data cleanup needed

**Edge Case Handling**:
```python
# Old code might have referenced DEFAULT_FIELD_PRIORITIES
# Ensure no imports remain after deletion
```

**Validation**:
```bash
# Search for any remaining references
grep -r "DEFAULT_FIELD_PRIORITIES" src/
# Should only find in tests/historical references, not production code
```

---

## Validation Checklist

- [ ] Unit tests pass: `pytest tests/config/test_defaults.py -v`
- [ ] Integration tests pass: `pytest tests/services/test_user_service.py -v`
- [ ] `DEFAULT_FIELD_PRIORITIES` removed from `mission_planner.py`
- [ ] `get_effective_field_priorities()` function works correctly
- [ ] New users receive all 15 fields with proper defaults
- [ ] User custom priorities override defaults as expected
- [ ] No hardcoded priority values (4, 6) remain in codebase
- [ ] API endpoint documentation updated
- [ ] All priorities are 1, 2, or 3 (validated by `validate_field_priorities()`)

---

## Dependencies

### External
- None (pure configuration change)

### Internal
- Handover 0302: Backend Field Priority Validation (ensures 1-2-3 system enforced)
- Handover 0306: Agent Templates in Context String (adds "agent_templates" field)

---

## Breaking Changes

**None** - This is a backward-compatible enhancement.

**Why No Breaking Changes?**:
1. User custom configs preserved (database unchanged)
2. New default system is superset of old hardcoded values
3. `get_effective_field_priorities()` gracefully handles `None` and partial configs
4. Validation ensures all priorities remain 1-2-3 (no invalid values)

---

## Notes

### Why Remove Hardcoded Defaults?

**Problems with Current Approach**:
1. **Duplication**: Defaults defined in two places (mission_planner.py + defaults.py)
2. **Inconsistency**: Different priority values (4/6 vs 1/2/3)
3. **Incomplete**: Only 2 fields vs 15 total fields
4. **Maintenance Burden**: Adding new fields requires updating multiple locations

**Benefits of Unified Approach**:
1. **Single Source of Truth**: `config/defaults.py` owns all defaults
2. **Consistency**: All priorities use 1-2-3 system
3. **Complete**: All 15 fields defined
4. **Maintainability**: Add new fields in one location

### Field Priority Philosophy

**Three-Tier System** (1-2-3):
- **Priority 1 (Always)**: Cannot be excluded - critical for agent understanding
- **Priority 2 (High)**: Included unless severe token constraints
- **Priority 3 (Medium)**: Included when token budget permits
- **Unassigned (null)**: Explicitly excluded by user

**Default Distribution**:
- Priority 1: 5 fields (33%) - Core technical foundation
- Priority 2: 6 fields (40%) - Important context for decisions
- Priority 3: 5 fields (27%) - Additional details and best practices

### Context Fields Rationale

**Why codebase_summary = Priority 2?**
- Agents need to understand existing code to avoid duplication
- Critical for refactoring, bug fixes, and enhancements
- Higher priority than infrastructure but lower than core tech stack

**Why architecture_overview = Priority 2?**
- System structure guides implementation decisions
- Prevents architectural violations
- Essential for maintaining consistency

**Why not Priority 1?**
- Can function without full codebase/architecture (unlike tech stack)
- Provides context but not critical foundation
- Token budget flexibility for users who prefer other fields

---

**Status**: Ready for execution
**Estimated Time**: 3-4 hours (config: 1h, refactoring: 1h, tests: 1.5h, documentation: 30min)
**Agent Budget**: 80K tokens
**Next Handover**: 0308 (Frontend Field Labels & Tooltips)
