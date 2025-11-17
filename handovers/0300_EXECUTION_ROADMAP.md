# Handover 0300: Context Management System - Execution Roadmap

**Created**: 2025-11-16
**Status**: Master Planning Document
**Purpose**: Comprehensive execution strategy for 0300 series handovers
**Total Scope**: 10 handovers, 88-128 hours estimated

---

## Executive Summary

The Context Management System (0300 series) implements the complete field priority and token reduction system as specified in the Giljo Vision Book. This roadmap provides dependency analysis, execution phasing, resource allocation, and risk mitigation strategies.

**Critical Path**: 0301 → {0302, 0303, 0306, 0307, 0308, 0311} → 0304 → 0305 → 0309 → 0310

**Timeline**:
- **Optimistic** (maximum parallelization): 9-11 days (+1 day for 0311)
- **Realistic** (balanced execution): 13-16 days (+1 day for 0311)
- **Conservative** (sequential, single-threaded): 20-22 days (+2 days for 0311)

---

## Tool Distribution & Parallelization Strategy

### Phase 1: Critical Fix (Sequential)
- **0301** - CLI (Sequential) - MUST GO FIRST (blocks everything)

### Phase 2: Context Sources (PARALLEL - Can Run Simultaneously)
**CLI Parallel Group (4 handovers)**:
- **0302** - CLI (Parallel) - Tech stack extraction
- **0303** - CLI (Parallel) - Config fields extraction
- **0311** - CLI (Parallel) - 360 Memory + Git integration

**CCW Parallel Group (3 handovers)**:
- **0306** - CCW (Parallel) - Agent templates in context
- **0307** - CCW (Parallel) - Backend default priorities
- **0308** - CCW (Parallel) - Frontend field labels & tooltips

**Execution Strategy**: Run all 7 in parallel (4 CLI branches + 3 CCW branches) after 0301 completes.

**Speedup**: 4-6 days sequential → **1-2 days parallel** (70% time reduction)

### Phase 3: Advanced Features (Sequential)
- **0304** - CLI (Sequential) - Token budget enforcement (requires Phase 2 complete)
- **0305** - CLI (Sequential) - Vision chunking (requires 0304)

### Phase 4: Polish & Testing (Sequential + Mixed)
- **0309** - CLI (Sequential) - Token estimation (requires 0305)
- **0310** - CLI + CCW (Mixed) - Integration tests (CLI) + Documentation (CCW)

### Tool Summary
| Phase | CLI Handovers | CCW Handovers | Parallelization |
|-------|---------------|---------------|-----------------|
| 1 | 0301 | - | Sequential (blocking) |
| 2 | 0302, 0303, 0311 | 0306, 0307, 0308 | **7 parallel** |
| 3 | 0304, 0305 | - | Sequential |
| 4 | 0309, 0310 (tests) | 0310 (docs) | Sequential + Mixed |
| **Total** | **8 CLI** | **3 CCW** | **Max parallel: 7** |

**Key Insight**: Phase 2 provides the biggest parallelization opportunity - run 7 handovers simultaneously to compress 4-6 days of sequential work into 1-2 days.

---

## Dependency Graph (ASCII)

```
                     [0300: Master Plan]
                              |
                              v
                    [0301: Priority Mapping Fix]
                      (CRITICAL - 1-2 days)
                              |
                              | BLOCKS EVERYTHING
                              v
        +---------------------+---------------------+---------------------+---------------------+
        |                     |                     |                     |                     |
        v                     v                     v                     v                     v
[0302: Tech Stack]  [0303: Config Fields]  [0306: Templates]  [0307: Defaults]  [0311: 360 Memory + Git]
   (2 days)              (2 days)              (1-2 days)         (1 day)              (1-2 days)
   PARALLEL              PARALLEL              PARALLEL           PARALLEL             PARALLEL (NEW)
        |                     |                     |                     |                     |
        +---------------------+---------------------+---------------------+---------------------+
                              |
                              v
                    [0308: Field Labels]
                        (1 day)
                        PARALLEL
                              |
        +---------------------+
        |
        v
[0304: Token Budget]
   (2 days)
   REQUIRES: 0302, 0303, 0311
        |
        v
[0305: Vision Chunking]
   (2-3 days)
   REQUIRES: 0304
        |
        v
[0309: Token Estimation]
   (1 day)
   REQUIRES: 0305
        |
        v
[0310: Integration Testing]
   (2 days)
   REQUIRES: ALL ABOVE (including 0311)
   FINAL VALIDATION - ALL 9 CONTEXT SOURCES
```

