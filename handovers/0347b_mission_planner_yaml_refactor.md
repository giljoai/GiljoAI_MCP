# Handover: MissionPlanner YAML Refactor

**Date:** 2025-12-14
**From Agent:** Documentation Manager (Planning)
**To Agent:** TDD Implementor
**Priority:** High
**Estimated Complexity:** 4 hours
**Status:** Not Started

---

## Task Summary

Refactor the `MissionPlanner._build_context_with_priorities()` method to use YAML output via the new `YAMLContextBuilder` class. This is Phase 2 of the Mission Response YAML Restructuring project (Handover 0347), which aims to achieve 93% token reduction in mission context responses.

**What needs to be done:**
Replace markdown string concatenation in `_build_context_with_priorities()` with structured YAML builder calls, while maintaining all existing field priority logic (Priority 1=CRITICAL, 2=IMPORTANT, 3=REFERENCE, 4=EXCLUDED).

**Why it's important:**
- **Token Efficiency**: Reduce mission context from ~21,000 tokens to ~1,500 tokens (93% reduction)
- **Structured Data**: YAML enables programmatic parsing by agents (vs prose markdown)
- **Maintainability**: Centralized YAML generation logic in YAMLContextBuilder
- **Consistency**: Unified YAML format across all mission responses

**Expected outcome:**
- `generate_mission()` returns missions with `mission_format: "yaml"` metadata
- Mission field contains valid, parseable YAML (verified via PyYAML)
- Token count for orchestrator missions drops to ~1,500 tokens
- All existing tests pass without modification

---

## Context and Background

### Project Timeline (Handover 0347 Series)

**0347a: YAMLContextBuilder** (Prerequisite - MUST complete first)
- Build `src/giljo_mcp/yaml_context_builder.py` class
- Implement 3-tier priority structure (CRITICAL/IMPORTANT/REFERENCE)
- Add token estimation methods
- Unit tests for YAML generation

**0347b: MissionPlanner YAML Refactor** (This handover)
- Refactor `_build_context_with_priorities()` to use YAMLContextBuilder
- Maintain field priority filtering logic
- Update token estimation to use `_estimate_yaml_tokens()`
- Integration tests for end-to-end YAML mission generation

**0347c: MCP Tools YAML Support** (Future)
- Update `get_orchestrator_instructions()` to return `mission_format: yaml`
- Update `get_agent_mission()` to return `mission_format: yaml`
- Frontend updates to display YAML missions

### Architectural Decisions

**Decision 1: YAML over JSON** (Handover 0347, lines 60-71)
- Rationale: YAML is more human-readable, supports comments, and reduces token count vs verbose JSON
- Implementation: Use PyYAML for generation/parsing

**Decision 2: 3-Tier Priority Structure** (Handover 0347, lines 1121-1245)
- **CRITICAL (Priority 1)**: Always included, inlined content (product_core, tech_stack)
- **IMPORTANT (Priority 2)**: Condensed summaries with fetch tools (architecture, testing, agent_templates)
- **REFERENCE (Priority 3)**: Metadata only with fetch instructions (vision_documents, memory_360, git_history)
- **EXCLUDED (Priority 4)**: Omitted entirely

**Decision 3: Client-Server Separation** (Handover 0246c)
- Mission context provides summaries and fetch instructions
- Agents call MCP tools (`fetch_vision_document()`, `fetch_360_memory()`, etc.) for detailed data
- Enables dynamic depth configuration per user

### Related Work

- **Handover 0312-0316**: Context Management v2.0 (Priority × Depth model)
- **Handover 0246a-c**: Orchestrator Workflow Pipeline (thin-client architecture)
- **Handover 0346**: Depth Config Field Standardization (prerequisite)

---

## Technical Details

### Files to Modify

**Primary File:**
```
F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py
```

**Method to Refactor:**
- `_build_context_with_priorities()` (lines ~1217-1700)
- Add new method: `_estimate_yaml_tokens()`

**Files to Create:**
```
F:\GiljoAI_MCP\tests\unit\test_mission_planner_yaml_output.py
```

**Existing Test Files (may need minor updates):**
```
F:\GiljoAI_MCP\tests\unit\test_mission_planner.py
F:\GiljoAI_MCP\tests\unit\test_mission_planner_priority.py
```

### Current Implementation Analysis

**Current Method Signature:**
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    depth_config: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> str:
    """Build context respecting user's field priorities and depth configuration."""
