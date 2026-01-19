# Handover 0390c: Stop JSONB Writes

**Part 3 of 4** in the 360 Memory JSONB Normalization series (0390)
**Date**: 2026-01-18
**Status**: Ready for Implementation
**Complexity**: High
**Estimated Duration**: 6-8 hours
**Branch**: `0390-360-memory-normalization`
**Prerequisite**: 0390b Complete (all reads from table)

---

## 1. EXECUTIVE SUMMARY

### Mission
Modify all 7 WRITE locations to insert into `product_memory_entries` table instead of appending to `Product.product_memory.sequential_history[]` JSONB array.

### Context
After 0390b, all reads come from the normalized table. This handover switches all write operations to insert into the table, making it the single source of truth.

### Why This Matters
- **Single Source of Truth**: No more dual-write risk
- **Referential Integrity**: FK constraints enforced
- **Cleaner Code**: Remove JSONB manipulation logic
- **Production Ready**: Table-only architecture

### Success Criteria
- [ ] Zero JSONB writes for 360 memory entries
- [ ] All new entries created in table
- [ ] Sequence numbers generated atomically
- [ ] WebSocket events emit table data
- [ ] All tests pass

---

## 2. TECHNICAL CONTEXT

### Current WRITE Locations (5 files, 7 call sites)

| File | Lines | Function | Current Pattern | New Pattern |
|------|-------|----------|-----------------|-------------|
| `tools/write_360_memory.py` | 200-218 | `write_360_memory()` | Append to JSONB | Repository insert |
| `tools/project_closeout.py` | 148-170 | `close_project_and_update_memory()` | Append to JSONB | Repository insert |
| `services/product_service.py` | 975-992 | `update_git_integration()` | JSONB mutation | **Keep** (git config only) |
| `services/product_service.py` | 1328-1332 | `_ensure_product_memory_initialized()` | Default structure | **Keep** (git config init) |
| `services/project_service.py` | 2179-2192 | `nuclear_delete_project()` | JSONB mutation | Already done in 0390b |
| `services/project_service.py` | 2265-2275 | `_purge_project_records()` | JSONB mutation | Already done in 0390b |

**Note**: Git integration config stays in JSONB (`product_memory.git_integration`) - only `sequential_history` moves to table.

---

## 3. SCOPE

### In Scope

1. **write_360_memory.py**
   - Replace JSONB append with repository insert
   - Use `get_next_sequence()` for atomic sequence
   - Emit WebSocket event with table data

2. **project_closeout.py (close_project_and_update_memory)**
   - Replace JSONB append with repository insert
   - Maintain all existing fields
   - Update return format

3. **WebSocket Events**
   - Update payloads to use table data
   - Maintain backward-compatible format

4. **TDD Tests**
   - Write tests for new table-based writes
   - Verify no JSONB mutations

### Out of Scope
- Git integration config (stays in JSONB)
- JSONB column deprecation (0390d)
- Read operations (done in 0390b)

---

## 4. IMPLEMENTATION PLAN

### Phase 1: Verify 0390b Complete (15 minutes)

**Tasks**:
```bash
# Verify all reads from table
grep -r "sequential_history" src/giljo_mcp/tools/context_tools/
# Should show no JSONB reads

# Verify project deletion uses table
grep -r "mark_entries_deleted" src/giljo_mcp/services/project_service.py
# Should find repository call

# Run all tests
pytest tests/ -v --tb=short
```

---

### Phase 2: Update write_360_memory.py (2 hours)

**File**: `src/giljo_mcp/tools/write_360_memory.py`

#### Current Implementation (lines 200-218):

```python
# Get or initialize product_memory
product_memory = product.product_memory or {}
sequential_history = product_memory.get("sequential_history", [])

# Calculate sequence
sequence_number = max([e.get("sequence", 0) for e in sequential_history] or [0]) + 1

# Build entry
history_entry = {
    "sequence": sequence_number,
    "project_id": project_id,
    "type": entry_type,
    ...
}

# Append and save
sequential_history.append(history_entry)
product.product_memory = dict(product_memory)
flag_modified(product, "product_memory")
```

