# Handover 0315: MCP Thin Client Refactor

**Status**: Not Started
**Tool**: Claude Code (CLI) - Requires backend implementation + MCP tool creation
**Created**: 2025-11-17
**Dependencies**: 0312 (v2.0 Design), 0313 (Priority System), 0314 (Depth Controls)
**Next**: Deployment (v2.0 goes live)

---

## Objective

Create 6 MCP tools for on-demand context fetching, implement thin prompt generator, and integrate with orchestrator staging. Reuse 60-80% of v1.0 extraction methods from `mission_planner.py`. Deprecate `OrchestratorPromptGenerator` (mark for removal in v4.0).

---

## Scope

### Backend Changes

1. **Create 6 MCP Tools** (`src/giljo_mcp/tools/context/`):

#### Tool 1: `get_vision_document.py`
```python
@mcp_tool
async def get_vision_document(
    product_id: str,
    tenant_key: str,
    chunking: str = "moderate"  # none | light | moderate | heavy
) -> str:
    """
    Fetch vision document respecting user's depth settings.

    Chunking levels:
    - none: Full document (potentially 50K+ tokens)
    - light: 1-2 chunks (~10K tokens total)
    - moderate: 3-5 chunks (~15-25K tokens total)
    - heavy: 6+ chunks (30K+ tokens total)

    Returns rich data at requested depth (NOT arbitrarily trimmed).
    """
    # REUSE: mission_planner.py:_extract_vision_content()
    # REUSE: ProductService.get_vision_chunks()
```

#### Tool 2: `get_360_memory.py`
```python
@mcp_tool
async def get_360_memory(
    product_id: str,
    tenant_key: str,
    last_n_projects: int = 3,  # 1 | 3 | 5 | 10
    detail: str = "summary"    # summary | full
) -> str:
    """
    Fetch 360 Memory historical learnings.

    Returns:
    - Objectives, decisions, context, knowledge_base (always included)
    - Sequential history: Last N projects based on user setting
    - Detail level:
      - summary: Include project summaries only (~500 tokens/project)
      - full: Include full project closeout details (~2K tokens/project)

    Sorted by sequence DESC (most recent first).
    """
    # REUSE: mission_planner.py:_extract_360_memory()
    # REUSE: ProductService.get_product_memory()
    # DEPENDENCY: Requires project closeout workflow (see project_closure_proposal.md)
```

#### Tool 3: `get_git_history.py`
```python
@mcp_tool
async def get_git_history(
    product_id: str,
    tenant_key: str,
    commits: int = 25  # 10 | 25 | 50 | 100
) -> str:
    """
    Fetch recent Git commits from product's configured repository.

    Returns:
    - Last N commits (based on user setting)
    - Format: commit hash, author, date, message
    - Sorted by date DESC (most recent first)

    Returns empty string if GitHub integration disabled.
    """
    # REUSE: mission_planner.py:_extract_git_history()
    # REUSE: ProductService.get_git_commits()
```

#### Tool 4: `get_agent_templates.py`
```python
@mcp_tool
async def get_agent_templates(
    product_id: str,
    tenant_key: str,
    detail: str = "standard"  # minimal | standard | full
) -> str:
    """
    Fetch active agent templates.

    Detail levels:
    - minimal: Name, type, one-line description (~50 tokens/agent)
    - standard: + Capabilities, tools, constraints (~100 tokens/agent)
    - full: + Full prompt, examples, integration notes (~300 tokens/agent)

    Returns only templates marked as active.
    """
    # REUSE: agent_selector.py:get_active_templates()
    # REUSE: TemplateManager.list_templates()
```

#### Tool 5: `get_tech_stack.py`
```python
@mcp_tool
async def get_tech_stack(
    product_id: str,
    tenant_key: str,
    sections: str = "all"  # required | all
) -> str:
    """
    Fetch product tech stack fields.

    Sections:
    - required: backend_tech, frontend_tech, database_tech only
    - all: + additional_tech_details, dev_tools, deployment_config

    Returns formatted markdown sections.
    """
    # REUSE: mission_planner.py:_extract_tech_stack()
    # REUSE: ProductService.get_product()
```

#### Tool 6: `get_architecture.py`
```python
@mcp_tool
async def get_architecture(
    product_id: str,
    tenant_key: str,
    depth: str = "overview"  # overview | detailed
) -> str:
    """
    Fetch product architecture documentation.

    Depth levels:
    - overview: High-level summary (~300 tokens)
    - detailed: Full architecture docs (~1K+ tokens)

    Sources:
    - Product.architecture_notes field
    - Linked architecture documents (if configured)
    """
    # REUSE: mission_planner.py:_extract_architecture()
    # REUSE: ProductService.get_product()
```

