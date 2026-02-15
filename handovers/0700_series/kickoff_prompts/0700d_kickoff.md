# Handover 0700d Kickoff: Legacy Succession Cleanup

**Agent**: Deep-Researcher (PRIMARY) + Backend-Tester (SECONDARY)
**Estimated Duration**: 2-3 hours
**Risk Level**: LOW (visualization confirms orphan status)
**Parallel Execution**: Can run alongside 0700b (no dependencies)

---

## Series Context

**Status**: 3 of 12 complete
- ✅ **0700a** - Light mode removal (complete)
- ✅ **0700** - Cleanup index creation (complete)
- ✅ **0701** - Dependency visualization (complete)
- 🔄 **0700d** - You are here (Legacy succession cleanup)
- ⏳ **0700b-h** - Remaining deprecated purge handovers

**Total Series Impact**: ~2000 lines removed (1500 deprecated, 400 dead code)

---

## Mission Scope

**Objective**: Remove deprecated Agent ID Swap succession system in favor of 360 Memory-based session continuity.

**Strategic Context**:
- Handover 0461f (Nov 2025) deprecated "Agent ID Swap" succession
- New system: `simple_handover.py` endpoint (360 Memory-based)
- Old system: `succession.py` endpoint + `trigger_succession()` method
- **No external users** - safe pre-release cleanup

**Key Decision Point**: This is FUNCTIONALITY removal (not just dead code), requires verification that new system is fully operational.

---

## 🎯 Visualization Confirmation (from 0701)

**CONFIRMED SAFE TO DELETE**:
```
api/endpoints/agent_jobs/succession.py - ZERO dependents
```

**Evidence**:
- File appears in `dependency_analysis.json` orphan_modules list (line 12)
- No other Python modules import from succession.py
- Endpoint is dynamically loaded via FastAPI router (import not visible to static analysis)
- **Conclusion**: File can be deleted with HIGH CONFIDENCE

**LOW-RISK Classification**: The visualization proves this file is isolated from the codebase dependency graph.

---

## What Still Needs Verification

While the file itself is orphaned, check these related components:

### 1. Service Method Caller Analysis
**Target**: `OrchestrationService.trigger_succession()` method
- Location: `src/giljo_mcp/services/orchestration_service.py:2167`
- Status: Marked DEPRECATED (0461f)
- **Action**: Use `grep` to find all callers before removing

### 2. Schema Usage Check
**Targets**:
- `SuccessionRequest` (schemas.py:185)
- `SuccessionResponse`
- `SuccessionStatusResponse`
- `InitiateHandoverResponse`
- `ManualSuccessionResponse`

**Action**: Verify no API consumers use these schemas (frontend, MCP tools, tests)

### 3. Frontend Integration
**Targets**:
- "Hand Over" button in `AgentCardEnhanced.vue`
- `/gil_handover` slash command

**Action**: Ensure these use `simple_handover` endpoint (not old succession endpoint)

---

## Phase-by-Phase Execution

### Phase 1: Context Acquisition (5 min)

**Required Reads**:
1. ✅ `handovers/0700_series/orchestrator_state.json` - Series status
2. ✅ `handovers/0700_series/comms_log.json` - Messages for 0700d
3. ✅ `handovers/0700_series/doc_impacts.json` - Docs to update
4. ✅ `handovers/0700_series/0700d_legacy_succession_cleanup.md` - Full spec

**Context Questions**:
- What did 0701 visualization reveal? (Already answered: succession.py is orphan)
- Are there blockers from 0700a or 0700? (Check comms_log)
- Which docs reference succession endpoint? (Check doc_impacts.json)

---

### Phase 2: Scope Investigation (15 min)

**Investigation Tasks**:

1. **Verify simple_handover is operational**:
   ```bash
   grep -r "simple.handover" api/endpoints/
   grep -r "simple_handover" frontend/src/
   ```

2. **Find all trigger_succession callers**:
   ```bash
   grep -r "trigger_succession" src/ api/ frontend/ | grep -v "DEPRECATED" | grep -v "#"
   ```

3. **Find all succession schema usage**:
   ```bash
   grep -r "SuccessionRequest\|SuccessionResponse\|ManualSuccessionResponse" src/ api/ frontend/
   ```

4. **Check frontend "Hand Over" button**:
   ```bash
   grep -r "Hand Over\|HandOver\|hand-over" frontend/src/components/
   grep -r "/trigger-succession" frontend/src/
   ```

5. **Check slash command**:
   ```bash
   grep -r "gil_handover" src/ api/
   ```

**Output**: List of all files to modify, with line numbers

---

### Phase 3: Execution (Main Work - 1 hour)

**Removal Order** (leaf nodes first):

#### Step 1: Delete Orphan Endpoint
```bash
rm api/endpoints/agent_jobs/succession.py
```

