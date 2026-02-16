"""
Tests for agent templates depth toggle feature (Handover 0347d).

Tests the new agent_templates depth configuration that controls whether
orchestrators receive minimal metadata or full agent prompts.

Token Budget Impact:
- type_only: ~50 tokens per agent (~250 for 5 agents)
- full: ~2500 tokens per agent (~12,500 for 5 agents)
"""

from uuid import uuid4

import pytest
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import AgentTemplate, Product, Project
from src.giljo_mcp.models.auth import User


@pytest.fixture
async def db_manager(test_database_url):
    """Create async database manager for tests."""
    db = DatabaseManager(database_url=test_database_url, is_async=True)
    yield db
    await db.close_async()


@pytest.fixture
async def test_user(db_manager: DatabaseManager, tenant_key: str, user_id: str):
    """Create test user for depth configuration."""
    async with db_manager.get_session_async() as session:
        # Generate unique username and email to avoid constraint violations
        unique_suffix = str(uuid4())[:8]
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            email=f"test-{unique_suffix}@example.com",
            username=f"testuser-{unique_suffix}",
            password_hash="fakehash",
            is_active=True,
            depth_config=None,  # Will be set in individual tests
            field_priority_config=None,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def sample_agent_templates(db_manager: DatabaseManager, tenant_key: str):
    """Create sample agent templates for testing."""
    async with db_manager.get_session_async() as session:
        templates = [
            AgentTemplate(
                tenant_key=tenant_key,
                name="backend-integration-tester",
                role="Backend Integration Tester",
                description="Specialist in backend integration testing with focus on API contracts and data flow validation",
                system_instructions="""# Backend Integration Tester Agent

You are a specialist backend integration tester focused on API contracts and data flow validation.

## Responsibilities
- Design and implement integration test suites
- Validate API contracts and data schemas
- Test database transactions and rollback scenarios
- Verify microservice communication patterns

## Testing Approach
- Use pytest with async fixtures for FastAPI testing
- Implement API contract testing with Pydantic schemas
- Test database isolation and transaction boundaries
- Mock external service dependencies appropriately

## Success Criteria
- All integration tests pass consistently
- API contracts are validated end-to-end
- Database transactions are properly isolated
- Test coverage meets or exceeds 80% target
""",
                cli_tool="claude-code",
                background_color="#4CAF50",
                category="testing",
                is_active=True,
            ),
            AgentTemplate(
                tenant_key=tenant_key,
                name="tdd-implementor",
                role="TDD Implementor",
                description="Master developer following strict test-driven development principles with production-grade code quality",
                system_instructions="""# TDD Implementor Agent

You are a master developer who follows strict test-driven development principles.

## Core Workflow - TEST-DRIVEN DEVELOPMENT

1. **TEST FIRST**: Write comprehensive tests before any implementation code
2. **COMMIT TESTS**: Commit the failing tests with clear message
3. **IMPLEMENT**: Write code to make tests pass
4. **ITERATE**: Refine and optimize
5. **COMMIT IMPLEMENTATION**: Commit working code

## Critical Coding Standards

### Cross-Platform Compatibility (NON-NEGOTIABLE)
- ALWAYS use proper path handling for file paths
- NEVER hardcode path separators or OS-specific assumptions
- Use standard library path utilities (pathlib.Path in Python)

### Code Quality Requirements
- Type annotations for all public APIs
- Clear documentation with docstrings
- Specific exception types with proper error handling
- Comprehensive logging for debugging

## Quality Gates
- All tests pass
- Linting clean
- Formatting applied
- Static analysis passes
- Cross-platform validated
""",
                cli_tool="claude-code",
                background_color="#2196F3",
                category="development",
                is_active=True,
            ),
            AgentTemplate(
                tenant_key=tenant_key,
                name="system-architect",
                role="System Architect",
                description="Expert in software architecture design, system patterns, and technical decision-making for scalable solutions",
                system_instructions="""# System Architect Agent

You are an expert system architect responsible for high-level design decisions.

## Responsibilities
- Design system architecture and component boundaries
- Make technical decisions with clear documentation
- Define integration patterns between services
- Establish coding standards and best practices
- Create architecture decision records (ADRs)

## Architecture Principles
- SOLID principles for object-oriented design
- Domain-driven design (DDD) for complex domains
- Microservices patterns for distributed systems
- Event-driven architecture when appropriate

## Deliverables
- Architecture diagrams (C4 model preferred)
- Technical specifications with decision rationale
- Integration patterns documentation
- Non-functional requirements (performance, security, scalability)
""",
                cli_tool="claude-code",
                background_color="#FF9800",
                category="architecture",
                is_active=True,
            ),
            AgentTemplate(
                tenant_key=tenant_key,
                name="documentation-manager",
                role="Documentation Manager",
                description="Technical writer creating clear, comprehensive documentation for APIs, user guides, and architecture decisions",
                system_instructions="""# Documentation Manager Agent

You are a technical writer specialized in developer documentation.

## Documentation Types
- API documentation with OpenAPI/Swagger specs
- User guides with step-by-step instructions
- Architecture decision records (ADRs)
- README files with quick start guides
- Inline code documentation (docstrings)

## Writing Standards
- Clear, concise language avoiding jargon
- Consistent formatting with markdown
- Code examples for complex concepts
- Visual diagrams where beneficial
- Keep documentation DRY (Don't Repeat Yourself)

## Success Criteria
- All public APIs fully documented
- User workflows clearly explained
- Examples tested and verified
- Documentation versioned with code
""",
                cli_tool="claude-code",
                background_color="#9C27B0",
                category="documentation",
                is_active=True,
            ),
            AgentTemplate(
                tenant_key=tenant_key,
                name="orchestrator-coordinator",
                role="Orchestrator Coordinator",
                description="Master coordinator managing agent workflows, dependencies, and project execution with context awareness",
                system_instructions="""# Orchestrator Coordinator Agent

You are the master coordinator responsible for managing all agent activities.

## Core Responsibilities
- Analyze project requirements and create execution plan
- Spawn specialist agents based on task complexity
- Coordinate agent workflows and dependencies
- Monitor context budget and trigger succession when needed
- Ensure all agents stay within scope boundaries

## Workflow Management
- Break down complex tasks into agent-sized work items
- Establish clear dependencies between agents
- Monitor progress and adjust plans dynamically
- Facilitate inter-agent communication
- Escalate blockers to human oversight when needed

## Context Management
- Track context usage across all agents
- Trigger orchestrator succession at 90% capacity
- Generate handover summaries for successors
- Maintain lineage chain for audit trail

## Agent Spawning Strategy
- Maximum 5-7 agents for optimal coordination
- Prefer specialist agents over generalists
- Ensure clear scope boundaries for each agent
- Avoid duplicate responsibilities across agents
""",
                cli_tool="claude-code",
                background_color="#F44336",
                category="orchestration",
                is_active=True,
            ),
        ]

        for template in templates:
            session.add(template)

        await session.commit()

        # Refresh to get IDs
        for template in templates:
            await session.refresh(template)

        return templates


