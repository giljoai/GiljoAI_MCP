# Implementation Prompt for Handover 0430

Paste this into a fresh Claude Code session:

---

## Task: Implement Handover 0430 - Add `self_identity` Category to fetch_context()

Read the full handover document at `handovers/0430_self_identity_category_fetch_context.md` for complete context.

### Problem
The orchestrator agent template stored in Admin Settings (AgentTemplate table) is NEVER delivered to the orchestrator. Critical behavioral guidance (MCP tool usage, check-in protocol, success criteria) is missing from the execution flow.

### Solution
Add `self_identity` as a new category to the existing `fetch_context()` MCP tool, enabling agents to retrieve their own templates on-demand.

### Implementation Steps

**Phase 1: Create internal tool (TDD)**
- Create `src/giljo_mcp/tools/context_tools/get_self_identity.py`
- Query `mcp_agent_templates` table by agent_name
- Return: system_instructions, behavioral_rules, success_criteria
- Write tests first in `tests/unit/context_tools/test_get_self_identity.py`

**Phase 2: Integrate into fetch_context**
- Modify `src/giljo_mcp/tools/context_tools/fetch_context.py`
- Add `self_identity` to CATEGORY_TOOLS mapping
- Add validation: requires `agent_name` parameter when category is `self_identity`

**Phase 3: Update MCP schema**
- Modify `api/endpoints/mcp_http.py`
- Add `self_identity` to categories enum in fetch_context tool schema
- Add optional `agent_name` parameter

**Phase 4: Update thin prompt**
- Modify `src/giljo_mcp/thin_prompt_generator.py` in `generate_staging_prompt()`
- Add Step 3: `fetch_context(categories=["self_identity"], agent_name="orchestrator")`

**Phase 5: Validate template content**
- Review `src/giljo_mcp/template_seeder.py` orchestrator template
- Remove any outdated content
- Ensure MCP tool guidance is current

**Phase 6: Integration testing**
- Test full flow: thin prompt → get_orchestrator_instructions → fetch_context(self_identity)
- Verify template content is returned correctly

### Key Constraints
- Follow TDD (write tests first)
- Use existing patterns from `get_product_context.py` and other internal tools
- Template is ~2K tokens, fetched on-demand
- Must work for orchestrator AND specialist agents

### Success Criteria
- [ ] `fetch_context(categories=["self_identity"], agent_name="orchestrator")` returns template
- [ ] Thin prompt includes Step 3 for identity fetch
- [ ] Unit tests pass
- [ ] Integration test passes
- [ ] No regression in existing fetch_context functionality

### Commands
```bash
# Run tests
pytest tests/unit/context_tools/test_get_self_identity.py -v
pytest tests/tools/test_fetch_context.py -v

# Verify import
python -c "from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity; print('OK')"
```

Begin by reading the full handover document, then implement Phase 1 with TDD.
