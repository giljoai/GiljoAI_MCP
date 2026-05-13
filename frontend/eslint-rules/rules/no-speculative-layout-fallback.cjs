/**
 * giljo-internal/no-speculative-layout-fallback
 *
 * Flags computed layout resolvers that fall back to a side-effecting layout
 * (DashboardLayout, AppLayout, MainLayout, etc.) when route.name is undefined.
 *
 * Anti-pattern E from the IMP-0013 audit: during the first navigation,
 * route.name can be undefined and a fallback to a layout that mounts
 * authenticated chrome (sidebar, WebSocket connection) causes a visible
 * flash of the wrong layout and spurious network traffic. Fall back to the
 * zero-side-effect AuthLayout (or equivalent) instead.
 */
'use strict'

const SIDE_EFFECT_LAYOUTS = new Set([
  'DashboardLayout',
  'AppLayout',
  'MainLayout',
  'DefaultLayout',
  'AdminLayout',
])

function getStringLikeValue(node) {
  if (!node) return null
  if (node.type === 'Literal' && typeof node.value === 'string') return node.value
  if (node.type === 'Identifier') return node.name
  return null
}

function checksRouteNameUndefined(test) {
  if (!test) return false
  // route.name === undefined  /  !route.name  /  route.name == null
  if (test.type === 'BinaryExpression' && (test.operator === '===' || test.operator === '==')) {
    const a = test.left
    const b = test.right
    const idIsRouteName = (n) =>
      n && n.type === 'MemberExpression' && n.property && n.property.name === 'name' &&
      n.object && n.object.type === 'Identifier' && /route/i.test(n.object.name)
    const isUndef = (n) =>
      (n && n.type === 'Identifier' && n.name === 'undefined') ||
      (n && n.type === 'Literal' && n.value === null)
    return (idIsRouteName(a) && isUndef(b)) || (idIsRouteName(b) && isUndef(a))
  }
  if (test.type === 'UnaryExpression' && test.operator === '!') {
    const inner = test.argument
    return (
      inner && inner.type === 'MemberExpression' && inner.property && inner.property.name === 'name'
    )
  }
  return false
}

module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'layout resolvers must default to a zero-side-effect layout (e.g. AuthLayout) when route.name is undefined',
    },
    schema: [],
    messages: {
      sideEffectFallback:
        'Layout fallback when route.name is undefined returns "{{layout}}", which mounts authenticated chrome. Fall back to AuthLayout (or another zero-side-effect layout) on the first navigation (IMP-0013 anti-pattern E).',
    },
  },
  create(context) {
    return {
      ConditionalExpression(node) {
        if (!checksRouteNameUndefined(node.test)) return
        // consequent runs when test true (route.name undefined). Flag if it resolves to a side-effect layout.
        const fallback = getStringLikeValue(node.consequent)
        if (fallback && SIDE_EFFECT_LAYOUTS.has(fallback)) {
          context.report({ node: node.consequent, messageId: 'sideEffectFallback', data: { layout: fallback } })
        }
      },
      LogicalExpression(node) {
        // route.name || 'DashboardLayout'
        if (node.operator !== '||') return
        const left = node.left
        const right = node.right
        const isRouteName =
          left.type === 'MemberExpression' && left.property && left.property.name === 'name' &&
          left.object && left.object.type === 'Identifier' && /route/i.test(left.object.name)
        if (!isRouteName) return
        const fallback = getStringLikeValue(right)
        if (fallback && SIDE_EFFECT_LAYOUTS.has(fallback)) {
          context.report({ node: right, messageId: 'sideEffectFallback', data: { layout: fallback } })
        }
      },
    }
  },
}
