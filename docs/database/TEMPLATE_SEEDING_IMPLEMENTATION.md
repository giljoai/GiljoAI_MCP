# Tenant Template Seeding - Implementation Guide

**Quick Reference for Implementing Tenant-Driven Template System**

---

## Quick Start

### 1. Run Database Migration

```bash
cd /f/GiljoAI_MCP
alembic revision --autogenerate -m "Add system template tracking to agent_templates"
# Edit the generated migration file (see Section 3 for content)
alembic upgrade head
```

### 2. Add Seeding Function

**File:** `src/giljo_mcp/template_seeding.py` (new file)

```python
"""
Tenant template seeding for GiljoAI MCP.
Automatically provisions default agent templates for new tenants.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from .models import AgentTemplate
from .template_manager import UnifiedTemplateManager

logger = logging.getLogger(__name__)


def seed_tenant_templates(
    session: Session,
    tenant_key: str,
    product_id: Optional[str] = None
) -> int:
    """
    Seed default agent templates for a new tenant.

    Args:
        session: Database session
        tenant_key: Tenant identifier
        product_id: Optional product scope (None = global tenant templates)

    Returns:
        Number of templates created

    Raises:
        ValueError: If seeding fails
    """
    # Check for existing templates
    existing_count = session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == tenant_key
    ).count()

    if existing_count > 0:
        logger.info(f"Tenant {tenant_key} already has {existing_count} templates - skipping seed")
        return 0

    # Load system templates
    template_mgr = UnifiedTemplateManager()
    system_templates = template_mgr._legacy_templates  # 6 default templates

    created_count = 0
    created_at = datetime.now(timezone.utc)

    for role, content in system_templates.items():
        try:
            # Create tenant template from system template
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,

                # Template definition
                name=role,
                category="role",
                role=role,
                template_content=content,
                variables=template_mgr.extract_variables(content) if hasattr(template_mgr, 'extract_variables') else [],
                behavioral_rules=template_mgr.get_behavioral_rules(role),
                success_criteria=template_mgr.get_success_criteria(role),

                # System template tracking (NEW)
                is_system_template=False,  # This is a COPY
                system_template_id=None,  # Could reference system template registry
                system_template_version="2.0.0",  # Current system version
                customized=False,  # Not yet modified by tenant

                # Standard metadata
                version="2.0.0",
                is_active=True,
                is_default=(role == "orchestrator"),
                preferred_tool="claude",

                # Audit trail
                created_by="system",
                created_at=created_at,
                meta_data={
                    "source": "seed_tenant_templates",
                    "seeded_at": created_at.isoformat(),
                    "seeded_for_tenant": tenant_key
                }
            )

            session.add(template)
            created_count += 1

        except Exception as e:
            logger.error(f"Failed to create template '{role}' for tenant {tenant_key}: {e}")
            raise ValueError(f"Template seeding failed for role '{role}': {e}") from e

    # Commit all templates atomically
    try:
        session.commit()
        logger.info(f"Successfully seeded {created_count} templates for tenant {tenant_key}")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to commit templates for tenant {tenant_key}: {e}")
        raise ValueError(f"Template seeding commit failed: {e}") from e

    return created_count


def mark_template_customized(
    session: Session,
    template_id: str,
    tenant_key: str
) -> bool:
    """
    Mark a template as customized when user modifies it.

    Args:
        session: Database session
        template_id: Template ID to mark
        tenant_key: Tenant key for security verification

    Returns:
        True if template was marked, False if already customized
    """
    template = session.query(AgentTemplate).filter(
        AgentTemplate.id == template_id,
        AgentTemplate.tenant_key == tenant_key  # Security: verify tenant ownership
    ).first()

    if not template:
        raise ValueError(f"Template {template_id} not found for tenant {tenant_key}")

    if template.customized:
        logger.debug(f"Template {template_id} already marked as customized")
        return False

    template.customized = True
    template.customized_at = datetime.now(timezone.utc)
    session.commit()

    logger.info(f"Marked template {template_id} ({template.name}) as customized for tenant {tenant_key}")
    return True


def find_upgradeable_templates(
    session: Session,
    tenant_key: str,
    new_system_version: str = "3.0.0"
) -> list[AgentTemplate]:
    """
    Find templates eligible for auto-upgrade to new system version.

    Args:
        session: Database session
        tenant_key: Tenant identifier
        new_system_version: New system template version

    Returns:
        List of templates that can be safely auto-upgraded
    """
    return session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == tenant_key,
        AgentTemplate.customized == False,  # NOT customized
        AgentTemplate.system_template_version != new_system_version,  # Outdated
        AgentTemplate.is_active == True
    ).all()
```

