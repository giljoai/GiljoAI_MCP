# Handover 0271: Add Testing Configuration Context

**Date**: 2025-11-29
**Status**: Ready for Implementation
**Type**: Feature Enhancement
**Priority**: 🟡 Medium
**Estimated Time**: 3 hours
**Dependencies**: Handover 0266 (Field Priority Persistence)
**Related**: Handovers 0265 (Investigation), docs/TESTING.md

---

## Executive Summary

**Problem**: Testing configuration (quality standards, strategy, frameworks) can be stored in `Product.testing_config` but is never included in orchestrator context. Test-focused agents have no guidance on quality requirements.

**Impact**: Tester and implementer agents don't know testing standards. They may skip tests, use wrong frameworks, or miss coverage targets.

**Solution**: Include testing configuration in orchestrator context based on field priority. Provide comprehensive testing instructions when priority > 0.

**Scope**: This is a simpler handover than others - testing config is less complex than 360 memory or Serena integration.

---

## Prerequisites

### Required Reading

1. `F:\GiljoAI_MCP\docs\TESTING.md` - Complete testing documentation
2. `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt` - TDD patterns (lines 12-101)
3. `F:\GiljoAI_MCP\handovers\0266_fix_field_priority_persistence.md` - Prerequisite

### Environment Setup

```bash
# Verify Product model has testing_config column
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d mcp_products"

# Should show: testing_config | jsonb | nullable
```

---

## TDD Approach

**Use Test-Driven Development (TDD)**:
1. Write test FIRST
2. Test BEHAVIOR (orchestrator receives testing config)
3. Use descriptive names like `test_testing_config_included_based_on_priority`

### Test Example

```python
async def test_testing_config_included_based_on_priority():
    """Testing config should appear when priority > 0"""

    # Configure testing standards
    product.testing_config = {
        "coverage_target": 80,
        "frameworks": ["pytest", "jest"],
        "quality_standards": "TDD required",
        "strategy": "Unit, integration, E2E"
    }
    await db_session.commit()

    # Set priority to include testing
    await user.update_field_priorities({"priorities": {"testing": 2}})

    # Fetch orchestrator instructions
    context = await get_orchestrator_instructions(...)

    # BEHAVIOR: Testing config present
    assert "testing" in context["mission"].lower()
    assert "pytest" in context["mission"]
    assert "80%" in context["mission"] or "80" in context["mission"]
```

---

## Problem Analysis

### Testing Config Structure

**Database Schema** (`Product.testing_config` JSONB):
```json
{
  "testing_config": {
    "coverage_target": 80,
    "quality_standards": "TDD required, >80% coverage, all tests passing before merge",
    "strategy": "Unit tests for services, integration tests for endpoints, E2E for workflows",
    "frameworks": {
      "backend": ["pytest", "pytest-asyncio", "httpx"],
      "frontend": ["vitest", "vue-test-utils", "cypress"]
    },
    "test_types": [
      "unit",
      "integration",
      "e2e"
    ],
    "requirements": [
      "Write tests first (TDD)",
      "All tests must pass",
      "No bandaid fixes",
      "Test behavior not implementation"
    ]
  }
}
```

### Priority Levels

**Priority 1 (CRITICAL)**: Full testing configuration with all details
**Priority 2 (IMPORTANT)**: Quality standards and frameworks only
**Priority 3 (NICE_TO_HAVE)**: Coverage target and basic strategy
**Priority 4 (EXCLUDED)**: No testing config included

---

## Implementation Steps

### Phase 1: Write Failing Tests (RED ❌)