**Verification**:
```bash
test ! -f api/endpoints/agent_jobs/succession.py
```

#### Step 2: Remove Endpoint Registration
**Check**: `api/endpoints/agent_jobs/__init__.py` or `api/app.py`
```bash
grep -n "succession" api/endpoints/agent_jobs/__init__.py api/app.py
```

**Action**: Remove import and `router.include_router()` call

#### Step 3: Remove Service Method
**Target**: `src/giljo_mcp/services/orchestration_service.py:2167`
```python
# DELETE THIS METHOD:
async def trigger_succession(
    self,
    job_id: str,
    tenant_key: str,
    ...
) -> dict:
    # ~100 lines...
```

**Verification**: No callers found in Phase 2

#### Step 4: Remove Deprecated Schemas
**Target**: `src/giljo_mcp/models/schemas.py`

Delete these classes:
- `SuccessionRequest` (line 185+)
- `SuccessionResponse`
- `SuccessionStatusResponse`
- `InitiateHandoverResponse`
- `ManualSuccessionResponse` (if exists)

**Search Pattern**:
```bash
grep -n "class.*Succession.*:" src/giljo_mcp/models/schemas.py
```

#### Step 5: Update Frontend (if needed)
**If** "Hand Over" button or `/gil_handover` calls old endpoint:

**Before**:
```javascript
POST /api/agent-jobs/{job_id}/trigger-succession
```

**After**:
```javascript
POST /api/agent-jobs/{job_id}/simple-handover
```

**Files to Check**:
- `frontend/src/components/projects/AgentCardEnhanced.vue`
- `frontend/src/components/StatusBoard/ActionIcons.vue`

#### Step 6: Remove Deprecated Prompt Method (if not used)
**Target**: `src/giljo_mcp/thin_prompt_generator.py:964`

**Method**: `generate_execution_prompt()`

**Verification**:
```bash
grep -r "generate_execution_prompt" src/ api/ | grep -v "DEPRECATED" | grep -v "#"
```

**Action**: Delete if no callers found

---

### Phase 4: Documentation (20 min)

**Check doc_impacts.json** for entries with:
- `handover_ids: ["0700d"]`
- `keywords: ["succession", "handover", "agent-jobs"]`

**Likely Docs to Update**:
- `docs/SERVICES.md` - OrchestrationService methods
- `docs/ORCHESTRATOR.md` - Succession protocol
- `CLAUDE.md` - Succession system references
- API docs (if exist) - Remove trigger-succession endpoint

**Update Actions**:
1. Remove code examples showing old succession endpoint
2. Remove references to "Agent ID Swap" succession
3. Update to describe `simple_handover` as authoritative
4. Remove `trigger_succession()` from service method lists

**Update doc_impacts.json**:
```json
{
  "status": "updated",
  "updated_by": "0700d",
  "updated_at": "[ISO timestamp]"
}
```

---

### Phase 5: Communication (10 min)

**Write to comms_log.json**:

```json
{
  "id": "[generate UUID]",
  "timestamp": "[ISO 8601]",
  "from_handover": "0700d",
  "to_handovers": ["0700e", "0700f", "0700g", "0700h"],
  "type": "info",
  "subject": "Legacy succession system removed successfully",
  "message": "Deleted api/endpoints/agent_jobs/succession.py (confirmed orphan with 0 dependents). Removed OrchestrationService.trigger_succession() method and 5 succession-related schemas (SuccessionRequest, SuccessionResponse, etc.). Frontend 'Hand Over' button now uses simple_handover endpoint exclusively. No breaking changes detected - all tests passing. ~400 lines removed total.",
  "files_affected": [
    "api/endpoints/agent_jobs/succession.py",
    "src/giljo_mcp/services/orchestration_service.py",
    "src/giljo_mcp/models/schemas.py",
    "api/endpoints/agent_jobs/__init__.py"
  ],
  "action_required": false,
  "context": {
    "lines_removed": 400,
    "schemas_removed": ["SuccessionRequest", "SuccessionResponse", "SuccessionStatusResponse", "InitiateHandoverResponse", "ManualSuccessionResponse"],
    "replacement_system": "simple_handover.py (360 Memory-based)",
    "visualization_confirmation": "succession.py confirmed orphan (0 dependents) by 0701"
  }
}
```

**Rationale**: Inform downstream handovers that succession cleanup is complete and simple_handover is the new standard.

---

### Phase 6: Testing & Commit (30 min)

**Test Strategy**:

1. **Run affected tests**:
   ```bash
   pytest tests/services/test_orchestration_service.py -v
   pytest tests/api/test_agent_jobs.py -v
   pytest tests/integration/ -v -k handover
   ```