```

**Current Approach:**
1. Builds markdown strings via string concatenation
2. Constructs sections like "## Product Core", "## Tech Stack", etc.
3. Applies priority filtering to include/exclude fields
4. Returns markdown blob (~21,000 tokens for typical orchestrator mission)

**Pain Points:**
- String concatenation is verbose and error-prone
- Markdown parsing by agents requires regex/heuristics
- Token count estimation is imprecise (character count / 4)
- Difficult to maintain consistent formatting

### Target Implementation (Handover 0347, lines 1085-1246)

**New Method Structure:**
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    depth_config: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> str:
    """
    Build context respecting user's field priorities and depth configuration.

    Handover 0347: Returns YAML-structured context instead of markdown blob.

    Returns:
        YAML-formatted context string with explicit priority framing.
        Total tokens: ~1,500 (down from ~21,000)
    """
    from src.giljo_mcp.yaml_context_builder import YAMLContextBuilder

    builder = YAMLContextBuilder()

    # Default configurations
    if field_priorities is None:
        field_priorities = {}
    if depth_config is None:
        depth_config = {
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
            "vision_documents": "moderate",  # Handover 0346
        }

    # Apply defaults if user has no config
    effective_priorities = field_priorities if field_priorities else DEFAULT_FIELD_PRIORITIES.copy()

    # === CRITICAL SECTION (Priority 1) ===

    # Product Core
    product_core_priority = effective_priorities.get("product_core", 1)
    if product_core_priority == 1:  # CRITICAL
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {
            "name": product.name,
            "description": product.description or "",
            "type": product.config_data.get("product_type", "Software") if product.config_data else "Software"
        })

    # Tech Stack
    tech_stack_priority = effective_priorities.get("tech_stack", 1)
    if tech_stack_priority == 1:  # CRITICAL
        tech_stack_data = product.config_data.get("tech_stack", {}) if product.config_data else {}
        if tech_stack_data:
            builder.add_critical("tech_stack")
            builder.add_critical_content("tech_stack", {
                "languages": tech_stack_data.get("languages", []),
                "backend": tech_stack_data.get("backend_frameworks", []),
                "frontend": tech_stack_data.get("frontend_frameworks", []),
                "database": tech_stack_data.get("databases", {})
            })

    # === IMPORTANT SECTION (Priority 2) ===

    # Architecture (condensed)
    architecture_priority = effective_priorities.get("architecture", 2)
    if architecture_priority == 2:  # IMPORTANT
        arch_data = product.config_data.get("architecture", {}) if product.config_data else {}
        if arch_data:
            builder.add_important("architecture")
            builder.add_important_content("architecture", {
                "pattern": arch_data.get("pattern", "Unknown"),
                "api": arch_data.get("api_style", "REST"),
                "patterns": arch_data.get("design_patterns", []),
                "fetch_details": "fetch_architecture()"
            })

    # Testing (condensed)
    testing_priority = effective_priorities.get("testing", 2)
    if testing_priority == 2:  # IMPORTANT
        testing_data = product.config_data.get("testing", {}) if product.config_data else {}
        if testing_data:
            builder.add_important("testing")
            builder.add_important_content("testing", {
                "target": testing_data.get("coverage_target", "80%"),
                "approach": testing_data.get("approach", "TDD"),
                "quality": testing_data.get("quality_standards", "production-grade")
            })

    # Agent Templates (reference to discovery tool)
    agent_templates_priority = effective_priorities.get("agent_templates", 2)
    if agent_templates_priority == 2:  # IMPORTANT
        builder.add_important("agent_templates")
        builder.add_important_content("agent_templates", {
            "discovery_tool": "get_available_agents()",
            "note": "Use MCP tool to fetch agent details on-demand"
        })

    # === REFERENCE SECTION (Priority 3) ===

    # Vision Documents (summary only)
    vision_priority = effective_priorities.get("vision_documents", 4)
    if vision_priority > 0 and vision_priority != 4:  # Not excluded
        vision_depth = depth_config.get("vision_documents", "moderate")

        if product.vision_documents:
            async with self.db_manager.get_session_async() as session:
                from sqlalchemy import select
                from src.giljo_mcp.models.products import VisionDocument

                stmt = select(VisionDocument).where(
                    VisionDocument.product_id == product.id,
                    VisionDocument.tenant_key == product.tenant_key,
                    VisionDocument.is_active == True
                ).order_by(VisionDocument.display_order).limit(1)

                result = await session.execute(stmt)
                vision_doc = result.scalar_one_or_none()

                if vision_doc:
                    builder.add_reference("vision_documents")
                    builder.add_reference_content("vision_documents", {
                        "available": True,
                        "depth_setting": vision_depth,
                        "estimated_tokens": vision_doc.original_token_count or 0,
                        "summary": f"Vision document with {vision_doc.chunk_count or 0} chunks",
                        "when_to_fetch": "UX decisions, detailed specs needed",
                        "fetch_tool": "fetch_vision_document(page=N)"
                    })

    # 360 Memory (summary only)
    memory_priority = effective_priorities.get("memory_360", 3)
    if memory_priority > 0 and memory_priority != 4:  # Not excluded
        memory_depth = depth_config.get("memory_360", 5)

        if product.product_memory and "sequential_history" in product.product_memory:
            project_count = len(product.product_memory["sequential_history"])
            builder.add_reference("memory_360")
            builder.add_reference_content("memory_360", {
                "projects": project_count,
                "status": f"{project_count} completed projects in history",
                "fetch_tool": f"fetch_360_memory(limit={memory_depth})"
            })
        else:
            builder.add_reference("memory_360")
            builder.add_reference_content("memory_360", {
                "projects": 0,
                "status": "First project - no history",
                "fetch_tool": "fetch_360_memory()"
            })

    # Git History (summary only)
    git_priority = effective_priorities.get("git_history", 3)
    if git_priority > 0 and git_priority != 4:  # Not excluded
        git_depth = depth_config.get("git_history", 25)

        builder.add_reference("git_history")
        builder.add_reference_content("git_history", {
            "commits": git_depth,
            "fetch_tool": f"fetch_git_history(limit={git_depth})"
        })

    return builder.to_yaml()
```

