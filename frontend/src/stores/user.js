/**
 * User Store - Authentication and Role Management
 * Manages user authentication state and role-based access control
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useUserStore = defineStore('user', () => {
  // State
  const currentUser = ref(null)
  const isLoading = ref(false)

  // Getters
  const isAuthenticated = computed(() => currentUser.value !== null)

  const isAdmin = computed(() => {
    if (!currentUser.value || !currentUser.value.role) {
      return false
    }
    return currentUser.value.role.toLowerCase() === 'admin'
  })

  // Actions
  async function fetchCurrentUser() {
    isLoading.value = true
    try {
      const response = await api.auth.me()
      currentUser.value = response.data
      return true
    } catch (error) {
      console.error('[UserStore] Failed to fetch current user:', error)
      currentUser.value = null
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function login(username, password) {
    isLoading.value = true
    try {
      await api.auth.login(username, password)
      // After successful login, fetch the user data
      await fetchCurrentUser()
      return true
    } catch (error) {
      console.error('[UserStore] Login failed:', error)
      currentUser.value = null
      return false
    } finally {
      isLoading.value = false
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
      isLoading.value = false
      
      // Clear remember me data
      localStorage.removeItem('remembered_username')
    }
  }

  async function checkAuth() {
    isLoading.value = true
    try {
      const response = await api.auth.me()
      currentUser.value = response.data
      return true
    } catch (error) {
      console.error('[UserStore] Auth check failed:', error)
      currentUser.value = null

      // v3.0 Unified: Always require valid authentication
      // No localhost bypass - unified authentication for ALL IPs
      return false
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    currentUser,
    isLoading,
    // Getters
    isAuthenticated,
    isAdmin,
    // Actions
    fetchCurrentUser,
    login,
    logout,
    checkAuth,
  }
})
