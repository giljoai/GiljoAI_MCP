# Handover: 0347 - Mission Response YAML Restructuring

**Date:** 2025-12-12
**From Agent:** Documentation Manager
**To Agent:** backend-integration-tester
**Priority:** High
**Estimated Complexity:** 8-10 hours
**Status:** Ready for Implementation

---

## Task Summary

The `get_orchestrator_instructions` MCP tool returns a `mission` field containing ~21,000 tokens of markdown-concatenated context. This is inefficient, hard to parse, and wastes tokens on content that could be fetched on-demand.

**Root Cause:** Mission field is a markdown blob that:
1. Inlines all context (vision docs, memory, git history) regardless of priority
2. Buries priority information in section headers (e.g., "## CRITICAL: Product Context")
3. Forces Claude to parse unstructured text to find relevant context
4. Includes 15K+ token vision documents even when user sets "light" depth

**Solution:** Restructure mission field as YAML with explicit priority framing:
- **CRITICAL** section (Priority 1) - Inline essential context (~350 tokens)
- **IMPORTANT** section (Priority 2) - Condensed guidance (~200 tokens)
- **REFERENCE** section (Priority 3) - Summaries with fetch tool pointers (~150 tokens)

**Token Impact:** 93% reduction (21,000 → ~1,500 tokens)

---

## DEPENDENCY - MUST COMPLETE FIRST

**This handover depends on 0346 (Depth Config Field Standardization) being completed first.**

Without 0346, the `vision_documents` depth setting will continue to be ignored due to field name mismatch (`vision_chunking` vs `vision_documents`). Implementing 0347 before 0346 will result in YAML output still containing full vision documents.

**Verification:** Before starting 0347, confirm:
```bash
grep -r "vision_chunking" src/ api/
# Should return NOTHING if 0346 is complete
```

---

## Technical Details

### Current Flow (Markdown Blob)

```
MissionPlanner._build_context_with_priorities()
  ↓
Returns: 21,000 token markdown string
  ↓
orchestration.py: get_orchestrator_instructions()
  ↓
Response: { "mission": "## CRITICAL...\n\n## IMPORTANT...\n\n[15K vision doc]..." }
  ↓
Claude Code: Must parse unstructured markdown to find priorities
```

### Proposed Flow (YAML Structure)

```
MissionPlanner._build_context_with_priorities()
  ↓
Returns: YAML dict with priority sections
  ↓
YAMLContextBuilder.to_yaml()
  ↓
orchestration.py: get_orchestrator_instructions()
  ↓
Response: { "mission": "priorities:\n  CRITICAL:\n    - product_core...", "format": "yaml" }
  ↓
Claude Code: Parse YAML → Explicit priority map → Fetch on-demand
```

---

## Proposed YAML Structure

### Example Output (TinyContacts project)

