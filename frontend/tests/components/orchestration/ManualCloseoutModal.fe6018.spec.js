/**
 * ManualCloseoutModal — FE-6018 git_commits capture test
 *
 * Edition Scope: Both (CE component, no saas/ imports)
 *
 * Asserts:
 *   (a) Filled SHA + message rows produce a git_commits array in the completeWithData payload
 *   (b) Optional author/date are included in the row when filled
 *   (c) No commit rows → payload omits git_commits (or sends []) and submit still works
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ManualCloseoutModal from '@/components/orchestration/ManualCloseoutModal.vue'

// ─── API mock ────────────────────────────────────────────────────────────────
// setup.js already mocks @/services/api globally. We grab the live mock ref
// so we can assert on it and reset between tests.
import api from '@/services/api'

// ─── Local v-model-aware stubs ───────────────────────────────────────────────
// The global Vuetify stubs in setup.js render inputs as plain <input v-bind="$attrs">
// which does NOT emit update:modelValue. Override them locally so setValue()
// drives the component's reactive state correctly.
const vTextField = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
}

const vTextarea = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<textarea :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"></textarea>',
}

const vCheckbox = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
/**
 * Mount the modal with the local v-model-aware stubs that override globals.
 */
function mountModal() {
  return mount(ManualCloseoutModal, {
    props: {
      show: true,
      projectId: 'proj-fe6018',
      projectName: 'FE-6018 Test Project',
    },
    global: {
      plugins: [createPinia()],
      stubs: {
        'v-text-field': vTextField,
        'v-textarea': vTextarea,
        'v-checkbox': vCheckbox,
      },
    },
  })
}

/**
 * Fill the summary textarea and check the confirm checkbox so canSubmit becomes true.
 * The summary textarea renders as <textarea data-testid="summary-field"> or we find
 * it by the textarea element inside the summary wrapper.
 */
