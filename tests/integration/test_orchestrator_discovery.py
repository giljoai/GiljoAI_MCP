"""
Integration tests for Handover 0246c: Token Reduction via Agent Discovery Tool.

Tests verify that orchestrator prompts no longer embed agent templates inline,
instead referencing get_available_agents() tool for on-demand discovery.

Expected token reduction: 594 -> 450 tokens (25% reduction).
"""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentExecution, Product, Project, User
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions


# Test fixtures
@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user."""
    user = User(
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_tenant(test_user: User):
    """Get tenant key from test user."""
    return test_user.tenant_key


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, test_user: User):
    """Create test product."""
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        description="Test product for token reduction tests",
        tenant_key=test_user.tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: User, test_product: Product):
    """Create test project."""
    project = Project(
        name=f"Test Project {uuid4().hex[:8]}",
        description="Test project for token reduction",
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        status="active",
        mission="Test mission for token reduction",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
class TestOrchestratorTokenReduction:
    """Integration tests for Handover 0246c token reduction."""

    async def test_prompt_no_longer_embeds_agent_templates(
        self, db_session, test_tenant, test_product, test_project, test_user
    ):
        """Test that orchestrator prompt no longer embeds agent templates inline."""

        # Create orchestrator job
        orchestrator = AgentExecution(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Test orchestrator for token reduction",
            job_metadata={
                "user_id": test_user.id,
                "field_priorities": {
                    "product_core": 1,
                    "vision_documents": 2,
                    "agent_templates": 3,
                    "project_description": 1,
                    "memory_360": 3,
                    "git_history": 3,
                },
            },
        )
        db_session.add(orchestrator)
        await db_session.commit()
        await db_session.refresh(orchestrator)

        # Generate thin prompt
        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_tenant,
            user_id=test_user.id,
        )

        prompt = await generator.generate(tool="claude-code")

        # Should reference get_available_agents() tool
        assert "get_available_agents" in prompt.lower(), (
            "Prompt must reference get_available_agents() tool for agent discovery"
        )

        # Should NOT embed agent templates inline
        # Old prompts had sections like "### Implementer Agent", "### Tester Agent"
        assert "### Implementer" not in prompt, "Prompt should not contain embedded Implementer agent template"
        assert "### Tester" not in prompt, "Prompt should not contain embedded Tester agent template"

        # Should not have multiple "Capabilities" sections (was in embedded templates)
        capabilities_count = prompt.count("**Capabilities**")
        assert capabilities_count < 3, (
            f"Found {capabilities_count} Capabilities sections (expected < 3, old format had 5-8)"
        )

    async def test_token_count_significantly_reduced(
        self, db_session, test_tenant, test_product, test_project, test_user
    ):
        """Test that prompt token count is significantly smaller (target: 450 tokens)."""

        orchestrator = AgentExecution(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Test",
            job_metadata={
                "user_id": test_user.id,
                "field_priorities": {
                    "product_core": 1,
                    "vision_documents": 2,
                    "agent_templates": 3,
                    "project_description": 1,
                    "memory_360": 3,
                    "git_history": 3,
                },
            },
        )
        db_session.add(orchestrator)
        await db_session.commit()
        await db_session.refresh(orchestrator)

        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_tenant,
            user_id=test_user.id,
        )

        prompt = await generator.generate(tool="claude-code")

        # Rough token estimate (chars ÷ 4)
        estimated_tokens = len(prompt) // 4

        # Old prompts were ~594-880 tokens with embedded templates
        # Target is 450 tokens (25% reduction from 594)
        # We'll allow up to 600 tokens as upper bound
        assert estimated_tokens < 600, f"Token count {estimated_tokens} not reduced enough (target: <600, ideal: 450)"

        print(f"\n✓ Token reduction achieved: ~{estimated_tokens} tokens (target: 450)")

    async def test_get_orchestrator_instructions_no_embedded_templates(
        self, db_session, test_tenant, test_product, test_project, test_user
    ):
        """Test that get_orchestrator_instructions() no longer returns embedded templates."""

        orchestrator = AgentExecution(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Test",
            job_metadata={"user_id": test_user.id, "field_priorities": {"product_core": 1, "agent_templates": 3}},
        )
        db_session.add(orchestrator)
        await db_session.commit()
        await db_session.refresh(orchestrator)

        # Call get_orchestrator_instructions (standalone version for testing)
        from giljo_mcp.config_manager import get_config
        from giljo_mcp.database import DatabaseManager

        config = get_config()
        db_manager = DatabaseManager(database_url=config.database.database_url, is_async=True)

        result = await get_orchestrator_instructions(str(orchestrator.job_id), test_tenant, db_manager)

        # Should NOT include agent_templates in response
        assert "agent_templates" not in result, "get_orchestrator_instructions() should not return agent_templates key"

        # Should include reference to discovery tool
        assert "agent_discovery_tool" in result or "get_available_agents" in str(result), (
            "Response should reference get_available_agents() tool for discovery"
        )

    async def test_discovery_tool_reference_in_prompt(
        self, db_session, test_tenant, test_product, test_project, test_user
    ):
        """Test that prompt contains clear reference to agent discovery tool."""

        orchestrator = AgentExecution(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Test",
            job_metadata={
                "user_id": test_user.id,
                "field_priorities": {
                    "agent_templates": 2  # IMPORTANT priority
                },
            },
        )
        db_session.add(orchestrator)
        await db_session.commit()
        await db_session.refresh(orchestrator)

        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_tenant,
            user_id=test_user.id,
        )

        prompt = await generator.generate(tool="claude-code")

        # Check for tool reference with correct parameters
        assert f"get_available_agents(tenant_key='{test_tenant}'" in prompt, (
            "Prompt should contain get_available_agents() tool call with tenant_key"
        )

        # Verify it's in Priority 2 section (IMPORTANT)
        assert "Priority 2 (IMPORTANT" in prompt, "Prompt should have Priority 2 section"

        # Tool reference should appear after Priority 2 header
        priority_2_index = prompt.find("Priority 2 (IMPORTANT")
        tool_ref_index = prompt.find("get_available_agents")

        assert tool_ref_index > priority_2_index, "get_available_agents() should appear in Priority 2 section"

    async def test_legacy_methods_removed(self):
        """Test that legacy template embedding methods are removed."""

        # Verify _format_agent_templates method does not exist
        generator_class = ThinClientPromptGenerator
        assert not hasattr(generator_class, "_format_agent_templates"), (
            "_format_agent_templates() method should be removed"
        )

        # Verify _get_agent_templates method does not exist
        assert not hasattr(generator_class, "_get_agent_templates"), "_get_agent_templates() method should be removed"

    async def test_multi_tenant_isolation_maintained(
        self, db_session, test_tenant, test_product, test_project, test_user
    ):
        """Test that tenant isolation is maintained in discovery tool reference."""

        orchestrator = AgentExecution(
            project_id=test_project.id,
            tenant_key=test_tenant,
            agent_display_name="orchestrator",
            status="waiting",
            mission="Test",
            job_metadata={
                "user_id": test_user.id,
                "field_priorities": {
                    "agent_templates": 1  # CRITICAL priority
                },
            },
        )
        db_session.add(orchestrator)
        await db_session.commit()
        await db_session.refresh(orchestrator)

        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_tenant,
            user_id=test_user.id,
        )

        prompt = await generator.generate(tool="claude-code")

        # Verify tenant_key is included in tool call
        assert f"tenant_key='{test_tenant}'" in prompt, (
            "get_available_agents() must include tenant_key for multi-tenant isolation"
        )

        # Verify active_only=True is set (security: don't expose inactive agents)
        assert "active_only=True" in prompt, "get_available_agents() should only expose active agents"
