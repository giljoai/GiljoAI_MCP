"""
Unit tests for Git + 360 Memory prompt injection logic.

Handover: Git Integration + 360 Memory Prompt Injection
Author: Backend Integration Tester Agent
Date: 2025-11-16

PURPOSE: Test-Driven Development (TDD) for prompt injection functionality.
These tests define expected behavior BEFORE implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def product_with_git_enabled():
    """Product with git integration enabled."""
    product = Product(
        id="prod-123",
        tenant_key="test-tenant",
        name="Test Product",
        description="Product with git enabled",
        product_memory={
            "git_integration": {
                "enabled": True,
                "commit_limit": 20,
                "default_branch": "main"
            },
            "learnings": [
                {
                    "sequence": 1,
                    "summary": "Initial setup completed",
                    "timestamp": "2025-11-01T10:00:00Z"
                },
                {
                    "sequence": 2,
                    "summary": "Database migration successful",
                    "timestamp": "2025-11-05T14:30:00Z"
                }
            ],
            "context": {
                "objectives": ["Build scalable system", "Maintain high test coverage"]
            }
        }
    )
    return product


@pytest.fixture
def product_with_git_disabled():
    """Product with git integration disabled."""
    product = Product(
        id="prod-456",
        tenant_key="test-tenant",
        name="Test Product No Git",
        description="Product without git",
        product_memory={
            "git_integration": {
                "enabled": False
            },
            "learnings": [
                {
                    "sequence": 1,
                    "summary": "Manual summary without git",
                    "timestamp": "2025-11-10T12:00:00Z"
                }
            ],
            "context": {
                "objectives": ["Quick prototyping"]
            }
        }
    )
    return product


@pytest.fixture
def product_with_custom_commit_limit():
    """Product with custom git commit limit."""
    product = Product(
        id="prod-789",
        tenant_key="test-tenant",
        name="Test Product Custom Limit",
        description="Product with custom commit limit",
        product_memory={
            "git_integration": {
                "enabled": True,
                "commit_limit": 50,
                "default_branch": "develop"
            },
            "learnings": []
        }
    )
    return product


@pytest.fixture
def product_no_memory():
    """Product with no product_memory configured."""
    product = Product(
        id="prod-000",
        tenant_key="test-tenant",
        name="Test Product No Memory",
        description="Product with empty memory",
        product_memory={"github": {}, "learnings": [], "context": {}}
    )
    return product


@pytest.fixture
def mock_project():
    """Mock project for testing."""
    project = Project(
        id="proj-123",
        tenant_key="test-tenant",
        name="Test Project",
        description="Test project description",
        mission="Test mission",
        context_budget=180000
    )
    return project


# ============================================================================
# TEST SUITE 1: 360 MEMORY INJECTION (ALWAYS PRESENT)
# ============================================================================

class TestMemoryInjection:
    """Test 360 memory injection logic (always included in prompts)."""

    def test_inject_360_memory_with_learnings(self, product_with_git_enabled):
        """BEHAVIOR: 360 memory section is ALWAYS included when learnings exist."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        memory_section = generator._inject_360_memory(product_with_git_enabled)

        # Assert 360 memory section exists
        assert memory_section is not None
        assert len(memory_section) > 0

        # Assert mentions 360 memory system
        assert "360 Memory" in memory_section or "memory" in memory_section.lower()

        # Assert includes learning count
        assert "2" in memory_section or "two" in memory_section.lower()

        # Assert provides instructions to use learnings
        assert "learning" in memory_section.lower() or "previous" in memory_section.lower()

    @pytest.mark.asyncio
    async def test_inject_360_memory_with_no_learnings(self, product_no_memory):
        """BEHAVIOR: 360 memory section still present even with no learnings."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        memory_section = generator._inject_360_memory(product_no_memory)

        # Assert section exists (even if no learnings)
        assert memory_section is not None

        # Assert mentions 360 memory system
        assert "360 Memory" in memory_section or "memory" in memory_section.lower()

    @pytest.mark.asyncio
    async def test_inject_360_memory_includes_context(self, product_with_git_enabled):
        """BEHAVIOR: Memory injection includes context data (objectives, decisions)."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        memory_section = generator._inject_360_memory(product_with_git_enabled)

        # Assert section exists
        assert memory_section is not None

        # Assert mentions objectives or context
        assert "objective" in memory_section.lower() or "context" in memory_section.lower()


