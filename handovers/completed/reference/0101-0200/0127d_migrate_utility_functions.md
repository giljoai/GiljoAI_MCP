# Handover 0127d: Migrate Utility Functions

**Status:** Ready to Execute
**Priority:** P2 - MEDIUM
**Estimated Duration:** 1-2 days
**Agent Budget:** 100K tokens
**Depends On:** 0127c (Complete)

---

## Executive Summary

### The Problem

During the endpoint modularization (Handovers 0124-0126), several utility functions were left in the old monolithic endpoint files (now backed up) instead of being migrated to the new modular structure or to appropriate service layers.

### Known Unmigrated Functions

From **0127 Completion Report**:
- `purge_expired_deleted_projects()` - Project cleanup utility
- `validate_active_agent_limit()` - Template validation
- `validate_project_path()` - Product path validation
- Various orchestrator protection functions

### The Goal

Locate these orphaned utility functions and migrate them to appropriate locations:
- Service layer (preferred)
- Utility modules
- Helper files within endpoint modules

---

## Objectives

### Primary Objectives

✅ **Locate Orphaned Functions** - Find all utility functions not migrated
✅ **Determine Proper Homes** - Decide where each function belongs
✅ **Migrate Functions** - Move to appropriate locations
✅ **Update Imports** - Fix all references to moved functions
✅ **Maintain Functionality** - Zero breaking changes

### Success Criteria

- All identified utility functions migrated
- No orphaned functions in backup files
- All imports updated and working
- Application starts and runs normally
- Tests pass (where applicable)

---

## Implementation Plan

### Phase 1: Discovery (2-3 hours)

**Step 1.1: Search for Known Functions**

```bash
# Search for the known unmigrated functions
grep -r "purge_expired_deleted_projects" . --include="*.py"
grep -r "validate_active_agent_limit" . --include="*.py"
grep -r "validate_project_path" . --include="*.py"
```

**Step 1.2: Check Backup Files for More**

```bash
# List all backup files from 0124-0126
ls -la api/endpoints/*.backup

# Search for function definitions in backups
grep "^def " api/endpoints/*.backup | grep -v "__" | sort -u
```

**Step 1.3: Compare Old vs New**

For each function found in backup files:
1. Check if it exists in new modular structure
2. Check if it's imported/used anywhere
3. Determine if it's actually needed

### Phase 2: Migration Planning (1-2 hours)

**Step 2.1: Categorize Functions**

Create categories:
1. **Service Layer Candidates** - Business logic functions
2. **Utility Functions** - Generic helpers
3. **Endpoint Helpers** - HTTP-specific utilities
4. **Deprecated/Unused** - Can be deleted

**Step 2.2: Determine Destinations**

| Function | Current Location | Destination | Reason |
|----------|-----------------|-------------|---------|
| purge_expired_deleted_projects | projects.backup? | ProjectService | Business logic |
| validate_active_agent_limit | templates.backup? | TemplateService | Validation logic |
| validate_project_path | products.backup? | ProductService | Path validation |
| ... | ... | ... | ... |

### Phase 3: Migration Execution (3-4 hours)

**Step 3.1: Migrate to Services**

For functions that belong in service layer:

```python
# Example: Add to ProjectService
class ProjectService:
    # ... existing methods ...

    async def purge_expired_deleted_projects(
        self,
        days_before_purge: int = 30
    ) -> int:
        """
        Purge soft-deleted projects older than specified days.

        Args:
            days_before_purge: Days to wait before permanent deletion

        Returns:
            Number of projects purged
        """
        async with self.db_manager.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days_before_purge)

            # Find expired soft-deleted projects
            result = await session.execute(
                select(Project).where(
                    and_(
                        Project.tenant_key == self.tenant_key,
                        Project.status == 'deleted',
                        Project.deleted_at < cutoff_date
                    )
                )
            )

            projects_to_purge = result.scalars().all()
            count = len(projects_to_purge)

            # Permanently delete
            for project in projects_to_purge:
                await session.delete(project)

            await session.commit()
            logger.info(f"Purged {count} expired deleted projects")

            return count
```

