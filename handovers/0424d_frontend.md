# Handover 0424d: Organization Frontend UI

**Date:** 2026-01-19
**From Agent:** Planning Session
**To Agent:** ux-designer / frontend-tester
**Priority:** HIGH
**Estimated Complexity:** 6-8 hours
**Status:** Ready for Implementation
**Parent:** 0424_org_hierarchy_overview.md
**Depends On:** 0424c (API Endpoints)

---

## Summary

Create frontend UI for Organization management:
- Organization settings page
- Member list and management
- Invite member dialog
- Org store for state management
- **UI Tweak**: Move "Test Connection" button above divider

---

## Scope

### New Components (4)
- `OrganizationSettings.vue` - Main org management page
- `MemberList.vue` - Display and manage org members
- `InviteMemberDialog.vue` - Dialog for inviting users
- `orgStore.js` - Vuex/Pinia store for org state

### Modified Components (4)
- `router/index.js` - Add org routes
- `MainLayout.vue` - Add org navigation link
- `api.js` - Add org API methods
- `DatabaseConnection.vue` - Move Test Connection button (UI tweak)

---

## Implementation Plan

### Step 1: Create Org Store (frontend/src/stores/orgStore.js)

```javascript
/**
 * Organization Store - Manages organization state.
 * Handover 0424d: State management for org UI.
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useOrgStore = defineStore('org', {
  state: () => ({
    organizations: [],
    currentOrg: null,
    members: [],
    loading: false,
    error: null
  }),

  getters: {
    userRole: (state) => {
      if (!state.currentOrg || !state.members.length) return null
      const userId = localStorage.getItem('userId')
      const membership = state.members.find(m => m.user_id === userId)
      return membership?.role || null
    },

    isOwner: (state) => {
      return state.userRole === 'owner'
    },

    isAdmin: (state) => {
      return ['owner', 'admin'].includes(state.userRole)
    },

    canManageMembers: (state) => {
      return ['owner', 'admin'].includes(state.userRole)
    }
  },

  actions: {
    async fetchOrganizations() {
      this.loading = true
      this.error = null
      try {
        const response = await api.get('/organizations')
        this.organizations = response.data
        return { success: true, data: this.organizations }
      } catch (error) {
        this.error = error.message
        return { success: false, error: error.message }
      } finally {
        this.loading = false
      }
    },

    async fetchOrganization(orgId) {
      this.loading = true
      this.error = null
      try {
        const response = await api.get(`/organizations/${orgId}`)
        this.currentOrg = response.data
        this.members = response.data.members || []
        return { success: true, data: this.currentOrg }
      } catch (error) {
        this.error = error.message
        return { success: false, error: error.message }
      } finally {
        this.loading = false
      }
    },

    async createOrganization(orgData) {
      this.loading = true
      try {
        const response = await api.post('/organizations', orgData)
        this.organizations.push(response.data)
        return { success: true, data: response.data }
      } catch (error) {
        return { success: false, error: error.response?.data?.detail || error.message }
      } finally {
        this.loading = false
      }
    },

    async updateOrganization(orgId, orgData) {
      this.loading = true
      try {
        const response = await api.put(`/organizations/${orgId}`, orgData)
        this.currentOrg = response.data
        // Update in list
        const index = this.organizations.findIndex(o => o.id === orgId)
        if (index >= 0) {
          this.organizations[index] = response.data
        }
        return { success: true, data: response.data }
      } catch (error) {
        return { success: false, error: error.response?.data?.detail || error.message }
      } finally {
        this.loading = false
      }
    },

    async deleteOrganization(orgId) {
      this.loading = true
      try {
        await api.delete(`/organizations/${orgId}`)
        this.organizations = this.organizations.filter(o => o.id !== orgId)
        if (this.currentOrg?.id === orgId) {
          this.currentOrg = null
        }
        return { success: true }
      } catch (error) {
        return { success: false, error: error.response?.data?.detail || error.message }
      } finally {
        this.loading = false
      }
    },

    async fetchMembers(orgId) {
      try {
        const response = await api.get(`/organizations/${orgId}/members`)
        this.members = response.data
        return { success: true, data: this.members }
      } catch (error) {
        return { success: false, error: error.message }
      }
    },

    async inviteMember(orgId, userId, role) {
      try {
        const response = await api.post(`/organizations/${orgId}/members`, {
          user_id: userId,
          role: role
        })
        this.members.push(response.data)
        return { success: true, data: response.data }
      } catch (error) {
        return { success: false, error: error.response?.data?.detail || error.message }
      }
    },

    async changeMemberRole(orgId, userId, newRole) {
      try {
        const response = await api.put(
          `/organizations/${orgId}/members/${userId}`,
          { role: newRole }
        )
        const index = this.members.findIndex(m => m.user_id === userId)
        if (index >= 0) {
          this.members[index] = response.data
        }
        return { success: true, data: response.data }
      } catch (error) {
        return { success: false, error: error.response?.data?.detail || error.message }
      }
    },

    async removeMember(orgId, userId) {
      try {
        await api.delete(`/organizations/${orgId}/members/${userId}`)
        this.members = this.members.filter(m => m.user_id !== userId)
        return { success: true }
      } catch (error) {
        return { success: false, error: error.response?.data?.detail || error.message }
      }
    },

    async transferOwnership(orgId, newOwnerId) {
      try {
        await api.post(`/organizations/${orgId}/transfer`, {
          new_owner_id: newOwnerId
        })
        // Refresh members to get updated roles
        await this.fetchMembers(orgId)
        return { success: true }
      } catch (error) {
        return { success: false, error: error.response?.data?.detail || error.message }
      }
    }
  }
})
```

