/**
 * AiToolConfigWizard.vue + AiToolGeneratePanel.vue — Split Rail redesign (FE-6259a).
 *
 * Integration coverage against the REAL AiToolGeneratePanel (not stubbed):
 *   - Route switching (web / cli / key) renders exactly one live artifact.
 *   - Every generated command/JSON string is byte-identical to the matching
 *     useMcpConfig generator call — the composable stays the single source
 *     of truth (ADR-001/003), never hand-composed here.
 *   - Edition gating: CE leads with the API-key route + editable server URL;
 *     SaaS shows all three routes + a read-only server URL.
 *   - Locked vocabulary: "Browser sign-in" present, "OAuth" and em dashes
 *     absent from all rendered user-facing copy.
 *   - Generic MCP / Antigravity are reachable ONLY under the API-key route.
 *   - Preserved contract: open()/openForKeyGeneration(), noActivator.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {
  generateConfigForTool,
  generateCodexEnvVar,
  buildServerUrl,
} from '@/composables/useMcpConfig'

const fetchConfigMock = vi.fn(() => Promise.resolve({ api: { ssl_enabled: false } }))
const checkEnhancedStatusMock = vi.fn(() => Promise.resolve({ mode: 'saas' }))
const createKeyMock = vi.fn(() => Promise.resolve({ data: { api_key: 'gm_sk_realkey_123' } }))

vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: (...args) => fetchConfigMock(...args),
    config: null,
  },
}))

vi.mock('@/services/setupService', () => ({
  default: {
    checkEnhancedStatus: (...args) => checkEnhancedStatusMock(...args),
  },
}))

vi.mock('@/services/api', () => ({
  default: {
    apiKeys: {
      create: (...args) => createKeyMock(...args),
    },
  },
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({ copy: vi.fn(() => Promise.resolve(true)) }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

import AiToolConfigWizard from '@/components/AiToolConfigWizard.vue'

const originalLocation = window.location

function setLocation({ protocol = 'http:', hostname = 'localhost', port = '5173' } = {}) {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...originalLocation, protocol, hostname, port, origin: `${protocol}//${hostname}:${port}` },
  })
}

function mountWizard() {
  return mount(AiToolConfigWizard, {
    global: {
      directives: {
        draggable: { mounted() {}, unmounted() {} },
      },
      stubs: {
        'v-tooltip': {
          template: '<div class="v-tooltip-stub"><slot name="activator" :props="{}"></slot><slot /></div>',
        },
        'v-expand-transition': { template: '<div><slot /></div>' },
      },
    },
  })
}

async function openWizard(opts = {}) {
  checkEnhancedStatusMock.mockResolvedValue({ mode: opts.mode || 'saas' })
  fetchConfigMock.mockResolvedValue({ api: { ssl_enabled: opts.sslEnabled === true } })
  setLocation(opts.location)
  const wrapper = mountWizard()
  await flushPromises()
  wrapper.vm.$.exposed.open()
  await flushPromises()
  return wrapper
}

async function selectRoute(wrapper, routeId) {
  await wrapper.find(`[data-testid="route-rail-${routeId}"]`).trigger('click')
  await flushPromises()
}

async function pickTool(wrapper, toolId) {
  await wrapper.find(`[data-testid="tool-pick-${toolId}"]`).trigger('click')
  await flushPromises()
}

function commandText(wrapper) {
  return wrapper.find('[data-testid="config-command"]').text()
}

describe('AiToolConfigWizard.vue — Split Rail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
  })

  describe('Web & app route', () => {
    it('shows the single live artifact: a copyable MCP server URL', async () => {
      const wrapper = await openWizard()
      const urlBlock = wrapper.find('[data-testid="web-url-display"]')
      expect(urlBlock.exists()).toBe(true)
      const expectedUrl = `${buildServerUrl({ host: 'localhost', port: null, protocol: 'http' })}/mcp`
      expect(urlBlock.text()).toContain(expectedUrl)
    })

    it('has no tool picker (one URL works for every connector)', async () => {
      const wrapper = await openWizard()
      expect(wrapper.find('[data-testid="rail-tools"]').exists()).toBe(false)
    })
  })

  describe('Terminal / CLI route', () => {
    it('emits the browser-sign-in command for Claude that matches useMcpConfig exactly', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'cli')
      const expected = generateConfigForTool('claude', buildServerUrl({ host: 'localhost', port: null, protocol: 'http' }), '', { authMethod: 'oauth', selfSigned: false })
      expect(commandText(wrapper)).toBe(expected)
      expect(commandText(wrapper)).not.toContain('Bearer')
    })

    it('produces the matching command for Codex and Gemini too', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'cli')
      const url = buildServerUrl({ host: 'localhost', port: null, protocol: 'http' })

      await pickTool(wrapper, 'codex')
      expect(commandText(wrapper)).toBe(generateConfigForTool('codex', url, '', { authMethod: 'oauth', selfSigned: false }))

      await pickTool(wrapper, 'gemini')
      expect(commandText(wrapper)).toBe(generateConfigForTool('gemini', url, '', { authMethod: 'oauth', selfSigned: false }))
    })

    it('never shows Generic MCP or Antigravity as pickable tools', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'cli')
      expect(wrapper.find('[data-testid="tool-pick-generic_mcp"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="tool-pick-antigravity"]').exists()).toBe(false)
    })

    it('copying the command shows the copied state', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'cli')
      await wrapper.find('[data-testid="configurator-copy-btn"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="configurator-copy-btn"]').text()).toContain('Copied!')
    })
  })

  describe('API key route', () => {
    it('shows the bearer placeholder command matching useMcpConfig before a key is generated', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'key')
      const url = buildServerUrl({ host: 'localhost', port: null, protocol: 'http' })
      const expected = generateConfigForTool('claude', url, '<YOUR_API_KEY>', { authMethod: 'bearer', selfSigned: false })
      expect(commandText(wrapper)).toBe(expected)
    })

    it('injects the real key into the command after generating one', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'key')
      await wrapper.find('[data-testid="generate-key-btn"]').trigger('click')
      await flushPromises()
      expect(createKeyMock).toHaveBeenCalledTimes(1)
      const url = buildServerUrl({ host: 'localhost', port: null, protocol: 'http' })
      const expected = generateConfigForTool('claude', url, 'gm_sk_realkey_123', { authMethod: 'bearer', selfSigned: false })
      expect(commandText(wrapper)).toBe(expected)
      expect(commandText(wrapper)).not.toContain('<YOUR_API_KEY>')
    })

    it('is the ONLY route where Generic MCP and Antigravity appear, with matching JSON output', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'key')
      expect(wrapper.find('[data-testid="tool-pick-generic_mcp"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="tool-pick-antigravity"]').exists()).toBe(true)

      const url = buildServerUrl({ host: 'localhost', port: null, protocol: 'http' })
      await pickTool(wrapper, 'generic_mcp')
      expect(commandText(wrapper)).toBe(generateConfigForTool('generic_mcp', url, '<YOUR_API_KEY>', { authMethod: 'bearer', selfSigned: false }))

      await pickTool(wrapper, 'antigravity')
      expect(commandText(wrapper)).toBe(generateConfigForTool('antigravity', url, '<YOUR_API_KEY>', { authMethod: 'bearer', selfSigned: false }))
    })

    it('shows the Codex env-var block only for Codex, matching generateCodexEnvVar', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'key')
      await pickTool(wrapper, 'codex')
      const textarea = wrapper.find('textarea')
      expect(textarea.exists()).toBe(true)
      expect(textarea.attributes('model-value')).toBe(generateCodexEnvVar('', 'windows'))

      await pickTool(wrapper, 'claude')
      // Claude has no env-var affordance (bearer key travels inline in the command).
      expect(wrapper.findAll('textarea').length).toBe(0)
    })
  })

  describe('Edition gating', () => {
    it('SaaS: shows all three routes and a read-only server URL chip', async () => {
      const wrapper = await openWizard({ mode: 'saas' })
      expect(wrapper.find('[data-testid="route-rail-web"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="route-rail-cli"]').exists()).toBe(true)
      await selectRoute(wrapper, 'key')
      expect(wrapper.find('[data-testid="server-url-chip"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="server-url-edit"]').exists()).toBe(false)
    })

    it('CE: hides Web & app and Terminal/CLI, leads with an editable API-key route', async () => {
      const wrapper = await openWizard({ mode: 'ce' })
      expect(wrapper.find('[data-testid="route-rail-web"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="route-rail-cli"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="pane-key"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="server-url-edit"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="server-url-chip"]').exists()).toBe(false)
    })

    it('CE: surfaces the self-signed cert-trust step for Node CLIs under the API-key route (not stranded)', async () => {
      const wrapper = await openWizard({ mode: 'ce', sslEnabled: true, location: { protocol: 'https:' } })
      // Node-based tool (claude) on CE, backend serving self-signed HTTPS, browser on HTTPS.
      expect(wrapper.text()).toContain('self-signed certificates')
    })

    it('SaaS never shows the cert-trust step (CE-only concern)', async () => {
      const wrapper = await openWizard({ mode: 'saas', sslEnabled: true, location: { protocol: 'https:' } })
      await selectRoute(wrapper, 'key')
      expect(wrapper.text()).not.toContain('self-signed certificates')
    })
  })

  describe('Locked vocabulary + design discipline', () => {
    it('never renders the word "OAuth" anywhere, across every route', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'cli')
      await selectRoute(wrapper, 'key')
      expect(wrapper.text()).not.toContain('OAuth')
    })

    it('labels the recommended CLI path "Browser sign-in"', async () => {
      const wrapper = await openWizard()
      expect(wrapper.text()).toContain('Browser sign-in')
    })

    it('contains no em dashes in any rendered copy', async () => {
      const wrapper = await openWizard()
      await selectRoute(wrapper, 'cli')
      await selectRoute(wrapper, 'key')
      expect(wrapper.text()).not.toContain('—')
    })
  })

  describe('Preserved contract', () => {
    it('exposes openForKeyGeneration, landing directly on the API-key route', async () => {
      checkEnhancedStatusMock.mockResolvedValue({ mode: 'saas' })
      const wrapper = mountWizard()
      await flushPromises()
      wrapper.vm.$.exposed.openForKeyGeneration()
      await flushPromises()
      expect(wrapper.find('[data-testid="pane-key"]').exists()).toBe(true)
    })

    it('keeps the configurator-modal testid on the top-level card', async () => {
      const wrapper = await openWizard()
      expect(wrapper.find('[data-testid="configurator-modal"]').exists()).toBe(true)
    })
  })
})
