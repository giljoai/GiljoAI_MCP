"""
Unified Template Manager for GiljoAI MCP
Consolidates template functionality from Projects 3.4 and 3.9.b
Single source of truth for all template operations
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional, Union

from sqlalchemy import select

from .database import DatabaseManager
from .models import AgentTemplate, TemplateAugmentation


logger = logging.getLogger(__name__)


def apply_augmentation(content: str, augmentation: Union[TemplateAugmentation, dict[str, Any]]) -> str:
    """
    Apply augmentation to template content.
    Handles both database objects and runtime dictionaries.

    Args:
        content: Template content to augment
        augmentation: Either a DB TemplateAugmentation or dict with:
            - type/augmentation_type: append, prepend, replace, inject
            - content: Content to apply
            - target/target_section: Optional target for replace/inject

    Returns:
        Augmented content
    """
    # Handle empty augmentation
    if not augmentation or (isinstance(augmentation, dict) and not augmentation):
        return content

    # Normalize input to dict format
    if isinstance(augmentation, TemplateAugmentation):
        aug_type = augmentation.augmentation_type
        aug_content = augmentation.content
        target = augmentation.target_section
    else:
        aug_type = augmentation.get("type") or augmentation.get("augmentation_type", "append")
        aug_content = augmentation.get("content", "")
        target = augmentation.get("target") or augmentation.get("target_section", "")

    # Apply augmentation based on type
    if aug_type == "append":
        return content + "\n\n" + aug_content
    if aug_type == "prepend":
        return aug_content + "\n\n" + content
    if aug_type == "replace" and target:
        return content.replace(target, aug_content)
    if aug_type == "inject" and target:
        index = content.find(target)
        if index != -1:
            end_index = index + len(target)
            return content[:end_index] + "\n" + aug_content + content[end_index:]

    return content


def process_template(
    content: str,
    variables: Optional[dict[str, Any]] = None,
    augmentations: Optional[list[Union[TemplateAugmentation, dict]]] = None,
    substitute_first: bool = False,
) -> str:
    """
    Process a template with variables and augmentations.

    Args:
        content: Base template content
        variables: Variables to substitute
        augmentations: List of augmentations to apply
        substitute_first: If True, substitute variables before augmentations

    Returns:
        Processed template content
    """
    processed = content

    # Apply variable substitution first if requested
    if substitute_first and variables:
        for key, value in variables.items():
            processed = processed.replace(f"{{{key}}}", str(value))

    # Apply augmentations
    if augmentations:
        # Sort by priority if available
        sorted_augs = augmentations
        if all(hasattr(a, "priority") or "priority" in a for a in augmentations):
            sorted_augs = sorted(
                augmentations,
                key=lambda x: (x.priority if hasattr(x, "priority") else x.get("priority", 0)),
            )

        for aug in sorted_augs:
            processed = apply_augmentation(processed, aug)

    # Apply variable substitution after if not done before
    if not substitute_first and variables:
        for key, value in variables.items():
            processed = processed.replace(f"{{{key}}}", str(value))

    return processed


def extract_variables(content: str) -> list[str]:
    """
    Extract variable names from template content.

    Args:
        content: Template content with {variable} placeholders

    Returns:
        List of unique variable names in order of first appearance
    """
    seen = set()
    result = []
    for var in re.findall(r"\{(\w+)\}", content):
        if var not in seen:
            seen.add(var)
            result.append(var)
    return result


class UnifiedTemplateManager:
    """
    Unified manager for all template operations.
    Handles both database-backed and legacy templates.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the template manager.

        Args:
            db_manager: Optional database manager for DB-backed templates
        """
        self.db_manager = db_manager
        self._template_cache = {}
        self._legacy_templates = self._load_legacy_templates()

    def _load_legacy_templates(self) -> dict[str, str]:
        """Load comprehensive templates extracted from mission_templates.py"""
        return {
            "orchestrator": """You are the Project Orchestrator for: {project_name}

PROJECT GOAL: {project_mission}
PRODUCT: {product_name}

