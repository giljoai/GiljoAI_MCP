# Handover 0700b: Database Schema Purge

## Context

**Decision**: Pre-release cleanup - remove ALL deprecated database columns before v1.0 ships.

**Rationale**: No external users exist. Ship a clean schema without backwards compatibility baggage.

**Reference**: Strategic direction change documented in `dead_code_audit.md` (2026-02-04)

## Scope

Remove deprecated columns from SQLAlchemy models and create clean baseline migration.

### Affected Tables

**1. agent_executions** (5 deprecated columns):
- `instance_number` - Line 184-189 (Handover 0461b deprecation)
- `decommissioned_at` - Line 200-204
- `succeeded_by` - Line 212-216
- `succession_reason` - Line 282-286
- `handover_summary` - Line 287-291

**2. products** (1 deprecated JSONB field - partial):
- `product_memory.sequential_history` - Line 123-126 (field within JSONB, see 0700c for full JSONB cleanup)

**3. templates** (1 deprecated column):
- `template_content` - Line 73-77 (models/templates.py)

**4. download_tokens** (2 deprecated columns):
- `is_used` - Line 620-622 (models/config.py)
- `downloaded_at` - Line 623-625

**5. projects** (1 soft-deprecated column):
- `context_budget` - Line 69 (products.py docstring line 46 notes soft deprecation)

## Tasks

### Phase 1: Model Cleanup
1. [ ] Remove `AgentExecution` deprecated columns (src/giljo_mcp/models/agent_identity.py):
   - Delete lines 184-189 (instance_number)
   - Delete lines 200-204 (decommissioned_at)
   - Delete lines 212-216 (succeeded_by)
   - Delete lines 282-286 (succession_reason)
   - Delete lines 287-291 (handover_summary)
   - Update class docstring (lines 143-152) to remove deprecation notices

2. [ ] Remove `AgentTemplate.template_content` column (src/giljo_mcp/models/templates.py):
   - Delete lines 73-77
   - Update template seeder if it writes to this column (src/giljo_mcp/template_seeder.py:248)

3. [ ] Remove `DownloadToken` legacy columns (src/giljo_mcp/models/config.py):
   - Delete lines 620-622 (is_used)
   - Delete lines 623-625 (downloaded_at)

4. [ ] Remove `Project.context_budget` soft-deprecated column (src/giljo_mcp/models/projects.py):
   - Delete line 69
   - Update docstring at line 46 to remove soft-deprecation note
   - Search for all code reading this field and migrate to AgentExecution.context_budget

### Phase 2: Code Migration
5. [ ] Search for all references to removed columns:
   ```bash
   grep -r "instance_number" src/ api/
   grep -r "decommissioned_at" src/ api/
   grep -r "succeeded_by" src/ api/
   grep -r "succession_reason" src/ api/
   grep -r "handover_summary" src/ api/
   grep -r "template_content" src/ api/
   grep -r "is_used" src/ api/
   grep -r "downloaded_at" src/ api/
   grep -r "context_budget" src/ api/ | grep -v "AgentExecution"
   ```

6. [ ] Remove or migrate code accessing deprecated columns:
   - Update any service methods reading these fields
   - Update any API endpoints returning these fields
   - Update any WebSocket events broadcasting these fields

### Phase 3: Migration Update
7. [ ] Update baseline migration (migrations/baseline_migration.py or equivalent):
   - Remove column definitions for all deprecated columns
   - Ensure migration generates clean schema matching updated models

8. [ ] Test fresh install:
   ```bash
   # Drop and recreate database
   python install.py --reset-db
   # Verify schema matches models
   python -c "from src.giljo_mcp.models import *; print('Models loaded successfully')"
   ```

### Phase 4: Documentation
9. [ ] Update CLAUDE.md to remove references to deprecated columns
10. [ ] Update API documentation if any endpoints documented these fields
11. [ ] Update any user guides mentioning removed fields

## Verification

- [ ] All imports resolve (no undefined column references)
- [ ] Fresh install completes without errors
- [ ] `pytest tests/ -v` passes (100% test suite)
- [ ] No grep matches for removed column names (except in comments/docs)
- [ ] Database schema inspection shows clean tables:
  ```bash
  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d agent_executions"
  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d templates"
  PGPASSWORD=4040 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d download_tokens"
  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d projects"
  ```

## Risk Assessment

**RISK: HIGH** - Database schema changes

**Mitigation**:
- Baseline migration approach ensures clean schema for new installs
- No upgrade migration needed (pre-release, no production databases exist)
- Comprehensive grep ensures all code references are found
- Test suite validates no broken dependencies

**Rollback Plan**:
- Git revert commit
- Restore model definitions from git history
- Re-run fresh install

## Dependencies

- **Depends on**: None (first handover in 0700 series schema cleanup)
- **Blocks**: 0700c (JSONB cleanup builds on clean schema)

## Estimated Impact

- **Lines removed**: ~60 lines (column definitions + comments)
- **Files modified**: 4 model files + migration file + scattered code references
- **Test updates**: Likely 5-10 tests checking deprecated fields
- **Fresh install time**: No change (~1 second)
- **Code search hits**: Estimate 20-30 references to migrate

## Notes

- `AgentExecution.messages` JSONB column NOT removed here (see 0700c for JSONB purge)
- `Product.product_memory.sequential_history` field NOT removed here (see 0700c)
- This handover focuses on simple column removal, not JSONB field migration
- The `Project.context_budget` removal requires careful migration to `AgentExecution.context_budget`
