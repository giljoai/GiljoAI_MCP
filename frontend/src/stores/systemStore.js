import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useSystemStore = defineStore('systemDomain', () => {
  const lastProgress = ref(null)
  const notifications = ref([])

  const notificationCount = computed(() => notifications.value.length)

  function handleProgress(payload) {
    lastProgress.value = payload || null
  }

  function handleNotification(payload) {
    if (!payload) return
    notifications.value = [payload, ...notifications.value].slice(0, 100)
  }

  function $reset() {
    lastProgress.value = null
    notifications.value = []
  }

  return {
    lastProgress,
    notifications,
    notificationCount,
    handleProgress,
    handleNotification,
    $reset,
  }
})
