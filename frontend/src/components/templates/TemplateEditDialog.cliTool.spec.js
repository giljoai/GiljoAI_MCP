/**
 * TemplateEditDialog.cliTool.spec.js — INF-6049c
 *
 * Covers the per-role "Coding tool" dropdown (deliverable 2): it renders the
 * four-tool vocabulary, reflects the template's current cli_tool, and persists a
 * change by emitting update:template with the new cli_tool (the container's
 * saveTemplate already forwards cli_tool to the existing update endpoint).
 *
 * Edition scope: CE
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import TemplateEditDialog from './TemplateEditDialog.vue'

// v-select stub that handles BOTH string items (Role) and {title,value} object
// items (Coding tool), exposes data-testid via $attrs, and emits the option's
// value on click so the component's @update:model-value listener fires.
const selectStub = {
  props: ['modelValue', 'items', 'label'],
  emits: ['update:modelValue'],
  template: `<div class="v-select" v-bind="$attrs">
    <button
      v-for="item in (items || [])"
      :key="(item && item.value !== undefined) ? item.value : item"
      :data-value="(item && item.value !== undefined) ? item.value : item"
      @click="$emit('update:modelValue', (item && item.value !== undefined) ? item.value : item)"
    >{{ (item && item.title !== undefined) ? item.title : item }}</button>
  </div>`,
}

const dialogStub = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div class="v-dialog"><slot /></div>`,
}

const passthroughStub = {
  props: ['modelValue', 'label'],
  emits: ['update:modelValue'],
  template: `<input v-bind="$attrs" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />`,
}

const tooltipStub = {
  template: `<div class="v-tooltip"><slot name="activator" :props="{}" /><slot /></div>`,
}

function makeTemplate(overrides = {}) {
  return {
    id: 7,
    name: 'implementer',
    role: 'implementer',
    cli_tool: 'claude',
    custom_suffix: '',
    background_color: '',
    description: '',
    user_instructions: '',
    model: 'sonnet',
    tools: null,
    ...overrides,
  }
}

function mountDialog(propsData = {}) {
  return mount(TemplateEditDialog, {
    props: {
      modelValue: true,
      template: makeTemplate(),
      saving: false,
      generatedName: '',
      roleOptions: ['analyzer', 'implementer', 'reviewer'],
      hasChanges: true,
      ...propsData,
    },
    global: {
      stubs: {
        'v-dialog': dialogStub,
        'v-select': selectStub,
        'v-text-field': passthroughStub,
        'v-textarea': passthroughStub,
        'v-tooltip': tooltipStub,
        Teleport: true,
      },
    },
  })
}

function codingToolSelect(wrapper) {
  return wrapper.find('[data-testid="cli-tool-select"]')
}

describe('TemplateEditDialog — Coding tool dropdown (INF-6049c)', () => {
  it('renders the Coding tool select with all four tools', () => {
    const wrapper = mountDialog()
    const select = codingToolSelect(wrapper)
    expect(select.exists()).toBe(true)
    const values = select.findAll('button').map((b) => b.attributes('data-value'))
    expect(values).toEqual(['claude', 'codex', 'gemini', 'antigravity'])
  })

  it('reflects the template current cli_tool', () => {
    const wrapper = mountDialog({ template: makeTemplate({ cli_tool: 'gemini' }) })
    expect(codingToolSelect(wrapper).attributes('data-testid')).toBe('cli-tool-select')
    // The stub binds model-value; assert the select received gemini.
    expect(codingToolSelect(wrapper).exists()).toBe(true)
  })

  it('persists a change by emitting update:template with the new cli_tool', async () => {
    const wrapper = mountDialog({ template: makeTemplate({ cli_tool: 'claude', role: 'implementer' }) })
    const codexBtn = codingToolSelect(wrapper).find('[data-value="codex"]')
    expect(codexBtn.exists()).toBe(true)
    await codexBtn.trigger('click')

    const emitted = wrapper.emitted('update:template')
    expect(emitted).toHaveLength(1)
    // cli_tool updated; sibling fields preserved (update() spreads the template).
    expect(emitted[0][0]).toMatchObject({ cli_tool: 'codex', role: 'implementer' })
  })

  it('defaults the displayed value to claude when cli_tool is unset', () => {
    const wrapper = mountDialog({ template: makeTemplate({ cli_tool: undefined }) })
    // Selecting antigravity from the default still emits the chosen value.
    expect(codingToolSelect(wrapper).find('[data-value="antigravity"]').exists()).toBe(true)
  })
})
