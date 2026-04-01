<template>
  <div class="message-list">
    <v-virtual-scroll v-if="messages.length > 0" :items="messages" :item-height="120" height="600">
      <template #default="{ item }">
        <div class="px-4 pt-3" @click="$emit('message-click', item)">
          <MessageItem :message="item" :show-actions="false" />
        </div>
      </template>
    </v-virtual-scroll>

    <!-- Empty state -->
    <EmptyState
      v-else
      icon="mdi-message-text-outline"
      title="No messages yet"
    />
  </div>
</template>

<script setup lang="ts">
import MessageItem from './MessageItem.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { Message } from '@/types/message'

interface Props {
  messages?: Message[]
}

const props = withDefaults(defineProps<Props>(), {
  messages: () => [],
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

</style>