```yaml
# ═══════════════════════════════════════════════════════════════
# CONTEXT PRIORITY MAP - Read this first
# ═══════════════════════════════════════════════════════════════
priorities:
  CRITICAL:  # Non-negotiable. Always follow.
    - product_core
    - tech_stack
  IMPORTANT: # Guidance. Follow unless conflicts with CRITICAL.
    - architecture
    - testing
    - agent_templates
  REFERENCE: # On-demand. Fetch only when needed.
    - vision_documents
    - memory_360
    - git_history

# ═══════════════════════════════════════════════════════════════
# CRITICAL (Priority 1) - Always inline, always read
# ═══════════════════════════════════════════════════════════════
product_core:
  name: "TinyContacts"
  type: "Contact management application"
  target: ["freelancers", "consultants", "small business"]
  key_features:
    - Photo uploads with auto-optimization
    - Important dates tracking
    - Tag-based organization
    - Fuzzy search

tech_stack:
  languages: [Python 3.11+, TypeScript 5.0+]
  backend: [FastAPI 0.104+, SQLAlchemy 2.0+, Pydantic 2.0+]
  frontend: [React 18.2+, Vite 5.0+, Tailwind CSS 3.3+, TanStack Query 5.0+]
  database:
    dev: SQLite 3.35+
    prod: PostgreSQL 13+

# ═══════════════════════════════════════════════════════════════
# IMPORTANT (Priority 2) - Inline but condensed
# ═══════════════════════════════════════════════════════════════
architecture:
  pattern: "Modular monolith with service layer"
  api: "REST + OpenAPI 3.0"
  patterns: [Repository, DI, MVC, Observer]
  fetch_details: fetch_architecture()

testing:
  target: 80% coverage
  approach: TDD
  quality: production-grade

agent_templates:
  available: [analyzer, implementer, documenter, tester, reviewer]
  max_enabled: 8
  discovery_tool: get_available_agents()

# ═══════════════════════════════════════════════════════════════
# REFERENCE (Priority 3) - Summary only, fetch on-demand
# ═══════════════════════════════════════════════════════════════
vision_documents:
  available: true
  depth_setting: moderate
  estimated_tokens: 12500
  summary: "40K word product vision - UX, specs, benefits, roadmap"
  when_to_fetch: "UX decisions, detailed specs needed"
  fetch_tool: fetch_vision_document(page=N)

memory_360:
  projects: 0
  status: "First project - no history"
  fetch_tool: fetch_360_memory()

git_history:
  commits: 25
  fetch_tool: fetch_git_history(limit=25)
```

---

## Files to Modify

### New Files (Create)

| File | Purpose |
|------|---------|
| `src/giljo_mcp/yaml_context_builder.py` | YAML context builder utility class |
| `tests/services/test_yaml_context_builder.py` | Unit tests for YAML builder |

### Modified Files (8 files)

| File | Line(s) | Change |
|------|---------|--------|
| `src/giljo_mcp/mission_planner.py` | 1217-1700 | Replace `_build_context_with_priorities()` markdown output with YAML builder calls |
| `src/giljo_mcp/tools/orchestration.py` | 1610-1678 | Add `format: yaml` to response metadata |
| `src/giljo_mcp/thin_prompt_generator.py` | 173 | Update default format to YAML |
| `api/endpoints/projects.py` | Various | Update response schema to include format field |
| `tests/tools/test_orchestration.py` | Various | Update assertions for YAML output |
| `tests/integration/test_mission_generation.py` | Various | Add YAML parsing validation |

---

## Implementation Plan

### Phase 1: TDD - Create YAML Builder Utility (2 hours)

**1.1 Write failing tests**

Create `tests/services/test_yaml_context_builder.py`:

```python
"""Handover 0347: YAML Context Builder Tests"""

import pytest
from src.giljo_mcp.yaml_context_builder import YAMLContextBuilder


class TestYAMLContextBuilder:
    def test_priority_map_section(self):
        builder = YAMLContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical("tech_stack")
        builder.add_important("architecture")
        builder.add_reference("vision_documents")

        yaml_output = builder.to_yaml()

        assert "priorities:" in yaml_output
        assert "CRITICAL:" in yaml_output
        assert "- product_core" in yaml_output
        assert "- tech_stack" in yaml_output
        assert "IMPORTANT:" in yaml_output
        assert "- architecture" in yaml_output
        assert "REFERENCE:" in yaml_output
        assert "- vision_documents" in yaml_output

    def test_critical_section_inline_content(self):
        builder = YAMLContextBuilder()
        builder.add_critical_content("product_core", {
            "name": "TinyContacts",
            "type": "Contact management",
            "features": ["photos", "dates", "tags"]
        })

        yaml_output = builder.to_yaml()

        assert "product_core:" in yaml_output
        assert "name: \"TinyContacts\"" in yaml_output
        assert "type: \"Contact management\"" in yaml_output
        assert "features:" in yaml_output

    def test_important_section_condensed_content(self):
        builder = YAMLContextBuilder()
        builder.add_important_content("architecture", {
            "pattern": "Modular monolith",
            "api": "REST + OpenAPI",
            "fetch_details": "fetch_architecture()"
        })

        yaml_output = builder.to_yaml()

        assert "architecture:" in yaml_output
        assert "pattern: \"Modular monolith\"" in yaml_output
        assert "fetch_details: fetch_architecture()" in yaml_output

    def test_reference_section_summary_only(self):
        builder = YAMLContextBuilder()
        builder.add_reference_content("vision_documents", {
            "available": True,
            "depth_setting": "moderate",
            "estimated_tokens": 12500,
            "summary": "40K word product vision",
            "fetch_tool": "fetch_vision_document(page=N)"
        })

        yaml_output = builder.to_yaml()

        assert "vision_documents:" in yaml_output
        assert "available: true" in yaml_output
        assert "estimated_tokens: 12500" in yaml_output
        assert "fetch_tool: fetch_vision_document(page=N)" in yaml_output

    def test_yaml_is_valid_parseable(self):
        import yaml

        builder = YAMLContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {"name": "Test"})

        yaml_output = builder.to_yaml()

        # Should not raise exception
        parsed = yaml.safe_load(yaml_output)

        assert "priorities" in parsed
        assert "product_core" in parsed

    def test_token_count_estimate(self):
        builder = YAMLContextBuilder()
        builder.add_critical_content("product_core", {"name": "Test"})
        builder.add_critical_content("tech_stack", {"languages": ["Python"]})

        yaml_output = builder.to_yaml()
        estimated_tokens = builder.estimate_tokens()

        # 1 token ≈ 4 characters
        expected = len(yaml_output) // 4

        assert estimated_tokens == expected
        assert estimated_tokens < 2000  # Should be well under budget
```

Run: `pytest tests/services/test_yaml_context_builder.py -v` → EXPECT FAILURE

**1.2 Implement YAML Builder**

Create `src/giljo_mcp/yaml_context_builder.py`:

```python
"""
YAML Context Builder for GiljoAI MCP Orchestrator Missions

Handover 0347: Restructures mission field from markdown blob to structured YAML
with explicit priority framing.

Purpose:
- Reduce mission tokens from ~21,000 to ~1,500 (93% reduction)
- Make priorities explicit upfront (CRITICAL/IMPORTANT/REFERENCE)
- Enable fetch-on-demand for reference content
- Improve Claude Code parsing efficiency

Usage:
    builder = YAMLContextBuilder()

    # Add priority declarations
    builder.add_critical("product_core")
    builder.add_important("architecture")
    builder.add_reference("vision_documents")

    # Add content
    builder.add_critical_content("product_core", {"name": "TinyContacts", ...})
    builder.add_reference_content("vision_documents", {"summary": "...", "fetch_tool": "..."})

    # Generate YAML
    yaml_output = builder.to_yaml()
"""

import yaml
from typing import Any, Dict, List


class YAMLContextBuilder:
    """
    Builds structured YAML context with priority framing.

    Organizes context into three priority tiers:
    - CRITICAL (Priority 1): Always inline, always read (~350 tokens)
    - IMPORTANT (Priority 2): Condensed guidance (~200 tokens)
    - REFERENCE (Priority 3): Summaries with fetch pointers (~150 tokens)
    """

    def __init__(self):
        self.critical_fields: List[str] = []
        self.important_fields: List[str] = []
        self.reference_fields: List[str] = []

        self.critical_content: Dict[str, Any] = {}
        self.important_content: Dict[str, Any] = {}
        self.reference_content: Dict[str, Any] = {}

    def add_critical(self, field_name: str) -> None:
        """Declare a field as CRITICAL priority (always inline)."""
        if field_name not in self.critical_fields:
            self.critical_fields.append(field_name)

    def add_important(self, field_name: str) -> None:
        """Declare a field as IMPORTANT priority (condensed)."""
        if field_name not in self.important_fields:
            self.important_fields.append(field_name)

    def add_reference(self, field_name: str) -> None:
        """Declare a field as REFERENCE priority (summary + fetch tool)."""
        if field_name not in self.reference_fields:
            self.reference_fields.append(field_name)

    def add_critical_content(self, field_name: str, content: Any) -> None:
        """Add content for a CRITICAL field (full detail)."""
        self.critical_content[field_name] = content

    def add_important_content(self, field_name: str, content: Any) -> None:
        """Add content for an IMPORTANT field (condensed)."""
        self.important_content[field_name] = content

    def add_reference_content(self, field_name: str, content: Any) -> None:
        """Add content for a REFERENCE field (summary only)."""
        self.reference_content[field_name] = content

    def to_yaml(self) -> str:
        """
        Generate YAML string with priority framing.

        Returns:
            Formatted YAML with priority map and tiered content sections.
        """
        output_parts = []

        # Header banner
        output_parts.append("# " + "=" * 67)
        output_parts.append("# CONTEXT PRIORITY MAP - Read this first")
        output_parts.append("# " + "=" * 67)

        # Priority map
        priority_map = {
            "priorities": {
                "CRITICAL": self.critical_fields if self.critical_fields else [],
                "IMPORTANT": self.important_fields if self.important_fields else [],
                "REFERENCE": self.reference_fields if self.reference_fields else []
            }
        }

        output_parts.append(yaml.dump(priority_map, default_flow_style=False, sort_keys=False))

        # CRITICAL section
        if self.critical_content:
            output_parts.append("# " + "=" * 67)
            output_parts.append("# CRITICAL (Priority 1) - Always inline, always read")
            output_parts.append("# " + "=" * 67)
            output_parts.append(yaml.dump(self.critical_content, default_flow_style=False, sort_keys=False))

        # IMPORTANT section
        if self.important_content:
            output_parts.append("# " + "=" * 67)
            output_parts.append("# IMPORTANT (Priority 2) - Inline but condensed")
            output_parts.append("# " + "=" * 67)
            output_parts.append(yaml.dump(self.important_content, default_flow_style=False, sort_keys=False))

        # REFERENCE section
        if self.reference_content:
            output_parts.append("# " + "=" * 67)
            output_parts.append("# REFERENCE (Priority 3) - Summary only, fetch on-demand")
            output_parts.append("# " + "=" * 67)
            output_parts.append(yaml.dump(self.reference_content, default_flow_style=False, sort_keys=False))

        return "\n".join(output_parts)

    def estimate_tokens(self) -> int:
        """
        Estimate token count for YAML output.

        Uses 1 token ≈ 4 characters heuristic.

        Returns:
            Estimated token count
        """
        yaml_output = self.to_yaml()
        return len(yaml_output) // 4
```

Run tests: `pytest tests/services/test_yaml_context_builder.py -v` → EXPECT PASS

---

### Phase 2: Update MissionPlanner (4 hours)

**2.1 Refactor `_build_context_with_priorities()` method**

File: `src/giljo_mcp/mission_planner.py`

Replace markdown string building with YAML builder calls:

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

**2.2 Update token estimation**

Add method to MissionPlanner:

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

---

### Phase 3: Update Orchestration Service (1 hour)

File: `src/giljo_mcp/tools/orchestration.py`

**3.1 Add format metadata to response**

Line 1673-1687, update return statement:

```python
return {
    "orchestrator_id": orchestrator_id,
    "project_id": str(project.id),
    "project_name": project.name,
    "project_description": project.description or "",
    "mission": condensed_mission,
    "mission_format": "yaml",  # NEW: Handover 0347
    "context_budget": orchestrator.context_budget or 150000,
    "context_used": orchestrator.context_used or 0,
    "agent_discovery_tool": "get_available_agents()",
    "field_priorities": field_priorities,
    "token_reduction_applied": bool(field_priorities),
    "estimated_tokens": estimated_tokens,
    "instance_number": orchestrator.instance_number or 1,
    "thin_client": True,
}
```

