"""
Tests for GitHub Integration Toggle Persistence - Handover 0269

Tests for GitHub integration toggle persistence functionality:
1. Toggle persists to Product.product_memory
2. Toggle state survives page refresh
3. Multi-tenant isolation maintained
4. Edge cases for branch names and commit limits

Handover 0269: Fix GitHub integration toggle persistence
"""

from unittest.mock import MagicMock, patch

import pytest

from src.giljo_mcp.models import Product
from src.giljo_mcp.services.git_service import GitService
from src.giljo_mcp.services.product_service import ProductService


# ============================================================================
# Unit Tests - ProductService.update_github_integration
# ============================================================================


@pytest.mark.asyncio
async def test_github_toggle_persists_to_database(db_session, test_user):
    """
    Test that GitHub integration toggle persists to Product.product_memory

    Scenario:
    1. Create a product with project_path
    2. Enable GitHub integration via ProductService
    3. Verify product_memory.git_integration.enabled = True
    """
    product = Product(
        tenant_key=test_user.tenant_key,
        name="Test Product",
        description="Test",
        project_path="/path/to/project",
    )
    db_session.add(product)
    await db_session.flush()
    product_id = product.id

    service = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    # Enable GitHub integration
    result = await service.update_git_integration(
        product_id=product_id,
        enabled=True,
        commit_limit=20,
        default_branch="main",
    )

    # Assertions
    assert result["success"] is True
    assert result["settings"]["enabled"] is True
    assert result["settings"]["commit_limit"] == 20
    assert result["settings"]["default_branch"] == "main"

    # Refresh product from database and verify persistence
    await db_session.refresh(product)
    if product.product_memory is None:
        product.product_memory = {}

    assert "git_integration" in product.product_memory
    assert product.product_memory["git_integration"]["enabled"] is True
    assert product.product_memory["git_integration"]["commit_limit"] == 20
    assert product.product_memory["git_integration"]["default_branch"] == "main"


@pytest.mark.asyncio
async def test_github_toggle_disable_clears_config(db_session, test_user):
    """
    Test that disabling GitHub integration clears detailed config

    Scenario:
    1. Enable GitHub integration with full config
    2. Disable it
    3. Verify only enabled=False remains
    """
    product = Product(
        tenant_key=test_user.tenant_key,
        name="Test Product",
        description="Test",
        project_path="/path/to/project",
    )
    db_session.add(product)
    await db_session.flush()
    product_id = product.id

    service = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    # Enable
    await service.update_git_integration(
        product_id=product_id,
        enabled=True,
        commit_limit=50,
        default_branch="staging",
    )

    # Disable
    result = await service.update_git_integration(
        product_id=product_id,
        enabled=False,
    )

    assert result["success"] is True
    assert result["settings"]["enabled"] is False

    # Detailed config should be cleared
    await db_session.refresh(product)
    if product.product_memory is None:
        product.product_memory = {}

    git_config = product.product_memory.get("git_integration", {})
    assert git_config.get("commit_limit") is None
    assert git_config.get("default_branch") is None


@pytest.mark.asyncio
async def test_get_product_includes_git_integration(db_session, test_user):
    """
    Test that get_product returns current git_integration state

    Scenario:
    1. Create product without GitHub enabled
    2. Verify get_product returns correct git_integration state
    """
    product = Product(
        tenant_key=test_user.tenant_key,
        name="Test Product 1",
        description="Test",
    )
    db_session.add(product)
    await db_session.flush()

    service = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    # Check disabled state
    result = await service.get_product(product.id)
    assert result["success"] is True
    git_config = result["product"]["product_memory"].get("git_integration", {})
    assert git_config.get("enabled", False) is False


# ============================================================================
# Unit Tests - GitService
# ============================================================================


@pytest.mark.asyncio
async def test_git_service_parses_git_log_correctly():
    """
    Test GitService parses git log output correctly

    Scenario:
    1. Provide raw git log output
    2. Parse and verify all fields extracted correctly
    """
    service = GitService()

    log_output = """abc123|John Doe|john@example.com|2025-11-29T10:00:00Z|First commit
def456|Jane Smith|jane@example.com|2025-11-28T15:30:00Z|Second commit with special chars: @#$%
"""

    commits = service._parse_git_log(log_output)

    assert len(commits) == 2
    assert commits[0]["sha"] == "abc123"
    assert commits[0]["author"] == "John Doe"
    assert commits[0]["email"] == "john@example.com"
    assert commits[0]["timestamp"] == "2025-11-29T10:00:00Z"
    assert commits[0]["message"] == "First commit"
    assert commits[1]["message"] == "Second commit with special chars: @#$%"


@pytest.mark.asyncio
async def test_git_service_parses_empty_log():
    """Test GitService handles empty git log gracefully"""
    service = GitService()
    commits = service._parse_git_log("")
    assert commits == []

    commits = service._parse_git_log("\n\n")
    assert commits == []


