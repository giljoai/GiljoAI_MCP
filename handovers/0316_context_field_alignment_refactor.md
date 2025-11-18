# Handover 0316: Context Field Alignment Refactor

**Date**: 2025-11-17
**Status**: Ready for Implementation
**Complexity**: High
**Estimated Effort**: 3-5 days
**Dependencies**: Handovers 0314, 0315
**Compliance**: TDD Required, Service Layer Pattern, Migration Methodology

---

## Executive Summary

This handover refactors the MCP context tool system to align perfectly with Product and Project UI field organization. The current implementation has 2 critical bugs (get_tech_stack, get_architecture) and missing context tools (get_product_context, get_project, get_testing). This refactor creates a clean 1:1 mapping between UI tabs and context tools while fixing architectural issues.

**Impact**:
- Fixes 2 critical bugs in existing context tools
- Adds 3 new context tools
- Reorganizes Product UI for better UX
- Improves context clarity for orchestrators
- Maintains backward compatibility

---

## Problem Statement

### Current Issues

**1. Broken Context Tools** (CRITICAL):
- `get_tech_stack.py` - Attempts to access non-existent Product columns (should use config_data JSONB)
- `get_architecture.py` - Attempts to access non-existent `architecture_notes` field (should use config_data JSONB)

**2. Missing Context Tools**:
- No `get_product_context.py` - General product info (name, description, features)
- No `get_project.py` - Current project context
- No `get_testing.py` - Testing strategy and quality standards

**3. UI Misalignment**:
- "Features" field located in wrong tab (Features & Testing instead of Basic Info)
- Tab name "Features & Testing" is confusing (should be just "Testing")
- Missing "Quality Standards" field
- "Context Budget" field needs deprecation

### User Requirements

**Product UI Changes**:
1. Move "Core Features" from "Features & Testing" tab → "Basic Info" tab
2. Rename "Features & Testing" tab → "Testing" tab
3. Add new "Quality Standards" standalone field to Testing tab
4. Keep all other fields in their current locations

**Project UI Changes**:
1. Deprecate "Context Budget" field (mark as deprecated, keep in DB for now)
2. Create get_project() context tool for project metadata

**Context Tool Changes**:
1. Fix get_tech_stack.py to use config_data JSONB
2. Fix get_architecture.py to use config_data JSONB
3. Create get_product_context.py (Product Core badge)
4. Create get_project.py (Project Context badge)
5. Create get_testing.py (Testing badge)

---

## Technical Specification

### 1. Database Schema Changes

**Product Model** (`src/giljo_mcp/models/products.py`):
- **Add field**: `quality_standards` (Text, nullable=True)
- **Location**: Direct column (not JSONB) for easier querying
- **Default**: None
- **Purpose**: Capture quality standards for testing (new requirement)

**Project Model** (`src/giljo_mcp/models/projects.py`):
- **Deprecate field**: `context_budget` (keep column, mark as deprecated in docstring)
- **No deletion**: Field remains for backward compatibility
- **Migration**: Add deprecation comment only

**Migration File**:
```python
# Generated via: alembic revision --autogenerate -m "add_quality_standards_to_product"
def upgrade():
    op.add_column('products', sa.Column('quality_standards', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('products', 'quality_standards')
```

### 2. Context Tool Implementations

#### 2.1 Fix: get_tech_stack.py

**File**: `src/giljo_mcp/tools/context_tools/get_tech_stack.py`

**Current Bug** (lines 129-141):
```python
# ❌ WRONG - These fields don't exist
programming_languages = product.programming_languages
frameworks = product.frameworks
database = product.database
```

**Fixed Implementation**:
```python
# ✅ CORRECT - Access config_data JSONB
config_data = product.config_data or {}
tech_stack = config_data.get("tech_stack", {})

return {
    "programming_languages": tech_stack.get("languages", []),
    "frontend_frameworks": tech_stack.get("frontend", []),
    "backend_frameworks": tech_stack.get("backend", []),
    "databases": tech_stack.get("database", []),
    "infrastructure": tech_stack.get("infrastructure", []),
    "dev_tools": tech_stack.get("dev_tools", []),
}
```

