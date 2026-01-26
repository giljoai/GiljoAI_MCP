# Handover 0430: Add `self_identity` Category to fetch_context() MCP Tool

**Date:** 2026-01-21
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor / Backend Integration Tester
**Priority:** High
**Estimated Complexity:** 6-8 hours
**Status:** Ready for Implementation

---

## Task Summary

Add a new `self_identity` category to the existing `fetch_context()` MCP tool that fetches the agent's own template from the database. This ensures orchestrators and agents receive their behavioral guidance, success criteria, and protocol instructions from the AgentTemplate stored in Admin Settings.

**Current Problem:** The orchestrator agent template is NEVER delivered to the orchestrator. It only receives:
- Thin prompt (~113 tokens) - identity + "call get_orchestrator_instructions"
- Hardcoded 5-chapter protocol from `_build_orchestrator_protocol()`
- AgentJob.mission (user input + context)

The orchestrator template contains critical behavioral guidance that's missing from the execution flow. This works currently because Claude Opus 4.5 is intelligent enough to compensate, but would fail with less capable LLMs.

**Proposed Solution:** Add `self_identity` as a fetchable context category, enabling agents to retrieve their own templates on-demand via the existing `fetch_context()` architecture.

---

## Context and Background

### Architectural Context
GiljoAI uses a thin-client architecture (Handover 0246 series) where prompts are ~450-550 tokens and agents fetch their context via MCP tools. This prevents token bloat and enables on-demand context loading.

### The Gap
While agents can fetch product context, vision documents, tech stack, etc., they currently CANNOT fetch their own identity/template. This means critical behavioral guidance from the AgentTemplate table is inaccessible during execution.

### Agent Template Content
The orchestrator template (stored in `mcp_agent_templates` table) contains:
- MCP tool usage patterns ("MCP tools are NATIVE tool calls, not curl/HTTP")
- Check-in protocol (when to report progress)
- Context request patterns (how to use fetch_context)
- Success criteria (definition of done)
- Agent-specific behavioral rules

**Estimated Size:** ~2,000 tokens per template (fetched on-demand, not embedded)

---

## Technical Details

### Files to Modify

**1. `src/giljo_mcp/tools/context_tools/fetch_context.py`**
- Add `self_identity` to `CATEGORY_TOOLS` mapping (line ~40)
- Add `self_identity` to `DEFAULT_DEPTHS` (line ~53) - set to `None` (no depth param)
- Add `self_identity` to `ALL_CATEGORIES` list (line ~65)
- Add validation: `self_identity` requires `agent_id` parameter

**2. `src/giljo_mcp/tools/context_tools/get_self_identity.py` (NEW FILE)**
- Create new internal tool to fetch agent template
- Query `mcp_agent_templates` table by `agent_name` (matches template filename)
- Return: `system_instructions`, `behavioral_rules`, `success_criteria`, `protocol`
- Follow same pattern as `get_product_context.py` and other internal tools

**3. `src/giljo_mcp/thin_prompt_generator.py`**
- Update `generate_staging_prompt()` method
- Add Step 3: "Fetch your identity: `fetch_context(categories=["self_identity"])`"
- Current structure has ~7 steps, this becomes step 3 (after MCP health check)

**4. `api/endpoints/mcp_http.py`**
- Update `fetch_context` MCP tool schema
- Add `"self_identity"` to categories enum (line with `"product_core", "vision_documents", ...`)
- Add optional `agent_id` parameter to schema (required when category is `self_identity`)

**5. `src/giljo_mcp/template_seeder.py` (VALIDATION ONLY)**
- Review orchestrator template content
- Remove outdated information
- Ensure MCP tool guidance is current
- Verify template structure matches expected fields

---

## Implementation Plan

### Phase 1: Create Internal Tool (TDD - 2 hours)
**RED → GREEN → REFACTOR**

1. **Write failing test** (`tests/tools/context_tools/test_get_self_identity.py`):
   ```python
   @pytest.mark.asyncio
   async def test_get_self_identity_returns_template_content(db_session, test_tenant):
       """Test that get_self_identity fetches template by agent name"""
       # Create test template
       template = AgentTemplate(
           name="orchestrator-coordinator",
           agent_display_name="Orchestrator",
           system_instructions="Orchestrate agents...",
           behavioral_rules="Use MCP tools...",
           success_criteria="All agents complete...",
           protocol="7-task staging workflow...",
           tenant_key=test_tenant
       )
       db_session.add(template)
       await db_session.commit()

       # Fetch self identity
       result = await get_self_identity(
           agent_name="orchestrator-coordinator",
           tenant_key=test_tenant,
           db_manager=db_session
       )

       # Verify template content returned
       assert result["success"] is True
       assert "orchestrator-coordinator" in result["data"]["agent_name"]
       assert "Orchestrate agents" in result["data"]["system_instructions"]
   ```

