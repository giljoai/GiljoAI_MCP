# Handover 0700c: JSONB Field Cleanup - Kickoff Prompt

**Date**: 2026-02-04
**Series**: 0700 Code Cleanup Series (Handover 5 of ~20)
**Mission**: Purge two deprecated JSONB data structures before v1.0 release
**Estimated Time**: 2-3 hours

---

## Series Context

You are executing handover **0700c** in the 0700 Code Cleanup Series, a pre-release purge operation to ship clean v1.0 code.

**Completed Handovers** (4/~20):
- ✅ **0700a** - Light mode removal (145 lines)
- ✅ **0700** - Cleanup index creation (75 entries cataloged)
- ✅ **0701** - Dependency visualization (458 files, 763 edges mapped)
- ✅ **0700d** - Legacy succession system purge (~750 lines)
- ✅ **0700b** - Database schema purge (7 columns, ~1,000 lines)

**Your Dependencies** (SATISFIED):
- ✅ 0700b complete - Removed succession columns (succeeded_by, succession_reason, handover_summary, decommissioned_at)
- ✅ 0700d complete - Deleted orchestrator_succession.py module

**Critical Context from 0700b**:
- This is a **PURGE operation**, not a migration
- Delete the column/field AND all code that uses it
- No external users exist - we can break things and git revert
- Fresh installs will work because baseline migration won't include removed columns
- 0700b removed ~1,000 lines successfully using this approach

---

## Mission Scope

Remove two major deprecated JSONB columns/fields that were replaced by normalized systems in prior handovers.

### Target 1: AgentExecution.messages JSONB Column (FULL REMOVAL)

**Deprecated**: Handover 0387i
**Replacement**: Counter columns (`messages_sent_count`, `messages_waiting_count`, `messages_read_count`)
**Action**: DROP COLUMN entirely + delete all code that reads/writes to it

**Location**: `src/giljo_mcp/models/agent_identity.py` lines 293-302

**What to Delete**:
1. Column definition from model
2. All code writing to `execution.messages` JSONB
3. Deprecated JSONB persistence methods in MessageService (line ~1283)
4. Any API responses that include messages array
5. Column definition from baseline migration

**What to KEEP**:
- Counter columns (lines 304-322 in agent_identity.py)
- Counter-based methods in MessageService

---

### Target 2: Product.product_memory.sequential_history Field (PARTIAL REMOVAL)

**Deprecated**: Handover 0390
**Replacement**: `product_memory_entries` table with proper foreign keys
**Action**: Remove `sequential_history` field from JSONB, keep column for `git_integration` config

**Location**: `src/giljo_mcp/models/products.py` lines 120-127

**What to Delete**:
1. `sequential_history` field from JSONB server_default (NOT the entire column)
2. All code reading/writing `product.product_memory["sequential_history"]`
3. Deprecated service methods:
   - `ProductService._validate_history_entry()` (lines 1717-1743)
   - `ProductService.add_learning_to_product_memory()` (lines 1759-1801)

**What to KEEP**:
- `Product.product_memory` JSONB column itself (still stores `git_integration` config)
- `ProductMemoryRepository` and normalized table system

---

## High-Risk Files (Handle with Care)

From 0701 dependency analysis, these files have 20+ dependents:

1. **src/giljo_mcp/models/agent_identity.py** - 32 dependents (CRITICAL)
2. **src/giljo_mcp/models/products.py** - Handle partial JSONB cleanup carefully

**Strategy**: Remove columns/fields cleanly, verify imports still work after changes.

---

## Phase-by-Phase Execution

### Phase 1: AgentExecution.messages Column Purge (60 min)

**Step 1.1: Verify Counter System (5 min)**
```bash
# Confirm counter columns are still present and working
grep -r "messages_sent_count\|messages_waiting_count\|messages_read_count" src/giljo_mcp/models/agent_identity.py
```

**Step 1.2: Find All JSONB Writes (10 min)**
```bash
# Search for code writing to messages JSONB
grep -r "\.messages\s*=" src/ api/
grep -r "execution\.messages\[" src/ api/
grep -r "agent\.messages" src/ api/
```

**Step 1.3: Remove Model Column (5 min)**
- Delete lines 293-302 in `src/giljo_mcp/models/agent_identity.py`
- Verify counter columns remain (lines 304-322)

