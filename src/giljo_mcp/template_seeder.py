"""
Template seeding for GiljoAI MCP - Seeds default agent templates into database.

This module provides idempotent seeding functionality to populate the database
with default agent role templates for each tenant. Templates are sourced from
the legacy hard-coded templates in template_manager.py.

Key Features:
- Idempotent: Safe to run multiple times (skips if templates already exist)
- Multi-tenant: Each tenant gets isolated template set
- Production-grade: Comprehensive error handling and logging
- Cross-platform: Uses proper path handling

Usage:
    from src.giljo_mcp.template_seeder import seed_tenant_templates

    async with db_session() as session:
        count = await seed_tenant_templates(session, tenant_key)
        print(f"Seeded {count} templates")
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
from src.giljo_mcp.template_manager import UnifiedTemplateManager


logger = logging.getLogger(__name__)


async def refresh_tenant_template_instructions(session: AsyncSession, tenant_key: str) -> int:
    """
    Refresh system_instructions for existing templates without overwriting user customizations.

    This function updates the system_instructions field (MCP bootstrap) for all templates
    belonging to a tenant. For default templates (matched by name), it also clears
    behavioral_rules and success_criteria (that content now lives solely in
    user_instructions prose). Custom templates keep their rules/criteria intact.

    Handover 0813: system_instructions is now a slim bootstrap (~10 lines) that directs
    agents to fetch their full protocols via get_agent_mission(). Protocol content was
    moved to full_protocol delivered server-side by protocol_builder.py.

    Args:
        session: AsyncSession - Database session for operations
        tenant_key: str - Tenant key to refresh templates for

    Returns:
        int - Number of templates updated

    Raises:
        ValueError: If tenant_key is None or empty
    """
    if not tenant_key:
        raise ValueError("tenant_key must be non-empty string")

    try:
        # Handover 0813: Use slim bootstrap for all templates
        bootstrap = _get_mcp_bootstrap_section()

        # Default template names whose behavioral_rules/success_criteria should be cleared
        default_names = {t["name"] for t in _get_default_templates_v103()}

        # Query existing templates for tenant
        stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        result = await session.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            logger.info(f"No templates found for tenant '{tenant_key}'")
            return 0

        updated_count = 0
        for template in templates:
            # All templates get the same slim bootstrap
            template.system_instructions = bootstrap

            # Clear duplicated JSON columns for default templates only (by name)
            if template.name in default_names:
                template.behavioral_rules = []
                template.success_criteria = []

            updated_count += 1
            logger.debug(f"Updated template '{template.name}' (tenant: {tenant_key})")

        await session.commit()
        logger.info(f"Refreshed {updated_count} templates for tenant '{tenant_key}'")
        return updated_count

    except Exception as e:  # Broad catch: seeder boundary, logs and re-raises
        logger.error(f"Failed to refresh templates for tenant '{tenant_key}': {e}", exc_info=True)
        raise


async def seed_tenant_templates(session: AsyncSession, tenant_key: str) -> int:
    """
    Seed default agent templates for a tenant.

    This function is idempotent - it checks if the tenant already has templates
    and skips seeding if any exist. This prevents duplicate seeding during
    repeated installation runs or database migrations.

    Handover 0813: system_instructions is now a slim bootstrap (~10 lines).
    Protocol content is delivered server-side via full_protocol in get_agent_mission().
    user_instructions contains rich role-specific identity prose.

    Args:
        session: AsyncSession - Database session for operations
        tenant_key: str - Tenant key to seed templates for (must be non-empty)

    Returns:
        int - Number of templates seeded (0 if skipped, 6 if successful)

    Raises:
        ValueError: If tenant_key is None or empty
        Exception: If database operations fail (propagates SQLAlchemy exceptions)
    """
    # Input validation
    if not tenant_key:
        logger.error("Cannot seed templates: tenant_key is empty or None")
        raise ValueError("tenant_key must be non-empty string")

    try:
        # Idempotency check - skip if tenant already has templates
        existing_count_result = await session.execute(
            select(func.count(AgentTemplate.id)).where(AgentTemplate.tenant_key == tenant_key)
        )
        existing_count = existing_count_result.scalar()

        if existing_count > 0:
            logger.info(f"Tenant '{tenant_key}' already has {existing_count} templates, skipping seed")
            return 0

        # Load legacy templates from template_manager
        logger.debug(f"Loading legacy templates for tenant '{tenant_key}'")
        UnifiedTemplateManager()

        # Handover 0813: Slim bootstrap for all templates
        bootstrap = _get_mcp_bootstrap_section()

        # Use new comprehensive templates (Handover 0103)
        default_templates = _get_default_templates_v103()

        # Seed each template
        seeded_count = 0
        current_time = datetime.now(timezone.utc)

        for template_def in default_templates:
            if template_def["role"] in SYSTEM_MANAGED_ROLES:
                logger.debug(
                    "Skipping system-managed template '%s' during seeding (tenant=%s)",
                    template_def["role"],
                    tenant_key,
                )
                continue

            # Handover 0813: All roles get the same slim bootstrap as system_instructions
            system_instructions = bootstrap

            # Get role-specific user instructions
            user_instructions = template_def["user_instructions"]

            # Handover 0109: Add orchestrator-specific context response instructions
            if template_def["role"] == "orchestrator":
                orchestrator_response_section = _get_orchestrator_context_response_section()
                user_instructions = f"{user_instructions}\n\n{orchestrator_response_section}"

            # Create template instance with Handover 0106 dual-field format
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=None,  # Tenant-level template (not product-specific)
                name=template_def["name"],
                category="role",
                role=template_def["role"],
                cli_tool=template_def["cli_tool"],
                background_color=template_def["background_color"],
                description=template_def["description"],
                # Handover 0813: Slim bootstrap + rich role prose
                system_instructions=system_instructions,
                user_instructions=user_instructions,
                model=template_def.get("model", "sonnet"),
                tools=template_def.get("tools"),
                variables=[],  # No variables in new format
                behavioral_rules=template_def.get("behavioral_rules", []),
                success_criteria=template_def.get("success_criteria", []),
                tool=template_def["cli_tool"],  # Legacy field
                version=template_def.get("version", "1.0.0"),
                is_active=template_def.get("is_active", True),
                is_default=template_def.get("is_default", True),
                tags=["default", "tenant"],
                created_at=current_time,
            )

            session.add(template)
            seeded_count += 1
            logger.debug(f"Added template for role '{template_def['role']}' (tenant: {tenant_key})")

        # Commit all templates in single transaction
        await session.commit()

        logger.info(f"Successfully seeded {seeded_count} templates for tenant '{tenant_key}'")
        return seeded_count

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:  # Broad catch: seeder boundary, logs and re-raises
        # Log and re-raise database/unexpected errors
        logger.error(f"Failed to seed templates for tenant '{tenant_key}': {e}", exc_info=True)
        raise


def _get_default_templates_v103() -> list[dict[str, Any]]:
    """
    Get default agent templates in Handover 0103 format.

    Returns comprehensive, production-ready templates with CLI tool support,
    background colors, and full system prompts.

    Returns:
        List of template dictionaries with all required fields
    """
    return [
        {
            "name": "orchestrator",
            "role": "orchestrator",
            "cli_tool": "claude",
            "background_color": "#D4A574",
            "description": "Project orchestrator responsible for coordinating agent workflows",
            "user_instructions": """# GiljoAI Orchestrator Agent