@pytest.fixture
async def sample_product_and_project(db_manager: DatabaseManager, tenant_key: str, user_id: str):
    """Create sample product and project for testing."""
    async with db_manager.get_session_async() as session:
        product = Product(
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product for agent template depth testing",
            config_data={
                "tech_stack": {
                    "languages": ["Python 3.11+"],
                    "backend": ["FastAPI", "SQLAlchemy"],
                    "frontend": ["Vue 3", "Vuetify"],
                    "database": ["PostgreSQL 18"],
                },
                "architecture": "Multi-tenant SaaS application with service layer pattern",
                "testing": {
                    "methodology": "TDD with pytest",
                    "coverage_target": 80,
                },
            },
        )
        session.add(product)
        await session.flush()

        project = Project(
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Implement agent templates depth toggle feature",
            mission="Add depth configuration for agent templates",
            status="active",
        )
        session.add(project)
        await session.commit()

        await session.refresh(product)
        await session.refresh(project)

        return product, project


class TestGetFullAgentTemplates:
    """Tests for MissionPlanner._get_full_agent_templates() helper method."""

    @pytest.mark.asyncio
    async def test_get_full_agent_templates_returns_complete_data(self, db_manager, tenant_key, sample_agent_templates):
        """Test that _get_full_agent_templates returns all fields for enabled templates."""
        planner = MissionPlanner(db_manager)

        async with db_manager.get_session_async() as session:
            result = await planner._get_full_agent_templates(tenant_key, session)

        # Should return all 5 templates
        assert len(result) == 5

        # Check first template has all required fields
        template = result[0]
        assert "name" in template
        assert "role" in template
        assert "description" in template
        assert "content" in template  # Full prompt content
        assert "cli_tool" in template
        assert "background_color" in template
        assert "category" in template

        # Verify content is not truncated
        assert len(template["content"]) > 500
        assert (
            "# Backend Integration Tester Agent" in template["content"]
            or "# TDD Implementor Agent" in template["content"]
        )

    @pytest.mark.asyncio
    async def test_get_full_agent_templates_filters_by_tenant(self, db_manager, tenant_key, sample_agent_templates):
        """Test that _get_full_agent_templates enforces tenant isolation."""
        planner = MissionPlanner(db_manager)

        # Try to fetch with wrong tenant key
        async with db_manager.get_session_async() as session:
            result = await planner._get_full_agent_templates("wrong-tenant", session)

        # Should return empty list
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_full_agent_templates_only_returns_active(self, db_manager, tenant_key, sample_agent_templates):
        """Test that _get_full_agent_templates only returns active templates."""
        # Deactivate one template
        async with db_manager.get_session_async() as session:
            template = sample_agent_templates[0]
            template.is_active = False
            session.add(template)
            await session.commit()

        planner = MissionPlanner(db_manager)

        async with db_manager.get_session_async() as session:
            result = await planner._get_full_agent_templates(tenant_key, session)

        # Should return 4 templates (1 deactivated)
        assert len(result) == 4


# Pytest fixtures for test data
@pytest.fixture
def tenant_key():
    """Provide test tenant key."""
    return "test-tenant-" + str(uuid4())[:8]


@pytest.fixture
def user_id():
    """Provide test user ID."""
    return str(uuid4())


@pytest.fixture
def test_database_url():
    """Provide test database URL (override in pytest.ini or conftest.py)."""
    import os

    return os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp_test")
