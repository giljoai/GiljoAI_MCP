# Handover 0434: Admin Settings UI Consolidation

**Date**: 2026-02-03
**Status**: Pending
**Agent**: Documentation Manager Agent
**Estimated Effort**: 8-12 hours
**Complexity**: Medium
**Type**: Frontend Refactoring + Minor Backend Fix

---

## Executive Summary

This handover consolidates scattered admin features into a unified Admin Settings interface, eliminating confusion about where to manage system-level vs. user-level settings. It introduces an "Identity" tab that aligns with enterprise SaaS patterns (Microsoft Entra ID terminology) and fixes a permission bug preventing users from viewing their own organization.

**Current Problems**:
- Admin features scattered across avatar menu ("My Workspace", "Users", "Admin Settings")
- "System" tab name is confusing (contains orchestrator prompt)
- OrganizationSettings.vue has permission bug (requires OrgMembership even when user has org_id)
- No clear separation between user settings and admin settings

**Solution**:
- Clean up avatar menu to remove scattered admin features
- Add "Identity" tab to Admin Settings (workspace + members + roles)
- Rename "System" tab to "Prompts" (clearer naming)
- Fix organization permission check
- Align with SaaS/enterprise patterns for future SSO/SCIM integration

---

## Context

### Background

The GiljoAI MCP server has a multi-level settings hierarchy:
1. **User Settings (My Settings)** - Personal preferences (context depth, priorities, theme)
2. **Organization Settings (My Workspace)** - Workspace management (name, members, roles)
3. **Admin Settings** - System-wide configuration (network, database, prompts, security)

The Organization Hierarchy feature (Handovers 0424a-n) introduced organizations with role-based access control. However, the UI grew organically and now has admin features scattered in multiple places.

### Current State Analysis

**Avatar Menu (AppBar.vue lines 75-110)**:
```vue
<!-- My Workspace link (Handover 0424i) -->
<v-list-item
  v-if="userStore.currentOrg"
  prepend-icon="mdi-office-building"
  @click="router.push(`/organizations/${userStore.currentOrg.id}/settings`)"
>
  <v-list-item-title>My Workspace</v-list-item-title>
</v-list-item>

<!-- Admin Settings - Only visible to admin users -->
<v-list-item
  v-if="currentUser && currentUser.role === 'admin'"
  :to="{ name: 'SystemSettings' }"
>
  <v-icon color="error">mdi-cog</v-icon>
  <v-list-item-title>Admin Settings</v-list-item-title>
</v-list-item>

<!-- Users Management - Only visible to admin users -->
<v-list-item v-if="currentUser && currentUser.role === 'admin'" :to="{ name: 'Users' }">
  <v-icon color="error">mdi-account-multiple</v-icon>
  <v-list-item-title>Users</v-list-item-title>
</v-list-item>
```

**SystemSettings.vue (Admin Settings) - Current Tabs**:
1. Network (ports, CORS)
2. Database (PostgreSQL config)
3. Integrations (API keys)
4. Security (cookie domains)
5. System (orchestrator prompt) ← **Confusing name**

**OrganizationSettings.vue - Separate Page**:
- Organization details (name, slug)
- Members list with role management
- Invite member functionality
- Delete organization (owner only)
- **Bug**: Line 192 checks `can_view_org()` which requires OrgMembership record

**Users.vue - Separate Page**:
- Wraps `UserManager.vue` component
- User CRUD operations
- Admin-only feature

### What's Working (Do NOT Change)

1. **UserProfileDialog.vue (lines 22-30)**:
   - Shows read-only workspace name and role badge
   - This is CORRECT behavior - users view their org context here
   - Do NOT add edit functionality

2. **User Settings (UserSettings.vue)**:
   - Personal context depth/priority configuration
   - Personal theme preferences
   - This is CORRECT - keep personal settings separate

3. **Backend OrgService**:
   - Working correctly
   - Permission checks may need minor adjustment but core logic is solid

### The Permission Bug

**File**: `api/endpoints/organizations/crud.py` (lines 167-215)
**Problem**: GET `/api/organizations/{org_id}` requires `can_view_org()` check (line 192)

