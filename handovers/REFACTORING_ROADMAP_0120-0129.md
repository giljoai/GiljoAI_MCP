---
**Document Type:** Master Refactoring Roadmap
**Version:** 1.1
**Created:** 2025-11-10
**Last Updated:** 2025-11-10
**Status:** In Progress (0121 ✅ COMPLETE)
**Timeline:** 8-10 weeks (after Handover 0119 completion)
**Scope:** Handovers 0120-0129
**Execution Strategy:** Sequential, one handover at a time
---

# GiljoAI MCP Refactoring Roadmap (0120-0129)

## 🎯 Mission Statement

**Transform the GiljoAI MCP backend from rapid-iteration prototype to production-ready architecture while maintaining the working orchestration system.**

---

## 🚨 CRITICAL CONSTRAINTS

### NO UI/UX CHANGES
**ZERO visual or user experience changes. The application looks and behaves IDENTICALLY to users.**
- ✅ Backend code refactoring ONLY
- ✅ Internal code organization changes
- ❌ NO changes to user interfaces
- ❌ NO changes to user workflows
- ❌ NO visual modifications

### API COMPATIBILITY GUARANTEE
**ALL API routes remain IDENTICAL. Frontend sees ZERO breaking changes.**
- ✅ Same HTTP methods (GET, POST, PUT, DELETE)
- ✅ Same route paths (`/api/v1/projects/*`, `/api/v1/templates/*`, etc.)
- ✅ Same request/response formats (add fields OK, remove fields NOT OK)
- ✅ Same error codes and formats
- ❌ NO route renames or moves
- ❌ NO breaking schema changes

**Example:**
```python
# BEFORE: All in one file
# api/endpoints/projects.py
POST /api/v1/projects -> create_project()

# AFTER: Split into modules
# api/endpoints/projects/crud.py
POST /api/v1/projects -> create_project()  # SAME ROUTE!
```

### AGGRESSIVE CLEANUP POLICY
**DELETE old code completely. NO facades, NO zombie code, NO orphans.**
- ✅ Delete old endpoint files after migration
- ✅ Remove all unused functions and tests
- ✅ Clean up imports and dependencies
- ✅ Remove commented code
- ❌ NO "backward compatibility facades" unless CRITICAL
- ❌ NO keeping old files "just in case"
- ❌ NO leaving dead code around

**Rationale:** Project is fully backed up. We can rollback entire refactoring if needed. Aggressive cleanup prevents future confusion.

### INTEGRATION TESTING MANDATE
**Every handover MUST pass comprehensive integration tests.**
- ✅ Normal use cases (happy path)
- ✅ Edge cases (boundary conditions)
- ✅ Error scenarios (failure handling)
- ✅ Multi-tenant isolation
- ✅ End-to-end workflows
- ✅ Performance benchmarks (< 5% degradation)

---

## 📋 Execution Philosophy

**Decision (2025-11-10):** Complete one handover at a time. Do NOT pre-create all handover documents.

### Rationale

**Why Sequential Execution:**
1. **Learn and Adapt:** Each handover reveals insights that inform the next
2. **Reduce Rework:** Early assumptions often change; sequential prevents cascading updates
3. **Maintain Flexibility:** Can reprioritize based on discoveries
4. **Prevent Scope Creep:** Focus on one task at a time ensures quality
5. **Avoid Planning Paralysis:** Don't spend weeks planning what may change

**Process:**
1. Complete current handover
2. Document learnings in completion summary
3. Review roadmap and adjust if needed
4. Create detailed plan for next handover only
5. Execute next handover with full focus
6. Repeat

**Example from 0121:**
- Handover document estimated 12 methods
- Actual implementation found 10 methods
- If we had pre-created 0122-0129, all would reference wrong numbers
- Sequential approach allowed us to adapt in real-time

### What We Create Upfront

**DO Create:**
- ✅ High-level roadmap (this document) - overall vision and sequence
- ✅ Scope documents for next 1-2 handovers - enough detail to start
- ✅ Dependency map - what blocks what

**DON'T Create:**
- ❌ Detailed specs for all 10 handovers - too much uncertainty
- ❌ Line-by-line implementation plans - will change
- ❌ Complete test plans for future work - premature

### Current Approach

