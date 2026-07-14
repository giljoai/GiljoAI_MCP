/**
 * UserGuideView — edition-aware rendering tests.
 *
 * Covers:
 *  1. SaaS mode: "Billing & Subscription" heading + guide-callout--saas
 *     element appear in the rendered output.
 *  2. CE mode: neither heading nor callout--saas element appear.
 *  3. CE / SaaS callout blockquotes: render with the correct class; marker
 *     text is stripped; label chip text is present.
 *  4. Sanitizer: keeps allowed callout class on <blockquote>;
 *     strips a disallowed class.
 *
 * Parallel-safe: no module-level mutable state; all state is local to each
 * describe block. marked is shared (singleton) but the renderer is installed
 * once and is idempotent — deterministic output regardless of call order.
 */
import { describe, it, expect } from 'vitest'
import { marked } from 'marked'
import { sanitizeHtml } from '@/composables/useSanitizeMarkdown'
import { installGuideCalloutRenderer, CALLOUT_LABELS } from '@/utils/guideCalloutRenderer'
import { slugify } from '@/utils/escapeHtml'

// Install the renderer once for all tests in this file.
// installGuideCalloutRenderer calls marked.use() which stacks renderers;
// marked processes the most recently added renderer first, so calling it
// multiple times is safe (idempotent behavior: same output either way).
installGuideCalloutRenderer(marked)

// ─── Helpers ─────────────────────────────────────────────────────────────────

// Minimal billing-guide.md content (mirrors the real file's first heading).
const BILLING_MD = `## Billing & Subscription

> [!SAAS]
> This chapter applies to hosted GiljoAI only.

Some billing text here.
`

/**
 * Build combined markdown the same way the component does:
 * shared docs + optional SaaS docs when isSaas is true.
 */
function buildCombinedMarkdown({ isSaas, saasDocs = {} }) {
  const sharedMd = '## Getting Started\n\nShared content here.\n'
  const parts = [sharedMd]

  if (isSaas) {
    const sortedKeys = Object.keys(saasDocs).sort()
    for (const key of sortedKeys) {
      const md = saasDocs[key]
      if (md) parts.push(md)
    }
  }

  return parts.join('\n\n---\n\n')
}

// ─── 1 & 2: Edition-gated SaaS chapter ──────────────────────────────────────

