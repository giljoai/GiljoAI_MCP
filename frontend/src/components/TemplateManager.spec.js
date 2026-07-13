/**
 * TemplateManager.spec.js — FE-6042b
 *
 * Characterization spec for TemplateManager.vue.
 * Written BEFORE the container/presentational split so the split is validated
 * by proving this same file (byte-unchanged) still passes after refactoring.
 *
 * Strategy: ALL assertions target either
 *   (a) api.templates.* mock calls (the public contract that never moves), OR
 *   (b) container-retained refs (editDialog, deleteDialog, resetDialog,
 *       deletingTemplate, resettingTemplate), OR
 *   (c) DOM testids that must be present whether the node lives in the container
 *       or in a child component (e.g., closeout-mode-toggle, template-toggle-${role}).
 *
 * The v-data-table stub iterates :items and renders named item.* slots so that
 * row-level testids (template-toggle-*, action menu items) are reachable in
 * jsdom. This stub shape also works once the table moves into TemplatesTable.
 *
 * Edition scope: CE
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import TemplateManager from '@/components/TemplateManager.vue'

// ---------------------------------------------------------------------------
// API mock — supplement the global setup.js mock with template-specific spies.
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
    settings: {
      getGeneral: vi.fn(() =>
        Promise.resolve({ data: { settings: { closeout_mode: 'hitl' } } })
      ),
      updateGeneral: vi.fn(() => Promise.resolve({ data: { success: true } })),
      // BE-9084: account-wide Headless-vs-HITL launch toggle
      getHeadlessLaunch: vi.fn(() =>
        Promise.resolve({ data: { allow_headless_launch: false } })
      ),
      updateHeadlessLaunch: vi.fn(() =>
        Promise.resolve({ data: { allow_headless_launch: true } })
      ),
      get: vi.fn(() => Promise.resolve({ data: {} })),
      update: vi.fn(() => Promise.resolve({ data: { success: true } })),
    },
    auth: {
      me: vi.fn(() => Promise.resolve({ data: { id: 1, username: 'testuser', role: 'admin' } })),
    },
  }
  return { api: apiObj, default: apiObj }
})

// ---------------------------------------------------------------------------
// Captured showToast spy (must be declared before vi.mock for hoisting)
// ---------------------------------------------------------------------------
let mockShowToast

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: (...args) => mockShowToast(...args),
  }),
}))

// ---------------------------------------------------------------------------
// Stubs
// ---------------------------------------------------------------------------

/**
 * v-data-table stub that renders item.* slots for every item.
 * This makes row-level testids reachable in jsdom both BEFORE and AFTER the
 * table moves into TemplatesTable — the slot names are the same either way.
 */
const dataTableStub = {
  props: ['headers', 'items', 'loading', 'search', 'itemsPerPage'],
  template: `
    <div class="v-data-table">
      <div v-for="item in (items || [])" :key="item.id" class="v-data-table-row">
        <slot name="item.name" :item="item" />
        <slot name="item.role" :item="item" />
        <slot name="item.is_active" :item="item" />
        <slot name="item.export_status" :item="item" />
        <slot name="item.updated_at" :item="item" />
        <slot name="item.actions" :item="item" />
      </div>
    </div>
  `,
}

/**
 * v-switch stub that properly emits update:model-value so toggle handlers fire.
 */
const switchStub = {
  props: ['modelValue', 'disabled', 'color', 'hideDetails', 'density', 'ariaLabel'],
  emits: ['update:modelValue'],
  template: `
    <input
      type="checkbox"
      class="v-switch"
      v-bind="$attrs"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.checked)"
    />
  `,
}

/**
 * v-menu that renders both activator and default slots so action items appear.
 */
const menuStub = {
  template: `<div class="v-menu"><slot name="activator" :props="{}" /><slot /></div>`,
}

const listItemStub = {
  props: ['title', 'prependIcon'],
  template: `<div class="v-list-item" v-bind="$attrs" :title="title"><slot /></div>`,
}

const tooltipStub = {
  props: ['text', 'location'],
  template: `<div class="v-tooltip"><slot name="activator" :props="{}" /><slot /></div>`,
}

// ---------------------------------------------------------------------------
// Mount helper
// ---------------------------------------------------------------------------

