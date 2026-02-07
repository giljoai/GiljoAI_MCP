# Handover 0731: Legacy Code Removal

**Series:** 0700 Code Health Audit Follow-Up
**Priority:** P2 - MEDIUM (Post v1.0)
**Risk Level:** MEDIUM
**Estimated Effort:** 16-24 hours
**Prerequisites:** Handover 0725 Audit, v1.0 Release Complete
**Status:** DEFERRED (Post v1.0)

---

## Mission Statement

Remove legacy backward compatibility layers, deprecated fields, and method stubs after v1.0 release and transition period.

**Current Status:** 89+ legacy patterns identified, including 400+ line compatibility layer.

---

## Why Post v1.0?

This handover should be executed **after v1.0 release** to allow:
1. Users to migrate to new APIs during v1.0 lifecycle
2. Documentation updates to reference new patterns
3. Transition period for plugin/extension authors
4. Verification that new patterns are stable

---

## Part 1: Agent Message Queue Compatibility Layer

**File:** `src/giljo_mcp/agent_message_queue.py` (Lines 345-747)

**Size:** 400+ lines of backward compatibility code

**Purpose:** Provides old API for `AgentCommunicationQueue`:
- `send_message()`
- `send_messages()`
- `get_messages()`
- `get_unread_count()`
- `acknowledge_all()`

**Investigation Required:**
1. Search codebase for usage of old API methods
2. Verify all callers migrated to new API
3. Check if any external plugins use old API (if plugin system exists)

**Removal Process:**
```bash
# 1. Verify no callers
grep -r "send_message\|get_messages\|acknowledge_all" src/ api/ tests/

# 2. If all callers migrated, remove compatibility methods
# Edit agent_message_queue.py, remove lines 345-747

# 3. Run tests
pytest tests/ -k message
```

**Risk:** HIGH if external plugins exist, MEDIUM if internal-only

---

## Part 2: Remove Deprecated Fields from Models

### Product Model (products.py)

**Deprecated Fields:**
1. Vision fields (removed in Handover 0128e)
   - Lines 77-80: Old vision schema fields
   - Lines 279-341: Migration helper properties

2. Product Memory JSONB (replaced by normalized table in 0390)
   - `Product.product_memory.sequential_history` field reference
   - Migration helpers in `ProductMemoryEntry` model

**Removal Process:**
```python
# BEFORE
class Product(Base):
    # ... other fields
    vision_depth = Column(String)  # DEPRECATED - Remove
    vision_summary = Column(Text)  # DEPRECATED - Remove

    @property
    def legacy_vision_format(self):  # DEPRECATED - Remove
        # Migration helper
        pass

# AFTER
class Product(Base):
    # ... other fields
    # Deprecated fields removed
```

**Verification:**
```bash
# Check for references
grep -r "vision_depth\|vision_summary\|legacy_vision_format" src/ api/

# If none found, safe to remove
```

---

### Template Model (template models)

**Deprecated Fields:**
- `category` (Line 37 in `api/endpoints/templates/models.py`)
- `project_type` (Line 38)
- `preferred_tool` (Line 39)

**Status:** Still in API schema - need to verify frontend doesn't use

**Removal Process:**
1. Check frontend for usage of these fields
2. If unused, remove from Pydantic schemas
3. Remove from database model if present
4. Update API documentation

---

### Context Budget Field

**Location:** `src/giljo_mcp/tools/context_tools/get_project.py` (Lines 5, 35, 96)

**Status:** Soft deprecated in v3.1, excluded from responses

**Removal Process:**
1. Remove `context_budget` field from Project model
2. Remove exclusion logic in MCP tools
3. Update database migration (may require migration file)
4. Verify no consumers rely on this field

---

## Part 3: Remove Method Stubs

### 1. trigger_succession() Stub

**File:** `src/giljo_mcp/services/orchestration_service.py:2179-2190`

**Status:** Removed in Handover 0700d, replaced by simple_handover.py endpoint

**Current Behavior:** Raises `NotImplementedError` with message

**Removal Process:**
```python
# BEFORE
async def trigger_succession(...):
    """REMOVED (Handover 0700d): Legacy Agent ID Swap succession removed."""
    raise NotImplementedError("Use simple_handover.py endpoint instead")

# AFTER
# Method completely removed
```

**Verification:**
```bash
# Check for callers
grep -r "trigger_succession" src/ api/ frontend/

# If none found (except docs), safe to remove
```

---

### 2. Serena MCP Placeholders

**File:** `src/giljo_mcp/discovery.py:614-654`

**Methods:**
1. Placeholder method 1 (not implemented)
2. Placeholder method 2 (not implemented)
3. Placeholder method 3 (not implemented)

**Decision Required:**
- **Option A:** Implement Serena MCP integration
- **Option B:** Remove placeholders if feature abandoned

**Recommendation:** Clarify product roadmap before removing.

---

### 3. Message Duplicate Detection Placeholder

