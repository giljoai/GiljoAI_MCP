# Handover 0373: Template Adapter Migration to Mission Generator

**Status**: Ready for Execution
**Priority**: Medium
**Estimated Effort**: 2-4 hours
**Risk Level**: Medium (affects core orchestrator functionality)
**Complexity**: Moderate (clean refactoring with clear migration path)

---

## Executive Summary

### What
Migrate from the incomplete adapter layer (`template_adapter.py`) to a clean, honest architecture by creating `mission_generator.py`. This removes unnecessary indirection while preserving all mission generation functionality.

### Why
During dead code cleanup (Handover 0371), we discovered `template_adapter.py` is NOT dead code but an INCOMPLETE MIGRATION artifact. It contains:
1. **TemplateAdapter** (lines 20-97): Thin wrapper around UnifiedTemplateManager that adds no value
2. **MissionTemplateGeneratorV2** (lines 99-312): Mission-specific generation methods that orchestrator actually uses

The current architecture has unnecessary layers:
```
orchestrator.py
  → MissionTemplateGeneratorV2 (template_adapter.py)
    → TemplateAdapter (template_adapter.py)
      → UnifiedTemplateManager (template_manager.py)
        → Database (AgentTemplate table)
```

### Goal
Create clean architecture with honest naming:
```
orchestrator.py
  → MissionGenerator (mission_generator.py)
    → UnifiedTemplateManager (template_manager.py)
      → Database (AgentTemplate table)
```

---

## Prerequisites

**CRITICAL**: Before starting, verify the following:

### 1. Understand Current Usage
```bash
# Verify orchestrator.py imports
grep "template_adapter" F:/GiljoAI_MCP/src/giljo_mcp/orchestrator.py

# Expected output (line 36):
# from .template_adapter import MissionTemplateGeneratorV2
```

### 2. Identify All Test Files
```bash
# Find all test files that import template_adapter
grep -r "template_adapter" F:/GiljoAI_MCP/tests/ --files-with-matches
```

**Expected test files**:
- `tests/unit/test_mission_templates.py`
- `tests/test_template_system.py`
- `tests/test_templates_validation.py`
- `tests/test_real_integration.py`
- `tests/test_consolidated_system.py`

### 3. Verify No Other Production Code Uses template_adapter
```bash
# Search src/ directory (excluding tests/)
grep -r "template_adapter" F:/GiljoAI_MCP/src/ --files-with-matches
```

**Expected result**: Only `orchestrator.py` should appear.

### 4. Database Check
Verify that `AgentTemplate` table exists and has active templates:
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM agent_templates WHERE is_active = true;"
```

**Expected**: At least 1 active template exists.

---

## Phase 1: Create MissionGenerator Class

### File: `F:\GiljoAI_MCP\src\giljo_mcp\mission_generator.py`

Create new file with the following structure:

```python
"""
Mission Generator for GiljoAI MCP
Generates agent missions using database-backed templates.

Replaces template_adapter.py with clean, honest architecture.
Handover 0373: Template Adapter Migration
"""

import logging
from typing import Any, Optional

from .database import DatabaseManager
from .system_prompts import SystemPromptService
from .template_manager import UnifiedTemplateManager


logger = logging.getLogger(__name__)