**New Token Estimation Method:**
```python
def _estimate_yaml_tokens(self, yaml_content: str) -> int:
    """
    Estimate token count for YAML content.

    Handover 0347: More accurate than markdown estimation due to structure.

    Args:
        yaml_content: YAML-formatted string

    Returns:
        Estimated token count (1 token ≈ 4 characters)
    """
    return len(yaml_content) // 4
```

### Database Schema Impact

**No database changes required.**

This handover is pure business logic refactoring - no schema modifications, no migrations.

### API Changes

**No API endpoint changes required.**

The `generate_mission()` method signature remains unchanged. Only the internal format of the `mission` field changes from markdown to YAML.

**Metadata Change:**
```python
# New metadata field in response
{
    "mission": "YAML string here",
    "mission_format": "yaml",  # NEW - indicates YAML structure
    "estimated_tokens": 1500,  # Updated to reflect YAML token count
    # ... other fields unchanged
}
```

---

## Implementation Plan

### Phase 1: Test Setup (TDD First - 1 hour)

**Step 1.1: Create test file**
```
F:\GiljoAI_MCP\tests\unit\test_mission_planner_yaml_output.py
```

**Step 1.2: Write failing tests**

Test cases to implement:

1. **test_mission_planner_returns_yaml_format**
   - Generate mission for orchestrator
   - Assert `mission_format == "yaml"`
   - Assert mission field is valid YAML (parseable by PyYAML)

2. **test_yaml_mission_respects_field_priorities**
   - Generate mission with custom field priorities
   - Parse YAML and verify CRITICAL/IMPORTANT/REFERENCE sections
   - Assert excluded fields (priority=4) are not present

3. **test_yaml_mission_token_count_reduced**
   - Generate mission with full context
   - Assert estimated_tokens < 2000 (down from ~21,000)
   - Verify >90% token reduction

4. **test_yaml_structure_contains_required_fields**
   - Parse YAML output
   - Assert presence of:
     - `CRITICAL` section with product_core, tech_stack
     - `IMPORTANT` section with architecture, testing, agent_templates
     - `REFERENCE` section with vision_documents, memory_360, git_history

5. **test_yaml_mission_preserves_depth_config**
   - Generate mission with custom depth config
   - Parse YAML and verify depth settings in REFERENCE section
   - Assert `fetch_360_memory(limit=10)` when depth_config["memory_360"] = 10

**Step 1.3: Run tests (expect failures)**
```bash
pytest tests/unit/test_mission_planner_yaml_output.py -v
```

**Expected Outcome:**
- All tests fail (YAML not implemented yet)
- Test failures are descriptive and clear

---

### Phase 2: Implementation (2 hours)

**Step 2.1: Import YAMLContextBuilder**

File: `src/giljo_mcp/mission_planner.py`

Add import at top of `_build_context_with_priorities()`:
```python
from src.giljo_mcp.yaml_context_builder import YAMLContextBuilder
```

**Step 2.2: Initialize builder**

