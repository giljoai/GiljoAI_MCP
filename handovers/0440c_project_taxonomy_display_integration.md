# Handover: 0440c - Project Taxonomy Display Integration

**Date:** 2026-01-22
**From Agent:** System Architect
**To Agent:** Frontend Tester / TDD Implementor
**Priority:** Medium
**Estimated Complexity:** 6-8 hours
**Status:** Ready for Implementation
**Series:** 0440 (Project Organization Enhancement)

**Prerequisites:**
- ✅ 0440a (Database schema + backend API) - MUST be complete
- ✅ 0440b (Frontend UI components) - MUST be complete

---

## Task Summary

Integrate the Project Taxonomy & Series System (from 0440a/b) into all display surfaces. Users will see their organized project names (e.g., "🟢 BE-0042a Refactor Auth") in:
1. Project list table
2. Project detail header
3. Browser tab title
4. Filters and sorting

**Why It's Important:**
- Completes the taxonomy feature end-to-end
- Users need visual confirmation their organization is working
- Filtering by type enables quick project discovery at scale

**Expected Outcome:**
- Color-coded series chips in project list table
- Series badge in project detail header
- Type filter chips for quick filtering
- Series-aware sorting
- Browser tab titles show series alias

---

## Context and Background

**Series Alias Format:**
- Full: `BE-0042a` (type + series + subseries)
- No subseries: `BE-0042` (type + series)
- No type: `0042` (series only)
- No series: `null` (legacy project, show name only)

**Existing Display Locations:**
- `ProjectsView.vue` - Table at `/projects`
- `ProjectTabs.vue` - Header at `/projects/{id}`

**Design Decision:** Series chip as PREFIX in name column (saves horizontal space)

---

## Technical Details

### Files to Modify

#### 1. Backend: `api/endpoints/projects/models.py`

**Add ProjectTypeResponse schema:**
```python
# Add after line ~100 (after existing response models)

class ProjectTypeResponse(BaseModel):
    """Response model for project type details."""
    id: str
    abbreviation: str
    label: str
    color: str  # Hex color for UI chips

    model_config = ConfigDict(from_attributes=True)
```

**Extend ProjectResponse schema:**
```python
# Add to existing ProjectResponse class (around line 57-77)

class ProjectResponse(BaseModel):
    """Response model for project details."""
    id: str
    alias: str
    name: str
    description: Optional[str] = None
    mission: str
    status: str
    staging_status: Optional[str] = None
    product_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    context_budget: Optional[int] = 150000
    context_used: Optional[int] = 0
    agent_count: int
    message_count: int
    agents: List[AgentSimple] = []
    execution_mode: str = "multi_terminal"

    # NEW: Taxonomy fields (0440c)
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeResponse] = None  # Nested for color
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    series_alias: Optional[str] = None  # Computed: "BE-0042a" or "0042" or None
```

---

#### 2. Backend: `api/endpoints/projects/crud.py` (or router.py)

**Add helper function for series alias computation:**
```python
# Add near top of file with other helpers

def compute_series_alias(project) -> Optional[str]:
    """
    Compute taxonomy-based alias for a project.

    Returns:
        "BE-0042a" - Full taxonomy (type + series + subseries)
        "BE-0042"  - Type + series (no subseries)
        "0042"     - Series only (no type)
        None       - No taxonomy assigned
    """
    if not project.series_number:
        return None

    parts = []

    # Add type abbreviation if present
    if project.project_type and project.project_type.abbreviation:
        parts.append(project.project_type.abbreviation)
        parts.append("-")

    # Add zero-padded series number (always 4 digits)
    parts.append(f"{project.series_number:04d}")

    # Add subseries letter if present
    if project.subseries:
        parts.append(project.subseries)

    return "".join(parts)  # "BE-0042a" or "0042"
```

**Update project response builders:**
```python
# In _build_project_response() or similar function, add:

def _build_project_response(project: Project) -> ProjectResponse:
    """Build ProjectResponse with computed series_alias."""

    # Build nested project_type if exists
    project_type_response = None
    if project.project_type:
        project_type_response = ProjectTypeResponse(
            id=project.project_type.id,
            abbreviation=project.project_type.abbreviation,
            label=project.project_type.label,
            color=project.project_type.color,
        )

    return ProjectResponse(
        id=project.id,
        alias=project.alias,
        name=project.name,
        # ... existing fields ...

        # Taxonomy fields (0440c)
        project_type_id=project.project_type_id,
        project_type=project_type_response,
        series_number=project.series_number,
        subseries=project.subseries,
        series_alias=compute_series_alias(project),
    )
```

