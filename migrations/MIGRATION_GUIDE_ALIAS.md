# Migration Guide: Add Alias to Projects Table

## Overview

This migration adds a 6-character alphanumeric `alias` column to the `projects` table to provide short, human-friendly project identifiers.

**Migration File**: `migrations/versions/add_alias_to_projects.py`
**Revision ID**: `add_alias_to_projects`
**Revises**: `f7f0422fda1e`

## What This Migration Does

1. Adds `alias` column to `projects` table (nullable initially)
2. Generates unique 6-character alphanumeric aliases for all existing projects
3. Creates unique index on `alias` column for database-level uniqueness enforcement
4. Makes `alias` NOT NULL after backfilling existing data

## Alias Format

- Length: 6 characters
- Character set: A-Z and 0-9 (uppercase letters and digits)
- Examples: `A1B2C3`, `XYZ123`, `9K4L2M`
- Uniqueness: Enforced by unique index at database level

## Running the Migration

### Prerequisites

1. Ensure PostgreSQL database is running
2. Ensure `.env` file contains database credentials:
   ```bash
   POSTGRES_PASSWORD=your_password
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=giljo_mcp
   POSTGRES_USER=giljo_user
   ```

### Step 1: Test Migration (Development)

```bash
# Navigate to project root
cd F:/GiljoAI_MCP

# Check current migration status
python -c "from alembic.config import Config; from alembic import command; cfg = Config(); cfg.set_main_option('script_location', 'migrations'); command.current(cfg)"

# Run migration
python -c "from alembic.config import Config; from alembic import command; cfg = Config(); cfg.set_main_option('script_location', 'migrations'); command.upgrade(cfg, 'head')"
```

### Step 2: Verify Migration Success

```bash
# Connect to database
psql -U postgres -d giljo_mcp

# Check alias column exists
\d projects

# Verify aliases were generated
SELECT id, name, alias FROM projects LIMIT 10;

# Verify unique index exists
\di idx_project_alias_unique

# Exit psql
\q
```

### Step 3: Production Migration

**IMPORTANT**: Always backup production database before running migrations!

```bash
# Backup database
pg_dump -U postgres -d giljo_mcp -F c -b -v -f "giljo_mcp_backup_$(date +%Y%m%d_%H%M%S).backup"

# Run migration
python -c "from alembic.config import Config; from alembic import command; cfg = Config(); cfg.set_main_option('script_location', 'migrations'); command.upgrade(cfg, 'head')"

# Verify migration
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) as total, COUNT(alias) as with_alias FROM projects;"
```

## Rollback Strategy

If issues occur, you can rollback the migration:

```bash
# Rollback one revision
python -c "from alembic.config import Config; from alembic import command; cfg = Config(); cfg.set_main_option('script_location', 'migrations'); command.downgrade(cfg, '-1')"
```

### Manual Rollback (if automated rollback fails)

```sql
-- Connect to database
psql -U postgres -d giljo_mcp

-- Drop unique index
DROP INDEX IF EXISTS idx_project_alias_unique;

-- Drop alias column
ALTER TABLE projects DROP COLUMN IF EXISTS alias;

-- Verify rollback
\d projects
```

## Performance Considerations

### Index Impact

- The unique index on `alias` will improve query performance when searching by alias
- Index size is minimal (6 bytes per row)
- Index creation is fast even for large tables (completed during migration)

### Query Performance

Before migration:
```sql
-- Slow: Full table scan
SELECT * FROM projects WHERE name = 'My Project';
```

After migration:
```sql
-- Fast: Index scan
SELECT * FROM projects WHERE alias = 'A1B2C3';
```

### Migration Time Estimates

- Small database (< 1,000 projects): < 1 second
- Medium database (1,000 - 10,000 projects): 1-5 seconds
- Large database (10,000+ projects): 5-30 seconds

**Note**: Migration uses batch updates for performance. No downtime required.

## Race Conditions Handling

The migration handles potential race conditions:

1. **Alias Generation**: Uses set-based deduplication during backfill
2. **Unique Constraint**: Database-level unique index prevents duplicates
3. **Transaction Safety**: All operations within a single transaction
4. **Tenant Isolation**: Updates filter by BOTH `id` AND `tenant_key` for security

## Code Changes Required

### Model Update

The `Project` model in `src/giljo_mcp/models.py` has been updated:

```python
alias = Column(String(6), nullable=False, unique=True, index=True, default=generate_project_alias,
               comment="6-character alphanumeric project identifier (e.g., A1B2C3)")
```

### Creating New Projects

```python
from giljo_mcp.models import Project

# Alias is auto-generated
project = Project(
    name="My Project",
    mission="Build something awesome",
    tenant_key=tenant_key,
    product_id=product_id
)
# project.alias will be automatically set to a unique 6-char code

session.add(project)
session.commit()
```

### Querying by Alias

```python
# Find project by alias
project = session.query(Project).filter(
    Project.alias == 'A1B2C3',
    Project.tenant_key == tenant_key  # CRITICAL: Always filter by tenant_key
).first()

# Use alias in API endpoints
@app.get("/api/projects/{alias}")
def get_project(alias: str, tenant_key: str):
    project = session.query(Project).filter(
        Project.alias == alias,
        Project.tenant_key == tenant_key
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

## API Endpoint Updates

Consider updating these endpoints to support alias lookup:

1. `GET /api/projects/{alias}` - Get project by alias
2. `PUT /api/projects/{alias}` - Update project by alias
3. `DELETE /api/projects/{alias}` - Delete project by alias

**Example**:
```python
# Before: Only ID lookup
GET /api/projects/550e8400-e29b-41d4-a716-446655440000

# After: ID or Alias lookup
GET /api/projects/A1B2C3  # Much shorter and user-friendly
```

## Testing Checklist

- [ ] Migration runs successfully on development database
- [ ] All existing projects have unique aliases
- [ ] New projects auto-generate unique aliases
- [ ] Unique index prevents duplicate aliases
- [ ] Alias queries filter by tenant_key for data isolation
- [ ] API endpoints support alias lookup
- [ ] Rollback works correctly
- [ ] Production backup created before migration
- [ ] Production migration tested and verified

## Troubleshooting

### Issue: Migration fails with "duplicate key value"

**Cause**: Alias collision during backfill (extremely rare with 36^6 = 2.1 billion combinations)

**Solution**: Run migration again - retry logic will generate new alias

### Issue: Migration takes longer than expected

**Cause**: Large number of existing projects

**Solution**: Normal behavior. Migration uses efficient batch updates. Monitor progress in database logs.

### Issue: "No module named 'alembic'"

**Cause**: Alembic not installed or virtual environment not activated

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install alembic
pip install alembic
```

## Support

For issues or questions:
1. Check migration logs in console output
2. Review PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-*.log`
3. Verify database state: `psql -U postgres -d giljo_mcp`
4. Consult database team for production issues

## References

- Alembic Documentation: https://alembic.sqlalchemy.org/
- PostgreSQL Unique Indexes: https://www.postgresql.org/docs/current/indexes-unique.html
- GiljoAI Project Architecture: `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
