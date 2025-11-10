# GiljoAI MCP - Technical Debt Analysis Report

**Generated**: November 10, 2025  
**Analysis Scope**: Complete codebase review (276K Python, 5.5K Frontend)  
**Overall Technical Debt Score**: VERY HIGH (Critical refactoring needed)

---

## EXECUTIVE SUMMARY

The GiljoAI MCP codebase demonstrates significant architectural debt from rapid iteration:

### Key Issues Found:
1. **2 God Objects** over 2000 lines with single-responsibility violations
2. **4 Different Agent Management Systems** with overlapping functionality
3. **2 Parallel Messaging Queue Implementations** (AgentCommunicationQueue vs MessageQueue)
4. **Duplicate Route Registration** (same router at different paths)
5. **333 HANDOVER/DEPRECATED/TODO Comments** indicating ongoing technical debt
6. **6 Overlapping Orchestration Systems** with unclear responsibilities

### Business Impact:
- **Maintainability**: Very Difficult - hard to understand data flow
- **Testing**: Challenging - tightly coupled components
- **Onboarding**: High effort - developers must understand multiple parallel systems
- **Bug Risk**: High - changes in one area risk breaking others
- **Feature Velocity**: Reduced due to complexity

---

## MONOLITHIC FILES REQUIRING REFACTORING

### CRITICAL PRIORITY

#### 1. ToolAccessor (2677 lines, 69 methods)
**Location**: `/src/giljo_mcp/tools/tool_accessor.py`

A "god object" class handling 10+ business domains:
- Projects (12 methods)
- Agents (8 methods)
- Messages (7 methods)
- Tasks (5 methods)
- Context/Vision (8 methods)
- Templates (4 methods)
- Orchestration (10+ methods)
- Job Management (8 methods)
- Other (7 methods)

**Impact**: Any domain change risks breaking others; impossible to unit test independently

**Recommendation**: Split into 8-10 focused service classes (ProjectService, AgentService, MessageService, TaskService, ContextService, TemplateService, OrchestrationService, JobService)

---

#### 2. ProjectOrchestrator (2012 lines, 39 methods)
**Location**: `/src/giljo_mcp/orchestrator.py`

Mixes orchestration engine with agent spawning, context management, and handoff logic.

**Recommendation**: Extract into ProjectLifecycleManager, AgentSpawner, ContextMonitor, HandoffCoordinator

---

### HIGH PRIORITY

#### 3. Projects Endpoint (2444 lines, 23 routes)
**Location**: `/api/endpoints/projects.py`

Mixing CRUD, lifecycle management, business logic, and agent integration.

#### 4. Templates Endpoint (1602 lines)
**Location**: `/api/endpoints/templates.py`

Mixing CRUD, version history, validation, system template protection, and WebSocket updates.

#### 5. Products Endpoint (1506 lines)
**Location**: `/api/endpoints/products.py`

Mixing CRUD, vision handling, chunking, agent jobs, and context searching.

#### 6. Agent Jobs Endpoint (1343 lines)
**Location**: `/api/endpoints/agent_jobs.py`

Mixing job lifecycle, messaging, spawning, health monitoring with dual message patterns.

---

## PARALLEL LEGACY/NEW SYSTEMS

### CRITICAL: Four Different Agent Management Systems

| File | Lines | Status | Routes |
|------|-------|--------|--------|
| agents.py | 447 | DEPRECATED (Handover 0116) - Commented Out | POST `/`, GET `/`, Health, Decommission |
| agent_management.py | 545 | ACTIVE | Vision upload, Job creation, Context search |
| agent_jobs.py | 1343 | PRIMARY | Full job lifecycle, messaging, spawning |
| agent_templates.py | 250 | ACTIVE | Template CRUD |

**Impact**: Developers unclear which endpoint to use; duplicated functionality

**Fix**: Consolidate into single agent_jobs.py endpoint with sub-routes

---

### HIGH: Two Messaging Queue Implementations

#### AgentCommunicationQueue (838 lines)
- Handover 0019: JSONB-based message queue
- Used by: agent_coordination.py, tool_accessor.py, orchestrator.py
- Simple JSONB storage in Job.messages