Replace markdown string initialization with:
```python
builder = YAMLContextBuilder()
```

**Step 2.3: Refactor CRITICAL section (Priority 1)**

Current code (lines ~1220-1280):
```python
# Markdown string concatenation
context = "## Product Core\n"
context += f"**Name**: {product.name}\n"
# ... etc
```

New code:
```python
# Product Core
product_core_priority = effective_priorities.get("product_core", 1)
if product_core_priority == 1:  # CRITICAL
    builder.add_critical("product_core")
    builder.add_critical_content("product_core", {
        "name": product.name,
        "description": product.description or "",
        "type": product.config_data.get("product_type", "Software") if product.config_data else "Software"
    })

# Tech Stack
tech_stack_priority = effective_priorities.get("tech_stack", 1)
if tech_stack_priority == 1:  # CRITICAL
    tech_stack_data = product.config_data.get("tech_stack", {}) if product.config_data else {}
    if tech_stack_data:
        builder.add_critical("tech_stack")
        builder.add_critical_content("tech_stack", {
            "languages": tech_stack_data.get("languages", []),
            "backend": tech_stack_data.get("backend_frameworks", []),
            "frontend": tech_stack_data.get("frontend_frameworks", []),
            "database": tech_stack_data.get("databases", {})
        })
```

**Step 2.4: Refactor IMPORTANT section (Priority 2)**

Current code (lines ~1300-1450):
```python
# Markdown sections for architecture, testing, etc.
```

New code:
```python
# Architecture (condensed)
architecture_priority = effective_priorities.get("architecture", 2)
if architecture_priority == 2:  # IMPORTANT
    arch_data = product.config_data.get("architecture", {}) if product.config_data else {}
    if arch_data:
        builder.add_important("architecture")
        builder.add_important_content("architecture", {
            "pattern": arch_data.get("pattern", "Unknown"),
            "api": arch_data.get("api_style", "REST"),
            "patterns": arch_data.get("design_patterns", []),
            "fetch_details": "fetch_architecture()"
        })

# Testing (condensed)
testing_priority = effective_priorities.get("testing", 2)
if testing_priority == 2:  # IMPORTANT
    testing_data = product.config_data.get("testing", {}) if product.config_data else {}
    if testing_data:
        builder.add_important("testing")
        builder.add_important_content("testing", {
            "target": testing_data.get("coverage_target", "80%"),
            "approach": testing_data.get("approach", "TDD"),
            "quality": testing_data.get("quality_standards", "production-grade")
        })

# Agent Templates (reference to discovery tool)
agent_templates_priority = effective_priorities.get("agent_templates", 2)
if agent_templates_priority == 2:  # IMPORTANT
    builder.add_important("agent_templates")
    builder.add_important_content("agent_templates", {
        "discovery_tool": "get_available_agents()",
        "note": "Use MCP tool to fetch agent details on-demand"
    })
```

**Step 2.5: Refactor REFERENCE section (Priority 3)**

Current code (lines ~1500-1680):
```python
# Full vision document chunks, full 360 memory, etc.
```

New code:
```python
# Vision Documents (summary only)
vision_priority = effective_priorities.get("vision_documents", 4)
if vision_priority > 0 and vision_priority != 4:  # Not excluded
    vision_depth = depth_config.get("vision_documents", "moderate")

    if product.vision_documents:
        async with self.db_manager.get_session_async() as session:
            from sqlalchemy import select
            from src.giljo_mcp.models.products import VisionDocument

            stmt = select(VisionDocument).where(
                VisionDocument.product_id == product.id,
                VisionDocument.tenant_key == product.tenant_key,
                VisionDocument.is_active == True
            ).order_by(VisionDocument.display_order).limit(1)

            result = await session.execute(stmt)
            vision_doc = result.scalar_one_or_none()

            if vision_doc:
                builder.add_reference("vision_documents")
                builder.add_reference_content("vision_documents", {
                    "available": True,
                    "depth_setting": vision_depth,
                    "estimated_tokens": vision_doc.original_token_count or 0,
                    "summary": f"Vision document with {vision_doc.chunk_count or 0} chunks",
                    "when_to_fetch": "UX decisions, detailed specs needed",
                    "fetch_tool": "fetch_vision_document(page=N)"
                })

# 360 Memory (summary only)
memory_priority = effective_priorities.get("memory_360", 3)
if memory_priority > 0 and memory_priority != 4:  # Not excluded
    memory_depth = depth_config.get("memory_360", 5)

    if product.product_memory and "sequential_history" in product.product_memory:
        project_count = len(product.product_memory["sequential_history"])
        builder.add_reference("memory_360")
        builder.add_reference_content("memory_360", {
            "projects": project_count,
            "status": f"{project_count} completed projects in history",
            "fetch_tool": f"fetch_360_memory(limit={memory_depth})"
        })
    else:
        builder.add_reference("memory_360")
        builder.add_reference_content("memory_360", {
            "projects": 0,
            "status": "First project - no history",
            "fetch_tool": "fetch_360_memory()"
        })

# Git History (summary only)
git_priority = effective_priorities.get("git_history", 3)
if git_priority > 0 and git_priority != 4:  # Not excluded
    git_depth = depth_config.get("git_history", 25)

    builder.add_reference("git_history")
    builder.add_reference_content("git_history", {
        "commits": git_depth,
        "fetch_tool": f"fetch_git_history(limit={git_depth})"
    })
```

