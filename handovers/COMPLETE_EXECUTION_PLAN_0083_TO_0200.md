# Complete Execution Plan: Projects 0083 → 0200+

**Created**: 2025-01-12
**Status**: Active Roadmap
**Scope**: All remaining work from handovers 0083-0118, 0130 series, and 0131-0200 roadmap
**Total Duration**: 14-20 weeks
**Goal**: Production-ready GiljoAI MCP Server

---

## 🚀 Quick Reference: Execution Order & Tool Selection

### Sequential Execution Order (Do in This Exact Order)

| # | Handover | Tool | Duration | Why This Tool | Can Parallelize? |
|---|----------|------|----------|---------------|------------------|
| 1 | 0130e | **CLI** | 4-6 hrs | DB + API wiring + testing | ❌ No (DB work) |
| 2 | 0118 | **CCW** | 3-4 days | Template updates (pure code) | ❌ No (depends on 0130e) |
| 3 | 0130a | **CLI** | 2-3 hrs | Runtime testing + validation | ❌ No (requires live system) |
| 4 | 0111 | **CLI** | 3-4 hrs | WebSocket debugging + DB fix | ❌ No (DB + diagnostics) |
| 5 | 0130b | **CLI** | 2-3 hrs | File deletion + cleanup | ❌ No (local filesystem) |
| 6 | 0117 | **CCW** | 5-6 hrs | Templates + frontend colors | ✅ Can run with #7 |
| 7 | 0095 | **CCW** | 2 weeks | API endpoints + docs | ✅ Can run with #6 |
| 8 | 0114 | **CCW** | 2 weeks | Frontend UI (Vue components) | ⚠️ After 0118 (needs messages) |

### Decision Point: 0130c/d or Skip?
- If YES → 9a & 9b (CCW, can parallelize)
- If NO → Skip to Phase 6 (0131+)

| 9a | 0130c | **CCW** | 1-2 days | Frontend component refactor | ✅ Can run with 9b |
| 9b | 0130d | **CCW** | 2-3 days | Frontend API centralization | ✅ Can run with 9a |

### Feature Development (0131-0160)
| Range | Category | Tool | Duration | Parallelization |
|-------|----------|------|----------|-----------------|
| 0131-0135 | Prompt Tuning | **CCW** | 2-3 weeks | ✅ Can split across 2-3 CCW sessions |
| 0136-0140 | Orchestrator Opt | **Mix** | 2-3 weeks | ⚠️ Backend (CLI), Frontend (CCW) |
| 0141-0145 | Slash Commands | **CLI** | 2-3 weeks | ❌ MCP tools + DB (sequential) |
| 0146-0150 | Close-Out | **CCW** | 1-2 weeks | ✅ Mostly frontend + templates |
| 0112 | Context UX | **CCW** | 8-10 hrs | ✅ Pure frontend |
| 0083 | Slash Harmony | **CLI** | 2-3 hrs | ❌ MCP registration + testing |

### Launch Preparation (0200-0239)
| Range | Category | Tool | Duration | Parallelization |
|-------|----------|------|----------|-----------------|
| 0200-0209 | Infrastructure | **CLI** | 1-2 weeks | ❌ Deployment + DB + monitoring |
| 0210-0219 | Open Source | **CCW** | 1 week | ✅ Documentation (parallel) |
| 0220-0229 | QA | **CLI** | 1-2 weeks | ❌ Testing + validation |
| 0230-0239 | Launch | **CCW** | 1 week | ✅ Docs + videos (parallel) |

---

## 🎯 Tool Selection Guide

### Use **Claude Code CLI (Local)** When:
- ✅ Database migrations or schema changes
- ✅ Testing with live backend/database
- ✅ Debugging runtime issues (WebSocket, API)
- ✅ File system operations (delete, move, cleanup)
- ✅ Local environment setup/validation
- ✅ MCP tool registration and testing
- ✅ Performance diagnostics
- ✅ Security testing
- ✅ Cross-platform installation testing

### Use **Claude Code Web (CCW)** When:
- ✅ Pure code changes (no DB required)
- ✅ Frontend work (Vue components, styles)
- ✅ Template updates (agent prompts)
- ✅ Documentation writing
- ✅ API endpoint creation (non-DB logic)
- ✅ Multiple independent tasks (parallelization)
- ✅ Large refactoring (leverage cloud tokens)