class MissionGenerator:
    """
    Mission generator that creates agent missions using database templates.

    Uses UnifiedTemplateManager for template retrieval and processing.
    Provides mission-specific generation methods for orchestrator coordination.

    Handover 0373: Replaces MissionTemplateGeneratorV2 from template_adapter.py
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize mission generator.

        Args:
            db_manager: Optional database manager for template access
        """
        self.db_manager = db_manager
        self.template_manager = UnifiedTemplateManager(db_manager) if db_manager else None
        self.system_prompt_service = SystemPromptService(db_manager)

        # Fallback templates if database is not available
        self.ORCHESTRATOR_TEMPLATE = """You are the Project Orchestrator for: {project_name}

PROJECT GOAL: {project_mission}

Your role is to coordinate agents and ensure project success."""

        self.ANALYZER_TEMPLATE = """You are the Analyzer Agent for: {project_name}

Your role is to analyze the system and provide insights."""

        self.IMPLEMENTER_TEMPLATE = """You are the Implementation Agent for: {project_name}

Your role is to implement the required functionality."""

        self.TESTER_TEMPLATE = """You are the Testing Agent for: {project_name}

Your role is to test the implementation thoroughly."""

        self.REVIEWER_TEMPLATE = """You are the Review Agent for: {project_name}

Your role is to review code and ensure quality."""

    async def generate_orchestrator_mission(
        self,
        project_name: str,
        project_mission: str,
        product_name: str = "GiljoAI MCP",
        additional_context: Optional[str] = None,
    ) -> str:
        """
        Generate orchestrator mission using database template.

        Args:
            project_name: Name of the project
            project_mission: Project mission/goal description
            product_name: Product name (default: "GiljoAI MCP")
            additional_context: Optional additional context to append

        Returns:
            Generated mission content
        """
        variables = {
            "project_name": project_name,
            "project_mission": project_mission,
            "product_name": product_name,
        }

        prompt_record = await self.system_prompt_service.get_orchestrator_prompt()
        content = prompt_record.content

        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))

        if additional_context:
            content = f"{content}\n\nADDITIONAL CONTEXT:\n{additional_context}"

        return content

    async def generate_agent_mission(
        self,
        role: str,
        project_name: str,
        project_type: Optional[str] = None,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None,
    ) -> str:
        """
        Generate agent mission using database template.

        Args:
            role: Agent role (analyzer, implementer, tester, reviewer)
            project_name: Name of the project
            project_type: Optional project type for customization
            custom_mission: Optional custom mission to use instead of template
            additional_instructions: Optional additional instructions to append

        Returns:
            Generated mission content
        """
        if self.template_manager:
            variables = {"project_name": project_name, "role": role}

            augmentations = []
            if custom_mission:
                augmentations.append(
                    {
                        "type": "replace",
                        "target": "YOUR MISSION:",
                        "content": f"YOUR MISSION:\n{custom_mission}",
                    }
                )

            if additional_instructions:
                augmentations.append(
                    {
                        "type": "append",
                        "content": f"\nADDITIONAL INSTRUCTIONS:\n{additional_instructions}",
                    }
                )

            try:
                # Use UnifiedTemplateManager directly (no adapter layer)
                template_result = await self.template_manager.get_template(
                    role=role.lower(),
                    tenant_key="system",  # Use system tenant for default templates
                    variables=variables,
                    augmentations=augmentations,
                )
                if template_result:
                    return template_result
            except Exception as e:
                logger.warning(f"Failed to get template for role '{role}': {e}")

        # Fallback to hardcoded templates
        template_map = {
            "analyzer": self.ANALYZER_TEMPLATE,
            "implementer": self.IMPLEMENTER_TEMPLATE,
            "tester": self.TESTER_TEMPLATE,
            "reviewer": self.REVIEWER_TEMPLATE,
        }

        template = template_map.get(role.lower(), "You are an agent for: {project_name}")
        content = template.format(project_name=project_name)

        if custom_mission:
            content = content.replace("Your role", custom_mission)

        if additional_instructions:
            content += f"\n\n{additional_instructions}"

        return content

    def generate_parallel_startup_instructions(self, agents: list[str], project_name: str) -> str:
        """
        Generate instructions for parallel agent startup.

        Args:
            agents: List of agent names to start in parallel
            project_name: Name of the project

        Returns:
            Formatted parallel startup instructions
        """
        agent_list = ", ".join(agents)
        return f"""
PARALLEL STARTUP INSTRUCTIONS for {project_name}:

The following agents should be started in parallel:
{agent_list}

Each agent should:
1. Acknowledge receipt of their mission
2. Begin their assigned tasks immediately
3. Communicate status updates regularly
4. Report completion when finished
"""

    def generate_context_limit_instructions(
        self,
        current_agent: str,
        next_agent: str,
        reason: str = "context limit approaching",
    ) -> str:
        """
        Generate instructions for context limit handling.

        Args:
            current_agent: Current agent name
            next_agent: Next agent name
            reason: Reason for context limit (default: "context limit approaching")

        Returns:
            Formatted context limit instructions
        """
        return f"""
CONTEXT LIMIT INSTRUCTIONS:

Current agent: {current_agent}
Next agent: {next_agent}
Reason: {reason}

Please prepare for handoff:
1. Summarize your current progress
2. Document any incomplete tasks
3. Prepare handoff package for {next_agent}
4. Signal completion of handoff
"""

    def generate_handoff_instructions(
        self, from_agent: str, to_agent: str, handoff_context: dict[str, Any]
    ) -> str:
        """
        Generate handoff instructions between agents.

        Args:
            from_agent: Source agent name
            to_agent: Target agent name
            handoff_context: Context data to transfer

        Returns:
            Formatted handoff instructions
        """
        context_summary = "\n".join([f"- {k}: {v}" for k, v in handoff_context.items()])

        return f"""
HANDOFF INSTRUCTIONS:

From: {from_agent}
To: {to_agent}

Handoff Context:
{context_summary}

The receiving agent should:
1. Acknowledge receipt of handoff
2. Review the provided context
3. Continue from where {from_agent} left off
4. Report any issues or questions
"""

    def generate_acknowledgment_instruction(self) -> str:
        """
        Generate acknowledgment instruction.

        Returns:
            Acknowledgment instruction text
        """
        return "Messages are automatically acknowledged when retrieved."

    def get_behavioral_rules(self, role: str) -> list[str]:
        """
        Get behavioral rules for a role.

        Args:
            role: Agent role

        Returns:
            List of behavioral rules
        """
        default_rules = {
            "orchestrator": [
                "Coordinate all agents effectively",
                "Ensure project goals are met",
                "Handle conflicts and blockers",
                "Maintain project momentum",
            ],
            "analyzer": [
                "Perform thorough analysis",
                "Document findings clearly",
                "Identify risks and opportunities",
                "Provide actionable insights",
            ],
            "implementer": [
                "Write clean, maintainable code",
                "Follow design specifications",
                "Handle errors appropriately",
                "Test your implementation",
            ],
            "tester": [
                "Test all functionality thoroughly",
                "Document test results",
                "Verify edge cases",
                "Ensure quality standards",
            ],
            "reviewer": [
                "Review code objectively",
                "Check for standards compliance",
                "Identify improvements",
                "Provide constructive feedback",
            ],
        }

        return default_rules.get(role.lower(), ["Follow project guidelines"])
