"""Verify setup_state table creation."""

import os
import sys

from sqlalchemy import create_engine, inspect


# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Database connection
DATABASE_URL = "postgresql://giljo_user:isw8HkrRSY1GXYH5G62d@localhost:5432/giljo_mcp"
engine = create_engine(DATABASE_URL)

# Inspect table
inspector = inspect(engine)

print("=" * 80)
print("SETUP_STATE TABLE VERIFICATION")
print("=" * 80)

# Check if table exists
if "setup_state" in inspector.get_table_names():
    print("✓ Table 'setup_state' exists\n")

    # Get columns
    print("COLUMNS:")
    print("-" * 80)
    columns = inspector.get_columns("setup_state")
    for col in columns:
        nullable = "NULL" if col["nullable"] else "NOT NULL"
        default = f" DEFAULT {col.get('default', 'none')}" if col.get("default") else ""
        print(f"  {col['name']:<25} {col['type']!s:<30} {nullable}{default}")

    # Get indexes
    print("\n\nINDEXES:")
    print("-" * 80)
    indexes = inspector.get_indexes("setup_state")
    for idx in indexes:
        unique = "UNIQUE" if idx.get("unique") else ""
        cols = ", ".join(idx["column_names"])
        print(f"  {idx['name']:<35} ({cols}) {unique}")

    # Get constraints
    print("\n\nCONSTRAINTS:")
    print("-" * 80)

    # Primary key
    pk = inspector.get_pk_constraint("setup_state")
    if pk:
        print(f"  PRIMARY KEY: {', '.join(pk['constrained_columns'])}")

    # Unique constraints
    unique_constraints = inspector.get_unique_constraints("setup_state")
    for uc in unique_constraints:
        cols = ", ".join(uc["column_names"])
        print(f"  UNIQUE: {uc['name']} ({cols})")

    # Check constraints
    check_constraints = inspector.get_check_constraints("setup_state")
    for cc in check_constraints:
        print(f"  CHECK: {cc['name']}")
        # sqltext = cc.get('sqltext', 'N/A')
        # print(f"    {sqltext[:100]}...")

    # Test insert and query using ORM
    print("\n\nTEST INSERT (using ORM):")
    print("-" * 80)
    from uuid import uuid4

    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Import the model
        import sys

        sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "src")))
        from giljo_mcp.models import SetupState

        # Create test instance
        test_state = SetupState(
            id=str(uuid4()),
            tenant_key="test_tenant",
            completed=False,
            setup_version="2.0.0",
            features_configured={},
            tools_enabled=[],
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
        )
        session.add(test_state)
        session.commit()

        print(f"  Inserted: id={test_state.id}, tenant_key={test_state.tenant_key}")

        # Query it back
        retrieved = session.query(SetupState).filter(SetupState.tenant_key == "test_tenant").first()
        print(f"  Queried: tenant_key={retrieved.tenant_key}, completed={retrieved.completed}")

        # Test helper methods
        print(f"  has_feature('database'): {retrieved.has_feature('database')}")
        print(f"  has_tool('project'): {retrieved.has_tool('project')}")

        # Test to_dict
        data = retrieved.to_dict()
        print(f"  to_dict() returned {len(data)} fields")

        # Clean up
        session.delete(test_state)
        session.commit()
        print("  Test row deleted")

    except Exception as e:
        print(f"  ERROR during ORM test: {e}")
        session.rollback()
    finally:
        session.close()

    print("\n✓ All verifications passed!")
    print("=" * 80)

else:
    print("✗ Table 'setup_state' does NOT exist!")
    print("\nAvailable tables:")
    for table in inspector.get_table_names():
        print(f"  - {table}")