2. **Implement minimal `get_self_identity()` function**:
   - Query `mcp_agent_templates` by `agent_name` and `tenant_key`
   - Return template fields: `system_instructions`, `behavioral_rules`, `success_criteria`, `protocol`
   - Follow pattern from `get_product_context.py`

3. **Refactor**: Add logging, error handling, structured response format

**Expected Test Outcome:**
- Initial run: FAIL (RED ❌) - function doesn't exist
- After implementation: PASS (GREEN ✅)

---

### Phase 2: Integrate into fetch_context (TDD - 2 hours)

1. **Write failing integration test** (`tests/tools/context_tools/test_fetch_context.py`):
   ```python
   @pytest.mark.asyncio
   async def test_fetch_context_self_identity_category(db_session, test_tenant):
       """Test that fetch_context supports self_identity category"""
       # Create test template and product
       template = await create_test_template(agent_name="orchestrator-coordinator")
       product = await create_test_product()

       # Fetch self_identity
       result = await fetch_context(
           product_id=product.id,
           tenant_key=test_tenant,
           categories=["self_identity"],
           agent_name="orchestrator-coordinator",  # NEW PARAM
           db_manager=db_session
       )

       # Verify structure
       assert "self_identity" in result
       assert "system_instructions" in result["self_identity"]
       assert "behavioral_rules" in result["self_identity"]
   ```

2. **Modify `fetch_context.py`**:
   - Add `agent_name` optional parameter
   - Add `"self_identity": get_self_identity` to `CATEGORY_TOOLS`
   - Add `"self_identity": None` to `DEFAULT_DEPTHS`
   - Add validation: if `"self_identity"` in categories, require `agent_name`

3. **Test edge cases**:
   - Template not found (should return graceful error)
   - Missing agent_name parameter (should raise validation error)
   - Multi-tenant isolation (tenant A can't fetch tenant B's templates)

**Expected Test Outcome:**
- Initial run: FAIL (RED ❌) - category not recognized
- After implementation: PASS (GREEN ✅)

---

### Phase 3: Update MCP Tool Schema (1 hour)

1. **Update `api/endpoints/mcp_http.py`**:
   - Add `"self_identity"` to categories enum in `fetch_context` tool schema
   - Add optional `agent_name: str` parameter to tool schema
   - Add description: "Required when category is 'self_identity'"

2. **Test MCP tool exposure**:
   ```bash
   # Start server
   python startup.py --dev

   # Call MCP tool via HTTP
   curl -X POST http://localhost:7272/mcp \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_api_key" \
     -d '{
       "jsonrpc": "2.0",
       "method": "tools/call",
       "params": {
         "name": "fetch_context",
         "arguments": {
           "product_id": "uuid",
           "tenant_key": "tenant",
           "categories": ["self_identity"],
           "agent_name": "orchestrator-coordinator"
         }
       },
       "id": 1
     }'
   ```

**Expected Outcome:** Tool schema validates successfully, returns template content

---

### Phase 4: Update Thin Prompt Generator (1 hour)

1. **Modify `src/giljo_mcp/thin_prompt_generator.py`**:
   - Locate `generate_staging_prompt()` method
   - Add new step after MCP health check:
     ```
     3. **Fetch Your Identity**: Call fetch_context(categories=["self_identity"], agent_name="{agent_name}") to retrieve your behavioral guidance, success criteria, and protocol instructions from the template system.
     ```

2. **Test prompt generation**:
   ```python
   @pytest.mark.asyncio
   async def test_staging_prompt_includes_self_identity_step():
       """Test that staging prompt instructs agent to fetch self_identity"""
       generator = ThinClientPromptGenerator()
       prompt = await generator.generate_staging_prompt(
           orchestrator_id="orch_123",
           agent_name="orchestrator-coordinator"
       )

       # Verify step exists
       assert "fetch_context(categories=[\"self_identity\"]" in prompt
       assert "agent_name=\"orchestrator-coordinator\"" in prompt
   ```

**Expected Outcome:** Staging prompt now includes identity fetch step

---

### Phase 5: Validate Template Content (30 minutes)

1. **Review `src/giljo_mcp/template_seeder.py`**:
   - Check orchestrator template content
   - Remove outdated references
   - Ensure MCP tool guidance is accurate ("MCP tools are NATIVE tool calls")
   - Verify 7-task staging workflow is documented

2. **Manual test**:
   - Seed database: `python install.py`
   - Check template content:
     ```bash
     PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
       "SELECT agent_display_name, LENGTH(system_instructions) FROM mcp_agent_templates WHERE name='orchestrator-coordinator';"
     ```