function mountTemplateManager(options = {}) {
  return mount(TemplateManager, {
    global: {
      plugins: [
        createTestingPinia({
          initialState: {
            user: {
              currentUser: {
                id: 1,
                username: 'testuser',
                role: 'admin',
                tenant_key: 'tk_test',
              },
            },
          },
          stubActions: false,
        }),
      ],
      stubs: {
        'v-data-table': dataTableStub,
        'v-switch': switchStub,
        'v-menu': menuStub,
        'v-list-item': listItemStub,
        'v-tooltip': tooltipStub,
        // Keep dialog as passthrough so internal state (editingTemplate) works
        'v-dialog': { template: '<div class="v-dialog"><slot /></div>' },
        Teleport: true,
        ...options.stubs,
      },
    },
    ...options.mountOptions,
  })
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeTemplate(overrides = {}) {
  return {
    id: 7,
    name: 'My Analyzer',
    role: 'analyzer',
    category: 'role',
    cli_tool: 'claude',
    custom_suffix: 'v2',
    background_color: '#abc123',
    model: 'sonnet',
    user_instructions: 'Do analysis.',
    tools: null,
    is_active: true,
    may_be_stale: false,
    user_managed_export: false,
    _system: false,
    last_exported_at: '2024-01-01T12:00:00Z',
    updated_at: '2024-01-01T12:00:00Z',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Group 1 — Header chip and stale banner
// ---------------------------------------------------------------------------

describe('TemplateManager — header chip', () => {
  let wrapper

  beforeEach(async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.templates.activeCount.mockResolvedValue({
      data: { active_count: 3, limit: 7 },
    })
    wrapper = mountTemplateManager()
    await flushPromises()
  })

  it('renders the Agent Template Manager heading', () => {
    expect(wrapper.text()).toContain('Agent Template Manager')
  })

  it('renders a chip showing totalActiveAgents / totalCapacity when loaded', async () => {
    // After loadActiveCount: totalActive = 3+1=4, totalCapacity = 7+1=8
    const chip = wrapper.find('.v-chip')
    expect(chip.exists()).toBe(true)
    expect(chip.text()).toContain('4')
    expect(chip.text()).toContain('8')
  })
})

describe('TemplateManager — stale templates banner', () => {
  it('shows stale banner when at least one template is stale and not user-managed', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.templates.list.mockResolvedValue({
      data: [makeTemplate({ may_be_stale: true, user_managed_export: false })],
    })
    const wrapper = mountTemplateManager()
    await flushPromises()
    // The v-alert renders its slot text
    const text = wrapper.text()
    expect(text).toContain('update the agent templates')
  })

  it('hides stale banner when all stale templates are user-managed', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.templates.list.mockResolvedValue({
      data: [makeTemplate({ may_be_stale: true, user_managed_export: true })],
    })
    const wrapper = mountTemplateManager()
    await flushPromises()
    expect(wrapper.text()).not.toContain('update the agent templates')
  })
})

// ---------------------------------------------------------------------------
// Group 2 — HITL toggle
// ---------------------------------------------------------------------------

describe('TemplateManager — HITL closeout toggle', () => {
  it('renders the closeout-mode-toggle testid', async () => {
    mockShowToast = vi.fn()
    const wrapper = mountTemplateManager()
    await flushPromises()
    expect(wrapper.find('[data-testid="closeout-mode-toggle"]').exists()).toBe(true)
  })

  it('calls api.settings.updateGeneral when toggle changes', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    const wrapper = mountTemplateManager()
    await flushPromises()

    const toggle = wrapper.find('[data-testid="closeout-mode-toggle"]')
    // Simulate turning the switch OFF (checked=false → enabled=false → autonomous)
    toggle.element.checked = false
    await toggle.trigger('change')
    await flushPromises()

    expect(api.settings.updateGeneral).toHaveBeenCalledWith(
      expect.objectContaining({ closeout_mode: 'autonomous' })
    )
  })

  it('calls api.settings.updateGeneral with hitl when toggle turns ON', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    // Start with autonomous mode loaded
    api.settings.getGeneral.mockResolvedValue({
      data: { settings: { closeout_mode: 'autonomous' } },
    })
    const wrapper = mountTemplateManager()
    await flushPromises()

    const toggle = wrapper.find('[data-testid="closeout-mode-toggle"]')
    toggle.element.checked = true
    await toggle.trigger('change')
    await flushPromises()

    expect(api.settings.updateGeneral).toHaveBeenCalledWith(
      expect.objectContaining({ closeout_mode: 'hitl' })
    )
  })
})

