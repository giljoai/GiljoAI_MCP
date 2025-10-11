# Template Manager UI Component Specifications

## Project: 5.1.c Dashboard Sub-Agent Visualization - Template Management Phase

**Designer**: designer agent
**Date**: 2025-01-15
**Version**: 1.0

---

## 1. TemplateManager.vue

### Overview

Main template management interface with CRUD operations, variable editor, and preview capabilities.

### Visual Design

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Template Manager Header                                      │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ 📝 Template Manager    [+ New Template] [Import] [Export] ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Search & Filters Bar                                         │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ 🔍 Search templates...  [Category ▼] [Role ▼] [Active ✓]  ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Template Data Table                                          │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Name ↓    Category    Role         Usage  Actions         ││
│ │ ─────────────────────────────────────────────────────────││
│ │ ✓ orchestrator  role  orchestrator   42   [👁][✏][🗑][📋]││
│ │ ✓ analyzer      role  analyzer       28   [👁][✏][🗑][📋]││
│ │ ✓ frontend_dev  role  frontend       15   [👁][✏][🗑][📋]││
│ │ □ custom_test   custom  -            0   [👁][✏][🗑][📋]││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Pagination                                                   │
│ [◀ Previous] Page 1 of 3 [Next ▶]  Showing 1-10 of 25       │
└─────────────────────────────────────────────────────────────┘
```

### Component Structure

```vue
<template>
  <v-container fluid>
    <!-- Header -->
    <v-row class="mb-4">
      <v-col cols="12">
        <v-card elevation="2" class="template-manager-header">
          <v-card-title class="d-flex align-center">
            <v-icon color="primary" class="mr-2">
              <!-- Use frontend/public/icons/document.svg -->
            </v-icon>
            <span class="text-h5">Template Manager</span>
            <v-spacer />

            <!-- Action Buttons -->
            <v-btn
              color="primary"
              variant="flat"
              prepend-icon="mdi-plus"
              @click="openNewTemplateDialog"
            >
              New Template
            </v-btn>
            <v-btn
              variant="outlined"
              class="ml-2"
              prepend-icon="mdi-import"
              @click="importTemplates"
            >
              Import
            </v-btn>
            <v-btn
              variant="outlined"
              class="ml-2"
              prepend-icon="mdi-export"
              @click="exportTemplates"
            >
              Export
            </v-btn>
          </v-card-title>
        </v-card>
      </v-col>
    </v-row>

    <!-- Search & Filters -->
    <v-row class="mb-4">
      <v-col cols="12">
        <v-card elevation="1">
          <v-card-text>
            <v-row dense align="center">
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="searchQuery"
                  prepend-inner-icon="mdi-magnify"
                  label="Search templates..."
                  density="compact"
                  hide-details
                  clearable
                  @input="debouncedSearch"
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="selectedCategory"
                  :items="categories"
                  label="Category"
                  density="compact"
                  hide-details
                  clearable
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-select
                  v-model="selectedRole"
                  :items="roles"
                  label="Role"
                  density="compact"
                  hide-details
                  clearable
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-checkbox
                  v-model="showActiveOnly"
                  label="Active Only"
                  density="compact"
                  hide-details
                />
              </v-col>
              <v-col cols="12" md="2">
                <v-btn variant="text" color="primary" @click="resetFilters">
                  Reset Filters
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Data Table -->
    <v-row>
      <v-col cols="12">
        <v-card elevation="2">
          <v-data-table
            :headers="headers"
            :items="filteredTemplates"
            :loading="loading"
            :items-per-page="itemsPerPage"
            class="template-data-table"
            hover
          >
            <!-- Custom row rendering -->
            <template v-slot:item.name="{ item }">
              <div class="d-flex align-center">
                <v-checkbox
                  v-model="item.is_active"
                  density="compact"
                  hide-details
                  @change="toggleActive(item)"
                />
                <span class="ml-2 font-weight-medium">{{ item.name }}</span>
                <v-chip
                  v-if="item.is_default"
                  size="x-small"
                  color="primary"
                  class="ml-2"
                >
                  DEFAULT
                </v-chip>
              </div>
            </template>

            <template v-slot:item.category="{ item }">
              <v-chip
                :color="getCategoryColor(item.category)"
                size="small"
                label
              >
                {{ item.category }}
              </v-chip>
            </template>

            <template v-slot:item.usage_count="{ item }">
              <div class="d-flex align-center">
                <span>{{ item.usage_count }}</span>
                <v-tooltip location="top">
                  <template v-slot:activator="{ props }">
                    <v-icon
                      v-bind="props"
                      size="small"
                      class="ml-1"
                      color="grey"
                    >
                      mdi-information-outline
                    </v-icon>
                  </template>
                  <div>
                    <div>Last used: {{ formatDate(item.last_used_at) }}</div>
                    <div>Avg generation: {{ item.avg_generation_ms }}ms</div>
                  </div>
                </v-tooltip>
              </div>
            </template>

            <template v-slot:item.actions="{ item }">
              <div class="d-flex gap-1">
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  @click="previewTemplate(item)"
                >
                  <v-icon size="small">mdi-eye</v-icon>
                  <v-tooltip activator="parent" location="top"
                    >Preview</v-tooltip
                  >
                </v-btn>
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  @click="editTemplate(item)"
                >
                  <v-icon size="small">mdi-pencil</v-icon>
                  <v-tooltip activator="parent" location="top">Edit</v-tooltip>
                </v-btn>
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  color="error"
                  @click="deleteTemplate(item)"
                >
                  <v-icon size="small">mdi-delete</v-icon>
                  <v-tooltip activator="parent" location="top"
                    >Delete</v-tooltip
                  >
                </v-btn>
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  @click="viewArchive(item)"
                >
                  <v-icon size="small">mdi-history</v-icon>
                  <v-tooltip activator="parent" location="top"
                    >Version History</v-tooltip
                  >
                </v-btn>
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  @click="duplicateTemplate(item)"
                >
                  <v-icon size="small">mdi-content-copy</v-icon>
                  <v-tooltip activator="parent" location="top"
                    >Duplicate</v-tooltip
                  >
                </v-btn>
              </div>
            </template>

            <!-- Loading state -->
            <template v-slot:loading>
              <MascotLoader message="Loading templates..." />
            </template>

            <!-- Empty state -->
            <template v-slot:no-data>
              <v-empty-state
                icon="mdi-file-document-outline"
                title="No templates found"
                text="Create your first template to get started"
              >
                <v-btn color="primary" @click="openNewTemplateDialog">
                  Create Template
                </v-btn>
              </v-empty-state>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- Template Editor Dialog -->
    <TemplateEditor
      v-model="editorDialog"
      :template="selectedTemplate"
      @save="saveTemplate"
      @cancel="editorDialog = false"
    />

    <!-- Template Preview Dialog -->
    <TemplatePreview
      v-model="previewDialog"
      :template="selectedTemplate"
      @close="previewDialog = false"
    />

    <!-- Archive Viewer Dialog -->
    <TemplateArchive
      v-model="archiveDialog"
      :template="selectedTemplate"
      @restore="restoreVersion"
      @close="archiveDialog = false"
    />
  </v-container>
