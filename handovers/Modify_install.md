# Modify_install: Template Archive Schema Alignment

**Goal:** Align the `template_archives` database table with the current ORM model so template history/reset endpoints and tests work consistently in both existing and fresh installations.

## 1. Required DB Change (Existing Databases)

Target table: `template_archives` (PostgreSQL, schema `public`).

Current ORM (see `src/giljo_mcp/models/templates.py`) expects these additional columns on `template_archives`:

- `system_instructions TEXT NULL`
- `user_instructions   TEXT NULL`

### 1.1 Alembic Migration (Preferred)

Create a new Alembic revision in `migrations/versions/`, e.g. `add_template_archive_dual_fields.py`:

```python
\"\"\"Add dual-field columns to template_archives

Revision ID: add_template_archive_dual_fields
Revises: add_template_mgmt
Create Date: 2025-XX-XX
\"\"\"

from alembic import op
import sqlalchemy as sa


revision = "add_template_archive_dual_fields"
down_revision = "add_template_mgmt"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("template_archives", sa.Column("system_instructions", sa.Text(), nullable=True))
    op.add_column("template_archives", sa.Column("user_instructions", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("template_archives", "user_instructions")
    op.drop_column("template_archives", "system_instructions")
```

**Execution for existing DBs:**

- Ensure the current alembic config (if present) points at the live DB.
- Run: `alembic upgrade head` (or `alembic upgrade add_template_archive_dual_fields` if you use explicit revision IDs).

This is idempotent across environments and safe for live data because new columns are nullable.

### 1.2 One-off SQL (Dev/Ad‑hoc)

If Alembic is not wired in a given environment, the minimal equivalent SQL is:

```sql
ALTER TABLE template_archives
    ADD COLUMN IF NOT EXISTS system_instructions TEXT;

ALTER TABLE template_archives
    ADD COLUMN IF NOT EXISTS user_instructions TEXT;
```

Agents should **prefer the Alembic migration**, but this SQL is useful for quick local repair.

## 2. Fresh Install Flow (install.py and Related Scripts)

Objective: A fresh customer installation must end up with a schema that already includes the new columns, without manual SQL.

### 2.1 Recommended Pattern

1. **Keep Alembic as the source of truth for schema evolution.**
2. In `install.py` (or the script that provisions the DB), ensure the following high‑level steps:
   - Create database (if not exists).
   - Run base migrations (including `add_template_mgmt` and `add_template_archive_dual_fields`):
     - e.g. `alembic upgrade head` using the same connection URL as `DatabaseManager`.
   - Optionally seed initial data (tenants, default templates, etc.).

### 2.2 Concrete Changes for an Agent

When you (or another agent) update `install.py` and any related setup scripts:

- **Locate DB initialization logic.** Typical places:
  - `install.py`
  - `installer/core/database.py` (or similar)
  - Any script that currently calls `DatabaseManager.create_tables_async()` directly.

- **Refactor away from “create_all as schema source of truth” for production installs:**
  - It is acceptable to use `create_all()` in test/dev bootstrap, but production installs should rely on Alembic revisions.

- **Add a clear `run_migrations()` step:**
  - Example (pseudo-code):
    ```python
    def run_migrations(database_url: str) -> None:
        \"\"\"Run Alembic migrations up to head for the given DB.\"\"\"
        # Configure Alembic programmatically with database_url
        # and call command.upgrade(config, \"head\")
    ```
  - Call `run_migrations()` in the install flow after DB creation and before seeding.

- **Ensure `DATABASE_URL` wiring is shared:**
  - `install.py`, `startup.py`, and `DatabaseManager` must agree on connection parameters (host, port, db name, user, password).
  - Agents editing `install.py` should reuse the same URL construction as `DatabaseManager.build_postgresql_url` or the central config.

## 3. Validation Steps for Agents

After adding the migration and updating the install flow, an agent should validate:

- For an existing DB:
  - `SELECT system_instructions, user_instructions FROM template_archives LIMIT 1;` runs without error.
  - `pytest tests/api/test_templates_api_0106.py::TestTemplateAPIDualFields::test_archive_includes_both_fields -q --no-cov` passes.

- For a fresh install:
  - Run `install.py` (or documented install command).
  - Verify `\d template_archives` in `psql` shows `system_instructions` and `user_instructions` columns.
  - Run the full template API test files (0103 + 0106) to ensure behavior and schema are aligned.

## 4. Summary for Future Agents

- **Primary change:** Add `system_instructions` and `user_instructions` columns to `template_archives` via Alembic migration.
- **Existing DBs:** Run the new migration (or the provided SQL) once.
- **Fresh installs:** Ensure `install.py` (and any installer scripts) always run all migrations so the DB schema matches the ORM.
- **Do not** rely solely on `Base.metadata.create_all()` for production schema; that’s for bootstrap/test only. Use migrations as the canonical source of schema truth.

