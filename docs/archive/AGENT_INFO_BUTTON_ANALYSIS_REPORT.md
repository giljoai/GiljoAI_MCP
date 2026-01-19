# Agent Info Button & Modal Implementation Analysis Report

**Project**: GiljoAI MCP
**Date**: 2025-11-23
**Status**: Complete Analysis

---

## EXECUTIVE SUMMARY

The GiljoAI MCP frontend has a **fully functional info button system** for displaying agent details and orchestrator prompts. The implementation follows clean patterns with proper separation of concerns:

- **LaunchTab.vue**: Info buttons (ℹ️) for Orchestrator and Agent Team cards
- **AgentDetailsModal.vue**: Reusable modal for displaying agent templates and orchestrator prompt
- **API Integration**: Separate endpoints for agent templates (`/api/v1/templates/`) and orchestrator prompt (`/api/v1/system/orchestrator-prompt`)

**Critical Finding**: The orchestrator **does NOT have a template** in the template manager—it uses a dedicated system endpoint instead. This is intentional design.

---

## 1. CURRENT IMPLEMENTATION ANALYSIS

### 1.1 LaunchTab Component
**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue`

#### Info Button Markup

**Orchestrator Card** (Lines 39-55):
```vue
<div class="orchestrator-card">
  <v-avatar :color="orchestratorAvatarColor" size="32" class="agent-avatar">
    <span class="orchestrator-text">Or</span>
  </v-avatar>
  <span class="agent-name">Orchestrator</span>
  <v-icon size="small" class="lock-icon">mdi-lock</v-icon>              <!-- LINE 44 -->
  <v-icon
    size="small"
    class="info-icon"
    role="button"
    tabindex="0"
    @click="handleOrchestratorInfo"
    @keydown.enter="handleOrchestratorInfo"
  >
    mdi-information                                                       <!-- LINE 53 -->
  </v-icon>
</div>
```

**Agent Team Cards** (Lines 62-82):
```vue
<div
  v-for="agent in nonOrchestratorAgents"
  :key="agent.agent_id || agent.job_id"
  class="agent-slim-card"
>
  <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
    {{ getAgentInitials(agent.agent_type) }}
  </div>
  <span class="agent-name">{{ agent.agent_type }}</span>
  <v-icon size="small" class="lock-icon">mdi-lock</v-icon>               <!-- LINE 71 -->
  <v-icon
    size="small"
    class="info-icon"
    role="button"
    tabindex="0"
    @click="handleAgentInfo(agent)"
    @keydown.enter="handleAgentInfo(agent)"
  >
    mdi-information                                                       <!-- LINE 80 -->
  </v-icon>
</div>
```

#### Icon Configuration

| Component | Icon 1 | Icon 2 |
|-----------|--------|--------|
| Orchestrator | `mdi-lock` (line 44) | `mdi-information` (line 53) |
| Agent Team | `mdi-lock` (line 71) | `mdi-information` (line 80) |

#### Handler Functions (Lines 331-349)

```javascript
/**
 * Handle Info icon click for Orchestrator
 */
function handleOrchestratorInfo() {
  selectedAgent.value = {
    agent_type: 'orchestrator',
    agent_name: 'Orchestrator',
    id: 'orchestrator',
  }
  showDetailsModal.value = true
}

/**
 * Handle Info icon click for Agent Team members
 */
function handleAgentInfo(agent) {
  selectedAgent.value = {
    ...agent,
    id: agent.id || agent.job_id,
  }
  showDetailsModal.value = true
}
```

#### Modal Integration (Lines 91-94)

```vue
<!-- Agent Details Modal -->
<AgentDetailsModal
  v-model="showDetailsModal"
  :agent="selectedAgent"
/>
```

#### Styling (Lines 582-595, 664-680)

**Orchestrator Card Icons**:
```scss
.lock-icon {
  color: $color-text-tertiary;
  flex-shrink: 0;
}

