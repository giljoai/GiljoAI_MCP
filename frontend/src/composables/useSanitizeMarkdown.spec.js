import { describe, it, expect } from 'vitest'
import { useSanitizeMarkdown, sanitizeHtml } from './useSanitizeMarkdown'

describe('useSanitizeMarkdown', () => {
  const { sanitizeMarkdown } = useSanitizeMarkdown()

  it('returns empty string for falsy input', () => {
    expect(sanitizeMarkdown('')).toBe('')
    expect(sanitizeMarkdown(null)).toBe('')
    expect(sanitizeMarkdown(undefined)).toBe('')
  })

  it('renders basic markdown to sanitized HTML', () => {
    const out = sanitizeMarkdown('**bold** and *italic*')
    expect(out).toContain('<strong>bold</strong>')
    expect(out).toContain('<em>italic</em>')
  })

  it('strips script tags from markdown input', () => {
    const out = sanitizeMarkdown('Hello <script>alert(1)</script>')
    expect(out).not.toContain('<script>')
    expect(out).not.toContain('alert(1)')
  })

  it('strips inline event handlers', () => {
    const out = sanitizeMarkdown('<img src="x" onerror="alert(1)">')
    expect(out).not.toContain('onerror')
  })

  it('blocks javascript: URLs in links', () => {
    const out = sanitizeMarkdown('[click](javascript:alert(1))')
    expect(out).not.toMatch(/href\s*=\s*["']?javascript:/i)
  })

  it('blocks data: URIs on images', () => {
    const out = sanitizeMarkdown('<img src="data:text/html,<script>alert(1)</script>">')
    expect(out).not.toMatch(/src\s*=\s*["']?data:/i)
  })

  it('allows tables', () => {
    const out = sanitizeMarkdown('| a | b |\n|---|---|\n| 1 | 2 |')
    expect(out).toContain('<table>')
    expect(out).toContain('<td>1</td>')
  })
})

describe('sanitizeHtml', () => {
  it('returns empty string for falsy input', () => {
    expect(sanitizeHtml('')).toBe('')
    expect(sanitizeHtml(null)).toBe('')
  })

  it('preserves allowed HTML tags', () => {
    expect(sanitizeHtml('<strong>ok</strong>')).toContain('<strong>ok</strong>')
  })

  it('strips script tags', () => {
    expect(sanitizeHtml('<script>alert(1)</script>')).not.toContain('<script>')
  })

  it('strips event handlers', () => {
    const out = sanitizeHtml('<a href="#" onclick="alert(1)">x</a>')
    expect(out).not.toContain('onclick')
  })

  it('blocks javascript: hrefs', () => {
    const out = sanitizeHtml('<a href="javascript:alert(1)">x</a>')
    expect(out).not.toMatch(/href\s*=\s*["']?javascript:/i)
  })
})