```

**Why this structure?**
- Direct use of UnifiedTemplateManager (no adapter wrapper)
- All mission generation methods preserved from MissionTemplateGeneratorV2
- Clear docstrings for each method
- Honest class naming (MissionGenerator vs MissionTemplateGeneratorV2)

---

## Phase 2: Update Orchestrator Import

### File: `F:\GiljoAI_MCP\src\giljo_mcp\orchestrator.py`

**BEFORE** (line 36):
```python
from .template_adapter import MissionTemplateGeneratorV2
```

**AFTER** (line 36):
```python
from .mission_generator import MissionGenerator
```

**BEFORE** (line 105):
```python
self.template_generator = MissionTemplateGeneratorV2(self.db_manager)
```

**AFTER** (line 105):
```python
self.template_generator = MissionGenerator(self.db_manager)
```

**Why these changes?**
- Single import change at top of file
- Single constructor call change in `__init__`
- All method calls remain identical (API compatibility maintained)

---

## Phase 3: Update Test Files

### Test File 1: `tests/unit/test_mission_templates.py`

**BEFORE**:
```python
from giljo_mcp.template_adapter import MissionTemplateGeneratorV2
```

**AFTER**:
```python
from giljo_mcp.mission_generator import MissionGenerator
```

**Also update all references**:
- `MissionTemplateGeneratorV2` → `MissionGenerator`

### Test File 2: `tests/test_template_system.py`

**BEFORE** (line 22):
```python
from giljo_mcp.template_adapter import MissionTemplateGeneratorV2
```

**AFTER**:
```python
from giljo_mcp.mission_generator import MissionGenerator
```

### Test File 3: `tests/test_templates_validation.py`

**BEFORE** (line 16):
```python
from giljo_mcp.template_adapter import MissionTemplateGeneratorV2
```

**AFTER**:
```python
from giljo_mcp.mission_generator import MissionGenerator
```

### Test File 4: `tests/test_real_integration.py`

**BEFORE** (line 16):
```python
from giljo_mcp.template_adapter import MissionTemplateGeneratorV2
```

**AFTER**:
```python
from giljo_mcp.mission_generator import MissionGenerator
```

### Test File 5: `tests/test_consolidated_system.py`

**BEFORE** (lines 232-261 section):
```python
from giljo_mcp.template_adapter import MissionTemplateGeneratorV2
```

**AFTER**:
```python
from giljo_mcp.mission_generator import MissionGenerator
```

**Also update all test instantiations**:
```python
# BEFORE
generator = MissionTemplateGeneratorV2(db_manager)

# AFTER
generator = MissionGenerator(db_manager)
```

---

## Phase 4: Cleanup

### Step 1: Delete template_adapter.py
```bash
rm F:/GiljoAI_MCP/src/giljo_mcp/template_adapter.py
```

### Step 2: Remove TemplateManager Alias from template_manager.py

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\template_manager.py`

**BEFORE** (line 1051):
```python
# Compatibility alias for backward compatibility
TemplateManager = UnifiedTemplateManager
```