**Step 1.4: Remove Deprecated MessageService Methods (20 min)**
- Open `src/giljo_mcp/services/message_service.py`
- Find section marked "DEPRECATED: JSONB Persistence Methods (Handover 0387f)" at line ~1283
- Delete all JSONB persistence methods
- Keep counter-based methods only

**Step 1.5: Update Baseline Migration (10 min)**
- Open `migrations/versions/baseline_v32_unified.py`
- Remove `messages` column from `agent_executions` table definition
- Ensure counter columns are defined

**Step 1.6: Verify Removal (10 min)**
```bash
# Should return ZERO results (except in comments):
grep -r "execution\.messages\s*\[" src/ api/
grep -r "agent\.messages\[" src/ api/

# Should return results (counter columns still in use):
grep -r "messages_sent_count" src/ api/
```

---

### Phase 2: Product.product_memory.sequential_history Field Cleanup (45 min)

**Step 2.1: Update Model server_default (10 min)**
- Open `src/giljo_mcp/models/products.py` line 122
- Change server_default from:
  ```python
  server_default=text("'{\"github\": {}, \"sequential_history\": [], \"context\": {}}'::jsonb")
  ```
  To:
  ```python
  server_default=text("'{\"github\": {}, \"context\": {}}'::jsonb")
  ```
- Update comment (lines 123-126) to remove sequential_history mention

**Step 2.2: Find All sequential_history Reads (10 min)**
```bash
grep -r "sequential_history" src/ api/
grep -r "product_memory\[" src/ api/
```

**Step 2.3: Remove Deprecated ProductService Methods (15 min)**
- Open `src/giljo_mcp/services/product_service.py`
- Delete lines 1717-1743: `_validate_history_entry()` (marked DEPRECATED Handover 0390d)
- Delete lines 1759-1801: `add_learning_to_product_memory()` (marked DEPRECATED Handover 0390d)

**Step 2.4: Verify ProductMemoryRepository Usage (10 min)**
- Ensure all code uses `ProductMemoryRepository.create_entry()` instead of JSONB writes
- Check MCP tools: `close_project_and_update_memory()`, `write_360_memory()`
- Verify they use the repository pattern

---

### Phase 3: Code Migration (30 min)

**Step 3.1: Update Any Remaining JSONB Access (15 min)**

If code reads `product.product_memory.get("sequential_history", [])`, replace with:
```python
entries = await ProductMemoryRepository.get_entries_by_product(session, product.id)
```

If code writes to JSONB, migrate to table insert:
```python
await ProductMemoryRepository.create_entry(session, product_id, entry_data)
```

**Step 3.2: Update Baseline Migration (10 min)**
- Change `product_memory` JSONB default value to exclude `sequential_history`
- Verify table definition still includes the column (for git_integration)

**Step 3.3: Model Import Verification (5 min)**
```bash
python -c "from src.giljo_mcp.models import AgentExecution, Product; print('Models loaded successfully')"
```

---

### Phase 4: Testing & Verification (30 min)

**Step 4.1: Grep Verification (10 min)**
```bash
# Should return ZERO results (except in comments):
grep -r "execution\.messages\s*\[" src/ api/
grep -r "sequential_history" src/ api/ | grep -v "Handover\|DEPRECATED\|#"

# Should return results (counter columns and repository still in use):
grep -r "messages_sent_count" src/ api/
grep -r "ProductMemoryRepository" src/ api/
```

**Step 4.2: Database Schema Inspection (10 min)**
```bash
# Should show counter columns only, not JSONB column
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d agent_executions" | grep messages

# Should show: '{"github": {}, "context": {}}'::jsonb
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT column_default FROM information_schema.columns WHERE table_name='products' AND column_name='product_memory';"
```

**Step 4.3: Test Suite (10 min)**
```bash
# Run tests for services that were modified
pytest tests/services/test_message_service.py -v
pytest tests/services/test_product_service.py -v
pytest tests/integration/ -v
```

---

### Phase 5: Documentation Updates (15 min)

**Check doc_impacts.json for your handover ID** and update affected docs.

**Expected Updates**:
- CLAUDE.md - Update message system references (line ~387)
- docs/360_MEMORY_MANAGEMENT.md - Update JSONB references
- docs/SERVICES.md - Update MessageService/ProductService examples

---

### Phase 6: Communication & Commit (15 min)

**Step 6.1: Write to comms_log.json**