2. **Verify no import errors**:
   ```bash
   python -c "from api.app import app; print('✓ API imports OK')"
   python -c "from src.giljo_mcp.services.orchestration_service import OrchestrationService; print('✓ Service imports OK')"
   ```

3. **Frontend build check**:
   ```bash
   cd frontend && npm run build
   ```

4. **Manual UI test** (if frontend changed):
   - Launch agent
   - Click "Hand Over" button
   - Verify handover completes successfully

**Expected Results**:
- All tests pass (or pre-existing failures documented)
- No import errors
- Frontend builds cleanly
- Hand Over button functional

**Update orchestrator_state.json**:
```json
{
  "handovers": {
    "0700d": {
      "status": "complete",
      "completed_at": "[ISO timestamp]",
      "worker_session_id": "[session ID]",
      "docs_updated": ["docs/SERVICES.md", "docs/ORCHESTRATOR.md", "CLAUDE.md"],
      "lines_removed": 400,
      "tests_status": "passing"
    }
  }
}
```

**Commit Format**:
```bash
git add -A
git commit -m "cleanup(0700d): Remove legacy Agent ID Swap succession system

Deprecated Agent ID Swap succession fully removed in favor of 360 Memory-based
session continuity (simple_handover.py). Visualization (0701) confirmed
succession.py is orphan with zero dependents - safe deletion.

Changes:
- DELETE api/endpoints/agent_jobs/succession.py (~200 lines)
- REMOVE OrchestrationService.trigger_succession() method (~100 lines)
- REMOVE 5 succession schemas: SuccessionRequest, SuccessionResponse,
  SuccessionStatusResponse, InitiateHandoverResponse, ManualSuccessionResponse (~60 lines)
- REMOVE generate_execution_prompt() from ThinClientPromptGenerator (~40 lines)
- UPDATE frontend 'Hand Over' button to use simple_handover endpoint
- REMOVE succession router registration from api/app.py

Docs Updated:
- docs/SERVICES.md (OrchestrationService methods)
- docs/ORCHESTRATOR.md (succession protocol)
- CLAUDE.md (succession references)

Total Impact: ~400 lines removed
Visualization Proof: succession.py confirmed orphan (0 dependents) by 0701
Replacement: simple_handover.py (Handover 0461f)

```

---

## Communication Requirements

### To Orchestrator
**Report when**:
- ✅ Investigation complete (list all files to modify)
- ✅ Execution 50% complete (endpoint deleted, service method removed)
- ✅ All tests passing
- ✅ Handover complete

### To Downstream Handovers (0700e-h)
**Via comms_log.json**:
- Succession cleanup complete
- simple_handover is authoritative system
- No breaking changes introduced

---

## Success Criteria

- [ ] `api/endpoints/agent_jobs/succession.py` deleted
- [ ] No imports of succession module exist
- [ ] `OrchestrationService.trigger_succession()` removed
- [ ] All succession schemas removed from schemas.py
- [ ] Frontend uses simple_handover endpoint exclusively
- [ ] All tests pass (or pre-existing failures documented)
- [ ] Documentation updated (SERVICES.md, ORCHESTRATOR.md, CLAUDE.md)
- [ ] Comms log entry written
- [ ] Orchestrator state updated
- [ ] Commit created with proper format

---

## Risk Mitigation

**LOW-RISK Handover** because:
1. ✅ Visualization confirms succession.py is orphan (0 dependents)
2. ✅ Replacement system (simple_handover.py) already operational (0461f)
3. ✅ No external users - pre-release cleanup
4. ✅ Comprehensive test coverage for new system

**Rollback Plan**:
```bash
git revert HEAD
python install.py  # Restore database if needed
```

**Blockers to Watch For**:
- Frontend still calling old endpoint (fix in Phase 3 Step 5)
- Tests relying on succession schemas (update to use simple_handover)
- Documentation lag (fix in Phase 4)

---

## Recommended Subagent Workflow

### Deep-Researcher (PRIMARY)
**Use for**:
- Phase 2 investigation (finding all succession references)
- Grep searches for callers, schema usage, frontend integration
- Verification that simple_handover is operational

### Backend-Tester (SECONDARY)
**Use for**:
- Phase 6 testing (service layer, integration tests)
- Verifying no import errors after deletion
- Confirming test suite still passes

---

## Key Takeaway

**This is a LOW-RISK handover with HIGH CONFIDENCE** thanks to the 0701 visualization. The dependency graph proves succession.py is isolated - no other modules depend on it. The main work is verification that frontend and slash commands use the new system, then safe deletion.

**Parallel Execution**: This handover has NO DEPENDENCIES on 0700b, so it can run concurrently.

---

**Good luck! The visualization did the heavy lifting - you're just cleaning up an orphaned file. 🧹**
