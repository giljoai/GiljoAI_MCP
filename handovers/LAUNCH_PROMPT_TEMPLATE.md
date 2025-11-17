# Production-Grade Handover Launch Prompt Template

**Purpose**: Copy-paste prompt for executing any GiljoAI handover with commercial-grade quality, TDD discipline, and architectural awareness.

**Usage**: Replace `{HANDOVER_NUMBER}` with actual handover (e.g., `0301`, `0311`, etc.)

---

## STANDARD LAUNCH PROMPT (Copy-Paste Ready)

```
Execute handover F:\GiljoAI_MCP\handovers\{HANDOVER_NUMBER}.md with production-grade quality.

CRITICAL REQUIREMENTS:

1. TDD DISCIPLINE (Non-Negotiable):
   - Write tests FIRST (Red phase - tests must fail initially)
   - Implement MINIMAL code to make tests pass (Green phase)
   - Refactor if needed (Refactor phase)
   - Test BEHAVIOR (what code does), not IMPLEMENTATION (how it does it)
   - Use descriptive test names: test_extraction_returns_full_detail_at_priority_10
   - Avoid testing internal implementation details
   - Coverage target: >80% for new code

2. ARCHITECTURAL DISCIPLINE:
   - Read F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md FIRST
   - Build on existing patterns (ProductService, ProjectService, etc.)
   - Do NOT reinvent methods that already exist
   - Use existing service layer patterns (AsyncSession, multi-tenant isolation, Pydantic schemas)
   - Follow established conventions (see 013A section 2.1-2.6 for area-specific patterns)
   - Reuse existing fixtures from tests/conftest.py

3. CODE QUALITY STANDARDS:
   - Production-grade code from the start (no bandaids, no "fix later" comments)
   - Follow existing patterns in F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md
   - Clean code: No zombie code, no commented-out blocks (delete, don't comment)
   - Cross-platform: Use pathlib.Path() for all file operations
   - Multi-tenant isolation: Include tenant_key in all DB queries
   - Error handling: Comprehensive, domain-specific exceptions
   - Logging: Structured metadata (extra={...}) for all significant operations

4. EXECUTION WORKFLOW:
   Phase 1 - Read & Understand (15-20 min):
     - Read complete handover document
     - Read F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md
     - Identify existing patterns to reuse
     - Identify integration points (which services, which endpoints)

   Phase 2 - Write Tests FIRST (Red - 30-40% of time):
     - Create test file: tests/unit/test_{feature_name}.py
     - Write failing unit tests for all new methods
     - Create integration test file: tests/integration/test_{feature_name}_integration.py
     - Write failing integration tests for end-to-end behavior
     - Run tests: pytest tests/ -v (all should fail RED ❌)

   Phase 3 - Implement (Green - 40-50% of time):
     - Write MINIMAL code to make tests pass
     - Follow service layer pattern if backend work
     - Follow component pattern if frontend work
     - Run tests iteratively: pytest tests/ -v (all should pass GREEN ✅)

   Phase 4 - Refactor & Polish (10-20% of time):
     - Extract common patterns into helpers
     - Optimize for performance (minimize DB queries, string operations)
     - Add comprehensive docstrings (Google style)
     - Add structured logging with metadata
     - Run tests: pytest tests/ -v (still GREEN ✅)

   Phase 5 - Validate & Document (10% of time):
     - Run full test suite: pytest tests/ --cov=src/giljo_mcp
     - Verify >80% coverage for new code
     - Update relevant documentation (SERVICES.md, CONTEXT_MANAGEMENT_SYSTEM.md, etc.)
     - Git commit with descriptive message

5. DELIVERABLES:
   - All tests passing (Green ✅)
   - >80% code coverage for new code
   - Clean implementation (no commented code, no TODOs)
   - Documentation updated
   - Git commit ready for review

6. CRITICAL CHECKS (Before Committing):
   ✓ Read 013A_code_review_architecture_status.md? (verify you reused existing patterns)
   ✓ Tests written FIRST? (TDD Red → Green → Refactor)
   ✓ All tests passing? (pytest tests/ -v)
   ✓ Coverage >80%? (pytest --cov)
   ✓ Multi-tenant isolation verified? (tenant_key in all queries)
   ✓ Cross-platform paths? (pathlib.Path, no hardcoded F:\)
   ✓ Production-grade? (no bandaids, no quick fixes)
   ✓ Documentation updated?

SHOW ME:
- Test file(s) created (with descriptive test names)
- Implementation file(s) modified
- Test results (all passing)
- Coverage report (>80% for new code)
- Git commit summary

BEGIN EXECUTION NOW.
```