</template>
```

### Color Scheme (from docs/color_themes.md)

- **Background**: `#182739` (Dark Blue - main background)
- **Cards**: `#1e3147` (Medium Dark Blue)
- **Table Headers**: `#0e1c2d` (Darkest Blue)
- **Primary Actions**: `#ffc300` (Yellow)
- **Success States**: `#67bd6d` (Green)
- **Error Actions**: `#c6298c` (Pink/Red)
- **Text**: `#e1e1e1` (Light Gray)
- **Borders**: `#315074` (Medium Blue)

### Icons Used (from frontend/public/icons/)

- `document.svg` - Template manager header
- `edit.svg` - Edit action
- `view.svg` - Preview action
- `delete.svg` - Delete action
- `archive.svg` - Version history
- `copy.svg` - Duplicate template
- `save.svg` - Save changes
- `checkmark.svg` - Active status

---

## 2. TemplateEditor.vue

### Overview

Modal dialog for creating and editing templates with syntax highlighting and variable management.

### Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│ Edit Template: orchestrator                          [X]    │
├─────────────────────────────────────────────────────────────┤
│ Template Details                                             │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Name: [orchestrator_____________]  Category: [role    ▼] ││
│ │ Role: [orchestrator         ▼]     Version: [1.0.1____]  ││
│ │ Description: [Template for orchestrator agents_________] ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Template Content                          Variables          │
│ ┌─────────────────────────────┬─────────────────────────────┐│
│ │ 1  You are the {role} agent │ Detected Variables:         ││
│ │ 2  for project {project}.   │ • role                      ││
│ │ 3                           │ • project                   ││
│ │ 4  Your mission:            │                             ││
│ │ 5  {mission_content}        │ + Add Variable              ││
│ │ 6                           │                             ││
│ │ 7  Success criteria:        │ Default Values:             ││
│ │ 8  {success_metrics}        │ role: [_______________]     ││
│ │                             │ project: [____________]     ││
│ └─────────────────────────────┴─────────────────────────────┘│
│                                                               │
│ Behavioral Rules                  Success Criteria           │
│ ┌─────────────────────────────┬─────────────────────────────┐│
│ │ □ Report progress regularly │ □ Complete all tasks        ││
│ │ □ Coordinate with team      │ □ Pass all tests            ││
│ │ + Add Rule                  │ + Add Criteria              ││
│ └─────────────────────────────┴─────────────────────────────┘│
│                                                               │
│ Preview with Augmentation                                    │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Augmentation: [Focus on performance optimization_______]  ││
│ │ ─────────────────────────────────────────────────────────││
│ │ Generated Mission Preview:                                ││
│ │ You are the orchestrator agent for project GiljoAI.      ││
│ │ [Preview content...]                                      ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ [Cancel]                    [Test Generate] [Save Template]  │
└─────────────────────────────────────────────────────────────┘
```

### Component Features

#### Code Editor

- **Syntax Highlighting**: Variables highlighted in yellow (#ffc300)
- **Line Numbers**: Show line numbers for reference
- **Auto-complete**: Suggest existing variables
- **Variable Detection**: Auto-detect {variable} patterns
- **Validation**: Check for unclosed brackets

#### Variable Management

- **Auto-detection**: Parse template for {variables}
- **Add/Remove**: Manual variable management
- **Default Values**: Set defaults for testing
- **Type Hints**: Optional type specifications

#### Preview Panel

- **Live Preview**: Real-time generation preview
- **Augmentation Test**: Test runtime augmentations
- **Performance**: Show generation time in ms
- **Token Count**: Display approximate token usage

---

## 3. TemplateArchive.vue

### Overview

Version history viewer with diff comparison and restore functionality.

### Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│ Version History: orchestrator                        [X]    │
├─────────────────────────────────────────────────────────────┤
│ Timeline View                                               │
│ ┌───────────────────────────────────────────────────────────┐│
│ │  Current ● v1.0.3 (Active)                               ││
│ │     │    Modified by: system | 2025-01-15 14:30          ││
│ │     │                                                     ││
│ │     ○── v1.0.2                                           ││
│ │     │    Modified by: user | 2025-01-14 10:15            ││
│ │     │    Changes: Updated success criteria               ││
│ │     │                                                     ││
│ │     ○── v1.0.1                                           ││
│ │     │    Modified by: system | 2025-01-13 09:00          ││
│ │     │    Changes: Added behavioral rules                 ││
│ │     │                                                     ││
│ │     ○── v1.0.0 (Original)                               ││
│ │          Created by: system | 2025-01-10 08:00           ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Version Comparison                                          │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Compare: [v1.0.3 ▼] with [v1.0.2 ▼]   [Show Diff]       ││
│ ├───────────────────────────────────────────────────────────┤│
│ │ v1.0.2                    │ v1.0.3 (Current)             ││
│ │ ───────────────────────────┼──────────────────────────────││
│ │ Line 5:                    │ Line 5:                     ││
│ │ - Report weekly            │ + Report daily              ││
│ │                            │                             ││
│ │ Line 12:                   │ Line 12:                    ││
│ │ - Success rate > 80%       │ + Success rate > 90%        ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Actions                                                      │
│ [View Full]  [Download]  [Restore This Version]  [Close]    │
└─────────────────────────────────────────────────────────────┘
```

