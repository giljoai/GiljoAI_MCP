# Handover 0623: Schema Consolidation (Baseline Migration)

**Phase**: 4 | **Tool**: CLI | **Agent**: database-architect | **Duration**: 1 day
**Parallel Group**: Sequential | **Depends On**: 0622

## Context
**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md`
**This Handover**: Create baseline schema migration consolidating all 44 migrations into single schema for fast fresh installs (2-3 min vs 5 min).

## Tasks

1. **Create Baseline Migration**: `migrations/versions/baseline_schema.py`
   - Create all 31 tables in correct order
   - Create indexes and constraints
   - Create pg_trgm extension
   - Revision ID: baseline_001, down_revision: None

2. **Verify Schema Match**: Ensure baseline creates identical schema to 44-chain
   ```bash
   # Baseline path
   dropdb giljo_mcp && createdb giljo_mcp
   alembic upgrade baseline_001
   pg_dump giljo_mcp > baseline_schema.sql

   # 44-chain path
   dropdb giljo_mcp && createdb giljo_mcp
   alembic upgrade head
   pg_dump giljo_mcp > chain_schema.sql

   # Compare (should be identical)
   diff baseline_schema.sql chain_schema.sql
   ```

3. **Update install.py**: Use baseline for fresh installs (detect empty DB → run baseline)

4. **Document Strategy**: `docs/guides/migration_strategy.md` - When to use baseline vs 44-chain

## Success Criteria
- [ ] Baseline migration created (all 31 tables)
- [ ] Schema verification passes (baseline == 44-chain)
- [ ] Fresh install <2 min (vs 5 min with 44-chain)
- [ ] Documentation updated

## Deliverables
**Created**: `migrations/versions/baseline_schema.py`, `handovers/600/0623_schema_verification.md`, `docs/guides/migration_strategy.md`
**Commit**: `feat: Add baseline schema migration for fast installs (Handover 0623)`

**Document Control**: 0623 | 2025-11-14
