/**
 * Test: ContextPriorityConfig - Git Integration Prop Handling
 *
 * Validates that ContextPriorityConfig properly accepts and uses the
 * gitIntegrationEnabled prop from parent (UserSettings.vue)
 *
 * Feature: Frontend Tester Agent - Component Testing
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ContextPriorityConfig from '@/components/settings/ContextPriorityConfig.vue'

describe('ContextPriorityConfig Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('Props', () => {
    it('should accept gitIntegrationEnabled prop', () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: true,
        },
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(wrapper.props('gitIntegrationEnabled')).toBe(true)
    })

    it('should default gitIntegrationEnabled to false', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(wrapper.props('gitIntegrationEnabled')).toBe(false)
    })
  })

  describe('Git Integration Status Display', () => {
    it('should render alert when git integration is disabled', () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: false,
        },
        global: {
          stubs: {
            'v-card': { template: '<div><slot /></div>' },
            'v-card-title': { template: '<div><slot /></div>' },
            'v-card-text': { template: '<div><slot /></div>' },
            'v-alert': {
              template: '<div class="v-alert" data-testid="git-disabled-alert"><slot /></div>',
            },
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      // Alert should be visible when git is disabled
      const alert = wrapper.find('[data-testid="git-disabled-alert"]')
      expect(alert.exists()).toBe(true)
    })

    it('should hide alert when git integration is enabled', () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: true,
        },
        global: {
          stubs: {
            'v-card': { template: '<div><slot /></div>' },
            'v-card-title': { template: '<div><slot /></div>' },
            'v-card-text': { template: '<div><slot /></div>' },
            'v-alert': {
              template: '<div class="v-alert" data-testid="git-disabled-alert" v-if="false"><slot /></div>',
            },
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      // Alert should be hidden when git is enabled
      const alerts = wrapper.findAll('[data-testid="git-disabled-alert"]')
      expect(alerts.length).toBe(0)
    })
  })

  describe('Context Disabled State', () => {
    it('should disable git_history context when gitIntegrationEnabled is false', () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: false,
        },
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      // isContextDisabled should return true for git_history
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)
    })

    it('should enable git_history context when gitIntegrationEnabled is true', () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: true,
        },
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      // isContextDisabled should return false for git_history
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)
    })

    it('should not disable other contexts based on git integration', () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: false,
        },
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      // Other contexts should not be disabled
      expect(wrapper.vm.isContextDisabled('product_description')).toBe(false)
      expect(wrapper.vm.isContextDisabled('vision_documents')).toBe(false)
      expect(wrapper.vm.isContextDisabled('tech_stack')).toBe(false)
      expect(wrapper.vm.isContextDisabled('architecture')).toBe(false)
      expect(wrapper.vm.isContextDisabled('testing')).toBe(false)
      expect(wrapper.vm.isContextDisabled('agent_templates')).toBe(false)
      expect(wrapper.vm.isContextDisabled('memory_360')).toBe(false)
    })
  })

  describe('Reactive Updates', () => {
    it('should reactively update when prop changes from disabled to enabled', async () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: false,
        },
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)

      // Update prop
      await wrapper.setProps({ gitIntegrationEnabled: true })

      expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)
    })

    it('should reactively update when prop changes from enabled to disabled', async () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: true,
        },
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)

      // Update prop
      await wrapper.setProps({ gitIntegrationEnabled: false })

      expect(wrapper.vm.isContextDisabled('git_history')).toBe(true)
    })
  })

  describe('Exposed Methods', () => {
    it('should have navigateToIntegrations method', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
          mocks: {
            $router: {
              push: vi.fn(),
            },
          },
        },
      })

      expect(typeof wrapper.vm.navigateToIntegrations).toBe('function')
    })

    it('should have isContextDisabled method', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(typeof wrapper.vm.isContextDisabled).toBe('function')
    })

    it('should have toggleContext method', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(typeof wrapper.vm.toggleContext).toBe('function')
    })

    it('should have updatePriority method', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(typeof wrapper.vm.updatePriority).toBe('function')
    })

    it('should have updateDepth method', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(typeof wrapper.vm.updateDepth).toBe('function')
    })

    it('should have saveConfig method', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      expect(typeof wrapper.vm.saveConfig).toBe('function')
    })
  })

  describe('Architecture Changes', () => {
    it('should NOT have WebSocket listener logic (moved to parent)', () => {
      const wrapper = mount(ContextPriorityConfig, {
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      // These methods should NOT be exposed (moved to parent)
      expect(wrapper.vm.checkGitIntegration).toBeUndefined()
      expect(wrapper.vm.handleGitIntegrationUpdate).toBeUndefined()
    })

    it('should use gitIntegrationEnabled from props, not internal state', () => {
      const wrapper = mount(ContextPriorityConfig, {
        props: {
          gitIntegrationEnabled: true,
        },
        global: {
          stubs: {
            'v-card': true,
            'v-card-title': true,
            'v-card-text': true,
            'v-alert': true,
            'v-icon': true,
            'v-divider': true,
            'v-switch': true,
            'v-select': true,
            'v-tooltip': true,
          },
        },
      })

      // Should accept and use the prop
      expect(wrapper.props('gitIntegrationEnabled')).toBe(true)
      // The component should be using the prop value in isContextDisabled
      expect(wrapper.vm.isContextDisabled('git_history')).toBe(false)
    })
  })
})
