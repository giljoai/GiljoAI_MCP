# Master Implementation Plan - VALIDATED

**Document Created**: 2026-01-28
**Validation Date**: 2026-01-28
**Strategy**: Consolidated, code-verified implementation roadmap
**Status**: Active - Corrected based on deep code inspection

---

## Executive Summary

This Master Implementation Plan consolidates and validates work across multiple handover series (0300-0440, 0480, 0700) for GiljoAI MCP v3.2+. It represents the **actual remaining work** after code verification, correcting previous planning documents that incorrectly marked items as complete.

**Scope**:
- Frontend API pattern fixes (REAL bugs discovered)
- Vision consolidation (NOT STARTED - previous claims incorrect)
- Database schema enhancements (organization hierarchy, project taxonomy)
- Code cleanup series (0700-0711 - NOT STARTED)
- WebSocket & message system polish
- MCP tools enhancements

**Total Estimated Effort**: 115-177 hours remaining
**Critical Path**: 0700 series code cleanup (51-71h) → Database schema (32-46h) → Vision consolidation (8-16h)

---

## Validation Results

### Status Verification Table

| Item | Plan Claims | Actual Status | Evidence |
|------|-------------|---------------|----------|
| **Phase 1 Bugs: Steps not working** | In Progress | ✅ **COMPLETE** | Handovers 0386, 0392, 0401 merged; `agentJobsStore.js:293-322` |
| **Phase 1 Bugs: Closeout button** | In Progress | ✅ **COMPLETE** | `ProjectTabs.vue:89-101` - conditional rendering working |
| **Phase 1 Bugs: Message read/ack** | In Progress | ✅ **COMPLETE** | Handovers 0362, 0401, 0407 merged; counter columns live |
| **0480 Exception Handling** | In Progress | ✅ **COMPLETE** | Merged to master (commit 4fa83605) |
| **0362 WebSocket Message Counters** | In Progress | ✅ **COMPLETE** | Counter columns implemented, JSONB deprecated |
| **0371 Dead Code Cleanup** | In Progress | ⚠️ **PARTIAL** | Specific handover complete (~20K lines removed), 0700 series NOT STARTED |
| **360 Memory (0390)** | In Progress | ✅ **COMPLETE** | `ProductMemoryEntry` model + `ProductMemoryRepository` fully implemented |
| **0377 Vision Consolidation** | Columns added | ❌ **FALSE** | Columns DO NOT exist; `consolidate_vision_documents()` NOT created; bug at `get_vision_document.py:112` CONFIRMED |
| **0353 Agent Team Awareness** | In Progress | ⚠️ **PARTIAL** | `_generate_team_context_header()` implemented, tests SKIPPED, template slimming NOT done |
| **0373 Template Adapter** | In Progress | ⚠️ **PARTIAL** | Handover doc exists; `template_adapter.py` (312 lines) still exists; migration NOT executed |
| **0424 Organization Hierarchy** | Planned | ❌ **NOT STARTED** | No models, no services, no APIs - only handover doc exists |
| **0440a Project Taxonomy** | Planned | ❌ **NOT STARTED** | No schema changes - only handover doc exists |
| **0700 Code Cleanup Series** | Planned | ❌ **NOT STARTED** | NO delinting, NO application mapping, NO index created |

### Frontend API Pattern Issues (REAL Bugs) - ✅ FIXED (2026-01-29)

| File | Line | Current (Broken) | Fix Required | Status |
|------|------|------------------|--------------|--------|
| `OrchestratorCard.vue` | 154 | `api.get()` doesn't exist | Add `api.prompts.orchestrator()` method | ✅ FIXED |
| `AgentExecutionModal.vue` | 108 | `api.get()` doesn't exist | Use `api.agentJobs.get(jobId)` | ✅ FIXED |
| `TemplateArchive.vue` | 248 | `api.get()` doesn't exist | Use `api.templates.history(id)` | ✅ FIXED |
| `TemplateArchive.vue` | 312 | `api.post()` doesn't exist | Use `api.templates.restore(id, archiveId)` | ✅ FIXED |

### Technical Debt Inventory

| Category | Count | Location |
|----------|-------|----------|
| DEPRECATED markers | 46 | Throughout codebase |
| TODO markers | 43 | Throughout codebase |
| Skip/xfail test markers | 168 | `tests/` directory |
| Dead adapter code | 312 lines | `src/giljo_mcp/orchestration/template_adapter.py` |

