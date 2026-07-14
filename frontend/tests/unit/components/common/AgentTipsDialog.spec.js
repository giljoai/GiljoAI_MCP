/**
 * FE-6105: AgentTipsDialog — Antigravity (agy) spawn chip.
 *
 * Verifies the Antigravity option is additive alongside the existing
 * Claude/Codex/Gemini chips, and that selecting it surfaces the agy spawn
 * command (Gemini-successor; reuses Gemini's @-syntax spawn behavior).
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import AgentTipsDialog from '@/components/common/AgentTipsDialog.vue'

describe('AgentTipsDialog — Antigravity spawn chip (FE-6105)', () => {
  let vuetify

  beforeEach(() => {
    vuetify = createVuetify({ components, directives })
  })

  // Stub structural containers so the (normally lazy / teleported) panel
  // content renders synchronously, while keeping the real v-chip-group so its
  // v-model selection actually drives the spawn-command v-if.
  const passthrough = (cls) => ({ template: `<div class="${cls}"><slot /></div>` })

  const createWrapper = () =>
    mount(AgentTipsDialog, {
      global: {
        plugins: [vuetify],
        directives: { draggable: {} },
        stubs: {
          'v-dialog': passthrough('v-dialog'),
          'v-tooltip': passthrough('v-tooltip'),
          'v-expansion-panels': passthrough('v-expansion-panels'),
          'v-expansion-panel': passthrough('v-expansion-panel'),
          'v-expansion-panel-title': passthrough('v-expansion-panel-title'),
          'v-expansion-panel-text': passthrough('v-expansion-panel-text'),
        },
      },
    })

  it('renders an Antigravity chip alongside the existing tool chips (additive)', () => {
    const wrapper = createWrapper()
    const chipLabels = wrapper.findAll('.v-chip-group .v-chip').map((c) => c.text())
    expect(chipLabels).toContain('Antigravity')
    // The existing tool chips remain — Antigravity is additive, not a replacement.
    expect(chipLabels.some((l) => l.includes('Claude Code CLI'))).toBe(true)
    expect(chipLabels.some((l) => l.includes('Codex'))).toBe(true)
    expect(chipLabels.some((l) => l.includes('Gemini'))).toBe(true)
  })

  it('shows the agy spawn command when Antigravity is selected', async () => {
    const wrapper = createWrapper()
    // Default selection is claude — the agy block must be hidden initially.
    expect(wrapper.text()).not.toContain('cmd /k agy')

    // Drive the real v-chip-group v-model so the spawn-command v-if flips.
    const group = wrapper.findComponent('.v-chip-group')
    group.vm.$emit('update:modelValue', 'antigravity')
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('cmd /k agy')
    expect(text).toContain('--yolo')
    // Successor-to-Gemini note is present so the user understands the lineage.
    expect(text).toContain('successor to Gemini CLI')
  })
})
