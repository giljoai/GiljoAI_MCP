"""
Template adapter to bridge the old MissionTemplateGenerator with the new database-backed system.
Provides backward compatibility for orchestrator.py while using the new template management.
"""

import logging
from typing import Any, Optional

from sqlalchemy import select

from .database import DatabaseManager
from .models import AgentTemplate
from .system_prompts import SystemPromptService
from .template_manager import apply_augmentation


logger = logging.getLogger(__name__)


class TemplateAdapter:
    """Adapter class to use database templates with the old interface"""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize the adapter with database manager"""
        self.db_manager = db_manager
        self._template_cache = {}

    async def get_template(
        self,
        role: str,
        variables: Optional[dict[str, str]] = None,
        augmentations: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        """
        Get a template from the database and apply substitutions

        Args:
            role: The agent role (orchestrator, analyzer, etc.)
            variables: Variables to substitute in the template
            augmentations: Runtime augmentations to apply

        Returns:
            The processed template content
        """
        try:
            # Check cache first
            cache_key = f"{role}_base"
            if cache_key not in self._template_cache:
                async with self.db_manager.get_session_async() as session:
                    # Query for the template
                    query = select(AgentTemplate).where(
                        AgentTemplate.role == role,
                        AgentTemplate.is_active,
                        AgentTemplate.is_default,
                    )

                    result = await session.execute(query)
                    template = result.scalar_one_or_none()

                    if not template:
                        # Fallback to name-based lookup
                        query = select(AgentTemplate).where(AgentTemplate.name == role, AgentTemplate.is_active)
                        result = await session.execute(query)
                        template = result.scalar_one_or_none()

                    if template:
                        self._template_cache[cache_key] = template.system_instructions

                        # Update usage stats
                        template.usage_count += 1
                        await session.commit()
                    else:
                        logger.warning(f"No template found for role '{role}'")
                        # Return None to trigger fallback in caller
                        return None

            # Get template content from cache
            content = self._template_cache.get(cache_key, "")

            # Apply augmentations
            if augmentations:
                for aug in augmentations:
                    content = apply_augmentation(content, aug)

            # Substitute variables
            if variables:
                for key, value in variables.items():
                    content = content.replace(f"{{{key}}}", str(value))

            return content

        except Exception as e:
            logger.exception(f"Failed to get template for role '{role}': {e}")
            return f"Error loading template: {e!s}"

    # _apply_augmentation method removed - using unified apply_augmentation from template_manager


class MissionTemplateGeneratorV2:
    """
    Drop-in replacement for MissionTemplateGenerator that uses database templates.
    Maintains the same interface for backward compatibility.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize with optional database manager"""
        self.db_manager = db_manager
        self.adapter = TemplateAdapter(db_manager) if db_manager else None
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
        """Generate orchestrator mission using database template"""
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
        """Generate agent mission using database template"""
        if self.adapter:
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

            template_result = await self.adapter.get_template(
                role=role.lower(), variables=variables, augmentations=augmentations
            )
            if template_result is not None:
                return template_result
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
        """Generate instructions for parallel agent startup"""
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
        """Generate instructions for context limit handling"""
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

    def generate_handoff_instructions(self, from_agent: str, to_agent: str, handoff_context: dict[str, Any]) -> str:
        """Generate handoff instructions between agents"""
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
        """Generate acknowledgment instruction"""
        return "Messages are automatically acknowledged when retrieved."

    def get_behavioral_rules(self, role: str) -> list[str]:
        """Get behavioral rules for a role"""
        # This would query the database for behavioral rules
        # For now, return default rules
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