.info-icon {
  color: $color-text-tertiary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Agent Team Card Icons**:
```scss
.lock-icon {
  color: $color-text-secondary;

  &:hover {
    color: $color-text-primary;
  }
}

.info-icon {
  color: $color-text-secondary;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

---

### 1.2 AgentDetailsModal Component
**File**: `F:\GiljoAI_MCP\frontend\src\components\projects\AgentDetailsModal.vue`

#### Component Props (Lines 164-173)

```javascript
const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  agent: {
    type: Object,
    default: null,
  },
})
```

#### Component Emits (Line 175)

```javascript
const emit = defineEmits(['update:modelValue'])
```

#### Orchestrator Detection (Lines 194-196)

```javascript
const isOrchestrator = computed(() => {
  return props.agent?.agent_type === 'orchestrator'
})
```

#### Template Data Fetching (Lines 223-242)

```javascript
const fetchTemplateData = async () => {
  if (!props.agent?.template_id) {
    error.value = null
    return
  }

  loading.value = true
  error.value = null
  templateData.value = null

  try {
    // Endpoint: GET /api/v1/templates/{template_id}/
    const response = await apiClient.templates.get(props.agent.template_id)
    templateData.value = response.data
  } catch (err) {
    console.error('[AgentDetailsModal] Failed to fetch template:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to fetch template data'
  } finally {
    loading.value = false
  }
}
```

#### Orchestrator Prompt Fetching (Lines 244-259)

```javascript
const fetchOrchestratorPrompt = async () => {
  loading.value = true
  error.value = null
  orchestratorPrompt.value = null

  try {
    // Endpoint: GET /api/v1/system/orchestrator-prompt
    const response = await apiClient.system.getOrchestratorPrompt()
    orchestratorPrompt.value = response.data.content
  } catch (err) {
    console.error('[AgentDetailsModal] Failed to fetch orchestrator prompt:', err)
    error.value =
      err.response?.data?.detail || err.message || 'Failed to fetch orchestrator prompt'
  } finally {
    loading.value = false
  }
}
```

#### Content Display

**Regular Agent Content** (Lines 43-106):
- Agent type chip and ID (lines 20-27)
- Description section (lines 44-48)
- Metadata (Model, Variables, Tools) (lines 51-87)
- Template content in monospace font with copy button (lines 89-105)

**Orchestrator Content** (Lines 109-126):
- Title: "Orchestrator System Prompt"
- Prompt content in monospace font with copy button

**Error & Loading States** (Lines 29-40):
- Loading spinner with "Loading..." text
- Error alert with error message

#### Data Fetching Watcher (Lines 271-289)

```javascript
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue && props.agent) {
      // Reset state
      templateData.value = null
      orchestratorPrompt.value = null
      error.value = null

      // Fetch appropriate data
      if (isOrchestrator.value) {
        fetchOrchestratorPrompt()
      } else if (props.agent.template_id) {
        fetchTemplateData()
      }
    }
  },
  { immediate: true }
)
```

#### Copy to Clipboard (Lines 261-268)

```javascript
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    copySuccess.value = true
  } catch (err) {
    console.error('[AgentDetailsModal] Failed to copy to clipboard:', err)
  }
}
```

---

### 1.3 API Service Integration
**File**: `F:\GiljoAI_MCP\frontend\src\services\api.js`

#### Templates Endpoint (Lines 400-415)

```javascript
templates: {
  list: (params) => apiClient.get('/api/v1/templates/', { params }),
  get: (id) => apiClient.get(`/api/v1/templates/${id}/`),
  create: (data) => apiClient.post('/api/v1/templates/', data),
  update: (id, data) => apiClient.put(`/api/v1/templates/${id}/`, data),
  delete: (id, archive = false) =>
    apiClient.delete(`/api/v1/templates/${id}/`, { params: { archive } }),
  history: (id, limit = 10) =>
    apiClient.get(`/api/v1/templates/${id}/history/`, { params: { limit } }),
  // ... other methods
},
```

**Template Retrieval in Modal**:
```javascript
const response = await apiClient.templates.get(props.agent.template_id)
// Endpoint: GET /api/v1/templates/{template_id}/
```

#### System Orchestrator Prompt Endpoint (Lines 558-563)

```javascript
system: {
  getOrchestratorPrompt: () => apiClient.get('/api/v1/system/orchestrator-prompt'),
  updateOrchestratorPrompt: (content) =>
    apiClient.put('/api/v1/system/orchestrator-prompt', { content }),
  resetOrchestratorPrompt: () => apiClient.post('/api/v1/system/orchestrator-prompt/reset'),
},
```

**Orchestrator Prompt Retrieval in Modal**:
```javascript
const response = await apiClient.system.getOrchestratorPrompt()
// Endpoint: GET /api/v1/system/orchestrator-prompt
```

---

### 1.4 Backend System Prompt Endpoint
**File**: `F:\GiljoAI_MCP\api\endpoints\system_prompts.py`

#### Endpoints
- **GET** `/api/v1/system/orchestrator-prompt` (Line 28)
- **PUT** `/api/v1/system/orchestrator-prompt` (Line 47)
- **POST** `/api/v1/system/orchestrator-prompt/reset` (Line 76)

#### Response Model
- Returns: `OrchestratorPromptResponse`
- Content field: `content` (string with orchestrator prompt)

---

### 1.5 StatusBoard ActionIcons Component
**File**: `F:\GiljoAI_MCP\frontend\src\components\StatusBoard\ActionIcons.vue`

#### Current Action Buttons (Lines 4-107)
1. **Launch** (mdi-rocket-launch)
2. **Copy Prompt** (mdi-content-copy)
3. **View Messages** (mdi-message-text) with unread badge
4. **Cancel** (mdi-cancel)
5. **Hand Over** (mdi-hand-left)

**Status**: ActionIcons does NOT include an info button. This is only in LaunchTab.

---

## 2. ORCHESTRATOR TEMPLATE STATUS

### Critical Finding: No Orchestrator Template in Template Manager

The orchestrator does **not have a template** in the database-backed template system. Instead:

1. **Design Pattern**: Orchestrator uses a **separate system-wide configuration endpoint**
2. **Rationale**: Orchestrator is a system component, not a user-instantiated agent
3. **Implementation**: Dedicated `/api/v1/system/orchestrator-prompt` endpoint
4. **Distinction**:
   - **Agent Templates**: CRUD via `/api/v1/templates/` (database templates)
   - **Orchestrator Prompt**: System config via `/api/v1/system/orchestrator-prompt`

### Evidence

**AgentDetailsModal Special Case** (Lines 194-196, 281-282):
```javascript
const isOrchestrator = computed(() => {
  return props.agent?.agent_type === 'orchestrator'
})