**Ensure eager loading of project_type:**
```python
# In project queries, add joinedload for project_type relationship

from sqlalchemy.orm import joinedload

# Example in list_projects():
query = select(Project).options(
    joinedload(Project.project_type)  # Add this line
).where(
    Project.tenant_key == tenant_key,
    Project.deleted_at.is_(None)
)
```

---

#### 3. Frontend: `frontend/src/views/ProjectsView.vue`

**Add series chip to Name column template (around line 188-195):**

Replace:
```vue
<!-- Name Column with ID -->
<template v-slot:item.name="{ item }">
  <div class="py-2">
    <div class="font-weight-bold text-body-2">{{ item.name }}</div>
    <div class="text-caption text-medium-emphasis" style="font-family: monospace">
      Project ID: {{ item.id }}
    </div>
  </div>
</template>
```

With:
```vue
<!-- Name Column with Series Chip + ID -->
<template v-slot:item.name="{ item }">
  <div class="py-2">
    <div class="d-flex align-center font-weight-bold text-body-2">
      <!-- Series Chip (only if series_alias exists) -->
      <v-chip
        v-if="item.series_alias"
        :color="item.project_type?.color || '#607D8B'"
        size="x-small"
        variant="flat"
        class="mr-2"
        :title="item.project_type?.label || 'Untyped'"
      >
        {{ item.series_alias }}
      </v-chip>
      <span>{{ item.name }}</span>
    </div>
    <div class="text-caption text-medium-emphasis" style="font-family: monospace">
      Project ID: {{ item.id }}
    </div>
  </div>
</template>
```

**Add Type Filter chips after Status filter (around line 96-108):**
```vue
<!-- Status Filter Chips -->
<div class="d-flex gap-2 flex-wrap align-center">
  <!-- Existing status chips... -->
</div>

<!-- Type Filter Chips (NEW - 0440c) -->
<div class="d-flex gap-2 flex-wrap align-center mt-3">
  <span class="text-caption text-medium-emphasis mr-2">Type:</span>
  <v-chip
    :color="filterType === 'all' ? 'primary' : 'default'"
    :variant="filterType === 'all' ? 'tonal' : 'outlined'"
    size="small"
    @click="filterType = 'all'"
    class="cursor-pointer"
  >
    All
  </v-chip>
  <v-chip
    v-for="ptype in projectTypes"
    :key="ptype.id"
    :color="filterType === ptype.id ? ptype.color : 'default'"
    :variant="filterType === ptype.id ? 'flat' : 'outlined'"
    size="small"
    @click="filterType = ptype.id"
    class="cursor-pointer"
  >
    <span :style="{ color: filterType === ptype.id ? 'white' : ptype.color }">●</span>
    {{ ptype.abbreviation }}
  </v-chip>
  <v-chip
    :color="filterType === 'none' ? 'grey' : 'default'"
    :variant="filterType === 'none' ? 'tonal' : 'outlined'"
    size="small"
    @click="filterType = 'none'"
    class="cursor-pointer"
  >
    No Type
  </v-chip>
</div>
```

**Add reactive state and computed filters:**
```javascript
// Add to reactive state section (around line 590)
const filterType = ref('all')
const projectTypes = ref([])

// Fetch project types on mount
onMounted(async () => {
  try {
    // ... existing fetches ...

    // Fetch project types for filter chips (0440c)
    const typesResponse = await api.projectTypes.list()
    projectTypes.value = typesResponse.data || []
  } catch (error) {
    console.error('Failed to load project types:', error)
  }
})

// Update filteredBySearch computed to also filter by type
const filteredBySearch = computed(() => {
  let results = activeProductProjects.value

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    results = results.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.mission?.toLowerCase().includes(query) ||
        p.id.toLowerCase().includes(query) ||
        p.series_alias?.toLowerCase().includes(query)  // Search by series too
    )
  }

  // Type filter (0440c)
  if (filterType.value !== 'all') {
    if (filterType.value === 'none') {
      results = results.filter((p) => !p.project_type_id)
    } else {
      results = results.filter((p) => p.project_type_id === filterType.value)
    }
  }

  return results
})
```