---

## EXAMPLE: HANDOVER 0311 LAUNCH

**Copy-paste this for Handover 0311 (360 Memory + Git Integration)**:

```
Execute handover F:\GiljoAI_MCP\handovers\0311_integrate_360_memory_context.md with production-grade quality.

CRITICAL REQUIREMENTS:

1. TDD DISCIPLINE (Non-Negotiable):
   - Write tests FIRST (Red phase - tests must fail initially)
   - Implement MINIMAL code to make tests pass (Green phase)
   - Refactor if needed (Refactor phase)
   - Test BEHAVIOR (what code does), not IMPLEMENTATION (how it does it)
   - Use descriptive test names: test_extraction_returns_full_detail_at_priority_10
   - Avoid testing internal implementation details
   - Coverage target: >80% for new code

2. ARCHITECTURAL DISCIPLINE:
   - Read F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md FIRST
   - Build on existing patterns (ProductService, ProjectService, mission_planner.py)
   - Do NOT reinvent methods that already exist
   - Use existing service layer patterns (AsyncSession, multi-tenant isolation, Pydantic schemas)
   - Follow established conventions (see 013A section 2.4 Products for product_memory patterns)
   - Reuse existing fixtures from tests/conftest.py

3. CODE QUALITY STANDARDS:
   - Production-grade code from the start (no bandaids, no "fix later" comments)
   - Follow existing patterns in F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md
   - Clean code: No zombie code, no commented-out blocks (delete, don't comment)
   - Cross-platform: Use pathlib.Path() for all file operations
   - Multi-tenant isolation: Include tenant_key in all DB queries
   - Error handling: Comprehensive, domain-specific exceptions
   - Logging: Structured metadata (extra={...}) for all significant operations

4. EXECUTION WORKFLOW:
   Phase 1 - Read & Understand (15-20 min):
     - Read complete handover 0311 document
     - Read F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md
     - Identify existing patterns: mission_planner.py _get_detail_level(), _count_tokens()
     - Identify integration points: mission_planner.py line 850+ in _build_context_with_priorities()

   Phase 2 - Write Tests FIRST (Red - 30-40% of time):
     - Create test file: tests/unit/test_360_memory_context_extraction.py
     - Write 8+ failing unit tests for _extract_product_learnings() at all priority levels
     - Create integration test file: tests/integration/test_context_with_360_memory.py
     - Write 4+ failing integration tests for full context build with 360 Memory + Git
     - Run tests: pytest tests/unit/test_360_memory_context_extraction.py -v (all should fail RED ❌)

   Phase 3 - Implement (Green - 40-50% of time):
     - Add _extract_product_learnings() method to mission_planner.py (reuse _get_detail_level() pattern)
     - Add _inject_git_instructions() method to mission_planner.py
     - Integrate into _build_context_with_priorities() at line 850+
     - Run tests iteratively: pytest tests/ -v (all should pass GREEN ✅)

   Phase 4 - Refactor & Polish (10-20% of time):
     - Extract common patterns into helpers if needed
     - Optimize token counting (reuse existing _count_tokens() method)
     - Add comprehensive docstrings (Google style, document priority levels)
     - Add structured logging: logger.debug("Added 360 Memory context", extra={"priority": learnings_priority})
     - Run tests: pytest tests/ -v (still GREEN ✅)

   Phase 5 - Validate & Document (10% of time):
     - Run full test suite: pytest tests/ --cov=src/giljo_mcp
     - Verify >80% coverage for new code
     - Update docs/CONTEXT_MANAGEMENT_SYSTEM.md (add 360 Memory section)
     - Update docs/technical/FIELD_PRIORITIES_SYSTEM.md (add product_memory.learnings to table)
     - Git commit with descriptive message

5. DELIVERABLES:
   - All tests passing (Green ✅)
   - >80% code coverage for new code
   - Clean implementation (no commented code, no TODOs)
   - Documentation updated
   - Git commit ready for review

6. CRITICAL CHECKS (Before Committing):
   ✓ Read 013A_code_review_architecture_status.md? (verify you reused _get_detail_level, _count_tokens)
   ✓ Tests written FIRST? (TDD Red → Green → Refactor)
   ✓ All tests passing? (pytest tests/ -v)
   ✓ Coverage >80%? (pytest --cov)
   ✓ Multi-tenant isolation verified? (tenant_key in all queries)
   ✓ Cross-platform paths? (pathlib.Path, no hardcoded F:\)
   ✓ Production-grade? (no bandaids, no quick fixes)
   ✓ Documentation updated? (CONTEXT_MANAGEMENT_SYSTEM.md, FIELD_PRIORITIES_SYSTEM.md)

SHOW ME:
- Test file(s) created (with descriptive test names)
- Implementation file(s) modified
- Test results (all passing)
- Coverage report (>80% for new code)
- Git commit summary

BEGIN EXECUTION NOW.
```

