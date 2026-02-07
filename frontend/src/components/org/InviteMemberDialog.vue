<template>
  <v-dialog v-model="dialogModel" max-width="500">
    <v-card>
      <v-card-title>Invite Member</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="userId"
          label="User ID"
          placeholder="Enter user ID to invite"
          :error-messages="error"
          data-test="invite-user-id"
        />
        <v-select v-model="role" :items="roles" label="Role" data-test="invite-role" />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn data-test="invite-cancel" @click="dialogModel = false">Cancel</v-btn>
        <v-btn
          color="primary"
          :loading="loading"
          :disabled="!userId"
          data-test="invite-submit"
          @click="invite"
        >
          Invite
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
/**
 * InviteMemberDialog - Dialog for inviting users to an organization.
 * Handover 0424d: Invite member dialog component.
 *
 * @component
 * @example
 * <InviteMemberDialog
 *   v-model="showDialog"
 *   :org-id="currentOrg.id"
 *   @invited="handleMemberInvited"
 * />
 */
import { ref, computed } from 'vue'
import { useOrgStore } from '@/stores/orgStore'

const props = defineProps({
  /** Organization ID to invite members to */
  orgId: { type: String, required: true },
  /** v-model for dialog visibility */
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'invited'])

const orgStore = useOrgStore()
const userId = ref('')
const role = ref('member')
const loading = ref(false)
const error = ref('')

// Two-way binding for dialog visibility
const dialogModel = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const roles = [
  { title: 'Admin', value: 'admin' },
  { title: 'Member', value: 'member' },
  { title: 'Viewer', value: 'viewer' },
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
    dialogModel.value = false
  } else {
    error.value = result.error
  }
}
</script>
