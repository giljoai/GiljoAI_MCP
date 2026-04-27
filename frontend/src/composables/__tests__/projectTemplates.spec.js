import { describe, expect, it } from 'vitest'
import { PROJECT_TEMPLATES } from '../projectTemplates'

const REQUIRED_FIELDS = [
  'id',
  'cardTitle',
  'cardSubtitle',
  'icon',
  'projectName',
  'projectDescription',
]

describe('PROJECT_TEMPLATES', () => {
  it('exports exactly two templates', () => {
    expect(PROJECT_TEMPLATES).toHaveLength(2)
  })

  it('is frozen at the top level', () => {
    expect(Object.isFrozen(PROJECT_TEMPLATES)).toBe(true)
  })

  it('uses the agreed stable ids in the agreed order', () => {
    expect(PROJECT_TEMPLATES.map((t) => t.id)).toEqual([
      'new_product_bootstrap',
      'existing_product_bootstrap',
    ])
  })

  it.each(REQUIRED_FIELDS)('every template has a non-empty %s', (field) => {
    for (const tmpl of PROJECT_TEMPLATES) {
      expect(tmpl[field]).toBeTruthy()
      expect(typeof tmpl[field]).toBe('string')
      expect(tmpl[field].trim().length).toBeGreaterThan(0)
    }
  })

  it('every template description is multi-line (becomes the orchestrator brief)', () => {
    for (const tmpl of PROJECT_TEMPLATES) {
      expect(tmpl.projectDescription.split('\n').length).toBeGreaterThan(1)
    }
  })
})