# ============================================================================
# TEST SUITE 2: GIT INTEGRATION INJECTION (CONDITIONAL)
# ============================================================================

class TestGitInjection:
    """Test git integration prompt injection (only when enabled)."""

    @pytest.mark.asyncio
    async def test_inject_git_when_enabled(self, product_with_git_enabled):
        """BEHAVIOR: When git_integration.enabled=true, prompt includes git instructions."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        git_section = generator._inject_git_instructions(product_with_git_enabled)

        # Assert git section exists
        assert git_section is not None
        assert len(git_section) > 0

        # Assert includes git commands
        assert "git log" in git_section
        assert "git show" in git_section

        # Assert mentions integration
        assert "Git Integration" in git_section or "git" in git_section.lower()

        # Assert includes commit limit (20)
        assert "20" in git_section or "-20" in git_section

    @pytest.mark.asyncio
    async def test_inject_git_when_disabled(self, product_with_git_disabled):
        """BEHAVIOR: When git_integration.enabled=false, git section is EMPTY."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        git_section = generator._inject_git_instructions(product_with_git_disabled)

        # Assert git section is empty string
        assert git_section == ""

    @pytest.mark.asyncio
    async def test_inject_git_no_config(self, product_no_memory):
        """BEHAVIOR: When no git_integration config, git section is EMPTY."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        git_section = generator._inject_git_instructions(product_no_memory)

        # Assert git section is empty (no config = disabled)
        assert git_section == ""

    @pytest.mark.asyncio
    async def test_inject_git_respects_commit_limit(self, product_with_custom_commit_limit):
        """BEHAVIOR: Git prompt uses product's custom commit_limit (50)."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        git_section = generator._inject_git_instructions(product_with_custom_commit_limit)

        # Assert git section exists
        assert git_section is not None
        assert len(git_section) > 0

        # Assert uses custom limit (50)
        assert "50" in git_section or "-50" in git_section

        # Assert does NOT use default limit (20)
        assert "-20" not in git_section

    @pytest.mark.asyncio
    async def test_inject_git_respects_default_branch(self, product_with_custom_commit_limit):
        """BEHAVIOR: Git prompt uses product's default_branch config."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        git_section = generator._inject_git_instructions(product_with_custom_commit_limit)

        # Assert git section exists
        assert git_section is not None

        # Assert mentions default branch (develop)
        assert "develop" in git_section


# ============================================================================
# TEST SUITE 3: COMBINED INJECTION (BOTH SOURCES)
# ============================================================================

class TestCombinedInjection:
    """Test combining 360 memory + git integration in prompts."""

    def test_orchestrator_prompt_includes_both_when_git_enabled(
        self,
        mock_db_session,
        product_with_git_enabled,
        mock_project
    ):
        """BEHAVIOR: Orchestrator prompt includes BOTH 360 memory AND git when enabled."""
        generator = ThinClientPromptGenerator(db=mock_db_session, tenant_key="test-tenant")

        # Mock database queries to return our test data
        with patch.object(generator, '_fetch_product', return_value=product_with_git_enabled):
            prompt = generator._build_thin_prompt_with_memory(
                orchestrator_id="orch-123",
                project_id="proj-123",
                project_name="Test Project",
                instance_number=1,
                tool="universal",
                product=product_with_git_enabled
            )

        # Assert both sections present
        assert "360 Memory" in prompt or "memory" in prompt.lower()
        assert "git log" in prompt
        assert "Git Integration" in prompt or "git" in prompt.lower()

        # Assert they are SEPARATE sections
        assert prompt.count("##") >= 2  # At least 2 section headers

    def test_orchestrator_prompt_only_memory_when_git_disabled(
        self,
        mock_db_session,
        product_with_git_disabled,
        mock_project
    ):
        """BEHAVIOR: Orchestrator prompt has 360 memory but NO git when disabled."""
        generator = ThinClientPromptGenerator(db=mock_db_session, tenant_key="test-tenant")

        with patch.object(generator, '_fetch_product', return_value=product_with_git_disabled):
            prompt = generator._build_thin_prompt_with_memory(
                orchestrator_id="orch-123",
                project_id="proj-123",
                project_name="Test Project",
                instance_number=1,
                tool="universal",
                product=product_with_git_disabled
            )

        # Assert 360 memory present
        assert "360 Memory" in prompt or "memory" in prompt.lower()

        # Assert git NOT present
        assert "git log" not in prompt
        assert "Git Integration" not in prompt

    def test_prompt_injection_preserves_existing_sections(
        self,
        mock_db_session,
        product_with_git_enabled
    ):
        """BEHAVIOR: Injected sections don't break existing prompt structure."""
        generator = ThinClientPromptGenerator(db=mock_db_session, tenant_key="test-tenant")

        with patch.object(generator, '_fetch_product', return_value=product_with_git_enabled):
            prompt = generator._build_thin_prompt_with_memory(
                orchestrator_id="orch-123",
                project_id="proj-123",
                project_name="Test Project",
                instance_number=1,
                tool="universal",
                product=product_with_git_enabled
            )

        # Assert existing sections still present
        assert "IDENTITY" in prompt
        assert "MCP CONNECTION" in prompt
        assert "STARTUP SEQUENCE" in prompt
        assert "Orchestrator ID" in prompt


