# Handover 0750a: Backend Redundant Exception Cleanup

**Date**: 2026-02-11
**Series**: 0750 Final Scrub (Part 1/3)
**Branch**: `cleanup/post-0745-audit-fixes` (continue existing)
**Parent Commit**: 7f0cdf33

---

## Context

The GiljoAI MCP server has a global exception handler at `api/exception_handlers.py` that catches:
- `BaseGiljoError` (all domain exceptions)
- `RequestValidationError`
- `StarletteHTTPException`
- Generic `Exception`

Domain exceptions are defined in `src/giljo_mcp/exceptions.py`:
- `ResourceNotFoundError` -> 404
- `ValidationError` -> 422
- `AuthorizationError` -> 403

This makes per-endpoint try/except blocks redundant. In the previous session (commit 7f0cdf33), `products/crud.py` was cleaned (25 redundant blocks removed). Three files remain.

## Task

Remove redundant try/except blocks from these files:

### File 1: `api/endpoints/products/lifecycle.py` (~38 except blocks)
- Remove try/except that catches generic `Exception` and returns 500
- Remove try/except that catches `HTTPException` and re-raises (pointless)
- Remove try/except that catches domain exceptions already handled globally
- Keep ONLY: except blocks that do business logic (e.g., rollback, cleanup, state mutation) before re-raising

### File 2: `api/endpoints/products/vision.py` (~27 except blocks)
- Same pattern: remove redundant try/except wrapping
- Keep any that perform cleanup (file handle closing, temp file deletion)

### File 3: `api/endpoints/products/git_integration.py` (~6 except blocks)
- Same pattern: remove redundant try/except wrapping

### How to identify redundant blocks

A block is REDUNDANT if it:
```python
# Pattern 1: Catch and re-raise HTTPException (global handler already does this)
try:
    ...
except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

# Pattern 2: Catch domain exception and convert to HTTPException (global handler does this)
try:
    ...
except ResourceNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))

# Pattern 3: Bare except that just logs and re-raises
try:
    ...
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

A block should be KEPT if it:
```python
# Does cleanup before re-raising
try:
    temp_file = create_temp()
    process(temp_file)
except Exception:
    temp_file.unlink()  # Cleanup!
    raise

# Performs business logic transformation
try:
    result = service.do_thing()
except SpecificError:
    result = fallback_value  # Business logic decision
```

## IMPORTANT: gitignore quirk

The `api/endpoints/products/` directory is gitignored. You MUST use `git add -f` to stage files:
```bash
git add -f api/endpoints/products/lifecycle.py
git add -f api/endpoints/products/vision.py
git add -f api/endpoints/products/git_integration.py
```

## Verification

1. Run `ruff check api/endpoints/products/` - zero errors
2. Run `pytest tests/ -x -q --timeout=30` - all pass (use short timeout to avoid hangs)
3. Count remaining except blocks per file and report in chain log

## Success Criteria

- [ ] All redundant try/except blocks removed from lifecycle.py
- [ ] All redundant try/except blocks removed from vision.py
- [ ] All redundant try/except blocks removed from git_integration.py
- [ ] ruff check passes
- [ ] pytest passes (or at minimum, no NEW failures)
- [ ] Changes committed to branch

---

## Chain Execution Instructions

### Step 1: Create Chain Log
The chain log already exists at `prompts/0750_chain/chain_log.json`. Read it.

### Step 2: Mark Session Started
Update session 0750a: `"status": "in_progress", "started_at": "<current timestamp>"`

### Step 3: Execute Handover Tasks

**CRITICAL: Use Task tool to spawn subagents for this work. Do NOT do all work directly.**

Recommended approach:
```
Task(subagent_type="tdd-implementor", prompt="Remove redundant try/except blocks from api/endpoints/products/lifecycle.py. The global exception handler at api/exception_handlers.py already catches BaseGiljoError, RequestValidationError, StarletteHTTPException, and generic Exception. Remove any try/except that just catches and re-raises or converts domain exceptions to HTTPException. Keep only blocks that perform cleanup or business logic before re-raising. Read the file first, understand the global handler, then carefully remove redundant blocks.")
```

Spawn similar agents for vision.py and git_integration.py (can run in parallel).

After agents complete:
1. Run `ruff check api/endpoints/products/`
2. Run `pytest tests/ -x -q --timeout=30`
3. Stage with `git add -f api/endpoints/products/lifecycle.py api/endpoints/products/vision.py api/endpoints/products/git_integration.py`
4. Commit with message describing the cleanup

### Step 4: Update Chain Log
Before spawning next terminal, update `prompts/0750_chain/chain_log.json`:
- `tasks_completed`: List what you actually did
- `deviations`: Any changes from plan
- `blockers_encountered`: Issues hit
- `notes_for_next`: Critical info for next agent (e.g., "console.log count is actually X not 100")
- `summary`: 2-3 sentence summary
- `status`: "complete"
- `completed_at`: "<timestamp>"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE this command (Don't Just Print It!):**

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0750b - Frontend Console Cleanup\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0750b. READ F:\GiljoAI_MCP\handovers\0750b_frontend_console_cleanup.md for full instructions. Check chain log at F:\GiljoAI_MCP\prompts\0750_chain\chain_log.json first.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS! Only ONE agent should spawn the next terminal. If your subagent already spawned it, DO NOT spawn again.**