---

## Phase 1: Quick Wins & Bug Fixes

**Estimated Effort**: 4-6 hours
**Priority**: 🔴 HIGH (user-facing issues)
**Dependencies**: None

### 1.1 Frontend API Pattern Fixes (2-3h) - ✅ COMPLETE

**Status**: ✅ **COMPLETE** - All 4 bugs fixed (Handover 0396, 2026-01-29)

#### Tasks:
- [x] Add `api.prompts.orchestrator(tool, projectId)` method
  - File: `frontend/src/services/api.js`
  - Endpoint: `GET /api/v1/prompts/orchestrator/{tool}`
  - Consumer: `OrchestratorCard.vue:154`

- [x] Fix `AgentExecutionModal.vue` to use `api.agentJobs.get(jobId)`
  - File: `frontend/src/components/projects/AgentExecutionModal.vue:108`
  - Also fixed: import statement (named → default export)

- [x] Fix `TemplateArchive.vue` history call
  - File: `frontend/src/components/TemplateArchive.vue:248`
  - Now uses: `api.templates.history(id)`

- [x] Fix `TemplateArchive.vue` restore call
  - File: `frontend/src/components/TemplateArchive.vue:312`
  - Now uses: `api.templates.restore(id, archiveId, reason)`
  - Also updated api.js to accept optional `reason` parameter

#### Testing:
- [x] Frontend build passes without errors
- [x] Grep verification: no `api.get()` or `api.post()` calls remain in components
- [ ] E2E smoke test of orchestrator card, agent modal, template archive (manual)

### 1.2 0353 Agent Team Awareness Completion (1-2h)

**Status**: ⚠️ **PARTIAL** - Core feature done, tests skipped, template slimming undecided

#### Tasks:
- [x] `_generate_team_context_header()` implemented ✅
- [x] Integrated into `get_agent_mission()` ✅
- [ ] **DECISION REQUIRED**: Slim agent templates by removing team awareness section?
  - If YES: Update 12 agent templates in `.claude/agents/`
  - If NO: Mark handover as complete
- [ ] Fix skipped tests in `tests/tools/test_agent_mission.py`
  - Requires dual-model fixtures (mock LLM + real database)
  - Alternative: Mark as integration tests requiring LLM access

### 1.3 Bug Verification (0h)

**Status**: ✅ **COMPLETE** - No work needed

| Bug | Status | Evidence |
|-----|--------|----------|
| Steps not working | ✅ FIXED | Handovers 0386, 0392, 0401 merged |
| Closeout button | ✅ WORKING | `ProjectTabs.vue:89-101` |
| Message read/ack | ✅ FIXED | Counter columns live, 0362/0401/0407 merged |

---

## Phase 2: Vision & Context Consolidation

**Estimated Effort**: 8-16 hours
**Priority**: 🔴 HIGH (fixes confirmed bug at `get_vision_document.py:112`)
**Dependencies**: None

### 2.1 0377 Vision Consolidation - START FROM SCRATCH (8-16h)

**Status**: ❌ **NOT STARTED** - Previous plan incorrectly claimed columns were added

#### CONFIRMED ISSUES:
1. ❌ Columns DO NOT exist on `Product` table (`consolidated_vision_text`, `consolidated_vision_tokens`, etc.)
2. ❌ `consolidate_vision_documents()` function NOT created
3. ❌ Bug at `get_vision_document.py:112` CONFIRMED (tries to access non-existent columns)

#### Tasks:
- [ ] Create migration `versions/0377_vision_consolidation.py`
  ```sql
  ALTER TABLE products ADD COLUMN consolidated_vision_text TEXT;
  ALTER TABLE products ADD COLUMN consolidated_vision_tokens INTEGER;
  ALTER TABLE products ADD COLUMN consolidated_vision_updated_at TIMESTAMP;
  ALTER TABLE products ADD COLUMN consolidation_method VARCHAR(50);
  ```

- [ ] Implement `consolidate_vision_documents()` in `src/giljo_mcp/services/product_service.py`
  - Method: Concatenate all vision documents with chunking support
  - Token counting via `tiktoken`
  - Store result in new columns
  - Update `consolidated_vision_updated_at` timestamp