describe('TemplateManager — BE-9084 Headless-vs-HITL launch toggle', () => {
  it('renders the headless-launch-toggle testid', async () => {
    mockShowToast = vi.fn()
    const wrapper = mountTemplateManager()
    await flushPromises()
    expect(wrapper.find('[data-testid="headless-launch-toggle"]').exists()).toBe(true)
  })

  it('loads the current headless setting on mount (default HITL / off)', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    mountTemplateManager()
    await flushPromises()
    expect(api.settings.getHeadlessLaunch).toHaveBeenCalled()
  })

  it('calls updateHeadlessLaunch(true) when the toggle turns ON', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    const wrapper = mountTemplateManager()
    await flushPromises()

    const toggle = wrapper.find('[data-testid="headless-launch-toggle"]')
    toggle.element.checked = true
    await toggle.trigger('change')
    await flushPromises()

    expect(api.settings.updateHeadlessLaunch).toHaveBeenCalledWith(true)
  })

  it('shows an error toast (revert path) when the save fails', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.settings.updateHeadlessLaunch.mockRejectedValueOnce(new Error('boom'))
    const wrapper = mountTemplateManager()
    await flushPromises()

    const toggle = wrapper.find('[data-testid="headless-launch-toggle"]')
    toggle.element.checked = true
    await toggle.trigger('change')
    await flushPromises()

    // The failed save must be attempted, then hit the catch/revert branch (error toast).
    expect(api.settings.updateHeadlessLaunch).toHaveBeenCalledWith(true)
    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error' })
    )
  })
})

// ---------------------------------------------------------------------------
// Group 3 — Data table row rendering
// ---------------------------------------------------------------------------

describe('TemplateManager — data table rows', () => {
  let wrapper

  beforeEach(async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.templates.list.mockResolvedValue({
      data: [
        makeTemplate({ id: 1, name: 'Analyzer', role: 'analyzer', is_active: true }),
        makeTemplate({ id: 2, name: 'Reviewer', role: 'reviewer', is_active: false }),
      ],
    })
    wrapper = mountTemplateManager()
    await flushPromises()
  })

  it('renders template-toggle for active user-managed template', () => {
    expect(
      wrapper.find('[data-testid="template-toggle-analyzer"]').exists()
    ).toBe(true)
  })

  it('renders template-toggle for inactive user-managed template', () => {
    expect(
      wrapper.find('[data-testid="template-toggle-reviewer"]').exists()
    ).toBe(true)
  })

  it('renders role badge text for each template', () => {
    const text = wrapper.text()
    expect(text).toContain('analyzer')
    expect(text).toContain('reviewer')
  })
})

// ---------------------------------------------------------------------------
// Group 4 — Active toggle fires api.templates.update
// ---------------------------------------------------------------------------

describe('TemplateManager — active toggle calls API', () => {
  it('calls api.templates.update when toggle changes', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.templates.list.mockResolvedValue({
      data: [makeTemplate({ id: 5, role: 'frontend', is_active: true })],
    })
    const wrapper = mountTemplateManager()
    await flushPromises()

    const toggle = wrapper.find('[data-testid="template-toggle-frontend"]')
    toggle.element.checked = false
    await toggle.trigger('change')
    await flushPromises()

    expect(api.templates.update).toHaveBeenCalledWith(5, { is_active: false })
  })
})

// ---------------------------------------------------------------------------
// Group 5 — Row action menu: edit opens dialog
// ---------------------------------------------------------------------------

