"""
MCPToolCatalogGenerator - Comprehensive MCP Tool Catalog for Orchestrators and Agents

Provides complete MCP tool definitions organized by category with usage patterns.
Generates full catalog for orchestrators and agent-type-specific subsets for spawned agents.

Key Features:
- 20+ MCP tools organized by category (orchestration, context, communication, tasks, project)
- Each tool includes: parameters, description, when-to-use guidance, and code examples
- Agent-type specific tool filtering (orchestrator gets all, implementer gets tasks+communication, etc.)
- Field priority support (respects mcp_tool_catalog priority setting)
- Complete orchestrator workflow pattern included
- Token-optimized formatting with clear structure

Handover 0270: Add Comprehensive MCP Tool Catalog
"""

import logging
from typing import ClassVar, Optional


logger = logging.getLogger(__name__)


class MCPToolCatalogGenerator:
    """Generate comprehensive MCP tool catalogs for orchestrators and agents."""

    # Tool definitions organized by category
    TOOLS: ClassVar[dict] = {
        "orchestration": {
            "get_orchestrator_instructions": {
                "params": ["job_id: str", "tenant_key: str"],
                "description": "Fetch context for orchestrator to CREATE mission plan",
                "returns": "Dict with project context, mission, agent templates, and field priorities",
                "when": [
                    "When orchestrator starts to get project requirements and available agents",
                    "To fetch condensed mission with context prioritization applied",
                    "To understand team composition and available specialists",
                ],
                "example": """# Orchestrator fetches mission
instructions = await get_orchestrator_instructions(
    job_id='orch-123',
    tenant_key='tenant-abc'
)

# Analyze requirements
mission = instructions['mission']  # Condensed with field priorities
templates = instructions.get('agent_templates', [])
""",
            },
            "spawn_agent_job": {
                "params": [
                    "agent_display_name: str",
                    "agent_name: str",
                    "mission: str",
                    "project_id: str",
                    "tenant_key: str",
                    "parent_job_id: Optional[str]",
                ],
                "description": "Create agent job in database and return thin prompt",
                "returns": "Dict with job_id, thin agent prompt, and token estimates",
                "when": [
                    "When orchestrator decides to spawn a specialist agent",
                    "To create database record linking agent to project",
                    "To generate thin prompt for agent to paste into Claude Code",
                ],
                "example": """# Orchestrator spawns implementer agent
result = await spawn_agent_job(
    agent_display_name='implementer',
    agent_name='Backend Developer',
    mission='Implement user authentication system',
    project_id='proj-123',
    tenant_key='tenant-abc',
    parent_job_id='orch-123'
)

agent_id = result['job_id']
prompt = result['agent_prompt']  # ~10 lines for agent to paste
""",
            },
            "get_workflow_status": {
                "params": ["project_id: str", "tenant_key: str"],
                "description": "Get current workflow status including active, completed, and failed agents",
                "returns": "Dict with agent counts, current stage, and progress percentage",
                "when": [
                    "To monitor progress of spawned agents",
                    "To check if all agents have completed their work",
                    "To understand which agents are stuck or failed",
                ],
                "example": """# Check workflow progress
status = await get_workflow_status(
    project_id='proj-123',
    tenant_key='tenant-abc'
)

active_count = status['active_agents']
progress = status['progress_percent']
if progress == 100:
    # All agents completed
    pass
""",
            },
        },
        "context": {
            "get_agent_mission": {
                "params": ["job_id: str", "tenant_key: str"],
                "description": "Fetch agent-specific mission and context (thin client pattern)",
                "returns": "Dict with mission, project context, parent orchestrator, and tokens",
                "when": [
                    "When spawned agent needs its full mission (called first by agent)",
                    "To retrieve context stored in database during spawn_agent_job",
                    "Part of thin client architecture - agent fetches instead of embedding",
                ],
                "example": """# Agent fetches its mission
mission = await get_agent_mission(
    job_id='agent-123',
    tenant_key='tenant-abc'
)

full_mission = mission['mission']  # ~2000 tokens of work
project_id = mission['project_id']
parent_orch_id = mission['parent_job_id']
""",
            },
            "get_available_agents": {
                "params": ["tenant_key: str", "active_only: bool"],
                "description": "Discover available specialist agents (orchestrator uses for planning)",
                "returns": "Dict with list of available agent templates and their capabilities",
                "when": [
                    "When orchestrator needs to decide which agents to spawn",
                    "To get list of available specialist types",
                    "For dynamic agent discovery (not static embedded templates)",
                ],
                "example": """# Orchestrator discovers available agents
agents = await get_available_agents(
    tenant_key='tenant-abc',
    active_only=True
)

agent_display_names = [a['agent_display_name'] for a in agents['agents']]
# Returns: ['implementer', 'tester', 'architect', 'documenter', ...]
""",
            },
        },
        "communication": {
            "send_message": {
                "params": [
                    "to_agents: list[str]",
                    "content: str",
                    "project_id: str",
                    "tenant_key: str",
                    "message_type: str",  # 'direct', 'broadcast', 'system'
                    "priority: str",  # 'low', 'normal', 'high'
                    "from_agent: Optional[str]",
                ],
                "description": "Send message to specific agents or broadcast to all (use to_agents=['all'])",
                "returns": "Dict with success status and message ID",
                "when": [
                    "When agents need to coordinate with each other",
                    "To send feedback, blockers, or questions",
                    "To broadcast status to all agents (to_agents=['all'])",
                ],
                "example": """# Send direct message to orchestrator
result = await send_message(
    to_agents=['orchestrator'],
    content='Blocked on database schema. Need guidance.',
    project_id='proj-123',
    tenant_key='tenant-abc',
    message_type='direct',
    priority='high',
    from_agent='implementer-1'
)

# Broadcast to all agents
result = await send_message(
    to_agents=['all'],
    content='Implementation complete. Ready for testing.',
    project_id='proj-123',
    tenant_key='tenant-abc',
    message_type='broadcast',
    priority='normal',
    from_agent='implementer-1'
)""",
            },
            "receive_messages": {
                "params": [
                    "agent_id: str",
                    "limit: int",
                ],
                "description": "Receive pending messages for an agent",
                "returns": "Dict with list of pending messages",
                "when": [
                    "When agent needs to check for messages from orchestrator or peers",
                    "At startup after fetching mission",
                    "Between major work phases",
                ],
                "example": """# Check for incoming messages
messages = await receive_messages(
    agent_id='implementer-1',
    limit=10
)

for msg in messages['messages']:
    print(f"From {msg['from_agent']}: {msg['content']}")
    # Messages are auto-acknowledged when retrieved
""",
            },
            "list_messages": {
                "params": [
                    "agent_id: Optional[str]",
                    "status: Optional[str]",
                    "limit: int",
                ],
                "description": "List messages with optional filters for history/inspection",
                "returns": "Dict with list of messages matching filters",
                "when": [
                    "To view message history",
                    "To check message status",
                    "For audit and debugging",
                ],
                "example": """# List recent messages for agent
messages = await list_messages(
    agent_id='implementer-1',
    status='pending',
    limit=20
)""",
            },
        },
        "tasks": {
            "update_job_progress": {
                "params": ["job_id: str", "percent_complete: int", "status_message: str", "tenant_key: str"],
                "description": "Update agent job progress and status",
                "returns": "Dict with success status and updated progress",
                "when": [
                    "When agent completes a milestone (every 10-20% progress)",
                    "To provide real-time status updates to orchestrator",
                    "When transitioning between major work phases",
                ],
                "example": """# Agent reports progress
await update_job_progress(
    job_id='agent-123',
    percent_complete=50,
    status_message='Database schema complete, starting API endpoints',
    tenant_key='tenant-abc'
)
""",
            },
            "complete_agent_job": {
                "params": [
                    "job_id: str",
                    "result_summary: str",
                    "key_artifacts: list[str]",
                    "tenant_key: str",
                ],
                "description": "Mark agent job as complete with final results",
                "returns": "Dict with completion confirmation and result storage info",
                "when": [
                    "When agent finishes all assigned work",
                    "To submit final deliverables and results",
                    "To signal to orchestrator that work is done",
                ],
                "example": """# Agent marks job complete
result = await complete_agent_job(
    job_id='agent-123',
    result_summary='Implemented all 5 API endpoints with tests',
    key_artifacts=['src/routes/auth.py', 'tests/test_auth.py'],
    tenant_key='tenant-abc'
)
""",
            },
            "report_job_error": {
                "params": [
                    "job_id: str",
                    "error_message: str",
                    "error_type: str",
                    "blocking: bool",
                    "tenant_key: str",
                ],
                "description": "Report error or blocker encountered during work",
                "returns": "Dict with error ID and escalation info",
                "when": [
                    "When encountering blocker preventing progress",
                    "To alert orchestrator to unexpected issues",
                    "When requiring input from other agents",
                ],
                "example": """# Agent reports blocking error
result = await report_job_error(
    job_id='agent-123',
    error_message='Database migration script syntax error on line 45',
    error_type='database_schema',
    blocking=True,
    tenant_key='tenant-abc'
)

error_id = result['error_id']
escalated_to = result.get('escalated_to')  # Orchestrator or peer agent
""",
            },
            "get_job_status": {
                "params": ["job_id: str", "tenant_key: str"],
                "description": "Fetch detailed status of specific agent job",
                "returns": "Dict with status, progress, messages, errors, and timeline",
                "when": [
                    "To check own status or monitor peer agents",
                    "When deciding whether to proceed or wait",
                    "For status reporting to orchestrator",
                ],
                "example": """# Check agent job status
status = await get_job_status(
    job_id='agent-456',
    tenant_key='tenant-abc'
)

progress = status['progress_percent']
current_phase = status['current_phase']
errors = status.get('errors', [])
""",
            },
        },
        "project": {
            "update_project_mission": {
                "params": [
                    "project_id: str",
                    "mission: str",
                    "tenant_key: str",
                ],
                "description": "Update project mission with generated execution plan",
                "returns": "Dict with success status and mission metadata",
                "when": [
                    "When orchestrator creates execution plan from requirements",
                    "To persist mission for tracking and history",
                    "After analyzing product vision and requirements",
                ],
                "example": """# Orchestrator saves mission plan
result = await update_project_mission(
    project_id='proj-123',
    mission='\"\"\"Detailed execution plan: ...'
    tenant_key='tenant-abc'
)
""",
            },
            "get_project_context": {
                "params": ["project_id: str", "tenant_key: str"],
                "description": "Fetch project requirements, status, and team context",
                "returns": "Dict with project name, description, mission, and agent assignments",
                "when": [
                    "When agent needs full project context",
                    "To understand scope and dependencies",
                    "For planning interactions with other agents",
                ],
                "example": """# Get project context
context = await get_project_context(
    project_id='proj-123',
    tenant_key='tenant-abc'
)

requirements = context['description']  # Original user requirements
current_mission = context['mission']  # Generated execution plan
""",
            },
            "activate_project": {
                "params": ["project_id: str", "tenant_key: str"],
                "description": "Activate project for orchestration",
                "returns": "Dict with activation confirmation and project status",
                "when": [
                    "When starting orchestration on a project",
                    "To transition from planning to execution phase",
                ],
                "example": """# Activate project
result = await activate_project(
    project_id='proj-123',
    tenant_key='tenant-abc'
)
""",
            },
            "close_project": {
                "params": [
                    "project_id: str",
                    "summary: str",
                    "key_outcomes: list[str]",
                    "tenant_key: str",
                ],
                "description": "Close project and update 360-degree memory",
                "returns": "Dict with closeout confirmation and memory update",
                "when": [
                    "When project work is complete",
                    "To archive learnings and decisions for future reference",
                    "To update product 360-memory with project results",
                ],
                "example": """# Close project and capture knowledge
result = await close_project(
    project_id='proj-123',
    summary='Completed user authentication system with OAuth2 and 2FA',
    key_outcomes=['OAuth2 implementation', '95% test coverage', 'Security audit passed'],
    tenant_key='tenant-abc'
)
""",
            },
            "get_project_members": {
                "params": ["project_id: str", "tenant_key: str"],
                "description": "Get list of all agents assigned to project",
                "returns": "Dict with agent list, their status, and assignments",
                "when": [
                    "To understand team composition",
                    "For coordinating between team members",
                    "To see who is responsible for which parts",
                ],
                "example": """# See who's on the team
members = await get_project_members(
    project_id='proj-123',
    tenant_key='tenant-abc'
)

for agent in members['agents']:
    agent_display_name = agent['agent_display_name']
    status = agent['status']  # working, waiting, complete
    assignment = agent['assignment']  # Their specific mission
""",
            },
        },
    }

    # Agent-type specific tool mappings
    AGENT_TOOL_MAPPINGS: ClassVar[dict] = {
        "orchestrator": [
            "orchestration.get_orchestrator_instructions",
            "orchestration.spawn_agent_job",
            "orchestration.get_workflow_status",
            "context.get_agent_mission",
            "context.get_available_agents",
            "communication.send_message",
            "communication.receive_messages",
            "communication.list_messages",
            "tasks.get_job_status",
            "project.update_project_mission",
            "project.get_project_context",
            "project.activate_project",
            "project.get_project_members",
        ],
        "implementer": [
            "context.get_agent_mission",
            "communication.send_message",
            "communication.receive_messages",
            "tasks.update_job_progress",
            "tasks.complete_agent_job",
            "tasks.report_job_error",
            "tasks.get_job_status",
            "project.get_project_context",
        ],
        "tester": [
            "context.get_agent_mission",
            "communication.send_message",
            "communication.receive_messages",
            "tasks.update_job_progress",
            "tasks.complete_agent_job",
            "tasks.report_job_error",
            "tasks.get_job_status",
            "project.get_project_context",
        ],
        "architect": [
            "context.get_agent_mission",
            "context.get_available_agents",
            "communication.send_message",
            "communication.receive_messages",
            "tasks.update_job_progress",
            "tasks.complete_agent_job",
            "project.get_project_context",
            "project.get_project_members",
        ],
        "documenter": [
            "context.get_agent_mission",
            "communication.send_message",
            "communication.receive_messages",
            "tasks.update_job_progress",
            "tasks.complete_agent_job",
            "project.get_project_context",
            "project.get_project_members",
        ],
    }

    def __init__(self):
        """Initialize catalog generator."""
        logger.debug("MCPToolCatalogGenerator initialized")

    def generate_full_catalog(self, field_priorities: Optional[dict] = None) -> str:
        """
        Generate complete MCP tool catalog for orchestrators.

        Args:
            field_priorities: Optional field priorities dict to check mcp_tool_catalog priority

        Returns:
            Formatted Markdown string with all tools organized by category
        """
        # Check if catalog should be included based on field priorities
        if field_priorities and field_priorities.get("mcp_tool_catalog", 1) == 0:
            logger.debug("MCP tool catalog excluded due to field priority")
            return ""

        catalog = """# MCP Tool Catalog

Complete reference for all available MCP tools for orchestration, context management, communication, and task coordination.

## Categories

1. **Orchestration** - Orchestrator coordination and workflow management
2. **Context** - Context fetching and agent mission management
3. **Communication** - Inter-agent messaging and coordination
4. **Tasks** - Agent job progress tracking and completion
5. **Project** - Project lifecycle and team management

---

"""

        # Generate sections for each category
        for category_name in ["orchestration", "context", "communication", "tasks", "project"]:
            category = self.TOOLS.get(category_name, {})
            if not category:
                continue

            catalog += self._generate_category_section(category_name, category)
            catalog += "\n"

        # Add workflow pattern section
        catalog += self._generate_usage_workflow()

        return catalog

    def _generate_category_section(self, category_name: str, tools: dict) -> str:
        """
        Generate Markdown section for a tool category.

        Args:
            category_name: Category name (orchestration, context, etc.)
            tools: Dict of tools in this category

        Returns:
            Formatted Markdown section
        """
        # Format category name nicely
        formatted_name = category_name.replace("_", " ").title()

        section = f"## {formatted_name} Tools\n\n"

        for tool_name, tool_info in tools.items():
            section += f"### {tool_name}\n\n"
            section += f"**Description**: {tool_info.get('description', 'N/A')}\n\n"

            # Parameters
            params = tool_info.get("params", [])
            if params:
                section += "**Parameters**:\n"
                for param in params:
                    section += f"- `{param}`\n"
                section += "\n"

            # Returns
            returns = tool_info.get("returns", "N/A")
            section += f"**Returns**: {returns}\n\n"

            # When to use
            when_list = tool_info.get("when", [])
            if when_list:
                section += "**When to use**:\n"
                for use_case in when_list:
                    section += f"- {use_case}\n"
                section += "\n"

            # Example
            example = tool_info.get("example", "")
            if example:
                section += "**Example**:\n```python\n"
                section += example.strip()
                section += "\n```\n\n"

            section += "---\n\n"

        return section

    def _generate_usage_workflow(self) -> str:
        """
        Generate typical orchestrator workflow pattern.

        Returns:
            Markdown string with workflow example
        """
        workflow = """## Typical Orchestrator Workflow

### Complete Orchestration Pattern

```python
# Step 1: Orchestrator fetches mission and available agents
instructions = await get_orchestrator_instructions(
    job_id='orch-id',
    tenant_key='tenant-key'
)

mission = instructions['mission']
available_agents = await get_available_agents(
    tenant_key='tenant-key',
    active_only=True
)

# Step 2: Analyze mission and create work breakdown
agents_needed = [
    ('implementer', 'Backend Developer', 'Implement API endpoints'),
    ('tester', 'QA Engineer', 'Write integration tests'),
    ('documenter', 'Tech Writer', 'Create API documentation'),
]

# Step 3: Update project with execution plan
await update_project_mission(
    project_id='proj-id',
    mission=f'Execution Plan:\\n' + '\\n'.join([f'- {name}: {mission}' for _, name, mission in agents_needed]),
    tenant_key='tenant-key'
)

# Step 4: Spawn agents
spawned_agents = {}
for agent_display_name, agent_name, work_mission in agents_needed:
    result = await spawn_agent_job(
        agent_display_name=agent_display_name,
        agent_name=agent_name,
        mission=work_mission,
        project_id='proj-id',
        tenant_key='tenant-key',
        parent_job_id='orch-id'
    )
    spawned_agents[agent_display_name] = result['job_id']
    print(f"Spawned {agent_name}: {result['agent_prompt']}")

# Step 5: Monitor progress
while True:
    status = await get_workflow_status(
        project_id='proj-id',
        tenant_key='tenant-key'
    )

    if status['progress_percent'] == 100:
        print("All agents completed!")
        break

    if status['failed_agents'] > 0:
        print(f"Warning: {status['failed_agents']} agents failed")
        # Handle failures
        break

    print(f"Progress: {status['progress_percent']}%")
    await asyncio.sleep(5)

# Step 6: Close project
await close_project(
    project_id='proj-id',
    summary='Successfully completed all development tasks',
    key_outcomes=['API endpoints', 'Test suite', 'Documentation'],
    tenant_key='tenant-key'
)
```

### Agent Execution Pattern

```python
# Step 1: Agent receives thin prompt with job ID and fetches full mission
mission = await get_agent_mission(
    job_id='agent-id',
    tenant_key='tenant-key'
)

project_context = await get_project_context(
    project_id=mission['project_id'],
    tenant_key='tenant-key'
)

# Step 2: Agent checks for incoming messages
messages = await receive_messages(
    agent_id='agent-id',
    limit=10
)

for msg in messages['messages']:
    print(f"Message from {msg['from_agent']}: {msg['content']}")
    # Messages are auto-acknowledged when retrieved

# Step 3: Agent works and reports progress
await update_job_progress(
    job_id='agent-id',
    percent_complete=25,
    status_message='Downloaded codebase and analyzed structure',
    tenant_key='tenant-key'
)

# Do actual work...
implement_features()

# Step 4: Agent can coordinate with peers
await send_message(
    to_agents=['other-agent-id'],
    content='Need clarification on database schema for users table',
    project_id='proj-id',
    tenant_key='tenant-key',
    message_type='direct',
    priority='normal',
    from_agent='agent-id'
)

# Step 5: Agent completes work
await complete_agent_job(
    job_id='agent-id',
    result_summary='Implemented 5 backend endpoints with full test coverage',
    key_artifacts=['src/routes/api.py', 'tests/test_api.py'],
    tenant_key='tenant-key'
)
```

---
"""
        return workflow

    def generate_for_agent(self, agent_display_name: str) -> str:
        """
        Generate agent-type-specific tool subset.

        Args:
            agent_display_name: Type of agent (implementer, tester, architect, etc.)

        Returns:
            Formatted Markdown string with relevant tools only
        """
        # Get tool references for this agent type
        tool_refs = self.AGENT_TOOL_MAPPINGS.get(agent_display_name, [])

        if not tool_refs:
            logger.warning(f"Unknown agent type: {agent_display_name}")
            return ""

        # Build catalog with only relevant tools
        catalog = f"# MCP Tools for {agent_display_name.title()} Agent\n\n"
        catalog += f"This is a curated subset of MCP tools relevant for {agent_display_name} work.\n\n"

        seen_categories = set()

        for tool_ref in tool_refs:
            parts = tool_ref.split(".")
            if len(parts) != 2:
                continue

            category_name, tool_name = parts
            category = self.TOOLS.get(category_name, {})
            tool_info = category.get(tool_name)

            if not tool_info:
                continue

            # Add category header if not seen
            if category_name not in seen_categories:
                formatted_name = category_name.replace("_", " ").title()
                catalog += f"## {formatted_name} Tools\n\n"
                seen_categories.add(category_name)

            # Add tool
            catalog += f"### {tool_name}\n\n"
            catalog += f"**Description**: {tool_info.get('description', 'N/A')}\n\n"

            params = tool_info.get("params", [])
            if params:
                catalog += "**Parameters**:\n"
                for param in params:
                    catalog += f"- `{param}`\n"
                catalog += "\n"

            returns = tool_info.get("returns", "N/A")
            catalog += f"**Returns**: {returns}\n\n"

            when_list = tool_info.get("when", [])
            if when_list:
                catalog += "**When to use**:\n"
                for use_case in when_list:
                    catalog += f"- {use_case}\n"
                catalog += "\n"

            example = tool_info.get("example", "")
            if example:
                catalog += "**Example**:\n```python\n"
                catalog += example.strip()
                catalog += "\n```\n\n"

            catalog += "---\n\n"

        # Add workflow section relevant to agent type
        if agent_display_name == "orchestrator":
            catalog += self._generate_usage_workflow()
        else:
            catalog += "## Quick Start\n\n1. Call `get_agent_mission()` to fetch your assignment\n"
            catalog += "2. Call `get_project_context()` to understand the project\n"
            catalog += "3. Call `update_job_progress()` to report status every 10-20% completion\n"
            catalog += "4. Call `send_message()` if you need help from other agents\n"
            catalog += "5. Call `complete_agent_job()` when finished\n\n"

        return catalog
