"""
Quick diagnostic script to identify API startup issues
Run this before starting the API server to catch errors early
"""

import sys
from pathlib import Path

print("=" * 70)
print("GiljoAI MCP Startup Diagnostics")
print("=" * 70)
print()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

errors = []
warnings = []

# 1. Check if setup directory exists
print("1. Checking setup directory structure...")
setup_dir = Path(__file__).parent / "src" / "giljo_mcp" / "setup"
if setup_dir.exists():
    print(f"   ✅ Setup directory exists: {setup_dir}")

    # Check for __init__.py
    init_file = setup_dir / "__init__.py"
    if init_file.exists():
        print(f"   ✅ __init__.py exists")
    else:
        warnings.append("Missing src/giljo_mcp/setup/__init__.py")
        print(f"   ⚠️ Missing __init__.py")

    # Check for state_manager.py
    state_manager = setup_dir / "state_manager.py"
    if state_manager.exists():
        print(f"   ✅ state_manager.py exists")
    else:
        errors.append("Missing src/giljo_mcp/setup/state_manager.py")
        print(f"   ❌ Missing state_manager.py")
else:
    errors.append(f"Setup directory does not exist: {setup_dir}")
    print(f"   ❌ Setup directory missing: {setup_dir}")
print()

# 2. Try importing SetupStateManager
print("2. Testing SetupStateManager import...")
try:
    from giljo_mcp.setup.state_manager import SetupStateManager
    print("   ✅ SetupStateManager imported successfully")
except ImportError as e:
    errors.append(f"Cannot import SetupStateManager: {e}")
    print(f"   ❌ Import failed: {e}")
except Exception as e:
    errors.append(f"Unexpected error importing SetupStateManager: {e}")
    print(f"   ❌ Unexpected error: {e}")
print()

# 3. Check database connection
print("3. Checking database connection...")
try:
    from giljo_mcp.config_manager import get_config
    config = get_config()
    print(f"   ✅ Config loaded successfully")
    print(f"   Mode: {config.mode if hasattr(config, 'mode') else 'unknown'}")

    if config.database:
        print(f"   Database: {config.database.type}")
        print(f"   Host: {config.database.host}")
        print(f"   Port: {config.database.port}")
        print(f"   Database: {config.database.database_name}")
    else:
        warnings.append("No database configuration found")
        print(f"   ⚠️ No database configured")
except Exception as e:
    errors.append(f"Config error: {e}")
    print(f"   ❌ Config error: {e}")
print()

# 4. Check if database tables exist
print("4. Checking database tables...")
try:
    from giljo_mcp.database import DatabaseManager
    config = get_config()

    if config.database:
        db_url = f"postgresql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.database_name}"
        db_manager = DatabaseManager(db_url, is_async=False)

        # Try to get a session
        with db_manager.session_scope() as session:
            # Check if setup_state table exists
            from sqlalchemy import inspect
            inspector = inspect(session.bind)
            tables = inspector.get_table_names()

            print(f"   Found {len(tables)} tables in database")

            if "setup_state" in tables:
                print("   ✅ setup_state table exists")
            else:
                warnings.append("setup_state table does not exist - run migrations")
                print("   ⚠️ setup_state table missing (need to run migrations)")

            if "projects" in tables:
                print("   ✅ projects table exists")
            else:
                warnings.append("projects table missing")
                print("   ⚠️ projects table missing")
    else:
        warnings.append("Cannot check database - no config")
        print("   ⚠️ Cannot check - no database config")

except Exception as e:
    errors.append(f"Database check failed: {e}")
    print(f"   ❌ Database check failed: {e}")
print()

# 5. Check Alembic migration status
print("5. Checking Alembic migration status...")
try:
    import subprocess
    result = subprocess.run(
        ["alembic", "current"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )

    if result.returncode == 0:
        print(f"   ✅ Alembic current: {result.stdout.strip()}")
        if "e2639692ae52" in result.stdout:
            print("   ✅ Latest migration applied (setup_state table)")
        else:
            warnings.append("setup_state migration not applied")
            print("   ⚠️ Latest migration (e2639692ae52) not applied")
    else:
        warnings.append(f"Alembic error: {result.stderr}")
        print(f"   ⚠️ Alembic error: {result.stderr.strip()}")
except FileNotFoundError:
    warnings.append("Alembic not found")
    print("   ⚠️ Alembic not available")
except Exception as e:
    warnings.append(f"Migration check error: {e}")
    print(f"   ⚠️ Error: {e}")
print()

# Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)

if errors:
    print(f"\n❌ ERRORS ({len(errors)}):")
    for i, error in enumerate(errors, 1):
        print(f"   {i}. {error}")
    print()

if warnings:
    print(f"⚠️ WARNINGS ({len(warnings)}):")
    for i, warning in enumerate(warnings, 1):
        print(f"   {i}. {warning}")
    print()

if not errors and not warnings:
    print("✅ All checks passed! API server should start successfully.")
    print()
elif not errors:
    print("⚠️ Warnings found but API should start. Review warnings above.")
    print()
else:
    print("❌ ERRORS FOUND - API server will likely fail to start!")
    print()
    print("RECOMMENDED ACTIONS:")
    if any("setup_state" in str(e).lower() for e in errors + warnings):
        print("   1. Create setup directory: mkdir -p src/giljo_mcp/setup")
        print("   2. Copy state_manager.py from F: drive to C: drive")
        print("   3. Run database migration: alembic upgrade head")
    print()

print("=" * 70)
