import { config } from '@vue/test-utils'
import { vi } from 'vitest'
import { createVuetify } from 'vuetify'

// Define global Vuetify component mocks
const VuetifyMock = {
  VContainer: { template: '<div><slot /></div>' },
  VRow: { template: '<div><slot /></div>' },
  VCol: { template: '<div><slot /></div>' },
  VStepper: { template: '<div><slot /></div>' },
  VStepperHeader: { template: '<div><slot /></div>' },
  VStepperItem: { template: '<div><slot /></div>' },
  VStepperContent: { template: '<div><slot /></div>' },
  VCard: { template: '<div><slot /></div>' },
  VCardTitle: { template: '<div><slot /></div>' },
  VCardText: { template: '<div><slot /></div>' },
  VCardActions: { template: '<div><slot /></div>' },
  VBtn: { template: '<button v-bind=\"$attrs\"><slot /></button>' }
}

// Global CSS and component mocking
vi.mock('vuetify/components', () => VuetifyMock)

// Mock all CSS imports
vi.mock('**/*.css', () => ({
  __esModule: true,
  default: ''
}))

// Stub out Vuetify plugin and composables
vi.mock('vuetify', () => ({
  createVuetify: () => ({
    install: () => {}
  }),
  useDisplay: () => ({
    mobile: { value: false },
    xs: { value: false },
    sm: { value: false },
    md: { value: false },
    lg: { value: true },
    xl: { value: false },
    xxl: { value: false },
    width: { value: 1920 },
    height: { value: 1080 },
    platform: { value: { android: false, ios: false, mac: false, touch: false, ssr: false } },
    name: { value: 'lg' }
  }),
  useTheme: () => ({
    global: {
      name: { value: 'dark' },
      current: { value: { dark: true, colors: { background: '#121212' } } }
    },
    name: { value: 'dark' },
    current: { value: { dark: true, colors: { background: '#121212' } } },
    computedThemes: { value: {} },
    themes: { value: {} },
    isDisabled: { value: false }
  })
}))

// Globally stub Vuetify components
config.global.stubs = {
  ...config.global.stubs,
  ...VuetifyMock
}

// Create a minimal Vuetify mock plugin
const vuetify = createVuetify()

// Global mocks and stubs
config.global.plugins = [vuetify]

config.global.stubs = {
  'v-container': { template: '<div><slot /></div>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-card': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-card-actions': { template: '<div><slot /></div>' },
  'v-stepper': { template: '<div><slot /></div>' },
  'v-progress-circular': { template: '<div>Progress</div>' },
  'v-progress-linear': { template: '<div><slot /></div>' },
  'v-overlay': { template: '<div><slot /></div>' },
  'v-img': { template: '<div><slot /></div>' },
  'v-btn': { template: '<button class="v-btn" v-bind="$attrs"><slot /></button>' },
  'v-icon': { template: '<span class="v-icon"><slot /></span>' },
  'v-avatar': { template: '<div class="v-avatar"><slot /></div>' },
  'v-chip': { template: '<span><slot /></span>' },
  'v-badge': { template: '<span><slot /></span>' },
  'v-alert': { template: '<div><slot /></div>' },
  'v-divider': { template: '<hr />' },
  'v-dialog': { template: '<div><slot /></div>' },
  'v-list': { template: '<div><slot /></div>' },
  'v-list-item': { template: '<div><slot /></div>' },
  'v-list-item-title': { template: '<div><slot /></div>' },
  'v-checkbox': { template: '<input type="checkbox" />' },
  'v-textarea': { template: '<textarea><slot /></textarea>' },
  'v-spacer': { template: '<div></div>' },
  'v-snackbar': { template: '<div><slot /></div>' },
  'v-stepper-window-item': { template: '<div><slot /></div>' },
  'v-switch': { template: '<input type="checkbox" />' }
}

// Provide mock implementations for browser APIs
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn()
  },
  writable: true
})

// Mock Web APIs
window.matchMedia = vi.fn().mockImplementation(query => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn()
}))

// Mock document.execCommand for clipboard operations
document.execCommand = vi.fn(() => true)

// Mock API service
vi.mock('@/services/api', () => ({
  api: {
    prompts: {
      execution: vi.fn(() => Promise.resolve({ data: { prompt: 'Mock orchestrator prompt' } })),
      agentPrompt: vi.fn(() => Promise.resolve({ data: { prompt: 'Mock agent prompt' } }))
    },
    get: vi.fn(() => Promise.resolve({ data: { prompt: 'Mock prompt text' } })),
    post: vi.fn(() => Promise.resolve({ data: { success: true } })),
    put: vi.fn(() => Promise.resolve({ data: { success: true } })),
    delete: vi.fn(() => Promise.resolve({ data: { success: true } }))
  },
  default: {
    get: vi.fn(() => Promise.resolve({ data: { prompt: 'Mock prompt text' } })),
    post: vi.fn(() => Promise.resolve({ data: { success: true } })),
    put: vi.fn(() => Promise.resolve({ data: { success: true } })),
    delete: vi.fn(() => Promise.resolve({ data: { success: true } }))
  }
}))

// Mock WebSocket service
vi.mock('@/services/websocket', () => ({
  webSocketService: {
    on: vi.fn(),
    off: vi.fn(),
    send: vi.fn(),
    isConnected: false
  }
}))

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
})
