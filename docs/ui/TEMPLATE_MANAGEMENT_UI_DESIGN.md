# Template Management UI Design Specification

**Feature**: Agent Template Management Interface
**Target Users**: System administrators, orchestrators
**Location**: GiljoAI MCP Dashboard → Templates section
**Status**: Design specification for implementation

---

## Overview

Web-based interface for managing AI agent templates in the GiljoAI MCP system. Enables CRUD operations on templates stored in PostgreSQL, with automatic export to `.claude/agents/*.md` files for Claude Code integration.

---

## User Flows

### Primary Flow: Browse and Manage Templates

```
Dashboard → Templates Menu → Template List → 
  ↓
  ├─ View Template Details
  ├─ Edit Template
  ├─ Create New Template
  ├─ Delete Template
  └─ Export Template (to .md file)
```

### Secondary Flow: Orchestrator Selecting Agent

```
Job Creation → Agent Type Dropdown (populated from templates) → 
Select Template → Job Created with Template Mission
```

---

## Screen Layouts

### 1. Template List View (Main Screen)

**Route**: `/templates`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  GiljoAI MCP Dashboard                    [User Menu]  │
├────────────────────────────────────────────────────────┤
│  [Dashboard] [Jobs] [Templates] [Settings]             │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Templates                              [+ New Template]│
│  ─────────────────────────────────────────────────────│
│                                                         │
│  Search: [________________] 🔍  Filter: [All ▼]        │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 📋 orchestrator                    v2.0.0  [Edit] │ │
│  │ Project Manager & Team Lead                       │ │
│  │ Tags: orchestrator, delegation, discovery         │ │
│  │ ─────────────────────────────────────────────────│ │
│  │ Status: ● Active  |  Last modified: 2 days ago    │ │
│  │ [View Details] [Export .md] [Deactivate]         │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 🔧 implementer                 v1.5.0  [Edit]     │ │
│  │ System Developer - Code implementation            │ │
│  │ Tags: developer, tdd, implementation              │ │
│  │ ─────────────────────────────────────────────────│ │
│  │ Status: ● Active  |  Last modified: 1 week ago    │ │
│  │ [View Details] [Export .md] [Deactivate]         │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  [Showing 2 of 6 templates]              [1] 2 3 >    │
└────────────────────────────────────────────────────────┘
```

**Components**:
- **Header Bar**: Navigation menu, user profile
- **Action Button**: "+ New Template" (top right)
- **Search Bar**: Real-time filter by name/role/tags
- **Filter Dropdown**: All, Active, Inactive, By Category
- **Template Cards**: Compact view with key info
- **Pagination**: Bottom of list

**Template Card Properties**:
- Icon (emoji or custom)
- Template name
- Version number
- One-line description
- Tags (pills)
- Status indicator (active/inactive)
- Last modified timestamp
- Action buttons (View, Edit, Export, Deactivate)

---

### 2. Template Detail View

**Route**: `/templates/:id`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  ← Back to Templates                      [Edit] [Export]│
├────────────────────────────────────────────────────────┤
│                                                         │
│  📋 orchestrator                            v2.0.0     │
│  Project Manager & Team Lead                          │
│  ───────────────────────────────────────────────────  │
│                                                         │
│  [Overview] [Template Content] [Variables] [Rules]    │
│                                                         │
│  ┌─ Overview Tab ────────────────────────────────────┐│
│  │                                                     ││
│  │  Role:           orchestrator                      ││
│  │  Category:       role                              ││
│  │  Version:        2.0.0                             ││
│  │  Status:         ● Active                          ││
│  │  Preferred Tool: claude                            ││
│  │                                                     ││
│  │  Description:                                      ││
│  │  Enhanced orchestrator template with discovery-   ││
│  │  first workflow and 30-80-10 principle...         ││
│  │                                                     ││
│  │  Tags:                                             ││
│  │  [orchestrator] [delegation] [discovery] [default]││
│  │                                                     ││
│  │  Variables Required:                               ││
│  │  • project_name                                    ││
│  │  • project_mission                                 ││
│  │  • product_name                                    ││
│  │                                                     ││
│  │  Behavioral Rules (7):                             ││
│  │  ✓ Coordinate all agents effectively              ││
│  │  ✓ Read vision document completely                ││
│  │  ✓ Enforce 3-tool rule                            ││
│  │  [View all 7 rules]                                ││
│  │                                                     ││
│  │  Success Criteria (6):                             ││
│  │  ✓ Vision document fully read                     ││
│  │  ✓ All product config reviewed                    ││
│  │  ✓ Serena MCP discoveries documented              ││
│  │  [View all 6 criteria]                             ││
│  │                                                     ││
│  │  Created:        2025-10-15 14:30 UTC             ││
│  │  Last Modified:  2025-10-17 09:15 UTC             ││
│  │  Modified By:    admin                             ││
│  │                                                     ││
│  └─────────────────────────────────────────────────── ┘│
│                                                         │
└────────────────────────────────────────────────────────┘
```