- [ ] Fix `get_vision_document.py:112` to use new columns
  - Current: Tries to access non-existent `Product.consolidated_vision`
  - Fix: Check `consolidated_vision_text` column, fallback to individual docs

- [ ] Add API endpoint `POST /api/products/{product_id}/consolidate-vision`
  - Calls `consolidate_vision_documents()`
  - Returns token count and status
  - Emits WebSocket event `product_vision_consolidated`

- [ ] Frontend integration
  - Add "Consolidate Vision" button to Product settings
  - Show consolidation status (timestamp, token count)
  - Display warning if vision docs modified after consolidation

#### Testing:
- [ ] Unit tests for `consolidate_vision_documents()`
- [ ] Integration test: Upload 3 vision docs → Consolidate → Verify columns
- [ ] Bug regression test: `get_vision_document.py:112` works with consolidated vision
- [ ] Performance test: Consolidate 50KB vision text in <2 seconds

---

## Phase 3: Database Schema Enhancements

**Estimated Effort**: 32-46 hours
**Priority**: 🟡 MEDIUM (foundational for multi-tenant scalability)
**Dependencies**: Phase 1 complete (avoid merge conflicts)

### 3.1 0424 Organization Hierarchy (24-34h)

**Status**: ❌ **NOT STARTED** - Only handover doc exists, no code

#### Tasks:
- [ ] Create models (`src/giljo_mcp/models.py`)
  ```python
  class Organization(Base):
      organization_id = Column(UUID)
      name = Column(String)
      billing_plan = Column(String)  # free, team, enterprise
      max_seats = Column(Integer)
      created_at = Column(DateTime)

  class OrganizationMember(Base):
      organization_id = Column(UUID, ForeignKey)
      user_id = Column(UUID, ForeignKey)
      role = Column(String)  # owner, admin, member
      joined_at = Column(DateTime)
  ```

- [ ] Create migration `versions/0424_organization_hierarchy.py`
  - Add `organizations` table
  - Add `organization_members` table
  - Add `organization_id` FK to `users` table
  - Migrate existing users to single-user organizations

- [ ] Implement `OrganizationService` (`src/giljo_mcp/services/organization_service.py`)
  - CRUD operations for organizations
  - Member management (add, remove, update role)
  - Billing plan enforcement
  - Seat limit checks

- [ ] Add API endpoints (`api/endpoints/organizations.py`)
  - `GET /api/organizations` - List user's orgs
  - `POST /api/organizations` - Create org
  - `GET /api/organizations/{org_id}/members` - List members
  - `POST /api/organizations/{org_id}/members` - Invite member
  - `DELETE /api/organizations/{org_id}/members/{user_id}` - Remove member

- [ ] Update authentication middleware
  - Add `organization_id` to JWT claims
  - Enforce organization-level permissions
  - Update `tenant_key` generation to include `organization_id`

- [ ] Frontend components
  - Organization settings page
  - Member management UI
  - Organization switcher in navigation
  - Billing plan display

#### Testing:
- [ ] Unit tests for `OrganizationService` (10 tests)
- [ ] Integration tests for org creation, member management (5 tests)
- [ ] E2E test: Create org → Invite member → Switch org → Verify isolation
- [ ] Migration test: Verify existing users migrated to single-user orgs

### 3.2 0440a Project Taxonomy (8-12h)

**Status**: ❌ **NOT STARTED** - Only handover doc exists, no schema changes

#### Tasks:
- [ ] Create migration `versions/0440a_project_taxonomy.py`
  ```sql
  ALTER TABLE projects ADD COLUMN project_type VARCHAR(50);
  ALTER TABLE projects ADD COLUMN tags JSONB DEFAULT '[]';
  ALTER TABLE projects ADD COLUMN priority VARCHAR(20);
  CREATE INDEX idx_projects_type ON projects(project_type);
  CREATE INDEX idx_projects_priority ON projects(priority);
  ```

- [ ] Update `Project` model with new fields
  - `project_type`: 'feature', 'bug', 'refactor', 'research', 'infrastructure'
  - `tags`: Array of strings (e.g., ['frontend', 'urgent', 'customer-request'])
  - `priority`: 'low', 'medium', 'high', 'critical'

- [ ] Add filtering to `ProjectService.get_projects()`
  - Filter by type, tags, priority
  - Sort by priority, created_at, updated_at

- [ ] Update API endpoints
  - `GET /api/projects?type=feature&priority=high&tags=frontend`
  - `PATCH /api/projects/{project_id}` - Update type/tags/priority

