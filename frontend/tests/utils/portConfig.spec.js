import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('portConfig', () => {
  let originalPort

  beforeEach(() => {
    vi.resetModules()
    originalPort = window.location.port
    vi.stubEnv('VITE_API_PORT', '')
    delete window.API_PORT
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('uses window.location.port when available', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, port: '7272' },
      writable: true,
      configurable: true,
    })

    const { getApiPort } = await import('@/utils/portConfig.js')
    expect(getApiPort()).toBe('7272')
  })

  it('falls back to 7272 when port is empty string', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, port: '' },
      writable: true,
      configurable: true,
    })

    const { getApiPort } = await import('@/utils/portConfig.js')
    expect(getApiPort()).toBe('7272')
  })

  it('prefers VITE_API_PORT env var over location.port', async () => {
    vi.stubEnv('VITE_API_PORT', '9999')
    Object.defineProperty(window, 'location', {
      value: { ...window.location, port: '7272' },
      writable: true,
      configurable: true,
    })

    const { getApiPort } = await import('@/utils/portConfig.js')
    expect(getApiPort()).toBe('9999')
  })

  it('getApiPortInt returns an integer', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, port: '7272' },
      writable: true,
      configurable: true,
    })

    const { getApiPortInt } = await import('@/utils/portConfig.js')
    const result = getApiPortInt()
    expect(typeof result).toBe('number')
    expect(Number.isInteger(result)).toBe(true)
    expect(result).toBe(7272)
  })
})