2. **Register MCP Tools**:
   ```python
   # src/giljo_mcp/tools/__init__.py
   from .context.get_vision_document import get_vision_document
   from .context.get_360_memory import get_360_memory
   from .context.get_git_history import get_git_history
   from .context.get_agent_templates import get_agent_templates
   from .context.get_tech_stack import get_tech_stack
   from .context.get_architecture import get_architecture

   # Register with MCP server
   mcp.add_tool(get_vision_document)
   mcp.add_tool(get_360_memory)
   mcp.add_tool(get_git_history)
   mcp.add_tool(get_agent_templates)
   mcp.add_tool(get_tech_stack)
   mcp.add_tool(get_architecture)
   ```

3. **Implement Thin Prompt Generator**:
   ```python
   # src/giljo_mcp/services/thin_client_prompt_generator.py
   class ThinClientPromptGenerator:
       """Generate <600 token prompts with MCP tool references"""

       async def generate_orchestrator_prompt(
           self,
           product_id: str,
           project_id: str,
           tenant_key: str,
           user_priorities: Dict[str, int],  # from User.field_priority_config
           user_depth: Dict[str, Any]        # from User.depth_config
       ) -> str:
           """
           Generate thin prompt for orchestrator.

           Template (~600 tokens):
           - Role description (~100 tokens)
           - MCP tool list grouped by priority (~150 tokens)
           - Depth settings (~100 tokens)
           - Project context (~100 tokens)
           - Workflow instructions (~100 tokens)
           - Success criteria (~50 tokens)
           """
           # Group MCP tools by priority
           critical_tools = []
           important_tools = []
           nice_to_have_tools = []

           if user_priorities.get("product_core") == 1:
               critical_tools.append(f"get_tech_stack(sections='{user_depth['tech_stack_sections']}')")
           # ... etc for all 6 sources

           # Build thin prompt template (see 0312 design doc for full template)
           prompt = f"""# Orchestrator Mission: {{project_name}}

You are the AI Orchestrator for product **{{product_name}}** (ID: {product_id}).

## Your Role
- Fetch context via MCP tools based on priority configuration
- Create mission plan respecting token budget: {{token_budget}} tokens
- Select appropriate agents from available templates
- Spawn agent jobs and coordinate execution

## MCP Tools Available

### Priority 1 (CRITICAL - Always Fetch)
{chr(10).join(f'- `{tool}`' for tool in critical_tools)}

### Priority 2 (IMPORTANT - Fetch if Budget Allows)
{chr(10).join(f'- `{tool}`' for tool in important_tools)}

### Priority 3 (NICE_TO_HAVE - Fetch if Budget Remaining)
{chr(10).join(f'- `{tool}`' for tool in nice_to_have_tools)}

## Workflow
1. Fetch CRITICAL context via MCP tools
2. Assess remaining token budget
3. Fetch IMPORTANT context if budget allows
4. Fetch NICE_TO_HAVE context if budget remaining
5. Create mission plan based on fetched context
6. Select agents using `agent_selector` workflow
7. Spawn agent jobs via `spawn_agent_job()` MCP tool
8. Monitor context usage, trigger succession at 90% capacity

Begin orchestration when ready.
"""
           return prompt
   ```

4. **Update `orchestrate_project()` MCP Tool**:
   ```python
   # src/giljo_mcp/tools/orchestrate_project.py
   @mcp_tool
   async def orchestrate_project(
       product_id: str,
       project_id: str,
       tenant_key: str
   ) -> str:
       """
       Orchestrate project using thin client architecture.

       V2.0: Uses thin prompt generator (NOT fat prompt generator).
       """
       # Get user priorities and depth config
       user = await UserService.get_user_by_tenant(tenant_key)
       priorities = user.field_priority_config
       depth = user.depth_config

       # Generate thin prompt
       thin_prompt = await ThinClientPromptGenerator().generate_orchestrator_prompt(
           product_id, project_id, tenant_key, priorities, depth
       )

       # Store orchestrator job with thin prompt
       # ... (rest of orchestration logic)

       return thin_prompt  # Return to orchestrator for execution
   ```

5. **Deprecate `OrchestratorPromptGenerator`**:
   ```python
   # src/giljo_mcp/services/orchestrator_prompt_generator.py
   import warnings

   class OrchestratorPromptGenerator:
       """
       DEPRECATED: Use ThinClientPromptGenerator instead.
       This class generates fat prompts (3000+ tokens) and will be removed in v4.0.
       """

       def __init__(self):
           warnings.warn(
               "OrchestratorPromptGenerator is deprecated. Use ThinClientPromptGenerator instead.",
               DeprecationWarning,
               stacklevel=2
           )
   ```

---

## Code Reuse from v1.0

