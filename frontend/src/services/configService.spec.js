/**
 * configService.spec.js — FE-6055
 *
 * Edition-gating hardening: a failed/timed-out config fetch must resolve the
 * edition to 'unknown' (NEVER 'ce'), must NOT render CE-only chrome (the dead
 * admin link) on a SaaS box, must NOT pin the bad guess (self-heals on the next
 * fetch without a reload), and — the mirror bug — must NOT render SaaS-only
 * chrome on an unknown/timed-out CE box.
 *
 * Exercises the REAL configService singleton. The NavigationDrawer admin gate
 * and useSaasMode.isCeConfirmed both reduce to
 * `getGiljoMode() === 'ce' && !isFallback()`, asserted here against live state.
 * (The useSaasMode side of the contract — including the 'unknown' mirror-bug
 * guard — is covered in tests/saas/useSaasMode.spec.js, which may import saas/.)
 *
 * Edition scope: Both (CE service module — no saas/ import here, per the
 * CE/SaaS import boundary).
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import configService from './configService'

// Mirrors the CE-only admin-link gate in NavigationDrawer.vue (isAdmin &&
// isCeConfirmed) and useSaasMode.isCeConfirmed: CE chrome shows ONLY on a
// confirmed, non-fallback 'ce'.
const adminVisible = (isAdmin) =>
  isAdmin && configService.getGiljoMode() === 'ce' && !configService.isFallback()

function okConfig(giljoMode) {
  return {
    ok: true,
    json: async () => ({
      api: { host: 'localhost', port: 8000, protocol: 'http' },
      mode: 'server',
      giljo_mode: giljoMode,
    }),
  }
}

describe('FE-6055 — edition gating fails to "unknown", never "ce"', () => {
  beforeEach(() => {
    configService.clearCache()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    configService.clearCache()
  })

  // (a) fallback -> 'unknown', never 'ce'
  it('resolves giljo_mode to "unknown" (never "ce") when the fetch fails', async () => {
    global.fetch.mockRejectedValueOnce(new Error('network down / timeout'))

    const cfg = await configService.fetchConfig()

    expect(cfg._fallback).toBe(true)
    expect(configService.getGiljoMode()).toBe('unknown')
    expect(configService.getGiljoMode()).not.toBe('ce')
  })

  // (b) admin/CE-only chrome hidden on unknown OR saas; shown only on confirmed ce
  it('hides the admin link on a timed-out (unknown) deployment', async () => {
    global.fetch.mockRejectedValueOnce(new Error('timeout'))
    await configService.fetchConfig()

    expect(adminVisible(true)).toBe(false)
  })

  it('hides the admin link on confirmed SaaS', async () => {
    global.fetch.mockResolvedValueOnce(okConfig('saas'))
    await configService.fetchConfig()

    expect(configService.getGiljoMode()).toBe('saas')
    expect(adminVisible(true)).toBe(false)
  })

  it('shows the admin link only on confirmed CE for an admin', async () => {
    global.fetch.mockResolvedValueOnce(okConfig('ce'))
    await configService.fetchConfig()

    expect(configService.getGiljoMode()).toBe('ce')
    expect(configService.isFallback()).toBe(false)
    expect(adminVisible(true)).toBe(true)
    // non-admins never see it regardless of edition
    expect(adminVisible(false)).toBe(false)
  })

  it('keeps the admin link hidden even if a fallback config ever reports "ce"', () => {
    // Defense-in-depth: a degraded/fallback config must not unlock CE chrome
    // even if its mode string says 'ce'. The !isFallback() guard catches it.
    configService.config = { giljo_mode: 'ce', _fallback: true }
    expect(adminVisible(true)).toBe(false)
  })

  // (c) the bad guess is not pinned: the next read retries and self-heals
  it('does NOT pin a fallback config and self-heals to SaaS on the next fetch', async () => {
    global.fetch.mockRejectedValueOnce(new Error('first fetch times out'))
    const first = await configService.fetchConfig()

    expect(first._fallback).toBe(true)
    // not cached -> the wrong edition is not frozen for the page session
    expect(configService.getRawConfig()).toBeNull()
    expect(global.fetch).toHaveBeenCalledTimes(1)

    // next read retries the REAL fetch (no manual reload) and heals to saas
    global.fetch.mockResolvedValueOnce(okConfig('saas'))
    const second = await configService.fetchConfig()

    expect(global.fetch).toHaveBeenCalledTimes(2)
    expect(second._fallback).toBeUndefined()
    expect(configService.getGiljoMode()).toBe('saas')
    expect(adminVisible(true)).toBe(false)
  })
})
