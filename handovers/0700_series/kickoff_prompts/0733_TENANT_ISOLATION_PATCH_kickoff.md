# Kickoff Prompt: Handover 0733 - Tenant Isolation API Security Patch

**Agent Type:** backend-integration-tester (or tdd-implementor)
**Branch:** feature/0700-code-cleanup-series
**Priority:** P1 - CRITICAL (Security Vulnerability)
**Estimated Effort:** 15-30 minutes
**Session Type:** Fresh agent, independent execution

---

## Mission

Fix security vulnerability in API endpoints that fail to pass `tenant_key` to service layer, allowing tenant isolation bypass. This is a **quick 1-line patch** to close the security hole before the 0730 Service Response Models refactor.

**Vulnerability Class:** Same as Handover 0433 (tenant_key fallback bypass)
**Attack Vector:** User A can send messages to User B's projects by knowing project_id
**Fix:** Add `tenant_key=current_user.tenant_key` to service calls in API endpoints

---

## Context

### Architecture Overview

**GiljoAI MCP v1.0** - Multi-tenant Python/FastAPI/PostgreSQL/Vue3 agent orchestration server

**Tenant Isolation Model (Per-User):**
- Each user has unique `tenant_key` assigned at registration
- All resources are user-owned and tenant-isolated
- Organization hierarchy exists (Handover 0424) but sharing NOT implemented yet

**Ownership Chain:**
```
Org → Users → Products → Projects → Tasks → Jobs → Messages
```

**Message Scope (CRITICAL):**
- Messages belong to projects (project-scoped)
- Messages are **private to project owner**
- NOT searchable across projects
- NOT part of 360 Memory or context sources
- Future: May become auditable/transcript, but never context-loaded

**Key Principle:** Users cannot access other users' projects/messages (full isolation)

**Reference:** `docs/organization.md` for complete hierarchy

---

## Vulnerability Details

### Service Layer Fallback Pattern

Service methods have "backward compatibility" fallback blocks:

```python
# Example from project_service.py
async def update_project_mission(project_id, mission, tenant_key=None):
    if tenant_key:
        # SAFE - Tenant filtered
        result = await session.execute(
            select(Project).where(
                Project.tenant_key == tenant_key,
                Project.id == project_id
            )
        )
    else:
        # VULNERABLE - No tenant filter!
        result = await session.execute(
            select(Project).where(Project.id == project_id)
        )
```

**Files with Fallback Pattern:**
1. `src/giljo_mcp/services/project_service.py` (2 methods)
2. `src/giljo_mcp/services/message_service.py` (1 method)

### API Endpoint Vulnerability

**Primary Issue:** API endpoints don't pass `tenant_key` to service layer

**File:** `api/endpoints/messages.py` (Line ~64-71)

```python
# CURRENT (VULNERABLE):
result = await message_service.send_message(
    to_agents=message.to_agents,
    content=message.content,
    project_id=message.project_id,
    message_type=message.message_type,
    priority=message.priority,
    from_agent=message.from_agent,
    # ❌ MISSING: tenant_key parameter
)
```

### Attack Scenario (Confirmed)

1. **User A** (tenant_abc) creates project `proj-123`
2. **User B** (tenant_xyz) discovers project ID somehow
3. **User B** calls `/api/messages/` with `project_id=proj-123`
4. API doesn't pass `tenant_key` → service receives `None`
5. Fallback executes: `select(Project).where(Project.id == project_id)` ← NO FILTER
6. **User B sends message to User A's project** ✅ VIOLATION

**Impact:** Violates "users cannot access other users' projects" policy

---

## Implementation Plan

### Phase 1: Locate Vulnerable Endpoints

**Search for service calls missing tenant_key:**

```bash
# Find message_service.send_message calls
grep -n "message_service.send_message" api/endpoints/messages.py

# Check for project_service methods (if called from API)
grep -n "update_project_mission\|delete_project" api/endpoints/projects.py
```

**Expected Files to Fix:**
1. `api/endpoints/messages.py` - CONFIRMED vulnerable
2. `api/endpoints/projects.py` - TBD (verify during implementation)

### Phase 2: Apply Fix

**Pattern for ALL endpoints:**

```python
# BEFORE (VULNERABLE):
result = await service_method(
    param1=value1,
    param2=value2,
    # Missing tenant_key
)

# AFTER (SECURE):
result = await service_method(
    param1=value1,
    param2=value2,
    tenant_key=current_user.tenant_key,  # ← ADD THIS LINE
)
```

**Primary Fix (REQUIRED):**

**File:** `api/endpoints/messages.py` (Line ~64-71)

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

**Additional Endpoints (if found):**
- Apply same pattern to any other endpoint calling service methods with fallback blocks
- Check `api/endpoints/projects.py` for `update_project_mission` or `delete_project` calls

### Phase 3: Testing

