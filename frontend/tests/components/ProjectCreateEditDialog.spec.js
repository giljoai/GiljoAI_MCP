/**
 * Regression: project-create "silent disabled Create" UX bug (perf-findings
 * 2026-06-11, found during live in-app UI testing on the test mirror).
 *
 * Old behavior: the Create button was `:disabled="!formValid"` AND save() did
 * `if (!formValid.value) return`. With a required-but-untouched Description,
 * formValid stayed false → the button was greyed out and clicking did nothing,
 * with NO visible reason (Vuetify only shows the required error after touch).
 *
 * Fix: the button is always clickable and save() validates ON CLICK via
 * projectFormRef.validate(), which surfaces "Description is required" on the
 * field. These tests prove save() now goes through validate() (the old code
 * never called it) and only POSTs when the form is valid.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createVuetify } from 'vuetify'
import ProjectCreateEditDialog from '@/components/projects/ProjectCreateEditDialog.vue'
import { useProjectStore } from '@/stores/projects'

vi.mock('@/services/api', () => ({
  default: {
    projects: {
      usedSubseries: vi.fn().mockResolvedValue({ data: { used_subseries: [] } }),
      checkSeries: vi.fn().mockResolvedValue({ data: { available: true } }),
    },
  },
}))

function mountDialog() {
  const vuetify = createVuetify()
  return mount(ProjectCreateEditDialog, {
    global: { plugins: [vuetify] },
    props: {
      modelValue: true,
      editingProject: null,
      activeProduct: { id: 'prod-1', name: 'Product 1' },
      projectTypes: [],
    },
  })
}

describe('ProjectCreateEditDialog - validate-on-click (silent-disable regression)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('save() validates on click and does NOT POST when the form is invalid', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    const store = useProjectStore()
    const createSpy = vi.spyOn(store, 'createProject').mockResolvedValue({ id: 'new-1' })

    // Simulate an invalid form (e.g. empty required Description). The fix routes
    // through validate(); the OLD code returned on `formValid` and never called it.
    const validate = vi.fn().mockResolvedValue({ valid: false })
    wrapper.vm.projectFormRef = { validate }

    await wrapper.vm.save()
    await flushPromises()

    expect(validate).toHaveBeenCalledTimes(1) // proves validate-on-click (old code never called it)
    expect(createSpy).not.toHaveBeenCalled() // invalid → no POST
  })

  it('save() POSTs when the form validates clean', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    const store = useProjectStore()
    const createSpy = vi.spyOn(store, 'createProject').mockResolvedValue({ id: 'new-1' })
    vi.spyOn(store, 'fetchProjects').mockResolvedValue([])

    wrapper.vm.localData = {
      name: 'My project',
      description: 'Do the thing',
      mission: '',
      status: 'inactive',
      project_type_id: null,
      series_number: null,
      subseries: null,
    }
    wrapper.vm.projectFormRef = { validate: vi.fn().mockResolvedValue({ valid: true }) }

    await wrapper.vm.save()
    await flushPromises()

    expect(createSpy).toHaveBeenCalledTimes(1)
    expect(createSpy.mock.calls[0][0]).toMatchObject({
      name: 'My project',
      description: 'Do the thing',
      product_id: 'prod-1',
    })
  })

  it('the Create button is not statically disabled (clickable so validation can surface)', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    const createBtn = wrapper.findAll('button').find((b) => b.text().includes('Create'))
    expect(createBtn).toBeTruthy()
    expect(createBtn.attributes('disabled')).toBeFalsy()
  })

  // Regression: cosmetic overlap (live UI testing 2026-06-11). With an
  // unconditional persistent-hint, the always-on Description hint collided with
  // the "Description is required" error in the details row when the field was
  // empty. The hint is now persistent only when the field has content — the
  // exact complement of when the required-error can fire — so they never coexist.
  it('Description hint persists only with content (cannot overlap the required-error)', async () => {
    const wrapper = mountDialog()
    await flushPromises()

    // Empty — the only state where the "Description is required" error fires:
    // the hint must NOT persist, so error and hint never share the details row.
    expect(wrapper.vm.descriptionHintPersistent).toBe(false)

    // With content (no error possible): the always-on guidance hint is preserved.
    wrapper.vm.localData.description = 'Build the thing'
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.descriptionHintPersistent).toBe(true)
  })
})