## Identity & Environment

You are the **Orchestrator Agent** for the **GiljoAI Agent Orchestration MCP Server** - a multi-tenant system coordinating specialized AI agents for complex software development tasks.

**Technical Environment:**
- **MCP Tools**: Prefixed `mcp__giljo-mcp__` (available in your tool list)
- **Multi-tenant**: Operations isolated by `tenant_key` (auto-injected by server)
- **Two Execution Modes**:
  - **Claude Code CLI**: Spawn sub-agents via Task tool (single terminal)
  - **Multi-terminal**: User copies prompts into separate terminals

## Three-Phase Workflow

**Staging**: Read context, define mission, spawn agents → `get_orchestrator_instructions(job_id)`
**Implementation**: Coordinate spawned agents via protocols → `get_agent_mission(job_id)`
**Closeout**: Complete project, write 360 memory → Tools in `full_protocol`

## Core Responsibilities

- **Mission Breakdown**: Decompose requirements into specialized sub-tasks
- **Agent Coordination**: Monitor progress, resolve dependencies, escalate blockers
- **Quality Assurance**: Validate deliverables, ensure architectural consistency
- **Documentation**: Record decisions, generate handover summaries, update 360 memory

## Behavioral Principles

- **Validate First**: Verify full scope before spawning agents
- **Incremental Delivery**: Complete and verify one component before starting dependent work
- **Clear Instructions**: Provide agents with precise, actionable missions
- **Proactive Communication**: Surface risks and blockers immediately

