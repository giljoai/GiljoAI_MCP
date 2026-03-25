# Handover 0840c: Product Config Normalization

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Planning Session)
**To Agent:** Next Session (database-expert + tdd-implementor + ux-designer)
**Priority:** Critical
**Estimated Complexity:** 12-16 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Replace the `Product.config_data` JSONB column with proper relational tables: `product_tech_stacks`, `product_architectures`, `product_test_configs`. Move `core_features` to the `products` table directly. Add new `target_platform` boolean fields. Rename the UI tab from "Basic Info" to "Product Info". Remove 6 ghost config keys that are referenced but never written.

**Prerequisite:** Handover 0840b (Message Normalization) must be complete. Check chain log.

## Context and Background

`Product.config_data` is a JSONB column storing a fixed-schema nested dict with 14 known leaf fields across 4 groups. It was designed for flexibility but the schema has been stable since October 2025. The user has confirmed the category-level toggle design: users toggle entire categories on/off (e.g., "Tech Stack" toggles ALL tech stack fields). Individual fields exist for documentation granularity during data entry, not for independent retrieval.

### Current config_data Structure (Being Replaced)
```json
{
  "tech_stack": { "languages": "", "frontend": "", "backend": "", "database": "", "infrastructure": "" },
  "architecture": { "pattern": "", "design_patterns": "", "api_style": "", "notes": "" },
  "features": { "core": "" },
  "test_config": { "strategy": "", "coverage_target": 80, "frameworks": "", "quality_standards": "" }
}
```

### Also Being Removed
- `Product.product_memory` JSONB — Verify current usage. `sequential_history` was already migrated to `product_memory_entries` (Handover 0390a). What remains (git integration config, context) should be assessed.
- `Product.tuning_state` JSONB — Used by tuning service. Assess whether this should be normalized or kept.

## Technical Details

### New Schema

```sql
-- Move core_features to products table
ALTER TABLE products ADD COLUMN core_features TEXT;
-- Backfill from config_data->>'features'->>'core'

-- Product Tech Stacks (1:1 with products)
CREATE TABLE product_tech_stacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    tenant_key VARCHAR(255) NOT NULL,
    programming_languages TEXT,
    frontend_frameworks TEXT,
    backend_frameworks TEXT,
    databases_storage TEXT,
    target_windows BOOLEAN DEFAULT FALSE,
    target_linux BOOLEAN DEFAULT FALSE,
    target_macos BOOLEAN DEFAULT FALSE,
    target_android BOOLEAN DEFAULT FALSE,
    target_ios BOOLEAN DEFAULT FALSE,
    target_cross_platform BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_product_tech_stacks_product ON product_tech_stacks(product_id);
CREATE INDEX idx_product_tech_stacks_tenant ON product_tech_stacks(tenant_key);

-- Product Architectures (1:1 with products)
CREATE TABLE product_architectures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    tenant_key VARCHAR(255) NOT NULL,
    primary_pattern TEXT,
    design_patterns TEXT,
    api_style TEXT,
    architecture_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_product_architectures_product ON product_architectures(product_id);
CREATE INDEX idx_product_architectures_tenant ON product_architectures(tenant_key);

-- Product Test Configs (1:1 with products)
CREATE TABLE product_test_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    tenant_key VARCHAR(255) NOT NULL,
    quality_standards TEXT,
    test_strategy VARCHAR(50),
    coverage_target INTEGER DEFAULT 80,
    testing_frameworks TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_product_test_configs_product ON product_test_configs(product_id);
CREATE INDEX idx_product_test_configs_tenant ON product_test_configs(tenant_key);
```

### UI Tab Rename

The current "Basic Info" tab in `ProductForm.vue` must be renamed to **"Product Info"**. This harmonizes with the context menu label. The tab contains: product name, codebase folder path, product description, and core product features.

**IMPORTANT:** "Product Info" category is ALWAYS ON — it cannot be toggled off. The `user_field_priorities` table (created in 0840d) will NOT have a row for product_info. In the frontend, this toggle should appear locked/disabled with a badge reading "Always On".

