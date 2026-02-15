# Handover Format & Tool Selection Guide

**Version**: v3.1+ (Post-Remediation)
**Last Updated**: 2025-11-15

## Overview

Handovers are the primary unit of work execution in GiljoAI MCP. Each handover is a scoped document describing a specific task, its implementation, and verification criteria. This guide covers handover format, tool selection (CCW vs CLI), and execution best practices.

---

## Handover Format (CRITICAL)

### **Handovers are SCOPED DOCUMENTS, not folders**

✅ **Correct**: `handovers/0060_mcp_agent_coordination_tool_exposure.md` (single file)
❌ **Incorrect**: `handovers/0060/` folder with multiple files

### **Naming Convention**

**Format**: `[SEQUENCE]_[SHORT_DESCRIPTION].md` (all lowercase, underscores)

**Examples**:
- `0050_single_active_product_architecture.md`
- `0051_product_form_autosave_ux.md`
- `0500_product_service_enhancement.md`
- `0512_claude_md_update_cleanup.md`

**Sequence Numbering**:
- `0001-0099`: Initial development
- `0100-0199`: Features and enhancements
- `0200-0299`: Infrastructure and deployment
- `0500-0599`: Remediation and fixes
- `0600-0699`: Audits and validations

**Exception**: Large handovers (rare) may use folder structure:
```
handovers/0052/
├── 0052_main.md
├── architecture.md
├── implementation.md
└── testing.md
```

### **Location**

**Primary**: `F:\GiljoAI_MCP\handovers/`
**Completed**: `F:\GiljoAI_MCP\handovers/completed/`
**Reference**: `F:\GiljoAI_MCP\handovers/completed/reference/`

### **Handover Structure**

Every handover should follow this structure:

```markdown
---
**Handover**: XXXX - [Short Title]
**Type**: [Backend | Frontend | Full-Stack | Documentation | Testing]
**Effort**: [Hours estimate]
**Priority**: [P0 | P1 | P2]
**Status**: [Planning | Active | Complete]
---

# Handover XXXX: [Title]

## Problem Statement
[What problem does this solve?]

## Scope
[What's included and excluded?]

## Tasks
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

## Success Criteria
- ✅ Criterion 1
- ✅ Criterion 2

## Implementation
[Details, code examples, architecture decisions]

## Testing
[How to verify this works]

## Rollback
[How to undo changes if needed]
```

---

## Tool Selection: CCW vs CLI

### **Complete Guide**: `handovers/CCW_OR_CLI_EXECUTION_GUIDE.md`

### **Quick Decision Matrix**

| Task Type | Tool | Why |
|-----------|------|-----|
| Database schema changes | CLI | Requires local database access |
| Service layer development | CLI | Needs database testing |
| API endpoint implementation | CLI | Requires backend server testing |
| Frontend Vue components | CCW | Pure frontend, no backend needed |
| Documentation writing | CCW | No code execution required |
| Integration testing | CLI | Needs full stack running |
| Multiple independent tasks | CCW | Parallelization (multi-branch) |
| MCP tool development | CLI | Requires MCP server testing |
| Template updates | CCW | Pure text changes |
| Vision document updates | CCW | Pure text changes |

### **Use CLI (Local) When:**
- ✅ Database migrations or schema changes
- ✅ Testing with live backend/database
- ✅ Debugging runtime issues
- ✅ File system operations (large file moves, gitignore updates)
- ✅ MCP tool registration and testing
- ✅ Integration testing (multi-service workflows)

### **Use CCW (Cloud) When:**
- ✅ Pure code changes (no DB required)
- ✅ Frontend work (Vue components, Vuetify UI)
- ✅ Template updates (agent prompts, mission templates)
- ✅ Documentation writing (markdown, guides)
- ✅ Multiple independent tasks (parallelization via multi-branch)
- ✅ API endpoint implementation (after service layer complete)

---

## Remediation Project Lessons (0500-0515)

### **Lesson 1: No More Stubs**

**Problem**: Handovers 0120-0130 left 23 HTTP 501 stub endpoints
**Fix**: All endpoints fully implemented in 0500-0515
**Going forward**: NEVER merge stubs - implement endpoints completely

❌ **DON'T** leave stubs:
```python
@router.post("/api/products/vision")
async def upload_vision():
    raise HTTPException(501, "Not Implemented")  # BAD
```

