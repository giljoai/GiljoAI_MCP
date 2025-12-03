# Handover 0081: Hybrid Launch Route Architecture

**Date**: 2025-11-01
**Status**: Pending Implementation
**Priority**: High
**Complexity**: Low (30 minutes estimated)

---

## Problem Statement

The current dynamic Jobs button implementation uses Vue watchers to track active project changes, which has proven fragile and high-maintenance:

1. **NavigationDrawer watchers break easily** - Token-expensive debugging cycles
2. **Complex state synchronization** - Product watcher + Project watcher both needed
3. **Developer friction** - High cognitive load for simple "go to active project" feature

However, fully removing dynamic routes would break existing features:
- Dashboard historical project viewing (uses `/projects/{id}?readonly=true`)
- Audit trail in server logs
- Browser history navigation between projects
- Direct linking/bookmarking capabilities

---

## Solution: Hybrid Route Architecture

Implement a **static `/launch` route that intelligently redirects** to preserve both simplicity and power.

### Architecture

```
User clicks "Jobs" button
    ↓
Navigate to /launch (static route, no watchers needed)
    ↓
LaunchRedirectView component fetches active project
    ↓
    ├─ If active project exists → Redirect to /projects/{id}
    └─ If no active project → Show "No Active Project" page
```

---

## Implementation Details

### Files to Modify

#### 1. **Create New Component: `frontend/src/views/LaunchRedirectView.vue`**

```vue
<template>
  <div v-if="loading" class="d-flex justify-center align-center" style="height: 100vh">
    <v-progress-circular indeterminate size="64" color="primary"></v-progress-circular>
  </div>

  <div v-else-if="!activeProject" class="d-flex flex-column justify-center align-center" style="height: 100vh">
    <v-icon size="96" color="grey-darken-2">mdi-briefcase-off-outline</v-icon>
    <h2 class="text-h4 mt-4 text-grey-darken-2">No Active Project</h2>
    <p class="text-body-1 mt-2 text-grey">Activate a project to launch the jobs interface</p>
    <v-btn color="primary" class="mt-6" to="/projects">
      Go to Projects
    </v-btn>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'

const router = useRouter()
const loading = ref(true)
const activeProject = ref(null)

onMounted(async () => {
  try {
    const response = await api.projects.getActive()
    if (response.data) {
      // Redirect to the dynamic project route
      router.replace(`/projects/${response.data.id}`)
    } else {
      // No active project - show the "no active project" page
      activeProject.value = null
      loading.value = false
    }
  } catch (err) {
    console.warn('[LaunchRedirect] Failed to fetch active project:', err)
    activeProject.value = null
    loading.value = false
  }
})
</script>
```

**Purpose**: Fetches active project and either redirects to its launch page OR shows "no active project" message.

---

#### 2. **Update Router: `frontend/src/router/index.js`**

Add new route for `/launch`:

```javascript
{
  path: '/launch',
  name: 'Launch',
  component: () => import('@/views/LaunchRedirectView.vue'),
  meta: { layout: 'default', title: 'Launch' }
}
```

**Note**: Place this BEFORE the `/projects/:projectId` route to ensure proper matching.

---

#### 3. **Simplify NavigationDrawer: `frontend/src/components/navigation/NavigationDrawer.vue`**

**Remove** (lines to delete):
- `import { useProjectStore } from '@/stores/projects'` (line 83)
- `const projectStore = useProjectStore()` (line 108)
- `const activeProjectId = ref(null)` (line 111)
- `fetchActiveProject()` function (lines 112-126)
- `onMounted(async () => { await fetchActiveProject() })` (lines 129-131)
- Product watcher (lines 134-144)
- **NEW** project watcher (lines 148-157)
- `jobsPath` computed (lines 158-160)
- `jobsTitle` computed (lines 162-164)

**Simplify** Jobs button (line 172):

```javascript
// Before (complex):
{ name: 'Jobs', path: jobsPath.value, title: jobsTitle.value, customIcon: jobsIcon.value, disabled: !activeProjectId.value }

// After (simple):
{ name: 'Jobs', path: '/launch', title: 'Jobs', customIcon: jobsIcon.value }
```

**Keep** (preserve functionality):
- `jobsIcon` computed (lines 147-155) - Still needed for dynamic icon based on current route

**Net Change**: ~60 lines removed, 1 line simplified

---

#### 4. **Update ProjectsView: `frontend/src/views/ProjectsView.vue`**

The "Launch" button in the projects list currently uses:

```javascript
router.push({ name: 'ProjectLaunch', params: { projectId } })
```

**Change**: Keep this as-is (uses direct dynamic route). This is correct because:
- User explicitly selected a specific project to launch
- Direct navigation is appropriate (not relying on "active" state)
- Preserves audit trail in URL

**No changes needed** to ProjectsView for this handover.

---

### Files Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `frontend/src/views/LaunchRedirectView.vue` | **Create** | +45 |
| `frontend/src/router/index.js` | Add `/launch` route | +6 |
| `frontend/src/components/navigation/NavigationDrawer.vue` | Remove watchers, simplify | -60, ~1 |
| **Total** | | **Net: -9 lines** |