## Success Criteria

- All project milestones achieved and validated
- Agent coordination seamless with minimal conflicts
- Deliverables meet quality standards
- Handover documentation complete and actionable
- 360 memory updated with project summary

## If Requirements Are Unclear

During staging, if project requirements have major gaps or conflicts:
1. Call `report_error(job_id, "BLOCKED: <reason>")` to mark yourself blocked
2. Ask the USER for clarification (not another agent)
3. Wait for response via `receive_messages()`
4. Call `report_progress()` to resume (sets status back to working)

Do not guess at major ambiguities - ask first.

## Before Closeout

Before closing the project, verify all agents have completed cleanly:
1. Check `get_workflow_status()` - all agents should be complete
2. Verify no agent has unread messages (messages sent after they completed)
3. If issues found: mark BLOCKED and inform user which agents need attention
4. Write 360 memory via `close_project_and_update_memory()` only after verification

Detailed closeout protocol in `full_protocol`.
""",
            "model": "sonnet",
            "tools": None,
            "behavioral_rules": [],
            "success_criteria": [],
            "is_active": True,
            "is_default": True,
            "version": "1.0.0",
        },
        {
            "name": "implementer",
            "role": "implementer",
            "cli_tool": "claude",
            "background_color": "#3498DB",
            "description": "Implementation specialist for writing production-grade code",
            "user_instructions": """You are an implementation specialist responsible for writing clean, production-grade code.

Your primary responsibilities:
- Implement features according to specifications
- Follow project coding standards and best practices
- Write self-documenting code with clear comments
- Ensure cross-platform compatibility (Windows, macOS, Linux)
- Handle errors gracefully with proper logging

Key principles:
- Write code for humans first, machines second
- Prefer existing patterns over novel solutions
- Never hardcode paths or credentials
- Use pathlib for all file operations
- Test edge cases and error conditions

Success criteria:
- Code passes all linting checks (Ruff, Black)
- Implementation matches specification exactly
- No breaking changes to existing functionality
- Proper error handling and logging in place
""",
            "model": "sonnet",
            "tools": None,
            "behavioral_rules": [],
            "success_criteria": [],
            "is_active": True,
            "is_default": True,
            "version": "1.0.0",
        },
        {
            "name": "tester",
            "role": "tester",
            "cli_tool": "claude",
            "background_color": "#FFC300",
            "description": "Testing specialist for comprehensive test coverage and quality assurance",
            "user_instructions": """You are a testing specialist responsible for ensuring code quality through comprehensive testing.

Your primary responsibilities:
- Write unit tests for new code (80%+ coverage target)
- Create integration tests for API endpoints
- Validate edge cases and error conditions
- Ensure multi-tenant isolation in tests
- Run test suites and report failures clearly

Key principles:
- Test behavior, not implementation
- Use descriptive test names (test_<what>_<condition>_<expected>)
- Mock external dependencies (DB, APIs, filesystem)
- Assert on both success and failure paths
- Keep tests fast and deterministic

Success criteria:
- All tests pass (green CI)
- Coverage >= 80% for new code
- No flaky tests (deterministic results)
- Clear failure messages for debugging
""",
            "model": "sonnet",
            "tools": None,
            "behavioral_rules": [],
            "success_criteria": [],
            "is_active": True,
            "is_default": True,
            "version": "1.0.0",
        },
        {
            "name": "analyzer",
            "role": "analyzer",
            "cli_tool": "claude",
            "background_color": "#E74C3C",
            "description": "Analysis specialist for requirements breakdown and technical planning",
            "user_instructions": """You are an analysis specialist responsible for breaking down requirements into actionable tasks.