✅ **DO** implement fully:
```python
@router.post("/api/products/vision")
async def upload_vision(
    product_id: int,
    content: str,
    session: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    service = ProductService(session, user.tenant_key)
    return await service.upload_vision_document(product_id, content)
```

### **Lesson 2: Test Immediately**

**Problem**: Test suite broken for weeks, took 2+ days to fix (0510/0511)
**Fix**: Restored >80% coverage, added E2E tests
**Going forward**: Run `pytest` after every handover, CI/CD enforces coverage

**After every handover**:
```bash
# Run tests before marking handover complete
pytest tests/ --cov=src/giljo_mcp --cov-report=term

# If coverage < 80%, add tests before proceeding
pytest tests/ --cov=src/giljo_mcp --cov-report=html
```

### **Lesson 3: Service Layer First**

**Problem**: Endpoints built before service layer, caused circular dependencies
**Fix**: Phase 0A (service layer) completed before Phase 0B (endpoints)
**Going forward**: Always build foundation first (DB → Services → Endpoints → Frontend)

**Correct Order**:
```
1. Database schema (models.py)
   ↓
2. Service layer (services/*.py)
   ↓
3. API endpoints (api/endpoints/*.py)
   ↓
4. Frontend components (frontend/src/components/*.vue)
```

### **Lesson 4: Parallel Execution**

**Problem**: Sequential execution wasted time on independent tasks
**Fix**: CCW parallelization (4 endpoints in 4h wall-clock vs 12h sequential)
**Going forward**: Use CCW for pure code, parallelize when possible

**Parallel Execution Example** (CCW):
```
Branch 1: Implement POST /api/products
Branch 2: Implement GET /api/products
Branch 3: Implement PUT /api/products/{id}
Branch 4: Implement DELETE /api/products/{id}

Wall-clock time: 4 hours (vs 16 hours sequential)
```

---

## Handover Execution Workflow

### **Phase 1: Planning** (15-30 minutes)

1. **Read handover document fully**
2. **Identify dependencies** (blocked by other handovers?)
3. **Choose tool** (CCW vs CLI based on decision matrix)
4. **Create todo list** (use TodoWrite tool)
5. **Estimate effort** (compare to handover estimate)

### **Phase 2: Implementation** (varies)

1. **Sequential tasks** (service → endpoints → frontend):
   ```bash
   # CLI: Sequential with testing
   # Implement service
   # Run: pytest tests/services/test_product_service.py -v
   # Implement endpoint
   # Run: pytest tests/endpoints/test_products_api.py -v
   # Implement frontend
   # Run: npm run dev (manual testing)
   ```

2. **Parallel tasks** (CCW multi-branch):
   ```
   Branch A: Endpoint 1 (2h)
   Branch B: Endpoint 2 (2h)
   Branch C: Endpoint 3 (2h)
   Branch D: Endpoint 4 (2h)
   Total: 2h wall-clock (vs 8h sequential)
   ```

### **Phase 3: Testing** (20-30% of implementation time)

1. **Unit tests** (service layer):
   ```bash
   pytest tests/services/ -v
   ```

2. **Integration tests** (full workflow):
   ```bash
   pytest tests/integration/ -v
   ```

3. **Manual testing** (UI workflows):
   ```bash
   python startup.py --dev
   # Test in browser: http://localhost:7272
   ```

### **Phase 4: Verification** (15-30 minutes)

1. **Check success criteria** (from handover document)
2. **Run full test suite**:
   ```bash
   pytest tests/ --cov=src/giljo_mcp --cov-report=html
   ```
3. **Verify coverage >80%**
4. **Check for regressions** (existing tests still pass)

### **Phase 5: Documentation** (15-30 minutes)

