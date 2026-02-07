"""
Unit tests for MissionPlanner._build_fetch_instructions() method.

Handover 0350b: Framing-based architecture for get_orchestrator_instructions().

Tests the new method that generates framing instructions (~500 tokens) instead of
inline context (~4-8K tokens). Orchestrator uses these instructions to call
fetch_context() tools on-demand.

Following TDD principles: Tests written BEFORE implementation.
"""

from unittest.mock import Mock

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project


class TestBuildFetchInstructions:
    """Test cases for _build_fetch_instructions() method."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.is_async = True
        return db_manager

    @pytest.fixture
    def mission_planner(self, mock_db_manager):
        """Create MissionPlanner instance with mocked dependencies."""
        return MissionPlanner(mock_db_manager)

    @pytest.fixture
    def sample_product(self):
        """Create a sample Product for testing."""
        product = Mock(spec=Product)
        product.id = "550e8400-e29b-41d4-a716-446655440000"
        product.tenant_key = "tenant_abc"
        product.name = "Test Product"
        product.description = "A test product description"
        product.config_data = {
            "tech_stack": {"languages": ["Python", "JavaScript"]},
            "architecture": "Modular monolith with service layer",
            "test_config": {"strategy": "TDD", "coverage_target": 80},
        }
        product.product_memory = {
            "sequential_history": [],
            "git_integration": {"enabled": False},
        }
        return product

    @pytest.fixture
    def sample_project(self):
        """Create a sample Project for testing."""
        project = Mock(spec=Project)
        project.id = "660e8400-e29b-41d4-a716-446655440001"
        project.tenant_key = "tenant_abc"
        project.name = "Test Project"
        project.description = "Build a new feature"
        return project

    # =========================================================================
    # Test: Tier Assignment Based on Priority
    # =========================================================================

    def test_build_fetch_instructions_returns_three_tiers(self, mission_planner, sample_product, sample_project):
        """Test that _build_fetch_instructions returns critical/important/reference tiers."""
        field_priorities = {
            "product_core": 1,
            "tech_stack": 2,
            "memory_360": 3,
        }
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        assert "critical" in result
        assert "important" in result
        assert "reference" in result
        assert isinstance(result["critical"], list)
        assert isinstance(result["important"], list)
        assert isinstance(result["reference"], list)

    def test_priority_1_maps_to_critical_tier(self, mission_planner, sample_product, sample_project):
        """Test that priority 1 fields go to critical tier."""
        field_priorities = {"product_core": 1}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        critical_fields = [item["field"] for item in result["critical"]]
        assert "product_core" in critical_fields

    def test_priority_2_maps_to_important_tier(self, mission_planner, sample_product, sample_project):
        """Test that priority 2 fields go to important tier."""
        field_priorities = {"tech_stack": 2}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        important_fields = [item["field"] for item in result["important"]]
        assert "tech_stack" in important_fields

    def test_priority_3_maps_to_reference_tier(self, mission_planner, sample_product, sample_project):
        """Test that priority 3 fields go to reference tier."""
        field_priorities = {"memory_360": 3}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        reference_fields = [item["field"] for item in result["reference"]]
        assert "memory_360" in reference_fields

    def test_priority_4_excluded_from_all_tiers(self, mission_planner, sample_product, sample_project):
        """Test that priority 4 (EXCLUDED) fields are not in any tier."""
        field_priorities = {
            "product_core": 1,
            "excluded_field": 4,
        }
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        all_fields = []
        for tier in ["critical", "important", "reference"]:
            all_fields.extend([item["field"] for item in result[tier]])

        assert "excluded_field" not in all_fields

    # =========================================================================
    # Test: Instruction Structure
    # =========================================================================

    def test_instruction_contains_required_fields(self, mission_planner, sample_product, sample_project):
        """Test that each instruction has field, tool, params, framing, estimated_tokens."""
        field_priorities = {"product_core": 1}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        assert len(result["critical"]) > 0
        instruction = result["critical"][0]

        assert "field" in instruction
        assert "tool" in instruction
        assert "params" in instruction
        assert "framing" in instruction
        assert "estimated_tokens" in instruction

    def test_instruction_tool_is_fetch_context(self, mission_planner, sample_product, sample_project):
        """Test that all instructions use fetch_context tool."""
        field_priorities = {
            "product_core": 1,
            "tech_stack": 2,
            "memory_360": 3,
        }
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        for tier in ["critical", "important", "reference"]:
            for instruction in result[tier]:
                assert instruction["tool"] == "fetch_context"

    def test_instruction_params_include_product_id_and_tenant_key(
        self, mission_planner, sample_product, sample_project
    ):
        """Test that params include product_id and tenant_key for multi-tenant isolation."""
        field_priorities = {"product_core": 1}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        instruction = result["critical"][0]
        assert "product_id" in instruction["params"]
        assert "tenant_key" in instruction["params"]
        assert instruction["params"]["product_id"] == str(sample_product.id)
        assert instruction["params"]["tenant_key"] == sample_product.tenant_key

    # =========================================================================
    # Test: Tier-Specific Framing
    # =========================================================================

    def test_critical_tier_framing_starts_with_required(self, mission_planner, sample_product, sample_project):
        """Test that critical tier framing starts with 'REQUIRED:'."""
        field_priorities = {"product_core": 1}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        instruction = result["critical"][0]
        assert instruction["framing"].startswith("REQUIRED:")

    def test_important_tier_framing_starts_with_recommended(self, mission_planner, sample_product, sample_project):
        """Test that important tier framing starts with 'RECOMMENDED:'."""
        field_priorities = {"tech_stack": 2}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        instruction = result["important"][0]
        assert instruction["framing"].startswith("RECOMMENDED:")

    def test_reference_tier_framing_starts_with_optional(self, mission_planner, sample_product, sample_project):
        """Test that reference tier framing starts with 'OPTIONAL:'."""
        field_priorities = {"memory_360": 3}
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        instruction = result["reference"][0]
        assert instruction["framing"].startswith("OPTIONAL:")

    # =========================================================================
    # Test: Depth Configuration
    # =========================================================================

    def test_depth_config_applied_to_vision_documents(self, mission_planner, sample_product, sample_project):
        """Test that depth_config is applied to vision_documents instruction."""
        field_priorities = {"vision_documents": 2}
        depth_config = {"vision_documents": 20}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Find vision_documents instruction
        vision_instr = None
        for tier in ["critical", "important", "reference"]:
            for item in result[tier]:
                if item["field"] == "vision_documents":
                    vision_instr = item
                    break

        assert vision_instr is not None
        assert vision_instr["params"]["limit"] == 20
        assert vision_instr.get("supports_pagination") is True

    def test_depth_config_applied_to_memory_360(self, mission_planner, sample_product, sample_project):
        """Test that depth_config is applied to memory_360 instruction."""
        field_priorities = {"memory_360": 3}
        depth_config = {"memory_360": 10}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Find memory_360 instruction
        memory_instr = None
        for item in result["reference"]:
            if item["field"] == "memory_360":
                memory_instr = item
                break

        assert memory_instr is not None
        assert memory_instr["params"]["limit"] == 10

    def test_depth_config_applied_to_git_history(self, mission_planner, sample_product, sample_project):
        """Test that depth_config is applied to git_history instruction."""
        # Enable git integration
        sample_product.product_memory = {"git_integration": {"enabled": True, "repository": "test/repo"}}
        field_priorities = {"git_history": 2}
        depth_config = {"git_history": 50}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Find git_history instruction
        git_instr = None
        for tier in ["critical", "important", "reference"]:
            for item in result[tier]:
                if item["field"] == "git_history":
                    git_instr = item
                    break

        assert git_instr is not None
        assert git_instr["params"]["limit"] == 50

    def test_depth_config_applied_to_agent_templates(self, mission_planner, sample_product, sample_project):
        """Test that depth_config is applied to agent_templates instruction."""
        field_priorities = {"agent_templates": 2}
        depth_config = {"agent_templates": "full"}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Find agent_templates instruction
        agent_instr = None
        for tier in ["critical", "important", "reference"]:
            for item in result[tier]:
                if item["field"] == "agent_templates":
                    agent_instr = item
                    break

        assert agent_instr is not None
        assert agent_instr["params"]["depth"] == "full"

    # =========================================================================
    # Test: All Known Fields
    # =========================================================================

    def test_all_known_fields_generate_instructions(self, mission_planner, sample_product, sample_project):
        """Test that all known context fields generate valid instructions."""
        # Enable git integration for git_history
        sample_product.product_memory = {"git_integration": {"enabled": True, "repository": "test/repo"}}

        field_priorities = {
            "product_core": 1,
            "vision_documents": 2,
            "tech_stack": 1,
            "architecture": 2,
            "testing": 3,
            "memory_360": 3,
            "git_history": 2,
            "agent_templates": 3,
        }
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Collect all fields
        all_fields = []
        for tier in ["critical", "important", "reference"]:
            all_fields.extend([item["field"] for item in result[tier]])

        # All configured fields should be present
        for field in field_priorities:
            if field_priorities[field] < 4:  # Not excluded
                assert field in all_fields, f"Field {field} missing from instructions"

    # =========================================================================
    # Test: Token Estimation
    # =========================================================================

    def test_total_response_under_1000_tokens(self, mission_planner, sample_product, sample_project):
        """Test that the framing response is under 1000 tokens (target: ~500)."""
        import json

        field_priorities = {
            "product_core": 1,
            "tech_stack": 2,
            "architecture": 2,
            "memory_360": 3,
        }
        depth_config = {}

        result = mission_planner._build_fetch_instructions(
            product=sample_product,
            project=sample_project,
            field_priorities=field_priorities,
            depth_config=depth_config,
        )

        # Estimate tokens: 1 token ~= 4 characters
        json_str = json.dumps(result)
        estimated_tokens = len(json_str) // 4

        assert estimated_tokens < 1000, f"Token count {estimated_tokens} exceeds 1000"


class TestGetTierFraming:
    """Test cases for _get_tier_framing() helper method."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.is_async = True
        return db_manager

    @pytest.fixture
    def mission_planner(self, mock_db_manager):
        """Create MissionPlanner instance."""
        return MissionPlanner(mock_db_manager)

    def test_critical_tier_adds_required_prefix(self, mission_planner):
        """Test that critical tier adds REQUIRED: prefix."""
        result = mission_planner._get_tier_framing("critical", "Product context")
        assert result.startswith("REQUIRED:")
        assert "Product context" in result

    def test_important_tier_adds_recommended_prefix(self, mission_planner):
        """Test that important tier adds RECOMMENDED: prefix."""
        result = mission_planner._get_tier_framing("important", "Tech stack info")
        assert result.startswith("RECOMMENDED:")
        assert "Tech stack info" in result

    def test_reference_tier_adds_optional_prefix(self, mission_planner):
        """Test that reference tier adds OPTIONAL: prefix."""
        result = mission_planner._get_tier_framing("reference", "Historical data")
        assert result.startswith("OPTIONAL:")
        assert "Historical data" in result

    def test_no_duplicate_prefix_if_already_present(self, mission_planner):
        """Test that prefix is not duplicated if already present."""
        result = mission_planner._get_tier_framing("critical", "REQUIRED: Already prefixed")
        assert result.count("REQUIRED:") == 1
