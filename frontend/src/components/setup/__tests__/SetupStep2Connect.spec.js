import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// ---------- Stub heavy dependencies ----------

// Capture the WebSocket subscription so tests can fire setup:tool_connected.
let wsHandlers = {}
vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: () => ({
    on: (event, handler) => {
      wsHandlers[event] = handler
      return () => {}
    },
  }),
}))

vi.mock('@/services/api', () => ({
  default: {
    apiKeys: {
      getActive: vi.fn().mockResolvedValue({ data: [] }),
      create: vi.fn().mockResolvedValue({ data: { api_key: 'gk_test_key_123' } }),
    },
  },
}))

// configService.fetchConfig drives edition (CE editable / SaaS read-only).
let mockGiljoMode = 'saas'
let mockSslEnabled = false
vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn().mockImplementation(() =>
      Promise.resolve({
        api: { host: 'localhost', port: '7272', protocol: mockSslEnabled ? 'https' : 'http', ssl_enabled: mockSslEnabled },
        giljo_mode: mockGiljoMode,
      }),
    ),
  },
}))

vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({ copy: vi.fn().mockResolvedValue(true) }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

// useMcpConfig is consumed REAL (not mocked) — the OAuth command generation is
// part of what we are validating.

const globalStubs = {
  'v-text-field': {
    template: '<input class="v-text-field-stub" :value="modelValue" @click="$emit(\'click\', $event)" />',
    props: ['modelValue'],
    emits: ['click', 'update:modelValue'],
  },
  'v-icon': { template: '<i class="v-icon-stub"><slot /></i>' },
  'v-btn': {
    template: '<button class="v-btn-stub" @click="$emit(\'click\', $event)"><slot /></button>',
    emits: ['click'],
  },
  'v-progress-circular': { template: '<span class="v-progress-stub" />' },
  'v-alert': { template: '<div class="v-alert-stub"><slot /></div>' },
  'v-expand-transition': { template: '<div><slot /></div>' },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' },
}

async function mountStep(selectedTools, giljoMode = 'saas') {
  mockGiljoMode = giljoMode
  const SetupStep2Connect = (await import('@/components/setup/SetupStep2Connect.vue')).default
  const wrapper = mount(SetupStep2Connect, {
    props: { selectedTools },
    global: { stubs: globalStubs },
  })
  await flushPromises() // onMounted: checkExistingKey + loadBackendConfig
  return wrapper
}

async function mountStepSsl(selectedTools, sslEnabled = false) {
  mockGiljoMode = 'saas'
  mockSslEnabled = sslEnabled
  const SetupStep2Connect = (await import('@/components/setup/SetupStep2Connect.vue')).default
  const wrapper = mount(SetupStep2Connect, {
    props: { selectedTools },
    global: { stubs: globalStubs },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  wsHandlers = {}
  mockGiljoMode = 'saas'
  mockSslEnabled = false
})

// -----------------------------------------------------------------------

describe('SetupStep2Connect — SaaS: Browser sign-in primary path (FE-6159/FE-6259b)', () => {
  it('shows "Browser sign-in" as the primary, recommended path for an OAuth-capable tool', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    const text = wrapper.text()
    expect(text).toContain('Browser sign-in')
    expect(text).toContain('Recommended')
    // Connect-vocabulary parity (FE-6259a/b, locked by P1): never the word "OAuth" in user copy.
    expect(text).not.toContain('OAuth')
    expect(text).not.toContain('—') // no em dashes anywhere in user copy
  })

  it('renders the browser-sign-in command with NO bearer token', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    const pre = wrapper.find('pre.config-code')
    expect(pre.exists()).toBe(true)
    // OAuth claude command: `claude mcp add --transport http giljo_mcp <url>/mcp --scope user`
    expect(pre.text()).toContain('claude mcp add')
    expect(pre.text()).toContain('/mcp')
    expect(pre.text()).not.toContain('Bearer')
    expect(pre.text()).not.toContain('Authorization')
  })

  it('keeps bearer behind a quiet "Use an API key instead" fallback (hidden by default)', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    expect(wrapper.text()).toContain('Use an API key instead')
    // API-key flow not shown until the fallback is toggled.
    expect(wrapper.text()).not.toContain('Generate API Key')

    const toggle = wrapper.find('.bearer-toggle-link')
    await toggle.trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('Generate API Key')
  })

  it('never surfaces the oauth_quirk_note (would leak "OAuth" into user copy)', async () => {
    // Codex's AUTH_CAPABILITIES.oauth_quirk_note literal is "OAuth auto-detected
    // on add." — P1 dropped rendering this note from the Split Rail configurator
    // (FE-6259a); this step drops it too.
    const wrapper = await mountStep(['codex_cli'], 'saas')
    expect(wrapper.find('.oauth-quirk-note').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('auto-detected')
  })

  it('treats Antigravity as key-only — no Browser sign-in section, shows the not-supported note', async () => {
    const wrapper = await mountStep(['antigravity_cli'], 'saas')
    const text = wrapper.text()
    expect(wrapper.find('[data-testid="oauth-section"]').exists()).toBe(false)
    expect(text).toContain('Browser sign-in is not supported')
    expect(text).not.toContain('OAuth')
    // Key-only tool shows the API-key flow immediately (no toggle needed).
    expect(text).toContain('Generate API Key')
  })
})

