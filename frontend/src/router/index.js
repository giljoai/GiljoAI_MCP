import { createRouter, createWebHistory } from 'vue-router'
import setupService from '@/services/setupService'
import configService from '@/services/configService'
import { useUserStore } from '@/stores/user'

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
    path: '/oauth/authorize',
    name: 'OAuthAuthorize',
    component: () => import('@/views/OAuthAuthorize.vue'),
    meta: {
      layout: 'auth',
      title: 'Authorize Application',
      showInNav: false,
      requiresAuth: false, // Page handles its own auth
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
    path: '/guide',
    name: 'UserGuide',
    component: () => import('@/views/UserGuideView.vue'),
    meta: {
      layout: 'default',
      title: 'User Guide',
      showInNav: false,
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

// SaaS routes are registered by frontend/src/saas/routes.js
// which calls router.addRoute() after config loads.
// CE router never imports from saas/ -- Deletion Test holds.

// Navigation guard (Handover 0034 - simplified fresh install detection)
// IMP-0011: demo/saas modes route fresh-install visitors to the public
// /demo-landing page (provided by saas/routes) instead of the CE
// CreateAdminAccount wizard. CE behavior is unchanged.
router.beforeEach(async (to, from, next) => {
  // Set page title
  document.title = `${to.meta.title || 'GiljoAI'} - GiljoAI MCP`

  // Fetch setupState ONCE at guard entry — single source of truth for both
  // mode resolution and route_signal. setupService caches with a 2s TTL so
  // subsequent reads in the same navigation are free.
  //
  // Why setupState is authoritative for `mode`: configService.getGiljoMode()
  // depends on an async fetch of /api/v1/config/frontend that may not have
  // resolved by the time this guard fires on first paint, in which case it
  // returns the 'ce' default. /api/setup/status returns `mode` synchronously
  // alongside route_signal — using it removes the race that previously caused
  // demo deployments to fall through to the CE branch and block /welcome.
  let setupState = null
  try {
    setupState = await setupService.checkEnhancedStatus()
  } catch {
    // Network error — proceed with configService fallback below
  }

  const mode = (() => {
    if (setupState?.mode) return setupState.mode
    try { return configService.getGiljoMode() } catch { return 'ce' }
  })()
  const isPublicLandingMode = mode !== 'ce'

  // PRIORITY 1: Fresh install / landing detection
  // Skip for the landing targets themselves and for /login to avoid loops.
  if (
    setupState &&
    to.path !== '/welcome' &&
    to.path !== '/login' &&
    to.path !== '/demo-landing' &&
    to.path !== '/register' &&
    to.path !== '/reset-password'
  ) {
    // Backend emits route_signal ∈ {'create_admin', 'login', 'public_landing'}
    // in addition to the legacy is_fresh_install/show_public_landing booleans.
    // Prefer route_signal when present; fall back to booleans + mode.
    //
    // IMPORTANT: `public_landing` is the signal for anonymous first-paint on
    // demo/saas deployments -- it routes unauthenticated visitors to the
    // marketing landing. It must NOT apply to authenticated users, otherwise
    // every post-login navigation bounces back to /demo-landing (see loop
    // reported 2026-04-22 on the demo server).
    const signal = setupState.route_signal
    const userStoreEarly = useUserStore()
    const isAuthenticated = !!userStoreEarly.currentUser
    if (signal === 'public_landing' && !isAuthenticated) {
      next('/demo-landing')
      return
    }
    if (signal === 'create_admin') {
      next('/welcome')
      return
    }
    // Legacy / belt-and-suspenders path (no route_signal yet or transient error).
    // In demo/saas we NEVER want the CreateAdminAccount wizard to be visible.
    if (
      isPublicLandingMode &&
      !isAuthenticated &&
      (setupState.show_public_landing || setupState.is_fresh_install)
    ) {
      next('/demo-landing')
      return
    }

    if (!isPublicLandingMode && setupState.is_fresh_install) {
      // CE fresh install (0 users) - redirect to create admin account
      next('/welcome')
      return
    }
  }

  // PRIORITY 2: Auth routes (layout: 'auth') - allow access without authentication
  if (to.meta.layout === 'auth') {
    // Security check: Block /welcome if users exist OR if we're in demo/saas mode
    // (demo/saas must never expose the admin-bootstrap UI publicly).
    if (to.path === '/welcome') {
      if (isPublicLandingMode) {
        console.warn('[SECURITY] Blocking /welcome in demo/saas mode - admin bootstrap is CLI-only')
        next('/demo-landing')
        return
      }
      // CE: block /welcome only when users genuinely exist. Defense-in-depth:
      // require BOTH !is_fresh_install AND total_users_count > 0 so the legacy
      // 'is_fresh_install: false in demo mode means no users' bug can never
      // resurface (the demo case is handled above by isPublicLandingMode).
      if (setupState && !setupState.is_fresh_install && (setupState.total_users_count ?? 0) > 0) {
        console.warn(
          '[SECURITY] Blocking /welcome access - users exist (total:',
          setupState.total_users_count,
          ')',
        )
        next('/login')
        return
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
      // Use store's fetchCurrentUser to ensure org fields (orgRole, etc.) are set
      if (!userStore.currentUser) {
        const success = await userStore.fetchCurrentUser()
        if (!success) throw new Error('Auth check failed')
      }
    } catch {
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
