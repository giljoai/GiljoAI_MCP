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

  // Actions
  async function fetchCurrentUser() {
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
      // Always clear local state
      currentUser.value = null
      clearOrgFields()

      // Clear tenant key from API client
      setTenantKey(null)

      // Clear remember me data
      localStorage.removeItem('remembered_username')

      // Clear notifications on logout (tenant isolation defense-in-depth)
      const { useNotificationStore } = await import('@/stores/notifications')
      useNotificationStore().clearAll()
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
    clearUser,
  }
})