**Legend**:
- `[ ]` = Handover
- `|`, `v` = Dependency flow
- PARALLEL = Can run simultaneously with siblings
- BLOCKS = Must complete before downstream work
- REQUIRES = Explicit dependencies

---

## Detailed Dependency Analysis

### 0301: Priority Mapping Fix (BLOCKING - P0) - **CLI (Sequential)**

**Status**: CRITICAL BUG FIX
**Dependencies**: None
**Blocks**: ALL other handovers
**Reason**: Fixes fundamental UI/Backend mapping bug (1/2/3 → 10/7/4)

**Why It Blocks Everything**:
- Current state: ALL priorities map to "minimal" (80% reduction)
- Without fix: Field priority tests cannot verify correct behavior
- Impact: Cannot validate any new context extraction features
- Must complete before ANY work on new context sources

**Execution**: MUST GO FIRST (no exceptions)

**Tool Selection: CLI (Sequential)**
- **Why CLI**: Requires database access for migration testing, backend + frontend changes, integration tests with PostgreSQL
- **Why Sequential**: Blocks all other work - cannot parallelize
- **Cannot Use CCW**: Migration script needs live DB access, priority validation requires backend testing

---

### Phase 2: Context Source Implementation (PARALLEL)

These handovers can execute simultaneously by different agents or sequentially by one agent. No inter-dependencies.

#### 0302: Tech Stack Context Extraction - **CLI (Parallel)**
**Dependencies**: 0301 complete
**Blocks**: 0304
**Parallel Safe**: Yes (independent context source)
**Resources**: Backend implementor agent + tester

**Output**: Extracts tech_stack.* from config_data

**Tool Selection: CLI (Parallel with 0303, 0306, 0307, 0308, 0311)**
- **Why CLI**: Requires database access for testing extraction from config_data JSONB field, pytest for TDD workflow
- **Why Parallel**: Independent of other extractors, can run simultaneously with 0303, 0306, 0307, 0308, 0311
- **Cannot Use CCW**: PostgreSQL access required for testing extraction logic

#### 0303: Product Config Fields Extraction - **CLI (Parallel)**
**Dependencies**: 0301 complete
**Blocks**: 0304
**Parallel Safe**: Yes (independent context source)
**Resources**: Backend implementor agent + tester

**Output**: Extracts architecture.*, test_config.*, features.*

**Tool Selection: CLI (Parallel with 0302, 0306, 0307, 0308, 0311)**
- **Why CLI**: Requires database access for testing config_data extraction, pytest with DB fixtures
- **Why Parallel**: Independent extractor, can run simultaneously with other Phase 2 handovers
- **Cannot Use CCW**: PostgreSQL required for integration tests

#### 0306: Agent Templates in Context String - **CCW (Parallel)**
**Dependencies**: 0301 complete
**Blocks**: 0304
**Parallel Safe**: Yes (independent context source)
**Resources**: Backend implementor agent + tester

**Output**: Includes agent templates in context

**Tool Selection: CCW (Parallel with 0302, 0303, 0307, 0308, 0311)**
- **Why CCW**: Pure code - reads template files and injects into context string, no DB operations during extraction
- **Why Parallel**: Independent of other extractors, can run simultaneously
- **Can Use CCW**: Template reading and string formatting work fine without DB access (tests run after merge via CLI)