**Tabs**:
1. **Overview**: Metadata, description, tags, status
2. **Template Content**: Full template text (read-only or edit mode)
3. **Variables**: List of required/optional variables with descriptions
4. **Rules**: Behavioral rules and success criteria

---

### 3. Create/Edit Template Form

**Route**: `/templates/new` or `/templates/:id/edit`

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│  ← Cancel                        [Save Draft] [Publish]│
├────────────────────────────────────────────────────────┤
│                                                         │
│  Create New Template                                   │
│  ───────────────────────────────────────────────────  │
│                                                         │
│  Basic Information                                     │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Name *         [implementer_______________]       │ │
│  │ Role *         [implementer_______________]       │ │
│  │ Category *     [Role-based ▼]                     │ │
│  │ Version *      [1.0.0_______________]             │ │
│  │ Preferred Tool [claude ▼]                         │ │
│  │                                                    │ │
│  │ Description *                                     │ │
│  │ ┌──────────────────────────────────────────────┐ │ │
│  │ │ System Developer responsible for code impl... │ │ │
│  │ │                                               │ │ │
│  │ └──────────────────────────────────────────────┘ │ │
│  │                                                    │ │
│  │ Tags           [developer] [tdd] [+ Add tag]     │ │
│  │                                                    │ │
│  │ Status         ○ Active  ○ Inactive               │ │
│  │ Default        ☐ Set as default template          │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  Template Content *                                    │
│  ┌──────────────────────────────────────────────────┐ │
│  │ You are the {role} for: {project_name}           │ │
│  │                                                    │ │
│  │ YOUR MISSION: {custom_mission}                   │ │
│  │                                                    │ │
│  │ ## CORE EXPERTISE                                │ │
│  │ ...                                              │ │
│  │                                                    │ │
│  │ [Markdown editor with syntax highlighting]       │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  Variables (3)                        [+ Add Variable] │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 1. project_name    (Required)                    │ │
│  │ 2. project_mission (Required)                    │ │
│  │ 3. product_name    (Optional)                    │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  Behavioral Rules (4)                [+ Add Rule]      │
│  ┌──────────────────────────────────────────────────┐ │
│  │ ✓ Write clean, maintainable code                 │ │
│  │ ✓ Follow architectural specs exactly             │ │
│  │ ✓ Report blockers immediately                    │ │
│  │ ✓ Hand off at 80% context usage                  │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  Success Criteria (3)                [+ Add Criterion] │
│  ┌──────────────────────────────────────────────────┐ │
│  │ ✓ All features implemented correctly             │ │
│  │ ✓ Code follows project standards                 │ │
│  │ ✓ Tests pass                                     │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│                          [Cancel] [Save Draft] [Publish]│
└────────────────────────────────────────────────────────┘
```

**Form Sections**:
1. **Basic Information**: Name, role, category, version, description
2. **Template Content**: Markdown editor with variable substitution preview
3. **Variables**: Dynamic list with add/remove
4. **Behavioral Rules**: Text input list
5. **Success Criteria**: Text input list

**Validation**:
- Required fields marked with *
- Version format: semver (1.0.0)
- Name uniqueness check
- Variable references in content must match Variables list

---

### 4. Export Template Modal

**Triggered by**: "Export .md" button

**Layout**:
```
┌──────────────────────────────────────────┐
│  Export Template to File                  │
├──────────────────────────────────────────┤
│                                           │
│  Template: orchestrator v2.0.0           │
│                                           │
│  Export Format:                           │
│  ○ Claude Code (.claude/agents/*.md)     │
│  ○ Codex (Custom format)                 │
│  ○ Gemini (Custom format)                │
│                                           │
│  Output Path:                             │
│  [.claude/agents/orchestrator.md_____]   │
│                                           │
│  Preview:                                 │
│  ┌────────────────────────────────────┐  │
│  │ ---                                 │  │
│  │ name: orchestrator                  │  │
│  │ description: "Project Manager..."   │  │
│  │ model: sonnet                       │  │
│  │ color: blue                         │  │
│  │ ---                                 │  │
│  │                                     │  │
│  │ You are the orchestrator for...    │  │
│  └────────────────────────────────────┘  │
│                                           │
│  [Cancel]              [Export & Download]│
└──────────────────────────────────────────┘
```

**Features**:
- Format selection (Claude/Codex/Gemini)
- Path customization
- Live preview of generated file
- Download button

---

## Component Specifications

### Template Card Component

**Props**:
```typescript
interface TemplateCardProps {
  id: number
  name: string
  role: string
  version: string
  description: string
  category: string
  tags: string[]
  isActive: boolean
  isDefault: boolean
  lastModified: Date
  modifiedBy: string
}
```

**Events**:
- `@view` - Navigate to detail view
- `@edit` - Navigate to edit form
- `@export` - Open export modal
- `@toggle-status` - Activate/deactivate template
- `@delete` - Open delete confirmation

**File**: `frontend/src/components/templates/TemplateCard.vue`

---

### Template Editor Component

**Props**:
```typescript
interface TemplateEditorProps {
  templateId?: number  // undefined for new templates
  mode: 'create' | 'edit'
}
```

**Features**:
- Markdown editor with syntax highlighting
- Variable substitution preview
- Auto-save to drafts
- Validation warnings
- Unsaved changes warning

**File**: `frontend/src/components/templates/TemplateEditor.vue`

---

### Variable Manager Component

**Props**:
```typescript
interface VariableManagerProps {
  variables: TemplateVariable[]
  templateContent: string  // To validate variable usage
}

interface TemplateVariable {
  name: string
  required: boolean
  description?: string
  defaultValue?: string
}
```

**Features**:
- Add/remove variables
- Mark as required/optional
- Validation against template content
- Highlight unused variables

**File**: `frontend/src/components/templates/VariableManager.vue`

---

## API Endpoints Required

### Template CRUD

```typescript
// List templates
GET /api/templates
Query params: ?category=role&status=active&search=orchestrator
Response: { templates: TemplateResponse[] }

// Get single template
GET /api/templates/:id
Response: TemplateDetailResponse

// Create template
POST /api/templates
Body: TemplateCreateRequest
Response: TemplateResponse

// Update template
PATCH /api/templates/:id
Body: TemplateUpdateRequest
Response: TemplateResponse

// Delete template
DELETE /api/templates/:id
Response: { success: boolean }

// Export template to file
POST /api/templates/:id/export
Body: { format: 'claude' | 'codex' | 'gemini', path?: string }
Response: { file_path: string, content: string }
```

### Template Status Management

```typescript
// Activate/deactivate
PATCH /api/templates/:id/status
Body: { is_active: boolean }
Response: TemplateResponse

// Set as default
PATCH /api/templates/:id/default
Body: { is_default: boolean }
Response: TemplateResponse
```

---

## Data Models (Pydantic Schemas)

### TemplateListResponse

```python
class TemplateListResponse(BaseModel):
    id: int
    name: str
    role: str
    version: str
    category: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool
    is_default: bool
    last_modified: datetime
    modified_by: str
```

### TemplateDetailResponse

```python
class TemplateDetailResponse(BaseModel):
    id: int
    tenant_key: str
    product_id: Optional[int] = None
    name: str
    category: str
    role: str
    template_content: str
    variables: List[str] = Field(default_factory=list)
    behavioral_rules: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    preferred_tool: str
    is_default: bool
    is_active: bool
    description: Optional[str] = None
    version: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: str
    modified_by: Optional[str] = None
```

### TemplateCreateRequest

```python
class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., max_length=50)
    template_content: str = Field(..., min_length=10)
    description: Optional[str] = None
    version: str = Field(default="1.0.0", pattern=r'^\d+\.\d+\.\d+$')
    variables: List[str] = Field(default_factory=list)
    behavioral_rules: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    preferred_tool: str = Field(default="claude")
    tags: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)
```

### TemplateUpdateRequest

```python
class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    template_content: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = Field(None, pattern=r'^\d+\.\d+\.\d+$')
    variables: Optional[List[str]] = None
    behavioral_rules: Optional[List[str]] = None
    success_criteria: Optional[List[str]] = None
    preferred_tool: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
```

### ExportTemplateRequest

```python
class ExportTemplateRequest(BaseModel):
    format: str = Field(..., pattern=r'^(claude|codex|gemini)$')
    output_path: Optional[str] = None
    include_metadata: bool = Field(default=True)
```

---

## State Management (Vue Store)

### Template Store Module

**File**: `frontend/src/stores/templateStore.js`

```javascript
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useTemplateStore = defineStore('templates', {
  state: () => ({
    templates: [],
    currentTemplate: null,
    loading: false,
    error: null,
    filters: {
      search: '',
      category: 'all',
      status: 'all'
    },
    pagination: {
      page: 1,
      pageSize: 10,
      total: 0
    }
  }),
  
  getters: {
    filteredTemplates: (state) => {
      let filtered = state.templates
      
      if (state.filters.search) {
        filtered = filtered.filter(t => 
          t.name.includes(state.filters.search) ||
          t.role.includes(state.filters.search) ||
          t.tags.some(tag => tag.includes(state.filters.search))
        )
      }
      
      if (state.filters.category !== 'all') {
        filtered = filtered.filter(t => t.category === state.filters.category)
      }
      
      if (state.filters.status !== 'all') {
        filtered = filtered.filter(t => 
          state.filters.status === 'active' ? t.is_active : !t.is_active
        )
      }
      
      return filtered
    },
    
    activeTemplates: (state) => state.templates.filter(t => t.is_active),
    defaultTemplate: (state) => state.templates.find(t => t.is_default)
  },
  
  actions: {
    async fetchTemplates() {
      this.loading = true
      try {
        const response = await api.get('/api/templates', {
          params: {
            category: this.filters.category === 'all' ? undefined : this.filters.category,
            status: this.filters.status === 'all' ? undefined : this.filters.status,
            search: this.filters.search || undefined,
            page: this.pagination.page,
            page_size: this.pagination.pageSize
          }
        })
        this.templates = response.data.templates
        this.pagination.total = response.data.total
        this.error = null
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },
    
    async fetchTemplate(id) {
      this.loading = true
      try {
        const response = await api.get(`/api/templates/${id}`)
        this.currentTemplate = response.data
        this.error = null
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },
    
    async createTemplate(templateData) {
      this.loading = true
      try {
        const response = await api.post('/api/templates', templateData)
        this.templates.push(response.data)
        this.error = null
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateTemplate(id, templateData) {
      this.loading = true
      try {
        const response = await api.patch(`/api/templates/${id}`, templateData)
        const index = this.templates.findIndex(t => t.id === id)
        if (index !== -1) {
          this.templates[index] = response.data
        }
        this.error = null
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async deleteTemplate(id) {
      this.loading = true
      try {
        await api.delete(`/api/templates/${id}`)
        this.templates = this.templates.filter(t => t.id !== id)
        this.error = null
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async exportTemplate(id, format, outputPath) {
      this.loading = true
      try {
        const response = await api.post(`/api/templates/${id}/export`, {
          format,
          output_path: outputPath
        })
        this.error = null
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async toggleStatus(id, isActive) {
      return this.updateTemplate(id, { is_active: isActive })
    },
    
    async setDefault(id) {
      return this.updateTemplate(id, { is_default: true })
    },
    
    setFilter(filterName, value) {
      this.filters[filterName] = value
      this.pagination.page = 1  // Reset to first page
      this.fetchTemplates()
    },
    
    setPage(page) {
      this.pagination.page = page
      this.fetchTemplates()
    }
  }
})
```

---

## User Interactions & Feedback

### Success States

**Template Created**:
```
✅ Template "implementer v1.0.0" created successfully
   [View Template] [Create Another]
```

**Template Exported**:
```
✅ Template exported to .claude/agents/orchestrator.md
   [Open Folder] [Export Another Format]
```

**Template Activated/Deactivated**:
```
✅ Template "orchestrator" activated
   Available for job creation
```

### Error States

**Validation Error**:
```
⚠️ Cannot save template
   • Name "orchestrator" already exists
   • Variable {missing_var} used in content but not declared
   • Version format must be x.y.z (e.g., 1.0.0)
```

**Export Error**:
```
❌ Failed to export template
   Output path .claude/agents/ is not writable
   [Choose Different Path] [Contact Support]
```

**Delete Confirmation**:
```
⚠️ Delete Template?
   
   Template: orchestrator v2.0.0
   
   This template is:
   • Used in 15 active jobs
   • Set as default template
   • Referenced in 3 orchestrations
   
   Deleting will NOT affect existing jobs but new jobs
   cannot use this template.
   
   [Cancel] [Delete Template]
```

---

## Responsive Design

### Desktop (≥1200px)
- Side-by-side layout for list + detail
- Full template editor with preview pane
- 3-column grid for template cards

### Tablet (768px - 1199px)
- Stacked layout (list → detail on separate screen)
- 2-column grid for template cards
- Collapsed sidebar navigation

### Mobile (≤767px)
- Single column layout
- Bottom sheet for quick actions
- Swipe gestures for navigation
- Simplified template editor (no live preview)

---

## Accessibility (WCAG 2.1 AA)

### Keyboard Navigation
- Tab order: Search → Filters → Template Cards → Action Buttons
- Enter/Space: Activate buttons and links
- Escape: Close modals and cancel forms
- Arrow keys: Navigate template list

### Screen Readers
- ARIA labels for all interactive elements
- Live regions for status updates
- Form field descriptions and error announcements
- Template card content summarized

### Visual Accessibility
- Color contrast ratio ≥ 4.5:1 for text
- Focus indicators on all interactive elements
- Status indicators use icons + text (not color alone)
- Font size minimum 16px, adjustable

---

## Performance Considerations

### Optimization Strategies
- **Virtual Scrolling**: For template lists >100 items
- **Lazy Loading**: Load template content only when viewing detail
- **Debounced Search**: 300ms delay on search input
- **Cached Data**: Store fetched templates in Pinia store
- **Optimistic Updates**: Immediate UI feedback, rollback on error

### Load Times
- Template list: < 500ms
- Template detail: < 300ms
- Template creation: < 1s
- Export to file: < 2s

---

## Security Considerations

### Authorization
- **Admin Only**: Template creation, editing, deletion
- **Read Access**: All authenticated users can view templates
- **Multi-Tenant Isolation**: Users only see templates for their tenant

### Input Validation
- **Server-Side**: All template fields validated in API
- **Client-Side**: Pre-validation to improve UX
- **Sanitization**: Template content sanitized to prevent XSS
- **Path Validation**: Export paths validated to prevent directory traversal

### Audit Trail
- **Created By**: Track user who created template
- **Modified By**: Track user who last modified template
- **Changelog**: Optional: Track version history
- **Export Log**: Log all template exports with timestamp and user

---

## Integration Points

### With Existing Features

**1. Job Creation Flow**:
```javascript
// When creating agent job, fetch available templates
const templates = await templateStore.fetchTemplates({ status: 'active' })

// Populate agent type dropdown
agentTypeOptions.value = templates.map(t => ({
  value: t.role,
  label: `${t.name} v${t.version}`,
  description: t.description
}))
```

**2. Orchestrator Agent Selection**:
```javascript
// In JobCoordinator.spawn_child_jobs()
// Fetch template by role
const template = await db.query(AgentTemplate).filter(
  AgentTemplate.role == child_spec['agent_type'],
  AgentTemplate.is_active == true,
  AgentTemplate.tenant_key == tenant_key
).first()

// Use template for mission
mission = template.template_content.format(**child_spec['variables'])
```

**3. Agent File Generator**:
```javascript
// Auto-export when template saved
async afterTemplateSaved(template) {
  if (settings.autoExportToClaudeCode) {
    await templateStore.exportTemplate(
      template.id,
      'claude',
      '.claude/agents/'
    )
  }
}
```

---

## Testing Requirements

### Unit Tests
- **Template Store**: All actions and getters
- **TemplateCard Component**: Props, events, rendering
- **TemplateEditor Component**: Validation, save, cancel
- **Variable Manager**: Add/remove, validation

### Integration Tests
- **Create Template Flow**: Form submission → API call → Success feedback
- **Edit Template Flow**: Load → Modify → Save → Updated in list
- **Export Template**: Export → File created → Content validation
- **Filter Templates**: Search → Filter → Pagination

### E2E Tests
- **Complete CRUD Workflow**: Create → View → Edit → Delete
- **Multi-User Scenario**: Admin creates, user views
- **Error Handling**: Network errors, validation failures
- **Export Workflow**: Export to Claude → Verify file → Import back

---

## Implementation Phases

### Phase 1: Core UI (Week 1)
- ✅ Template list view
- ✅ Template detail view
- ✅ Basic CRUD operations
- ✅ Search and filter

### Phase 2: Advanced Features (Week 2)
- ✅ Template editor with markdown support
- ✅ Variable manager
- ✅ Behavioral rules editor
- ✅ Export to .md file

### Phase 3: Integration (Week 3)
- ✅ Job creation integration
- ✅ Auto-export on save
- ✅ Template versioning
- ✅ Audit trail

### Phase 4: Polish (Week 4)
- ✅ Responsive design
- ✅ Accessibility improvements
- ✅ Performance optimization
- ✅ Documentation

---

## Wireframe Assets

### Template List View (Desktop)
![Template List Wireframe](wireframes/template-list.png)

### Template Editor (Desktop)
![Template Editor Wireframe](wireframes/template-editor.png)

### Export Modal
![Export Modal Wireframe](wireframes/export-modal.png)

---

## Open Questions

1. **Template Versioning**: Should we support version history (changelog)?
2. **Template Inheritance**: Should templates support inheritance (base template + override)?
3. **Template Marketplace**: Future: Share templates with community?
4. **Template Testing**: Should we provide a "Test Template" sandbox mode?
5. **Real-Time Collaboration**: Should multiple admins be able to edit simultaneously?

---

## Conclusion

This UI design provides a comprehensive, production-grade interface for managing AI agent templates in the GiljoAI MCP system. The design prioritizes:

- **Usability**: Intuitive workflows for template management
- **Integration**: Seamless connection with job creation and orchestration
- **Flexibility**: Support for multiple export formats (Claude, Codex, Gemini)
- **Security**: Role-based access and multi-tenant isolation
- **Performance**: Optimized for large template libraries

**Next Steps**:
1. Review and approve design specification
2. Create detailed wireframes/mockups
3. Begin Phase 1 implementation (Core UI)
4. Iterate based on user feedback

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-19
**Author**: AI Architecture Team
**Status**: Awaiting approval for implementation
