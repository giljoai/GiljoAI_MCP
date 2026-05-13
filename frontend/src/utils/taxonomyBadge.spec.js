/**
 * Unit tests for taxonomyBadgeStyle — the shared util consumed by
 * ProjectsView (.project-id-badge) and TasksView (.taxonomy-badge).
 *
 * FE-5046: extracted from ProjectsView's local projectIdBadgeStyle()
 * helper. The two views must produce identical inline styles for the
 * same color input so the Type+Serial badge stays visually consistent.
 */
import { describe, it, expect } from 'vitest'
import { taxonomyBadgeStyle, DEFAULT_PROJECT_TYPE_COLOR } from '@/utils/taxonomyBadge'

describe('taxonomyBadgeStyle', () => {
  it('returns a 15% tint background and full-brightness foreground for a given hex', () => {
    const style = taxonomyBadgeStyle('#6DB3E4')
    expect(style).toEqual({
      backgroundColor: '#6DB3E426',
      color: '#6DB3E4',
    })
  })

  it('falls back to DEFAULT_PROJECT_TYPE_COLOR when color is empty/null/undefined', () => {
    const fallbackBg = `${DEFAULT_PROJECT_TYPE_COLOR}26`
    expect(taxonomyBadgeStyle(null)).toEqual({
      backgroundColor: fallbackBg,
      color: DEFAULT_PROJECT_TYPE_COLOR,
    })
    expect(taxonomyBadgeStyle(undefined)).toEqual({
      backgroundColor: fallbackBg,
      color: DEFAULT_PROJECT_TYPE_COLOR,
    })
    expect(taxonomyBadgeStyle('')).toEqual({
      backgroundColor: fallbackBg,
      color: DEFAULT_PROJECT_TYPE_COLOR,
    })
  })
})