**Completed:**
- ✅ 0120: Message Queue Consolidation (COMPLETE)
- ✅ 0121: ToolAccessor Phase 1 (COMPLETE)
- ✅ 0122: Orchestration Documentation (COMPLETE)

**Ready to Execute:**
- 📝 0123: ToolAccessor Phase 2 (scope created, ready to start)

**Future (create when ready):**
- ⏳ 0124-0129: Will create detailed specs after 0122/0123 learnings

---

## 📊 Current State (Post-0119, Including 0090)

### ✅ What's Working
- **Orchestration System:** First successful end-to-end test completed (EVALUATION_FIRST_TEST)
- **MCP Protocol:** 100% tool success rate
- **MCP Tool Metadata:** Enhanced with rich metadata (Handover 0090)
- **Agent Execution:** Proven 3-agent parallel execution, 76.2K tokens total
- **API Surface:** Clean after Handover 0119 (broken endpoints fixed, dual routes removed)
- **Frontend:** Clean architecture (only 16 TODO comments)
- **Database Layer:** SQLAlchemy 2.0, 100% async/await compliance

### 🔗 Recent Parallel Work (Handover 0090)
**Completed before/during roadmap planning:**
- Added rich metadata to all 25 MCP tools
- Updated `api/endpoints/mcp_tools.py` (572 lines changed)
- Updated `api/endpoints/messages.py` (90 lines changed)
- Updated `api/endpoints/agent_jobs.py` (1 line change)
- Added comprehensive test coverage for MCP metadata

**Integration Points:**
- **Handover 0120:** messages.py may use message queues - verify compatibility after consolidation
- **Handovers 0121-0129:** No conflicts - MCP metadata is orthogonal to architectural refactoring

### ⚠️ What Needs Fixing
- **2 God Objects:** ToolAccessor (2,677 lines), ProjectOrchestrator (2,012 lines)
- **2 Message Queues:** Duplicate implementations (838 lines each)
- **6 Orchestration Systems:** Unclear boundaries
- **4 Monolithic Endpoints:** 1,300-2,400 lines each
- **Duplicate Agent Systems:** 4 overlapping endpoint files

**Technical Debt:** ~15,000 lines of problematic code across 26 files

---

## 🗺️ Refactoring Phases Overview

### Phase 0: Prerequisites ✅
**Handover 0119** - API Harmonization & Backward Compatibility Cleanup
- **Duration:** 1-2 days
- **Status:** Must be completed first
- **Impact:** Fixes broken frontend, removes dual routes, deletes agents.py (448 lines)

---

### Phase 1: Critical Backend Architecture (2-3 weeks)

**Handover 0120** - Message Queue Consolidation
- **Duration:** 1 week
- **Agent Budget:** 200K tokens (4 agents)
- **Impact:** Remove 838 lines of duplicate code
- **Deliverable:** Single AgentMessageQueue with advanced features

**Handover 0121** - ToolAccessor Phase 1: Extract ProjectService
- **Duration:** 1-2 weeks
- **Agent Budget:** 200K tokens (3 agents)
- **Impact:** Reduce ToolAccessor by 377 lines, create ProjectService pattern
- **Deliverable:** Standalone ProjectService, proven extraction pattern

**Handover 0122** - Orchestration Systems Documentation
- **Duration:** 3-5 days
- **Agent Budget:** 200K tokens (2 agents)
- **Impact:** Clarify relationships between 6 orchestration modules
- **Deliverable:** Architecture diagrams, consolidation recommendations

**Phase 1 Totals:**
- **Duration:** 2-3 weeks
- **Lines Removed/Refactored:** ~1,215 lines
- **Risk Level:** MEDIUM
- **Priority:** CRITICAL

---

### Phase 2: Service Layer Completion (3-4 weeks)

**Handover 0123** - ToolAccessor Phase 2: Extract Remaining Services
- **Duration:** 2-3 weeks
- **Agent Budget:** 200K tokens × 7 agents (parallel execution!)
- **Services Extracted:**
  1. AgentService (8 methods, ~300 lines)
  2. MessageService (7 methods, ~250 lines)
  3. TaskService (5 methods, ~200 lines)
  4. ContextService (8 methods, ~350 lines)
  5. TemplateService (4 methods, ~150 lines)
  6. OrchestrationService (10+ methods, ~400 lines)
  7. JobService (8 methods, ~300 lines)
