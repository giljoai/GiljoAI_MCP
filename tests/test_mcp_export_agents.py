"""
Test suite for MCP export_agents command functionality (Handover 0084).

Tests the new copy-command interface for agent template export that solves
path resolution issues with the previous web-based approach.
"""

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate, Product, User
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.claude_export import (
    export_agents_command,
    get_product_for_tenant,
    validate_product_path,
)
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


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
async def test_product(db_session: AsyncSession, test_user: User) -> Product:
    """Create test product with project_path"""
    product = Product(
        id="prod_001",
        tenant_key=test_user.tenant_key,
        name="Test Product",
        description="Test product for export",
        project_path="/tmp/test_project",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_templates(db_session: AsyncSession, test_user: User, test_product: Product) -> list[AgentTemplate]:
    """Create test agent templates"""
    templates = [
        AgentTemplate(
            id="tmpl_orchestrator_001",
            tenant_key=test_user.tenant_key,
            product_id=test_product.id,
            name="orchestrator",
            category="role",
            role="orchestrator",
            system_instructions="You are the Orchestrator agent.",
            behavioral_rules=["Coordinate tasks", "Monitor progress"],
            success_criteria=["All tasks completed successfully"],
            is_active=True,
        ),
        AgentTemplate(
            id="tmpl_coder_001",
            tenant_key=test_user.tenant_key,
            product_id=test_product.id,
            name="coder",
            category="role",
            role="coder",
            system_instructions="You are the Coder agent.",
            behavioral_rules=["Write clean code", "Follow best practices"],
            success_criteria=["Code passes all tests"],
            is_active=True,
        ),
    ]

    for template in templates:
        db_session.add(template)

    await db_session.commit()

    for template in templates:
        await db_session.refresh(template)

    return templates


@pytest_asyncio.fixture
async def temp_export_dir() -> AsyncGenerator[Path, None]:
    """Create temporary directory for export testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / ".claude" / "agents"
        export_path.mkdir(parents=True, exist_ok=True)
        yield export_path


@pytest_asyncio.fixture
async def mock_db_manager(db_session: AsyncSession) -> DatabaseManager:
    """Create mock database manager"""
    db_manager = MagicMock()
    db_manager.get_tenant_session_async = AsyncMock()
    db_manager.get_tenant_session_async.return_value.__aenter__ = AsyncMock(return_value=db_session)
    db_manager.get_tenant_session_async.return_value.__aexit__ = AsyncMock(return_value=None)
    return db_manager


@pytest_asyncio.fixture
async def mock_tenant_manager() -> TenantManager:
    """Create mock tenant manager"""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = "test_tenant_001"
    return tenant_manager


@pytest_asyncio.fixture
async def tool_accessor(mock_db_manager: DatabaseManager, mock_tenant_manager: TenantManager) -> ToolAccessor:
    """Create ToolAccessor with mocked dependencies"""
    return ToolAccessor(mock_db_manager, mock_tenant_manager)


class TestExportAgentsCommand:
    """Test the core export_agents_command functionality"""

    @pytest.mark.asyncio
    async def test_export_agents_personal_directory(
        self,
        mock_db_manager: DatabaseManager,
        test_user: User,
        test_templates: list[AgentTemplate],
        temp_export_dir: Path,
    ):
        """Test exporting agents to personal ~/.claude/agents directory"""

        # Mock the personal directory path
        personal_path = temp_export_dir.parent.parent / ".claude" / "agents"
        personal_path.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = temp_export_dir.parent.parent

            with patch("api.endpoints.claude_export.export_templates_to_claude_code") as mock_export:
                mock_export.return_value = {
                    "success": True,
                    "exported_count": 2,
                    "files": [
                        {"name": "orchestrator", "path": str(personal_path / "orchestrator.md")},
                        {"name": "coder", "path": str(personal_path / "coder.md")},
                    ],
                    "message": "Successfully exported 2 template(s)",
                }

                result = await export_agents_command(
                    db_manager=mock_db_manager,
                    tenant_key=test_user.tenant_key,
                    personal=True,
                )

                assert result["success"] is True
                assert result["exported_count"] == 2
                assert len(result["files"]) == 2

                # Verify export function was called with correct path
                mock_export.assert_called_once()
                call_args = mock_export.call_args
                assert str(personal_path) in call_args.kwargs["export_path"]

    @pytest.mark.asyncio
    async def test_export_agents_product_directory(
        self,
        mock_db_manager: DatabaseManager,
        test_user: User,
        test_templates: list[AgentTemplate],
        temp_export_dir: Path,
    ):
        """Test exporting agents to product-specific directory"""

        product_path = str(temp_export_dir)

        with patch("api.endpoints.claude_export.export_templates_to_claude_code") as mock_export:
            mock_export.return_value = {
                "success": True,
                "exported_count": 2,
                "files": [
                    {"name": "orchestrator", "path": f"{product_path}/orchestrator.md"},
                    {"name": "coder", "path": f"{product_path}/coder.md"},
                ],
                "message": "Successfully exported 2 template(s)",
            }

            result = await export_agents_command(
                db_manager=mock_db_manager,
                tenant_key=test_user.tenant_key,
                product_path=product_path,
            )

            assert result["success"] is True
            assert result["exported_count"] == 2

            # Verify export function was called with correct path
            mock_export.assert_called_once()
            call_args = mock_export.call_args
            assert call_args.kwargs["export_path"] == product_path

    @pytest.mark.asyncio
    async def test_export_agents_missing_parameters(
        self,
        mock_db_manager: DatabaseManager,
        test_user: User,
    ):
        """Test error when neither product_path nor personal is specified"""

        result = await export_agents_command(
            db_manager=mock_db_manager,
            tenant_key=test_user.tenant_key,
            product_path=None,
            personal=False,
        )

        assert result["success"] is False
        assert "Must specify either --product-path or --personal" in result["error"]

    @pytest.mark.asyncio
    async def test_export_agents_user_not_found(
        self,
        mock_db_manager: DatabaseManager,
        temp_export_dir: Path,
    ):
        """Test error when user is not found"""

        # Mock empty user query result
        empty_session = MagicMock()
        empty_session.execute = AsyncMock()
        empty_session.execute.return_value.scalar_one_or_none.return_value = None

        mock_db_manager.get_tenant_session_async.return_value.__aenter__ = AsyncMock(return_value=empty_session)

        result = await export_agents_command(
            db_manager=mock_db_manager,
            tenant_key="nonexistent_tenant",
            personal=True,
        )

        assert result["success"] is False
        assert "User not found for tenant" in result["error"]


class TestGetProductForTenant:
    """Test the get_product_for_tenant helper function"""

    @pytest.mark.asyncio
    async def test_get_active_product(
        self,
        mock_db_manager: DatabaseManager,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test getting active product for tenant"""

        result = await get_product_for_tenant(
            mock_db_manager,
            test_product.tenant_key,
        )

        assert result is not None
        assert result.id == test_product.id
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_get_specific_product(
        self,
        mock_db_manager: DatabaseManager,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test getting specific product by ID"""

        result = await get_product_for_tenant(
            mock_db_manager,
            test_product.tenant_key,
            test_product.id,
        )

        assert result is not None
        assert result.id == test_product.id

    @pytest.mark.asyncio
    async def test_get_product_not_found(
        self,
        mock_db_manager: DatabaseManager,
        db_session: AsyncSession,
    ):
        """Test when no product is found"""

        # Mock empty query result
        empty_session = MagicMock()
        empty_session.execute = AsyncMock()
        empty_session.execute.return_value.scalar_one_or_none.return_value = None

        mock_db_manager.get_tenant_session_async.return_value.__aenter__ = AsyncMock(return_value=empty_session)

        result = await get_product_for_tenant(
            mock_db_manager,
            "nonexistent_tenant",
        )

        assert result is None


class TestValidateProductPath:
    """Test the validate_product_path helper function"""

    @pytest.mark.asyncio
    async def test_validate_existing_directory(
        self,
        mock_db_manager: DatabaseManager,
        db_session: AsyncSession,
        test_product: Product,
        temp_export_dir: Path,
    ):
        """Test validating an existing writable directory"""

        test_path = str(temp_export_dir.parent)

        result = await validate_product_path(
            mock_db_manager,
            test_product.tenant_key,
            test_product.id,
            test_path,
        )

        assert result["success"] is True
        assert result["project_path"] == test_path

    @pytest.mark.asyncio
    async def test_validate_nonexistent_path(
        self,
        mock_db_manager: DatabaseManager,
        db_session: AsyncSession,
        test_product: Product,
    ):
        """Test validating a nonexistent path"""

        nonexistent_path = "/nonexistent/path/that/does/not/exist"

        result = await validate_product_path(
            mock_db_manager,
            test_product.tenant_key,
            test_product.id,
            nonexistent_path,
        )

        assert result["success"] is False
        assert "Path does not exist" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_file_instead_of_directory(
        self,
        mock_db_manager: DatabaseManager,
        db_session: AsyncSession,
        test_product: Product,
        temp_export_dir: Path,
    ):
        """Test validating a file path instead of directory"""

        # Create a temporary file
        temp_file = temp_export_dir.parent / "test_file.txt"
        temp_file.write_text("test content")

        result = await validate_product_path(
            mock_db_manager,
            test_product.tenant_key,
            test_product.id,
            str(temp_file),
        )

        assert result["success"] is False
        assert "is not a directory" in result["error"]


class TestToolAccessorExportMethods:
    """Test the ToolAccessor export_agents and related methods"""

    @pytest.mark.asyncio
    async def test_export_agents_with_product_path(
        self,
        tool_accessor: ToolAccessor,
        test_product: Product,
        temp_export_dir: Path,
    ):
        """Test ToolAccessor export_agents method with product path"""

        with patch("src.giljo_mcp.tools.claude_export.export_agents_command") as mock_export:
            mock_export.return_value = {
                "success": True,
                "exported_count": 2,
                "files": [],
                "message": "Export successful",
            }

            result = await tool_accessor.export_agents(
                product_path=str(temp_export_dir),
            )

            assert result["success"] is True
            assert result["exported_count"] == 2

            # Verify the command was called with correct parameters
            mock_export.assert_called_once()
            call_args = mock_export.call_args
            assert call_args.kwargs["product_path"] == str(temp_export_dir)

    @pytest.mark.asyncio
    async def test_export_agents_personal(
        self,
        tool_accessor: ToolAccessor,
    ):
        """Test ToolAccessor export_agents method for personal directory"""

        with patch("src.giljo_mcp.tools.claude_export.export_agents_command") as mock_export:
            mock_export.return_value = {
                "success": True,
                "exported_count": 1,
                "files": [],
                "message": "Export successful",
            }

            result = await tool_accessor.export_agents(personal=True)

            assert result["success"] is True
            assert result["exported_count"] == 1

            # Verify the command was called with personal=True
            mock_export.assert_called_once()
            call_args = mock_export.call_args
            assert call_args.kwargs["personal"] is True

    @pytest.mark.asyncio
    async def test_export_agents_auto_detect_product_path(
        self,
        tool_accessor: ToolAccessor,
        mock_db_manager: DatabaseManager,
        test_product: Product,
    ):
        """Test auto-detecting product path from active product"""

        # Mock getting product with project_path
        mock_product = MagicMock()
        mock_product.project_path = "/test/project/path"

        with patch("src.giljo_mcp.tools.claude_export.get_product_for_tenant") as mock_get_product:
            mock_get_product.return_value = mock_product

            with patch("src.giljo_mcp.tools.claude_export.export_agents_command") as mock_export:
                mock_export.return_value = {
                    "success": True,
                    "exported_count": 2,
                    "files": [],
                    "message": "Export successful",
                }

                result = await tool_accessor.export_agents()

                assert result["success"] is True

                # Verify the command was called with auto-detected path
                mock_export.assert_called_once()
                call_args = mock_export.call_args
                expected_path = "/test/project/path/.claude/agents"
                assert call_args.kwargs["product_path"] == expected_path

    @pytest.mark.asyncio
    async def test_set_product_path(
        self,
        tool_accessor: ToolAccessor,
        temp_export_dir: Path,
    ):
        """Test setting product path via ToolAccessor"""

        with patch("src.giljo_mcp.tools.claude_export.validate_product_path") as mock_validate:
            mock_validate.return_value = {
                "success": True,
                "product_id": "prod_001",
                "project_path": str(temp_export_dir.parent),
                "message": "Product path updated successfully",
            }

            result = await tool_accessor.set_product_path(
                project_path=str(temp_export_dir.parent),
            )

            assert result["success"] is True
            assert result["project_path"] == str(temp_export_dir.parent)

    @pytest.mark.asyncio
    async def test_get_product_path(
        self,
        tool_accessor: ToolAccessor,
        test_product: Product,
    ):
        """Test getting product path via ToolAccessor"""

        with patch("src.giljo_mcp.tools.claude_export.get_product_for_tenant") as mock_get_product:
            mock_get_product.return_value = test_product

            result = await tool_accessor.get_product_path()

            assert result["success"] is True
            assert result["project_path"] == test_product.project_path
            assert result["has_path"] is True

    @pytest.mark.asyncio
    async def test_export_agents_no_tenant_context(
        self,
        tool_accessor: ToolAccessor,
    ):
        """Test error when no tenant context is available"""

        # Mock no tenant available
        tool_accessor.tenant_manager.get_current_tenant.return_value = None

        result = await tool_accessor.export_agents(personal=True)

        assert result["success"] is False
        assert "No tenant context available" in result["error"]


class TestCrossPatformCompatibility:
    """Test cross-platform path handling"""

    @pytest.mark.asyncio
    async def test_windows_path_handling(
        self,
        mock_db_manager: DatabaseManager,
        test_user: User,
        temp_export_dir: Path,
    ):
        """Test handling Windows-style paths"""

        # Test with Windows-style path
        windows_path = r"C:\Users\TestUser\Projects\MyProject\.claude\agents"

        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_dir", return_value=True):
            with patch("pathlib.Path.mkdir"):
                with patch("api.endpoints.claude_export.export_templates_to_claude_code") as mock_export:
                    mock_export.return_value = {
                        "success": True,
                        "exported_count": 1,
                        "files": [],
                        "message": "Export successful",
                    }

                    result = await export_agents_command(
                        db_manager=mock_db_manager,
                        tenant_key=test_user.tenant_key,
                        product_path=windows_path,
                    )

                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unix_path_handling(
        self,
        mock_db_manager: DatabaseManager,
        test_user: User,
        temp_export_dir: Path,
    ):
        """Test handling Unix-style paths"""

        # Test with Unix-style path
        unix_path = "/home/user/projects/my-project/.claude/agents"

        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.is_dir", return_value=True):
            with patch("pathlib.Path.mkdir"):
                with patch("api.endpoints.claude_export.export_templates_to_claude_code") as mock_export:
                    mock_export.return_value = {
                        "success": True,
                        "exported_count": 1,
                        "files": [],
                        "message": "Export successful",
                    }

                    result = await export_agents_command(
                        db_manager=mock_db_manager,
                        tenant_key=test_user.tenant_key,
                        product_path=unix_path,
                    )

                    assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__])
