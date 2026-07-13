<template>
  <BaseDialog
    v-model="isOpen"
    type="info"
    icon="mdi-forum-plus"
    title="New Thread"
    size="md"
    :persistent="false"
    @cancel="onCancel"
  >
    <template #default>
      <v-text-field
        v-model="form.subject"
        label="Subject"
        variant="outlined"
        density="compact"
        hide-details="auto"
        class="mb-4"
        data-testid="new-thread-subject"
      />

      <v-text-field
        v-model="form.project_id"
        label="Project ID (optional)"
        variant="outlined"
        density="compact"
        hide-details="auto"
        class="mb-4"
        data-testid="new-thread-project"
      />

      <v-text-field
        v-model="form.product_id"
        label="Product ID (optional)"
        variant="outlined"
        density="compact"
        hide-details="auto"
        data-testid="new-thread-product"
      />

      <v-alert
        v-if="errorMsg"
        type="error"
        variant="tonal"
        density="compact"
        class="mt-3"
        data-testid="new-thread-error"
      >
        {{ errorMsg }}
      </v-alert>
    </template>

    <template #actions>
      <v-btn
        variant="text"
        size="small"
        class="mr-2"
        data-testid="new-thread-cancel"
        @click="onCancel"
      >
        Cancel
      </v-btn>
      <v-btn
        :disabled="!form.subject.trim()"
        :loading="creating"
        variant="flat"
        color="primary"
        size="small"
        data-testid="new-thread-submit"
        @click="onCreate"
      >
        Create Thread
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useCommHubStore } from '@/stores/commHubStore'
import { useToast } from '@/composables/useToast'
import BaseDialog from '@/components/common/BaseDialog.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'created'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const commHub = useCommHubStore()
const { showToast } = useToast()

const form = reactive({
  subject: '',
  project_id: '',
  product_id: '',
})

const creating = ref(false)
const errorMsg = ref(null)

function onCancel() {
  resetForm()
  emit('update:modelValue', false)
}

function resetForm() {
  form.subject = ''
  form.project_id = ''
  form.product_id = ''
  errorMsg.value = null
}

async function onCreate() {
  if (!form.subject.trim()) return
  creating.value = true
  errorMsg.value = null
  try {
    const body = { subject: form.subject.trim() }
    if (form.project_id.trim()) body.project_id = form.project_id.trim()
    if (form.product_id.trim()) body.product_id = form.product_id.trim()

    const thread = await commHub.createThread(body)
    showToast({ type: 'success', message: 'Thread created.' })
    emit('created', thread)
    emit('update:modelValue', false)
    resetForm()
  } catch (err) {
    const msg = err?.response?.data?.detail || err?.message || 'Failed to create thread.'
    errorMsg.value = msg
    showToast({ type: 'error', message: msg })
  } finally {
    creating.value = false
  }
}
</script>
