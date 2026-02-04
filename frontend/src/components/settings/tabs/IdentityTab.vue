<template>
  <v-row v-if="loading" class="my-6">
    <v-col cols="12" class="text-center">
      <v-progress-circular indeterminate color="primary" />
    </v-col>
  </v-row>

  <v-alert v-else-if="error" type="error" class="mb-4" data-test="error-alert">
    {{ error }}
  </v-alert>

  <v-row v-else-if="currentOrg" class="ga-4">
    <!-- Workspace Details Section -->
    <v-col cols="12" md="6">
      <v-card data-test="workspace-card">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-office-building</v-icon>
          Workspace Details
        </v-card-title>

        <v-card-text>
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
        </v-card-text>

        <v-card-actions v-if="isAdmin" class="gap-2">
          <v-spacer />
          <v-btn variant="text" @click="resetForm" data-test="reset-btn">
            Reset
          </v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            :disabled="!isFormDirty"
            @click="saveOrgDetails"
            data-test="save-org-btn"
          >
            <v-icon start>mdi-content-save</v-icon>
            Save Changes
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-col>

    <!-- Users Section -->
    <v-col cols="12" md="6">
      <v-card data-test="users-card">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-account-group</v-icon>
          Users
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-0">
          <UserManager />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>

  <v-alert v-else type="warning" class="my-6" data-test="no-org-alert">
    <v-icon start>mdi-alert</v-icon>
    No organization found. Please contact your administrator.
  </v-alert>

  <!-- Notification Snackbar -->
  <v-snackbar
    v-model="snackbar.show"
    :color="snackbar.color"
    :timeout="3000"
    data-test="snackbar"
  >
    {{ snackbar.message }}
  </v-snackbar>
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
import UserManager from '@/components/UserManager.vue'

// Stores
const orgStore = useOrgStore()
const userStore = useUserStore()

// Local state
const orgForm = ref({ name: '' })
const saving = ref(false)
const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
})

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
function showNotification(message, color = 'success') {
  snackbar.value = { show: true, message, color }
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
