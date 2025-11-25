# Session: Handover 0246a Refocus to Staging Prompt Implementation

**Date**: 2025-11-24
**Context**: Critical handover refocus after discovering the frontend toggle was already fixed by a previous agent. The REAL missing piece is the staging prompt implementation.

---

## Key Decisions

### Decision 1: Pivot from Frontend Toggle to Backend Staging Prompt
**Rationale**: The frontend execution mode toggle was already implemented by a previous agent. The user discovered that 0246a was misfocused on a "trivial fix" when the ACTUAL missing piece is the `_build_staging_prompt()` method - the core orchestration function that prepares projects for execution.

**Impact**: This refocus unlocks understanding that **80% of the dynamic agent discovery vision is unimplemented at the prompt generation layer**, not at the UI layer.

### Decision 2: Document the 7-Task Staging Workflow
**Rationale**: The staging prompt must execute a strict sequence of validation and discovery tasks:
1. Identity & Context Verification
2. MCP Health Check
3. Environment Understanding (CLAUDE.md)
4. Agent Discovery & Version Check
5. Context Prioritization & Mission Creation
6. Agent Job Spawning
7. Activation

This sequencing prevents race conditions and ensures proper initialization.

### Decision 3: Prioritize Removal of Embedded Agent Templates
**Rationale**: Current implementation embeds 142 tokens of hardcoded agent templates. This is brittle and causes version mismatches. Should replace with dynamic `get_available_agents()` MCP tool call.

**Savings**: Removes 142 tokens, improves maintainability, enables true dynamic discovery.

### Decision 4: Add Product ID to Identity Section
**Rationale**: Current identity section missing Product ID, which is critical for context prioritization and 360 memory management. Must add immediately.

### Decision 5: Estimate 4-5 Day Timeline (46-60 Hours)
**Rationale**: Implementation broken into 7 phases:
- Phase 1: Analysis (4-6h)
- Phase 2: Tasks 1-2 (8-10h)
- Phase 3: Tasks 3-4 (10-12h)
- Phase 4: Task 5 (8-10h)
- Phase 5: Tasks 6-7 (6-8h)
- Phase 6: Testing (6-8h)
- Phase 7: Documentation (4-6h)

---

## Technical Details

### The Staging Prompt Structure

The new `_build_staging_prompt()` method will be organized as:

```python
def _build_staging_prompt(self) -> str:
    # Phase 1: Identity & Context (200 tokens)
    identity = self._build_identity_section()

    # Phase 2: MCP Health Check (300 tokens)
    health_check = self._build_mcp_health_check_section()

    # Phase 3: Environment Understanding (400 tokens)
    environment = self._build_environment_section()

    # Phase 4: Agent Discovery (500 tokens)
    discovery = self._build_agent_discovery_section()

    # Phase 5: Context Prioritization (600 tokens)
    context = self._build_context_prioritization_section()

    # Phase 6: Job Spawning (400 tokens)
    spawning = self._build_job_spawning_section()

    # Phase 7: Activation (300 tokens)
    activation = self._build_activation_section()

    return f"{identity}\n{health_check}\n{environment}\n..."
```

### Key Token Budget

- **Current embedding size**: 3.2K tokens (includes 142 token agent template dump)
- **Target new size**: 2.7K tokens
- **Savings**: 142 tokens (removed agent templates)
- **Flexibility gained**: 142 tokens for improved instructions

### MCP Tool Integration

The staging prompt must include explicit instructions to call:
1. `get_available_agents()` - Dynamic agent discovery (replaces hardcoding)
2. `fetch_product_context()` - Product information
3. `fetch_vision_document()` - Vision docs (with user's depth setting)
4. `fetch_git_history()` - Commit context
5. `fetch_360_memory()` - Project history

Each tool call documented in prompt instructions, NOT embedded in templates.

---

## Lessons Learned

### Lesson 1: Verify Previous Work Before Starting
Don't assume what needs to be built. The frontend toggle was already fixed by a previous agent (Handover 0235 or earlier). This refocus saved us from implementing duplicate work.

### Lesson 2: Vision Implementation Can Span Multiple Layers
The dynamic agent discovery vision isn't just about agent templates - it's about:
- Dynamic MCP tool integration (not hardcoding)
- Version checking and compatibility validation
- Proper 7-task sequencing to prevent race conditions
- Context prioritization based on user settings

Missing any layer breaks the entire vision.

### Lesson 3: Token Budget is Real Constraint
Embedding agent templates consumes 142 tokens. Removing this and using dynamic discovery saves tokens AND improves maintainability. This pattern applies across the system.

### Lesson 4: Task Sequencing Matters
The 7-task workflow isn't arbitrary - each task depends on previous ones:
- Can't do agent discovery (Task 3) before MCP health check (Task 2)
- Can't spawn jobs (Task 6) before context prioritization (Task 5)
- Strict ordering prevents async/race condition bugs

---

## Files Modified

- `F:\GiljoAI_MCP\handovers\0246a_staging_prompt_implementation.md` - Complete rewrite from toggle to staging prompt focus

---

## Related Documentation

- **Handover 0246**: Dynamic Agent Discovery Research (foundational understanding)
- **Handover 0245**: Initial Dynamic Agent Discovery (related work)
- **Handover 0235**: GUI Redesign - Status Board components
- **CLAUDE.md**: Project configuration file that staging prompt must read
- **ThinClientPromptGenerator**: The class containing `_build_staging_prompt()`

---

## Next Steps for Implementation Agent

1. **Phase 1**: Read `thin_prompt_generator.py` to understand current implementation
2. **Find agent templates**: Locate embedded 142-token agent template section
3. **Plan replacement**: Design MCP tool calls to replace hardcoding
4. **Implement sequentially**: Build each of the 7 task sections
5. **Test thoroughly**: Ensure all 7 tasks work in correct order
6. **Validate token count**: Confirm prompt stays under 3.5K tokens

---

## Success Definition

This handover is successful when:
- ✅ All 7 staging tasks implemented in correct sequence
- ✅ Agent templates removed (142 tokens freed)
- ✅ `get_available_agents()` MCP tool called (not embedded)
- ✅ Version checking and compatibility validation included
- ✅ Product ID added to identity section
- ✅ Tests passing (>85% coverage)
- ✅ Token count < 3.5K
- ✅ Full integration with existing orchestration workflows

---

**Document Version**: 1.0
**Session Type**: Handover Refocus
**Priority**: HIGHEST
**Timeline**: 4-5 days of focused implementation
