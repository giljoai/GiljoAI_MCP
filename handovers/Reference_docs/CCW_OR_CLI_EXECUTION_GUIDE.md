# CCW vs CLI Execution Guide

**Version**: 1.0
**Created**: 2025-11-12
**Purpose**: Decision framework for task distribution between Claude Code CLI (local) and Claude Code Web (cloud)
**Scope**: All GiljoAI MCP handovers (0083-0239)

---

## EXECUTIVE SUMMARY

This guide provides a comprehensive decision framework for choosing between **Claude Code CLI** (local development with database access) and **Claude Code Web** (cloud-based parallel development) when executing GiljoAI MCP handovers.

**Key Insight**: CCW excels at parallel, pure-code tasks (frontend, documentation, templates), while CLI is required for database-dependent, sequential, or integration tasks.

**Workflow Philosophy** (Direct from User):
> "I have you (claude code CLI, local to DB and on the dev machine with the application) and I have claude code web (CCW) at my disposal, I have a lot of coding tokens to spend in CCW. However it works like this Creates new branch → pulls in master → writes code in CCW environment on cloud → pushes to GitHub. I as a user have to merge into master or current working branch I am using, and test local and maybe diagnose with you claude code CLI locally. CCW works really well because it allows a lot of parallel projects to run if we can/want."

---

## TABLE OF CONTENTS

