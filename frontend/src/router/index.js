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
      title: 'Welcome to GiljoAI MCP',
      showInNav: false,
      requiresAuth: false, // Public route - first-time setup
      requiresSetup: false, // Skip setup check for this route
      requiresPasswordChange: false, // Skip password change check for this route
    },
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('@/views/ChangePassword.vue'),
    meta: {
      title: 'Change Default Password',
      showInNav: false,
      requiresAuth: false, // Allow access without auth - first-time setup
      requiresSetup: false, // Skip setup check for this route
      requiresPasswordChange: false, // Skip password change check for this route
    },
  },
  {
    path: '/setup',
    name: 'Setup',
    component: () => import('@/views/SetupWizard.vue'),
    meta: {
      title: 'Setup Wizard',
      showInNav: false,
      requiresSetup: false, // Skip setup check for this route
      requiresAuth: true, // PHASE 2: Requires authentication - user must login first
      requiresPasswordChange: false, // Skip password change check for this route
    },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: {
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
      title: 'Product Details',
      showInNav: false,
    },
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('@/views/ProjectsView.vue'),
    meta: {
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
      title: 'Project Details',
      showInNav: false,
    },
  },
  {
    path: '/agents',
    name: 'Agents',
    component: () => import('@/views/AgentsView.vue'),
    meta: {
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
      title: 'API & Integrations',
      showInNav: false,
      requiresAuth: true,
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: {
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

  // Skip all checks for routes that explicitly don't require them
  if (to.meta.requiresSetup === false && to.meta.requiresAuth === false && to.meta.requiresPasswordChange === false) {
    next()
    return
  }

  // CRITICAL: Check setup status and password requirements
  // Priority order: Password Change → Setup Wizard → Normal Auth
  if (to.meta.requiresSetup !== false) {
    try {
      const status = await setupService.checkStatus()

      // HIGHEST PRIORITY: Check for default password requirement FIRST
      // This ensures password change happens before setup wizard
      if (to.meta.requiresPasswordChange !== false && status.default_password_active) {
        if (to.path !== '/change-password') {
          console.log('[ROUTER] Default password active, redirecting to welcome setup')
          next('/welcome')
          return
        }
      }

      // SECOND PRIORITY: If password has been changed, check database initialization
      if (!status.default_password_active && !status.database_initialized && to.path !== '/setup') {
        // Password changed but database not initialized, redirect to wizard
        console.log('[ROUTER] Database not initialized, redirecting to setup wizard')
        next('/setup')
        return
      }

      // If password has been changed and user is on change-password page, redirect to setup or dashboard
      if (to.path === '/change-password' && !status.default_password_active) {
        if (!status.database_initialized) {
          console.log('[ROUTER] Password changed, redirecting to setup wizard')
          next('/setup')
        } else {
          console.log('[ROUTER] Password already changed and database initialized, redirecting to dashboard')
          next('/')
        }
        return
      }

      // If on setup wizard but default password still active, redirect to password change
      if (to.path === '/setup' && status.default_password_active) {
        console.log('[ROUTER] Must change password before setup, redirecting to welcome setup')
        next('/welcome')
        return
      }

    } catch (error) {
      // SECURITY FAIL-SAFE: If setup status check fails (pristine database, API unreachable),
      // redirect to password change modal instead of setup wizard
      // This ensures we ALWAYS require password change on fresh install, even if status check fails
      if (to.path !== '/setup' && to.path !== '/login' && to.path !== '/welcome') {
        console.log('[ROUTER] Setup status check failed - assuming fresh install, redirecting to welcome setup (FAIL-SAFE)')
        next('/welcome')
        return
      }
      // If already navigating to setup, login, or welcome, allow it
      console.log('[ROUTER] Setup status check unavailable, but navigating to', to.path)
    }
  }

  // Get user store for role checking
  const userStore = useUserStore()

  // Check authentication (AFTER setup check - only for routes that completed setup)
  const requiresAuth = to.meta.requiresAuth !== false
  if (requiresAuth) {
    try {
      // Use API client to get current user (includes Bearer token from localStorage)
      const response = await api.auth.me()

      // Get user data from response
      const userData = response.data

      // If we don't have user data in store, set it
      if (!userStore.currentUser) {
        userStore.currentUser = userData
      }
    } catch (error) {
      // Not authenticated or network error, redirect to login
      console.log('User not authenticated, redirecting to login')
      next({
        path: '/login',
        query: { redirect: to.fullPath },
      })
      return
    }
  }

  // Check admin role requirement
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    console.log('Admin access required, redirecting to dashboard')
    next({ name: 'Dashboard' })
    return
  }

  // All checks passed, allow navigation
  next()
})

export default router