**Step 3.2: Create Utility Modules**

If needed, create new utility modules:

```python
# api/endpoints/projects/utils.py
"""Utility functions for project endpoints."""

def validate_project_name(name: str) -> bool:
    """Validate project name format."""
    # Implementation
    pass

def sanitize_project_path(path: str) -> str:
    """Sanitize project path for filesystem."""
    # Implementation
    pass
```

**Step 3.3: Update Imports**

For each migrated function:

```python
# OLD (in endpoint file)
from somewhere import purge_expired_deleted_projects

# NEW (after migration to service)
from .dependencies import get_project_service

@router.post("/purge-deleted")
async def purge_deleted_projects(
    service: ProjectService = Depends(get_project_service)
):
    count = await service.purge_expired_deleted_projects()
    return {"purged": count}
```

### Phase 4: Cleanup (1-2 hours)

**Step 4.1: Remove from Backup Files**

After confirming migration:
1. Document what was migrated
2. Note that functions are now in proper locations
3. Backup files can remain as-is (already .backup)

**Step 4.2: Update Documentation**

Create migration record:

```markdown
## Utility Functions Migration Record

### From projects.py.backup:
- purge_expired_deleted_projects → ProjectService.purge_expired_deleted_projects()
- validate_project_name → projects/utils.py

### From templates.py.backup:
- validate_active_agent_limit → TemplateService.validate_active_agent_limit()
```

### Phase 5: Validation (1-2 hours)

**Step 5.1: Test Each Migration**

```bash
# Test that imports work
python -c "from src.giljo_mcp.services import ProjectService"

# Test application starts
python startup.py --dev
```

**Step 5.2: Test Functionality**

If endpoints use these functions:
```bash
# Test specific endpoints
curl -X POST http://localhost:7272/api/v1/projects/purge-deleted
```

---

## Special Considerations

### Orchestrator Protection Functions

Some functions might be security/protection related:
- Rate limiting checks
- Permission validations
- Tenant isolation checks

These should go to:
- Middleware (if they're cross-cutting)
- Service layer (if they're domain-specific)
- Security module (if they're auth-related)

### Database Utility Functions

Functions that directly operate on database might need:
- Session management updates
- Async/await conversion
- Tenant key injection

### Path Validation Functions

Path-related utilities should consider:
- Cross-platform compatibility (Windows/Linux/Mac)
- Security (path traversal prevention)
- Project isolation

---

## Validation Checklist

- [ ] All known utility functions located
- [ ] Migration destinations determined
- [ ] Functions migrated to appropriate locations
- [ ] All imports updated
- [ ] No broken references
- [ ] Application starts successfully
- [ ] Affected endpoints tested
- [ ] Documentation updated

---

## Risk Assessment

**Risk 1: Breaking Working Endpoints**
- **Impact:** MEDIUM
- **Mitigation:** Test each endpoint after migration

**Risk 2: Missing Dependencies**
- **Impact:** LOW
- **Mitigation:** Check all imports before deletion

**Risk 3: Changing Function Behavior**
- **Impact:** MEDIUM
- **Mitigation:** Preserve exact logic during migration

---

## Expected Outcomes

### Before
- Utility functions scattered in backup files
- Unclear where functions belong
- Risk of losing functionality

### After
- All utilities in proper locations
- Service layer contains business logic
- Clean separation of concerns
- Maintainable code structure

---

## Next Steps

After completing this handover:
1. Proceed to 0128 (Backend Deep Cleanup parent task)
2. Then 0128a (Split models.py)
3. Continue sequentially through roadmap

---

**Created:** 2025-11-10
**Priority:** P2 - MEDIUM
**Estimated:** 1-2 days
**Sequential Position:** After 0127c, Before 0128