### 3. Create Migration File

**File:** `migrations/versions/YYYYMMDD_add_system_template_tracking.py`

```python
"""Add system template tracking fields

Revision ID: add_system_template_tracking
Revises: add_template_mgmt
Create Date: 2025-10-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "add_system_template_tracking"
down_revision = "add_template_mgmt"  # Update to your latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Add system template tracking fields to agent_templates table"""

    # Add new columns (nullable initially for existing data)
    op.add_column("agent_templates",
        sa.Column("is_system_template", sa.Boolean(), nullable=True,
                  comment="True if this is a system-provided template (immutable)")
    )
    op.add_column("agent_templates",
        sa.Column("system_template_id", sa.String(36), nullable=True,
                  comment="Reference to system template this was copied from")
    )
    op.add_column("agent_templates",
        sa.Column("system_template_version", sa.String(20), nullable=True,
                  comment="Version of system template at time of copy")
    )
    op.add_column("agent_templates",
        sa.Column("customized", sa.Boolean(), nullable=True,
                  comment="True if user has modified this tenant template")
    )
    op.add_column("agent_templates",
        sa.Column("customized_at", sa.DateTime(timezone=True), nullable=True,
                  comment="When template was first customized by tenant")
    )

    # Backfill existing data (mark as customized for safety)
    op.execute("""
        UPDATE agent_templates
        SET
            is_system_template = false,
            customized = true,
            system_template_version = version
        WHERE is_system_template IS NULL
    """)

    # Make boolean columns non-nullable after backfill
    op.alter_column("agent_templates", "is_system_template", nullable=False)
    op.alter_column("agent_templates", "customized", nullable=False)

    # Add partial indexes for performance
    op.create_index(
        "idx_template_system",
        "agent_templates",
        ["is_system_template"],
        postgresql_where=sa.text("is_system_template = true")
    )
    op.create_index(
        "idx_template_customized",
        "agent_templates",
        ["customized"],
        postgresql_where=sa.text("customized = true")
    )
    op.create_index(
        "idx_template_system_ref",
        "agent_templates",
        ["system_template_id"]
    )


def downgrade():
    """Remove system template tracking fields"""

    # Drop indexes first
    op.drop_index("idx_template_system_ref", "agent_templates")
    op.drop_index("idx_template_customized", "agent_templates")
    op.drop_index("idx_template_system", "agent_templates")

    # Drop columns
    op.drop_column("agent_templates", "customized_at")
    op.drop_column("agent_templates", "customized")
    op.drop_column("agent_templates", "system_template_version")
    op.drop_column("agent_templates", "system_template_id")
    op.drop_column("agent_templates", "is_system_template")
```

### 4. Integrate with Installer

**File:** `installer/core/config.py` (modify existing)

Add seeding call after first admin creation:

```python
# Around line 700 (after SetupState creation)
from src.giljo_mcp.template_seeding import seed_tenant_templates

def _seed_default_templates(self, session: Session, tenant_key: str) -> None:
    """Seed default agent templates for tenant"""
    try:
        count = seed_tenant_templates(session, tenant_key, product_id=None)
        logger.info(f"Seeded {count} default templates for tenant {tenant_key}")
    except Exception as e:
        logger.warning(f"Template seeding failed (non-critical): {e}")
        # Non-critical - templates can be added later via API

# Call in seed_database() after SetupState creation:
def seed_database(self) -> bool:
    # ... existing code ...

    # After SetupState creation
    setup_state = SetupState.create_or_update(
        session,
        tenant_key=tenant_key,
        database_initialized=True,
        # ... other fields ...
    )
    session.commit()

    # NEW: Seed default templates
    self._seed_default_templates(session, tenant_key)

    return True
```

### 5. Update Template Manager

**File:** `src/giljo_mcp/template_manager.py` (add method)

```python
# Add to UnifiedTemplateManager class

def extract_variables(self, content: str) -> list[str]:
    """
    Extract variable names from template content.

    Args:
        content: Template content with {variable} placeholders

    Returns:
        List of unique variable names
    """
    import re
    seen = set()
    result = []
    for var in re.findall(r"\{(\w+)\}", content):
        if var not in seen:
            seen.add(var)
            result.append(var)
    return result
```

---

## Testing Checklist

### Unit Tests

**File:** `tests/unit/test_template_seeding.py`