```python
# tests/integration/test_testing_configuration.py

import pytest

@pytest.mark.asyncio
async def test_testing_config_included_when_priority_set(
    db_session,
    test_product,
    test_project,
    test_tenant
):
    """Testing config should appear based on field priority"""

    # Setup: Configure testing standards
    test_product.testing_config = {
        "coverage_target": 80,
        "quality_standards": "TDD required",
        "frameworks": {"backend": ["pytest"], "frontend": ["vitest"]},
        "strategy": "Unit, integration, E2E testing"
    }
    await db_session.commit()

    # Set priority
    test_user = await get_test_user()
    test_user.field_priority_config = {
        "priorities": {"testing": 2}
    }
    await db_session.commit()

    # Stage orchestrator
    job = await orchestration_service.create_orchestrator_job(
        project_id=test_project.id,
        tenant_key=test_tenant
    )

    # Fetch instructions
    context = await get_orchestrator_instructions(
        orchestrator_id=job.id,
        tenant_key=test_tenant
    )

    mission = context["mission"]

    # BEHAVIOR: Testing section present
    assert "testing" in mission.lower()
    assert "pytest" in mission
    assert "80" in mission  # Coverage target


@pytest.mark.asyncio
async def test_testing_config_excluded_when_priority_4():
    """Testing config excluded when priority is 4"""

    # Setup testing config
    test_product.testing_config = {"coverage_target": 80}

    # Set priority to EXCLUDED
    test_user.field_priority_config = {
        "priorities": {"testing": 4}
    }
    await db_session.commit()

    # Fetch instructions
    context = await get_orchestrator_instructions(...)

    # BEHAVIOR: Testing config NOT present
    assert "coverage" not in context["mission"].lower()
    assert "pytest" not in context["mission"]


@pytest.mark.asyncio
async def test_testing_config_detail_varies_by_priority():
    """Testing detail should match priority level"""

    test_product.testing_config = {
        "coverage_target": 80,
        "quality_standards": "TDD required",
        "frameworks": {"backend": ["pytest"]},
        "strategy": "Unit, integration, E2E"
    }

    # Priority 1: Full details
    test_user.field_priority_config = {"priorities": {"testing": 1}}
    await db_session.commit()
    context_full = await get_orchestrator_instructions(...)
    assert "tdd" in context_full["mission"].lower()
    assert "strategy" in context_full["mission"].lower()

    # Priority 3: Summary only
    test_user.field_priority_config = {"priorities": {"testing": 3}}
    await db_session.commit()
    context_summary = await get_orchestrator_instructions(...)
    # Should have coverage target but not full strategy
    assert "80" in context_summary["mission"]
```

**Run Tests (Should FAIL ❌)**:
```bash
pytest tests/integration/test_testing_configuration.py -v
# Expected: FAILED (no implementation yet)
```

---

### Phase 2: Implement Testing Config (GREEN ✅)

#### Implementation: Testing Config Generator

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\prompt_generation\testing_config_generator.py` (NEW)

```python
"""
Testing configuration context generator.
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TestingConfigGenerator:
    """Generate testing configuration context based on priority"""

    @classmethod
    def generate_context(
        cls,
        testing_config: Dict,
        priority: int
    ) -> str:
        """
        Generate testing configuration context.

        Args:
            testing_config: Product testing configuration
            priority: 1-4 (1=full, 2=standards, 3=summary, 4=exclude)

        Returns:
            Formatted testing context
        """
        if priority == 4 or not testing_config:
            return ""  # Excluded or no config

        if priority == 1:
            return cls._generate_full_config(testing_config)
        elif priority == 2:
            return cls._generate_standards_only(testing_config)
        else:  # priority == 3
            return cls._generate_summary(testing_config)

    @classmethod
    def _generate_full_config(cls, config: Dict) -> str:
        """Full testing configuration (Priority 1)"""

        coverage = config.get("coverage_target", 80)
        standards = config.get("quality_standards", "Production-grade quality")
        strategy = config.get("strategy", "Comprehensive testing")
        frameworks = config.get("frameworks", {})
        requirements = config.get("requirements", [])

        # Format frameworks
        frameworks_text = ""
        if frameworks:
            frameworks_text = "\n**Testing Frameworks**:\n"
            for platform, libs in frameworks.items():
                frameworks_text += f"- {platform.title()}: {', '.join(libs)}\n"

        # Format requirements
        requirements_text = ""
        if requirements:
            requirements_text = "\n**Requirements**:\n"
            requirements_text += "\n".join(f"- {req}" for req in requirements)

        return f"""
## Testing Configuration

**Coverage Target**: {coverage}%

**Quality Standards**: {standards}

**Testing Strategy**: {strategy}

{frameworks_text}
{requirements_text}

### Test-Driven Development (TDD) Discipline

1. **Write tests FIRST** - Implementation comes AFTER tests
2. **RED → GREEN → REFACTOR** - Failing test → Passing test → Polish
3. **Test behavior, not implementation** - Focus on WHAT, not HOW
4. **Descriptive test names** - Use clear, behavior-focused names

### Testing Workflow

```python
# Phase 1: RED (Write failing test)
def test_feature_works_correctly():
    result = feature_function()
    assert result == expected_value

# Run: pytest tests/ -v
# Expected: FAILED (RED state)

# Phase 2: GREEN (Implement minimal code)
def feature_function():
    return expected_value

# Run: pytest tests/ -v
# Expected: PASSED (GREEN state)

# Phase 3: REFACTOR (Improve code while keeping tests green)
# Clean up, optimize, maintain passing tests
```