- [ ] Frontend enhancements
  - Project type selector in creation dialog
  - Tag input component (multi-select)
  - Priority badge in project cards
  - Filter UI in projects list

#### Testing:
- [ ] Unit tests for filtering logic (6 tests)
- [ ] Integration test: Create project with type/tags → Filter → Verify results
- [ ] Migration test: Verify indexes created, existing projects have NULL values

---

## Phase 4: Code Cleanup (0700 Series)

**Estimated Effort**: 51-71 hours
**Priority**: 🔴 CRITICAL (technical debt reduction, maintainability)
**Dependencies**: None (can run in parallel with other phases)

### 4.1 0700 Series Status - NOT STARTED

| ID | Title | Effort | Status | Priority |
|----|-------|--------|--------|----------|
| **0700** | Cleanup Index Creation | 2-3h | ❌ NOT STARTED | 🔴 HIGH (infrastructure) |
| **0701** | Dependency Visualization | 3-5h | ❌ NOT STARTED | 🟡 MEDIUM |
| **0702** | Utils & Config Cleanup | 4-6h | ❌ NOT STARTED | 🟡 MEDIUM |
| **0703** | Auth & Logging Cleanup | 4-6h | ❌ NOT STARTED | 🟡 MEDIUM |
| **0704** | Models Base Cleanup | 6-8h | ❌ NOT STARTED | 🔴 HIGH |
| **0705** | Models Core Cleanup | 6-8h | ❌ NOT STARTED | 🔴 HIGH |
| **0706** | Models Agents Cleanup | 8-12h | ❌ NOT STARTED | 🔴 CRITICAL |
| **0707** | Services Leaf Cleanup | 4-6h | ❌ NOT STARTED | 🟡 MEDIUM |
| **0708** | Services Core Cleanup | 6-8h | ❌ NOT STARTED | 🔴 HIGH |
| **0711** | API MCP Cleanup | 8-10h | ❌ NOT STARTED | 🔴 CRITICAL |

**Total 0700 Series**: 51-71 hours

### 4.2 0700 Infrastructure - Index Creation (2-3h)

**Purpose**: Create automated tracking system for code cleanup work

#### Tasks:
- [ ] Create `scripts/code_cleanup/generate_index.py`
  - Scan codebase for DEPRECATED markers (46 found)
  - Scan codebase for TODO markers (43 found)
  - Scan tests for skip/xfail markers (168 found)
  - Generate markdown index with file locations, line numbers

- [ ] Create `docs/CODE_CLEANUP_INDEX.md`
  - Table of DEPRECATED items with removal targets
  - Table of TODO items with priority
  - Table of skipped tests with reasons
  - Link to individual handover docs

- [ ] Add pre-commit hook to update index
  - Run `generate_index.py` on commit
  - Fail if new DEPRECATED markers added without handover reference

#### Output Example:
```markdown
## DEPRECATED Markers (46 total)

| File | Line | Item | Removal Target | Handover |
|------|------|------|----------------|----------|
| `src/giljo_mcp/orchestration/template_adapter.py` | 15 | `OrchestratorPromptGenerator` | v4.0 | 0088 |
| `src/giljo_mcp/models.py` | 234 | `Product.product_memory.sequential_history` | v4.0 | 0390 |
```

### 4.3 0706 Models Agents Cleanup (8-12h) - CRITICAL PATH

**Priority**: 🔴 CRITICAL (affects all agent operations)

#### Tasks:
- [ ] Remove `AgentExecution.messages` JSONB column (DEPRECATED 0387i)
  - Migration: Drop column
  - Update all queries to use counter columns
  - Remove serialization logic

- [ ] Clean up `AgentJob` model
  - Remove unused fields
  - Add proper indexes
  - Update docstrings

- [ ] Consolidate agent-related enums
  - `AgentStatus`, `JobStatus`, `MessageType` → single location
  - Remove duplicates

- [ ] Update repository patterns
  - Ensure all agent queries use proper filters
  - Add missing tenant_key checks

#### Testing:
- [ ] Migration test: Drop messages column, verify counters work
- [ ] Integration test: Create job → Send message → Verify counters increment
- [ ] Performance test: Query 1000 agents in <100ms

### 4.4 0711 API MCP Cleanup (8-10h) - CRITICAL PATH

