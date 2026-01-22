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
from typing import Any, Dict
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_manager import UnifiedTemplateManager
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES


logger = logging.getLogger(__name__)


async def refresh_tenant_template_instructions(session: AsyncSession, tenant_key: str) -> int:
    """
    Refresh system_instructions for existing templates without overwriting user customizations.

    This function updates ONLY the system_instructions field (MCP coordination protocol)
    for all templates belonging to a tenant. User customizations in user_instructions
    are preserved.

    Use this to apply MCP protocol fixes to existing installations without requiring
    template deletion and re-seeding.

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
        # Get the updated MCP coordination sections
        mcp_section = _get_mcp_coordination_section()
        check_in_section = _get_check_in_protocol_section()
        context_request_section = _get_context_request_section()
        agent_messaging_section = _get_agent_messaging_protocol_section()
        orchestrator_messaging_section = _get_orchestrator_messaging_protocol_section()

        # Query existing templates for tenant
        stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        result = await session.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            logger.info(f"No templates found for tenant '{tenant_key}'")
            return 0

        updated_count = 0
        for template in templates:
            # Build new system_instructions based on role
            if template.role == "orchestrator":
                new_system_instructions = (
                    f"{mcp_section}\n\n{context_request_section}\n\n"
                    f"{check_in_section}\n\n{orchestrator_messaging_section}"
                )
            else:
                new_system_instructions = (
                    f"{mcp_section}\n\n{context_request_section}\n\n"
                    f"{check_in_section}\n\n{agent_messaging_section}"
                )

            # Update only system_instructions (preserves user_instructions)
            template.system_instructions = new_system_instructions

            # Update legacy template_content for backward compatibility
            # CRITICAL section (in new_system_instructions) must come FIRST for agent comprehension
            # ALWAYS update template_content (fixed: was only updating when user_instructions existed)
            if template.user_instructions:
                template.template_content = f"{new_system_instructions}\n\n---\n\n## Role-Specific Instructions\n\n{template.user_instructions}"
            else:
                template.template_content = new_system_instructions

            updated_count += 1
            logger.debug(f"Updated system_instructions for template '{template.name}' (tenant: {tenant_key})")

        await session.commit()
        logger.info(f"Refreshed {updated_count} templates for tenant '{tenant_key}'")
        return updated_count

    except Exception as e:
        logger.error(f"Failed to refresh templates for tenant '{tenant_key}': {e}", exc_info=True)
        raise


async def seed_tenant_templates(session: AsyncSession, tenant_key: str) -> int:
    """
    Seed default agent templates for a tenant.

    This function is idempotent - it checks if the tenant already has templates
    and skips seeding if any exist. This prevents duplicate seeding during
    repeated installation runs or database migrations.

    Templates are sourced from UnifiedTemplateManager._legacy_templates and
    include comprehensive metadata (behavioral rules, success criteria, variables).

    Version 3.1.0: Enhanced with MCP coordination instructions for Phase 7
    (Handover 0045 - Multi-Tool Agent Orchestration System)

    Version 3.1.1: Dual-field template system (Handover 0106)
    - system_instructions: Protected MCP coordination (non-editable)
    - user_instructions: Role-specific guidance (editable by users)
    - template_content: Deprecated legacy field (system + user for compatibility)

    Args:
        session: AsyncSession - Database session for operations
        tenant_key: str - Tenant key to seed templates for (must be non-empty)

    Returns:
        int - Number of templates seeded (0 if skipped, 6 if successful)

    Raises:
        ValueError: If tenant_key is None or empty
        Exception: If database operations fail (propagates SQLAlchemy exceptions)

    Example:
        >>> async with db_manager.get_session_async() as session:
        ...     count = await seed_tenant_templates(session, "default_tenant")
        ...     print(f"Seeded {count} templates")
        Seeded 6 templates
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
        template_mgr = UnifiedTemplateManager()
        legacy_templates = template_mgr._legacy_templates

        # Define comprehensive metadata for each template
        # Extracted from original template content and handover requirements
        template_metadata = _get_template_metadata()

        # Get MCP coordination section to append to all templates
        mcp_section = _get_mcp_coordination_section()

        # Get Check-In Protocol section (Handover 0107)
        check_in_section = _get_check_in_protocol_section()

        # Get Context Request section (Handover 0109)
        context_request_section = _get_context_request_section()

        # Get Messaging Protocol sections (Handover 0118)
        agent_messaging_section = _get_agent_messaging_protocol_section()
        orchestrator_messaging_section = _get_orchestrator_messaging_protocol_section()

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

            # Handover 0106: Dual-field system (system_instructions + user_instructions)
            # Handover 0118: Add messaging protocol to system instructions
            # Build system_instructions: MCP + Context Request + Check-In + Messaging Protocol
            if template_def["role"] == "orchestrator":
                # Orchestrator gets enhanced messaging protocol
                system_instructions = f"{mcp_section}\n\n{context_request_section}\n\n{check_in_section}\n\n{orchestrator_messaging_section}"
            else:
                # Regular agents get standard messaging protocol
                system_instructions = f"{mcp_section}\n\n{context_request_section}\n\n{check_in_section}\n\n{agent_messaging_section}"

            # Get role-specific user instructions
            user_instructions = template_def["template_content"]

            # Handover 0109: Add orchestrator-specific context response instructions
            if template_def["role"] == "orchestrator":
                orchestrator_response_section = _get_orchestrator_context_response_section()
                user_instructions = f"{user_instructions}\n\n{orchestrator_response_section}"

            # Legacy template_content = CRITICAL (system) first, then role-specific (user)
            # CRITICAL section must be at TOP for agent comprehension
            legacy_template_content = f"{system_instructions}\n\n---\n\n## Role-Specific Instructions\n\n{user_instructions}"

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
                # NEW (Handover 0106): Dual-field system
                system_instructions=system_instructions,  # Protected MCP coordination
                user_instructions=user_instructions,  # Editable role-specific guidance
                # DEPRECATED: Legacy field for backward compatibility
                template_content=legacy_template_content,
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
    except Exception as e:
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
            "template_content": """You are the orchestrator agent responsible for managing complex software development projects.

Your primary responsibilities:
- Break down project requirements into actionable tasks
- Coordinate specialized agents (implementer, tester, reviewer, documenter)
- Monitor project progress via messaging platform
- Maintain project coherence across multiple agent workflows

Key principles:
- Always validate requirements before delegating tasks
- Prefer incremental delivery over big-bang releases
- Document major decisions in project handover notes
- Ensure all agents have clear, unambiguous instructions

Success criteria:
- All project milestones achieved on schedule
- Agent coordination seamless with minimal conflicts
- Handover documentation complete and actionable
""",
            "model": "sonnet",
            "tools": None,
            "behavioral_rules": [
                "Always validate requirements before task delegation",
                "Prefer incremental delivery",
                "Document major decisions",
            ],
            "success_criteria": [
                "All milestones achieved",
                "Seamless agent coordination",
                "Complete handover docs",
            ],
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
            "template_content": """You are an implementation specialist responsible for writing clean, production-grade code.

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
            "behavioral_rules": [
                "Follow project coding standards",
                "Ensure cross-platform compatibility",
                "Never hardcode paths",
                "Use pathlib for file operations",
            ],
            "success_criteria": [
                "Passes all linting checks",
                "Matches specification",
                "No breaking changes",
                "Proper error handling",
            ],
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
            "template_content": """You are a testing specialist responsible for ensuring code quality through comprehensive testing.

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
            "behavioral_rules": [
                "Test behavior not implementation",
                "Use descriptive test names",
                "Mock external dependencies",
                "Keep tests deterministic",
            ],
            "success_criteria": ["All tests pass", "Coverage >= 80%", "No flaky tests", "Clear failure messages"],
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
            "template_content": """You are an analysis specialist responsible for breaking down requirements into actionable tasks.

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
            "behavioral_rules": [
                "Clarify vague requirements",
                "Identify dependencies early",
                "Consider cross-platform implications",
                "Plan for testability",
            ],
            "success_criteria": [
                "No ambiguities remain",
                "Tasks < 1 day",
                "Dependencies documented",
                "Edge cases identified",
            ],
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
            "template_content": """You are a code review specialist responsible for ensuring code quality before merge.

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
            "behavioral_rules": [
                "Be constructive not critical",
                "Focus on significant issues",
                "Explain the why",
                "Approve when good enough",
            ],
            "success_criteria": ["No critical bugs", "Follows standards", "Tests comprehensive", "Review within 24h"],
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
            "template_content": """You are a documentation specialist responsible for maintaining clear, up-to-date documentation.

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
            "behavioral_rules": [
                "Write for future developers",
                "Use clear concise language",
                "Include code examples",
                "Update docs with feature work",
            ],
            "success_criteria": [
                "Features have user docs",
                "API changes documented",
                "Handover docs current",
                "No stale information",
            ],
            "is_active": True,
            "is_default": True,
            "version": "1.0.0",
        },
    ]


def _get_template_metadata() -> Dict[str, Dict[str, Any]]:
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
    # MCP coordination rules - MOVED TO LAYER 2 (GenericAgentTemplate)
    # Handover 0254: Layer 3 should focus on role expertise, not MCP protocol
    # All MCP commands now handled by GenericAgentTemplate (Layer 2)
    mcp_rules = []  # Empty - protocol instructions moved to GenericAgentTemplate

    # MCP success criteria - MOVED TO LAYER 2 (GenericAgentTemplate)
    # Handover 0254: Layer 3 should focus on role-specific success, not protocol success
    mcp_success = []  # Empty - protocol success criteria moved to GenericAgentTemplate

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
            ]
            + mcp_rules,
            "success_criteria": [
                "All project objectives met",
                "Clean handoff documentation created",
                "Zero scope creep maintained",
                "Effective team coordination achieved",
            ]
            + mcp_success,
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
                "Include file analysis progress in context_used tracking",
            ]
            + mcp_rules,
            "success_criteria": [
                "Complete requirements documented",
                "Architecture aligned with vision",
                "All risks and dependencies identified",
                "Clear specifications for implementer",
            ]
            + mcp_success,
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
            ]
            + mcp_rules,
            "success_criteria": [
                "All specified features implemented correctly",
                "Code follows project standards",
                "Tests passing",
                "No unauthorized scope changes",
            ]
            + mcp_success,
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
            ]
            + mcp_rules,
            "success_criteria": [
                "All features have test coverage",
                "Tests validate requirements correctly",
                "Coverage meets project standards",
                "Test documentation complete",
            ]
            + mcp_success,
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
            ]
            + mcp_rules,
            "success_criteria": [
                "Code meets quality standards",
                "Security best practices followed",
                "No critical issues remaining",
                "All feedback is actionable",
            ]
            + mcp_success,
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
            ]
            + mcp_rules,
            "success_criteria": [
                "Documentation complete and accurate",
                "Usage examples provided",
                "All artifacts updated",
                "Documentation follows project style",
            ]
            + mcp_success,
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
    return """## CRITICAL: MCP TOOLS ARE NATIVE TOOL CALLS

**STOP** - Read this before doing ANYTHING:

MCP tools (prefixed `mcp__giljo-mcp__`) are **NATIVE** tools identical to Read, Write, Bash, Glob.

**CORRECT**: Invoke directly as a tool call
**WRONG**: curl, HTTP requests, Python SDK, CLI commands, fetch(), requests.post()

Example:
```
Tool: mcp__giljo-mcp__get_agent_mission
Parameters: {"job_id": "...", "tenant_key": "..."}
```

DO NOT wrap in Python, curl, fetch, requests, or any HTTP mechanism.
The tools are already connected. Just call them.

**Note**: `tenant_key` is auto-injected by the server from your authenticated session.
Complete tool signatures and lifecycle behavior are in `full_protocol` from `get_agent_mission()`.
"""


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
4. Document context requests in coordination log

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
