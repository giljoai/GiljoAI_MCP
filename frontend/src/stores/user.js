/**
 * User Store - Authentication and Role Management
 * Manages user authentication state and role-based access control
 * Includes organization context (Handover 0424h)
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { setTenantKey } from '@/services/api'

export const useUserStore = defineStore('user', () => {
  // State
  const currentUser = ref(null)

  // Org state (Handover 0424h)
  const orgId = ref(null)
  const orgName = ref(null)
  const orgRole = ref(null)

  // Getters
  const isAuthenticated = computed(() => currentUser.value !== null)

  const isAdmin = computed(() => {
    if (!currentUser.value || !currentUser.value.role) {
      return false
    }
    return currentUser.value.role.toLowerCase() === 'admin'
  })

  // Organization computed properties (Handover 0424h)
  const currentOrg = computed(() => {
    if (!orgId.value) return null
    return {
      id: orgId.value,
      name: orgName.value,
      role: orgRole.value
    }
  })

  // Deduplicates concurrent fetchCurrentUser() calls (single in-flight request)
  let _fetchPending = null

  // Actions
  async function fetchCurrentUser() {
    if (_fetchPending) return _fetchPending
    _fetchPending = _doFetchCurrentUser()
    try {
      return await _fetchPending
    } finally {
      _fetchPending = null
    }
  }

  async function _doFetchCurrentUser() {
    try {
      const response = await api.auth.me()
      currentUser.value = response.data

      // Store org fields from API response (Handover 0424h)
      orgId.value = response.data?.org_id || null
      orgName.value = response.data?.org_name || null
      orgRole.value = response.data?.org_role || null

      // Update API client tenant key after successful auth
      if (currentUser.value?.tenant_key) {
        setTenantKey(currentUser.value.tenant_key)
      }

      return true
    } catch (error) {
      console.error('[UserStore] Failed to fetch current user:', error)
      currentUser.value = null
      clearOrgFields()
      return false
    }
  }

  async function login(username, password) {
    try {
      await api.auth.login(username, password)
      // After successful login, fetch the user data
      await fetchCurrentUser()
      return true
    } catch (error) {
      console.error('[UserStore] Login failed:', error)
      currentUser.value = null
      clearOrgFields()
      return false
    }
  }

  async function logout() {
    try {
      await api.auth.logout()
    } catch (error) {
      console.error('[UserStore] Logout endpoint failed:', error)
      // Continue with local cleanup even if API call fails
    } finally {
      // Always clear local auth state -- every field the router guard or any
      // view could read must be reset so a post-logout navigation cannot
      // render a protected view from stale Pinia state (regression: demo
      // server 2026-04-24, route-guard-bypass leak).
      currentUser.value = null
      clearOrgFields()

      // Cancel any in-flight fetchCurrentUser() dedupe token so the next
      // navigation fires a fresh /api/auth/me against the now-invalid cookie.
      _fetchPending = null

      // Clear tenant key from API client so subsequent pre-auth requests
      // (e.g. /api/setup/status) don't reuse the logged-out user's header.
      setTenantKey(null)

      // Clear remember me data
      try {
        localStorage.removeItem('remembered_username')
      } catch {
        // localStorage may be unavailable in restricted environments
      }

      // Clear dependent stores on logout (tenant isolation defense-in-depth).
      // Wrap dynamic imports in try/catch so a bundler or test-env failure
      // here can never prevent the auth state above from being cleared.
      try {
        const { useWebSocketStore } = await import('@/stores/websocket')
        useWebSocketStore().disconnect()
      } catch (e) {
        console.warn('[UserStore] WebSocket disconnect skipped:', e)
      }
      try {
        const { useNotificationStore } = await import('@/stores/notifications')
        useNotificationStore().clearAll()
      } catch (e) {
        console.warn('[UserStore] Notification store cleanup skipped:', e)
      }
      try {
        const { useProductStore } = await import('@/stores/products')
        useProductStore().clearProductData()
      } catch (e) {
        console.warn('[UserStore] Product store cleanup skipped:', e)
      }
      try {
        const { useTaskStore } = await import('@/stores/tasks')
        useTaskStore().tasks = []
      } catch (e) {
        console.warn('[UserStore] Task store cleanup skipped:', e)
      }
    }
  }

  async function checkAuth() {
    try {
      const response = await api.auth.me()
      currentUser.value = response.data

      // Store org fields from API response (Handover 0424h)
      orgId.value = response.data?.org_id || null
      orgName.value = response.data?.org_name || null
      orgRole.value = response.data?.org_role || null

      // Update API client tenant key after successful auth
      if (currentUser.value?.tenant_key) {
        setTenantKey(currentUser.value.tenant_key)
      }

      return true
    } catch (error) {
      console.error('[UserStore] Auth check failed:', error)
      currentUser.value = null
      clearOrgFields()

      // v3.0 Unified: Always require valid authentication
      // No localhost bypass - unified authentication for ALL IPs
      return false
    }
  }

  // Helper method to clear org fields (Handover 0424h)
  function clearOrgFields() {
    orgId.value = null
    orgName.value = null
    orgRole.value = null
  }

  // Update setup wizard state (Handover 0855c)
  async function updateSetupState(payload) {
    const response = await api.auth.updateSetupState(payload)
    const data = response.data
    if (currentUser.value) {
      if (data.setup_complete !== undefined) currentUser.value.setup_complete = data.setup_complete
      if (data.setup_selected_tools !== undefined) currentUser.value.setup_selected_tools = data.setup_selected_tools
      if (data.setup_step_completed !== undefined) currentUser.value.setup_step_completed = data.setup_step_completed
      if (data.learning_complete !== undefined) currentUser.value.learning_complete = data.learning_complete
    }
    return data
  }

  // Clear all user and org state (Handover 0424h)
  function clearUser() {
    currentUser.value = null
    clearOrgFields()
  }

  return {
    // State
    currentUser,
    // Org state (Handover 0424h)
    orgId,
    orgName,
    orgRole,
    // Getters
    isAuthenticated,
    isAdmin,
    // Org computed properties (Handover 0424h)
    currentOrg,
    // Actions
    fetchCurrentUser,
    login,
    logout,
    checkAuth,
    updateSetupState,
    clearUser,
  }
})
