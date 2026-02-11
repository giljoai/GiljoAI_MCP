# Handover 0731a: Pydantic Response Models + Design Validation

**Handover ID:** 0731a
**Series:** 0731 Typed Service Returns (Part 1/4)
**Phase:** Design & Model Creation
**Priority:** P1 - HIGH
**Estimated Effort:** 4-6 hours
**Status:** READY
**Branch:** `feature/0731-typed-service-returns`
**Dependencies:** 0480 series (exception hierarchy - COMPLETE), 0730a design docs (COMPLETE)
**Blocks:** 0731b, 0731c, 0731d

---

## 1. Mission & Context

### What We're Doing
Create Pydantic response model classes that will replace `dict[str, Any]` returns across all 14 service files (111 `-> dict[str, Any]` annotations). This is the foundation phase - no service code changes yet, just creating the models and validating the existing design.

### Why This Matters
The `dict[str, Any]` return pattern is the single biggest "AI slop" perception risk in the codebase (per 0740 community audit). It provides zero IDE support, no type checking, and no compile-time safety. Every consumer must know dict structure by convention. Typed Pydantic models fix all of this.

### What Already Exists
- **Design doc**: `docs/architecture/service_response_models.md` - Catalogues all 117 dict wrapper instances across 12 services with target return types. Created in 0730a (validated 2026-02-07).
- **Exception hierarchy**: `src/giljo_mcp/exceptions.py` - 25+ domain exceptions with `default_status_code`, `error_code`, `context` dict, `to_dict()`. Created in 0480 series.
- **Global exception handler**: `api/exception_handlers.py` - Maps BaseGiljoError to HTTP responses automatically.
- **Archived reference**: `archive/0730-rushed-implementation` branch has a rushed but functional implementation (use as pattern reference ONLY, do not cherry-pick).

