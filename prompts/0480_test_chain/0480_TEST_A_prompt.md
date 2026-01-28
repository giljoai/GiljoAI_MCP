# Terminal Session: 0480-TEST-A - Backend Service Tests

## Mission
Execute backend service tests for the 0480 Exception Handling Migration.

## Test Plan Reference
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0480_TEST_PLAN.md`

## Your Tasks

### 1. Run ProjectService Tests
```bash
cd F:\GiljoAI_MCP
python -m pytest tests/services/test_project_service*.py -v --tb=short 2>&1 | tee tests/reports/0480_TEST_A_project.log
```

### 2. Run OrchestrationService Tests
```bash
python -m pytest tests/tools/test_tool_accessor*.py -v --tb=short -k "orchestrat" 2>&1 | tee tests/reports/0480_TEST_A_orchestration.log
```

### 3. Analyze Failures
For each failure:
- Is it related to 0480 changes (dict→exception migration)?
- Or is it a pre-existing test issue (mocking, fixtures)?

### 4. Create Summary Report
Write results to `F:\GiljoAI_MCP\tests\reports\0480_TEST_A_RESULTS.md`:
- Total tests run
- Passed/Failed counts
- List of 0480-related failures (if any)
- List of pre-existing failures

## Success Criteria
- All tests related to exception handling pass
- Pre-existing failures documented but not blocking

## On Completion
Spawn next terminal:
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0480-TEST-B\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute test phase 0480-TEST-B. Read F:\GiljoAI_MCP\prompts\0480_test_chain\0480_TEST_B_prompt.md\"' -Verb RunAs"
```
