import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getApiBaseUrl, getWsBaseUrl } from '@/composables/useApiUrl'

describe('useApiUrl', () => {
  const originalLocation = window.location
  const originalApiBaseUrl = window.API_BASE_URL

  beforeEach(() => {
    vi.unstubAllEnvs()
    delete window.API_BASE_URL
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    // Restore window.location in case a test overrode it
    if (window.location !== originalLocation) {
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: originalLocation,
      })
    }
    if (originalApiBaseUrl === undefined) {
      delete window.API_BASE_URL
    } else {
      window.API_BASE_URL = originalApiBaseUrl
    }
  })

  function setLocation(origin) {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, origin, href: `${origin}/` },
    })
  }

  describe('getApiBaseUrl', () => {
    it('returns VITE_API_URL verbatim when it is an absolute https URL', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', 'https://demo.giljo.ai')
      expect(getApiBaseUrl()).toBe('https://demo.giljo.ai')
    })

    it('strips a trailing slash from VITE_API_URL', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', 'https://demo.giljo.ai/')
      expect(getApiBaseUrl()).toBe('https://demo.giljo.ai')
    })

    it('accepts absolute http URLs too', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:7272')
      expect(getApiBaseUrl()).toBe('http://127.0.0.1:7272')
    })

    it('ignores VITE_API_URL when it is not absolute', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', '/api')
      setLocation('https://acme.giljo.ai')
      expect(getApiBaseUrl()).toBe('https://acme.giljo.ai')
    })

    it('uses window.API_BASE_URL when no VITE_API_URL', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', '')
      window.API_BASE_URL = 'https://runtime.example.com'
      expect(getApiBaseUrl()).toBe('https://runtime.example.com')
    })

    it('returns empty string in dev mode', () => {
      vi.stubEnv('DEV', true)
      vi.stubEnv('VITE_API_URL', '')
      expect(getApiBaseUrl()).toBe('')
    })

    it('falls back to window.location.origin in prod', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', '')
      setLocation('http://127.0.0.1:7272')
      expect(getApiBaseUrl()).toBe('http://127.0.0.1:7272')
    })

    it('uses SaaS subdomain origin when VITE_API_URL is unset', () => {
      // SaaS tenant deployment: no VITE_API_URL, served from tenant subdomain.
      // Must fall back to window.location.origin, not a hardcoded host.
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', '')
      setLocation('https://acme.giljo.ai')
      expect(getApiBaseUrl()).toBe('https://acme.giljo.ai')
    })

    it('does not append VITE_API_PORT to an absolute VITE_API_URL', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', 'https://demo.giljo.ai')
      vi.stubEnv('VITE_API_PORT', '7272')
      expect(getApiBaseUrl()).toBe('https://demo.giljo.ai')
    })
  })

  describe('getWsBaseUrl', () => {
    it('derives wss from https API base', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', 'https://demo.giljo.ai')
      expect(getWsBaseUrl()).toBe('wss://demo.giljo.ai')
    })

    it('derives ws from http API base', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', 'http://127.0.0.1:7272')
      expect(getWsBaseUrl()).toBe('ws://127.0.0.1:7272')
    })

    it('returns empty string in dev mode', () => {
      vi.stubEnv('DEV', true)
      vi.stubEnv('VITE_API_URL', '')
      expect(getWsBaseUrl()).toBe('')
    })

    it('derives ws scheme from same-origin fallback', () => {
      vi.stubEnv('DEV', false)
      vi.stubEnv('VITE_API_URL', '')
      setLocation('https://acme.giljo.ai')
      expect(getWsBaseUrl()).toBe('wss://acme.giljo.ai')
    })
  })
})
