import { vi } from 'vitest'

export const setupServiceMock = {
  detectSerena: vi.fn().mockResolvedValue({
    installed: false,
    version: null,
    error: null
  }),
  attachSerena: vi.fn().mockResolvedValue({
    success: true,
    error: null
  }),
  getSerenaStatus: vi.fn().mockResolvedValue({
    enabled: false,
    version: null
  }),
  detachSerena: vi.fn().mockResolvedValue({
    success: true,
    error: null
  })
}

export default setupServiceMock