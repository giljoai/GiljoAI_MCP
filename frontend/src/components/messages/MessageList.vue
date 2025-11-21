<template>
  <div class="message-list">
    <v-virtual-scroll
      v-if="messages.length > 0"
      :items="messages"
      :item-height="120"
      height="600"
    >
      <template #default="{ item }">
        <div class="px-4 pt-3" @click="$emit('message-click', item)">
          <MessageItem
            :message="item"
            :show-actions="false"
          />
        </div>
      </template>
    </v-virtual-scroll>

    <!-- Empty state -->
    <v-alert
      v-else
      type="info"
      variant="tonal"
      class="ma-4"
    >
      <div class="empty-state text-center">
        <v-icon size="64" color="grey-lighten-1">mdi-message-text-outline</v-icon>
        <p class="text-grey-lighten-1 mt-4">No messages yet</p>
      </div>
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import MessageItem from './MessageItem.vue'
import type { Message } from '@/types/message'

interface Props {
  messages?: Message[]
}

const props = withDefaults(defineProps<Props>(), {
  messages: () => []
})

const emit = defineEmits<{
  'message-click': [message: Message]
}>()
</script>

<style scoped>
.message-list {
  width: 100%;
  position: relative;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}
</style>
