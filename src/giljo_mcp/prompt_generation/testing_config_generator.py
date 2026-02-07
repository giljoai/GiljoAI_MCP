"""
Testing Configuration Context Generator.

Generates testing configuration context for orchestrators based on field priority.
Supports priority-based detail levels and agent-specific guidance.

Handover 0271: Testing Configuration Context Integration
"""

import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class TestingConfigGenerator:
    """Generate testing configuration context based on priority and agent type."""

    @classmethod
    def generate_context(cls, testing_config: Optional[dict[str, Any]], priority: int = 1) -> str:
        """
        Generate testing configuration context.

        Args:
            testing_config: Product testing configuration (from config_data.testing_config)
            priority: Priority level (1=CRITICAL/FULL, 2=IMPORTANT/STANDARDS,
                                    3=NICE_TO_HAVE/SUMMARY, 4=EXCLUDED/NONE)

        Returns:
            Formatted testing context as string (empty if priority=4 or config is None)
        """
        # Priority 4 (EXCLUDED) returns empty
        if priority == 4:
            return ""

        # None config returns empty (but empty dict {} is valid)
        if testing_config is None:
            return ""

        # Generate based on priority level
        if priority == 1:
            return cls._generate_full_config(testing_config)
        if priority == 2:
            return cls._generate_standards_only(testing_config)
        # priority == 3
        return cls._generate_summary(testing_config)

    @classmethod
    def _generate_full_config(cls, config: dict[str, Any]) -> str:
        """
        Generate full testing configuration (Priority 1 - CRITICAL).

        Includes:
        - Coverage target
        - Quality standards
        - Testing strategy
        - Testing frameworks
        - Requirements
        - TDD workflow examples
        """
        coverage = config.get("coverage_target", 80)
        standards = config.get("quality_standards", "Production-grade quality")
        strategy = config.get("strategy", "Comprehensive testing strategy")
        frameworks = config.get("frameworks", {})
        requirements = config.get("requirements", [])

        # Format frameworks by platform
        frameworks_text = ""
        if frameworks:
            frameworks_text = "\n**Testing Frameworks**:\n"
            if isinstance(frameworks, dict):
                for platform, libs in frameworks.items():
                    if libs:
                        frameworks_text += f"- {platform.title()}: {', '.join(libs)}\n"
            else:
                # Handle if frameworks is a list
                frameworks_text += f"- {', '.join(frameworks) if frameworks else 'Standard frameworks'}\n"

        # Format requirements
        requirements_text = ""
        if requirements:
            requirements_text = "\n**Requirements**:\n"
            for req in requirements:
                requirements_text += f"- {req}\n"

        return f"""
## Testing Configuration

**Coverage Target**: {coverage}%

**Quality Standards**: {standards}

**Testing Strategy**: {strategy}
{frameworks_text}{requirements_text}

### Test-Driven Development (TDD) Discipline

TDD is a disciplined approach where you write tests FIRST, then implement code to make them pass.

1. **Write tests FIRST** - Implementation comes AFTER tests are written and failing
2. **RED → GREEN → REFACTOR** - Failing test (RED) → Passing test (GREEN) → Polish code (REFACTOR)
3. **Test behavior, not implementation** - Focus on WHAT the code should do, not HOW it does it
4. **Descriptive test names** - Use clear, behavior-focused test names
5. **One assertion per test** - Keep tests focused and easy to understand

### TDD Workflow Example

```python
# Phase 1: RED (Write failing test first)
def test_calculator_adds_two_numbers():
    '''Verify calculator correctly adds two numbers'''
    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5  # This test FAILS because add() doesn't exist yet

# Run: pytest tests/test_calculator.py -v
# Expected: FAILED (RED state)

# Phase 2: GREEN (Implement minimal code to make test pass)
class Calculator:
    def add(self, a, b):
        return a + b  # Minimal implementation to pass test

# Run: pytest tests/test_calculator.py -v
# Expected: PASSED (GREEN state)

# Phase 3: REFACTOR (Improve code while keeping tests green)
class Calculator:
    def add(self, a, b):
        '''Add two numbers.

        Args:
            a: First number
            b: Second number

        Returns:
            Sum of a and b
        '''
        return a + b  # Added documentation, tests still pass
```

### When Implementing Features

1. Identify the behavior you need to implement
2. Write a test that describes that behavior
3. Run the test (it will fail - RED)
4. Write minimal code to make it pass (GREEN)
5. Refactor to improve code quality (REFACTOR)
6. Repeat for next behavior
"""

    @classmethod
    def _generate_standards_only(cls, config: dict[str, Any]) -> str:
        """
        Generate standards and frameworks only (Priority 2 - IMPORTANT).

        Includes:
        - Coverage target
        - Quality standards
        - Testing frameworks
        - Brief TDD note
        """
        coverage = config.get("coverage_target", 80)
        standards = config.get("quality_standards", "Production-grade quality")
        frameworks = config.get("frameworks", {})

        # Extract framework names
        frameworks_list = []
        if frameworks:
            if isinstance(frameworks, dict):
                for platform, libs in frameworks.items():
                    if libs:
                        frameworks_list.extend(libs)
            else:
                frameworks_list = frameworks if isinstance(frameworks, list) else []

        frameworks_str = ", ".join(frameworks_list) if frameworks_list else "Standard frameworks"

        return f"""
## Testing Configuration

**Coverage Target**: {coverage}%

**Quality Standards**: {standards}

**Frameworks**: {frameworks_str}

### Testing Approach

Use TDD (Test-Driven Development): Write tests first, then implement code to make them pass.
"""

    @classmethod
    def _generate_summary(cls, config: dict[str, Any]) -> str:
        """
        Generate summary only (Priority 3 - NICE_TO_HAVE).

        Includes:
        - Coverage target
        - Brief TDD note
        """
        coverage = config.get("coverage_target", 80)

        return f"""
## Testing Configuration

**Coverage Target**: {coverage}%

Apply TDD approach: Write tests first, then implement code.
"""

    @classmethod
    def generate_for_agent(cls, testing_config: Optional[dict[str, Any]], agent_display_name: str) -> str:
        """
        Generate agent-specific testing guidance.

        Args:
            testing_config: Product testing configuration
            agent_display_name: Type of agent (tester, implementer, reviewer, architect, etc.)

        Returns:
            Testing context appropriate for the agent type
        """
        if agent_display_name in ["tester", "implementer"]:
            # Full config for testing-focused agents
            return cls.generate_context(testing_config, priority=1)
        if agent_display_name in ["reviewer"]:
            # Standards only for reviewers
            return cls.generate_context(testing_config, priority=2)
        # Summary for others (architect, documenter, etc.)
        return cls.generate_context(testing_config, priority=3)


