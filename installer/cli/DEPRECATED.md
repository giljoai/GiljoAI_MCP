# DEPRECATED: installer/cli

**This installer is NO LONGER USED.**

## Use Root Installer Instead

```bash
# CORRECT - Use root installer
python install.py
```

## Why Deprecated?

The `installer/cli/` installer was using the wrong approach for database table creation:
- **OLD (WRONG)**: Attempted to use Alembic migrations that don't exist
- **NEW (CORRECT)**: Uses `DatabaseManager.create_tables_async()` like the rest of the application

## Installer Architecture

The root `install.py` uses the SAME table creation method as api/app.py:

```python
# In install.py (line ~450)
await db_manager.create_tables_async()

# In api/app.py (line 186)
await state.db_manager.create_tables_async()

# In database.py
async def create_tables_async(self):
    async with self.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**This ensures consistency across the entire application.**

## What Happened?

The `installer/cli/` installer was calling:
```python
db_installer.run_migrations()  # WRONG - tried to use Alembic
```

But the project doesn't use Alembic. This caused:
- Tables not being created during installation
- API starting in setup mode (db_manager = None)
- Password change endpoint failing (503 errors)
- Fresh installations being broken

## Current Status

This folder is kept only for historical reference. **DO NOT USE.**

All new installations should use:
```bash
python install.py
```

---

**Date Deprecated**: October 11, 2025
**Replacement**: `install.py` (root directory)
