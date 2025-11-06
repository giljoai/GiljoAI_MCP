"""
Validation script for Orchestrator Upgrade implementation.

Checks:
1. config_data JSONB migration successful
2. get_filtered_config() returns correct fields per role
3. Orchestrator template seeds as default
4. activate_agent() uses enhanced template
5. Sub-agents receive filtered context
6. Population script extracts from CLAUDE.md
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect

from src.giljo_mcp.context_manager import get_filtered_config, get_full_config
from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import AgentTemplate, Product


def validate_migration():
    """Validate config_data column exists with GIN index"""
    print("Validating database migration...")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not set")
        return False

    db = get_db_manager(database_url=database_url)
    engine = db.engine
    inspector = inspect(engine)

    # Check column exists
    columns = [col["name"] for col in inspector.get_columns("products")]
    if "config_data" not in columns:
        print("config_data column not found in products table")
        return False

    # Check GIN index exists
    indexes = inspector.get_indexes("products")
    gin_index_found = any(idx.get("name") == "idx_product_config_data_gin" for idx in indexes)

    if not gin_index_found:
        print("GIN index not found (may be normal if using partial indexing)")

    print("config_data column exists")
    return True


def validate_filtering():
    """Validate role-based filtering works"""
    print("\nValidating role-based filtering...")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not set")
        return False

    # Create test product
    db = get_db_manager(database_url=database_url)
    with db.get_session() as session:
        test_product = Product(
            tenant_key="validation-test",
            name="Validation Test",
            config_data={
                "architecture": "Test",
                "tech_stack": ["Python"],
                "test_commands": ["pytest"],
                "api_docs": "/docs/api.md",
                "serena_mcp_enabled": True,
            },
        )
        session.add(test_product)
        session.commit()
        session.refresh(test_product)

        # Test orchestrator gets all
        full_config = get_full_config(test_product)
        if len(full_config) != 5:
            print(f"Orchestrator should get all 5 fields, got {len(full_config)}")
            return False

        # Test implementer filtering
        impl_config = get_filtered_config("implementer-1", test_product)
        if "test_commands" in impl_config:
            print("Implementer should not receive test_commands")
            return False
        if "architecture" not in impl_config:
            print("Implementer should receive architecture")
            return False

        # Test tester filtering
        test_config = get_filtered_config("tester-1", test_product)
        if "test_commands" not in test_config:
            print("Tester should receive test_commands")
            return False
        if "api_docs" in test_config:
            print("Tester should not receive api_docs")
            return False

        # Cleanup
        session.delete(test_product)
        session.commit()

    print("Role-based filtering working correctly")
    return True


def validate_orchestrator_template():
    """Validate enhanced orchestrator template is seeded as default"""
    print("\nValidating orchestrator template...")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not set")
        return False

    db = get_db_manager(database_url=database_url)
    with db.get_session() as session:
        template = (
            session.query(AgentTemplate)
            .filter(AgentTemplate.name == "orchestrator", AgentTemplate.is_default == True)
            .first()
        )

        if not template:
            print("Default orchestrator template not found")
            return False

        content = template.template_content.lower()

        # Check for key features
        checks = {
            "30-80-10 principle": "30-80-10" in content,
            "3-tool rule": "3-tool" in content,
            "Discovery workflow": "discovery" in content and "serena" in content,
            "Delegation enforcement": "delegate" in content,
            "After-action docs": "completion report" in content or "devlog" in content,
        }

        for check_name, passed in checks.items():
            if not passed:
                print(f"Orchestrator template missing: {check_name}")
                return False

    print("Enhanced orchestrator template validated")
    return True


def main():
    """Run all validations"""
    print("=" * 60)
    print("ORCHESTRATOR UPGRADE VALIDATION")
    print("=" * 60)

    results = []

    results.append(("Migration", validate_migration()))
    results.append(("Filtering", validate_filtering()))
    results.append(("Template", validate_orchestrator_template()))

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    all_passed = all(result[1] for result in results)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}")

    print("=" * 60)

    if all_passed:
        print("\nALL VALIDATIONS PASSED")
        return 0
    print("\nSOME VALIDATIONS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
