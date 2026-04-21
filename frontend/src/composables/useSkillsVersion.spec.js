import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSkillsVersion } from './useSkillsVersion'
import api from '@/services/api'

describe('useSkillsVersion', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Ensure the health mock exists (added dynamically since global setup may not have it)
    if (!api.health) {
      api.health = { check: vi.fn() }
    }
  })

  it('returns initial state with no localStorage value', () => {
    window.localStorage.getItem = vi.fn(() => null)
    const { localVersion, serverVersion, isOutdated, hasChecked } = useSkillsVersion()

    expect(localVersion.value).toBe(null)
    expect(serverVersion.value).toBe(null)
    expect(isOutdated.value).toBe(false)
    expect(hasChecked.value).toBe(false)
  })

  it('reads local version from localStorage', () => {
    window.localStorage.getItem = vi.fn((key) => {
      if (key === 'giljo_skills_version') return '2026.04.20'
      return null
    })

    const { localVersion } = useSkillsVersion()
    expect(localVersion.value).toBe('2026.04.20')
  })

  it('checkServerVersion fetches skills_version from health endpoint', async () => {
    window.localStorage.getItem = vi.fn((key) => {
      if (key === 'giljo_skills_version') return '2026.04.18'
      return null
    })
    api.health.check.mockResolvedValue({
      data: { status: 'healthy', skills_version: '2026.04.20' },
    })

    const { checkServerVersion, serverVersion, isOutdated, hasChecked } = useSkillsVersion()
    await checkServerVersion()

    expect(api.health.check).toHaveBeenCalledOnce()
    expect(serverVersion.value).toBe('2026.04.20')
    expect(isOutdated.value).toBe(true)
    expect(hasChecked.value).toBe(true)
  })

  it('isOutdated is false when versions match', async () => {
    window.localStorage.getItem = vi.fn((key) => {
      if (key === 'giljo_skills_version') return '2026.04.20'
      return null
    })
    api.health.check.mockResolvedValue({
      data: { status: 'healthy', skills_version: '2026.04.20' },
    })

    const { checkServerVersion, isOutdated } = useSkillsVersion()
    await checkServerVersion()

    expect(isOutdated.value).toBe(false)
  })

  it('isOutdated is false when server has no skills_version', async () => {
    window.localStorage.getItem = vi.fn((key) => {
      if (key === 'giljo_skills_version') return '2026.04.18'
      return null
    })
    api.health.check.mockResolvedValue({
      data: { status: 'healthy' },
    })

    const { checkServerVersion, isOutdated } = useSkillsVersion()
    await checkServerVersion()

    expect(isOutdated.value).toBe(false)
  })

  it('shows badge when local has no version (never ran giljo_setup)', async () => {
    window.localStorage.getItem = vi.fn(() => null)
    api.health.check.mockResolvedValue({
      data: { status: 'healthy', skills_version: '2026.04.20' },
    })

    const { checkServerVersion, isOutdated } = useSkillsVersion()
    await checkServerVersion()

    expect(isOutdated.value).toBe(true)
  })

  it('dismiss sets dismissed flag and persists to localStorage', () => {
    window.localStorage.getItem = vi.fn((key) => {
      if (key === 'giljo_skills_version') return '2026.04.18'
      return null
    })
    window.localStorage.setItem = vi.fn()

    const { dismiss, isDismissed } = useSkillsVersion()
    dismiss('2026.04.20')

    expect(isDismissed.value).toBe(true)
    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      'giljo_skills_dismissed_version',
      '2026.04.20'
    )
  })

  it('showBadge respects dismissed version', async () => {
    window.localStorage.getItem = vi.fn((key) => {
      if (key === 'giljo_skills_version') return '2026.04.18'
      if (key === 'giljo_skills_dismissed_version') return '2026.04.20'
      return null
    })
    api.health.check.mockResolvedValue({
      data: { status: 'healthy', skills_version: '2026.04.20' },
    })

    const { checkServerVersion, showBadge } = useSkillsVersion()
    await checkServerVersion()

    expect(showBadge.value).toBe(false)
  })

  it('handles API error gracefully', async () => {
    window.localStorage.getItem = vi.fn((key) => {
      if (key === 'giljo_skills_version') return '2026.04.18'
      return null
    })
    api.health.check.mockRejectedValue(new Error('Network error'))

    const { checkServerVersion, serverVersion, isOutdated, hasChecked } = useSkillsVersion()
    await checkServerVersion()

    expect(serverVersion.value).toBe(null)
    expect(isOutdated.value).toBe(false)
    expect(hasChecked.value).toBe(false)
  })

  it('updateLocalVersion writes to localStorage and updates state', () => {
    window.localStorage.getItem = vi.fn(() => null)
    window.localStorage.setItem = vi.fn()

    const { updateLocalVersion, localVersion } = useSkillsVersion()
    updateLocalVersion('2026.04.20')

    expect(localVersion.value).toBe('2026.04.20')
    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      'giljo_skills_version',
      '2026.04.20'
    )
  })
})