---

### Phase 4: Testing (3 hours)

**4.1 Unit Tests**

Update `tests/tools/test_orchestration.py`:

```python
@pytest.mark.asyncio
async def test_get_orchestrator_instructions_returns_yaml(db_manager, sample_orchestrator):
    """Handover 0347: Mission field should be valid YAML."""
    import yaml

    response = await get_orchestrator_instructions(
        orchestrator_id=str(sample_orchestrator.job_id),
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    assert response["mission_format"] == "yaml"
    assert "mission" in response

    # Should be parseable YAML
    parsed = yaml.safe_load(response["mission"])

    assert "priorities" in parsed
    assert "CRITICAL" in parsed["priorities"]
    assert "IMPORTANT" in parsed["priorities"]
    assert "REFERENCE" in parsed["priorities"]

@pytest.mark.asyncio
async def test_yaml_mission_token_count(db_manager, sample_orchestrator):
    """Handover 0347: YAML mission should be <2,000 tokens."""
    response = await get_orchestrator_instructions(
        orchestrator_id=str(sample_orchestrator.job_id),
        tenant_key=sample_orchestrator.tenant_key,
        db_manager=db_manager
    )

    estimated_tokens = response["estimated_tokens"]

    # Should be dramatically reduced from ~21,000
    assert estimated_tokens < 2000, f"Expected <2K tokens, got {estimated_tokens}"
```

**4.2 Integration Tests**

Create `tests/integration/test_yaml_mission_generation.py`:

```python
"""Handover 0347: Integration tests for YAML mission generation."""

import pytest
import yaml
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


@pytest.mark.asyncio
async def test_full_yaml_mission_generation(db_manager, sample_product, sample_project):
    """Test complete YAML mission generation workflow."""
    planner = MissionPlanner(db_manager)

    field_priorities = {
        "product_core": 1,
        "tech_stack": 1,
        "architecture": 2,
        "testing": 2,
        "vision_documents": 3,
        "memory_360": 3,
        "git_history": 3
    }

    depth_config = {
        "vision_documents": "moderate",
        "memory_360": 5,
        "git_history": 25
    }

    mission_yaml = await planner._build_context_with_priorities(
        product=sample_product,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config=depth_config
    )

    # Validate YAML structure
    parsed = yaml.safe_load(mission_yaml)

    assert "priorities" in parsed
    assert "product_core" in parsed
    assert "tech_stack" in parsed

    # Validate token count
    estimated_tokens = len(mission_yaml) // 4
    assert estimated_tokens < 2000

@pytest.mark.asyncio
async def test_yaml_mission_with_vision_summary(db_manager, product_with_vision, sample_project):
    """Vision documents should be summarized, not inlined."""
    planner = MissionPlanner(db_manager)

    field_priorities = {"vision_documents": 3}  # REFERENCE
    depth_config = {"vision_documents": "moderate"}

    mission_yaml = await planner._build_context_with_priorities(
        product=product_with_vision,
        project=sample_project,
        field_priorities=field_priorities,
        depth_config=depth_config
    )

    parsed = yaml.safe_load(mission_yaml)

    # Should have vision_documents as reference
    assert "vision_documents" in parsed
    assert "fetch_tool" in parsed["vision_documents"]
    assert "summary" in parsed["vision_documents"]

    # Should NOT have full vision content inlined
    assert len(mission_yaml) < 5000  # Much smaller than full 21K
```

---

## Success Criteria

