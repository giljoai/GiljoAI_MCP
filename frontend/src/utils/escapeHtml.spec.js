import { describe, it, expect } from 'vitest'
import { escapeHtml, slugify } from './escapeHtml'

describe('escapeHtml', () => {
  it('escapes the five HTML-special characters', () => {
    expect(escapeHtml('<script>alert("x")</script>')).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'
    )
    expect(escapeHtml("it's")).toBe('it&#39;s')
    expect(escapeHtml('a & b')).toBe('a &amp; b')
  })

  it('returns empty string for null/undefined', () => {
    expect(escapeHtml(null)).toBe('')
    expect(escapeHtml(undefined)).toBe('')
    expect(escapeHtml('')).toBe('')
  })

  it('coerces non-string input to string', () => {
    expect(escapeHtml(42)).toBe('42')
    expect(escapeHtml(true)).toBe('true')
  })

  it('leaves safe text untouched', () => {
    expect(escapeHtml('hello world')).toBe('hello world')
  })
})

describe('slugify', () => {
  it('lowercases and hyphenates', () => {
    expect(slugify('Getting Started')).toBe('getting-started')
  })

  it('strips characters outside [a-z0-9-]', () => {
    expect(slugify('<script>alert(1)</script>')).toBe('scriptalert1script')
    expect(slugify('Hello, World!')).toBe('hello-world')
  })

  it('collapses runs of hyphens and trims leading/trailing', () => {
    expect(slugify('--a---b--')).toBe('a-b')
  })

  it('handles null/undefined', () => {
    expect(slugify(null)).toBe('')
    expect(slugify(undefined)).toBe('')
  })

  it('output is always safe to interpolate as an HTML id', () => {
    const out = slugify('<h2 id="x">injected</h2>')
    expect(out).toMatch(/^[a-z0-9-]*$/)
  })
})
