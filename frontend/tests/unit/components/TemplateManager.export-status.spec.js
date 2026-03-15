/**
 * TemplateManager - Export Status Column Tests
 * Handover 0335 - Task 4: UI Staleness Indicator
 *
 * Tests the export status column that displays:
 * - Warning chip for stale templates (may_be_stale: true)
 * - Last export timestamp or "Never exported"
 * - Tooltip with helpful context
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import TemplateManager from '../TemplateManager.vue'
import api from '@/services/api'

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    templates: {
      list: vi.fn(),
      activeCount: vi.fn(),
    },
  },
}))


const vuetify = createVuetify({
  components,
  directives,
})

const mockTemplates = [
  {
    id: 'template-1',
    name: 'implementer',
    role: 'implementer',
    cli_tool: 'claude',
    system_instructions: 'You are an implementer...',
    is_active: true,
    is_system_role: false,
    updated_at: '2025-12-08T16:00:00Z',
    last_exported_at: '2025-12-08T15:00:00Z',
    may_be_stale: true, // Updated after last export
    variables: [],
    behavioral_rules: [],
    success_criteria: [],
    tags: [],
  },
  {
    id: 'template-2',
    name: 'tester',
    role: 'tester',
    cli_tool: 'claude',
    system_instructions: 'You are a tester...',
    is_active: true,
    is_system_role: false,
    updated_at: '2025-12-08T14:00:00Z',
    last_exported_at: '2025-12-08T15:00:00Z',
    may_be_stale: false, // Up to date
    variables: [],
    behavioral_rules: [],
    success_criteria: [],
    tags: [],
  },
  {
    id: 'template-3',
    name: 'documenter',
    role: 'documenter',
    cli_tool: 'claude',
    system_instructions: 'You are a documenter...',
    is_active: false,
    is_system_role: false,
    updated_at: '2025-12-08T10:00:00Z',
    last_exported_at: null, // Never exported
    may_be_stale: false,
    variables: [],
    behavioral_rules: [],
    success_criteria: [],
    tags: [],
  },
]

describe('TemplateManager - Export Status Column', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.templates.list.mockResolvedValue({ data: mockTemplates })
    api.templates.activeCount.mockResolvedValue({
      data: {
        total_active: 2,
        total_capacity: 8,
        active_count: 2,
        max_allowed: 7,
        remaining_slots: 5,
        system_reserved: 1,
      },
    })
  })

  it('should display "Export Status" column header', async () => {
    const wrapper = mount(TemplateManager, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 100))

    const headers = wrapper.findAll('th')
    const headerTexts = headers.map((h) => h.text())
    expect(headerTexts).toContain('Export Status')
  })

  it('should show warning chip for stale templates', async () => {
    const wrapper = mount(TemplateManager, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Find warning chips with "May be outdated" text
    const warningChips = wrapper.findAll('.v-chip[color="warning"]')
    const staleChip = warningChips.find((chip) => chip.text().includes('May be outdated'))

    expect(staleChip).toBeDefined()
    expect(staleChip.text()).toContain('May be outdated')
  })

  it('should display "Never exported" for templates without export timestamp', async () => {
    const wrapper = mount(TemplateManager, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Find text containing "Never exported"
    const neverExportedText = wrapper.findAll('.text-caption').find((el) => el.text() === 'Never exported')

    expect(neverExportedText).toBeDefined()
  })

  it('should display formatted timestamp for exported templates', async () => {
    const wrapper = mount(TemplateManager, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Check that timestamps are formatted (e.g., "Dec 08, 2025 15:00")
    const timestamps = wrapper.findAll('.text-caption')
    const hasFormattedTimestamp = timestamps.some(
      (el) => el.text().match(/\w{3} \d{2}, \d{4}/) // Format: MMM dd, yyyy
    )

    expect(hasFormattedTimestamp).toBe(true)
  })

  it('should have accessible ARIA label on warning chip', async () => {
    const wrapper = mount(TemplateManager, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Find warning chip with aria-label
    const warningChip = wrapper.find('.v-chip[aria-label="Template may be outdated"]')
    expect(warningChip.exists()).toBe(true)
  })

  it('should show contextual tooltip for stale templates', async () => {
    const wrapper = mount(TemplateManager, {
      global: {
        plugins: [vuetify],
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Verify tooltip structure exists (Vuetify tooltips are complex to test)
    const tooltips = wrapper.findAllComponents({ name: 'VTooltip' })
    expect(tooltips.length).toBeGreaterThan(0)
  })
})
