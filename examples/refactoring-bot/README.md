# Simple Refactoring Bot Example

This example demonstrates how to use the GiljoAI MCP Orchestrator to create an autonomous refactoring bot that improves code quality across a codebase.

## What This Example Shows

- How to create a project with orchestrator agents
- Inter-agent communication patterns
- Using templates for consistent agent missions
- Coordinating multiple agents for a common goal

## The Scenario

Your team has inherited a legacy Python codebase with various code quality issues:

- Inconsistent naming conventions
- Missing docstrings
- Complex functions that should be split
- Old-style string formatting that should use f-strings

The refactoring bot will orchestrate multiple specialized agents to systematically improve the code.

## Architecture

```
┌─────────────────┐
│   Orchestrator  │ Coordinates the refactoring workflow
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│Analyzer│ │Linter│ │Refactor │ │Validator │
└────────┘ └──────┘ └─────────┘ └──────────┘
```

## Quick Start

```python
# 1. Initialize the orchestrator
from giljo_mcp import create_orchestrator

orchestrator = create_orchestrator(
    project_name="legacy-code-refactor",
    tenant_key="refactor-bot-demo"
)

# 2. Define the refactoring mission
mission = """
Systematically refactor the legacy codebase to improve code quality.
Focus on readability, maintainability, and modern Python practices.
"""

# 3. Create the project
project = orchestrator.create_project(
    name="Legacy Code Refactoring",
    mission=mission
)

# 4. Spawn specialized agents
agents = orchestrator.spawn_agents([
    {"name": "analyzer", "type": "code_analyzer"},
    {"name": "linter", "type": "style_checker"},
    {"name": "refactor", "type": "code_transformer"},
    {"name": "validator", "type": "test_runner"}
])

# 5. Start the orchestration
orchestrator.execute()
```

## Full Implementation

See `refactor_bot.py` for the complete implementation with error handling, progress tracking, and customization options.

## Agent Roles

### Analyzer Agent

- Scans codebase for improvement opportunities
- Creates priority list of refactoring tasks
- Identifies patterns and anti-patterns

### Linter Agent

- Checks code against style guidelines
- Reports violations with fix suggestions
- Tracks improvement metrics

### Refactor Agent

- Executes actual code transformations
- Applies consistent patterns
- Ensures backward compatibility

### Validator Agent

- Runs tests after each refactoring
- Verifies no functionality broken
- Reports success/failure to orchestrator

## Customization

You can customize the refactoring rules by modifying the templates:

```python
from giljo_mcp.template_manager import TemplateManager

tm = TemplateManager(session, tenant_key, product_id)

# Customize analyzer focus
analyzer_mission = await tm.get_template(
    name="analyzer",
    augmentations="Focus on performance bottlenecks",
    variables={"max_complexity": 10}
)
```

## Expected Output

After running the refactoring bot:

1. **Analysis Report** - Detailed findings of code issues
2. **Refactoring Log** - All transformations applied
3. **Metrics Dashboard** - Before/after quality metrics
4. **Test Results** - Verification that nothing broke

## Next Steps

- Try modifying the agent templates for different refactoring strategies
- Add more specialized agents (e.g., security scanner, documentation writer)
- Integrate with CI/CD pipeline for automatic refactoring

## Troubleshooting

If agents aren't communicating:

```python
# Check message queue
messages = orchestrator.get_pending_messages("analyzer")
print(f"Pending: {len(messages)}")

# Verify agent health
health = orchestrator.check_agent_health("analyzer")
print(f"Status: {health['status']}")
```

## Learn More

- [Full API Documentation](../../docs/api/)
- [Agent Templates Guide](../../docs/guides/templates.md)
- [Orchestration Patterns](../../docs/patterns/)
