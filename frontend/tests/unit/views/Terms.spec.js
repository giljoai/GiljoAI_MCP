/**
 * Terms.vue regression spec.
 *
 * Locks in:
 *   - CE-shipped legal copy avoids naming SaaS billing vendors.
 *   - Dedicated Billing/Refunds section (§7) references the Merchant of
 *     Record, statutory withdrawal rights, and the default non-refundable stance.
 *   - Team SKU advertising softened (Team is post-Solo per
 *     SAAS_COMMERCIALIZATION.md — must not promise an SKU that doesn't
 *     exist).
 *
 * Edition: ships in CE.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import Terms from '@/views/Terms.vue'

function mountTerms() {
  return mount(Terms, {
    global: {
      stubs: {
        'v-container': { template: '<div><slot /></div>' },
        'v-card': { template: '<div><slot /></div>' },
        'router-link': { template: '<a><slot /></a>' },
      },
    },
  })
}

describe('Terms.vue', () => {
  it('keeps billing provider copy generic in CE-shipped legal text', () => {
    const wrapper = mountTerms()
    expect(wrapper.text()).toContain('billing provider')
    expect(wrapper.text()).toContain('Merchant of Record')
    expect(wrapper.text()).not.toMatch(/specific billing vendor/i)
  })

  it('has a dedicated Billing and refunds section', () => {
    const wrapper = mountTerms()
    expect(wrapper.text()).toMatch(/Billing and refunds/i)
    expect(wrapper.text()).toMatch(/invoicing/i)
    expect(wrapper.text()).toMatch(/taxes/i)
    expect(wrapper.text()).toMatch(/provider'?s refund policy/i)
  })

  it('preserves EU/UK statutory withdrawal rights language', () => {
    const wrapper = mountTerms()
    expect(wrapper.text()).toMatch(/EU\/UK customers retain\s+statutory withdrawal rights/i)
    expect(wrapper.text()).toMatch(/generally non-refundable/i)
  })

  it('routes refund exceptional cases through support@', () => {
    const wrapper = mountTerms()
    expect(wrapper.html()).toContain('mailto:support@giljo.ai')
  })

  it('does not advertise a Team SKU as if it exists today', () => {
    const wrapper = mountTerms()
    // Historical copy: "Solo / Team (SaaS)". Current copy: "Solo (SaaS)"
    // with "Additional tiers (e.g. Team) may be offered in the future".
    expect(wrapper.text()).not.toMatch(/Solo \/ Team/i)
    expect(wrapper.text()).toMatch(/Solo \(SaaS\)/i)
  })

  it('states the auto-cancel deletion rule (BE-9040d prod flip)', () => {
    const text = mountTerms().text().replace(/\s+/g, ' ')
    // Post-BE-9040d: confirming deletion auto-cancels an active
    // subscription; access ends, no further charges. Consistent with
    // Privacy §6 and the canonical Terms of Service.
    expect(text).toMatch(/confirming deletion cancels it/i)
    expect(text).toMatch(/no further charges occur/i)
    expect(text).toMatch(/immediate deletion or an optional 30-day grace/i)
    expect(text).not.toMatch(/must first cancel it in Billing/i)
  })

  it('uses only operator mailboxes from the CLAUDE.md allowlist', () => {
    const wrapper = mountTerms()
    const html = wrapper.html()
    expect(html).toContain('admin@giljo.ai')
    expect(html).toContain('support@giljo.ai')
    expect(html).not.toContain(`patrik@${'giljo.ai'}`)
    expect(html).not.toContain(`mailto:info@${'giljo.ai'}`)
  })
})
