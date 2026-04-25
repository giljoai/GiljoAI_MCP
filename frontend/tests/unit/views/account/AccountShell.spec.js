/**
 * FE-0023: /account shell smoke test.
 *
 * Verifies that the AccountShell renders all three sub-tabs and that each
 * sub-route renders its real (or stub) content for Profile, Billing, and
 * Danger Zone.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createPinia, setActivePinia } from 'pinia'

import AccountShell from '@/views/account/AccountShell.vue'
import ProfilePage from '@/views/account/ProfilePage.vue'
import BillingPage from '@/views/account/BillingPage.vue'
import DangerPage from '@/views/account/DangerPage.vue'

// Mock api service used by ProfilePage (avoid real network calls).
vi.mock('@/services/configService', () => ({
  default: {
    getEdition: () => 'saas',
    getGiljoMode: () => 'saas',
  },
}))

vi.mock('@/services/api', () => ({
  default: {
    auth: {
      updateUser: vi.fn().mockResolvedValue({ data: { ok: true } }),
    },
  },
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({
    currentUser: {
      id: 1,
      username: 'admin',
      role: 'admin',
      email: 'admin@test.com',
      full_name: 'Admin User',
    },
    currentOrg: null,
    orgRole: null,
  }),
}))

const RoleBadgeStub = { template: '<span class="role-badge-stub" />', props: ['role', 'size'] }

const globalStubs = {
  RoleBadge: RoleBadgeStub,
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/account',
        component: AccountShell,
        children: [
          { path: '', redirect: { name: 'AccountProfile' } },
          { path: 'profile', name: 'AccountProfile', component: ProfilePage },
          { path: 'billing', name: 'AccountBilling', component: BillingPage },
          { path: 'danger', name: 'AccountDanger', component: DangerPage },
        ],
      },
    ],
  })
}

describe('AccountShell.vue', () => {
  let vuetify
  let pinia
  let router

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
    pinia = createPinia()
    setActivePinia(pinia)
    router = makeRouter()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders the shell page header and three sub-tab pills', async () => {
    await router.push('/account/profile')
    await router.isReady()

    const wrapper = mount(AccountShell, {
      global: {
        plugins: [vuetify, router, pinia],
        stubs: globalStubs,
      },
    })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Account')
    expect(text).toContain('Profile')
    expect(text).toContain('Billing')
    expect(text).toContain('Danger Zone')

    expect(wrapper.find('[data-test="account-profile-tab"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="account-billing-tab"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="account-danger-tab"]').exists()).toBe(true)
  })

  it('renders Profile content at /account/profile', async () => {
    await router.push('/account/profile')
    await router.isReady()

    const wrapper = mount(AccountShell, {
      global: {
        plugins: [vuetify, router, pinia],
        stubs: globalStubs,
      },
    })
    await flushPromises()

    // Save button is the unique data-test on ProfilePage.
    const saveBtn = wrapper.find('[data-test="save-profile-btn"]')
    expect(saveBtn.exists()).toBe(true)
  })

  it('renders Billing stub at /account/billing', async () => {
    await router.push('/account/billing')
    await router.isReady()

    const wrapper = mount(AccountShell, {
      global: {
        plugins: [vuetify, router, pinia],
        stubs: globalStubs,
      },
    })
    await flushPromises()

    expect(wrapper.find('[data-test="billing-stub"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Plan management coming with Solo launch')
  })

  it('renders Danger Zone at /account/danger with the SAAS-022 redesigned cards', async () => {
    await router.push('/account/danger')
    await router.isReady()

    const wrapper = mount(AccountShell, {
      global: {
        plugins: [vuetify, router, pinia],
        stubs: {
          ...globalStubs,
          // The lazy SaaS-only modal is irrelevant to this shell smoke test.
          DeleteAccountDialog: { template: '<div />' },
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('[data-test="danger-page"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="export-data-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="delete-account-card"]').exists()).toBe(true)

    // Export card still wears its "Coming soon" chip.
    expect(wrapper.text()).toContain('Coming soon')
    // Delete card is now active.
    expect(wrapper.find('[data-test="open-delete-account-dialog"]').exists()).toBe(true)
  })

  it('redirects /account to /account/profile', async () => {
    await router.push('/account')
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('AccountProfile')
  })
})