#### MessageQueue (838 lines)
- Advanced features: Priority routing, Circuit breaker, Dead-letter queue, Stuck message detection
- Used by: message.py
- RoutingEngine with 3+ rule types

**Impact**: Two parallel systems create maintenance burden

**Fix**: Merge MessageQueue into AgentCommunicationQueue or vice versa

---

### HIGH: Six Agent Communication Files (Overlapping Responsibilities)

1. **agent_communication.py** (326 lines) - Tool registration
2. **agent_communication_queue.py** (838 lines) - Message queue
3. **agent_coordination.py** (811 lines) - Job coordination tools
4. **agent_coordination_external.py** (657 lines) - External tools
5. **agent_messaging.py** (469 lines) - Messaging tools
6. **message.py** (521 lines) - Message tool functions

**Recommendation**: Consolidate into single agent_communication module

---

### HIGH: Duplicate Route Registration

**File**: `/api/app.py` (Lines 770-773)

```python
# Same router mounted at TWO different paths:
app.include_router(orchestration.router, prefix="/api/orchestrator")
app.include_router(orchestration.router, prefix="/api/v1/orchestration")  # Handover 0109

app.include_router(prompts.router, prefix="/api/prompts")
app.include_router(prompts.router, prefix="/api/v1/prompts")  # Handover 0109
```

**Impact**: 
- Clients confused about which endpoint to use
- Maintenance burden: changes need testing on both paths
- API documentation confusion

**Fix**: Choose canonical paths (prefer `/api/v1/*`), deprecate old paths

---

### HIGH: Six Overlapping Orchestration Systems

- **orchestrator.py** (2012 lines) - Core orchestration
- **mission_planner.py** (1563 lines) - Mission planning  
- **orchestrator_succession.py** (543 lines) - Succession handling
- **job_coordinator.py** (497 lines) - Job coordination
- **agent_job_manager.py** (1030 lines) - Job management
- **workflow_engine.py** (415 lines) - Workflow execution

**Unclear**: Which module handles what? How do they coordinate?

---

## FRONTEND ANALYSIS

### Good News: Frontend is Clean!

**Technical Debt**: LOW (only 16 TODO/FIXME comments in entire frontend)

**Large Files** (but appropriately scoped):
- projectTabs.js (536 lines) - Pinia store
- websocket.js (506 lines) - WebSocket service
- agentFlow.js (448 lines) - Pinia store
- api.js (438 lines) - API client

**Minor Issue**: WebSocket split into websocket.js + flowWebSocket.js - could consolidate

---

## DETAILED RECOMMENDATIONS (PRIORITY ORDER)

### Phase 1: Critical (2-3 weeks)
1. ✓ Remove agents.py endpoint - stop half-commenting, fully remove with migration guide
2. ✓ Consolidate MessageQueue systems - merge the 838-line implementations
3. ✓ Start ToolAccessor refactoring - extract ProjectService first