### Step 2: Create OrganizationSettings.vue

```vue
<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Organization Settings</h1>
      </v-col>
    </v-row>

    <v-row v-if="loading">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate />
      </v-col>
    </v-row>

    <template v-else-if="currentOrg">
      <!-- Organization Details -->
      <v-row>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Organization Details</v-card-title>
            <v-card-text>
              <v-text-field
                v-model="orgForm.name"
                label="Organization Name"
                :disabled="!isAdmin"
              />
              <v-text-field
                v-model="currentOrg.slug"
                label="Slug (URL-friendly)"
                disabled
                hint="Cannot be changed after creation"
              />
              <v-btn
                v-if="isAdmin"
                color="primary"
                :loading="saving"
                @click="saveOrgDetails"
              >
                Save Changes
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Members Section -->
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>
              Members
              <v-spacer />
              <v-btn
                v-if="canManageMembers"
                color="primary"
                size="small"
                @click="showInviteDialog = true"
              >
                <v-icon start>mdi-account-plus</v-icon>
                Invite
              </v-btn>
            </v-card-title>
            <v-card-text>
              <MemberList
                :members="members"
                :can-manage="canManageMembers"
                :is-owner="isOwner"
                @change-role="handleRoleChange"
                @remove="handleRemoveMember"
                @transfer="handleTransferOwnership"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Danger Zone (Owner only) -->
      <v-row v-if="isOwner">
        <v-col cols="12">
          <v-card color="error" variant="outlined">
            <v-card-title class="text-error">Danger Zone</v-card-title>
            <v-card-text>
              <v-btn
                color="error"
                variant="outlined"
                @click="showDeleteDialog = true"
              >
                Delete Organization
              </v-btn>
              <p class="text-caption mt-2">
                This will permanently delete the organization and all its data.
              </p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <v-alert v-else type="error">
      Organization not found or you don't have access.
    </v-alert>

    <!-- Invite Dialog -->
    <InviteMemberDialog
      v-model="showInviteDialog"
      :org-id="currentOrg?.id"
      @invited="handleMemberInvited"
    />

    <!-- Delete Confirmation -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Organization?</v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ currentOrg?.name }}</strong>?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteOrg">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrgStore } from '@/stores/orgStore'
import MemberList from '@/components/org/MemberList.vue'
import InviteMemberDialog from '@/components/org/InviteMemberDialog.vue'

const route = useRoute()
const router = useRouter()
const orgStore = useOrgStore()

const orgForm = ref({ name: '' })
const saving = ref(false)
const showInviteDialog = ref(false)
const showDeleteDialog = ref(false)

// Computed from store
const loading = computed(() => orgStore.loading)
const currentOrg = computed(() => orgStore.currentOrg)
const members = computed(() => orgStore.members)
const isOwner = computed(() => orgStore.isOwner)
const isAdmin = computed(() => orgStore.isAdmin)
const canManageMembers = computed(() => orgStore.canManageMembers)

// Load org on mount
onMounted(async () => {
  const orgId = route.params.orgId
  if (orgId) {
    await orgStore.fetchOrganization(orgId)
    if (currentOrg.value) {
      orgForm.value.name = currentOrg.value.name
    }
  }
})

// Watch for org changes
watch(currentOrg, (newOrg) => {
  if (newOrg) {
    orgForm.value.name = newOrg.name
  }
})

async function saveOrgDetails() {
  saving.value = true
  const result = await orgStore.updateOrganization(currentOrg.value.id, {
    name: orgForm.value.name
  })
  saving.value = false

  if (result.success) {
    // Show success notification
  } else {
    // Show error notification
  }
}

async function handleRoleChange({ userId, newRole }) {
  const result = await orgStore.changeMemberRole(
    currentOrg.value.id,
    userId,
    newRole
  )
  if (!result.success) {
    // Show error notification
  }
}

async function handleRemoveMember(userId) {
  const result = await orgStore.removeMember(currentOrg.value.id, userId)
  if (!result.success) {
    // Show error notification
  }
}

async function handleTransferOwnership(newOwnerId) {
  const result = await orgStore.transferOwnership(currentOrg.value.id, newOwnerId)
  if (!result.success) {
    // Show error notification
  }
}

function handleMemberInvited(member) {
  // Member added to store automatically
  showInviteDialog.value = false
}

async function deleteOrg() {
  const result = await orgStore.deleteOrganization(currentOrg.value.id)
  if (result.success) {
    router.push('/dashboard')
  }
  showDeleteDialog.value = false
}
</script>
```

