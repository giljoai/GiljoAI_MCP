<template>
  <v-dialog
    :model-value="isOpen"
    max-width="800px"
    persistent
    @update:model-value="handleDialogUpdate"
  >
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center justify-space-between bg-primary pa-4">
        <div class="d-flex align-center">
          <v-icon class="mr-2" color="white">mdi-message-text</v-icon>
          <span class="text-white">Messages: {{ agentName }}</span>
        </div>
        <v-btn
          icon
          size="small"
          variant="text"
          color="white"
          data-testid="close-button"
          @click="close"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider />

      <!-- Message List (reuse extracted component) -->
      <v-card-text class="pa-0 message-modal-content">
        <MessageList :messages="messages" @message-click="handleMessageClick" />
      </v-card-text>

      <v-divider />

      <!-- Message Input (modal position) -->
      <v-card-actions class="pa-4">
        <MessageInput
          :job-id="jobId"
          position="modal"
          class="flex-grow-1"
          @message-sent="handleMessageSent"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import MessageList from './MessageList.vue'
import MessageInput from '../projects/MessageInput.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true,
  },
  jobId: {
    type: String,
    required: true,
  },
  agentName: {
    type: String,
    required: true,
  },
  messages: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'message-sent'])

function close() {
  emit('close')
}

function handleDialogUpdate(value) {
  if (!value) {
    close()
  }
}

function handleMessageClick(message) {
  console.log('[MessageModal] Message clicked:', message.id)
}

function handleMessageSent(messageData) {
  emit('message-sent', messageData)
}
</script>

<style scoped>
.message-modal-content {
  max-height: 600px;
  overflow-y: auto;
}

.bg-primary {
  background-color: rgb(var(--v-theme-primary));
}

.text-white {
  color: white !important;
}
</style>