**Add series-aware sorting (update sortedProjects computed):**
```javascript
// Replace existing sortedProjects computed (around line 680)
const sortedProjects = computed(() => {
  const sorted = [...filteredProjects.value]

  sorted.sort((a, b) => {
    // Active projects always come first
    const aActive = a.status === 'active' ? 0 : 1
    const bActive = b.status === 'active' ? 0 : 1
    if (aActive !== bActive) return aActive - bActive

    // Apply user-selected sort
    if (sortConfig.value && sortConfig.value.length > 0) {
      const { key, order } = sortConfig.value[0]
      const isAsc = order === 'asc'

      // Special handling for series sorting (0440c)
      if (key === 'series') {
        // Sort by: type abbreviation → series number → subseries
        const aType = a.project_type?.abbreviation || 'ZZZ'
        const bType = b.project_type?.abbreviation || 'ZZZ'
        if (aType !== bType) {
          return isAsc ? aType.localeCompare(bType) : bType.localeCompare(aType)
        }

        const aSeries = a.series_number || 99999
        const bSeries = b.series_number || 99999
        if (aSeries !== bSeries) {
          return isAsc ? aSeries - bSeries : bSeries - aSeries
        }

        const aSub = a.subseries || ''
        const bSub = b.subseries || ''
        return isAsc ? aSub.localeCompare(bSub) : bSub.localeCompare(aSub)
      }

      // Default sorting for other columns
      let aVal = a[key]
      let bVal = b[key]

      if (!aVal) aVal = ''
      if (!bVal) bVal = ''

      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase()
        bVal = bVal.toLowerCase()
      }

      if (aVal < bVal) return isAsc ? -1 : 1
      if (aVal > bVal) return isAsc ? 1 : -1
    }

    return 0
  })

  return sorted
})
```

**Add Series column to headers (optional - if user prefers separate column):**
```javascript
// Update headers array (around line 637)
const headers = [
  { title: 'Name', key: 'name', sortable: true, width: '25%' },
  // Optional: Add separate Series column
  // { title: 'Series', key: 'series', sortable: true, width: '10%' },
  { title: 'Status', key: 'status', sortable: true, width: '12%' },
  // ... rest of columns
]
```

---

#### 4. Frontend: `frontend/src/components/projects/ProjectTabs.vue`

**Update header display (replace lines 6-11):**

Replace:
```vue
<div class="d-flex align-center gap-4">
  <h1 class="text-h4">Project:</h1>
  <h2 class="project-name">{{ project?.name || 'Loading...' }}</h2>
</div>
<p class="text-subtitle-1 text-medium-emphasis mb-0">
  Project ID: {{ project?.project_id || project?.id || 'N/A' }}
</p>
```

With:
```vue
<div class="d-flex align-center gap-4">
  <h1 class="text-h4">Project:</h1>
  <h2 class="project-name d-flex align-center">
    <!-- Series Chip (0440c) -->
    <v-chip
      v-if="project?.series_alias"
      :color="project?.project_type?.color || '#607D8B'"
      size="small"
      variant="flat"
      class="mr-3"
      :title="project?.project_type?.label || 'Untyped'"
    >
      {{ project.series_alias }}
    </v-chip>
    <span>{{ project?.name || 'Loading...' }}</span>
  </h2>
</div>
<p class="text-subtitle-1 text-medium-emphasis mb-0">
  Project ID: {{ project?.project_id || project?.id || 'N/A' }}
</p>
```

**Add browser tab title watcher:**
```javascript
// Add to script setup section (around line 270)
import { watch } from 'vue'

// Update browser tab title when project loads (0440c)
watch(
  () => props.project,
  (project) => {
    if (project) {
      const prefix = project.series_alias ? `${project.series_alias} ` : ''
      document.title = `${prefix}${project.name} - GiljoAI`
    }
  },
  { immediate: true }
)

// Reset title on unmount
onBeforeUnmount(() => {
  document.title = 'GiljoAI MCP'
})
```

---

## Implementation Plan

### Phase 1: Backend Response Enhancement (2-3 hours)
**Recommended Agent:** TDD Implementor

1. Add `ProjectTypeResponse` schema to models.py
2. Extend `ProjectResponse` with taxonomy fields
3. Create `compute_series_alias()` helper function
4. Update response builders to include nested project_type
5. Add `joinedload(Project.project_type)` to queries
6. Write unit tests for `compute_series_alias()`:
   - Test with full taxonomy (type + series + subseries)
   - Test with type + series (no subseries)
   - Test with series only (no type)
   - Test with no series (returns None)

### Phase 2: Frontend Table Display (2-3 hours)
**Recommended Agent:** Frontend Tester