YOUR DISCOVERY APPROACH (Dynamic Context Loading):
1. Read the vision document using get_vision()
   - IMPORTANT: If it returns multiple parts (check total_parts in response), call it multiple times
   - Example: If total_parts=3, call get_vision(part=1), get_vision(part=2), get_vision(part=3)
   - Read ALL parts to get complete vision before proceeding
2. Review product settings with get_product_settings() - understand technical configuration
3. Use Serena MCP to explore the codebase for implementation details
4. Only load what's relevant to this specific project

YOUR AUTHORITY:
- Create any agents with ANY job types you deem necessary
- Define precise missions for each agent based on discoveries
- Choose optimal implementation approach
- Design the agent pipeline that best achieves the goal

YOUR RESPONSIBILITIES:

1. VISION GUARDIAN:
   - Read and understand the ENTIRE vision document first (all parts if chunked)
   - Every decision must align with the vision
   - Challenge the human if their request drifts from vision
   - Document which vision principles guide each decision

2. SCOPE SHERIFF:
   - Keep agents narrowly focused on their specific missions
   - No agent should interpret or expand beyond their given scope
   - Agents must check with you for ANY scope questions
   - You define the boundaries, agents execute within them

3. STRATEGIC ARCHITECT:
   - Design the optimal sequence of agents (suggested: analyzer, implementer, tester)
   - Create job types that match the actual work needed
   - Ensure missions compound efficiently with no gaps or overlaps
   - Each agent should have crystal-clear success criteria

4. PROGRESS TRACKER:
   - Regular check-ins with human on major decisions
   - Escalate vision conflicts immediately
   - Report when agents request scope expansion
   - Document handoffs and completion status

BEHAVIORAL INSTRUCTIONS:
- Tell user if agents should run in parallel at start or started in order
- Tell all agents to acknowledge messages as they read them
- Only use handoff MCP feature upon context limit and moving to agent #2 of same type
- Agents should communicate questions and advice to the orchestrator who will ask the user
- Agents shall communicate status when completed to the next agent and report to orchestrator
- Agents can start preparing work and plan while waiting for completion message from prior agent

REMEMBER:
- Discover context dynamically - don't pre-load everything
- Focus on what's relevant to THIS project
- You have Serena MCP to help explore the codebase
- The vision document is your north star
- If get_vision() returns parts, read ALL parts before proceeding""",
            "analyzer": """You are the System Analyzer for: {project_name}

YOUR MISSION: {custom_mission}

DISCOVERY WORKFLOW:
1. Use Serena MCP to explore relevant code sections
2. Read only what's necessary for analysis
3. Focus on understanding patterns and architecture
4. Document findings clearly

RESPONSIBILITIES:
- Understand requirements and constraints
- Analyze existing codebase and patterns
- Create architectural designs and specifications
- Identify potential risks and dependencies
- Prepare clear handoff documentation for implementer

BEHAVIORAL RULES:
- Acknowledge all messages immediately upon reading
- Report progress to orchestrator regularly
- Ask orchestrator if scope questions arise
- Complete analysis before implementer starts coding
- Document all architectural decisions with rationale
- Create implementation specifications with exact requirements

SUCCESS CRITERIA:
- Complete understanding of requirements documented
- Architecture design aligns with vision and existing patterns
- All risks and dependencies identified
- Clear specifications ready for implementer
- Handoff documentation complete""",
            "implementer": """You are the System Implementer for: {project_name}

YOUR MISSION: {custom_mission}

IMPLEMENTATION WORKFLOW:
1. Wait for analyzer's specifications
2. Use Serena MCP symbolic operations for edits
3. Follow existing code patterns exactly
4. Test your changes incrementally

RESPONSIBILITIES:
- Write clean, maintainable code
- Follow architectural specifications exactly
- Implement features according to requirements
- Ensure code quality and standards compliance
- Create proper documentation

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Never expand scope beyond specifications
- Report blockers to orchestrator immediately
- Hand off to next agent when context approaches 80%
- Follow CLAUDE.md coding standards strictly
- Use symbolic editing when possible for precision

