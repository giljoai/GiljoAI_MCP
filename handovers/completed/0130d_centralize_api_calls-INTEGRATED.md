# Handover 0130d: Centralize API Calls and Error Handling

---
**⚠️ CRITICAL UPDATE (2025-11-12): MERGED INTO HANDOVER 0515**

This handover has been **merged** into the 0500 series remediation project:

**New Scope**: Handover 0515 - Frontend Consolidation
**Parent Project**: Projectplan_500.md
**Status**: Deferred until after critical remediation (Handovers 0500-0514 complete)

**Reason for Merger**: The refactoring (Handovers 0120-0130) left 23 critical implementation gaps. API centralization (0130d) and component consolidation (0130c) are now combined into a single cohesive frontend consolidation effort (Handover 0515). See:
- **Investigation Reports**: Products, Projects, Settings, Orchestration breakage
- **Master Plan**: `handovers/Projectplan_500.md`
- **New Handover**: `handovers/0515_frontend_consolidation.md`

**MERGED INTO**: Handover 0515 combines both 0130c (merge duplicate components) and 0130d (centralize API calls) into a single cohesive frontend consolidation effort.

**Original scope below** (preserved for historical reference):

---

**Date**: 2025-11-12
**Priority**: P2 (Medium - Code Quality & Maintainability)
**Duration**: 2-3 days
**Status**: Merged into Handover 0515
**Type**: API Architecture Refactoring
**Dependencies**: None (can run independently)
**Parent**: Handover 0130 (Frontend WebSocket Modernization)

---

## Executive Summary

### Why Centralize API Calls?

**PROBLEM**: Raw axios calls scattered across 30+ components lead to:
- **Inconsistent error handling**: Some components show toasts, others log to console, some do nothing
- **Duplicate code**: Same API patterns repeated in multiple files
- **AI tool confusion**: When an AI tool needs to call an API, it might:
  - Copy-paste axios call from wrong component
  - Use outdated error handling pattern
  - Miss authentication headers
  - Forget to handle loading states

**FOR AGENTIC AI TOOLS**: Clear, centralized API patterns guide AI tools to:
- Import from single `/services/api.js` location
- Use consistent error handling automatically
- Follow established authentication patterns
- Implement proper loading states

**SOLUTION**: Centralize all API calls in `/services/api.js` with consistent patterns.

### What We're Centralizing

1. **Project API Calls** (~10 components with raw axios)
   - Create, update, delete, list projects
   - Activate/deactivate projects
   - Soft delete and recovery

2. **Agent Job API Calls** (~8 components with raw axios)
   - Spawn jobs, trigger succession
   - Update job status, results
   - Query job history

3. **Template API Calls** (~3 components with raw axios)
   - Fetch, update, diff templates
   - Reset to defaults

4. **Consistent Error Handling**
   - Standardize toast notifications
   - Retry logic for network errors
   - Auth token refresh handling

---

## Objectives

### Primary Objectives

1. **Centralize API Methods**
   - Move all axios calls to `/services/api.js`
   - Create clean method signatures: `api.projects.create(data)`
   - Update all component usages (30+ files)

2. **Standardize Error Handling**
   - Consistent toast notifications for errors
   - Automatic retry for network failures (configurable)
   - Auth token refresh on 401 responses
   - Proper error propagation to components

3. **Improve Developer Experience**
   - Single source of truth for API endpoints
   - TypeScript-style JSDoc for autocomplete
   - Clear method naming conventions
   - Reduce component complexity

### Secondary Objectives

1. **Add Request/Response Interceptors**
   - Automatic loading state management
   - Request ID for debugging
   - Response caching (GET requests)
   - Rate limiting visibility

2. **Create API Mock Layer**
   - Enable frontend development without backend
   - Improve test reliability
   - Faster component iteration

3. **Document API Patterns**
   - Add examples to COMPONENT_GUIDE.md
   - Create API usage decision tree
   - Guide AI tools to correct patterns

---

## Current State Analysis

### Scattered API Calls Audit

**Raw Axios Usage Examples**:

**Example 1: ProjectsView.vue (Inconsistent)**:
```javascript
// No loading state
// No error handling
// Direct axios import
import axios from 'axios'

async function createProject() {
  const response = await axios.post('/api/projects', projectData)
  projects.value.push(response.data)
}
```