async function fillRequiredBase(wrapper) {
  // Fill summary (≥50 chars)
  const summaryTextarea = wrapper.find('[data-testid="summary-field"]')
  await summaryTextarea.setValue(
    'This is a detailed summary of the work completed in this project. Fifty chars min.',
  )

  // Check the confirmation checkbox
  const checkbox = wrapper.find('[data-testid="manual-confirm-checkbox"]')
  await checkbox.setValue(true)
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('ManualCloseoutModal — FE-6018 git_commits capture', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Ensure completeWithData resolves successfully
    api.projects.completeWithData.mockResolvedValue({ data: { project_id: 'proj-fe6018' } })
  })

  // ── (a) Filled SHA + message rows produce git_commits in payload ──────────
  it('(a) builds git_commits array from filled SHA + message rows', async () => {
    const wrapper = mountModal()
    await fillRequiredBase(wrapper)

    // Add first commit row
    const addBtn = wrapper.find('[data-testid="add-commit-btn"]')
    await addBtn.trigger('click')

    // Fill SHA and message in the first row
    const shaInput = wrapper.find('[data-testid="commit-sha-0"]')
    const msgInput = wrapper.find('[data-testid="commit-msg-0"]')
    await shaInput.setValue('abc1234def5678')
    await msgInput.setValue('feat: initial implementation')

    // Submit
    const submitBtn = wrapper.find('[data-testid="manual-complete-btn"]')
    await submitBtn.trigger('click')
    await vi.waitFor(() => {
      expect(api.projects.completeWithData).toHaveBeenCalled()
    })

    const [, payload] = api.projects.completeWithData.mock.calls[0]
    expect(payload.git_commits).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          sha: 'abc1234def5678',
          message: 'feat: initial implementation',
        }),
      ]),
    )
    expect(payload.git_commits).toHaveLength(1)
  })

  // ── (b) Optional author/date included when filled ─────────────────────────
  it('(b) includes optional author and date when filled', async () => {
    const wrapper = mountModal()
    await fillRequiredBase(wrapper)

    const addBtn = wrapper.find('[data-testid="add-commit-btn"]')
    await addBtn.trigger('click')

    const shaInput = wrapper.find('[data-testid="commit-sha-0"]')
    const msgInput = wrapper.find('[data-testid="commit-msg-0"]')
    const authorInput = wrapper.find('[data-testid="commit-author-0"]')
    const dateInput = wrapper.find('[data-testid="commit-date-0"]')

    await shaInput.setValue('deadbeef1234')
    await msgInput.setValue('fix: resolve race condition')
    await authorInput.setValue('GiljoAI')
    await dateInput.setValue('2026-06-05T10:00:00Z')

    const submitBtn = wrapper.find('[data-testid="manual-complete-btn"]')
    await submitBtn.trigger('click')
    await vi.waitFor(() => {
      expect(api.projects.completeWithData).toHaveBeenCalled()
    })

    const [, payload] = api.projects.completeWithData.mock.calls[0]
    expect(payload.git_commits[0]).toMatchObject({
      sha: 'deadbeef1234',
      message: 'fix: resolve race condition',
      author: 'GiljoAI',
      date: '2026-06-05T10:00:00Z',
    })
  })

  // ── (c) No rows → payload omits git_commits (or []) + submit still works ──
  it('(c) submits successfully with no commit rows (empty / omitted git_commits)', async () => {
    const wrapper = mountModal()
    await fillRequiredBase(wrapper)

    // Do NOT add any commit rows
    const submitBtn = wrapper.find('[data-testid="manual-complete-btn"]')
    await submitBtn.trigger('click')
    await vi.waitFor(() => {
      expect(api.projects.completeWithData).toHaveBeenCalled()
    })

    const [, payload] = api.projects.completeWithData.mock.calls[0]
    // Either not present, or present as an empty array — both are valid
    const commits = payload.git_commits
    expect(commits === undefined || (Array.isArray(commits) && commits.length === 0)).toBe(true)
    // Sanity: summary is present
    expect(payload.summary).toBeTruthy()
  })

  // ── Edge: a row with only SHA (no message) must NOT be included ───────────
  it('ignores incomplete rows (SHA without message)', async () => {
    const wrapper = mountModal()
    await fillRequiredBase(wrapper)

    const addBtn = wrapper.find('[data-testid="add-commit-btn"]')
    await addBtn.trigger('click')

    // Fill SHA only, leave message empty
    const shaInput = wrapper.find('[data-testid="commit-sha-0"]')
    await shaInput.setValue('deadbeef')
    // message left blank

    const submitBtn = wrapper.find('[data-testid="manual-complete-btn"]')
    await submitBtn.trigger('click')
    await vi.waitFor(() => {
      expect(api.projects.completeWithData).toHaveBeenCalled()
    })

    const [, payload] = api.projects.completeWithData.mock.calls[0]
    const commits = payload.git_commits
    expect(commits === undefined || (Array.isArray(commits) && commits.length === 0)).toBe(true)
  })

  // ── Edge: remove-row button removes the row from the payload ─────────────
  it('remove-row button removes the commit from the payload', async () => {
    const wrapper = mountModal()
    await fillRequiredBase(wrapper)

    const addBtn = wrapper.find('[data-testid="add-commit-btn"]')
    await addBtn.trigger('click')

    const shaInput = wrapper.find('[data-testid="commit-sha-0"]')
    const msgInput = wrapper.find('[data-testid="commit-msg-0"]')
    await shaInput.setValue('aaabbbccc')
    await msgInput.setValue('chore: bump deps')

    // Remove the row
    const removeBtn = wrapper.find('[data-testid="remove-commit-0"]')
    await removeBtn.trigger('click')

    const submitBtn = wrapper.find('[data-testid="manual-complete-btn"]')
    await submitBtn.trigger('click')
    await vi.waitFor(() => {
      expect(api.projects.completeWithData).toHaveBeenCalled()
    })

    const [, payload] = api.projects.completeWithData.mock.calls[0]
    const commits = payload.git_commits
    expect(commits === undefined || (Array.isArray(commits) && commits.length === 0)).toBe(true)
  })
})
