/**
 * FE-9000e — OrganizationSettings.vue regression trap coverage.
 *
 * DefaultLayout's router-view now keys on the matched route record, not the
 * resolved path, so a param-only nav (/organizations/A/settings ->
 * /organizations/B/settings) reuses this component instance instead of
 * remounting it. Before this WO, the view only fetched onMounted (its
 * existing watcher only reacted to the currentOrg store value, not the
 * route param) -- with instance reuse it would silently show the previous
 * org's stale data. This asserts the added param watcher refetches on a
 * route.params.orgId change.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import { reactive } from 'vue'
import api from '@/services/api'

const mockRoute = reactive({ params: { orgId: 'org-1' } })
const mockRouter = { push: vi.fn() }
vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

import OrganizationSettings from '@/views/OrganizationSettings.vue'

function mountView() {
  const vuetify = createVuetify()
  return mount(OrganizationSettings, {
    global: {
      plugins: [vuetify],
      stubs: {
        MemberList: true,
        InviteMemberDialog: true,
      },
    },
  })
}

describe('OrganizationSettings.vue — refetch on param change (FE-9000e regression trap)', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockRoute.params.orgId = 'org-1'
  })

  afterEach(() => {
    // Unmount so the previous test's watcher on the shared mockRoute doesn't
    // fire again (and steal a queued mockResolvedValueOnce) on the next test.
    if (wrapper) wrapper.unmount()
    wrapper = null
  })

  it('fetches the org for the initial route param on mount', async () => {
    api.organizations.get.mockResolvedValueOnce({ data: { id: 'org-1', name: 'Org One', members: [] } })

    wrapper = mountView()
    await flushPromises()

    expect(api.organizations.get).toHaveBeenCalledWith('org-1')
    expect(wrapper.vm.orgForm.name).toBe('Org One')
  })

  it('refetches and swaps the loaded org when route.params.orgId changes (instance-reuse case)', async () => {
    api.organizations.get.mockResolvedValueOnce({ data: { id: 'org-1', name: 'Org One', members: [] } })
    wrapper = mountView()
    await flushPromises()
    expect(wrapper.vm.orgForm.name).toBe('Org One')

    api.organizations.get.mockResolvedValueOnce({ data: { id: 'org-2', name: 'Org Two', members: [] } })
    mockRoute.params.orgId = 'org-2'
    await flushPromises()

    expect(api.organizations.get).toHaveBeenCalledWith('org-2')
    expect(wrapper.vm.orgForm.name).toBe('Org Two')
  })
})
