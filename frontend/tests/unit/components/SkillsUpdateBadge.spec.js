import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick, defineComponent, h } from 'vue'
import SkillsUpdateBadge from '@/components/navigation/SkillsUpdateBadge.vue'

// Mock the composable
const mockCheckServerVersion = vi.fn()
const mockDismiss = vi.fn()
const mockShowBadge = ref(false)
const mockServerVersion = ref(null)
const mockIsOutdated = ref(false)

vi.mock('@/composables/useSkillsVersion', () => ({
  useSkillsVersion: () => ({
    showBadge: mockShowBadge,
    serverVersion: mockServerVersion,
    isOutdated: mockIsOutdated,
    checkServerVersion: mockCheckServerVersion,
    dismiss: mockDismiss,
  }),
}))

// Tooltip stub that renders both slots
const TooltipStub = defineComponent({
  setup(_, { slots }) {
    return () => {
      const activator = slots.activator?.({ props: {} })
      const defaultSlot = slots.default?.()
      return h('div', { class: 'v-tooltip-stub' }, [activator, defaultSlot])
    }
  },
})

function mountBadge() {
  return mount(SkillsUpdateBadge, {
    global: {
      stubs: {
        'v-tooltip': TooltipStub,
      },
    },
  })
}

describe('SkillsUpdateBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockShowBadge.value = false
    mockServerVersion.value = null
    mockIsOutdated.value = false
  })

  it('renders nothing when showBadge is false', () => {
    const wrapper = mountBadge()
    expect(wrapper.find('.skills-badge').exists()).toBe(false)
  })

  it('renders badge when showBadge is true', async () => {
    mockShowBadge.value = true
    mockServerVersion.value = '2026.04.20'
    const wrapper = mountBadge()
    await nextTick()

    expect(wrapper.find('.skills-badge').exists()).toBe(true)
  })

  it('calls checkServerVersion on mount', () => {
    mountBadge()
    expect(mockCheckServerVersion).toHaveBeenCalledOnce()
  })

  it('shows update instruction text', async () => {
    mockShowBadge.value = true
    mockServerVersion.value = '2026.04.20'
    const wrapper = mountBadge()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('giljo_setup')
    expect(text).toContain('New skills available')
  })

  it('has dismiss button', async () => {
    mockShowBadge.value = true
    mockServerVersion.value = '2026.04.20'
    const wrapper = mountBadge()
    await nextTick()

    const dismissBtn = wrapper.find('[data-testid="skills-dismiss-btn"]')
    expect(dismissBtn.exists()).toBe(true)
  })

  it('dismiss button calls dismiss with server version', async () => {
    mockShowBadge.value = true
    mockServerVersion.value = '2026.04.20'
    const wrapper = mountBadge()
    await nextTick()

    const dismissBtn = wrapper.find('[data-testid="skills-dismiss-btn"]')
    await dismissBtn.trigger('click')

    expect(mockDismiss).toHaveBeenCalledWith('2026.04.20')
  })

  it('badge element has correct accessibility attributes', async () => {
    mockShowBadge.value = true
    mockServerVersion.value = '2026.04.20'
    const wrapper = mountBadge()
    await nextTick()

    const badge = wrapper.find('.skills-badge')
    expect(badge.attributes('role')).toBe('status')
    expect(badge.attributes('tabindex')).toBe('0')
    expect(badge.attributes('aria-label')).toBe('New agent skills available')
  })
})
