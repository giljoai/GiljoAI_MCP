import { describe, it, expect, vi } from 'vitest'
import {
  detectOS,
  getPythonPath,
  normalizePathForOS
} from '@/utils/pathDetection'

describe('Path Detection Utilities', () => {
  const mockHomePath = '/home/user/GiljoAI_MCP'
  const mockWindowsPath = 'F:\\GiljoAI_MCP'

  beforeEach(() => {
    // Reset platform detection
    vi.resetModules()
  })

  it('detects correct operating system', () => {
    vi.stubGlobal('process', {
      platform: 'win32',
      env: { USERPROFILE: 'C:\\Users\\testuser' }
    })
    expect(detectOS()).toBe('windows')

    vi.stubGlobal('process', {
      platform: 'darwin',
      env: { HOME: '/Users/testuser' }
    })
    expect(detectOS()).toBe('macos')

    vi.stubGlobal('process', {
      platform: 'linux',
      env: { HOME: '/home/testuser' }
    })
    expect(detectOS()).toBe('linux')
  })

  it('generates correct Python path for different operating systems', () => {
    // Windows path
    vi.stubGlobal('process', {
      platform: 'win32',
      env: { USERPROFILE: mockWindowsPath }
    })
    const windowsPythonPath = getPythonPath(mockWindowsPath)
    expect(windowsPythonPath).toMatch(/venv\\Scripts\\python\.exe$/)

    // Linux/macOS path
    vi.stubGlobal('process', {
      platform: 'linux',
      env: { HOME: mockHomePath }
    })
    const linuxPythonPath = getPythonPath(mockHomePath)
    expect(linuxPythonPath).toMatch(/venv\/bin\/python$/)
  })

  it('normalizes paths for different operating systems', () => {
    // Windows-style path
    const windowsPath = 'F:\\GiljoAI_MCP\\folder\\file.txt'
    const normalizedWindowsPath = normalizePathForOS(windowsPath)
    expect(normalizedWindowsPath).toBe('F:/GiljoAI_MCP/folder/file.txt')

    // Unix-style path
    const unixPath = '/home/user/GiljoAI_MCP/folder/file.txt'
    const normalizedUnixPath = normalizePathForOS(unixPath)
    expect(normalizedUnixPath).toBe(unixPath)
  })

  it('handles edge cases for path detection', () => {
    // Undefined or empty home path
    vi.stubGlobal('process', {
      platform: 'linux',
      env: { HOME: undefined }
    })
    expect(() => getPythonPath()).toThrow()

    // Path with special characters
    const specialPath = '/path/with space/GiljoAI_MCP'
    const specialPythonPath = getPythonPath(specialPath)
    expect(specialPythonPath).toMatch(/venv\/bin\/python$/)
  })
})