**Step 2.6: Return YAML**

Replace:
```python
return context  # Returns markdown string
```

With:
```python
return builder.to_yaml()  # Returns YAML string
```

**Step 2.7: Add token estimation method**

Add new method to `MissionPlanner` class:
```python
def _estimate_yaml_tokens(self, yaml_content: str) -> int:
    """
    Estimate token count for YAML content.

    Handover 0347: More accurate than markdown estimation due to structure.

    Args:
        yaml_content: YAML-formatted string

    Returns:
        Estimated token count (1 token ≈ 4 characters)
    """
    return len(yaml_content) // 4
```

**Step 2.8: Update mission metadata**

Find the code in `generate_mission()` that sets mission metadata:
```python
# Current code
return {
    "mission": mission_text,
    "estimated_tokens": self._count_tokens(mission_text),
    # ... other fields
}
```

Replace with:
```python
# New code
return {
    "mission": mission_text,
    "mission_format": "yaml",  # NEW
    "estimated_tokens": self._estimate_yaml_tokens(mission_text),  # Updated
    # ... other fields
}
```

**Expected Outcome:**
- All markdown string building replaced with YAML builder calls
- Method returns valid YAML string
- Tests should start passing

---

### Phase 3: Verification & Testing (1 hour)

**Step 3.1: Run new tests**
```bash
pytest tests/unit/test_mission_planner_yaml_output.py -v
```

**Expected Result:**
- ✅ All tests pass
- Token count < 2000 (verified)
- YAML structure validated

**Step 3.2: Run existing tests**
```bash
pytest tests/unit/test_mission_planner.py -v
pytest tests/unit/test_mission_planner_priority.py -v
```

**Expected Result:**
- ✅ All existing tests pass (behavior unchanged from external perspective)
- May need minor adjustments if tests assert on markdown format

**Step 3.3: Integration test**

Create simple integration test in new file:
```python
# tests/unit/test_mission_planner_yaml_output.py

@pytest.mark.asyncio
async def test_end_to_end_yaml_mission_generation(db_session, sample_product, sample_project):
    """Test full mission generation flow with YAML output."""
    planner = MissionPlanner(db_manager=db_manager)

    mission_data = await planner.generate_mission(
        product_id=sample_product.id,
        project_id=sample_project.id,
        role="orchestrator",
        tenant_key="test_tenant"
    )

    # Verify metadata
    assert mission_data["mission_format"] == "yaml"
    assert mission_data["estimated_tokens"] < 2000

    # Verify YAML structure
    import yaml
    parsed = yaml.safe_load(mission_data["mission"])

    assert "CRITICAL" in parsed
    assert "IMPORTANT" in parsed
    assert "REFERENCE" in parsed

    # Verify product_core is in CRITICAL
    assert "product_core" in parsed["CRITICAL"]
    assert parsed["CRITICAL"]["product_core"]["name"] == sample_product.name

    # Verify fetch tools in REFERENCE
    assert "vision_documents" in parsed["REFERENCE"]
    assert "fetch_tool" in parsed["REFERENCE"]["vision_documents"]
```

**Step 3.4: Manual verification**

Run server and generate orchestrator mission:
```bash
python startup.py --dev
```

Check generated mission:
1. Create new project in UI
2. Launch orchestrator
3. Check agent job `mission` field in database:
   ```sql
   SELECT mission, mission_format, estimated_tokens
   FROM mcp_agent_jobs
   WHERE agent_type = 'orchestrator'
   ORDER BY created_at DESC
   LIMIT 1;
   ```
4. Verify:
   - `mission_format = 'yaml'`
   - `estimated_tokens < 2000`
   - Mission is valid YAML (copy to YAML validator)

