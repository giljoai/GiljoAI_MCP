# Handover Prompt for Agent: Execute 0124

## Primary Directive

Execute Handover 0124: Agent Endpoint Consolidation

**Quality Standards:**
- Production-grade code
- Commercially viable quality
- No shortcuts
- No band-aids
- No technical debt

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

- [ ] All code follows existing patterns from 0123
- [ ] Comprehensive docstrings on all functions
- [ ] Type hints throughout
- [ ] Error handling and logging
- [ ] Unit tests >80% coverage
- [ ] Integration tests for full workflows
- [ ] All linting passes
- [ ] No performance degradation
- [ ] API documentation updated
- [ ] Completion document written
- [ ] REFACTORING_ROADMAP updated to mark 0124 complete

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