- **Impact:** Eliminate ToolAccessor god object completely (~1,950 lines extracted)
- **Deliverable:** 8 focused services, ToolAccessor retired

**Handover 0124** - Agent Endpoint Consolidation
- **Duration:** 1 week
- **Agent Budget:** 200K tokens (2 agents)
- **Impact:** Merge 3 agent endpoint files into 1 (agent_jobs.py)
- **Deliverable:** Single agent endpoint with clear sub-routes

**Phase 2 Totals:**
- **Duration:** 3-4 weeks
- **Lines Removed/Refactored:** ~2,500 lines
- **Risk Level:** MEDIUM
- **Priority:** HIGH

---

### Phase 3: Endpoint Modularization (2-3 weeks)

**Handover 0125** - Projects Endpoint Modularization
- **Duration:** 1 week
- **Agent Budget:** 200K tokens (3 agents)
- **Impact:** Split projects.py (2,444 lines) into 3 focused modules
  - projects_crud.py (CRUD operations)
  - projects_lifecycle.py (lifecycle management)
  - projects_completion.py (completion workflow)
- **Deliverable:** Modular project endpoints using ProjectService

**Handover 0126** - Templates & Products Endpoint Modularization
- **Duration:** 1-2 weeks
- **Agent Budget:** 200K tokens × 2 (parallel: templates + products)
- **Impact:** Split templates.py (1,602 lines) and products.py (1,506 lines)
- **Deliverable:** Modular endpoints using service layer

**Phase 3 Totals:**
- **Duration:** 2-3 weeks
- **Lines Refactored:** ~5,500 lines
- **Risk Level:** LOW-MEDIUM
- **Priority:** MEDIUM

---

### Phase 4: Deep Cleanup (1-2 weeks)

**Handover 0127** - Deprecated Code Removal
- **Duration:** 3-5 days
- **Agent Budget:** 200K tokens (2 agents)
- **Impact:** Remove auth_legacy.py, Product.vision_* fields, v2.x migration code
- **Deliverable:** Cleaned codebase, removed dead code

**Handover 0128** - Frontend Consolidation
- **Duration:** 2-3 days
- **Agent Budget:** 200K tokens (1 agent)
- **Impact:** Merge websocket.js + flowWebSocket.js
- **Deliverable:** Simplified frontend services

**Phase 4 Totals:**
- **Duration:** 1-2 weeks
- **Lines Removed:** ~500 lines
- **Risk Level:** LOW
- **Priority:** LOW

---

### Phase 5: Testing & Validation (ongoing)

**Handover 0129** - Integration Testing
- **Duration:** 1 week
- **Agent Budget:** 200K tokens (3 agents: test writer, load tester, documenter)
- **Impact:** Comprehensive test coverage for refactored architecture
- **Deliverable:** Integration tests, load tests, updated documentation

**Phase 5 Totals:**
- **Duration:** 1 week
- **Lines Added:** ~1,000 lines (tests)
- **Risk Level:** LOW
- **Priority:** MEDIUM

---

## 📈 Cumulative Impact

### Code Metrics

| Phase | Duration | Lines Removed/Refactored | Files Changed | Risk | Priority |
|-------|----------|--------------------------|---------------|------|----------|
| 0 (0119) | 1-2 days | 448 | 15-20 | MEDIUM | CRITICAL |
| 1 (0120-0122) | 2-3 weeks | 1,215 | 8-10 | MEDIUM | CRITICAL |
| 2 (0123-0124) | 3-4 weeks | 2,500 | 12-15 | MEDIUM | HIGH |
| 3 (0125-0126) | 2-3 weeks | 5,500 | 6-8 | LOW-MEDIUM | MEDIUM |
| 4 (0127-0128) | 1-2 weeks | 500 | 8-10 | LOW | LOW |
| 5 (0129) | 1 week | +1,000 (tests) | 5-10 | LOW | MEDIUM |
| **TOTAL** | **8-10 weeks** | **~10,163 lines** | **54-73 files** | - | - |