// Different fetch path for orchestrator
if (isOrchestrator.value) {
  fetchOrchestratorPrompt()  // Uses system endpoint
} else if (props.agent.template_id) {
  fetchTemplateData()  // Uses template endpoint
}
```

**No Template ID for Orchestrator**:
- Regular agents have `template_id` field
- Orchestrator in LaunchTab has no template_id
- Modal handles orchestrator specially without expecting template_id

---

## 3. ICON ANALYSIS & PROPOSED CHANGES

### Current Icon Configuration

**Both Orchestrator & Agent Cards**:
```
[Avatar] [Name] [Lock Icon] [Info Icon]
```

| Component | Icon 1 | Icon 2 | Current File | Line |
|-----------|--------|--------|--------------|------|
| Orchestrator | `mdi-lock` | `mdi-information` | LaunchTab.vue | 44, 53 |
| Agent Team | `mdi-lock` | `mdi-information` | LaunchTab.vue | 71, 80 |

### Proposed Icon Changes

Based on QUICK_LAUNCH.txt principles (no zombie code, reuse existing patterns):

#### Change 1: Lock Icon → Eye Icon
**Location**: LaunchTab.vue lines 44 and 71

**Current**:
```vue
<v-icon size="small" class="lock-icon">mdi-lock</v-icon>
```

**Proposed**:
```vue
<v-icon size="small" class="eye-icon">mdi-eye</v-icon>
```

**Rationale**: Eye icon better represents "view/read" action for viewing agent templates/prompts

#### Change 2: Add Edit Pencil Icon (Optional)
**Location**: LaunchTab.vue, after agent team card icon section

**Current**:
```vue
<v-icon size="small" class="lock-icon">mdi-lock</v-icon>
<v-icon size="small" class="info-icon" role="button" tabindex="0">mdi-information</v-icon>
```

**Proposed** (if edit functionality needed):
```vue
<v-icon size="small" class="eye-icon">mdi-eye</v-icon>
<v-icon size="small" class="edit-icon" role="button" tabindex="0">mdi-pencil</v-icon>
```

---

## 4. REUSABLE COMPONENTS & PATTERNS

### AgentDetailsModal.vue
**Status**: Fully functional, production-ready

**Capabilities**:
- Display agent template details
- Display orchestrator system prompt
- Copy content to clipboard
- Loading states and error handling
- Responsive modal with proper accessibility

**Reusability**:
- Can be imported into other components
- Handles both agent and orchestrator cases automatically
- No hardcoded project/context dependencies

**Known Usage**:
- LaunchTab.vue (lines 91-94)

**Potential Additional Usage**:
- ActionIcons component (JobsTab)
- Agent detail views
- Agent management pages

### Handler Pattern
**Files**: LaunchTab.vue (lines 331-349)

**Pattern**:
```javascript
function handleOrchestratorInfo() {
  selectedAgent.value = { agent_type: 'orchestrator', ... }
  showDetailsModal.value = true
}