#### New Implementation:

```python
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

# Initialize repository
repo = ProductMemoryRepository()

# Get atomic sequence number
sequence_number = await repo.get_next_sequence(
    session=active_session,
    product_id=product.id,
)

# Create entry in table
entry = await repo.create_entry(
    session=active_session,
    tenant_key=tenant_key,
    product_id=product.id,
    project_id=project_id,
    sequence=sequence_number,
    entry_type=entry_type,
    source="write_360_memory_v1",
    timestamp=datetime.utcnow(),
    project_name=project.name if project else None,
    summary=summary,
    key_outcomes=key_outcomes,
    decisions_made=decisions_made,
    git_commits=git_commits,
    author_job_id=author_job_id,
    author_name=author_info.get("author_name"),
    author_type=author_info.get("author_type"),
)

# Commit
if owns_session:
    await active_session.commit()

# Return success
return {
    "success": True,
    "sequence_number": entry.sequence,
    "entry_id": str(entry.id),
    "git_commits_count": len(git_commits) if git_commits else 0,
    "entry_type": entry_type,
    "message": "360 Memory entry written successfully",
}
```

**Remove**:
- `flag_modified(product, "product_memory")`
- All `sequential_history.append()` calls
- JSONB manipulation code

---

### Phase 3: Update project_closeout.py (2 hours)

**File**: `src/giljo_mcp/tools/project_closeout.py`

Find `close_project_and_update_memory()` function and update similarly.

#### Key Changes:

1. **Import repository**:
```python
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository
```

2. **Replace JSONB append**:
```python
repo = ProductMemoryRepository()

sequence = await repo.get_next_sequence(
    session=session,
    product_id=product.id,
)

entry = await repo.create_entry(
    session=session,
    tenant_key=tenant_key,
    product_id=product.id,
    project_id=project.id,
    sequence=sequence,
    entry_type="project_closeout",
    source="closeout_v1",
    timestamp=datetime.utcnow(),
    project_name=project.name,
    summary=summary,
    key_outcomes=key_outcomes,
    decisions_made=decisions_made,
    git_commits=git_commits,
    deliverables=deliverables,
    metrics=metrics,
    priority=priority,
    significance_score=significance_score,
    token_estimate=token_estimate,
    tags=tags,
)
```

3. **Update return format**:
```python
return {
    "success": True,
    "sequence_number": entry.sequence,
    "entry_id": str(entry.id),
    ...
}
```

---

### Phase 4: Update WebSocket Events (1 hour)

Ensure WebSocket events for memory updates use table data.

**Event**: `product:memory:updated`

**Payload format** (maintain compatibility):
```json
{
  "product_id": "...",
  "entry": {
    "sequence": 5,
    "type": "project_closeout",
    "project_id": "...",
    ...
  }
}
```

**Implementation**:
```python
# After creating entry
await websocket_manager.emit_to_tenant(
    tenant_key=tenant_key,
    event="product:memory:updated",
    data={
        "product_id": str(product.id),
        "entry": entry.to_dict(),
    }
)
```

---

### Phase 5: TDD Tests (1.5 hours)

**Test File**: `tests/tools/test_write_360_memory_table.py`

