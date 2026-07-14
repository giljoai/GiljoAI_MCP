/**
 * BaseDialog — phase 2 capability tests (FE-9154)
 *
 * Covers the two additive capabilities layered on top of the FE-9146 base:
 *   1. `type="primary"` → the yellow `.dlg-header--primary` band (design-system
 *      dialog anatomy: major-workflow actions like tune/closeout/upgrade).
 *   2. `#headerIcon` slot → replaces the default type icon in the header icon
 *      area (used by agent-scoped dialogs to host a dynamically-tinted badge).
 *
 * Both MUST be default-inert: with neither the new type nor the slot supplied,
 * BaseDialog renders exactly as the 45+ existing adopters rely on.
 *
 * The global v-dialog stub (tests/setup.js) renders its slot inline, so the
 * header/footer are queryable without teleport gymnastics.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseDialog from '@/components/common/BaseDialog.vue'

function mountDialog(props = {}, slots = {}) {
  return mount(BaseDialog, {
    props: {
      modelValue: true,
      title: 'Test Dialog',
      ...props,
    },
    slots,
  })
}

describe('BaseDialog — type="primary" band (FE-9154)', () => {
  it('renders the .dlg-header--primary band when type is primary', () => {
    const wrapper = mountDialog({ type: 'primary' })

    const header = wrapper.find('.dlg-header')
    expect(header.exists()).toBe(true)
    expect(header.classes()).toContain('dlg-header--primary')
  })

  it('does not emit a Vue prop-validation warning for type="primary"', () => {
    // A rejected validator would flag primary as invalid; the mount above only
    // proves the class renders (typeConfig fallback also renders .dlg-header).
    // This asserts the validator itself accepts the value.
    const validator = BaseDialog.props.type.validator
    expect(validator('primary')).toBe(true)
    expect(validator('info')).toBe(true)
    expect(validator('nonsense')).toBe(false)
  })

  it('default type (info) renders no colored band — capability is default-inert', () => {
    const wrapper = mountDialog()

    const header = wrapper.find('.dlg-header')
    expect(header.exists()).toBe(true)
    expect(header.classes()).not.toContain('dlg-header--primary')
    expect(header.classes()).not.toContain('dlg-header--warning')
    expect(header.classes()).not.toContain('dlg-header--danger')
  })

  it('warning/danger bands are unaffected by the primary addition', () => {
    expect(mountDialog({ type: 'warning' }).find('.dlg-header').classes())
      .toContain('dlg-header--warning')
    expect(mountDialog({ type: 'danger' }).find('.dlg-header').classes())
      .toContain('dlg-header--danger')
  })
})

describe('BaseDialog — #headerIcon slot (FE-9154)', () => {
  it('renders #headerIcon slot content in the header when provided', () => {
    const wrapper = mountDialog(
      {},
      { headerIcon: '<div class="agent-badge-sq custom-badge">IM</div>' },
    )

    const header = wrapper.find('.dlg-header')
    expect(header.find('.custom-badge').exists()).toBe(true)
    expect(header.text()).toContain('IM')
  })

  it('suppresses the default type icon when #headerIcon is provided', () => {
    const wrapper = mountDialog(
      {},
      { headerIcon: '<div class="custom-badge">IM</div>' },
    )

    // The slot REPLACES the default icon area — no leftover .dlg-icon.
    expect(wrapper.find('.dlg-icon').exists()).toBe(false)
  })

  it('renders the default type icon when #headerIcon is NOT provided (default-inert)', () => {
    const wrapper = mountDialog()

    // Fallback: the built-in .dlg-icon still renders exactly as the 45+
    // existing adopters rely on.
    expect(wrapper.find('.dlg-icon').exists()).toBe(true)
  })

  it('still honors hideIcon (no default icon, no slot) → header has no icon', () => {
    const wrapper = mountDialog({ hideIcon: true })
    expect(wrapper.find('.dlg-icon').exists()).toBe(false)
  })
})
