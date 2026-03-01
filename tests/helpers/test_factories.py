"""
Test data factories for consistent test data generation
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


class TestDataFactory:
    """Factory for creating test data objects"""

    @staticmethod
    def create_project_data(
        name: str = "Test Project",
        description: str = "Test project description for testing purposes",
        mission: str = "Test mission for integration testing",
        status: str = "active",
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create project data dictionary"""
        import random

        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "mission": mission,
            "status": status,
            "tenant_key": tenant_key or str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "series_number": random.randint(1, 999999),
        }

    @staticmethod
    def create_agent_job_data(
        project_id: str,
        tenant_key: str,
        job_type: str = "worker",
        mission: str = "Test mission for agent job",
        status: str = "active",
    ) -> dict[str, Any]:
        """
        Create AgentJob data dictionary (work order - the WHAT).

        Migration Note (0367d): Replaced MCPAgentJob with AgentJob.
        Field mappings:
        - AgentExecution.agent_display_name → AgentJob.job_type
        - AgentExecution.status values → AgentJob.status (active/completed/cancelled)
        """
        return {
            "job_id": str(uuid.uuid4()),
            "tenant_key": tenant_key,
            "project_id": project_id,
            "job_type": job_type,
            "mission": mission,
            "status": status,
            "created_at": datetime.now(timezone.utc),
            "job_metadata": {},
        }

    @staticmethod
    def create_agent_execution_data(
        job_id: str,
        tenant_key: str,
        agent_name: str = "test_agent",
        agent_display_name: str = "worker",
        status: str = "waiting",
    ) -> dict[str, Any]:
        """
        Create AgentExecution data dictionary (executor - the WHO).

        Migration Note (0367d): Extracted from AgentExecution.
        Execution-specific fields:
        - status: waiting/working/blocked/complete/failed/cancelled/decommissioned
        - progress, messages, spawned_by, succeeded_by, etc.
        """
        return {
            "agent_id": str(uuid.uuid4()),
            "job_id": job_id,
            "tenant_key": tenant_key,
            "agent_display_name": agent_display_name,
            "agent_name": agent_name,
            "status": status,
            "progress": 0,
            "messages_sent_count": 0,
            "messages_waiting_count": 0,
            "messages_read_count": 0,
            "health_status": "unknown",
            "tool_type": "universal",
        }

    @staticmethod
    def create_agent_data(
        project_id: str,
        tenant_key: str,
        agent_name: str = "test_agent",
        agent_display_name: str = "worker",
        mission: str = "Test mission for agent job",
        status: str = "waiting",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Create both AgentJob and AgentExecution data (backward compatibility).

        Migration Note (0367d): Replaced MCPAgentJob with AgentJob + AgentExecution.
        Returns tuple of (job_data, execution_data) for tests that need both.

        For new tests, use create_agent_job_data() and create_agent_execution_data() directly.
        """
        # Map old status to new job status (3 values: active/completed/cancelled)
        job_status = "active" if status in ["waiting", "working", "blocked"] else status

        job_data = TestDataFactory.create_agent_job_data(
            project_id=project_id,
            tenant_key=tenant_key,
            job_type=agent_display_name,
            mission=mission,
            status=job_status,
        )

        execution_data = TestDataFactory.create_agent_execution_data(
            job_id=job_data["job_id"],
            tenant_key=tenant_key,
            agent_name=agent_name,
            agent_display_name=agent_display_name,
            status=status,
        )

        return job_data, execution_data

    @staticmethod
    def create_message_data(
        from_agent: str,
        to_agents: list[str],
        content: str,
        project_id: str,
        message_type: str = "direct",
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Create message data dictionary"""
        return {
            "id": str(uuid.uuid4()),
            "from_agent": from_agent,
            "to_agents": to_agents,
            "content": content,
            "project_id": project_id,
            "type": message_type,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        }

    @staticmethod
    def create_task_data(content: str, category: str = "general", priority: str = "medium") -> dict[str, Any]:
        """Create task data dictionary"""
        return {
            "id": str(uuid.uuid4()),
            "content": content,
            "category": category,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
        }


class ProjectFactory:
    """Factory for creating Project model instances"""

    @staticmethod
    def build(**kwargs) -> Project:
        """Build a Project instance with default values"""
        defaults = TestDataFactory.create_project_data()
        defaults.update(kwargs)
        return Project(**defaults)


class AgentFactory:
    """
    Factory for creating AgentJob and AgentExecution model instances.

    Migration Note (0367d): Replaced MCPAgentJob with AgentJob + AgentExecution.
    """

    @staticmethod
    def build(project_id: str, tenant_key: str, **kwargs) -> tuple[AgentJob, AgentExecution]:
        """
        Build AgentJob and AgentExecution instances with default values.

        Migration Note (0367d): Now returns tuple of (job, execution).
        For backward compatibility, returns both models.
        Tests can use: job, execution = AgentFactory.build(...)
        """
        job_data, execution_data = TestDataFactory.create_agent_data(project_id, tenant_key, **kwargs)

        job = AgentJob(**job_data)
        execution = AgentExecution(**execution_data)

        return job, execution

    @staticmethod
    def build_job(project_id: str, tenant_key: str, **kwargs) -> AgentJob:
        """Build only AgentJob instance (work order - the WHAT)"""
        defaults = TestDataFactory.create_agent_job_data(project_id, tenant_key)
        defaults.update(kwargs)
        return AgentJob(**defaults)

    @staticmethod
    def build_execution(job_id: str, tenant_key: str, **kwargs) -> AgentExecution:
        """Build only AgentExecution instance (executor - the WHO)"""
        defaults = TestDataFactory.create_agent_execution_data(job_id, tenant_key)
        defaults.update(kwargs)
        return AgentExecution(**defaults)

    @staticmethod
    def build_with_execution(project_id: str, tenant_key: str, **kwargs) -> tuple[AgentJob, AgentExecution]:
        """
        Explicitly build both job and execution.
        Alias for build() for clarity in tests.
        """
        return AgentFactory.build(project_id, tenant_key, **kwargs)


class MessageFactory:
    """Factory for creating Message model instances"""

    @staticmethod
    def build(from_agent: str, to_agents: list[str], content: str, project_id: str, **kwargs) -> Message:
        """Build a Message instance with default values"""
        defaults = TestDataFactory.create_message_data(from_agent, to_agents, content, project_id)
        defaults.update(kwargs)
        return Message(**defaults)
