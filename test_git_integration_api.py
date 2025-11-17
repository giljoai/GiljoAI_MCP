"""
Quick test script for Git Integration API endpoints (Handover 013B)
Tests GET and POST /api/v1/products/{product_id}/git-integration
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.models import Product


async def test_git_integration():
    """Test git integration API endpoints"""

    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.init()

    try:
        # Get active product
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Product).where(Product.is_active == True)
            )
            product = result.scalar_one_or_none()

            if not product:
                print("❌ No active product found")
                return

            print(f"✓ Found active product: {product.name} (ID: {product.id})")

        # Initialize ProductService
        service = ProductService(
            db_manager=db_manager,
            tenant_key=product.tenant_key
        )

        # Test 1: Get git integration settings (should return defaults)
        print("\n[TEST 1] GET git integration settings...")
        result = await service.get_product(str(product.id), include_metrics=False)
        if result["success"]:
            product_data = result["product"]
            git_settings = product_data.get("product_memory", {}).get("git_integration", {})
            print(f"✓ Current settings: {git_settings}")
        else:
            print(f"❌ Failed to get product: {result['error']}")
            return

        # Test 2: Enable git integration
        print("\n[TEST 2] POST enable git integration...")
        result = await service.update_git_integration(
            product_id=str(product.id),
            enabled=True,
            commit_limit=25,
            default_branch="develop"
        )
        if result["success"]:
            print(f"✓ Enabled git integration: {result['settings']}")
        else:
            print(f"❌ Failed to enable: {result['error']}")
            return

        # Test 3: Verify settings persisted
        print("\n[TEST 3] GET verify settings persisted...")
        result = await service.get_product(str(product.id), include_metrics=False)
        if result["success"]:
            product_data = result["product"]
            git_settings = product_data.get("product_memory", {}).get("git_integration", {})
            assert git_settings["enabled"] == True, "enabled should be True"
            assert git_settings["commit_limit"] == 25, "commit_limit should be 25"
            assert git_settings["default_branch"] == "develop", "default_branch should be develop"
            print(f"✓ Settings verified: {git_settings}")
        else:
            print(f"❌ Failed to verify: {result['error']}")
            return

        # Test 4: Disable git integration
        print("\n[TEST 4] POST disable git integration...")
        result = await service.update_git_integration(
            product_id=str(product.id),
            enabled=False
        )
        if result["success"]:
            print(f"✓ Disabled git integration: {result['settings']}")
            assert result["settings"]["enabled"] == False, "enabled should be False"
        else:
            print(f"❌ Failed to disable: {result['error']}")
            return

        print("\n✅ All tests passed!")

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(test_git_integration())