**Net Result:**
- **Remove:** ~9,163 lines of duplicate/problematic code
- **Add:** ~1,000 lines of tests + ~3,000 lines of services = ~4,000 lines
- **Net Reduction:** ~5,163 lines
- **Quality Improvement:** Massive (god objects → focused services)

---

### Architectural Improvements

**Before (Post-0119):**
- ❌ 2 god objects (ToolAccessor, ProjectOrchestrator)
- ❌ 2 duplicate message queues
- ❌ 6 unclear orchestration systems
- ❌ 4 monolithic endpoints (1,300-2,400 lines)
- ❌ 4 overlapping agent systems
- ⚠️ Hard to test (tight coupling)
- ⚠️ Hard to maintain (mixed concerns)

**After (Post-0129):**
- ✅ 8 focused service classes (200-400 lines each)
- ✅ Single message queue (AgentMessageQueue)
- ✅ Documented orchestration architecture
- ✅ Modular endpoints (300-800 lines each)
- ✅ Single agent endpoint
- ✅ Easy to test (dependency injection)
- ✅ Easy to maintain (single responsibility)

---

## 🤖 Agent Execution Strategy

### Token Budget Planning

**Available Resources:**
- **Main Orchestrator:** 200K tokens
- **Sub-Agents:** 200K tokens each
- **Proven Success:** 3 agents in parallel (EVALUATION_FIRST_TEST)

**Execution Approach:**
- **Sequential handovers** (0120 → 0121 → ... → 0129)
- **Parallel agents within handovers** where possible
- **Clear success criteria** before proceeding to next handover

### Parallelization Opportunities

**Handover 0123** - ToolAccessor Phase 2:
- **7 agents in parallel** (one per service extraction)
- Each agent: ~60K tokens (well within budget)
- Massive time savings (2-3 weeks → potentially 1 week)

**Handover 0126** - Templates & Products:
- **2 agents in parallel** (one per endpoint)
- Each agent: ~80K tokens
- Timeline: 1-2 weeks → potentially 1 week

**Total Parallelization Potential:**
- **Savings:** ~2-3 weeks off 8-10 week timeline
- **Optimistic Timeline:** 6-7 weeks with aggressive parallelization

---

## 🎯 Success Criteria

### Phase-Level Success

Each handover must achieve:
1. ✅ **All tests pass** - Unit + integration + regression
2. ✅ **EVALUATION_FIRST_TEST passes** - Zero regressions
3. ✅ **Code review approved** - Senior developer sign-off
4. ✅ **Documentation complete** - Architecture diagrams, migration guides
5. ✅ **Performance maintained** - No slowdowns

### Overall Success (Post-0129)

- [ ] **Zero god objects** - All large classes refactored
- [ ] **Single patterns** - One message queue, one agent endpoint
- [ ] **>80% test coverage** - All services well-tested
- [ ] **Clean architecture** - Service layer, modular endpoints
- [ ] **Maintainable** - New developers can onboard quickly
- [ ] **Scalable** - Can add features without fear
- [ ] **Production-ready** - Can launch v3.0 with confidence

---

## 🚨 Risk Management

### Overall Risks

**Risk #1: Breaking Working System**
- **Mitigation:** EVALUATION_FIRST_TEST after every handover
- **Contingency:** Rollback capability for each handover

**Risk #2: Timeline Overruns**
- **Mitigation:** Each handover independently scoped
- **Contingency:** Can pause after any handover, still improved

**Risk #3: Pattern Doesn't Work**
- **Mitigation:** Phase 1 (0121) is proof-of-concept
- **Contingency:** Adjust pattern before Phase 2

**Risk #4: Agent Budget Exceeded**
- **Mitigation:** Each handover scoped to 200K tokens
- **Contingency:** Split handover into sub-handovers

### Risk by Phase

| Phase | Risk Level | Mitigation Strategy |
|-------|-----------|---------------------|
| 1 (0120-0122) | MEDIUM | Extensive testing, gradual rollout |
| 2 (0123-0124) | MEDIUM | Proven pattern from Phase 1 |
| 3 (0125-0126) | LOW-MEDIUM | Service layer already exists |
| 4 (0127-0128) | LOW | Dead code removal is low-risk |
| 5 (0129) | LOW | Testing phase, no functional changes |

---

## 📚 Dependencies & Blockers

### Hard Prerequisites