### Scope
- Validate the design doc against current codebase (methods may have changed since 0730a)
- Create Pydantic response model classes
- Write comprehensive tests for the models
- Do NOT modify any service code (that's 0731b/c)

---

## 2. What Will Change

### New Files
- `src/giljo_mcp/schemas/service_responses.py` - All response model classes

### Modified Files
- `src/giljo_mcp/schemas/__init__.py` - Export new models
- `docs/architecture/service_response_models.md` - Update if methods changed

### New Test Files
- `tests/schemas/test_service_responses.py` - Model validation tests

---

## 3. Embedded Coding Principles

You MUST follow these principles:

1. **Use Serena MCP tools** for code exploration (`find_symbol`, `get_symbols_overview`, `find_referencing_symbols`) - REQUIRED for discovering current method signatures
2. **Follow TDD**: Write tests FIRST, then implement models
3. **Use `pathlib.Path()`** for all file operations (cross-platform)
4. **Multi-tenant isolation**: All models that include tenant data must have `tenant_key` field
5. **No emojis in code** unless explicitly requested
6. **Clean code**: Production-grade, no shortcuts
7. **Use subagents**: Leverage `tdd-implementor` for model creation with tests

---

## 4. Implementation Details

### Step 1: Validate Design Doc Against Current Codebase

Use Serena MCP tools to verify each service's current methods match the design doc:

```python
# For each service, verify method signatures
mcp__serena__get_symbols_overview("src/giljo_mcp/services/org_service.py")
mcp__serena__get_symbols_overview("src/giljo_mcp/services/user_service.py")
# ... etc for all 14 service files
```

Check for:
- Methods added since design doc was written
- Methods removed or renamed
- Parameter changes
- Any new dict wrapper patterns not catalogued

Update `docs/architecture/service_response_models.md` if discrepancies found.

### Step 2: Design Response Model Classes

**Pattern for single-object returns:**
```python
# Service currently returns: {"success": True, "data": Organization}
# Service will return: Organization (the SQLAlchemy model directly)
# No Pydantic wrapper needed for single objects
```

**Pattern for composite returns:**
```python
from pydantic import BaseModel

class DeleteResult(BaseModel):
    """Result of a delete operation."""
    deleted: bool = True
    id: str

class TransferResult(BaseModel):
    """Result of an ownership transfer."""
    transferred: bool = True
    from_user_id: str
    to_user_id: str
```

**Pattern for list returns with metadata:**
```python
class PaginatedResult(BaseModel, Generic[T]):
    """Paginated list result."""
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50
```

**Key design decisions:**
- Simple CRUD methods return SQLAlchemy models directly (no wrapper)
- Delete/transfer/batch operations return typed result models
- List operations return `list[Model]` or `PaginatedResult[Model]`
- Error cases raise domain exceptions (never return error dicts)
- Methods that already return bool/str/None stay unchanged

### Step 3: Create Response Models File

Create `src/giljo_mcp/schemas/service_responses.py` with:
- All shared result types (DeleteResult, TransferResult, etc.)
- Service-specific response models where needed
- Proper docstrings and type annotations
- Optional field defaults where appropriate

### Step 4: Write Tests

Create `tests/schemas/test_service_responses.py`:
- Test model creation with valid data
- Test validation (required fields, types)
- Test serialization (`model_dump()`)
- Test optional fields with defaults

---

## 5. TDD Workflow

**MANDATORY: Write tests FIRST, then implement.**

```python
# tests/schemas/test_service_responses.py

def test_delete_result_creation():
    """DeleteResult should capture deleted resource ID."""
    result = DeleteResult(id="abc-123")
    assert result.deleted is True
    assert result.id == "abc-123"

def test_delete_result_requires_id():
    """DeleteResult must have an id."""
    with pytest.raises(ValidationError):
        DeleteResult()

def test_transfer_result_creation():
    """TransferResult should capture from/to user IDs."""
    result = TransferResult(from_user_id="user-1", to_user_id="user-2")
    assert result.transferred is True
```

Write ALL model tests first. Then create the models to make them pass.

---

## 6. Serena MCP Usage Requirements

**REQUIRED** - Use these tools for codebase exploration:

```
mcp__serena__get_symbols_overview(file_path) - Get all classes/functions in a file
mcp__serena__find_symbol(symbol_name) - Find where a class/function is defined
mcp__serena__find_referencing_symbols(symbol_name) - Find all callers of a function
```

Use Serena to:
1. Verify current method signatures in all 14 service files
2. Check existing schema definitions in `src/giljo_mcp/schemas/`
3. Find existing Pydantic models that might be reusable
4. Verify exception classes in `src/giljo_mcp/exceptions.py`

Do NOT read entire files with `Read` tool when Serena can give you targeted symbol information.

---

## 7. Testing Requirements

- All response model tests must pass
- Run: `pytest tests/schemas/test_service_responses.py -v`
- Coverage: 100% of new model classes
- Test both valid and invalid data
- Test serialization/deserialization

---

## 8. Definition of Done

- [ ] Design doc validated against current codebase (updated if needed)
- [ ] All response model classes created in `src/giljo_mcp/schemas/service_responses.py`
- [ ] Tests written FIRST using TDD approach
- [ ] All tests passing: `pytest tests/schemas/test_service_responses.py -v`
- [ ] Models exported from `src/giljo_mcp/schemas/__init__.py`
- [ ] No regressions in existing tests
- [ ] Code follows principles in HANDOVER_INSTRUCTIONS.md
- [ ] Changes committed with proper message format
- [ ] Chain log updated
- [ ] STOPPED - awaiting 0731b execution via chain

---

## 9. Git Commit Standards

```bash
git add src/giljo_mcp/schemas/service_responses.py
git add src/giljo_mcp/schemas/__init__.py
git add tests/schemas/test_service_responses.py
git add docs/architecture/service_response_models.md  # if updated

git commit -m "feat(0731a): Create Pydantic response models for typed service returns

Add response model classes (DeleteResult, TransferResult, PaginatedResult, etc.)
for replacing dict[str, Any] returns across 14 service files. TDD: tests written
first. Design doc validated against current codebase.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 10. STOP Boundary

## CRITICAL: STOP AFTER COMPLETION

**DO NOT PROCEED TO 0731b WITHOUT COMPLETING THE CHAIN STEPS BELOW.**

This phase is complete when response model classes are created and tested.
Update the chain log, then spawn the next terminal.

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0731_chain/chain_log.json`. This is session 1 of 4. Mark your session as `"status": "in_progress", "started_at": "<timestamp>"`.

### Step 2: Execute Handover Tasks

**CRITICAL: Use Task tool to spawn subagents for this work. Do NOT do all work directly.**

Recommended approach:

Agent 1 - Design validation:
```
Task(subagent_type="deep-researcher", prompt="Validate the design doc at docs/architecture/service_response_models.md against the current codebase. For each of the 14 service files listed in the grep output (org_service.py, user_service.py, product_service.py, task_service.py, project_service.py, message_service.py, orchestration_service.py, template_service.py, settings_service.py, auth_service.py, config_service.py, agent_job_manager.py, vision_summarizer.py, consolidation_service.py), use Serena MCP tools to get current method signatures and compare with the design doc. Report any discrepancies.")
```

Agent 2 - Model creation with TDD:
```
Task(subagent_type="tdd-implementor", prompt="Create Pydantic response models in src/giljo_mcp/schemas/service_responses.py. First write tests in tests/schemas/test_service_responses.py. Models needed: DeleteResult(id: str, deleted: bool=True), TransferResult(from_user_id: str, to_user_id: str, transferred: bool=True), and any service-specific models identified in docs/architecture/service_response_models.md. Most services will return SQLAlchemy models directly - only create Pydantic models for composite results. Follow TDD: tests first, then models. Export from schemas/__init__.py.")
```

### Step 3: Verify & Commit
After agents complete:
1. Run `pytest tests/schemas/ -v` - all pass
2. Run `ruff check src/giljo_mcp/schemas/`
3. Commit per git standards above

### Step 4: Update Chain Log
Update `prompts/0731_chain/chain_log.json` for session 0731a:
- `tasks_completed`: What was done
- `deviations`: Changes from plan
- `notes_for_next`: What 0731b needs to know (e.g., which models to use for which service)
- `summary`: 2-3 sentences
- `status`: "complete"
- `completed_at`: "<timestamp>"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE this command (Don't Just Print It!):**

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0731b - Tier 1 Service Refactor\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0731b. READ F:\GiljoAI_MCP\handovers\0731b_tier1_service_refactor.md for full instructions. Check chain log at F:\GiljoAI_MCP\prompts\0731_chain\chain_log.json first. Branch: feature/0731-typed-service-returns. Use Task subagents (tdd-implementor) for the refactoring work.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS! Only ONE agent should spawn the next terminal. If your subagent already spawned it, DO NOT spawn again.**
