import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useTheme } from 'vuetify'
import api from '@/services/api'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const httpProto = window.location.protocol === 'https:' ? 'https' : 'http'
  const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'

  const settings = ref({
    theme: 'dark',
    notifications: {
      position: 'bottom-right',
      duration: 5,
    },
    compactView: false,
    showMascot: true,
    apiUrl: `${httpProto}://localhost:6002`,
    wsUrl: `${wsProto}://localhost:6003`,
  })

  const loading = ref(false)
  const error = ref(null)

  // Field priority configuration (Handover 0048)
  const fieldPriorityConfig = ref(null)

  // Theme management
  const theme = useTheme()

  // Getters
  const notificationPosition = computed(() => settings.value.notifications?.position || 'bottom-right')
  const notificationDuration = computed(() => (settings.value.notifications?.duration || 5) * 1000)

  // Actions
  async function loadSettings() {
    loading.value = true
    error.value = null
    try {
      // Load from localStorage first
      const savedSettings = localStorage.getItem('giljo_settings')
      if (savedSettings) {
        settings.value = { ...settings.value, ...JSON.parse(savedSettings) }
      }

      // CRITICAL: Check theme-preference as source of truth
      // This prevents NavigationDrawer theme toggles from being overwritten
      const themePreference = localStorage.getItem('theme-preference')
      if (themePreference && themePreference === 'dark') {
        settings.value.theme = themePreference
      }

      // Apply theme after synchronization
      applyTheme()

      // Then try to load from server
      try {
        const response = await api.settings.get()
        settings.value = { ...settings.value, ...response.data }

        // Re-check theme-preference after server load
        const currentThemePreference = localStorage.getItem('theme-preference')
        if (currentThemePreference && currentThemePreference === 'dark') {
          settings.value.theme = currentThemePreference
        }

        saveToLocalStorage()
      } catch {
        // Using local settings, server not available
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to load settings:', err)
    } finally {
      loading.value = false
    }
  }

  async function saveSettings() {
    loading.value = true
    error.value = null
    try {
      // Save to localStorage immediately
      saveToLocalStorage()

      // Then sync with server
      try {
        await api.settings.update(settings.value)
      } catch {
        // Settings saved locally, server sync failed
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to save settings:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function updateSetting(key, value) {
    if (settings.value[key] !== undefined) {
      settings.value[key] = value

      // Apply theme immediately if changed
      if (key === 'theme') {
        applyTheme()
      }

      // Auto-save
      saveToLocalStorage()
    }
  }

  async function updateSettings(partial) {
    settings.value = { ...settings.value, ...partial }
    saveToLocalStorage()
    try {
      await api.settings.update(settings.value)
    } catch {
      // Settings saved locally, server sync failed silently
    }
  }


  function applyTheme() {
    theme.change(settings.value.theme)
  }

  function saveToLocalStorage() {
    localStorage.setItem('giljo_settings', JSON.stringify(settings.value))
  }

  function resetSettings() {
    settings.value = {
      theme: 'dark',
      notifications: {
        position: 'bottom-right',
        duration: 5,
      },
      compactView: false,
      showMascot: true,
      apiUrl: `${httpProto}://localhost:6002`,
      wsUrl: `${wsProto}://localhost:6003`,
    }
    applyTheme()
    saveToLocalStorage()
  }

  function clearError() {
    error.value = null
  }

  // Field Priority Configuration Actions (Handover 0048)
  async function fetchFieldPriorityConfig() {
    try {
      const response = await api.users.getFieldPriorityConfig()
      fieldPriorityConfig.value = response.data
    } catch (err) {
      console.error('Failed to fetch field priority config:', err)
      throw err
    }
  }

  async function updateFieldPriorityConfig(config) {
    try {
      const response = await api.users.updateFieldPriorityConfig(config)
      fieldPriorityConfig.value = response.data
    } catch (err) {
      console.error('Failed to update field priority config:', err)
      throw err
    }
  }

  async function resetFieldPriorityConfig() {
    try {
      const response = await api.users.resetFieldPriorityConfig()
      fieldPriorityConfig.value = response.data
    } catch (err) {
      console.error('Failed to reset field priority config:', err)
      throw err
    }
  }

  // Watch for settings changes
  watch(
    settings,
    () => {
      saveToLocalStorage()
    },
    { deep: true },
  )

  return {
    // State
    settings,
    loading,
    error,
    fieldPriorityConfig,

    // Getters
    notificationPosition,
    notificationDuration,

    // Actions
    loadSettings,
    saveSettings,
    updateSetting,
    updateSettings,
    resetSettings,
    clearError,
    fetchFieldPriorityConfig,
    updateFieldPriorityConfig,
    resetFieldPriorityConfig,
  }
})
