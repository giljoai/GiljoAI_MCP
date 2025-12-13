"""
Handover 0346: Depth Config Field Standardization Tests

Tests verify that 'vision_documents' is the canonical field name for vision
document depth configuration throughout the codebase.

This is a TDD implementation - these tests are written FIRST and should FAIL
until the implementation is complete.
"""

import pytest
from pydantic import ValidationError


class TestDepthConfigFieldStandardization:
    """Test suite for vision_documents field standardization."""

    def test_pydantic_model_uses_vision_documents(self):
        """Verify DepthConfig Pydantic model uses 'vision_documents' field."""
        from api.endpoints.users import DepthConfig

        # Default should use vision_documents
        config = DepthConfig()
        assert hasattr(config, 'vision_documents'), \
            "DepthConfig must have 'vision_documents' field"
        assert not hasattr(config, 'vision_chunking'), \
            "DepthConfig must NOT have deprecated 'vision_chunking' field"
        assert config.vision_documents == 'moderate', \
            "Default vision_documents should be 'moderate'"

    def test_depth_config_accepts_all_levels(self):
        """Verify all valid depth levels are accepted."""
        from api.endpoints.users import DepthConfig

        valid_levels = ['none', 'light', 'moderate', 'heavy']
        for level in valid_levels:
            config = DepthConfig(vision_documents=level)
            assert config.vision_documents == level, \
                f"DepthConfig should accept '{level}' for vision_documents"

    def test_depth_config_rejects_invalid_levels(self):
        """Verify invalid depth levels are rejected."""
        from api.endpoints.users import DepthConfig

        with pytest.raises(ValidationError):
            DepthConfig(vision_documents='invalid_level')

    def test_user_model_default_depth_config_uses_vision_documents(self):
        """Verify User model default depth config uses 'vision_documents' key."""
        from src.giljo_mcp.models.auth import User

        # Get default depth config from User model
        default_depth_config = User.__table__.columns['depth_config'].default.arg

        assert 'vision_documents' in default_depth_config, \
            "User.depth_config default must contain 'vision_documents' key"
        assert 'vision_chunking' not in default_depth_config, \
            "User.depth_config default must NOT contain deprecated 'vision_chunking' key"
        assert default_depth_config['vision_documents'] == 'moderate', \
            "Default vision_documents level should be 'moderate'"

    def test_user_service_get_depth_config_uses_vision_documents(self):
        """Verify UserService get_depth_config uses 'vision_documents' key in default."""
        from src.giljo_mcp.services.user_service import UserService
        import inspect

        # Check the implementation method (get_depth_config delegates to this)
        source = inspect.getsource(UserService._get_depth_config_impl)
        assert 'vision_documents' in source or '"vision_documents"' in source, \
            "UserService._get_depth_config_impl must use 'vision_documents' in defaults"
        assert 'vision_chunking' not in source and '"vision_chunking"' not in source, \
            "UserService._get_depth_config_impl must NOT use deprecated 'vision_chunking'"

    def test_user_service_validate_depth_config_checks_vision_documents(self):
        """Verify UserService update methods validate 'vision_documents' field."""
        from src.giljo_mcp.services.user_service import UserService
        import inspect

        # Check that validation code references vision_documents
        source = inspect.getsource(UserService._update_depth_config_impl)
        assert 'vision_documents' in source or '"vision_documents"' in source, \
            "UserService validation must check 'vision_documents' field"
        assert 'vision_chunking' not in source and '"vision_chunking"' not in source, \
            "UserService validation must NOT check deprecated 'vision_chunking' field"

    def test_project_service_uses_vision_documents(self):
        """Verify ProjectService uses 'vision_documents' in default depth config."""
        from src.giljo_mcp.services.project_service import ProjectService

        # Check that any hardcoded defaults use vision_documents
        # This test verifies the default dict at line ~1765
        import inspect
        source = inspect.getsource(ProjectService)

        # Should contain vision_documents
        assert 'vision_documents' in source or '"vision_documents"' in source, \
            "ProjectService should reference 'vision_documents' field"

        # Should NOT contain vision_chunking
        assert 'vision_chunking' not in source and '"vision_chunking"' not in source, \
            "ProjectService should NOT reference deprecated 'vision_chunking' field"

    def test_thin_prompt_generator_uses_vision_documents(self):
        """Verify ThinClientPromptGenerator uses 'vision_documents' in depth config."""
        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        # Check docstring and default dict
        import inspect
        source = inspect.getsource(ThinClientPromptGenerator)

        # Should contain vision_documents
        assert 'vision_documents' in source or '"vision_documents"' in source, \
            "ThinClientPromptGenerator should reference 'vision_documents' field"

        # Should NOT contain vision_chunking
        assert 'vision_chunking' not in source and '"vision_chunking"' not in source, \
            "ThinClientPromptGenerator should NOT reference deprecated 'vision_chunking' field"