### Files That Must Change

**Models:**
- `src/giljo_mcp/models/products.py` — Add `core_features` to Product, create ProductTechStack, ProductArchitecture, ProductTestConfig models. Remove `config_data` column.
- Remove `get_config_field()` method from Product model

**Services:**
- `src/giljo_mcp/services/product_service.py` — Rewrite create/update product to write to related tables
- `src/giljo_mcp/services/product_tuning_service.py` — MAJOR REWRITE: Currently reads/writes `config_data` deeply. Must use related tables instead.
- `src/giljo_mcp/context_manager.py` — Remove ROLE_CONFIG_FILTERS ghost keys, rewrite `get_full_config`, `get_filtered_config`, `get_config_summary` to query related tables
- `src/giljo_mcp/thin_prompt_generator.py` — Update config reads to use related tables

**Tools:**
- `src/giljo_mcp/tools/context_tools/get_tech_stack.py` — Query `product_tech_stacks` table
- `src/giljo_mcp/tools/context_tools/get_architecture.py` — Query `product_architectures` table
- `src/giljo_mcp/tools/context_tools/get_testing.py` — Query `product_test_configs` table
- `src/giljo_mcp/tools/context_tools/get_product_context.py` — Update to use related tables

**Frontend:**
- `frontend/src/components/products/ProductForm.vue` — Restructure form to write to separate endpoints/objects per category. Rename "Basic Info" tab to "Product Info". Add target platform toggle switches (Windows, Linux, macOS, Android, iOS, Cross-Platform).
- `frontend/src/components/products/ProductDetailsDialog.vue` — Read from new structure
- `frontend/src/stores/products.js` — Update store to handle related table data

**API:**
- Product create/update endpoints — Accept nested structure and write to related tables
- Product read endpoints — Include related table data in response

### Migration Data Backfill

```sql
-- Backfill core_features
UPDATE products SET core_features = config_data->'features'->>'core' WHERE config_data IS NOT NULL;

-- Backfill product_tech_stacks
INSERT INTO product_tech_stacks (product_id, tenant_key, programming_languages, frontend_frameworks, backend_frameworks, databases_storage)
SELECT id, tenant_key,
  config_data->'tech_stack'->>'languages',
  config_data->'tech_stack'->>'frontend',
  config_data->'tech_stack'->>'backend',
  config_data->'tech_stack'->>'database'
FROM products WHERE config_data IS NOT NULL AND config_data->'tech_stack' IS NOT NULL;

-- Backfill product_architectures
INSERT INTO product_architectures (product_id, tenant_key, primary_pattern, design_patterns, api_style, architecture_notes)
SELECT id, tenant_key,
  config_data->'architecture'->>'pattern',
  config_data->'architecture'->>'design_patterns',
  config_data->'architecture'->>'api_style',
  config_data->'architecture'->>'notes'
FROM products WHERE config_data IS NOT NULL AND config_data->'architecture' IS NOT NULL;

-- Backfill product_test_configs
INSERT INTO product_test_configs (product_id, tenant_key, quality_standards, test_strategy, coverage_target, testing_frameworks)
SELECT id, tenant_key,
  config_data->'test_config'->>'quality_standards',
  config_data->'test_config'->>'strategy',
  COALESCE((config_data->'test_config'->>'coverage_target')::integer, 80),
  config_data->'test_config'->>'frameworks'
FROM products WHERE config_data IS NOT NULL AND config_data->'test_config' IS NOT NULL;
```

### Product.product_memory and Product.tuning_state Assessment