### Step 3: Create MemberList.vue

```vue
<template>
  <v-list>
    <v-list-item
      v-for="member in members"
      :key="member.id"
    >
      <template #prepend>
        <v-avatar color="primary" size="40">
          <span class="text-uppercase">{{ member.user_id.slice(0, 2) }}</span>
        </v-avatar>
      </template>

      <v-list-item-title>
        User: {{ member.user_id.slice(0, 8) }}...
      </v-list-item-title>

      <v-list-item-subtitle>
        <v-chip
          :color="roleColor(member.role)"
          size="small"
          class="mr-2"
        >
          {{ member.role }}
        </v-chip>
        <span class="text-caption">
          Joined {{ formatDate(member.joined_at) }}
        </span>
      </v-list-item-subtitle>

      <template #append>
        <v-menu v-if="canManage && member.role !== 'owner'">
          <template #activator="{ props }">
            <v-btn icon="mdi-dots-vertical" variant="text" v-bind="props" />
          </template>
          <v-list>
            <v-list-item
              v-for="role in availableRoles"
              :key="role"
              :disabled="member.role === role"
              @click="$emit('change-role', { userId: member.user_id, newRole: role })"
            >
              <v-list-item-title>Make {{ role }}</v-list-item-title>
            </v-list-item>
            <v-divider />
            <v-list-item
              class="text-error"
              @click="$emit('remove', member.user_id)"
            >
              <v-list-item-title>Remove from org</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <!-- Transfer ownership (owner only, to admins) -->
        <v-btn
          v-if="isOwner && member.role === 'admin'"
          color="warning"
          variant="text"
          size="small"
          @click="$emit('transfer', member.user_id)"
        >
          Transfer Ownership
        </v-btn>
      </template>
    </v-list-item>

    <v-list-item v-if="!members.length">
      <v-list-item-title class="text-center text-grey">
        No members
      </v-list-item-title>
    </v-list-item>
  </v-list>
</template>

<script setup>
defineProps({
  members: { type: Array, required: true },
  canManage: { type: Boolean, default: false },
  isOwner: { type: Boolean, default: false }
})

defineEmits(['change-role', 'remove', 'transfer'])

const availableRoles = ['admin', 'member', 'viewer']

function roleColor(role) {
  const colors = {
    owner: 'purple',
    admin: 'blue',
    member: 'green',
    viewer: 'grey'
  }
  return colors[role] || 'grey'
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString()
}
</script>
```

### Step 4: Create InviteMemberDialog.vue