**Test Coverage Required**:
- Test with empty config_data
- Test with partial tech_stack data
- Test with complete tech_stack data
- Test multi-tenant isolation

#### 2.2 Fix: get_architecture.py

**File**: `src/giljo_mcp/tools/context_tools/get_architecture.py`

**Current Bug** (line 119):
```python
# ❌ WRONG - Field doesn't exist
architecture_notes = product.architecture_notes
```

**Fixed Implementation**:
```python
# ✅ CORRECT - Access config_data JSONB
config_data = product.config_data or {}
architecture = config_data.get("architecture", {})

return {
    "primary_pattern": architecture.get("pattern", ""),
    "design_patterns": architecture.get("design_patterns", ""),
    "api_style": architecture.get("api_style", ""),
    "architecture_notes": architecture.get("notes", ""),
}
```

**Test Coverage Required**:
- Test with empty config_data
- Test with partial architecture data
- Test with complete architecture data
- Test depth parameter (overview vs detailed)

#### 2.3 New: get_product_context.py

**File**: `src/giljo_mcp/tools/context_tools/get_product_context.py`

**Purpose**: Fetch general product information (Product Core badge)

**Fields to Include**:
```python
return {
    "product_name": product.name,
    "product_description": product.description,
    "project_path": product.project_path,
    "core_features": config_data.get("features", {}).get("core", []),
    "is_active": product.is_active,
    "created_at": product.created_at.isoformat(),
}
```

**Parameters**:
- `product_id` (required)
- `tenant_key` (required)
- `include_metadata` (optional, default=False) - includes meta_data JSONB

**Test Coverage Required**:
- Test basic product fetch
- Test with metadata included
- Test multi-tenant isolation
- Test non-existent product

#### 2.4 New: get_project.py

**File**: `src/giljo_mcp/tools/context_tools/get_project.py`

**Purpose**: Fetch current project context (Project Context badge)

**Fields to Include**:
```python
return {
    "project_name": project.name,
    "project_alias": project.alias,
    "project_description": project.description,
    "orchestrator_mission": project.mission,
    "status": project.status,
    "staging_status": project.staging_status,
    "context_used": project.context_used,
    # NOTE: context_budget excluded (deprecated)
}
```

**Parameters**:
- `project_id` (required)
- `tenant_key` (required)
- `include_summary` (optional, default=False) - includes orchestrator_summary if completed

**Test Coverage Required**:
- Test active project fetch
- Test completed project with summary
- Test multi-tenant isolation
- Test non-existent project

#### 2.5 New: get_testing.py

**File**: `src/giljo_mcp/tools/context_tools/get_testing.py`

**Purpose**: Fetch testing strategy and quality standards (Testing badge)

**Fields to Include**:
```python
config_data = product.config_data or {}
test_config = config_data.get("test_config", {})

return {
    "quality_standards": product.quality_standards,  # New direct field
    "testing_strategy": test_config.get("strategy", ""),
    "coverage_target": test_config.get("coverage_target", 80),
    "testing_frameworks": test_config.get("frameworks", []),
    "test_commands": config_data.get("test_commands", []),
}
```

**Parameters**:
- `product_id` (required)
- `tenant_key` (required)

**Test Coverage Required**:
- Test with quality_standards set
- Test with empty test_config
- Test with complete test configuration
- Test multi-tenant isolation

### 3. Context Tool Registration

**File**: `src/giljo_mcp/tools/context.py`

**Add Registrations** (after line 1414):
```python
@mcp.tool()
async def fetch_product_context(
    product_id: str,
    tenant_key: str,
    include_metadata: bool = False,
) -> Dict[str, Any]:
    """
    Fetch general product information (Product Core).

    Returns product name, description, features, and metadata.
    """
    from .context_tools.get_product_context import get_product_context
    return await get_product_context(product_id, tenant_key, include_metadata, db_manager)

@mcp.tool()
async def fetch_project_context(
    project_id: str,
    tenant_key: str,
    include_summary: bool = False,
) -> Dict[str, Any]:
    """
    Fetch current project context.

    Returns project name, description, mission, status, and optional summary.
    """
    from .context_tools.get_project import get_project
    return await get_project(project_id, tenant_key, include_summary, db_manager)

@mcp.tool()
async def fetch_testing_config(
    product_id: str,
    tenant_key: str,
) -> Dict[str, Any]:
    """
    Fetch testing strategy and quality standards.

    Returns quality standards, strategy, coverage targets, and frameworks.
    """
    from .context_tools.get_testing import get_testing
    return await get_testing(product_id, tenant_key, db_manager)
```