```python
"""
TDD tests for table-based 360 memory writes (Handover 0390c).
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.tools.write_360_memory import write_360_memory
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry


class TestWrite360MemoryTable:
    """Tests for table-based write_360_memory."""

    @pytest.mark.asyncio
    async def test_creates_table_entry(self, async_session, test_product, test_project, db_manager):
        """write_360_memory should create entry in table, not JSONB."""
        result = await write_360_memory(
            project_id=str(test_project.id),
            tenant_key="test_tenant",
            summary="Test summary",
            key_outcomes=["outcome1"],
            decisions_made=["decision1"],
            db_manager=db_manager,
            session=async_session,
        )

        assert result["success"] is True
        assert "entry_id" in result

        # Verify entry in table
        entry = await async_session.get(ProductMemoryEntry, uuid4(result["entry_id"]))
        assert entry is not None
        assert entry.summary == "Test summary"

    @pytest.mark.asyncio
    async def test_no_jsonb_mutation(self, async_session, test_product, test_project, db_manager):
        """write_360_memory should NOT mutate product_memory JSONB."""
        # Get initial JSONB state
        initial_memory = dict(test_product.product_memory or {})
        initial_count = len(initial_memory.get("sequential_history", []))

        await write_360_memory(
            project_id=str(test_project.id),
            tenant_key="test_tenant",
            summary="Test",
            key_outcomes=[],
            decisions_made=[],
            db_manager=db_manager,
            session=async_session,
        )

        # Refresh product
        await async_session.refresh(test_product)

        # JSONB should be unchanged
        new_count = len((test_product.product_memory or {}).get("sequential_history", []))
        assert new_count == initial_count

    @pytest.mark.asyncio
    async def test_atomic_sequence_generation(self, async_session, test_product, test_project, db_manager):
        """Sequence numbers should be atomic and unique."""
        # Create 3 entries
        results = []
        for i in range(3):
            result = await write_360_memory(
                project_id=str(test_project.id),
                tenant_key="test_tenant",
                summary=f"Entry {i}",
                key_outcomes=[],
                decisions_made=[],
                db_manager=db_manager,
                session=async_session,
            )
            results.append(result)

        sequences = [r["sequence_number"] for r in results]
        # Should be 1, 2, 3 (or incrementing from existing max)
        assert sequences[1] == sequences[0] + 1
        assert sequences[2] == sequences[1] + 1
```

---

### Phase 6: Integration Testing (1 hour)

**Test Scenarios**:

1. **Write 360 Memory**
   - Entry created in table
   - JSONB unchanged
   - Sequence atomic

2. **Close Project and Update Memory**
   - Entry created in table
   - All fields populated
   - WebSocket event emitted

3. **Concurrent Writes**
   - No sequence conflicts
   - All entries created

4. **Frontend Receives Update**
   - WebSocket payload correct
   - UI updates properly

---

## 5. TESTING REQUIREMENTS

### Unit Tests
- Table entry creation
- No JSONB mutation
- Sequence atomicity

### Integration Tests
- End-to-end write flow
- WebSocket events
- Concurrent writes

---

## 6. ROLLBACK PLAN

### Rollback Triggers
- Entries not created in table
- Sequence conflicts
- WebSocket breaks

### Rollback Steps
```bash
# Re-enable JSONB writes
git checkout HEAD~1 -- src/giljo_mcp/tools/write_360_memory.py
git checkout HEAD~1 -- src/giljo_mcp/tools/project_closeout.py
```

---

## 7. FILES INDEX

### Files to MODIFY

| File | Changes | Risk |
|------|---------|------|
| `src/giljo_mcp/tools/write_360_memory.py` | Repository insert | HIGH |
| `src/giljo_mcp/tools/project_closeout.py` | Repository insert | HIGH |
| `api/events/handlers.py` | WebSocket payload (if applicable) | MEDIUM |

### Files to CREATE

| File | Purpose |
|------|---------|
| `tests/tools/test_write_360_memory_table.py` | TDD tests |
| `tests/tools/test_project_closeout_table.py` | TDD tests |

---

## 8. SUCCESS CRITERIA

### Functional
- [ ] Zero JSONB writes for 360 memory
- [ ] All entries in table
- [ ] Sequences atomic
- [ ] WebSocket events work

### Quality
- [ ] All tests pass
- [ ] No linting errors
- [ ] TDD discipline followed

### Documentation
- [ ] Closeout notes completed
- [ ] Ready for 0390d handover

---

## CLOSEOUT NOTES

**Status**: [NOT STARTED]

*To be filled upon completion*

---

**Document Version**: 1.0
**Last Updated**: 2026-01-18