1. Add series chip to name column template
2. Add type filter chips below status filters
3. Update `filteredBySearch` computed with type filtering
4. Update `sortedProjects` with series-aware sorting
5. Fetch project types on mount for filter chips
6. Write component tests:
   - Test chip renders with correct color
   - Test filter chips show/hide correct projects
   - Test sorting by series works

### Phase 3: Project Detail Header & Browser Title (1-2 hours)
**Recommended Agent:** Frontend Tester

1. Add series chip to ProjectTabs.vue header
2. Add watch for browser tab title
3. Add cleanup on unmount
4. Write E2E test for full workflow

### Phase 4: Edge Cases & Polish (1 hour)
**Recommended Agent:** Frontend Tester

1. Test legacy projects (no taxonomy) display correctly
2. Test projects with partial taxonomy (series but no type)
3. Test filter edge cases (empty results)
4. Verify responsive design on mobile
5. Check accessibility (chip colors have sufficient contrast)

---

## Testing Requirements

### Unit Tests (Backend)

```python
# tests/test_compute_series_alias.py

import pytest
from api.endpoints.projects.crud import compute_series_alias
from unittest.mock import MagicMock

class TestComputeSeriesAlias:
    def test_full_taxonomy_returns_type_series_subseries(self):
        """BE-0042a format for full taxonomy."""
        project = MagicMock()
        project.series_number = 42
        project.subseries = 'a'
        project.project_type = MagicMock(abbreviation='BE')

        result = compute_series_alias(project)
        assert result == 'BE-0042a'

    def test_no_subseries_returns_type_series(self):
        """BE-0042 format when no subseries."""
        project = MagicMock()
        project.series_number = 42
        project.subseries = None
        project.project_type = MagicMock(abbreviation='BE')

        result = compute_series_alias(project)
        assert result == 'BE-0042'

    def test_no_type_returns_series_only(self):
        """0042 format when no type assigned."""
        project = MagicMock()
        project.series_number = 42
        project.subseries = None
        project.project_type = None

        result = compute_series_alias(project)
        assert result == '0042'

    def test_no_series_returns_none(self):
        """None when no series assigned (legacy project)."""
        project = MagicMock()
        project.series_number = None

        result = compute_series_alias(project)
        assert result is None

    def test_zero_padded_series(self):
        """Series number should be zero-padded to 4 digits."""
        project = MagicMock()
        project.series_number = 1
        project.subseries = None
        project.project_type = MagicMock(abbreviation='FE')

        result = compute_series_alias(project)
        assert result == 'FE-0001'
```

### Integration Tests (Frontend)

```javascript
// tests/components/ProjectsView.spec.js

import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import ProjectsView from '@/views/ProjectsView.vue'

describe('ProjectsView - Taxonomy Display (0440c)', () => {
  const vuetify = createVuetify()

  it('displays series chip with correct color when project has taxonomy', async () => {
    const wrapper = mount(ProjectsView, {
      global: { plugins: [vuetify] },
      data() {
        return {
          projects: [{
            id: '123',
            name: 'Test Project',
            series_alias: 'BE-0042a',
            project_type: { color: '#4CAF50', label: 'Backend' }
          }]
        }
      }
    })

    const chip = wrapper.find('[data-testid="series-chip"]')
    expect(chip.exists()).toBe(true)
    expect(chip.text()).toBe('BE-0042a')
    expect(chip.attributes('style')).toContain('#4CAF50')
  })

  it('hides series chip when project has no taxonomy', async () => {
    const wrapper = mount(ProjectsView, {
      global: { plugins: [vuetify] },
      data() {
        return {
          projects: [{
            id: '456',
            name: 'Legacy Project',
            series_alias: null,
            project_type: null
          }]
        }
      }
    })

    const chip = wrapper.find('[data-testid="series-chip"]')
    expect(chip.exists()).toBe(false)
  })

  it('filters projects by type when type chip clicked', async () => {
    // Test implementation
  })

  it('sorts projects by series correctly', async () => {
    // Test implementation
  })
})
```

### E2E Test

