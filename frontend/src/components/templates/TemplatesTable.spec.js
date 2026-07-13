/**
 * TemplatesTable.spec.js — FE-6042b
 *
 * Co-located child spec for TemplatesTable.vue.
 * Covers render variants and EVERY emit.
 *
 * Edition scope: CE
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import TemplatesTable from './TemplatesTable.vue'

// ---------------------------------------------------------------------------
// Stubs
// ---------------------------------------------------------------------------

/**
 * v-data-table stub that renders item.* slots for every item.
 * Same shape as in TemplateManager.spec.js — the slot names are stable.
 */
const dataTableStub = {
  props: ['headers', 'items', 'loading', 'search', 'itemsPerPage'],
  template: `
    <div class="v-data-table">
      <div v-for="item in (items || [])" :key="item.id" class="v-data-table-row">
        <slot name="item.name" :item="item" />
        <slot name="item.role" :item="item" />
        <slot name="item.is_active" :item="item" />
        <slot name="item.export_status" :item="item" />
        <slot name="item.updated_at" :item="item" />
        <slot name="item.actions" :item="item" />
      </div>
    </div>
  `,
}

/**
 * v-switch stub: emits update:modelValue on change.
 */
const switchStub = {
  props: ['modelValue', 'disabled', 'color', 'hideDetails', 'density', 'ariaLabel'],
  emits: ['update:modelValue'],
  template: `
    <input
      type="checkbox"
      class="v-switch"
      v-bind="$attrs"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.checked)"
    />
  `,
}

const menuStub = {
  template: `<div class="v-menu"><slot name="activator" :props="{}" /><slot /></div>`,
}

const listItemStub = {
  props: ['title', 'prependIcon'],
  template: `<div class="v-list-item" v-bind="$attrs" :title="title"><slot /></div>`,
}

