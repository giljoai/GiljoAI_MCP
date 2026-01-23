# Handover: Project Taxonomy & Series System - Frontend UI

**Date:** 2026-01-22
**From Agent:** UX Designer
**To Agent:** Frontend Implementor (TDD-Implementor + UX-Designer)
**Priority:** Medium
**Estimated Complexity:** 8-12 hours
**Status:** Not Started
**Prerequisite:** 0440a (Database & Backend) MUST be complete

---

## Task Summary

Implement frontend UI components for the Project Taxonomy & Series System, enabling users to organize projects using a hierarchical naming scheme similar to handovers (e.g., BE-0042a, FE-0120). This enhances project discoverability and organization.

**What needs to be done:**
- Add "Project Series" section to Create/Edit Project dialog in ProjectsView.vue
- Create reusable ProjectSeriesSelector component with type/series/subseries selection
- Create AddTypeModal for custom project type creation
- Integrate with backend APIs (GET /api/v1/project-types/, POST endpoints, validation)
- Implement real-time validation and live preview of taxonomy strings

**Why it's important:**
- Users managing 50+ projects need better organization than flat lists
- Taxonomy enables filtering, grouping, and logical sequences
- Mimics familiar handover numbering system (user-validated UX pattern)

**Expected outcome:**
- Users can optionally assign project type (BE/FE/DB/custom), series (0001-9999), subseries (a-z)
- Live preview shows formatted taxonomy (e.g., "🟢 BE-0042a")
- Warnings displayed if taxonomy combination already exists
- Custom types persist tenant-wide for reuse

---

## Context and Background

### User Requirements
Users requested project organization similar to the handover system after finding it intuitive. The feature must be:
1. **Optional** - Not required for project creation
2. **Flexible** - Custom types allowed beyond BE/FE/DB defaults
3. **Validated** - No duplicate taxonomy combinations
4. **Visual** - Color-coded types with live preview

### Architectural Decisions
- **Three-level hierarchy**: Type (BE) → Series (0042) → Subseries (a)
- **Tenant isolation**: Project types are tenant-specific (no global types)
- **Database storage**: `project_type_id` (FK), `series_number` (int), `subseries` (char) in projects table
- **Frontend state**: Types cached in Pinia store, series availability fetched on-demand

### Related Features
- Complements existing project filtering/search in ProjectsView.vue
- Will enable future features: taxonomy-based project grouping, series navigation
- Backend implements `/api/v1/project-types/` CRUD and `/api/v1/projects/validate-taxonomy`

---

## Technical Details

### Files to Modify

#### 1. `frontend/src/views/ProjectsView.vue`
**Current state:** Dialog has Project Name, Description fields (lines 300-355)
**Changes needed:**
- Add collapsible expansion panel "Project Series (Optional)" after description field
- Import and embed `<ProjectSeriesSelector>` component
- Pass project data via v-model for two-way binding
- Display validation warnings if taxonomy exists

**Code location:**
```vue
<!-- Line ~350 - After description textarea, before form closing -->
<v-expansion-panels variant="accordion" class="mb-3">
  <v-expansion-panel>
    <v-expansion-panel-title>
      <v-icon start>mdi-file-tree</v-icon>
      Project Series (Optional)
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <ProjectSeriesSelector
        v-model:projectTypeId="projectData.project_type_id"
        v-model:seriesNumber="projectData.series_number"
        v-model:subseries="projectData.subseries"
        @validation-warning="handleValidationWarning"
      />
    </v-expansion-panel-text>
  </v-expansion-panel>
</v-expansion-panels>
```

#### 2. `frontend/src/components/projects/ProjectSeriesSelector.vue` (NEW)
**Purpose:** Reusable component for type/series/subseries selection
**Props:**
- `projectTypeId` (String, optional) - Selected type UUID
- `seriesNumber` (Number, optional) - Selected series (1-9999)
- `subseries` (String, optional) - Selected subseries ('a'-'z')

**Emits:**
- `update:projectTypeId` - When type changes
- `update:seriesNumber` - When series changes
- `update:subseries` - When subseries changes
- `validation-warning` - When duplicate taxonomy detected

**Key functionality:**
- Fetch project types from API on mount
- Show type dropdown with colored dots (using type.color hex)
- "Add custom type..." option opens AddTypeModal
- Series dropdown shows next 5 available by default, with pagination
- Subseries dropdown: fixed list (none, a-z)
- Live preview updates as selections change
- Debounced validation call to `/api/v1/projects/validate-taxonomy`