---

## CUSTOMIZATION GUIDE

### For Backend Service Layer Work (e.g., 0500, 0501, 0502):

Replace Section 4 Phase 1 with:
```
Phase 1 - Read & Understand (15-20 min):
  - Read complete handover document
  - Read F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md section 2.4-2.6 (Products, Projects, Jobs)
  - Identify existing service patterns: ProductService, ProjectService
  - Identify AsyncSession injection pattern
  - Identify Pydantic schema patterns from api/schemas/
```

Replace Section 4 Phase 3 with:
```
Phase 3 - Implement (Green - 40-50% of time):
  - Create service class in src/giljo_mcp/services/{service_name}.py
  - Follow AsyncSession injection pattern (see ProductService)
  - Add multi-tenant isolation (tenant_key parameter)
  - Use Pydantic schemas for validation
  - WebSocket events for real-time updates (if applicable)
  - Run tests iteratively: pytest tests/ -v (all should pass GREEN ✅)
```

### For Frontend Components (e.g., 0507, 0508, 0509):

Replace Section 4 Phase 1 with:
```
Phase 1 - Read & Understand (15-20 min):
  - Read complete handover document
  - Read F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md section 2.1-2.2 (User Settings, Admin Settings)
  - Identify existing component patterns in frontend/src/components/
  - Identify Pinia store patterns in frontend/src/stores/
  - Identify API service patterns in frontend/src/services/api.js
```

Replace Section 4 Phase 3 with:
```
Phase 3 - Implement (Green - 40-50% of time):
  - Create Vue component in frontend/src/components/{component_name}.vue
  - Use Composition API (Vue 3 <script setup>)
  - Follow Vuetify 3 patterns (v-card, v-btn, v-text-field, etc.)
  - Integrate with Pinia store if state needed
  - Add API calls via frontend/src/services/api.js
  - Run component tests: npm run test:unit
```

### For API Endpoints (e.g., 0503, 0504, 0505, 0506):

Replace Section 4 Phase 1 with:
```
Phase 1 - Read & Understand (15-20 min):
  - Read complete handover document
  - Read F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md section 2.4-2.6
  - Identify existing endpoint patterns in api/endpoints/
  - Identify service layer methods to call (ProductService, ProjectService, etc.)
  - Identify Pydantic request/response models in api/schemas/
```

Replace Section 4 Phase 3 with:
```
Phase 3 - Implement (Green - 40-50% of time):
  - Create endpoint file in api/endpoints/{endpoint_name}.py
  - Define routes with proper HTTP methods (GET/POST/PUT/DELETE)
  - Use Pydantic models for request/response validation
  - Call service layer methods (don't duplicate business logic)
  - Add proper error handling (HTTPException with status codes)
  - Register routes in api/app.py
  - Run tests iteratively: pytest tests/api/test_{endpoint_name}.py -v
```

---

## QUALITY CHECKLIST (Mandatory Before Completion)