```python
import pytest
from src.giljo_mcp.template_seeding import seed_tenant_templates, mark_template_customized
from src.giljo_mcp.models import AgentTemplate


def test_seed_tenant_templates_creates_six_templates(db_session):
    """Test seeding creates all 6 default templates"""
    count = seed_tenant_templates(db_session, "test-tenant-1")
    assert count == 6

    templates = db_session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == "test-tenant-1"
    ).all()
    assert len(templates) == 6

    roles = {t.role for t in templates}
    expected_roles = {"orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"}
    assert roles == expected_roles


def test_seed_tenant_templates_marks_not_customized(db_session):
    """Test seeded templates are marked as not customized"""
    seed_tenant_templates(db_session, "test-tenant-2")

    templates = db_session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == "test-tenant-2"
    ).all()

    for template in templates:
        assert template.customized is False
        assert template.customized_at is None
        assert template.system_template_version == "2.0.0"


def test_seed_tenant_templates_skips_if_exists(db_session):
    """Test seeding skips if tenant already has templates"""
    count1 = seed_tenant_templates(db_session, "test-tenant-3")
    assert count1 == 6

    count2 = seed_tenant_templates(db_session, "test-tenant-3")
    assert count2 == 0  # Skipped

    total = db_session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == "test-tenant-3"
    ).count()
    assert total == 6  # Still only 6


def test_mark_template_customized(db_session):
    """Test marking template as customized"""
    seed_tenant_templates(db_session, "test-tenant-4")

    template = db_session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == "test-tenant-4",
        AgentTemplate.role == "orchestrator"
    ).first()

    # Mark as customized
    result = mark_template_customized(db_session, template.id, "test-tenant-4")
    assert result is True

    # Verify
    db_session.refresh(template)
    assert template.customized is True
    assert template.customized_at is not None

    # Second call returns False (already customized)
    result2 = mark_template_customized(db_session, template.id, "test-tenant-4")
    assert result2 is False


def test_tenant_isolation(db_session):
    """Test templates are isolated per tenant"""
    seed_tenant_templates(db_session, "tenant-a")
    seed_tenant_templates(db_session, "tenant-b")

    tenant_a_templates = db_session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == "tenant-a"
    ).all()
    tenant_b_templates = db_session.query(AgentTemplate).filter(
        AgentTemplate.tenant_key == "tenant-b"
    ).all()

    assert len(tenant_a_templates) == 6
    assert len(tenant_b_templates) == 6

    # Verify no cross-tenant IDs
    a_ids = {t.id for t in tenant_a_templates}
    b_ids = {t.id for t in tenant_b_templates}
    assert len(a_ids & b_ids) == 0  # No overlap
```

### Integration Tests

**File:** `tests/integration/test_installer_template_seeding.py`

```python
import pytest
from installer.core.config import ConfigManager
from src.giljo_mcp.models import AgentTemplate, SetupState


def test_installer_seeds_templates_on_first_setup(test_db):
    """Test installer seeds templates during first setup"""
    config_mgr = ConfigManager()

    # Run installer seed_database()
    success = config_mgr.seed_database()
    assert success is True

    # Verify templates created
    with test_db.get_session() as session:
        templates = session.query(AgentTemplate).all()
        assert len(templates) >= 6  # At least 6 for default tenant

        # Verify setup state
        setup_state = session.query(SetupState).first()
        assert setup_state is not None
        assert setup_state.database_initialized is True


def test_multi_tenant_template_isolation(test_db):
    """Test multiple tenants get independent template sets"""
    from src.giljo_mcp.template_seeding import seed_tenant_templates

    with test_db.get_session() as session:
        # Seed 3 different tenants
        seed_tenant_templates(session, "company-a")
        seed_tenant_templates(session, "company-b")
        seed_tenant_templates(session, "company-c")

        # Verify each has 6 templates
        for tenant in ["company-a", "company-b", "company-c"]:
            count = session.query(AgentTemplate).filter(
                AgentTemplate.tenant_key == tenant
            ).count()
            assert count == 6

        # Verify total is 18 (3 tenants × 6 templates)
        total = session.query(AgentTemplate).count()
        assert total == 18
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Create migration file: `add_system_template_tracking.py`
- [ ] Review migration SQL (verify indexes, constraints)
- [ ] Test migration on development database
- [ ] Verify rollback procedure works
- [ ] Create `template_seeding.py` module
- [ ] Add unit tests for seeding functions
- [ ] Add integration tests for installer
- [ ] Update `installer/core/config.py` integration
- [ ] Run full test suite (`pytest tests/`)
- [ ] Test with fresh database (no existing templates)
- [ ] Test with existing database (migration path)

### Deployment Steps

```bash
# 1. Backup production database
pg_dump -U postgres -d giljo_mcp > backup_before_template_migration.sql