**AFTER**:
```python
# Alias removed - use UnifiedTemplateManager directly (Handover 0373)
```

**Why remove this alias?**
- It was created for backward compatibility with old code
- With template_adapter.py deleted, nothing uses the alias
- Keeps codebase honest and clean

---

## Verification Checklist

After completing all phases, verify the following:

### 1. File Structure Verification
```bash
# Verify new file exists
ls F:/GiljoAI_MCP/src/giljo_mcp/mission_generator.py

# Verify old file deleted
ls F:/GiljoAI_MCP/src/giljo_mcp/template_adapter.py
# Expected: File not found
```

### 2. Import Verification
```bash
# Search for any remaining template_adapter imports
grep -r "template_adapter" F:/GiljoAI_MCP/src/ F:/GiljoAI_MCP/tests/
# Expected: No results
```

### 3. Run Tests
```bash
# Run all tests to verify nothing broke
pytest tests/ -v

# Run specific template tests
pytest tests/test_template_system.py -v
pytest tests/unit/test_mission_templates.py -v
```

**Expected**: All tests pass with same results as before migration.

### 4. Orchestrator Smoke Test
```python
# Quick Python test to verify orchestrator can create mission generator
from giljo_mcp.database import get_db_manager
from giljo_mcp.orchestrator import ProjectOrchestrator

orchestrator = ProjectOrchestrator()
print(f"Template generator type: {type(orchestrator.template_generator).__name__}")
# Expected output: "MissionGenerator"
```

### 5. Manual Template Generation Test
```python
import asyncio
from giljo_mcp.database import get_db_manager
from giljo_mcp.mission_generator import MissionGenerator

async def test_mission_generation():
    db_manager = get_db_manager()
    generator = MissionGenerator(db_manager)

    # Test orchestrator mission
    orchestrator_mission = await generator.generate_orchestrator_mission(
        project_name="Test Project",
        project_mission="Test the migration"
    )
    print(f"Orchestrator mission length: {len(orchestrator_mission)}")

    # Test agent mission
    agent_mission = await generator.generate_agent_mission(
        role="implementer",
        project_name="Test Project"
    )
    print(f"Agent mission length: {len(agent_mission)}")

asyncio.run(test_mission_generation())
```

**Expected**: Both missions generated successfully with non-zero lengths.

---

## Rollback Plan

If something breaks during migration, follow these steps to revert:

### Step 1: Restore template_adapter.py
```bash
git checkout HEAD -- F:/GiljoAI_MCP/src/giljo_mcp/template_adapter.py
```

### Step 2: Restore orchestrator.py
```bash
git checkout HEAD -- F:/GiljoAI_MCP/src/giljo_mcp/orchestrator.py
```

### Step 3: Restore test files
```bash
git checkout HEAD -- tests/unit/test_mission_templates.py
git checkout HEAD -- tests/test_template_system.py
git checkout HEAD -- tests/test_templates_validation.py
git checkout HEAD -- tests/test_real_integration.py
git checkout HEAD -- tests/test_consolidated_system.py
```

### Step 4: Delete mission_generator.py
```bash
rm F:/GiljoAI_MCP/src/giljo_mcp/mission_generator.py
```

### Step 5: Verify rollback
```bash
pytest tests/ -v
```

**Expected**: All tests pass, system back to pre-migration state.

---

## Success Criteria

Migration is considered successful when:

- ✅ `mission_generator.py` created with all methods from `MissionTemplateGeneratorV2`
- ✅ `orchestrator.py` imports and uses `MissionGenerator`
- ✅ All 5 test files updated to use `MissionGenerator`
- ✅ `template_adapter.py` deleted
- ✅ `TemplateManager` alias removed from `template_manager.py`
- ✅ All tests pass with same results as before
- ✅ No remaining references to `template_adapter` in codebase
- ✅ Orchestrator can generate missions successfully
- ✅ Architecture is cleaner with fewer layers of indirection

---

## Risk Assessment

### Medium Risk Items

1. **Orchestrator is core functionality**
   - **Mitigation**: All method signatures preserved for API compatibility
   - **Testing**: Run full test suite before and after migration

2. **5 test files need updates**
   - **Mitigation**: Simple find-replace for imports
   - **Verification**: Each test file verified individually

3. **Database template access**
   - **Mitigation**: UnifiedTemplateManager usage unchanged
   - **Verification**: Manual smoke test of template retrieval

### Low Risk Items

1. **File deletion** - Safe to delete after verification all imports removed
2. **Alias removal** - Only affects old code that no longer exists
3. **Class rename** - API compatible, just different name

