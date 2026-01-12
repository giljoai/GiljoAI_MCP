"""
Orchestration data structures for the GiljoAI MCP Server.

This module defines all data structures used in the orchestration workflow:
- Mission: Agent-specific mission with context and constraints
- RequirementAnalysis: Analysis of user requirements for agent selection
- AgentConfig: Configuration for a single agent in the workflow
- WorkflowStage: A stage in the workflow containing one or more agents
- StageResult: Results from executing a workflow stage
- WorkflowResult: Overall workflow execution results

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
        template_content: The actual template content
        priority: Priority level for this agent's work
        mission_scope: Brief description of the mission scope
        mission: Optional Mission object with detailed mission information
        context_chunks: Optional list of context data chunks
    """

    role: str
    template_id: str
    template_content: str
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
            "template_content": self.template_content,
            "priority": self.priority,
            "mission_scope": self.mission_scope,
            "mission": self.mission.to_dict() if self.mission else None,
            "context_chunks": self.context_chunks,
        }
        return params


@dataclass
class WorkflowStage:
    """
    A stage in the workflow containing one or more agents.

    A WorkflowStage groups related agent work together and defines
    dependencies, timeouts, and retry behavior for the stage.

    Attributes:
        name: Name of the workflow stage
        agents: List of AgentConfig objects for this stage
        depends_on: Optional list of stage names this stage depends on
        critical: Whether this stage is critical (default True)
        timeout_seconds: Timeout for the stage in seconds (default 3600)
        max_retries: Maximum number of retries allowed (default 1)
        retry_count: Current retry count (default 0)
    """

    name: str
    agents: list[AgentConfig]
    depends_on: Optional[list[str]] = None
    critical: bool = True
    timeout_seconds: int = 3600
    max_retries: int = 1
    retry_count: int = 0

    def is_ready(self, completed_stages: list[str]) -> bool:
        """
        Check if this stage is ready to execute based on dependencies.

        Args:
            completed_stages: List of stage names that have been completed

        Returns:
            bool: True if all dependencies are met or no dependencies exist
        """
        if self.depends_on is None or len(self.depends_on) == 0:
            return True

        return all(dep in completed_stages for dep in self.depends_on)


@dataclass
class StageResult:
    """
    Results from executing a workflow stage.

    This class contains the execution results for a single workflow stage,
    including job IDs, results, duration, and status.

    Attributes:
        stage_name: Name of the stage that was executed
        job_ids: List of job IDs created for this stage
        results: Dictionary of results from the stage execution
        duration: Duration of stage execution in seconds
        status: Execution status (e.g., 'completed', 'failed', 'skipped')
    """

    stage_name: str
    job_ids: list[str]
    results: dict
    duration: float
    status: str


@dataclass
class WorkflowResult:
    """
    Overall workflow execution results.

    This class contains the complete results from a workflow execution,
    including all completed stages, failed stages, and success metrics.

    Attributes:
        completed: List of StageResult objects for completed stages
        failed: List of stage names that failed
        status: Overall workflow status ('completed', 'partial', 'failed')
        duration_seconds: Total workflow duration in seconds
        token_reduction_achieved: Optional context prioritization percentage achieved
    """

    completed: list[StageResult]
    failed: list[str]
    status: str
    duration_seconds: float
    token_reduction_achieved: Optional[float] = None

    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate of the workflow.

        Returns:
            float: Success rate as a decimal (0.0 to 1.0)
        """
        total_stages = len(self.completed) + len(self.failed)
        if total_stages == 0:
            return 0.0

        return len(self.completed) / total_stages