```python
@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    # Check membership
    if not await org_service.can_view_org(org_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )
```

**Issue**: User may have `User.org_id` set but no active `OrgMembership` record if:
- User was created during Welcome flow but membership wasn't created
- User switched orgs and old membership was soft-deleted
- Database migration didn't create membership records

**Result**: "Organization not found or you don't have access" error (OrganizationSettings.vue line 102)

### SaaS Model Alignment

This consolidation sets the foundation for enterprise features:

| Concept | Current | Future |
|---------|---------|--------|
| **Workspace** | Organization name | Multi-org support |
| **Identity** | Local users + roles | SAML/OIDC SSO, SCIM provisioning |
| **Members** | Manual invite | Auto-provisioning via SSO |
| **Roles** | owner/admin/member/viewer | Custom role definitions |
| **Licenses** | N/A | Seat-based subscriptions |

Using "Identity" tab name aligns with:
- Microsoft Entra ID (formerly Azure AD)
- Okta Identity Management
- Auth0 Identity Platform

---

## Technical Details

### Files to Modify

#### Phase 1: AppBar Cleanup

**File**: `frontend/src/components/navigation/AppBar.vue`

**Remove** (lines 75-82):
```vue
<!-- My Workspace link (Handover 0424i) -->
<v-list-item
  v-if="userStore.currentOrg"
  prepend-icon="mdi-office-building"
  @click="router.push(`/organizations/${userStore.currentOrg.id}/settings`)"
>
  <v-list-item-title>My Workspace</v-list-item-title>
</v-list-item>

<v-divider v-if="userStore.currentOrg" />
```

**Remove** (lines 104-110):
```vue
<!-- Users Management - Only visible to admin users -->
<v-list-item v-if="currentUser && currentUser.role === 'admin'" :to="{ name: 'Users' }">
  <template v-slot:prepend>
    <v-icon color="error">mdi-account-multiple</v-icon>
  </template>
  <v-list-item-title>Users</v-list-item-title>
</v-list-item>
```

**Result**: Avatar menu simplified to:
- Edit Profile (opens UserProfileDialog)
- My Settings (user preferences)
- Admin Settings (admins only)
- Logout

#### Phase 2: Identity Tab Creation

**File**: `frontend/src/components/settings/tabs/IdentityTab.vue` (NEW)

**Requirements**:
1. Organization section:
   - Display org name (editable by owner/admin)
   - Display slug (read-only)
   - Save button (owner/admin only)

2. Members section:
   - List members with role badges
   - Role dropdown (owner/admin can change)
   - Remove member button (owner/admin)
   - Invite button (owner/admin)

3. Reuse existing components:
   - `MemberList.vue` (from OrganizationSettings)
   - `InviteMemberDialog.vue` (from OrganizationSettings)
   - `RoleBadge.vue` (from common)

**Implementation Notes**:
- Import from `@/stores/orgStore` for data
- Use `userStore.currentUser.org_id` to load organization
- Handle loading/error states
- Emit snackbar notifications on success/error
- Admin-only visibility enforced at parent level (SystemSettings.vue)

**Sample Structure**:
```vue
<template>
  <v-row>
    <v-col cols="12" md="6">
      <v-card>
        <v-card-title>Workspace Details</v-card-title>
        <v-card-text>
          <!-- Org name, slug, save button -->
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" md="6">
      <v-card>
        <v-card-title>
          Members
          <v-spacer />
          <v-btn>Invite</v-btn>
        </v-card-title>
        <v-card-text>
          <MemberList :members="members" ... />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>

  <InviteMemberDialog v-model="showInvite" ... />
</template>
```

#### Phase 3: SystemSettings.vue Integration

**File**: `frontend/src/views/SystemSettings.vue`

**Add tab button** (after line 19, before "Network" tab):
```vue
<v-btn value="identity" min-width="120">
  <v-icon start>mdi-account-group</v-icon>
  Identity
</v-btn>
```