**Update Log Statement** (line 1416):
```python
logger.info("Context and discovery tools registered (including 9 thin client context tools)")
```

### 4. Frontend Changes

#### 4.1 Product UI Reorganization

**File**: `frontend/src/views/ProductsView.vue`

**Changes**:
1. **Move "Core Features" Field** (lines 899-920):
   - Cut from "Features & Testing" tab
   - Paste into "Basic Info" tab (after Description field, around line 344)

2. **Rename Tab** (line 132):
   - Change: `{ title: 'Features & Testing', value: 4 }`
   - To: `{ title: 'Testing', value: 4 }`

3. **Add Quality Standards Field** (after line 899):
```vue
<v-textarea
  v-model="form.quality_standards"
  label="Quality Standards"
  placeholder="Define your quality standards (e.g., code review required, 80% coverage, zero critical bugs)"
  rows="4"
  :rules="[]"
  hint="Standalone field for quality expectations"
  persistent-hint
/>
```

4. **Update Form Data** (line 191):
```javascript
quality_standards: '',  // Add to form data
```

5. **Update Save Logic** (around line 1250):
```javascript
// Include quality_standards in payload
quality_standards: this.form.quality_standards || null,
```

#### 4.2 Project UI Deprecation

**File**: `frontend/src/views/ProjectsView.vue`

**Changes** (line 404-410):
1. **Add Deprecation Warning**:
```vue
<v-text-field
  v-model.number="editedProject.context_budget"
  label="Context Budget (Deprecated)"
  type="number"
  :rules="[rules.required, rules.positiveNumber]"
  hint="⚠️ Deprecated: This field will be removed in v4.0. Context is now managed via depth configuration."
  persistent-hint
  disabled
/>
```

2. **Disable Field**: Add `disabled` prop to prevent edits

#### 4.3 Depth Configuration Update

**File**: `frontend/src/components/settings/DepthConfiguration.vue`

**Add 3 New Depth Controls** (after line 180):
```vue
<!-- Product Context -->
<v-card class="mb-4">
  <v-card-title>Product Context</v-card-title>
  <v-card-text>
    <v-switch
      v-model="localConfig.product_context_enabled"
      label="Include product name, description, and core features"
      color="primary"
    />
  </v-card-text>
</v-card>

<!-- Project Context -->
<v-card class="mb-4">
  <v-card-title>Project Context</v-card-title>
  <v-card-text>
    <v-switch
      v-model="localConfig.project_context_enabled"
      label="Include current project name, description, and mission"
      color="primary"
    />
  </v-card-text>
</v-card>

<!-- Testing Configuration -->
<v-card class="mb-4">
  <v-card-title>Testing Configuration</v-card-title>
  <v-card-text>
    <v-switch
      v-model="localConfig.testing_config_enabled"
      label="Include quality standards, strategy, and frameworks"
      color="primary"
    />
  </v-card-text>
</v-card>
```

**Update Token Estimator** (`frontend/src/services/depthTokenEstimator.ts`):
```typescript
TOKEN_ESTIMATES = {
  // ... existing estimates ...
  product_context_enabled: { true: 500, false: 0 },
  project_context_enabled: { true: 300, false: 0 },
  testing_config_enabled: { true: 400, false: 0 },
}
```

### 5. Service Layer Updates

**File**: `src/giljo_mcp/services/product_service.py`

**Add Method** (after create_product):
```python
async def update_quality_standards(
    self,
    product_id: str,
    quality_standards: str,
    tenant_key: str,
) -> Dict[str, Any]:
    """
    Update quality standards for a product.

    Args:
        product_id: Product UUID
        quality_standards: Quality standards text
        tenant_key: Tenant isolation key

    Returns:
        Updated product data
    """
    async with self.db_manager.get_session() as session:
        product = await session.get(Product, product_id)

        if not product or product.tenant_key != tenant_key:
            raise ValueError(f"Product {product_id} not found")

        product.quality_standards = quality_standards
        await session.commit()

        return {"product_id": product_id, "quality_standards": quality_standards}
```