// -----------------------------------------------------------------------

describe('SetupStep2Connect — CE: API-key-only gating (FE-6242)', () => {
  it('CE: hides the browser-sign-in section for an OAuth-capable tool', async () => {
    const wrapper = await mountStep(['claude_code'], 'ce')
    // Browser sign-in section must NOT be shown on CE
    expect(wrapper.find('.oauth-section').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Browser sign-in')
  })

  it('CE: hides the "Use an API key instead" toggle link', async () => {
    const wrapper = await mountStep(['claude_code'], 'ce')
    expect(wrapper.find('.bearer-toggle-link').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Use an API key instead')
  })

  it('CE: shows the API-key flow immediately without toggling', async () => {
    const wrapper = await mountStep(['claude_code'], 'ce')
    // On CE, bearer flow is shown directly
    expect(wrapper.text()).toContain('Generate API Key')
  })

  it('CE: Antigravity (key-only) still works — key-only note shown', async () => {
    const wrapper = await mountStep(['antigravity_cli'], 'ce')
    expect(wrapper.text()).toContain('Browser sign-in is not supported')
    expect(wrapper.text()).toContain('Generate API Key')
  })

  it('CE: WS connect checker fires and marks tool connected', async () => {
    const wrapper = await mountStep(['claude_code'], 'ce')
    expect(typeof wsHandlers['setup:tool_connected']).toBe('function')

    wsHandlers['setup:tool_connected']({ tool_name: 'mcp_connected' })
    await nextTick()

    const canProceed = wrapper.emitted('can-proceed')
    expect(canProceed[canProceed.length - 1]).toEqual([true])
  })
})

// -----------------------------------------------------------------------

describe('SetupStep2Connect — connected-state gate + green-connect light', () => {
  it('starts not-connected and blocks proceeding', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    expect(wrapper.text()).toContain('Waiting for connection')
    const canProceed = wrapper.emitted('can-proceed')
    expect(canProceed).toBeTruthy()
    expect(canProceed[canProceed.length - 1]).toEqual([false])
  })

  it('flips to connected + can-proceed=true when setup:tool_connected fires', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    expect(typeof wsHandlers['setup:tool_connected']).toBe('function')

    // The MCP server emits a generic connect event — marks selected tools connected.
    wsHandlers['setup:tool_connected']({ tool_name: 'mcp_connected' })
    await nextTick()

    expect(wrapper.text()).toContain('Connected')
    const canProceed = wrapper.emitted('can-proceed')
    expect(canProceed[canProceed.length - 1]).toEqual([true])
    // step-data reports the connected tool list for the parent to persist.
    const stepData = wrapper.emitted('step-data')
    expect(stepData[stepData.length - 1][0].connectedTools).toContain('claude_code')
  })
})

// -----------------------------------------------------------------------