**Before Starting:**
- ✅ Handover 0119 complete (API surface clean)
- ✅ EVALUATION_FIRST_TEST baseline established

### Sequential Dependencies

**Cannot Proceed Until Previous Completes:**
- 0121 depends on 0120 (needs clean message queue)
- 0123 depends on 0121 (needs proven extraction pattern)
- 0124 depends on 0123 (needs service layer)
- 0125 depends on 0123 (needs ProjectService)

### Parallel Opportunities

**Can Run Simultaneously:**
- 0122 can run parallel to 0121 (documentation vs implementation)
- 0127 + 0128 can run parallel (backend + frontend cleanup)
- Within 0123: 7 service extractions in parallel
- Within 0126: templates + products in parallel

---

## 📅 Timeline Options

### Option A: Sequential Execution (Conservative)
**Duration:** 10-12 weeks
- All handovers sequential
- Thorough testing between each
- Lower risk, slower delivery

### Option B: Moderate Parallelization (Recommended)
**Duration:** 8-10 weeks
- Parallel agents within handovers (0123, 0126)
- Sequential handovers
- Balanced risk/speed

### Option C: Aggressive Parallelization (Fast Track)
**Duration:** 6-7 weeks
- Maximum parallelization where possible
- Concurrent handovers where safe (e.g., 0122 + 0121)
- Higher risk, faster delivery

**Recommendation:** Option B (Moderate) - proven pattern from EVALUATION_FIRST_TEST

---

## 🎓 Lessons from EVALUATION_FIRST_TEST

### What We Learned

**Proven:**
- ✅ 3 agents can work in parallel successfully
- ✅ 200K token budget is generous (agents used 24-40K each)
- ✅ MCP tools work flawlessly (100% success rate)
- ✅ Agent coordination works
- ✅ Message passing works

**Implications for Refactoring:**
- Can confidently spawn 7 agents in Handover 0123
- Token budgets are conservative (good safety margin)
- Orchestration system is solid foundation
- Message queue refactoring won't break coordination

**Key Insight:** The system works. Now make it maintainable.

---

## 📖 Documentation Strategy

### Per-Handover Documentation

Each handover creates:
1. **Handover Document** - Detailed implementation plan
2. **Architecture Diagrams** - Visual representation of changes
3. **Migration Guide** - How to adapt existing code
4. **Test Plan** - Coverage and validation strategy

### Overall Documentation

**Created During Roadmap:**
- `REFACTORING_ROADMAP_0120-0129.md` (this document)
- `TECHNICAL_DEBT_ANALYSIS.md` (updated with handover series)
- `SERVICES_ARCHITECTURE.md` (created in 0121, updated throughout)
- `ORCHESTRATION_ARCHITECTURE.md` (created in 0122)

**Updated Post-Completion:**
- README.md - Architecture overview
- CHANGELOG.md - All changes documented
- Developer onboarding docs

---

## 🔄 Feedback Loop

### After Each Handover

1. **Retrospective:**
   - What went well?
   - What could be improved?
   - Pattern adjustments needed?

2. **Update Roadmap:**
   - Adjust timeline if needed
   - Update risk assessments
   - Refine future handover scopes

3. **Document Lessons:**
   - Add to handover completion summary
   - Feed into next handover planning

---

## 🚀 Getting Started

### Immediate Next Steps

1. **Complete Handover 0119** (if not done)
   - Fix broken frontend
   - Remove dual routes
   - Delete agents.py

2. **Start Handover 0120** (Message Queue Consolidation)
   - Read handover document: `handovers/0120_message_queue_consolidation.md`
   - Spawn implementer agent
   - Follow day-by-day plan

3. **Track Progress**
   - Update handover status as complete
   - Move to `handovers/completed/` directory
   - Update TECHNICAL_DEBT_ANALYSIS.md

---

## 📊 Progress Tracking

### Handover Status Board