1. [Quick Decision Tree](#quick-decision-tree)
2. [When to Use CLI](#when-to-use-cli)
3. [When to Use CCW](#when-to-use-ccw)
4. [Execution Patterns](#execution-patterns)
5. [Task Mapping Table](#task-mapping-table)
6. [Workflow Examples](#workflow-examples)
7. [Best Practices](#best-practices)
8. [Testing Strategy](#testing-strategy)
9. [Merge Strategy](#merge-strategy)
10. [Common Pitfalls](#common-pitfalls)

---

## QUICK DECISION TREE

```
Start: New Handover Task
         |
         ├─> Does it modify database schema? ───────> YES → CLI (Sequential)
         |                                              NO ↓
         |
         ├─> Does it require live DB access? ──────────> YES → CLI (Sequential)
         |   (e.g., testing, migrations, queries)        NO ↓
         |
         ├─> Does it involve file system operations? ──> YES → CLI (Sequential)
         |   (delete, move, cleanup)                     NO ↓
         |
         ├─> Does it require debugging/diagnostics? ───> YES → CLI (Sequential)
         |   (WebSocket, API, performance)               NO ↓
         |
         ├─> Does it depend on other in-progress work? > YES → Wait → CLI/CCW (Sequential)
         |                                                NO ↓
         |
         ├─> Is it pure code? ──────────────────────────> YES → CCW (Parallel)
         |   (frontend, templates, docs, endpoints)
         |
         └─> DEFAULT: Start with CCW, test locally with CLI
```

---

## WHEN TO USE CLI

### Core Criteria
Use **Claude Code CLI (Local)** when tasks require:
- Direct database access (PostgreSQL)
- Live backend runtime environment
- Local file system operations
- Integration testing with full stack
- MCP tool registration and testing
- Debugging and diagnostics

### Specific Use Cases

#### 1. Database Operations
**Why CLI**: Requires PostgreSQL connection, schema modifications, or data migrations.

**Examples**:
- Schema changes (new columns, indexes, constraints)
- Database migrations (Alembic scripts)
- Data seeding or backfilling
- Complex queries requiring EXPLAIN ANALYZE
- Multi-tenant isolation testing

**Handovers**: 0500, 0501, 0502, 0510, 0135, 0136

```bash
# Typical CLI workflow for DB tasks
cd /f/GiljoAI_MCP
source venv/bin/activate
pytest tests/test_product_service.py -v
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp
```

#### 2. Integration Testing
**Why CLI**: Requires live backend + database + frontend stack.

**Examples**:
- E2E workflow testing (product → project → orchestrator)
- WebSocket real-time updates validation
- API endpoint integration tests (pytest with DB fixtures)
- Multi-tenant isolation verification
- Performance benchmarking

**Handovers**: 0510, 0511, 0130a, 0220-0229

```bash
# Integration testing workflow
python startup.py --dev  # Start backend
cd frontend/ && npm run dev  # Start frontend
pytest tests/integration/ -v --db-fixtures
```

#### 3. Debugging & Diagnostics
**Why CLI**: Requires live system observation, logs, breakpoints.

**Examples**:
- WebSocket connection issues
- API response debugging (401/501/404 errors)
- Performance profiling (slow queries, memory leaks)
- Log analysis (backend + frontend + PostgreSQL)
- Network diagnostics (CORS, firewall, ports)

**Handovers**: 0111, 0130a, ACTIVE_DEBUGGING_websocket_realtime_updates.md

```bash
# Debugging workflow
tail -f logs/giljo_mcp.log  # Watch backend logs
tail -f /f/PostgreSQL/data/postgresql.log  # Watch DB logs
curl -v http://192.168.1.192:7272/api/health  # Test endpoints
```

#### 4. File System Operations
**Why CLI**: Requires local file access, deletion, cleanup.

**Examples**:
- Deleting deprecated files (cleanup after refactoring)
- Moving files between directories
- Log rotation and archiving
- Temporary file cleanup
- Git branch cleanup

**Handovers**: 0130b (file deletion)

```bash
# File cleanup workflow
git rm src/giljo_mcp/deprecated_module.py
find logs/ -type f -mtime +30 -delete
git clean -fdx  # Remove untracked files
```

#### 5. MCP Tool Development
**Why CLI**: Requires MCP server registration, testing with Claude Code.

**Examples**:
- Adding new MCP tools (`src/giljo_mcp/tools/`)
- Testing MCP tool functionality with `claude-code mcp test`
- Debugging MCP server connectivity
- Validating multi-tenant isolation in MCP tools

**Handovers**: 0083, 0095 (MCP endpoints), 0138 (closeout tool), 0141-0145 (slash commands)

```bash
# MCP tool development workflow
cd src/giljo_mcp/tools/
# Add new tool: new_tool.py
# Register in __init__.py
python -m pytest tests/test_mcp_tools.py -k test_new_tool
claude-code mcp test giljo-mcp new_tool
```

#### 6. Sequential Dependencies
**Why CLI**: Tasks that MUST run in order, cannot parallelize.

**Examples**:
- Service layer → API endpoints → Frontend (Phase 0 → 1 → 2)
- Database migration → Data backfill → Test suite
- Refactoring → Integration tests → Deployment

**Handovers**: All Phase 0 tasks (0500-0502), then Phase 1, etc.

---

## WHEN TO USE CCW

### Core Criteria
Use **Claude Code Web (Cloud)** when tasks:
- Are pure code changes (no DB required)
- Can run independently (no hard dependencies)
- Benefit from parallelization (3-4 simultaneous branches)
- Leverage cloud token budget efficiently
- Don't require local environment

### Specific Use Cases

#### 1. Frontend Development
**Why CCW**: Pure Vue 3 + Vuetify code, no backend/DB needed during development.

**Examples**:
- New Vue components (forms, dialogs, cards)
- UI/UX improvements (styles, layouts, responsiveness)
- Frontend refactoring (component consolidation)
- Vuetify theming and customization
- Frontend routing and navigation

**Handovers**: 0507-0509, 0114, 0112, 0130c, 0130d, 0515, 0137 (GitHub backend UI), 0139b (WebSocket listeners)

**Parallelization**: Can run 2-3 frontend handovers simultaneously on separate CCW branches.

```
CCW Branch 1: 0507_api_client_url_fixes
CCW Branch 2: 0508_vision_upload_error_handling
CCW Branch 3: 0509_succession_ui_components
↓
User merges all 3 → Tests locally with CLI
```

#### 2. API Endpoint Creation
**Why CCW**: Pure FastAPI code, no DB logic required (service layer handles DB).

**Examples**:
- REST endpoint definitions (`api/endpoints/`)
- Request/response models (Pydantic schemas)
- API route registration (`api/app.py`)
- Endpoint documentation (OpenAPI)
- Basic endpoint logic (calling service methods)

**Handovers**: 0503-0506 (all 4 can run in parallel)

**Parallelization**: 4 CCW branches for endpoint groups.

```
CCW Branch 1: 0503_product_endpoints
CCW Branch 2: 0504_project_endpoints
CCW Branch 3: 0505_orchestrator_succession_endpoint
CCW Branch 4: 0506_settings_endpoints
↓
User merges all 4 → CLI runs integration tests
```

#### 3. Agent Template Updates
**Why CCW**: Pure markdown/text files, template logic in Python (no DB during edit).

**Examples**:
- Agent prompt engineering (orchestrator, implementer, tester)
- Template variable updates
- Behavioral rules and success criteria
- Mission condensation templates
- Tool preference updates

**Handovers**: 0118, 0117 (templates), 0131-0135 (prompt tuning)

**Parallelization**: Can update 6 agent templates simultaneously (one per CCW branch).

```
CCW Branch 1: Update orchestrator_template.md
CCW Branch 2: Update implementer_template.md
CCW Branch 3: Update tester_template.md
CCW Branch 4: Update reviewer_template.md
CCW Branch 5: Update documenter_template.md
CCW Branch 6: Update optimizer_template.md
↓
User merges all 6 → CLI tests template resolution
```

#### 4. Documentation Writing
**Why CCW**: Markdown files, no local environment needed.

**Examples**:
- User guides (installation, quick start, features)
- Developer guides (architecture, API reference, contributing)
- Handover documentation (scoped task descriptions)
- Roadmap updates (execution plans, timelines)
- Session memories and devlogs

**Handovers**: 0512-0514 (all 3 can run in parallel)

**Parallelization**: 3 CCW branches for documentation types.

```
CCW Branch 1: 0512_CLAUDE_md_update_cleanup
CCW Branch 2: 0513_handover_0132_documentation
CCW Branch 3: 0514_roadmap_rewrites
↓
User merges all 3 → CLI validates links/formatting
```

#### 5. Pure Refactoring
**Why CCW**: Code restructuring without behavior changes, testable after merge.

**Examples**:
- Component consolidation (duplicate removal)
- API call centralization (DRY principle)
- Module reorganization (file moves, renames)
- Code cleanup (removing stubs, dead code)
- Linting and formatting

**Handovers**: 0130c, 0130d, 0515

**Parallelization**: Can run both 0130c and 0130d in parallel.

```
CCW Branch 1: 0130c_consolidate_duplicate_components
CCW Branch 2: 0130d_centralize_api_calls
↓
User merges both → CLI runs test suite
```

#### 6. Independent Feature Work
**Why CCW**: Features with no cross-dependencies, can develop in isolation.

**Examples**:
- New UI features (context prioritization UX)
- New API features (job dynamic links)
- New tools (MCP tool additions)
- Performance optimizations (caching, query tuning)

**Handovers**: 0112, 0135, 0146-0150

**Parallelization**: Multiple CCW branches for independent features.

---

## EXECUTION PATTERNS

### Pattern 1: Sequential CLI Workflow
**Use Case**: Database migrations, service layer development, integration testing.

```
Phase 0: Service Layer (CLI, Sequential)
├─> 0500: ProductService Enhancement (4h)
│   └─> CLI: Implement service methods with DB queries
├─> 0501: ProjectService Implementation (12-16h)
│   └─> CLI: Implement lifecycle methods with DB transactions
└─> 0502: OrchestrationService Integration (4-5h)
    └─> CLI: Integrate AgentJobManager with context tracking

Total: 3-4 days, CLI only, cannot parallelize
```

**Why Sequential**: Each service builds on the previous one, requires DB schema from prior steps.

### Pattern 2: Parallel CCW Workflow
**Use Case**: Independent API endpoints, frontend components, documentation.

```
Phase 1: API Endpoints (CCW, Parallel)
├─> CCW Branch 1: 0503_product_endpoints (2h)
├─> CCW Branch 2: 0504_project_endpoints (4h)
├─> CCW Branch 3: 0505_orchestrator_succession_endpoint (3h)
└─> CCW Branch 4: 0506_settings_endpoints (3-4h)

Total: 4h wall-clock time (4 simultaneous CCW sessions)
vs. 12-13h sequential time (400% speedup)
```

**Why Parallel**: No dependencies, all endpoints call service layer (already implemented in Phase 0).

### Pattern 3: Mixed CLI → CCW Workflow
**Use Case**: Service layer (CLI) enables endpoint development (CCW).

```
Week 1:
├─> Days 1-3: CLI (Service Layer)
│   ├─> 0500, 0501, 0502 (sequential)
│   └─> User tests locally: Service methods work
└─> Days 4-5: CCW (Endpoints)
    ├─> 4 parallel CCW branches (0503-0506)
    └─> User merges all 4 → CLI integration tests

Week 2:
├─> Days 1-2: CCW (Frontend)
│   ├─> 3 parallel CCW branches (0507-0509)
│   └─> User merges all 3 → CLI UI testing
└─> Days 3-5: CLI (Integration Testing)
    └─> 0510, 0511 (pytest + E2E)
```

**Why Mixed**: CLI establishes foundation, CCW parallelizes implementation, CLI validates.

### Pattern 4: CCW → CLI → CCW Iteration
**Use Case**: Rapid prototyping with local validation.

```
Iteration 1:
├─> CCW: Implement feature on branch
├─> User: Merge to master
├─> CLI: Test locally, find bugs
├─> CCW: Fix bugs on new branch
├─> User: Merge fixes
└─> CLI: Validate fixes work

Iteration 2:
├─> CCW: Add enhancements
└─> ... repeat cycle
```

**Why Iteration**: CCW for fast coding, CLI for real testing, iterate until stable.

---

## TASK MAPPING TABLE

### Projectplan_500: Handovers 0500-0515

| Handover | Title | Tool | Duration | Parallel? | Phase |
|----------|-------|------|----------|-----------|-------|
| **0500** | ProductService Enhancement | **CLI** | 4h | ❌ No (DB) | 0 |
| **0501** | ProjectService Implementation | **CLI** | 12-16h | ❌ No (DB) | 0 |
| **0502** | OrchestrationService Integration | **CLI** | 4-5h | ❌ No (DB) | 0 |
| **0503** | Product Endpoints | **CCW** | 2h | ✅ Yes (Group 1) | 1 |
| **0504** | Project Endpoints | **CCW** | 4h | ✅ Yes (Group 1) | 1 |
| **0505** | Orchestrator Succession Endpoint | **CCW** | 3h | ✅ Yes (Group 1) | 1 |
| **0506** | Settings Endpoints | **CCW** | 3-4h | ✅ Yes (Group 1) | 1 |
| **0507** | API Client URL Fixes | **CCW** | 1h | ✅ Yes (Group 2) | 2 |
| **0508** | Vision Upload Error Handling | **CCW** | 2h | ✅ Yes (Group 2) | 2 |
| **0509** | Succession UI Components | **CCW** | 4-6h | ✅ Yes (Group 2) | 2 |
| **0510** | Fix Broken Test Suite | **CLI** | 8-12h | ❌ No (DB + pytest) | 3 |
| **0511** | E2E Integration Tests | **CLI** | 12-16h | ❌ No (DB + E2E) | 3 |
| **0512** | CLAUDE.md Update & Cleanup | **CCW** | 2h | ✅ Yes (Group 3) | 4 |
| **0513** | Handover 0132 Documentation | **CCW** | 2h | ✅ Yes (Group 3) | 4 |
| **0514** | Roadmap Rewrites | **CCW** | 10h | ✅ Yes (Group 3) | 4 |
| **0515** | Frontend Consolidation | **CCW** | 1-2 days | ⚠️ Sequential | 5 |

**Parallelization Summary**:
- **Group 1 (Phase 1)**: 4 parallel CCW branches (0503-0506) - 12h sequential → 4h wall-clock (300% speedup)
- **Group 2 (Phase 2)**: 3 parallel CCW branches (0507-0509) - 7h sequential → 6h wall-clock (17% speedup)
- **Group 3 (Phase 4)**: 3 parallel CCW branches (0512-0514) - 14h sequential → 10h wall-clock (40% speedup)

### 360 Memory Management: Handovers 0135-0139

| Handover | Title | Tool | Duration | Parallel? | Reason |
|----------|-------|------|----------|-----------|--------|
| **0135** | Database Schema (product_memory JSONB) | **CLI** | 1d | ❌ No (DB) | Alembic migration, GIN index, multi-tenant testing |
| **0136** | Memory Initialization | **CLI** | 1d | ❌ No (DB) | ProductService.create_product() modification, backward compat |
| **0137** | GitHub Integration Backend | **CCW** | 1d | ✅ Yes (Group F) | Pure FastAPI + Vue UI enablement, no DB during dev |
| **0138** | Project Closeout MCP Tool | **CLI** | 1.5d | ❌ No (MCP) | MCP tool registration, orchestrator workflow testing |
| **0139a** | WebSocket Event Emission | **CLI** | 0.5d | ⚠️ Partial (Group G) | Service layer event emission, tenant isolation |
| **0139b** | Frontend WebSocket Listeners | **CCW** | 0.5d | ⚠️ Partial (Group G) | Vue components, event handlers, toast notifications |

**Parallelization Strategy**:
- **Group F**: 0137 (CCW) can overlap with 0136 (CLI) testing phase
- **Group G**: 0139a (CLI) + 0139b (CCW) can run simultaneously

**Dependency Chain**: 0135 → 0136 → 0137 → 0138 → 0139a+b

**Wall-Clock Time**: 5 days (vs 5.5 days sequential) through strategic parallelization

### Complete Execution Plan: Handovers 0083-0239

| Handover | Title | Tool | Duration | Parallel? | Category |
|----------|-------|------|----------|-----------|----------|
| **0130e** | Runtime + Validation Checks | **CLI** | 4-6h | ❌ No (DB + API) | Refactoring |
| **0118** | Agent Role Refactor (8 roles) | **CCW** | 3-4 days | ❌ No (depends on 0130e) | Templates |
| **0130a** | Runtime Testing | **CLI** | 2-3h | ❌ No (live system) | Testing |
| **0111** | WebSocket Debugging | **CLI** | 3-4h | ❌ No (DB + diagnostics) | Debugging |
| **0130b** | File Deletion Cleanup | **CLI** | 2-3h | ❌ No (filesystem) | Cleanup |
| **0117** | Templates + Frontend Colors | **CCW** | 5-6h | ✅ Can run with 0095 | Templates |
| **0095** | MCP Streamable HTTP API | **CCW** | 2 weeks | ✅ Can run with 0117 | API |
| **0114** | Jobs Tab UI Harmonization | **CCW** | 2 weeks | ⚠️ After 0118 | Frontend |
| **0130c** | Consolidate Duplicate Components | **CCW** | 1-2 days | ✅ Can run with 0130d | Refactoring |
| **0130d** | Centralize API Calls | **CCW** | 2-3 days | ✅ Can run with 0130c | Refactoring |
| **0131-0135** | Prompt Tuning (5 handovers) | **CCW** | 2-3 weeks | ✅ Split across 2-3 CCW | Prompts |
| **0136-0140** | Orchestrator Optimization | **Mix** | 2-3 weeks | ⚠️ Backend (CLI), Frontend (CCW) | Orchestrator |
| **0141-0145** | Slash Commands (5 handovers) | **CLI** | 2-3 weeks | ❌ No (MCP tools + DB) | MCP Tools |
| **0146-0150** | Close-Out Features | **CCW** | 1-2 weeks | ✅ Mostly frontend | Features |
| **0112** | Context Prioritization UX | **CCW** | 8-10h | ✅ Pure frontend | Frontend |
| **0083** | Slash Command Harmony | **CLI** | 2-3h | ❌ No (MCP registration) | MCP Tools |
| **0200-0209** | Infrastructure (10 handovers) | **CLI** | 1-2 weeks | ❌ No (deployment + DB) | Launch Prep |
| **0210-0219** | Open Source (10 handovers) | **CCW** | 1 week | ✅ Documentation (parallel) | Launch Prep |
| **0220-0229** | QA & Testing (10 handovers) | **CLI** | 1-2 weeks | ❌ No (testing + validation) | Launch Prep |
| **0230-0239** | Launch (10 handovers) | **CCW** | 1 week | ✅ Docs + videos (parallel) | Launch Prep |

**Key Insights**:
- **CLI-Required**: 0130e, 0130a, 0111, 0130b, 0141-0145, 0083, 0200-0209, 0220-0229 (25 handovers)
- **CCW-Optimal**: 0118, 0117, 0095, 0114, 0130c-d, 0131-0135, 0146-0150, 0112, 0210-0219, 0230-0239 (35 handovers)
- **Mixed**: 0136-0140 (backend CLI, frontend CCW)

---

## WORKFLOW EXAMPLES

### Example 1: Week 1 (Projectplan_500)

**Monday-Wednesday (CLI)**: Service Layer Implementation
```bash
# Day 1: ProductService Enhancement (0500)
cd /f/GiljoAI_MCP
git checkout -b 0500-product-service-enhancement
# Implement ProductService methods with DB queries
python startup.py --dev  # Test locally
pytest tests/test_product_service.py -v
git add . && git commit -m "feat(0500): Implement ProductService enhancement"
git push origin 0500-product-service-enhancement
# User merges to master

# Day 2-3: ProjectService + OrchestrationService (0501-0502)
# Similar CLI workflow, sequential execution
```

**Thursday (CCW)**: Parallel Endpoint Development (4 branches)
```bash
# CCW Session 1: 0503 (Product Endpoints)
New branch: 0503-product-endpoints
Pulls master (includes 0500-0502 service layer)
Implements: api/endpoints/products.py (vision_upload, activate, deactivate)
Push to GitHub

# CCW Session 2: 0504 (Project Endpoints)
New branch: 0504-project-endpoints
Implements: api/endpoints/projects.py (activate, deactivate, staging, summary)
Push to GitHub

# CCW Session 3: 0505 (Succession Endpoint)
New branch: 0505-orchestrator-succession-endpoint
Implements: api/endpoints/agent_jobs.py (trigger_succession)
Push to GitHub

# CCW Session 4: 0506 (Settings Endpoints)
New branch: 0506-settings-endpoints
Implements: api/endpoints/settings.py (general_settings, product_info)
Push to GitHub
```

**Friday (User + CLI)**: Merge & Integration Testing
```bash
# User manually merges all 4 CCW branches
git merge 0503-product-endpoints
git merge 0504-project-endpoints
git merge 0505-orchestrator-succession-endpoint
git merge 0506-settings-endpoints

# CLI: Run integration tests
cd /f/GiljoAI_MCP
python startup.py --dev
pytest tests/integration/test_endpoints.py -v
# Manual testing via dashboard
# Fix any merge conflicts or bugs locally
```

---

### Example 2: Week 2 (Projectplan_500)

**Monday-Tuesday (CCW)**: Parallel Frontend Development (3 branches)
```bash
# CCW Session 1: 0507 (API Client URL Fixes)
New branch: 0507-api-client-url-fixes
Fix: frontend/src/api.js (correct endpoint paths)
Push to GitHub

# CCW Session 2: 0508 (Vision Upload Error Handling)
New branch: 0508-vision-upload-error-handling
Implement: Error notifications in VisionUploadDialog.vue
Push to GitHub

# CCW Session 3: 0509 (Succession UI Components)
New branch: 0509-succession-ui-components
Create: SuccessionTimeline.vue, LaunchSuccessorDialog.vue
Push to GitHub
```

**Tuesday PM (User + CLI)**: Merge & UI Testing
```bash
# User merges all 3 frontend branches
git merge 0507-api-client-url-fixes
git merge 0508-vision-upload-error-handling
git merge 0509-succession-ui-components

# CLI: Test frontend locally
cd frontend/
npm run dev
# Manual testing: Upload vision doc, trigger succession, view timeline
# Check browser console for errors
```

**Wednesday-Friday (CLI)**: Sequential Integration Testing
```bash
# Day 3-4: Fix Broken Test Suite (0510)
cd /f/GiljoAI_MCP
pytest tests/ -v --tb=short  # Identify failing tests
# Fix DB fixtures, mock issues, assertion errors
pytest tests/ -v --cov=src/giljo_mcp --cov-report=html
# Achieve >80% coverage

# Day 5: E2E Integration Tests (0511)
# Create E2E test scenarios:
# 1. Product creation → Vision upload → Project creation → Orchestrator launch
# 2. Orchestrator succession (manual + auto)
# 3. Agent job lifecycle (pending → active → completed)
pytest tests/integration/test_e2e_workflows.py -v
```

---

### Example 3: Documentation Sprint (CCW Parallel)

**Goal**: Complete 3 documentation handovers in 1 day using CCW parallelization.

```bash
# CCW Session 1: 0512 (CLAUDE.md Update)
New branch: 0512-claude-md-update
Tasks:
- Update CLAUDE.md with 0500-0515 changes
- Remove references to stub endpoints
- Add new service methods to Quick Reference
- Update database schema notes
Push to GitHub (2h)

# CCW Session 2: 0513 (Handover 0132 Documentation)
New branch: 0513-handover-0132-documentation
Tasks:
- Create docs/handovers/0132_remediation_summary.md
- Document 23 fixed issues
- Add before/after examples
- Create upgrade guide
Push to GitHub (2h)

# CCW Session 3: 0514 (Roadmap Rewrites)
New branch: 0514-roadmap-rewrites
Tasks:
- Update REFACTORING_ROADMAP_0131-0200.md
- Rewrite COMPLETE_EXECUTION_PLAN_0083_TO_0200.md
- Update CCW_OR_CLI_EXECUTION_GUIDE.md (this doc)
Push to GitHub (10h, can split across multiple days)

# End of Day: User merges all 3
git merge 0512-claude-md-update
git merge 0513-handover-0132-documentation
git merge 0514-roadmap-rewrites

# CLI: Validate markdown formatting
cd /f/GiljoAI_MCP/docs
# Check links, formatting, consistency
```

**Result**: 3 documentation tasks completed in parallel (~1 day wall-clock) vs. 14h sequential.

---

## BEST PRACTICES

### 1. Maximize CCW Parallelism
**Strategy**: Group independent tasks and launch simultaneously.

**Good Example** (Phase 1 Endpoints):
```
4 CCW sessions running in parallel:
├─> CCW 1: Product endpoints (2h)
├─> CCW 2: Project endpoints (4h)
├─> CCW 3: Succession endpoint (3h)
└─> CCW 4: Settings endpoints (3h)

Wall-clock: 4h (slowest task)
Sequential: 12h total
Speedup: 300%
```

**Bad Example** (Sequential CCW):
```
CCW 1: Product endpoints (2h) → wait for merge
CCW 2: Project endpoints (4h) → wait for merge
CCW 3: Succession endpoint (3h) → wait for merge
CCW 4: Settings endpoints (3h)

Wall-clock: 12h
Sequential: 12h
Speedup: 0% (wasted parallelization opportunity)
```

### 2. Use CLI for Foundation, CCW for Implementation
**Strategy**: CLI builds service layer (DB-dependent), CCW builds on top (pure code).

**Workflow**:
```
Week 1: CLI → Service Layer (0500-0502)
├─> ProductService (DB queries)
├─> ProjectService (DB transactions)
└─> OrchestrationService (context tracking)

Week 2: CCW → Endpoints (0503-0506)
├─> Endpoints call service methods (no DB logic in endpoints)
└─> 4 parallel branches, fast development
```

**Why**: Service layer requires DB testing (CLI), endpoints are pure FastAPI routing (CCW).

### 3. Merge Frequently, Test Locally
**Strategy**: Don't let CCW branches diverge for days, merge daily and test.

**Good Example** (Daily Merge Cycle):
```
Monday AM: CCW creates 3 branches (0507-0509)
Monday PM: User merges all 3 → CLI tests locally → Finds 2 bugs
Tuesday AM: CCW fixes bugs on new branches
Tuesday PM: User merges fixes → CLI validates → All green
```

**Bad Example** (Week-Long Divergence):
```
Monday: CCW creates 3 branches
Tuesday-Friday: CCW continues work (no merge)
Friday PM: User merges → 15 merge conflicts → 20 bugs found
Weekend: User spends 8h fixing conflicts and bugs
```

### 4. Use CLI for Debugging, CCW for Fixes
**Strategy**: CLI diagnoses issues with live system, CCW implements fixes.

**Workflow**:
```
CLI: Discovers WebSocket disconnection issue (0111)
├─> Observes logs: "WebSocket connection closed unexpectedly"
├─> Checks DB: agent_jobs.status stuck in 'active'
└─> Identifies root cause: Missing heartbeat mechanism

CCW: Implements fix on branch
├─> Add heartbeat field to agent_jobs table
├─> Implement heartbeat API endpoint
├─> Update frontend to send heartbeat every 30s
└─> Push to GitHub

User: Merges fix → CLI tests locally → Validates WebSocket stays connected
```

### 5. Test Incrementally, Not in Bulk
**Strategy**: Test each CCW branch individually before merging next.

**Good Example** (Incremental Testing):
```
CCW Branch 1: 0503 → User merges → CLI tests product endpoints → Green
CCW Branch 2: 0504 → User merges → CLI tests project endpoints → Green
CCW Branch 3: 0505 → User merges → CLI tests succession endpoint → Green
CCW Branch 4: 0506 → User merges → CLI tests settings endpoints → Green
```

**Bad Example** (Bulk Testing):
```
CCW Branches 1-4: All developed in parallel
User: Merges all 4 at once
CLI: Tests all endpoints → 10 failures across multiple branches
User: Spends 4h debugging which branch caused which failure
```

**Why**: Incremental testing isolates failures to specific branches, faster debugging.

### 6. Use CCW for Large Refactoring
**Strategy**: Leverage cloud tokens for tedious refactoring tasks.

**Use Cases**:
- Component consolidation (0130c): Merge 5 duplicate AgentCard components into one
- API centralization (0130d): Migrate 30+ components from inline axios to api.js
- Prompt tuning (0131-0135): Update 6 agent templates with new behavioral rules

**Why**: Large refactoring requires many token-intensive operations (find/replace, file moves, import updates). CCW's cloud token budget handles this efficiently.

### 7. Always Test Locally Before Moving On
**Strategy**: Never trust CCW code until tested on local environment.

**Workflow**:
```
CCW: Implements feature
User: Merges to master
CLI: Runs test suite + manual testing
├─> Tests pass → Move to next handover
└─> Tests fail → Create bug fix branch in CCW, repeat
```

**Why**: CCW environment doesn't have access to PostgreSQL, live backend, or real WebSocket connections. Local testing is REQUIRED.

---

## TESTING STRATEGY

### CLI Testing (Required)
**When**: After merging every CCW branch.

**Test Types**:
1. **Unit Tests** (pytest):
   ```bash
   pytest tests/test_product_service.py -v
   pytest tests/test_project_service.py -v
   pytest tests/test_orchestration_service.py -v
   ```

2. **Integration Tests** (pytest with DB fixtures):
   ```bash
   pytest tests/integration/test_endpoints.py -v --db-fixtures
   pytest tests/integration/test_workflows.py -v --db-fixtures
   ```

3. **E2E Tests** (manual + automated):
   ```bash
   python startup.py --dev  # Start backend
   cd frontend/ && npm run dev  # Start frontend
   # Manual testing via dashboard:
   # - Create product → Upload vision → Create project → Launch orchestrator
   # - Trigger succession → View timeline → Validate handover
   # - Test multi-tenant isolation (switch tenants)
   ```

4. **Database Validation** (psql):
   ```bash
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp
   # Verify schema changes applied
   \d mcp_products  # Check config_data column exists
   \d mcp_agent_jobs  # Check context_used column exists
   # Verify data integrity
   SELECT * FROM mcp_products WHERE config_data IS NULL;
   SELECT * FROM mcp_agent_jobs WHERE context_used > context_budget;
   ```

### CCW Testing (Pre-Merge)
**When**: Before pushing to GitHub (limited testing in cloud).

**Test Types**:
1. **Syntax Validation**:
   - Python: `ruff check src/; black --check src/`
   - Vue: `npm run lint`
   - Markdown: Check formatting, links

2. **Type Checking**:
   - Python: `mypy src/giljo_mcp`
   - TypeScript: `npm run type-check`

3. **Basic Logic Tests** (if possible without DB):
   - Test pure functions (no DB dependency)
   - Test Pydantic models (validation logic)
   - Test Vue component rendering (Vitest)

**Limitations**: CCW cannot test:
- Database queries (no PostgreSQL access)
- API endpoints (no live backend)
- WebSocket connections (no real-time server)
- Multi-tenant isolation (requires DB)

### When to Test What

| Test Type | CLI | CCW | Frequency |
|-----------|-----|-----|-----------|
| Unit Tests (pytest) | ✅ | ❌ | After every merge |
| Integration Tests | ✅ | ❌ | After phase completion |
| E2E Tests | ✅ | ❌ | After major milestones |
| Database Validation | ✅ | ❌ | After schema changes |
| Syntax/Linting | ✅ | ✅ | Before every push |
| Type Checking | ✅ | ✅ | Before every push |
| Manual UI Testing | ✅ | ❌ | After frontend changes |
| Performance Testing | ✅ | ❌ | Weekly / before launch |

---

## MERGE STRATEGY

### Git Workflow (User-Driven)

**CCW Development**:
```bash
# CCW Session 1: Automatically creates branch
Branch: 0503-product-endpoints
Base: master (pulls latest)
Changes: Implements product endpoints
Action: Pushes to GitHub

# CCW Session 2: Automatically creates branch
Branch: 0504-project-endpoints
Base: master (pulls latest)
Changes: Implements project endpoints
Action: Pushes to GitHub
```

**User Merge** (Local):
```bash
# User manually merges CCW branches into master
cd /f/GiljoAI_MCP
git checkout master
git pull origin master

# Option 1: Merge with merge commit (preferred for tracking)
git merge --no-ff 0503-product-endpoints -m "feat(0503): Add product endpoints"
git merge --no-ff 0504-project-endpoints -m "feat(0504): Add project endpoints"

# Option 2: Rebase (cleaner history, riskier)
git merge --ff-only 0503-product-endpoints
git merge --ff-only 0504-project-endpoints

# Push merged master
git push origin master

# Delete merged branches (cleanup)
git branch -d 0503-product-endpoints
git branch -d 0504-project-endpoints
git push origin --delete 0503-product-endpoints
git push origin --delete 0504-project-endpoints
```

### Handling Merge Conflicts

**Common Conflicts** (CCW parallel branches):
1. **Same file edits** (e.g., both branches modify `api/app.py`):
   ```bash
   git merge 0503-product-endpoints  # Succeeds
   git merge 0504-project-endpoints  # CONFLICT in api/app.py

   # Resolve manually
   code api/app.py  # VS Code shows conflict markers
   # Keep both changes, remove markers
   git add api/app.py
   git commit -m "Merge 0504: Resolve conflict in api/app.py"
   ```

2. **Import order conflicts** (both branches add imports):
   ```python
   # Branch 1 adds:
   from api.endpoints.products import router as products_router

   # Branch 2 adds:
   from api.endpoints.projects import router as projects_router

   # Merged result (keep both):
   from api.endpoints.products import router as products_router
   from api.endpoints.projects import router as projects_router
   ```

3. **Route registration conflicts** (both branches register routes):
   ```python
   # Branch 1:
   app.include_router(products_router, prefix="/api/products")

   # Branch 2:
   app.include_router(projects_router, prefix="/api/projects")

   # Merged result (keep both):
   app.include_router(products_router, prefix="/api/products")
   app.include_router(projects_router, prefix="/api/projects")
   ```

**Prevention Strategy**:
- Design CCW branches to edit different files (e.g., 0503 → products.py, 0504 → projects.py)
- For shared files (api/app.py), merge sequentially instead of parallel
- Use feature flags to isolate changes

### Testing After Merge

**Required** (CLI):
```bash
# 1. Run test suite
pytest tests/ -v --tb=short

# 2. Start backend and frontend
python startup.py --dev
cd frontend/ && npm run dev

# 3. Manual testing via dashboard
# - Test all features from merged branches
# - Check browser console for errors
# - Verify database changes applied

# 4. Validate no regressions
# - Test existing features still work
# - Check multi-tenant isolation
# - Verify authentication flows
```

---

## COMMON PITFALLS

### Pitfall 1: Running DB Tasks on CCW
**Problem**: CCW has no PostgreSQL access, DB tasks fail silently or create broken code.

**Example**:
```python
# CCW Branch: 0500-product-service-enhancement
# Implements ProductService.update_product() with DB query
def update_product(self, product_id, updates):
    product = db.query(Product).filter_by(id=product_id).first()
    product.config_data = updates.get("config_data")
    db.commit()

# CCW: Code looks correct, pushes to GitHub
# User: Merges to master
# CLI: Tests fail - db object not defined, session errors
```

**Solution**: Always run DB-dependent tasks on CLI, test locally before merge.

### Pitfall 2: Not Testing CCW Branches Before Next Merge
**Problem**: Merging multiple untested branches creates debugging nightmare.

**Example**:
```
Monday: CCW creates 4 branches (0503-0506)
Tuesday: User merges all 4 without testing
Wednesday: CLI tests fail - 10 errors across multiple branches
Wednesday PM: User spends 4h debugging which branch caused which error
```

**Solution**: Merge → Test → Merge → Test (incremental validation).

### Pitfall 3: Letting CCW Branches Diverge Too Long
**Problem**: Long-lived branches accumulate merge conflicts.

**Example**:
```
Week 1: CCW Branch 1 created from master (commit A)
Week 2: Master advances to commit E (10 new commits)
Week 2 Friday: CCW Branch 1 tries to merge → 15 conflicts
```

**Solution**: Merge CCW branches daily or within 2-3 days max.

### Pitfall 4: Not Pulling Latest Master Before CCW Session
**Problem**: CCW creates branch from stale master, misses recent changes.

**Example**:
```
Monday AM: Master includes service layer (0500-0502)
Monday PM: CCW Session starts but pulls old master (before service layer)
Tuesday: CCW implements endpoints calling non-existent service methods
Tuesday PM: User merges → Endpoints fail (service methods missing)
```

**Solution**: Ensure CCW always pulls latest master before creating branch.

### Pitfall 5: Skipping Local Testing After Merge
**Problem**: Broken code reaches master, blocks other work.

**Example**:
```
User: Merges CCW branch → Skips local testing → Pushes to master
Next Developer: Pulls master → pytest fails → Cannot work
Next Developer: Wastes 2h debugging someone else's broken code
```

**Solution**: ALWAYS test locally after merge before pushing to master.

### Pitfall 6: Using CCW for Debugging
**Problem**: CCW has no access to logs, live system, or DB for diagnostics.

**Example**:
```
Issue: WebSocket disconnections in production
User: Asks CCW to debug
CCW: Cannot see logs, cannot inspect DB, cannot test WebSocket
CCW: Guesses at solution, implements fix
User: Merges fix → Issue persists
```

**Solution**: ALWAYS use CLI for debugging (logs, DB queries, live system observation).

### Pitfall 7: Parallelizing Dependent Tasks
**Problem**: CCW branches depend on each other, fail when run in parallel.

**Example**:
```
CCW Branch 1: Implements service layer (ProductService)
CCW Branch 2: Implements endpoints calling ProductService
Both run in parallel → Branch 2 fails (ProductService doesn't exist yet)
```

**Solution**: Identify dependencies, run sequentially (CLI for service layer, then CCW for endpoints).

---

## APPENDIX A: HANDOVER QUICK REFERENCE

### By Tool Type

**CLI-Only Handovers** (23 total):
- Database: 0500, 0501, 0502
- Testing: 0510, 0511, 0130a, 0220-0229
- Debugging: 0111
- Filesystem: 0130b
- MCP Tools: 0083, 0141-0145
- Runtime: 0130e
- Infrastructure: 0200-0209

**CCW-Optimal Handovers** (35 total):
- Endpoints: 0503-0506
- Frontend: 0507-0509, 0114, 0112, 0130c, 0130d, 0515, 0146-0150
- Templates: 0118, 0117, 0131-0135
- Docs: 0512-0514, 0210-0219, 0230-0239
- API: 0095

**Mixed Handovers** (5 total):
- Orchestrator: 0136-0140 (backend CLI, frontend CCW)

### By Parallelization Potential

**High Parallelization** (can run 3-4 simultaneous CCW branches):
- Phase 1 Endpoints: 0503, 0504, 0505, 0506 (4 branches)
- Phase 2 Frontend: 0507, 0508, 0509 (3 branches)
- Phase 4 Docs: 0512, 0513, 0514 (3 branches)
- Prompt Tuning: 0131-0135 (5 branches, can split into 2-3 CCW sessions)
- Launch Docs: 0230-0239 (10 branches, split into 3-4 CCW sessions)

**Medium Parallelization** (can run 2 simultaneous CCW branches):
- Frontend Refactoring: 0130c, 0130d (2 branches)
- Templates: 0117, 0118 (2 branches, but 0118 depends on 0130e)

**No Parallelization** (sequential only):
- All CLI handovers (database, testing, debugging)
- Dependent CCW handovers (0118 requires 0130e)

---

## APPENDIX B: DECISION MATRICES

### Decision Matrix 1: Tool Selection by Task Characteristics

| Characteristic | CLI | CCW |
|---------------|-----|-----|
| Requires database access | ✅ | ❌ |
| Requires live backend | ✅ | ❌ |
| Requires file system ops | ✅ | ❌ |
| Pure code (no dependencies) | ⚠️ Can use, but CCW is faster | ✅ |
| Can parallelize | ❌ | ✅ |
| Requires debugging | ✅ | ❌ |
| Large token budget needed | ⚠️ Limited | ✅ |
| Integration testing | ✅ | ❌ |
| Documentation writing | ⚠️ Can use | ✅ Faster |
| Frontend development | ⚠️ Can use | ✅ Faster |

### Decision Matrix 2: Parallelization Feasibility

| Task Dependency | Parallelization Strategy | Example |
|----------------|--------------------------|---------|
| No dependencies | Full parallelization (3-4 CCW branches) | 0503-0506 endpoints |
| Soft dependencies | Partial parallelization (2 CCW branches) | 0130c-d refactoring |
| Hard dependencies | Sequential only (no parallelization) | 0500 → 0501 → 0502 service layer |
| Mixed dependencies | Staged parallelization (CLI → CCW parallel → CLI) | Phase 0 (CLI) → Phase 1 (CCW 4x) → Phase 3 (CLI) |

### Decision Matrix 3: Risk vs. Parallelization

| Risk Level | Parallelization Approach | Testing Strategy |
|-----------|--------------------------|------------------|
| Low (independent tasks) | Full parallelization (4 CCW branches) | Test all after merge |
| Medium (shared files) | Partial parallelization (2 CCW branches) | Test each before next merge |
| High (schema changes) | Sequential only (CLI) | Test after every change |
| Critical (launch blockers) | Sequential with staged gates (CLI → CCW → CLI) | Comprehensive E2E testing |

---

## REVISION HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-12 | Documentation Manager | Initial creation based on Projectplan_500 and user workflow |

---

**End of CCW vs CLI Execution Guide**