### Code Quality
- [ ] No hardcoded paths (use pathlib.Path)
- [ ] No commented-out code (delete, don't comment)
- [ ] No TODO/FIXME comments (implement now or create ticket)
- [ ] No magic numbers (use constants)
- [ ] No duplicate code (DRY principle)
- [ ] Descriptive variable/method names (no single letters except loop vars)

### Testing
- [ ] Tests written FIRST (TDD Red → Green → Refactor)
- [ ] All tests passing (pytest tests/ -v)
- [ ] Coverage >80% (pytest --cov=src/giljo_mcp)
- [ ] Test names descriptive (test_extraction_returns_full_detail_at_priority_10)
- [ ] Tests focus on BEHAVIOR not IMPLEMENTATION
- [ ] Edge cases covered (empty data, missing fields, invalid inputs)

### Architecture
- [ ] Read 013A_code_review_architecture_status.md
- [ ] Reused existing patterns (no reinvention)
- [ ] Service layer used for backend (if applicable)
- [ ] Multi-tenant isolation verified (tenant_key in queries)
- [ ] Pydantic schemas used for validation
- [ ] WebSocket events emitted (if real-time updates needed)

### Documentation
- [ ] Docstrings added (Google style)
- [ ] CONTEXT_MANAGEMENT_SYSTEM.md updated (if context work)
- [ ] SERVICES.md updated (if new service added)
- [ ] TESTING.md patterns followed
- [ ] API documentation current (if new endpoints)

### Git
- [ ] Descriptive commit message
- [ ] No merge conflicts
- [ ] All files staged (git status clean)

---

## ANTI-PATTERNS TO AVOID

### ❌ DON'T:
- Write implementation before tests (breaks TDD)
- Comment out old code (delete it - git remembers)
- Add "TODO" or "FIXME" comments (implement now or create ticket)
- Hardcode paths like "F:\GiljoAI_MCP\" (use pathlib.Path)
- Skip reading 013A (leads to reinventing existing methods)
- Test implementation details (test public API behavior)
- Mix V0/V1/V2 patterns (follow 013A for current patterns)
- Add dependencies without checking existing ones
- Skip error handling (comprehensive error handling required)
- Skip logging (structured logging with metadata required)

### ✅ DO:
- Write tests FIRST (Red → Green → Refactor)
- Delete dead code completely
- Implement features completely (production-grade from start)
- Use pathlib.Path() for cross-platform compatibility
- Read 013A before coding (understand existing patterns)
- Test behavior (what code does, not how)
- Follow service layer pattern (see ProductService, ProjectService)
- Reuse existing methods (_get_detail_level, _count_tokens, etc.)
- Add comprehensive error handling
- Add structured logging with metadata

---

## SUCCESS CRITERIA

**You know you're done when**:
1. ✅ All tests written FIRST and passing (TDD discipline)
2. ✅ Coverage >80% for new code
3. ✅ 013A patterns followed (no reinvented methods)
4. ✅ Production-grade code (no bandaids)
5. ✅ Clean code (no zombies, no comments, no TODOs)
6. ✅ Documentation updated
7. ✅ Git commit ready for review
8. ✅ No warnings from pytest or ruff

**Final validation command**:
```bash
# All must pass before considering handover complete
pytest tests/ -v --cov=src/giljo_mcp --cov-report=html
ruff check src/ api/
black --check src/ api/
git status  # Should show clean working tree
```

---

## EXAMPLE OUTPUT (What You Should See)

```
✅ Phase 1 Complete: Read handover 0311 + 013A architecture status
   - Identified existing patterns: _get_detail_level(), _count_tokens()
   - Integration point: mission_planner.py line 850+

✅ Phase 2 Complete: Tests written FIRST (Red ❌)
   - Created tests/unit/test_360_memory_context_extraction.py (8 tests)
   - Created tests/integration/test_context_with_360_memory.py (4 tests)
   - All tests failing as expected (Red ❌)

✅ Phase 3 Complete: Implementation (Green ✅)
   - Added _extract_product_learnings() to mission_planner.py
   - Added _inject_git_instructions() to mission_planner.py
   - Integrated into _build_context_with_priorities()
   - All tests passing (Green ✅)

✅ Phase 4 Complete: Refactored & Polished
   - Reused _get_detail_level() pattern (no reinvention)
   - Added docstrings (Google style)
   - Added structured logging
   - All tests still passing (Green ✅)

✅ Phase 5 Complete: Validated & Documented
   - Coverage: 87% for new code (>80% ✅)
   - Updated CONTEXT_MANAGEMENT_SYSTEM.md
   - Updated FIELD_PRIORITIES_SYSTEM.md
   - Git commit ready

Test Results:
============================= 12 passed in 2.34s =============================

Coverage Report:
src/giljo_mcp/mission_planner.py  87%  (lines 850-920 new code)

Git Commit:
feat(0311): Integrate 360 Memory + Git into context system

- Added _extract_product_learnings() with priority-based detail levels
- Added _inject_git_instructions() for Git integration toggle
- Integrated both into _build_context_with_priorities()
- 12 tests passing (8 unit + 4 integration)
- Coverage: 87% for new code

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>

HANDOVER 0311 COMPLETE ✅
```

---

## NOTES

- This template enforces TDD discipline (tests first, always)
- This template enforces architectural awareness (read 013A first)
- This template enforces production-grade quality (no bandaids)
- This template is copy-paste ready (just replace {HANDOVER_NUMBER})
- This template works for CLI or CCW execution (adjust tooling as needed)

**Document Version**: 1.0
**Created**: 2025-11-16
**Purpose**: Standardize handover execution with production-grade quality