function handleAgentInfo(agent) {
  selectedAgent.value = { ...agent, ... }
  showDetailsModal.value = true
}
```

**Reusability**: Can be extracted to composable for use in multiple components

### Icon Styling Pattern
**Files**: LaunchTab.vue (lines 582-595, 664-680)

**Pattern**:
```scss
.info-icon {
  color: $color-text-secondary;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Consistency**: Matches design system for interactive icons

---

## 5. DETAILED FILE LOCATIONS & LINE NUMBERS

### Frontend Components

| Component | File | Key Sections |
|-----------|------|--------------|
| LaunchTab | `frontend/src/components/projects/LaunchTab.vue` | Props: 123-139 |
| | | Orchestrator Card: 39-55 |
| | | Agent Team Cards: 62-82 |
| | | Info Button Icons: 44, 53, 71, 80 |
| | | Handlers: 331-349 |
| | | Modal Integration: 91-94 |
| | | Styling: 582-595, 664-680 |
| AgentDetailsModal | `frontend/src/components/projects/AgentDetailsModal.vue` | Props: 164-173 |
| | | Emits: 175 |
| | | isOrchestrator: 194-196 |
| | | fetchTemplateData: 223-242 |
| | | fetchOrchestratorPrompt: 244-259 |
| | | Template Content Display: 43-106 |
| | | Orchestrator Content Display: 109-126 |
| | | Error/Loading States: 29-40 |
| | | Data Watcher: 271-289 |
| | | Copy Function: 261-268 |
| ActionIcons | `frontend/src/components/StatusBoard/ActionIcons.vue` | Action Buttons: 4-107 |
| | | Note: Does NOT include info button |

### API Services

| Service | File | Endpoint | Line |
|---------|------|----------|------|
| Templates | `frontend/src/services/api.js` | `get(id)` → GET `/api/v1/templates/{id}/` | 401 |
| System | `frontend/src/services/api.js` | `getOrchestratorPrompt()` → GET `/api/v1/system/orchestrator-prompt` | 559 |

### Backend Endpoints

| Endpoint | File | Method | Line |
|----------|------|--------|------|
| `/api/v1/system/orchestrator-prompt` | `api/endpoints/system_prompts.py` | GET | 28 |
| `/api/v1/system/orchestrator-prompt` | `api/endpoints/system_prompts.py` | PUT | 47 |
| `/api/v1/system/orchestrator-prompt/reset` | `api/endpoints/system_prompts.py` | POST | 76 |

---

## 6. WHAT NEEDS TO CHANGE

### Summary of Required Changes

| Change | File | Line(s) | Current | Proposed |
|--------|------|---------|---------|----------|
| 1. Lock → Eye Icon (Orchestrator) | LaunchTab.vue | 44 | `mdi-lock` | `mdi-eye` |
| 2. Lock → Eye Icon (Agents) | LaunchTab.vue | 71 | `mdi-lock` | `mdi-eye` |
| 3. Add Edit Icon (Optional) | LaunchTab.vue | ~82 | (none) | `mdi-pencil` |
| 4. Update Icon Styling | LaunchTab.vue | 582-595, 664-680 | `.lock-icon` | `.eye-icon` |
| 5. Add Edit Handler (Optional) | LaunchTab.vue | ~350 | (none) | `handleAgentEdit()` |
| 6. Add Edit Action Binding (Optional) | LaunchTab.vue | ~81 | (none) | `@click="handleAgentEdit"` |

### Minimal Change Set (Lock → Eye Only)
**Estimated effort**: 10 minutes
- 2 icon replacements (lines 44, 71)
- 2 CSS class renames (lines 582-595, 664-680)

### Extended Change Set (With Edit Pencil)
**Estimated effort**: 30 minutes
- All minimal changes
- Add pencil icon markup
- Add CSS styling for pencil icon
- Add handler function
- Add event binding

---

## 7. QUICK REFERENCE: EXACT CHANGES

### Change 1: Orchestrator Lock Icon (Line 44)

**Before**:
```vue
<v-icon size="small" class="lock-icon">mdi-lock</v-icon>
```

**After**:
```vue
<v-icon size="small" class="eye-icon">mdi-eye</v-icon>
```

### Change 2: Agent Team Lock Icon (Line 71)

**Before**:
```vue
<v-icon size="small" class="lock-icon">mdi-lock</v-icon>
```

**After**:
```vue
<v-icon size="small" class="eye-icon">mdi-eye</v-icon>
```

### Change 3: Update CSS Classes (Lines 582-595)

**Before**:
```scss
.lock-icon {
  color: $color-text-tertiary;
  flex-shrink: 0;
}
```

**After**:
```scss
.eye-icon {
  color: $color-text-tertiary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

### Change 4: Update CSS Classes (Lines 664-680)

**Before**:
```scss
.lock-icon {
  color: $color-text-secondary;

  &:hover {
    color: $color-text-primary;
  }
}
```

**After**:
```scss
.eye-icon {
  color: $color-text-secondary;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

---

## 8. TESTING COVERAGE

### Existing Tests

**AgentDetailsModal Tests**: `frontend/tests/unit/components/projects/AgentDetailsModal.spec.js`
- Template data fetching
- Orchestrator prompt fetching
- Error handling
- Copy to clipboard functionality
- Modal open/close state

**LaunchTab Tests**: `frontend/tests/unit/components/projects/LaunchTab.spec.js`
- Info button click handlers
- Modal integration
- Agent list rendering

### Tests That Need Updates (After Icon Changes)

1. Check for snapshot tests that include icon names
2. Update accessibility tests to reference new icon classes
3. Verify hover states work with new icons

---

## 9. ACCESSIBILITY NOTES

### Current Accessibility

**Info Button Implementation**:
- ✅ `role="button"` for semantic meaning
- ✅ `tabindex="0"` for keyboard focus
- ✅ `@keydown.enter` for Enter key activation
- ✅ Color hover states for visual feedback

**Modal**:
- ✅ Proper focus management
- ✅ ARIA labels for close button
- ✅ Escape key closes dialog (Vuetify v-dialog)

### After Icon Changes

- ✅ Eye icon is universally understood
- ✅ No accessibility regression expected
- ⚠️ Update any screen reader announcements if present

---

## 10. KEY OBSERVATIONS

1. **No Orchestrator Template**: By design, orchestrator uses system endpoint, not template system
2. **Modal is Already Global**: AgentDetailsModal can be reused in other components without modification
3. **Type Detection Works**: `isOrchestrator` computed properly handles agent type detection
4. **API Integration Complete**: Both template and system endpoints properly wired
5. **Accessibility Ready**: Info icons properly implement keyboard access patterns
6. **Responsive Design**: Modal handles all screen sizes correctly
7. **Error Handling**: Proper error states and user feedback implemented
8. **Pattern Consistency**: Icon styling follows design system tokens

---

## 11. RECOMMENDATIONS

### For Implementation

1. **Start Minimal**: Change lock → eye icons first (lowest risk)
2. **Verify Visually**: Test on multiple screen sizes and browsers
3. **Test Accessibility**: Ensure Tab and Enter keys still work correctly
4. **Consider Edit Feature**: Evaluate if edit functionality is needed before adding pencil icon
5. **No Breaking Changes**: All changes are backward compatible

### For Future Enhancements

1. **Info in ActionIcons**: Consider adding info button to StatusBoard table's ActionIcons component
2. **Edit Functionality**: If agent mission editing is needed, add pencil icon handler
3. **Reusable Modal**: Extract handlers to composable for use in multiple components
4. **Template Management**: Consider UI for orchestrator prompt in admin settings

---

## 12. CONCLUSION

The current implementation is **well-structured and production-ready**. The info button system properly displays agent templates and orchestrator prompts with appropriate error handling. Icon changes (lock → eye) are straightforward and follow existing patterns.

**No architectural changes needed—only cosmetic icon updates** if desired.