class TestDepthConfigAPIRoundtrip:
    """Test full API roundtrip with depth config."""

    @pytest.mark.skip(reason="Requires test_user_with_session fixture - deferred to integration test suite")
    @pytest.mark.asyncio
    async def test_depth_config_api_roundtrip(self, async_client, test_user_with_session):
        """Test complete roundtrip: POST depth config, GET returns same config."""
        user, session_token = test_user_with_session

        # POST depth config with vision_documents
        depth_config_payload = {
            'vision_documents': 'heavy',
            'product_core': 'exclude',
            'tech_stack': 'required',
            'architecture': 'overview',
            'testing': 'none',
            'memory_360': 1,
            'git_history': 10,
            'agent_templates': 'minimal'
        }

        response = await async_client.post(
            '/api/users/me/context/depth',
            json=depth_config_payload,
            headers={'Authorization': f'Bearer {session_token}'}
        )
        assert response.status_code == 200, \
            f"POST depth config failed: {response.json()}"

        # GET depth config
        response = await async_client.get(
            '/api/users/me/context/depth',
            headers={'Authorization': f'Bearer {session_token}'}
        )
        assert response.status_code == 200, \
            f"GET depth config failed: {response.json()}"

        data = response.json()
        assert data['vision_documents'] == 'heavy', \
            "GET should return same vision_documents value as POST"
        assert 'vision_chunking' not in data, \
            "GET should NOT return deprecated 'vision_chunking' field"


class TestFrontendFieldNaming:
    """Test frontend uses correct field names."""

    def test_frontend_component_uses_vision_documents(self):
        """Verify ContextPriorityConfig.vue uses 'vision_documents' field."""
        from pathlib import Path

        component_path = Path('F:/GiljoAI_MCP/frontend/src/components/settings/ContextPriorityConfig.vue')
        assert component_path.exists(), "ContextPriorityConfig.vue not found"

        content = component_path.read_text(encoding='utf-8')

        # Should use vision_documents
        assert 'vision_documents' in content or 'vision_documents:' in content, \
            "ContextPriorityConfig.vue should use 'vision_documents' field"

        # Should NOT use vision_document_depth
        assert 'vision_document_depth' not in content, \
            "ContextPriorityConfig.vue should NOT use deprecated 'vision_document_depth' field"

    def test_frontend_test_spec_uses_vision_documents(self):
        """Verify test spec uses 'vision_documents' field."""
        from pathlib import Path

        spec_path = Path('F:/GiljoAI_MCP/frontend/src/components/settings/ContextPriorityConfig.vision.spec.js')
        assert spec_path.exists(), "Test spec not found"

        content = spec_path.read_text(encoding='utf-8')

        # Should use vision_documents
        assert 'vision_documents' in content or "'vision_documents'" in content, \
            "Test spec should use 'vision_documents' field"

        # Should NOT use vision_document_depth
        assert 'vision_document_depth' not in content, \
            "Test spec should NOT use deprecated 'vision_document_depth' field"
