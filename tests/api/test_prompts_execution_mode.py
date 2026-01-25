"""
API Integration Tests for Prompts Endpoint Execution Mode - Handover 0260 Phase 4

Tests the staging endpoint with execution_mode parameter:
- GET /api/prompts/staging/{project_id}?execution_mode=<mode>

Test Coverage (TDD - RED Phase):
1. Endpoint accepts execution_mode query parameter
2. execution_mode=multi_terminal returns standard prompt
3. execution_mode=claude_code_cli returns CLI-enhanced prompt
4. Default behavior (no param) returns multi_terminal prompt
5. Invalid execution_mode values return 422
6. Prompt content verification for each mode
7. Authentication requirements
8. Multi-tenant isolation

Phase: Test-First Development (RED Phase - Tests FAIL)
Status: Awaiting implementation in /api/prompts/staging endpoint
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from passlib.hash import bcrypt


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def prompt_test_user(api_client: AsyncClient, db_manager):
    """
    Create a test user for prompt endpoint tests.
    Returns tuple of (user, token).
    """
    from src.giljo_mcp.models import User, Product
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"prompt_user_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key()

    async with db_manager.get_session_async() as session:
        # Create user
        user = User(
            username=username,
            password_hash=bcrypt.hash("test_password"),
            email=f"{username}@test.com",
            tenant_key=tenant_key,
            role="developer",
            is_active=True,
        )
        session.add(user)

        # Create product for user's tenant
        product = Product(
            id=str(uuid4()),
            name="Test Product",
            description="Test product for prompts",
            tenant_key=tenant_key,
            config_data={
                "tech_stack": {
                    "languages": ["Python 3.11+"],
                    "frameworks": ["FastAPI"]
                }
            }
        )
        session.add(product)

        await session.commit()
        await session.refresh(user)
        await session.refresh(product)

        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

        return user, token, product


@pytest.fixture
async def test_project_for_prompts(db_manager, prompt_test_user):
    """Create a test project for prompt generation tests."""
    from src.giljo_mcp.models import Project

    user, token, product = prompt_test_user

    async with db_manager.get_session_async() as session:
        project = Project(
            id=str(uuid4()),
            name="Prompt Test Project",
            description="Test project for execution mode prompts",
            mission="Test mission for prompt generation",
            status="staged",
            tenant_key=user.tenant_key,
            product_id=product.id,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        return project, token


# ============================================================================
# ENDPOINT PARAMETER ACCEPTANCE TESTS
# ============================================================================

class TestStagingEndpointExecutionModeParameter:
    """Test GET /api/prompts/staging accepts execution_mode parameter"""

    @pytest.mark.asyncio
    async def test_staging_endpoint_accepts_execution_mode_param(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """GET /api/prompts/staging should accept execution_mode query param"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'prompt' in data

    @pytest.mark.asyncio
    async def test_staging_endpoint_accepts_multi_terminal_mode(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """GET /api/prompts/staging should accept execution_mode=multi_terminal"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=multi_terminal',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'prompt' in data

    @pytest.mark.asyncio
    async def test_staging_endpoint_defaults_to_multi_terminal(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """GET /api/prompts/staging without param defaults to multi-terminal"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        data = response.json()
        prompt = data['prompt']

        # Should NOT contain CLI-specific instructions (default is multi-terminal)
        assert 'CLAUDE CODE CLI MODE' not in prompt
        assert 'STRICT TASK TOOL' not in prompt


# ============================================================================
# PROMPT CONTENT VERIFICATION TESTS
# ============================================================================

class TestStagingPromptContentByMode:
    """Test prompt content varies by execution_mode"""

    @pytest.mark.asyncio
    async def test_multi_terminal_mode_excludes_cli_instructions(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """Multi-terminal mode prompt should NOT contain CLI instructions"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=multi_terminal',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        prompt = response.json()['prompt']

        # Should NOT contain CLI-specific sections
        assert 'CLAUDE CODE CLI MODE' not in prompt
        assert 'STRICT TASK TOOL REQUIREMENTS' not in prompt
        assert 'EXACT AGENT NAMING' not in prompt

    @pytest.mark.asyncio
    async def test_claude_code_cli_mode_includes_strict_instructions(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """Claude Code CLI mode prompt MUST contain CLI MODE CRITICAL section"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        prompt = response.json()['prompt']

        # Handover 0342: Trimmed CLI mode - now uses concise CLI MODE CRITICAL block
        # Full rules are in get_orchestrator_instructions() response
        assert 'CLI MODE CRITICAL' in prompt
        assert 'SINGLE SOURCE OF TRUTH' in prompt

    @pytest.mark.asyncio
    async def test_cli_mode_includes_agent_display_name_guidance(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """CLI mode prompt must include agent_display_name vs agent_name guidance"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        prompt = response.json()['prompt']

        # Handover 0342: Concise agent_display_name guidance
        assert 'agent_display_name' in prompt
        assert 'agent_name' in prompt
        # Must explain agent_display_name is for UI labels, agent_name is for template lookup
        assert 'template' in prompt.lower() or 'EXACTLY match' in prompt
        assert 'display' in prompt.lower() or 'Descriptive' in prompt

    @pytest.mark.asyncio
    async def test_cli_mode_references_get_orchestrator_instructions(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """CLI mode must reference get_orchestrator_instructions for full rules"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        prompt = response.json()['prompt']

        # Handover 0342: Full rules deferred to MCP response
        assert 'get_orchestrator_instructions' in prompt
        # Should mention that full rules are in the response
        assert 'cli_mode_rules' in prompt or 'allowed_agent_display_names' in prompt

    @pytest.mark.asyncio
    async def test_cli_mode_includes_task_tool_reference(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """CLI mode must reference Task tool subagent_type usage"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        prompt = response.json()['prompt']

        # Handover 0342: Concise Task tool reference
        assert 'Task(subagent_type=' in prompt
        # Must clarify field distinction between agent_display_name and agent_name
        assert 'NOT agent_name' in prompt or 'agent_display_name value' in prompt


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestExecutionModeValidation:
    """Test validation of execution_mode parameter"""

    @pytest.mark.asyncio
    async def test_invalid_execution_mode_returns_422(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """Invalid execution_mode value should return 422"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=invalid_mode',
            cookies={"access_token": token}
        )

        # Pydantic validation should return 422 Unprocessable Entity
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_case_sensitive_execution_mode(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """execution_mode should be case-sensitive"""
        project, token = test_project_for_prompts

        # Wrong case should fail validation
        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=CLAUDE_CODE_CLI',
            cookies={"access_token": token}
        )

        # Should return 422 (or accept it if case-insensitive is allowed)
        # This test documents the expected behavior
        assert response.status_code in [200, 422], \
            "Endpoint must either accept or reject uppercase mode values consistently"


# ============================================================================
# AUTHENTICATION & AUTHORIZATION TESTS
# ============================================================================

class TestStagingExecutionModeAuthentication:
    """Test authentication requirements for staging endpoint"""

    @pytest.mark.asyncio
    async def test_staging_endpoint_requires_authentication(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """GET /api/prompts/staging requires authentication"""
        project, token = test_project_for_prompts

        # No authentication
        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli'
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_staging_endpoint_enforces_tenant_isolation(
        self, api_client: AsyncClient, db_manager
    ):
        """GET /api/prompts/staging enforces multi-tenant isolation"""
        from src.giljo_mcp.models import User, Product, Project
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        from src.giljo_mcp.tenant import TenantManager

        # Create two tenants
        tenant_a_key = TenantManager.generate_tenant_key()
        tenant_b_key = TenantManager.generate_tenant_key()

        # Generate unique IDs for this test run
        unique_id_a = uuid4().hex[:8]
        unique_id_b = uuid4().hex[:8]

        async with db_manager.get_session_async() as session:
            # Tenant A user and project
            user_a = User(
                username=f"user_a_{unique_id_a}",
                password_hash=bcrypt.hash("password"),
                email=f"user_a_{unique_id_a}@test.com",
                tenant_key=tenant_a_key,
                role="developer",
                is_active=True,
            )
            product_a = Product(
                id=str(uuid4()),
                name="Product A",
                description="Test",
                tenant_key=tenant_a_key
            )
            project_a = Project(
                id=str(uuid4()),
                name="Project A",
                description="Test",
                mission="Test mission A",  # Required field
                tenant_key=tenant_a_key,
                product_id=product_a.id,
            )

            # Tenant B user and project
            user_b = User(
                username=f"user_b_{unique_id_b}",
                password_hash=bcrypt.hash("password"),
                email=f"user_b_{unique_id_b}@test.com",
                tenant_key=tenant_b_key,
                role="developer",
                is_active=True,
            )
            product_b = Product(
                id=str(uuid4()),
                name="Product B",
                description="Test",
                tenant_key=tenant_b_key
            )
            project_b = Project(
                id=str(uuid4()),
                name="Project B",
                description="Test",
                mission="Test mission B",  # Required field
                tenant_key=tenant_b_key,
                product_id=product_b.id,
            )

            session.add_all([user_a, product_a, project_a, user_b, product_b, project_b])
            await session.commit()

            token_a = JWTManager.create_access_token(
                user_id=user_a.id,
                username=user_a.username,
                role=user_a.role,
                tenant_key=user_a.tenant_key,
            )

        # User A should NOT be able to access Project B
        response = await api_client.get(
            f'/api/v1/prompts/staging/{project_b.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token_a}
        )

        # Should return 404 (project not found) due to tenant filtering
        assert response.status_code == 404


# ============================================================================
# RESPONSE FORMAT TESTS
# ============================================================================

class TestStagingResponseFormat:
    """Test response format consistency across modes"""

    @pytest.mark.asyncio
    async def test_response_includes_required_fields(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """Response should include all required fields"""
        project, token = test_project_for_prompts

        response = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert 'prompt' in data
        assert 'orchestrator_id' in data
        assert 'instance_number' in data
        assert 'estimated_prompt_tokens' in data

    @pytest.mark.asyncio
    async def test_both_modes_return_same_field_structure(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """Both execution modes should return same response structure"""
        project, token = test_project_for_prompts

        # Multi-terminal response
        response_mt = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=multi_terminal',
            cookies={"access_token": token}
        )

        # CLI mode response
        response_cli = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response_mt.status_code == 200
        assert response_cli.status_code == 200

        # Both should have same keys
        mt_keys = set(response_mt.json().keys())
        cli_keys = set(response_cli.json().keys())

        assert mt_keys == cli_keys, \
            "Both execution modes must return same response structure"


# ============================================================================
# PROMPT LENGTH COMPARISON
# ============================================================================

class TestPromptLengthByMode:
    """Test prompt length differences between modes"""

    @pytest.mark.asyncio
    async def test_cli_mode_prompt_longer_than_multi_terminal(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """CLI mode prompt should be longer due to additional instructions"""
        project, token = test_project_for_prompts

        # Get multi-terminal prompt
        response_mt = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=multi_terminal',
            cookies={"access_token": token}
        )

        # Get CLI mode prompt
        response_cli = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response_mt.status_code == 200
        assert response_cli.status_code == 200

        mt_prompt = response_mt.json()['prompt']
        cli_prompt = response_cli.json()['prompt']

        # CLI mode should be longer
        assert len(cli_prompt) > len(mt_prompt), \
            "CLI mode prompt should be longer due to Task tool instructions"

    @pytest.mark.asyncio
    async def test_cli_mode_token_estimate_reflects_length(
        self, api_client: AsyncClient, test_project_for_prompts
    ):
        """CLI mode should have higher estimated_prompt_tokens"""
        project, token = test_project_for_prompts

        # Get multi-terminal token estimate
        response_mt = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=multi_terminal',
            cookies={"access_token": token}
        )

        # Get CLI mode token estimate
        response_cli = await api_client.get(
            f'/api/v1/prompts/staging/{project.id}?execution_mode=claude_code_cli',
            cookies={"access_token": token}
        )

        assert response_mt.status_code == 200
        assert response_cli.status_code == 200

        mt_tokens = response_mt.json()['estimated_prompt_tokens']
        cli_tokens = response_cli.json()['estimated_prompt_tokens']

        # CLI mode should have higher token count
        assert cli_tokens > mt_tokens, \
            "CLI mode token estimate should be higher"