**Reuse (60-80% target)**:
- `mission_planner.py:_extract_vision_content()` → `get_vision_document` tool
- `mission_planner.py:_extract_360_memory()` → `get_360_memory` tool
- `mission_planner.py:_extract_git_history()` → `get_git_history` tool
- `mission_planner.py:_extract_tech_stack()` → `get_tech_stack` tool
- `mission_planner.py:_extract_architecture()` → `get_architecture` tool
- `agent_selector.py:get_active_templates()` → `get_agent_templates` tool

**Remove**:
- `OrchestratorPromptGenerator` (deprecated, mark for removal in v4.0)
- Uniform trimming logic (no longer needed)
- Fat prompt generation (replaced by thin prompts)

**New**:
- `ThinClientPromptGenerator` service
- 6 MCP tools in `src/giljo_mcp/tools/context/` directory
- MCP tool registration in `__init__.py`

---

## Testing Strategy

### Unit Tests (`tests/giljo_mcp/test_mcp_thin_client.py`)

1. **MCP Tool Testing** (6 tools × multiple depth settings):
   - Test `get_vision_document` with all chunking levels (none/light/moderate/heavy)
   - Test `get_360_memory` with all project counts (1/3/5/10) and detail levels (summary/full)
   - Test `get_git_history` with all commit counts (10/25/50/100)
   - Test `get_agent_templates` with all detail levels (minimal/standard/full)
   - Test `get_tech_stack` with all section levels (required/all)
   - Test `get_architecture` with all depth levels (overview/detailed)

2. **Multi-Tenant Isolation**:
   - Test tenant_key filtering (product A data not returned for tenant B request)
   - Test error handling (product not found for tenant)

3. **Rich Data Delivery**:
   - Verify NO arbitrary trimming (data returned at requested depth, not truncated)
   - Verify token estimates within ±10% margin

### Integration Tests (`tests/integration/test_thin_client_e2e.py`)

1. **End-to-End Workflow**:
   - Create user → set priority/depth configuration
   - Create product → upload vision, add 360 memory
   - Create project → trigger orchestrator staging
   - Verify thin prompt generated (<600 tokens)
   - Simulate orchestrator fetching via MCP tools (priority order)
   - Verify rich data returned (no arbitrary trimming)
   - Verify context usage tracking
   - Verify succession trigger at 90% capacity

2. **Thin Prompt Generator**:
   - Test prompt size (<600 tokens)
   - Test MCP tool references (all 6 tools listed)
   - Test priority grouping (CRITICAL/IMPORTANT/NICE/EXCLUDED)
   - Test depth settings inclusion

**Coverage Target**: >80%

---

## Deliverables

1. 6 MCP tools in `src/giljo_mcp/tools/context/` directory
2. `ThinClientPromptGenerator` service in `src/giljo_mcp/services/`
3. Updated `orchestrate_project()` tool (uses thin prompt generator)
4. Deprecated `OrchestratorPromptGenerator` (mark for removal in v4.0)
5. Tests: `test_mcp_thin_client.py`, `test_thin_prompt_generator.py` (>80% coverage)
6. Migration guide: `docs/guides/thin_client_migration_guide.md`

---

## Success Criteria

- [ ] 6 MCP tools created and registered with MCP server
- [ ] Thin prompt generator produces <600 token prompts
- [ ] MCP tools return rich data at requested depth (no arbitrary trimming)
- [ ] Multi-tenant isolation enforced (all tools respect tenant_key)
- [ ] `orchestrate_project()` uses thin prompt generator (NOT fat prompt generator)
- [ ] `OrchestratorPromptGenerator` deprecated (warnings emitted)
- [ ] Code reuse achieved (60-80% of v1.0 extraction methods)
- [ ] Tests pass with >80% coverage
- [ ] Migration guide documents v1.0 → v2.0 transition

---

## Dependencies

**Blocked by**:
- 0312 (v2.0 Design)
- 0313 (Priority System) - orchestrator needs priority config to decide WHAT to fetch
- 0314 (Depth Controls) - MCP tools need depth config to determine HOW MUCH data to return

**Blocks**: None (final handover in v2.0 sequence)

**Open Dependency**: Project closeout workflow (affects `get_360_memory` tool) - see `project_closure_proposal.md`

---

## Notes

**Hard Cutover**: Clean implementation, no feature flags. v1.0 fat prompt generator deprecated after v2.0 deployment.

**Code Reuse Target**: 60-80% of v1.0 extraction methods reused in MCP tools. Only architectural approach changes (priority semantics, thin client).

**Follow 013A Patterns**:
- Service layer pattern (ThinClientPromptGenerator)
- Multi-tenant isolation (tenant_key filtering in all MCP tools)
- Production-grade code from start (no TODOs, no bandaids)
- Use `pathlib.Path()` for all file operations
- Comprehensive error handling
- >80% test coverage

**Migration Guide**:
- Document v1.0 → v2.0 transition
- Explain fat prompt → thin prompt migration
- Show MCP tool usage examples
- Document deprecation timeline (v4.0 removal of `OrchestratorPromptGenerator`)