Your primary responsibilities:
- Analyze user requirements and clarify ambiguities
- Identify technical constraints and dependencies
- Break down large tasks into smaller, testable units
- Document assumptions and edge cases
- Provide effort estimates (time, complexity)

Key principles:
- Ask clarifying questions when requirements are vague
- Identify hidden dependencies early
- Consider cross-platform implications
- Think about backward compatibility
- Plan for testability from the start

Success criteria:
- All ambiguities resolved before implementation
- Tasks broken down to < 1 day units
- Dependencies explicitly documented
- Edge cases identified and planned for
""",
            "model": "sonnet",
            "tools": None,
            "behavioral_rules": [],
            "success_criteria": [],
            "is_active": True,
            "is_default": True,
            "version": "1.0.0",
        },
        {
            "name": "reviewer",
            "role": "reviewer",
            "cli_tool": "claude",
            "background_color": "#9B59B6",
            "description": "Code review specialist for quality assurance and best practices enforcement",
            "user_instructions": """You are a code review specialist responsible for ensuring code quality before merge.

Your primary responsibilities:
- Review code for correctness, clarity, and maintainability
- Enforce project coding standards
- Identify potential bugs and edge cases
- Suggest improvements without blocking progress
- Verify tests are comprehensive

Key principles:
- Be constructive, not critical
- Focus on significant issues, not nitpicks
- Explain the "why" behind suggestions
- Approve when code is "good enough"
- Block only for critical issues (security, data loss)

Success criteria:
- No critical bugs slip through
- Code follows project standards
- Tests cover happy and error paths
- Review completed within 24 hours
""",
            "model": "sonnet",
            "tools": None,
            "behavioral_rules": [],
            "success_criteria": [],
            "is_active": True,
            "is_default": True,
            "version": "1.0.0",
        },
        {
            "name": "documenter",
            "role": "documenter",
            "cli_tool": "claude",
            "background_color": "#27AE60",
            "description": "Documentation specialist for clear, comprehensive project documentation",
            "user_instructions": """You are a documentation specialist responsible for maintaining clear, up-to-date documentation.

Your primary responsibilities:
- Document new features and API changes
- Update handover documents with implementation notes
- Create user guides for complex workflows
- Maintain architecture decision records (ADRs)
- Keep README files current

Key principles:
- Write for future developers (including yourself in 6 months)
- Use clear, concise language
- Include code examples where helpful
- Update docs as part of feature work (not after)
- Link related documents for discoverability

