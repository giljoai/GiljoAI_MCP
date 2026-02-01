# Handover 0424k: Update Baseline Migration with Organization Tables

**Status:** Ready for Execution
**Color:** `#4CAF50` (Green - Database Foundation)
**Prerequisites:** 0424j (Migration Finalization - COMPLETE)
**Spawns:** 0424l (Fresh Install Verification)
**Chain:** 0424 Organization Hierarchy Series (Extended)

---

## Overview

The 0424a-j series added organization hierarchy to SQLAlchemy models but did NOT update the baseline Alembic migration. Fresh installs will fail because the migration doesn't create `organizations`, `org_memberships` tables or `org_id` columns.

**Problem Discovered:**
- Models have: `Organization`, `OrgMembership`, `User.org_id`, `Product.org_id`, etc.
- Migration `baseline_v32_unified.py` has: NONE of these tables/columns
- Fresh install: Creates 32 tables, MISSING org infrastructure
- Result: Any org-related code will fail with "relation does not exist"

**What This Accomplishes:**
- Updates baseline migration to include organization tables
- Adds org_id columns to users, products, agent_templates, tasks
- Fresh install will create complete schema
- Enables customer deployment

**Impact:**
- Fresh installs will work correctly
- Backup restore compatibility maintained (org_id nullable in migration)
- No changes to model files (already correct)

---

## Prerequisites

**Required Handovers:**
- 0424a-j: All COMPLETE (models exist, code works with existing data)

**Verify Before Starting:**
```powershell
# Check models have org infrastructure
cat src/giljo_mcp/models/organizations.py | head -20

# Check migration is MISSING org tables
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT 'organizations' FROM information_schema.tables WHERE table_name='organizations';" 2>&1

# Confirm migration file location
ls migrations/versions/baseline_v32_unified.py
```

---

## Implementation Phases

### Phase 1: Add Organizations Table to Migration

**Edit:** `migrations/versions/baseline_v32_unified.py`

**Find the `upgrade()` function and add BEFORE the `users` table creation (around line 280):**

```python
    # Organization Hierarchy (Handover 0424k)
    op.create_table('organizations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_key', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_org_tenant', 'organizations', ['tenant_key'], unique=False)
    op.create_index('idx_org_slug', 'organizations', ['slug'], unique=True)
    op.create_index('idx_org_active', 'organizations', ['is_active'], unique=False)
```

### Phase 2: Add org_id Column to Users Table

**Find the `users` table creation (around line 285) and add org_id column:**

```python
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_key', sa.String(length=36), nullable=False),
    sa.Column('org_id', sa.String(length=36), nullable=True),  # ADD THIS LINE - nullable for migration compatibility
    sa.Column('username', sa.String(length=64), nullable=False),
    # ... rest of existing columns ...
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='SET NULL'),  # ADD THIS
    sa.CheckConstraint("role IN ('admin', 'developer', 'viewer')", name='ck_user_role'),
    # ... rest of constraints ...
    )
    op.create_index('idx_user_org_id', 'users', ['org_id'], unique=False)  # ADD THIS
```

### Phase 3: Add OrgMemberships Table

**Add AFTER users table creation (around line 320):**

```python
    # Organization Memberships (Handover 0424k)
    op.create_table('org_memberships',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('org_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('role', sa.String(length=32), nullable=False),
    sa.Column('invited_by', sa.String(length=36), nullable=True),
    sa.Column('tenant_key', sa.String(length=36), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('org_id', 'user_id', name='uq_org_user'),
    sa.CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name='ck_membership_role')
    )
    op.create_index('idx_membership_org', 'org_memberships', ['org_id'], unique=False)
    op.create_index('idx_membership_user', 'org_memberships', ['user_id'], unique=False)
    op.create_index('idx_membership_tenant', 'org_memberships', ['tenant_key'], unique=False)
```

### Phase 4: Add org_id to Products Table

**Find `products` table creation (around line 207) and add:**

```python
    op.create_table('products',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_key', sa.String(length=36), nullable=False),
    sa.Column('org_id', sa.String(length=36), nullable=True),  # ADD THIS LINE
    sa.Column('name', sa.String(length=255), nullable=False),
    # ... rest of existing columns ...
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='SET NULL'),  # ADD THIS
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_product_org_id', 'products', ['org_id'], unique=False)  # ADD THIS
```

### Phase 5: Add org_id to Agent Templates Table

**Find `agent_templates` table creation (around line 38) and add:**

```python
    op.create_table('agent_templates',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_key', sa.String(length=36), nullable=False),
    sa.Column('org_id', sa.String(length=36), nullable=True),  # ADD THIS LINE
    sa.Column('name', sa.String(length=255), nullable=False),
    # ... rest of existing columns ...
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='SET NULL'),  # ADD THIS
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_template_org_id', 'agent_templates', ['org_id'], unique=False)  # ADD THIS
```

### Phase 6: Add org_id to Tasks Table

**Find `tasks` table creation (around line 920) and add:**