#### 0307: Backend Default Field Priorities - **CCW (Parallel)**
**Dependencies**: 0301 complete
**Blocks**: None (config-only change)
**Parallel Safe**: Yes (no code dependencies)
**Resources**: Backend config specialist

**Output**: Aligned default priorities in config/defaults.py

**Tool Selection: CCW (Parallel with 0302, 0303, 0306, 0308, 0311)**
- **Why CCW**: Pure code - updates Python dictionary in defaults.py, no DB operations
- **Why Parallel**: Config-only change, completely independent of other handovers
- **Can Use CCW**: Simple code edit, tests run after merge via CLI

#### 0308: Frontend Field Labels & Tooltips - **CCW (Parallel)**
**Dependencies**: 0301 complete
**Blocks**: None (UI-only change)
**Parallel Safe**: Yes (frontend-only work)
**Resources**: Frontend developer

**Output**: User-facing field descriptions and help text

**Tool Selection: CCW (Parallel with 0302, 0303, 0306, 0307, 0311)**
- **Why CCW**: Pure frontend code - Vue components, tooltips, labels, no backend/DB needed
- **Why Parallel**: UI-only changes, completely independent of backend extractors
- **Can Use CCW**: Frontend development works perfectly in CCW (test UI after merge via CLI)

#### 0311: 360 Memory + Git Integration (NEW - Added 2025-11-16) - **CLI (Parallel)**
**Dependencies**: 0301 complete (for correct priority mapping), 0135-0139 complete (360 Memory backend), 013B complete (Git refactor)
**Blocks**: 0304 (token budget needs to account for 360 Memory), 0310 (final testing needs all 9 context sources)
**Parallel Safe**: Yes (independent context source)
**Resources**: Backend implementor agent + tester

**Output**: 9th context source operational - learnings history + git instructions integrated into mission_planner.py

**Background**: Handovers 0135-0139 implemented 360 Memory backend (product_memory.learnings array), and handover 013B refactored Git integration (simplified toggle). This handover completes the integration by adding extraction logic to mission_planner.py.

**Key Methods**:
- `_extract_product_learnings()` - Priority-based extraction (full/moderate/abbreviated/minimal)
- `_inject_git_instructions()` - Toggle-based git command injection
- Integration into `_build_context_with_priorities()` at line 850+

**Tool Selection: CLI (Parallel with 0302, 0303, 0306, 0307, 0308)**
- **Why CLI**: Requires database access for testing product_memory.learnings extraction, pytest with DB fixtures for TDD workflow
- **Why Parallel**: Independent context source, can run simultaneously with other Phase 2 extractors
- **Cannot Use CCW**: PostgreSQL access required to test learnings array extraction and git_integration toggle

---

### Phase 3: Advanced Features (SEQUENTIAL)

These MUST run sequentially due to data dependencies.

#### 0304: Token Budget Enforcement - **CLI (Sequential)**
**Dependencies**: 0302, 0303, 0311 complete (needs all context sources to test budget)
**Blocks**: 0305
**Parallel Safe**: No (requires complete context sources)
**Reason**: Budget enforcement logic needs to test against REAL context from all sources

**Critical Path**: YES (longest dependency chain)

**Tool Selection: CLI (Sequential after Phase 2)**
- **Why CLI**: Requires database access to test budget enforcement with real context from all 9 sources, pytest integration tests
- **Why Sequential**: Must wait for 0302, 0303, 0311 to complete (needs full context to test truncation logic)
- **Cannot Use CCW**: Needs live DB to generate real context with all extractors for budget testing

#### 0305: Vision Document Chunking Integration - **CLI (Sequential)**
**Dependencies**: 0304 complete (needs budget enforcement for chunk selection)
**Blocks**: 0309
**Parallel Safe**: No (requires budget logic)
**Reason**: Chunk selection respects token budget limits

**Critical Path**: YES

**Tool Selection: CLI (Sequential after 0304)**
- **Why CLI**: Requires database access for PostgreSQL full-text search (GIN indexes), VisionDocumentChunker integration testing
- **Why Sequential**: Must wait for 0304 (chunk selection respects token budget limits)
- **Cannot Use CCW**: PostgreSQL GIN-indexed full-text search required for sub-100ms chunk retrieval

