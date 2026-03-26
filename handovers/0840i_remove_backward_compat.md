# Handover 0840i: Remove All Backward Compatibility Layers

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Audit)
**To Agent:** Next Session (tdd-implementor + ux-designer)
**Priority:** Critical
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Remove ALL backward compatibility / legacy reconstruction code added by the 0840 series. The user explicitly wants ONE clean path — no dual systems, no legacy dict reconstruction. The application will be reinstalled fresh, so there is no migration compatibility concern. Agents building on this codebase must only see the normalized table structure.

**Branch:** `feature/0840-jsonb-normalization`

## Context

The 0840 series normalized JSONB into relational tables but preserved backward compatibility by reconstructing the old dict/array structures in API responses and accepting them on input. This creates a dual system where future agents will see both patterns and build dependencies on the legacy one. The user wants this removed entirely.

## Technical Details

### PART 1: Product config_data Reconstruction (REMOVE)

**Backend API — Stop reconstructing config_data dict:**

1. `api/endpoints/products/crud.py` lines 54-87, 111-112 — `_build_product_response()` reconstructs `config_data` dict from normalized tables. REPLACE with direct exposure of normalized fields:
   ```
   Instead of: config_data: {tech_stack: {languages: "...", ...}, architecture: {...}}
   Return:     tech_stack: {programming_languages: "...", frontend_frameworks: "...", ...}
               architecture: {primary_pattern: "...", ...}
               test_config: {quality_standards: "...", ...}
               core_features: "..."
   ```

2. `api/endpoints/products/lifecycle.py` lines 48-84, 107-108 — DUPLICATE `_build_product_response()`. Same change. Consider extracting a shared helper to avoid duplication.

3. `api/endpoints/products/models.py` — Replace schemas:
   - `ProductCreate`: Remove `config_data: Optional[dict]`. Add typed fields for each table (tech_stack, architecture, test_config as Pydantic models)
   - `ProductUpdate`: Same
   - `ProductResponse`: Remove `config_data: Optional[dict]` and `has_config_data: bool`. Add typed sub-models for tech_stack, architecture, test_config, and a `core_features: Optional[str]` field

**Backend Service — Stop splitting config_data dict:**

4. `src/giljo_mcp/services/product_service.py`:
   - `_create_config_relations()` (lines 141-179) — Remove the legacy field mapping (e.g., `languages` → `programming_languages`). Accept the canonical column names directly.
   - `_update_config_relations()` (lines 181-219) — Same cleanup
   - `create_product()` (lines 288-313) — Accept `core_features` directly, not extracted from `config_data["features"]["core"]`
   - `update_product()` (lines 514-521) — Accept `core_features` directly

**Frontend — Send/receive normalized structure:**

5. `frontend/src/components/products/ProductForm.vue`:
   - `saveProduct()` (line 946) — Send `tech_stack: {...}`, `architecture: {...}`, `test_config: {...}`, `core_features: "..."` as separate fields, NOT wrapped in `config_data` dict
   - `loadProductData()` (line 1036+) — Read from `product.tech_stack`, `product.architecture`, etc., NOT from `product.config_data`
   - Form field bindings should map directly to the normalized field names (e.g., `programming_languages` not `languages`)

6. `frontend/src/components/products/ProductDetailsDialog.vue` (lines 224-309):
   - Display from `product.tech_stack.programming_languages` instead of `product.config_data.tech_stack.languages`
   - Display from `product.architecture.primary_pattern` instead of `product.config_data.architecture.pattern`
   - Use `product.core_features` instead of `product.config_data.features.core`
   - Use `product.test_config.quality_standards` instead of `product.config_data.test_config.quality_standards`
   - Replace `v-if="product.has_config_data"` with `v-if="product.tech_stack || product.architecture || product.test_config"`

### PART 2: Message Backward Compatibility (REMOVE)

**API Schema:**

