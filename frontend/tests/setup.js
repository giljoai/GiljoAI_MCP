/**
 * Vitest global test setup
 * Configures Vue Test Utils and Vuetify for all tests
 */
import { config } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { vi } from 'vitest'

// Suppress Vuetify warnings in tests
config.global.config.warnHandler = () => null

// Mock CSS imports
vi.mock('*.css', () => ({
  default: {}
}))

// Mock window.matchMedia (required for Vuetify)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver (required for some Vuetify components)
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver (required for some Vuetify components)
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Global mocks for authentication and routing
config.global.mocks = {
  $router: {
    push: vi.fn(),
    currentRoute: {
      value: {
        path: '/'
      }
    }
  },
  $route: {
    path: '/'
  }
}

// Mock Pinia stores globally
config.global.plugins = [
  createPinia()
]

// Mock localStorage
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn()
  },
  writable: true
})

// Global test helpers
const resetAllMocks = () => {
  vi.resetAllMocks()
  vi.clearAllMocks()
}

// Register global test utilities
global.resetAllMocks = resetAllMocks