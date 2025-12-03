# Handover 0301: Fix Priority Mapping UI-Backend Bug (TDD)

**Status**: Active
**Tool**: Claude Code (CLI) - Requires database access and integration testing
**Estimated Time**: 2-3 hours
**Created**: 2025-11-16
**Assignee**: TDD Implementor Agent

## Executive Summary

Critical bug in field priority mapping causes ALL user-configured priorities to map to "minimal" detail level (80% context prioritization) instead of the intended full/moderate/abbreviated levels. This defeats the purpose of the context prioritization and orchestration system.

**Root Cause**: UI sends Priority 1/2/3 (values: 1, 2, 3) but backend `_get_detail_level()` expects 1-10 scale.

**Impact**: Users experience unexpectedly aggressive context prioritization regardless of their priority settings.

**Solution**: Map UI priority values to correct backend scale in `UserSettings.vue` saveFieldPriority function.

## Problem Statement

### Current Behavior (BROKEN)

**UI Layer** (`frontend/src/views/UserSettings.vue`):
```javascript
// Lines 912-920
priority1Fields.value.forEach(field => {
  fieldsConfig[field] = 1  // ❌ WRONG: Backend expects 10
})
priority2Fields.value.forEach(field => {
  fieldsConfig[field] = 2  // ❌ WRONG: Backend expects 7
})
priority3Fields.value.forEach(field => {
  fieldsConfig[field] = 3  // ❌ WRONG: Backend expects 4
})
```

**Backend Layer** (`src/giljo_mcp/mission_planner.py:512-522`):
```python
def _get_detail_level(self, priority: int) -> str:
    """Map priority (1-10) to detail level."""
    if priority >= 10:
        return "full"        # 0% context prioritization
    if priority >= 7:
        return "moderate"    # 25% context prioritization
    if priority >= 4:
        return "abbreviated" # 50% context prioritization
    if priority >= 1:
        return "minimal"     # 80% context prioritization (EVERYTHING GOES HERE!)
    return "exclude"
```

**Result**: ALL priorities (1, 2, 3) fall into the `priority >= 1` branch → "minimal" → 80% reduction

### Expected Behavior (CORRECT)

| UI Priority | UI Display | Backend Value | Detail Level | Token Reduction |
|-------------|------------|---------------|--------------|-----------------|
| Priority 1 | Always Included | 10 | full | 0% |
| Priority 2 | High Priority | 7 | moderate | 25% |
| Priority 3 | Medium Priority | 4 | abbreviated | 50% |
| Unassigned | (not sent) | 0 | exclude | 100% (omitted) |

## TDD Implementation Plan

### Phase 1: Write Failing Tests (RED) ✅

**File**: `tests/integration/test_field_priority_mapping.py` (NEW)

**Test Specifications** (behavior-focused):

1. **test_priority_1_always_included_maps_to_full_detail**
   - Given: User assigns field to Priority 1 (Always Included)
   - When: Field priority config saved via API
   - Then: Backend receives priority=10 → detail_level="full" → 0% context prioritization

2. **test_priority_2_high_priority_maps_to_moderate_detail**
   - Given: User assigns field to Priority 2 (High Priority)
   - When: Field priority config saved via API
   - Then: Backend receives priority=7 → detail_level="moderate" → 25% context prioritization

3. **test_priority_3_medium_priority_maps_to_abbreviated_detail**
   - Given: User assigns field to Priority 3 (Medium Priority)
   - When: Field priority config saved via API
   - Then: Backend receives priority=4 → detail_level="abbreviated" → 50% context prioritization

4. **test_unassigned_fields_excluded_from_config**
   - Given: User leaves field unassigned
   - When: Field priority config saved via API
   - Then: Field not included in saved config → backend treats as priority=0 → "exclude"

5. **test_actual_token_counts_match_detail_levels**
   - Given: User configures mixed priorities (1/2/3/unassigned)
   - When: Orchestrator generates condensed mission via `_build_context_with_priorities()`
   - Then:
     - Priority 1 fields: Full content (reference token count)
     - Priority 2 fields: ~75% of reference tokens (25% reduction)
     - Priority 3 fields: ~50% of reference tokens (50% reduction)
     - Unassigned fields: 0 tokens (excluded)

6. **test_priority_mapping_backwards_compatibility**
   - Given: Existing user has old config with 1/2/3 values (before fix)
   - When: Migration or validation applied
   - Then: Old values auto-converted to 10/7/4 OR validation warns user to reconfigure

**Write these tests FIRST** - they should FAIL initially (RED phase).

### Phase 2: Minimal Fix (GREEN) ✅

**Goal**: Make tests pass with minimal code changes.

#### Change 1: Update Frontend Mapping

**File**: `frontend/src/views/UserSettings.vue`
**Function**: `saveFieldPriority()` (lines 906-940)
**Change**:

```javascript
// BEFORE (BROKEN)
priority1Fields.value.forEach(field => {
  fieldsConfig[field] = 1  // ❌ Maps to "minimal"
})
priority2Fields.value.forEach(field => {
  fieldsConfig[field] = 2  // ❌ Maps to "minimal"
})
priority3Fields.value.forEach(field => {
  fieldsConfig[field] = 3  // ❌ Maps to "minimal"
})

// AFTER (FIXED)
priority1Fields.value.forEach(field => {
  fieldsConfig[field] = 10  // ✅ Maps to "full"
})
priority2Fields.value.forEach(field => {
  fieldsConfig[field] = 7   // ✅ Maps to "moderate"
})
priority3Fields.value.forEach(field => {
  fieldsConfig[field] = 4   // ✅ Maps to "abbreviated"
})
```

#### Change 2: Update Schema Validation (Optional but Recommended)

**File**: `api/endpoints/users.py`
**Class**: `FieldPriorityConfig` (lines 132-138)
**Change**: Add validation to ensure values are in expected ranges

```python
# BEFORE
class FieldPriorityConfig(BaseModel):
    """Request/Response model for field priority configuration"""

    fields: dict[str, int] = Field(..., description="Field paths mapped to priority (1-3)")
    token_budget: int = Field(1500, description="Maximum tokens for config_data section")
    version: str = Field("1.0", description="Config schema version")

# AFTER
from pydantic import field_validator

class FieldPriorityConfig(BaseModel):
    """Request/Response model for field priority configuration"""

    fields: dict[str, int] = Field(
        ...,
        description="Field paths mapped to priority (0, 4, 7, or 10)"
    )
    token_budget: int = Field(1500, description="Maximum tokens for config_data section")
    version: str = Field("1.0", description="Config schema version")

    @field_validator("fields")
    @classmethod
    def validate_priority_values(cls, v: dict[str, int]) -> dict[str, int]:
        """Ensure priority values are in correct backend scale (0, 4, 7, 10)."""
        valid_priorities = {0, 4, 7, 10}
        for field_path, priority in v.items():
            if priority not in valid_priorities:
                raise ValueError(
                    f"Invalid priority {priority} for field '{field_path}'. "
                    f"Must be one of: 0 (exclude), 4 (abbreviated), 7 (moderate), 10 (full)"
                )
        return v
```

**Run tests** - they should now PASS (GREEN phase).

### Phase 3: Refactor (REFACTOR) ✅

**Goal**: Improve code quality without changing behavior.

#### Refactor 1: Add Constants

**File**: `frontend/src/views/UserSettings.vue`
**Location**: Top of script section
**Addition**:

```javascript
// Field Priority Constants (must match backend MissionPlanner._get_detail_level)
const PRIORITY_ALWAYS_INCLUDED = 10  // "full" detail - 0% context prioritization
const PRIORITY_HIGH = 7              // "moderate" detail - 25% context prioritization
const PRIORITY_MEDIUM = 4            // "abbreviated" detail - 50% context prioritization
const PRIORITY_EXCLUDE = 0           // "exclude" - 100% context prioritization (omitted)

// Update saveFieldPriority function to use constants
async function saveFieldPriority() {
  savingFieldPriority.value = true
  try {
    const fieldsConfig = {}
    priority1Fields.value.forEach(field => {
      fieldsConfig[field] = PRIORITY_ALWAYS_INCLUDED  // ✅ Explicit constant
    })
    priority2Fields.value.forEach(field => {
      fieldsConfig[field] = PRIORITY_HIGH  // ✅ Explicit constant
    })
    priority3Fields.value.forEach(field => {
      fieldsConfig[field] = PRIORITY_MEDIUM  // ✅ Explicit constant
    })
    // ... rest of function
  }
}
```

#### Refactor 2: Update Documentation

**File**: `frontend/src/views/UserSettings.vue`
**Location**: Add comment above `saveFieldPriority()` function
**Content**:

```javascript
/**
 * Save user's field priority configuration.
 *
 * IMPORTANT: UI priorities (1/2/3) are mapped to backend scale (10/7/4) to match
 * MissionPlanner._get_detail_level() expected ranges:
 *
 * - Priority 1 (Always Included) → 10 → "full" (0% context prioritization)
 * - Priority 2 (High Priority)    → 7  → "moderate" (25% context prioritization)
 * - Priority 3 (Medium Priority)  → 4  → "abbreviated" (50% context prioritization)
 * - Unassigned                    → 0  → "exclude" (100% context prioritization)
 *
 * See: src/giljo_mcp/mission_planner.py:512 (_get_detail_level)
 */
async function saveFieldPriority() {
  // ... implementation
}
```

**File**: `src/giljo_mcp/mission_planner.py`
**Location**: Add to `_get_detail_level()` docstring
**Content**:

```python
def _get_detail_level(self, priority: int) -> str:
    """
    Map priority (0-10 scale) to detail level.

    IMPORTANT: UI layer must map visual priorities to this scale:
    - UI "Priority 1 (Always Included)" → 10 → "full"
    - UI "Priority 2 (High Priority)"    → 7  → "moderate"
    - UI "Priority 3 (Medium Priority)"  → 4  → "abbreviated"
    - UI "Unassigned"                    → 0  → "exclude"

    See: frontend/src/views/UserSettings.vue (saveFieldPriority function)

    Args:
        priority: Field importance weight (0-10)

    Returns:
        Detail level string: "full", "moderate", "abbreviated", "minimal", "exclude"
    """
    if priority >= 10:
        return "full"        # 0% context prioritization
    if priority >= 7:
        return "moderate"    # 25% context prioritization
    if priority >= 4:
        return "abbreviated" # 50% context prioritization
    if priority >= 1:
        return "minimal"     # 80% context prioritization
    return "exclude"         # 100% context prioritization (omitted)
```

#### Refactor 3: Add Backend Constants (Optional)

**File**: `src/giljo_mcp/mission_planner.py`
**Location**: Top of file, after imports
**Addition**:

```python
# Field Priority Scale (0-10)
# These values correspond to UI priority selections
PRIORITY_FULL = 10        # UI: "Priority 1 (Always Included)" → "full" detail
PRIORITY_MODERATE = 7     # UI: "Priority 2 (High Priority)" → "moderate" detail
PRIORITY_ABBREVIATED = 4  # UI: "Priority 3 (Medium Priority)" → "abbreviated" detail
PRIORITY_MINIMAL = 1      # Legacy/edge case → "minimal" detail
PRIORITY_EXCLUDE = 0      # UI: Unassigned → "exclude" (omitted)

# Update _get_detail_level to use constants (optional for clarity)
def _get_detail_level(self, priority: int) -> str:
    """Map priority (0-10 scale) to detail level."""
    if priority >= PRIORITY_FULL:
        return "full"
    if priority >= PRIORITY_MODERATE:
        return "moderate"
    if priority >= PRIORITY_ABBREVIATED:
        return "abbreviated"
    if priority >= PRIORITY_MINIMAL:
        return "minimal"
    return "exclude"
```