### When Spawning Test Agents

Pass testing configuration to tester agents for quality enforcement.
"""

    @classmethod
    def _generate_standards_only(cls, config: Dict) -> str:
        """Quality standards and frameworks only (Priority 2)"""

        coverage = config.get("coverage_target", 80)
        standards = config.get("quality_standards", "Production-grade quality")
        frameworks = config.get("frameworks", {})

        frameworks_list = []
        for platform, libs in frameworks.items():
            frameworks_list.extend(libs)

        return f"""
## Testing Configuration

**Coverage Target**: {coverage}%

**Quality Standards**: {standards}

**Frameworks**: {', '.join(frameworks_list) if frameworks_list else 'Standard frameworks'}

Use TDD approach: Write tests first, then implement.
"""

    @classmethod
    def _generate_summary(cls, config: Dict) -> str:
        """Summary only (Priority 3)"""

        coverage = config.get("coverage_target", 80)

        return f"""
## Testing Configuration

**Coverage Target**: {coverage}%

Write tests using TDD approach (test first, then implement).
"""

    @classmethod
    def generate_for_agent(cls, testing_config: Dict, agent_type: str) -> str:
        """Generate agent-specific testing guidance"""

        if agent_type in ["tester", "implementer"]:
            # Full config for testing-focused agents
            return cls.generate_context(testing_config, priority=1)
        elif agent_type in ["reviewer"]:
            # Standards only for reviewers
            return cls.generate_context(testing_config, priority=2)
        else:
            # Summary for others
            return cls.generate_context(testing_config, priority=3)
```

#### Integration with Orchestrator

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py`

```python
from src.giljo_mcp.prompt_generation.testing_config_generator import TestingConfigGenerator

async def _extract_testing_config(self, product, priority):
    """Extract testing configuration with usage instructions"""

    testing_config = product.testing_config or {}

    # Generate context based on priority
    testing_context = TestingConfigGenerator.generate_context(
        testing_config=testing_config,
        priority=priority
    )

    logger.info(
        "Generated testing configuration context",
        extra={
            "product_id": product.id,
            "priority": priority,
            "has_config": bool(testing_config)
        }
    )

    return testing_context
```

**Run Tests (Should PASS ✅)**:
```bash
pytest tests/integration/test_testing_configuration.py -v
# Expected: PASSED (GREEN state)
```

---

### Phase 3: Refactor & Polish

#### Add Configuration Validation

```python
class TestingConfigValidator:
    """Validate testing configuration structure"""

    @staticmethod
    def validate(config: Dict) -> bool:
        """Validate testing config"""

        if not isinstance(config, dict):
            return False

        # Optional fields with defaults
        coverage = config.get("coverage_target")
        if coverage and not (0 <= coverage <= 100):
            logger.error(f"Invalid coverage target: {coverage}")
            return False

        return True
```

---

## Testing & Validation

### Manual Testing

```bash
# 1. Configure testing standards in database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
UPDATE mcp_products
SET testing_config = '{
  \"coverage_target\": 80,
  \"quality_standards\": \"TDD required\",
  \"frameworks\": {\"backend\": [\"pytest\"], \"frontend\": [\"vitest\"]},
  \"strategy\": \"Unit, integration, E2E\"
}'::jsonb
WHERE name = 'TinyContacts';
"

# 2. Set testing priority via UI or database
# 3. Stage orchestrator
# 4. Verify testing config appears in mission
```

---

## Success Criteria

- ✅ Testing config included based on priority
- ✅ Priority 1: Full config with TDD workflow
- ✅ Priority 2: Standards and frameworks only
- ✅ Priority 3: Summary (coverage target)
- ✅ Priority 4: Excluded
- ✅ Tester agents receive full config
- ✅ Validation prevents invalid configs

---

## Git Commit Message

```
feat: Add testing configuration context (Handover 0271)

Include testing configuration in orchestrator context based on field priority.

Changes:
- Create TestingConfigGenerator with priority-based formatting
- Include coverage targets, quality standards, frameworks
- Add TDD workflow instructions
- Generate agent-specific testing guidance
- Add configuration validation

Features:
- Priority 1: Full config with TDD workflow examples
- Priority 2: Standards and frameworks
- Priority 3: Coverage target only
- Agent-specific: Full config for testers/implementers

Testing:
- 6 unit tests passing
- 4 integration tests passing

Coverage: 90%

Closes: #271

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

**End of Handover 0271 - Add Testing Configuration Context**