### Features

#### Timeline View

- **Visual Timeline**: Vertical timeline with version nodes
- **Version Details**: Author, timestamp, change summary
- **Current Indicator**: Highlight active version
- **Collapsed View**: Expand/collapse for space

#### Diff Viewer

- **Side-by-side**: Compare two versions
- **Inline Diff**: Alternative inline view
- **Syntax Highlight**: Maintain template highlighting
- **Change Statistics**: Lines added/removed/modified

#### Actions

- **Restore**: Revert to previous version
- **Download**: Export specific version
- **View Full**: See complete template content
- **Compare Any**: Select any two versions

---

## 4. TemplatePreview.vue

### Overview

Read-only preview dialog with mission generation testing.

### Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│ Template Preview: frontend_developer                 [X]    │
├─────────────────────────────────────────────────────────────┤
│ Template Information                                        │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Name: frontend_developer                                 ││
│ │ Category: role | Version: 1.0.2 | Usage: 28 times        ││
│ │ Last Used: 2025-01-15 10:30 | Avg Generation: 45ms       ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Test Generation                                             │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Variable Values:                                          ││
│ │ project: [GiljoAI_________________]                      ││
│ │ component: [SubAgentTimeline______]                      ││
│ │ framework: [Vue 3_________________]                      ││
│ │                                                           ││
│ │ Augmentation: [Add focus on performance________________] ││
│ │                                                           ││
│ │ [Generate Preview]                                        ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Generated Mission                                           │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ You are the frontend_developer agent for project GiljoAI.││
│ │ Your task is to implement SubAgentTimeline component     ││
│ │ using Vue 3 framework.                                   ││
│ │                                                           ││
│ │ Additional focus: Add focus on performance               ││
│ │                                                           ││
│ │ Success Criteria:                                         ││
│ │ • Component renders correctly                            ││
│ │ • All tests pass                                         ││
│ │ • Performance metrics met                                ││
│ │                                                           ││
│ │ Generation time: 42ms | Tokens: ~250                     ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ [Copy Mission]  [Export Template]  [Edit Template]  [Close] │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Integration Requirements

