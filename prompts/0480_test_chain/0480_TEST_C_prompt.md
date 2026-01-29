# Terminal Session: 0480-TEST-C - API Endpoint Tests

## Mission
Execute API endpoint integration tests for the 0480 Exception Handling Migration.

## Test Plan Reference
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0480_TEST_PLAN.md`

## Server Info
- Backend: http://localhost:7272
- Frontend: http://localhost:7274
- Database: PostgreSQL (password: 4010)

## Your Tasks

### 1. Run API Endpoint Tests
```bash
cd F:\GiljoAI_MCP
python -m pytest tests/api/ -v --tb=short 2>&1 | tee tests/reports/0480_TEST_C_api.log
```

### 2. Test Error Responses via curl
```bash
# Test 404 response for non-existent project
curl -X GET "http://localhost:7272/api/projects/nonexistent-uuid" \
  -H "Authorization: Bearer <token>" | jq

# Expected: {"detail": {"code": "NOT_FOUND", "message": "Project not found"}}
```

### 3. Verify HTTP Status Codes
| Exception | Expected HTTP Status |
|-----------|---------------------|
| ResourceNotFoundError | 404 |
| ValidationError | 400 |
| AuthorizationError | 403 |
| BaseGiljoException | 500 |

### 4. Create Summary Report
Write results to `F:\GiljoAI_MCP\tests\reports\0480_TEST_C_RESULTS.md`

## Success Criteria
- All API endpoints return correct HTTP status codes
- Error responses have consistent format

## On Completion
Spawn browser test terminal:
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0480-TEST-BROWSER\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute browser E2E tests. Read F:\GiljoAI_MCP\prompts\0480_test_chain\0480_TEST_BROWSER_prompt.md\"' -Verb RunAs"
```