**Expected Outcome:**
- All automated tests pass
- Manual verification confirms YAML output
- Token count verified < 2000

---

## Testing Requirements

### Unit Tests

**File:** `tests/unit/test_mission_planner_yaml_output.py`

**Required Tests:**

1. `test_mission_planner_returns_yaml_format()`
   - **Behavior**: Mission format metadata is set to "yaml"
   - **Coverage**: Response metadata structure

2. `test_yaml_mission_respects_field_priorities()`
   - **Behavior**: Priority filtering works with YAML builder
   - **Coverage**: Priority 1/2/3/4 logic

3. `test_yaml_mission_token_count_reduced()`
   - **Behavior**: YAML output achieves >90% token reduction
   - **Coverage**: Token estimation accuracy

4. `test_yaml_structure_contains_required_fields()`
   - **Behavior**: YAML contains all expected sections
   - **Coverage**: YAML structure validation

5. `test_yaml_mission_preserves_depth_config()`
   - **Behavior**: Depth configuration settings appear in REFERENCE section
   - **Coverage**: Depth config integration

6. `test_yaml_mission_handles_empty_product_data()`
   - **Behavior**: Gracefully handles products with minimal config_data
   - **Coverage**: Edge case handling

7. `test_yaml_mission_excludes_priority_4_fields()`
   - **Behavior**: Fields marked EXCLUDED (priority=4) do not appear
   - **Coverage**: Exclusion logic

**Coverage Target:** >85% for `_build_context_with_priorities()` method

### Integration Tests

**File:** `tests/integration/test_mission_planner_yaml_integration.py`

**Required Tests:**

1. `test_end_to_end_yaml_mission_generation()`
   - Full flow: product → project → mission
   - Verify database persistence of YAML mission
   - Verify mission is parseable

2. `test_yaml_mission_with_vision_documents()`
   - Product with uploaded vision documents
   - Verify REFERENCE section includes vision metadata

3. `test_yaml_mission_with_360_memory()`
   - Product with sequential project history
   - Verify REFERENCE section includes memory stats

**Coverage Target:** >80% for mission generation flow

### Manual Testing

**Test Procedure:**

1. **Setup:**
   - Fresh database: `python install.py`
   - Start server: `python startup.py --dev`
   - Create user account

2. **Create Product:**
   - Name: "Test Product YAML"
   - Upload vision document (test with chunking)
   - Configure tech stack (Python, FastAPI, Vue3)
   - Configure architecture (Microservices, REST)

3. **Create Project:**
   - Name: "YAML Mission Test"
   - Description: "Verify YAML mission generation"

4. **Launch Orchestrator:**
   - Click "Launch Project"
   - Wait for orchestrator job creation

