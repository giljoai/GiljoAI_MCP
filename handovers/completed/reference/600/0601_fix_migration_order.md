# Handover 0601: Fix Migration Order & Fresh Install

**Phase**: 0
**Tool**: CLI (Local)
**Agent Type**: installation-flow-agent
**Duration**: 6 hours
**Parallel Group**: Sequential
**Depends On**: 0600

---

## Context

**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md` for universal project context.

**Previous Handovers**: Handover 0600 completed comprehensive system audit, documenting migration chain issues including 20251114_create_missing_base_tables.py running at position 44 instead of position 1.

**This Handover**: Fix migration order by moving the 20251114_create_missing_base_tables.py migration to early in the chain, update all downstream dependencies, and validate that fresh installation works correctly in <5 minutes.

---

## Specific Objectives

- **Objective 1**: Move 20251114_create_missing_base_tables.py to position 1 in migration chain
- **Objective 2**: Update all downstream migration down_revision pointers
- **Objective 3**: Test fresh install on clean PostgreSQL database (<5 min target)
- **Objective 4**: Validate pg_trgm extension creation
- **Objective 5**: Verify all 31 tables created in correct order with proper constraints
- **Objective 6**: Benchmark install time and document performance

---

## Tasks

### Task 1: Analyze Current Migration Chain
**What**: Review audit findings from 0600 to understand current migration order
**Why**: Need complete understanding before making changes
**Files**:
- `handovers/600/0600_migration_dependency_graph.txt` - Review migration chain
- `migrations/versions/20251114_create_missing_base_tables.py` - Current problematic migration
**Commands**:
```bash
cd /f/GiljoAI_MCP
alembic history | head -20  # See first migrations
alembic history | tail -20  # See last migrations (where 20251114 currently is)
```

### Task 2: Identify Target Position for 20251114
**What**: Determine correct position for base table creation (should be after initial schema, before feature migrations)
**Why**: Base tables must exist before other migrations reference them
**Files**: `migrations/versions/*.py` - Review early migrations
**Commands**:
```bash
# Find the initial schema migration
ls -lt migrations/versions/ | tail -10
grep -l "initial" migrations/versions/*.py
```

**Decision Point**: Target position should be:
- After: Initial Alembic setup (if exists)
- Before: Any migration that references the 14 missing tables (mcp_agent_jobs, settings, etc.)

### Task 3: Rename and Reorder Migration File
**What**: Rename 20251114_create_missing_base_tables.py to run early in chain
**Why**: Alembic orders by revision ID, so changing down_revision makes it run earlier
**Files**:
- `migrations/versions/20251114_create_missing_base_tables.py` - Modify down_revision
**Commands**:
```bash
cd /f/GiljoAI_MCP/migrations/versions

# Backup original
cp 20251114_create_missing_base_tables.py 20251114_create_missing_base_tables.py.backup

# Edit down_revision (change from current head to early migration)
# Example: down_revision = "45abb2fcc00d"  # Early migration after initial schema
```

**Example Change**:
```python
# Before:
down_revision: Union[str, Sequence[str], None] = "00450fa7780c"  # Current head

# After:
down_revision: Union[str, Sequence[str], None] = "45abb2fcc00d"  # Early in chain
```

### Task 4: Update Downstream Migration Dependencies
**What**: Find all migrations that pointed to 20251114's old predecessor, update to point to 20251114
**Why**: Maintain migration chain continuity
**Files**: All migrations that previously pointed to 00450fa7780c (old head)
**Commands**:
```bash
# Find migrations that need updating
grep -r "down_revision.*00450fa7780c" migrations/versions/

# Update each to point to 20251114's revision ID instead
```

### Task 5: Test Fresh Install (Clean Database)
**What**: Drop and recreate database, run install.py, verify success
**Why**: Validate migration order fix works on fresh install
**Commands**:
```bash
# Drop and recreate database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test;"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Temporarily update config.yaml to use test database
# (or set DATABASE_URL environment variable)

# Run fresh install with timing
time python install.py
```

**What to Verify**:
- Install completes without errors
- All 31 tables created
- pg_trgm extension created
- Default tenant created
- Total time <5 minutes (target: 2-3 minutes with proper order)

### Task 6: Validate Schema Correctness
**What**: Verify all 31 tables exist with correct schema
**Why**: Ensure migration reordering didn't break schema
**Commands**:
```bash
# Connect to test database
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test

# List all tables (should be 31 + alembic_version)
\dt

# Verify key tables exist
\d+ products
\d+ projects
\d+ mcp_agent_jobs
\d+ settings

# Check pg_trgm extension
\dx

# Exit
\q
```

### Task 7: Benchmark Install Time
**What**: Run fresh install 3 times, average time, compare to 5-minute target
**Why**: Performance validation ensures migration order improvement
**Commands**:
```bash
# Run 3 fresh installs
for i in {1..3}; do
  echo "Run $i:"
  PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE giljo_mcp_test;"
  PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test;"
  time python install.py 2>&1 | grep "real"
done
```

**Document in**: `handovers/600/0601_fresh_install_test.md`

### Task 8: Cleanup Test Database
**What**: Drop test database, restore config.yaml
**Why**: Return to clean state
**Commands**:
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE giljo_mcp_test;"
# Restore config.yaml if modified
```

---

## Success Criteria

- [ ] **Migration Reordered**: 20251114 migration runs early in chain (not at position 44)
- [ ] **Dependencies Updated**: All downstream migrations point to correct predecessors
- [ ] **Fresh Install Works**: Install completes successfully on clean database
- [ ] **All Tables Created**: 31 tables + alembic_version table exist
- [ ] **pg_trgm Extension**: Extension created and verified
- [ ] **Install Time**: Fresh install <5 min (ideally 2-3 min)
- [ ] **Default Tenant**: Default tenant created (tenant_key present)
- [ ] **Commit**: Migration fixes committed with descriptive message

---

## Validation Steps

**How to verify this handover is complete:**

```bash
# Step 1: Verify migration order
cd /f/GiljoAI_MCP
alembic history | head -20
# Expected: 20251114 should appear early in list (not at end)

# Step 2: Run fresh install test
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test;"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test;"
time python install.py
# Expected: No errors, completes in <5 min

# Step 3: Verify table count
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
# Expected: 32 tables (31 + alembic_version)

# Step 4: Verify pg_trgm extension
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test -c "\dx pg_trgm"
# Expected: Extension listed

# Step 5: Verify default tenant
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test -c "SELECT tenant_key FROM products LIMIT 1;"
# Expected: At least one tenant_key value (or table empty but exists)

# Step 6: Cleanup
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE giljo_mcp_test;"
```

**Expected Output**:
- Fresh install completes in 2-4 minutes
- All 31 application tables created
- pg_trgm extension installed
- No migration errors
- Test report documents 3 successful runs with average time

---

## Deliverables

### Code
- **Modified**:
  - `migrations/versions/20251114_create_missing_base_tables.py` - Updated down_revision
  - Other migration files - Updated dependencies (if needed)

### Documentation
- **Created**:
  - `handovers/600/0601_fresh_install_test.md` - Fresh install test report with:
    - 3 test run results
    - Average install time
    - Table creation verification
    - pg_trgm extension verification
    - Performance comparison (before/after fix)

### Git Commit
- **Message**: `fix: Reorder migration chain for fresh install success (Handover 0601)`
- **Branch**: master (CLI execution)

---

## Dependencies

### Requires (Before Starting)
- **Handover 0600**: Audit complete, migration dependency graph available
- **Database**: PostgreSQL running, ability to create/drop test databases
- **Permissions**: Database superuser access (for extension creation)

### Blocks (What's Waiting)
- **Handover 0602**: Requires working fresh install to establish test baseline
- **All Phase 1-6 handovers**: Depend on stable migration foundation

---

## Notes for Agent

### CLI (Local) Execution
This is a CLI handover requiring local execution:

- You have database access - create/drop test databases freely
- Modify migration files directly (not mocked)
- Run install.py to test end-to-end
- Commit directly to master after validation

### Migration Safety
**CRITICAL**: Alembic migration reordering is delicate:

- Always backup migration files before editing
- Test fresh install thoroughly before committing
- Verify migration history is linear (no branches)
- Document any manual SQL fixes needed

### Common Patterns
Reference from AGENT_REFERENCE_GUIDE.md:

- Database setup: See "Database Setup" section
- Migration pattern: See "Migration Pattern" section
- Testing commands: See "Testing Commands" section

### Known Issues
From Handover 0510/0511 conversation:

- Migration 20251029_0073_01 has early return if mcp_agent_jobs doesn't exist (GOOD)
- Migration 20251027_single_active has connection.commit() after ALTER TABLE (GOOD)
- Migration order is the core issue - this handover fixes it

### Quality Checklist
Before marking this handover complete:

- [ ] Migration chain is linear (no circular dependencies)
- [ ] Fresh install tested 3+ times (reproducible success)
- [ ] All 31 tables created with correct schema
- [ ] pg_trgm extension verified
- [ ] Install time <5 min (ideally 2-3 min)
- [ ] Test report comprehensive and accurate
- [ ] Commit message follows convention
- [ ] No breaking changes to existing installations (only affects fresh installs)

---

**Document Control**:
- **Handover**: 0601
- **Created**: 2025-11-14
- **Status**: Ready for execution
