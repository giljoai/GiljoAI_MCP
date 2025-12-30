/**
 * Auto-Save Composable
 *
 * Provides automatic form data persistence to LocalStorage with debouncing.
 * Designed for critical data preservation in complex multi-tab forms.
 *
 * Features:
 * - 500ms debounced saves to prevent performance issues
 * - LocalStorage-first approach (no backend calls during typing)
 * - Graceful error handling (quota exceeded, parse errors)
 * - Cache metadata (timestamp, age, size)
 * - Save status tracking for UI feedback
 *
 * @example
 * const autoSave = useAutoSave({
 *   key: 'product_form_draft_123',
 *   data: productForm,
 *   debounceMs: 500,
 * })
 */

import { ref, watch, onUnmounted, getCurrentInstance } from 'vue'
import { debounce } from 'lodash-es'

export function useAutoSave(options = {}) {
  const { key, data, saveFunction, debounceMs = 500, enableBackgroundSave = false } = options

  // Reactive state
  const saveStatus = ref('saved') // 'saved' | 'saving' | 'unsaved' | 'error'
  const lastSaved = ref(null) // Timestamp (ms since epoch)
  const hasUnsavedChanges = ref(false)
  const errorMessage = ref(null)

  /**
   * Save form data to LocalStorage (synchronous, <5ms)
   * @returns {boolean} Success status
   */
  function saveToCache() {
    if (!key || !data.value) {
      console.warn('[AUTO-SAVE] Missing key or data, skipping cache save')
      return false
    }

    try {
      const cacheData = {
        data: data.value,
        timestamp: Date.now(),
        version: '1.0',
      }

      const serialized = JSON.stringify(cacheData)
      localStorage.setItem(key, serialized)

      console.log('[AUTO-SAVE] ✓ Saved to LocalStorage:', {
        key,
        sizeBytes: serialized.length,
        timestamp: new Date(cacheData.timestamp).toISOString(),
      })

      return true
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to save to LocalStorage:', error)

      if (error.name === 'QuotaExceededError') {
        errorMessage.value = 'Storage quota exceeded. Changes saved in memory only.'
        saveStatus.value = 'error'
      } else {
        errorMessage.value = 'Failed to save draft. Changes saved in memory only.'
        saveStatus.value = 'error'
      }

      return false
    }
  }

  /**
   * Save to backend API (asynchronous, optional)
   * @returns {Promise<boolean>} Success status
   */
  async function saveToBackend() {
    if (!saveFunction || !enableBackgroundSave) {
      return false
    }

    try {
      saveStatus.value = 'saving'
      await saveFunction(data.value)
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
      hasUnsavedChanges.value = false
      errorMessage.value = null

      console.log('[AUTO-SAVE] ✓ Saved to backend:', {
        key,
        timestamp: new Date(lastSaved.value).toISOString(),
      })

      return true
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to save to backend:', error)
      saveStatus.value = 'error'
      errorMessage.value = 'Failed to save to server. Changes cached locally.'
      return false
    }
  }

  /**
   * Debounced save function (500ms default)
   * Saves to LocalStorage immediately, optionally to backend
   */
  const debouncedSave = debounce(async () => {
    if (!key || !data.value) {
      console.warn('[AUTO-SAVE] Missing key or data, skipping debounced save')
      return
    }

    const cacheSuccess = saveToCache()

    if (enableBackgroundSave && cacheSuccess) {
      await saveToBackend()
    } else if (cacheSuccess) {
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
      hasUnsavedChanges.value = false
      errorMessage.value = null
    }
  }, debounceMs)

  /**
   * Watch for changes in form data
   * Triggers debounced save on any change
   */
  const stopWatch = watch(
    () => data.value,
    () => {
      hasUnsavedChanges.value = true
      saveStatus.value = 'unsaved'
      debouncedSave()
    },
    { deep: true },
  )

  /**
   * Restore form data from LocalStorage
   * @returns {Object|null} Cached data or null if not found/invalid
   */
  function restoreFromCache() {
    if (!key) {
      console.warn('[AUTO-SAVE] Missing key, cannot restore from cache')
      return null
    }

    try {
      const cached = localStorage.getItem(key)
      if (!cached) {
        console.log('[AUTO-SAVE] No cache found for key:', key)
        return null
      }

      const cacheData = JSON.parse(cached)

      // Validate cache structure
      if (!cacheData.data || !cacheData.timestamp) {
        console.warn('[AUTO-SAVE] Invalid cache format, clearing:', key)
        clearCache()
        return null
      }

      const ageMs = Date.now() - cacheData.timestamp
      const ageMinutes = Math.round(ageMs / 60000)

      console.log('[AUTO-SAVE] ✓ Restored from cache:', {
        key,
        age: `${ageMinutes} minutes ago`,
        timestamp: new Date(cacheData.timestamp).toISOString(),
      })

      return cacheData.data
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to restore from cache:', error)
      clearCache()
      return null
    }
  }

  /**
   * Clear cache from LocalStorage
   */
  function clearCache() {
    if (!key) {
      console.warn('[AUTO-SAVE] Missing key, cannot clear cache')
      return
    }

    try {
      localStorage.removeItem(key)
      console.log('[AUTO-SAVE] ✓ Cleared cache:', key)
      hasUnsavedChanges.value = false
      saveStatus.value = 'saved'
      errorMessage.value = null
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to clear cache:', error)
    }
  }

  /**
   * Force immediate save (cancel debounce)
   * @returns {Promise<boolean>} Success status
   */
  function forceSave() {
    debouncedSave.cancel()

    const cacheSuccess = saveToCache()

    if (enableBackgroundSave && cacheSuccess) {
      return saveToBackend()
    } else {
      saveStatus.value = 'saved'
      lastSaved.value = Date.now()
      hasUnsavedChanges.value = false
      return Promise.resolve(cacheSuccess)
    }
  }

  /**
   * Get cache metadata without loading full data
   * @returns {Object|null} Cache metadata or null if not found
   */
  function getCacheMetadata() {
    if (!key) {
      return null
    }

    try {
      const cached = localStorage.getItem(key)
      if (!cached) {
        return null
      }

      const cacheData = JSON.parse(cached)
      const ageMs = Date.now() - cacheData.timestamp

      return {
        exists: true,
        timestamp: cacheData.timestamp,
        ageMs,
        ageMinutes: Math.round(ageMs / 60000),
        ageHours: Math.round(ageMs / 3600000),
        version: cacheData.version || 'unknown',
        sizeBytes: cached.length,
        sizeKB: Math.round(cached.length / 1024),
      }
    } catch (error) {
      console.error('[AUTO-SAVE] Failed to get cache metadata:', error)
      return null
    }
  }

  /**
   * Cleanup on component unmount
   * Stops watchers and cancels pending saves
   *
   * NOTE: Guard with getCurrentInstance() to prevent Vue warning when composable
   * is called outside setup() or after an await in async setup()
   */
  if (getCurrentInstance()) {
    onUnmounted(() => {
      stopWatch()
      debouncedSave.cancel()
      console.log('[AUTO-SAVE] Cleanup complete:', key)
    })
  }

  // Return public API
  return {
    // Reactive state
    saveStatus,
    lastSaved,
    hasUnsavedChanges,
    errorMessage,

    // Methods
    saveToCache,
    saveToBackend,
    restoreFromCache,
    clearCache,
    forceSave,
    getCacheMetadata,
  }
}
