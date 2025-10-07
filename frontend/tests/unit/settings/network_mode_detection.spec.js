import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Network Mode Detection', () => {
  let mockFetch

  beforeEach(() => {
    // Reset fetch mock before each test
    mockFetch = vi.fn()
    global.fetch = mockFetch
  })

  it('should detect localhost mode from /api/v1/config', async () => {
    const mockConfig = {
      installation: { mode: 'localhost' },
      services: {
        api: {
          host: '127.0.0.1',
          port: 7272
        }
      },
      security: {
        cors: { allowed_origins: ['http://localhost:7274'] }
      }
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockConfig)
    })

    const { default: SettingsView } = await import('@/views/SettingsView.vue')
    const component = mount(SettingsView)

    await vi.runAllTicks()

    expect(component.vm.currentMode).toBe('localhost')
    expect(component.vm.networkSettings.apiHost).toBe('127.0.0.1')
    expect(component.vm.corsOrigins).toEqual(['http://localhost:7274'])
  })

  it('should detect lan mode from fallback /api/setup/status', async () => {
    // First attempt fails
    mockFetch
      .mockRejectedValueOnce(new Error('Config endpoint failed'))
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          network_mode: 'lan',
          host: '0.0.0.0',
          port: 7272,
          allowed_origins: ['http://192.168.1.100:7274']
        })
      })

    const { default: SettingsView } = await import('@/views/SettingsView.vue')
    const component = mount(SettingsView)

    await vi.runAllTicks()

    expect(component.vm.currentMode).toBe('lan')
    expect(component.vm.networkSettings.apiHost).toBe('0.0.0.0')
    expect(component.vm.corsOrigins).toEqual(['http://192.168.1.100:7274'])
  })

  it('handles multiple fallback scenarios', async () => {
    // Completely failed network detection
    mockFetch
      .mockRejectedValueOnce(new Error('Config endpoint failed'))
      .mockRejectedValueOnce(new Error('Fallback status failed'))

    const { default: SettingsView } = await import('@/views/SettingsView.vue')
    const component = mount(SettingsView)

    await vi.runAllTicks()

    expect(component.vm.currentMode).toBe('localhost')
    expect(component.vm.networkSettings.apiHost).toBe('127.0.0.1')
    expect(component.vm.corsOrigins).toEqual([])
  })
})