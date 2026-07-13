/**
 * Tests for the Download My Data section on the account Danger Zone page.
 *
 * BE-5062 — GDPR data portability. The section must:
 *   - render in CE (edition === 'community')
 *   - render in SaaS when the current user is an org admin
 *   - be hidden in SaaS when the current user is NOT an org admin
 *   - be hidden when edition is not 'community' and user is not an admin
 *   - call api.account.exportMyData() when the user clicks Generate Export
 *   - reflect WebSocket `tenant:export_progress` events in the UI
 *   - surface the download link when the export completes
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// ---------- Module mocks ----------

// Capture the on-handlers so the test can simulate WebSocket events.
const wsHandlers = new Map()
function emitWsEvent(type, payload) {
  const set = wsHandlers.get(type)
  if (set) set.forEach((h) => h(payload))
}
const wsOnMock = vi.fn((type, handler) => {
  if (!wsHandlers.has(type)) wsHandlers.set(type, new Set())
  wsHandlers.get(type).add(handler)
  return () => wsHandlers.get(type)?.delete(handler)
})
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({ on: wsOnMock }),
}))

const exportMyDataMock = vi.fn()
vi.mock('@/services/api', () => ({
  default: {
    account: {
      exportMyData: (...args) => exportMyDataMock(...args),
    },
  },
}))

const showToastMock = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: showToastMock }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// configService.getEdition() controls edition-aware visibility (matches existing
// pattern in this file for the SaaS-only delete card).
const editionRef = { value: 'community' }
vi.mock('@/services/configService', () => ({
  default: {
    getEdition: () => editionRef.value,
  },
}))

// useUserStore exposes isAdmin; BE-5062 SaaS gate reads it for the export card.
const userIsAdminRef = { value: false }
vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    get isAdmin() {
      return userIsAdminRef.value
    },
  }),
}))

// ---------- Helper ----------

async function mountPage() {
  setActivePinia(createPinia())
  const { default: DangerPage } = await import('@/views/account/DangerPage.vue')
  return mount(DangerPage, {
    global: {
      stubs: {
        'v-icon': { template: '<i class="v-icon-stub"><slot /></i>' },
        'v-btn': {
          template:
            '<button class="v-btn-stub" :disabled="disabled || loading" @click="$emit(\'click\', $event)"><slot /></button>',
          props: ['disabled', 'loading', 'color', 'variant', 'size'],
          emits: ['click'],
        },
        'v-chip': { template: '<span class="v-chip-stub"><slot /></span>' },
        'v-progress-linear': {
          template: '<div class="v-progress-linear-stub" :data-value="modelValue" />',
          props: ['modelValue', 'indeterminate', 'color', 'height'],
        },
        // IMP-5042: the relocated orchestrator-prompt editor. Stub it so mounting
        // DangerPage as an admin doesn't trigger the real component's api.system call.
        SystemPromptTab: { template: '<div data-test="orchestrator-prompt-stub" />' },
      },
    },
  })
}

// ---------- Suite ----------

describe('DangerPage — Download My Data section (BE-5062)', () => {
  beforeEach(() => {
    wsHandlers.clear()
    wsOnMock.mockClear()
    exportMyDataMock.mockReset()
    showToastMock.mockClear()
    editionRef.value = 'community'
    userIsAdminRef.value = false
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the Download My Data section in CE (edition=community)', async () => {
    editionRef.value = 'community'
    const wrapper = await mountPage()
    await flushPromises()
    expect(wrapper.find('[data-test="download-my-data-section"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="generate-export-btn"]').exists()).toBe(true)
  })

  it('renders the section in SaaS when the user is an org admin', async () => {
    editionRef.value = 'saas'
    userIsAdminRef.value = true
    const wrapper = await mountPage()
    await flushPromises()
    expect(wrapper.find('[data-test="download-my-data-section"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="generate-export-btn"]').exists()).toBe(true)
  })

  it('hides the section in SaaS when the user is NOT an org admin', async () => {
    editionRef.value = 'saas'
    userIsAdminRef.value = false
    const wrapper = await mountPage()
    await flushPromises()
    expect(wrapper.find('[data-test="download-my-data-section"]').exists()).toBe(false)
  })

  it('hides the section when edition is non-community and user is not an admin', async () => {
    editionRef.value = 'saas'
    userIsAdminRef.value = false
    const wrapper = await mountPage()
    await flushPromises()
    expect(wrapper.find('[data-test="download-my-data-section"]').exists()).toBe(false)
  })

  it('calls api.account.exportMyData() when Generate Export is clicked', async () => {
    exportMyDataMock.mockResolvedValue({
      data: {
        download_url: '/api/download/temp/abc123/tenant_export.zip',
        expires_at: '2026-05-14T15:00:00+00:00',
        model_counts: { products: 3, projects: 2 },
      },
    })
    const wrapper = await mountPage()
    await flushPromises()

    await wrapper.find('[data-test="generate-export-btn"]').trigger('click')
    await flushPromises()

    expect(exportMyDataMock).toHaveBeenCalledTimes(1)
  })

  it('updates the progress indicator on tenant:export_progress events', async () => {
    // Keep the API call pending so the progress UI stays mounted.
    exportMyDataMock.mockImplementation(
      () =>
        new Promise(() => {
          /* never resolves during this test */
        }),
    )
    const wrapper = await mountPage()
    await flushPromises()
    await wrapper.find('[data-test="generate-export-btn"]').trigger('click')
    await flushPromises()

    emitWsEvent('tenant:export_progress', {
      type: 'tenant:export_progress',
      schema_version: '1.0',
      timestamp: '2026-05-14T14:30:00+00:00',
      data: {
        model: 'Project',
        current: 3,
        total: 10,
        records: 0,
        phase: 'exporting',
        tenant_key: 'tenant-1',
      },
    })
    await flushPromises()

    const status = wrapper.find('[data-test="export-progress-status"]')
    expect(status.exists()).toBe(true)
    // Status text should reference the current model and counts.
    expect(status.text()).toMatch(/Project/i)
    expect(status.text()).toContain('3')
    expect(status.text()).toContain('10')
  })

  // IMP-5042: the orchestrator-prompt editor moved here from the admin panel.
  // It is admin-only (its endpoints are require_admin).
  it('shows the orchestrator-prompt section for an admin', async () => {
    editionRef.value = 'community'
    userIsAdminRef.value = true
    const wrapper = await mountPage()
    await flushPromises()
    expect(wrapper.find('[data-test="orchestrator-prompt-section"]').exists()).toBe(true)
  })

  it('hides the orchestrator-prompt section for a non-admin', async () => {
    editionRef.value = 'saas'
    userIsAdminRef.value = false
    const wrapper = await mountPage()
    await flushPromises()
    expect(wrapper.find('[data-test="orchestrator-prompt-section"]').exists()).toBe(false)
  })

  it('shows a download link when the export completes', async () => {
    exportMyDataMock.mockResolvedValue({
      data: {
        download_url: '/api/download/temp/abc123/tenant_export.zip',
        expires_at: '2026-05-14T15:00:00+00:00',
        model_counts: { products: 3, projects: 2 },
      },
    })
    const wrapper = await mountPage()
    await flushPromises()
    await wrapper.find('[data-test="generate-export-btn"]').trigger('click')
    await flushPromises()

    const link = wrapper.find('[data-test="export-download-link"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('/api/download/temp/abc123/tenant_export.zip')
  })
})