describe('TemplateManager — row action: edit opens dialog', () => {
  it('sets editDialog=true when Edit is clicked', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.templates.list.mockResolvedValue({
      data: [makeTemplate({ id: 3, role: 'backend', name: 'My Backend' })],
    })
    const wrapper = mountTemplateManager()
    await flushPromises()

    // Find the Edit list item by title attribute
    const editItem = wrapper.find('[title="Edit"]')
    expect(editItem.exists()).toBe(true)
    await editItem.trigger('click')

    expect(wrapper.vm.editDialog).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Group 6 — Row action menu: duplicate opens dialog
// ---------------------------------------------------------------------------

describe('TemplateManager — row action: duplicate', () => {
  it('sets editDialog=true and id=null when Duplicate is clicked', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    api.templates.list.mockResolvedValue({
      data: [makeTemplate({ id: 4, role: 'tester', name: 'My Tester' })],
    })
    const wrapper = mountTemplateManager()
    await flushPromises()

    const dupItem = wrapper.find('[title="Duplicate"]')
    expect(dupItem.exists()).toBe(true)
    await dupItem.trigger('click')

    expect(wrapper.vm.editDialog).toBe(true)
    expect(wrapper.vm.editingTemplate.id).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Group 7 — Row action menu: reset opens confirm dialog
// ---------------------------------------------------------------------------

describe('TemplateManager — row action: reset to default', () => {
  it('sets resetDialog=true and resettingTemplate when Reset is clicked', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    const tpl = makeTemplate({ id: 6, role: 'documenter', name: 'My Docs', is_default: true })
    api.templates.list.mockResolvedValue({ data: [tpl] })
    const wrapper = mountTemplateManager()
    await flushPromises()

    const resetItem = wrapper.find('[title="Reset to Default"]')
    expect(resetItem.exists()).toBe(true)
    await resetItem.trigger('click')

    expect(wrapper.vm.resetDialog).toBe(true)
    expect(wrapper.vm.resettingTemplate?.id).toBe(6)
  })
})

// ---------------------------------------------------------------------------
// Group 8 — Row action menu: delete opens confirm dialog
// ---------------------------------------------------------------------------

describe('TemplateManager — row action: delete', () => {
  it('sets deleteDialog=true and deletingTemplate when Delete is clicked', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    const tpl = makeTemplate({ id: 9, role: 'reviewer', name: 'Reviewer' })
    api.templates.list.mockResolvedValue({ data: [tpl] })
    const wrapper = mountTemplateManager()
    await flushPromises()

    const deleteItem = wrapper.find('[title="Delete"]')
    expect(deleteItem.exists()).toBe(true)
    await deleteItem.trigger('click')

    expect(wrapper.vm.deleteDialog).toBe(true)
    expect(wrapper.vm.deletingTemplate?.id).toBe(9)
  })
})

// ---------------------------------------------------------------------------
// Group 9 — Row action menu: mark-user-managed calls API
// ---------------------------------------------------------------------------

describe('TemplateManager — row action: mark as user managed', () => {
  it('calls api.templates.update with user_managed_export=true', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    const tpl = makeTemplate({ id: 11, role: 'analyzer', may_be_stale: true, user_managed_export: false })
    api.templates.list.mockResolvedValue({ data: [tpl] })
    const wrapper = mountTemplateManager()
    await flushPromises()

    const markItem = wrapper.find('[title="Mark as User Managed"]')
    expect(markItem.exists()).toBe(true)
    await markItem.trigger('click')
    await flushPromises()

    expect(api.templates.update).toHaveBeenCalledWith(11, { user_managed_export: true })
  })
})

// ---------------------------------------------------------------------------
// Group 10 — Create / Edit / Save flow
// ---------------------------------------------------------------------------

describe('TemplateManager — create / save flow', () => {
  let wrapper
  let api

  beforeEach(async () => {
    mockShowToast = vi.fn()
    api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    wrapper = mountTemplateManager()
    await flushPromises()
  })

  it('calls api.templates.create with correct data when saving a new template', async () => {
    wrapper.vm.editingTemplate.id = null
    wrapper.vm.editingTemplate.role = 'analyzer'
    wrapper.vm.editingTemplate.custom_suffix = 'fast'
    wrapper.vm.editingTemplate.description = 'Fast analyzer'
    wrapper.vm.editingTemplate.user_instructions = 'Be fast'

    await wrapper.vm.saveTemplate()
    await flushPromises()

    expect(api.templates.create).toHaveBeenCalledWith(
      expect.objectContaining({
        role: 'analyzer',
        category: 'role',
      })
    )
  })

  it('calls api.templates.update when saving an existing template', async () => {
    wrapper.vm.editingTemplate.id = 42
    wrapper.vm.editingTemplate.role = 'backend'
    wrapper.vm.editingTemplate.user_instructions = 'Be good'

    await wrapper.vm.saveTemplate()
    await flushPromises()

    expect(api.templates.update).toHaveBeenCalledWith(42, expect.any(Object))
  })

  it('closes editDialog after successful save', async () => {
    wrapper.vm.editDialog = true
    wrapper.vm.editingTemplate.id = null
    wrapper.vm.editingTemplate.role = 'tester'

    await wrapper.vm.saveTemplate()
    await flushPromises()

    expect(wrapper.vm.editDialog).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Group 11 — Delete confirm flow
// ---------------------------------------------------------------------------

describe('TemplateManager — delete confirm flow', () => {
  it('calls api.templates.delete with correct id and closes dialog', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    const wrapper = mountTemplateManager()
    await flushPromises()

    wrapper.vm.deletingTemplate = makeTemplate({ id: 77 })
    wrapper.vm.deleteDialog = true

    await wrapper.vm.deleteTemplate()
    await flushPromises()

    expect(api.templates.delete).toHaveBeenCalledWith(77)
    expect(wrapper.vm.deleteDialog).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Group 12 — Reset confirm flow
// ---------------------------------------------------------------------------

describe('TemplateManager — reset confirm flow', () => {
  it('calls api.templates.reset with correct id and closes dialog', async () => {
    mockShowToast = vi.fn()
    const api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    const wrapper = mountTemplateManager()
    await flushPromises()

    wrapper.vm.resettingTemplate = makeTemplate({ id: 88 })
    wrapper.vm.resetDialog = true

    await wrapper.vm.resetTemplate()
    await flushPromises()

    expect(api.templates.reset).toHaveBeenCalledWith(88)
    expect(wrapper.vm.resetDialog).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Group 13 — saveTemplate() error handling (from existing tests/components spec)
// ---------------------------------------------------------------------------

describe('TemplateManager — saveTemplate() error handling', () => {
  let wrapper
  let api

  beforeEach(async () => {
    mockShowToast = vi.fn()
    api = (await import('@/services/api')).default
    vi.clearAllMocks()
    mockShowToast = vi.fn()
    wrapper = mountTemplateManager()
    wrapper.vm.editingTemplate.id = null
    wrapper.vm.editingTemplate.role = 'analyzer'
    wrapper.vm.editingTemplate.custom_suffix = 'mycopy'
  })

  it('shows warning toast titled "Name Already Exists" on 400 + "already exists"', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: { status: 400, data: { detail: 'Template with this name already exists.' } },
    })
    await wrapper.vm.saveTemplate()
    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'warning', title: 'Name Already Exists' })
    )
  })

  it('shows warning toast titled "Name Already Exists" on 400 + "unique"', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: { status: 400, data: { detail: 'unique constraint violation on name' } },
    })
    await wrapper.vm.saveTemplate()
    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'warning', title: 'Name Already Exists' })
    )
  })

  it('shows generic error toast on 400 with unrelated detail', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: { status: 400, data: { detail: 'Invalid role value.' } },
    })
    await wrapper.vm.saveTemplate()
    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error', title: 'Error' })
    )
  })

  it('shows generic error toast on 500', async () => {
    api.templates.create.mockRejectedValueOnce({
      response: { status: 500, data: { detail: 'Internal server error' } },
    })
    await wrapper.vm.saveTemplate()
    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error', title: 'Error' })
    )
  })

  it('shows generic error toast on network failure (no response)', async () => {
    api.templates.create.mockRejectedValueOnce(new Error('Network Error'))
    await wrapper.vm.saveTemplate()
    expect(mockShowToast).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error', title: 'Error' })
    )
  })
})

