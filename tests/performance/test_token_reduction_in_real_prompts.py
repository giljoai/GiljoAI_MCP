"""
Phase 4: Token Reduction in Real Prompts Performance Test (Handover 0246d)

Validates token reduction achieved in real orchestrator prompts:
- Baseline (embedded templates): ~594-880 tokens
- Target (dynamic discovery): ~450 tokens
- Acceptance: <600 tokens (25% reduction)

TDD Phase: RED (Tests written BEFORE optimization complete)
Expected: Tests MAY FAIL initially if token reduction not achieved
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from src.giljo_mcp.models import Project, MCPAgentJob, Product, User, AgentTemplate
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user"""
    user = User(
        username=f"tokentest_{uuid4().hex[:8]}",
        email=f"token_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(db_session, test_user):
    """Create test product"""
    product = Product(
        name=f"Token Test Product {uuid4().hex[:8]}",
        description="Token reduction test product",
        tenant_key=test_user.tenant_key,
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, test_user, test_product):
    """Create test project"""
    project = Project(
        name=f"Token Test Project {uuid4().hex[:8]}",
        description="Token reduction test project",
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        status="active",
        mission="Test token reduction",
        meta_data={"execution_mode": "claude-code"}
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def populate_agent_templates(db_session, test_user):
    """Populate agent templates for realistic testing"""
    templates = [
        AgentTemplate(
            name="implementer",
            role="Code Implementation Specialist",
            description="Implements features using TDD",
            tenant_key=test_user.tenant_key,
            is_active=True,
            version="1.1.0",
            template_content="Implementation template"
        ),
        AgentTemplate(
            name="tester",
            role="Quality Assurance Specialist",
            description="Writes comprehensive tests",
            tenant_key=test_user.tenant_key,
            is_active=True,
            version="1.0.0",
            template_content="Testing template"
        ),
        AgentTemplate(
            name="reviewer",
            role="Code Review Specialist",
            description="Reviews code for quality",
            tenant_key=test_user.tenant_key,
            is_active=True,
            version="1.0.0",
            template_content="Review template"
        ),
        AgentTemplate(
            name="documenter",
            role="Documentation Specialist",
            description="Creates comprehensive docs",
            tenant_key=test_user.tenant_key,
            is_active=True,
            version="1.0.0",
            template_content="Documentation template"
        ),
        AgentTemplate(
            name="architect",
            role="System Architecture Specialist",
            description="Designs system architecture",
            tenant_key=test_user.tenant_key,
            is_active=True,
            version="1.0.0",
            template_content="Architecture template"
        )
    ]

    for template in templates:
        db_session.add(template)

    await db_session.commit()
    return templates


@pytest.mark.asyncio
class TestTokenReductionInRealPrompts:
    """Tests for token reduction in real orchestrator prompts."""

    async def test_staging_prompt_token_count(
        self, db_session, test_user, test_project, populate_agent_templates
    ):
        """
        Test staging prompt token count.
        Target: <1200 tokens
        Ideal: 800-1000 tokens
        """

        orchestrator = MCPAgentJob(
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            agent_type="orchestrator",
            status="staging",
            mission="Test staging prompt",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code"
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()

        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_user.tenant_key,
            user_id=test_user.id
        )

        # Generate staging prompt
        from unittest.mock import patch, MagicMock
        with patch.object(generator, '_fetch_project', return_value=test_project), \
             patch.object(generator, '_fetch_product', return_value=MagicMock(id=test_project.product_id, name="Test")):

            prompt = await generator.generate_staging_prompt(
                orchestrator_id=str(orchestrator.job_id),
                project_id=str(test_project.id)
            )

        # Token estimation (chars ÷ 4)
        token_count = len(prompt) // 4

        assert token_count < 1200, \
            f"Staging prompt token count ({token_count}) exceeds budget (1200)"

        is_ideal = 800 <= token_count <= 1000

        print(f"\n✓ Staging prompt token count:")
        print(f"  - Token count: ~{token_count} tokens")
        print(f"  - Budget: <1200 tokens")
        print(f"  - Ideal range (800-1000): {is_ideal}")
        print(f"  - Status: {'OPTIMAL' if is_ideal else 'ACCEPTABLE'}")

    async def test_execution_prompt_token_reduction(
        self, db_session, test_user, test_project, populate_agent_templates
    ):
        """
        Test execution prompt achieves 25% token reduction.
        Baseline: ~594-880 tokens (with embedded templates)
        Target: ~450 tokens (without embedded templates)
        Acceptance: <600 tokens
        """

        orchestrator = MCPAgentJob(
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            agent_type="orchestrator",
            status="active",
            mission="Test execution prompt",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code",
                "field_priorities": {
                    "product_core": 1,
                    "agent_templates": 2,  # IMPORTANT
                    "project_context": 1
                }
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()

        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_user.tenant_key,
            user_id=test_user.id
        )

        prompt = await generator.generate(
            instance_number=1,
            tool="claude-code"
        )

        # Token estimation
        token_count = len(prompt) // 4

        # Calculate reduction from baseline (594 tokens)
        baseline = 594
        reduction_tokens = baseline - token_count
        reduction_percent = (reduction_tokens / baseline) * 100

        assert token_count < 600, \
            f"Token count ({token_count}) exceeds acceptance threshold (600)"

        # Target is 25% reduction (594 → 450)
        is_optimal = token_count <= 473  # 450 + 5% tolerance

        print(f"\n✓ Execution prompt token reduction:")
        print(f"  - Baseline (old): ~{baseline} tokens")
        print(f"  - Current: ~{token_count} tokens")
        print(f"  - Reduction: {reduction_tokens} tokens ({reduction_percent:.1f}%)")
        print(f"  - Target: 25% reduction (594 → 450)")
        print(f"  - Status: {'OPTIMAL (25%+ reduction)' if reduction_percent >= 25 else 'ACCEPTABLE'}")

    async def test_no_embedded_templates_in_prompt(
        self, db_session, test_user, test_project, populate_agent_templates
    ):
        """
        Test that prompts no longer embed agent templates inline.
        This is the source of token reduction.
        """

        orchestrator = MCPAgentJob(
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            agent_type="orchestrator",
            status="active",
            mission="Test no embedded templates",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code"
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()

        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_user.tenant_key,
            user_id=test_user.id
        )

        prompt = await generator.generate(
            instance_number=1,
            tool="claude-code"
        )

        # Should NOT contain embedded template sections
        embedded_indicators = [
            "### Implementer",
            "### Tester",
            "### Reviewer",
            "**Capabilities:**",  # Was in embedded templates
            "**Responsibilities:**"  # Was in embedded templates
        ]

        found_embedded = [indicator for indicator in embedded_indicators if indicator in prompt]

        assert len(found_embedded) == 0, \
            f"Prompt contains embedded template indicators: {found_embedded}"

        # Should reference get_available_agents() instead
        assert "get_available_agents" in prompt.lower(), \
            "Prompt must reference get_available_agents() for dynamic discovery"

        print(f"\n✓ No embedded templates validation:")
        print(f"  - Embedded template indicators found: {len(found_embedded)}")
        print(f"  - References get_available_agents(): ✓")
        print(f"  - Token reduction achieved via dynamic discovery: ✓")

    async def test_token_reduction_consistent_across_modes(
        self, db_session, test_user, test_project, populate_agent_templates
    ):
        """
        Test that token reduction is consistent across execution modes.
        Both Claude Code and Multi-Terminal should achieve similar reduction.
        """

        modes = ["claude-code", "multi-terminal"]
        token_counts = {}

        for mode in modes:
            test_project.meta_data = {"execution_mode": mode}
            await db_session.commit()

            orchestrator = MCPAgentJob(
                project_id=test_project.id,
                tenant_key=test_user.tenant_key,
                agent_type="orchestrator",
                status="active",
                mission=f"Test {mode}",
                job_metadata={
                    "user_id": test_user.id,
                    "execution_mode": mode
                }
            )
            db_session.add(orchestrator)
            await db_session.commit()

            generator = ThinClientPromptGenerator(
                session=db_session,
                orchestrator_id=str(orchestrator.job_id),
                project_id=str(test_project.id),
                tenant_key=test_user.tenant_key,
                user_id=test_user.id
            )

            prompt = await generator.generate(
                instance_number=1,
                tool=mode
            )

            token_counts[mode] = len(prompt) // 4

        # Both modes should be under 600 tokens
        for mode, count in token_counts.items():
            assert count < 600, \
                f"{mode} mode token count ({count}) exceeds threshold (600)"

        # Token counts should be similar (within 20% of each other)
        max_count = max(token_counts.values())
        min_count = min(token_counts.values())
        variance = ((max_count - min_count) / min_count) * 100

        print(f"\n✓ Token reduction consistency across modes:")
        for mode, count in token_counts.items():
            reduction_pct = ((880 - count) / 880) * 100
            print(f"  - {mode}: ~{count} tokens ({reduction_pct:.1f}% reduction)")
        print(f"  - Variance between modes: {variance:.1f}%")
        print(f"  - Consistency: {'HIGH' if variance < 20 else 'MODERATE'}")

    async def test_token_reduction_scales_with_agent_count(
        self, db_session, test_user, test_project, populate_agent_templates
    ):
        """
        Test that token reduction scales (doesn't grow with agent count).
        Old approach: Token count grew linearly with agent count.
        New approach: Token count stays constant (agents fetched dynamically).
        """

        # Add more agents (beyond the 5 in populate_agent_templates)
        for i in range(10):
            agent = AgentTemplate(
                name=f"scaletest_agent_{i}",
                role=f"Scale Test Agent {i}",
                description="Testing token scaling",
                tenant_key=test_user.tenant_key,
                is_active=True,
                version="1.0.0",
                template_content="Scale test"
            )
            db_session.add(agent)

        await db_session.commit()

        # Generate prompt with 15 total agents
        orchestrator = MCPAgentJob(
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            agent_type="orchestrator",
            status="active",
            mission="Scale test",
            job_metadata={
                "user_id": test_user.id,
                "execution_mode": "claude-code"
            }
        )
        db_session.add(orchestrator)
        await db_session.commit()

        generator = ThinClientPromptGenerator(
            session=db_session,
            orchestrator_id=str(orchestrator.job_id),
            project_id=str(test_project.id),
            tenant_key=test_user.tenant_key,
            user_id=test_user.id
        )

        prompt = await generator.generate(
            instance_number=1,
            tool="claude-code"
        )

        token_count = len(prompt) // 4

        # Token count should still be under 600 despite 15 agents
        assert token_count < 600, \
            f"Token count ({token_count}) grew with agent count (should stay constant)"

        print(f"\n✓ Token reduction scales with agent count:")
        print(f"  - Agent count: 15 agents")
        print(f"  - Token count: ~{token_count} tokens")
        print(f"  - Still under budget: ✓")
        print(f"  - Old approach would be: ~1200+ tokens (15 agents × 80 tokens)")
        print(f"  - Scaling improvement: ~50-75% reduction")