1. **Update CLAUDE.md** (if new patterns introduced)
2. **Update relevant docs/** (if architecture changed)
3. **Create handover completion summary** (in handover doc or separate file)

### **Phase 6: Commit** (5-10 minutes)

1. **Git status check**:
   ```bash
   git status
   git diff
   ```

2. **Commit with descriptive message**:
   ```bash
   git add .
   git commit -m "feat(XXXX): [Short description]

   Complete Handover XXXX: [Title]

   Changes:
   - Change 1
   - Change 2

   Success criteria verified:
   - ✅ Criterion 1
   - ✅ Criterion 2

   Completed: [date]"
   ```

---

## Multi-Handover Execution (Phases)

### **Remediation Example (Handovers 0500-0515)**

**Phase 0A: Service Layer** (Week 1, Days 1-3) - CLI Sequential
- 0500: ProductService Enhancement (4h)
- 0501: ProjectService Implementation (12-16h)
- 0502: OrchestrationService Integration (4-5h)
- **Total**: 20-25h sequential (cannot parallelize - dependencies)

**Phase 0B: API Endpoints** (Week 1, Days 4-5) - CCW Parallel (4 branches)
- 0503: Product Endpoints (2h)
- 0504: Project Endpoints (4h)
- 0505: Orchestrator Succession Endpoint (3h)
- 0506: Settings Endpoints (3-4h)
- **Total**: 12h work, 4h wall-clock (parallelization)

**Phase 0C: Frontend Fixes** (Week 2, Days 1-2) - CCW Parallel (3 branches)
- 0507: API Client URL Fixes (1h)
- 0508: Vision Upload Error Handling (2h)
- 0509: Succession UI Components (4-6h)
- **Total**: 7-9h work, 6h wall-clock

**Phase 0D: Integration Testing** (Week 2, Days 3-5) - CLI Sequential
- 0510: Fix Broken Test Suite (8-12h)
- 0511: E2E Integration Tests (12-16h)
- **Total**: 20-28h sequential (testing requires full stack)

**Phase 0E: Documentation** (Week 3, Days 1-2) - CCW Parallel (3 branches)
- 0512: CLAUDE.md Update & Cleanup (2h)
- 0513: Handover 0132 Documentation (2h)
- 0514: Roadmap Rewrites (10h)
- **Total**: 14h work, 10h wall-clock

---

## Common Handover Patterns

### **Pattern 1: Database → Service → Endpoint → Frontend**

**Example**: Add "favorite projects" feature

```
1. Database (CLI):
   - Add favorite BOOLEAN column to mcp_projects
   - Migration: ALTER TABLE mcp_projects ADD COLUMN favorite BOOLEAN DEFAULT FALSE

2. Service (CLI):
   - ProjectService.toggle_favorite(project_id)
   - Unit tests: test_toggle_favorite()

3. Endpoint (CLI or CCW):
   - POST /api/projects/{id}/favorite
   - API tests: test_favorite_endpoint()

4. Frontend (CCW):
   - Add star icon to project cards
   - Toggle on click
   - WebSocket update for real-time sync
```

### **Pattern 2: Pure Frontend Enhancement**

**Example**: Add dark mode toggle

```
1. Frontend (CCW):
   - Add theme toggle in settings
   - Vuetify theme configuration
   - Persist theme preference (localStorage)
   - CSS variable updates

No backend changes needed → CCW parallel execution
```

### **Pattern 3: Documentation Update**

**Example**: Update architecture diagrams

```
1. Documentation (CCW):
   - Update docs/ARCHITECTURE.md
   - Create new diagrams (mermaid.js or PNG)
   - Update cross-references in CLAUDE.md
   - Verify all links work

No code changes → CCW parallel execution
```

---

## Handover Archive Process

### **When to Archive**

Archive handovers after:
1. ✅ Implementation complete
2. ✅ Tests passing (>80% coverage)
3. ✅ Success criteria verified
4. ✅ Git commit merged
5. ✅ No open issues related to handover

### **Archive Location**

**Completed handovers**: `handovers/completed/XXXX_[title].md`
**Reference handovers**: `handovers/completed/reference/`

### **Archive Format**

Append to completed handover:

```markdown
---

## Completion Summary

**Completed**: 2025-11-15
**Effort**: 4 hours (estimated: 4 hours)
**Commits**: f468cc3, 58479ac
**Coverage**: 85.2% (target: >80%)

### What Was Delivered
- ✅ ProductService vision upload with chunking
- ✅ 25K token per chunk limit enforced
- ✅ Unit tests for chunking logic
- ✅ Integration tests for full upload workflow

### Lessons Learned
- Chunking threshold of 25K chosen to stay under Claude API limit
- JSONB config_data field allows flexible product configuration
- WebSocket events critical for real-time upload progress

### Follow-Up Handovers
- 0503: Product Endpoints (implement API for vision upload)
- 0508: Vision Upload Error Handling (add user-facing errors)
```

---

## Related Documentation

- **Handover Instructions**: [handovers/handover_instructions.md](../handovers/handover_instructions.md)

---

**Last Updated**: 2025-11-15 (Post-Remediation v3.1.1)