**File:** `src/giljo_mcp/agent_message_queue.py:857-859`

**Status:** Returns `False` as placeholder

**Removal Process:**
- **Option A:** Implement duplicate detection
- **Option B:** Remove placeholder if feature not needed

---

## Part 4: WebSocket Event Type Aliases

**File:** `api/websocket.py` (Lines 21-79)

**Purpose:** Support both underscore and colon variants:
- `product_update` vs `product:update`
- `agent_job_created` vs `agent:job:created`

**Flag:** `emit_legacy_aliases` controls dual emission

**Removal Process:**
1. Check frontend for usage of underscore variants
2. Migrate frontend to colon variants
3. Remove legacy emission logic
4. Update WebSocket documentation

**Breaking Change:** YES - requires frontend update

---

## Part 5: Logging Backward Compatibility

**File:** `src/giljo_mcp/logging/__init__.py`

**Compatibility:**
- Line 155: `get_colored_logger()` alias for `get_logger()`
- Lines 170-177: Auto-configure on import

**Assessment:** Low impact, can remain for convenience

**Recommendation:** Keep (not worth breaking)

---

## Part 6: Dependencies Module Re-export

**File:** `api/dependencies/__init__.py` (Lines 11-31)

**Purpose:** Re-exports for backward compatibility:
- `get_tenant_key`
- `get_db`

**Removal Process:**
1. Search for imports from `api.dependencies`
2. Update to import from `api.dependencies.{specific_module}`
3. Remove re-export layer

**Breaking Change:** YES - requires import updates throughout codebase

**Recommendation:** Keep (minimal cost, high disruption to remove)

---

## Part 7: Model Exports

**File:** `src/giljo_mcp/models/__init__.py`

**Status:** Maintains backward compatibility for 427 existing imports

**Assessment:** Critical compatibility layer

**Recommendation:** **DO NOT REMOVE** - too many dependents

---

## Part 8: Commented Code Cleanup

### Commented Imports

**File:** `api/endpoints/setup.py:70-71`

```python
# from sqlalchemy import select  # REMOVE
# from src.giljo_mcp.models import User  # REMOVE
```

**Process:** Simply delete commented lines

---

## Part 9: Type Ignore Comments

**File:** `src/giljo_mcp/tools/product.py`

**Lines:** 51, 52, 162, 163

**Investigation Required:**
1. Understand why type ignore needed
2. Attempt proper typing
3. If impossible, document reason
4. If resolvable, fix typing and remove ignore

---

## Part 10: Ollama References

**File:** `src/giljo_mcp/template_manager.py`

**Count:** 12 instances noted

**Status:** Ollama support may have been removed

**Removal Process:**
1. Verify Ollama is no longer supported
2. Search for all Ollama references
3. Remove references and related code
4. Update documentation

---

## Testing Strategy

### Regression Testing
After each removal:
```bash
# Full test suite
pytest tests/

# Ruff linting
ruff check src/ api/

# Application startup
python startup.py --dev

# Frontend build
cd frontend && npm run build
```

### Integration Testing
- Verify all API endpoints work
- Verify frontend loads and functions
- Verify agent orchestration works
- Verify WebSocket events propagate

---

## Success Criteria

- [ ] Agent Message Queue compatibility layer evaluated (keep or remove)
- [ ] Deprecated model fields removed
- [ ] Method stubs removed
- [ ] WebSocket event aliases consolidated (if frontend ready)
- [ ] Commented code removed
- [ ] Type ignores investigated and resolved
- [ ] Ollama references removed (if applicable)
- [ ] All tests pass
- [ ] Ruff linting clean
- [ ] Application works end-to-end
- [ ] Frontend works with changes

---

## Rollout Strategy

1. **v1.0 Release** - All legacy code remains, marked deprecated
2. **v1.1** - Warnings added for legacy API usage
3. **v1.2** - Small legacy removals (commented code, type ignores)
4. **v2.0** - Major legacy removals (this handover)

---

## Files to Modify

**Primary Targets:**
1. `src/giljo_mcp/agent_message_queue.py` (Lines 345-747)
2. `src/giljo_mcp/models/products.py` (Lines 77-80, 279-341)
3. `src/giljo_mcp/services/orchestration_service.py` (Lines 2179-2190)
4. `src/giljo_mcp/discovery.py` (Lines 614-654)
5. `api/websocket.py` (Lines 21-79)
6. `api/endpoints/setup.py` (Lines 70-71)
7. `src/giljo_mcp/tools/product.py` (Lines 51, 52, 162, 163)
8. `src/giljo_mcp/template_manager.py` (12 Ollama references)

**Additional:**
- `api/endpoints/templates/models.py` (deprecated fields)
- `src/giljo_mcp/tools/context_tools/get_project.py` (context_budget)

---

## Reference

**Audit Report:** `handovers/0725_AUDIT_REPORT.md` (Lines 214-242)
**Deprecation Findings:** `handovers/0725_findings_deprecation.md`