- [ ] All unit tests pass (YAMLContextBuilder)
- [ ] All integration tests pass (mission generation)
- [ ] Mission field contains valid YAML (parseable by PyYAML)
- [ ] Priorities declared at top of YAML output
- [ ] CRITICAL content inline (~350 tokens)
- [ ] IMPORTANT content condensed (~200 tokens)
- [ ] REFERENCE content summarized with fetch tools (~150 tokens)
- [ ] Total mission tokens < 2,000 (down from 21,000)
- [ ] `mission_format: yaml` field in response
- [ ] No references to old markdown structure remain
- [ ] Coverage >80% for new code
- [ ] E2E: Orchestrator can parse YAML and fetch context on-demand

---

## Testing Requirements

### Unit Tests

**YAMLContextBuilder:**
- [ ] `test_priority_map_section` - Priority declarations
- [ ] `test_critical_section_inline_content` - CRITICAL content structure
- [ ] `test_important_section_condensed_content` - IMPORTANT content structure
- [ ] `test_reference_section_summary_only` - REFERENCE content structure
- [ ] `test_yaml_is_valid_parseable` - PyYAML validation
- [ ] `test_token_count_estimate` - Token estimation accuracy

**MissionPlanner:**
- [ ] `test_build_context_returns_yaml` - Output format validation
- [ ] `test_yaml_token_reduction` - Token count <2K
- [ ] `test_vision_documents_summarized` - Vision not inlined

### Integration Tests

- [ ] `test_full_yaml_mission_generation` - Complete workflow
- [ ] `test_yaml_mission_with_vision_summary` - Vision summarization
- [ ] `test_orchestrator_instructions_yaml_format` - MCP tool response

### Manual E2E Tests

1. Launch project with vision document
2. Fetch orchestrator instructions via MCP tool
3. Verify YAML structure in response
4. Confirm token count <2,000
5. Call `fetch_vision_document()` to retrieve full content

---

## Token Impact Analysis

| Component | Current (Markdown) | Proposed (YAML) | Savings |
|-----------|-------------------|-----------------|---------|
| Product core | ~500 | ~200 | 60% |
| Tech stack | ~400 | ~150 | 62% |
| Architecture | ~1,500 | ~100 | 93% |
| Testing | ~300 | ~50 | 83% |
| Vision doc | ~15,000 | ~100 (summary) | 99% |
| 360 Memory | ~500 | ~50 | 90% |
| Git History | ~800 | ~50 | 94% |
| Agent Templates | ~2,000 | ~100 | 95% |
| **TOTAL** | **~21,000** | **~1,500** | **93%** |

**Impact:**
- Orchestrator startup: Faster context loading
- Token budget: More room for actual work
- Parsing: Structured YAML vs unstructured markdown
- Maintainability: Clear priority separation

---

## Dependencies and Blockers

**Dependencies:**
- **0346 (Depth Config Field Standardization)** - MUST COMPLETE FIRST
  - Without 0346, `vision_documents` depth will be ignored
  - YAML will contain full vision doc even when user selects "light"

**Blockers:** None (after 0346 complete)

---

## Rollback Plan

If YAML format causes issues:

1. **Immediate rollback:**
   ```bash
   git revert HEAD
   ```

2. **Restore markdown output:**
   - Revert `mission_planner.py` changes
   - Remove `yaml_context_builder.py`
   - Restore old `_build_context_with_priorities()` method

3. **Database:** No schema changes - rollback is clean

4. **Clients:** Add backward compatibility:
   ```python
   if response.get("mission_format") == "yaml":
       # Parse YAML
   else:
       # Parse markdown (fallback)
   ```

---

## Additional Resources

**Related Handovers:**
- 0346: Depth Config Field Standardization (PREREQUISITE)
- 0345e: Sumy Compression Levels (vision summarization)
- 0314: Depth Controls Implementation
- 0246c: Dynamic Agent Discovery (reduced agent template inlining)
- 0283: Context Management v2.0 (field priorities and depth)