**Add tab content** (after line 42, before "Network" window-item):
```vue
<!-- Identity Tab -->
<v-window-item value="identity">
  <IdentityTab />
</v-window-item>
```

**Rename System tab** (line 33-36):
```vue
<!-- Change from "System" to "Prompts" -->
<v-btn value="prompts" min-width="120">
  <v-icon start>mdi-file-document-edit</v-icon>
  Prompts
</v-btn>
```

**Update window-item** (line 94):
```vue
<!-- Change value from "system" to "prompts" -->
<v-window-item value="prompts">
  <SystemPromptTab />
</v-window-item>
```

**Import component** (line 117):
```vue
import IdentityTab from '@/components/settings/tabs/IdentityTab.vue'
```

**Tab order** (final state):
1. Identity (NEW)
2. Network
3. Database
4. Integrations
5. Security
6. Prompts (renamed from System)

#### Phase 4: Permission Bug Fix

**File**: `api/endpoints/organizations/crud.py` (lines 167-215)

**Option A - Fix Permission Check** (Recommended):
```python
@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    # Allow access if user's org_id matches OR has membership
    if current_user.org_id != org_id:
        if not await org_service.can_view_org(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization"
            )

    result = await org_service.get_organization(org_id)
    # ... rest of endpoint
```

**Option B - Ensure Membership** (Alternative):
- Update AuthService to ALWAYS create OrgMembership when setting user.org_id
- Add migration to backfill missing memberships
- Keep strict permission check

**Recommended**: Option A (simpler, handles edge cases)

#### Phase 5: Route Cleanup (Optional)

**File**: `frontend/src/router/index.js`

