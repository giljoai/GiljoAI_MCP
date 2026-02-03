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

    <!-- Members Section -->
    <v-col cols="12" md="6">
      <v-card data-test="members-card">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-account-multiple</v-icon>
          Members
          <v-spacer />
          <v-btn
            v-if="canManageMembers"
            color="primary"
            size="small"
            variant="tonal"
            @click="showInviteDialog = true"
            data-test="invite-btn"
          >
            <v-icon start size="small">mdi-account-plus</v-icon>
            Invite
          </v-btn>
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-0">
          <MemberList
            :members="members"
            :can-manage="canManageMembers"
            :is-owner="isOwner"
            data-test="member-list"
            @change-role="handleRoleChange"
            @remove="handleRemoveMember"
            @transfer="handleTransferOwnership"
          />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>

  <v-alert v-else type="warning" class="my-6" data-test="no-org-alert">
    <v-icon start>mdi-alert</v-icon>
    No organization found. Please contact your administrator.
  </v-alert>

  <!-- Invite Member Dialog -->
  <InviteMemberDialog
    v-if="currentOrg"
    v-model="showInviteDialog"
    :org-id="currentOrg.id"
    data-test="invite-dialog"
    @invited="handleMemberInvited"
  />

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
 * IdentityTab - Workspace and member management tab for Admin Settings.
 * Handover 0434: Identity tab consolidating workspace and member management.
 *
 * @component
 * @example
 * <IdentityTab />
 */

import { ref, computed, onMounted, watch } from 'vue'
import { useOrgStore } from '@/stores/orgStore'
import { useUserStore } from '@/stores/user'
import MemberList from '@/components/org/MemberList.vue'
import InviteMemberDialog from '@/components/org/InviteMemberDialog.vue'

// Stores
const orgStore = useOrgStore()
const userStore = useUserStore()

// Local state
const orgForm = ref({ name: '' })
const saving = ref(false)
const showInviteDialog = ref(false)
const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
})

// Computed from stores
const loading = computed(() => orgStore.loading)
const error = computed(() => orgStore.error)
const currentOrg = computed(() => orgStore.currentOrg)
const members = computed(() => orgStore.members)
const isOwner = computed(() => orgStore.isOwner)
const isAdmin = computed(() => orgStore.isAdmin)
const canManageMembers = computed(() => orgStore.canManageMembers)

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

// Handle member role change
async function handleRoleChange({ userId, newRole }) {
  if (!currentOrg.value) return

  const result = await orgStore.changeMemberRole(currentOrg.value.id, userId, newRole)

  if (result.success) {
    showNotification('Member role updated')
  } else {
    showNotification(result.error || 'Failed to update member role', 'error')
  }
}

// Handle member removal
async function handleRemoveMember(userId) {
  if (!currentOrg.value) return

  const result = await orgStore.removeMember(currentOrg.value.id, userId)

  if (result.success) {
    showNotification('Member removed from workspace')
  } else {
    showNotification(result.error || 'Failed to remove member', 'error')
  }
}

// Handle ownership transfer
async function handleTransferOwnership(newOwnerId) {
  if (!currentOrg.value) return

  const result = await orgStore.transferOwnership(currentOrg.value.id, newOwnerId)

  if (result.success) {
    showNotification('Workspace ownership transferred successfully')
  } else {
    showNotification(result.error || 'Failed to transfer ownership', 'error')
  }
}

// Handle member invitation success
function handleMemberInvited(member) {
  showNotification('Member invited successfully')
  showInviteDialog.value = false
}
</script>
