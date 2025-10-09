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

// Navigation guard for page titles, authentication, setup check, and role-based access
router.beforeEach(async (to, from, next) => {
  // Set page title
  document.title = `${to.meta.title || 'GiljoAI'} - MCP Orchestrator`

  // Skip all checks for routes that explicitly don't require them
  if (to.meta.requiresSetup === false && to.meta.requiresAuth === false) {
    next()
    return
  }

  // Get user store for role checking
  const userStore = useUserStore()

  // Check authentication (unless explicitly disabled)
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

  // Check if setup is complete (for authenticated routes)
  if (to.meta.requiresSetup !== false) {
    try {
      const status = await setupService.checkStatus()

      if (!status.completed && to.path !== '/setup') {
        // Setup not complete, redirect to wizard
        console.log('Setup not completed, redirecting to setup wizard')
        next('/setup')
        return
      }
    } catch (error) {
      // If setup status check fails (endpoint doesn't exist yet),
      // continue anyway to avoid blocking navigation
      console.log('Setup status check unavailable, continuing with navigation')
    }
  }

  // All checks passed, allow navigation
  next()
})

export default router
