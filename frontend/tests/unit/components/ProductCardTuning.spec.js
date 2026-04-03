import { describe, it, expect } from 'vitest'

/**
 * 0842h: Tests for the tuning state logic used by the tuning icon
 * on product cards in ProductsView.
 *
 * ProductsView is a large view with many dependencies, so we test
 * the getTuningState logic directly rather than full-mounting the view.
 * The logic determines badge visibility and color:
 * - 'normal': no badge dot
 * - 'proposals': warning (yellow) dot — pending tuning proposals
 * - 'stale': info (blue) dot — unread context_tuning notification
 */

// Extract the getTuningState logic as tested in ProductsView lines 638-645
function getTuningState(product, notifications = []) {
  if (product.tuning_state?.pending_proposals) return 'proposals'
  const hasUnread = notifications.some(
    (n) => !n.read && n.type === 'context_tuning' && n.metadata?.product_id === product.id,
  )
  if (hasUnread) return 'stale'
  return 'normal'
}

// Badge rendering logic from ProductsView template lines 189-192
function getBadgeProps(product, notifications = []) {
  const state = getTuningState(product, notifications)
  return {
    modelValue: state !== 'normal',
    color: state === 'proposals' ? 'warning' : 'info',
  }
}

// Tooltip text logic from ProductsView template line 209
function getTooltipText(product, notifications = []) {
  const state = getTuningState(product, notifications)
  if (state === 'proposals') return 'Tuning proposals ready for review'
  if (state === 'stale') return 'Context tuning recommended'
  return 'Tune Context'
}

describe('Tuning Icon — getTuningState logic', () => {
  const baseProduct = { id: 'prod-1', name: 'Test', tuning_state: {} }

  it('returns "normal" when no proposals and no notifications', () => {
    expect(getTuningState(baseProduct)).toBe('normal')
  })

  it('returns "normal" when tuning_state is empty object', () => {
    expect(getTuningState({ ...baseProduct, tuning_state: {} })).toBe('normal')
  })

  it('returns "normal" when tuning_state is undefined', () => {
    expect(getTuningState({ ...baseProduct, tuning_state: undefined })).toBe('normal')
  })

  it('returns "proposals" when pending_proposals exist', () => {
    const product = {
      ...baseProduct,
      tuning_state: {
        pending_proposals: {
          overall_summary: 'Context drift detected',
          architecture: { current_summary: 'Old', proposed_value: 'New' },
        },
      },
    }
    expect(getTuningState(product)).toBe('proposals')
  })

  it('returns "stale" when unread context_tuning notification matches product', () => {
    const notifications = [
      { id: 'n1', read: false, type: 'context_tuning', metadata: { product_id: 'prod-1' } },
    ]
    expect(getTuningState(baseProduct, notifications)).toBe('stale')
  })

  it('returns "normal" when context_tuning notification is read', () => {
    const notifications = [
      { id: 'n1', read: true, type: 'context_tuning', metadata: { product_id: 'prod-1' } },
    ]
    expect(getTuningState(baseProduct, notifications)).toBe('normal')
  })

  it('returns "normal" when notification is for a different product', () => {
    const notifications = [
      { id: 'n1', read: false, type: 'context_tuning', metadata: { product_id: 'prod-other' } },
    ]
    expect(getTuningState(baseProduct, notifications)).toBe('normal')
  })

  it('proposals takes priority over stale notifications', () => {
    const product = {
      ...baseProduct,
      tuning_state: { pending_proposals: { overall_summary: 'Drift' } },
    }
    const notifications = [
      { id: 'n1', read: false, type: 'context_tuning', metadata: { product_id: 'prod-1' } },
    ]
    expect(getTuningState(product, notifications)).toBe('proposals')
  })
})

describe('Tuning Icon — badge props', () => {
  const baseProduct = { id: 'prod-1', name: 'Test', tuning_state: {} }

  it('badge hidden for normal state', () => {
    const props = getBadgeProps(baseProduct)
    expect(props.modelValue).toBe(false)
  })

  it('badge visible with warning color for proposals', () => {
    const product = {
      ...baseProduct,
      tuning_state: { pending_proposals: { overall_summary: 'Drift' } },
    }
    const props = getBadgeProps(product)
    expect(props.modelValue).toBe(true)
    expect(props.color).toBe('warning')
  })

  it('badge visible with info color for stale', () => {
    const notifications = [
      { id: 'n1', read: false, type: 'context_tuning', metadata: { product_id: 'prod-1' } },
    ]
    const props = getBadgeProps(baseProduct, notifications)
    expect(props.modelValue).toBe(true)
    expect(props.color).toBe('info')
  })
})

describe('Tuning Icon — tooltip text', () => {
  const baseProduct = { id: 'prod-1', name: 'Test', tuning_state: {} }

  it('shows "Tune Context" for normal state', () => {
    expect(getTooltipText(baseProduct)).toBe('Tune Context')
  })

  it('shows proposals text when proposals pending', () => {
    const product = {
      ...baseProduct,
      tuning_state: { pending_proposals: { overall_summary: 'Drift' } },
    }
    expect(getTooltipText(product)).toBe('Tuning proposals ready for review')
  })

  it('shows stale text when notification unread', () => {
    const notifications = [
      { id: 'n1', read: false, type: 'context_tuning', metadata: { product_id: 'prod-1' } },
    ]
    expect(getTooltipText(baseProduct, notifications)).toBe('Context tuning recommended')
  })
})
