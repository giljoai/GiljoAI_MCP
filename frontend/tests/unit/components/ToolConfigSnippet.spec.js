import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock the clipboard composable
const mockCopy = vi.fn().mockResolvedValue(true)
vi.mock('@/composables/useClipboard', () => ({
  useClipboard: () => ({
    copy: mockCopy,
    copied: { value: false },
    isSupported: { value: true },
    error: { value: null },
    reset: vi.fn(),
  }),
}))

import ToolConfigSnippet from '@/components/ToolConfigSnippet.vue'

describe('ToolConfigSnippet', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    wrapper = mount(ToolConfigSnippet, {
      props: {
        language: 'json',
        config: '{"key": "test_api_key"}'
      }
    })
  })

  it('renders config snippet with correct language', () => {
    const codeBlock = wrapper.find('[data-test="config-snippet"]')
    expect(codeBlock.exists()).toBe(true)
    expect(codeBlock.text()).toContain('test_api_key')
  })

  it('copies config to clipboard when copy button clicked', async () => {
    const copyButton = wrapper.find('[data-test="copy-button"]')
    await copyButton.trigger('click')

    expect(mockCopy).toHaveBeenCalledWith('{"key": "test_api_key"}')
    expect(wrapper.vm.copySuccess).toBe(true)
  })

  it('handles different language configs', async () => {
    await wrapper.setProps({
      language: 'toml',
      config: 'key = "test_api_key"'
    })

    const codeBlock = wrapper.find('[data-test="config-snippet"]')
    expect(codeBlock.text()).toContain('test_api_key')
    expect(wrapper.vm.language).toBe('toml')
  })

  it('shows success message after copying', async () => {
    const copyButton = wrapper.find('[data-test="copy-button"]')
    await copyButton.trigger('click')

    const successMessage = wrapper.find('[data-test="copy-success"]')
    expect(successMessage.exists()).toBe(true)
  })
})
