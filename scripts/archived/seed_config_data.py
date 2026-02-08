"""
Seed config_data for existing products from project detection.

This script populates Product.config_data for products that don't have it yet,
using automatic detection from CLAUDE.md and project files.

Usage:
    python scripts/seed_config_data.py                  # All products
    python scripts/seed_config_data.py --product-id ID  # Specific product
    python scripts/seed_config_data.py --tenant-key KEY # All products for tenant
    python scripts/seed_config_data.py --dry-run        # Show what would be done
    python scripts/seed_config_data.py --force          # Overwrite existing config_data
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.config_manager import populate_config_data
from src.giljo_mcp.context_manager import validate_config_data
from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import Product


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def seed_products(
    product_id: str = None, tenant_key: str = None, dry_run: bool = False, force: bool = False, root_path: Path = None
) -> Dict[str, Any]:
    """
    Seed config_data for products.

    Args:
        product_id: Optional specific product ID
        tenant_key: Optional filter by tenant
        dry_run: If True, don't write to database
        force: If True, overwrite existing config_data
        root_path: Root path of the project (defaults to CWD)

    Returns:
        Summary dictionary with statistics
    """
    db = get_db_manager()

    if root_path is None:
        root_path = Path.cwd()

    results = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0, "products": []}

    with db.get_session() as session:
        # Build query
        query = session.query(Product)

        if product_id:
            query = query.filter(Product.id == product_id)

        if tenant_key:
            query = query.filter(Product.tenant_key == tenant_key)

        products = query.all()

        logger.info(f"Found {len(products)} product(s) to process")

        for product in products:
            results["processed"] += 1

            product_info = {
                "id": product.id,
                "name": product.name,
                "tenant_key": product.tenant_key,
                "status": "unknown",
            }

            try:
                # Check if already has config_data
                if product.config_data and len(product.config_data) > 0 and not force:
                    logger.info(
                        f"Product '{product.name}' already has config_data ({len(product.config_data)} fields), skipping"
                    )
                    product_info["status"] = "skipped"
                    product_info["reason"] = "already has config_data"
                    product_info["existing_fields"] = list(product.config_data.keys())
                    results["skipped"] += 1
                    results["products"].append(product_info)
                    continue

                # Extract config_data
                logger.info(f"Extracting config_data for product: {product.name}")
                config_data = populate_config_data(product.id, root_path)

                # Validate
                is_valid, errors = validate_config_data(config_data)
                if not is_valid:
                    logger.error(f"Validation failed for {product.name}: {errors}")
                    product_info["status"] = "error"
                    product_info["errors"] = errors
                    results["errors"] += 1
                    results["products"].append(product_info)
                    continue

                # Show before/after
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Product: {product.name} ({product.id})")
                logger.info(f"{'=' * 60}")

                if product.config_data:
                    logger.info(f"BEFORE ({len(product.config_data)} fields):")
                    logger.info(json.dumps(product.config_data, indent=2))
                else:
                    logger.info("BEFORE: (empty)")

                logger.info(f"\nAFTER ({len(config_data)} fields):")
                logger.info(json.dumps(config_data, indent=2))
                logger.info(f"{'=' * 60}\n")

                product_info["config_data"] = config_data
                product_info["field_count"] = len(config_data)

                if not dry_run:
                    # Update product
                    product.config_data = config_data
                    session.commit()
                    logger.info(f"Updated config_data for product: {product.name}")
                    product_info["status"] = "updated"
                    results["updated"] += 1
                else:
                    logger.info(f"[DRY RUN] Would update product: {product.name}")
                    product_info["status"] = "would_update"
                    results["updated"] += 1

                results["products"].append(product_info)

            except Exception as e:
                logger.error(f"Failed to process product {product.name}: {e}", exc_info=True)
                product_info["status"] = "error"
                product_info["error"] = str(e)
                results["errors"] += 1
                results["products"].append(product_info)

    return results


def print_summary(results: Dict[str, Any]):
    """Print a summary of the seeding operation."""
    print("\n" + "=" * 60)
    print("CONFIG DATA SEEDING SUMMARY")
    print("=" * 60)
    print(f"Products processed: {results['processed']}")
    print(f"Products updated:   {results['updated']}")
    print(f"Products skipped:   {results['skipped']}")
    print(f"Errors:             {results['errors']}")
    print("=" * 60)

    if results["products"]:
        print("\nProduct Details:")
        for product in results["products"]:
            status_emoji = {
                "updated": "[OK]",
                "would_update": "[OK - DRY RUN]",
                "skipped": "[SKIP]",
                "error": "[ERROR]",
            }.get(product["status"], "[?]")

            print(f"\n  {status_emoji} {product['name']} ({product['id'][:8]}...)")
            print(f"      Status: {product['status']}")

            if product["status"] in ("updated", "would_update"):
                print(f"      Fields: {product.get('field_count', 0)}")
            elif product["status"] == "skipped":
                print(f"      Reason: {product.get('reason', 'unknown')}")
                if "existing_fields" in product:
                    print(f"      Existing: {', '.join(product['existing_fields'][:5])}")
            elif product["status"] == "error":
                if "errors" in product:
                    print("      Validation errors:")
                    for err in product["errors"]:
                        print(f"        - {err}")
                if "error" in product:
                    print(f"      Error: {product['error']}")

    print("\n" + "=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed config_data for products from project detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Seed all products
  python scripts/seed_config_data.py

  # Seed specific product
  python scripts/seed_config_data.py --product-id abc123

  # Seed all products for a tenant
  python scripts/seed_config_data.py --tenant-key my-tenant

  # Dry run (show what would be done)
  python scripts/seed_config_data.py --dry-run

  # Force overwrite existing config_data
  python scripts/seed_config_data.py --force

  # Use custom project root
  python scripts/seed_config_data.py --root /path/to/project
        """,
    )

    parser.add_argument("--product-id", help="Specific product ID to process")
    parser.add_argument("--tenant-key", help="Filter products by tenant key")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing to database")
    parser.add_argument("--force", action="store_true", help="Overwrite existing config_data")
    parser.add_argument("--root", type=Path, help="Project root path (defaults to current directory)")
    parser.add_argument("--all", action="store_true", help="Process all products (default behavior)")

    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes will be made\n")

    if args.force:
        logger.info("FORCE MODE - Will overwrite existing config_data\n")

    # Execute seeding
    results = seed_products(
        product_id=args.product_id,
        tenant_key=args.tenant_key,
        dry_run=args.dry_run,
        force=args.force,
        root_path=args.root,
    )

    # Print summary
    print_summary(results)

    # Exit code based on errors
    if results["errors"] > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