**Priority**: 🔴 CRITICAL (affects all MCP tool calls)

#### Tasks:
- [ ] Consolidate MCP tool registration
  - Single registration point in `src/giljo_mcp/tools/__init__.py`
  - Remove duplicate registrations
  - Add validation for missing tenant_key parameters

- [ ] Standardize MCP response formats
  - All tools return `{"success": bool, "data": any, "error": str?}`
  - Remove ad-hoc response formats

- [ ] Add MCP tool deprecation warnings
  - Mark deprecated tools in registration
  - Log warnings when called
  - Update client SDKs

- [ ] Clean up tool documentation
  - Auto-generate tool docs from docstrings
  - Add usage examples for all tools
  - Update `docs/MCP_TOOLS_MANUAL.md`

#### Testing:
- [ ] Unit test: Verify all tools registered
- [ ] Integration test: Call each tool via HTTP, verify response format
- [ ] E2E test: Orchestrator workflow using cleaned tools

### 4.5 0373 Template Adapter Removal (2-4h)

**Status**: ⚠️ **PARTIAL** - Handover doc exists, migration not executed

#### Tasks:
- [ ] Delete `src/giljo_mcp/orchestration/template_adapter.py` (312 lines)
- [ ] Update all imports to use `ThinClientPromptGenerator`
  - Search for `OrchestratorPromptGenerator` imports
  - Replace with `ThinClientPromptGenerator`
  - Update 4 files found in codebase

- [ ] Remove from `src/giljo_mcp/orchestration/__init__.py`
- [ ] Update tests to remove adapter references
- [ ] Add deprecation notice to CHANGELOG.md

#### Testing:
- [ ] Verify no imports of `OrchestratorPromptGenerator` remain
- [ ] Run full test suite to catch broken imports
- [ ] E2E test: Generate orchestrator prompt using thin client

---

## Phase 5: WebSocket & Message System Polish

**Estimated Effort**: 8-16 hours
**Priority**: 🟡 MEDIUM (system already functional, this is polish)
**Dependencies**: Phase 4.3 (0706 Models Agents Cleanup)

### 5.1 0362 Verification (1-2h)

**Status**: ✅ **COMPLETE** - Verify integration only

#### Tasks:
- [x] Counter columns implemented ✅
- [x] JSONB column deprecated ✅
- [ ] **VERIFICATION ONLY**: Run integration test suite
- [ ] **VERIFICATION ONLY**: Check WebSocket events emit correctly
- [ ] Update documentation to mark JSONB as deprecated in v4.0

### 5.2 Message System Harmony Review (4-8h)

**Purpose**: Ensure message system consistency after counter column migration

#### Tasks:
- [ ] Audit all message-related endpoints
  - `POST /api/messages` - send message
  - `GET /api/messages` - list messages
  - `PATCH /api/messages/{id}/acknowledge` - acknowledge message
  - Verify all use counter columns, none touch JSONB

- [ ] Update frontend message components
  - `MessageCenter.vue` - verify counter display
  - `MessageBadge.vue` - verify real-time updates
  - Remove any references to JSONB message arrays

- [ ] WebSocket event consistency
  - `message_sent` → increments `messages_sent_count`
  - `message_received` → increments `messages_waiting_count`
  - `message_acknowledged` → decrements `messages_waiting_count`, increments `messages_read_count`
  - Add event payload validation

- [ ] Documentation update
  - `docs/MESSAGE_SYSTEM.md` - reflect counter-based architecture
  - Add migration guide for client applications
  - Document WebSocket event payloads

#### Testing:
- [ ] Integration test: Send 10 messages → Verify counters match
- [ ] WebSocket test: Subscribe to events → Verify payloads
- [ ] Performance test: 100 concurrent messages → No counter drift

### 5.3 0365 Orchestrator Handover Behavior (3-6h)

**Purpose**: Refine manual handover workflow for orchestrators

#### Tasks:
- [ ] Review `create_successor_orchestrator()` MCP tool
  - Verify handover summary generation (<10K tokens)
  - Check lineage tracking (spawned_by chain)
  - Ensure context_used reset for successor

- [ ] Test `/gil_handover` slash command
  - Verify it calls `create_successor_orchestrator()`
  - Check UI "Hand Over" button triggers same flow
  - Validate handover summary quality