**Expected Outcome:** Template content is current and accurate (~2,000 tokens)

---

### Phase 6: Integration Testing (1-2 hours)

1. **End-to-end workflow test**:
   ```python
   @pytest.mark.asyncio
   async def test_orchestrator_fetches_self_identity_on_staging():
       """Test full flow: staging prompt → fetch_context → template retrieval"""
       # Create product, project, orchestrator job
       product = await create_test_product()
       project = await create_test_project(product_id=product.id)
       orch_job = await create_orchestrator_job(project_id=project.id)

       # Generate staging prompt
       prompt = await generate_staging_prompt(orch_job.id)

       # Verify prompt instructs self_identity fetch
       assert "fetch_context(categories=[\"self_identity\"]" in prompt

       # Simulate agent calling fetch_context
       result = await fetch_context(
           product_id=product.id,
           tenant_key=product.tenant_key,
           categories=["self_identity"],
           agent_name="orchestrator-coordinator"
       )

       # Verify template content returned
       assert result["self_identity"]["system_instructions"] is not None
       assert len(result["self_identity"]["system_instructions"]) > 1000  # ~2K tokens
   ```

2. **Manual test with real orchestrator**:
   - Launch orchestrator via UI
   - Verify it calls `fetch_context(categories=["self_identity"])`
   - Verify template content appears in orchestrator's context

**Expected Outcome:** Full flow works end-to-end

---

## Testing Requirements

### Unit Tests (Write FIRST)
**File:** `tests/tools/context_tools/test_get_self_identity.py`
- `test_get_self_identity_returns_template_content()` - Happy path
- `test_get_self_identity_template_not_found()` - Graceful error
- `test_get_self_identity_enforces_tenant_isolation()` - Security

**File:** `tests/tools/context_tools/test_fetch_context.py`
- `test_fetch_context_self_identity_category()` - Integration
- `test_fetch_context_self_identity_requires_agent_name()` - Validation
- `test_fetch_context_self_identity_with_user_config()` - Priority system

**Coverage Target:** >80% for new code

---

### Integration Tests
**File:** `tests/integration/test_orchestrator_identity_fetch.py`
- `test_orchestrator_staging_prompt_includes_identity_step()`
- `test_orchestrator_fetches_template_via_mcp_tool()`
- `test_template_content_matches_database_record()`

---

### Manual Testing
**Procedure:**
1. Start server: `python startup.py --dev`
2. Create product via UI
3. Launch orchestrator
4. Check orchestrator logs for `fetch_context(categories=["self_identity"])` call
5. Verify template content appears in orchestrator context
6. Confirm orchestrator follows behavioral guidance from template

**Expected Results:**
- Orchestrator calls `fetch_context` with `self_identity` category
- Template content (~2K tokens) returned successfully
- Orchestrator behavior aligns with template instructions

---

## Dependencies and Blockers

### Dependencies
- ✅ `fetch_context()` tool already exists (Handover 0350a)
- ✅ `AgentTemplate` table seeded with orchestrator template
- ✅ Thin prompt generator infrastructure exists (Handover 0246a)

### No Current Blockers
All required infrastructure is in place. This is a pure additive change.

---

## Success Criteria

**Definition of Done:**
- [ ] `get_self_identity()` internal tool implemented (TDD)
- [ ] `self_identity` category added to `fetch_context()`
- [ ] MCP tool schema updated with new category
- [ ] Staging prompt includes identity fetch step
- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Manual testing confirms end-to-end flow works
- [ ] Template content validated and current
- [ ] Multi-tenant isolation verified
- [ ] Documentation updated (API reference, MCP tools manual)

**Behavioral Verification:**
- Orchestrator fetches template via `fetch_context(categories=["self_identity"])`
- Template content (~2K tokens) available in orchestrator's context
- Orchestrator follows behavioral guidance from template (e.g., "MCP tools are NATIVE tool calls")

---

## Rollback Plan

**If Things Go Wrong:**
1. **Revert code changes**:
   ```bash
   git revert HEAD
   ```

2. **Remove `self_identity` from tool schema**:
   - Remove from `api/endpoints/mcp_http.py`
   - Remove from `fetch_context.py`

3. **Restore staging prompt**:
   - Remove identity fetch step from `thin_prompt_generator.py`

4. **Validate rollback**:
   ```bash
   pytest tests/tools/context_tools/ -v
   pytest tests/integration/ -v
   ```

**No Database Impact:** This change only adds code, no schema modifications required.

---

## Additional Resources

### Related Files
- `src/giljo_mcp/tools/context_tools/fetch_context.py` - Main tool to modify
- `src/giljo_mcp/tools/context_tools/get_product_context.py` - Pattern reference
- `src/giljo_mcp/models.py` - AgentTemplate model (lines ~800-850)
- `src/giljo_mcp/thin_prompt_generator.py` - Prompt generation
- `api/endpoints/mcp_http.py` - MCP tool schema

