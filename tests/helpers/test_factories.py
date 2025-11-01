"""
Test data factories for consistent test data generation
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from src.giljo_mcp.models import Agent, Message, Project


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
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "mission": mission,
            "status": status,
            "tenant_key": tenant_key or str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    @staticmethod
    def create_agent_data(
        project_id: str, name: str = "test_agent", agent_type: str = "worker", status: str = "active"
    ) -> dict[str, Any]:
        """Create agent data dictionary"""
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": agent_type,
            "status": status,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

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
    """Factory for creating Agent model instances"""

    @staticmethod
    def build(project_id: str, **kwargs) -> Agent:
        """Build an Agent instance with default values"""
        defaults = TestDataFactory.create_agent_data(project_id)
        defaults.update(kwargs)
        return Agent(**defaults)


class MessageFactory:
    """Factory for creating Message model instances"""

    @staticmethod
    def build(from_agent: str, to_agents: list[str], content: str, project_id: str, **kwargs) -> Message:
        """Build a Message instance with default values"""
        defaults = TestDataFactory.create_message_data(from_agent, to_agents, content, project_id)
        defaults.update(kwargs)
        return Message(**defaults)