```python
    op.create_table('tasks',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_key', sa.String(length=36), nullable=False),
    sa.Column('org_id', sa.String(length=36), nullable=True),  # ADD THIS LINE
    # ... rest of existing columns ...
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='SET NULL'),  # ADD THIS
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_task_org_id', 'tasks', ['org_id'], unique=False)  # ADD THIS
```

### Phase 7: Update Downgrade Function

**Find the `downgrade()` function and add drops in REVERSE order:**

```python
def downgrade():
    # Drop org_id indexes and columns (Handover 0424k)
    op.drop_index('idx_task_org_id', table_name='tasks')
    op.drop_constraint('tasks_org_id_fkey', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'org_id')

    op.drop_index('idx_template_org_id', table_name='agent_templates')
    op.drop_constraint('agent_templates_org_id_fkey', 'agent_templates', type_='foreignkey')
    op.drop_column('agent_templates', 'org_id')

    op.drop_index('idx_product_org_id', table_name='products')
    op.drop_constraint('products_org_id_fkey', 'products', type_='foreignkey')
    op.drop_column('products', 'org_id')

    op.drop_table('org_memberships')

    op.drop_index('idx_user_org_id', table_name='users')
    op.drop_constraint('users_org_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'org_id')

    op.drop_table('organizations')

    # ... rest of existing downgrade ...
```

---

## Success Criteria

**Migration File:**
- [ ] `organizations` table added with all columns and indexes
- [ ] `org_memberships` table added with all columns, indexes, and constraints
- [ ] `users.org_id` column added (nullable=True for migration compatibility)
- [ ] `products.org_id` column added (nullable=True)
- [ ] `agent_templates.org_id` column added (nullable=True)
- [ ] `tasks.org_id` column added (nullable=True)
- [ ] All FK constraints reference `organizations.id`
- [ ] Downgrade function properly drops everything

**Verification:**
- [ ] Migration file has no syntax errors (python -m py_compile)
- [ ] Table creation order is correct (organizations before users, users before org_memberships)
- [ ] FK constraint order is correct

---

## Chain Execution Instructions

**CRITICAL: This handover is part of the 0424 chain (extended). You MUST update chain_log.json.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json
```

Verify 0424j status is "complete".

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json` - find the 0424k session entry and set:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover

**CRITICAL: Use Task Tool Subagents**

```javascript
Task.create({
  subagent_type: 'database-expert',
  prompt: `Execute handover 0424k Phase 1-7. Read F:\\GiljoAI_MCP\\handovers\\0424k_baseline_migration_org_tables.md for full instructions.

Your tasks:
1. Edit migrations/versions/baseline_v32_unified.py
2. Add organizations table (BEFORE users table)
3. Add org_id column to users table (nullable=True)
4. Add org_memberships table (AFTER users table)
5. Add org_id to products, agent_templates, tasks tables
6. Update downgrade() function
7. Verify with: python -m py_compile migrations/versions/baseline_v32_unified.py

IMPORTANT:
- organizations table MUST be created BEFORE users (FK dependency)
- users table MUST be created BEFORE org_memberships (FK dependency)
- org_id columns MUST be nullable=True (for backup restore compatibility)
- Do NOT change any existing column definitions, only ADD new ones`
})
```

### Step 4: Commit Your Work

```bash
git add -A && git commit -m "feat(0424k): Add organization tables to baseline migration

- Add organizations table with tenant_key, name, slug, settings, is_active
- Add org_memberships table with org_id, user_id, role, invited_by
- Add org_id column to users table (nullable for migration)
- Add org_id column to products, agent_templates, tasks tables
- Add all FK constraints and indexes
- Update downgrade() function

Handover: 0424k
Chain: 0424 Organization Hierarchy (Extended)
Impact: Fresh installs now create complete org schema

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 5: Update Chain Log

Update `prompts/0424_chain/chain_log.json`:
- Set 0424k status to "complete"
- Fill in tasks_completed, deviations, blockers_encountered
- Add notes_for_next for 0424l
- Add summary

### Step 6: Spawn Next Terminal

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
- Only ONE agent should spawn the next terminal
- Check if terminal 0424l is already running before executing

**Use Bash tool to EXECUTE this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0424l - Fresh Install Verify\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0424l. READ: F:\GiljoAI_MCP\handovers\0424l_fresh_install_verification.md - Verify fresh install and backup restore. Use Task subagents. Update chain_log.json when complete.\"' -Verb RunAs"
```

---

## Notes

**Why nullable=True for org_id columns?**
- Existing backups don't have org_id data
- Restore needs to work without constraint violations
- Post-restore migration script populates org_id from org_memberships
- NOT NULL can be enforced after data migration (already done in 0424j for live data)

**Table Creation Order (Critical):**
1. organizations (no dependencies)
2. users (depends on organizations for org_id FK)
3. org_memberships (depends on both organizations and users)
4. Everything else

---

**Next Handover:** 0424l (Fresh Install & Restore Verification)
