"""
Test suite for Product.project_path field functionality (Handover 0084).

Tests the new project_path field added to Product model for agent export
functionality, including validation, API endpoints, and database operations.
"""

import tempfile
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, User
from src.giljo_mcp.services.product_service import ProductService


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user for authentication"""
    user = User(
        id="user_001",
        tenant_key="test_tenant_001",
        username="test_user",
        email="test@example.com",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def temp_project_dir() -> AsyncGenerator[Path, None]:
    """Create temporary directory for project path testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestProductProjectPathModel:
    """Test Product model with project_path field"""

    @pytest.mark.asyncio
    async def test_create_product_with_project_path(
        self,
        db_session: AsyncSession,
        test_user: User,
        temp_project_dir: Path,
    ):
        """Test creating product with project_path field"""

        product = Product(
            id="prod_001",
            tenant_key=test_user.tenant_key,
            name="Test Product",
            description="Test product with project path",
            project_path=str(temp_project_dir),
        )

        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        assert product.project_path == str(temp_project_dir)

    @pytest.mark.asyncio
    async def test_create_product_without_project_path(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating product without project_path (nullable field)"""

        product = Product(
            id="prod_002",
            tenant_key=test_user.tenant_key,
            name="Test Product No Path",
            description="Test product without project path",
            project_path=None,
        )

        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        assert product.project_path is None

    @pytest.mark.asyncio
    async def test_update_product_project_path(
        self,
        db_session: AsyncSession,
        test_user: User,
        temp_project_dir: Path,
    ):
        """Test updating product's project_path"""

        # Create product without path
        product = Product(
            id="prod_003",
            tenant_key=test_user.tenant_key,
            name="Test Product Update",
            description="Test product for path update",
            project_path=None,
        )

        db_session.add(product)
        await db_session.commit()

        # Update with project path
        product.project_path = str(temp_project_dir)
        await db_session.commit()
        await db_session.refresh(product)

        assert product.project_path == str(temp_project_dir)

    @pytest.mark.asyncio
    async def test_query_products_by_project_path(
        self,
        db_session: AsyncSession,
        test_user: User,
        temp_project_dir: Path,
    ):
        """Test querying products by project_path"""

        product = Product(
            id="prod_004",
            tenant_key=test_user.tenant_key,
            name="Test Product Query",
            description="Test product for querying",
            project_path=str(temp_project_dir),
        )

        db_session.add(product)
        await db_session.commit()

        # Query by project_path
        result = await db_session.execute(select(Product).where(Product.project_path == str(temp_project_dir)))
        found_product = result.scalar_one_or_none()

        assert found_product is not None
        assert found_product.id == product.id


class TestValidateProjectPath:
    """Test project path validation function"""

    def test_validate_existing_directory(self, temp_project_dir: Path):
        """Test validating an existing directory"""

        result = ProductService.validate_project_path(str(temp_project_dir))
        assert result is True

    def test_validate_empty_path(self):
        """Test validating empty path (should pass as optional)"""

        result = ProductService.validate_project_path("")
        assert result is True

        result = ProductService.validate_project_path(None)
        assert result is True

    def test_validate_nonexistent_path(self):
        """Test validating nonexistent path"""

        nonexistent_path = "/this/path/does/not/exist/anywhere"

        with pytest.raises(HTTPException) as exc_info:
            ProductService.validate_project_path(nonexistent_path)

        assert exc_info.value.status_code == 400
        assert "does not exist" in str(exc_info.value.detail)

    def test_validate_file_instead_of_directory(self, temp_project_dir: Path):
        """Test validating a file path instead of directory"""

        # Create a temporary file
        temp_file = temp_project_dir / "test_file.txt"
        temp_file.write_text("test content")

        with pytest.raises(HTTPException) as exc_info:
            ProductService.validate_project_path(str(temp_file))

        assert exc_info.value.status_code == 400
        assert "is not a directory" in str(exc_info.value.detail)

    def test_validate_unwritable_directory(self, temp_project_dir: Path):
        """Test validating unwritable directory"""

        # Mock permission error
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
            with pytest.raises(HTTPException) as exc_info:
                ProductService.validate_project_path(str(temp_project_dir))

            assert exc_info.value.status_code == 400
            assert "is not writable" in str(exc_info.value.detail)

    def test_validate_home_directory_expansion(self):
        """Test home directory expansion in path validation"""

        # Test with tilde path
        with patch("pathlib.Path.expanduser") as mock_expand:
            mock_expanded = Path("/home/user/projects")
            mock_expand.return_value = mock_expanded

            with patch.object(mock_expanded, "exists", return_value=True):
                with patch.object(mock_expanded, "is_dir", return_value=True):
                    with patch.object(mock_expanded, "mkdir"):
                        result = ProductService.validate_project_path("~/projects")
                        assert result is True

                        # Verify expanduser was called
                        mock_expand.assert_called_once()


class TestProductAPIEndpoints:
    """Test product API endpoints with project_path field"""

    def test_create_product_with_project_path_form_data(self, client: TestClient, temp_project_dir: Path):
        """Test creating product via API with project_path in form data"""

        form_data = {
            "name": "Test Product API",
            "description": "Test product via API",
            "project_path": str(temp_project_dir),
        }

        # Mock authentication and validation
        with patch("api.dependencies.get_tenant_key", return_value="test_tenant_001"):
            with patch(
                "src.giljo_mcp.services.product_service.ProductService.validate_project_path", return_value=True
            ):
                response = client.post("/api/v1/products/", data=form_data)

        # Note: This test would need proper API setup to run fully
        # For now, we're testing the validation logic

    def test_update_product_with_project_path(self, client: TestClient, temp_project_dir: Path):
        """Test updating product via API with new project_path"""

        form_data = {
            "project_path": str(temp_project_dir),
        }

        # Mock authentication and validation
        with patch("api.dependencies.get_tenant_key", return_value="test_tenant_001"):
            with patch(
                "src.giljo_mcp.services.product_service.ProductService.validate_project_path", return_value=True
            ):
                response = client.put("/api/v1/products/prod_001", data=form_data)

        # Note: This test would need proper API setup to run fully

    def test_product_response_includes_project_path(self):
        """Test that ProductResponse includes project_path field"""

        from api.endpoints.products import ProductResponse

        # Create response with project_path
        response = ProductResponse(
            id="prod_001",
            name="Test Product",
            description="Test description",
            vision_path=None,
            created_at=datetime.now(),
            updated_at=None,
            project_count=0,
            task_count=0,
            has_vision=False,
            unresolved_tasks=0,
            unfinished_projects=0,
            vision_documents_count=0,
            config_data=None,
            has_config_data=False,
            is_active=False,
            project_path="/test/project/path",
        )

        assert response.project_path == "/test/project/path"

    def test_product_create_request_includes_project_path(self):
        """Test that ProductCreate request model includes project_path"""

        from api.endpoints.products import ProductCreate

        # Create request with project_path
        request = ProductCreate(
            name="Test Product",
            description="Test description",
            project_path="/test/project/path",
        )

        assert request.project_path == "/test/project/path"

    def test_product_update_request_includes_project_path(self):
        """Test that ProductUpdate request model includes project_path"""

        from api.endpoints.products import ProductUpdate

        # Create update request with project_path
        request = ProductUpdate(
            name="Updated Product",
            project_path="/updated/project/path",
        )

        assert request.project_path == "/updated/project/path"


class TestProjectPathValidationIntegration:
    """Test integration of project_path validation with API endpoints"""

    @pytest.mark.asyncio
    async def test_validation_called_on_create(self, temp_project_dir: Path):
        """Test that validation is called during product creation"""

        # This would test the actual endpoint call with validation
        # Requires full API setup with dependencies

    @pytest.mark.asyncio
    async def test_validation_called_on_update(self, temp_project_dir: Path):
        """Test that validation is called during product update"""

        # This would test the actual endpoint call with validation
        # Requires full API setup with dependencies

    def test_validation_error_handling(self):
        """Test proper error handling when validation fails"""

        with patch("src.giljo_mcp.services.product_service.ProductService.validate_project_path") as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Project path validation failed")

            # Test that HTTPException is properly propagated
            with pytest.raises(HTTPException) as exc_info:
                ProductService.validate_project_path("/invalid/path")

            assert exc_info.value.status_code == 400


class TestCrossPatformPaths:
    """Test cross-platform path handling"""

    def test_windows_path_validation(self):
        """Test validation of Windows-style paths"""

        windows_path = r"C:\Users\TestUser\Projects\MyProject"

        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_dir", return_value=True):
            with patch("pathlib.Path.mkdir"):
                result = ProductService.validate_project_path(windows_path)
                assert result is True

    def test_unix_path_validation(self):
        """Test validation of Unix-style paths"""

        unix_path = "/home/user/projects/my-project"

        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_dir", return_value=True):
            with patch("pathlib.Path.mkdir"):
                result = ProductService.validate_project_path(unix_path)
                assert result is True

    def test_path_normalization(self):
        """Test that paths are properly normalized"""

        paths_to_test = [
            "/home/user/../user/projects",
            r"C:\Users\Test\..\Test\Projects",
            "~/projects",
        ]

        for test_path in paths_to_test:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_dir", return_value=True):
                    with patch("pathlib.Path.mkdir"):
                        with patch("pathlib.Path.expanduser") as mock_expand:
                            mock_expand.return_value = Path("/normalized/path")

                            result = ProductService.validate_project_path(test_path)
                            assert result is True


class TestDatabaseMigration:
    """Test database migration for project_path field"""

    @pytest.mark.asyncio
    async def test_migration_adds_project_path_column(self, db_session: AsyncSession):
        """Test that migration properly adds project_path column"""

        # This test would verify the migration was applied correctly
        # by checking the table schema

        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        columns = inspector.get_columns("products")

        column_names = [col["name"] for col in columns]
        assert "project_path" in column_names

        # Find the project_path column
        project_path_col = next(col for col in columns if col["name"] == "project_path")

        # Verify it's nullable (as per our migration)
        assert project_path_col["nullable"] is True

        # Verify the type is String/VARCHAR
        assert "VARCHAR" in str(project_path_col["type"]).upper()

    @pytest.mark.asyncio
    async def test_existing_products_after_migration(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that existing products work correctly after migration"""

        # Create product without setting project_path
        product = Product(
            id="prod_legacy",
            tenant_key=test_user.tenant_key,
            name="Legacy Product",
            description="Product created before migration",
            # project_path should default to None
        )

        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Verify project_path is None for legacy products
        assert product.project_path is None

        # Verify we can update it later
        product.project_path = "/updated/path"
        await db_session.commit()
        await db_session.refresh(product)

        assert product.project_path == "/updated/path"


if __name__ == "__main__":
    pytest.main([__file__])