**Example 2: ProductsView.vue (Better, but duplicated)**:
```javascript
// Has loading state
// Custom error toast
// Still raw axios
import axios from 'axios'
import { useToast } from '@/composables/useToast'

const loading = ref(false)
const { showToast } = useToast()

async function activateProduct(id) {
  loading.value = true
  try {
    await axios.post(`/api/products/${id}/activate`)
    showToast({ message: 'Product activated', color: 'success' })
  } catch (error) {
    showToast({ message: error.response?.data?.detail || 'Failed', color: 'error' })
  } finally {
    loading.value = false
  }
}
```

**Example 3: TemplateManager.vue (Most complete, but pattern should be shared)**:
```javascript
// Full error handling
// Loading states
// But still component-specific
import axios from 'axios'
import { useToast } from '@/composables/useToast'

const loading = ref(false)
const { showToast } = useToast()

async function updateTemplate(name, content) {
  loading.value = true
  try {
    const response = await axios.put(`/api/templates/${name}`, { content })
    showToast({ message: 'Template updated', color: 'success' })
    return response.data
  } catch (error) {
    const message = error.response?.data?.detail || 'Update failed'
    showToast({ message, color: 'error' })
    throw error
  } finally {
    loading.value = false
  }
}
```

**Problem**: Each component reimplements error handling, loading states, and toast notifications.

### Target Architecture

**Centralized API Service** (`services/api.js`):
```javascript
// Single source of truth for all API calls
import axios from 'axios'
import { useToast } from '@/composables/useToast'

const api = {
  projects: {
    async list() {
      return await apiCall('GET', '/api/projects')
    },
    async create(data) {
      return await apiCall('POST', '/api/projects', data)
    },
    async activate(id) {
      return await apiCall('POST', `/api/projects/${id}/activate`)
    },
    // ... all project methods
  },
  products: {
    async list() {
      return await apiCall('GET', '/api/products')
    },
    // ... all product methods
  },
  templates: {
    async list() {
      return await apiCall('GET', '/api/templates')
    },
    // ... all template methods
  },
}

// Centralized error handling, loading, toast notifications
async function apiCall(method, url, data = null, options = {}) {
  const {
    showSuccessToast = false,
    successMessage = 'Success',
    showErrorToast = true,
    errorMessage = null,
    retry = 0,
    cache = false,
  } = options

  try {
    const response = await axios({ method, url, data })

    if (showSuccessToast) {
      const { showToast } = useToast()
      showToast({ message: successMessage, color: 'success' })
    }

    return response.data
  } catch (error) {
    if (showErrorToast) {
      const { showToast } = useToast()
      const message = errorMessage || error.response?.data?.detail || 'Request failed'
      showToast({ message, color: 'error' })
    }

    // Retry logic for network errors
    if (retry > 0 && !error.response) {
      await new Promise(resolve => setTimeout(resolve, 1000))
      return apiCall(method, url, data, { ...options, retry: retry - 1 })
    }

    throw error
  }
}

export default api
```

**Component Usage** (simplified):
```javascript
import api from '@/services/api'

async function createProject() {
  try {
    const project = await api.projects.create(projectData)
    projects.value.push(project)
  } catch (error) {
    // Error already handled by api.js (toast shown)
    // Component just needs to handle UI state
  }
}
```

**Benefits**:
- 20-30 lines per component → 5-10 lines
- Consistent error handling everywhere
- Loading states handled by API layer
- Easy to add features (caching, retry, rate limiting)

---

## Implementation Plan

### Phase 1: Audit Current API Calls (2-3 hours)

**Steps**:
1. Find all raw axios imports
2. Categorize by API endpoint
3. Identify error handling patterns
4. Document findings

**Commands**:
```bash
# Find all axios imports (excluding services/api.js)
grep -r "import.*axios" frontend/src --include="*.vue" --include="*.js" | grep -v "services/api"

# Find all API endpoint calls
grep -r "/api/" frontend/src --include="*.vue" --include="*.js" -A 3 -B 3

# Count raw axios usages
grep -r "axios\.(get|post|put|delete|patch)" frontend/src --include="*.vue" | wc -l
```

**Document in**: `handovers/0130d_API_AUDIT.md`