```javascript
// tests/e2e/project-taxonomy-display.spec.js

import { test, expect } from '@playwright/test'

test.describe('Project Taxonomy Display (0440c)', () => {
  test('displays series alias in project list and detail', async ({ page }) => {
    // Create a project with taxonomy via API or UI
    await page.goto('/projects')

    // Verify series chip in table
    const tableRow = page.locator('[data-testid="project-card"]').first()
    const seriesChip = tableRow.locator('.v-chip')
    await expect(seriesChip).toContainText('BE-0042')

    // Click to open project detail
    await tableRow.click()

    // Verify series chip in header
    const headerChip = page.locator('.project-header .v-chip')
    await expect(headerChip).toContainText('BE-0042')

    // Verify browser tab title
    await expect(page).toHaveTitle(/BE-0042/)
  })

  test('filters projects by type', async ({ page }) => {
    await page.goto('/projects')

    // Click Backend type filter
    await page.click('text=BE')

    // Verify only Backend projects shown
    const visibleProjects = page.locator('[data-testid="project-card"]')
    for (const project of await visibleProjects.all()) {
      const chip = project.locator('.v-chip')
      await expect(chip).toContainText('BE-')
    }
  })
})
```

### Manual Testing Procedure

1. **Setup:** Ensure 0440a/b are complete and you have projects with/without taxonomy
2. **Project List Table:**
   - [ ] Projects with full taxonomy show colored chip (e.g., "🟢 BE-0042a")
   - [ ] Projects with series only show "0042" (grey)
   - [ ] Projects without taxonomy show name only (no chip)
3. **Type Filtering:**
   - [ ] Click "BE" chip - only Backend projects shown
   - [ ] Click "No Type" - only legacy projects shown
   - [ ] Click "All" - all projects shown
4. **Sorting:**
   - [ ] Sort by series groups by type, then number, then subseries
   - [ ] Legacy projects sort to bottom
5. **Project Detail:**
   - [ ] Header shows colored chip before name
   - [ ] Browser tab shows "BE-0042 Project Name - GiljoAI"
6. **Edge Cases:**
   - [ ] Project with type but no series (should not show chip)
   - [ ] Project with series but no type (shows "0042" grey)
   - [ ] Delete project type - projects show "0042" (graceful degradation)

---

## Dependencies and Blockers

**Dependencies:**
1. 0440a must be complete (database schema, `project_type` relationship)
2. 0440b must be complete (API endpoints for project types)
3. Project queries must eagerly load `project_type` relationship

**Questions to Resolve:**
1. Should we add a "Series" column to the table or keep it in Name column? (Recommendation: Name column)
2. What color for untyped projects with series? (Recommendation: #607D8B grey)
3. Should sorting by series be default or user-selected? (Recommendation: User-selected)

---

## Success Criteria

- [ ] Backend returns `series_alias` in all project responses
- [ ] Backend returns nested `project_type` object with color
- [ ] Frontend displays colored series chips in project table
- [ ] Type filter chips work correctly
- [ ] Series sorting works correctly
- [ ] Project detail header shows series chip
- [ ] Browser tab title includes series alias
- [ ] Legacy projects (no taxonomy) display correctly
- [ ] All unit tests pass (>80% coverage)
- [ ] E2E test passes
- [ ] No console errors

---

## Rollback Plan

**If issues arise:**
1. Backend: Revert changes to `models.py` and `crud.py`
2. Frontend: Revert changes to `ProjectsView.vue` and `ProjectTabs.vue`
3. No database changes in this handover (display only)

**Safe rollback command:**
```bash
git checkout HEAD~1 -- api/endpoints/projects/models.py
git checkout HEAD~1 -- api/endpoints/projects/crud.py
git checkout HEAD~1 -- frontend/src/views/ProjectsView.vue
git checkout HEAD~1 -- frontend/src/components/projects/ProjectTabs.vue
```

---

## Additional Resources

- [Vuetify Chips](https://vuetifyjs.com/en/components/chips/)
- [HANDOVER_INSTRUCTIONS.md](HANDOVER_INSTRUCTIONS.md)
- [docs/SERVICES.md](../docs/SERVICES.md)
- Related: 0440a (Database), 0440b (Frontend UI)

---

## Completion Protocol

When complete:
1. Run tests: `pytest tests/ && cd frontend && npm run test:unit`
2. Run E2E: `cd frontend && npm run test:e2e`
3. Complete manual test procedure above
4. Update this handover with completion notes
5. Move to: `handovers/completed/0440c_project_taxonomy_display_integration-C.md`
6. Commit: `git commit -m "feat: Project taxonomy display integration (0440c)"`

---

**Remember:** The goal is to make the taxonomy VISIBLE. Users should immediately see their organized naming throughout the UI. Make the chips colorful and the filtering intuitive!