```vue
<template>
  <v-dialog v-model="model" max-width="500">
    <v-card>
      <v-card-title>Invite Member</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="userId"
          label="User ID"
          placeholder="Enter user ID to invite"
          :error-messages="error"
        />
        <v-select
          v-model="role"
          :items="roles"
          label="Role"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="model = false">Cancel</v-btn>
        <v-btn
          color="primary"
          :loading="loading"
          :disabled="!userId"
          @click="invite"
        >
          Invite
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useOrgStore } from '@/stores/orgStore'

const props = defineProps({
  orgId: { type: String, required: true }
})

const emit = defineEmits(['invited'])

const model = defineModel({ type: Boolean, default: false })

const orgStore = useOrgStore()
const userId = ref('')
const role = ref('member')
const loading = ref(false)
const error = ref('')

const roles = [
  { title: 'Admin', value: 'admin' },
  { title: 'Member', value: 'member' },
  { title: 'Viewer', value: 'viewer' }
]

async function invite() {
  if (!userId.value) return

  loading.value = true
  error.value = ''

  const result = await orgStore.inviteMember(props.orgId, userId.value, role.value)

  loading.value = false

  if (result.success) {
    emit('invited', result.data)
    userId.value = ''
    role.value = 'member'
    model.value = false
  } else {
    error.value = result.error
  }
}
</script>
```

### Step 5: Update Router (frontend/src/router/index.js)

```javascript
// Add organization routes
{
  path: '/organizations/:orgId/settings',
  name: 'OrganizationSettings',
  component: () => import('@/views/OrganizationSettings.vue'),
  meta: { requiresAuth: true }
}
```

### Step 6: UI Tweak - Move Test Connection Button (DatabaseConnection.vue)

**File:** `frontend/src/components/DatabaseConnection.vue`

**Before:** Test Connection button is below the divider
**After:** Test Connection button is above the divider

Find the current location of the Test Connection button and move it above any `<v-divider>` element in the form section.

```vue
<!-- BEFORE (button below divider) -->
<v-divider class="my-4" />
<v-btn color="primary" @click="testConnection">Test Connection</v-btn>

<!-- AFTER (button above divider) -->
<v-btn color="primary" @click="testConnection" class="mb-4">Test Connection</v-btn>
<v-divider class="my-4" />
```

---

## Files to Create/Modify

### NEW Files:
```
□ frontend/src/views/OrganizationSettings.vue (~200 lines)
□ frontend/src/components/org/MemberList.vue (~120 lines)
□ frontend/src/components/org/InviteMemberDialog.vue (~80 lines)
□ frontend/src/stores/orgStore.js (~200 lines)
```

### MODIFIED Files:
```
□ frontend/src/router/index.js (5 lines - add route)
□ frontend/src/services/api.js (already has base, may need org methods)
□ frontend/src/components/DatabaseConnection.vue (move button - 2 lines)
```

---

## Test Scenarios (Manual)

1. **View org settings** - Navigate to `/organizations/{id}/settings`
2. **Update org name** - Change name and save (admin/owner)
3. **Invite member** - Click invite, enter user ID, select role
4. **Change member role** - Use dropdown to change role (admin/owner)
5. **Remove member** - Remove non-owner member (admin/owner)
6. **Transfer ownership** - Transfer to admin (owner only)
7. **Delete organization** - Delete org (owner only)
8. **Permission denied** - Verify member/viewer can't edit

---

## Verification Checklist

- [ ] OrganizationSettings page renders correctly
- [ ] Member list shows all members with roles
- [ ] Invite dialog works for owner/admin
- [ ] Role change works for non-owner members
- [ ] Remove member works (cannot remove owner)
- [ ] Transfer ownership works
- [ ] Delete organization works (owner only)
- [ ] Permission checks enforced in UI
- [ ] Test Connection button moved above divider
- [ ] No console errors
- [ ] Responsive design works

---

## Dependencies

- **Depends on:** 0424c (API Endpoints must exist)
- **Blocks:** 0424e (Integration testing)

---

## Notes for Implementing Agent

1. **Follow Vuetify patterns** - Match existing components
2. **Use Pinia store** - All state in orgStore
3. **Permission-based UI** - Hide/disable based on role
4. **Error handling** - Show user-friendly messages
5. **UI tweak is simple** - Just move the button element

---

## Success Criteria

- [ ] All 4 new components created
- [ ] Organization settings page functional
- [ ] Member management works end-to-end
- [ ] Permission levels reflected in UI
- [ ] Test Connection button moved (UI tweak)
- [ ] No regressions in other components
- [ ] Manual testing complete
