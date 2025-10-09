/**
 * Path Detection Utilities
 *
 * Cross-platform path detection and normalization for GiljoAI MCP configuration.
 * Handles OS-specific path separators and Python executable locations.
 */

/**
 * Detect the current operating system
 * @returns {string} 'windows' | 'linux' | 'macos'
 */
export function detectOS() {
  // In browser environment, use navigator
  if (typeof window !== 'undefined' && window.navigator) {
    const platform = window.navigator.platform?.toLowerCase() || ''
    const userAgent = window.navigator.userAgent?.toLowerCase() || ''

    if (platform.includes('win') || userAgent.includes('windows')) {
      return 'windows'
    }
    if (platform.includes('mac') || userAgent.includes('mac')) {
      return 'macos'
    }
    if (platform.includes('linux') || userAgent.includes('linux')) {
      return 'linux'
    }
  }

  // Fallback for Node.js environment (testing)
  if (typeof process !== 'undefined' && process.platform) {
    const platform = process.platform
    if (platform === 'win32') return 'windows'
    if (platform === 'darwin') return 'macos'
    if (platform === 'linux') return 'linux'
  }

  // Default fallback
  return 'linux'
}

/**
 * Generate OS-specific Python executable path
 * @param {string} projectPath - Base project path (e.g., 'F:/GiljoAI_MCP')
 * @param {string} [os] - Target OS (if not provided, auto-detects)
 * @returns {string} Full path to Python executable
 * @throws {Error} If projectPath is not provided
 */
export function getPythonPath(projectPath, os) {
  if (!projectPath) {
    throw new Error('Project path is required')
  }

  const targetOS = os || detectOS()

  // Normalize project path for consistency
  const normalizedPath = normalizePathForOS(projectPath, targetOS)

  if (targetOS === 'windows') {
    // Windows: F:\GiljoAI_MCP\venv\Scripts\python.exe
    return `${normalizedPath}\\venv\\Scripts\\python.exe`
  } else {
    // Linux/macOS: /home/user/GiljoAI_MCP/venv/bin/python
    return `${normalizedPath}/venv/bin/python`
  }
}

/**
 * Normalize path separators for target OS
 * @param {string} path - Path to normalize
 * @param {string} [os] - Target OS (if not provided, auto-detects)
 * @returns {string} Normalized path
 */
export function normalizePathForOS(path, os) {
  if (!path) return path

  const targetOS = os || detectOS()

  if (targetOS === 'windows') {
    // Convert forward slashes to backslashes for Windows
    return path.replace(/\//g, '\\')
  } else {
    // Convert backslashes to forward slashes for Unix-like systems
    return path.replace(/\\/g, '/')
  }
}