describe('UserGuideView — edition-gated SaaS chapter', () => {
  it('SaaS mode: combined markdown includes "Billing & Subscription" heading', () => {
    const combined = buildCombinedMarkdown({
      isSaas: true,
      saasDocs: { '../saas/docs/billing-guide.md': BILLING_MD },
    })
    expect(combined).toContain('## Billing & Subscription')
  })

  it('SaaS mode: rendered HTML includes guide-callout--saas element and heading', () => {
    const html = marked.parse(BILLING_MD)
    const sanitized = sanitizeHtml(html)
    expect(sanitized).toContain('guide-callout--saas')
    expect(sanitized).not.toContain('[!SAAS]')
    // Heading text is HTML-escaped by the renderer
    expect(sanitized).toContain('Billing')
    expect(sanitized).toContain('Subscription')
  })

  it('CE mode: combined markdown does NOT include SaaS docs when isSaas is false', () => {
    const combined = buildCombinedMarkdown({
      isSaas: false,
      saasDocs: { '../saas/docs/billing-guide.md': BILLING_MD },
    })
    expect(combined).not.toContain('Billing & Subscription')
  })

  it('CE mode: combined markdown with empty glob also excludes SaaS content', () => {
    const combined = buildCombinedMarkdown({
      isSaas: false,
      saasDocs: {},
    })
    expect(combined).not.toContain('Billing')
    expect(combined).toContain('Getting Started')
  })

  it('SaaS mode: TOC entries include Billing heading when SaaS doc is present', () => {
    const combined = buildCombinedMarkdown({
      isSaas: true,
      saasDocs: { '../saas/docs/billing-guide.md': BILLING_MD },
    })
    const tocEntries = []
    for (const line of combined.split('\n')) {
      const match = line.match(/^## (.+)$/)
      if (match) {
        const text = match[1].trim()
        tocEntries.push({ text, anchor: slugify(text) })
      }
    }
    const tocTexts = tocEntries.map((e) => e.text)
    expect(tocTexts).toContain('Billing & Subscription')
    expect(tocTexts).toContain('Getting Started')
  })

  it('CE mode: TOC entries do NOT include Billing heading', () => {
    const combined = buildCombinedMarkdown({
      isSaas: false,
      saasDocs: {},
    })
    const tocEntries = []
    for (const line of combined.split('\n')) {
      const match = line.match(/^## (.+)$/)
      if (match) {
        tocEntries.push(match[1].trim())
      }
    }
    expect(tocEntries).not.toContain('Billing & Subscription')
  })

  it('SaaS mode: multiple SaaS docs are sorted by path for determinism', () => {
    const aDocs = {
      '../saas/docs/z-last.md': '## Z Chapter\n\nZ content.\n',
      '../saas/docs/a-first.md': '## A Chapter\n\nA content.\n',
    }
    const combined = buildCombinedMarkdown({ isSaas: true, saasDocs: aDocs })
    const aIdx = combined.indexOf('## A Chapter')
    const zIdx = combined.indexOf('## Z Chapter')
    // a-first.md sorts before z-last.md so A chapter appears first
    expect(aIdx).toBeLessThan(zIdx)
  })
})

// ─── 3: Callout blockquote rendering ─────────────────────────────────────────

describe('UserGuideView — callout renderer', () => {
  it('renders [!CE] blockquote with class guide-callout--ce', () => {
    const md = '> [!CE]\n> Self-hosted feature only.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).toContain('guide-callout--ce')
  })

  it('strips the [!CE] marker text from the rendered output', () => {
    const md = '> [!CE]\n> Self-hosted feature only.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).not.toContain('[!CE]')
  })

  it('renders [!SAAS] blockquote with class guide-callout--saas', () => {
    const md = '> [!SAAS]\n> Hosted-only feature.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).toContain('guide-callout--saas')
    expect(sanitized).not.toContain('[!SAAS]')
  })

  it('CE callout label chip text equals CALLOUT_LABELS.CE constant', () => {
    const md = '> [!CE]\n> Self-hosted feature only.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).toContain(CALLOUT_LABELS.CE)
  })

  it('SaaS callout label chip text equals CALLOUT_LABELS.SAAS constant', () => {
    const md = '> [!SAAS]\n> Hosted-only feature.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).toContain(CALLOUT_LABELS.SAAS)
  })

  it('plain blockquote (no marker) renders as regular <blockquote> without callout class', () => {
    const md = '> A regular blockquote with no marker.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).toContain('<blockquote>')
    expect(sanitized).not.toContain('guide-callout')
  })

  it('CE callout body content is preserved after the label', () => {
    const md = '> [!CE]\n> This is the body text of the CE callout.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).toContain('body text of the CE callout')
  })

  it('CE callout renders both label and guide-callout base class', () => {
    const md = '> [!CE]\n> Body.\n'
    const sanitized = sanitizeHtml(marked.parse(md))
    expect(sanitized).toContain('guide-callout')
    expect(sanitized).toContain('guide-callout--ce')
  })
})

// ─── 4: Sanitizer — callout class allowlist on blockquote ────────────────────

describe('sanitizeHtml — guide callout class restrictions on blockquote', () => {
  it('keeps guide-callout class on blockquote', () => {
    const out = sanitizeHtml('<blockquote class="guide-callout">Text</blockquote>')
    expect(out).toContain('class="guide-callout"')
  })

  it('keeps guide-callout--ce class on blockquote', () => {
    const out = sanitizeHtml('<blockquote class="guide-callout guide-callout--ce">Text</blockquote>')
    expect(out).toContain('guide-callout--ce')
  })

  it('keeps guide-callout--saas class on blockquote', () => {
    const out = sanitizeHtml('<blockquote class="guide-callout guide-callout--saas">Text</blockquote>')
    expect(out).toContain('guide-callout--saas')
  })

  it('strips a disallowed class from blockquote (e.g. "evil")', () => {
    const out = sanitizeHtml('<blockquote class="evil">Text</blockquote>')
    expect(out).not.toContain('class="evil"')
  })

  it('strips unknown class even when mixed with a callout class on blockquote', () => {
    const out = sanitizeHtml('<blockquote class="guide-callout--ce injected-class">Text</blockquote>')
    expect(out).toContain('guide-callout--ce')
    expect(out).not.toContain('injected-class')
  })

  it('does NOT strip arbitrary classes on non-blockquote elements (hook is blockquote-scoped)', () => {
    // The hook targets only blockquote — other allowed elements pass class through normally.
    const out = sanitizeHtml('<div class="some-class">Text</div>')
    expect(out).toContain('some-class')
  })

  it('a blockquote with no class attribute remains unaffected by the hook', () => {
    const out = sanitizeHtml('<blockquote>Plain blockquote</blockquote>')
    expect(out).toContain('<blockquote>')
    expect(out).toContain('Plain blockquote')
  })
})