**Consider deprecating** (but don't break existing bookmarks):
- `/organizations/:orgId/settings` - Keep route but redirect to Admin Settings → Identity tab
- `/users` - Keep route but redirect to Admin Settings → Identity tab

**Add redirect logic**:
```javascript
{
  path: '/organizations/:orgId/settings',
  redirect: (to) => {
    // Redirect to Admin Settings Identity tab
    return { name: 'SystemSettings', hash: '#identity' }
  }
},
{
  path: '/users',
  redirect: { name: 'SystemSettings', hash: '#identity' }
}
```

### Data Flow

```
Avatar Menu (Admin Settings)
  → SystemSettings.vue (Admin Settings view)
    → IdentityTab.vue (NEW)
      → OrgStore.fetchOrganization(user.org_id)
        → GET /api/organizations/{org_id}
          → OrgService.get_organization() [with fixed permission check]
            → Returns org + members
      → MemberList.vue (reused component)
      → InviteMemberDialog.vue (reused component)
```

### State Management

**OrgStore** (`frontend/src/stores/orgStore.js`):
- Already has all necessary methods
- `fetchOrganization(org_id)` - Load org details
- `updateOrganization(org_id, data)` - Save name
- `changeMemberRole()`, `removeMember()`, etc.

**UserStore** (`frontend/src/stores/user.js`):
- `currentUser.org_id` - User's organization ID
- `currentOrg` - Computed org details
- `orgRole` - User's role in org

**No new state management needed** - reuse existing stores.

---

## Implementation Plan

### Phase 1: AppBar Cleanup (2 hours)

**Tasks**:
1. Remove "My Workspace" link (lines 75-82)
2. Remove "Users" link (lines 104-110)
3. Test avatar menu renders correctly
4. Verify Edit Profile and My Settings still work

**Files Modified**:
- `frontend/src/components/navigation/AppBar.vue`

**Testing**:
- Avatar menu displays: Edit Profile, My Settings, Admin Settings, Logout
- No broken links or console errors
- Admin-only users see Admin Settings

**Sub-agent**: `frontend-tester`

**Success Criteria**:
- ✅ Avatar menu has exactly 4 items for admins (Edit Profile, My Settings, Admin Settings, Logout)
- ✅ Avatar menu has 3 items for non-admins (no Admin Settings)
- ✅ No console errors

---

### Phase 2: Identity Tab Component (4 hours)

**Tasks**:
1. Create `frontend/src/components/settings/tabs/IdentityTab.vue`
2. Import OrgStore and UserStore
3. Implement organization details section
4. Implement members section (reuse MemberList.vue)
5. Add invite functionality (reuse InviteMemberDialog.vue)
6. Add save functionality for org name
7. Add loading/error states
8. Add snackbar notifications

**Files Created**:
- `frontend/src/components/settings/tabs/IdentityTab.vue`

**Files Referenced**:
- `frontend/src/components/org/MemberList.vue` (reuse)
- `frontend/src/components/org/InviteMemberDialog.vue` (reuse)
- `frontend/src/components/common/RoleBadge.vue` (reuse)
- `frontend/src/stores/orgStore.js` (data source)

**Testing**:
- Component renders with mock org data
- Save button updates org name
- Invite dialog opens and closes
- Member role changes persist
- Loading states display correctly
- Error messages appear on failure

**Sub-agent**: `frontend-tester`

**Success Criteria**:
- ✅ Component loads org data via OrgStore
- ✅ Org name can be edited and saved
- ✅ Members list displays with role badges
- ✅ Invite dialog works
- ✅ Role changes work (owner/admin only)
- ✅ Error handling displays helpful messages

---

### Phase 3: SystemSettings Integration (2 hours)

**Tasks**:
1. Add "Identity" tab button to SystemSettings.vue
2. Add Identity tab window-item
3. Rename "System" tab to "Prompts"
4. Update window-item value from "system" to "prompts"
5. Import IdentityTab component
6. Test tab switching
7. Verify tab order and icons

**Files Modified**:
- `frontend/src/views/SystemSettings.vue`

**Testing**:
- All tabs render correctly
- Tab switching works smoothly
- Identity tab appears first in tab list
- Prompts tab shows orchestrator prompt content
- Icons and labels are correct

**Sub-agent**: `frontend-tester`

**Success Criteria**:
- ✅ 6 tabs display: Identity, Network, Database, Integrations, Security, Prompts
- ✅ Identity tab is first
- ✅ Tab content loads correctly
- ✅ No console errors

---

### Phase 4: Permission Bug Fix (2 hours)

**Tasks**:
1. Review current permission check in organizations/crud.py
2. Implement Option A (check user.org_id OR membership)
3. Add logging for permission checks
4. Test with user who has org_id but no membership
5. Test with user who has membership
6. Test with user who has neither (should fail)

**Files Modified**:
- `api/endpoints/organizations/crud.py`

**Files Referenced**:
- `src/giljo_mcp/services/org_service.py` (permission methods)
- `src/giljo_mcp/models/organizations.py` (Organization, OrgMembership)
- `src/giljo_mcp/models/auth.py` (User)

**Testing**:
- User with org_id can view their org (NEW - fixes bug)
- User with membership can view org (existing)
- User with neither gets 403 (existing)
- Admin can view any org (if admin override added)

**Sub-agent**: `backend-integration-tester`

**Success Criteria**:
- ✅ Users can view their own org (user.org_id matches)
- ✅ Members can view org via membership
- ✅ Non-members get 403 error
- ✅ OrganizationSettings.vue loads without error

---

### Phase 5: E2E Testing & Polish (2 hours)

**Tasks**:
1. Write E2E test for admin settings flow
2. Test Identity tab with real data
3. Test org name save
4. Test member invite
5. Test role changes
6. Test navigation from avatar menu
7. Verify no broken routes
8. Update user documentation (if needed)

**Files Created**:
- `frontend/tests/e2e/admin-settings-identity.spec.js` (NEW)

**Files Modified**:
- `docs/user_guides/admin_settings.md` (update screenshots/instructions)

**Testing Scenarios**:
1. **Admin Login → Admin Settings**:
   - Click avatar → Admin Settings
   - Identity tab loads org details
   - Members list displays correctly

2. **Edit Organization**:
   - Change org name
   - Click Save
   - Verify update persists

3. **Member Management**:
   - Click Invite
   - Enter user ID
   - Invite member
   - Verify member appears in list
   - Change member role
   - Remove member

4. **Non-Admin User**:
   - Avatar menu does NOT show Admin Settings
   - Direct navigation to /system-settings redirects (403)

**Sub-agent**: `frontend-tester` + `documentation-manager`

**Success Criteria**:
- ✅ E2E tests pass for admin flow
- ✅ E2E tests pass for non-admin (no access)
- ✅ No console errors or warnings
- ✅ Documentation updated
- ✅ User guide screenshots current

---

## Testing Strategy

### Unit Tests

**IdentityTab.vue**:
```javascript
describe('IdentityTab.vue', () => {
  it('renders org name and slug', () => {})
  it('allows admin to edit org name', () => {})
  it('shows members list', () => {})
  it('opens invite dialog', () => {})
  it('handles save errors gracefully', () => {})
})
```

**SystemSettings.vue**:
```javascript
describe('SystemSettings.vue - Identity Tab', () => {
  it('includes Identity tab button', () => {})
  it('renders IdentityTab component', () => {})
  it('renamed System tab to Prompts', () => {})
})
```

**organizations/crud.py**:
```python
def test_get_organization_with_org_id_match():
    """User with matching org_id can view org."""

def test_get_organization_with_membership():
    """User with membership can view org."""

def test_get_organization_no_access():
    """User with no access gets 403."""
```

### Integration Tests

**Admin Settings Flow**:
1. Login as admin
2. Navigate to Admin Settings
3. Click Identity tab
4. Verify org loaded
5. Edit org name
6. Save changes
7. Verify persisted

**Member Management Flow**:
1. Login as owner
2. Open Identity tab
3. Invite new member
4. Change member role
5. Remove member

### E2E Tests

**File**: `frontend/tests/e2e/admin-settings-identity.spec.js`

```javascript
describe('Admin Settings - Identity Tab', () => {
  it('admin can access Identity tab', () => {
    cy.login('admin', 'password')
    cy.get('[data-test="avatar-menu"]').click()
    cy.get('[data-test="admin-settings"]').click()
    cy.get('[data-test="identity-tab"]').click()
    cy.contains('Workspace Details').should('be.visible')
  })

  it('non-admin cannot access Admin Settings', () => {
    cy.login('viewer', 'password')
    cy.get('[data-test="avatar-menu"]').click()
    cy.get('[data-test="admin-settings"]').should('not.exist')
  })

  it('can edit organization name', () => {
    cy.login('admin', 'password')
    cy.navigateTo('Admin Settings → Identity')
    cy.get('[data-test="org-name"]').clear().type('New Workspace Name')
    cy.get('[data-test="save-org-btn"]').click()
    cy.contains('Organization updated successfully')
  })
})
```

---

## Success Criteria

### Functional Requirements

- ✅ Avatar menu cleaned up (4 items for admin, 3 for non-admin)
- ✅ Admin Settings has 6 tabs: Identity, Network, Database, Integrations, Security, Prompts
- ✅ Identity tab shows org details + members list
- ✅ Owner/admin can edit org name and manage members
- ✅ Users can view their own org (permission bug fixed)
- ✅ All existing functionality preserved (network, database, security, prompts tabs)

### Technical Requirements

- ✅ Reuses existing components (MemberList, InviteMemberDialog, RoleBadge)
- ✅ Uses OrgStore for state management (no new stores)
- ✅ Follows Vuetify 3 patterns (v-card, v-btn, v-list)
- ✅ Matches existing design system (global-tabs-window class)
- ✅ Permission check fixed (user.org_id OR membership)

### Quality Requirements

- ✅ Unit tests for IdentityTab component
- ✅ Integration tests for permission fix
- ✅ E2E tests for admin settings flow
- ✅ No console errors or warnings
- ✅ Responsive design (works on mobile)
- ✅ Accessibility (ARIA labels, keyboard navigation)

### Documentation Requirements

- ✅ User guide updated with new Identity tab
- ✅ Screenshots updated for Admin Settings
- ✅ API documentation updated (if permission endpoint changed)
- ✅ Handover document created (this file)

---

## Risks & Mitigation

### Risk 1: Breaking Existing Users/Orgs Routes

**Impact**: High
**Probability**: Medium

**Mitigation**:
- Keep existing routes functional (deprecate, don't delete)
- Add redirects from old routes to new Identity tab
- Test with real user bookmarks
- Add console warnings for deprecated routes

### Risk 2: Permission Logic Side Effects

**Impact**: High
**Probability**: Low

**Mitigation**:
- Thoroughly test permission check changes
- Add comprehensive unit tests
- Test edge cases (no org_id, no membership, both)
- Add logging to track permission checks

### Risk 3: Component Reuse Issues

**Impact**: Medium
**Probability**: Low

**Mitigation**:
- Review MemberList.vue and InviteMemberDialog.vue before reuse
- Test in new context (Admin Settings vs. standalone page)
- Verify props/events work correctly
- Add integration tests

### Risk 4: State Management Conflicts

**Impact**: Medium
**Probability**: Low

**Mitigation**:
- Use existing OrgStore methods (no new state)
- Test concurrent updates (multiple tabs)
- Verify WebSocket updates work
- Add state synchronization tests

---

## Future Enhancements

These are OUT OF SCOPE for this handover but should be considered for future work:

### Phase 2 (Future): Users Tab in Identity

**Goal**: Consolidate user management into Identity tab

**Design**:
```
Identity Tab
├── Organization (current)
├── Members (current)
└── Users (NEW)
    ├── All tenant users
    ├── System role management (admin/developer/viewer)
    └── User creation/deletion
```

**Benefits**:
- Single location for all identity management
- Clear separation: Members = org-level, Users = tenant-level
- Aligns with enterprise IAM patterns

**Effort**: 4-6 hours

### Phase 3 (Future): Role Hierarchy

**Goal**: Custom role definitions with permissions

**Design**:
- Define custom roles (e.g., "Project Manager", "Read-Only Auditor")
- Assign permissions to roles (e.g., can_create_project, can_view_logs)
- Assign roles to users

**Benefits**:
- Flexible permission model
- Enterprise-ready role management
- Granular access control

**Effort**: 16-20 hours

### Phase 4 (Future): SSO Integration

**Goal**: SAML/OIDC single sign-on

**Design**:
- Identity tab → SSO Configuration section
- SAML metadata upload
- OIDC client configuration
- Auto-provisioning settings

**Benefits**:
- Enterprise authentication
- Reduced password management
- Compliance with corporate policies

**Effort**: 40-60 hours

---

## Related Handovers

- **0424a-n**: Organization Hierarchy (14-handover chain)
  - 0424a-b: Organization/OrgMembership models + OrgService
  - 0424c-d: API endpoints + frontend components
  - 0424i: Welcome screen + AppBar integration
  - 0424o: Workspace tab removal from My Settings (CORRECT)

- **0023**: Password Reset via PIN
  - Recovery PIN system used in UserProfileDialog

- **0243a-f**: GUI Redesign Series
  - Design tokens and component patterns to follow

---

## Sub-Agent Assignments

### Phase 1: AppBar Cleanup
**Agent**: `frontend-tester`
**Skills**: Vue 3, Vuetify, component testing
**Deliverables**: Cleaned avatar menu, unit tests

### Phase 2: Identity Tab Component
**Agent**: `frontend-tester`
**Skills**: Vue 3, Vuetify, Pinia stores, component composition
**Deliverables**: IdentityTab.vue, unit tests

### Phase 3: SystemSettings Integration
**Agent**: `frontend-tester`
**Skills**: Vue 3, Vuetify, tab navigation
**Deliverables**: Updated SystemSettings.vue, integration tests

### Phase 4: Permission Bug Fix
**Agent**: `backend-integration-tester`
**Skills**: FastAPI, SQLAlchemy, pytest, permission logic
**Deliverables**: Fixed permission check, unit tests

### Phase 5: E2E Testing & Documentation
**Agents**: `frontend-tester` + `documentation-manager`
**Skills**: Cypress/Playwright, technical writing, screenshots
**Deliverables**: E2E tests, updated user guides

---

## Acceptance Checklist

Before marking this handover complete, verify:

- [ ] Avatar menu simplified (no "My Workspace" or "Users" links)
- [ ] Admin Settings has Identity tab as first tab
- [ ] Identity tab shows org name and members
- [ ] Identity tab allows editing (owner/admin only)
- [ ] System tab renamed to Prompts
- [ ] Permission bug fixed (users can view their org)
- [ ] All unit tests pass (>80% coverage)
- [ ] All integration tests pass
- [ ] E2E tests pass for admin flow
- [ ] E2E tests pass for non-admin (no access)
- [ ] No console errors or warnings
- [ ] Documentation updated
- [ ] Code review completed
- [ ] Ready for production deployment

---

## Notes for Executing Agent

### Key Design Decisions

1. **Why "Identity" not "Users & Organizations"?**
   - Aligns with Microsoft Entra ID, Okta, Auth0
   - Prepares for SSO/SCIM future work
   - Short, clear, professional

2. **Why consolidate into Admin Settings?**
   - Reduces cognitive load (one place for all admin work)
   - Eliminates confusion about where to find features
   - Matches enterprise SaaS patterns (1Password, Slack, GitHub)

3. **Why keep UserProfileDialog org display read-only?**
   - Prevents confusion (org changes should be admin-only)
   - Provides context without edit temptation
   - Aligns with user vs. admin separation

4. **Why fix permission with org_id check?**
   - Simplest solution (no migration needed)
   - Handles edge cases (missing membership records)
   - Future-proof (works even if membership deleted)

### Development Tips

1. **Component Reuse**:
   - Copy prop definitions from OrganizationSettings.vue
   - MemberList expects specific event signatures
   - InviteMemberDialog uses v-model pattern

2. **Store Usage**:
   - Always check loading state before rendering
   - Handle null currentOrg gracefully
   - Use computed for reactive updates

3. **Testing**:
   - Mock OrgStore in component tests
   - Use real database for integration tests
   - Test both admin and non-admin users

4. **Styling**:
   - Follow SystemSettings.vue patterns
   - Use `.bordered-tabs-content` class
   - Match spacing from other tabs

### Common Pitfalls

1. **Don't break existing routes** - Add redirects, don't delete
2. **Don't forget loading states** - Network calls take time
3. **Don't skip permission tests** - Security is critical
4. **Don't ignore mobile** - Test responsive design
5. **Don't forget error handling** - Network failures happen

---

## Appendix

### File Inventory

**Frontend Files**:
- `frontend/src/components/navigation/AppBar.vue` (MODIFY)
- `frontend/src/views/SystemSettings.vue` (MODIFY)
- `frontend/src/components/settings/tabs/IdentityTab.vue` (CREATE)
- `frontend/src/components/org/MemberList.vue` (REUSE)
- `frontend/src/components/org/InviteMemberDialog.vue` (REUSE)
- `frontend/src/components/common/RoleBadge.vue` (REUSE)
- `frontend/src/stores/orgStore.js` (REFERENCE)
- `frontend/src/stores/user.js` (REFERENCE)
- `frontend/tests/e2e/admin-settings-identity.spec.js` (CREATE)

**Backend Files**:
- `api/endpoints/organizations/crud.py` (MODIFY - permission fix)
- `src/giljo_mcp/services/org_service.py` (REFERENCE)
- `src/giljo_mcp/models/organizations.py` (REFERENCE)
- `src/giljo_mcp/models/auth.py` (REFERENCE)

**Documentation Files**:
- `docs/user_guides/admin_settings.md` (UPDATE)
- `handovers/0434_admin_settings_ui_consolidation.md` (THIS FILE)

### Glossary

- **Identity**: Collection of users, roles, and access controls (enterprise IAM term)
- **Workspace**: User-facing name for "organization" (less technical)
- **Tenant**: Multi-tenant isolation boundary (per-user in GiljoAI)
- **OrgMembership**: Join table linking users to organizations with roles
- **Permission Check**: Authorization logic to determine access rights
- **Avatar Menu**: Dropdown menu from user avatar icon in app bar

---

**End of Handover 0434**
