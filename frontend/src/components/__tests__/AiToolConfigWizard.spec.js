/**
 * AiToolConfigWizard.vue — Split Rail shell (FE-6259a).
 *
 * Verifies the LEFT rail (route picker + contextual tool picker) and edition
 * gating owned by the wizard shell itself. AiToolGeneratePanel is stubbed so
 * these tests focus only on route/tool selection state, not artifact content
 * (that is covered by tests/components/AiToolConfigWizard.spec.js against the
 * real panel).
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ---------- Stub heavy dependencies ----------

vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn().mockResolvedValue({
      api: { host: 'localhost', port: '7272', protocol: 'http', ssl_enabled: false },
    }),
  },
}))

let mockMode = 'saas'
vi.mock('@/services/setupService', () => ({
  default: {
    checkEnhancedStatus: vi.fn().mockImplementation(() => Promise.resolve({ mode: mockMode })),
  },
}))

// useMcpConfig is consumed REAL — AUTH_CAPABILITIES drives which tools are
// offered under the Terminal/CLI route (supports_oauth === true only).

// The generate panel is a separate, dedicated component — stub it to a
// marker so we test only the rail here.
vi.mock('@/components/AiToolGeneratePanel.vue', () => ({
  default: {
    name: 'AiToolGeneratePanel',
    props: ['route', 'selectedTool', 'selectedRow', 'isCe', 'backendConfig'],
    template: '<div class="generate-panel-stub" :data-route="route" :data-tool="selectedTool" />',
  },
}))

const globalStubs = {
  // Render the dialog's default slot unconditionally so the rail is mounted.
  'v-dialog': { template: '<div><slot /></div>' },
  'v-card': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-icon': { template: '<i class="v-icon-stub"><slot /></i>' },
  'v-img': { template: '<span class="v-img-stub" />' },
  'v-btn': { template: '<button class="v-btn-stub" @click="$emit(\'click\', $event)"><slot /></button>', emits: ['click'] },
}

async function mountWizard(mode = 'saas') {
  mockMode = mode
  const AiToolConfigWizard = (await import('@/components/AiToolConfigWizard.vue')).default
  const wrapper = mount(AiToolConfigWizard, {
    global: { stubs: globalStubs },
    directives: { draggable: {} },
  })
  await flushPromises() // onMounted: loadBackendConfig + loadModeFlag
  return wrapper
}

beforeEach(() => {
  mockMode = 'saas'
})

// -----------------------------------------------------------------------

describe('AiToolConfigWizard — Split Rail: SaaS route picker', () => {
  it('renders all three connection routes', async () => {
    const wrapper = await mountWizard('saas')
    expect(wrapper.find('[data-testid="route-rail-web"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="route-rail-cli"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="route-rail-key"]').exists()).toBe(true)
  })

  it('defaults to the Web & app route with no tool picker', async () => {
    const wrapper = await mountWizard('saas')
    expect(wrapper.find('[data-testid="route-rail-web"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.find('.generate-panel-stub').attributes('data-route')).toBe('web')
    expect(wrapper.find('[data-testid="rail-tools"]').exists()).toBe(false)
  })

  it('switching to Terminal/CLI shows only browser-sign-in-capable tools', async () => {
    const wrapper = await mountWizard('saas')
    await wrapper.find('[data-testid="route-rail-cli"]').trigger('click')
    expect(wrapper.find('.generate-panel-stub').attributes('data-route')).toBe('cli')
    expect(wrapper.find('[data-testid="tool-pick-claude"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tool-pick-codex"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tool-pick-gemini"]').exists()).toBe(true)
    // Key-only tools never appear under Terminal/CLI.
    expect(wrapper.find('[data-testid="tool-pick-antigravity"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="tool-pick-generic_mcp"]').exists()).toBe(false)
  })

  it('switching to API key shows every tool, including Generic MCP and Antigravity', async () => {
    const wrapper = await mountWizard('saas')
    await wrapper.find('[data-testid="route-rail-key"]').trigger('click')
    expect(wrapper.find('.generate-panel-stub').attributes('data-route')).toBe('key')
    for (const id of ['claude', 'codex', 'gemini', 'antigravity', 'generic_mcp']) {
      expect(wrapper.find(`[data-testid="tool-pick-${id}"]`).exists()).toBe(true)
    }
  })

  it('remembers the last tool picked per route', async () => {
    const wrapper = await mountWizard('saas')
    await wrapper.find('[data-testid="route-rail-key"]').trigger('click')
    await wrapper.find('[data-testid="tool-pick-antigravity"]').trigger('click')
    expect(wrapper.find('.generate-panel-stub').attributes('data-tool')).toBe('antigravity')

    await wrapper.find('[data-testid="route-rail-cli"]').trigger('click')
    // CLI route keeps its own (still-default) tool selection, unaffected by key route's pick.
    expect(wrapper.find('.generate-panel-stub').attributes('data-tool')).toBe('claude')

    await wrapper.find('[data-testid="route-rail-key"]').trigger('click')
    expect(wrapper.find('.generate-panel-stub').attributes('data-tool')).toBe('antigravity')
  })

  it('no em dashes appear in the rail copy', async () => {
    const wrapper = await mountWizard('saas')
    expect(wrapper.text()).not.toContain('—')
  })

  it('never renders the word OAuth in rail copy — Browser sign-in is the label', async () => {
    const wrapper = await mountWizard('saas')
    expect(wrapper.text()).not.toContain('OAuth')
    expect(wrapper.text()).toContain('Browser sign-in')
  })
})

// -----------------------------------------------------------------------

describe('AiToolConfigWizard — Split Rail: CE API-key-only gating (FE-6242 lineage)', () => {
  it('CE: hides the Web & app and Terminal/CLI routes entirely', async () => {
    const wrapper = await mountWizard('ce')
    expect(wrapper.find('[data-testid="route-rail-web"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="route-rail-cli"]').exists()).toBe(false)
  })

  it('CE: leads with the API-key route, selected by default', async () => {
    const wrapper = await mountWizard('ce')
    expect(wrapper.find('[data-testid="route-rail-key"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="route-rail-key"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.find('.generate-panel-stub').attributes('data-route')).toBe('key')
  })

  it('CE: the API-key tool picker still lists every tool', async () => {
    const wrapper = await mountWizard('ce')
    for (const id of ['claude', 'codex', 'gemini', 'antigravity', 'generic_mcp']) {
      expect(wrapper.find(`[data-testid="tool-pick-${id}"]`).exists()).toBe(true)
    }
  })
})

// -----------------------------------------------------------------------

describe('AiToolConfigWizard — openForKeyGeneration + noActivator (preserved contract)', () => {
  it('exposes openForKeyGeneration as a callable method that lands on the API-key route', async () => {
    const AiToolConfigWizard = (await import('@/components/AiToolConfigWizard.vue')).default
    const wrapper = mount(AiToolConfigWizard, {
      global: { stubs: globalStubs },
      directives: { draggable: {} },
    })
    await flushPromises()
    expect(typeof wrapper.vm.openForKeyGeneration).toBe('function')
    wrapper.vm.openForKeyGeneration()
    await flushPromises()
    expect(wrapper.find('.generate-panel-stub').attributes('data-route')).toBe('key')
  })

  it('exposes open as a callable method', async () => {
    const AiToolConfigWizard = (await import('@/components/AiToolConfigWizard.vue')).default
    const wrapper = mount(AiToolConfigWizard, {
      global: { stubs: globalStubs },
      directives: { draggable: {} },
    })
    await flushPromises()
    expect(typeof wrapper.vm.open).toBe('function')
  })

  it('noActivator prop suppresses the activator pill button', async () => {
    const AiToolConfigWizard = (await import('@/components/AiToolConfigWizard.vue')).default
    const withActivator = mount(AiToolConfigWizard, {
      global: { stubs: { ...globalStubs, 'v-dialog': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' } } },
      directives: { draggable: {} },
    })
    await flushPromises()
    expect(withActivator.find('.configurator-pill').exists()).toBe(true)

    const noActivator = mount(AiToolConfigWizard, {
      props: { noActivator: true },
      global: { stubs: { ...globalStubs, 'v-dialog': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' } } },
      directives: { draggable: {} },
    })
    await flushPromises()
    expect(noActivator.find('.configurator-pill').exists()).toBe(false)
  })
})