### API Endpoints

```typescript
// Template CRUD
GET    /api/templates              // List all templates
GET    /api/templates/:id          // Get single template
POST   /api/templates              // Create new template
PUT    /api/templates/:id          // Update template
DELETE /api/templates/:id          // Delete template

// Archive operations
GET    /api/templates/:id/archive  // Get version history
POST   /api/templates/:id/restore  // Restore version

// Generation
POST   /api/templates/generate     // Test generation
GET    /api/templates/stats        // Usage statistics
```

### WebSocket Events

```javascript
// Real-time updates
websocketService.onMessage("template:created", (data) => {
  // Add to list
});

websocketService.onMessage("template:updated", (data) => {
  // Update in list
});

websocketService.onMessage("template:deleted", (data) => {
  // Remove from list
});
```

### Pinia Store

```javascript
// stores/templates.js
export const useTemplateStore = defineStore("templates", {
  state: () => ({
    templates: [],
    selectedTemplate: null,
    filters: {
      search: "",
      category: null,
      role: null,
      activeOnly: true,
    },
    loading: false,
    error: null,
  }),

  actions: {
    async fetchTemplates() {
      // GET /api/templates
    },

    async createTemplate(template) {
      // POST /api/templates
    },

    async updateTemplate(id, updates) {
      // PUT /api/templates/:id
    },

    async deleteTemplate(id) {
      // DELETE /api/templates/:id
    },

    async generatePreview(templateId, variables, augmentation) {
      // POST /api/templates/generate
    },
  },
});
```

---

## 6. Responsive Design

### Mobile (320px - 600px)

- Stack filters vertically
- Simplified table (name, category, actions)
- Full-screen dialogs
- Touch-optimized controls

### Tablet (600px - 960px)

- 2-column filter layout
- Abbreviated table columns
- Modal dialogs
- Touch + mouse support

### Desktop (960px+)

- Full table with all columns
- Side-by-side editor panels
- Floating dialogs
- Keyboard shortcuts

---

## 7. Performance Requirements

- **Table Load**: <300ms for 100 templates
- **Search**: <100ms debounced
- **Generation Preview**: <100ms
- **Archive Load**: <200ms for 50 versions
- **Auto-save**: Every 30 seconds in editor

---

## 8. Accessibility

- **Keyboard Navigation**: Tab through all controls
- **Screen Reader**: ARIA labels and roles
- **Focus Management**: Trap focus in dialogs
- **High Contrast**: Support system preferences
- **Error Messages**: Clear, actionable feedback

---

## 9. Success Metrics

✅ All CRUD operations functional
✅ Variable detection and substitution working
✅ Version history with restore capability
✅ Generation preview <100ms
✅ Responsive on all screen sizes
✅ Theme colors properly applied
✅ WebSocket real-time updates
✅ Export/Import functionality

---

## 10. Handoff Instructions

### For frontend_developer:

1. **Implement in this order**:

   - TemplateManager.vue (main interface)
   - TemplateEditor.vue (create/edit dialog)
   - TemplatePreview.vue (preview dialog)
   - TemplateArchive.vue (version history)

2. **Use existing components**:

   - MascotLoader.vue for loading states
   - ToastManager.vue for notifications
   - ConnectionStatus.vue for API status

3. **Follow color theme strictly**:

   - Reference docs/color_themes.md
   - Use CSS variables for theme switching

4. **Test all breakpoints**:

   - 320px, 600px, 960px, 1280px
   - Ensure touch gestures work on mobile

5. **Integrate with backend**:
   - Template Manager API at /api/templates
   - WebSocket events for real-time sync

---

**Designer Agent Signature**: Template Manager UI specifications complete
**Delivered**: 2025-01-15
**Next Step**: Implementation by frontend_developer