---

### Phase 4: Polish & Validation (SEQUENTIAL)

#### 0309: Token Estimation Improvements - **CLI (Sequential)**
**Dependencies**: 0305 complete (needs chunking for accurate estimation)
**Blocks**: 0310
**Parallel Safe**: No (requires complete system)
**Output**: Improved token counting accuracy

**Tool Selection: CLI (Sequential after 0305)**
- **Why CLI**: Requires database access to test token estimation with real context (all 9 sources + chunking)
- **Why Sequential**: Must wait for 0305 (needs chunking for accurate estimation)
- **Cannot Use CCW**: Needs live system to validate token counts match actual context generation

#### 0310: Integration Testing & Documentation - **CLI + CCW (Mixed)**
**Dependencies**: ALL previous handovers complete
**Blocks**: None (final validation)
**Parallel Safe**: No (tests entire system)
**Output**: >80% test coverage, production readiness

**Tool Selection: CLI + CCW (Mixed)**
- **CLI Part**: Integration tests, E2E tests, performance benchmarks (requires live backend + DB + frontend)
- **CCW Part**: Documentation updates (CONTEXT_MANAGEMENT_SYSTEM.md, FIELD_PRIORITIES_SYSTEM.md, user guides)
- **Why Mixed**: Tests require CLI (DB + full stack), documentation can be CCW (parallel markdown editing)
- **Execution**: Run CLI tests first, then CCW documentation in parallel with any remaining validation

---

## Execution Phases Summary

### Phase 1: Critical Bug Fix (BLOCKING) - 1-2 days
0301 must complete before ANY other work begins.

### Phase 2: Context Sources (PARALLEL) - 4-6 days  
0302, 0303, 0306, 0307, 0308 can run in parallel after 0301.

### Phase 3: Advanced Features (SEQUENTIAL) - 4-5 days
0304 requires 0302+0303 complete.
0305 requires 0304 complete.

### Phase 4: Polish & Testing (SEQUENTIAL) - 3 days
0309 requires 0305 complete.
0310 requires ALL previous handovers complete.

---

## Timeline Estimates

### Optimistic: 8-10 days
With 5 agents and perfect execution.

### Realistic: 12-15 days  
With 2-3 agents and minor issues.

### Conservative: 18-20 days
Single agent, comprehensive testing.

---

## Success Metrics

### Functional (100% operational)
- Priority mapping: 1 to 10, 2 to 7, 3 to 4
- All 9 context sources implemented
- Token budget enforced (<5% violations)
- Vision chunking active
- Token reduction: 70% average

### Performance (<200ms)
- Individual extractor: <50ms
- Complete context build: <200ms
- Token counting: <20ms for 10K tokens

### Quality (>80%)
- Unit test coverage: >80%
- Integration coverage: >70%
- Zero regressions

### Cost Savings
- Mission size: <2000 tokens
- Savings: >$100/month at scale
- Efficiency: 70% token reduction

---

## Related Documentation

**Foundation**:
- 0300_context_management_system_implementation.md
- 0301_fix_priority_mapping_ui_backend.md

**Architecture**:
- ../docs/SERVICES.md
- ../docs/TESTING.md
- ../docs/ORCHESTRATOR.md

**Handovers**: 0301-0311 (0311 added 2025-11-16 for 360 Memory + Git integration)

---

**Status**: APPROVED - Ready for Execution
**Version**: 1.2 (Added CLI/CCW tool selection + parallelization strategy)
**Updated**: 2025-11-16
**Next Review**: After Phase 1 (0301)

**Changelog**:
- **v1.2 (2025-11-16)**: Added CLI/CCW tool selection monikers to all handovers with parallelization strategy
- **v1.1 (2025-11-16)**: Added handover 0311 for 360 Memory + Git context integration (completes 9th context source from PDF spec)

---

**End of Execution Roadmap**