- [ ] Frontend handover UI
  - Display handover summary to user
  - Show lineage chain (Orchestrator #1 → #2 → #3)
  - Add confirmation dialog before handover

- [ ] Documentation
  - `docs/ORCHESTRATOR.md` - Add handover workflow section
  - Add screenshots of handover UI
  - Document when to trigger manual handover

#### Testing:
- [ ] Integration test: Orchestrator reaches 80% context → Handover → Verify successor created
- [ ] E2E test: Use UI "Hand Over" button → Verify new orchestrator receives condensed mission
- [ ] Verify lineage chain preserved across 3 handovers

---

## Phase 6: MCP Tools Enhancements

**Estimated Effort**: 20-40 hours
**Priority**: 🟢 LOW (enhancements, not fixes)
**Dependencies**: Phase 4 (code cleanup) recommended first

### 6.1 MCP Tool Documentation Generation (8-12h)

#### Tasks:
- [ ] Create `scripts/generate_mcp_docs.py`
  - Parse all MCP tools from `src/giljo_mcp/tools/`
  - Extract docstrings, parameters, return types
  - Generate markdown documentation

- [ ] Auto-update `docs/MCP_TOOLS_MANUAL.md`
  - Run script on pre-commit hook
  - Include usage examples from docstrings
  - Add "last updated" timestamp

- [ ] Add parameter validation
  - Pydantic schemas for all MCP tools
  - Automatic validation before execution
  - Clear error messages for invalid parameters

### 6.2 MCP Tool Deprecation System (6-10h)

#### Tasks:
- [ ] Add `@deprecated` decorator for MCP tools
  - Logs warning when called
  - Returns deprecation notice in response
  - Tracks usage statistics

- [ ] Create deprecation registry
  - `docs/MCP_DEPRECATIONS.md` - list deprecated tools
  - Removal timeline (e.g., v4.0, v5.0)
  - Migration guides for each tool

- [ ] Update client SDKs
  - Add deprecation warnings
  - Suggest alternative tools
  - Auto-migrate where possible

### 6.3 MCP Tool Performance Monitoring (6-8h)

#### Tasks:
- [ ] Add timing decorators to all MCP tools
  - Measure execution time
  - Log slow tools (>1 second)
  - Track call frequency

- [ ] Create performance dashboard
  - Frontend: `Settings → MCP Tools → Performance`
  - Show slowest tools, call counts, error rates
  - Add alerting for tools exceeding thresholds

- [ ] Optimize slow tools
  - Identify top 5 slowest tools
  - Add caching where appropriate
  - Optimize database queries

---

## Recommended Execution Order

### Sprint 1: Foundation (Week 1) - 14-24h
1. ✅ **Phase 1.3**: Bug Verification (0h) - Already complete
2. ✅ **Phase 1.1**: Frontend API Pattern Fixes (~0.5h) - COMPLETE (Handover 0396, 2026-01-29)
3. 🔧 **Phase 1.2**: 0353 Completion (1-2h) - Finish partial work
4. 🔴 **Phase 2.1**: 0377 Vision Consolidation (8-16h) - Fix confirmed bug
5. 🔴 **Phase 4.1**: 0700 Infrastructure (2-3h) - Enable tracking for cleanup

### Sprint 2: Code Cleanup (Week 2-3) - 51-71h
6. 🔴 **Phase 4.3**: 0706 Models Agents Cleanup (8-12h) - Critical path
7. 🔴 **Phase 4.4**: 0711 API MCP Cleanup (8-10h) - Critical path
8. 🔴 **Phase 4.2**: 0704 Models Base Cleanup (6-8h)
9. 🔴 **Phase 4.2**: 0705 Models Core Cleanup (6-8h)
10. 🔴 **Phase 4.2**: 0708 Services Core Cleanup (6-8h)
11. 🟡 **Phase 4.2**: 0701-0703, 0707 (15-23h) - Remaining cleanup items
12. ⚠️ **Phase 4.5**: 0373 Template Adapter Removal (2-4h)

### Sprint 3: Schema Enhancements (Week 4-5) - 32-46h
13. 🟡 **Phase 3.1**: 0424 Organization Hierarchy (24-34h) - Foundational
14. 🟡 **Phase 3.2**: 0440a Project Taxonomy (8-12h)

### Sprint 4: Polish & Enhancements (Week 6) - 28-56h
15. 🟡 **Phase 5.1**: 0362 Verification (1-2h)
16. 🟡 **Phase 5.2**: Message System Harmony (4-8h)
17. 🟡 **Phase 5.3**: 0365 Orchestrator Handover (3-6h)
18. 🟢 **Phase 6**: MCP Tools Enhancements (20-40h) - Optional

**Total**: 115-177 hours (14-22 working days at 8h/day)

---

## Dependencies Map

```
┌─────────────────────────────────────────────────────────────┐
│                         SPRINT 1                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │   Phase 1.1  │   │  Phase 1.2   │   │  Phase 2.1   │   │
│  │  API Fixes   │   │  0353 Done   │   │  Vision 0377 │   │
│  │   (2-3h)     │   │   (1-2h)     │   │   (8-16h)    │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│         │                                      │            │
│         └──────────────┬───────────────────────┘            │
│                        ▼                                     │
│                ┌──────────────┐                             │
│                │  Phase 4.1   │                             │
│                │  0700 Index  │                             │
│                │   (2-3h)     │                             │
│                └──────────────┘                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      SPRINT 2 (CRITICAL)                    │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │  Phase 4.3   │──▶│  Phase 4.4   │──▶│  Phase 4.2   │   │
│  │  0706 Models │   │  0711 MCP    │   │  0704-0708   │   │
│  │  (8-12h)     │   │  (8-10h)     │   │  (33-47h)    │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│         │                                      │            │
│         └──────────────┬───────────────────────┘            │
│                        ▼                                     │
│                ┌──────────────┐                             │
│                │  Phase 4.5   │                             │
│                │  0373 Remove │                             │
│                │   (2-4h)     │                             │
│                └──────────────┘                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                         SPRINT 3                            │
│  ┌──────────────┐                   ┌──────────────┐       │
│  │  Phase 3.1   │                   │  Phase 3.2   │       │
│  │  0424 Org    │──────────────────▶│  0440a Tax   │       │
│  │  (24-34h)    │                   │  (8-12h)     │       │
│  └──────────────┘                   └──────────────┘       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                         SPRINT 4                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │  Phase 5.1   │──▶│  Phase 5.2   │──▶│  Phase 5.3   │   │
│  │  0362 Verify │   │  Msg Harmony │   │  0365 Handover│  │
│  │   (1-2h)     │   │   (4-8h)     │   │   (3-6h)     │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│                                              │              │
│                                              ▼              │
│                                      ┌──────────────┐       │
│                                      │  Phase 6     │       │
│                                      │  MCP Tools   │       │
│                                      │  (20-40h)    │       │
│                                      └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Critical Path**: Phase 1 → Phase 4 (0700 series) → Phase 3 → Phase 5
**Parallel Work**: Phase 6 can run alongside Sprint 3-4

---

## Risk Assessment

### HIGH RISK 🔴

| Risk | Impact | Mitigation |
|------|--------|------------|
| **0377 Vision Consolidation bug** | Orchestrators cannot fetch vision context | Sprint 1 priority; thorough testing of `get_vision_document.py` fix |
| **0706 Models cleanup breaks agent operations** | All agent jobs fail | Comprehensive migration tests; staged rollout; quick rollback plan |
| ~~**Frontend API pattern fixes introduce regressions**~~ | ~~UI components broken~~ | ✅ COMPLETE - Build passes, grep verified, no direct api.get/post calls |
| **0700 series scope creep** | Cleanup takes 2x estimated time | Strict scope definition; time-box each handover; skip low-priority items if needed |

### MEDIUM RISK 🟡

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Organization hierarchy breaks existing multi-tenancy** | Tenant isolation compromised | Migration tests with existing data; manual QA of tenant boundaries |
| **Message counter drift during high concurrency** | Incorrect message counts | Load testing with 100+ concurrent messages; add counter reconciliation job |
| **Template adapter removal breaks legacy integrations** | Old clients fail | Deprecation warnings before removal; maintain adapter for 1 minor version |

### LOW RISK 🟢

| Risk | Impact | Mitigation |
|------|--------|------------|
| **0353 template slimming breaks agent prompts** | Agents missing context | Decision gate: test with 3 agents before mass rollout |
| **Project taxonomy adds minimal value** | Wasted effort | Quick user feedback loop; pivot if not used |
| **MCP tool enhancements low adoption** | Phase 6 effort wasted | Optional phase; skip if other work overruns |

---

## Success Metrics

### Code Quality Metrics
| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| DEPRECATED markers | 46 | 0 | `grep -r "DEPRECATED" src/` |
| TODO markers | 43 | <10 | `grep -r "TODO" src/` |
| Skipped tests | 168 | <20 | `pytest --collect-only -q \| grep skip` |
| Test coverage | ~80% | >85% | `pytest --cov` |
| Dead code (lines) | ~5,000 | <1,000 | `vulture src/` |

### Functional Metrics
| Feature | Success Criteria |
|---------|------------------|
| **Vision Consolidation** | Orchestrators fetch consolidated vision in <500ms; bug at line 112 fixed |
| **Organization Hierarchy** | 3 users can create org, invite members, switch orgs without cross-tenant leaks |
| **Project Taxonomy** | Filter 100 projects by type+tags in <200ms |
| **Frontend API Fixes** | ✅ COMPLETE - All 4 components fixed (2026-01-29) |
| **Message System** | 100 concurrent messages → counters accurate within 1% |

### Performance Metrics
| Operation | Current | Target |
|-----------|---------|--------|
| Orchestrator mission fetch | ~800ms | <500ms |
| Vision consolidation | N/A | <2s for 50KB |
| Project list (filtered) | ~300ms | <200ms |
| MCP tool average latency | ~250ms | <150ms |

### Documentation Metrics
| Deliverable | Status |
|-------------|--------|
| `docs/CODE_CLEANUP_INDEX.md` | ❌ NOT CREATED |
| `docs/MCP_TOOLS_MANUAL.md` (auto-generated) | ❌ MANUAL |
| `docs/MESSAGE_SYSTEM.md` (counter-based) | ⚠️ OUTDATED |
| `docs/ORGANIZATION_HIERARCHY.md` | ❌ NOT CREATED |
| Migration guides for all schema changes | ⚠️ PARTIAL |

---

## Appendix: Item-by-Item Status

### ✅ COMPLETE (No Work Needed)
- Phase 1 Bugs: Steps not working (Handovers 0386, 0392, 0401 merged)
- Phase 1 Bugs: Closeout button (`ProjectTabs.vue:89-101` working)
- Phase 1 Bugs: Message read/ack (Handovers 0362, 0401, 0407 merged)
- 0480 Exception Handling (Merged to master, commit 4fa83605)
- 0362 WebSocket Message Counters (Counter columns implemented)
- 0371 Dead Code Cleanup (Specific handover; ~20K lines removed)
- 360 Memory (0390) (`ProductMemoryEntry` model + repository live)

### ⚠️ PARTIAL (Needs Completion)
- 0353 Agent Team Awareness (Core done; tests skipped; template slimming undecided)
- 0373 Template Adapter (Handover exists; `template_adapter.py` not deleted)

### 🔧 NEEDS WORK (Incorrect Status)
- 0377 Vision Consolidation (Columns DO NOT exist; bug confirmed at `get_vision_document.py:112`)

### ✅ RECENTLY COMPLETED
- Frontend API Pattern Fixes (Handover 0396, 2026-01-29) - All 4 bugs fixed

### ❌ NOT STARTED (Only Handover Docs Exist)
- 0424 Organization Hierarchy (No models, services, APIs)
- 0440a Project Taxonomy (No schema changes)
- 0700 Code Cleanup Series (NO delinting, NO index, NOT STARTED)

### 🟢 OPTIONAL (Low Priority)
- Phase 6: MCP Tools Enhancements (20-40h, nice-to-have)
- 0701 Dependency Visualization (Helpful but not critical)

---

## Maintenance Notes

**Document Owner**: Documentation Manager Agent
**Last Validated**: 2026-01-28 (Deep code inspection)
**Next Review**: After Sprint 1 completion (re-validate status)

**Update Triggers**:
- Any handover marked complete → Update status tables
- New bugs discovered → Add to Phase 1
- Scope changes → Update effort estimates
- Sprint completion → Update dependencies map

**Cross-References**:
- [CLAUDE.md](F:\GiljoAI_MCP\CLAUDE.md) - Primary project guidance
- [docs/HANDOVERS.md](../docs/HANDOVERS.md) - Handover execution workflow
- [docs/SERVICES.md](../docs/SERVICES.md) - Service layer patterns
- [docs/TESTING.md](../docs/TESTING.md) - Testing strategy

---

**END OF DOCUMENT**
