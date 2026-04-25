import { createRouter, createWebHistory } from 'vue-router'
import setupService from '@/services/setupService'
import configService from '@/services/configService'
import { createAuthGuard } from '@/router/authGuard'

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
    path: '/tools',
    name: 'Tools',
    alias: '/settings', // back-compat: old bookmarks, deep links, and external docs keep resolving
    component: () => import('@/views/ToolsView.vue'),
    meta: {
      layout: 'default',
      title: 'Tools',
      icon: 'mdi-tools',
      showInNav: false,
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
  // Account shell with Profile / Billing / Danger sub-tabs (FE-0023).
  {
    path: '/account',
    component: () => import('@/views/account/AccountShell.vue'),
    meta: {
      layout: 'default',
      title: 'Account',
      showInNav: false,
      requiresAuth: true,
    },
    children: [
      {
        path: '',
        redirect: { name: 'AccountProfile' },
      },
      {
        path: 'profile',
        name: 'AccountProfile',
        component: () => import('@/views/account/ProfilePage.vue'),
        meta: { title: 'Account · Profile', requiresAuth: true },
      },
      {
        path: 'billing',
        name: 'AccountBilling',
        component: () => import('@/views/account/BillingPage.vue'),
        meta: { title: 'Account · Billing', requiresAuth: true },
      },
      {
        path: 'danger',
        name: 'AccountDanger',
        component: () => import('@/views/account/DangerPage.vue'),
        meta: { title: 'Account · Danger Zone', requiresAuth: true },
      },
    ],
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

// Navigation guard (Handover 0034 - simplified fresh install detection;
// hardened 2026-04-24 to close the route-guard-bypass leak observed on
// demo.giljo.ai where typing /home in the address bar after logout rendered
// the protected view. The full guard now lives in ./authGuard.js so it can
// be unit-tested in isolation -- see tests/unit/router/authGuard.spec.js).
//
// Option A: every navigation to a protected route re-verifies the session
// by calling /api/auth/me via userStore.checkAuth(). On auth failure the
// store is reset and the user is redirected to /login.
router.beforeEach(createAuthGuard({ setupService, configService }))

export default router
