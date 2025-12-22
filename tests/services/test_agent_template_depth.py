"""
Tests for agent templates depth toggle feature (Handover 0347d).

Tests the new agent_templates depth configuration that controls whether
orchestrators receive minimal metadata or full agent prompts.

Token Budget Impact:
- type_only: ~50 tokens per agent (~250 for 5 agents)
- full: ~2500 tokens per agent (~12,500 for 5 agents)
"""

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.mission_planner import MissionPlanner
from giljo_mcp.models import Product, Project, AgentTemplate
from giljo_mcp.models.agent_identity import AgentExecution
from giljo_mcp.models.auth import User
from giljo_mcp.tools.orchestration import get_orchestrator_instructions


@pytest.fixture
async def db_manager(test_database_url):
    """Create async database manager for tests."""
    db = DatabaseManager(database_url=test_database_url, is_async=True)
    yield db
    await db.close()


@pytest.fixture
async def test_user(db_manager: DatabaseManager, tenant_key: str, user_id: str):
    """Create test user for depth configuration."""
    async with db_manager.get_session_async() as session:
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            email="test@example.com",
            username="testuser",
            hashed_password="fakehash",
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
                content="""# Backend Integration Tester Agent

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
                content="""# TDD Implementor Agent

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
                content="""# System Architect Agent

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
                content="""# Documentation Manager Agent

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
                content="""# Orchestrator Coordinator Agent

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
    async def test_get_full_agent_templates_returns_complete_data(
        self, db_manager, tenant_key, sample_agent_templates
    ):
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
        assert "# Backend Integration Tester Agent" in template["content"] or "# TDD Implementor Agent" in template["content"]

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


class TestAgentTemplateDepthIntegration:
    """Integration tests for agent templates depth configuration in orchestrator instructions."""

    @pytest.mark.asyncio
    async def test_type_only_mode_returns_minimal_agent_data(
        self, db_manager, tenant_key, user_id, sample_product_and_project, sample_agent_templates
    ):
        """Test that type_only depth mode returns minimal agent template data (~50 tokens/agent)."""
        product, project = sample_product_and_project

        # Create orchestrator job
        async with db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                tenant_key=tenant_key,
                job_id=str(uuid4()),
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                project_id=project.id,
                mission="Test mission",
                status="pending",
                context_budget=150000,
            )
            session.add(orchestrator)
            await session.commit()
            await session.refresh(orchestrator)

            # Set user config with agent_templates depth = type_only
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()
            user.depth_config = {
                "agent_templates": "type_only",
                "memory_360": 5,
                "git_history": 20,
                "vision_documents": "medium",
            }
            await session.commit()

        # Fetch orchestrator instructions
        instructions = await get_orchestrator_instructions(
            orchestrator_id=str(orchestrator.job_id),
            tenant_key=tenant_key,
            user_id=user_id,
            db_manager=db_manager,
        )

        # Verify mission is JSON format (Handover 0347b)
        assert instructions["mission_format"] == "json"
        mission = instructions["mission"]

        # Check that agent templates are in "important" tier with minimal data
        assert "important" in mission
        assert "agent_templates" in mission["important"]

        agent_templates_data = mission["important"]["agent_templates"]

        # Should have summary and fetch tool pointer (not full content)
        assert "summary" in agent_templates_data or "templates" in agent_templates_data

        # If templates are included, they should be minimal (type_only format)
        if "templates" in agent_templates_data:
            templates = agent_templates_data["templates"]
            assert len(templates) > 0

            # Check first template has minimal data
            template = templates[0]
            assert "name" in template
            assert "role" in template
            assert "description" in template

            # Description should be truncated to ~200 chars
            assert len(template["description"]) <= 220

            # Should NOT have full content field
            assert "content" not in template

        # Estimated token count should be low (<500 tokens for agent_templates section)
        # Type only mode: ~50 tokens per agent * 5 = ~250 tokens
        import json
        agent_section_json = json.dumps(agent_templates_data)
        agent_section_tokens = len(agent_section_json) // 4
        assert agent_section_tokens < 500, f"Agent templates section too large: {agent_section_tokens} tokens (expected <500)"

    @pytest.mark.asyncio
    async def test_full_mode_returns_complete_agent_prompts(
        self, db_manager, tenant_key, user_id, sample_product_and_project, sample_agent_templates
    ):
        """Test that full depth mode returns complete agent prompts (~2500 tokens/agent)."""
        product, project = sample_product_and_project

        # Create orchestrator job
        async with db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                tenant_key=tenant_key,
                job_id=str(uuid4()),
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                project_id=project.id,
                mission="Test mission",
                status="pending",
                context_budget=150000,
            )
            session.add(orchestrator)
            await session.commit()
            await session.refresh(orchestrator)

            # Set user config with agent_templates depth = full
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()
            user.depth_config = {
                "agent_templates": "full",
                "memory_360": 5,
                "git_history": 20,
                "vision_documents": "medium",
            }
            await session.commit()

        # Fetch orchestrator instructions
        instructions = await get_orchestrator_instructions(
            orchestrator_id=str(orchestrator.job_id),
            tenant_key=tenant_key,
            user_id=user_id,
            db_manager=db_manager,
        )

        # Verify mission is JSON format
        assert instructions["mission_format"] == "json"
        mission = instructions["mission"]

        # Check that agent templates are in "important" tier with full data
        assert "important" in mission
        assert "agent_templates" in mission["important"]

        agent_templates_data = mission["important"]["agent_templates"]

        # Should have full template data
        assert "templates" in agent_templates_data
        templates = agent_templates_data["templates"]
        assert len(templates) > 0

        # Check first template has complete data
        template = templates[0]
        assert "name" in template
        assert "role" in template
        assert "description" in template
        assert "content" in template  # Full prompt content

        # Content should be complete (not truncated)
        assert len(template["content"]) > 500
        assert "##" in template["content"]  # Should have markdown headers

        # Description should NOT be truncated
        assert len(template["description"]) > 50

        # Estimated token count should be high (>10,000 tokens for all templates)
        # Full mode: ~2500 tokens per agent * 5 = ~12,500 tokens
        import json
        agent_section_json = json.dumps(agent_templates_data)
        agent_section_tokens = len(agent_section_json) // 4
        assert agent_section_tokens > 10000, f"Agent templates section too small: {agent_section_tokens} tokens (expected >10,000)"

    @pytest.mark.asyncio
    async def test_invalid_depth_defaults_to_type_only(
        self, db_manager, tenant_key, user_id, sample_product_and_project, sample_agent_templates
    ):
        """Test that invalid depth values gracefully default to type_only."""
        product, project = sample_product_and_project

        # Create orchestrator job
        async with db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                tenant_key=tenant_key,
                job_id=str(uuid4()),
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                project_id=project.id,
                mission="Test mission",
                status="pending",
                context_budget=150000,
            )
            session.add(orchestrator)
            await session.commit()
            await session.refresh(orchestrator)

            # Set user config with INVALID agent_templates depth
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()
            user.depth_config = {
                "agent_templates": "INVALID_VALUE",  # Invalid depth value
                "memory_360": 5,
                "git_history": 20,
                "vision_documents": "medium",
            }
            await session.commit()

        # Fetch orchestrator instructions
        instructions = await get_orchestrator_instructions(
            orchestrator_id=str(orchestrator.job_id),
            tenant_key=tenant_key,
            user_id=user_id,
            db_manager=db_manager,
        )

        # Should not error - gracefully defaults to type_only
        assert "error" not in instructions
        assert instructions["mission_format"] == "json"
        mission = instructions["mission"]

        # Check agent templates are present (minimal format as fallback)
        assert "important" in mission
        assert "agent_templates" in mission["important"]

        # Verify token count is low (type_only fallback)
        import json
        agent_section_json = json.dumps(mission["important"]["agent_templates"])
        agent_section_tokens = len(agent_section_json) // 4
        assert agent_section_tokens < 500, "Invalid depth should default to type_only (low token count)"

    @pytest.mark.asyncio
    async def test_backwards_compatibility_missing_config(
        self, db_manager, tenant_key, user_id, sample_product_and_project, sample_agent_templates
    ):
        """Test backwards compatibility when depth_config is missing."""
        product, project = sample_product_and_project

        # Create orchestrator job
        async with db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                tenant_key=tenant_key,
                job_id=str(uuid4()),
                agent_type="orchestrator",
                agent_name="Test Orchestrator",
                project_id=project.id,
                mission="Test mission",
                status="pending",
                context_budget=150000,
            )
            session.add(orchestrator)
            await session.commit()
            await session.refresh(orchestrator)

            # Set user config with NO depth_config field
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()
            user.depth_config = None  # Missing depth config
            await session.commit()

        # Fetch orchestrator instructions
        instructions = await get_orchestrator_instructions(
            orchestrator_id=str(orchestrator.job_id),
            tenant_key=tenant_key,
            user_id=user_id,
            db_manager=db_manager,
        )

        # Should not error - use defaults
        assert "error" not in instructions
        assert instructions["mission_format"] == "json"
        mission = instructions["mission"]

        # Check agent templates are present with default behavior
        assert "important" in mission
        assert "agent_templates" in mission["important"]

        # Default should be type_only (token efficient)
        import json
        agent_section_json = json.dumps(mission["important"]["agent_templates"])
        agent_section_tokens = len(agent_section_json) // 4
        assert agent_section_tokens < 500, "Missing config should default to type_only"


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
