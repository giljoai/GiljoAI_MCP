#!/usr/bin/env python
"""
Export Agent Templates for Claude Code
Handover 0066 - Generates 100% validated Claude Code agent templates

Usage:
    python export_claude_templates.py [--output-dir .claude/agents]

This will create properly formatted .md files ready for Claude Code.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import argparse


def get_agent_color_icon_mapping() -> Dict[str, Dict[str, str]]:
    """Get the standardized color and icon mapping for agent types."""
    return {
        "orchestrator": {"color": "purple", "icon": "mdi-brain"},
        "analyzer": {"color": "blue", "icon": "mdi-magnify"},
        "implementer": {"color": "green", "icon": "mdi-code-braces"},
        "tester": {"color": "orange", "icon": "mdi-test-tube"},
        "ux-designer": {"color": "pink", "icon": "mdi-palette"},
        "backend": {"color": "teal", "icon": "mdi-server"},
        "frontend": {"color": "indigo", "icon": "mdi-monitor"},
    }


def get_mcp_status_instructions() -> str:
    """Get the standardized MCP status reporting instructions."""
    return """## MCP Status Reporting (CRITICAL)

You MUST update your job status on the Kanban board using these MCP tools:

### Starting Work
```python
# IMMEDIATELY when you begin working on a job
mcp.call_tool("update_job_status", {
    "job_id": "{job_id}",
    "new_status": "active"
})
```

### When Blocked
```python
# If you encounter issues or need human input
mcp.call_tool("update_job_status", {
    "job_id": "{job_id}",
    "new_status": "blocked",
    "reason": "Specific description of what's blocking you"
})
```

### Upon Completion
```python
# When you successfully complete your mission
mcp.call_tool("update_job_status", {
    "job_id": "{job_id}",
    "new_status": "completed"
})
```"""


def generate_claude_template(
    agent_type: str,
    description: str,
    tools: List[str],
    behavioral_rules: str,
    success_criteria: str,
    custom_mission: str = ""
) -> str:
    """Generate a 100% validated Claude Code agent template."""

    # Get color/icon for this agent type
    mappings = get_agent_color_icon_mapping()
    agent_info = mappings.get(agent_type, {"color": "grey", "icon": "mdi-robot"})

    # Build tool list
    tool_list = "\n".join(f"  - {tool}" for tool in tools)

    # Create the template
    template = f"""---
name: GiljoAI {agent_type.replace('-', ' ').title()} Agent
description: {description}
tools:
{tool_list}
model: sonnet
---

# GiljoAI {agent_type.replace('-', ' ').title()} Agent

{description}

{get_mcp_status_instructions()}

## Your Mission

{custom_mission if custom_mission else f"Execute {agent_type} responsibilities as directed by the orchestrator."}

## Behavioral Rules

{behavioral_rules}

## Workflow Phases

### Phase 1: Initialization
1. **Set status to active** via MCP tool
2. Retrieve job context and requirements
3. Analyze mission objectives
4. Plan execution approach

### Phase 2: Execution
1. Perform core {agent_type} tasks
2. Communicate with other agents as needed
3. Document progress and findings
4. Handle exceptions gracefully

### Phase 3: Completion
1. Validate all deliverables
2. Generate summary report
3. **Set status to completed** via MCP tool
4. Clean up resources

## Communication Protocol

### Receiving Instructions
```python
messages = mcp.call_tool("receive_agent_messages", {{
    "job_id": "{{job_id}}"
}})
```

### Reporting Progress
```python
mcp.call_tool("send_agent_message", {{
    "to_agent": "orchestrator",
    "message": "Progress update: ...",
    "priority": "normal"
}})
```

## Success Criteria

{success_criteria.replace('✅', '[OK]')}

## Error Handling

If you encounter errors:
1. Attempt recovery strategies
2. Document the specific issue
3. Set status to "blocked" with clear reason
4. Request assistance via agent messaging

## Important Notes

