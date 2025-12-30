# Migrations

## Baseline Migration Approach (Handover 0601)

This project uses a unified baseline migration for fresh installations.

### Active Migrations

- `versions/caeddfdbb2a0_unified_baseline_all_tables.py` - Creates all 32 tables from pristine SQLAlchemy models

### Archived Migrations

Pre-baseline migrations are preserved in `archive/pre_baseline/` for historical reference.
These are NOT used by fresh installations.

**Archived Files:**
- `0670e17a56ff_remove_deprecated_vision_summary_fields.py` - Legacy migration (superseded by baseline)
- `0103_BEFORE_AFTER_COMPARISON.md` - Historical documentation
- `0103_DEPLOYMENT_CHECKLIST.md` - Historical documentation
- `0103_SECURITY_FIX_SUMMARY.md` - Historical documentation

### Adding Schema Changes

When modifying the database schema:

1. Update SQLAlchemy models in `src/giljo_mcp/models/`
2. Update the baseline migration (`caeddfdbb2a0_unified_baseline_all_tables.py`) to match
3. Run `python install.py` to apply changes to your local database

**Do NOT create new Alembic migrations** - modify the baseline instead.

### Why Baseline Approach?

The baseline migration approach provides:
- **Fresh installs in <1 second** (single migration vs. multiple sequential ones)
- **Clean slate** - all tables created from current SQLAlchemy model state
- **Simplified maintenance** - one file to keep in sync with models
- **Zero historical baggage** - no legacy migration chain to maintain

### Migration History

Old incremental migrations (pre-0601) are archived in `archive/pre_baseline/` and `archive/versions_pre_reset/`.
These directories preserve the historical migration chain but are not executed during installation.

For complete migration history, see `archive/MIGRATION_HISTORY_PRE_RESET_20251221.md`.