# ============================================================================
# TEST SUITE 4: EDGE CASES & ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_git_injection_with_missing_commit_limit(self):
        """BEHAVIOR: Uses default commit_limit (20) when not specified."""
        product = Product(
            id="prod-edge",
            tenant_key="test-tenant",
            name="Edge Case Product",
            product_memory={
                "git_integration": {
                    "enabled": True
                    # commit_limit MISSING
                }
            }
        )

        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")
        git_section = generator._inject_git_instructions(product)

        # Assert uses default limit (20)
        assert "20" in git_section or "-20" in git_section

    @pytest.mark.asyncio
    async def test_git_injection_with_missing_default_branch(self):
        """BEHAVIOR: Handles missing default_branch gracefully."""
        product = Product(
            id="prod-edge2",
            tenant_key="test-tenant",
            name="Edge Case Product 2",
            product_memory={
                "git_integration": {
                    "enabled": True,
                    "commit_limit": 30
                    # default_branch MISSING
                }
            }
        )

        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")
        git_section = generator._inject_git_instructions(product)

        # Assert git section still generated (no crash)
        assert git_section is not None
        assert len(git_section) > 0

    @pytest.mark.asyncio
    async def test_memory_injection_with_empty_learnings(self):
        """BEHAVIOR: Handles empty learnings list gracefully."""
        product = Product(
            id="prod-edge3",
            tenant_key="test-tenant",
            name="Edge Case Product 3",
            product_memory={
                "learnings": [],  # Empty list
                "context": {}
            }
        )

        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")
        memory_section = generator._inject_360_memory(product)

        # Assert section exists (no crash)
        assert memory_section is not None

    @pytest.mark.asyncio
    async def test_injection_with_null_product_memory(self):
        """BEHAVIOR: Handles None product_memory gracefully."""
        product = Product(
            id="prod-edge4",
            tenant_key="test-tenant",
            name="Edge Case Product 4",
            product_memory=None  # NULL memory
        )

        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        # Should not crash
        memory_section = generator._inject_360_memory(product)
        git_section = generator._inject_git_instructions(product)

        assert memory_section is not None
        assert git_section == ""  # Git disabled when no config


# ============================================================================
# TEST SUITE 5: INTEGRATION TESTS
# ============================================================================

