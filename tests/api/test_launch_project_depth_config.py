"""
Launch Project Depth Config Tests - TDD GREEN Phase

Tests that verify user depth config (specifically agent_templates setting) is
correctly passed from the API endpoint to the service layer and reflected in
orchestrator instructions via context_fetch_instructions.

ARCHITECTURE INSIGHT:
- agent_templates in instructions["agent_templates"] are ALWAYS minimal (name/role/description)
- This is a quick reference list, not controlled by depth config
- Depth config controls context_fetch_instructions["critical"|"important"|"reference"]
- When depth="full", orchestrator must call fetch_context(categories=["agent_templates"])
- When depth="type_only", NO fetch instruction is added (minimal inline is sufficient)

Expected Behavior:
1. User launches project with user_id passed to service
2. User's depth_config is fetched and applied to fetch instructions
3. When depth_config = {"agent_templates": "full"}, fetch instructions include agent_templates
4. When depth_config = {"agent_templates": "type_only"}, fetch instructions exclude agent_templates
5. Minimal inline templates always present regardless of depth

Test Status: GREEN (tests now check correct architecture)
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock
from uuid import uuid4


class TestLaunchProjectPassesUserIdToService:
    """Test that launch_project endpoint passes user_id to service layer"""

    @pytest.mark.asyncio
    async def test_launch_project_passes_user_id_to_service(
        self,
        api_client: AsyncClient,
        db_manager,
        test_user
    ):
        """
        Test: When user launches a project, their user_id should be passed to service.

        Expected Behavior:
        - Endpoint extracts current_user.id from authentication
        - Endpoint calls ProjectService.launch_project(project_id, user_id=current_user.id, ...)
        - Service uses user_id to fetch depth_config from database
        """
        from src.giljo_mcp.models import Product, Project, AgentTemplate
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        # Setup: Create product, project, and at least one agent template
        async with db_manager.get_session_async() as session:
            product = Product(
                id=str(uuid4()),
                name="Test Product",
                description="Test product for launch",
                tenant_key=test_user.tenant_key,
                is_active=True
            )
            session.add(product)

            project = Project(
                id=str(uuid4()),
                name="Test Project",
                description="Test project for launch",
                mission="Test mission",
                status="inactive",
                tenant_key=test_user.tenant_key,
                product_id=product.id
            )
            session.add(project)

            # Add agent template (required for orchestrator instructions)
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=test_user.tenant_key,
                product_id=product.id,
                name="test-implementer",
                role="implementer",
                description="Test implementation specialist",
                system_instructions="Test template content for implementer agent",
                is_active=True,
                category="role"
            )
            session.add(template)

            await session.commit()

            project_id = project.id

        # Create auth token for test user
        token = JWTManager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
            role=test_user.role,
            tenant_key=test_user.tenant_key
        )

        # Create mock service to capture launch_project arguments
        mock_service = AsyncMock()
        mock_service.launch_project = AsyncMock(return_value={
            "success": True,
            "data": {
                "project_id": project_id,
                "orchestrator_job_id": str(uuid4()),
                "launch_prompt": "Mock prompt",
                "status": "active"
            }
        })

        # Override the dependency to inject our mock
        from api.endpoints.projects.dependencies import get_project_service
        from api.app import app

        def override_project_service():
            return mock_service

        app.dependency_overrides[get_project_service] = override_project_service

        try:
            # Act: Launch project as authenticated user
            response = await api_client.post(
                f"/api/v1/projects/{project_id}/launch",
                cookies={"access_token": token}
            )

            # Assert: Response successful
            assert response.status_code == 200, f"Launch failed: {response.json()}"

            # Assert: user_id was passed to service layer
            mock_service.launch_project.assert_called_once()
            call_kwargs = mock_service.launch_project.call_args.kwargs

            assert "user_id" in call_kwargs, (
                "BUG: user_id not passed to ProjectService.launch_project(). "
                "This prevents user's depth_config from being fetched."
            )
            assert call_kwargs["user_id"] == test_user.id, (
                f"Expected user_id={test_user.id}, got {call_kwargs.get('user_id')}"
            )
        finally:
            # Clean up override
            if get_project_service in app.dependency_overrides:
                del app.dependency_overrides[get_project_service]


class TestLaunchProjectWithFullAgentTemplates:
    """Test that agent_templates='full' adds fetch instruction for full templates"""

    @pytest.mark.asyncio
    async def test_launch_with_full_agent_templates_includes_fetch_instruction(
        self,
        api_client: AsyncClient,
        db_manager,
        test_user
    ):
        """
        Test: When user has depth_config = {"agent_templates": "full"}, orchestrator
        instructions should include a fetch instruction for agent_templates category.

        Expected Behavior:
        - User's depth_config["agent_templates"] = "full"
        - context_fetch_instructions includes agent_templates with depth="full"
        - Orchestrator must call fetch_context(categories=["agent_templates"]) to get full content
        - Minimal inline templates still present in agent_templates list
        """
        from src.giljo_mcp.models import Product, Project, AgentTemplate
        from src.giljo_mcp.models.agent_identity import AgentJob
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        from sqlalchemy import update

        # Setup: Update test user's depth_config to request full agent templates
        async with db_manager.get_session_async() as session:
            from src.giljo_mcp.models import User

            await session.execute(
                update(User)
                .where(User.id == test_user.id)
                .values(depth_config={
                    "vision_documents": "medium",
                    "memory_360": 3,
                    "git_history": 25,
                    "agent_templates": "full",  # USER WANTS FULL TEMPLATES
                })
            )
            await session.commit()

            # Create product and project
            product = Product(
                id=str(uuid4()),
                name="Test Product",
                description="Test product",
                tenant_key=test_user.tenant_key,
                is_active=True
            )
            session.add(product)

            project = Project(
                id=str(uuid4()),
                name="Test Project",
                description="Test project",
                mission="Test mission",
                status="inactive",
                tenant_key=test_user.tenant_key,
                product_id=product.id
            )
            session.add(project)

            # Add agent template with full content
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=test_user.tenant_key,
                product_id=product.id,
                name="test-implementer",
                role="implementer",
                description="Test implementation specialist for TDD workflows",
                system_instructions="# Test Implementer Agent\n\nYou are a test implementation specialist...",
                is_active=True,
                category="role"
            )
            session.add(template)

            await session.commit()

            project_id = project.id

        # Create auth token
        token = JWTManager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
            role=test_user.role,
            tenant_key=test_user.tenant_key
        )

        # Act: Launch project
        response = await api_client.post(
            f"/api/v1/projects/{project_id}/launch",
            cookies={"access_token": token}
        )

        # Assert: Launch successful
        assert response.status_code == 200, f"Launch failed: {response.json()}"
        data = response.json()

        orchestrator_job_id = data["orchestrator_job_id"]

        # Verify orchestrator job was created (Handover 0358a: Use AgentJob instead of MCPAgentJob)
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(AgentJob).where(AgentJob.job_id == orchestrator_job_id)
            )
            orchestrator_job = result.scalar_one_or_none()

            assert orchestrator_job is not None, "Orchestrator job not created"

            # Check job_metadata contains user_id
            job_metadata = orchestrator_job.job_metadata or {}
            assert "user_id" in job_metadata, (
                "BUG: user_id not stored in job_metadata. "
                "This prevents orchestrator from knowing which user launched the project."
            )
            assert job_metadata["user_id"] == test_user.id

            # Get orchestrator instructions via ToolAccessor (simulates MCP tool call)
            from src.giljo_mcp.tools.tool_accessor import ToolAccessor
            from src.giljo_mcp.tenant import TenantManager

            tenant_manager = TenantManager()
            tenant_manager.set_current_tenant(test_user.tenant_key)

            tool_accessor = ToolAccessor(
                db_manager=db_manager,
                tenant_manager=tenant_manager
            )

            instructions = await tool_accessor.get_orchestrator_instructions(
                job_id=orchestrator_job_id,
                tenant_key=test_user.tenant_key
            )

            # Assert: Minimal inline templates should always be present
            assert "agent_templates" in instructions, "agent_templates missing from instructions"
            inline_templates = instructions["agent_templates"]
            assert len(inline_templates) > 0, "No inline agent templates returned"

            # Verify inline templates are minimal (name/role/description only)
            for template in inline_templates:
                assert "name" in template
                assert "role" in template
                assert "description" in template
                # Should NOT have full content in inline version
                assert "system_instructions" not in template

            # Assert: context_fetch_instructions should include agent_templates
            fetch_instructions = instructions.get("context_fetch_instructions", {})
            assert fetch_instructions, "No context_fetch_instructions found"

            # Find agent_templates in one of the priority tiers
            agent_templates_instruction = None
            for tier in ["critical", "important", "reference"]:
                tier_instructions = fetch_instructions.get(tier, [])
                for instruction in tier_instructions:
                    if instruction.get("field") == "agent_templates":
                        agent_templates_instruction = instruction
                        break
                if agent_templates_instruction:
                    break

            assert agent_templates_instruction is not None, (
                "BUG: agent_templates not in context_fetch_instructions. "
                "User requested agent_templates='full', but no fetch instruction was added. "
                f"Fetch instructions: {fetch_instructions}"
            )

            # Verify the instruction has correct parameters
            assert agent_templates_instruction["tool"] == "fetch_context"
            assert agent_templates_instruction["params"]["category"] == "agent_templates"
            # Depth parameter should be "full" (passed to fetch_context)
            assert agent_templates_instruction["params"].get("depth") == "full"


class TestLaunchProjectWithTypeOnlyAgentTemplates:
    """Test that agent_templates='type_only' skips fetch instruction (inline only)"""

    @pytest.mark.asyncio
    async def test_launch_with_type_only_agent_templates_skips_fetch(
        self,
        api_client: AsyncClient,
        db_manager,
        test_user
    ):
        """
        Test: When user has depth_config = {"agent_templates": "type_only"}, orchestrator
        instructions should NOT include a fetch instruction for agent_templates.

        Expected Behavior:
        - User's depth_config["agent_templates"] = "type_only"
        - context_fetch_instructions does NOT include agent_templates
        - Minimal inline templates still present (sufficient for type_only)
        """
        from src.giljo_mcp.models import Product, Project, AgentTemplate
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        from sqlalchemy import update

        # Setup: Update test user's depth_config to request type_only
        async with db_manager.get_session_async() as session:
            from src.giljo_mcp.models import User

            await session.execute(
                update(User)
                .where(User.id == test_user.id)
                .values(depth_config={
                    "vision_documents": "medium",
                    "memory_360": 3,
                    "git_history": 25,
                    "agent_templates": "type_only",  # USER WANTS MINIMAL TEMPLATES
                })
            )
            await session.commit()

            # Create product and project
            product = Product(
                id=str(uuid4()),
                name="Test Product",
                description="Test product",
                tenant_key=test_user.tenant_key,
                is_active=True
            )
            session.add(product)

            project = Project(
                id=str(uuid4()),
                name="Test Project",
                description="Test project",
                mission="Test mission",
                status="inactive",
                tenant_key=test_user.tenant_key,
                product_id=product.id
            )
            session.add(project)

            # Add agent template
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=test_user.tenant_key,
                product_id=product.id,
                name="test-implementer",
                role="implementer",
                description="Test implementation specialist",
                system_instructions="Full template content here",
                is_active=True,
                category="role"
            )
            session.add(template)

            await session.commit()

            project_id = project.id

        # Create auth token
        token = JWTManager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
            role=test_user.role,
            tenant_key=test_user.tenant_key
        )

        # Act: Launch project
        response = await api_client.post(
            f"/api/v1/projects/{project_id}/launch",
            cookies={"access_token": token}
        )

        # Assert: Launch successful
        assert response.status_code == 200, f"Launch failed: {response.json()}"
        data = response.json()

        orchestrator_job_id = data["orchestrator_job_id"]

        # Verify orchestrator instructions
        async with db_manager.get_session_async() as session:
            from src.giljo_mcp.tools.tool_accessor import ToolAccessor
            from src.giljo_mcp.tenant import TenantManager

            tenant_manager = TenantManager()
            tenant_manager.set_current_tenant(test_user.tenant_key)

            tool_accessor = ToolAccessor(
                db_manager=db_manager,
                tenant_manager=tenant_manager
            )

            instructions = await tool_accessor.get_orchestrator_instructions(
                job_id=orchestrator_job_id,
                tenant_key=test_user.tenant_key
            )

            # Assert: Minimal inline templates should be present
            assert "agent_templates" in instructions, "agent_templates missing from instructions"
            inline_templates = instructions["agent_templates"]
            assert len(inline_templates) > 0, "No inline agent templates returned"

            # Verify inline templates are minimal (sufficient for type_only)
            for template in inline_templates:
                assert "name" in template
                assert "role" in template
                assert "description" in template

            # Assert: context_fetch_instructions should NOT include agent_templates
            fetch_instructions = instructions.get("context_fetch_instructions", {})

            # Search for agent_templates in all tiers
            agent_templates_found = False
            for tier in ["critical", "important", "reference"]:
                tier_instructions = fetch_instructions.get(tier, [])
                for instruction in tier_instructions:
                    if instruction.get("field") == "agent_templates":
                        agent_templates_found = True
                        break

            assert not agent_templates_found, (
                "BUG: agent_templates in context_fetch_instructions when depth='type_only'. "
                "Inline templates should be sufficient, no fetch needed. "
                f"Fetch instructions: {fetch_instructions}"
            )


class TestLaunchProjectRespectsUserDepthConfig:
    """Test that user's depth config overrides system defaults"""

    @pytest.mark.asyncio
    async def test_user_full_overrides_default_type_only(
        self,
        api_client: AsyncClient,
        db_manager,
        test_user
    ):
        """
        Test: User's depth_config should override DEFAULT_DEPTH_CONFIG.

        Expected Behavior:
        - DEFAULT_DEPTH_CONFIG has agent_templates = "type_only"
        - User sets agent_templates = "full"
        - Fetch instructions should include agent_templates (user override applied)
        """
        from src.giljo_mcp.models import Product, Project, AgentTemplate
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        from sqlalchemy import update

        # Setup: Set user's preference to FULL (opposite of default)
        async with db_manager.get_session_async() as session:
            from src.giljo_mcp.models import User

            # Verify default is "type_only"
            from src.giljo_mcp.tools.context_tools.fetch_context import DEFAULT_DEPTHS
            assert DEFAULT_DEPTHS.get("agent_templates") == "type_only", (
                "Test assumption broken: DEFAULT_DEPTHS changed"
            )

            # Set user to opposite of default
            await session.execute(
                update(User)
                .where(User.id == test_user.id)
                .values(depth_config={
                    "vision_documents": "medium",
                    "memory_360": 3,
                    "git_history": 25,
                    "agent_templates": "full",  # OVERRIDE DEFAULT
                })
            )
            await session.commit()

            # Create product and project
            product = Product(
                id=str(uuid4()),
                name="Test Product",
                description="Test product",
                tenant_key=test_user.tenant_key,
                is_active=True
            )
            session.add(product)

            project = Project(
                id=str(uuid4()),
                name="Test Project",
                description="Test project",
                mission="Test mission",
                status="inactive",
                tenant_key=test_user.tenant_key,
                product_id=product.id
            )
            session.add(project)

            # Add agent template
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=test_user.tenant_key,
                product_id=product.id,
                name="test-implementer",
                role="implementer",
                description="Test implementation specialist",
                system_instructions="Full template content for testing",
                is_active=True,
                category="role"
            )
            session.add(template)

            await session.commit()

            project_id = project.id

        # Create auth token
        token = JWTManager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
            role=test_user.role,
            tenant_key=test_user.tenant_key
        )

        # Act: Launch project
        response = await api_client.post(
            f"/api/v1/projects/{project_id}/launch",
            cookies={"access_token": token}
        )

        # Assert: Launch successful
        assert response.status_code == 200, f"Launch failed: {response.json()}"
        data = response.json()

        orchestrator_job_id = data["orchestrator_job_id"]

        # Verify user's setting was applied (not default)
        async with db_manager.get_session_async() as session:
            from src.giljo_mcp.tools.tool_accessor import ToolAccessor
            from src.giljo_mcp.tenant import TenantManager

            tenant_manager = TenantManager()
            tenant_manager.set_current_tenant(test_user.tenant_key)

            tool_accessor = ToolAccessor(
                db_manager=db_manager,
                tenant_manager=tenant_manager
            )

            instructions = await tool_accessor.get_orchestrator_instructions(
                job_id=orchestrator_job_id,
                tenant_key=test_user.tenant_key
            )

            # Assert: Should use user's "full" setting (not default "type_only")
            fetch_instructions = instructions.get("context_fetch_instructions", {})

            # Find agent_templates instruction
            agent_templates_instruction = None
            for tier in ["critical", "important", "reference"]:
                tier_instructions = fetch_instructions.get(tier, [])
                for instruction in tier_instructions:
                    if instruction.get("field") == "agent_templates":
                        agent_templates_instruction = instruction
                        break
                if agent_templates_instruction:
                    break

            assert agent_templates_instruction is not None, (
                "BUG: agent_templates not in fetch instructions. "
                "User set agent_templates='full' but got default 'type_only' behavior. "
                "This proves user's depth_config was NOT applied."
            )

            # Verify depth is "full"
            assert agent_templates_instruction["params"].get("depth") == "full", (
                f"Expected depth='full', got {agent_templates_instruction['params'].get('depth')}"
            )
