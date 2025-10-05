import { createRouter, createWebHistory } from 'vue-router'
import setupService from '@/services/setupService'

// Route definitions - views will be implemented after analyzer results
const routes = [
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
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: {
      title: 'Settings',
      icon: 'mdi-cog',
      showInNav: true,
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

// Navigation guard for page titles and setup check
router.beforeEach(async (to, from, next) => {
  // Set page title
  document.title = `${to.meta.title || 'GiljoAI'} - MCP Orchestrator`

  // Skip setup check for the setup route itself
  if (to.meta.requiresSetup === false) {
    next()
    return
  }

  // Check if setup is complete
  try {
    const status = await setupService.checkStatus()

    if (!status.completed && to.path !== '/setup') {
      // Setup not complete, redirect to wizard
      console.log('Setup not completed, redirecting to setup wizard')
      next('/setup')
    } else if (status.completed && to.path === '/setup') {
      // Setup already done, redirect to dashboard
      console.log('Setup already completed, redirecting to dashboard')
      next('/')
    } else {
      next()
    }
  } catch (error) {
    // If setup status check fails (endpoint doesn't exist yet),
    // continue anyway to avoid blocking navigation
    console.log('Setup status check unavailable, continuing with navigation')
    next()
  }
})

export default router