class TestPromptIntegration:
    """Integration tests with real prompt generation workflow."""

    @pytest.mark.asyncio
    async def test_full_prompt_generation_with_git_enabled(
        self,
        mock_db_session,
        product_with_git_enabled,
        mock_project
    ):
        """INTEGRATION: Full prompt generation includes git + memory."""
        from unittest.mock import MagicMock
        
        generator = ThinClientPromptGenerator(db=mock_db_session, tenant_key="test-tenant")

        # Mock database execute to return proper scalar results
        mock_project.product_id = product_with_git_enabled.id
        
        # Mock project query
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        
        # Mock product query
        mock_product_result = MagicMock()
        mock_product_result.scalar_one_or_none.return_value = product_with_git_enabled
        
        # Mock orchestrator query (no existing orchestrator)
        mock_orch_result = MagicMock()
        mock_orch_scalars = MagicMock()
        mock_orch_scalars.first.return_value = None
        mock_orch_result.scalars.return_value = mock_orch_scalars
        
        # Mock instance number query
        mock_instance_result = MagicMock()
        mock_instance_result.scalar.return_value = 0
        
        # Setup execute mock to return appropriate results
        async def mock_execute(stmt):
            # Detect query type by inspecting statement
            stmt_str = str(stmt)
            if "projects" in stmt_str.lower() and "product_id" not in stmt_str.lower():
                return mock_project_result
            elif "products" in stmt_str.lower():
                return mock_product_result
            elif "mcp_agent_jobs" in stmt_str.lower() and "max" in stmt_str.lower():
                return mock_instance_result
            else:
                return mock_orch_result
        
        mock_db_session.execute = mock_execute
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Generate full prompt
        result = await generator.generate(
            project_id="proj-123",
            user_id="user-123",
            tool="universal",
            instance_number=1,
            field_priorities=None
        )

        # Assert result structure
        assert "orchestrator_id" in result
        assert "thin_prompt" in result

        prompt = result["thin_prompt"]

        # Assert both injections present
        assert "360 Memory" in prompt or "memory" in prompt.lower()
        assert "git log" in prompt

        # Assert existing structure preserved
        assert "IDENTITY" in prompt
        assert "MCP CONNECTION" in prompt

    @pytest.mark.asyncio
    async def test_full_prompt_generation_with_git_disabled(
        self,
        mock_db_session,
        product_with_git_disabled,
        mock_project
    ):
        """INTEGRATION: Full prompt generation excludes git when disabled."""
        from unittest.mock import MagicMock
        
        generator = ThinClientPromptGenerator(db=mock_db_session, tenant_key="test-tenant")

        # Mock database execute to return proper scalar results
        mock_project.product_id = product_with_git_disabled.id
        
        # Mock project query
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        
        # Mock product query
        mock_product_result = MagicMock()
        mock_product_result.scalar_one_or_none.return_value = product_with_git_disabled
        
        # Mock orchestrator query (no existing orchestrator)
        mock_orch_result = MagicMock()
        mock_orch_scalars = MagicMock()
        mock_orch_scalars.first.return_value = None
        mock_orch_result.scalars.return_value = mock_orch_scalars
        
        # Mock instance number query
        mock_instance_result = MagicMock()
        mock_instance_result.scalar.return_value = 0
        
        # Setup execute mock to return appropriate results
        async def mock_execute(stmt):
            stmt_str = str(stmt)
            if "projects" in stmt_str.lower() and "product_id" not in stmt_str.lower():
                return mock_project_result
            elif "products" in stmt_str.lower():
                return mock_product_result
            elif "mcp_agent_jobs" in stmt_str.lower() and "max" in stmt_str.lower():
                return mock_instance_result
            else:
                return mock_orch_result
        
        mock_db_session.execute = mock_execute
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await generator.generate(
            project_id="proj-123",
            user_id="user-123",
            tool="universal",
            instance_number=1,
            field_priorities=None
        )

        prompt = result["thin_prompt"]

        # Assert memory present, git absent
        assert "360 Memory" in prompt or "memory" in prompt.lower()
        assert "git log" not in prompt


# ============================================================================
# TEST SUITE 6: TOKEN BUDGET VERIFICATION
# ============================================================================

class TestTokenBudget:
    """Verify injected prompts stay within token budget."""

    @pytest.mark.asyncio
    async def test_injected_prompt_stays_under_budget(self, product_with_git_enabled):
        """BEHAVIOR: Injected sections don't bloat prompt beyond reasonable limits."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        memory_section = generator._inject_360_memory(product_with_git_enabled)
        git_section = generator._inject_git_instructions(product_with_git_enabled)

        # Calculate combined token estimate (1 token ≈ 4 chars)
        combined_chars = len(memory_section) + len(git_section)
        estimated_tokens = combined_chars // 4

        # Assert injections stay under 500 tokens combined
        assert estimated_tokens < 500, f"Injected sections too large: {estimated_tokens} tokens"

    @pytest.mark.asyncio
    async def test_memory_section_concise(self, product_with_git_enabled):
        """BEHAVIOR: 360 memory section is concise (<250 tokens)."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        memory_section = generator._inject_360_memory(product_with_git_enabled)
        estimated_tokens = len(memory_section) // 4

        # Assert under 250 tokens
        assert estimated_tokens < 250, f"Memory section too large: {estimated_tokens} tokens"

    @pytest.mark.asyncio
    async def test_git_section_concise(self, product_with_git_enabled):
        """BEHAVIOR: Git integration section is concise (<300 tokens)."""
        generator = ThinClientPromptGenerator(db=AsyncMock(), tenant_key="test-tenant")

        git_section = generator._inject_git_instructions(product_with_git_enabled)
        estimated_tokens = len(git_section) // 4

        # Assert under 300 tokens
        assert estimated_tokens < 300, f"Git section too large: {estimated_tokens} tokens"
