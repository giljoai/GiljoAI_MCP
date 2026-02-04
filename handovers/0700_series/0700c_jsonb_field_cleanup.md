# Handover 0700c: JSONB Field Cleanup

## Context

**Decision**: Pre-release cleanup - remove deprecated JSONB columns and fields before v1.0.

**Rationale**:
- `AgentExecution.messages` JSONB array replaced by counter columns (Handover 0387i)
- `Product.product_memory.sequential_history` JSONB array replaced by `product_memory_entries` table (Handover 0390)
- No external users exist - safe to purge deprecated data structures

**Reference**: Strategic direction change documented in `dead_code_audit.md` (2026-02-04)

## Scope

Remove two major deprecated JSONB columns and migrate code to use replacement systems.

### Affected Columns

**1. AgentExecution.messages** (Line 293-302 in models/agent_identity.py)
- **DEPRECATED**: Handover 0387i
- **Replacement**: `messages_sent_count`, `messages_waiting_count`, `messages_read_count` (counter columns)
- **Current state**: Column exists but marked deprecated, code should not write to it
- **Action**: DROP COLUMN entirely

**2. Product.product_memory JSONB** (Partial - Line 120-127 in models/products.py)
- **DEPRECATED field**: `sequential_history` array within JSONB
- **Replacement**: `product_memory_entries` table with proper foreign keys (Handover 0390)
- **Current state**: JSONB column contains `{"github": {}, "sequential_history": [], "context": {}}`
- **Action**: Keep JSONB column but remove `sequential_history` field, update server_default

**Note**: We're NOT removing the entire `product_memory` JSONB column because `git_integration` config is still in use per CLAUDE.md.

## Tasks

### Phase 1: Remove AgentExecution.messages Column

1. [ ] Remove model definition (src/giljo_mcp/models/agent_identity.py):
   - Delete lines 293-302 (messages column + comments)
   - Verify counter columns remain (lines 304-322)

2. [ ] Search for code writing to messages JSONB:
   ```bash
   grep -r "\.messages\s*=" src/ api/
   grep -r "execution\.messages" src/ api/
   grep -r "agent\.messages" src/ api/
   grep -r "JSONB.*messages" src/ api/
   ```

3. [ ] Remove deprecated methods from MessageService (src/giljo_mcp/services/message_service.py):
   - Section at line 1283 marked "# DEPRECATED: JSONB Persistence Methods (Handover 0387f)"
   - Search file for methods writing to JSONB and remove them
   - Keep counter-based methods only

4. [ ] Update baseline migration:
   - Remove `messages` column from `agent_executions` table definition
   - Ensure counter columns are defined

### Phase 2: Clean Product.product_memory JSONB Field

5. [ ] Update Product model (src/giljo_mcp/models/products.py):
   - Line 122: Change server_default from:
     ```python
     server_default=text("'{\"github\": {}, \"sequential_history\": [], \"context\": {}}'::jsonb")
     ```
     To:
     ```python
     server_default=text("'{\"github\": {}, \"context\": {}}'::jsonb")
     ```
   - Lines 123-126: Update comment to remove sequential_history mention:
     ```python
     comment="Product memory storage. NOTE: Only 'git_integration' config remains in use. "
         "See product_memory_entries table for project history (Handover 0390)."
     ```

6. [ ] Search for code reading sequential_history:
   ```bash
   grep -r "sequential_history" src/ api/
   grep -r "product_memory\[" src/ api/
   ```

7. [ ] Remove deprecated methods from ProductService (src/giljo_mcp/services/product_service.py):
   - Line 1717-1743: `_validate_history_entry()` - Marked DEPRECATED (Handover 0390d)
   - Line 1759-1801: `add_learning_to_product_memory()` - Marked DEPRECATED (Handover 0390d)
   - Both methods write to JSONB which is deprecated - delete entirely

8. [ ] Verify ProductMemoryRepository usage:
   - Ensure all code uses `ProductMemoryRepository.create_entry()` instead of JSONB writes
   - Check MCP tools: `close_project_and_update_memory()`, `write_360_memory()`

### Phase 3: Code Migration

9. [ ] Update any remaining JSONB field access:
   - If code reads `product.product_memory.get("sequential_history", [])`, replace with database query:
     ```python
     entries = await ProductMemoryRepository.get_entries_by_product(session, product.id)
     ```
   - If code writes to JSONB, migrate to table insert:
     ```python
     await ProductMemoryRepository.create_entry(session, product_id, entry_data)
     ```

10. [ ] Update baseline migration:
    - Change `product_memory` JSONB default value to exclude `sequential_history`

### Phase 4: Verification

11. [ ] Grep verification:
    ```bash
    # Should return ZERO results (except in comments):
    grep -r "execution\.messages\s*\[" src/ api/
    grep -r "sequential_history" src/ api/ | grep -v "Handover\|DEPRECATED\|#"

    # Should return results (counter columns still in use):
    grep -r "messages_sent_count" src/ api/
    grep -r "ProductMemoryRepository" src/ api/
    ```

12. [ ] Test JSONB field access:
    ```python
    # In a test file or python shell:
    from src.giljo_mcp.models import Product
    product = Product(name="Test", product_memory={})
    assert "sequential_history" not in product.product_memory
    assert "github" in product.product_memory  # Still valid
    ```

## Verification

- [ ] Model imports succeed without errors
- [ ] Fresh install creates correct schema (no messages column, clean product_memory default)
- [ ] Grep shows zero JSONB writes to deprecated fields
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Database schema inspection confirms:
  ```bash
  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d agent_executions" | grep messages
  # Should show counter columns only, not JSONB column

  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT column_default FROM information_schema.columns WHERE table_name='products' AND column_name='product_memory';"
  # Should show: '{"github": {}, "context": {}}'::jsonb
  ```

## Risk Assessment

**RISK: HIGH** - Database schema changes affecting core data structures

**Mitigation**:
- Counter columns already implemented and tested (Handover 0387)
- ProductMemoryRepository already implemented and tested (Handover 0390)
- Baseline migration approach ensures clean schema
- Comprehensive grep ensures all JSONB access is found
- Test suite validates message and memory systems work without JSONB

**Rollback Plan**:
- Git revert commit
- Restore JSONB columns from git history
- Re-run fresh install

## Dependencies

- **Depends on**: 0700b (clean schema baseline established)
- **Blocks**: None (independent from other cleanups)

## Estimated Impact

- **Lines removed**: ~150 lines
  - AgentExecution.messages column: ~10 lines
  - MessageService JSONB methods: ~80 lines
  - ProductService deprecated methods: ~50 lines
  - Product.product_memory updates: ~10 lines
- **Files modified**: 4 (2 models, 2 services)
- **Migration changes**: server_default update for products table
- **Test updates**: Remove tests for deprecated JSONB methods

## Notes

- **DO NOT** remove entire `Product.product_memory` JSONB column - `git_integration` config still uses it
- **DO** remove `AgentExecution.messages` JSONB column entirely - fully replaced by counters
- **DO** remove `sequential_history` field from product_memory JSONB - fully replaced by table
- CLAUDE.md documents both deprecations (lines referencing 0387i and 0390)