@pytest.mark.asyncio
async def test_git_service_parses_malformed_log():
    """Test GitService skips malformed lines"""
    service = GitService()

    log_output = """abc123|John Doe|john@example.com|2025-11-29T10:00:00Z|First commit
invalid_line_without_pipes
def456|Jane Smith|jane@example.com|2025-11-28T15:30:00Z|Second commit
"""

    commits = service._parse_git_log(log_output)

    # Should have parsed 2 valid commits, skipped 1 malformed
    assert len(commits) == 2
    assert commits[0]["sha"] == "abc123"
    assert commits[1]["sha"] == "def456"


@pytest.mark.asyncio
async def test_git_service_handles_missing_path():
    """
    Test GitService handles missing path gracefully

    Scenario:
    1. Call with non-existent path
    2. Verify error handled
    """
    service = GitService()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("Path not found")
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            result = await service.validate_repository("/nonexistent/path")
            assert result is False


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.asyncio
async def test_github_toggle_with_special_branch_names(db_session, test_user):
    """
    Test GitHub toggle works with various branch name formats

    Scenario:
    1. Test with branch names: main, master, develop, feature/new-feature, etc.
    2. Verify all persist correctly
    """
    product = Product(
        tenant_key=test_user.tenant_key,
        name="Test Product",
        description="Test",
        project_path="/path/to/project",
    )
    db_session.add(product)
    await db_session.flush()
    product_id = product.id

    service = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    branch_names = ["main", "master", "develop", "feature/new-feature", "release-v1.0"]

    for branch in branch_names:
        result = await service.update_git_integration(
            product_id=product_id,
            enabled=True,
            commit_limit=20,
            default_branch=branch,
        )
        assert result["success"] is True
        assert result["settings"]["default_branch"] == branch


@pytest.mark.asyncio
async def test_github_toggle_boundary_commit_limits(db_session, test_user):
    """
    Test GitHub toggle with boundary commit limit values

    Scenario:
    1. Test with commit_limit: 1, 50, 100
    2. Verify all persist correctly
    """
    product = Product(
        tenant_key=test_user.tenant_key,
        name="Test Product",
        description="Test",
        project_path="/path/to/project",
    )
    db_session.add(product)
    await db_session.flush()
    product_id = product.id

    service = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    limits = [1, 50, 100]

    for limit in limits:
        result = await service.update_git_integration(
            product_id=product_id,
            enabled=True,
            commit_limit=limit,
        )
        assert result["success"] is True
        assert result["settings"]["commit_limit"] == limit


@pytest.mark.asyncio
async def test_github_toggle_multi_tenant_isolation(db_session, test_user):
    """
    Test that GitHub toggle respects multi-tenant isolation

    Scenario:
    1. Create products for different tenants
    2. Enable GitHub for tenant 1
    3. Verify tenant 2 cannot access tenant 1's product
    """
    # Create product for tenant 1
    product1 = Product(
        tenant_key=test_user.tenant_key,
        name="Product 1",
        description="Test",
        project_path="/path/to/project",
    )
    db_session.add(product1)
    await db_session.flush()

    # Service for tenant 1 - should work
    service1 = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    result = await service1.update_git_integration(
        product_id=product1.id,
        enabled=True,
    )
    assert result["success"] is True

    # Service for different tenant - should fail
    service2 = ProductService(
        db_manager=MagicMock(),
        tenant_key="different_tenant_key",
        test_session=db_session,
    )

    result = await service2.update_git_integration(
        product_id=product1.id,
        enabled=False,
    )
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_github_toggle_product_not_found(db_session, test_user):
    """
    Test that update fails gracefully when product doesn't exist

    Scenario:
    1. Try to update non-existent product
    2. Verify error returned
    """
    service = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    result = await service.update_git_integration(
        product_id="nonexistent-product-id",
        enabled=True,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_github_toggle_re_enable_after_disable(db_session, test_user):
    """
    Test that GitHub toggle can be re-enabled after being disabled

    Scenario:
    1. Enable GitHub integration
    2. Disable it
    3. Re-enable it with new settings
    4. Verify new settings are used
    """
    product = Product(
        tenant_key=test_user.tenant_key,
        name="Test Product",
        description="Test",
        project_path="/path/to/project",
    )
    db_session.add(product)
    await db_session.flush()
    product_id = product.id

    service = ProductService(
        db_manager=MagicMock(),
        tenant_key=test_user.tenant_key,
        test_session=db_session,
    )

    # Enable
    result1 = await service.update_git_integration(
        product_id=product_id,
        enabled=True,
        commit_limit=20,
        default_branch="main",
    )
    assert result1["success"] is True

    # Disable
    result2 = await service.update_git_integration(
        product_id=product_id,
        enabled=False,
    )
    assert result2["success"] is True

    # Re-enable with different settings
    result3 = await service.update_git_integration(
        product_id=product_id,
        enabled=True,
        commit_limit=50,
        default_branch="develop",
    )
    assert result3["success"] is True
    assert result3["settings"]["commit_limit"] == 50
    assert result3["settings"]["default_branch"] == "develop"
