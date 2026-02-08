# Handover 0733: Security Patch - Enforce Tenant Isolation in API Endpoints

**Priority:** P1 - CRITICAL (Security Vulnerability)
**Estimated Effort:** 15-30 minutes
**Risk Level:** VERY LOW (minimal code change)
**Prerequisites:** None
**Blocks:** 0730 series (should be fixed before Service Response Models refactor)

---

## Executive Summary

Security vulnerability discovered in API endpoints that fail to pass `tenant_key` to service layer, allowing tenant isolation bypass. This quick patch enforces tenant filtering at the API layer by passing `current_user.tenant_key` to service calls.

**Vulnerability Class:** Same as Handover 0433 (Task Product Binding)
**Attack Vector:** User A can send messages to User B's projects by knowing project_id
**Scope:** API layer only (service fallbacks remain for 0731 cleanup)

---

## Background

### Current Architecture (Per-User Tenancy)
- Each user has unique `tenant_key` assigned at registration
- Organization hierarchy exists (0424 series) but sharing NOT yet implemented
- All resources (products, projects, tasks, jobs) are user-isolated

### Message Scope (Architecture Note)
**Messages belong to projects** and inherit project-level tenant isolation:
- Messages are project-scoped (NOT searchable across projects)
- Messages are NOT part of 360 Memory
- Messages are NOT part of any context sources
- Future: May become transcript/auditable, but not context-loaded
- **Critical:** Message access MUST be filtered by project's tenant_key

### Vulnerability Discovery
System-architect analysis found API endpoints missing `tenant_key` parameter:
- `api/endpoints/messages.py`: send_message endpoint
- Other endpoints TBD (check update_project_mission, switch_project)

### Service Layer Fallback Pattern
Service methods have "backward compatibility" fallback:
```python
if tenant_key:
    result = select(Project).where(Project.tenant_key == tenant_key, Project.id == project_id)
else:
    # Fallback - NO TENANT FILTER (VULNERABLE!)
    result = select(Project).where(Project.id == project_id)
```

When API doesn't pass `tenant_key`, fallback executes without isolation.

---

## Attack Scenario (Confirmed)

1. **User A** (tenant_abc) creates project `proj-123`
2. **User B** (tenant_xyz) discovers project ID somehow
3. **User B** calls `/api/messages/` with `project_id=proj-123`
4. API endpoint doesn't pass `tenant_key` → service receives `None`
5. Fallback executes: `select(Project).where(Project.id == project_id)` ← NO FILTER
6. **User B sends message to User A's project** ✅ VIOLATION

**Impact:** Violates "users will never collaborate on projects" policy

---

## Scope

### IN SCOPE (This Handover):
✅ Fix API endpoints to pass `tenant_key=current_user.tenant_key`
✅ Close security hole with minimal risk
✅ Test that tenant isolation works

### OUT OF SCOPE (Defer to 0730 series):
❌ Remove service layer fallback blocks
❌ Make `tenant_key` required in service signatures
❌ Add validation like Handover 0433
❌ Comprehensive test updates

**Rationale:** 0730 series will refactor these service methods anyway (Service Response Models). Better to fix both concerns together to avoid updating tests twice.

---

## Implementation

### Files to Modify (3-5 files estimated):

**Primary Fix:**
1. `api/endpoints/messages.py` - Add `tenant_key=current_user.tenant_key`

**Additional Endpoints (TBD - verify during implementation):**
2. Check for `update_project_mission` API endpoint
3. Check for `switch_project` API endpoint

### Code Changes

**File: `api/endpoints/messages.py` (Line ~64-71)**

**BEFORE:**
```python
result = await message_service.send_message(
    to_agents=message.to_agents,
    content=message.content,
    project_id=message.project_id,
    message_type=message.message_type,
    priority=message.priority,
    from_agent=message.from_agent,
    # MISSING: tenant_key parameter
)
```

**AFTER:**
```python
result = await message_service.send_message(
    to_agents=message.to_agents,
    content=message.content,
    project_id=message.project_id,
    message_type=message.message_type,
    priority=message.priority,
    from_agent=message.from_agent,
    tenant_key=current_user.tenant_key,  # ← ADD THIS LINE
)
```

**Pattern for Other Endpoints:**
1. Find endpoint method (e.g., `@router.post("/endpoint")`)
2. Check if it calls a service method with fallback pattern
3. Add `tenant_key=current_user.tenant_key` to service call

---

## Testing

### Manual Verification:
1. Create project as User A
2. Try to send message as User B to User A's project
3. Expected: 404 or permission denied (project not found for User B's tenant)
4. Actual: Should fail (tenant filter working)

### Automated Tests:
- No new tests needed (existing tests already use fixtures with tenant_key)
- Run existing test suite to verify no regressions:
  ```bash
  pytest tests/api/test_messages_api.py -v
  pytest tests/services/test_message_service.py -v
  ```

### Expected Results:
✅ All existing tests pass (tenant_key now provided, fallback not reached)
✅ No behavior changes for legitimate requests
✅ Cross-tenant requests fail (security restored)

---

## Success Criteria

**Code:**
- ✅ API endpoints pass `tenant_key=current_user.tenant_key` to service layer
- ✅ Service fallback blocks become unreachable (harmless dead code)
- ✅ No service signature changes (wait for 0731)

**Security:**
- ✅ User A cannot access User B's projects/tasks/jobs
- ✅ Messages remain tenant-isolated
- ✅ Attack scenario no longer works

**Testing:**
- ✅ All existing tests pass
- ✅ No regressions introduced

**Documentation:**
- ✅ Handover committed to repo
- ✅ Note added to 0730 series spec to remove fallbacks during refactor

---

## Rollback Plan

If issues arise:
```bash
# Revert the commit
git revert <commit-hash>

# Or remove the tenant_key parameter manually
# (Service fallback will activate again - not ideal but functional)
```

**Risk:** VERY LOW - just passing an existing value that should have been passed

---

## Follow-Up Work (0730 Series)

This quick patch is a **stopgap**. Full cleanup will happen in Handover 0730 series:

**0730 Series Scope (Service Response Models):**
1. Remove all fallback blocks from service methods
2. Make `tenant_key` required (no Optional)
3. Add validation: `if not tenant_key: raise ValidationError(...)`
4. Update ~100 test calls to include tenant_key
5. Apply 0433 pattern comprehensively

**Benefits of Two-Phase Approach:**
- Security hole closed NOW (15 min)
- Comprehensive cleanup DURING 0730 refactor (one big update)
- Tests updated once (for both exception handling and tenant isolation)

---

## Related Handovers

- **0433:** Task Product Binding and Tenant Isolation Fix (same vulnerability class)
- **0424:** Organization Hierarchy (context for future sharing model)
- **0730 Series:** Service Response Models (will include comprehensive tenant isolation cleanup)

---

## References

- Organization Hierarchy: `docs/organization.md`
- System Architecture Analysis: Deep-researcher agent (0728 session)
- Vulnerability Pattern: Same as 0433 (tenant_key fallback bypass)

---

**Created:** 2026-02-07
**Status:** READY
**Agent:** Backend-tester (implementation) + TDD-implementor (if test updates needed)