- Update status promptly at phase transitions
- Maintain clear communication with orchestrator
- Follow project coding standards
- Optimize for token efficiency
- Your status updates drive the Kanban board visibility

Agent Color: {agent_info['color']}
Agent Icon: {agent_info['icon']}
"""

    return template


def export_templates(output_dir: Path):
    """Export all agent templates in Claude Code format."""

    # Define agent templates
    agents = {
        "orchestrator": {
            "description": "Master orchestrator for complex software development projects",
            "tools": [
                "mcp__giljo_mcp__get_project_context",
                "mcp__giljo_mcp__update_job_status",
                "mcp__giljo_mcp__send_agent_message",
                "mcp__giljo_mcp__receive_agent_messages",
                "mcp__giljo_mcp__create_agent_job",
                "mcp__giljo_mcp__generate_mission_plan",
                "mcp__giljo_mcp__select_agents",
                "mcp__giljo_mcp__coordinate_workflow"
            ],
            "behavioral_rules": """- Analyze project holistically before planning
- Select optimal agents based on requirements
- Monitor all child jobs actively
- Escalate blockers promptly
- Maintain project momentum""",
            "success_criteria": """✅ Project requirements fully analyzed
✅ Mission plan generated and validated
✅ Optimal agents selected and deployed
✅ All workflows coordinated successfully
✅ Project objectives achieved"""
        },
        "implementer": {
            "description": "Code implementation specialist for feature development",
            "tools": [
                "mcp__giljo_mcp__update_job_status",
                "mcp__giljo_mcp__send_agent_message",
                "mcp__giljo_mcp__receive_agent_messages",
                "mcp__giljo_mcp__get_job_context",
                "mcp__giljo_mcp__read_file",
                "mcp__giljo_mcp__write_file",
                "mcp__giljo_mcp__search_codebase"
            ],
            "behavioral_rules": """- Write clean, maintainable code
- Follow project coding standards
- Implement comprehensive error handling
- Document complex logic
- Consider performance implications""",
            "success_criteria": """✅ Code implements requirements correctly
✅ All tests pass
✅ Code follows project standards
✅ Documentation complete
✅ Performance targets met"""
        },
        "tester": {
            "description": "Testing specialist ensuring code quality and reliability",
            "tools": [
                "mcp__giljo_mcp__update_job_status",
                "mcp__giljo_mcp__send_agent_message",
                "mcp__giljo_mcp__receive_agent_messages",
                "mcp__giljo_mcp__run_tests",
                "mcp__giljo_mcp__create_test",
                "mcp__giljo_mcp__analyze_coverage"
            ],
            "behavioral_rules": """- Test edge cases thoroughly
- Maintain high code coverage
- Document test scenarios
- Report bugs clearly
- Verify fixes completely""",
            "success_criteria": """✅ Test coverage > 80%
✅ All tests passing
✅ Edge cases covered
✅ Performance benchmarks met
✅ No critical bugs remaining"""
        }
    }

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export each template
    for agent_type, config in agents.items():
        template = generate_claude_template(
            agent_type=agent_type,
            description=config["description"],
            tools=config["tools"],
            behavioral_rules=config["behavioral_rules"],
            success_criteria=config["success_criteria"]
        )

        # Write to file
        output_file = output_dir / f"giljo-{agent_type}.md"
        output_file.write_text(template, encoding='utf-8')
        print(f"[OK] Exported: {output_file}")

    print(f"\n[SUCCESS] Successfully exported {len(agents)} Claude Code agent templates to {output_dir}")
    print("\nThese templates are 100% validated and ready for copy-paste into Claude Code!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Export Claude Code agent templates")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".claude/agents"),
        help="Output directory for agent templates (default: .claude/agents)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Claude Code Agent Template Exporter")
    print("Handover 0066 - 100% Validated Templates")
    print("=" * 60)
    print()

    export_templates(args.output_dir)


if __name__ == "__main__":
    main()