const tooltipStub = {
  props: ['text', 'location'],
  template: `<div class="v-tooltip"><slot name="activator" :props="{}" /><slot /></div>`,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTemplate(overrides = {}) {
  return {
    id: 1,
    name: 'My Analyzer',
    role: 'analyzer',
    category: 'role',
    is_active: true,
    may_be_stale: false,
    user_managed_export: false,
    _system: false,
    last_exported_at: '2024-01-01T12:00:00Z',
    updated_at: '2024-01-01T12:00:00Z',
    ...overrides,
  }
}

const defaultHeaders = [
  { title: 'Agent Name', key: 'name', align: 'start' },
  { title: 'Role', key: 'role', align: 'start' },
  { title: 'Active', key: 'is_active', align: 'center' },
]

function mountTable(propsData = {}) {
  return mount(TemplatesTable, {
    props: {
      templates: [makeTemplate()],
      loading: false,
      headers: defaultHeaders,
      search: '',
      remainingUserSlots: 5,
      userAgentLimit: 7,
      ...propsData,
    },
    global: {
      stubs: {
        'v-data-table': dataTableStub,
        'v-switch': switchStub,
        'v-menu': menuStub,
        'v-list-item': listItemStub,
        'v-tooltip': tooltipStub,
      },
    },
  })
}

// ---------------------------------------------------------------------------
// Render variants
// ---------------------------------------------------------------------------

describe('TemplatesTable — render', () => {
  it('renders without errors for an empty template list', () => {
    const wrapper = mountTable({ templates: [] })
    expect(wrapper.find('.v-data-table').exists()).toBe(true)
  })

  it('renders a row per template', () => {
    const wrapper = mountTable({
      templates: [
        makeTemplate({ id: 1, role: 'analyzer' }),
        makeTemplate({ id: 2, role: 'reviewer' }),
      ],
    })
    const rows = wrapper.findAll('.v-data-table-row')
    expect(rows).toHaveLength(2)
  })

  it('renders role badge text for each template', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ role: 'backend' })],
    })
    expect(wrapper.text()).toContain('backend')
  })

  it('renders a toggle (v-switch) for user-managed templates', () => {
    const wrapper = mountTable()
    expect(wrapper.find('.v-switch').exists()).toBe(true)
  })

  it('does not render a toggle for system-managed (_system=true) templates', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ _system: true })],
    })
    // _system row renders mdi-lock icon, not a switch
    expect(wrapper.find('.v-switch').exists()).toBe(false)
  })

  it('renders testid template-toggle-{role} for user-managed template', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ id: 5, role: 'frontend' })],
    })
    expect(wrapper.find('[data-testid="template-toggle-frontend"]').exists()).toBe(true)
  })

  it('renders "User Managed" chip when user_managed_export=true', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ user_managed_export: true })],
    })
    expect(wrapper.text()).toContain('User Managed')
  })

  it('renders "System managed" text for _system templates', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ _system: true })],
    })
    expect(wrapper.text()).toContain('System managed')
  })

  it('renders "Never exported" when last_exported_at is null', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ last_exported_at: null })],
    })
    expect(wrapper.text()).toContain('Never exported')
  })

  it('renders "May be outdated" chip when may_be_stale=true and is_active=true', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ may_be_stale: true, is_active: true })],
    })
    expect(wrapper.text()).toContain('May be outdated')
  })

  it('does not render action menu for _system templates', () => {
    const wrapper = mountTable({
      templates: [makeTemplate({ _system: true })],
    })
    expect(wrapper.find('[aria-label="Template actions"]').exists()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Emits — every declared emit
// ---------------------------------------------------------------------------

describe('TemplatesTable — emit: toggle-active', () => {
  it('emits toggle-active with (item, newValue) when switch changes', async () => {
    const tpl = makeTemplate({ id: 10, role: 'tester', is_active: true })
    const wrapper = mountTable({ templates: [tpl] })

    const toggle = wrapper.find('[data-testid="template-toggle-tester"]')
    toggle.element.checked = false
    await toggle.trigger('change')

    expect(wrapper.emitted('toggle-active')).toHaveLength(1)
    expect(wrapper.emitted('toggle-active')[0]).toEqual([tpl, false])
  })
})

describe('TemplatesTable — emit: edit', () => {
  it('emits edit with the item when Edit is clicked', async () => {
    const tpl = makeTemplate({ id: 3, role: 'backend' })
    const wrapper = mountTable({ templates: [tpl] })

    await wrapper.find('[title="Edit"]').trigger('click')

    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.emitted('edit')[0]).toEqual([tpl])
  })
})

describe('TemplatesTable — emit: duplicate', () => {
  it('emits duplicate with the item when Duplicate is clicked', async () => {
    const tpl = makeTemplate({ id: 4, role: 'documenter' })
    const wrapper = mountTable({ templates: [tpl] })

    await wrapper.find('[title="Duplicate"]').trigger('click')

    expect(wrapper.emitted('duplicate')).toHaveLength(1)
    expect(wrapper.emitted('duplicate')[0]).toEqual([tpl])
  })
})

describe('TemplatesTable — emit: reset', () => {
  it('emits reset with the item when Reset to Default is clicked', async () => {
    const tpl = makeTemplate({ id: 6, role: 'reviewer', is_default: true })
    const wrapper = mountTable({ templates: [tpl] })

    await wrapper.find('[title="Reset to Default"]').trigger('click')

    expect(wrapper.emitted('reset')).toHaveLength(1)
    expect(wrapper.emitted('reset')[0]).toEqual([tpl])
  })

  it('hides Reset to Default for a non-default (custom) template', () => {
    // BE-9018: reset only restores real content for a shipped default template;
    // a custom template has nothing to reset to, so the action is not offered.
    const tpl = makeTemplate({ id: 7, role: 'reviewer', is_default: false })
    const wrapper = mountTable({ templates: [tpl] })

    expect(wrapper.find('[title="Reset to Default"]').exists()).toBe(false)
  })
})

describe('TemplatesTable — emit: delete', () => {
  it('emits delete with the item when Delete is clicked', async () => {
    const tpl = makeTemplate({ id: 9, role: 'implementer' })
    const wrapper = mountTable({ templates: [tpl] })

    await wrapper.find('[title="Delete"]').trigger('click')

    expect(wrapper.emitted('delete')).toHaveLength(1)
    expect(wrapper.emitted('delete')[0]).toEqual([tpl])
  })
})

describe('TemplatesTable — emit: mark-user-managed', () => {
  it('emits mark-user-managed when Mark as User Managed is clicked (stale, not user-managed)', async () => {
    const tpl = makeTemplate({ id: 11, role: 'analyzer', may_be_stale: true, user_managed_export: false })
    const wrapper = mountTable({ templates: [tpl] })

    await wrapper.find('[title="Mark as User Managed"]').trigger('click')

    expect(wrapper.emitted('mark-user-managed')).toHaveLength(1)
    expect(wrapper.emitted('mark-user-managed')[0]).toEqual([tpl])
  })

  it('does not render Mark as User Managed when template is not stale', () => {
    const tpl = makeTemplate({ id: 12, role: 'analyzer', may_be_stale: false })
    const wrapper = mountTable({ templates: [tpl] })

    expect(wrapper.find('[title="Mark as User Managed"]').exists()).toBe(false)
  })

  it('does not render Mark as User Managed when already user-managed', () => {
    const tpl = makeTemplate({ id: 13, role: 'analyzer', may_be_stale: true, user_managed_export: true })
    const wrapper = mountTable({ templates: [tpl] })

    expect(wrapper.find('[title="Mark as User Managed"]').exists()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Slot passthrough: search prop forwarded to v-data-table
// ---------------------------------------------------------------------------

describe('TemplatesTable — search prop', () => {
  it('passes search to the v-data-table stub', () => {
    const wrapper = mountTable({ search: 'hello' })
    // The stub renders as a div with class v-data-table; we can verify via props
    const table = wrapper.findComponent(dataTableStub)
    expect(table.props('search')).toBe('hello')
  })
})