| ID | Handover | Status | Duration | Completion Date |
|----|----------|--------|----------|-----------------|
| 0119 | API Harmonization | **PREREQUISITE** | 1-2 days | - |
| 0120 | Message Queue Consolidation | Planning | 1 week | - |
| 0121 | ToolAccessor Phase 1 | **✅ COMPLETE** | 1 day | 2025-11-10 |
| 0122 | Orchestration Documentation | **✅ COMPLETE** | 1 day | 2025-11-10 |
| 0123 | ToolAccessor Phase 2 | **✅ COMPLETE** | 1 day | 2025-11-10 |
| 0124 | Agent Endpoint Consolidation | **✅ COMPLETE** | 1 day | 2025-11-10 |
| 0125 | Projects Modularization | **✅ COMPLETE** | 1 day | 2025-11-10 |
| 0126 | Templates & Products Modularization | **Ready** | 1-2 weeks | - |
| 0127 | Deprecated Code Removal | Planning | 3-5 days | - |
| 0128 | Frontend Consolidation | Planning | 2-3 days | - |
| 0129 | Integration Testing | Planning | 1 week | - |

**0123 Final Results:**
- ✅ **ALL SERVICES EXTRACTED** (5/5): TemplateService, TaskService, MessageService, ContextService, OrchestrationService
- ✅ **ToolAccessor Reduced**: 2,324 → ~1,200 lines (-48% reduction, -1,124 lines)
- ✅ **Production Quality**: >80% test coverage on all services (95 total unit tests)
- ✅ **Zero Breaking Changes**: 100% backward compatible
- ✅ **Unblocks**: Handovers 0124, 0125, 0126 now ready to proceed

**Update this table after each handover completion!**

---

## 🎯 Vision: Post-Refactoring Architecture

### Service Layer

```
src/giljo_mcp/services/
├── project_service.py       (350 lines) - Project CRUD + lifecycle
├── agent_service.py          (300 lines) - Agent spawning + management
├── message_service.py        (250 lines) - Message routing + delivery
├── task_service.py           (200 lines) - Task management
├── context_service.py        (350 lines) - Context + vision handling
├── template_service.py       (150 lines) - Template CRUD
├── orchestration_service.py  (400 lines) - Orchestration logic
└── job_service.py            (300 lines) - Job lifecycle management
```

### Endpoint Layer (Focused on HTTP)

```
api/endpoints/
├── projects_crud.py          (600 lines) - Project CRUD
├── projects_lifecycle.py     (500 lines) - Project lifecycle
├── projects_completion.py    (400 lines) - Project completion
├── agent_jobs.py             (1000 lines) - Consolidated agent endpoint
├── templates_crud.py         (500 lines) - Template CRUD
├── templates_versions.py     (400 lines) - Template versioning
├── products_crud.py          (500 lines) - Product CRUD
├── products_vision.py        (400 lines) - Product vision
└── ... (other endpoints)
```

### Infrastructure Layer

```
src/giljo_mcp/
├── agent_message_queue.py    (900 lines) - Single message queue
├── orchestrator.py           (1500 lines) - Orchestration engine (reduced)
├── mission_planner.py        (1500 lines) - Mission planning
└── ... (other infrastructure)
```

**Total Lines:** Similar to current, but much better organized!

---

## 🌟 Success Vision

**After completing this roadmap:**

1. **Developer Experience:**
   - New developers onboard in days, not weeks
   - Can understand architecture from diagrams
   - Can find code quickly (services named logically)

2. **Testing:**
   - Unit test individual services in isolation
   - Integration tests verify service interactions
   - 80%+ code coverage across services

3. **Maintenance:**
   - Changes to projects don't affect agents
   - Can refactor services independently
   - Clear boundaries reduce bugs

4. **Scalability:**
   - Can add new services without touching existing code
   - Service layer makes API endpoints thin
   - Easy to add features post-launch

5. **Production Readiness:**
   - Clean architecture inspires confidence
   - Can launch v3.0 knowing system is maintainable
   - Technical debt paid down before scaling

---

## 📞 Support & Questions

**If you get stuck:**
1. Review the specific handover document (e.g., `0120_message_queue_consolidation.md`)
2. Check `TECHNICAL_DEBT_ANALYSIS.md` for context
3. Refer to `EVALUATION_FIRST_TEST.md` for baseline
4. Consult completed handovers in `handovers/completed/` for patterns

**Remember:** This is a marathon, not a sprint. Each handover makes the system better!

---

**Let's build something amazing! 🚀**

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Status:** Ready for Execution
**Next Handover:** 0120 (Message Queue Consolidation)
