# Handover 0127c: Deep Deprecated Code Removal

**Status:** Ready to Execute
**Priority:** P1 - HIGH
**Estimated Duration:** 2-3 days
**Agent Budget:** 150K tokens
**Depends On:** 0127a (Test Suite Fixed)

---

## Executive Summary

### Critical Issue

Deprecated code still exists throughout the codebase that can confuse future AI agents and developers. This includes entire deprecated modules, database fields, and scattered backup files that weren't caught in the initial 0127 cleanup.

### Files to Remove Completely

```
src/giljo_mcp/auth_legacy.py (672 lines) - DEPRECATED auth system
src/giljo_mcp/prompt_generator.py (~1000 lines) - DEPRECATED fat prompts
frontend/src/components/navigation/NavigationDrawer.vue.backup
tests/installer/test_platform_handlers.py.backup
src/giljo_mcp/mission_planner.py.backup
```

### Database Fields to Deprecate

```sql
-- Product table
Product.vision_document  -- DEPRECATED
Product.vision_text      -- DEPRECATED
Product.vision_source    -- DEPRECATED
Product.chunked          -- DEPRECATED

-- MCPAgentJob table
MCPAgentJob.prompt       -- DEPRECATED (use system_instructions + user_instructions)

-- Various tables
*.agent_id              -- Foreign keys to removed Agent model
```

---

## Why This Is Critical

### Agent Confusion Prevention

AI coding agents may:
- Import from deprecated modules by mistake
- Use old authentication patterns from auth_legacy.py
- Generate fat prompts using prompt_generator.py
- Reference deprecated database fields
- Follow old patterns found in backup files

### Code Quality Impact

- 2,000+ lines of dead code consuming space
- Deprecated patterns misleading developers
- Database schema confusion
- Increased maintenance burden

---

## Implementation Plan

### Phase 1: Verify References (2-3 hours)

**Step 1.1: Check auth_legacy.py Usage**

```bash
# Check if anything imports auth_legacy
grep -r "auth_legacy" --include="*.py" --exclude-dir=".git" .

# Check for specific functions from auth_legacy
grep -r "auto_login\|legacy_authenticate" --include="*.py" .

# Expected: No results (safe to delete)
```

**Step 1.2: Check prompt_generator.py Usage**

```bash
# Check for imports
grep -r "prompt_generator\|PromptGenerator" --include="*.py" .

# Check for fat prompt references
grep -r "fat_prompt\|full_prompt" --include="*.py" .

# May find: References in thin_prompt_generator.py (verify these are comments only)
```

**Step 1.3: Check Database Field Usage**

```bash
# Check for vision field usage
grep -r "vision_document\|vision_text\|vision_source\|chunked" --include="*.py" .

# Check for agent_id references
grep -r "agent_id" --include="*.py" .

# Document all occurrences for careful removal
```

### Phase 2: Remove Deprecated Files (1-2 hours)

**Step 2.1: Delete auth_legacy.py**

```bash
# Verify no imports
python -c "import ast; ast.parse(open('src/giljo_mcp/auth_legacy.py').read())"

# Check file is marked deprecated
head -20 src/giljo_mcp/auth_legacy.py | grep -i deprecated

# Delete if confirmed deprecated
rm src/giljo_mcp/auth_legacy.py

# Verify application still starts
python -c "from api import app; print('✅ App imports OK')"
```

**Step 2.2: Delete prompt_generator.py**

```bash
# Confirm it's the fat prompt generator
grep "class.*PromptGenerator" src/giljo_mcp/prompt_generator.py

# Ensure thin_prompt_generator.py exists as replacement
ls -la src/giljo_mcp/thin_prompt_generator.py

# Delete deprecated generator
rm src/giljo_mcp/prompt_generator.py

# Test imports
python -c "from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator"
```

**Step 2.3: Remove Backup Files**

```bash
# Remove remaining backup files
rm frontend/src/components/navigation/NavigationDrawer.vue.backup
rm tests/installer/test_platform_handlers.py.backup
rm src/giljo_mcp/mission_planner.py.backup

# Verify no other backup files remain
find . -name "*.backup" -o -name "*.bak"
```

### Phase 3: Clean Database Models (3-4 hours)

**Step 3.1: Update Product Model**

```python
# src/giljo_mcp/models.py

class Product(Base, TenantMixin):
    """Product model."""
    __tablename__ = 'products'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)

    # REMOVE THESE DEPRECATED FIELDS:
    # vision_document = Column(Text)  # DEPRECATED - remove
    # vision_text = Column(Text)      # DEPRECATED - remove
    # vision_source = Column(String)  # DEPRECATED - remove
    # chunked = Column(Boolean)       # DEPRECATED - remove

    # Keep these active fields:
    settings = Column(JSON)
    status = Column(String)
    # ... rest of model ...
```

**Step 3.2: Update MCPAgentJob Model**

```python
class MCPAgentJob(Base, TenantMixin):
    """Agent job model."""
    __tablename__ = 'mcp_agent_jobs'

    job_id = Column(String, primary_key=True)

    # REMOVE THIS:
    # prompt = Column(Text)  # DEPRECATED - remove

    # Keep these that replace it:
    system_instructions = Column(Text)
    user_instructions = Column(Text)
    # ... rest of model ...
```

**Step 3.3: Create Migration**