Add an entry:
```json
{
  "id": "0700c-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0700c",
  "to_handovers": ["0700e", "0700f", "orchestrator"],
  "type": "info",
  "subject": "JSONB field cleanup complete - messages and sequential_history removed",
  "message": "Removed AgentExecution.messages JSONB column entirely (~150 lines) and Product.product_memory.sequential_history field. Counter columns and ProductMemoryRepository are now authoritative. Verified with grep and database schema inspection. All tests passing.",
  "files_affected": [
    "src/giljo_mcp/models/agent_identity.py",
    "src/giljo_mcp/models/products.py",
    "src/giljo_mcp/services/message_service.py",
    "src/giljo_mcp/services/product_service.py",
    "migrations/versions/baseline_v32_unified.py"
  ],
  "action_required": false,
  "context": {
    "lines_removed": 150,
    "columns_removed": ["AgentExecution.messages"],
    "fields_removed": ["Product.product_memory.sequential_history"],
    "replacement_systems": ["Counter columns", "product_memory_entries table"]
  }
}
```

**Step 6.2: Commit**
```bash
git add -A
git commit -m "cleanup(0700c): Remove deprecated JSONB fields

Removed AgentExecution.messages JSONB column and Product.product_memory.sequential_history field.
Counter-based message system and normalized product_memory_entries table are now authoritative.

Changes:
- Deleted AgentExecution.messages column definition
- Removed JSONB persistence methods from MessageService (~80 lines)
- Removed sequential_history field from Product.product_memory server_default
- Deleted ProductService._validate_history_entry() and add_learning_to_product_memory() (~50 lines)
- Updated baseline migration to reflect new schema

Docs Updated:
- CLAUDE.md (message system references)
- docs/360_MEMORY_MANAGEMENT.md (JSONB references)
- docs/SERVICES.md (service examples)

Verified with grep, database inspection, and test suite.

```

---

## Recommended Subagents

**PRIMARY**: `database-expert` - Handles JSONB column removal and model changes
**SECONDARY**: `backend-integration-tester` - Verifies message counters and memory system still work

---

## Critical Reminders

1. **This is a PURGE, not a migration** - Delete the column/field AND all code that uses it
2. **DO NOT remove entire Product.product_memory column** - Only remove `sequential_history` field from JSONB
3. **DO remove AgentExecution.messages column entirely** - Fully replaced by counters
4. **High-risk file alert**: agent_identity.py has 32 dependents - verify imports after changes
5. **Fresh installs will work** - Baseline migration will have clean schema
6. **Git revert is your rollback** - No migration, just code deletion

---

## Verification Commands Summary

```bash
# 1. Models load successfully
python -c "from src.giljo_mcp.models import AgentExecution, Product; print('Models loaded')"

# 2. No JSONB writes remain
grep -r "execution\.messages\[" src/ api/
grep -r "sequential_history" src/ api/ | grep -v "DEPRECATED\|#"

# 3. Replacement systems still work
grep -r "messages_sent_count" src/ api/
grep -r "ProductMemoryRepository" src/ api/

# 4. Database schema is clean
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d agent_executions" | grep messages
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d products" | grep product_memory

# 5. Tests pass
pytest tests/services/test_message_service.py -v
pytest tests/services/test_product_service.py -v
```

---

## Expected Outcome

**Lines Removed**: ~150 lines
- AgentExecution.messages column: ~10 lines
- MessageService JSONB methods: ~80 lines
- ProductService deprecated methods: ~50 lines
- Product.product_memory updates: ~10 lines

**Files Modified**: 5
- src/giljo_mcp/models/agent_identity.py
- src/giljo_mcp/models/products.py
- src/giljo_mcp/services/message_service.py
- src/giljo_mcp/services/product_service.py
- migrations/versions/baseline_v32_unified.py

**Tests**: All passing after cleanup

**Risk Level**: HIGH (database schema changes affecting core data structures)

**Mitigation**: Counter columns and ProductMemoryRepository already implemented and tested in prior handovers (0387i, 0390). Comprehensive grep ensures all JSONB access is found.

---

## Ready to Start?

Read the full handover spec at:
`handovers/0700_series/0700c_jsonb_field_cleanup.md`

Follow the Worker Protocol at:
`handovers/0700_series/WORKER_PROTOCOL.md`

Check for upstream messages in:
`handovers/0700_series/comms_log.json` (filter to_handovers: "0700c")

**Go forth and purge!** 🔥
