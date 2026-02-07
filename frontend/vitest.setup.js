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
  VBtn: { template: '<button><slot /></button>' }
}

// Global CSS and component mocking
vi.mock('vuetify/components', () => VuetifyMock)

// Ignore Vuetify CSS
vi.mock('vuetify/lib/components/VCode/VCode.css', () => ({
  __esModule: true,
  default: ''
}))

// Mock all CSS imports
vi.mock('**/*.css', () => ({
  __esModule: true,
  default: ''
}))

// Stub out Vuetify plugin
vi.mock('vuetify', () => ({
  createVuetify: () => ({
    install: () => {}
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
  'v-stepper': { template: '<div><slot /></div>' },
  'v-progress-circular': { template: '<div>Progress</div>' },
  'v-progress-linear': { template: '<div>Progress Linear</div>' },
  'v-overlay': { template: '<div><slot /></div>' },
  'v-img': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-stepper-window-item': { template: '<div><slot /></div>' }
}

// Mock global properties and methods
vi.mock('pinia', () => ({
  defineStore: vi.fn(),
  storeToRefs: vi.fn()
}))

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

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
})
