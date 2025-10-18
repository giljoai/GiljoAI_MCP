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
    name: 'WelcomeSetup',
    component: () => import('@/views/WelcomeSetup.vue'),
    meta: {
      layout: 'auth',
      title: 'Welcome to GiljoAI MCP',
      showInNav: false,
      requiresAuth: false, // Public route - first-time setup
      requiresSetup: false, // Skip setup check for this route
      requiresPasswordChange: false, // Skip password change check for this route
    },
  },
  {
    path: '/',
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
    path: '/products',
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
    path: '/projects/:id',
    name: 'ProjectDetail',
    component: () => import('@/views/ProjectDetailView.vue'),
    meta: {
      layout: 'default',
      title: 'Project Details',
      showInNav: false,
    },
  },
  {
    path: '/agents',
    name: 'Agents',
    component: () => import('@/views/AgentsView.vue'),
    meta: {
      layout: 'default',
      title: 'Agent Monitoring',
      icon: 'mdi-robot',
      showInNav: true,
    },
  },
  {
    path: '/messages',
    name: 'Messages',
    component: () => import('@/views/MessagesView.vue'),
    meta: {
      layout: 'default',
      title: 'Message Center',
      icon: 'mdi-message-text',
      showInNav: true,
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
    path: '/api-keys',
    name: 'ApiKeys',
    component: () => import('@/views/ApiKeysView.vue'),
    meta: {
      layout: 'default',
      title: 'My API Keys',
      showInNav: false, // Now in profile menu
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
    path: '/users',
    name: 'Users',
    component: () => import('@/views/UsersView.vue'),
    meta: {
      layout: 'default',
      title: 'User Management',
      icon: 'mdi-account-multiple',
      showInNav: true,
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
  {
    path: '/settings/integrations',
    name: 'IntegrationsSettings',
    component: () => import('@/views/Settings/IntegrationsView.vue'),
    meta: {
      layout: 'default',
      title: 'API & Integrations',
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

// Navigation guard for page titles, authentication, setup check, password change check, and role-based access
router.beforeEach(async (to, from, next) => {
  // Set page title
  document.title = `${to.meta.title || 'GiljoAI'} - MCP Orchestrator`

  // FIRST: Check for factory default password (applies to ALL routes)
  // If default password is active, redirect to welcome screen BEFORE any other checks
  if (to.path !== '/welcome' && to.meta.requiresPasswordChange !== false) {
    try {
      const status = await setupService.checkStatus()
      if (status.default_password_active) {
        console.log('[ROUTER] Factory default password active, redirecting to welcome setup')
        next('/welcome')
        return
      }
    } catch (error) {
      // If setup status check fails, continue with normal flow
      console.log('[ROUTER] Setup status check failed (factory password check):', error.message)
    }
  }

  // Auth routes (layout: 'auth') - allow access without authentication
  if (to.meta.layout === 'auth') {
    // Still need to check setup flow for auth routes
    if (to.meta.requiresSetup !== false) {
      try {
        const status = await setupService.checkStatus()

        // Check for default password requirement
        if (to.meta.requiresPasswordChange !== false && status.default_password_active) {
          if (to.path !== '/welcome') {
            console.log('[ROUTER] Default password active, redirecting to welcome setup')
            next('/welcome')
            return
          }
        }

        // If password changed but database not initialized, redirect to login
        if (!status.default_password_active && !status.database_initialized) {
          console.log('[ROUTER] Database not initialized, redirecting to login')
          next('/login')
          return
        }
      } catch (error) {
        // Network error during setup check
        const hasCompletedSetup = localStorage.getItem('setup_completed') === 'true'
        const hasAuthCookie = document.cookie.includes('access_token')

        console.log('[ROUTER] Setup status check failed:', {
          hasCompletedSetup,
          hasAuthCookie,
          targetPath: to.path,
          errorType: error.message
        })

        // If existing installation, show server down page
        if (hasCompletedSetup || hasAuthCookie) {
          if (to.path !== '/server-down') {
            console.log('[ROUTER] Existing installation detected - server unreachable, redirecting to error page')
            next('/server-down')
            return
          }
        } else {
          // Fresh install - allow navigation to welcome/login/server-down
          if (to.path !== '/welcome' && to.path !== '/login' && to.path !== '/server-down') {
            console.log('[ROUTER] Fresh install detected - redirecting to welcome setup')
            next('/welcome')
            return
          }
        }
      }
    }

    // Allow access to auth routes
    next()
    return
  }

  // App routes (layout: 'default') - check authentication
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
      console.log('[ROUTER] User not authenticated, redirecting to login')
      next({
        path: '/login',
        query: { redirect: to.fullPath },
      })
      return
    }
  }

  // Check admin role requirement
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    console.log('[ROUTER] Admin access required, redirecting to dashboard')
    next({ name: 'Dashboard' })
    return
  }

  // All checks passed, allow navigation
  next()
})

export default router