**Documentation:**
- YAML spec: https://yaml.org/spec/1.2/spec.html
- PyYAML docs: https://pyyaml.org/wiki/PyYAMLDocumentation
- Context Management v2.0: `docs/CONTEXT_MANAGEMENT_V2.md`

**Code References:**
- Current mission builder: `src/giljo_mcp/mission_planner.py:1217`
- MCP tool response: `src/giljo_mcp/tools/orchestration.py:1673`
- Priority framing: `src/giljo_mcp/mission_planner.py:1170`

---

## Recommended Sub-Agent

**backend-integration-tester** - This task requires:
- Service layer modification (MissionPlanner)
- MCP tool response format changes (orchestration.py)
- New utility class creation (YAMLContextBuilder)
- Comprehensive unit and integration testing
- Token estimation validation
- E2E workflow verification

The integration tester specializes in service-layer changes with testing coverage.

---

## Migration Notes

**For Future Orchestrators:**
- Claude Code will receive YAML-formatted missions
- Priorities are explicit (no parsing markdown headers)
- Reference content fetched on-demand via MCP tools
- Token budget is 93% more efficient

**For Existing Code:**
- No breaking changes to database schema
- Response format adds `mission_format` field
- Clients can add YAML parser (PyYAML available)
- Backward compatibility possible via format detection

---

## Current Implementation Reference

**IMPORTANT**: This section provides exact code context so a fresh agent can work without exploring the codebase.

### MissionPlanner._build_context_with_priorities() (Line 1217)

Current implementation returns a markdown blob by appending strings to `context_sections`:

```python
# src/giljo_mcp/mission_planner.py:1217-1366 (excerpt)

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

    Returns:
        Formatted context string with priority-based and depth-based filtering.
        # <-- THIS IS THE PROBLEM: Returns unstructured markdown string
    """
    # Default depth configuration
    if depth_config is None:
        depth_config = {
            "memory_360": 5,
            "git_history": 20,
            "agent_templates": "full",
        }

    context_sections = []  # <-- Collects markdown strings
    total_tokens = 0

    # === Product Name/Description ===
    product_core_priority = effective_priorities.get("product_core", 1)

    if product_core_priority != 4:  # Not excluded
        product_content = f"**Name**: {product.name}"
        if product.description:
            product_content += f"\n**Description**: {product.description}"

        # Apply priority framing (adds "## CRITICAL: ..." header)
        framed_product = self._apply_priority_framing(
            section_name="Product Context",
            content=product_content,
            priority=product_core_priority,
        )

        if framed_product:
            context_sections.append(framed_product)  # <-- Appends markdown

    # ... similar pattern for tech_stack, architecture, vision_documents, etc.

    return "\n\n".join(context_sections)  # <-- Returns ~21K token markdown blob
```

### Key Problem Points

| Line | Issue |
|------|-------|
| 1333 | `context_sections = []` - Uses list of strings, not structured data |
| 1347 | `_apply_priority_framing()` - Wraps content in markdown headers |
| End | `"\n\n".join(context_sections)` - Returns concatenated markdown |

### Model Schemas (for test fixtures)

**Product** (`src/giljo_mcp/models/products.py:33`):
```python
class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_path = Column(String(500), nullable=True)
    quality_standards = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    config_data = Column(JSON, default=dict)  # Contains tech_stack, architecture
    product_memory = Column(JSON, default=dict)  # Contains 360 memory

    # Relationships
    vision_documents = relationship("VisionDocument", back_populates="product")
    projects = relationship("Project", back_populates="product")
```

**Project** (`src/giljo_mcp/models/projects.py:28`):
```python
class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"))
    name = Column(String(255), nullable=False)
    alias = Column(String(6), nullable=False, unique=True)  # e.g., "A1B2C3"
    description = Column(Text, nullable=False)  # Human-written
    mission = Column(Text, nullable=False)  # AI-generated
    status = Column(String(50), default="inactive")
    context_budget = Column(Integer, default=150000)
    context_used = Column(Integer, default=0)
```

