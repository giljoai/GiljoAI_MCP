/**
 * giljo-internal/no-scattered-mode-checks
 *
 * Flags scattered `mode === 'ce' | 'saas' | 'demo'` and
 * `GILJO_MODE === '...'` comparisons outside a centralized capability
 * module (composables/useEditionCapabilities.* or saas/composables/useSaasMode.*).
 *
 * The audit found 12+ files reading mode directly. Per CLAUDE.md edition
 * gating patterns, capability checks should be funneled through one
 * module so adding a fourth edition is a one-file change.
 */
'use strict'

const MODE_VALUES = new Set(['ce', 'saas', 'demo'])

function isAllowlistedFilename(filename) {
  if (!filename) return false
  const lower = filename.replace(/\\/g, '/').toLowerCase()
  // The capability module itself is allowed to switch on mode directly.
  return (
    lower.includes('/composables/useeditioncapabilities') ||
    lower.includes('/saas/composables/usesaasmode') ||
    lower.includes('/composables/usegiljomode') ||
    lower.includes('/services/configservice') // mode source of truth
  )
}

function getStringLit(node) {
  if (!node) return null
  if (node.type === 'Literal' && typeof node.value === 'string') return node.value
  return null
}

function leftSideIsModeIdent(node) {
  if (!node) return false
  if (node.type === 'Identifier') {
    return /mode$/i.test(node.name) || node.name === 'GILJO_MODE'
  }
  if (node.type === 'MemberExpression' && node.property && node.property.name) {
    return /mode$/i.test(node.property.name) || node.property.name === 'GILJO_MODE'
  }
  return false
}

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description:
        'disallow scattered `mode === "ce" | "saas" | "demo"` checks outside a centralized capability module',
    },
    schema: [],
    messages: {
      scattered:
        'Scattered mode check (`{{name}} === "{{value}}"`). Funnel through useEditionCapabilities / useSaasMode so adding a new edition is a one-file change.',
    },
  },
  create(context) {
    const filename = context.filename || context.getFilename()
    if (isAllowlistedFilename(filename)) return {}
    return {
      BinaryExpression(node) {
        if (node.operator !== '===' && node.operator !== '==' && node.operator !== '!==' && node.operator !== '!=') return
        const lit = getStringLit(node.right) || getStringLit(node.left)
        if (!lit || !MODE_VALUES.has(lit)) return
        const ident = leftSideIsModeIdent(node.left) ? node.left : leftSideIsModeIdent(node.right) ? node.right : null
        if (!ident) return
        const name = ident.type === 'Identifier' ? ident.name : ident.property.name
        context.report({ node, messageId: 'scattered', data: { name, value: lit } })
      },
    }
  },
}
