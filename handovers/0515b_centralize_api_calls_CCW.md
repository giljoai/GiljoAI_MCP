# Handover 0515b: Centralize API Calls [CCW]

**Execution Environment**: CCW (Claude Code Web)
**Duration**: 1-2 days
**Branch Name**: `ccw-0515b-centralize-api`
**Can Run Parallel With**: 0515a

---

## Why CCW?
- Pure frontend JavaScript/TypeScript work
- No database operations
- No backend changes needed
- Large token usage for refactoring 30+ components

---

## Scope

Remove all direct axios calls from Vue components and centralize them in a service layer.

### Current State
- 30+ components making direct axios calls
- Inconsistent error handling
- No request/response interceptors
- API URLs hardcoded in components

### Target State
- Zero axios imports in components
- All API calls through service layer
- Centralized error handling
- Type-safe API methods

---

## Files to Create

### 1. Enhanced API Client (`frontend/src/api.js`)
```javascript
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:7272',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for auth
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      const authStore = useAuthStore()
      authStore.logout()
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

### 2. Product Service (`frontend/src/services/productService.js`)
```javascript
import api from '@/api'

export const productService = {
  // List all products
  async list(filters = {}) {
    return api.get('/api/products', { params: filters })
  },

  // Create product
  async create(productData) {
    return api.post('/api/products', productData)
  },

  // Update product
  async update(productId, updates) {
    return api.put(`/api/products/${productId}`, updates)
  },

  // Delete product
  async delete(productId) {
    return api.delete(`/api/products/${productId}`)
  },

  // Activate product
  async activate(productId) {
    return api.post(`/api/products/${productId}/activate`)
  },

  // Deactivate product
  async deactivate(productId) {
    return api.post(`/api/products/${productId}/deactivate`)
  },

  // Upload vision document
  async uploadVision(productId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/api/products/${productId}/vision`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // Get vision documents
  async getVisionDocs(productId) {
    return api.get(`/api/products/${productId}/vision`)
  },

  // Delete vision document
  async deleteVision(productId, docId) {
    return api.delete(`/api/products/${productId}/vision/${docId}`)
  }
}
```

### 3. Project Service (`frontend/src/services/projectService.js`)
```javascript
import api from '@/api'

export const projectService = {
  async list(filters = {}) {
    return api.get('/api/projects', { params: filters })
  },

  async get(projectId) {
    return api.get(`/api/projects/${projectId}`)
  },

  async create(projectData) {
    return api.post('/api/projects', projectData)
  },

  async update(projectId, updates) {
    return api.put(`/api/projects/${projectId}`, updates)
  },

  async delete(projectId) {
    return api.delete(`/api/projects/${projectId}`)
  },

  async activate(projectId) {
    return api.post(`/api/projects/${projectId}/activate`)
  },

  async deactivate(projectId) {
    return api.post(`/api/projects/${projectId}/deactivate`)
  },

  async complete(projectId, summary) {
    return api.post(`/api/projects/${projectId}/complete`, { summary })
  },

  async cancel(projectId, reason) {
    return api.post(`/api/projects/${projectId}/cancel`, { reason })
  },

  async getStatus(projectId) {
    return api.get(`/api/projects/${projectId}/status`)
  },

  async getSummary(projectId) {
    return api.get(`/api/projects/${projectId}/summary`)
  },

  async getOrchestrator(projectId) {
    return api.get(`/api/projects/${projectId}/orchestrator`)
  }
}
```

### 4. Agent Service (`frontend/src/services/agentService.js`)
```javascript
import api from '@/api'

export const agentService = {
  async list(filters = {}) {
    return api.get('/api/agent-jobs', { params: filters })
  },

  async get(jobId) {
    return api.get(`/api/agent-jobs/${jobId}`)
  },

  async spawn(jobData) {
    return api.post('/api/agent-jobs/spawn', jobData)
  },

  async acknowledge(jobId) {
    return api.post(`/api/agent-jobs/${jobId}/acknowledge`)
  },

  async complete(jobId, result) {
    return api.post(`/api/agent-jobs/${jobId}/complete`, { result })
  },

  async fail(jobId, error) {
    return api.post(`/api/agent-jobs/${jobId}/error`, { error })
  },

  async cancel(jobId) {
    return api.post(`/api/agent-jobs/${jobId}/cancel`)
  },

  async getHealth() {
    return api.get('/api/agent-jobs/health')
  },

  async triggerSuccession(jobId, reason) {
    return api.post(`/api/agent-jobs/${jobId}/succession`, { reason })
  }
}
```

### 5. Settings Service (`frontend/src/services/settingsService.js`)
```javascript
import api from '@/api'

export const settingsService = {
  async getSettings() {
    return api.get('/api/settings')
  },

  async updateSettings(settings) {
    return api.put('/api/settings', settings)
  },

  async getFieldPriorities() {
    return api.get('/api/settings/field-priorities')
  },

  async updateFieldPriorities(priorities) {
    return api.put('/api/settings/field-priorities', priorities)
  },

  async resetFieldPriorities() {
    return api.post('/api/settings/field-priorities/reset')
  }
}
```

---

## Components to Update

### Example: ProductList.vue (BEFORE)
```vue
<script setup>
import axios from 'axios'
import { ref, onMounted } from 'vue'

const products = ref([])

onMounted(async () => {
  try {
    const response = await axios.get('http://localhost:7272/api/products')
    products.value = response.data
  } catch (error) {
    console.error('Failed to load products:', error)
  }
})
</script>
```

### Example: ProductList.vue (AFTER)
```vue
<script setup>
import { productService } from '@/services/productService'
import { ref, onMounted } from 'vue'

const products = ref([])
const loading = ref(false)
const error = ref(null)

onMounted(async () => {
  loading.value = true
  try {
    products.value = await productService.list()
  } catch (err) {
    error.value = err.message
    // Error handling done by interceptor
  } finally {
    loading.value = false
  }
})
</script>
```

---

## Migration Checklist

### Components to Update (Find & Replace axios)
```bash
# Find all axios imports
grep -r "import axios" frontend/src/components/
grep -r "from 'axios'" frontend/src/components/
grep -r 'from "axios"' frontend/src/components/

# Find all axios usage
grep -r "axios\." frontend/src/components/
```

**Known Components Using axios**:
1. `frontend/src/components/products/ProductList.vue`
2. `frontend/src/components/products/ProductForm.vue`
3. `frontend/src/components/products/VisionUpload.vue`
4. `frontend/src/components/projects/ProjectList.vue`
5. `frontend/src/components/projects/ProjectForm.vue`
6. `frontend/src/components/projects/LaunchTab.vue`
7. `frontend/src/components/agents/AgentList.vue`
8. `frontend/src/components/agents/AgentMonitor.vue`
9. `frontend/src/components/settings/GeneralSettings.vue`
10. `frontend/src/components/settings/UserSettings.vue`
11. `frontend/src/views/Dashboard.vue`
12. `frontend/src/views/Products.vue`
13. `frontend/src/views/Projects.vue`
14. `frontend/src/views/Settings.vue`
15. 15+ more components...

---

## Success Criteria

- [ ] Zero axios imports in component files
- [ ] All API calls use service layer
- [ ] Consistent error handling across app
- [ ] Auth token automatically attached
- [ ] 401 errors trigger logout
- [ ] Loading states managed consistently
- [ ] Build succeeds
- [ ] All API calls still work

---

## Testing Strategy

### After Each Component Update
1. Test the specific feature works
2. Check network tab for proper API calls
3. Test error scenarios (disconnect network)
4. Verify auth headers are sent

### Final Testing
```bash
# Build should succeed
npm run build

# No axios imports in components
grep -r "import axios" frontend/src/components/ # Should return nothing

# All services exported
ls frontend/src/services/ # Should list all service files
```

---

## Common Issues & Solutions

**Issue**: API call fails after migration
**Solution**: Check service method signature matches component usage

**Issue**: Auth token not attached
**Solution**: Ensure interceptor is set up before first API call

**Issue**: Error handling broken
**Solution**: Update component to handle Promise rejections

**Issue**: File upload not working
**Solution**: Ensure FormData and headers set correctly

---

**End of 0515b Scope**