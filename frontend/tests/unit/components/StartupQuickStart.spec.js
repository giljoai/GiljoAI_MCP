import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import StartupQuickStart from '../settings/StartupQuickStart.vue'

const pushMock = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

describe('StartupQuickStart', () => {
  beforeEach(() => {
    pushMock.mockReset()
  })

  it('renders steps and includes an MCP HTTP snippet', () => {
    const wrapper = mount(StartupQuickStart, {
      global: {
        stubs: {
          'v-alert': true,
          'v-row': true,
          'v-col': true,
          'v-card': true,
          'v-card-title': true,
          'v-card-subtitle': true,
          'v-card-text': true,
          'v-card-actions': true,
          'v-btn': true,
          'v-icon': true,
          'v-chip': true,
          'v-checkbox': true,
          'v-checkbox-btn': true,
          'v-list': true,
          'v-list-item': true,
          'v-list-item-title': true,
          'v-list-item-subtitle': true,
          'v-avatar': true,
          'v-dialog': true,
          'v-spacer': true,
          'v-tooltip': true,
          ToolConfigSnippet: true,
        },
      },
    })

    expect(wrapper.vm.steps.length).toBeGreaterThan(0)

    // Ensure the computed snippet has expected essentials
    expect(wrapper.vm.mcpHttpSnippet).toContain('/mcp')
    expect(wrapper.vm.mcpHttpSnippet).toContain('X-API-Key')
  })

  it('navigates to UserSettings Integrations tab action', () => {
    const wrapper = mount(StartupQuickStart, {
      global: {
        stubs: {
          'v-alert': true,
          'v-row': true,
          'v-col': true,
          'v-card': true,
          'v-card-title': true,
          'v-card-subtitle': true,
          'v-card-text': true,
          'v-card-actions': true,
          'v-btn': true,
          'v-icon': true,
          'v-chip': true,
          'v-checkbox': true,
          'v-checkbox-btn': true,
          'v-list': true,
          'v-list-item': true,
          'v-list-item-title': true,
          'v-list-item-subtitle': true,
          'v-avatar': true,
          'v-dialog': true,
          'v-spacer': true,
          'v-tooltip': true,
          ToolConfigSnippet: true,
        },
      },
    })

    wrapper.vm.runAction({ type: 'userSettingsTab', tab: 'integrations' })

    expect(pushMock).toHaveBeenCalledWith({ name: 'UserSettings', query: { tab: 'integrations' } })
  })
})