SUCCESS CRITERIA:
- All specified features implemented correctly
- Code follows project standards and patterns
- No scope creep or unauthorized changes
- Tests pass (if applicable)
- Documentation updated""",
            "tester": """You are the System Tester for: {project_name}

YOUR MISSION: {custom_mission}

TESTING WORKFLOW:
1. Wait for implementer's completion
2. Create comprehensive test coverage
3. Validate against original requirements
4. Document all findings

RESPONSIBILITIES:
- Write comprehensive test suites
- Validate implementation against requirements
- Find and document bugs
- Ensure code coverage and quality metrics
- Create test documentation

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Test only what was implemented
- Report failures to orchestrator
- Provide clear pass/fail status
- Document test coverage metrics
- Create regression test suite

SUCCESS CRITERIA:
- All features have test coverage
- Tests validate requirements correctly
- Bug reports are clear and actionable
- Coverage meets project standards
- Test documentation complete""",
            "reviewer": """You are the Code Reviewer for: {project_name}

YOUR MISSION: {custom_mission}

REVIEW WORKFLOW:
1. Wait for implementation and testing completion
2. Review code for quality and standards
3. Check security best practices
4. Validate architectural compliance

RESPONSIBILITIES:
- Review code for quality and standards
- Identify potential improvements
- Ensure security best practices
- Validate architectural compliance
- Provide actionable feedback

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Focus review on implemented changes only
- Escalate major issues to orchestrator
- Provide constructive feedback
- Document all review findings
- Suggest improvements with examples

SUCCESS CRITERIA:
- Code meets quality standards
- Security best practices followed
- Architecture compliance validated
- All feedback is actionable
- Review documentation complete""",
            "documenter": """You are the Documentation Agent for: {project_name}

YOUR MISSION: {custom_mission}

DOCUMENTATION WORKFLOW:
1. Wait for implementation completion
2. Document all deliverables thoroughly
3. Create usage examples and guides
4. Update architectural documentation

RESPONSIBILITIES:
- Create comprehensive documentation for all project deliverables
- Write usage examples and tutorials
- Document API specifications
- Update README and setup guides
- Document architectural decisions

BEHAVIORAL RULES:
- Acknowledge all messages immediately
- Focus documentation on implemented features only
- Report progress to orchestrator regularly
- Create clear, actionable documentation
- Follow project documentation standards
- Include code examples where helpful

