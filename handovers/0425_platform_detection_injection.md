# Handover: Platform Detection Injection

**Date:** 2026-01-19
**From Agent:** Orchestrator (Claude Code CLI session)
**To Agent:** tdd-implementor, ux-designer, system-architect
**Priority:** Medium
**Estimated Complexity:** 4-6 hours total
**Status:** Ready for Implementation
**MCP Enhancement List:** #14 (Platform-Specific Command Guidance)

---

## Task Summary

Implement platform detection to ensure orchestrators and agents write platform-appropriate shell commands in missions.

**Problem**: Orchestrators create missions with Unix commands (e.g., `sleep 5`) when developers work on Windows, forcing agents to mentally translate commands.

**Solution**: Two-part approach:
1. **Target Platform** (static) - Add to Product card as user-configured field
2. **Dev Environment** (dynamic) - Each agent self-detects OS at runtime

---

## Context and Background

### Architecture Constraint
The MCP server is **remote/hosted** (LAN/WAN) - it cannot detect the developer's OS. Multiple developers on different OSes can connect to the same server simultaneously.

```
GiljoAI MCP Server (LAN/WAN/Hosted)
         │
    ┌────┴────┬────────────┐
    │         │            │
Developer PC  Developer PC  Developer PC
(Windows)     (macOS)       (Linux)
```

### Two Distinct Concepts

| Concept | Description | Storage | Example |
|---------|-------------|---------|---------|
| **Target Platform** | What OS the product runs on | Product model (static) | "Building a Windows desktop app" |
| **Dev Environment** | What OS the developer uses | Runtime detection (dynamic) | "I'm coding on macOS" |

These are independent - you might build a cross-platform app (`Target: All`) while developing on Windows.

---

## Technical Details

### Phase 1: Product Card - Target Platform Field

**Model Change** (`src/giljo_mcp/models.py`):
```python
class Product(Base):
    # ... existing fields ...
    target_platforms = Column(ARRAY(String), default=['all'])
    # Valid values: ['windows', 'linux', 'macos', 'all']
```

**Frontend Change** (Product form Tab 3 - Tech Stack):
Add multi-select checkbox group:
```
Target Platform(s):
[ ] Windows  [ ] Linux  [ ] macOS  [x] All (Cross-platform)
```

**Context Inclusion** (`fetch_context(categories=["tech_stack"])`):
```python
"target_platforms": ["windows", "linux"]  # or ["all"]
```

### Phase 2: Agent Self-Detection Protocol

**Orchestrator Protocol** (`get_orchestrator_instructions()` CH2):
Add Step 0 before current Step 1:
```markdown
## STEP 0: DETECT ENVIRONMENT
Before planning, detect your development environment:
```bash
python -c "import platform; print(platform.system())"
```
Store result (Windows/Linux/Darwin) - use platform-appropriate commands in agent missions.
```

**Agent Template** (generic agent protocol Phase 1):
Add to Phase 1 (STARTUP):
```markdown
## ENVIRONMENT DETECTION
Detect your OS before executing tasks:
```bash
python -c "import platform; print(platform.system())"
```
Adapt shell commands accordingly:
- Sleep: Windows `timeout /t N /nobreak` | Unix `sleep N`
- Clear: Windows `cls` | Unix `clear`
```

---

## Implementation Plan

### Phase 1: Backend - Product Model (1-2 hours)
**Recommended Agent:** tdd-implementor

1. Add `target_platforms` field to Product model
2. Add migration (or rely on install.py auto-migration)
3. Update ProductService to handle new field
4. Include in `fetch_context(categories=["tech_stack"])` response
5. Write unit tests

**Files:**
- `src/giljo_mcp/models.py` - Add column
- `src/giljo_mcp/services/product_service.py` - Handle field
- `src/giljo_mcp/tools/context_tools/tech_stack.py` - Include in response
- `tests/services/test_product_service.py` - Add tests

### Phase 2: Frontend - Product Form (1-2 hours)
**Recommended Agent:** ux-designer

1. Add target platform multi-select to Tab 3 (Tech Stack)
2. Wire up to product store
3. Update form submission to include new field
4. Add validation (at least one platform selected)

**Files:**
- `frontend/src/components/products/ProductFormTechStack.vue` - Add UI
- `frontend/src/stores/productStore.js` - Handle field
- `frontend/src/api/products.js` - Include in API calls

### Phase 3: Protocol Injection (1-2 hours)
**Recommended Agent:** system-architect

1. Add Step 0 (DETECT ENVIRONMENT) to orchestrator protocol CH2
2. Add ENVIRONMENT DETECTION to generic agent template Phase 1
3. Update documentation

**Files:**
- `src/giljo_mcp/services/orchestration_service.py` - CH2 update
- `src/giljo_mcp/template_seeder.py` - Agent template update
- `docs/ORCHESTRATOR.md` - Document new step

---

## Testing Requirements

### Unit Tests
- Product model accepts `target_platforms` array
- ProductService validates platform values
- fetch_context includes target_platforms in tech_stack response

### Integration Tests
- Create product with target_platforms via API
- Verify orchestrator receives target_platforms in context
- Verify agent template includes environment detection step

### Manual Testing
1. Create new product, set target platform to "Windows"
2. Launch orchestrator, verify it receives target_platforms
3. Verify orchestrator protocol includes Step 0
4. Spawn agent, verify template includes environment detection

---

## Success Criteria

- [ ] Product model has `target_platforms` field
- [ ] Product form allows platform selection
- [ ] `fetch_context(categories=["tech_stack"])` includes target_platforms
- [ ] Orchestrator protocol CH2 has Step 0: DETECT ENVIRONMENT
- [ ] Agent template Phase 1 has ENVIRONMENT DETECTION
- [ ] All tests pass
- [ ] Documentation updated

---

## Dependencies and Blockers

**Dependencies:** None - independent feature

**Blockers:** None identified

---

## Rollback Plan

1. Remove `target_platforms` column (migration down)
2. Revert frontend form changes
3. Remove protocol injection text

All changes are additive - no breaking changes to existing functionality.

---

## Additional Resources

- MCP Enhancement List #14: `F:\TinyContacts\MCP_ENHANCEMENT_LIST.md`
- Architecture diagram: `handovers/Reference_docs/Workflow PPT to JPG/Slide3.JPG`
- Orchestrator protocol: `docs/ORCHESTRATOR.md`
- Agent templates: `.claude/agents/`

---

## Progress Updates

### 2026-01-19 - Initial Creation
**Status:** Ready for Implementation
**Work Done:**
- Created handover document
- Defined two-part solution (static + dynamic)
- Identified all files to modify
- Outlined testing requirements

**Next Steps:**
- Launch tdd-implementor for backend
- Launch ux-designer for frontend
- Launch system-architect for protocol