**Run tests again** - they should still PASS (verify refactor didn't break anything).

## Files to Modify

### Frontend
- `frontend/src/views/UserSettings.vue` (saveFieldPriority function)
  - Lines 906-940 (primary change)
  - Add constants at top of script section (refactor)
  - Add documentation comment (refactor)

### Backend
- `api/endpoints/users.py` (FieldPriorityConfig schema)
  - Lines 132-138 (add validation)
- `src/giljo_mcp/mission_planner.py` (_get_detail_level method)
  - Lines 512-522 (add documentation)
  - Optional: Add constants at top of file

### Tests (NEW)
- `tests/integration/test_field_priority_mapping.py`
  - 6 test functions (see Phase 1)
  - Full integration tests covering UI → API → Backend → Token Reduction flow

## Test Implementation Details

### Test File Structure

```python
"""
Integration tests for field priority mapping (UI → Backend).

CRITICAL BUG FIX: UI sends 1/2/3 but backend expects 10/7/4 for correct detail levels.
Before fix: All priorities map to "minimal" (80% context prioritization)
After fix: Priorities map to "full"/"moderate"/"abbreviated" as intended

Handover: 0301
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User, Product, Project, MCPAgentJob
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.database import DatabaseManager


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user for priority mapping tests."""
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
        field_priority_config=None  # Will be set by tests
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, test_user: User):
    """Create test product with vision and config_data."""
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        description="Test product for priority mapping.",
        tenant_key=test_user.tenant_key,
        is_active=True,
        primary_vision_text="Product vision document with detailed information about the product goals and strategy.",
        config_data={
            "architecture": "Microservices architecture using FastAPI, PostgreSQL, and Vue3 frontend.",
            "dependencies": "Python 3.11+, PostgreSQL 18, Node.js 18+",
            "deployment": "Docker containers with docker-compose orchestration"
        }
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: User, test_product: Product):
    """Create test project with codebase summary."""
    project = Project(
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project for implementing authentication system with JWT tokens and role-based access control.",
        product_id=str(test_product.id),
        tenant_key=test_user.tenant_key,
        status="active",
        mission="Implement secure authentication system with multi-tenant support.",
        context_budget=180000,
        codebase_summary="""
# Codebase Summary

## Architecture
- FastAPI backend with async PostgreSQL
- Vue 3 frontend with Vuetify components
- Multi-tenant data isolation

## Key Files
- api/endpoints/auth.py - Authentication endpoints
- src/giljo_mcp/models/auth.py - User model and password handling
- frontend/src/views/Login.vue - Login interface

## Recent Changes
- Added JWT token refresh mechanism
- Implemented role-based access control
- Enhanced password reset flow with PIN system
"""
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_priority_1_always_included_maps_to_full_detail(
    db_session: AsyncSession,
    test_user: User,
    test_product: Product,
    test_project: Project
):
    """
    Priority 1 (Always Included) should map to backend value 10 → "full" detail (0% context prioritization).

    Test Flow:
    1. User configures "codebase_summary" as Priority 1 (value: 10 after fix)
    2. Backend _get_detail_level(10) returns "full"
    3. Full codebase summary included in condensed mission (0% reduction)

    Expected: Full content with all sections intact
    """
    # ARRANGE: Set user field priorities (simulating POST /api/users/field-priority-config)
    # After fix: UI sends 10 for Priority 1 (not 1)
    test_user.field_priority_config = {
        "version": "1.0",
        "fields": {
            "codebase_summary": 10  # Priority 1 → backend value 10 → "full"
        },
        "token_budget": 2000
    }
    await db_session.commit()

    # ACT: Build context with priorities (simulating get_orchestrator_instructions)
    planner = MissionPlanner(DatabaseManager())
    condensed_mission = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"codebase_summary": 10},  # Priority 1 → 10
        user_id=str(test_user.id)
    )

    # ASSERT: Verify full codebase summary included (0% context prioritization)
    assert "## Codebase" in condensed_mission, "Codebase section should be present"
    assert "# Codebase Summary" in condensed_mission, "Full content header should be present"
    assert "## Architecture" in condensed_mission, "Architecture section should be present"
    assert "## Key Files" in condensed_mission, "Key Files section should be present"
    assert "## Recent Changes" in condensed_mission, "Recent Changes section should be present"

    # Verify detail level mapping
    detail_level = planner._get_detail_level(10)
    assert detail_level == "full", f"Priority 10 should map to 'full', got '{detail_level}'"

    # Verify token count is NOT aggressively reduced
    codebase_section = condensed_mission.split("## Codebase")[1].split("##")[0]
    codebase_tokens = planner._count_tokens(codebase_section)
    original_tokens = planner._count_tokens(test_project.codebase_summary)

    # "full" should be ~100% of original (allow 5% variance for formatting)
    token_ratio = codebase_tokens / original_tokens
    assert token_ratio >= 0.95, (
        f"Priority 1 (full) should preserve ~100% of tokens. "
        f"Got {token_ratio:.1%} ({codebase_tokens} / {original_tokens} tokens)"
    )


@pytest.mark.asyncio
async def test_priority_2_high_priority_maps_to_moderate_detail(
    db_session: AsyncSession,
    test_user: User,
    test_product: Product,
    test_project: Project
):
    """
    Priority 2 (High Priority) should map to backend value 7 → "moderate" detail (25% context prioritization).

    Test Flow:
    1. User configures "codebase_summary" as Priority 2 (value: 7 after fix)
    2. Backend _get_detail_level(7) returns "moderate"
    3. Slightly condensed codebase summary included (~75% of original tokens)

    Expected: Content preserved with minor condensation
    """
    # ARRANGE: Set user field priorities (Priority 2 → backend value 7)
    test_user.field_priority_config = {
        "version": "1.0",
        "fields": {
            "codebase_summary": 7  # Priority 2 → backend value 7 → "moderate"
        },
        "token_budget": 2000
    }
    await db_session.commit()

    # ACT: Build context with priorities
    planner = MissionPlanner(DatabaseManager())
    condensed_mission = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"codebase_summary": 7},  # Priority 2 → 7
        user_id=str(test_user.id)
    )

    # ASSERT: Verify moderate detail level (25% context prioritization)
    assert "## Codebase" in condensed_mission, "Codebase section should be present"

    # Verify detail level mapping
    detail_level = planner._get_detail_level(7)
    assert detail_level == "moderate", f"Priority 7 should map to 'moderate', got '{detail_level}'"

    # Verify token count shows ~25% reduction (75% preserved)
    codebase_section = condensed_mission.split("## Codebase")[1].split("##")[0]
    codebase_tokens = planner._count_tokens(codebase_section)
    original_tokens = planner._count_tokens(test_project.codebase_summary)

    # "moderate" should be ~75% of original (allow 10% variance)
    token_ratio = codebase_tokens / original_tokens
    assert 0.65 <= token_ratio <= 0.85, (
        f"Priority 2 (moderate) should preserve ~75% of tokens. "
        f"Got {token_ratio:.1%} ({codebase_tokens} / {original_tokens} tokens)"
    )


@pytest.mark.asyncio
async def test_priority_3_medium_priority_maps_to_abbreviated_detail(
    db_session: AsyncSession,
    test_user: User,
    test_product: Product,
    test_project: Project
):
    """
    Priority 3 (Medium Priority) should map to backend value 4 → "abbreviated" detail (50% context prioritization).

    Test Flow:
    1. User configures "codebase_summary" as Priority 3 (value: 4 after fix)
    2. Backend _get_detail_level(4) returns "abbreviated"
    3. Abbreviated codebase summary included (~50% of original tokens)

    Expected: Content significantly condensed, key headers preserved
    """
    # ARRANGE: Set user field priorities (Priority 3 → backend value 4)
    test_user.field_priority_config = {
        "version": "1.0",
        "fields": {
            "codebase_summary": 4  # Priority 3 → backend value 4 → "abbreviated"
        },
        "token_budget": 2000
    }
    await db_session.commit()

    # ACT: Build context with priorities
    planner = MissionPlanner(DatabaseManager())
    condensed_mission = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"codebase_summary": 4},  # Priority 3 → 4
        user_id=str(test_user.id)
    )

    # ASSERT: Verify abbreviated detail level (50% context prioritization)
    assert "## Codebase" in condensed_mission, "Codebase section should be present"

    # Verify detail level mapping
    detail_level = planner._get_detail_level(4)
    assert detail_level == "abbreviated", f"Priority 4 should map to 'abbreviated', got '{detail_level}'"

    # Verify token count shows ~50% reduction (50% preserved)
    codebase_section = condensed_mission.split("## Codebase")[1].split("##")[0]
    codebase_tokens = planner._count_tokens(codebase_section)
    original_tokens = planner._count_tokens(test_project.codebase_summary)

    # "abbreviated" should be ~50% of original (allow 15% variance)
    token_ratio = codebase_tokens / original_tokens
    assert 0.35 <= token_ratio <= 0.65, (
        f"Priority 3 (abbreviated) should preserve ~50% of tokens. "
        f"Got {token_ratio:.1%} ({codebase_tokens} / {original_tokens} tokens)"
    )


@pytest.mark.asyncio
async def test_unassigned_fields_excluded_from_config(
    db_session: AsyncSession,
    test_user: User,
    test_product: Product,
    test_project: Project
):
    """
    Unassigned fields should NOT be included in the field priority config.
    Backend treats missing fields as priority=0 → "exclude" (100% context prioritization).

    Test Flow:
    1. User configures some fields but leaves "codebase_summary" unassigned
    2. Field not included in saved config
    3. Backend _get_detail_level(0) returns "exclude"
    4. Codebase summary section omitted from condensed mission

    Expected: Unassigned field completely excluded from context
    """
    # ARRANGE: Set user field priorities WITHOUT codebase_summary (unassigned)
    test_user.field_priority_config = {
        "version": "1.0",
        "fields": {
            "architecture": 10,  # Assigned to Priority 1
            # "codebase_summary": NOT PRESENT (unassigned)
        },
        "token_budget": 2000
    }
    await db_session.commit()

    # ACT: Build context with priorities (codebase_summary not in field_priorities dict)
    planner = MissionPlanner(DatabaseManager())
    condensed_mission = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={"architecture": 10},  # codebase_summary NOT present
        user_id=str(test_user.id)
    )

    # ASSERT: Verify codebase summary EXCLUDED (100% context prioritization)
    # Note: Implementation may show "## Codebase" header with no content OR omit section entirely
    # Both are acceptable as long as the substantive content is excluded

    # Check if section exists
    if "## Codebase" in condensed_mission:
        # If section exists, it should be nearly empty (header only)
        codebase_section = condensed_mission.split("## Codebase")[1].split("##")[0].strip()
        codebase_tokens = planner._count_tokens(codebase_section)
        assert codebase_tokens < 10, (
            f"Unassigned field should be excluded (< 10 tokens). Got {codebase_tokens} tokens"
        )
    else:
        # Section completely omitted (preferred behavior)
        pass  # This is correct - unassigned field is excluded

    # Verify detail level mapping for priority=0
    detail_level = planner._get_detail_level(0)
    assert detail_level == "exclude", f"Priority 0 should map to 'exclude', got '{detail_level}'"


@pytest.mark.asyncio
async def test_actual_token_counts_match_detail_levels(
    db_session: AsyncSession,
    test_user: User,
    test_product: Product,
    test_project: Project
):
    """
    Integration test: Verify actual context prioritization percentages match detail levels
    when multiple fields have different priorities.

    Test Flow:
    1. Configure mixed priorities:
       - architecture: Priority 1 (value 10) → "full" (0% reduction)
       - codebase_summary: Priority 2 (value 7) → "moderate" (25% reduction)
       - (other fields from config_data unassigned) → "exclude" (100% reduction)
    2. Generate condensed mission
    3. Verify each field's token count matches expected reduction

    Expected: Token counts align with detail level definitions
    """
    # ARRANGE: Set mixed field priorities
    test_user.field_priority_config = {
        "version": "1.0",
        "fields": {
            "architecture": 10,      # Priority 1 → "full" (0% reduction)
            "codebase_summary": 7,   # Priority 2 → "moderate" (25% reduction)
            # "dependencies": unassigned → "exclude" (100% reduction)
        },
        "token_budget": 2000
    }
    await db_session.commit()

    # ACT: Build context with mixed priorities
    planner = MissionPlanner(DatabaseManager())
    condensed_mission = await planner._build_context_with_priorities(
        product=test_product,
        project=test_project,
        field_priorities={
            "architecture": 10,
            "codebase_summary": 7
        },
        user_id=str(test_user.id)
    )

    # ASSERT: Verify token counts for each field

    # 1. Architecture (Priority 1 → "full" → 0% reduction)
    assert "## Architecture" in condensed_mission
    arch_section = condensed_mission.split("## Architecture")[1].split("##")[0]
    arch_tokens = planner._count_tokens(arch_section)
    original_arch = test_product.config_data.get("architecture", "")
    original_arch_tokens = planner._count_tokens(f"## Architecture\n{original_arch}")

    arch_ratio = arch_tokens / original_arch_tokens if original_arch_tokens > 0 else 1.0
    assert arch_ratio >= 0.95, (
        f"Architecture (Priority 1/full) should preserve ~100% of tokens. "
        f"Got {arch_ratio:.1%}"
    )

    # 2. Codebase Summary (Priority 2 → "moderate" → 25% reduction)
    assert "## Codebase" in condensed_mission
    codebase_section = condensed_mission.split("## Codebase")[1].split("##")[0]
    codebase_tokens = planner._count_tokens(codebase_section)
    original_codebase_tokens = planner._count_tokens(test_project.codebase_summary)

    codebase_ratio = codebase_tokens / original_codebase_tokens
    assert 0.65 <= codebase_ratio <= 0.85, (
        f"Codebase (Priority 2/moderate) should preserve ~75% of tokens. "
        f"Got {codebase_ratio:.1%}"
    )

    # 3. Dependencies (Unassigned → "exclude" → 100% reduction)
    # Should NOT appear in condensed mission (or appear as nearly empty)
    if "## Dependencies" in condensed_mission:
        dep_section = condensed_mission.split("## Dependencies")[1].split("##")[0].strip()
        dep_tokens = planner._count_tokens(dep_section)
        assert dep_tokens < 10, (
            f"Dependencies (unassigned/exclude) should be omitted. Got {dep_tokens} tokens"
        )


@pytest.mark.asyncio
async def test_priority_mapping_backwards_compatibility(
    db_session: AsyncSession,
    test_user: User,
    test_product: Product,
    test_project: Project
):
    """
    EDGE CASE: Existing users may have old config with 1/2/3 values (before fix).
    Verify that old values are handled gracefully (either auto-converted or validation warns).

    Test Flow:
    1. User has old config with values 1/2/3 (before fix)
    2. Attempt to use config in mission planning
    3. System should either:
       a) Auto-convert: 1→10, 2→7, 3→4 (transparent migration), OR
       b) Reject config with validation error (force user to reconfigure)

    Decision: AUTO-CONVERSION preferred for better UX (no user action required)

    Expected: Old configs auto-converted or validation error raised
    """
    # ARRANGE: Simulate old config with 1/2/3 values (before fix)
    old_config = {
        "version": "1.0",
        "fields": {
            "codebase_summary": 1,  # OLD: Priority 1 sent as 1 (should be 10)
            "architecture": 2,       # OLD: Priority 2 sent as 2 (should be 7)
            "dependencies": 3        # OLD: Priority 3 sent as 3 (should be 4)
        },
        "token_budget": 2000
    }

    # Option A: Auto-conversion (RECOMMENDED)
    # Add migration function to convert old values
    def migrate_old_priority_values(config: dict) -> dict:
        """Migrate old priority values (1/2/3) to new scale (10/7/4)."""
        old_to_new = {1: 10, 2: 7, 3: 4}
        if "fields" in config:
            migrated_fields = {}
            for field, priority in config["fields"].items():
                migrated_fields[field] = old_to_new.get(priority, priority)
            config["fields"] = migrated_fields
        return config

    migrated_config = migrate_old_priority_values(old_config)
    test_user.field_priority_config = migrated_config
    await db_session.commit()

    # ACT: Verify migration worked
    assert migrated_config["fields"]["codebase_summary"] == 10
    assert migrated_config["fields"]["architecture"] == 7
    assert migrated_config["fields"]["dependencies"] == 4

    # Option B: Validation error (ALTERNATIVE - less user-friendly)
    # Test that FieldPriorityConfig schema rejects old values
    from api.endpoints.users import FieldPriorityConfig
    from pydantic import ValidationError

    try:
        # Attempt to validate old config (should fail after adding validation)
        FieldPriorityConfig(**old_config)
        pytest.fail("Old config should be rejected by validation")
    except ValidationError as e:
        # Expected - validation rejects old values
        assert "priority" in str(e).lower() or "invalid" in str(e).lower()
```

## Validation Checklist

After implementing the fix, verify:

### Unit Tests
- [ ] All 6 new integration tests pass
- [ ] Existing `test_orchestrator_field_priorities.py` tests still pass
- [ ] No regressions in other field priority tests

### Manual Testing
1. **UI Configuration**:
   - [ ] Open My Settings → Context → Field Priorities
   - [ ] Drag fields to Priority 1 (Always Included)
   - [ ] Drag fields to Priority 2 (High Priority)
   - [ ] Drag fields to Priority 3 (Medium Priority)
   - [ ] Leave some fields unassigned
   - [ ] Click "Save Field Priority Config"

2. **Backend Verification**:
   - [ ] Query database: `SELECT field_priority_config FROM mcp_users WHERE id = '<user_id>';`
   - [ ] Verify Priority 1 fields have value `10` (not `1`)
   - [ ] Verify Priority 2 fields have value `7` (not `2`)
   - [ ] Verify Priority 3 fields have value `4` (not `3`)
   - [ ] Verify unassigned fields are NOT in the config dict

3. **Orchestrator Mission**:
   - [ ] Stage a project via UI (Products → Stage Project)
   - [ ] Copy orchestrator instructions from generated prompt
   - [ ] Verify Priority 1 fields show FULL content (not truncated)
   - [ ] Verify Priority 2 fields show MODERATE condensation (~75% of original)
   - [ ] Verify Priority 3 fields show ABBREVIATED content (~50% of original)
   - [ ] Verify unassigned fields are EXCLUDED entirely

4. **Token Reduction Metrics**:
   - [ ] Check orchestrator job metadata: `SELECT job_metadata FROM mcp_agent_jobs WHERE agent_type = 'orchestrator';`
   - [ ] Verify `field_priorities` matches user's config (values 10/7/4, not 1/2/3)
   - [ ] Verify `token_reduction_applied` is true
   - [ ] Check logs for context prioritization percentage (should be < 70%, not 80%)

### Performance Testing
- [ ] Verify context prioritization system still achieves 70% reduction target (not 80%)
- [ ] Check that token counts match expected detail levels
- [ ] Ensure no performance degradation from validation logic

## Rollback Plan

If critical issues discovered after deployment:

### Immediate Rollback (< 5 minutes)
1. **Revert Frontend Change**:
   ```bash
   git checkout HEAD~1 frontend/src/views/UserSettings.vue
   cd frontend && npm run build
   ```

2. **Restart Frontend Server**:
   ```bash
   # If running in production
   systemctl restart giljo-frontend
   ```

### Database Migration (if validation added)
If FieldPriorityConfig validation causes issues:

1. **Temporarily disable validation**:
   ```python
   # In api/endpoints/users.py
   # Comment out @field_validator decorator
   ```

2. **Restart API server**:
   ```bash
   systemctl restart giljo-api
   ```

### User Communication
If users have invalid configs:

1. **Identify affected users**:
   ```sql
   SELECT id, username, field_priority_config
   FROM mcp_users
   WHERE field_priority_config IS NOT NULL
   AND (
       field_priority_config->'fields' ? '1' OR
       field_priority_config->'fields' ? '2' OR
       field_priority_config->'fields' ? '3'
   );
   ```

2. **Auto-migrate old configs** (recommended):
   ```python
   # Run migration script
   python scripts/migrate_field_priorities.py
   ```

3. **OR notify users to reconfigure** (alternative):
   - Display banner in UI: "Please update your Field Priority settings"
   - Link to My Settings → Context → Field Priorities

## Success Criteria

- [ ] All 6 new integration tests pass
- [ ] Existing tests remain passing (no regressions)
- [ ] Manual testing confirms correct mapping (1→10, 2→7, 3→4)
- [ ] Orchestrator missions show expected detail levels (full/moderate/abbreviated)
- [ ] Context prioritization metrics align with priority selections
- [ ] No performance degradation
- [ ] Documentation updated (code comments, docstrings)
- [ ] Rollback plan tested and validated

## Notes

### Why This Bug Occurred
1. **UI Layer**: Designed with logical priority system (1, 2, 3)
2. **Backend Layer**: Designed with 1-10 scale for granular control
3. **Integration Gap**: No mapping layer between UI and backend scales
4. **Result**: Direct pass-through of UI values (1/2/3) to backend expecting (10/7/4)

### Why Simple Fix Works
- UI already uses 3 discrete priority levels (no need for 1-10 granularity)
- Backend `_get_detail_level()` uses threshold-based mapping (>= comparisons)
- Changing 3 constants in frontend fixes the mismatch
- No database migration required (configs stored as JSONB, values are just integers)

### Future Improvements (Post-Fix)
1. Add E2E test that exercises full UI → API → Backend → Token Reduction flow
2. Consider adding UI validation to prevent manual editing of invalid values
3. Add logging/metrics to track context prioritization effectiveness per priority level
4. Create admin dashboard to view aggregate context prioritization statistics

## Related Files

### Source Code
- `frontend/src/views/UserSettings.vue` (UI layer - PRIMARY FIX)
- `api/endpoints/users.py` (API schema validation)
- `src/giljo_mcp/mission_planner.py` (Backend context prioritization)
- `src/giljo_mcp/tools/orchestration.py` (Orchestrator instructions)

### Tests
- `tests/integration/test_field_priority_mapping.py` (NEW - this handover)
- `tests/integration/test_orchestrator_field_priorities.py` (EXISTING - validates metadata flow)
- `tests/integration/test_mcp_get_orchestrator_instructions.py` (EXISTING - MCP tool tests)

### Documentation
- `docs/SERVICES.md` (Service layer architecture)
- `docs/TESTING.md` (Testing strategy)
- `CLAUDE.md` (Coding standards - cross-platform patterns)

## Handover Acceptance

**Implementor**: Execute this handover following strict TDD principles:
1. Write ALL tests first (Phase 1 - RED)
2. Verify tests FAIL as expected
3. Implement minimal fix (Phase 2 - GREEN)
4. Verify tests PASS
5. Refactor for quality (Phase 3 - REFACTOR)
6. Verify tests still PASS
7. Run full test suite to ensure no regressions
8. Perform manual testing per validation checklist
9. Update this handover with test results and any findings

**Reviewer**: Verify:
- [ ] All tests written before implementation
- [ ] Tests initially failed (RED phase documented)
- [ ] Minimal fix applied (no over-engineering)
- [ ] Tests now pass (GREEN phase documented)
- [ ] Refactoring improves code quality without changing behavior
- [ ] Manual testing completed per checklist
- [ ] Documentation updated appropriately

---

## Implementation Summary

**Status**: ✅ Completed 2025-11-17
**Implemented By**: TDD Implementor Agent
**Git Commits**: a2c8c07, 932e86b

### What Was Built
- Fixed critical priority mapping bug where UI sent 1/2/3 but backend expected 10/7/4
- Updated `UserSettings.vue` to map Priority 1→10, Priority 2→7, Priority 3→4
- Added Pydantic validator in `FieldPriorityConfig` schema for value enforcement
- Implemented comprehensive test suite (6 integration tests passing)
- Fixed auth header bug in defaults.py (commit 932e86b)
- Resolved context generation with correct detail levels

### Files Modified
- `frontend/src/views/UserSettings.vue` (lines 912-920) - Priority mapping fix
- `api/endpoints/users.py` (lines 132-180) - Pydantic validation
- `src/giljo_mcp/config/defaults.py` (auth header fix)
- `tests/integration/test_field_priority_mapping.py` (6 tests - NEW)

### Testing
- All 6 integration tests passing
- Manual UI testing verified correct mapping
- Context prioritization validated (0%/25%/50% for priorities 1/2/3)
- No regressions in existing orchestrator tests

### Token Reduction Impact
Critical fix enabling proper context prioritization system:
- Before: ALL priorities → minimal (80% reduction)
- After: Priority 1 → full (0%), Priority 2 → moderate (25%), Priority 3 → abbreviated (50%)
- System now achieves intended context prioritization and orchestration target

### Production Status
All tests passing. Production ready. Part of v3.1 Context Management System.

---

**End of Handover 0301**


---

## v2.0 Architecture Status

**Date**: November 17, 2025
**Status**: v1.0 Complete - Code REUSED in v2.0 Refactor

### What Changed in v2.0

After completing this handover as part of v1.0, an architectural pivot was identified:

**Issue**: v1.0 conflated prioritization (importance) with token trimming (budget management)
**Solution**: Refactor to 2-dimensional model (Priority × Depth)

### Code Reuse in v2.0

**This handover's work is being REUSED** in the following v2.0 handovers:

- ✅ **Handover 0313** (Priority System): Reuses priority validation and UI patterns
- ✅ **Handover 0314** (Depth Controls): Reuses extraction methods
- ✅ **Handover 0315** (MCP Thin Client): Reuses 60-80% of extraction logic

### Preserved Work

**Production Code** (REUSED):
- All extraction methods (`_format_tech_stack`, `_extract_config_field`, etc.)
- Bug fixes (auth header, priority validation)
- Test coverage (30+ tests adapted for v2.0)

**Architecture** (EVOLVED):
- Priority semantics changed (trimming → emphasis)
- Depth controls added (per-source chunking)
- MCP thin client (fat → thin prompts)

### Why No Rollback

**Code Quality**: Implementation was sound, only architectural approach changed
**Test Coverage**: All tests reused with updated assertions
**Production Ready**: v1.0 code is stable and serves as foundation for v2.0

**Conclusion**: This handover's work is valuable and preserved in v2.0 architecture.

