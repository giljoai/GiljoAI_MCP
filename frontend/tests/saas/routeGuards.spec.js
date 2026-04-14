import { describe, it, expect, beforeEach, vi } from 'vitest'

const { _mode } = vi.hoisted(() => ({ _mode: { value: 'ce' } }))

vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn(() => Promise.resolve()),
    getGiljoMode: vi.fn(() => _mode.value),
    config: { giljo_mode: _mode.value },
  },
}))

vi.mock('@/services/setupService', () => ({
  default: {
    checkEnhancedStatus: vi.fn(() => Promise.resolve({ is_fresh_install: false })),
  },
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: null,
    isAdmin: false,
    fetchCurrentUser: vi.fn(() => Promise.resolve(false)),
  }),
}))

import configService from '@/services/configService'

describe('SaaS route registration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _mode.value = 'ce'
    configService.fetchConfig.mockImplementation(() => Promise.resolve())
    configService.getGiljoMode.mockImplementation(() => _mode.value)
  })

  it('registerSaasRoutes adds /register route when mode is demo', async () => {
    _mode.value = 'demo'
    vi.resetModules()

    const routerModule = await import('@/router/index.js')
    const router = routerModule.default

    // Before registration, /register should not exist
    const beforeRoute = router.getRoutes().find(r => r.path === '/register')
    expect(beforeRoute).toBeUndefined()

    // Import and call registerSaasRoutes
    const { registerSaasRoutes } = await import('@/saas/routes/index.js')
    registerSaasRoutes()

    // After registration, /register should exist
    const afterRoute = router.getRoutes().find(r => r.path === '/register')
    expect(afterRoute).toBeDefined()
    expect(afterRoute.meta.layout).toBe('auth')
    expect(afterRoute.meta.requiresAuth).toBe(false)
  })

  it('registerSaasRoutes adds /register route when mode is saas', async () => {
    _mode.value = 'saas'
    vi.resetModules()

    const routerModule = await import('@/router/index.js')
    const router = routerModule.default

    const { registerSaasRoutes } = await import('@/saas/routes/index.js')
    registerSaasRoutes()

    const route = router.getRoutes().find(r => r.path === '/register')
    expect(route).toBeDefined()
    expect(route.meta.layout).toBe('auth')
  })

  it('registerSaasRoutes does NOT add /register in CE mode', async () => {
    _mode.value = 'ce'
    vi.resetModules()

    const routerModule = await import('@/router/index.js')
    const router = routerModule.default

    const { registerSaasRoutes } = await import('@/saas/routes/index.js')
    registerSaasRoutes()

    const route = router.getRoutes().find(r => r.path === '/register')
    expect(route).toBeUndefined()
  })

  it('CE router does not have /register route by default', async () => {
    vi.resetModules()

    const routerModule = await import('@/router/index.js')
    const router = routerModule.default

    const route = router.getRoutes().find(r => r.path === '/register')
    expect(route).toBeUndefined()
  })
})
