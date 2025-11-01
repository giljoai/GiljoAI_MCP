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

**End of Handover 0081**
