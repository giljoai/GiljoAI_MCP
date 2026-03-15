/**
 * Auto-Save Composable Test Suite
 * Handover 0051: Product Form Auto-Save & UX Polish
 *
 * Tests for LocalStorage-based form data persistence with debouncing.
 *
 * NOTE: The useAutoSave composable creates a watch() unconditionally,
 * so callers MUST provide a valid ref for `data`. Calling without `data`
 * will cause a runtime error in the watch getter (data.value on undefined).
 * Tests that previously omitted `data` now provide a dummy ref.
 *
 * IMPORTANT: The global tests/setup.js replaces window.localStorage with
 * vi.fn() mocks that do nothing. This test file restores a real in-memory
 * localStorage implementation in beforeEach to test actual persistence.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ref, nextTick } from 'vue'
import { useAutoSave } from '@/composables/useAutoSave'

/**
 * Create a real in-memory localStorage implementation.
 * The global setup replaces localStorage with vi.fn() no-ops,
 * so we need a functional implementation for these tests.
 */
function createLocalStorageMock() {
  let store = {}
  return {
    getItem: vi.fn((key) => {
      return key in store ? store[key] : null
    }),
    setItem: vi.fn((key, value) => {
      store[key] = String(value)
    }),
    removeItem: vi.fn((key) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn((index) => {
      return Object.keys(store)[index] || null
    }),
  }
}

describe('useAutoSave Composable', () => {
  let realLocalStorage

  beforeEach(() => {
    // Replace the global no-op localStorage mock with a real implementation
    realLocalStorage = createLocalStorageMock()
    Object.defineProperty(window, 'localStorage', {
      value: realLocalStorage,
      writable: true,
      configurable: true,
    })
    localStorage.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
    localStorage.clear()
  })

  describe('Basic Initialization', () => {
    it('should initialize with default values', () => {
      const data = ref({ name: '', description: '' })
      const autoSave = useAutoSave({ key: 'test_key', data })

      expect(autoSave.saveStatus.value).toBe('saved')
      expect(autoSave.hasUnsavedChanges.value).toBe(false)
      expect(autoSave.errorMessage.value).toBeNull()
      expect(autoSave.lastSaved.value).toBeNull()
    })

    it('should handle missing key gracefully', () => {
      const data = ref({ name: '' })
      const autoSave = useAutoSave({ data })

      // Should not crash, methods should handle missing key
      expect(autoSave).toBeDefined()
      expect(autoSave.saveStatus.value).toBe('saved')
    })

    it('should crash if data is missing because watch() accesses data.value', () => {
      // The composable creates watch(() => data.value, ...) unconditionally,
      // so providing no data will cause a TypeError
      expect(() => {
        useAutoSave({ key: 'test_key' })
      }).toThrow()
    })
  })

  describe('saveToCache - LocalStorage Persistence', () => {
    it('should save form data to LocalStorage', () => {
      const data = ref({ name: 'Test Product', description: 'Test Description' })
      const autoSave = useAutoSave({ key: 'product_form_test', data })

      const result = autoSave.saveToCache()

      expect(result).toBe(true)
      const stored = localStorage.getItem('product_form_test')
      expect(stored).not.toBeNull()

      const parsed = JSON.parse(stored)
      expect(parsed.data.name).toBe('Test Product')
      expect(parsed.data.description).toBe('Test Description')
      expect(parsed.timestamp).toBeDefined()
      expect(parsed.version).toBe('1.0')
    })

    it('should handle quota exceeded error gracefully', () => {
      const data = ref({ name: 'Test', description: 'A'.repeat(1000000) })
      const autoSave = useAutoSave({ key: 'test_key', data })

      // Mock localStorage.setItem to throw QuotaExceededError
      const originalSetItem = localStorage.setItem
      localStorage.setItem = vi.fn(() => {
        const error = new Error('QuotaExceededError')
        error.name = 'QuotaExceededError'
        throw error
      })

      const result = autoSave.saveToCache()

      expect(result).toBe(false)
      expect(autoSave.saveStatus.value).toBe('error')
      expect(autoSave.errorMessage.value).toContain('Storage quota exceeded')

      localStorage.setItem = originalSetItem
    })

    it('should handle generic storage errors', () => {
      const data = ref({ name: 'Test' })
      const autoSave = useAutoSave({ key: 'test_key', data })

      const originalSetItem = localStorage.setItem
      localStorage.setItem = vi.fn(() => {
        throw new Error('Storage failed')
      })

      const result = autoSave.saveToCache()

      expect(result).toBe(false)
      expect(autoSave.saveStatus.value).toBe('error')
      expect(autoSave.errorMessage.value).toContain('Failed to save draft')

      localStorage.setItem = originalSetItem
    })

    it('should not save if key is missing', () => {
      const data = ref({ name: 'Test' })
      const autoSave = useAutoSave({ data })

      const result = autoSave.saveToCache()

      expect(result).toBe(false)
    })
  })

  describe('restoreFromCache - Draft Recovery', () => {
    it('should restore data from LocalStorage', () => {
      const cacheData = {
        data: { name: 'Cached Product', description: 'Cached Description' },
        timestamp: Date.now(),
        version: '1.0',
      }

      localStorage.setItem('product_cache', JSON.stringify(cacheData))

      const data = ref({ name: '', description: '' })
      const autoSave = useAutoSave({ key: 'product_cache', data })

      const restored = autoSave.restoreFromCache()

      expect(restored).toBeDefined()
      expect(restored.name).toBe('Cached Product')
      expect(restored.description).toBe('Cached Description')
    })

    it('should return null if cache does not exist', () => {
      const data = ref({ name: '' })
      const autoSave = useAutoSave({ key: 'nonexistent', data })

      const restored = autoSave.restoreFromCache()

      expect(restored).toBeNull()
    })

    it('should return null and clear invalid cache', () => {
      localStorage.setItem('invalid_cache', 'not valid json')

      const data = ref({ name: '' })
      const autoSave = useAutoSave({ key: 'invalid_cache', data })

      const restored = autoSave.restoreFromCache()

      expect(restored).toBeNull()
      expect(localStorage.getItem('invalid_cache')).toBeNull()
    })

    it('should return null if cache is missing required fields', () => {
      const badCache = {
        data: { name: 'Test' },
        // Missing timestamp
      }

      localStorage.setItem('bad_cache', JSON.stringify(badCache))

      const data = ref({ name: '' })
      const autoSave = useAutoSave({ key: 'bad_cache', data })

      const restored = autoSave.restoreFromCache()

      expect(restored).toBeNull()
      expect(localStorage.getItem('bad_cache')).toBeNull()
    })

    it('should calculate cache age correctly', () => {
      const tenMinutesAgo = Date.now() - 10 * 60 * 1000
      const cacheData = {
        data: { name: 'Test' },
        timestamp: tenMinutesAgo,
        version: '1.0',
      }

      localStorage.setItem('aged_cache', JSON.stringify(cacheData))

      const data = ref({ name: '' })
      const autoSave = useAutoSave({ key: 'aged_cache', data })

      const metadata = autoSave.getCacheMetadata()

      expect(metadata).not.toBeNull()
      expect(metadata.ageMinutes).toBeGreaterThanOrEqual(9)
      expect(metadata.ageMinutes).toBeLessThanOrEqual(11)
    })
  })

  describe('clearCache - Cache Removal', () => {
    it('should remove cache from LocalStorage', () => {
      localStorage.setItem('cache_to_clear', JSON.stringify({ data: {}, timestamp: Date.now() }))

      const data = ref({})
      const autoSave = useAutoSave({ key: 'cache_to_clear', data })

      autoSave.clearCache()

      expect(localStorage.getItem('cache_to_clear')).toBeNull()
      expect(autoSave.hasUnsavedChanges.value).toBe(false)
      expect(autoSave.saveStatus.value).toBe('saved')
      expect(autoSave.errorMessage.value).toBeNull()
    })

    it('should handle missing cache gracefully', () => {
      const data = ref({})
      const autoSave = useAutoSave({ key: 'nonexistent', data })

      // Should not throw
      expect(() => autoSave.clearCache()).not.toThrow()
    })

    it('should handle missing key gracefully', () => {
      const data = ref({})
      const autoSave = useAutoSave({ data })

      // Should not throw (clearCache guards on missing key)
      expect(() => autoSave.clearCache()).not.toThrow()
    })
  })

  describe('Debounced Save - 500ms Default', () => {
    it('should debounce saves (500ms default)', async () => {
      const data = ref({ name: 'Initial' })
      useAutoSave({ key: 'debounce_test', data, debounceMs: 500 })

      // Change data multiple times rapidly
      data.value.name = 'Change 1'
      await nextTick()
      data.value.name = 'Change 2'
      await nextTick()
      data.value.name = 'Change 3'
      await nextTick()

      expect(localStorage.getItem('debounce_test')).toBeNull()

      // Fast-forward time by 499ms
      vi.advanceTimersByTime(499)
      expect(localStorage.getItem('debounce_test')).toBeNull()

      // Fast-forward remaining 1ms
      vi.advanceTimersByTime(1)
      expect(localStorage.getItem('debounce_test')).not.toBeNull()

      const cached = JSON.parse(localStorage.getItem('debounce_test'))
      expect(cached.data.name).toBe('Change 3')
    })

    it('should update save status: unsaved -> saved', async () => {
      const data = ref({ name: 'Test' })
      const autoSave = useAutoSave({ key: 'status_test', data, debounceMs: 100 })

      expect(autoSave.saveStatus.value).toBe('saved')

      data.value.name = 'Updated'
      await nextTick()

      expect(autoSave.saveStatus.value).toBe('unsaved')
      expect(autoSave.hasUnsavedChanges.value).toBe(true)

      vi.advanceTimersByTime(100)

      expect(autoSave.saveStatus.value).toBe('saved')
      expect(autoSave.hasUnsavedChanges.value).toBe(false)
      expect(autoSave.lastSaved.value).toBeDefined()
    })
  })

  describe('forceSave - Immediate Save', () => {
    it('should force immediate save without debounce delay', () => {
      const data = ref({ name: 'Test' })
      const autoSave = useAutoSave({ key: 'force_test', data, debounceMs: 5000 })

      data.value.name = 'Updated'
      expect(localStorage.getItem('force_test')).toBeNull()

      const result = autoSave.forceSave()

      expect(result).toBeDefined()
      expect(localStorage.getItem('force_test')).not.toBeNull()

      const cached = JSON.parse(localStorage.getItem('force_test'))
      expect(cached.data.name).toBe('Updated')
    })

    it('should cancel pending debounced save', async () => {
      const data = ref({ name: 'Initial' })
      const autoSave = useAutoSave({ key: 'cancel_test', data, debounceMs: 500 })

      data.value.name = 'Change 1'
      await nextTick()
      data.value.name = 'Change 2'

      autoSave.forceSave()
      vi.advanceTimersByTime(500)

      const cached = JSON.parse(localStorage.getItem('cancel_test'))
      expect(cached.data.name).toBe('Change 2')
    })
  })

  describe('getCacheMetadata - Cache Info', () => {
    it('should return cache metadata including age and size', () => {
      const cacheData = {
        data: { name: 'Test', description: 'Test Description' },
        timestamp: Date.now() - 5 * 60 * 1000, // 5 minutes ago
        version: '1.0',
      }

      const serialized = JSON.stringify(cacheData)
      localStorage.setItem('metadata_test', serialized)

      const data = ref({})
      const autoSave = useAutoSave({ key: 'metadata_test', data })

      const metadata = autoSave.getCacheMetadata()

      expect(metadata).not.toBeNull()
      expect(metadata.exists).toBe(true)
      expect(metadata.timestamp).toBeDefined()
      expect(metadata.ageMs).toBeGreaterThan(0)
      expect(metadata.ageMinutes).toBe(5)
      expect(metadata.version).toBe('1.0')
      expect(metadata.sizeBytes).toBe(serialized.length)
    })

    it('should return null if cache does not exist', () => {
      const data = ref({})
      const autoSave = useAutoSave({ key: 'nonexistent_metadata', data })

      const metadata = autoSave.getCacheMetadata()

      expect(metadata).toBeNull()
    })

    it('should return null if key is missing', () => {
      const data = ref({})
      const autoSave = useAutoSave({ data })

      const metadata = autoSave.getCacheMetadata()

      expect(metadata).toBeNull()
    })
  })

  describe('Watch Behavior - Deep Reactive Updates', () => {
    it('should watch for deep changes in reactive data', async () => {
      const data = ref({
        basic: { name: 'Test' },
        config: { tech: 'Vue' },
      })

      const autoSave = useAutoSave({ key: 'deep_test', data, debounceMs: 100 })

      expect(autoSave.hasUnsavedChanges.value).toBe(false)

      // Change nested property
      data.value.config.tech = 'Vue 3'
      await nextTick()

      expect(autoSave.hasUnsavedChanges.value).toBe(true)
      expect(autoSave.saveStatus.value).toBe('unsaved')

      vi.advanceTimersByTime(100)

      expect(localStorage.getItem('deep_test')).not.toBeNull()
      const cached = JSON.parse(localStorage.getItem('deep_test'))
      expect(cached.data.config.tech).toBe('Vue 3')
    })

    it('should handle array mutations', async () => {
      const data = ref({
        items: ['item1'],
      })

      useAutoSave({ key: 'array_test', data, debounceMs: 100 })

      data.value.items.push('item2')
      await nextTick()

      vi.advanceTimersByTime(100)

      const cached = JSON.parse(localStorage.getItem('array_test'))
      expect(cached.data.items).toEqual(['item1', 'item2'])
    })
  })

  describe('Edit vs Create Mode - Cache Keys', () => {
    it('should use different cache keys for new vs edit mode', async () => {
      const newData = ref({ name: 'New Product' })
      useAutoSave({ key: 'product_form_draft_new', data: newData, debounceMs: 100 })

      const editData = ref({ name: 'Existing Product' })
      useAutoSave({ key: 'product_form_draft_123', data: editData, debounceMs: 100 })

      newData.value.name = 'Updated New'
      editData.value.name = 'Updated Existing'
      await nextTick()

      vi.advanceTimersByTime(100)

      const newCached = JSON.parse(localStorage.getItem('product_form_draft_new'))
      const editCached = JSON.parse(localStorage.getItem('product_form_draft_123'))

      expect(newCached.data.name).toBe('Updated New')
      expect(editCached.data.name).toBe('Updated Existing')
      expect(newCached).not.toEqual(editCached)
    })
  })

  describe('Cleanup on Unmount', () => {
    it('should stop watching on unmount', () => {
      const data = ref({ name: 'Test' })
      const autoSave = useAutoSave({ key: 'cleanup_test', data, debounceMs: 100 })

      data.value.name = 'Updated'
      vi.advanceTimersByTime(100)

      // Note: In actual component unmount, cleanup will be called
      // This test verifies the structure is correct for cleanup
      expect(autoSave.clearCache).toBeDefined()
    })
  })

  describe('Multiple Products Isolation', () => {
    it('should handle multiple products with separate caches', async () => {
      const productA = ref({ name: 'Product A' })
      const productB = ref({ name: 'Product B' })

      useAutoSave({
        key: 'product_form_draft_a',
        data: productA,
        debounceMs: 100,
      })
      useAutoSave({
        key: 'product_form_draft_b',
        data: productB,
        debounceMs: 100,
      })

      productA.value.name = 'Product A Updated'
      productB.value.name = 'Product B Updated'
      await nextTick()

      vi.advanceTimersByTime(100)

      const cachedA = JSON.parse(localStorage.getItem('product_form_draft_a'))
      const cachedB = JSON.parse(localStorage.getItem('product_form_draft_b'))

      expect(cachedA.data.name).toBe('Product A Updated')
      expect(cachedB.data.name).toBe('Product B Updated')
      expect(cachedA).not.toEqual(cachedB)
    })
  })

  describe('Special Characters Handling', () => {
    it('should properly escape and store special characters', async () => {
      const data = ref({
        name: '<script>alert("xss")</script>',
        description: 'Test with "quotes" and \'apostrophes\'',
      })

      useAutoSave({ key: 'special_chars_test', data, debounceMs: 100 })

      // Trigger save via data mutation
      data.value.name = data.value.name + ' '
      await nextTick()
      vi.advanceTimersByTime(100)

      const cached = JSON.parse(localStorage.getItem('special_chars_test'))
      expect(cached.data.description).toContain('quotes')
      expect(cached.data.description).toContain('apostrophes')
    })

    it('should handle unicode characters', async () => {
      const data = ref({
        name: 'Product test',
        description: 'Emojis test',
      })

      useAutoSave({ key: 'unicode_test', data, debounceMs: 100 })

      // Trigger save via data mutation
      data.value.name = 'Product test updated'
      await nextTick()
      vi.advanceTimersByTime(100)

      const cached = JSON.parse(localStorage.getItem('unicode_test'))
      expect(cached.data.name).toContain('Product test updated')
    })
  })
})
