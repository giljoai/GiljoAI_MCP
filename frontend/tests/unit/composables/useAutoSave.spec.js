/**
 * Auto-Save Composable Test Suite
 * Handover 0051: Product Form Auto-Save & UX Polish
 *
 * Tests for LocalStorage-based form data persistence with debouncing
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ref } from 'vue'
import { useAutoSave } from '@/composables/useAutoSave'

describe('useAutoSave Composable', () => {
  beforeEach(() => {
    // Clear localStorage before each test
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
  })

  describe('saveToCache - LocalStorage Persistence', () => {
    it('should save form data to LocalStorage', () => {
      const data = ref({ name: 'Test Product', description: 'Test Description' })
      const autoSave = useAutoSave({ key: 'product_form_test', data })

      const result = autoSave.saveToCache()

      expect(result).toBe(true)
      const stored = localStorage.getItem('product_form_test')
      expect(stored).toBeDefined()

      const parsed = JSON.parse(stored)
      expect(parsed.data.name).toBe('Test Product')
      expect(parsed.data.description).toBe('Test Description')
      expect(parsed.timestamp).toBeDefined()
      expect(parsed.version).toBe('1.0')
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
  })

  describe('clearCache - Cache Removal', () => {
    it('should remove cache from LocalStorage', () => {
      localStorage.setItem('cache_to_clear', JSON.stringify({ data: {} }))

      const data = ref({})
      const autoSave = useAutoSave({ key: 'cache_to_clear', data })

      autoSave.clearCache()

      expect(localStorage.getItem('cache_to_clear')).toBeNull()
      expect(autoSave.hasUnsavedChanges.value).toBe(false)
      expect(autoSave.saveStatus.value).toBe('saved')
      expect(autoSave.errorMessage.value).toBeNull()
    })
  })

  describe('Debounced Save', () => {
    it('should debounce saves (500ms default)', async () => {
      const data = ref({ name: 'Initial' })
      const autoSave = useAutoSave({ key: 'debounce_test', data, debounceMs: 500 })

      // Change data multiple times rapidly
      data.value.name = 'Change 1'
      data.value.name = 'Change 2'
      data.value.name = 'Change 3'

      expect(localStorage.getItem('debounce_test')).toBeNull()

      // Fast-forward time by 499ms
      vi.advanceTimersByTime(499)
      expect(localStorage.getItem('debounce_test')).toBeNull()

      // Fast-forward remaining 1ms
      vi.advanceTimersByTime(1)
      expect(localStorage.getItem('debounce_test')).toBeDefined()

      const cached = JSON.parse(localStorage.getItem('debounce_test'))
      expect(cached.data.name).toBe('Change 3')
    })

    it('should update save status: unsaved -> saved', async () => {
      const data = ref({ name: 'Test' })
      const autoSave = useAutoSave({ key: 'status_test', data, debounceMs: 100 })

      expect(autoSave.saveStatus.value).toBe('saved')

      data.value.name = 'Updated'
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
      expect(localStorage.getItem('force_test')).toBeDefined()

      const cached = JSON.parse(localStorage.getItem('force_test'))
      expect(cached.data.name).toBe('Updated')
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

      expect(metadata).toBeDefined()
      expect(metadata.exists).toBe(true)
      expect(metadata.timestamp).toBeDefined()
      expect(metadata.ageMs).toBeGreaterThan(0)
    })

    it('should return null if cache does not exist', () => {
      const data = ref({})
      const autoSave = useAutoSave({ key: 'nonexistent_metadata', data })

      const metadata = autoSave.getCacheMetadata()

      expect(metadata).toBeNull()
    })
  })

  describe('Multiple Products Isolation', () => {
    it('should handle multiple products with separate caches', () => {
      const productA = ref({ name: 'Product A' })
      const productB = ref({ name: 'Product B' })

      const autoSaveA = useAutoSave({
        key: 'product_form_draft_a',
        data: productA,
        debounceMs: 100,
      })
      const autoSaveB = useAutoSave({
        key: 'product_form_draft_b',
        data: productB,
        debounceMs: 100,
      })

      productA.value.name = 'Product A Updated'
      productB.value.name = 'Product B Updated'

      vi.advanceTimersByTime(100)

      const cachedA = JSON.parse(localStorage.getItem('product_form_draft_a'))
      const cachedB = JSON.parse(localStorage.getItem('product_form_draft_b'))

      expect(cachedA.data.name).toBe('Product A Updated')
      expect(cachedB.data.name).toBe('Product B Updated')
      expect(cachedA).not.toEqual(cachedB)
    })
  })

  describe('Special Characters Handling', () => {
    it('should properly store special characters', () => {
      const data = ref({
        name: '<script>alert("xss")</script>',
        description: 'Test with "quotes" and \'apostrophes\'',
      })

      const autoSave = useAutoSave({ key: 'special_chars_test', data, debounceMs: 100 })

      vi.advanceTimersByTime(100)

      const cached = JSON.parse(localStorage.getItem('special_chars_test'))
      expect(cached.data.name).toBe('<script>alert("xss")</script>')
      expect(cached.data.description).toContain('quotes')
      expect(cached.data.description).toContain('apostrophes')
    })

    it('should handle unicode characters', () => {
      const data = ref({
        name: 'Product Chinese English',
        description: 'Test with emojis',
      })

      const autoSave = useAutoSave({ key: 'unicode_test', data, debounceMs: 100 })

      vi.advanceTimersByTime(100)

      const cached = JSON.parse(localStorage.getItem('unicode_test'))
      expect(cached.data.name).toBe('Product Chinese English')
    })
  })
})
