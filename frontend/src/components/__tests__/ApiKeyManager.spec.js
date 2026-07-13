/**
 * ApiKeyManager.spec.js — FE-6242
 *
 * Tests the "Configurator" pill button added to the API Keys header and the
 * AiToolConfigWizard integration. Edition scope: Both.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// AiToolConfigWizard is a complex child — stub it so these tests focus on
// ApiKeyManager's own UI: the Configurator button and the wizard ref wiring.
vi.mock('@/components/AiToolConfigWizard.vue', () => ({
  default: {
    name: 'AiToolConfigWizard',
    props: { noActivator: Boolean },
    template: '<div class="wizard-stub" />',
    // Expose the tracked method as a component instance method so the parent
    // ref call can be validated.
    setup() {
      return {
        openForKeyGeneration: vi.fn(),
      }
    },
  },
}))

// BaseDialog is used for the revoke confirmation — stub it.
vi.mock('@/components/common/BaseDialog.vue', () => ({
  default: { name: 'BaseDialog', template: '<div class="base-dialog-stub"><slot /></div>' },
}))

vi.mock('@/composables/useFormatDate', () => ({
  useFormatDate: () => ({ formatDateTime: (d) => String(d) }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

// api mock (global setup already provides this, but ensure apiKeys is present)
vi.mock('@/services/api', () => ({
  default: {
    apiKeys: {
      list: vi.fn().mockResolvedValue({ data: [] }),
      delete: vi.fn().mockResolvedValue({ data: {} }),
    },
  },
}))

const globalStubs = {
  'v-icon': { template: '<i class="v-icon-stub"><slot /></i>' },
  'v-btn': {
    template: '<button class="v-btn-stub" v-bind="$attrs" @click="$emit(\'click\', $event)"><slot /></button>',
    emits: ['click'],
  },
  'v-card': { template: '<div class="v-card-stub"><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-chip': { template: '<span class="v-chip-stub"><slot /></span>' },
  'v-tooltip': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' },
  'v-alert': { template: '<div class="v-alert-stub"><slot /></div>' },
  'v-data-table': { template: '<div class="v-data-table-stub" />' },
}

async function mountManager() {
  const ApiKeyManager = (await import('@/components/ApiKeyManager.vue')).default
  const wrapper = mount(ApiKeyManager, {
    global: { stubs: globalStubs },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
})

// -----------------------------------------------------------------------

describe('ApiKeyManager — Configurator pill button (FE-6242)', () => {
  it('renders the Configurator button in the header', async () => {
    const wrapper = await mountManager()
    // The button is identified by data-testid="apikey-configurator-btn"
    const btn = wrapper.find('[data-testid="apikey-configurator-btn"]')
    expect(btn.exists()).toBe(true)
  })

  it('renders the AiToolConfigWizard with noActivator=true', async () => {
    const wrapper = await mountManager()
    const wizard = wrapper.findComponent({ name: 'AiToolConfigWizard' })
    expect(wizard.exists()).toBe(true)
    expect(wizard.props('noActivator')).toBe(true)
  })

  it('calls openForKeyGeneration on the wizard when the button is clicked', async () => {
    const wrapper = await mountManager()
    const btn = wrapper.find('[data-testid="apikey-configurator-btn"]')
    await btn.trigger('click')
    // wizard ref's openForKeyGeneration should have been called
    const wizard = wrapper.findComponent({ name: 'AiToolConfigWizard' })
    expect(wizard.vm.openForKeyGeneration).toHaveBeenCalledOnce()
  })
})
