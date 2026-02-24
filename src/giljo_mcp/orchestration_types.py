"""
Orchestration data structures for the GiljoAI MCP Server.

This module defines data structures used in the orchestration workflow:
- Mission: Agent-specific mission with context and constraints
- RequirementAnalysis: Analysis of user requirements for agent selection
- AgentConfig: Configuration for a single agent in the workflow

All classes use dataclasses for clean, typed data structures.
"""

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Mission:
    """
    Agent-specific mission with context and constraints.

    A Mission represents the specific work assigned to an agent, including
    the mission content, context references, priority, and success criteria.

    Attributes:
        agent_role: The role of the agent (e.g., 'architect', 'implementor')
        content: Markdown-formatted mission content (500-1500 tokens recommended)
        token_count: Number of tokens in the mission content
        context_chunk_ids: List of context chunk IDs relevant to this mission
        priority: Priority level ('required', 'high', 'medium', 'low')
        scope_boundary: Optional explicit scope boundary for the mission
        success_criteria: Optional success criteria for the mission
        dependencies: Optional list of mission IDs this mission depends on
    """

    agent_role: str
    content: str
    token_count: int
    context_chunk_ids: list[str]
    priority: str
    scope_boundary: Optional[str] = None
    success_criteria: Optional[str] = None
    dependencies: Optional[list[str]] = None

    def to_dict(self) -> dict:
        """
        Convert Mission to dictionary representation.

        Returns:
            dict: Dictionary containing all mission fields
        """
        return asdict(self)


@dataclass
class RequirementAnalysis:
    """
    Analysis of user requirements for agent selection and workflow planning.

    This class represents the analyzed requirements, including work types,
    complexity, technology stack, and estimated resource needs.

    Attributes:
        work_types: Mapping of work types to their categories (e.g., {'architecture': 'system_design'})
        complexity: Complexity level ('simple', 'moderate', 'complex')
        tech_stack: List of technologies involved
        keywords: List of keywords extracted from requirements
        estimated_agents_needed: Estimated number of agents needed
        feature_categories: Optional list of feature categories
    """

    work_types: dict[str, str]
    complexity: str
    tech_stack: list[str]
    keywords: list[str]
    estimated_agents_needed: int
    feature_categories: Optional[list[str]] = None

    def get_agent_priority(self, agent_display_name: str) -> str:
        """
        Get the priority level for a specific agent type.

        Args:
            agent_display_name: The type of agent to get priority for

        Returns:
            str: Priority level from work_types, or 'low' if not found
        """
        return self.work_types.get(agent_display_name, "low")


@dataclass
class AgentConfig:
    """
    Configuration for a single agent in the workflow.

    This class contains all configuration needed to create and execute
    an agent job, including template information, mission, and context.

    Attributes:
        role: The agent's role (e.g., 'architect', 'implementor')
        template_id: ID of the template to use
        priority: Priority level for this agent's work
        mission_scope: Brief description of the mission scope
        mission: Optional Mission object with detailed mission information
        context_chunks: Optional list of context data chunks
    """

    role: str
    template_id: str
    priority: str
    mission_scope: str
    mission: Optional[Mission] = None
    context_chunks: Optional[list[str]] = None

    def to_job_params(self) -> dict:
        """
        Convert AgentConfig to job parameters dictionary.

        Converts the configuration to a format suitable for creating
        agent jobs, converting nested Mission objects to dictionaries.

        Returns:
            dict: Job parameters including all config fields
        """
        params = {
            "agent_role": self.role,
            "template_id": self.template_id,
            "priority": self.priority,
            "mission_scope": self.mission_scope,
            "mission": self.mission.to_dict() if self.mission else None,
            "context_chunks": self.context_chunks,
        }
        return params