describe('SetupStep2Connect — server URL edition gating', () => {
  it('is editable (click reveals host/port fields) on CE', async () => {
    const wrapper = await mountStep(['claude_code'], 'ce')
    expect(wrapper.find('.server-edit-fields').exists()).toBe(false)
    const field = wrapper.find('input.v-text-field-stub')
    await field.trigger('click')
    await nextTick()
    expect(wrapper.find('.server-edit-fields').exists()).toBe(true)
  })

  it('is read-only (no edit reveal, lock icon shown) on SaaS', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    expect(wrapper.find('.server-lock-icon').exists()).toBe(true)
    const field = wrapper.find('input.v-text-field-stub')
    await field.trigger('click')
    await nextTick()
    expect(wrapper.find('.server-edit-fields').exists()).toBe(false)
  })
})

// -----------------------------------------------------------------------

describe('SetupStep2Connect — HTTPS cert-trust guidance (INF-6241)', () => {
  it('shows no cert-trust note in OAuth section when ssl_enabled is false', async () => {
    const wrapper = await mountStepSsl(['claude_code'], false)
    expect(wrapper.find('.oauth-cert-note').exists()).toBe(false)
  })

  it('shows an OAuth-section cert-trust note when ssl_enabled is true (C4 gap closure)', async () => {
    const wrapper = await mountStepSsl(['claude_code'], true)
    expect(wrapper.find('.oauth-cert-note').exists()).toBe(true)
    const text = wrapper.find('.oauth-cert-note').text()
    expect(text).toContain('HTTPS certificate trust')
    expect(text).toContain('certificate')
  })

  it('does not imply GiljoAI issued the cert in the OAuth cert note', async () => {
    const wrapper = await mountStepSsl(['claude_code'], true)
    const text = wrapper.find('.oauth-cert-note').text()
    expect(text).not.toContain('root CA')
    expect(text).not.toContain('rootCA')
    expect(text).not.toContain('mkcert')
  })
})

// -----------------------------------------------------------------------

describe('SetupStep2Connect — data-testid hook presence (FE-6247)', () => {
  it('root element carries data-testid="step2-connect"', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    expect(wrapper.find('[data-testid="step2-connect"]').exists()).toBe(true)
  })

  it('server URL field carries data-testid="server-url-field"', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    expect(wrapper.find('[data-testid="server-url-field"]').exists()).toBe(true)
  })

  it('SaaS + OAuth tool: data-testid="oauth-section" and data-testid="bearer-toggle" both present', async () => {
    const wrapper = await mountStep(['claude_code'], 'saas')
    expect(wrapper.find('[data-testid="oauth-section"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="bearer-toggle"]').exists()).toBe(true)
  })

  it('CE: data-testid="oauth-section" absent, data-testid="bearer-toggle" absent', async () => {
    const wrapper = await mountStep(['claude_code'], 'ce')
    expect(wrapper.find('[data-testid="oauth-section"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="bearer-toggle"]').exists()).toBe(false)
  })

  it('key-only tool: data-testid="apikey-only-note" present, data-testid="oauth-section" absent', async () => {
    const wrapper = await mountStep(['antigravity_cli'], 'saas')
    expect(wrapper.find('[data-testid="apikey-only-note"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="oauth-section"]').exists()).toBe(false)
  })

  it('multi-tool: each tool tab carries data-testid="tool-tab-{id}"', async () => {
    const wrapper = await mountStep(['claude_code', 'codex_cli'], 'saas')
    expect(wrapper.find('[data-testid="tool-tab-claude_code"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tool-tab-codex_cli"]').exists()).toBe(true)
  })

  it('SaaS + HTTPS: data-testid="oauth-cert-note" renders when ssl_enabled', async () => {
    const wrapper = await mountStepSsl(['claude_code'], true)
    expect(wrapper.find('[data-testid="oauth-cert-note"]').exists()).toBe(true)
  })

  it('SaaS + non-HTTPS: data-testid="oauth-cert-note" absent', async () => {
    const wrapper = await mountStepSsl(['claude_code'], false)
    expect(wrapper.find('[data-testid="oauth-cert-note"]').exists()).toBe(false)
  })
})