**Before dropping these, the agent MUST verify:**
1. `product_memory` — What keys remain after `sequential_history` was migrated out? If only `git_integration` config remains, consider a `product_git_config` column or table.
2. `tuning_state` — This is actively used by `product_tuning_service.py`. It stores `{last_tuned_at, last_tuned_at_sequence, pending_proposals}`. Decide: keep as JSONB (it's a legitimate config blob), or normalize `pending_proposals` into a table.

**Decision guideline:** If the tuning service is the only reader/writer and the data is small + rarely queried in WHERE clauses, keeping JSONB is acceptable. Document the decision in chain log.

## Implementation Plan

### Phase 1: Database Migration
1. Create Alembic migration with idempotency guards
2. Add `core_features` column to products
3. Create 3 related tables
4. Backfill data
5. Drop `config_data` column (after all code updated)

### Phase 2: Model Updates
1. Create new SQLAlchemy models with relationships
2. Update Product model (add core_features, relationships, remove config_data)
3. Remove `get_config_field()` method

### Phase 3: Service Layer Rewrite
1. Product creation: create related table rows
2. Product update: update related table rows
3. Context manager: query related tables
4. Tuning service: adapt to new structure
5. Context tools: query specific related tables

### Phase 4: Frontend Updates
1. ProductForm.vue: restructure tabs, rename "Basic Info" → "Product Info", add platform toggles
2. ProductDetailsDialog.vue: read from new structure
3. Store: handle related table data

### Phase 5: Test Rewrite
**Files requiring REWRITE:**
- `tests/services/test_product_tuning_service.py` (25 tests)
- `tests/integration/test_product_service_integration_features.py` (9 tests)
- `tests/unit/test_context_manager_validation.py` (14 tests)
- `tests/unit/test_context_manager_config.py` (15 tests)
- `tests/unit/test_populate_config_data.py` (23 tests)
- `tests/unit/test_project_closeout_repository.py` (6 tests)

**Files requiring UPDATE:**
- Multiple test files with product fixtures containing `config_data`

### Phase 6: Verify
1. `ruff check src/ api/` clean
2. All tests pass
3. No remaining `config_data` references (grep to confirm)
4. Frontend product form works: create, edit, view
5. Context tools return correct data from new tables

## CRITICAL: Tenant Isolation

Every new table MUST include `tenant_key`. Every query MUST filter by `tenant_key`. Products → related tables must cascade correctly.

## Success Criteria

- [ ] 3 related tables created (product_tech_stacks, product_architectures, product_test_configs)
- [ ] `core_features` column on products table
- [ ] `config_data` JSONB column dropped from products
- [ ] 6 target platform booleans on product_tech_stacks
- [ ] "Basic Info" tab renamed to "Product Info"
- [ ] Ghost config keys removed from context_manager.py
- [ ] Tuning service adapted to new structure
- [ ] All context tools query related tables
- [ ] All tests pass
- [ ] `ruff check` clean
- [ ] Committed to `feature/0840-jsonb-normalization`

## Rollback Plan

`alembic downgrade -1`. Git revert.

## Coding Principles (from HANDOVER_INSTRUCTIONS.md)

- TDD: Write tests FIRST for new table operations
- Clean Code: DELETE config_data entirely, no dual-read patterns
- Tenant isolation: EVERY query filters by tenant_key
- No function exceeds 200 lines, no class exceeds 1000 lines
- Search before you build: Use existing ProductService patterns
- Trace full chain: model → repository → service → tool → endpoint → frontend → test

## STOP CONDITIONS

If any of these occur, STOP and document in chain log for user review:
- `product_memory` contains data beyond git_integration that is actively needed
- `tuning_state` normalization would break the tuning flow in non-obvious ways
- Frontend restructuring reveals undocumented component dependencies

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0840_chain/chain_log.json`. Verify 0840b status is `complete`. Read 0840b `notes_for_next`.

### Step 2: Mark Session Started
Update session 0840c: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Use database-expert for migration, tdd-implementor for service rewrite, ux-designer for frontend.

### Step 4: Update Chain Log

### Step 5: Commit Work
```bash
git add -A
git commit -m "feat: Normalize Product config — relational tables replace config_data JSONB (0840c)"
```

### Step 6: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0840d - User Settings Normalization\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0840d. READ FIRST: F:\GiljoAI_MCP\handovers\0840d_user_settings_normalization.md then READ: F:\GiljoAI_MCP\prompts\0840_chain\0840d_prompt.md for chain instructions. You are on branch feature/0840-jsonb-normalization. Use database-expert and tdd-implementor subagents.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