**Categories**:
```markdown
## Projects API (10 files)
- ProjectsView.vue: list, create, update, delete
- ProductsView.vue: activate, deactivate
- LaunchTab.vue: spawn orchestrator

## Agent Jobs API (8 files)
- JobsTab.vue: list, trigger succession
- AgentCardEnhanced.vue: update status
- OrchestratorLaunchButton.vue: spawn job

## Templates API (3 files)
- TemplateManager.vue: list, update, reset
- UserSettings.vue: fetch user templates

## Auth API (2 files)
- Login.vue: login, logout
- ForgotPasswordPin.vue: reset password

## Settings API (5 files)
- SystemSettings.vue: network, database configs
- UserSettings.vue: user preferences
```

**Success Criteria**:
- ✅ All raw axios usages documented
- ✅ API endpoints categorized
- ✅ Error handling patterns identified
- ✅ Migration priority determined

### Phase 2: Extend `/services/api.js` (4-6 hours)

**Steps**:
1. Read current `services/api.js` structure
2. Add missing API methods
3. Standardize method signatures
4. Add JSDoc documentation
5. Test each method

**Current Structure** (check what exists):
```bash
cat frontend/src/services/api.js | head -50
```

**Extended Structure**:
```javascript
/**
 * Centralized API Service
 *
 * All API calls should go through this service for:
 * - Consistent error handling
 * - Automatic toast notifications
 * - Auth token management
 * - Request retry logic
 *
 * Usage:
 *   import api from '@/services/api'
 *   const projects = await api.projects.list()
 *   const newProject = await api.projects.create(data)
 */

import axios from 'axios'
import { useToast } from '@/composables/useToast'
import { API_CONFIG } from '@/config/api'

// Create axios instance with base config
const axiosInstance = axios.create({
  baseURL: API_CONFIG.baseURL || window.API_BASE_URL || 'http://localhost:7272',
  timeout: 30000,
  withCredentials: true, // Important for cookie-based auth
})

// Request interceptor (add request ID, loading state)
axiosInstance.interceptors.request.use(
  (config) => {
    // Add request ID for debugging
    config.headers['X-Request-ID'] = generateRequestId()

    // Add tenant key if available
    const tenantKey = localStorage.getItem('tenant_key')
    if (tenantKey) {
      config.headers['X-Tenant-Key'] = tenantKey
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor (handle 401, errors)
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle 401 (redirect to login)
    if (error.response?.status === 401) {
      // Clear auth state
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }

    return Promise.reject(error)
  }
)

/**
 * Generic API call with error handling
 */
async function apiCall(method, url, data = null, options = {}) {
  const {
    showSuccessToast = false,
    successMessage = 'Success',
    showErrorToast = true,
    errorMessage = null,
    retry = 0,
  } = options

  try {
    const response = await axiosInstance({
      method,
      url,
      data,
    })

    // Success toast if requested
    if (showSuccessToast) {
      const { showToast } = useToast()
      showToast({ message: successMessage, color: 'success' })
    }

    return response.data
  } catch (error) {
    // Error toast if requested
    if (showErrorToast) {
      const { showToast } = useToast()
      const message = errorMessage || error.response?.data?.detail || 'Request failed'
      showToast({ message, color: 'error', timeout: 5000 })
    }

    // Retry logic for network errors (not server errors)
    if (retry > 0 && !error.response) {
      console.log(`[API] Retrying request (${retry} attempts remaining)`)
      await new Promise(resolve => setTimeout(resolve, 1000))
      return apiCall(method, url, data, { ...options, retry: retry - 1 })
    }

    throw error
  }
}

/**
 * Projects API
 */
const projects = {
  /**
   * List all projects
   * @returns {Promise<Array>} Array of project objects
   */
  async list() {
    return await apiCall('GET', '/api/projects')
  },

  /**
   * Get single project
   * @param {string} id - Project ID
   * @returns {Promise<Object>} Project object
   */
  async get(id) {
    return await apiCall('GET', `/api/projects/${id}`)
  },

  /**
   * Create new project
   * @param {Object} data - Project data
   * @returns {Promise<Object>} Created project
   */
  async create(data) {
    return await apiCall('POST', '/api/projects', data, {
      showSuccessToast: true,
      successMessage: 'Project created successfully',
    })
  },

  /**
   * Update project
   * @param {string} id - Project ID
   * @param {Object} data - Updated project data
   * @returns {Promise<Object>} Updated project
   */
  async update(id, data) {
    return await apiCall('PUT', `/api/projects/${id}`, data, {
      showSuccessToast: true,
      successMessage: 'Project updated successfully',
    })
  },

  /**
   * Delete project (soft delete)
   * @param {string} id - Project ID
   * @returns {Promise<void>}
   */
  async delete(id) {
    return await apiCall('DELETE', `/api/projects/${id}`, null, {
      showSuccessToast: true,
      successMessage: 'Project deleted',
    })
  },

  /**
   * Activate project
   * @param {string} id - Project ID
   * @returns {Promise<Object>} Activated project
   */
  async activate(id) {
    return await apiCall('POST', `/api/projects/${id}/activate`, null, {
      showSuccessToast: true,
      successMessage: 'Project activated',
    })
  },

  /**
   * Recover deleted project
   * @param {string} id - Project ID
   * @returns {Promise<Object>} Recovered project
   */
  async recover(id) {
    return await apiCall('POST', `/api/projects/${id}/recover`, null, {
      showSuccessToast: true,
      successMessage: 'Project recovered',
    })
  },
}

/**
 * Products API
 */
const products = {
  async list() {
    return await apiCall('GET', '/api/products')
  },

  async get(id) {
    return await apiCall('GET', `/api/products/${id}`)
  },

  async create(data) {
    return await apiCall('POST', '/api/products', data, {
      showSuccessToast: true,
      successMessage: 'Product created',
    })
  },

  async update(id, data) {
    return await apiCall('PUT', `/api/products/${id}`, data, {
      showSuccessToast: true,
      successMessage: 'Product updated',
    })
  },

  async delete(id) {
    return await apiCall('DELETE', `/api/products/${id}`, null, {
      showSuccessToast: true,
      successMessage: 'Product deleted',
    })
  },

  async activate(id) {
    return await apiCall('POST', `/api/products/${id}/activate`, null, {
      showSuccessToast: true,
      successMessage: 'Product activated',
    })
  },
}

/**
 * Agent Jobs API
 */
const agentJobs = {
  async list(params = {}) {
    const query = new URLSearchParams(params).toString()
    return await apiCall('GET', `/api/agent-jobs${query ? `?${query}` : ''}`)
  },

  async get(id) {
    return await apiCall('GET', `/api/agent-jobs/${id}`)
  },

  async spawn(data) {
    return await apiCall('POST', '/api/agent-jobs/spawn', data, {
      showSuccessToast: true,
      successMessage: 'Agent job spawned',
    })
  },

  async triggerSuccession(id, reason = 'manual') {
    return await apiCall('POST', `/api/agent-jobs/${id}/trigger-succession`, { reason }, {
      showSuccessToast: true,
      successMessage: 'Succession triggered',
    })
  },

  async updateStatus(id, status, result = null) {
    return await apiCall('PATCH', `/api/agent-jobs/${id}`, { status, result })
  },
}

/**
 * Templates API
 */
const templates = {
  async list() {
    return await apiCall('GET', '/api/templates')
  },

  async get(name) {
    return await apiCall('GET', `/api/templates/${name}`)
  },

  async update(name, content) {
    return await apiCall('PUT', `/api/templates/${name}`, { content }, {
      showSuccessToast: true,
      successMessage: 'Template updated',
    })
  },

  async reset(name) {
    return await apiCall('POST', `/api/templates/${name}/reset`, null, {
      showSuccessToast: true,
      successMessage: 'Template reset to default',
    })
  },

  async diff(name) {
    return await apiCall('GET', `/api/templates/${name}/diff`)
  },
}

/**
 * Auth API
 */
const auth = {
  async login(username, password) {
    return await apiCall('POST', '/api/auth/login', { username, password }, {
      showSuccessToast: true,
      successMessage: 'Login successful',
    })
  },

  async logout() {
    return await apiCall('POST', '/api/auth/logout', null, {
      showSuccessToast: true,
      successMessage: 'Logged out',
    })
  },

  async me() {
    return await apiCall('GET', '/api/auth/me')
  },

  async resetPassword(pin, newPassword) {
    return await apiCall('POST', '/api/auth/reset-password', { pin, new_password: newPassword }, {
      showSuccessToast: true,
      successMessage: 'Password reset successfully',
    })
  },
}

/**
 * Utility functions
 */
function generateRequestId() {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// Export unified API object
export default {
  projects,
  products,
  agentJobs,
  templates,
  auth,
  // Direct axios instance access for custom calls
  axios: axiosInstance,
}
```