### Phase 2: Consolidation (3-4 weeks)
4. Complete ToolAccessor split into 8 focused services
5. Consolidate Agent endpoints - merge agent_management.py into agent_jobs.py
6. Fix duplicate route registration - standardize on /api/v1/* paths
7. Split Projects endpoint (2444 lines) into ProjectCRUD + ProjectLifecycle + ProjectCompletion

### Phase 3: Cleanup (2-3 weeks)
8. Remove deprecated code (auth_legacy.py, Product.vision_* fields)
9. Consolidate orchestration systems - document relationships between 6 modules
10. Clean up config migration - remove v2.x to v3.0 handling (assume v3.0+)
11. Frontend: Consolidate websocket.js + flowWebSocket.js

### Phase 4: Testing (ongoing)
- Add integration tests for consolidated endpoints
- Load testing on new architecture
- Document API contract changes

---

## IMPLEMENTATION ESTIMATES

| Task | Effort | Timeline |
|------|--------|----------|
| ToolAccessor refactoring | High | 2-3 weeks |
| Agent endpoint consolidation | High | 1 week |
| Message queue merge | High | 1 week |
| Projects endpoint split | Medium | 1-2 weeks |
| Orchestration consolidation | Medium | 2 weeks |
| Complete refactoring | **TOTAL: 8-10 weeks** | |

---

## KEY FILES REFERENCED

### Backend Structure
```
/src/giljo_mcp/
├── tools/
│   ├── tool_accessor.py          (2677 lines) - GOD OBJECT ⚠️
│   ├── orchestration.py          (1392 lines)
│   ├── context.py                (1486 lines)
│   ├── task.py                   (1277 lines)
│   ├── agent.py                  (954 lines)
│   ├── agent_coordination.py      (811 lines)
│   ├── agent_coordination_external.py (657 lines)
│   ├── message.py                (521 lines)
│   └── agent_messaging.py         (469 lines)
├── orchestrator.py               (2012 lines) - GOD OBJECT ⚠️
├── mission_planner.py            (1563 lines)
├── agent_job_manager.py          (1030 lines)
├── agent_communication_queue.py   (838 lines) - DUPLICATE SYSTEM ⚠️
├── message_queue.py              (838 lines) - DUPLICATE SYSTEM ⚠️
└── models.py                     (2271 lines - 30 classes, ACCEPTABLE)

/api/endpoints/
├── projects.py                   (2444 lines) ⚠️
├── products.py                   (1506 lines) ⚠️
├── templates.py                  (1602 lines) ⚠️
├── agent_jobs.py                 (1343 lines) ⚠️
├── agents.py                     (447 lines) - DEPRECATED ⚠️
├── agent_management.py           (545 lines) - OVERLAPS ⚠️
└── auth.py                       (1055 lines)
```

### Frontend Structure
```
/frontend/src/
├── stores/              (Generally good, 3.5-5.3K lines)
├── services/            (Some consolidation opportunity)
├── composables/         (Well organized)
└── components/          (Not analyzed, component files typically small)
```

---

## DATABASE & ORM PATTERNS

**Status**: Good
- Using modern SQLAlchemy 2.0 `select()` patterns (356+ instances)
- No deprecated `query()` patterns
- Proper async/await patterns

**Issue**: Complex v2→v3 migration logic in config_manager.py

---

## TECHNICAL DEBT METRICS

```
Total Code Review Comments (HANDOVER/TODO/FIXME): 333
  - By file: orchestrator.py (3), model.py (multiple), config_manager.py (multiple)

Large Files (>300 lines): 34 files
  - Acceptable: 8 files (tests, install scripts, models)
  - Problematic: 26 files requiring refactoring

Duplicate Systems Detected: 3
  1. Messaging: AgentCommunicationQueue vs MessageQueue
  2. Agent Management: 4 endpoints
  3. Orchestration: 6 overlapping modules

Code Duplication: ~15% estimated (especially agent-related code)

Frontend Technical Debt: LOW
  - Only 16 TODO/FIXME comments (vs 333 in backend)
  - No duplicate systems
  - Appropriate use of Pinia stores
```

---

## RISK ASSESSMENT

**Risk of Refactoring**: MEDIUM
- Large codebase but well-tested
- Clear entry points (API endpoints)
- Good separation between frontend and backend

**Risk of NOT Refactoring**: HIGH
- Increasing maintenance burden
- Higher onboarding costs for new developers
- More bugs from tight coupling
- Slower feature development

---

## CONCLUSION

The GiljoAI MCP codebase has grown organically through multiple "Handover" phases without proper architectural refactoring. Key architectural problems:

1. **God Objects** (ToolAccessor, ProjectOrchestrator) making testing impossible
2. **Parallel Systems** (4 agent endpoints, 2 message queues) creating confusion
3. **Poor Separation of Concerns** (projects endpoint with 2444 lines)
4. **Dead/Deprecated Code** still in repository (agents.py)

**Recommended Action**: Prioritize refactoring of ToolAccessor and agent systems (Phases 1-2) to unblock feature development and reduce maintenance burden.

The frontend is relatively clean and requires minimal refactoring.

---

*For questions about specific files or recommendations, refer to the sections above or examine the referenced file paths.*