---

## Implementation Plan (TDD)

### Phase 1: Database Migration (Day 1)

**Red Phase**:
1. Write test: `test_quality_standards_field_exists`
2. Write test: `test_context_budget_deprecated_warning`
3. Run tests (should fail ❌)

**Green Phase**:
1. Add `quality_standards` column to Product model
2. Generate migration: `alembic revision --autogenerate -m "add_quality_standards_to_product"`
3. Run migration: `alembic upgrade head`
4. Run tests (should pass ✅)

**Refactor Phase**:
1. Add docstring deprecation warning to `context_budget`
2. Update model documentation

### Phase 2: Fix Existing Context Tools (Day 1-2)

**Red Phase**:
1. Write test: `test_get_tech_stack_from_config_data`
2. Write test: `test_get_architecture_from_config_data`
3. Write test: `test_tech_stack_empty_config_data`
4. Write test: `test_architecture_empty_config_data`
5. Run tests (should fail ❌)

**Green Phase**:
1. Fix `get_tech_stack.py` to use config_data JSONB
2. Fix `get_architecture.py` to use config_data JSONB
3. Run tests iteratively until GREEN ✅

**Refactor Phase**:
1. Extract common JSONB access pattern
2. Add structured logging
3. Update tool documentation

### Phase 3: Create New Context Tools (Day 2-3)

**Red Phase** (for each tool):
1. Write test: `test_get_product_context_basic`
2. Write test: `test_get_product_context_with_metadata`
3. Write test: `test_get_project_context_basic`
4. Write test: `test_get_project_context_with_summary`
5. Write test: `test_get_testing_config_basic`
6. Write test: `test_get_testing_config_empty`
7. Run tests (should fail ❌)

**Green Phase**:
1. Create `get_product_context.py`
2. Create `get_project.py`
3. Create `get_testing.py`
4. Register tools in `context.py`
5. Run tests iteratively until GREEN ✅

**Refactor Phase**:
1. Ensure all tools follow same pattern
2. Add consistent error handling
3. Add structured logging

### Phase 4: Frontend Changes (Day 3-4)

**Red Phase**:
1. Write E2E test: `test_features_field_in_basic_info_tab`
2. Write E2E test: `test_testing_tab_renamed`
3. Write E2E test: `test_quality_standards_field_exists`
4. Write E2E test: `test_context_budget_disabled`
5. Run tests (should fail ❌)

**Green Phase**:
1. Move Features field to Basic Info tab
2. Rename tab from "Features & Testing" to "Testing"
3. Add Quality Standards field
4. Disable Context Budget field
5. Run tests iteratively until GREEN ✅

**Refactor Phase**:
1. Extract tab components if ProductsView.vue becomes too large
2. Update form validation
3. Update save logic

### Phase 5: Depth Configuration (Day 4-5)

**Red Phase**:
1. Write test: `test_product_context_depth_control`
2. Write test: `test_project_context_depth_control`
3. Write test: `test_testing_config_depth_control`
4. Write test: `test_token_estimation_includes_new_tools`
5. Run tests (should fail ❌)

**Green Phase**:
1. Add 3 new depth controls to DepthConfiguration.vue
2. Update depthTokenEstimator.ts with new estimates
3. Update backend depth_config schema
4. Run tests iteratively until GREEN ✅

**Refactor Phase**:
1. Ensure consistent UI patterns
2. Update token estimates based on real data
3. Add tooltips and help text

### Phase 6: Integration Testing (Day 5)

**Red Phase**:
1. Write E2E test: `test_full_product_creation_with_new_fields`
2. Write E2E test: `test_orchestrator_fetches_all_9_context_tools`
3. Write E2E test: `test_depth_config_affects_context_fetch`
4. Run tests (should fail ❌)

**Green Phase**:
1. Fix any integration issues
2. Run tests iteratively until GREEN ✅

**Refactor Phase**:
1. Optimize database queries
2. Add caching where appropriate
3. Final code review

---

## Testing Requirements

### Unit Tests

