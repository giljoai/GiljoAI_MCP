"""
Comprehensive test suite for ThinClientPromptGenerator (Handover 0088 - Phase 2)

Tests the NEW thin client prompt generator that generates ~10 line prompts
with MCP tool references instead of embedding 3000-line fat prompts.

Target: 85%+ code coverage
Priority: CRITICAL - Enables context prioritization and orchestration feature
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator, ThinPromptResponse


@pytest.mark.asyncio
class TestThinClientGeneratorBasic:
    """Basic functionality tests for thin client prompt generator."""

    async def test_generate_thin_prompt_success(self, db_session):
        """
        Test successful generation of thin prompt.

        Expected Flow:
        1. Create project and product
        2. Generate thin prompt
        3. Verify prompt is ~10 lines
        4. Verify orchestrator job created
        5. Verify mission stored
        """
        # Setup tenant and test data
        tenant_key = str(uuid4())
        user_id = str(uuid4())

        # Create user
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username="testuser",
            email="test@giljoai.com",
            field_priority_config={"product_vision": 10, "architecture": 7, "codebase_summary": 4},
        )
        db_session.add(user)

        # Create product
        product = Product(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Test product for thin prompt testing",
            vision_document="This is a test product vision document with sufficient content to test context prioritization.",
        )
        db_session.add(product)

        # Create project
        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test project for thin prompt",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Generate thin prompt
        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), user_id=user_id, tool="claude-code")

        # Verify response structure
        assert isinstance(result, ThinPromptResponse)
        assert result.orchestrator_id is not None
        assert result.project_id == str(project.id)
        assert result.project_name == "Test Project"
        assert result.mcp_tool_name == "get_orchestrator_instructions"
        assert result.instructions_stored is True

        # Verify prompt is thin
        prompt_lines = result.prompt.split("\n")
        assert len(prompt_lines) <= 30, f"Prompt should be ~10-30 lines, got {len(prompt_lines)}"
        assert result.estimated_prompt_tokens < 150, (
            f"Prompt should be <150 tokens, got {result.estimated_prompt_tokens}"
        )

        # Verify orchestrator job created in database
        orchestrator = await db_session.get(AgentExecution, result.orchestrator_id)
        assert orchestrator is not None
        assert orchestrator.agent_display_name == "orchestrator"
        assert orchestrator.status == "pending"
        assert orchestrator.tenant_key == tenant_key
        assert orchestrator.project_id == str(project.id)

        # Verify mission stored
        assert orchestrator.mission is not None
        assert len(orchestrator.mission) > 0

    async def test_thin_prompt_is_actually_thin(self, db_session):
        """
        Validate that prompt is genuinely thin (~10 lines, <100 tokens).

        This is THE critical test - prompts must be copy-pasteable.
        """
        tenant_key = str(uuid4())

        # Create minimal test data
        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            description="Description",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        # Generate thin prompt
        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), tool="claude-code")

        # CRITICAL VALIDATIONS
        prompt_lines = result.prompt.split("\n")
        non_empty_lines = [line for line in prompt_lines if line.strip()]

        # Prompt should be concise
        assert len(non_empty_lines) <= 30, f"Too many lines: {len(non_empty_lines)}"
        assert result.estimated_prompt_tokens < 150, f"Too many tokens: {result.estimated_prompt_tokens}"

        # Prompt should NOT contain mission content
        assert "product_vision" not in result.prompt.lower()
        assert "architecture" not in result.prompt.lower()
        assert len(result.prompt) < 2000, "Prompt is too long - contains embedded content"

        # Prompt MUST contain MCP tool reference
        assert "get_orchestrator_instructions" in result.prompt
        assert result.orchestrator_id in result.prompt

    async def test_orchestrator_job_created_in_database(self, db_session):
        """
        Verify orchestrator job is created and persisted correctly.
        """
        tenant_key = str(uuid4())

        # Create test data
        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision content")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        # Generate thin prompt
        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), tool="codex")

        # Verify database persistence
        orchestrator = await db_session.get(AgentExecution, result.orchestrator_id)
        assert orchestrator is not None
        assert orchestrator.agent_display_name == "orchestrator"
        assert orchestrator.agent_name == "Orchestrator #2"
        assert orchestrator.status == "pending"
        assert orchestrator.tool_type == "codex"
        assert orchestrator.context_budget == 150000
        assert orchestrator.context_used == 0

    async def test_mission_stored_with_field_priorities(self, db_session):
        """
        Verify condensed mission is stored with field priorities applied.
        """
        tenant_key = str(uuid4())
        user_id = str(uuid4())

        # Create user with field priorities
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username="testuser",
            field_priority_config={
                "product_vision": 10,  # Full detail
                "architecture": 4,  # Abbreviated
                "dependencies": 2,  # Minimal
            },
        )
        db_session.add(user)

        # Create product with large vision
        large_vision = "PRODUCT VISION:\n" + ("Detail " * 1000)  # Large content
        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document=large_vision)
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        # Generate with user's field priorities
        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), user_id=user_id, tool="claude-code")

        # Verify mission is condensed (not full vision)
        orchestrator = await db_session.get(AgentExecution, result.orchestrator_id)
        mission_length = len(orchestrator.mission)
        vision_length = len(large_vision)

        assert mission_length < vision_length, "Mission should be condensed"
        # Mission should be significantly smaller due to field priorities
        assert mission_length < vision_length * 0.5, "Field priorities should reduce content by at least 50%"

    async def test_user_field_priorities_applied(self, db_session):
        """
        Verify user's field priority configuration is fetched and applied.
        """
        tenant_key = str(uuid4())
        user_id = str(uuid4())

        # Create user with specific priorities
        user = User(
            id=user_id,
            tenant_key=tenant_key,
            username="priorityuser",
            field_priority_config={"product_vision": 10, "architecture": 8, "codebase_summary": 3, "dependencies": 1},
        )
        db_session.add(user)

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        # Generate with user field priorities
        generator = ThinClientPromptGenerator(db_session, tenant_key)

        # Test private method to get field priorities
        field_priorities = await generator._get_user_field_priorities(user_id)

        assert field_priorities is not None
        assert field_priorities["product_vision"] == 10
        assert field_priorities["architecture"] == 8
        assert field_priorities["codebase_summary"] == 3
        assert field_priorities["dependencies"] == 1

    async def test_token_estimate_accurate(self, db_session):
        """
        Verify token estimation is accurate for thin prompts.
        """
        tenant_key = str(uuid4())

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), tool="claude-code")

        # Token estimate should be reasonable
        # 1 token ≈ 4 characters (rough estimate)
        char_count = len(result.prompt)
        estimated_tokens = char_count // 4

        # Result token estimate should be within 20% of actual calculation
        assert abs(result.estimated_prompt_tokens - estimated_tokens) < estimated_tokens * 0.2


@pytest.mark.asyncio
class TestThinClientGeneratorSecurity:
    """Security and multi-tenant isolation tests."""

    async def test_multi_tenant_isolation(self, db_session):
        """
        Verify thin client generator enforces multi-tenant isolation.
        """
        tenant1_key = str(uuid4())
        tenant2_key = str(uuid4())

        # Create project for tenant 1
        product1 = Product(
            id=str(uuid4()), tenant_key=tenant1_key, name="Tenant1 Product", vision_document="Tenant 1 vision"
        )
        db_session.add(product1)

        project1 = Project(
            id=str(uuid4()),
            tenant_key=tenant1_key,
            product_id=product1.id,
            name="Tenant1 Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project1)

        # Create project for tenant 2
        product2 = Product(
            id=str(uuid4()), tenant_key=tenant2_key, name="Tenant2 Product", vision_document="Tenant 2 vision"
        )
        db_session.add(product2)

        project2 = Project(
            id=str(uuid4()),
            tenant_key=tenant2_key,
            product_id=product2.id,
            name="Tenant2 Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project2)
        await db_session.commit()

        # Tenant 1 generator tries to access Tenant 2 project
        generator_tenant1 = ThinClientPromptGenerator(db_session, tenant1_key)

        with pytest.raises(ValueError, match="Project .* not found"):
            await generator_tenant1.generate(
                project_id=str(project2.id),  # Tenant 2 project
                tool="claude-code",
            )


@pytest.mark.asyncio
class TestThinClientGeneratorErrors:
    """Error handling and validation tests."""

    async def test_invalid_tool_error(self, db_session):
        """
        Test error handling for invalid tool parameter.
        """
        tenant_key = str(uuid4())

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)

        with pytest.raises(ValueError, match="Invalid tool"):
            await generator.generate(
                project_id=str(project.id),
                tool="invalid-tool",  # Invalid
            )

    async def test_project_not_found_error(self, db_session):
        """
        Test error handling when project doesn't exist.
        """
        tenant_key = str(uuid4())
        fake_project_id = str(uuid4())

        generator = ThinClientPromptGenerator(db_session, tenant_key)

        with pytest.raises(ValueError, match="Project .* not found"):
            await generator.generate(project_id=fake_project_id, tool="claude-code")

    async def test_user_not_found_graceful(self, db_session):
        """
        Test graceful handling when user doesn't exist (should use empty priorities).
        """
        tenant_key = str(uuid4())
        fake_user_id = str(uuid4())

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)

        # Should not raise error, just use empty field priorities
        result = await generator.generate(
            project_id=str(project.id),
            user_id=fake_user_id,  # Non-existent user
            tool="claude-code",
        )

        assert result is not None
        assert result.orchestrator_id is not None


@pytest.mark.asyncio
class TestThinClientGeneratorPromptContent:
    """Tests for prompt content and format."""

    async def test_staging_prompt_includes_execution_plan_step(self, db_session):
        """
        Verify staging prompt includes step to write execution plan.

        This test ensures orchestrators are instructed to persist their
        execution strategy via update_agent_mission() for fresh-session retrieval.
        """
        tenant_key = str(uuid4())

        # Product model no longer has vision_document field (Handover 0128e)
        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", description="Test product")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            description="Test project",
            mission="Test mission for staging prompt",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)

        # Generate staging prompt (claude_code_mode=True to use staging prompt)
        staging_prompt = await generator.generate_staging_prompt(
            orchestrator_id=str(uuid4()), project_id=str(project.id), claude_code_mode=True
        )

        # Verify execution plan instruction is present
        assert "WRITE YOUR EXECUTION PLAN" in staging_prompt
        assert "update_agent_mission" in staging_prompt

        # Verify key components of the execution plan instruction
        assert "Agent execution order" in staging_prompt
        assert "Dependency graph" in staging_prompt
        assert "Coordination checkpoints" in staging_prompt
        assert "Success criteria" in staging_prompt

    async def test_mcp_connection_config_included(self, db_session):
        """
        Verify MCP connection configuration is included in prompt (Amendment C).
        """
        tenant_key = str(uuid4())

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), tool="claude-code")

        # Verify MCP connection details in prompt
        assert "MCP CONNECTION" in result.prompt or "mcp__giljo-mcp__" in result.prompt
        assert "get_orchestrator_instructions" in result.prompt
        assert result.orchestrator_id in result.prompt
        assert tenant_key in result.prompt

    async def test_prompt_includes_identity_info(self, db_session):
        """
        Verify prompt includes all necessary identity information.
        """
        tenant_key = str(uuid4())

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="My Test Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="My Test Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)
        result = await generator.generate(project_id=str(project.id), tool="claude-code")

        # Verify identity elements in prompt
        assert "Orchestrator #3" in result.prompt
        assert "My Test Project" in result.prompt
        assert result.orchestrator_id in result.prompt
        assert str(project.id) in result.prompt

    async def test_prompt_different_tools(self, db_session):
        """
        Test prompt generation for different AI coding tools.
        """
        tenant_key = str(uuid4())

        product = Product(id=str(uuid4()), tenant_key=tenant_key, name="Product", vision_document="Vision")
        db_session.add(product)

        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=product.id,
            name="Project",
            status="active",
            context_budget=150000,
        )
        db_session.add(project)
        await db_session.commit()

        generator = ThinClientPromptGenerator(db_session, tenant_key)

        # Test each supported tool
        for tool in ["claude-code", "codex", "gemini"]:
            result = await generator.generate(project_id=str(project.id), tool=tool)

            assert result.prompt is not None
            assert len(result.prompt) > 0
            # Verify orchestrator created with correct tool
            orchestrator = await db_session.get(AgentExecution, result.orchestrator_id)
            assert orchestrator.tool_type == tool