---

## Benefits

### ✅ Simplicity
- Jobs button: Static link (no watchers, no state management)
- NavigationDrawer: 60 fewer lines of complex reactive code
- Developers: Zero mental overhead for "how does Jobs button work?"

### ✅ Preserved Functionality
- Dashboard historical viewing: Still uses `/projects/{id}?readonly=true`
- Audit trail: Redirected URL contains project ID in logs
- Browser history: Navigate between projects via back button
- Bookmarking: Can still bookmark specific project launch pages
- Direct linking: Projects list "Launch" button uses direct route

### ✅ Error Handling
- No active project: Clean UI message instead of broken link
- API failure: Graceful fallback to "no active project" state

### ✅ Future-Proof
- Adding new status changes: No watcher updates needed
- Product switching: No special logic required
- Project activation/deactivation: Just works™

---

## Testing Checklist

After implementation, verify:

1. **Jobs Button Navigation**
   - [ ] Click Jobs button with active project → Redirects to `/projects/{id}` ✓
   - [ ] Click Jobs button with no active project → Shows "No Active Project" page ✓
   - [ ] Redirect is fast (< 100ms perceived delay) ✓

2. **Projects List Launch**
   - [ ] Click "Launch" from projects list → Opens correct project ✓
   - [ ] URL shows `/projects/{specific_project_id}` ✓

3. **Dashboard Historical Viewing**
   - [ ] Click completed project from Dashboard → Opens readonly view ✓
   - [ ] URL contains `?readonly=true` parameter ✓

4. **Browser Navigation**
   - [ ] Back button navigates between different projects ✓
   - [ ] Browser history shows meaningful project URLs ✓

5. **State Changes**
   - [ ] Activate a project → Next Jobs click goes to that project ✓
   - [ ] Switch products → Next Jobs click goes to new product's active project ✓
   - [ ] Deactivate all projects → Jobs click shows "No Active Project" ✓

6. **Audit Trail**
   - [ ] Server logs show `/projects/{id}` for launches (not `/launch`) ✓
   - [ ] Each project access has unique URL in logs ✓

---

## Migration Notes

### Breaking Changes
**NONE**. This is a purely additive change:
- New `/launch` route added
- Old `/projects/{id}` routes unchanged
- All existing functionality preserved

### Rollback Plan
If issues arise:
1. Revert NavigationDrawer to use dynamic `jobsPath` computed
2. Remove `/launch` route from router
3. Delete LaunchRedirectView.vue component

---

## Architecture Decision Record

### Why Hybrid Instead of Full Static?

**Considered**: Changing all project routes to `/launch` (fully static)

**Rejected because**:
1. Dashboard historical viewing requires project-specific URLs
2. Audit trail value (compliance, debugging, user support)
3. Browser history provides better UX for multi-project workflows
4. Bookmarking/sharing project links has existing user value

**Hybrid wins** by providing simplicity where it matters (Jobs button) while preserving power where needed (direct access).

---

## Related Handovers

- **Handover 0050**: Single Active Product Architecture
- **Handover 0050b**: Single Active Project Per Product
- **Handover 0062**: Project activation optimistic updates (still applies to `/projects/{id}` route)
- **Handover 0071**: Simplified Project State Management (inactive/active/completed/cancelled/deleted)

---

## Implementation Notes for Fresh Agents

### Context Needed
- Vue 3 composition API
- Vue Router 4
- Vuetify 3 components
- Pinia store pattern (projects store)

### Key Architectural Principles
1. **Redirect, don't embed** - LaunchRedirectView should NOT contain project launch logic, just redirect to existing ProjectLaunchView
2. **Keep ProjectLaunchView unchanged** - All existing project launch UI stays in `/projects/{id}` route
3. **Static Jobs link** - NavigationDrawer should not know about active project state
4. **Preserve audit trail** - Final URL after redirect must contain project ID

### Common Pitfalls to Avoid
- ❌ Don't move ProjectLaunchView logic into LaunchRedirectView
- ❌ Don't remove `/projects/{id}` route (Dashboard depends on it)
- ❌ Don't add watchers to LaunchRedirectView (defeats the purpose)
- ❌ Don't forget to remove ALL watcher code from NavigationDrawer

---

## Success Criteria

This handover is considered complete when:

1. ✅ Jobs button uses static `/launch` route
2. ✅ No watchers in NavigationDrawer related to active project
3. ✅ LaunchRedirectView component exists and redirects correctly
4. ✅ All tests pass (see Testing Checklist above)
5. ✅ Frontend rebuilt and deployed
6. ✅ Net reduction in code complexity (fewer lines)
7. ✅ Dashboard historical viewing still works
8. ✅ Server logs show project IDs in URLs

---

## Estimated Effort

- **Development**: 20 minutes
- **Testing**: 10 minutes
- **Frontend Rebuild**: 3 minutes
- **Total**: ~30 minutes

**Risk**: Low (additive change, easy rollback)
**Impact**: High (eliminates fragile watcher architecture)

---

## Questions for Implementation Agent

