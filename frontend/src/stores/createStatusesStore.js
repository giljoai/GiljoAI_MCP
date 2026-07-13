/**
 * createStatusesStore — Pinia store factory shared by `projectStatusesStore`
 * and `taskStatusesStore` (dup-8).
 *
 * Both stores mirror a backend status enum (`ProjectStatus` / `TaskStatus`)
 * by fetching a `GET .../statuses/` list endpoint exactly once per session
 * and caching it. Consumers read `validValues`, `getMeta(value)`, or
 * `isValid(value)` instead of embedding their own status list.
 *
 * Boot pattern: call `ensureLoaded()` from DefaultLayout.onMounted after the
 * user is authenticated. Calls are coalesced — multiple components may call
 * `ensureLoaded()` concurrently and only one HTTP request is issued.
 *
 * @param {string} storeId - Pinia store id (e.g. 'projectStatuses').
 * @param {() => Promise<{data: unknown}>} fetchStatuses - API call returning
 *   the status list response (e.g. `() => api.projectStatuses.list()`).
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export function createStatusesStore(storeId, fetchStatuses) {
  return defineStore(storeId, () => {
    const statuses = ref([])
    const loaded = ref(false)
    const loading = ref(false)

    // In-flight promise so concurrent ensureLoaded() callers share one request.
    let inFlight = null

    const validValues = computed(() => statuses.value.map((s) => s.value))

    // O(1) lookup by value. Recomputed whenever statuses change.
    const metaByValue = computed(() => {
      const map = new Map()
      for (const s of statuses.value) {
        map.set(s.value, s)
      }
      return map
    })

    /**
     * Return the metadata object for a status value, or undefined if not in
     * the canonical set. Callers should treat undefined as "render a
     * fallback / muted badge" rather than "throw" — orphan values may
     * surface from stale WebSocket events during a deploy window.
     */
    function getMeta(value) {
      return metaByValue.value.get(value)
    }

    /**
     * Membership test against the canonical enum. Returns false for
     * undefined / null / empty / unknown values.
     */
    function isValid(value) {
      if (!value) return false
      return metaByValue.value.has(value)
    }

    /**
     * Fetch and cache the canonical status metadata. Idempotent: the second
     * and subsequent calls resolve immediately from cache. Concurrent
     * callers share a single in-flight HTTP request.
     */
    async function ensureLoaded() {
      if (loaded.value) return
      if (inFlight) return inFlight

      loading.value = true
      inFlight = (async () => {
        try {
          const response = await fetchStatuses()
          // Defensive: API contract says array; if backend returns malformed
          // payload we leave the cache empty and let the next call retry.
          const data = Array.isArray(response?.data) ? response.data : []
          statuses.value = data
          loaded.value = true
        } finally {
          loading.value = false
          inFlight = null
        }
      })()

      return inFlight
    }

    /**
     * Clear the cache so the next `ensureLoaded()` call refetches. Mainly
     * useful for tests; production code does not need to reset.
     */
    function reset() {
      statuses.value = []
      loaded.value = false
      loading.value = false
      inFlight = null
    }

    return {
      // state
      statuses,
      loaded,
      loading,
      // getters
      validValues,
      // actions
      ensureLoaded,
      getMeta,
      isValid,
      reset,
    }
  })
}