class TestingConfigValidator:
    """Validate testing configuration structure."""

    @staticmethod
    def validate(config: Optional[dict[str, Any]]) -> bool:
        """
        Validate testing configuration.

        Args:
            config: Testing configuration to validate

        Returns:
            True if config is valid, False otherwise
        """
        if config is None:
            return True  # None is acceptable

        if not isinstance(config, dict):
            logger.warning(f"Testing config must be dict, got {type(config)}")
            return False

        # Validate coverage target if present
        coverage = config.get("coverage_target")
        if coverage is not None:
            try:
                coverage_num = float(coverage)
                if not (0 <= coverage_num <= 100):
                    logger.warning(f"Coverage target must be 0-100, got {coverage_num}")
                    return False
            except (TypeError, ValueError):
                logger.warning(f"Coverage target must be numeric, got {coverage}")
                return False

        # Validate frameworks structure if present
        frameworks = config.get("frameworks")
        if frameworks is not None:
            if isinstance(frameworks, dict):
                # Check each platform has a list of frameworks
                for platform, libs in frameworks.items():
                    if not isinstance(libs, (list, tuple)):
                        logger.warning(f"Frameworks for {platform} must be list/tuple")
                        return False
            elif not isinstance(frameworks, (list, tuple)):
                logger.warning("Frameworks must be dict or list")
                return False

        # Validate requirements if present
        requirements = config.get("requirements")
        if requirements is not None:
            if not isinstance(requirements, (list, tuple)):
                logger.warning("Requirements must be list/tuple")
                return False

        return True
