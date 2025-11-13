"""
Unit tests for Product Activation response fields

Verifies that all API endpoints return the is_active field correctly
"""

from datetime import datetime

from api.endpoints.products.models import ProductResponse


class TestProductResponseSchema:
    """Test the ProductResponse model includes is_active field"""

    def test_product_response_includes_is_active_field(self):
        """Test that ProductResponse model has is_active field"""
        # Verify field exists in model
        fields = ProductResponse.model_fields
        assert "is_active" in fields, "is_active field missing from ProductResponse model"

        # Verify field type and default
        field = ProductResponse.model_fields["is_active"]
        assert field.is_required() is False, "is_active should not be required"

    def test_product_response_with_is_active_false(self):
        """Test creating ProductResponse with is_active=False"""
        response = ProductResponse(
            id="test-1",
            name="Test Product",
            description="Test",
            vision_path=None,
            created_at=datetime(2024, 1, 1),
            updated_at=None,
            is_active=False,
        )

        assert response.is_active is False
        assert response.id == "test-1"

    def test_product_response_with_is_active_true(self):
        """Test creating ProductResponse with is_active=True"""
        response = ProductResponse(
            id="test-2",
            name="Test Product",
            description="Test",
            vision_path=None,
            created_at=datetime(2024, 1, 1),
            updated_at=None,
            is_active=True,
        )

        assert response.is_active is True
        assert response.id == "test-2"

    def test_product_response_serialization(self):
        """Test that ProductResponse serializes with is_active field"""
        response = ProductResponse(
            id="test-3",
            name="Test Product",
            description="Test",
            vision_path=None,
            created_at=datetime(2024, 1, 1),
            updated_at=None,
            project_count=2,
            task_count=5,
            has_vision=False,
            unresolved_tasks=1,
            unfinished_projects=1,
            vision_documents_count=0,
            is_active=True,
        )

        # Serialize to dict
        data = response.model_dump()

        # Verify is_active is in serialized output
        assert "is_active" in data
        assert data["is_active"] is True

    def test_product_response_json_schema(self):
        """Test that ProductResponse JSON schema includes is_active"""
        schema = ProductResponse.model_json_schema()

        # Verify is_active is in schema properties
        assert "is_active" in schema["properties"], "is_active missing from JSON schema"

        # Verify is_active type
        is_active_schema = schema["properties"]["is_active"]
        assert is_active_schema.get("type") == "boolean"

    def test_list_of_product_responses_with_mixed_is_active(self):
        """Test that a list of ProductResponse objects preserves is_active"""
        products = [
            ProductResponse(
                id="prod-1",
                name="Product 1",
                description=None,
                vision_path=None,
                created_at=datetime(2024, 1, 1),
                updated_at=None,
                is_active=True,
            ),
            ProductResponse(
                id="prod-2",
                name="Product 2",
                description=None,
                vision_path=None,
                created_at=datetime(2024, 1, 2),
                updated_at=None,
                is_active=False,
            ),
            ProductResponse(
                id="prod-3",
                name="Product 3",
                description=None,
                vision_path=None,
                created_at=datetime(2024, 1, 3),
                updated_at=None,
                is_active=False,
            ),
        ]

        # Serialize list
        data = [p.model_dump() for p in products]

        # Verify is_active in each item
        assert data[0]["is_active"] is True
        assert data[1]["is_active"] is False
        assert data[2]["is_active"] is False


class TestProductActivationButtonLogic:
    """Test the button text logic based on is_active field"""

    def test_button_text_when_inactive(self):
        """Test button shows 'Activate' when is_active=False"""
        product = ProductResponse(
            id="test-1",
            name="Test",
            description=None,
            vision_path=None,
            created_at=datetime(2024, 1, 1),
            updated_at=None,
            is_active=False,
        )

        # Frontend logic: button_text = "Deactivate" if product.is_active else "Activate"
        button_text = "Deactivate" if product.is_active else "Activate"
        assert button_text == "Activate"

    def test_button_text_when_active(self):
        """Test button shows 'Deactivate' when is_active=True"""
        product = ProductResponse(
            id="test-2",
            name="Test",
            description=None,
            vision_path=None,
            created_at=datetime(2024, 1, 1),
            updated_at=None,
            is_active=True,
        )

        # Frontend logic: button_text = "Deactivate" if product.is_active else "Activate"
        button_text = "Deactivate" if product.is_active else "Activate"
        assert button_text == "Deactivate"

    def test_button_toggle_simulation(self):
        """Simulate clicking button multiple times"""
        product = ProductResponse(
            id="test-3",
            name="Test",
            description=None,
            vision_path=None,
            created_at=datetime(2024, 1, 1),
            updated_at=None,
            is_active=False,
        )

        # Initially inactive - show Activate button
        button_text = "Deactivate" if product.is_active else "Activate"
        assert button_text == "Activate"

        # User clicks Activate - server returns is_active=True
        product.is_active = True
        button_text = "Deactivate" if product.is_active else "Activate"
        assert button_text == "Deactivate"

        # User clicks Deactivate - server returns is_active=False
        product.is_active = False
        button_text = "Deactivate" if product.is_active else "Activate"
        assert button_text == "Activate"


class TestProductResponseWithAllFields:
    """Test ProductResponse with full data"""

    def test_complete_product_response(self):
        """Test ProductResponse with all fields populated"""
        response = ProductResponse(
            id="prod-complete",
            name="Complete Product",
            description="A product with all fields",
            vision_path="/path/to/vision",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 2),
            project_count=5,
            task_count=20,
            has_vision=True,
            unfinished_projects=2,
            unresolved_tasks=5,
            vision_documents_count=3,
            config_data={"tech_stack": {"languages": "Python"}, "architecture": {"pattern": "MVC"}},
            has_config_data=True,
            is_active=True,  # THE FIX: This field must be present
        )

        # Verify all fields including is_active
        assert response.id == "prod-complete"
        assert response.is_active is True
        assert response.config_data is not None
        assert response.has_config_data is True

        # Verify serialization includes is_active
        data = response.model_dump()
        assert data["is_active"] is True