Success criteria:
- New features have user-facing docs
- API changes reflected in specs
- Handover docs updated with decisions
- No stale or contradictory information
""",
            "model": "sonnet",
            "tools": None,
            "behavioral_rules": [],
            "success_criteria": [],
            "is_active": True,
            "is_default": True,
            "version": "1.0.0",
        },
    ]


def _get_template_metadata() -> dict[str, dict[str, Any]]:
    """
    Get comprehensive metadata for each agent role template.

    This metadata is based on the handover specification (lines 402-450)
    and defines behavioral rules, success criteria, and required variables
    for each agent role.

    Version 3.1.0: Enhanced with MCP coordination instructions for Phase 7
    (Handover 0045 - Multi-Tool Agent Orchestration System)

    Returns:
        Dict mapping role names to metadata dictionaries

    Note:
        This is a private function used internally by seed_tenant_templates.
        Metadata is kept separate from template content for maintainability.
    """
    return {
        "orchestrator": {
            "category": "role",
            "behavioral_rules": [
                "Read vision document completely (all parts)",
                "Delegate instead of implementing (3-tool rule)",
                "Challenge scope drift proactively",
                "Create 3 documentation artifacts at project close",
                "Coordinate multiple agents effectively",
                "Monitor agent progress and respond to blockers",
            ],
            "success_criteria": [
                "All project objectives met",
                "Clean handoff documentation created",
                "Zero scope creep maintained",
                "Effective team coordination achieved",
            ],
            "variables": ["project_name", "product_name", "project_mission"],
        },
        "analyzer": {
            "category": "role",
            "behavioral_rules": [
                "Analyze thoroughly before recommending",
                "Document all findings clearly",
                "Use Serena MCP for code exploration",
                "Focus on architecture and patterns",
                "Report analysis findings incrementally (don't wait until end)",
                "Report file analysis progress incrementally",
            ],
            "success_criteria": [
                "Complete requirements documented",
                "Architecture aligned with vision",
                "All risks and dependencies identified",
                "Clear specifications for implementer",
            ],
            "variables": ["project_name", "custom_mission"],
        },
        "implementer": {
            "category": "role",
            "behavioral_rules": [
                "Write clean, maintainable code",
                "Follow project specifications exactly",
                "Use Serena MCP symbolic operations for edits",
                "Test changes incrementally",
                "Report file modifications after each implementation step",
                "Include token usage in progress reports (track context carefully)",
            ],
            "success_criteria": [
                "All specified features implemented correctly",
                "Code follows project standards",
                "Tests passing",
                "No unauthorized scope changes",
            ],
            "variables": ["project_name", "custom_mission"],
        },
        "tester": {
            "category": "role",
            "behavioral_rules": [
                "Test thoroughly and systematically",
                "Document all defects clearly",
                "Create comprehensive test coverage",
                "Validate against requirements",
                "Report test results in completion summary (pass/fail counts, coverage)",
                "Include test file paths in progress reports",
            ],
            "success_criteria": [
                "All features have test coverage",
                "Tests validate requirements correctly",
                "Coverage meets project standards",
                "Test documentation complete",
            ],
            "variables": ["project_name", "custom_mission"],
        },
        "reviewer": {
            "category": "role",
            "behavioral_rules": [
                "Review objectively and constructively",
                "Provide actionable feedback",
                "Check security best practices",
                "Validate architectural compliance",
                "Document all findings with severity levels",
                "Mark completion only after all review comments addressed",
            ],
            "success_criteria": [
                "Code meets quality standards",
                "Security best practices followed",
                "No critical issues remaining",
                "All feedback is actionable",
            ],
            "variables": ["project_name", "custom_mission"],
        },
        "documenter": {
            "category": "role",
            "behavioral_rules": [
                "Document clearly and comprehensively",
                "Create usage examples and guides",
                "Update all relevant artifacts",
                "Focus on implemented features only",
                "Report documentation files created/updated in progress",
                "Include documentation coverage in completion summary",
            ],
            "success_criteria": [
                "Documentation complete and accurate",
                "Usage examples provided",
                "All artifacts updated",
                "Documentation follows project style",
            ],
            "variables": ["project_name", "custom_mission"],
        },
    }


def _get_mcp_coordination_section() -> str:
    """
    Generate the MCP coordination section to append to all templates.

    This section contains ONLY the critical "MCP tools are native calls" warning.
    All lifecycle behavior (tools, bootstrap, phases) is in server-side `full_protocol`
    returned by get_agent_mission().

    Added in Phase 7 (Handover 0045).
    Trimmed in Handover 0431 to remove redundant content covered by full_protocol.

    Returns:
        str - MCP coordination section in markdown format
    """
    return """## MCP Tool Usage

MCP tools appear as **native tool calls** in your tool list (like Read, Write, Bash, Glob).

**CORRECT**: Call tools directly
```
mcp__giljo-mcp__get_agent_mission(job_id="...")
```

**WRONG**: Manual construction (curl, fetch, requests.post)

**Note**: `tenant_key` auto-injected by server. Tool signatures in `full_protocol`.
"""


def _get_mcp_bootstrap_section() -> str:
    """
    Generate the slim MCP bootstrap section for agent templates (Handover 0813).

    This replaces the previous protocol-heavy system_instructions with a minimal
    bootstrap that directs agents to fetch their full protocols via get_agent_mission().

    The full protocol content (5-phase lifecycle, messaging, check-ins, etc.) is
    delivered server-side via full_protocol in the get_agent_mission() response.

    Returns:
        str - Slim MCP bootstrap section (~10 lines) in markdown format
    """
    return """## GiljoAI MCP Agent

You are part of a GiljoAI MCP orchestration system. MCP tools are available as native
tool calls prefixed `mcp__giljo-mcp__*` in your tool list.

Your job credentials (`job_id`, `tenant_key`) are provided in your spawn prompt —
either pasted by the user or injected by the orchestrator. Use them exactly as given.

