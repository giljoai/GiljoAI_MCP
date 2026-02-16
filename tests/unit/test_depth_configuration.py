"""
Unit tests for depth configuration (Handover 0283).

Tests verify that depth settings control HOW MUCH detail is included
for 360 Memory, Git History, and Agent Templates.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.templates import AgentTemplate
from src.giljo_mcp.tools.agent_discovery import _format_agent_info, get_available_agents


@pytest.fixture
def mock_product():
    """Create mock product with vision, tech stack, and git integration."""
    product = MagicMock(spec=Product)
    product.id = "prod-123"
    product.name = "Test Product"
    product.description = "Test Description"
    product.tenant_key = "tk_test"
    product.vision_documents = []
    product.primary_vision_text = ""
    product.config_data = {
        "tech_stack": {
            "languages": ["Python", "JavaScript"],
            "frameworks": ["FastAPI", "Vue"],
            "database": "PostgreSQL",
        }
    }
    product.product_memory = {
        "sequential_history": [
            {"sequence": 1, "summary": "Project 1", "key_outcomes": []},
            {"sequence": 2, "summary": "Project 2", "key_outcomes": []},
            {"sequence": 3, "summary": "Project 3", "key_outcomes": []},
            {"sequence": 4, "summary": "Project 4", "key_outcomes": []},
            {"sequence": 5, "summary": "Project 5", "key_outcomes": []},
            {"sequence": 6, "summary": "Project 6", "key_outcomes": []},
            {"sequence": 7, "summary": "Project 7", "key_outcomes": []},
            {"sequence": 8, "summary": "Project 8", "key_outcomes": []},
            {"sequence": 9, "summary": "Project 9", "key_outcomes": []},
            {"sequence": 10, "summary": "Project 10", "key_outcomes": []},
        ],
        "git_integration": {
            "enabled": True,
            "commit_limit": 20,  # Will be overridden by depth config
        },
    }
    return product


@pytest.fixture
def mock_project():
    """Create mock project."""
    project = MagicMock(spec=Project)
    project.id = "proj-123"
    project.description = "Test project description"
    return project


@pytest.fixture
def mock_db_manager():
    """Create mock database manager."""
    db_manager = MagicMock()
    db_manager.get_session_async = AsyncMock()
    return db_manager


# ==============================================================================
# 360 Memory Depth Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_360_memory_depth_1_project(mock_product, mock_project, mock_db_manager):
    """Test 360 Memory with depth=1 returns 1 project."""
    planner = MissionPlanner(mock_db_manager)

    result = await planner._extract_product_history(
        product=mock_product,
        priority=2,  # IMPORTANT
        max_entries=1,  # Depth configuration
    )

    # Should contain exactly 1 project (most recent)
    assert "Learning #10" in result
    assert "Learning #9" not in result
    assert "Project 10" in result


@pytest.mark.asyncio
async def test_360_memory_depth_3_projects(mock_product, mock_project, mock_db_manager):
    """Test 360 Memory with depth=3 returns 3 projects."""
    planner = MissionPlanner(mock_db_manager)

    result = await planner._extract_product_history(
        product=mock_product,
        priority=2,
        max_entries=3,  # Depth configuration
    )

    # Should contain exactly 3 most recent projects
    assert "Learning #10" in result
    assert "Learning #9" in result
    assert "Learning #8" in result
    assert "Learning #7" not in result  # Older project excluded


@pytest.mark.asyncio
async def test_360_memory_depth_5_projects(mock_product, mock_project, mock_db_manager):
    """Test 360 Memory with depth=5 (default) returns 5 projects."""
    planner = MissionPlanner(mock_db_manager)

    result = await planner._extract_product_history(
        product=mock_product,
        priority=2,
        max_entries=5,  # Default depth
    )

    # Should contain exactly 5 most recent projects
    assert "Learning #10" in result
    assert "Learning #9" in result
    assert "Learning #8" in result
    assert "Learning #7" in result
    assert "Learning #6" in result
    assert "Learning #5" not in result  # Older project excluded


@pytest.mark.asyncio
async def test_360_memory_depth_10_projects(mock_product, mock_project, mock_db_manager):
    """Test 360 Memory with depth=10 returns all 10 projects."""
    planner = MissionPlanner(mock_db_manager)

    result = await planner._extract_product_history(
        product=mock_product,
        priority=2,
        max_entries=10,  # Maximum depth
    )

    # Should contain all 10 projects
    assert "Learning #10" in result
    assert "Learning #1" in result
    assert result.count("Learning #") == 10


# ==============================================================================
# Git History Depth Tests
# ==============================================================================


def test_git_history_depth_5_commits(mock_db_manager):
    """Test Git History with depth=5 shows 5 commits in examples."""
    planner = MissionPlanner(mock_db_manager)

    git_config = {
        "enabled": True,
        "commit_limit": 5,  # Depth configuration
    }

    result = planner._inject_git_instructions(git_config)

    # Should contain git log with 5 commits
    assert "git log --oneline -5" in result
    assert result.count("git") >= 4  # Multiple git commands


def test_git_history_depth_10_commits(mock_db_manager):
    """Test Git History with depth=10 shows 10 commits in examples."""
    planner = MissionPlanner(mock_db_manager)

    git_config = {"enabled": True, "commit_limit": 10}

    result = planner._inject_git_instructions(git_config)

    assert "git log --oneline -10" in result


def test_git_history_depth_20_commits_default(mock_db_manager):
    """Test Git History with depth=20 (default) shows 20 commits."""
    planner = MissionPlanner(mock_db_manager)

    git_config = {
        "enabled": True,
        "commit_limit": 20,  # Default depth
    }

    result = planner._inject_git_instructions(git_config)

    assert "git log --oneline -20" in result


def test_git_history_depth_100_commits_maximum(mock_db_manager):
    """Test Git History with depth=100 (maximum) shows 100 commits."""
    planner = MissionPlanner(mock_db_manager)

    git_config = {"enabled": True, "commit_limit": 100}

    result = planner._inject_git_instructions(git_config)

    assert "git log --oneline -100" in result


# ==============================================================================
# Agent Templates Depth Tests
# ==============================================================================


def test_agent_template_depth_type_only():
    """Test agent template with depth='type_only' returns minimal info."""
    template = MagicMock(spec=AgentTemplate)
    template.name = "implementer"
    template.role = "Code Implementation Specialist"
    template.version = "1.2.0"
    template.description = "A very long description that would normally be included..."
    template.created_at = datetime.now(timezone.utc)

    result = _format_agent_info(template, depth="type_only")

    # Should only have name, role, version
    assert result["name"] == "implementer"
    assert result["role"] == "Code Implementation Specialist"
    assert result["version_tag"] == "1.2.0"

    # Should NOT have description, expected_filename, created_at
    assert "description" not in result
    assert "expected_filename" not in result
    assert "created_at" not in result


def test_agent_template_depth_full():
    """Test agent template with depth='full' returns all info."""
    template = MagicMock(spec=AgentTemplate)
    template.name = "implementer"
    template.role = "Code Implementation Specialist"
    template.version = "1.2.0"
    template.description = "Full description with details..."
    template.created_at = datetime.now(timezone.utc)

    result = _format_agent_info(template, depth="full")

    # Should have all fields
    assert result["name"] == "implementer"
    assert result["role"] == "Code Implementation Specialist"
    assert result["version_tag"] == "1.2.0"
    assert result["description"] == "Full description with details..."
    assert result["expected_filename"] == "implementer_1.2.0.md"
    assert result["created_at"] is not None


def test_agent_template_depth_default_is_full():
    """Test agent template without depth parameter defaults to 'full'."""
    template = MagicMock(spec=AgentTemplate)
    template.name = "tester"
    template.role = "Testing Specialist"
    template.version = "1.0.0"
    template.description = "Test description"
    template.created_at = datetime.now(timezone.utc)

    result = _format_agent_info(template)  # No depth parameter

    # Should default to full
    assert "description" in result
    assert "expected_filename" in result


@pytest.mark.asyncio
async def test_get_available_agents_depth_type_only():
    """Test get_available_agents with depth='type_only' filters fields."""
    # Mock database session
    mock_session = AsyncMock()

    # Mock template
    template = MagicMock(spec=AgentTemplate)
    template.name = "implementer"
    template.role = "Code Implementation Specialist"
    template.version = "1.2.0"
    template.description = "Long description..."
    template.created_at = datetime.now(timezone.utc)
    template.is_active = True

    # Mock query result
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [template]
    mock_session.execute.return_value = mock_result

    result = await get_available_agents(session=mock_session, tenant_key="tk_test", depth="type_only")

    # Should succeed
    assert result["success"] is True
    agents = result["data"]["agents"]
    assert len(agents) == 1

    # First agent should only have name, role, version
    agent = agents[0]
    assert "name" in agent
    assert "role" in agent
    assert "version_tag" in agent
    assert "description" not in agent
    assert "expected_filename" not in agent


@pytest.mark.asyncio
async def test_get_available_agents_depth_full():
    """Test get_available_agents with depth='full' includes all fields."""
    mock_session = AsyncMock()

    template = MagicMock(spec=AgentTemplate)
    template.name = "implementer"
    template.role = "Code Implementation Specialist"
    template.version = "1.2.0"
    template.description = "Full description"
    template.created_at = datetime.now(timezone.utc)
    template.is_active = True

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [template]
    mock_session.execute.return_value = mock_result

    result = await get_available_agents(session=mock_session, tenant_key="tk_test", depth="full")

    assert result["success"] is True
    agent = result["data"]["agents"][0]

    # Should have all fields
    assert "name" in agent
    assert "role" in agent
    assert "version_tag" in agent
    assert "description" in agent
    assert "expected_filename" in agent
    assert "created_at" in agent


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_build_context_with_mixed_depths(mock_product, mock_project, mock_db_manager):
    """Test _build_context_with_priorities with mixed depth configuration."""
    planner = MissionPlanner(mock_db_manager)

    field_priorities = {
        "product_core": 1,  # CRITICAL
        "memory_360": 2,  # IMPORTANT
        "git_history": 0,  # Excluded (but git toggle enabled)
    }

    depth_config = {
        "memory_360": 3,  # Show 3 projects
        "git_history": 10,  # Show 10 commits
        "agent_templates": "type_only",  # Minimal
    }

    # Mock the async context manager for serena (if needed)
    with patch.object(planner, "_fetch_serena_codebase_context", return_value=None):
        result = await planner._build_context_with_priorities(
            product=mock_product,
            project=mock_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
            user_id="user-123",
            include_serena=False,
        )

    # Should contain memory with 3 projects
    assert "Learning #10" in result
    assert "Learning #9" in result
    assert "Learning #8" in result
    assert "Learning #7" not in result

    # Should contain git instructions with 10 commits
    assert "git log --oneline -10" in result


@pytest.mark.asyncio
async def test_build_context_without_depth_config_uses_defaults(mock_product, mock_project, mock_db_manager):
    """Test _build_context_with_priorities without depth_config uses defaults."""
    planner = MissionPlanner(mock_db_manager)

    field_priorities = {
        "product_core": 1,
        "memory_360": 2,
    }

    # Don't pass depth_config (should use defaults)
    with patch.object(planner, "_fetch_serena_codebase_context", return_value=None):
        result = await planner._build_context_with_priorities(
            product=mock_product,
            project=mock_project,
            field_priorities=field_priorities,
            # depth_config=None,  # Defaults applied in method
            user_id="user-123",
            include_serena=False,
        )

    # Should use default depth (5 projects for 360 memory)
    assert "Learning #10" in result
    assert "Learning #6" in result
    assert "Learning #5" not in result

    # Should use default git depth (20 commits)
    assert "git log --oneline -20" in result


def test_default_depth_config_values():
    """Test DEFAULT_DEPTH_CONFIG constants are correct."""
    from src.giljo_mcp.services.orchestration_service import DEFAULT_DEPTH_CONFIG

    assert DEFAULT_DEPTH_CONFIG["memory_360"] == 5
    assert DEFAULT_DEPTH_CONFIG["git_history"] == 20
    assert DEFAULT_DEPTH_CONFIG["agent_templates"] == "full"
