# Handover 0700d: Legacy Succession Cleanup

## Context

**Decision**: Pre-release cleanup - remove deprecated Agent ID Swap succession system.

**Rationale**:
- Handover 0461f deprecated "Agent ID Swap" succession in favor of "360 Memory-based session continuity"
- New system uses `simple_handover.py` endpoint
- Old system uses `succession.py` endpoint and `trigger_succession()` method
- No external users exist - safe to remove legacy system

**Reference**: Strategic direction change documented in `dead_code_audit.md` (2026-02-04)

## Scope

Remove legacy succession endpoint, deprecated service methods, and related schemas.

### Affected Components

**1. API Endpoint** (api/endpoints/agent_jobs/succession.py):
- Entire file marked DEPRECATED (Line 4)
- Endpoint: `POST /api/agent-jobs/{job_id}/trigger-succession`
- Supporting endpoint: `GET /api/agent-jobs/{job_id}/succession-status`

**2. Service Method** (src/giljo_mcp/services/orchestration_service.py):
- `trigger_succession()` method - Line 2167 marked DEPRECATED
- Used by deprecated endpoint above

**3. Pydantic Schemas** (src/giljo_mcp/models/schemas.py):
- `SuccessionRequest` schema - Line 185 marked DEPRECATED (Handover 0461f)
- Supporting schemas: `SuccessionResponse`, `SuccessionStatusResponse`, `InitiateHandoverResponse`

**4. Frontend Integration**:
- "Hand Over" button in `AgentCardEnhanced.vue` (may call old endpoint)
- `/gil_handover` slash command (may call old endpoint)

**5. Deprecated Prompt Method** (src/giljo_mcp/thin_prompt_generator.py):
- `generate_execution_prompt()` - Line 964 marked DEPRECATED
- Used in legacy orchestrator flow

## Tasks

### Phase 1: Remove API Endpoint

1. [ ] Delete endpoint file:
   ```bash
   rm api/endpoints/agent_jobs/succession.py
   ```

2. [ ] Remove endpoint registration from router (api/endpoints/agent_jobs/__init__.py or api/app.py):
   ```bash
   grep -r "succession" api/endpoints/agent_jobs/__init__.py api/app.py
   # Remove import and router.include_router() call
   ```

3. [ ] Verify no other code imports succession router:
   ```bash
   grep -r "from.*succession import" api/
   grep -r "import.*succession" api/
   ```

### Phase 2: Remove Service Method

4. [ ] Remove `trigger_succession()` from OrchestrationService (src/giljo_mcp/services/orchestration_service.py):
   - Delete method starting at line 2167 (marked DEPRECATED)
   - Search for method definition: `async def trigger_succession(`

5. [ ] Verify no code calls trigger_succession:
   ```bash
   grep -r "trigger_succession" src/ api/ | grep -v "DEPRECATED"
   # Should only show imports/calls from deleted files
   ```

### Phase 3: Remove Deprecated Schemas

6. [ ] Remove schemas from models/schemas.py:
   - Delete `SuccessionRequest` (line 185+)
   - Delete `SuccessionResponse`
   - Delete `SuccessionStatusResponse`
   - Delete `InitiateHandoverResponse`
   - Search pattern: `class.*Succession.*Request|Response`

7. [ ] Verify no code uses removed schemas:
   ```bash
   grep -r "SuccessionRequest\|SuccessionResponse\|InitiateHandoverResponse" src/ api/
   ```

### Phase 4: Update Frontend

8. [ ] Check "Hand Over" button implementation (frontend/src/components/):
   ```bash
   grep -r "trigger-succession\|trigger_succession" frontend/src/
   ```

9. [ ] If button calls old endpoint, update to use simple-handover:
   - Find in: `AgentCardEnhanced.vue` or similar component
   - Change endpoint from `/api/agent-jobs/{job_id}/trigger-succession`
   - To: `/api/agent-jobs/{job_id}/simple-handover` (or equivalent new endpoint)

10. [ ] Check `/gil_handover` slash command:
    ```bash
    grep -r "gil_handover" src/ api/
    # Update to use simple-handover endpoint
    ```

### Phase 5: Remove Deprecated Prompt Generator Method

11. [ ] Remove `generate_execution_prompt()` from ThinClientPromptGenerator (src/giljo_mcp/thin_prompt_generator.py):
    - Delete method starting at line 964 (marked DEPRECATED)
    - Method signature: `async def generate_execution_prompt(`
    - Warning log at line 970: "generate_execution_prompt() is deprecated"

12. [ ] Verify no code calls generate_execution_prompt:
    ```bash
    grep -r "generate_execution_prompt" src/ api/ | grep -v "DEPRECATED\|#"
    ```

### Phase 6: Documentation Updates

13. [ ] Update CLAUDE.md:
    - Remove references to Agent ID Swap succession
    - Ensure simple-handover is documented as the official succession mechanism

14. [ ] Update API documentation (if exists):
    - Remove trigger-succession endpoint docs
    - Add/update simple-handover endpoint docs

## Verification

- [ ] Deleted files no longer exist:
  ```bash
  test ! -f api/endpoints/agent_jobs/succession.py
  ```

- [ ] No imports of deleted modules:
  ```bash
  grep -r "succession import" api/ src/ | wc -l  # Should be 0
  ```

- [ ] No calls to deleted methods:
  ```bash
  grep -r "trigger_succession\|generate_execution_prompt" src/ api/ | grep -v "DEPRECATED\|#" | wc -l  # Should be 0
  ```

- [ ] All tests pass:
  ```bash
  pytest tests/ -v
  ```

- [ ] Frontend builds successfully:
  ```bash
  cd frontend && npm run build
  ```

- [ ] "Hand Over" button works with new endpoint (manual UI test)

## Risk Assessment

**RISK: MEDIUM** - Removes user-facing endpoint and UI functionality

**Mitigation**:
- New simple-handover system already implemented (Handover 0461f)
- Frontend button can be updated to use new endpoint
- Slash command can be updated to use new endpoint
- No data loss - succession mechanism still exists, just different implementation
- Comprehensive grep ensures all callers are found

**Rollback Plan**:
- Git revert commit
- Restore succession.py from git history
- Restore deleted service method and schemas
- Re-run fresh install

## Dependencies

- **Depends on**: 0700b (schema cleanup for succession-related columns already done)
- **Blocks**: None (independent cleanup)
- **Related**: Simple-handover endpoint must be verified working before this cleanup

## Estimated Impact

- **Files deleted**: 1 (succession.py endpoint file)
- **Lines removed**: ~400 lines
  - Endpoint file: ~200 lines
  - Service method: ~100 lines
  - Schemas: ~60 lines
  - Prompt generator method: ~40 lines
- **Files modified**: 4-6 (router registration, frontend components, service, schemas, prompt generator)
- **Test updates**: Remove tests for trigger-succession endpoint

## Notes

- **Critical**: Verify simple-handover endpoint is fully functional before removing old system
- Frontend "Hand Over" button must be tested after migration
- `/gil_handover` slash command must be tested after migration
- This handover removes FUNCTIONALITY (not just dead code), requires careful testing
- Document the migration in devlog for future reference
