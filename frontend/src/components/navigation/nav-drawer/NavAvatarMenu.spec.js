/**
 * NavAvatarMenu.spec.js — FE-6006 unit 3a
 *
 * Smoke tests: avatar renders, user info shows, key menu items present.
 * Edition scope: Both
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import NavAvatarMenu from './NavAvatarMenu.vue'

vi.mock('@/i18n/licenseCopy', () => ({
  getLicenseCopy: vi.fn(() => ({
    editionLabel: 'Community Edition',
    longDescription: 'Test description',
  })),
}))

vi.mock('@/services/configService', () => ({
  default: {
    fetchConfig: vi.fn().mockResolvedValue({}),
    getEdition: vi.fn().mockReturnValue('community'),
    getGiljoMode: vi.fn().mockReturnValue('ce'),
    getVersion: vi.fn().mockReturnValue('1.0.0'),
  },
}))

vi.mock('@/services/setupService', () => ({
  default: {
    checkEnhancedStatus: vi.fn().mockResolvedValue({ total_users_count: 1 }),
  },
}))

const globalStubs = {
  'v-icon': { template: '<i class="v-icon"><slot /></i>' },
  'v-menu': { template: '<div class="v-menu"><slot name="activator" :props="{}" /><slot /></div>' },
  'v-list': { template: '<ul class="v-list"><slot /></ul>' },
  'v-list-item': { props: ['title', 'to', 'prependIcon'], template: '<li class="v-list-item" v-bind="$attrs" :title="title">{{ title }}<slot /></li>' },
  'v-list-item-title': { template: '<div class="v-list-item-title"><slot /></div>' },
  'v-list-item-subtitle': { template: '<div class="v-list-item-subtitle"><slot /></div>' },
  'v-divider': { template: '<hr class="v-divider" />' },
  'v-dialog': { template: '<div class="v-dialog"><slot /></div>' },
  'v-card': { template: '<div class="v-card"><slot /></div>' },
  'v-card-text': { template: '<div class="v-card-text"><slot /></div>' },
  'v-btn': { template: '<button class="v-btn" v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>' },
  'v-chip': { template: '<span class="v-chip"><slot /></span>' },
  'RoleBadge': { template: '<span />' },
  'BaseDialog': { template: '<div />' },
  'ConnectionDebugDialog': { template: '<div />' },
}

describe('NavAvatarMenu', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const baseProps = {
    currentUser: { username: 'patrik', email: 'patrik@example.com', role: 'admin' },
    giljoMode: 'ce',
    userInitials: 'PA',
    accountBadgeState: 'none',
    isAccountScheduledForDeletion: false,
    accountBadgeStateModifier: 'none',
    accountStatusTitle: '',
    accountStatusSubtitle: '',
    cancellingDeletion: false,
    AccountStatusBadgeComponent: null,
    isAdmin: true,
  }

  function mountMenu(props = {}) {
    return mount(NavAvatarMenu, {
      props: { ...baseProps, ...props },
      global: { stubs: globalStubs },
    })
  }

  it('renders the avatar orb', () => {
    const wrapper = mountMenu()
    expect(wrapper.find('.nav-orb--avatar').exists()).toBe(true)
  })

  it('shows user initials in the orb', () => {
    const wrapper = mountMenu()
    expect(wrapper.find('.nav-orb-initials').text()).toBe('PA')
  })

  it('shows Account / Profile menu item', () => {
    const wrapper = mountMenu()
    expect(wrapper.text()).toContain('Account / Profile')
  })

  it('shows Logout menu item when currentUser is set', () => {
    const wrapper = mountMenu()
    expect(wrapper.text()).toContain('Logout')
  })

  it('shows Admin Settings item in CE mode for admin', () => {
    const wrapper = mountMenu({ isAdmin: true, giljoMode: 'ce' })
    expect(wrapper.text()).toContain('Admin Settings')
  })

  it('hides Admin Settings item in SaaS mode', () => {
    const wrapper = mountMenu({ isAdmin: true, giljoMode: 'saas' })
    expect(wrapper.text()).not.toContain('Admin Settings')
  })

  it('emits logout when Logout item is clicked', async () => {
    const wrapper = mountMenu()
    const logoutItem = wrapper.findAll('.v-list-item').find(el => el.text().includes('Logout'))
    await logoutItem.trigger('click')
    expect(wrapper.emitted('logout')).toBeTruthy()
  })
})