// ---------------------------------------------------------------------------
// Group 14 — duplicateTemplate() (from existing tests/components spec)
// ---------------------------------------------------------------------------

describe('TemplateManager — duplicateTemplate()', () => {
  let wrapper

  beforeEach(async () => {
    mockShowToast = vi.fn()
    wrapper = mountTemplateManager()
  })

  it('sets custom_suffix to empty string', () => {
    const tpl = makeTemplate({ custom_suffix: 'old-suffix' })
    wrapper.vm.duplicateTemplate(tpl)
    expect(wrapper.vm.editingTemplate.custom_suffix).toBe('')
  })

  it('sets display name to "<original name> (Copy)"', () => {
    const tpl = makeTemplate({ name: 'My Analyzer' })
    wrapper.vm.duplicateTemplate(tpl)
    expect(wrapper.vm.editingTemplate.name).toBe('My Analyzer (Copy)')
  })

  it('sets id to null', () => {
    const tpl = makeTemplate({ id: 99 })
    wrapper.vm.duplicateTemplate(tpl)
    expect(wrapper.vm.editingTemplate.id).toBeNull()
  })

  it('opens the edit dialog', () => {
    const tpl = makeTemplate()
    wrapper.vm.duplicateTemplate(tpl)
    expect(wrapper.vm.editDialog).toBe(true)
  })
})