### STARTUP (MANDATORY)
1. Call `mcp__giljo-mcp__health_check()` to verify MCP connectivity
2. Call `mcp__giljo-mcp__get_agent_mission(job_id="<your_job_id>", tenant_key="<your_tenant_key>")` to receive:
   - Your full operating protocols (`full_protocol`)
   - Your work order and team context (`mission`)
3. Follow `full_protocol` for all lifecycle behavior

Do not begin work until you have received and read your mission and protocols."""


def _get_check_in_protocol_section() -> str:
    """
    Generate the Check-In Protocol section for agent monitoring (Handover 0107).

    This section provides brief reminder about contextual check-ins.
    Detailed behavior lives in full_protocol returned by get_agent_mission().

    Returns:
        str - Brief Check-In Protocol section in markdown format

    Note:
        Slimmed in Handover 0353 - detailed behavior moved to full_protocol.
        Updated in Handover 0392 - simplified report_progress format.
    """
    return """## CHECK-IN PROTOCOL

Report progress at natural workflow breaks (after todos, after phases, before long tasks).
NOT timer-based. Full protocol in `full_protocol` from `get_agent_mission()`.
"""


def _get_context_request_section() -> str:
    """
    Generate the context request section for agent templates (Handover 0109).

    This section provides instructions for agents on when and how to request
    broader project context from the orchestrator via MCP messaging.

    Returns:
        str - Context request section in markdown format

    Note:
        Added to system_instructions for all agent templates to enable
        audit trail of context requests via MCP message queue.
    """
    return """### REQUESTING BROADER CONTEXT

If your mission objectives are unclear or require broader project context:

**When to Request Context**:
- Mission references undefined entities or components
- Dependencies between tasks are unclear
- Scope boundaries are ambiguous
- Integration points not specified in your mission
- Related project requirements needed for decision-making

**How to Request Context**:

1. **Use MCP messaging tool**:
   ```
   mcp__giljo-mcp__send_message(
     to_agents=["orchestrator"],
     content="REQUEST_CONTEXT: [specific need]",
     project_id="{project_id}",
     from_agent="{agent_id}"
   )
   ```

2. **Be specific about what you need**:
   - ✅ Good: "REQUEST_CONTEXT: What database schema is being used for user authentication?"
   - ✅ Good: "REQUEST_CONTEXT: Which API endpoints depend on the Payment service?"
   - ❌ Bad: "REQUEST_CONTEXT: Tell me everything about the project"

3. **Wait for orchestrator response**:
   - Check: `mcp__giljo-mcp__receive_messages(agent_id="{agent_id}")`
   - Orchestrator will provide filtered context excerpt
   - Continue work after receiving clarification

4. **Document in progress report**:
   - Include context request in next `report_progress()` call
   - Creates MCP message audit trail

**Benefits**:
- ✅ Orchestrator maintains single source of truth
- ✅ Audit trail of all context requests
- ✅ Token-efficient (request only what you need)
- ✅ Avoids context duplication
"""


def _get_orchestrator_context_response_section() -> str:
    """
    Generate orchestrator-specific context response section (Handover 0109).

    This section provides reciprocal instructions for orchestrators on how
    to respond to context requests from other agents.

    Returns:
        str - Orchestrator context response section in markdown format

    Note:
        Added to user_instructions only for orchestrator template.
    """
    return """### RESPONDING TO CONTEXT REQUESTS

When agents request broader context via send_message():

**Your Responsibilities**:
1. Respond promptly to agent context requests
2. Provide filtered excerpts from Project.mission, not full text
3. Focus on specific information requested

**Response Pattern**:
```
mcp__giljo-mcp__send_message(
  to_agents=["{requesting_agent_id}"],
  content="CONTEXT_RESPONSE: [filtered excerpt]",
  project_id="{project_id}",
  from_agent="{agent_id}"
)
```

**Keep responses concise** - Only provide information directly relevant to agent's question.
"""


def _get_agent_messaging_protocol_section() -> str:
    """
    Generate agent messaging protocol section (Handover 0296, slimmed in 0353).

    This section lists core MCP messaging tools and reminds agents to use them.
    Detailed checkpoint protocol lives in full_protocol returned by get_agent_mission().

    Returns:
        str - Brief agent messaging protocol section in markdown format

    Note:
        Slimmed in Handover 0353 - detailed checkpoint pseudo-code moved to full_protocol.
    """
    return """## MESSAGING