```python
# migrations/versions/xxx_remove_deprecated_fields.py

"""Remove deprecated fields

Revision ID: xxx
Create Date: 2025-11-10
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Drop deprecated columns from products table
    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_column('vision_document')
        batch_op.drop_column('vision_text')
        batch_op.drop_column('vision_source')
        batch_op.drop_column('chunked')

    # Drop deprecated prompt column from mcp_agent_jobs
    with op.batch_alter_table('mcp_agent_jobs') as batch_op:
        batch_op.drop_column('prompt')

    # Remove any agent_id foreign keys
    # List tables and constraints found in Phase 1

def downgrade():
    # Re-add columns if needed for rollback
    pass
```

### Phase 4: Clean Code References (2-3 hours)

**Step 4.1: Remove Deprecated Imports**

```python
# Find and remove any imports of deleted modules
# In any file that had:
from src.giljo_mcp import auth_legacy  # Remove
from src.giljo_mcp.auth_legacy import auto_login  # Remove
from src.giljo_mcp import prompt_generator  # Remove
from src.giljo_mcp.prompt_generator import PromptGenerator  # Remove
```

**Step 4.2: Update Code Using Deprecated Fields**

For any code referencing deprecated Product fields:

```python
# OLD (if found):
product.vision_document = vision_data  # Remove
product.vision_text = text  # Remove

# NEW (if needed):
product.settings['vision'] = vision_data  # Use settings JSON field
```

For any code referencing deprecated MCPAgentJob.prompt:

```python
# OLD:
job.prompt = full_prompt  # Remove

# NEW:
job.system_instructions = system_part
job.user_instructions = user_part
```

**Step 4.3: Update Tests**

Remove any tests for deprecated functionality:

```python
# Remove tests like:
def test_auth_legacy():  # Delete entire test
def test_fat_prompt_generation():  # Delete entire test
def test_product_vision_fields():  # Update to not test deprecated fields
```

### Phase 5: Validation (2-3 hours)

**Step 5.1: Verify No Broken Imports**

```bash
# Full import test
find . -name "*.py" -exec python -m py_compile {} \;

# Test critical imports
python -c "from api import app"
python -c "from src.giljo_mcp import models"
python -c "from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator"
```

**Step 5.2: Run Database Migration**

```bash
# Backup database first
pg_dump -U postgres giljo_mcp > backup_before_migration.sql

# Run migration
alembic upgrade head

# Verify schema changes
psql -U postgres -d giljo_mcp -c "\d products"
psql -U postgres -d giljo_mcp -c "\d mcp_agent_jobs"
```

**Step 5.3: Run Full Test Suite**

```bash
# All tests should pass
pytest tests/ -v

# Check for deprecation warnings
pytest tests/ -v -W error::DeprecationWarning
```

**Step 5.4: Start Application**

```bash
# Start and test basic flows
python startup.py --dev

# Test product creation/update (no vision fields)
# Test agent job creation (no prompt field)
```

---

## Special Considerations

### OrchestratorPromptGenerator

**Note:** `OrchestratorPromptGenerator` is marked deprecated but scheduled for removal in v4.0. DO NOT remove it in this handover - it may still be referenced.

### Thin Client Architecture

Ensure `ThinClientPromptGenerator` is working and all references to fat prompts are removed:

```python
# Verify thin client is active
grep -r "ThinClientPromptGenerator" --include="*.py" .
# Should find active usage

grep -r "OrchestratorPromptGenerator" --include="*.py" .
# May still be referenced (OK for now)
```

### Database Backup

**CRITICAL:** Before running migration:

```bash
# Full backup
pg_dump -U postgres giljo_mcp > pre_0127c_backup.sql

# Verify backup is complete
ls -lh pre_0127c_backup.sql
```

---

## Validation Checklist

- [ ] All deprecated files deleted (5 files)
- [ ] No broken imports in codebase
- [ ] Database migration created and tested
- [ ] Deprecated fields removed from models
- [ ] No references to deleted modules
- [ ] Test suite passes 100%
- [ ] Application starts successfully
- [ ] Basic workflows tested
- [ ] Database backup created

---

## Risk Assessment

**Risk 1: Breaking Hidden Dependencies**
- **Impact:** HIGH
- **Mitigation:** Thorough grep search before deletion

**Risk 2: Database Migration Failure**
- **Impact:** HIGH
- **Mitigation:** Full backup before migration, test on dev DB first

**Risk 3: Runtime Errors from Removed Fields**
- **Impact:** MEDIUM
- **Mitigation:** Comprehensive testing after changes

---

## Rollback Plan

If issues arise:

```bash
# Restore database
psql -U postgres -d giljo_mcp < pre_0127c_backup.sql

# Git restore files
git checkout HEAD -- src/giljo_mcp/auth_legacy.py
git checkout HEAD -- src/giljo_mcp/prompt_generator.py

# Revert migration
alembic downgrade -1
```

---

## Expected Outcomes

### Before
- 2,000+ lines of deprecated code
- Confusing deprecated patterns
- Risk of agents using old code
- Database schema with unused fields

### After
- Clean codebase with only active code
- Clear patterns for agents to follow
- Simplified database schema
- Reduced maintenance burden

### Metrics
- Lines removed: ~2,000
- Files deleted: 5
- Database fields removed: 5+
- Test suite: Still 100% passing

---

**Created:** 2025-11-10
**Priority:** P1 - HIGH
**Complete After:** 0127a (Test Suite)