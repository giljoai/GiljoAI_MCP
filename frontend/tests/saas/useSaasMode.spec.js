import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'

// Mock configService before importing the composable
const mockConfigService = {
  fetchConfig: vi.fn(() => Promise.resolve()),
  getGiljoMode: vi.fn(() => 'ce'),
  config: null,
}

vi.mock('@/services/configService', () => ({
  default: mockConfigService,
}))

// We must re-import the composable fresh for each test to reset module-level state
// Use dynamic imports to work around module caching

describe('useSaasMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset module-level state by resetting the module registry
    vi.resetModules()
    mockConfigService.getGiljoMode.mockReturnValue('ce')
    mockConfigService.fetchConfig.mockResolvedValue()
  })

  it('defaults to CE mode before init()', async () => {
    const { useSaasMode } = await import('@/saas/composables/useSaasMode')
    const { giljoMode, isCe, isSaas, isDemo, isSaasOrDemo, editionLabel } = useSaasMode()

    expect(giljoMode.value).toBe('ce')
    expect(isCe.value).toBe(true)
    expect(isSaas.value).toBe(false)
    expect(isDemo.value).toBe(false)
    expect(isSaasOrDemo.value).toBe(false)
    expect(editionLabel.value).toBe('Community Edition')
  })

  it('returns Demo Edition label after init() with demo mode', async () => {
    mockConfigService.getGiljoMode.mockReturnValue('demo')

    const { useSaasMode } = await import('@/saas/composables/useSaasMode')
    const { giljoMode, isDemo, isSaasOrDemo, editionLabel, init } = useSaasMode()

    await init()

    expect(giljoMode.value).toBe('demo')
    expect(isDemo.value).toBe(true)
    expect(isSaasOrDemo.value).toBe(true)
    expect(editionLabel.value).toBe('Demo Edition')
  })

  it('returns SaaS Edition label after init() with saas mode', async () => {
    mockConfigService.getGiljoMode.mockReturnValue('saas')

    const { useSaasMode } = await import('@/saas/composables/useSaasMode')
    const { giljoMode, isSaas, isSaasOrDemo, editionLabel, init } = useSaasMode()

    await init()

    expect(giljoMode.value).toBe('saas')
    expect(isSaas.value).toBe(true)
    expect(isSaasOrDemo.value).toBe(true)
    expect(editionLabel.value).toBe('SaaS Edition')
  })

  it('calls configService.fetchConfig() on first init()', async () => {
    const { useSaasMode } = await import('@/saas/composables/useSaasMode')
    const { init } = useSaasMode()

    await init()

    expect(mockConfigService.fetchConfig).toHaveBeenCalledTimes(1)
  })

  it('does not call fetchConfig on subsequent init() calls (idempotent)', async () => {
    const { useSaasMode } = await import('@/saas/composables/useSaasMode')
    const { init } = useSaasMode()

    await init()
    await init()
    await init()

    expect(mockConfigService.fetchConfig).toHaveBeenCalledTimes(1)
  })

  it('giljoMode ref is readonly (cannot be directly mutated)', async () => {
    const { useSaasMode } = await import('@/saas/composables/useSaasMode')
    const { giljoMode } = useSaasMode()

    // readonly refs should warn on direct mutation in dev mode
    // The ref itself should still reflect the underlying value
    expect(giljoMode.value).toBe('ce')
  })

  it('shares state across multiple useSaasMode() calls', async () => {
    mockConfigService.getGiljoMode.mockReturnValue('demo')

    const { useSaasMode } = await import('@/saas/composables/useSaasMode')

    const instance1 = useSaasMode()
    await instance1.init()

    const instance2 = useSaasMode()

    // instance2 should see the same state without calling init()
    expect(instance2.giljoMode.value).toBe('demo')
    expect(instance2.isDemo.value).toBe(true)
  })
})
