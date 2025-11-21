import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import MessageInput from '@/components/projects/MessageInput.vue'

describe('MessageInput - Position Prop (Handover 0231 Phase 4)', () => {
  it('defaults to inline position', () => {
    const wrapper = mount(MessageInput, {
      props: { jobId: 'test-job-1' }
    })

    expect(wrapper.classes()).toContain('position-inline')
  })

  it('applies modal position class', () => {
    const wrapper = mount(MessageInput, {
      props: { jobId: 'test-job-1', position: 'modal' }
    })

    expect(wrapper.classes()).toContain('position-modal')
  })

  it('applies sticky position class', () => {
    const wrapper = mount(MessageInput, {
      props: { jobId: 'test-job-1', position: 'sticky' }
    })

    expect(wrapper.classes()).toContain('position-sticky')
  })

  it('validates position prop values', () => {
    // Valid values
    expect(() => {
      mount(MessageInput, { props: { jobId: 'test', position: 'inline' } })
    }).not.toThrow()

    expect(() => {
      mount(MessageInput, { props: { jobId: 'test', position: 'modal' } })
    }).not.toThrow()

    expect(() => {
      mount(MessageInput, { props: { jobId: 'test', position: 'sticky' } })
    }).not.toThrow()
  })
})
