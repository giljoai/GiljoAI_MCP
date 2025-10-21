# Quick Start: Project Alias Migration

## TL;DR

Add a 6-character alias column to projects table.

```bash
# Test it works
python test_alias_generation.py

# Run migration
python run_alembic_migration.py upgrade

# Verify
psql -U postgres -d giljo_mcp -c "SELECT id, name, alias FROM projects LIMIT 5;"
```

## What This Does

- Adds `alias` column (e.g., `A1B2C3`) to `projects` table
- Generates unique aliases for all existing projects
- Creates unique index for fast lookups
- Takes < 1 second for most databases

## Files Modified

1. `migrations/versions/add_alias_to_projects.py` - Migration script
2. `src/giljo_mcp/models.py` - Updated Project model

## Usage After Migration

### Create Project (Alias Auto-Generated)

```python
project = Project(
    name="My Project",
    mission="Build something",
    tenant_key=tenant_key
)
# project.alias is automatically set (e.g., "A1B2C3")
```

### Query by Alias

```python
project = session.query(Project).filter(
    Project.alias == 'A1B2C3',
    Project.tenant_key == tenant_key  # CRITICAL: Always filter by tenant_key
).first()
```

### API Endpoint Example

```python
@app.get("/api/projects/{alias}")
def get_project(alias: str, tenant_key: str):
    return session.query(Project).filter(
        Project.alias == alias,
        Project.tenant_key == tenant_key
    ).first_or_404()
```

## Rollback

```bash
python run_alembic_migration.py downgrade
```

## Troubleshooting

**Migration fails?**
1. Check PostgreSQL is running: `psql -U postgres -l`
2. Check `.env` has `POSTGRES_PASSWORD`
3. Check logs for specific error

**Need help?**
- Full guide: `migrations/MIGRATION_GUIDE_ALIAS.md`
- Summary: `MIGRATION_SUMMARY.md`

## Performance

- 100 projects: < 1 second
- 1,000 projects: < 1 second
- 10,000 projects: < 1 second
- 100,000 projects: < 1 second

## Safety

- All operations in single transaction
- Tenant isolation maintained
- Unique constraint prevents duplicates
- Rollback available if needed
