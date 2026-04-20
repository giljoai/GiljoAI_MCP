/**
 * TemplateManager.spec.js
 *
 * Vitest specs for the template duplicate fix (commit 9d2d84bc3).
 *
 * Covers:
 *   Group 1 — duplicateTemplate() sets correct initial state for duplication
 *   Group 2 — saveTemplateAndPreview() error handling: name-collision 400 vs generic errors
 *
 * TDD: tests describe BEHAVIOR (what the component does to the user),
 * not implementation details.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import TemplateManager from '@/components/TemplateManager.vue'

// ---------------------------------------------------------------------------
// Captured showToast spy — must be declared before vi.mock (hoisting)
// ---------------------------------------------------------------------------
let mockShowToast

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: (...args) => mockShowToast(...args),
  }),
}))

// ---------------------------------------------------------------------------
// WebSocket mock (component subscribes on mount)
// ---------------------------------------------------------------------------
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocketV2: () => ({
    on: vi.fn(),
    off: vi.fn(),
    isConnected: { value: true },
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
  }),
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
  }),
}))

// ---------------------------------------------------------------------------
// API mock — global setup.js already mocks @/services/api, but we override
// templates.* here so we control resolve/reject per test.
// ---------------------------------------------------------------------------
vi.mock('@/services/api', () => {
  const apiObj = {
    templates: {
      list: vi.fn(() => Promise.resolve({ data: [] })),
      get: vi.fn(() => Promise.resolve({ data: {} })),
      create: vi.fn(() => Promise.resolve({ data: { id: 42 } })),
      update: vi.fn(() => Promise.resolve({ data: {} })),
      delete: vi.fn(() => Promise.resolve({ data: { success: true } })),
      preview: vi.fn(() => Promise.resolve({ data: { preview: 'Mock preview content' } })),
      activeCount: vi.fn(() =>
        Promise.resolve({ data: { active_count: 2, limit: 7, available: 5 } })
      ),
      history: vi.fn(() => Promise.resolve({ data: [] })),
      restore: vi.fn(() => Promise.resolve({ data: { success: true } })),
      reset: vi.fn(() => Promise.resolve({ data: { success: true } })),
    },
    auth: {
      me: vi.fn(() => Promise.resolve({ data: { id: 1, username: 'testuser', role: 'admin' } })),
    },
  }
  return { api: apiObj, default: apiObj }
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mountTemplateManager = () =>
  mount(TemplateManager, {
    global: {
      plugins: [
        createTestingPinia({
          initialState: {
            user: {
              currentUser: { id: 1, username: 'testuser', role: 'admin', tenant_key: 'tk_test' },
            },
          },
          stubActions: false,
        }),
      ],
      stubs: {
        // Stub heavy child components so mount is fast and focused
        VDataTable: true,
        VDataTableServer: true,
        VDialog: { template: '<div><slot /></div>' },
        Teleport: true,
      },
    },
  })

const makeTemplate = (overrides = {}) => ({
  id: 7,
  name: 'My Analyzer',
  role: 'analyzer',
  cli_tool: 'claude',
  custom_suffix: 'v2',
  background_color: '#abc123',
  model: 'sonnet',
  user_instructions: 'Do analysis.',
  tools: null,
  ...overrides,
})

// ---------------------------------------------------------------------------
// Group 1: duplicateTemplate() behavior
// ---------------------------------------------------------------------------

describe('duplicateTemplate()', () => {
  let wrapper

  beforeEach(() => {
    mockShowToast = vi.fn()
    wrapper = mountTemplateManager()
  })

  it('sets custom_suffix to empty string so user must provide their own name', () => {
    const template = makeTemplate({ custom_suffix: 'old-suffix' })
    wrapper.vm.duplicateTemplate(template)
    expect(wrapper.vm.editingTemplate.custom_suffix).toBe('')
  })

  it('sets display name to "<original name> (Copy)" as a hint', () => {
    const template = makeTemplate({ name: 'My Analyzer' })
    wrapper.vm.duplicateTemplate(template)
    expect(wrapper.vm.editingTemplate.name).toBe('My Analyzer (Copy)')
  })

  it('sets id to null so a new template is created instead of overwriting the original', () => {
    const template = makeTemplate({ id: 99 })
    wrapper.vm.duplicateTemplate(template)
    expect(wrapper.vm.editingTemplate.id).toBeNull()
  })

  it('opens the edit dialog', () => {
    const template = makeTemplate()
    wrapper.vm.duplicateTemplate(template)
    expect(wrapper.vm.editDialog).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Group 2: saveTemplateAndPreview() error handling
// ---------------------------------------------------------------------------

describe('saveTemplateAndPreview() error handling', () => {
  let wrapper
  let api

  beforeEach(async () => {
    mockShowToast = vi.fn()
    api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    wrapper = mountTemplateManager()

    // Seed editingTemplate with a new (id=null) template so create path is taken
    wrapper.vm.editingTemplate.id = null
    wrapper.vm.editingTemplate.role = 'analyzer'
    wrapper.vm.editingTemplate.custom_suffix = 'mycopy'
  })

  it('shows warning toast titled "Name Already Exists" when backend returns 400 with "already exists" in detail', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: {
        status: 400,
        data: { detail: 'Template with this name already exists.' },
      },
    })

    await wrapper.vm.saveTemplateAndPreview()

    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'warning',
        title: 'Name Already Exists',
      })
    )
  })

  it('shows warning toast titled "Name Already Exists" when backend returns 400 with "unique" in detail', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: {
        status: 400,
        data: { detail: 'unique constraint violation on name' },
      },
    })

    await wrapper.vm.saveTemplateAndPreview()

    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'warning',
        title: 'Name Already Exists',
      })
    )
  })

  it('shows generic error toast when backend returns 400 with unrelated detail', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: {
        status: 400,
        data: { detail: 'Invalid role value.' },
      },
    })

    await wrapper.vm.saveTemplateAndPreview()

    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
        title: 'Error',
      })
    )
  })

  it('shows generic error toast when backend returns 500', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: {
        status: 500,
        data: { detail: 'Internal server error' },
      },
    })

    await wrapper.vm.saveTemplateAndPreview()

    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
        title: 'Error',
      })
    )
  })

  it('shows generic error toast when error has no response (network failure)', async () => {
    api.templates.create.mockRejectedValueOnce(new Error('Network Error'))

    await wrapper.vm.saveTemplateAndPreview()

    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'error',
        title: 'Error',
      })
    )
  })
})