**File**: `tests/unit/test_context_tools_refactor.py`
- `test_get_tech_stack_fixed` - Verifies config_data access
- `test_get_architecture_fixed` - Verifies config_data access
- `test_get_product_context_basic` - Basic fetch
- `test_get_product_context_metadata` - With metadata
- `test_get_project_context_basic` - Basic fetch
- `test_get_project_context_summary` - With summary
- `test_get_testing_config_complete` - All fields
- `test_get_testing_config_empty` - Empty config_data

**File**: `tests/unit/test_quality_standards.py`
- `test_quality_standards_field_exists`
- `test_quality_standards_nullable`
- `test_update_quality_standards_service`

### Integration Tests

**File**: `tests/integration/test_context_tools_integration.py`
- `test_all_9_context_tools_registered`
- `test_tech_stack_returns_config_data`
- `test_architecture_returns_config_data`
- `test_product_context_multi_tenant_isolation`
- `test_project_context_multi_tenant_isolation`
- `test_testing_config_multi_tenant_isolation`

### E2E Tests (Frontend)

**File**: `frontend/tests/e2e/test_product_ui_refactor.spec.js`
- `test_features_moved_to_basic_info`
- `test_testing_tab_renamed`
- `test_quality_standards_field_visible`
- `test_product_creation_saves_quality_standards`

**File**: `frontend/tests/e2e/test_project_ui_refactor.spec.js`
- `test_context_budget_disabled`
- `test_context_budget_shows_deprecation_warning`

### Coverage Target

- Unit tests: >85% for new/changed code
- Integration tests: >80% for context tools
- E2E tests: Cover all UI changes

---

## Rollback Plan

If issues arise during implementation:

1. **Database Rollback**:
   ```bash
   alembic downgrade -1  # Revert quality_standards column
   ```

2. **Code Rollback**:
   - Revert context tool fixes via git
   - Remove new context tool files
   - Revert context.py registration changes

3. **Frontend Rollback**:
   - Revert ProductsView.vue changes (git)
   - Revert ProjectsView.vue changes (git)
   - Revert DepthConfiguration.vue changes (git)

**Rollback Decision Criteria**:
- If >20% of tests fail after implementation
- If performance degrades significantly
- If critical bugs discovered in production

---

## Success Criteria

✅ All 2 bugs fixed (get_tech_stack, get_architecture)
✅ All 3 new context tools created and tested
✅ Product UI reorganized (Features moved, Testing renamed, Quality Standards added)
✅ Project UI updated (Context Budget deprecated)
✅ Depth configuration updated with 3 new controls
✅ All tests passing (>80% coverage)
✅ Migration successful (no rogue migrations)
✅ Documentation updated
✅ Backend starts without errors
✅ Frontend builds without errors

---

## Dependencies

- ✅ Handover 0314 (Depth Configuration) - Complete
- ✅ Handover 0315 (MCP Thin Client) - Complete
- ✅ Service Layer Pattern - Established
- ✅ Multi-Tenant Isolation - Established
- ✅ Migration Methodology - Established

---

## Notes for Implementer

1. **Follow TDD Strictly**: Write tests FIRST, then implement
2. **Reuse Patterns**: Look at existing context tools for patterns
3. **Service Layer**: All business logic in services, not endpoints
4. **Multi-Tenant**: Always filter by tenant_key
5. **JSONB Access**: Use `.get()` with defaults to avoid KeyError
6. **Cross-Platform**: Use pathlib.Path for any file operations
7. **Structured Logging**: Include context in all log messages
8. **Backward Compatibility**: Don't delete context_budget column
9. **Migration**: Use `--autogenerate`, never manual migrations
10. **Code Review**: Reference 013A architecture status document

---

## Post-Implementation

After completing this handover:

1. Update CLAUDE.md with handover completion
2. Create devlog entry documenting changes
3. Update API documentation (if endpoints changed)
4. Test with real orchestrator workflows
5. Monitor for any performance issues
6. Prepare for Handover 0318 (Documentation Update)

---

**Handover Created**: 2025-11-17
**Ready for**: Implementation by TDD-focused agent
**Estimated Completion**: 5 days
**Risk Level**: Medium (UI changes + database migration)