### Workflow Pattern:
```
CCW: Code on cloud → Push to GitHub branch
 ↓
YOU: Merge into master/working branch
 ↓
CLI: Pull locally → Test → Diagnose issues
 ↓
CCW: Fix issues → Push to GitHub
 ↓
Repeat until stable
```

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Critical Path](#critical-path)
3. [Phase Breakdown](#phase-breakdown)
4. [Gantt Chart](#gantt-chart)
5. [Dependencies Map](#dependencies-map)
6. [Risk Mitigation](#risk-mitigation)
7. [Decision Points](#decision-points)
8. [Phase Gate Criteria](#phase-gate-criteria)
9. [Rollback Procedures](#rollback-procedures)
10. [Resource Requirements](#resource-requirements)
11. [Success Metrics](#success-metrics)
12. [Tool Selection Matrix](#tool-selection-matrix)

---

## Executive Summary

### Current State (2025-01-12)

**Completed Work**:
- ✅ 0120-0129 series: Service layer, OWASP security, succession (22 handovers)
- ✅ 0130a: WebSocket V2 migration (build complete, runtime testing pending)
- ✅ 0083-0118 audit: 32 handovers archived, 10 active identified
- ✅ New roadmap 0131-0200 created (feature dev + launch prep)

**Critical Finding**:
- 🔴 **Messaging infrastructure broken**: 0130e (infrastructure) BLOCKS 0118 (agent behavior)
- 🔴 **First execution test**: ZERO inter-agent messages sent (templates don't use messaging)
- 🟡 **WebSocket real-time updates broken**: UI requires page refresh (0111)

### Execution Strategy

**3-Phase Approach**:

1. **Foundation Phase (Weeks 1-5)**: Fix critical infrastructure
   - Fix messaging (0130e → 0118)
   - Validate WebSocket V2 (0130a testing)
   - Fix real-time updates (0111)
   - Clean zombie code (0130b)
   - Add 8-role system (0117)
   - Production UI (0114)
   - Multi-CLI support (0095)

2. **Feature Phase (Weeks 6-12)**: Build missing functionality
   - Prompt tuning for agents
   - Orchestrator optimization
   - Slash command system
   - Project close-out procedures
   - Context UX enhancements

3. **Launch Phase (Weeks 13-16)**: Production readiness
   - One-liner installation (0200)
   - Open source compliance (0210-0219)
   - Security & QA (0220-0229)
   - Marketing & support (0230-0239)

**Total Duration**: 14-20 weeks to production launch

---

## Critical Path

```
CRITICAL PATH: 0130e → 0118 → 0117 & 0114
└─ Total: ~3 weeks (blocking all feature development)

WEEK 1-2: MESSAGING INFRASTRUCTURE (CRITICAL)
┌──────────────────────────────────────────────┐
│ 0130e (4-6 hrs) → 0118 (3-4 days)            │
│ Infrastructure     Agent Behavior            │
│ BLOCKS: 0118      BLOCKS: 0117, 0114         │
└──────────────────────────────────────────────┘

WEEK 2: VALIDATION & QUICK WINS (HIGH PRIORITY)
┌──────────────────────────────────────────────┐
│ 0130a Testing (2-3 hrs) | 0111 Fix (3-4 hrs)│
│ WebSocket V2 Validate   | Real-time Updates │
└──────────────────────────────────────────────┘

WEEK 3: CLEANUP & ENHANCEMENT (MEDIUM PRIORITY)
┌──────────────────────────────────────────────┐
│ 0130b (2-3 hrs) → 0117 (5-6 hrs)             │
│ Zombie Code       8-Role System              │
│                   Depends: 0118 complete     │
└──────────────────────────────────────────────┘

WEEK 4-5: PRODUCTION POLISH (PARALLEL)
┌────────────────────────┬─────────────────────┐
│ 0114 (2 weeks)         │ 0095 (2 weeks)      │
│ Jobs Tab UI            │ Streamable HTTP     │
│ Depends: 0118 complete │ Independent         │
└────────────────────────┴─────────────────────┘

DECISION POINT: Continue 0130c/d or skip to 0131?

WEEK 6-12: FEATURE DEVELOPMENT (0131-0199)
WEEK 13-16: LAUNCH PREPARATION (0200-0239)
```

**Critical Dependency**: Everything after Week 2 depends on 0130e + 0118 completion

---

## Phase Breakdown

### Phase 0: Pre-Execution ✅ COMPLETE

**Duration**: Completed
**Status**: ✅ All tasks complete

**Completed Tasks**:
- [x] 0130a WebSocket V2 migration (build succeeds, 3.15s, 1672 modules)
- [x] Security test fixes (Project description, job_id length)
- [x] 0130b-e handovers created (zombie code, components, API, messaging)
- [x] 0083-0118 audit (10 active, 32 archived)
- [x] Roadmap 0131-0200 created (feature dev + launch prep)
- [x] Roadmap 0120-0130 retired (completion date: 2025-11-12)
- [x] Backup branch created (`backup_branch_before_websocketV2`)

**Deliverables**:
- `handovers/0130a_MIGRATION_TEST_RESULTS.md`
- `handovers/0083-0118_AUDIT_REPORT.md`
- `handovers/REFACTORING_ROADMAP_0131-0200.md`
- `handovers/REFACTORING_ROADMAP_0120-0130.md` (retired)
- `handovers/0130_SERIES_CLOSURE_SUMMARY.md`
- `handovers/0130_SERIES_EXECUTION_PLAN.md`
- `handovers/0130e_fix_inter_agent_messaging.md`

---

### Phase 1: Critical Messaging Infrastructure

**Duration**: 4-5 days (Week 1-2)
**Priority**: 🔴 P0 CRITICAL
**Blocking**: All feature development

#### 1.1 Handover 0130e: Fix Inter-Agent Messaging Infrastructure

**Effort**: 4-6 hours
**Priority**: P0 (BLOCKS 0118)
**Risk**: MEDIUM

**Problem**:
- Message router exists but NOT registered in `api/app.py`
- WebSocket events not broadcasting
- API endpoints return 404
- Frontend can't reach message endpoints

**Tasks**:
```python
# Phase 1: Investigation (1 hour)
- [ ] Trace message flow: Frontend → API → Database → WebSocket
- [ ] Identify missing router registration
- [ ] Check WebSocket broadcast wiring

# Phase 2: Backend Wiring (2 hours)
- [ ] Register message router in api/app.py
- [ ] Wire WebSocket broadcast to message events
- [ ] Test POST /api/messages endpoint
- [ ] Test GET /api/messages endpoint
- [ ] Test WebSocket message broadcasts

# Phase 3: Frontend Integration (1 hour)
- [ ] Verify Message Center receives messages
- [ ] Test message filtering by agent
- [ ] Test real-time message updates

# Phase 4: Testing (1 hour)
- [ ] End-to-end test: Send message → Database → WebSocket → Frontend
- [ ] Test multi-tenant isolation
- [ ] Test message types (BLOCKER, QUESTION, PROGRESS, COMPLETE, USER)

# Phase 5: Documentation & Archival (30 mins)
- [ ] Update 0130e handover with findings
- [ ] Archive as 0130e-C.md
```

**Success Criteria**:
- ✅ POST /api/messages returns 201 (not 404)
- ✅ Messages appear in database
- ✅ WebSocket broadcasts to subscribed clients
- ✅ Frontend Message Center displays messages
- ✅ No cross-tenant leakage

**Blockers**: None
**Blocks**: 0118 (Agent Messaging Protocol)

**Files Modified**:
- `api/app.py` (register router)
- `api/endpoints/messages.py` (verify endpoints)
- Potentially: `api/websocket_manager.py` (broadcast wiring)

---

#### 1.2 Handover 0118: Agent Messaging Protocol Implementation

**Effort**: 3-4 days
**Priority**: P0 (BLOCKS 0117, 0114)
**Risk**: HIGH (template complexity)
**Depends On**: 0130e complete

**Problem**:
- Templates exist but don't use messaging
- First execution test: ZERO messages sent
- Complex dependencies fail (no coordination)
- User interaction broken (no message handling)

**Tasks**:

```markdown
# Phase 1: Orchestrator Template Updates (1 day)
- [ ] Add communication protocol section (clear headers, examples)
- [ ] Add welcome message after spawning agent
  └─ "Hello {agent_name}, I'm orchestrator {id}. Mission: {summary}"
- [ ] Add periodic message monitoring loop
  └─ "Check messages every 5-10 actions (not every action)"
- [ ] Add message type handlers
  ├─ BLOCKER: Escalate to user, log, pause workflow
  ├─ QUESTION: Forward to user or answer if trivial
  ├─ PROGRESS: Log, update UI via WebSocket
  ├─ COMPLETE: Mark agent job complete, trigger dependents
  └─ USER: Forward to target agent
- [ ] Add dependency notification logic
  └─ Send DEPENDENCY_MET when prerequisite completes
- [ ] Add status broadcasts
  └─ Send workflow status every major milestone
- [ ] Add escalation handling
  └─ If agent blocked >5 min, notify user

# Phase 2: Agent Template Updates (1 day)
- [ ] Update all 6 agent templates (implementer, tester, reviewer, etc.)
- [ ] Add "Check messages BEFORE starting work" instruction
- [ ] Add periodic message check (every 5-10 actions)
  └─ Use MCP tool: receive_messages(agent_id, limit=10)
- [ ] Add progress reporting after milestones
  └─ "After completing major task, send PROGRESS message"
- [ ] Add blocker reporting protocol
  └─ "If blocked, send BLOCKER message immediately"
- [ ] Add completion broadcast
  └─ "When done, send COMPLETE message with summary"
- [ ] Add user message handling
  └─ "If USER message received, respond within 30 seconds"

# Phase 3: Dependency Coordination (1-2 days)
- [ ] Implement auto-detect dependencies in mission_planner.py
  └─ Parse mission for "depends on", "requires", "after" keywords
- [ ] Add dependency waiting logic to agent templates
  └─ "If dependencies exist, check status before starting"
  └─ "Wait for DEPENDENCY_MET message (max 10 min)"
- [ ] Add timeout and escalation for deadlocks
  └─ "If waiting >10 min, send BLOCKER to orchestrator"
- [ ] Add DEPENDENCY_MET notification system
  └─ Orchestrator sends when prerequisite agent completes

# Phase 4: User Message Handling (1 day)
- [ ] Add user message detection to all templates
  └─ Filter messages with type=USER
- [ ] Add user message response protocol
  └─ Acknowledge within 30 seconds
  └─ Provide status update or answer question
- [ ] Add orchestrator user message forwarding
  └─ If user sends to specific agent, orchestrator routes it

# Phase 5: Testing & Validation (1-2 days)
- [ ] Test Workflow #1: Simple messaging
  └─ 2 agents, no dependencies, exchange PROGRESS messages
- [ ] Test Workflow #2: Dependency coordination
  └─ Analyzer depends on implementer, wait for DEPENDENCY_MET
- [ ] Test Workflow #3: Blocker handling
  └─ Introduce intentional error, verify BLOCKER escalation
- [ ] Test Workflow #4: User mid-execution message
  └─ Send message to agent during work, verify response
- [ ] Test Workflow #5: Multi-terminal mode
  └─ Test with Codex CLI or Gemini CLI (external agent execution)
- [ ] Complete validation checklist
  └─ Orchestrator uses messaging: ✅
  └─ All 6 agents use messaging: ✅
  └─ Message hub usage >0: ✅
  └─ Dependency coordination works: ✅
  └─ User messages responded to: ✅
  └─ Blocker escalation works: ✅
```

**Success Criteria**:
- ✅ Message hub usage: >0 messages (baseline: 0 in first test)
- ✅ Agent communication rate: ≥1 message per major milestone
- ✅ Dependency coordination: 100% success rate
- ✅ User message response time: <30 seconds for acknowledgment
- ✅ Blocker resolution: 100% escalation rate when blocked

**Risk Mitigation**:
- **Template complexity**: Use clear section headers, code examples, keep instructions concise
- **Message spam**: Define clear rules (milestones only, not every action)
- **Dependency deadlocks**: Add cycle detection, 10-minute timeout, orchestrator override
- **Performance impact**: Check messages every 5-10 actions, not every action
- **Backward compatibility**: Test with original TinyContacts workflow

**Blockers**: 0130e (infrastructure must work first)
**Blocks**: 0117 (8-role system needs messaging), 0114 (Message Center needs real messages)

**Files Modified**:
- `src/giljo_mcp/templates/orchestrator_template.py`
- `src/giljo_mcp/templates/implementer_template.py`
- `src/giljo_mcp/templates/tester_template.py`
- `src/giljo_mcp/templates/reviewer_template.py`
- `src/giljo_mcp/templates/analyzer_template.py`
- `src/giljo_mcp/templates/architect_template.py`
- `src/giljo_mcp/templates/documenter_template.py`
- `src/giljo_mcp/mission_planner.py` (dependency auto-detect)

**Archive**: `handovers/completed/0118_agent_messaging_protocol_implementation-C.md`

---

### Phase 2: Validation & Quick Wins

**Duration**: 1 day (Week 2)
**Priority**: 🟡 P1 HIGH
**Goal**: Validate 0130a migration, fix user-facing issues

#### 2.1 Handover 0130a: Runtime Testing

**Effort**: 2-3 hours
**Priority**: P1
**Risk**: LOW (rollback available)

**Tasks**:
```markdown
- [ ] Start frontend: cd frontend && npm run dev
- [ ] Navigate to http://localhost:7274
- [ ] Login successfully
- [ ] Verify connection status chip shows "Connected" (green)
- [ ] Check browser console (no errors)
- [ ] Create new project → Appears without refresh
- [ ] Update project status → UI updates immediately
- [ ] Create agent job → Status updates in real-time
- [ ] Stop backend server → Connection status shows "Reconnecting" (yellow)
- [ ] Restart backend server → Connection status shows "Connected" (green)
- [ ] Click connection status chip → Debug panel opens
- [ ] Verify statistics (messages sent/received)
- [ ] Test "Force Reconnect" button
- [ ] Test "Send Test" button
- [ ] Navigate between routes 20 times
- [ ] Check Chrome DevTools Memory (no leaks)
```

**Success Criteria**:
- ✅ All 17 checklist items pass
- ✅ No console errors
- ✅ Real-time updates work without refresh
- ✅ Reconnection works automatically
- ✅ Debug panel functional
- ✅ No memory leaks

**If Successful**:
- Archive `handovers/0130a_websocket_consolidation.md` as `0130a-C.md`
- Delete backup files (`.backup-0130a`) as part of 0130b

**If Failures**:
- Document issues in `handovers/0130a_RUNTIME_ISSUES.md`
- Create fix handover (0130a-fix)
- Consider rollback to `backup_branch_before_websocketV2`

**Rollback Procedure** (if critical failures):
```bash
cd /f/GiljoAI_MCP
git checkout backup_branch_before_websocketV2
cd frontend && npm run build
```

---

#### 2.2 Handover 0111: WebSocket Real-Time Updates & Orchestrator ID Bug

**Effort**: 3-4 hours
**Priority**: P1
**Risk**: MEDIUM (may require FastAPI state management changes)

**Problems**:
1. WebSocket broadcasts don't work from MCP tool context
2. Orchestrator ID changes on every "Stage Project" click

**Tasks**:

```markdown
# Phase 1: Investigation (1 hour)
- [ ] Determine why WebSocket broadcast fails from MCP context
  └─ Trace connection between `api.app.state` and MCP tool execution
  └─ Check if FastAPI state accessible from MCP thread
  └─ Verify WebSocket manager initialization
  └─ Check broadcast method signature and async handling

# Phase 2: Fix #1 - WebSocket Broadcasts (1-2 hours)
- [ ] Implement solution (likely: pass WebSocket manager to MCP tools)
  └─ Option A: Pass manager as parameter to MCP tool functions
  └─ Option B: Store manager in global state accessible from MCP
  └─ Option C: Use event bus pattern (pub/sub)
- [ ] Test update_project_mission() broadcasts mission to UI
- [ ] Test spawn_agent_job() broadcasts agent card to UI
- [ ] Verify mission panel updates without refresh
- [ ] Verify agent cards appear in real-time

# Phase 3: Fix #2 - Orchestrator ID Stability (1 hour)
- [ ] Modify orchestrator creation logic in spawn_agent_job() or orchestrate_project()
  └─ Check if orchestrator already exists for project
  └─ If exists: Return existing orchestrator ID
  └─ If not exists: Create new orchestrator
- [ ] Create orchestrator once at project activation (not at staging)
- [ ] Ensure ID persists across multiple "Stage Project" clicks
- [ ] Test orchestrator continuity across staging operations

# Phase 4: End-to-End Testing (30 mins)
- [ ] Activate project
- [ ] Stage project (mission appears without refresh)
- [ ] Click "Stage Project" again (same orchestrator ID)
- [ ] Spawn agents (cards appear without refresh)
- [ ] Check browser console (no errors)
```

**Success Criteria**:
- ✅ Mission panel updates without page refresh
- ✅ Agent cards appear without page refresh
- ✅ Orchestrator ID stable across multiple stagings
- ✅ No WebSocket connection errors in console

**Risk Mitigation**:
- **FastAPI state access**: Budget 1 hour for investigation before implementation
- **Breaking changes**: Test with existing workflows to ensure backward compatibility
- **Async complexity**: Use async/await properly for WebSocket broadcasts

**Archive**: `handovers/completed/0111_websocket_realtime_updates_orchestrator_id_bug-C.md`

---

### Phase 3: Cleanup & Enhancement

**Duration**: 1 day (Week 3)
**Priority**: 🟢 P1 MEDIUM
**Goal**: Remove zombie code, improve agent specialization

#### 3.1 Handover 0130b: Remove Zombie Code and Backups

**Effort**: 2-3 hours
**Priority**: P1
**Risk**: LOW

**Why Important**: Prevents AI coding tools from discovering deprecated patterns

**Tasks**:

```markdown
# Phase 1: Delete Backup Files (30 mins)
- [ ] Delete frontend/src/services/websocket.js.backup-0130a (507 lines)
- [ ] Delete frontend/src/services/flowWebSocket.js.backup-0130a (377 lines)
- [ ] Delete frontend/src/stores/websocket.old.js.backup-0130a (318 lines)
- [ ] Delete frontend/src/composables/useWebSocket.old.js.backup-0130a (142 lines)
- [ ] Total removal: 1,344 lines of zombie code

# Phase 2: Delete Example/Template Backup Files (30 mins)
- [ ] Audit for .example, .template, .old, .bak, .backup files
- [ ] Delete or move to /archive folder if historical value
- [ ] Update .gitignore to prevent future backups

# Phase 3: Add Deprecation Documentation (1 hour)
- [ ] Create docs/DEPRECATED_PATTERNS.md
  └─ Document old WebSocket service pattern
  └─ Document flowWebSocket pattern
  └─ Document old composable pattern
  └─ Explain why deprecated
  └─ Show migration path to V2

# Phase 4: Verify Clean State (30 mins)
- [ ] Run grep for "websocket.js.backup" references
- [ ] Run grep for "flowWebSocket" imports
- [ ] Check no broken imports remain
- [ ] Verify build still succeeds
- [ ] Run frontend dev server (no errors)
```

**Success Criteria**:
- ✅ 1,344 lines of backup files deleted
- ✅ No .backup, .old, .bak files in /src
- ✅ DEPRECATED_PATTERNS.md created
- ✅ Build succeeds
- ✅ Dev server runs without errors

**Archive**: `handovers/completed/0130b_remove_zombie_code_and_backups-C.md`

---

#### 3.2 Handover 0117: 8-Role Agent System Refactoring

**Effort**: 5-6 hours
**Priority**: P1
**Risk**: LOW (no database schema changes)
**Depends On**: 0118 complete (needs messaging in new templates)

**Changes**:
- Split "implementer" → "backend-implementer" + "frontend-implementer"
- Rename "reviewer" → "code-reviewer"
- Add "devops" role
- Total: 6 roles → 8 roles

**Tasks**:

```markdown
# Phase 1: Backend Template Updates (2.5 hours)
- [ ] Create backend-implementer template (Blue #3498DB)
  └─ Focus: Python, FastAPI, database, API design
  └─ Behavioral rules: Backend best practices, security
  └─ Success criteria: Tests pass, API documented
- [ ] Create frontend-implementer template (Cyan #00BCD4)
  └─ Focus: Vue 3, Vuetify, WebSocket integration
  └─ Behavioral rules: Responsive design, accessibility
  └─ Success criteria: UI matches spec, no console errors
- [ ] Rename reviewer → code-reviewer template (Purple #9B59B6)
  └─ Update behavioral rules: Code quality, security, performance
  └─ Update success criteria: OWASP compliance, test coverage
- [ ] Create devops template (Pink #E91E63)
  └─ Focus: Docker, nginx, PostgreSQL, deployment
  └─ Behavioral rules: Security hardening, monitoring
  └─ Success criteria: Zero-downtime deployment
- [ ] Update template metadata in _get_template_metadata()
  └─ Add 4 new template entries
  └─ Keep backward compatibility (old "implementer" still works)

# Phase 2: Frontend Color Configuration (1.5 hours)
- [ ] Add 4 new color objects to frontend/src/config/agentColors.js
  └─ backendImplementer: { primary: '#3498DB', dark: '#2C3E50', light: '#ECF0F1' }
  └─ frontendImplementer: { primary: '#00BCD4', dark: '#006064', light: '#E0F7FA' }
  └─ codeReviewer: { primary: '#9B59B6', dark: '#6C3483', light: '#F4ECF7' }
  └─ devops: { primary: '#E91E63', dark: '#880E4F', light: '#FCE4EC' }
- [ ] Expand AGENT_SYNONYMS map (40+ aliases)
  └─ 'backend': 'backendImplementer'
  └─ 'frontend': 'frontendImplementer'
  └─ 'reviewer': 'codeReviewer'
  └─ 'ops': 'devops'
  └─ Plus variations: 'Backend Developer', 'Frontend Dev', etc.
- [ ] Add CSS variables to frontend/src/styles/agent-colors.scss
  └─ --backend-implementer-primary, --backend-implementer-dark, etc.
- [ ] Add agent card header styles (.agent-card.backend-implementer)
- [ ] Add chat head badge styles (.chat-head.backend-implementer)

# Phase 3: Documentation (1 hour)
- [ ] Update handovers/Simple_Vision.md
  └─ Change "6 specialized agent roles" → "8 specialized agent roles"
  └─ Add backend-implementer, frontend-implementer, devops descriptions
- [ ] Update docs/AGENT_CONTEXT_ESSENTIAL.md
  └─ Update role list section
  └─ Add new role capabilities
- [ ] Update handovers/start_to_finish_agent_FLOW.md
  └─ Update seeded templates section (6 → 8)

# Phase 4: Testing (1 hour)
- [ ] Fresh install creates exactly 8 templates
- [ ] All 8 agent cards render with correct colors
- [ ] Synonym mapping works
  └─ Test: Create agent with role="backend" → Maps to backendImplementer
  └─ Test: Create agent with role="reviewer" → Maps to codeReviewer
- [ ] MCP tools accept new role names
  └─ Test: spawn_agent_job(agent_type="backend-implementer") succeeds
- [ ] Template export caps at 8 roles (not 6)
- [ ] Backward compatibility
  └─ Old agent jobs with role="implementer" still render
  └─ No errors in console for old data
```

**Success Criteria**:
- ✅ 8 agent templates created
- ✅ All templates have messaging protocol (from 0118)
- ✅ Colors render correctly in UI
- ✅ Synonym mapping works (40+ aliases)
- ✅ Backward compatible (old "implementer" jobs still work)
- ✅ Documentation updated

**Why Low Risk**:
- No database schema changes (role is String(50))
- Frontend already has alias infrastructure
- Agent cards fully dynamic (no hardcoded role checks)
- MCP tools role-agnostic

**Archive**: `handovers/completed/0117_8_role_agent_system_refactoring-C.md`

---

### Phase 4: Production UI

**Duration**: 2 weeks (Week 4-5)
**Priority**: 🟡 P1 HIGH
**Goal**: Production-grade interface matching design specification

#### 4.1 Handover 0114: Jobs Tab UI/UX Harmonization

**Effort**: 2 weeks
**Priority**: P1
**Risk**: MEDIUM (scope complexity)
**Depends On**: 0118 complete (Message Center needs real messages)

**What This Is**: Complete UI overhaul matching 9-slide PDF specification

**Tasks**:

```markdown
# Phase 1: Dual Tab Implementation (2 days)
- [ ] Implement Staging tab
  └─ Shows only orchestrator card
  └─ "Stage Project" button (primary action)
  └─ Mission panel (collapsible)
  └─ Empty state: "No orchestrator staged"
- [ ] Implement Jobs tab
  └─ Shows all agents including orchestrator
  └─ Grid layout (responsive)
  └─ Sort by: Created, Status, Role, Name
  └─ Filter by: Status, Role
- [ ] Tab switching behavior
  └─ Preserve state when switching tabs
  └─ Update URL query param (?tab=staging or ?tab=jobs)
  └─ Deep linking support (share specific tab)
- [ ] State persistence
  └─ Remember last active tab in localStorage
  └─ Restore tab on page reload

# Phase 2: 8-State Badge System (2 days)
- [ ] Implement 8 status badges
  └─ waiting: Grey #9E9E9E
  └─ staging: Blue #2196F3
  └─ working: Green #4CAF50
  └─ completed: Success #66BB6A
  └─ failed: Error #F44336
  └─ blocked: Warning #FF9800
  └─ cancelled: Grey #757575
  └─ decommissioned: Grey #BDBDBD
- [ ] State transition validation
  └─ Prevent invalid transitions (e.g., decommissioned → working)
  └─ Backend validation in agent_job_manager.py
- [ ] Color-coded badges per design spec
  └─ Match PDF slide 3: Badge styling
  └─ Icons for each state (mdi-*)

# Phase 3: Claude Code Toggle Integration (2 days)
- [ ] Dynamic button text
  └─ If toggle ON: "Launch Agent" (executes immediately)
  └─ If toggle OFF: "Copy Launch Prompt" (clipboard)
- [ ] Execution prompt dialog (from Handover 0109)
  └─ Thin client prompt (70% token reduction)
  └─ Include: agent_job_id, tenant_key, mission summary
  └─ Multi-line text area with copy button
  └─ Syntax highlighting for readability
- [ ] Clipboard copy functionality
  └─ Copy to clipboard on button click
  └─ Toast notification: "Launch prompt copied"
  └─ Works on all browsers (fallback for non-HTTPS)

# Phase 4: Orchestrator Actions (2 days)
- [ ] "Close Out Project" button
  └─ Only visible on orchestrator card
  └─ Confirmation dialog: "Mark all agents decommissioned?"
  └─ Marks all agents in project as decommissioned
  └─ Updates project status to 'completed'
  └─ Shows project completion banner
- [ ] "Continue Working" button
  └─ Only visible on decommissioned orchestrator
  └─ Re-enables orchestrator (decommissioned → waiting)
  └─ Allows spawning new agents
  └─ Hides completion banner
- [ ] Project completion banner
  └─ Appears above Jobs tab when all agents decommissioned
  └─ Shows: Project name, Completion date, Summary stats
  └─ "Download Summary" button (JSON export)
  └─ "Archive Project" button (soft delete)
- [ ] Summary report download
  └─ JSON format with all agent jobs
  └─ Includes: Mission, Agent roles, Status, Timestamps, Messages
  └─ Filename: `{project_name}_summary_{date}.json`

# Phase 5: Message Center Integration (3 days)
- [ ] Real messages from 0118 implementation
  └─ Display messages in chronological order
  └─ Auto-scroll to latest message
  └─ Unread badge on agent cards
- [ ] Message filtering by agent
  └─ Click agent card → Filter messages to that agent
  └─ "Show All" button to clear filter
- [ ] Message type badges
  └─ BLOCKER: Red badge
  └─ QUESTION: Yellow badge
  └─ PROGRESS: Blue badge
  └─ COMPLETE: Green badge
  └─ USER: Purple badge
- [ ] Auto-scroll on new message
  └─ If scrolled to bottom: Auto-scroll to new message
  └─ If scrolled up: Show "New messages" badge, don't auto-scroll

# Phase 6: Visual Polish (3 days)
- [ ] Match PDF design specification
  └─ Slide 1: Overall layout
  └─ Slide 2: Staging tab design
  └─ Slide 3: Jobs tab grid
  └─ Slide 4: Agent card states
  └─ Slide 5: Message Center
  └─ Slide 6: Orchestrator actions
  └─ Slide 7: Completion banner
  └─ Slide 8: Mobile responsive
  └─ Slide 9: Accessibility
- [ ] Responsive layout
  └─ Desktop: 3-column grid
  └─ Tablet: 2-column grid
  └─ Mobile: 1-column stacked
- [ ] Loading states
  └─ Skeleton loaders for agent cards
  └─ Spinner for "Stage Project" action
  └─ Loading message in Message Center
- [ ] Error states
  └─ Failed to load agents: Retry button
  └─ Message send failed: Error toast + retry
  └─ Network error: Offline banner
- [ ] Accessibility (WCAG 2.1 AA)
  └─ ARIA labels on all interactive elements
  └─ Keyboard navigation (Tab, Enter, Space)
  └─ Focus indicators
  └─ Screen reader announcements for status changes
  └─ Color contrast ratios ≥4.5:1
```

**Success Criteria**:
- ✅ Dual-mode tabs (Staging vs Jobs) functional
- ✅ 8-state badge system implemented
- ✅ Claude Code toggle changes button behavior
- ✅ Orchestrator actions work (Close Out, Continue)
- ✅ Message Center displays real messages from 0118
- ✅ UI matches PDF specification (9 slides)
- ✅ Responsive on desktop, tablet, mobile
- ✅ WCAG 2.1 AA compliant

**Risk Mitigation**:
- **Scope creep**: Phase implementation, deliver MVP first
- **Design interpretation**: Reference PDF slides frequently
- **Message Center dependency**: 0118 must be complete and tested

**Related Handovers**:
- 0113 (Unified State System)
- 0073 (Static Agent Grid)
- 0107 (Agent Monitoring)
- 0105 (Claude Code Toggle)
- 0109 (Execution Prompt Dialog)

**Archive**: `handovers/completed/0114_jobs_tab_ui_ux_harmonization-C.md`

---

### Phase 5: Multi-CLI Support (PARALLEL with Phase 4)

**Duration**: 2 weeks (Week 4-5, runs parallel to 0114)
**Priority**: 🟡 P1 HIGH
**Goal**: Enable Codex CLI and Gemini CLI integration

#### 5.1 Handover 0095: Streamable HTTP MCP Architecture

**Effort**: 2 weeks
**Priority**: P1
**Risk**: MEDIUM (HTTPS migration complexity)
**Independent**: Can run parallel to 0114

**What This Is**:
- Add streamable HTTP transport for MCP (Codex CLI requirement)
- Add SSE (Server-Sent Events) variant (Gemini CLI support)
- Migrate to HTTPS for all MCP traffic (security)
- Keep existing JSON-RPC `/mcp` endpoint (backward compatible)

**Tasks**:

```markdown
# Phase 1: Streamable HTTP Endpoints (3 days)
- [ ] POST /mcp/stream endpoint
  └─ Accept JSON-RPC request body
  └─ Return streamable response (SSE format)
  └─ Preserve auth (API keys, Bearer tokens)
  └─ Maintain tenancy isolation
- [ ] GET /mcp/stream endpoint (SSE)
  └─ Long-lived connection for receiving responses
  └─ Content-Type: text/event-stream
  └─ Keepalive heartbeat every 30 seconds
  └─ Close on timeout (5 minutes)
- [ ] Backward compatibility
  └─ Keep POST /mcp endpoint (existing JSON-RPC)
  └─ No breaking changes to current clients
  └─ Version negotiation header (X-MCP-Version: 2.0)

# Phase 2: HTTPS Migration (3 days)
- [ ] HTTP/HTTPS toggle in Admin Settings UI
  └─ Development override: Allow HTTP for localhost
  └─ Production requirement: Enforce HTTPS
  └─ Warning banner if HTTP enabled in production mode
- [ ] Certificate management section
  └─ UI for uploading cert.pem and key.pem
  └─ Let's Encrypt integration instructions
  └─ Caddy auto-HTTPS option
  └─ Validate cert before applying (openssl verify)
- [ ] Backend HTTPS enforcement
  └─ Check X-Forwarded-Proto header (proxy mode)
  └─ Reject HTTP requests if HTTPS required
  └─ Return 426 Upgrade Required with instructions
  └─ Environment variable override: ALLOW_HTTP_MCP=1
- [ ] Error messages
  └─ Clear instructions: "HTTPS required for MCP in production"
  └─ Provide cert setup guide link
  └─ Show how to use reverse proxy

# Phase 3: Proxy Configuration (2 days)
- [ ] nginx proxy example
  └─ Configuration file: nginx.conf.example
  └─ Proxy /mcp and /mcp/stream endpoints
  └─ Enable streaming (proxy_buffering off)
  └─ WebSocket upgrade support
  └─ SSL termination
- [ ] Caddy proxy example
  └─ Caddyfile example
  └─ Automatic HTTPS with Let's Encrypt
  └─ Reverse proxy to localhost:7272
  └─ Streaming support
- [ ] Deployment scenarios
  └─ Localhost (development): HTTP allowed
  └─ LAN (team): HTTPS recommended, HTTP optional
  └─ WAN (internet): HTTPS required

# Phase 4: CLI Integration Testing (4 days)
- [ ] Test Codex CLI with streamable HTTP
  └─ Configure Codex with POST /mcp/stream endpoint
  └─ Test tool calls (spawn_agent_job, update_project_mission)
  └─ Test streaming responses
  └─ Verify auth works (API key or Bearer token)
- [ ] Test Gemini CLI with SSE transport
  └─ Configure Gemini with GET /mcp/stream endpoint
  └─ Test long-lived connection
  └─ Test keepalive heartbeat
  └─ Verify timeout handling
- [ ] Test Claude Code with HTTP transport
  └─ Verify backward compatibility with POST /mcp
  └─ Test upgrade to streamable if supported
- [ ] Verify all auth mechanisms
  └─ API key in header
  └─ Bearer token in Authorization header
  └─ Session cookie (fallback)
  └─ Multi-tenant isolation (tenant_key validation)

# Phase 5: Documentation (2 days)
- [ ] Update INSTALLATION_FLOW_PROCESS.md
  └─ Add proxy setup section
  └─ Certificate installation guide
  └─ Let's Encrypt + Caddy quickstart
- [ ] Document CLI-specific configuration
  └─ Codex CLI: How to add streamable MCP server
  └─ Gemini CLI: How to configure SSE transport
  └─ Claude Code: Existing JSON-RPC (no changes)
- [ ] Security best practices guide
  └─ Why HTTPS is required
  └─ Certificate management
  └─ Firewall configuration
  └─ Rate limiting recommendations
```

**Success Criteria**:
- ✅ POST /mcp/stream endpoint functional
- ✅ GET /mcp/stream (SSE) endpoint functional
- ✅ HTTPS toggle in Admin Settings
- ✅ nginx and Caddy proxy examples provided
- ✅ Codex CLI successfully connects and executes tools
- ✅ Gemini CLI successfully connects and executes tools
- ✅ Claude Code backward compatible (POST /mcp still works)
- ✅ Documentation complete

**Risk Mitigation**:
- **HTTPS complexity**: Provide HTTP override for development
- **Certificate management**: Document Let's Encrypt automation
- **Breaking changes**: Maintain backward compatibility with POST /mcp

**Related Handovers**:
- 0092 (Bearer Auth Support) - Already complete
- 0069 (Native MCP for Codex & Gemini) - Provides context

**Archive**: `handovers/completed/0095_streamable_http_mcp_architecture-C.md`

---

## DECISION POINT: 0130c/d or Skip to 0131?

**Context**: After Phase 5, you've completed critical infrastructure. Two remaining 0130 handovers:
- 0130c: Consolidate Duplicate Components (1-2 days)
- 0130d: Centralize API Calls (2-3 days)

### Option A: Execute 0130c + 0130d (3-5 days)

**Benefits**:
- Cleaner codebase for AI coding tools
- Reduced component confusion (which AgentCard to use?)
- Centralized API patterns (easier to maintain)

**Costs**:
- 1 week delay before feature development
- Deferred value (doesn't add user-facing features)

**When to Choose**:
- If codebase complexity is causing AI tool errors
- If team is confused about which components to use
- If centralized API patterns needed for upcoming features

### Option B: Skip to 0131 (Recommended)

**Rationale**:
- Core goals achieved (WebSocket V2, messaging fixed, zombie code removed)
- 0130c/d are polish, not blockers
- Feature development has higher priority
- Can revisit in 0200 range if needed

**When to Choose**:
- If user-facing features are more urgent
- If current codebase complexity is manageable
- If 1-week delay is unacceptable

**User Preference**: User indicated feature development is priority (prompt tuning, orchestrator optimization, slash commands, close-out procedures)

**Recommendation**: Skip to Phase 6 (0131 Feature Development)

---

### Phase 6: Feature Development - 0131 Range

**Duration**: 6-12 weeks (Week 6-17)
**Priority**: 🟢 P1 MEDIUM
**Goal**: Build missing features before launch

**Context**: User identified critical gaps:
- Prompt tuning for agents
- Orchestrator optimization
- Slash command system for tasks
- Project close-out procedures

**Proposed Handovers** (to be created):

#### 6.1 Prompt Tuning for Agents (0131-0135)

**Duration**: 2-3 weeks
**Goal**: Optimize agent templates based on execution data

**Proposed Handovers**:
- **0131**: A/B Testing Framework for Agent Prompts
  - Create experiment infrastructure
  - Run multiple prompt variants in parallel
  - Track success metrics (task completion, time, quality)
  - Statistical significance testing

- **0132**: Agent Performance Metrics Dashboard
  - Track: Completion rate, Avg time per task, Error rate, Message frequency
  - Per-agent analytics (which agents perform best)
  - Per-template analytics (which templates need tuning)

- **0133**: Prompt Optimization Engine
  - Analyze successful vs failed executions
  - Identify common failure patterns
  - Suggest template improvements
  - Auto-tune behavioral rules based on data

- **0134**: Template Version Control & Rollback
  - Version history for each template
  - Compare versions (diff view)
  - Rollback to previous version if regression
  - Branch/merge for template experiments

- **0135**: Prompt Library & Best Practices
  - Curated collection of high-performing prompts
  - Domain-specific templates (web app, CLI tool, API, etc.)
  - Community-contributed templates
  - Rating and review system

#### 6.2 Orchestrator Optimization (0136-0140)

**Duration**: 2-3 weeks
**Goal**: Improve mission planning, agent selection, workflow coordination

**Proposed Handovers**:
- **0136**: Smart Mission Decomposition
  - Better task breakdown (current: keyword-based, future: LLM-assisted)
  - Dependency auto-detection improvements
  - Parallel task identification
  - Critical path analysis

- **0137**: Intelligent Agent Selection
  - Match agent capabilities to task requirements
  - Load balancing across agents
  - Fallback agent selection (if primary unavailable)
  - Skill-based routing

- **0138**: Workflow Coordination Enhancements
  - Better dependency management (current: linear, future: DAG)
  - Dynamic re-planning when tasks fail
  - Adaptive timeouts based on task complexity
  - Escalation policies (when to notify user)

- **0139**: Orchestrator Learning System
  - Learn from past project executions
  - Identify successful workflow patterns
  - Predict task duration based on history
  - Recommend optimal agent assignments

- **0140**: Multi-Orchestrator Coordination
  - Support for multiple concurrent projects
  - Resource allocation across orchestrators
  - Shared agent pool
  - Inter-orchestrator communication

#### 6.3 Slash Command System (0141-0145)

**Duration**: 2-3 weeks
**Goal**: Task-specific shortcuts for common workflows

**Proposed Handovers**:
- **0141**: Slash Command Infrastructure
  - Expand beyond `/gil_*` pattern
  - Dynamic command registration
  - Plugin architecture for custom commands
  - Help system (`/help`)

- **0142**: Project Management Commands
  - `/project create <name>` - Quick project creation
  - `/project activate <id>` - Switch active project
  - `/project close` - Close out current project
  - `/project status` - Show project summary

- **0143**: Agent Management Commands
  - `/spawn <role> <name>` - Quick agent spawn
  - `/status <agent_name>` - Check agent status
  - `/message <agent_name> <text>` - Send message to agent
  - `/cancel <agent_name>` - Cancel agent job

- **0144**: Workflow Commands
  - `/run <workflow_name>` - Execute predefined workflow
  - `/pause` - Pause current workflow
  - `/resume` - Resume paused workflow
  - `/rollback` - Revert to previous state

- **0145**: Debugging & Diagnostics Commands
  - `/logs <agent_name>` - Show agent logs
  - `/debug <agent_name>` - Enable debug mode
  - `/trace <job_id>` - Show execution trace
  - `/health` - System health check

#### 6.4 Project Close-Out Procedures (0146-0150)

**Duration**: 1-2 weeks
**Goal**: Formalize project completion workflow

**Proposed Handovers**:
- **0146**: Completion Checklist System
  - Pre-close validation (all agents complete, no blockers)
  - User-defined close-out checklist
  - Required vs optional checklist items
  - Checklist templates by project type

- **0147**: Project Summary Generation
  - Auto-generate project report
  - Include: Mission, Agents, Messages, Timeline, Outcomes
  - Export formats: JSON, Markdown, PDF
  - Customizable report templates

- **0148**: Archive & Export Functionality
  - Archive project (soft delete with recovery)
  - Export all project data
  - Include: Code changes, Logs, Messages, Artifacts
  - Compression and encryption options

- **0149**: Post-Project Analytics
  - Success metrics: Time to completion, Agent efficiency, Error rate
  - Lessons learned extraction
  - Recommendations for future projects
  - Performance comparison vs similar projects

- **0150**: Knowledge Base Integration
  - Extract reusable patterns from completed projects
  - Add to template library
  - Tag and categorize learnings
  - Search previous projects for solutions

#### 6.5 Nice-to-Have Enhancements (0151-0160)

**Proposed Handovers**:
- **0112**: Context Prioritization UX Enhancements (8-10 hours)
  - Mission summary panel
  - Token badges on agent cards
  - System metrics dashboard
  - Treemap visualization

- **0083**: Slash Command Harmonization (2-3 hours)
  - Rename all to `/gil_*` pattern
  - Update documentation

- **0151-0160**: Reserved for additional features discovered during development

**Total Phase 6 Duration**: 6-12 weeks

---

### Phase 7: Launch Preparation - 0200 Range

**Duration**: 4 weeks (Week 18-21)
**Priority**: 🔵 P2 LOW (until features complete)
**Goal**: Production-ready deployment

#### 7.1 Infrastructure & Ops (0200-0209)

**Duration**: 1-2 weeks

**Proposed Handovers**:
- **0200**: Aggregate 0100 One-Liner Installation + Deployment Automation
  - macOS: `curl -fsSL https://install.giljoai.com/install.sh | bash`
  - Windows: `irm https://install.giljoai.com/install.ps1 | iex`
  - Linux: `wget -qO- https://install.giljoai.com/install.sh | bash`
  - Automated dependency detection and installation
  - Zero-config setup wizard
  - Health check and validation

- **0201**: Server Hardening & Security
  - Rate limiting (per-user, per-endpoint)
  - DDoS protection (fail2ban integration)
  - Secure headers (CSP, HSTS, X-Frame-Options)
  - Input validation and sanitization
  - SQL injection prevention (already using SQLAlchemy ORM)

- **0202**: Monitoring & Observability
  - Prometheus metrics export
  - Grafana dashboard templates
  - Application performance monitoring (APM)
  - Error tracking (Sentry integration)
  - Health check endpoints

- **0203**: Logging & Auditing
  - Structured logging (JSON format)
  - Log aggregation (ELK stack or similar)
  - Audit trail for sensitive operations
  - Log rotation and retention policies
  - Compliance logging (GDPR, SOC2)

- **0204**: Backup & Disaster Recovery
  - Automated database backups (daily, weekly, monthly)
  - Point-in-time recovery
  - Backup encryption and compression
  - Offsite backup storage (S3, Azure Blob)
  - Recovery testing procedures

- **0205**: Performance Optimization
  - Database query optimization
  - Connection pooling tuning
  - Caching strategy (Redis)
  - CDN for static assets
  - Load testing and benchmarking

- **0206-0209**: Reserved for additional ops tasks

#### 7.2 Open Source Preparation (0210-0219)

**Duration**: 1 week

**Proposed Handovers**:
- **0210**: LICENSE Selection and Application
  - Choose license: MIT (recommended for max adoption)
  - Apply LICENSE file to repository root
  - Add license headers to source files
  - Document third-party licenses (dependencies)

- **0211**: CONTRIBUTING.md Guide
  - Code of Conduct (Contributor Covenant)
  - How to report bugs
  - How to suggest features
  - How to submit pull requests
  - Development setup instructions
  - Testing guidelines
  - Code style guide

- **0212**: CODE_OF_CONDUCT.md
  - Adopt Contributor Covenant 2.1
  - Define expected behavior
  - Define unacceptable behavior
  - Enforcement procedures
  - Scope and enforcement contacts

- **0213**: GitHub Templates
  - Issue templates (bug report, feature request)
  - Pull request template
  - Discussion templates
  - Security policy (SECURITY.md)

- **0214**: Community Documentation
  - README.md enhancements (badges, quickstart)
  - FAQ.md (common questions)
  - CHANGELOG.md (version history)
  - ROADMAP.md (public roadmap)

- **0215-0219**: Reserved for community setup tasks

#### 7.3 Quality Assurance (0220-0229)

**Duration**: 1-2 weeks

**Proposed Handovers**:
- **0220**: Security Audit
  - OWASP Top 10 validation (already 10/10)
  - Penetration testing
  - Dependency vulnerability scanning (npm audit, safety)
  - Secret scanning (prevent accidental commits)
  - Security header validation

- **0221**: Performance Benchmarking
  - Load testing (concurrent users)
  - Stress testing (breaking points)
  - Endurance testing (24-hour run)
  - API response time benchmarks
  - Database query performance

- **0222**: Cross-Platform Testing
  - Windows 10/11 compatibility
  - macOS Monterey/Ventura/Sonoma compatibility
  - Ubuntu 20.04/22.04/24.04 compatibility
  - Browser compatibility (Chrome, Firefox, Safari, Edge)

- **0223**: Accessibility Audit
  - WCAG 2.1 AA compliance
  - Screen reader testing (NVDA, JAWS, VoiceOver)
  - Keyboard navigation
  - Color contrast validation
  - Focus indicators

- **0224**: Internationalization (i18n)
  - English (primary)
  - Spanish (secondary)
  - French (secondary)
  - German (secondary)
  - Translation infrastructure (vue-i18n)

- **0225-0229**: Reserved for QA tasks

#### 7.4 Launch Readiness (0230-0239)

**Duration**: 1 week

**Proposed Handovers**:
- **0230**: Demo Videos & Tutorials
  - 2-minute overview video
  - 10-minute getting started tutorial
  - Agent coordination demo
  - Messaging system demo
  - Orchestrator succession demo

- **0231**: User Documentation
  - Installation guide
  - Quick start guide
  - User manual (comprehensive)
  - Admin guide
  - Troubleshooting guide

- **0232**: Developer Documentation
  - API reference
  - MCP tool documentation
  - Architecture overview
  - Database schema
  - Deployment guide

- **0233**: Marketing Materials
  - Product website (landing page)
  - Feature highlights
  - Use cases and testimonials
  - Comparison matrix (vs competitors)
  - Pricing (if applicable)

- **0234**: Support Infrastructure
  - GitHub Discussions setup
  - Discord server (community)
  - Email support (support@giljoai.com)
  - Knowledge base (documentation site)
  - Status page (uptime monitoring)

- **0235-0239**: Reserved for launch tasks

---

## Gantt Chart

```
PHASE 0: PRE-EXECUTION (COMPLETE)
════════════════════════════════════════════════════════════════
✅✅✅✅✅✅✅✅✅✅ COMPLETE

PHASE 1: CRITICAL MESSAGING (WEEK 1-2) - 🔴 P0
════════════════════════════════════════════════════════════════
Week 1: [0130e][========0118========]
Week 2: [====0118====]

PHASE 2: VALIDATION & QUICK WINS (WEEK 2) - 🟡 P1
════════════════════════════════════════════════════════════════
Week 2: [0130a Test][0111 Fix]

PHASE 3: CLEANUP & ENHANCEMENT (WEEK 3) - 🟢 P1
════════════════════════════════════════════════════════════════
Week 3: [0130b][0117]

PHASE 4-5: PRODUCTION UI & CLI (WEEK 4-5) - 🟡 P1 (PARALLEL)
════════════════════════════════════════════════════════════════
Week 4: [============0114============][=====0095=====]
Week 5: [============0114============][=====0095=====]

DECISION POINT: 0130c/d OR SKIP TO 0131?
════════════════════════════════════════════════════════════════
Option A: [0130c][===0130d===] (3-5 days delay)
Option B: Skip to Phase 6 (RECOMMENDED)

PHASE 6: FEATURE DEVELOPMENT (WEEK 6-17) - 🟢 P1
════════════════════════════════════════════════════════════════
Week  6-8:  [======Prompt Tuning (0131-0135)======]
Week  9-11: [====Orchestrator Opt (0136-0140)====]
Week 12-14: [====Slash Commands (0141-0145)====]
Week 15-16: [==Close-Out (0146-0150)==]
Week 17:    [=0112=][0083][=0151-0160=]

PHASE 7: LAUNCH PREPARATION (WEEK 18-21) - 🔵 P2
════════════════════════════════════════════════════════════════
Week 18-19: [==Infra & Ops (0200-0209)==]
Week 19:    [=Open Source (0210-0219)=]
Week 20:    [==QA (0220-0229)==]
Week 21:    [=Launch (0230-0239)=]

TOTAL TIMELINE: 14-20 WEEKS
════════════════════════════════════════════════════════════════
Critical Path:  3 weeks (Phase 1-3)
Production UI:  2 weeks (Phase 4-5, parallel)
Features:       6-12 weeks (Phase 6, depends on scope)
Launch Prep:    4 weeks (Phase 7)
```

---

## Dependencies Map

```
CRITICAL PATH DEPENDENCIES
══════════════════════════════════════════════════════════════

0130e (Infrastructure Fix)
  │
  └─→ 0118 (Agent Messaging Protocol)
        ├─→ 0117 (8-Role System) - needs messaging in templates
        ├─→ 0114 (Jobs Tab UI) - Message Center needs real messages
        └─→ ALL FUTURE FEATURES - multi-agent coordination depends on this

INDEPENDENT TRACKS
══════════════════════════════════════════════════════════════

0130a (WebSocket V2 Testing)
  └─→ Archive 0130a-C.md if successful
  └─→ Delete backup files in 0130b

0111 (WebSocket Real-Time Updates)
  └─→ No dependencies
  └─→ Improves UX immediately

0130b (Remove Zombie Code)
  └─→ Depends on 0130a success (delete backup files)

0095 (Streamable HTTP MCP)
  └─→ No dependencies (can run parallel to 0114)

FEATURE DEVELOPMENT DEPENDENCIES
══════════════════════════════════════════════════════════════

0131-0135 (Prompt Tuning)
  └─→ Requires 0118 complete (data collection needs messaging)

0136-0140 (Orchestrator Optimization)
  └─→ Requires 0118 complete (coordination needs messaging)

0141-0145 (Slash Commands)
  └─→ Requires 0118 complete (commands trigger agent workflows)

0146-0150 (Close-Out Procedures)
  └─→ Requires 0114 complete (close-out UI)

0112 (Context UX)
  └─→ No dependencies (nice-to-have polish)

0083 (Slash Command Harmonization)
  └─→ Should be done AFTER 0141-0145 (all commands exist first)

LAUNCH PREP DEPENDENCIES
══════════════════════════════════════════════════════════════

0200-0209 (Infrastructure & Ops)
  └─→ Requires ALL features complete

0210-0219 (Open Source Prep)
  └─→ Can start anytime (independent)

0220-0229 (QA)
  └─→ Requires ALL features complete

0230-0239 (Launch Readiness)
  └─→ Requires QA complete
```

---

## Risk Mitigation

### Phase 1 Risks: Critical Messaging

**Risk 1.1: 0130e Infrastructure More Complex Than Expected**
- **Probability**: MEDIUM
- **Impact**: HIGH (blocks 0118)
- **Mitigation**:
  - Budget 1-hour investigation before implementation
  - If complexity exceeds 6 hours, escalate to user
  - Consider alternative: Simplify message routing (direct DB access)
- **Rollback**: Defer messaging features, mark 0118 as blocked

**Risk 1.2: 0118 Template Complexity Overload**
- **Probability**: HIGH
- **Impact**: MEDIUM (confusing templates)
- **Mitigation**:
  - Use clear section headers and code examples
  - Keep instructions concise (milestones only, not every action)
  - User testing with simple 2-agent workflow before complex cases
- **Rollback**: Simplify messaging (only BLOCKER and COMPLETE, drop others)

**Risk 1.3: Message Spam Floods Message Center**
- **Probability**: MEDIUM
- **Impact**: MEDIUM (UI overwhelmed)
- **Mitigation**:
  - Define clear rules: Message at milestones only (not every action)
  - Rate limiting: Max 1 message per minute per agent
  - Message aggregation: Combine similar PROGRESS messages
- **Rollback**: Add message filtering/hiding in UI

### Phase 2 Risks: Validation & Quick Wins

**Risk 2.1: 0130a Runtime Testing Reveals Critical Issues**
- **Probability**: LOW
- **Impact**: HIGH (WebSocket V2 unusable)
- **Mitigation**:
  - Backup branch exists: `backup_branch_before_websocketV2`
  - Rollback procedure documented in `0130a_MIGRATION_TEST_RESULTS.md`
  - Only archive 0130a if all 17 checklist items pass
- **Rollback**: `git checkout backup_branch_before_websocketV2`

**Risk 2.2: 0111 WebSocket Broadcast Fix Requires Deep FastAPI Changes**
- **Probability**: MEDIUM
- **Impact**: MEDIUM (exceeds 4-hour estimate)
- **Mitigation**:
  - Budget 1-hour investigation before implementation
  - If complexity exceeds 4 hours, consider workarounds (polling fallback)
- **Rollback**: Document issue, defer to 0200 range

### Phase 3 Risks: Cleanup & Enhancement

**Risk 3.1: Deleting Backup Files Breaks Something**
- **Probability**: LOW
- **Impact**: LOW (easy to restore)
- **Mitigation**:
  - Verify build succeeds BEFORE deleting backups
  - Git commit after each deletion (granular rollback)
  - Keep backups in Git history (can restore from commit)
- **Rollback**: `git revert <commit>` to restore backups

**Risk 3.2: 8-Role System Breaks Backward Compatibility**
- **Probability**: LOW
- **Impact**: MEDIUM (old agent jobs don't render)
- **Mitigation**:
  - Test with existing agent jobs BEFORE archiving
  - Keep synonym mapping for old "implementer" role
  - Frontend already has fallback color (grey) for unknown roles
- **Rollback**: Revert frontend color changes, keep 6 templates

### Phase 4-5 Risks: Production UI & CLI

**Risk 4.1: 0114 Scope Creep (2-week estimate expands)**
- **Probability**: HIGH
- **Impact**: MEDIUM (schedule delay)
- **Mitigation**:
  - Phase implementation: Deliver MVP first (dual tabs + basic badges)
  - Defer polish (animations, micro-interactions) to 0151-0160
  - Set hard deadline: 2 weeks, cut scope if needed
- **Rollback**: Defer 0114 to 0200 range, focus on features

**Risk 4.2: 0095 HTTPS Migration Breaks Existing Clients**
- **Probability**: MEDIUM
- **Impact**: HIGH (MCP tools stop working)
- **Mitigation**:
  - Maintain backward compatibility with POST /mcp (JSON-RPC)
  - HTTP override for development (`ALLOW_HTTP_MCP=1`)
  - Comprehensive testing with Claude Code before launch
- **Rollback**: Disable HTTPS requirement, keep HTTP fallback

### Phase 6 Risks: Feature Development

**Risk 6.1: Feature Scope Exceeds 12 Weeks**
- **Probability**: MEDIUM
- **Impact**: HIGH (launch delay)
- **Mitigation**:
  - Prioritize ruthlessly: P0 features only in 0131-0150
  - Defer nice-to-haves to post-launch (0151-0160)
  - Set hard deadline for Phase 6: 12 weeks maximum
- **Rollback**: Launch with minimum features, add post-launch

**Risk 6.2: User Requirements Change During Development**
- **Probability**: MEDIUM
- **Impact**: MEDIUM (rework required)
- **Mitigation**:
  - Weekly check-ins with user during Phase 6
  - Show working prototypes early and often
  - Keep handovers flexible (can adjust mid-phase)
- **Rollback**: Pause feature development, realign with user

### Phase 7 Risks: Launch Preparation

**Risk 7.1: Security Audit Reveals Critical Vulnerabilities**
- **Probability**: LOW
- **Impact**: HIGH (launch blocked)
- **Mitigation**:
  - Already achieved OWASP 10/10 in Phase 0
  - Run security scans continuously during development
  - Budget 1 week for fixes if vulnerabilities found
- **Rollback**: Delay launch until critical issues fixed

**Risk 7.2: Performance Benchmarks Fail**
- **Probability**: MEDIUM
- **Impact**: MEDIUM (optimization needed)
- **Mitigation**:
  - Run performance tests early in Phase 7 (not last week)
  - Budget 1 week for optimization if needed
  - Set realistic targets: 100 concurrent users, <500ms API response
- **Rollback**: Reduce concurrency limits, add caching

---

## Decision Points

### Decision Point 1: 0130c/d or Skip to 0131? (After Week 5)

**Context**: After completing 0130a-b and 0114/0095, decide whether to continue 0130 cleanup or start features

**Option A: Execute 0130c + 0130d**
- **Duration**: 3-5 days
- **Benefits**:
  - Consolidate duplicate components (cleaner codebase)
  - Centralize API calls (consistent patterns)
  - Easier for AI tools to navigate
- **Costs**:
  - 1 week delay before features
  - Deferred value (no user-facing improvements)

**Option B: Skip to 0131 (Recommended)**
- **Duration**: 0 days (immediate start)
- **Benefits**:
  - Start features immediately
  - Higher user value
  - Can revisit 0130c/d in 0200 range if needed
- **Costs**:
  - Some codebase duplication remains
  - AI tools may occasionally choose wrong component

**Decision Criteria**:
- Choose A if: AI tools are making errors due to duplication
- Choose B if: Features are higher priority than polish

**User Preference**: User indicated features are priority → Choose B

---

### Decision Point 2: Feature Scope for 0131-0150 (Week 6)

**Context**: Phase 6 has 50 proposed handovers. Need to prioritize.

**Must-Have (P0) - Do First**:
- 0131-0135: Prompt Tuning (user requested)
- 0136-0140: Orchestrator Optimization (user requested)
- 0141-0145: Slash Commands (user requested)
- 0146-0150: Close-Out Procedures (user requested)

**Nice-to-Have (P1) - Do If Time**:
- 0112: Context Prioritization UX
- 0083: Slash Command Harmonization

**Deferred (P2) - Post-Launch**:
- 0151-0160: Additional features discovered during development

**Decision Criteria**:
- If Phase 6 exceeds 12 weeks: Cut nice-to-haves
- If user requests new feature: Add to 0151-0160 range

---

### Decision Point 3: Launch Readiness (Week 17)

**Context**: After features complete, decide if ready for Phase 7 launch prep

**Readiness Checklist**:
- [ ] All P0 features complete (0131-0150)
- [ ] 0118 messaging validated (multi-agent coordination works)
- [ ] WebSocket V2 stable (no runtime issues)
- [ ] Jobs Tab UI complete (production-grade)
- [ ] Multi-CLI support working (Codex + Gemini)
- [ ] No critical bugs (P0/P1 bugs resolved)
- [ ] User acceptance testing complete

**If Checklist Passes**: Proceed to Phase 7 (launch prep)

**If Checklist Fails**: Extend Phase 6, create fix handovers, re-evaluate in 1 week

---

## Phase Gate Criteria

### Phase 1 Gate: Critical Messaging Complete

**Entry Criteria**:
- 0130e infrastructure fix complete (router registered, WebSocket wired)
- 0118 agent templates updated with messaging protocol

**Exit Criteria**:
- ✅ Message hub usage >0 (baseline: 0 in first test)
- ✅ Agents coordinate dependencies successfully
- ✅ User messages responded to within 30 seconds
- ✅ Blocker escalation works (orchestrator notified)
- ✅ 5 test workflows pass (simple, dependency, blocker, user, multi-terminal)
- ✅ No regression in existing workflows (TinyContacts still works)

**If Gate Fails**: Do not proceed to Phase 2. Fix issues, re-test.

---

### Phase 2 Gate: Validation Complete

**Entry Criteria**:
- Phase 1 gate passed
- 0130a runtime testing checklist ready

**Exit Criteria**:
- ✅ All 17 0130a runtime tests pass
- ✅ 0111 WebSocket fixes implemented
- ✅ Real-time updates work without refresh
- ✅ Orchestrator ID stable across stagings
- ✅ No console errors in browser
- ✅ No memory leaks detected

**If Gate Fails**: Rollback WebSocket V2 if critical issues. Document and create fix handovers.

---

### Phase 3 Gate: Cleanup Complete

**Entry Criteria**:
- Phase 2 gate passed
- 0118 messaging complete (Phase 1)

**Exit Criteria**:
- ✅ 1,344 lines of zombie code deleted
- ✅ DEPRECATED_PATTERNS.md created
- ✅ 8 agent templates created
- ✅ All templates have messaging protocol
- ✅ Frontend renders all 8 roles with correct colors
- ✅ Backward compatibility validated

**If Gate Fails**: Complete cleanup before Phase 4. May defer 0117 if blocking.

---

### Phase 4-5 Gate: Production UI & CLI Complete

**Entry Criteria**:
- Phase 3 gate passed
- 0118 messaging validated (Message Center dependency)

**Exit Criteria**:
- ✅ Dual-mode tabs functional (Staging vs Jobs)
- ✅ 8-state badge system implemented
- ✅ Claude Code toggle works
- ✅ Orchestrator actions functional (Close Out, Continue)
- ✅ Message Center displays real messages
- ✅ UI matches PDF specification
- ✅ Streamable HTTP endpoints functional
- ✅ Codex CLI and Gemini CLI tested successfully
- ✅ WCAG 2.1 AA compliant

**If Gate Fails**: Defer polish features, deliver MVP only. May skip 0095 if multi-CLI not urgent.

---

### Phase 6 Gate: Features Complete

**Entry Criteria**:
- Phase 4-5 gate passed
- User approval to start feature development

**Exit Criteria**:
- ✅ All P0 features complete (0131-0150)
- ✅ Prompt tuning operational
- ✅ Orchestrator optimization deployed
- ✅ Slash command system functional
- ✅ Close-out procedures implemented
- ✅ User acceptance testing passed
- ✅ No P0/P1 bugs open

**If Gate Fails**: Extend Phase 6 by 2 weeks. If still failing, cut scope to P0 only.

---

### Phase 7 Gate: Launch Ready

**Entry Criteria**:
- Phase 6 gate passed
- User approval to start launch prep

**Exit Criteria**:
- ✅ One-liner installation works on all platforms
- ✅ Security audit passed (no critical vulnerabilities)
- ✅ Performance benchmarks met (100 users, <500ms response)
- ✅ Cross-platform testing complete
- ✅ Open source compliance (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT)
- ✅ Documentation complete (user + developer + admin)
- ✅ Demo videos and tutorials published
- ✅ Support infrastructure ready

**If Gate Fails**: Do not launch. Resolve issues, re-test, re-evaluate.

---

## Rollback Procedures

### Rollback 1: WebSocket V2 Migration (0130a)

**Trigger**: Critical runtime failures in 0130a testing

**Procedure**:
```bash
cd /f/GiljoAI_MCP
git checkout backup_branch_before_websocketV2
cd frontend && npm run build
```

**Validation**:
- Build succeeds
- Old WebSocket service restored
- Real-time updates work
- No console errors

**Impact**: Reverts to 4-layer WebSocket architecture, loses 70% token reduction benefits

---

### Rollback 2: Messaging Infrastructure (0130e + 0118)

**Trigger**: Messaging too complex, exceeds timeline

**Procedure**:
1. Mark 0118 as "DEFERRED"
2. Update templates: Remove messaging protocol sections
3. Disable message router in `api/app.py`
4. Hide Message Center in frontend
5. Document decision in `handovers/0118_DEFERRED.md`

**Validation**:
- Existing workflows still work (no messaging required)
- UI hides Message Center
- No errors in console

**Impact**: Multi-agent coordination manual (user must monitor), no dependency auto-detection

---

### Rollback 3: 8-Role System (0117)

**Trigger**: Backward compatibility issues, old jobs break

**Procedure**:
1. Revert frontend color changes (git revert)
2. Keep 6 original templates only
3. Remove backend-implementer, frontend-implementer, devops templates
4. Restore old "implementer" and "reviewer" templates

**Validation**:
- Old agent jobs render correctly
- No console errors
- Template seeding creates 6 templates

**Impact**: Loses agent specialization benefits, but maintains compatibility

---

### Rollback 4: Jobs Tab UI (0114)

**Trigger**: Scope too large, exceeds 2 weeks

**Procedure**:
1. Keep existing Jobs view (simple list)
2. Defer dual-mode tabs to 0200 range
3. Defer 8-state badge system to 0200 range
4. Keep basic status badges only
5. Document decision in `handovers/0114_DEFERRED.md`

**Validation**:
- Existing Jobs view still functional
- Agent cards render
- Status updates work

**Impact**: Loses production-grade UI polish, but core functionality preserved

---

### Rollback 5: Streamable HTTP (0095)

**Trigger**: HTTPS migration breaks existing clients

**Procedure**:
1. Disable HTTPS requirement (set `ALLOW_HTTP_MCP=1`)
2. Keep POST /mcp endpoint only (JSON-RPC)
3. Remove POST/GET /mcp/stream endpoints
4. Document decision in `handovers/0095_DEFERRED.md`

**Validation**:
- Claude Code MCP tools still work
- Existing API key auth works
- No breaking changes

**Impact**: Loses Codex/Gemini CLI support, but Claude Code unaffected

---

### Rollback 6: Feature Development (0131-0150)

**Trigger**: Timeline exceeds 12 weeks, launch urgency

**Procedure**:
1. Complete only P0 features in progress
2. Mark P1/P2 features as "POST-LAUNCH"
3. Create roadmap for post-launch features
4. Document decision in `handovers/FEATURE_ROADMAP_POST_LAUNCH.md`

**Validation**:
- Core features functional (prompt tuning, orchestrator optimization)
- No half-finished features deployed
- Clear plan for post-launch work

**Impact**: Launches with minimum features, adds more post-launch based on user feedback

---

## Resource Requirements

### Phase 1-3: Foundation (Weeks 1-3)

**Human Resources**:
- 1 Full-stack developer (Python + Vue)
- 1 QA engineer (testing support)

**Compute Resources**:
- Development server (localhost)
- PostgreSQL database (localhost)
- Frontend dev server (npm run dev)

**Time Allocation**:
- Week 1-2: 80% on 0130e + 0118 (messaging)
- Week 2: 20% on 0130a testing + 0111 fixes
- Week 3: 100% on 0130b + 0117 (cleanup + 8 roles)

---

### Phase 4-5: Production UI & CLI (Weeks 4-5)

**Human Resources**:
- 1 Frontend developer (Vue + Vuetify)
- 1 Backend developer (FastAPI + MCP)
- 1 QA engineer (UI/UX testing)

**Compute Resources**:
- Development server
- PostgreSQL database
- Frontend dev server
- Test environment for CLI integration

**Time Allocation**:
- Week 4-5: 50% on 0114 (Jobs Tab), 50% on 0095 (Streamable HTTP)
- Parallel execution (2 developers)

---

### Phase 6: Feature Development (Weeks 6-17)

**Human Resources**:
- 1-2 Full-stack developers (depends on scope)
- 1 UX designer (for 0112 Context UX)
- 1 QA engineer (continuous testing)

**Compute Resources**:
- Development server
- Staging environment (production-like)
- PostgreSQL database
- Frontend dev server

**Time Allocation**:
- Weeks 6-8: Prompt Tuning (0131-0135)
- Weeks 9-11: Orchestrator Optimization (0136-0140)
- Weeks 12-14: Slash Commands (0141-0145)
- Weeks 15-16: Close-Out Procedures (0146-0150)
- Week 17: Polish (0112, 0083, 0151-0160)

---

### Phase 7: Launch Preparation (Weeks 18-21)

**Human Resources**:
- 1 DevOps engineer (infrastructure)
- 1 Technical writer (documentation)
- 1 Security engineer (audit)
- 1 QA engineer (comprehensive testing)
- 1 Marketing (demos, videos)

**Compute Resources**:
- Production server (cloud deployment)
- Staging environment (mirror of production)
- PostgreSQL database (production-grade)
- CDN for static assets
- Load testing infrastructure

**Time Allocation**:
- Week 18-19: Infrastructure + Open Source (0200-0219)
- Week 20: QA (0220-0229)
- Week 21: Launch Readiness (0230-0239)

---

## Success Metrics

### Phase 1 Success Metrics: Critical Messaging

**Metric 1: Message Hub Usage**
- **Baseline**: 0 messages (first execution test)
- **Target**: >10 messages in simple 2-agent workflow
- **Measurement**: Query `mcp_agent_messages` table

**Metric 2: Dependency Coordination Success Rate**
- **Baseline**: 0% (no coordination)
- **Target**: 100% when dependencies exist
- **Measurement**: Test workflows with dependencies, verify DEPENDENCY_MET messages

**Metric 3: User Message Response Time**
- **Baseline**: N/A (not implemented)
- **Target**: <30 seconds for acknowledgment
- **Measurement**: Send USER message during workflow, measure time to response

**Metric 4: Blocker Escalation Rate**
- **Baseline**: 0% (blockers not detected)
- **Target**: 100% escalation when blocked
- **Measurement**: Introduce intentional error, verify BLOCKER sent to orchestrator

---

### Phase 2 Success Metrics: Validation & Quick Wins

**Metric 5: WebSocket V2 Stability**
- **Baseline**: Unknown (not tested)
- **Target**: 100% of 17 runtime tests pass
- **Measurement**: Execute `handovers/0130a_MIGRATION_TEST_RESULTS.md` checklist

**Metric 6: Real-Time Update Latency**
- **Baseline**: N/A (requires page refresh)
- **Target**: <500ms from backend event to UI update
- **Measurement**: Measure time from WebSocket broadcast to DOM update

**Metric 7: Orchestrator ID Stability**
- **Baseline**: Changes on every "Stage Project" click
- **Target**: Same ID across 10 consecutive stagings
- **Measurement**: Click "Stage Project" 10 times, verify ID unchanged

---

### Phase 3 Success Metrics: Cleanup & Enhancement

**Metric 8: Zombie Code Elimination**
- **Baseline**: 1,344 lines of backup files
- **Target**: 0 lines of zombie code in /src
- **Measurement**: Count lines in .backup, .old, .bak files

**Metric 9: Agent Role Diversity**
- **Baseline**: 6 roles (implementer, tester, reviewer, analyzer, architect, documenter)
- **Target**: 8 roles (+ backend-implementer, frontend-implementer, devops)
- **Measurement**: Query `mcp_agent_templates` table

**Metric 10: Template Messaging Compliance**
- **Baseline**: 0% templates use messaging
- **Target**: 100% templates include messaging protocol
- **Measurement**: Audit all 8 templates for messaging sections

---

### Phase 4-5 Success Metrics: Production UI & CLI

**Metric 11: Jobs Tab Feature Completeness**
- **Baseline**: Simple list view
- **Target**: 100% of PDF spec implemented (9 slides)
- **Measurement**: Checklist comparison vs PDF

**Metric 12: Message Center Message Volume**
- **Baseline**: 0 messages (Message Center empty)
- **Target**: >50 messages in complex 5-agent workflow
- **Measurement**: Run complex workflow, count messages in Message Center

**Metric 13: Multi-CLI Compatibility**
- **Baseline**: Claude Code only
- **Target**: Claude Code + Codex CLI + Gemini CLI all functional
- **Measurement**: Test spawn_agent_job() from each CLI

**Metric 14: UI Accessibility Score**
- **Baseline**: Unknown
- **Target**: WCAG 2.1 AA (100% compliant)
- **Measurement**: Lighthouse accessibility audit (score ≥90)

---

### Phase 6 Success Metrics: Feature Development

**Metric 15: Prompt A/B Test Success Rate**
- **Baseline**: No A/B testing
- **Target**: 20% improvement in task completion rate (best vs worst prompt)
- **Measurement**: Compare completion rates across prompt variants

**Metric 16: Orchestrator Workflow Efficiency**
- **Baseline**: Manual task breakdown
- **Target**: 50% reduction in manual mission planning time
- **Measurement**: Time to generate mission plan (before vs after optimization)

**Metric 17: Slash Command Usage**
- **Baseline**: 0 slash commands
- **Target**: 20+ commands, 80% user adoption
- **Measurement**: Track command usage in logs, survey user adoption

**Metric 18: Project Close-Out Compliance**
- **Baseline**: No formalized close-out
- **Target**: 100% of projects follow close-out checklist
- **Measurement**: Count projects closed with vs without checklist

---

### Phase 7 Success Metrics: Launch Readiness

**Metric 19: Installation Success Rate**
- **Baseline**: Unknown
- **Target**: 95% one-liner installation success (all platforms)
- **Measurement**: Test on 20 clean machines (Windows, macOS, Linux)

**Metric 20: Security Audit Score**
- **Baseline**: OWASP 10/10 (already achieved)
- **Target**: OWASP 10/10 + zero critical vulnerabilities
- **Measurement**: Penetration test report

**Metric 21: Performance Under Load**
- **Baseline**: Unknown
- **Target**: 100 concurrent users, <500ms API response time
- **Measurement**: Load testing with JMeter or Locust

**Metric 22: Documentation Completeness**
- **Baseline**: Developer docs only
- **Target**: User + Admin + Developer docs 100% complete
- **Measurement**: Checklist of required doc pages

---

## Appendix A: Handover Status Table (0083-0118)

| ID | Title | Status | Priority | Effort | Dependencies | Blocks |
|---|---|---|---|---|---|---|
| 0083 | Slash Commands Harmonization | Not Done | P2 | 2-3h | 0141-0145 | None |
| 0090 | MCP Tool Exposure (duplicate) | Unclear | P3 | 1h | Investigation | None |
| 0095 | Streamable HTTP MCP | Planning | P1 | 2w | None | Codex/Gemini |
| 0100 | One-Liner Installation | Deferred | P3 | 1w | None | Launch |
| 0111 | WebSocket Real-Time Updates | Investigation | P1 | 3-4h | None | None |
| 0112 | Context Prioritization UX | Proposed | P2 | 8-10h | None | None |
| 0114 | Jobs Tab UI/UX | Planning | P1 | 2w | 0118 | None |
| 0117 | 8-Role Agent System | Planning | P1 | 5-6h | 0118 | None |
| 0118 | Agent Messaging Protocol | CRITICAL | P0 | 3-4d | 0130e | 0117, 0114 |
| 0084b-0119 | (32 handovers) | Complete | N/A | N/A | Archived | None |

---

## Appendix B: 0131-0200 Roadmap Overview

### Feature Development (0131-0199)

**Prompt Tuning (0131-0135)**: 2-3 weeks
- A/B testing framework
- Performance metrics dashboard
- Optimization engine
- Version control & rollback
- Prompt library

**Orchestrator Optimization (0136-0140)**: 2-3 weeks
- Smart mission decomposition
- Intelligent agent selection
- Workflow coordination enhancements
- Orchestrator learning system
- Multi-orchestrator coordination

**Slash Commands (0141-0145)**: 2-3 weeks
- Infrastructure & plugin architecture
- Project management commands
- Agent management commands
- Workflow commands
- Debugging & diagnostics commands

**Close-Out Procedures (0146-0150)**: 1-2 weeks
- Completion checklist system
- Project summary generation
- Archive & export functionality
- Post-project analytics
- Knowledge base integration

**Polish & Enhancements (0151-0160)**: 1 week
- 0112: Context UX (8-10h)
- 0083: Slash command harmonization (2-3h)
- Reserved for additional features

### Launch Preparation (0200-0239)

**Infrastructure & Ops (0200-0209)**: 1-2 weeks
- 0200: Aggregate 0100 (one-liner install) + deployment automation
- Server hardening, monitoring, logging, backups, performance

**Open Source Prep (0210-0219)**: 1 week
- LICENSE (MIT), CONTRIBUTING.md, CODE_OF_CONDUCT.md
- GitHub templates, community docs

**Quality Assurance (0220-0229)**: 1-2 weeks
- Security audit, performance benchmarks, cross-platform testing
- Accessibility audit, i18n

**Launch Readiness (0230-0239)**: 1 week
- Demo videos, user docs, developer docs, marketing, support

---

## Appendix C: File References

**Migration Documentation (0130a)**:
- `handovers/0130a_websocket_consolidation.md` - Specification
- `handovers/0130a_MIGRATION_GUIDE.md` - Step-by-step guide
- `handovers/0130a_MIGRATION_TEST_RESULTS.md` - Runtime testing checklist
- `handovers/0130a_COMPLETION_SUMMARY.md` - Build results

**Audit Reports**:
- `handovers/0083-0118_AUDIT_REPORT.md` - Status of 37 handovers
- `handovers/0130_SERIES_CLOSURE_SUMMARY.md` - 0120-0130 accomplishments

**Roadmaps**:
- `handovers/REFACTORING_ROADMAP_0120-0130.md` - Retired (complete)
- `handovers/REFACTORING_ROADMAP_0131-0200.md` - Active (feature dev + launch)

**Active Handovers (0130 Series)**:
- `handovers/0130b_remove_zombie_code_and_backups.md`
- `handovers/0130c_consolidate_duplicate_components.md`
- `handovers/0130d_centralize_api_calls.md`
- `handovers/0130e_fix_inter_agent_messaging.md`

**Execution Plans**:
- `handovers/0130_SERIES_EXECUTION_PLAN.md` - Detailed 0130 plan
- `handovers/COMPLETE_EXECUTION_PLAN_0083_TO_0200.md` - This document

---

## Tool Selection Matrix

### Phase 1: Critical Messaging Infrastructure (Week 1-2)

#### 0130e: Fix Inter-Agent Messaging Infrastructure
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - Database wiring required (register router in api/app.py)
  - WebSocket broadcast debugging (requires live system)
  - End-to-end testing with backend running
  - API endpoint validation (POST/GET /api/messages)
- **Can Parallelize**: ❌ No
- **Workflow**:
  1. CLI: Investigate message routing
  2. CLI: Wire router in api/app.py
  3. CLI: Test endpoints with backend running
  4. CLI: Validate WebSocket broadcasts
  5. CLI: Archive 0130e-C.md

---

#### 0118: Agent Messaging Protocol Implementation
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - Pure template updates (7 Python files)
  - No database changes required
  - Large refactoring (leverage cloud tokens)
  - Can test templates offline (no live backend needed)
- **Can Parallelize**: ❌ No (depends on 0130e complete)
- **Workflow**:
  1. CCW: Create branch (e.g., claude/0118-agent-messaging)
  2. CCW: Update orchestrator template (messaging protocol)
  3. CCW: Update 6 agent templates (check messages, report progress)
  4. CCW: Update mission_planner.py (dependency auto-detect)
  5. CCW: Push to GitHub
  6. YOU: Merge into master
  7. CLI: Pull locally, test with live backend
  8. CLI: Run 5 test workflows (simple, dependency, blocker, user, multi-terminal)
  9. CLI: Archive 0118-C.md if tests pass

---

### Phase 2: Validation & Quick Wins (Week 2)

#### 0130a: Runtime Testing
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - Requires live backend + frontend running
  - Browser testing (Chrome DevTools)
  - Memory leak detection (heap snapshots)
  - WebSocket connection validation
  - Real-time update testing
- **Can Parallelize**: ❌ No
- **Workflow**:
  1. CLI: Start backend (python startup.py)
  2. CLI: Start frontend (cd frontend && npm run dev)
  3. CLI: Execute 17-item checklist from 0130a_MIGRATION_TEST_RESULTS.md
  4. CLI: If pass → Archive 0130a-C.md
  5. CLI: If fail → Document issues, create fix handover

---

#### 0111: WebSocket Real-Time Updates & Orchestrator ID Bug
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - Runtime debugging required (WebSocket broadcasts)
  - FastAPI state investigation
  - Database fix (orchestrator ID stability)
  - Requires backend running for testing
- **Can Parallelize**: ✅ Yes (can run while 0130a testing)
- **Workflow**:
  1. CLI: Investigate WebSocket broadcast failure (1 hour)
  2. CLI: Implement fix (likely: pass WebSocket manager to MCP tools)
  3. CLI: Fix orchestrator ID creation logic
  4. CLI: Test end-to-end (mission appears, agent cards appear, no refresh)
  5. CLI: Archive 0111-C.md

---

### Phase 3: Cleanup & Enhancement (Week 3)

#### 0130b: Remove Zombie Code and Backups
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - File deletion (local filesystem operations)
  - Verify build succeeds after deletion
  - Create DEPRECATED_PATTERNS.md
- **Can Parallelize**: ❌ No
- **Workflow**:
  1. CLI: Delete 4 .backup-0130a files (1,344 lines)
  2. CLI: Audit for other .bak, .old, .example files
  3. CLI: npm run build (verify success)
  4. CLI: Create docs/DEPRECATED_PATTERNS.md
  5. CLI: Git commit
  6. CLI: Archive 0130b-C.md

---

#### 0117: 8-Role Agent System Refactoring
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - Template updates (4 new Python files)
  - Frontend color config (JavaScript/SCSS)
  - Documentation updates (Markdown)
  - No database changes
- **Can Parallelize**: ⚠️ Depends on 0118 complete (needs messaging in templates)
- **Workflow**:
  1. CCW: Create branch (claude/0117-8-role-system)
  2. CCW: Create 4 new templates (backend-implementer, frontend-implementer, code-reviewer, devops)
  3. CCW: Update frontend colors (agentColors.js, agent-colors.scss)
  4. CCW: Update docs (Simple_Vision.md, AGENT_CONTEXT_ESSENTIAL.md)
  5. CCW: Push to GitHub
  6. YOU: Merge into master
  7. CLI: Pull locally, test fresh install (8 templates created)
  8. CLI: Test backward compatibility (old "implementer" jobs still render)
  9. CLI: Archive 0117-C.md

---

### Phase 4-5: Production UI & Multi-CLI (Week 4-5, PARALLEL)

#### 0114: Jobs Tab UI/UX Harmonization
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - Pure Vue 3 frontend work (components, styles)
  - Large refactoring (2 weeks, many tokens)
  - No backend changes required
  - Can test UI in isolation
- **Can Parallelize**: ✅ Yes (can run with 0095)
- **Depends On**: 0118 complete (Message Center needs real messages)
- **Workflow**:
  1. CCW: Create branch (claude/0114-jobs-tab-ui)
  2. CCW: Phase 1 - Dual tabs (2 days)
  3. CCW: Phase 2 - 8-state badges (2 days)
  4. CCW: Phase 3 - Claude Code toggle (2 days)
  5. CCW: Phase 4 - Orchestrator actions (2 days)
  6. CCW: Phase 5 - Message Center integration (3 days)
  7. CCW: Phase 6 - Visual polish (3 days)
  8. CCW: Push to GitHub
  9. YOU: Merge into master
  10. CLI: Pull locally, test UI with live backend
  11. CLI: Accessibility audit (Lighthouse)
  12. CLI: Archive 0114-C.md

---

#### 0095: Streamable HTTP MCP Architecture
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - API endpoint creation (FastAPI routes)
  - Documentation (Markdown, examples)
  - No database changes
  - Can develop endpoints in isolation
- **Can Parallelize**: ✅ Yes (can run with 0114, independent)
- **Workflow**:
  1. CCW: Create branch (claude/0095-streamable-http)
  2. CCW: Phase 1 - POST/GET /mcp/stream endpoints (3 days)
  3. CCW: Phase 2 - HTTPS toggle in Admin Settings (3 days)
  4. CCW: Phase 3 - Proxy configs (nginx, Caddy) (2 days)
  5. CCW: Phase 5 - Documentation (2 days)
  6. CCW: Push to GitHub
  7. YOU: Merge into master
  8. CLI: Pull locally
  9. CLI: Phase 4 - Test with Codex CLI, Gemini CLI (4 days)
  10. CLI: Archive 0095-C.md

---

### Decision Point: 0130c/d or Skip?

#### 0130c: Consolidate Duplicate Components (If chosen)
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - Vue component refactoring
  - Extract shared logic to composables
  - No backend changes
- **Can Parallelize**: ✅ Yes (can run with 0130d)
- **Workflow**:
  1. CCW: Create branch (claude/0130c-consolidate)
  2. CCW: Merge AgentCard variants (1 day)
  3. CCW: Merge Timeline variants (1 day)
  4. CCW: Push to GitHub
  5. YOU: Merge, test locally
  6. CLI: Archive 0130c-C.md

---

#### 0130d: Centralize API Calls (If chosen)
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - Frontend refactoring (centralize axios calls)
  - Create api.js module
  - No backend changes
- **Can Parallelize**: ✅ Yes (can run with 0130c)
- **Workflow**:
  1. CCW: Create branch (claude/0130d-centralize-api)
  2. CCW: Create frontend/src/api/api.js (2 days)
  3. CCW: Migrate 30+ raw axios calls (1 day)
  4. CCW: Push to GitHub
  5. YOU: Merge, test locally
  6. CLI: Archive 0130d-C.md

---

### Phase 6: Feature Development (Week 6-17)

#### 0131-0135: Prompt Tuning for Agents
- **Tool**: ☁️ **CCW (Cloud)** (with CLI for testing)
- **Why**:
  - Template updates, frontend dashboards
  - Can split across 2-3 CCW sessions (parallel)
  - CLI needed for database testing
- **Can Parallelize**: ✅ Yes (split into sub-handovers, run 2-3 in parallel)
- **Workflow**:
  1. CCW Session 1: 0131 (A/B testing framework) - 1 week
  2. CCW Session 2: 0132 (Performance dashboard) - 1 week (parallel with 0131)
  3. CCW Session 3: 0133 (Optimization engine) - 1 week
  4. CLI: Merge all, test with database
  5. CCW Session 4: 0134 (Version control) - 3 days
  6. CCW Session 5: 0135 (Prompt library) - 3 days (parallel with 0134)
  7. CLI: Final integration testing
  8. CLI: Archive 0131-0135-C.md

---

#### 0136-0140: Orchestrator Optimization
- **Tool**: 🔀 **MIX (CCW for frontend, CLI for backend)**
- **Why**:
  - Backend logic changes (mission_planner.py, agent_selector.py)
  - Frontend dashboards (Vue components)
  - Database queries (requires CLI testing)
- **Can Parallelize**: ⚠️ Partial (frontend sessions parallel, backend sequential)
- **Workflow**:
  1. CLI: 0136 (Smart mission decomposition) - 1 week (backend heavy)
  2. CCW: 0137 (Intelligent agent selection) - 1 week (can run parallel)
  3. CLI: 0138 (Workflow coordination) - 1 week (backend heavy)
  4. CCW: 0139 (Orchestrator learning UI) - 3 days (frontend)
  5. CLI: 0140 (Multi-orchestrator) - 4 days (database + backend)
  6. CLI: Integration testing
  7. CLI: Archive 0136-0140-C.md

---

#### 0141-0145: Slash Command System
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - MCP tool registration (backend)
  - Database schema changes (slash_commands table)
  - Plugin architecture (requires testing)
  - Commands trigger workflows (integration testing)
- **Can Parallelize**: ❌ No (sequential, database dependent)
- **Workflow**:
  1. CLI: 0141 (Infrastructure) - 1 week
  2. CLI: 0142 (Project commands) - 3 days
  3. CLI: 0143 (Agent commands) - 3 days
  4. CLI: 0144 (Workflow commands) - 3 days
  5. CLI: 0145 (Debug commands) - 2 days
  6. CLI: Integration testing (all commands)
  7. CLI: Archive 0141-0145-C.md

---

#### 0146-0150: Project Close-Out Procedures
- **Tool**: ☁️ **CCW (Cloud)** (with CLI for testing)
- **Why**:
  - Mostly frontend (checklists, reports, UI)
  - Some backend (summary generation, export)
  - Can parallelize frontend work
- **Can Parallelize**: ✅ Yes (frontend sessions can run parallel)
- **Workflow**:
  1. CCW Session 1: 0146 (Checklist system) - 3 days
  2. CCW Session 2: 0147 (Summary generation) - 3 days (parallel)
  3. CCW Session 3: 0148 (Archive/export) - 3 days
  4. CLI: Merge, test export with database
  5. CCW Session 4: 0149 (Analytics) - 2 days
  6. CCW Session 5: 0150 (Knowledge base) - 2 days (parallel)
  7. CLI: Final integration testing
  8. CLI: Archive 0146-0150-C.md

---

#### 0112: Context Prioritization UX Enhancements
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - Pure Vue 3 frontend work
  - Dashboard, charts, visualizations
  - No backend changes
- **Can Parallelize**: ✅ Yes (independent, can run anytime)
- **Workflow**:
  1. CCW: Create branch (claude/0112-context-ux)
  2. CCW: Mission summary panel (3 hours)
  3. CCW: Agent card token badges (2 hours)
  4. CCW: System metrics dashboard (3 hours)
  5. CCW: Context visualization (treemap) (2 hours)
  6. CCW: Push to GitHub
  7. YOU: Merge, test locally
  8. CLI: Archive 0112-C.md

---

#### 0083: Slash Commands /gil Pattern Harmonization
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - MCP tool registration updates
  - Command testing with live backend
  - Documentation updates
- **Can Parallelize**: ❌ No
- **Should Run After**: 0141-0145 (all commands exist first)
- **Workflow**:
  1. CLI: Audit existing slash commands
  2. CLI: Rename to /gil_* pattern
  3. CLI: Update MCP registration
  4. CLI: Test all commands
  5. CLI: Update docs
  6. CLI: Archive 0083-C.md

---

### Phase 7: Launch Preparation (Week 18-21)

#### 0200-0209: Infrastructure & Ops
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - One-liner installation (cross-platform testing)
  - Server hardening (deployment, monitoring)
  - Database backups (PostgreSQL)
  - Performance optimization (load testing)
- **Can Parallelize**: ❌ No (deployment + testing sequential)
- **Workflow**:
  1. CLI: 0200 (One-liner install) - 1 week
  2. CLI: Test on macOS, Windows, Linux (clean machines)
  3. CLI: 0201-0205 (Hardening, monitoring, logging, backups, performance) - 1 week
  4. CLI: Archive 0200-0209-C.md

---

#### 0210-0219: Open Source Preparation
- **Tool**: ☁️ **CCW (Cloud)**
- **Why**:
  - Pure documentation (Markdown files)
  - Can parallelize across multiple sessions
  - No backend/database required
- **Can Parallelize**: ✅ Yes (split into 2-3 parallel sessions)
- **Workflow**:
  1. CCW Session 1: 0210-0212 (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT) - 2 days
  2. CCW Session 2: 0213-0214 (GitHub templates, community docs) - 2 days (parallel)
  3. CCW Session 3: 0215-0219 (Additional docs) - 3 days (parallel)
  4. YOU: Merge all, review
  5. CLI: Archive 0210-0219-C.md

---

#### 0220-0229: Quality Assurance
- **Tool**: 🔧 **CLI (Local)**
- **Why**:
  - Security testing (penetration, vulnerability scans)
  - Performance benchmarks (load testing with live backend)
  - Cross-platform testing (real machines)
  - Accessibility audit (Lighthouse, screen readers)
- **Can Parallelize**: ❌ No (testing requires sequential validation)
- **Workflow**:
  1. CLI: 0220 (Security audit) - 3 days
  2. CLI: 0221 (Performance benchmarks) - 2 days
  3. CLI: 0222 (Cross-platform testing) - 3 days
  4. CLI: 0223 (Accessibility audit) - 2 days
  5. CLI: 0224 (i18n testing) - 2 days
  6. CLI: Archive 0220-0229-C.md

---

#### 0230-0239: Launch Readiness
- **Tool**: ☁️ **CCW (Cloud)** (with CLI for video production)
- **Why**:
  - Documentation (Markdown, user guides)
  - Marketing materials (can parallelize)
  - Demo videos (may need CLI for screen recording)
- **Can Parallelize**: ✅ Yes (split into 2-3 parallel sessions)
- **Workflow**:
  1. CCW Session 1: 0230-0232 (Videos, user docs, dev docs) - 3 days
  2. CCW Session 2: 0233-0234 (Marketing, support) - 2 days (parallel)
  3. CCW Session 3: 0235-0239 (Additional launch tasks) - 2 days (parallel)
  4. CLI: Record demo videos (screen recording)
  5. CLI: Archive 0230-0239-C.md

---

## Summary: Tool Selection by Phase

| Phase | CCW Sessions | CLI Sessions | Can Parallelize |
|-------|--------------|--------------|-----------------|
| **Phase 1** (Weeks 1-2) | 1 (0118) | 1 (0130e) | ❌ Sequential |
| **Phase 2** (Week 2) | 0 | 2 (0130a, 0111) | ✅ Both CLI can run parallel |
| **Phase 3** (Week 3) | 1 (0117) | 1 (0130b) | ❌ Sequential |
| **Phase 4-5** (Weeks 4-5) | 2 (0114, 0095) | 1 (0095 testing) | ✅ CCW parallel, CLI after |
| **Phase 6** (Weeks 6-17) | 5-10 sessions | 3-5 sessions | ✅ Many parallel opportunities |
| **Phase 7** (Weeks 18-21) | 2-3 sessions | 2 sessions | ⚠️ Partial (docs parallel, QA sequential) |

**Total CCW Sessions**: ~15-20 (leverage cloud tokens heavily)
**Total CLI Sessions**: ~10-15 (database, testing, deployment)

---

## Change Log

| Date | Version | Changes | Author |
|---|---|---|---|
| 2025-01-12 | 1.0 | Initial execution plan created | Claude Code CLI |
| 2025-01-12 | 1.1 | Added tool selection matrix (CCW vs CLI) | Claude Code CLI |

---

**END OF EXECUTION PLAN**