7. `api/endpoints/messages.py`:
   - Line 34: Remove `to_agent: Optional[str] = None` compat field from MessageResponse
   - Line 33: Keep `recipients: list[str]` (the new clean field name)
   - Rename `to_agents` to `recipients` everywhere in schemas for clarity

**Service Layer:**

8. `src/giljo_mcp/services/message_service.py`:
   - Line 1462-1463: Remove `to_agents` array reconstruction from junction table. Instead, return `recipients` as a list of recipient objects or IDs directly from the relationship
   - Line 1265: Remove single-agent `acknowledged_by` extraction. Return `acknowledgments` as a list from the relationship
   - Line 1572, 1586: `completed_by` in response models is fine as a scalar (it's the agent who completed it, not a legacy array)

**Frontend Messages:**

9. `frontend/src/stores/messages.js`:
   - Line 31, 61, 76-81: Update to use `recipients` instead of `to_agents`, `acknowledgments` instead of `acknowledged_by`

10. `frontend/src/services/api.js` line 329: Update message send payload to use `recipients` instead of `to_agents`

11. `frontend/src/types/message.ts` line 10: Update type definition

### PART 3: Field Name Harmonization

The old `config_data` used short names (`languages`, `frontend`, `backend`, `database`, `pattern`, `notes`). The new tables use descriptive names (`programming_languages`, `frontend_frameworks`, `backend_frameworks`, `databases_storage`, `primary_pattern`, `architecture_notes`).

**Remove ALL short-name mappings.** The canonical names are the column names on the normalized tables. Frontend forms should use these names directly.

## Implementation Plan

### Phase 1: Define Clean Pydantic Schemas
Create typed schemas for the normalized structure:
```python
class TechStackSchema(BaseModel):
    programming_languages: Optional[str] = None
    frontend_frameworks: Optional[str] = None
    backend_frameworks: Optional[str] = None
    databases_storage: Optional[str] = None
    infrastructure: Optional[str] = None
    dev_tools: Optional[str] = None
    target_windows: bool = False
    target_linux: bool = False
    target_macos: bool = False
    target_android: bool = False
    target_ios: bool = False
    target_cross_platform: bool = False

class ArchitectureSchema(BaseModel):
    primary_pattern: Optional[str] = None
    design_patterns: Optional[str] = None
    api_style: Optional[str] = None
    architecture_notes: Optional[str] = None

class TestConfigSchema(BaseModel):
    quality_standards: Optional[str] = None
    test_strategy: Optional[str] = None
    coverage_target: int = 80
    testing_frameworks: Optional[str] = None
```

### Phase 2: Update Backend API
1. Replace response builders in crud.py and lifecycle.py
2. Update ProductCreate/Update/Response schemas
3. Clean product_service.py input handling

### Phase 3: Update Frontend
1. ProductForm.vue — send/receive normalized fields
2. ProductDetailsDialog.vue — display normalized fields
3. Messages components — use recipients/acknowledgments

### Phase 4: Clean Message API
1. Update message schemas
2. Remove compat fields
3. Update frontend message handling

### Phase 5: Test Updates
1. Update all product API tests
2. Update all message API tests
3. Run full suite

## Success Criteria

- [ ] No `config_data` dict anywhere in API requests or responses
- [ ] No `to_agents` or `to_agent` compat fields — only `recipients`
- [ ] No `acknowledged_by` legacy field — only `acknowledgments`
- [ ] No legacy field name mappings (languages → programming_languages etc.)
- [ ] Frontend sends/receives normalized field names directly
- [ ] All tests pass
- [ ] `ruff check src/ api/` clean
- [ ] Committed to `feature/0840-jsonb-normalization`

## Reporting

Write results to `prompts/0840_chain/0840i_results.json`

## Coding Principles

- ONE way to do things — no compat layers, no dual paths
- Clean Code: DELETE compat code completely
- Tenant isolation maintained
- TDD for new schema validation
