# Handover Prompt for Agent: Execute 0124

## Primary Directive

Execute Handover 0124: Agent Endpoint Consolidation

**Quality Standards:**
- Production-grade code
- Commercially viable quality
- No shortcuts
- No band-aids
- No technical debt

## 🚨 CRITICAL CONSTRAINTS

### ZERO UI/UX Changes
**The application looks and behaves IDENTICALLY to users.**
- Backend code refactoring ONLY
- NO changes to user interfaces
- NO changes to user workflows
- NO visual modifications

### API COMPATIBILITY GUARANTEE
**ALL API routes remain IDENTICAL. Frontend sees ZERO breaking changes.**
- Same HTTP methods (GET, POST, PUT, DELETE)
- Same route paths (`/api/v1/agent-jobs/*`)
- Same request/response formats (add fields OK, remove fields NOT OK)
- Same error codes and formats
- NO route renames or moves
- NO breaking schema changes

### AGGRESSIVE CLEANUP POLICY
**DELETE old code completely. NO facades, NO zombie code, NO orphans.**
- Delete `agents.py` completely after migration
- Delete `orchestration.py` completely after migration
- Remove spawn_agents from `projects_lifecycle.py`
- Delete ALL old agent-related test files
- Clean up all imports and dependencies
- Remove all commented code
- NO "backward compatibility facades"
- NO keeping old files "just in case"

**Rationale:** Project is fully backed up. We can rollback entire refactoring if needed. Aggressive cleanup prevents future confusion and code rot.

## Required Reading (IN ORDER)

### 1. Read First: Refactoring Roadmap
**File:** `handovers/REFACTORING_ROADMAP_0120-0129.md`
**Purpose:** Understand the overall refactoring strategy and how 0124 fits into the bigger picture

### 2. Read Second: Previous Handover Completion (0123)
**File:** `handovers/completed/0123_tool_accessor_phase2_extract_services-COMPLETE.md`
**Purpose:** Understand the service extraction pattern that 0124 builds upon

### 3. Read Third: Orchestration Documentation
**File:** `handovers/0122_orchestration_documentation.md`
**Purpose:** Deep understanding of the orchestration architecture and OrchestrationService

### 4. Read Fourth: The Target Handover
**File:** `handovers/0124_agent_endpoint_consolidation.md`
**Purpose:** Detailed implementation plan and specifications for this handover

## Execution Instructions

After reading all four documents in order:

1. **Create a Todo List** - Use TodoWrite to track all phases and tasks
2. **Follow the 5-Phase Plan** - Documented in 0124 handover scope
3. **Test Everything** - >80% coverage minimum
4. **Validate Syntax** - All files must be syntactically correct
5. **Update Documentation** - REFACTORING_ROADMAP and completion document
6. **Commit and Push** - Clear commit messages following git best practices

## Phase Breakdown (from 0124)

- **Phase 1:** Create agent_jobs module structure (1 day)
- **Phase 2:** Implement spawn endpoints (1-2 days)
- **Phase 3:** Implement lifecycle endpoints (1-2 days)
- **Phase 4:** Implement status & query endpoints (1-2 days)
- **Phase 5:** Testing & validation (2-3 days)

## Success Criteria

✅ All agent endpoints accessible via `/api/v1/agent-jobs/*`
✅ All endpoints use OrchestrationService (no direct DB access)
✅ File sizes reduced to 150-200 lines per module
✅ Backward compatibility maintained
✅ >80% test coverage on all new code
✅ All tests passing
✅ API documentation complete
✅ Completion document written

## Additional Context (Read If Needed)

### Core Service Documentation
- `src/giljo_mcp/services/orchestration_service.py` - The service you'll be using
- `tests/unit/test_orchestration_service.py` - Service test patterns

### Existing Endpoint Patterns
- `api/endpoints/projects/` - Example of modularized endpoints (from 0125 plan)
- Current agent endpoints scattered in various files (you'll discover during execution)

### Database Models
- `src/giljo_mcp/models/mcp_agent_job.py` - The 7-state job lifecycle model
- `src/giljo_mcp/models/agent.py` - Legacy 4-state model (being deprecated)

### Architecture References
- Thin Client Architecture - Agents fetch missions from database
- WebSocket Broadcasting - Via HTTP bridge to orchestrator
- Multi-tenancy - All operations must respect tenant isolation

## Key Architectural Decisions to Maintain

1. **OrchestrationService Only** - All agent/job operations go through OrchestrationService
2. **Thin Endpoints** - Minimal logic, delegate to service layer
3. **Pydantic Validation** - All request/response models validated
4. **Tenant Isolation** - Never bypass tenant checks
5. **Consistent Error Handling** - Use HTTPException with proper status codes
6. **No Direct Database Access** - Service layer handles all DB operations

## Quality Checklist Before Completion

### Code Quality
- [ ] All code follows existing patterns from 0123
- [ ] Comprehensive docstrings on all functions
- [ ] Type hints throughout
- [ ] Error handling and logging
- [ ] All linting passes (ruff, mypy)
- [ ] No commented code remaining
- [ ] No unused imports
- [ ] No zombie/orphan code

### Testing (CRITICAL - User Requirement)
- [ ] Unit tests >80% coverage on all new code
- [ ] Integration tests for **normal use cases** (happy path)
- [ ] Integration tests for **edge cases** (boundary conditions)
- [ ] Integration tests for **error scenarios** (failure handling)
- [ ] Multi-tenant isolation tests
- [ ] Performance tests (< 5% degradation)
- [ ] End-to-end workflow tests
- [ ] ALL tests passing

### Code Cleanup (CRITICAL - Aggressive Policy)
- [ ] Deleted `agents.py` completely
- [ ] Deleted `orchestration.py` completely
- [ ] Removed spawn_agents from `projects_lifecycle.py`
- [ ] Deleted ALL old agent test files
- [ ] Verified NO references to deleted files (grep check)
- [ ] Cleaned up ALL imports
- [ ] NO facades or compatibility wrappers remaining

### API Compatibility (CRITICAL - Zero Breaking Changes)
- [ ] All routes at `/api/v1/agent-jobs/*` unchanged
- [ ] Same HTTP methods
- [ ] Same request/response formats
- [ ] Same error codes
- [ ] Frontend tests still pass (if available)
- [ ] API documentation reflects current state only

### Documentation
- [ ] API documentation updated
- [ ] Completion document written
- [ ] REFACTORING_ROADMAP updated to mark 0124 complete
- [ ] Architecture diagrams updated (if needed)

## Git Workflow

**Branch:** Create new branch: `claude/handover-0124-agent-endpoint-consolidation-[SESSION_ID]`
**Commits:** Clear, descriptive messages following established patterns
**Push:** When complete, push to remote with `-u` flag

## Final Instruction

Execute Handover 0124 with the same level of quality and thoroughness demonstrated in Handover 0123. This is production code that will serve real users in a commercial product.

**Read the four documents in order, then execute.**

---

**Created:** 2025-11-10
**For:** Handover 0124 Execution
**Quality Standard:** Production-grade, commercially viable, no shortcuts