---

## Implementation Notes

### For the Executing Agent

1. **Read files before editing**: Use Read tool on each file before making changes
2. **Verify paths**: All file paths are absolute (Windows format: `F:\GiljoAI_MCP\...`)
3. **Test incrementally**: Run tests after each phase, not just at the end
4. **Document issues**: If any unexpected errors occur, document them clearly
5. **Use git**: Create a feature branch before starting migration

### Execution Order

1. Phase 1: Create mission_generator.py (NEW FILE)
2. Phase 2: Update orchestrator.py imports (2 changes)
3. Phase 3: Update test files (5 files, simple imports)
4. **RUN TESTS** ← Critical checkpoint
5. Phase 4: Cleanup (delete old file, remove alias)
6. **RUN TESTS AGAIN** ← Final verification

### Time Estimates

- Phase 1: 30 minutes (new file creation)
- Phase 2: 10 minutes (orchestrator updates)
- Phase 3: 30 minutes (test file updates)
- Phase 4: 10 minutes (cleanup)
- Verification: 40 minutes (testing + smoke tests)
- **Total**: 2 hours (best case) to 4 hours (with issues)

---

## Related Documentation

- **Template System**: `docs/SERVICES.md` - Service layer patterns
- **Orchestrator**: `docs/ORCHESTRATOR.md` - Orchestrator documentation
- **Testing**: `docs/TESTING.md` - Test patterns and coverage
- **Architecture**: `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - System architecture

---

## Completion Checklist

Before marking this handover complete, verify:

- [ ] `mission_generator.py` created with complete implementation
- [ ] `orchestrator.py` updated (2 changes verified)
- [ ] All 5 test files updated and verified
- [ ] `template_adapter.py` deleted
- [ ] `TemplateManager` alias removed
- [ ] All tests passing (`pytest tests/ -v`)
- [ ] No remaining `template_adapter` references in codebase
- [ ] Orchestrator smoke test passed
- [ ] Manual mission generation test passed
- [ ] Documentation updated (if needed)
- [ ] Git commit created with descriptive message

---

**Handover 0373 Complete**: Template adapter migration to mission generator architecture.

---

### 0373.1 – Additional Findings (2025-12-22)

This section records follow-up analysis so future work can refine 0373 without destabilizing the working system.

**1) TemplateAdapter and tenant/product isolation**

- `TemplateAdapter.get_template()` currently queries `AgentTemplate` by role/name and `is_active`/`is_default`, but it does **not** filter by `tenant_key` or `product_id`.
- `UnifiedTemplateManager.get_template()` _does_ handle `tenant_key`, `product_id`, `project_type`, and Serena augmentation.
- As a result, agent missions generated via `MissionTemplateGeneratorV2 → TemplateAdapter` don’t yet fully align with the “per-user tenant” design policy.
- When implementing 0373, a key goal should be: route agent mission generation through `UnifiedTemplateManager.get_template()` (directly or via a revised adapter) so mission templates honor tenant/product isolation.

**2) SystemPromptService vs UnifiedTemplateManager**

- `MissionTemplateGeneratorV2.generate_orchestrator_mission()` uses `SystemPromptService.get_orchestrator_prompt()` as its source of truth for orchestrator missions (system prompt).
- `UnifiedTemplateManager` focuses on agent role templates and augmentations, not system prompts.
- Any move from `MissionTemplateGeneratorV2` into `mission_generator.py` should preserve this split:
  - Orchestrator missions: continue to come from SystemPromptService.
  - Agent missions: migrate toward `UnifiedTemplateManager.get_template()` for tenant-aware role templates.

**3) Recommended staged scope for 0373**

To keep risk moderate and behavior stable:

- Stage A (low risk, high value):
  - Introduce `MissionGenerator` as a thin extract of `MissionTemplateGeneratorV2` (no behavior changes).
  - Keep `template_adapter.py` as a compatibility façade that re-exports `MissionTemplateGeneratorV2` for tests and existing imports.
- Stage B (higher value, still incremental):
  - Change agent mission generation to call `UnifiedTemplateManager.get_template(role, tenant_key, product_id, …)` instead of hitting `AgentTemplate` directly.
  - Add tests that assert tenant/product-specific templates are respected.
- Stage C (optional cleanup):
  - Once everything is stable and tests are green, remove `TemplateAdapter` and collapse any remaining indirection.

These stages keep the MCP tools, job/execution model, and dashboard behavior untouched while tightening mission generation around the new template architecture.
