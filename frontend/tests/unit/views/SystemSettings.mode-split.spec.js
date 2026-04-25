/**
 * SEC-0005a: SystemSettings tab visibility by GILJO_MODE.
 *
 * Role and mode are orthogonal:
 *   - Role (admin) controls what you can do within your tenant.
 *   - Mode (ce/demo/saas) controls what the product exposes.
 *
 * Server-admin tabs (Network, Database, Security) are visible only in CE mode.
 * Product-admin tabs (Identity, Prompts) are always visible to admins.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'

// Mock configService so useSaasMode resolves the mode we want for each test
const _mode = { value: 'ce' }
vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn(() => Promise.resolve()),
    getGiljoMode: vi.fn(() => _mode.value),
    getEdition: vi.fn(() => 'community'),
    config: null,
  },
}))

// Mock api service used by SystemSettings
vi.mock('@/services/api', () => ({
  default: {
    settings: {
      getCookieDomains: vi.fn().mockResolvedValue({ data: { domains: [] } }),
      addCookieDomain: vi.fn().mockResolvedValue({ data: { success: true } }),
      removeCookieDomain: vi.fn().mockResolvedValue({ data: { success: true } }),
    },
    system: {
      getOrchestratorPrompt: vi
        .fn()
        .mockResolvedValue({ data: { content: 'p', is_override: false } }),
    },
  },
}))

const defaultStubs = {
  DatabaseConnection: { template: '<div data-test="db-stub">DB</div>' },
  NetworkSettingsTab: { template: '<div data-test="network-stub">Network</div>' },
  SecuritySettingsTab: { template: '<div data-test="security-stub">Security</div>' },
  SystemPromptTab: { template: '<div data-test="prompts-stub">Prompts</div>' },
  IdentityTab: { template: '<div data-test="identity-stub">Identity</div>' },
}

describe('SystemSettings.vue -- SEC-0005a mode split', () => {
  let vuetify
  let router
  let pinia

  beforeEach(async () => {
    vi.resetModules()
    vuetify = createVuetify({ components, directives })
    pinia = createPinia()
    setActivePinia(pinia)
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'Dashboard', component: { template: '<div />' } },
        { path: '/admin/settings', name: 'SystemSettings', component: { template: '<div />' } },
      ],
    })

    global.fetch = vi.fn((url) => {
      if (typeof url === 'string' && url.includes('/api/v1/config/database')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ database: { host: 'localhost', port: 5432 } }),
        })
      }
      if (typeof url === 'string' && url.includes('/api/v1/config')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            services: {
              external_host: 'localhost',
              api: { port: 7272 },
              frontend: { port: 7274 },
            },
            security: { cors: { allowed_origins: [] } },
          }),
        })
      }
      return Promise.resolve({ ok: true, json: async () => ({}) })
    })

    _mode.value = 'ce'
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  async function mountView() {
    const { default: SystemSettings } = await import('@/views/SystemSettings.vue')
    return mount(SystemSettings, {
      global: {
        plugins: [vuetify, router, pinia],
        stubs: defaultStubs,
      },
    })
  }

  it('CE mode: renders all 5 pill toggles (Identity, Network, Database, Security, Prompts)', async () => {
    _mode.value = 'ce'
    const wrapper = await mountView()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Identity')
    expect(text).toContain('Network')
    expect(text).toContain('Database')
    expect(text).toContain('Security')
    expect(text).toContain('Prompts')

    expect(wrapper.find('[data-test="network-tab"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="database-tab"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="security-tab"]').exists()).toBe(true)
  })

  it('demo mode: renders only Identity and Prompts pills, hides Network/Database/Security', async () => {
    _mode.value = 'demo'
    const wrapper = await mountView()
    await flushPromises()

    expect(wrapper.find('[data-test="network-tab"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="database-tab"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="security-tab"]').exists()).toBe(false)

    // Product-admin tabs still present
    expect(wrapper.find('[data-test="identity-tab"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Prompts')
  })

  it('saas mode: renders only Identity and Prompts pills, hides server-admin tabs', async () => {
    _mode.value = 'saas'
    const wrapper = await mountView()
    await flushPromises()

    expect(wrapper.find('[data-test="network-tab"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="database-tab"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="security-tab"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="identity-tab"]').exists()).toBe(true)
  })

  it('demo mode: default active tab falls back to identity (never a hidden tab)', async () => {
    _mode.value = 'demo'
    const wrapper = await mountView()
    await flushPromises()

    expect(wrapper.vm.activeTab).toBe('identity')
  })
})