### Test Fixture Templates

```python
# tests/conftest.py - Add these fixtures

import pytest
from uuid import uuid4
from src.giljo_mcp.models import Product, Project

@pytest.fixture
def sample_product(db_manager):
    """Create a sample product with config_data for testing."""
    product = Product(
        id=str(uuid4()),
        tenant_key="tk_test_fixture_123",
        name="TinyContacts",
        description="Modern contact management application",
        is_active=True,
        config_data={
            "tech_stack": {
                "languages": ["Python 3.11+", "TypeScript 5.0+"],
                "backend_frameworks": ["FastAPI 0.104+", "SQLAlchemy 2.0+"],
                "frontend_frameworks": ["React 18.2+", "Tailwind CSS 3.3+"],
                "databases": {"dev": "SQLite 3.35+", "prod": "PostgreSQL 13+"}
            },
            "architecture": {
                "pattern": "Modular monolith with service layer",
                "api_style": "REST + OpenAPI 3.0",
                "design_patterns": ["Repository", "DI", "MVC", "Observer"]
            },
            "testing": {
                "coverage_target": "80%",
                "approach": "TDD",
                "quality_standards": "production-grade"
            }
        },
        product_memory={
            "sequential_history": []  # Empty for new product
        }
    )
    return product

@pytest.fixture
def sample_project(db_manager, sample_product):
    """Create a sample project linked to sample_product."""
    project = Project(
        id=str(uuid4()),
        tenant_key=sample_product.tenant_key,
        product_id=sample_product.id,
        name="0001 Setup folder structure",
        alias="A1B2C3",
        description="Setup the proper folder structure and index files",
        mission="Create organized folder structure with documentation",
        status="active",
        context_budget=150000,
        context_used=0
    )
    return project

@pytest.fixture
def product_with_vision(db_manager, sample_product):
    """Sample product with vision document for testing summarization."""
    from src.giljo_mcp.models.products import VisionDocument

    vision_doc = VisionDocument(
        id=str(uuid4()),
        product_id=sample_product.id,
        tenant_key=sample_product.tenant_key,
        title="TinyContacts Product Vision",
        content="Full 40K word vision document content...",
        original_token_count=21000,
        chunk_count=5,
        is_active=True,
        display_order=1
    )
    sample_product.vision_documents = [vision_doc]
    return sample_product
```

### Test Orchestrator Fixture

```python
@pytest.fixture
def sample_orchestrator(db_manager, sample_project):
    """Create a sample orchestrator job for MCP tool testing."""
    from src.giljo_mcp.models import MCPAgentJob

    orchestrator = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key=sample_project.tenant_key,
        project_id=sample_project.id,
        agent_type="orchestrator",
        status="active",
        context_budget=150000,
        context_used=0,
        instance_number=1,
        job_metadata={
            "depth_config": {
                "vision_documents": "moderate",  # Handover 0346 - correct field name
                "memory_360": 5,
                "git_history": 25,
                "agent_templates": "full"
            }
        }
    )
    return orchestrator
```

### E2E Test Data

For manual E2E testing, use these existing IDs from the database:

```python
# From user's paste - real orchestrator in database
TEST_ORCHESTRATOR_ID = "62af6b2f-404c-4332-bfbc-241d645765c1"
TEST_PROJECT_ID = "b25ebff8-2316-4ae1-b4f4-1c848e15088c"
TEST_TENANT_KEY = "***REMOVED***"

# MCP endpoint for E2E testing
MCP_SERVER_URL = "http://10.1.0.164:7272/mcp"
```

---

**Estimated Total Effort:** 8-10 hours
- Phase 1 (YAML Builder): 2 hours
- Phase 2 (MissionPlanner): 4 hours
- Phase 3 (Orchestration Service): 1 hour
- Phase 4 (Testing): 3 hours