SUCCESS CRITERIA:
- All implemented features have complete documentation
- Usage examples are clear and working
- API documentation is accurate and complete
- Documentation follows project standards
- Architectural decisions are well documented""",
        }

    async def get_template(
        self,
        role: str,
        variables: Optional[dict[str, Any]] = None,
        augmentations: Optional[list[Union[TemplateAugmentation, dict]]] = None,
        project_type: Optional[str] = None,
        product_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> str:
        """
        Get a processed template for the specified role.

        Args:
            role: Agent role (orchestrator, analyzer, etc.)
            variables: Variables to substitute
            augmentations: Runtime augmentations to apply
            project_type: Optional project type for specialized templates
            product_id: Optional product ID for product-specific templates
            use_cache: Whether to use cached templates

        Returns:
            Processed template content
        """
        try:
            # Try database first if available
            if self.db_manager:
                template_content = await self._get_db_template(role, project_type, product_id, use_cache)
            else:
                # Fall back to legacy templates
                template_content = self._legacy_templates.get(role.lower(), f"No template available for role: {role}")

            # Process the template
            return process_template(template_content, variables, augmentations)

        except Exception as e:
            logger.exception(f"Failed to get template for role '{role}': {e}")
            # Return fallback template
            fallback = self._legacy_templates.get(role.lower(), f"Error loading template for role: {role}")
            return process_template(fallback, variables, augmentations)

    async def _get_db_template(
        self,
        role: str,
        project_type: Optional[str],
        product_id: Optional[str],
        use_cache: bool,
    ) -> str:
        """Get template from database with caching"""
        cache_key = f"{role}_{project_type}_{product_id}"

        if use_cache and cache_key in self._template_cache:
            return self._template_cache[cache_key]

        async with self.db_manager.get_session() as session:
            # Build query
            query = select(AgentTemplate).where(AgentTemplate.role == role, AgentTemplate.is_active)

            # Add filters
            if product_id:
                query = query.where(AgentTemplate.product_id == product_id)
            if project_type:
                query = query.where(AgentTemplate.project_type == project_type)

            # Try to get most specific template first
            result = await session.execute(query)
            template = result.scalar_one_or_none()

            # Fall back to default template for role
            if not template:
                query = select(AgentTemplate).where(
                    AgentTemplate.role == role,
                    AgentTemplate.is_active,
                    AgentTemplate.is_default,
                )
                result = await session.execute(query)
                template = result.scalar_one_or_none()

            if template:
                # Update usage stats
                template.usage_count += 1
                template.last_used_at = datetime.now(timezone.utc)
                await session.commit()

                # Cache the template
                if use_cache:
                    self._template_cache[cache_key] = template.template_content

                return template.template_content

            # Fall back to legacy template
            return self._legacy_templates.get(role.lower(), f"No template available for role: {role}")

    def clear_cache(self):
        """Clear the template cache"""
        self._template_cache.clear()
        logger.info("Template cache cleared")

    def get_cached_templates(self) -> list[str]:
        """Get list of cached template keys"""
        return list(self._template_cache.keys())

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
                "Read vision document completely",
                "Challenge scope drift",
            ],
            "analyzer": [
                "Perform thorough analysis",
                "Document findings clearly",
                "Identify risks and opportunities",
                "Provide actionable insights",
                "Follow established patterns",
            ],
            "implementer": [
                "Write clean, maintainable code",
                "Follow design specifications",
                "Handle errors appropriately",
                "Test your implementation",
                "Document complex logic",
            ],
            "tester": [
                "Test all functionality thoroughly",
                "Document test results",
                "Verify edge cases",
                "Ensure quality standards",
                "Report issues clearly",
            ],
            "reviewer": [
                "Review code objectively",
                "Check for standards compliance",
                "Identify improvements",
                "Provide constructive feedback",
                "Verify requirements met",
            ],
            "documenter": [
                "Use clear, concise language",
                "Include code examples",
                "Follow documentation standards",
                "Organize content logically",
                "Keep documentation current",
            ],
        }

        return default_rules.get(role.lower(), ["Follow project guidelines"])

    def get_success_criteria(self, role: str) -> list[str]:
        """
        Get success criteria for a role.

        Args:
            role: Agent role

        Returns:
            List of success criteria
        """
        default_criteria = {
            "orchestrator": [
                "Vision document fully read",
                "All agents spawned with clear missions",
                "Project goals achieved",
                "Handoffs completed successfully",
            ],
            "analyzer": [
                "Complete system analysis",
                "Design documents created",
                "Integration points identified",
                "Risks assessed",
            ],
            "implementer": [
                "All features implemented",
                "Code follows project standards",
                "Tests pass",
                "No breaking changes",
            ],
            "tester": [
                "All tests written and passing",
                "Edge cases covered",
                "Performance validated",
                "Regression tests included",
            ],
            "reviewer": [
                "Code review complete",
                "All issues addressed",
                "Standards compliance verified",
                "Documentation approved",
            ],
            "documenter": [
                "All features documented",
                "Examples provided",
                "Setup instructions complete",
                "Architecture documented",
            ],
        }

        return default_criteria.get(role.lower(), ["Complete assigned tasks"])


# Singleton instance for global use
_template_manager_instance = None


def get_template_manager(
    db_manager: Optional[DatabaseManager] = None,
) -> UnifiedTemplateManager:
    """
    Get the singleton template manager instance.

    Args:
        db_manager: Optional database manager

    Returns:
        UnifiedTemplateManager instance
    """
    global _template_manager_instance

    if _template_manager_instance is None:
        _template_manager_instance = UnifiedTemplateManager(db_manager)
    elif db_manager and _template_manager_instance.db_manager is None:
        # Update with database manager if not previously set
        _template_manager_instance.db_manager = db_manager

    return _template_manager_instance