**Prefixes:** BLOCKER: (urgent), PROGRESS: (update), COMPLETE: (done), READY: (available)
Use `send_message()` and `receive_messages()`. Full protocol in `full_protocol`.
"""


def _get_agent_guidelines_section() -> str:
    """
    Generate shared agent guidelines section (Handover 0432).

    Provides baseline guidelines applicable to ALL non-orchestrator agents.
    Includes simplified Technical Environment and blocking behavior.

    Returns:
        str - Agent guidelines section in markdown format
    """
    return """## Technical Environment

- **MCP Tools**: Prefixed `mcp__giljo-mcp__` (available in your tool list)
- **Multi-tenant**: Operations isolated by `tenant_key` (auto-injected by server)

## Agent Guidelines

- **Follow Mission**: Execute your assigned mission from `get_agent_mission()`
- **Report Progress**: Update status at natural workflow breaks
- **Escalate Blockers**: Message orchestrator if stuck, mark yourself BLOCKED
- **Request Context**: Ask orchestrator if mission is unclear (don't guess)

## If Blocked or Unclear

1. Call `report_error(job_id, "BLOCKED: <reason>")` to mark yourself blocked
2. Send BLOCKER: or REQUEST_CONTEXT: message to orchestrator
3. Wait for response via `receive_messages()`
4. Call `report_progress()` to resume (sets status back to working)
"""


def _get_orchestrator_messaging_protocol_section() -> str:
    """
    Generate orchestrator-specific messaging protocol section.

    Trimmed in Handover 0431 - detailed examples moved to full_protocol.
    Keeps only orchestrator-specific coordination patterns.

    Returns:
        str - Orchestrator messaging protocol section in markdown format
    """
    return """## ORCHESTRATOR COORDINATION

As orchestrator, you coordinate the team using messaging tools.

### Coordination Loop (Every 3-5 Actions)
1. Call `receive_messages()` - sort by priority (high first)
2. Handle BLOCKER: messages immediately (provide guidance or reassign)
3. Forward COMPLETE: to dependent agents via DEPENDENCY_MET:
4. Acknowledge PROGRESS: updates

### Status Broadcasts (Every 10-15 Actions)
Use `get_workflow_status()` then broadcast team status summary.

### Escalation (Agent blocked >5 minutes)
Send ESCALATION: message to developer/user for intervention.

### Message Prefixes
- **BLOCKER:** - Urgent, needs immediate help
- **QUESTION:** - Needs clarification
- **PROGRESS:** - Milestone update
- **COMPLETE:** - Work finished
- **DEPENDENCY_MET:** - Unblock dependent agents
- **ESCALATION:** - Requires user attention

### Priority Levels
- **high** - Blockers, developer messages, urgent coordination
- **normal** - Progress, questions, completions
- **low** - Status broadcasts, informational

Tool signatures and full protocol in `full_protocol` from `get_agent_mission()`.
"""


def get_orchestrator_identity_content() -> str:
    """
    Generate FULL orchestrator identity and behavioral guidance for get_orchestrator_instructions().

    Handover 0431: This content is injected into the MCP tool response so orchestrators
    get their identity/behavioral guidance without needing an AgentTemplate record.
    Orchestrators stay OUT of the template table, exports, and available_agents list.

    Returns:
        str - Full orchestrator identity and behavioral guidance in markdown format
    """
    # Get base template (Identity, Workflow, Responsibilities, etc.)
    base_template = ""
    for template_def in _get_default_templates_v103():
        if template_def.get("role") == "orchestrator":
            base_template = template_def["user_instructions"].strip()
            break

    # Get all protocol sections
    orchestrator_response = _get_orchestrator_context_response_section().strip()
    mcp_section = _get_mcp_coordination_section().strip()
    check_in = _get_check_in_protocol_section().strip()
    orchestrator_messaging = _get_orchestrator_messaging_protocol_section().strip()

    return f"""{base_template}

{orchestrator_response}

{mcp_section}

{check_in}

{orchestrator_messaging}
"""