### Documentation References
- `docs/api/context_tools.md` - Context API reference (UPDATE THIS)
- `docs/manuals/MCP_TOOLS_MANUAL.md` - MCP tools documentation (UPDATE THIS)
- `handovers/0350_on_demand_context_fetch_architecture.md` - Original architecture
- `handovers/0246a_orchestrator_staging_workflow.md` - Staging workflow

### Similar Implementations
- `get_product_context()` - Fetches product-level context
- `get_project()` - Fetches project-level context
- Both follow same pattern: query DB → structure response → return dict

### GitHub Issues
- N/A - This is a new feature, not a bug fix

---

## Token Budget Impact

**Before Change:**
- Orchestrator template: NEVER delivered (missing from execution flow)
- Orchestrator relies on hardcoded protocol + Claude's intelligence

**After Change:**
- Template fetched on-demand via `fetch_context(categories=["self_identity"])`
- ~2,000 tokens when fetched (not embedded in thin prompt)
- Follows existing on-demand architecture (Handover 0350 series)

**Net Impact:**
- Thin prompt size: UNCHANGED (~113 tokens)
- Context budget: +2,000 tokens when `self_identity` fetched
- Total orchestrator context: Still within budget (thin-client architecture)

---

## Implementation Notes

### Why This Approach?
1. **Reuses Existing Infrastructure**: Leverages `fetch_context()` pattern (no new MCP tool)
2. **On-Demand Loading**: Template only fetched when needed (token-efficient)
3. **User-Editable**: Templates stored in Admin Settings (UI-configurable)
4. **Multi-Tenant Safe**: Enforces tenant isolation via existing patterns
5. **Priority-Compatible**: Can be configured via context priority system

### Alternative Approaches Considered
**❌ Embed template in thin prompt:**
- Bloats prompt from ~113 tokens to ~2,113 tokens
- Violates thin-client architecture principle
- Not on-demand (always present)

**❌ Create separate MCP tool (`get_agent_template`):**
- Adds ~100 tokens to MCP schema overhead
- Duplicates `fetch_context` pattern
- Inconsistent with existing architecture

**✅ Add to `fetch_context()` as category:** (CHOSEN)
- Consistent with existing patterns
- No schema overhead (reuses existing tool)
- On-demand loading
- User-configurable via priority system

---

## Coding Principles (Follow QUICK_LAUNCH.txt)

**TDD Discipline:**
- Write tests FIRST (RED phase)
- Implement minimal code (GREEN phase)
- Refactor and polish (REFACTOR phase)

**Service Layer Pattern:**
- No direct DB queries in endpoints
- Use dependency injection
- Return `dict[str, Any]` with `success/data/error`

**Multi-Tenant Isolation:**
- ALL queries filter by `tenant_key`
- Test cross-tenant access is blocked

**Cross-Platform Paths:**
- Use `pathlib.Path()` only
- No hardcoded Windows paths

**Clean Code:**
- DELETE old code, don't comment out
- Structured logging with metadata
- Pydantic schemas for validation

---

## Timeline Estimate

**Phase 1:** Create internal tool (TDD) - 2 hours
**Phase 2:** Integrate into fetch_context - 2 hours
**Phase 3:** Update MCP schema - 1 hour
**Phase 4:** Update thin prompt - 1 hour
**Phase 5:** Validate template content - 30 minutes
**Phase 6:** Integration testing - 1-2 hours

**Total:** 7.5-8.5 hours (fits in 1 development day)

---

## Final Checklist

**Before Starting:**
- [ ] Read `QUICK_LAUNCH.txt` for coding principles
- [ ] Review `fetch_context.py` implementation pattern
- [ ] Check `get_product_context.py` for internal tool pattern
- [ ] Verify `AgentTemplate` model structure

**During Implementation:**
- [ ] Write tests FIRST (TDD discipline)
- [ ] Run tests after each phase
- [ ] Maintain >80% coverage
- [ ] Use `pathlib.Path()` for all file operations
- [ ] Enforce multi-tenant isolation

**After Completion:**
- [ ] All tests passing (unit + integration)
- [ ] Coverage report generated (`pytest --cov`)
- [ ] Manual testing complete (full flow validated)
- [ ] Documentation updated (API reference, MCP manual)
- [ ] Git commit with descriptive message
- [ ] Handover marked complete and archived

---

**Remember:** This change enables orchestrators to access their own behavioral guidance from the template system. It's a critical piece of the thin-client architecture that was previously missing. Use TDD, follow existing patterns, and test thoroughly.