**Test Each Method**:
```bash
# Start dev server
cd frontend && npm run dev

# In browser console:
import api from '@/services/api'

// Test projects
const projects = await api.projects.list()
const newProject = await api.projects.create({ name: 'Test', mission: 'Test' })

// Test products
const products = await api.products.list()

// Verify toasts appear on success/error
```

**Success Criteria**:
- ✅ All API methods implemented
- ✅ JSDoc documentation complete
- ✅ Error handling consistent
- ✅ Toast notifications working
- ✅ Manual testing confirms all methods work

### Phase 3: Migrate Components (6-8 hours)

**Steps**:
1. Update one component at a time
2. Test each migration
3. Commit incrementally
4. Update documentation

**Migration Pattern**:

**Before** (ProjectsView.vue):
```javascript
import axios from 'axios'
import { useToast } from '@/composables/useToast'

const loading = ref(false)
const { showToast } = useToast()

async function createProject() {
  loading.value = true
  try {
    const response = await axios.post('/api/projects', projectData.value)
    projects.value.push(response.data)
    showToast({ message: 'Project created', color: 'success' })
  } catch (error) {
    showToast({ message: error.response?.data?.detail || 'Failed', color: 'error' })
  } finally {
    loading.value = false
  }
}
```

**After** (ProjectsView.vue):
```javascript
import api from '@/services/api'

const loading = ref(false)

async function createProject() {
  loading.value = true
  try {
    const project = await api.projects.create(projectData.value)
    projects.value.push(project)
    // Toast automatically shown by api.projects.create
  } catch (error) {
    // Error toast automatically shown by api layer
    // Component only needs to handle UI state
  } finally {
    loading.value = false
  }
}
```

