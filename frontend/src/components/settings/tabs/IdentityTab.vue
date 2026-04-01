<template>
  <v-card variant="flat" class="smooth-border identity-card" data-test="workspace-card">
    <v-card-title>Identity</v-card-title>
    <v-card-subtitle class="identity-subtitle">Workspace and user management</v-card-subtitle>

    <v-card-text>
      <!-- Loading State -->
      <div v-if="loading" class="d-flex justify-center py-8">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <v-alert v-else-if="error" type="error" class="mb-4" data-test="error-alert">
        {{ error }}
      </v-alert>

      <template v-else-if="currentOrg">
        <!-- Workspace Details Section -->
        <h3 class="text-h6 mb-3">Workspace Details</h3>

        <v-text-field
          v-model="orgForm.name"
          label="Workspace Name"
          variant="outlined"
          :disabled="!isAdmin || saving"
          placeholder="Enter workspace name"
          hint="The name of your workspace"
          persistent-hint
          data-test="org-name-field"
          class="mb-4"
        />

        <v-text-field
          :model-value="currentOrg.slug"
          label="Slug (URL-friendly)"
          variant="outlined"
          disabled
          placeholder="url-slug"
          hint="Cannot be changed after creation"
          persistent-hint
          data-test="org-slug-field"
        />

        <!-- Users Section -->
        <v-divider class="my-6" />

        <h3 class="text-h6 mb-3" data-test="users-card">Users</h3>

        <UserManager />
      </template>

      <v-alert v-else type="warning" data-test="no-org-alert">
        No organization found. Please contact your administrator.
      </v-alert>
    </v-card-text>

    <v-card-actions v-if="isAdmin && currentOrg && !loading">
      <v-spacer />
      <v-btn variant="text" data-test="reset-btn" @click="resetForm">
        Reset
      </v-btn>
      <v-btn
        color="primary"
        :loading="saving"
        :disabled="!isFormDirty"
        data-test="save-org-btn"
        @click="saveOrgDetails"
      >
        <v-icon start>mdi-content-save</v-icon>
        Save Changes
      </v-btn>
    </v-card-actions>
  </v-card>


</template>

<script setup>
/**
 * IdentityTab - Workspace and user management tab for Admin Settings.
 * Handover 0434: Identity tab consolidating workspace and member management.
 * Handover 0424q: Replaced member invite with direct user creation via UserManager.
 *
 * @component
 * @example
 * <IdentityTab />
 */

import { ref, computed, onMounted, watch } from 'vue'
import { useOrgStore } from '@/stores/orgStore'
import { useUserStore } from '@/stores/user'
import { useToast } from '@/composables/useToast'
import UserManager from '@/components/UserManager.vue'

// Stores
const orgStore = useOrgStore()
const userStore = useUserStore()
const { showToast } = useToast()

// Local state
const orgForm = ref({ name: '' })
const saving = ref(false)

// Computed from stores
const loading = computed(() => orgStore.loading)
const error = computed(() => orgStore.error)
const currentOrg = computed(() => orgStore.currentOrg)
const isAdmin = computed(() => orgStore.isAdmin)

// Form state tracking
const isFormDirty = computed(() => {
  return orgForm.value.name !== (currentOrg.value?.name || '')
})

// Show notification helper
function showNotification(message, type = 'success') {
  showToast({ message, type })
}

// Load organization on component mount
onMounted(async () => {
  const orgId = userStore.currentUser?.org_id
  if (orgId) {
    await orgStore.fetchOrganization(orgId)
    if (currentOrg.value) {
      orgForm.value.name = currentOrg.value.name
    }
  }
})

// Watch for organization changes and update form
watch(currentOrg, (newOrg) => {
  if (newOrg) {
    orgForm.value.name = newOrg.name
  }
})

// Save organization details
async function saveOrgDetails() {
  if (!currentOrg.value || !isFormDirty.value) return

  saving.value = true

  const result = await orgStore.updateOrganization(currentOrg.value.id, {
    name: orgForm.value.name,
  })

  saving.value = false

  if (result.success) {
    showNotification('Workspace updated successfully')
  } else {
    showNotification(result.error || 'Failed to update workspace', 'error')
  }
}

// Reset form to original values
function resetForm() {
  if (currentOrg.value) {
    orgForm.value.name = currentOrg.value.name
  }
}
</script>

<style lang="scss" scoped>
@use '../../../styles/design-tokens' as *;
.identity-card {
  background: var(--bg-raised, #1e3147);
  border-radius: $border-radius-rounded;
}

.identity-subtitle {
  color: var(--text-muted);
}
</style>