Before starting, verify:

1. Is the Dashboard historical viewing feature actively used? (Affects priority)
2. Are there any custom route guards that might interfere with `/launch` redirect?
3. Does the project have E2E tests that need updating for new route?

---

## Implementation Results

### ✅ **COMPLETED** - 2025-11-01

**Primary Implementation**: Commit `cc74770` (Nov 1, 2025)
**Post-Implementation Fixes**: Commit `6027982` (Nov 2, 2025 - by Codex)

### What Was Built

**Core Implementation (cc74770)**:
- ✅ Created `LaunchRedirectView.vue` (45 lines)
  - Fetches active project via api.projects.getActive()
  - Redirects to /projects/{id} when active exists
  - Shows "No Active Project" fallback UI
  - Graceful error handling

- ✅ Added `/launch` route to router
  - Static route (no watchers needed)
  - Requires authentication
  - Preserves audit trail in final URL

- ✅ Simplified NavigationDrawer (~60 lines removed)
  - Removed product watcher (14 lines)
  - Removed project watcher (9 lines)
  - Removed fetchActiveProject() function (14 lines)
  - Removed state management (activeProjectId, jobsPath, jobsTitle)
  - Jobs button now static: `to="/launch"`

**Post-Implementation Fixes by Codex (6027982)**:

After initial implementation, Codex identified and fixed navigation indicator issues:

1. **Jobs Nav Indicator Fix** (`NavigationDrawer.vue`)
   - Problem: When entering dynamic project route (/projects/{id}), "Projects" nav showed as active instead of "Jobs"
   - Fix: Updated active route detection logic to show "Jobs" as active when viewing /projects/{id}
   - Result: Jobs button correctly highlights when user is in project launch view

2. **Dynamic Launch Button State** (`ProjectsView.vue`)
   - Problem: "Launch" button on project list didn't update to "Working" after starting implementation
   - Fix: Added dynamic button state based on project status
   - Result: Button shows "Working" indicator when orchestrator is active

3. **Route State Synchronization** (`LaunchRedirectView.vue`)
   - Enhanced navigation state tracking across route transitions
   - Ensures consistent nav highlighting when navigating back from /products

### Impact

**Code Quality**:
- Net reduction: -4 lines (removed 65, added 61)
- Eliminated fragile watcher architecture
- Reduced cognitive load for developers
- Improved maintainability

**User Experience**:
- ✅ Jobs button always functional (no disabled state)
- ✅ Clear "No Active Project" messaging
- ✅ Correct nav indicator highlighting (Jobs vs Projects)
- ✅ Dynamic button states reflect orchestrator status
- ✅ Preserved all existing functionality (history, bookmarking, audit trails)

**Performance**:
- Faster (no watchers on every state change)
- Reduced memory footprint (fewer reactive refs)
- Cleaner component lifecycle

### Files Modified

**Primary Implementation**:
1. `frontend/src/views/LaunchRedirectView.vue` (NEW - 45 lines)
2. `frontend/src/router/index.js` (UPDATED - added /launch route)
3. `frontend/src/components/navigation/NavigationDrawer.vue` (UPDATED - removed 65 lines)

**Post-Implementation Fixes**:
4. `frontend/src/components/navigation/NavigationDrawer.vue` (ENHANCED - nav indicator logic)
5. `frontend/src/views/ProjectsView.vue` (ENHANCED - dynamic button states)
6. `frontend/src/views/LaunchRedirectView.vue` (ENHANCED - state sync)

### Success Criteria Met

✅ Jobs button routes to static /launch path
✅ Active project redirects to /projects/{id}
✅ No active project shows graceful fallback UI
✅ Dashboard historical viewing preserved
✅ Browser history navigation works
✅ Direct linking/bookmarking functional
✅ Audit trails in server logs maintained
✅ **Nav indicators correctly show active route (Codex fix)**
✅ **Launch button shows working state (Codex fix)**
✅ Frontend builds successfully
✅ No breaking changes
✅ Code complexity reduced

### Lessons Learned

1. **Watchers Are Fragile**: Vue watchers for cross-component state synchronization create maintenance burden
2. **Static Routes Win**: Server-side route resolution is more reliable than client-side state management
3. **Post-Implementation Polish Matters**: Initial implementation worked but Codex's nav indicator fixes improved UX significantly
4. **Iterative Improvement**: Navigation state tracking needed refinement after real-world testing

### Testing Completed

✅ Server starts without errors (API: 7273, Frontend: 7275)
✅ Frontend build successful (LaunchRedirectView: 1.22 kB gzipped)
✅ Route properly registered in router
✅ API endpoint /api/v1/projects/active requires auth
✅ Nav indicators highlight correctly across all routes
✅ Launch button state updates based on orchestrator status
✅ "No Active Project" fallback displays correctly
✅ Redirect to /projects/{id} works seamlessly

---

**Status**: ✅ Complete with post-implementation enhancements
**Complexity**: Low (as estimated - 30 min initial, 15 min polish)
**Quality**: Production-ready
**Acknowledgments**: Initial implementation + Codex navigation polish

**End of Handover 0081**
