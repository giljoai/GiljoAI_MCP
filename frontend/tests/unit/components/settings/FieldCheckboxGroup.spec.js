import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import FieldCheckboxGroup from '@/components/settings/FieldCheckboxGroup.vue'

describe('FieldCheckboxGroup', () => {
  let wrapper

  const mockFields = [
    { key: 'languages', label: 'Programming Languages', tokens: 50 },
    { key: 'frameworks', label: 'Frameworks', tokens: 100 },
    { key: 'databases', label: 'Databases', tokens: 50 },
    { key: 'dependencies', label: 'Dependencies', tokens: 100 },
  ]

  const defaultModelValue = {
    languages: true,
    frameworks: true,
    databases: false,
    dependencies: false,
  }

  beforeEach(() => {
    wrapper = mount(FieldCheckboxGroup, {
      props: {
        fields: mockFields,
        modelValue: defaultModelValue,
        label: 'Tech Stack',
      },
      global: {
        plugins: [
          createTestingPinia({
            initialState: {}
          })
        ],
        stubs: {
          'v-checkbox': {
            template: '<input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
            props: ['modelValue', 'label']
          },
          'v-chip': { template: '<span class="v-chip"><slot /></span>' },
        }
      }
    })
  })

  it('renders with correct label', () => {
    expect(wrapper.text()).toContain('Tech Stack')
  })

  it('renders all fields', () => {
    const text = wrapper.text()
    expect(text).toContain('Programming Languages')
    expect(text).toContain('Frameworks')
    expect(text).toContain('Databases')
    expect(text).toContain('Dependencies')
  })

  it('shows token estimates for each field', () => {
    const text = wrapper.text()
    expect(text).toContain('50')
    expect(text).toContain('100')
  })

  it('emits update:modelValue when checkbox changes', async () => {
    // Simulate checkbox change
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes.length).toBe(4)

    // Change first checkbox
    await checkboxes[0].setValue(false)

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
  })

  it('calculates total tokens from selected fields', () => {
    // With languages (50) and frameworks (100) selected
    const totalTokens = wrapper.vm.totalTokens
    expect(totalTokens).toBe(150) // 50 + 100
  })

  it('updates total tokens when selection changes', async () => {
    // Initial total: 150 (languages + frameworks)
    expect(wrapper.vm.totalTokens).toBe(150)

    // Update model to include databases
    await wrapper.setProps({
      modelValue: {
        languages: true,
        frameworks: true,
        databases: true,
        dependencies: false,
      }
    })

    expect(wrapper.vm.totalTokens).toBe(200) // 50 + 100 + 50
  })

  it('shows 0 tokens when nothing selected', async () => {
    await wrapper.setProps({
      modelValue: {
        languages: false,
        frameworks: false,
        databases: false,
        dependencies: false,
      }
    })

    expect(wrapper.vm.totalTokens).toBe(0)
  })

  it('handles empty fields array gracefully', async () => {
    await wrapper.setProps({
      fields: [],
      modelValue: {}
    })

    expect(wrapper.vm.totalTokens).toBe(0)
  })

  it('toggles field selection correctly', async () => {
    // Call toggleField method directly
    wrapper.vm.toggleField('databases')

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0].databases).toBe(true) // Should toggle from false to true
  })

  it('toggles all fields when selectAll is called', async () => {
    wrapper.vm.selectAll(true)

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const lastEmitted = emitted[emitted.length - 1][0]
    expect(lastEmitted.languages).toBe(true)
    expect(lastEmitted.frameworks).toBe(true)
    expect(lastEmitted.databases).toBe(true)
    expect(lastEmitted.dependencies).toBe(true)
  })

  it('deselects all fields when selectAll(false) is called', async () => {
    wrapper.vm.selectAll(false)

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const lastEmitted = emitted[emitted.length - 1][0]
    expect(lastEmitted.languages).toBe(false)
    expect(lastEmitted.frameworks).toBe(false)
    expect(lastEmitted.databases).toBe(false)
    expect(lastEmitted.dependencies).toBe(false)
  })

  it('correctly identifies if all fields are selected', async () => {
    await wrapper.setProps({
      modelValue: {
        languages: true,
        frameworks: true,
        databases: true,
        dependencies: true,
      }
    })

    expect(wrapper.vm.allSelected).toBe(true)
  })

  it('correctly identifies if some fields are selected', () => {
    expect(wrapper.vm.someSelected).toBe(true)
    expect(wrapper.vm.allSelected).toBe(false)
  })
})
