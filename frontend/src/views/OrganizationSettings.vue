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
                data-test="org-name"
              />
              <v-text-field
                v-model="currentOrg.slug"
                label="Slug (URL-friendly)"
                disabled
                hint="Cannot be changed after creation"
                data-test="org-slug"
              />
              <v-btn
                v-if="isAdmin"
                color="primary"
                :loading="saving"
                @click="saveOrgDetails"
                data-test="save-org-btn"
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
                data-test="invite-btn"
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
                data-test="delete-org-btn"
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

    <v-alert v-else type="error" data-test="org-not-found">
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
          Are you sure you want to delete <strong>{{ currentOrg?.name }}</strong
          >? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false" data-test="delete-cancel">Cancel</v-btn>
          <v-btn color="error" @click="deleteOrg" data-test="delete-confirm">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
/**
 * OrganizationSettings - Main organization management page.
 * Handover 0424d: Organization settings view with member management.
 *
 * @view
 * @route /organizations/:orgId/settings
 */
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
const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
})

// Computed from store
const loading = computed(() => orgStore.loading)
const currentOrg = computed(() => orgStore.currentOrg)
const members = computed(() => orgStore.members)
const isOwner = computed(() => orgStore.isOwner)
const isAdmin = computed(() => orgStore.isAdmin)
const canManageMembers = computed(() => orgStore.canManageMembers)

// Show notification
function showNotification(message, color = 'success') {
  snackbar.value = {
    show: true,
    message,
    color,
  }
}

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
    name: orgForm.value.name,
  })
  saving.value = false

  if (result.success) {
    showNotification('Organization updated successfully')
  } else {
    showNotification(result.error || 'Failed to update organization', 'error')
  }
}

async function handleRoleChange({ userId, newRole }) {
  const result = await orgStore.changeMemberRole(currentOrg.value.id, userId, newRole)
  if (result.success) {
    showNotification('Member role updated')
  } else {
    showNotification(result.error || 'Failed to update role', 'error')
  }
}

async function handleRemoveMember(userId) {
  const result = await orgStore.removeMember(currentOrg.value.id, userId)
  if (result.success) {
    showNotification('Member removed')
  } else {
    showNotification(result.error || 'Failed to remove member', 'error')
  }
}

async function handleTransferOwnership(newOwnerId) {
  const result = await orgStore.transferOwnership(currentOrg.value.id, newOwnerId)
  if (result.success) {
    showNotification('Ownership transferred successfully')
  } else {
    showNotification(result.error || 'Failed to transfer ownership', 'error')
  }
}

function handleMemberInvited(member) {
  showNotification(`Member ${member.user_id.slice(0, 8)}... invited successfully`)
  showInviteDialog.value = false
}

async function deleteOrg() {
  const result = await orgStore.deleteOrganization(currentOrg.value.id)
  if (result.success) {
    showNotification('Organization deleted')
    router.push('/Dashboard')
  } else {
    showNotification(result.error || 'Failed to delete organization', 'error')
  }
  showDeleteDialog.value = false
}
</script>
