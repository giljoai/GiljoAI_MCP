import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useTheme } from 'vuetify'
import api from '@/services/api'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const settings = ref({
    theme: 'dark',
    autoRefresh: true,
    refreshInterval: 5000,
    notifications: true,
    soundEnabled: false,
    compactView: false,
    showMascot: true,
    apiUrl: 'http://localhost:6002',
    wsUrl: 'ws://localhost:6003',
  })

  const productInfo = ref(null)
  const sessionInfo = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Theme management
  const theme = useTheme()

  // Getters
  const isDarkTheme = computed(() => settings.value.theme === 'dark')
  const refreshEnabled = computed(() => settings.value.autoRefresh)
  const notificationsEnabled = computed(() => settings.value.notifications)

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
      if (themePreference && (themePreference === 'dark' || themePreference === 'light')) {
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
        if (currentThemePreference && (currentThemePreference === 'dark' || currentThemePreference === 'light')) {
          settings.value.theme = currentThemePreference
        }

        saveToLocalStorage()
      } catch (serverError) {
        console.log('Using local settings, server not available')
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
      } catch (serverError) {
        console.log('Settings saved locally, server sync failed')
      }
    } catch (err) {
      error.value = err.message
      console.error('Failed to save settings:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadProductInfo() {
    try {
      const response = await api.settings.getProduct()
      productInfo.value = response.data
    } catch (err) {
      console.error('Failed to load product info:', err)
    }
  }

  async function loadSessionInfo() {
    try {
      const response = await api.session.info()
      sessionInfo.value = response.data
    } catch (err) {
      console.error('Failed to load session info:', err)
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

  function toggleTheme() {
    settings.value.theme = settings.value.theme === 'dark' ? 'light' : 'dark'
    applyTheme()
    saveToLocalStorage()
  }

  function applyTheme() {
    theme.global.name.value = settings.value.theme  // TODO: Upgrade to theme.change() after Vuetify 3.7+
  }

  function saveToLocalStorage() {
    localStorage.setItem('giljo_settings', JSON.stringify(settings.value))
  }

  function resetSettings() {
    settings.value = {
      theme: 'dark',
      autoRefresh: true,
      refreshInterval: 5000,
      notifications: true,
      soundEnabled: false,
      compactView: false,
      showMascot: true,
      apiUrl: 'http://localhost:6002',
      wsUrl: 'ws://localhost:6003',
    }
    applyTheme()
    saveToLocalStorage()
  }

  function clearError() {
    error.value = null
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
    productInfo,
    sessionInfo,
    loading,
    error,

    // Getters
    isDarkTheme,
    refreshEnabled,
    notificationsEnabled,

    // Actions
    loadSettings,
    saveSettings,
    loadProductInfo,
    loadSessionInfo,
    updateSetting,
    toggleTheme,
    resetSettings,
    clearError,
  }
})