5. **Verify Mission:**
   - Check database: `SELECT mission FROM mcp_agent_jobs WHERE agent_type = 'orchestrator' ORDER BY created_at DESC LIMIT 1;`
   - Copy mission field
   - Paste into YAML validator (https://www.yamllint.com/)
   - Verify structure:
     ```yaml
     CRITICAL:
       product_core:
         name: "Test Product YAML"
         description: "..."
         type: "Software"
       tech_stack:
         languages: ["Python"]
         backend: ["FastAPI"]
         frontend: ["Vue3"]
         database: {...}

     IMPORTANT:
       architecture:
         pattern: "Microservices"
         api: "REST"
         fetch_details: "fetch_architecture()"
       testing:
         target: "80%"
         approach: "TDD"
       agent_templates:
         discovery_tool: "get_available_agents()"

     REFERENCE:
       vision_documents:
         available: true
         depth_setting: "moderate"
         estimated_tokens: 12500
         fetch_tool: "fetch_vision_document(page=N)"
       memory_360:
         projects: 0
         status: "First project - no history"
         fetch_tool: "fetch_360_memory()"
       git_history:
         commits: 25
         fetch_tool: "fetch_git_history(limit=25)"
     ```

6. **Verify Token Count:**
   - Check `estimated_tokens` field in database
   - Should be ~1,200-1,800 tokens (down from ~21,000)

**Expected Results:**
- ✅ YAML validates without errors
- ✅ All CRITICAL/IMPORTANT/REFERENCE sections present
- ✅ Token count < 2000
- ✅ Fetch tools referenced in REFERENCE section
- ✅ Depth config values appear in fetch tool parameters

---

## Dependencies and Blockers

### Dependencies

**CRITICAL Dependency:**
- ✅ **Handover 0347a** (YAMLContextBuilder) MUST be completed first
  - Class: `src/giljo_mcp/yaml_context_builder.py`
  - Methods: `add_critical()`, `add_important()`, `add_reference()`, `to_yaml()`
  - Tests: `tests/unit/test_yaml_context_builder.py`

**Soft Dependency:**
- ✅ **Handover 0346** (Depth Config Field Standardization) - already completed
  - Standardizes `vision_documents` depth field

### Known Blockers

**None identified** as of 2025-12-14.

Potential blockers if 0347a incomplete:
- Missing YAMLContextBuilder class → implement 0347a first
- Import errors → verify 0347a tests pass

---

## Success Criteria

### Definition of Done

**Code:**
- ✅ `_build_context_with_priorities()` refactored to use YAMLContextBuilder
- ✅ `_estimate_yaml_tokens()` method added
- ✅ `generate_mission()` returns `mission_format: "yaml"` metadata
- ✅ All markdown string concatenation removed

**Tests:**
- ✅ All new unit tests pass (7 tests in `test_mission_planner_yaml_output.py`)
- ✅ All existing unit tests pass (no regressions)
- ✅ Integration tests pass (3 tests)
- ✅ Manual test procedure executed successfully

**Validation:**
- ✅ Generated missions are valid YAML (parseable by PyYAML)
- ✅ Token count reduced to ~1,500 (>90% reduction from ~21,000)
- ✅ CRITICAL/IMPORTANT/REFERENCE sections structured correctly
- ✅ Field priority filtering works (priority 4 excluded)
- ✅ Depth config values propagate to REFERENCE section

**Documentation:**
- ✅ Docstring for `_build_context_with_priorities()` updated with Handover 0347 note
- ✅ Docstring for `_estimate_yaml_tokens()` added
- ✅ This handover document updated with completion status

**Performance:**
- ✅ Mission generation time < 200ms (no performance regression)
- ✅ Database query count unchanged

### Verification Steps

**Automated Verification:**
```bash
# Run all MissionPlanner tests
pytest tests/unit/test_mission_planner*.py -v --cov=src.giljo_mcp.mission_planner --cov-report=term

# Verify coverage >85%
pytest tests/unit/test_mission_planner_yaml_output.py --cov=src.giljo_mcp.mission_planner --cov-report=html
```

**Manual Verification:**
1. Create product with full config (tech stack, architecture, testing)
2. Upload vision document (verify chunking)
3. Create project and launch orchestrator
4. Query database for mission:
   ```sql
   SELECT
     mission_format,
     estimated_tokens,
     LENGTH(mission) as mission_length,
     mission
   FROM mcp_agent_jobs
   WHERE agent_type = 'orchestrator'
   ORDER BY created_at DESC
   LIMIT 1;
   ```
5. Verify:
   - `mission_format = 'yaml'`
   - `estimated_tokens < 2000`
   - `mission` is valid YAML

**Token Count Verification:**
```python
# Quick script to verify token reduction
import yaml
from src.giljo_mcp.mission_planner import MissionPlanner

planner = MissionPlanner(db_manager)
mission_data = await planner.generate_mission(product_id, project_id, "orchestrator", tenant_key)

yaml_tokens = mission_data["estimated_tokens"]
print(f"YAML tokens: {yaml_tokens}")
print(f"Reduction: {((21000 - yaml_tokens) / 21000 * 100):.1f}%")

# Expected output:
# YAML tokens: ~1500
# Reduction: ~93%
```

---

## Rollback Plan

### If YAML Implementation Fails

**Immediate Rollback:**
```bash
# Revert changes
git checkout src/giljo_mcp/mission_planner.py

# Verify tests pass
pytest tests/unit/test_mission_planner.py -v
```

**Partial Rollback (if tests fail):**
```python
# Keep YAMLContextBuilder but add fallback in _build_context_with_priorities()

async def _build_context_with_priorities(self, ...):
    try:
        # New YAML implementation
        from src.giljo_mcp.yaml_context_builder import YAMLContextBuilder
        builder = YAMLContextBuilder()
        # ... YAML logic
        return builder.to_yaml()
    except Exception as e:
        logger.error(f"YAML generation failed: {e}, falling back to markdown")
        # Fall back to old markdown implementation
        return self._build_context_markdown(product, project, ...)  # Old method
```

**Fallback Configuration:**
```python
# Add feature flag in config.yaml
mission_output:
  format: "yaml"  # Options: "yaml" | "markdown"
  fallback_enabled: true
```

### Data Impact Assessment

**No data loss risk:**
- Mission field is VARCHAR/TEXT - accepts both markdown and YAML
- `mission_format` is new metadata field (optional)
- Existing missions in database are not modified

**Safe rollback:**
- Old markdown missions still readable
- New YAML missions backward compatible (agents can parse both)

---

## Additional Resources

### Documentation

**Primary Reference:**
- [Handover 0347](F:\GiljoAI_MCP\handovers\0347_mission_response_yaml_restructuring.md) - Full YAML restructuring spec

**Related Handovers:**
- [Handover 0346](F:\GiljoAI_MCP\handovers\0346_depth_config_field_standardization.md) - Depth config prerequisite
- [Handover 0312-0316](F:\GiljoAI_MCP\handovers\completed\0300_EXECUTION_ROADMAP_COMPLETE.md) - Context Management v2.0
- [Handover 0246a-c](F:\GiljoAI_MCP\CLAUDE.md#orchestrator-workflow-pipeline) - Thin-client architecture

**Architecture Docs:**
- [docs/ORCHESTRATOR.md](F:\GiljoAI_MCP\docs\ORCHESTRATOR.md) - Orchestrator workflow
- [docs/SERVICES.md](F:\GiljoAI_MCP\docs\SERVICES.md) - Service layer patterns

### Code References

**Key Files:**
```
src/giljo_mcp/mission_planner.py             # Primary modification
src/giljo_mcp/yaml_context_builder.py        # Dependency (0347a)
tests/unit/test_mission_planner_priority.py  # Existing priority tests
```

**Related MCP Tools:**
```
src/giljo_mcp/tools/fetch_product_context.py    # Context fetching
src/giljo_mcp/tools/fetch_vision_document.py    # Vision chunking
src/giljo_mcp/tools/fetch_360_memory.py         # Memory retrieval
```

### External Resources

**YAML Specification:**
- [YAML 1.2 Spec](https://yaml.org/spec/1.2/spec.html)
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)

**Token Estimation:**
- [OpenAI Tokenizer](https://platform.openai.com/tokenizer) - Verify token counts
- [tiktoken Library](https://github.com/openai/tiktoken) - Precise token counting

**YAML Validators:**
- [YAMLLint](https://www.yamllint.com/) - Online validator
- [JSON-to-YAML Converter](https://www.json2yaml.com/) - Format comparison

---

## TDD Principles Reminder

**This handover MUST follow Test-Driven Development:**

1. ✅ **Write the test FIRST** (it should fail initially)
   - Create `test_mission_planner_yaml_output.py`
   - Write all 7 unit tests
   - Run tests → expect failures

2. ✅ **Implement minimal code to make test pass**
   - Refactor `_build_context_with_priorities()` incrementally
   - Run tests after each section (CRITICAL → IMPORTANT → REFERENCE)
   - Fix failures before moving to next section

3. ✅ **Refactor if needed**
   - Extract common patterns (e.g., priority checking logic)
   - Optimize YAML structure for token efficiency
   - Run tests to ensure no regression

4. ✅ **Test should focus on BEHAVIOR** (what the code does), not IMPLEMENTATION
   - ✅ Good: `assert mission_data["mission_format"] == "yaml"`
   - ❌ Bad: `assert isinstance(builder, YAMLContextBuilder)`

5. ✅ **Use descriptive test names**
   - ✅ Good: `test_yaml_mission_respects_field_priorities`
   - ❌ Bad: `test_priorities`

6. ✅ **Avoid testing internal implementation details**
   - ✅ Good: Test that YAML output is valid and contains expected sections
   - ❌ Bad: Test that `builder.add_critical()` was called exactly 2 times

---

## Progress Updates

### 2025-12-14 - Documentation Manager (Planning)
**Status:** Not Started
**Work Done:**
- Created handover document (0347b)
- Analyzed MissionPlanner implementation structure
- Defined test requirements (7 unit tests, 3 integration tests)
- Mapped refactoring steps (CRITICAL → IMPORTANT → REFERENCE)

**Next Steps:**
- Assign to TDD Implementor
- Wait for 0347a (YAMLContextBuilder) completion
- Begin Phase 1 (Test Setup) once 0347a is merged

**Questions:**
- None

---

**Ready for Implementation:** Once Handover 0347a completes, this is ready for TDD Implementor.

**Estimated Timeline:**
- Test setup: 1 hour
- Implementation: 2 hours
- Verification: 1 hour
- **Total: 4 hours**

**Token Impact:**
- Current: ~21,000 tokens per orchestrator mission
- Target: ~1,500 tokens per orchestrator mission
- **Reduction: 93%**
