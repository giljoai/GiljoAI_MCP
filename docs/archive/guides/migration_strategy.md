# Migration Strategy (Post-Nuclear Reset)

## Current State

**Single Baseline Migration**: `migrations/versions/f504ea46e988_baseline_schema_all_27_tables.py`

- **Tables Created**: 32 tables (31 data tables + alembic_version)
- **Fresh Install Time**: 0.57 seconds (vs 5+ minutes with broken 44-migration chain)
- **pg_trgm Extension**: Automatically installed
- **Status**: WORKING PERFECTLY

## Fresh Install Flow

1. User runs `python install.py`
2. install.py detects empty database (no alembic_version table)
3. Runs `alembic upgrade head`
4. Alembic runs baseline migration (f504ea46e988)
5. All 32 tables created in single transaction
6. pg_trgm extension installed
7. Installation completes in <60 seconds

## Database Schema (Baseline)

### Core Tables (32 total)
- **Authentication**: users, api_keys, mcp_sessions
- **Products**: products, vision_documents, visions, git_configs, git_commits
- **Projects**: projects, sessions, discovery_config
- **Agents**: mcp_agent_jobs, agent_interactions, jobs, messages
- **Templates**: agent_templates, template_archives, template_augmentations, template_usage_stats
- **Tasks**: tasks
- **Context**: context_index, large_document_index, mcp_context_index, mcp_context_summary
- **Configuration**: configurations, settings, setup_state, optimization_rules, optimization_metrics
- **Utilities**: api_metrics, download_tokens
- **Alembic**: alembic_version

### Key Features
- **Multi-tenant isolation**: All tables have tenant_key with indexes
- **Full-text search**: pg_trgm extension enabled
- **JSONB support**: Efficient JSON querying for config_data, meta_data
- **Soft delete**: products and projects support recovery
- **Succession tracking**: mcp_agent_jobs supports orchestrator handover
- **Template management**: Database-backed agent templates with 3-tier caching

## Future Migrations

### Adding New Schema Changes
```bash
# 1. Update SQLAlchemy models in src/giljo_mcp/models/
# 2. Generate migration
alembic revision --autogenerate -m "add_new_feature"

# 3. Review generated migration
# 4. Test migration on dev database
alembic upgrade head

# 5. Test rollback
alembic downgrade -1

# 6. Commit migration file
```

### Migration Chain
- **Current**: f504ea46e988 (baseline)
- **Future**: f504ea46e988 → [incremental changes]

Alembic will detect changes in SQLAlchemy models and generate incremental migrations on top of the baseline.

## Rollback Strategy

### Restore Old Migration Chain (If Needed)
```bash
# 1. Restore database from backup
PGPASSWORD=4010 psql -U postgres -d giljo_mcp < backups/giljo_mcp_pre_nuclear_YYYYMMDD_HHMMSS.sql

# 2. Restore migration files from archive
cp migration_archive_YYYYMMDD/*.py migrations/versions/

# 3. Update alembic_version table
PGPASSWORD=4010 psql -U postgres -d giljo_mcp -c "UPDATE alembic_version SET version_num = '20251026_224146';"
```

### Backup Archive Locations
- **Database**: `backups/giljo_mcp_pre_nuclear_20251114_200550.sql` (47KB)
- **Migrations**: `migration_archive_20251114/` (45 files)

## Benefits of Nuclear Reset

### Before (Broken 44-Migration Chain)
- Fresh install: FAILS with chicken-and-egg errors
- Migration time: 5+ minutes (if it worked)
- Migration conflicts: 44 potential points of failure
- Maintenance: Complex dependency graph

### After (Single Baseline)
- Fresh install: SUCCESS in 0.57 seconds
- Migration time: <1 second
- Migration conflicts: ZERO (single atomic operation)
- Maintenance: Simple, clean foundation

## Testing Results

### Fresh Install (Empty Database)
```
Database: giljo_mcp_nuclear_test
Time: 0.560 seconds
Tables: 32 created
Extensions: pg_trgm installed
Status: SUCCESS
```

### install.py Flow Test
```
Database: giljo_mcp_install_test
Time: 0.570 seconds
Tables: 32 created
Status: SUCCESS
```

### Schema Verification
```
Users: 29 columns, 9 indexes
Products: 11 columns, 7 indexes (vision_type constraint removed)
Projects: 21 columns, 8 indexes
MCPAgentJobs: 35 columns, 12 indexes
```

## Migration File Details

### File: migrations/versions/f504ea46e988_baseline_schema_all_27_tables.py
- **Size**: 59KB
- **Operations**: 62 total (31 CREATE TABLE + 31 DROP TABLE in downgrade)
- **Indexes**: 150+ indexes created
- **Constraints**: Foreign keys, CHECK constraints, UNIQUE constraints
- **Extensions**: pg_trgm (CREATE in upgrade, DROP in downgrade)

## Model Fixes Applied

### Product Model (Handover 0128e)
**Issue**: CheckConstraint referenced deprecated `vision_type` column
**Fix**: Removed CheckConstraint from `__table_args__`
**File**: `src/giljo_mcp/models/products.py` line 110

Before:
```python
CheckConstraint("vision_type IN ('file', 'inline', 'none')", name="ck_product_vision_type"),
```

After:
```python
# Handover 0128e: Removed CheckConstraint for deprecated vision_type field
```

## Developer Guidelines

### When to Create New Migration
- Adding new table
- Adding new column to existing table
- Creating new index
- Changing column type or constraint
- Adding database-level validation

### Migration Best Practices
1. Always test on dev database first
2. Review autogenerated migration (Alembic can miss things)
3. Test both upgrade AND downgrade
4. Include data migrations if needed
5. Document breaking changes
6. Use descriptive migration messages

### Multi-Tenant Safety
CRITICAL: All new tables MUST include:
- `tenant_key` column (VARCHAR(36), NOT NULL)
- Index on `tenant_key` for query performance
- Tenant isolation in ALL queries

### Example: Adding New Table
```python
# models/my_new_table.py
class MyNewTable(Base):
    __tablename__ = "my_new_table"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)  # REQUIRED
    name = Column(String(100), nullable=False)

    __table_args__ = (
        Index("idx_my_table_tenant", "tenant_key"),  # REQUIRED
    )
```

## Production Deployment

### For Existing Installations (FUTURE)
When we go to production with real user data:

1. **DO NOT** use nuclear reset (data loss!)
2. **DO** create incremental migrations from baseline
3. **DO** test migrations on staging database with production data copy
4. **DO** backup before migration
5. **DO** have rollback plan ready

### For Fresh Installations (NOW)
- Use baseline migration (f504ea46e988)
- Fast, clean, reliable
- No migration chain complexity

## Contact

Questions about migration strategy? See:
- **Handover 0600**: Nuclear migration reset documentation
- **Handover 0128e**: Product model vision field deprecation
- **Database Expert Agent**: This migration strategy doc

Have a great day!