# 2. Run migration
cd /f/GiljoAI_MCP
alembic upgrade head

# 3. Verify migration
psql -U postgres -d giljo_mcp -c "\d agent_templates"
# Should show 5 new columns: is_system_template, system_template_id, etc.

# 4. Test seeding with new tenant
python scripts/test_template_seeding.py --tenant test-tenant-001

# 5. Verify isolation
psql -U postgres -d giljo_mcp -c "
SELECT tenant_key, COUNT(*) FROM agent_templates GROUP BY tenant_key;
"
```

### Post-Deployment Validation

```sql
-- 1. Verify all templates have metadata
SELECT COUNT(*) as missing_metadata
FROM agent_templates
WHERE is_system_template IS NULL OR customized IS NULL;
-- Expected: 0

-- 2. Check customization distribution
SELECT
    customized,
    COUNT(*) as template_count
FROM agent_templates
GROUP BY customized;

-- 3. Verify index usage
EXPLAIN ANALYZE
SELECT * FROM agent_templates
WHERE tenant_key = 'test-tenant'
  AND customized = false;
-- Should use idx_template_tenant or idx_template_customized

-- 4. Test cross-tenant isolation
SELECT COUNT(*) FROM agent_templates t1
JOIN agent_templates t2 ON t1.id = t2.id AND t1.tenant_key != t2.tenant_key;
-- Expected: 0
```

---

## Troubleshooting

### Issue: Migration Fails on Existing Data

**Symptom:** `NOT NULL constraint failed: agent_templates.is_system_template`

**Solution:**
```sql
-- Manually backfill before running migration
UPDATE agent_templates
SET is_system_template = false, customized = true
WHERE is_system_template IS NULL;
```

### Issue: Seeding Creates Duplicate Templates

**Symptom:** `IntegrityError: duplicate key value violates unique constraint`

**Solution:**
- Check `uq_template_product_name_version` constraint
- Ensure seeding function checks for existing templates first
- Verify tenant_key is correct (not reusing existing tenant)

### Issue: Performance Degradation After Migration

**Symptom:** Template queries slower than expected

**Solution:**
```sql
-- Reindex tables
REINDEX TABLE agent_templates;

-- Analyze table for query planner
ANALYZE agent_templates;

-- Verify index usage
EXPLAIN ANALYZE SELECT * FROM agent_templates WHERE tenant_key = 'test';
```

---

## Quick Reference

### Seed Templates Manually

```python
from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.template_seeding import seed_tenant_templates

db_manager = get_db_manager()
with db_manager.get_session() as session:
    count = seed_tenant_templates(session, "my-tenant-key")
    print(f"Created {count} templates")
```

### Mark Template as Customized

```python
from src.giljo_mcp.template_seeding import mark_template_customized

with db_manager.get_session() as session:
    mark_template_customized(session, template_id, tenant_key)
```

### Find Upgradeable Templates

```python
from src.giljo_mcp.template_seeding import find_upgradeable_templates

with db_manager.get_session() as session:
    templates = find_upgradeable_templates(session, "my-tenant", "3.0.0")
    print(f"Found {len(templates)} templates to upgrade")
```

---

## Documentation Updates

### Files to Update

- [ ] `docs/CLAUDE.md` - Add template seeding section
- [ ] `docs/INSTALLATION_FLOW_PROCESS.md` - Document automatic seeding
- [ ] `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - Update database schema
- [ ] `api/endpoints/templates.py` - Add customization tracking
- [ ] `README.md` - Update feature list

### CLAUDE.md Addition

```markdown
## Agent Templates

**Automatic Seeding:** Each tenant receives 6 default agent templates on first setup:
- orchestrator - Project coordination (enhanced v2.0)
- analyzer - System analysis
- implementer - Code implementation
- tester - Quality assurance
- reviewer - Code review
- documenter - Documentation

**Customization:** Templates can be modified per tenant. System tracks:
- `customized` flag - Marks user-modified templates
- `system_template_version` - Tracks system template version at copy time
- Upgrade path - Auto-upgrade non-customized templates on system updates

**Database:** All templates scoped to `tenant_key` for complete isolation
```

---

## Next Steps

1. **Immediate:** Create migration file
2. **Short-term:** Implement seeding function
3. **Testing:** Run full test suite
4. **Deployment:** Stage → Production migration
5. **Monitoring:** Track seeding success rate

**Estimated Time:** 8-12 hours total
**Priority:** High (enables multi-tenant template management)
**Risk:** Low (additive changes only)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Status:** Ready for Implementation
