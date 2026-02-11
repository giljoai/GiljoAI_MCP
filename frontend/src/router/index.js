import { createRouter, createWebHistory } from 'vue-router'
import setupService from '@/services/setupService'
import { useUserStore } from '@/stores/user'
import api from '@/services/api'

// Route definitions - views will be implemented after analyzer results
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      layout: 'auth',
      title: 'Login',
      showInNav: false,
      requiresAuth: false, // Public route, no auth required
      requiresSetup: false, // Skip setup check for this route
      requiresPasswordChange: false, // Skip password change check for this route
    },
  },
  {
    path: '/welcome',
    name: 'CreateAdminAccount',
    component: () => import('@/views/CreateAdminAccount.vue'),
    meta: {
      layout: 'auth',
      title: 'Create Administrator Account',
      showInNav: false,
      requiresAuth: false, // Public route - fresh install only
      requiresSetup: false, // Skip setup check for this route
    },
  },
  {
    path: '/first-login',
    name: 'FirstLogin',
    component: () => import('@/views/FirstLogin.vue'),
    meta: {
      layout: 'auth',
      title: 'Complete Account Setup',
      showInNav: false,
      requiresAuth: true, // Requires authentication
      requiresSetup: false, // Skip setup check for this route
      requiresPasswordChange: false, // Skip password change check (this IS the password change page)
    },
  },
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/WelcomeView.vue'),
    meta: {
      layout: 'default',
      title: 'Home',
      icon: 'mdi-home',
      showInNav: true,
      requiresAuth: true,
    },
  },
  {
    path: '/Dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: {
      layout: 'default',
      title: 'Dashboard',
      icon: 'mdi-view-dashboard',
      showInNav: true,
    },
  },
  {
    path: '/Products',
    name: 'Products',
    component: () => import('@/views/ProductsView.vue'),
    meta: {
      layout: 'default',
      title: 'Products',
      icon: 'mdi-package-variant',
      showInNav: true,
    },
  },
  {
    path: '/products/:id',
    name: 'ProductDetail',
    component: () => import('@/views/ProductDetailView.vue'),
    meta: {
      layout: 'default',
      title: 'Product Details',
      showInNav: false,
    },
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('@/views/ProjectsView.vue'),
    meta: {
      layout: 'default',
      title: 'Project Management',
      icon: 'mdi-folder-multiple',
      showInNav: true,
    },
  },
  {
    path: '/launch',
    name: 'Launch',
    component: () => import('@/views/LaunchRedirectView.vue'),
    meta: {
      layout: 'default',
      title: 'Launch',
      showInNav: false,
      requiresAuth: true,
    },
  },
  {
    path: '/projects/:projectId',
    name: 'ProjectLaunch',
    component: () => import('@/views/ProjectLaunchView.vue'),
    meta: {
      layout: 'default',
      title: 'Project Launch',
      showInNav: false,
      requiresAuth: true,
    },
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/TasksView.vue'),
    meta: {
      layout: 'default',
      title: 'Task Management',
      icon: 'mdi-clipboard-check',
      showInNav: true,
    },
  },
  {
    path: '/messages',
    name: 'Messages',
    component: () => import('@/views/MessagesView.vue'),
    meta: {
      layout: 'default',
      title: 'Messages',
      icon: 'mdi-message-text',
      showInNav: true,
      requiresAuth: true,
    },
  },
  {
    path: '/settings',
    name: 'UserSettings',
    component: () => import('@/views/UserSettings.vue'),
    meta: {
      layout: 'default',
      title: 'My Settings',
      icon: 'mdi-cog',
      showInNav: false, // Now in profile menu, not main nav
      requiresAuth: true,
    },
  },
  {
    path: '/admin/settings',
    name: 'SystemSettings',
    component: () => import('@/views/SystemSettings.vue'),
    meta: {
      layout: 'default',
      title: 'System Settings',
      icon: 'mdi-cog-outline',
      showInNav: true, // Show in main nav for admins
      requiresAuth: true,
      requiresAdmin: true,
    },
  },
  {
    path: '/admin/users',
    name: 'Users',
    component: () => import('@/views/Users.vue'),
    meta: {
      layout: 'default',
      title: 'User Management',
      icon: 'mdi-account-multiple',
      showInNav: false, // Accessible via avatar dropdown, not main nav
      requiresAuth: true,
      requiresAdmin: true,
    },
  },
  {
    path: '/admin/mcp-integration',
    name: 'McpIntegration',
    component: () => import('@/views/McpIntegration.vue'),
    meta: {
      layout: 'default',
      title: 'MCP Integration',
      icon: 'mdi-connection',
      showInNav: true,
      requiresAuth: true,
      requiresAdmin: true,
    },
  },
  // Organization Routes (Handover 0424d)
  {
    path: '/organizations/:orgId/settings',
    name: 'OrganizationSettings',
    component: () => import('@/views/OrganizationSettings.vue'),
    meta: {
      layout: 'default',
      title: 'Organization Settings',
      icon: 'mdi-office-building',
      showInNav: false,
      requiresAuth: true,
    },
  },
  {
    path: '/server-down',
    name: 'ServerDown',
    component: () => import('@/views/ServerDownView.vue'),
    meta: {
      layout: 'auth',
      title: 'Server Unreachable',
      showInNav: false,
      requiresAuth: false,
      requiresSetup: false,
      requiresPasswordChange: false,
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: {
      layout: 'default',
      title: '404 Not Found',
      showInNav: false,
    },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// Navigation guard (Handover 0034 - simplified fresh install detection)
router.beforeEach(async (to, from, next) => {
  // Set page title
  document.title = `${to.meta.title || 'GiljoAI'} - MCP Orchestrator`

  // PRIORITY 1: Fresh install detection (check BEFORE auth for all routes except /welcome)
  if (to.path !== '/welcome' && to.path !== '/login') {
    try {
      const setupState = await setupService.checkEnhancedStatus()

      if (setupState.is_fresh_install) {
        // Fresh install (0 users) - redirect to create admin account
        next('/welcome')
        return
      }
    } catch (error) {
      // Network error - continue (will fail at auth check if needed)
    }
  }

  // PRIORITY 2: Auth routes (layout: 'auth') - allow access without authentication
  if (to.meta.layout === 'auth') {
    // Security check: Block /welcome if users exist (attack prevention)
    if (to.path === '/welcome') {
      try {
        const setupState = await setupService.checkEnhancedStatus()
        if (!setupState.is_fresh_install) {
          // Users exist - block welcome page access
          console.warn(
            '[SECURITY] Blocking /welcome access - users exist (total:',
            setupState.total_users_count,
            ')',
          )
          next('/login')
          return
        }
      } catch (error) {
        // On error, allow access (conservative for fresh installs)
      }
    }

    // Allow access to auth routes
    next()
    return
  }

  // PRIORITY 3: App routes (layout: 'default') - check authentication
  const userStore = useUserStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth) {
    try {
      // Use API client to get current user
      const response = await api.auth.me()
      const userData = response.data

      // Update user store if needed
      if (!userStore.currentUser) {
        userStore.currentUser = userData
      }
    } catch (error) {
      // Not authenticated, redirect to login
      next({
        path: '/login',
        query: { redirect: to.fullPath },
      })
      return
    }
  }

  // Check admin role requirement
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next({ name: 'Dashboard' })
    return
  }

  // All checks passed, allow navigation
  next()
})

export default router