**Code Reduction**: 15 lines → 8 lines (47% reduction per component)

**Migration Order** (prioritize by usage frequency):
1. ProjectsView.vue (high usage)
2. ProductsView.vue (high usage)
3. TemplateManager.vue (medium usage)
4. JobsTab.vue (medium usage)
5. LaunchTab.vue (medium usage)
6. ... (remaining 25 files)

**Commit Pattern** (incremental):
```bash
git add frontend/src/views/ProjectsView.vue
git commit -m "refactor(0130d): Migrate ProjectsView to centralized API

Changes:
- Replaced raw axios calls with api.projects methods
- Removed duplicate error handling (now in api.js)
- Reduced component code by 7 lines

Benefits:
- Consistent error handling
- Automatic toast notifications
- Easier to maintain

Handover: 0130d - Centralize API Calls (1/30 components)"
```

**Success Criteria**:
- ✅ All 30 components migrated
- ✅ No raw axios imports remain (except api.js)
- ✅ All tests passing
- ✅ No regressions detected

### Phase 4: Update Documentation (1 hour)

**Update**: `frontend/COMPONENT_GUIDE.md`
```markdown
## API Calls

### Using Centralized API Service ✅

**Location**: `services/api.js`

**Purpose**: Single source of truth for all API calls

**When to use**: Always use this for API calls. Do NOT import axios directly.

**Example**:
```vue
<script setup>
import api from '@/services/api'
import { ref } from 'vue'

const loading = ref(false)
const projects = ref([])

async function loadProjects() {
  loading.value = true
  try {
    projects.value = await api.projects.list()
  } catch (error) {
    // Error already handled (toast shown)
  } finally {
    loading.value = false
  }
}