**Manual Verification (Optional):**
1. Start server: `python startup.py --dev`
2. Create project as User A
3. Try to send message as User B to User A's project
4. Expected: 404 or permission denied (project not found for User B's tenant)

**Automated Tests (REQUIRED):**

```bash
# Run existing tests - should all pass with fix
pytest tests/api/test_messages_api.py -v
pytest tests/services/test_message_service.py -v

# Run integration tests
pytest tests/integration/ -v -k message
```

**Expected Results:**
- ✅ All existing tests pass (tenant_key now provided, fallback not reached)
- ✅ No new test failures
- ✅ Service fallback blocks become unreachable (harmless dead code until 0730)

### Phase 4: Documentation & Commit

**Create completion report:**

```markdown
# Handover 0733 - Completion Report

## Changes Made
- [ ] Fixed api/endpoints/messages.py (added tenant_key)
- [ ] Fixed api/endpoints/XXX.py (if applicable)
- [ ] Total files modified: X

## Testing Results
- [ ] pytest tests/api/test_messages_api.py: PASS
- [ ] pytest tests/services/test_message_service.py: PASS
- [ ] pytest tests/integration/ -k message: PASS

## Security Verification
- [ ] Confirmed tenant_key passed to all vulnerable service calls
- [ ] Service fallback blocks now unreachable
- [ ] Attack scenario no longer works

## Files Modified
1. api/endpoints/messages.py - Line XX (added tenant_key=current_user.tenant_key)
2. [other files if any]

## Next Steps
- Handover 0730 series will remove fallback blocks during Service Response Models refactor
```

**Commit Message:**

```
fix(0733): Enforce tenant isolation in message API endpoints

SECURITY FIX - Closes tenant bypass vulnerability

Problem:
- API endpoints didn't pass tenant_key to service layer
- Service fallback allowed cross-tenant message sending
- User B could send messages to User A's projects

Solution:
- Added tenant_key=current_user.tenant_key to service calls
- Service fallback blocks now unreachable (dead code)
- Full cleanup deferred to Handover 0730 series

Attack vector closed: Cross-tenant message access
Vulnerability class: Same as Handover 0433

Related: #0733
Follow-up: Handover 0730 series (remove fallback blocks)

```

---

## Success Criteria

**Code:**
- ✅ API endpoints pass `tenant_key=current_user.tenant_key` to service layer
- ✅ At least 1 file fixed (messages.py), possibly 2-3 total
- ✅ No service signature changes (wait for 0730)

**Security:**
- ✅ User A cannot send messages to User B's projects
- ✅ Messages remain tenant-isolated
- ✅ Attack scenario no longer works

**Testing:**
- ✅ All existing tests pass (no regressions)
- ✅ Tests confirm tenant_key is now provided

**Documentation:**
- ✅ Completion report created
- ✅ Changes committed with proper message
- ✅ Handover 0733 marked COMPLETE

---

## Scope Boundaries

### IN SCOPE (This Handover):
✅ Fix API endpoints to pass tenant_key
✅ Close security hole with minimal risk
✅ Test that tenant isolation works
✅ Document changes

### OUT OF SCOPE (Defer to 0730 series):
❌ Remove service layer fallback blocks
❌ Make `tenant_key` required in service signatures
❌ Add validation like Handover 0433
❌ Comprehensive test updates

**Rationale:** 0730 series will refactor these service methods anyway (Service Response Models). Better to fix both concerns together to avoid updating tests twice.

---

## Key Files Reference

**Read for Context:**
1. `handovers/0733_TENANT_ISOLATION_API_SECURITY_PATCH.md` - Full handover spec
2. `docs/organization.md` - Organization hierarchy and isolation model
3. `handovers/0433_task_product_binding_and_tenant_isolation_fix.md` - Similar vulnerability pattern

**Files to Modify:**
1. `api/endpoints/messages.py` - PRIMARY FIX (confirmed vulnerable)
2. `api/endpoints/projects.py` - Check for vulnerable calls (TBD)

**Service Layer (DO NOT MODIFY - fallbacks will be removed in 0730):**
1. `src/giljo_mcp/services/message_service.py` - Has fallback block
2. `src/giljo_mcp/services/project_service.py` - Has fallback blocks

**Tests to Run:**
1. `tests/api/test_messages_api.py`
2. `tests/services/test_message_service.py`
3. `tests/integration/` (filter for message-related)

---

## Workflow Steps

```bash
# 1. Read handover spec
cat handovers/0733_TENANT_ISOLATION_API_SECURITY_PATCH.md

# 2. Read organization doc for context
cat docs/organization.md

# 3. Locate vulnerable endpoints
grep -n "message_service.send_message" api/endpoints/messages.py

# 4. Apply fix (add tenant_key=current_user.tenant_key)
# Use Edit tool to modify api/endpoints/messages.py

# 5. Run tests
pytest tests/api/test_messages_api.py -v
pytest tests/services/test_message_service.py -v
pytest tests/integration/ -v -k message

# 6. Create completion report
# Document files changed, test results, security verification

# 7. Commit
git add api/endpoints/messages.py [other files]
git commit -m "fix(0733): Enforce tenant isolation in message API endpoints"
```

---

## Related Handovers

- **0433:** Task Product Binding and Tenant Isolation Fix (same vulnerability class)
- **0424:** Organization Hierarchy (context for tenant model)
- **0728:** Remove Deprecated Vision Model (previous cleanup in series)
- **0730 Series:** Service Response Models (will include comprehensive tenant isolation cleanup)

---

## Environment

**Branch:** feature/0700-code-cleanup-series
**Python:** 3.11+
**Database:** PostgreSQL (tenant_key isolation enforced)
**Framework:** FastAPI (current_user.tenant_key available in all protected endpoints)

---

## Rollback Plan

If issues arise:

```bash
# Revert the commit
git revert <commit-hash>

# Service fallback will activate again (not ideal but functional)
# No data loss risk - just removes security fix
```

**Risk Level:** VERY LOW - just passing an existing value that should have been passed

---

## Questions to Ask User (If Needed)

1. If you find additional vulnerable endpoints beyond messages.py, should I fix them all in this handover?
2. If tests fail unexpectedly, should I investigate or defer to you?
3. Should I update HANDOVER_CATALOGUE.md to mark 0733 as COMPLETE?

---

**Created:** 2026-02-07
**Status:** READY FOR EXECUTION
**Handover Spec:** `handovers/0733_TENANT_ISOLATION_API_SECURITY_PATCH.md`
**Expected Duration:** 15-30 minutes
**Success Indicator:** All tests pass + messages.py has tenant_key parameter added
