# Terminal Session: 0480-TEST-B - MCP Tool Tests

## Mission
Execute MCP tool integration tests for the 0480 Exception Handling Migration.

## Test Plan Reference
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0480_TEST_PLAN.md`

## Your Tasks

### 1. Run MCP Tool Tests
```bash
cd F:\GiljoAI_MCP
python -m pytest tests/tools/ -v --tb=short 2>&1 | tee tests/reports/0480_TEST_B_tools.log
```

### 2. Test MCP Error Responses Directly
Use the MCP server to test error handling:

```python
# Test via Python
from src.giljo_mcp.tools.orchestration_tools import get_agent_mission

# This should return proper error response, not crash
result = await get_agent_mission(job_id="nonexistent-uuid", tenant_key="test")
# Expected: {"success": False, "error": {"code": "NOT_FOUND", "message": "..."}}
```

### 3. Verify Error Response Format
All MCP tools should return errors in this format:
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Human-readable error",
    "context": {"job_id": "..."}
  }
}
```

### 4. Create Summary Report
Write results to `F:\GiljoAI_MCP\tests\reports\0480_TEST_B_RESULTS.md`

## Success Criteria
- MCP tools return proper error format (not raise exceptions to caller)
- All tool tests pass

## On Completion
Spawn next terminal:
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0480-TEST-C\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute test phase 0480-TEST-C. Read F:\GiljoAI_MCP\prompts\0480_test_chain\0480_TEST_C_prompt.md\"' -Verb RunAs"
```