async function createProject(data) {
  try {
    const project = await api.projects.create(data)
    projects.value.push(project)
    // Success toast automatically shown
  } catch (error) {
    // Error toast automatically shown
  }
}
</script>
```

### Available API Methods

**Projects**:
- `api.projects.list()` - List all projects
- `api.projects.get(id)` - Get single project
- `api.projects.create(data)` - Create project
- `api.projects.update(id, data)` - Update project
- `api.projects.delete(id)` - Soft delete project
- `api.projects.activate(id)` - Activate project
- `api.projects.recover(id)` - Recover deleted project

**Products**:
- `api.products.list()` - List all products
- `api.products.get(id)` - Get single product
- `api.products.create(data)` - Create product
- `api.products.update(id, data)` - Update product
- `api.products.delete(id)` - Delete product
- `api.products.activate(id)` - Activate product

**Agent Jobs**:
- `api.agentJobs.list(params)` - List agent jobs
- `api.agentJobs.get(id)` - Get single job
- `api.agentJobs.spawn(data)` - Spawn new agent job
- `api.agentJobs.triggerSuccession(id, reason)` - Trigger orchestrator succession
- `api.agentJobs.updateStatus(id, status, result)` - Update job status

**Templates**:
- `api.templates.list()` - List all templates
- `api.templates.get(name)` - Get template content
- `api.templates.update(name, content)` - Update template
- `api.templates.reset(name)` - Reset to default
- `api.templates.diff(name)` - Show diff from default

### Error Handling

All API methods automatically:
- ✅ Show error toast notifications
- ✅ Show success toast notifications (for create/update/delete)
- ✅ Retry network errors (up to 3 times)
- ✅ Handle 401 (redirect to login)

Components only need to handle loading states and UI updates.

### For Agentic AI Tools

When writing code that calls APIs:
1. Always import: `import api from '@/services/api'`
2. Use appropriate method: `api.projects.create(data)`
3. Handle loading: `loading.value = true/false`
4. Do NOT import axios directly
5. Do NOT implement custom error handling

## Deprecated Patterns (Do Not Use)

### Direct Axios Import ❌
```javascript
// WRONG - Do not use
import axios from 'axios'
const response = await axios.post('/api/projects', data)
```

### Custom Error Handling ❌
```javascript
// WRONG - Error handling is centralized
try {
  await api.projects.create(data)
} catch (error) {
  showToast({ message: error.message, color: 'error' }) // Don't do this!
}
```

### Correct Pattern ✅
```javascript
// CORRECT - Use centralized API
import api from '@/services/api'

const loading = ref(false)

async function createProject() {
  loading.value = true
  try {
    const project = await api.projects.create(data)
    // Success toast automatically shown
    return project
  } catch (error) {
    // Error toast automatically shown
  } finally {
    loading.value = false
  }
}
```
```

---

## Success Criteria

### Code Quality Metrics

**Before 0130d**:
- Raw axios imports: 30+ files
- Error handling: Inconsistent (5 different patterns)
- API call duplication: High (same patterns repeated)
- Component complexity: 20-30 lines per API call

**After 0130d**:
- Raw axios imports: 1 file (services/api.js) ✅
- Error handling: Centralized and consistent ✅
- API call duplication: Zero (DRY principle) ✅
- Component complexity: 8-10 lines per API call ✅

### Quality Improvements

- [ ] Code reduction: 40-50% in components with API calls
- [ ] Error handling: 100% consistent
- [ ] Toast notifications: Automatic and standardized
- [ ] Developer experience: Clear API method signatures
- [ ] AI tool guidance: Single import location

---

## Rollback Plan

### If Centralization Breaks Features

**Option 1: Revert Migration Commits** (incremental rollback):
```bash
# Revert specific component migration
git log --oneline | grep "Migrate.*API"
git revert <commit-hash>
```

**Option 2: Restore Old Pattern** (emergency):
```bash
# Restore axios import in component
import axios from 'axios'
// Temporarily use old pattern until fix deployed
```

---

## Completion Checklist

- [ ] Phase 1: API call audit complete (30+ files documented)
- [ ] Phase 2: API service extended with all methods
- [ ] Phase 3: All components migrated (30+ files)
- [ ] Phase 4: Documentation updated
- [ ] No raw axios imports remain (except services/api.js)
- [ ] All tests passing
- [ ] No regressions detected
- [ ] COMPONENT_GUIDE.md updated
- [ ] Handover archived: `handovers/completed/0130d_centralize_api_calls-C.md`

---

**Created**: 2025-11-12
**Status**: READY TO EXECUTE (standalone or after 0130c)
**Duration**: 2-3 days
**Success Factor**: Single source of truth for all API patterns


---
# INTEGRATION NOTE
**Date**: 2025-11-15
**Status**: INTEGRATED INTO 0515

This work has been integrated into:
- **Handover 0515**: Frontend Consolidation & WebSocket V2 Completion
- **Specifically**: 0515b - Centralize API Calls

See: /handovers/0515_frontend_consolidation_websocket_v2.md