#### 3. `frontend/src/components/projects/AddTypeModal.vue` (NEW)
**Purpose:** Modal for creating custom project types
**Fields:**
- Abbreviation (2-4 chars, uppercase only, required)
- Label (1-50 chars, required)
- Color (hex picker, default #E91E63)

**Validation:**
- Abbreviation regex: `/^[A-Z]{2,4}$/`
- Label max length: 50 chars
- Color format: `/^#[0-9A-Fa-f]{6}$/`
- Live preview shows: `[colored-dot] ABBR - Label`

**On submit:**
- POST `/api/v1/project-types/` with validated data
- Emit `type-created` event with new type object
- Close modal and select new type in parent selector

#### 4. `frontend/src/services/api.js`
**Add to exports:**
```javascript
projectTypes: {
  list: () => apiClient.get('/api/v1/project-types/'),
  create: (data) => apiClient.post('/api/v1/project-types/', data),
  update: (id, data) => apiClient.put(`/api/v1/project-types/${id}`, data),
  delete: (id) => apiClient.delete(`/api/v1/project-types/${id}`),
},

projects: {
  // ... existing methods ...
  validateTaxonomy: (typeId, series, subseries) =>
    apiClient.get('/api/v1/projects/validate-taxonomy', {
      params: { type_id: typeId, series, subseries }
    }),
  getNextSeries: (typeId) =>
    apiClient.get('/api/v1/projects/next-series', {
      params: { type_id: typeId }
    }),
  getAvailableSeries: (typeId, limit = 5) =>
    apiClient.get('/api/v1/projects/available-series', {
      params: { type_id: typeId, limit }
    }),
}
```

#### 5. `frontend/src/stores/projectTypes.js` (NEW - Optional)
**Purpose:** Cache project types to avoid repeated API calls
**State:**
```javascript
{
  types: [], // Array of ProjectType objects
  loading: false,
  lastFetched: null,
}
```

**Actions:**
- `fetchTypes()` - Fetch and cache types (with 5-minute TTL)
- `createType(data)` - POST new type and update cache
- `deleteType(id)` - DELETE type and update cache

**Alternative:** Store types in projectStore if Pinia store overhead not needed

---

## Implementation Plan

### Phase 1: API Integration (2-3 hours)
**Actions:**
1. Add project type endpoints to `api.js` (list, create, update, delete)
2. Add taxonomy validation endpoints (validateTaxonomy, getAvailableSeries)
3. Create `projectTypes.js` Pinia store OR add to existing projectStore
4. Write unit tests for API methods and store actions

**Expected outcome:**
- `api.projectTypes.list()` returns tenant's project types
- Store caches types and invalidates on create/delete
- Validation endpoint returns `{ exists: boolean, project_id?: string }`

**Testing criteria:**
- Mock API responses in Vitest tests
- Verify store updates cache correctly
- Test error handling for network failures

### Phase 2: AddTypeModal Component (2-3 hours)
**Actions:**
1. Create `AddTypeModal.vue` with Vuetify components:
   - `v-dialog` with max-width 600px
   - `v-text-field` for abbreviation (uppercase auto-transform)
   - `v-text-field` for label
   - `v-color-picker` or `v-menu` + color swatches for color
   - Live preview using computed property
2. Implement validation rules using Vuetify form validation
3. Add submit handler: POST to API, emit `type-created`, close modal
4. Write unit tests using Vitest + Vue Test Utils

**Expected outcome:**
- Modal opens on "Add custom type..." click
- Form validates before submission
- New type appears in parent selector dropdown immediately
- Preview shows formatted type with colored dot

**Testing criteria:**
- Unit test: Form validation rejects invalid input
- Unit test: Successful submission emits event with correct payload
- Unit test: Color picker updates preview in real-time
- Integration test: Modal integrated with ProjectSeriesSelector

**Vuetify Components:**
```vue
<template>
  <v-dialog :model-value="modelValue" max-width="600" persistent>
    <v-card>
      <v-card-title>Add Project Type</v-card-title>
      <v-card-text>
        <v-form ref="form" v-model="formValid">
          <v-text-field
            v-model="abbreviation"
            label="Abbreviation (2-4 chars)"
            :rules="[rules.abbreviation]"
            hint="e.g., DEV, TEST"
            counter="4"
            @input="abbreviation = abbreviation.toUpperCase()"
          />
          <v-text-field
            v-model="label"
            label="Label"
            :rules="[rules.label]"
            hint="e.g., DevOps, Testing"
            counter="50"
          />
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-text-field
                :model-value="color"
                label="Color"
                readonly
                v-bind="props"
              >
                <template v-slot:prepend-inner>
                  <div :style="{ backgroundColor: color, width: '24px', height: '24px', borderRadius: '50%' }" />
                </template>
              </v-text-field>
            </template>
            <v-color-picker v-model="color" mode="hex" />
          </v-menu>

          <!-- Live Preview -->
          <v-alert type="info" variant="tonal" class="mt-3">
            <div class="d-flex align-center">
              <div :style="{ backgroundColor: color, width: '16px', height: '16px', borderRadius: '50%', marginRight: '8px' }" />
              <strong>{{ abbreviation || 'ABBR' }} - {{ label || 'Label' }}</strong>
            </div>
          </v-alert>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="$emit('update:modelValue', false)">Cancel</v-btn>
        <v-btn color="primary" :disabled="!formValid" @click="handleSubmit">Add Type</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
```

### Phase 3: ProjectSeriesSelector Component (3-4 hours)
**Actions:**
1. Create `ProjectSeriesSelector.vue` with three-section layout:
   - **Type dropdown**: `v-select` with custom item template (colored dot + label)
   - **Series dropdown**: `v-select` with pagination footer (Show: 5/10/25/ALL)
   - **Subseries dropdown**: `v-select` with fixed list (none, a-z)
2. Add "Add custom type..." option to type dropdown (opens AddTypeModal)
3. Implement live preview computed property: `previewTaxonomy()`
4. Debounce validation check (500ms) when selections change
5. Display warning alert if taxonomy exists
6. Write unit tests for component logic

**Expected outcome:**
- Type selection updates series availability
- Series dropdown shows ✓ for used numbers (disabled unless subseries selected)
- Live preview updates instantly: "🟢 BE-0042a"
- Warning shown if combination exists: "⚠️ BE-0042 already exists (Project: Feature X)"

**Testing criteria:**
- Unit test: Type selection triggers series fetch
- Unit test: Preview formats correctly with all/some/no selections
- Unit test: Validation debounce works (not called on every keystroke)
- Integration test: Component integrated with AddTypeModal

**Vuetify Components:**
```vue
<template>
  <div class="project-series-selector">
    <!-- Type Selection -->
    <v-select
      :model-value="projectTypeId"
      @update:model-value="handleTypeChange"
      :items="typeOptions"
      label="Type"
      item-title="display"
      item-value="id"
      density="compact"
      variant="outlined"
    >
      <template v-slot:item="{ props, item }">
        <v-list-item v-bind="props">
          <template v-slot:prepend>
            <div
              :style="{ backgroundColor: item.raw.color, width: '12px', height: '12px', borderRadius: '50%' }"
            />
          </template>
        </v-list-item>
        <v-divider v-if="item.raw.id === 'divider'" />
        <v-list-item v-if="item.raw.id === 'add-custom'" @click="showAddTypeModal = true">
          <template v-slot:prepend>
            <v-icon>mdi-plus-circle</v-icon>
          </template>
          <v-list-item-title>Add custom type...</v-list-item-title>
        </v-list-item>
      </template>
    </v-select>

    <!-- Series & Subseries Row -->
    <v-row>
      <v-col cols="6">
        <v-select
          :model-value="seriesNumber"
          @update:model-value="$emit('update:seriesNumber', $event)"
          :items="seriesOptions"
          label="Series"
          density="compact"
          variant="outlined"
          :disabled="!projectTypeId"
        >
          <template v-slot:append>
            <v-btn size="x-small" variant="text" @click="toggleSeriesLimit">
              Show: {{ seriesLimit }}
            </v-btn>
          </template>
        </v-select>
      </v-col>
      <v-col cols="6">
        <v-select
          :model-value="subseries"
          @update:model-value="$emit('update:subseries', $event)"
          :items="subseries Options"
          label="Subseries"
          density="compact"
          variant="outlined"
          :disabled="!seriesNumber"
        />
      </v-col>
    </v-row>

    <!-- Live Preview -->
    <v-alert v-if="previewTaxonomy" type="info" variant="tonal" density="compact" class="mt-2">
      <div class="d-flex align-center">
        <div
          :style="{ backgroundColor: selectedType?.color, width: '12px', height: '12px', borderRadius: '50%', marginRight: '8px' }"
        />
        <strong>Preview: {{ previewTaxonomy }}</strong>
      </div>
    </v-alert>

    <!-- Validation Warning -->
    <v-alert v-if="validationWarning" type="warning" variant="tonal" density="compact" class="mt-2">
      {{ validationWarning }}
    </v-alert>

    <!-- Add Type Modal -->
    <AddTypeModal
      v-model="showAddTypeModal"
      @type-created="handleTypeCreated"
    />
  </div>
</template>
```

### Phase 4: ProjectsView Integration (1-2 hours)
**Actions:**
1. Import `ProjectSeriesSelector` into `ProjectsView.vue`
2. Add expansion panel to Create/Edit dialog (after description field)
3. Add taxonomy fields to `projectData` reactive object:
   ```javascript
   projectData: {
     name: '',
     description: '',
     project_type_id: null,
     series_number: null,
     subseries: null,
   }
   ```
4. Handle validation warnings in parent component
5. Update form submit to include taxonomy fields in API payload
6. Test end-to-end flow: create project with taxonomy

**Expected outcome:**
- Expansion panel collapses by default (optional feature)
- Creating project with taxonomy succeeds
- Editing project preserves existing taxonomy
- Form validation works with optional taxonomy fields

**Testing criteria:**
- E2E test: Create project with full taxonomy (type + series + subseries)
- E2E test: Create project with partial taxonomy (type only)
- E2E test: Create project without taxonomy (all null)
- E2E test: Edit project and change taxonomy
- E2E test: Validation warning prevents duplicate taxonomy

### Phase 5: Testing & Polish (2 hours)
**Actions:**
1. Write comprehensive unit tests:
   - AddTypeModal form validation
   - ProjectSeriesSelector component logic
   - Store/API integration
2. Write integration tests:
   - Modal + Selector interaction
   - Selector + ProjectsView interaction
3. Write E2E tests using Playwright (if available) or Cypress:
   - Full project creation flow with taxonomy
   - Custom type creation and immediate use
   - Duplicate taxonomy warning
4. Manual testing:
   - Keyboard navigation (Tab, Enter, Escape)
   - Screen reader compatibility (ARIA labels)
   - Color contrast validation (WCAG AA)
   - Responsive behavior (mobile, tablet, desktop)

**Expected outcome:**
- All unit tests passing (>80% coverage)
- E2E tests cover critical user flows
- Accessibility checklist verified
- Responsive design tested on multiple screen sizes

**Testing criteria:**
- Vitest: 30+ unit tests passing
- E2E: 5+ critical flows automated
- Manual: Accessibility checklist 100% complete (see below)

---

## Dependencies and Blockers

### Dependencies
1. **0440a MUST be complete:**
   - Database schema: `project_types`, `projects` table updates
   - Backend API: `/api/v1/project-types/` CRUD endpoints
   - Backend API: `/api/v1/projects/validate-taxonomy`
   - Backend API: `/api/v1/projects/available-series`

2. **Vuetify 3 components:**
   - `v-select` with custom templates
   - `v-color-picker` or color menu
   - `v-expansion-panels` for collapsible section
   - `v-dialog` for modal

3. **Pinia store (optional):**
   - If projectTypes store created, ensure Pinia configured in `main.js`

### Known Blockers
- **None identified** (assuming 0440a complete and backend APIs tested)

### Questions Needing Answers
1. Should project types be deletable if projects reference them?
   - **Recommendation:** Backend should prevent deletion (FK constraint) or cascade update to null
2. Should series numbers have leading zeros in display? (e.g., "0042" vs "42")
   - **Recommendation:** Display with leading zeros (4 digits) for consistency with handovers
3. Should taxonomy be editable after project creation?
   - **Recommendation:** Yes, allow editing to fix mistakes

---

## Testing Requirements

### Unit Tests (Vitest + Vue Test Utils)

#### AddTypeModal.vue
```javascript
describe('AddTypeModal', () => {
  test('validates abbreviation format (2-4 uppercase chars)', async () => {
    const wrapper = mount(AddTypeModal, { props: { modelValue: true } })
    const input = wrapper.find('[label="Abbreviation"]')

    await input.setValue('dev')
    expect(input.vm.errorMessages).toContain('Must be 2-4 uppercase letters')

    await input.setValue('DEV')
    expect(input.vm.errorMessages).toHaveLength(0)
  })

  test('live preview updates with form input', async () => {
    const wrapper = mount(AddTypeModal, { props: { modelValue: true } })

    await wrapper.find('[label="Abbreviation"]').setValue('DEV')
    await wrapper.find('[label="Label"]').setValue('DevOps')
    await wrapper.setData({ color: '#E91E63' })

    expect(wrapper.find('.preview').text()).toContain('DEV - DevOps')
    expect(wrapper.find('.preview div').attributes('style')).toContain('#E91E63')
  })

  test('emits type-created event on successful submit', async () => {
    const wrapper = mount(AddTypeModal, {
      props: { modelValue: true },
      global: { mocks: { $api: { projectTypes: { create: vi.fn().mockResolvedValue({ data: { id: 'uuid' } }) } } } }
    })

    await wrapper.find('[label="Abbreviation"]').setValue('DEV')
    await wrapper.find('[label="Label"]').setValue('DevOps')
    await wrapper.find('[color="primary"]').trigger('click')

    expect(wrapper.emitted('type-created')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual([false]) // Modal closes
  })
})
```

#### ProjectSeriesSelector.vue
```javascript
describe('ProjectSeriesSelector', () => {
  test('fetches project types on mount', async () => {
    const mockStore = { fetchTypes: vi.fn() }
    mount(ProjectSeriesSelector, {
      global: { provide: { projectTypesStore: mockStore } }
    })

    expect(mockStore.fetchTypes).toHaveBeenCalled()
  })

  test('preview taxonomy formats correctly', async () => {
    const wrapper = mount(ProjectSeriesSelector, {
      props: {
        projectTypeId: 'uuid',
        seriesNumber: 42,
        subseries: 'a'
      },
      global: {
        provide: {
          projectTypesStore: {
            types: [{ id: 'uuid', abbreviation: 'BE', color: '#4CAF50' }]
          }
        }
      }
    })

    expect(wrapper.vm.previewTaxonomy).toBe('BE-0042a')
  })

  test('validates taxonomy with debounce', async () => {
    vi.useFakeTimers()
    const validateSpy = vi.fn()
    const wrapper = mount(ProjectSeriesSelector, {
      global: { mocks: { $api: { projects: { validateTaxonomy: validateSpy } } } }
    })

    await wrapper.setProps({ seriesNumber: 42 })
    await wrapper.setProps({ seriesNumber: 43 })

    vi.advanceTimersByTime(500)
    expect(validateSpy).toHaveBeenCalledTimes(1) // Debounced

    vi.useRealTimers()
  })
})
```

### Integration Tests

```javascript
describe('ProjectSeriesSelector + AddTypeModal Integration', () => {
  test('custom type creation updates selector dropdown', async () => {
    const wrapper = mount(ProjectSeriesSelector, {
      global: {
        plugins: [createPinia()],
        mocks: { $api: mockApi }
      }
    })

    // Open add type modal
    await wrapper.find('[item-value="add-custom"]').trigger('click')
    const modal = wrapper.findComponent(AddTypeModal)

    // Fill form
    await modal.find('[label="Abbreviation"]').setValue('DEV')
    await modal.find('[label="Label"]').setValue('DevOps')
    await modal.find('[color="primary"]').trigger('click')

    // Verify new type appears in selector
    await wrapper.vm.$nextTick()
    expect(wrapper.find('v-select').props('items')).toContainEqual(
      expect.objectContaining({ abbreviation: 'DEV', label: 'DevOps' })
    )
  })
})
```

### E2E Tests (Playwright / Cypress)

```javascript
describe('Project Creation with Taxonomy', () => {
  test('creates project with full taxonomy', async () => {
    await page.goto('/projects')
    await page.click('[data-test="create-project-btn"]')

    await page.fill('[label="Project Name"]', 'Test Project')
    await page.fill('[label="Project Description"]', 'Test description')

    // Expand series section
    await page.click('text=Project Series (Optional)')

    // Select type
    await page.click('[label="Type"]')
    await page.click('text=BE - Backend')

    // Select series
    await page.click('[label="Series"]')
    await page.click('text=0042')

    // Select subseries
    await page.click('[label="Subseries"]')
    await page.click('text=a')

    // Verify preview
    await expect(page.locator('text=Preview: BE-0042a')).toBeVisible()

    // Submit
    await page.click('[data-test="submit-project-btn"]')

    // Verify project created
    await expect(page.locator('text=Project created successfully')).toBeVisible()
  })

  test('shows warning for duplicate taxonomy', async () => {
    // ... similar setup ...

    await page.click('[label="Series"]')
    await page.click('text=0001') // Existing series

    await expect(page.locator('text=BE-0001 already exists')).toBeVisible()
  })
})
```

---

## Success Criteria

### Definition of Done
- [ ] AddTypeModal component created with form validation
- [ ] ProjectSeriesSelector component created with live preview
- [ ] ProjectsView dialog updated with taxonomy section
- [ ] API integration complete (projectTypes, validation endpoints)
- [ ] Pinia store (or equivalent) caching project types
- [ ] All unit tests passing (>80% coverage)
- [ ] E2E tests cover critical flows (create with taxonomy, custom type, validation)
- [ ] Accessibility checklist verified (see below)
- [ ] Manual testing complete (keyboard nav, screen readers, responsive)
- [ ] Documentation updated (component API docs, user guides if needed)

### Accessibility Checklist
**CRITICAL - Verify before marking complete:**
- [ ] Color contrast ≥ 4.5:1 for text (use WebAIM contrast checker)
- [ ] Focus indicators visible on all interactive elements (type/series/subseries dropdowns)
- [ ] Complete keyboard navigation (Tab, Shift+Tab, Enter, Escape)
- [ ] ARIA labels on dropdowns: `aria-label="Project type"`, etc.
- [ ] Form labels properly associated with inputs
- [ ] Error messages descriptive and actionable ("Abbreviation must be 2-4 uppercase letters")
- [ ] Color not sole indicator (colored dots + text labels)
- [ ] Modal can be closed with Escape key
- [ ] Screen reader announces validation warnings

### Responsive Breakpoints
- [ ] Mobile (< 600px): Stacked layout, series/subseries full width
- [ ] Tablet (600-960px): Two-column layout for series/subseries
- [ ] Desktop (> 960px): Optimal layout with all controls visible

---

## Rollback Plan

### If Things Go Wrong

#### Scenario 1: API Integration Fails
**Symptom:** 500 errors from `/api/v1/project-types/`
**Action:**
1. Check backend logs: `tail -f F:\GiljoAI_MCP\logs\api_server.log`
2. Verify 0440a migration ran: `PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT * FROM project_types;"`
3. If backend broken, disable frontend feature:
   ```vue
   <!-- In ProjectsView.vue -->
   <v-expansion-panel v-if="false"> <!-- TEMPORARY DISABLE -->
   ```

#### Scenario 2: Vuetify Component Incompatibility
**Symptom:** `v-color-picker` not rendering or throwing errors
**Action:**
1. Check Vuetify version: `npm list vuetify` (should be ^3.x)
2. Fallback: Use `v-menu` + color swatches instead of picker:
   ```vue
   <v-menu>
     <template v-slot:activator="{ props }">
       <v-btn v-bind="props">{{ color }}</v-btn>
     </template>
     <v-card>
       <v-card-text>
         <div class="color-swatches">
           <v-btn v-for="c in colorOptions" @click="color = c" />
         </div>
       </v-card-text>
     </v-card>
   </v-menu>
   ```

#### Scenario 3: Performance Issues (Slow Series Dropdown)
**Symptom:** Dropdown laggy when showing 100+ series numbers
**Action:**
1. Reduce default limit from 25 to 5: `seriesLimit = 5`
2. Implement virtual scrolling (Vuetify 3 supports this):
   ```vue
   <v-virtual-scroll :items="seriesOptions" height="300" />
   ```
3. Add debouncing to series fetching (already implemented in plan)

#### Complete Rollback
If feature needs complete removal:
1. Revert `ProjectsView.vue` changes: `git checkout HEAD -- frontend/src/views/ProjectsView.vue`
2. Delete new components: `rm frontend/src/components/projects/{ProjectSeriesSelector,AddTypeModal}.vue`
3. Revert API changes: `git checkout HEAD -- frontend/src/services/api.js`
4. Frontend reverts to pre-0440b state (no taxonomy UI)

---

## Additional Resources

### Vuetify 3 Documentation
- [v-select API](https://vuetifyjs.com/en/components/selects/)
- [v-color-picker API](https://vuetifyjs.com/en/components/color-pickers/)
- [v-expansion-panels API](https://vuetifyjs.com/en/components/expansion-panels/)
- [v-dialog API](https://vuetifyjs.com/en/components/dialogs/)
- [Form Validation](https://vuetifyjs.com/en/features/forms/)

### Design Patterns in Existing Codebase
- **Modal pattern**: `frontend/src/components/settings/modals/ClaudeConfigModal.vue` (lines 1-100)
- **Dropdown with custom items**: ProjectsView.vue status filter chips (lines 96-115)
- **Form validation**: ProjectsView.vue create dialog (lines 334-355)
- **Pinia store pattern**: `frontend/src/stores/projects.js`

### Testing Resources
- [Vitest + Vue Test Utils Guide](https://vitest.dev/guide/)
- [Vuetify Testing Guide](https://vuetifyjs.com/en/getting-started/unit-testing/)
- [Playwright Vue Component Testing](https://playwright.dev/docs/test-components)

### Related Handovers
- **0440a**: Database & Backend (prerequisite - verify complete before starting)
- **0243 series**: GUI Redesign (reference for Vuetify patterns, testing strategy)

### GitHub Issues
- Check repo for related issues: `https://github.com/patrik-giljoai/GiljoAI-MCP/issues?q=is%3Aissue+taxonomy`

---

## Recommended Sub-Agent

**Primary:** `ux-designer` (Vue component design, accessibility, responsive layout)
**Secondary:** `tdd-implementor` (unit/integration test creation)
**Tertiary:** `frontend-tester` (E2E test automation, manual testing)

**Why UX Designer:**
- Requires strong Vuetify component knowledge
- Accessibility compliance critical (WCAG AA)
- Responsive design across breakpoints
- User experience optimization (live preview, validation warnings)

**Why TDD Implementor:**
- Test-first approach ensures robust validation logic
- Complex component interactions (modal + selector + API)
- Debouncing and async state management

**Coordination:**
1. UX Designer creates component structure and styling
2. TDD Implementor writes tests and refines logic
3. Frontend Tester verifies E2E flows and accessibility

---

## Progress Updates

### [Date] - [Agent/Session]
**Status:** [Not Started | In Progress | Blocked | Completed]
**Work Done:**
- [Specific changes made]
- [Tests added/passed]
- [Issues discovered]

**Next Steps:**
- [What's remaining]
- [New blockers]
- [Questions for user]

---

## Implementation Notes

### Color Palette Recommendations
Default project types should use accessible, distinct colors:
- **BE (Backend):** #4CAF50 (Green) - Success/operational theme
- **FE (Frontend):** #2196F3 (Blue) - Visual/UI theme
- **DB (Database):** #FF9800 (Orange) - Data/storage theme

Custom types default to: #E91E63 (Pink) - User-defined theme

All colors verified for WCAG AA contrast against white background.

### Debounce Implementation
Use Lodash debounce or Vue composable:
```javascript
import { debounce } from 'lodash-es'

const debouncedValidation = debounce(async (typeId, series, subseries) => {
  const { data } = await api.projects.validateTaxonomy(typeId, series, subseries)
  if (data.exists) {
    validationWarning.value = `Taxonomy already exists (Project: ${data.project_name})`
  } else {
    validationWarning.value = null
  }
}, 500)
```

### Series Number Display
Always display with leading zeros (4 digits):
```javascript
const formatSeries = (num) => String(num).padStart(4, '0')
// 42 → "0042"
```

### Subseries List
Fixed array, no custom values:
```javascript
const subseriesOptions = [
  { title: '(none)', value: null },
  ...Array.from({ length: 26 }, (_, i) => ({
    title: String.fromCharCode(97 + i), // 'a'-'z'
    value: String.fromCharCode(97 + i)
  }))
]
```

---

**Remember:** This is an OPTIONAL feature. Ensure all validations gracefully handle null values (no taxonomy selected). Projects without taxonomy should create successfully without errors.
