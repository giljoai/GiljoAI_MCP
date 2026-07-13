/**
 * giljo-internal/no-optional-call-on-api
 *
 * Flags optional-chaining method INVOCATIONS on the static `api` service
 * object — `api.x?.y()` / `api.x?.y?.()` (an optional CALL, i.e. the
 * CallExpression itself carries `?.()`). When the method is missing the
 * optional-call short-circuits to `undefined` and silently no-ops instead
 * of throwing, which is exactly how a dead `api.products?.metrics?.()`
 * survived a dead-code pass AND a perf sprint (FE-3007 audit).
 *
 * A missing endpoint must CRASH in dev. Call api methods non-optionally
 * (`api.x.y()`); optional chaining on a property access (`api.products?.list()`,
 * which still THROWS if `list` is undefined) is fine and NOT flagged — only the
 * optional INVOCATION `?.()` is banned.
 */
'use strict'

/**
 * Descend a callee chain to its root object identifier name.
 * `api.products?.metrics` -> 'api'.
 */
function rootObjectName(node) {
  let cur = node
  while (cur) {
    switch (cur.type) {
      case 'Identifier':
        return cur.name
      case 'MemberExpression':
        cur = cur.object
        break
      case 'CallExpression':
        cur = cur.callee
        break
      case 'ChainExpression':
        cur = cur.expression
        break
      case 'TSNonNullExpression':
        cur = cur.expression
        break
      default:
        return null
    }
  }
  return null
}

module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'disallow optional-chaining method invocations on the static api object (api.x?.y()); a missing endpoint must throw in dev, not silently no-op',
    },
    schema: [],
    messages: {
      optionalCall:
        'Optional-call `?.()` on the api object silently no-ops when the endpoint is missing (how a dead api.products?.metrics?.() survived two cleanup passes). Invoke it non-optionally (api.x.y()) so a missing endpoint throws in dev.',
    },
  },
  create(context) {
    return {
      CallExpression(node) {
        // Only the optional INVOCATION form `?.()` — not a normal call on an
        // optionally-accessed member (api.products?.list(), which throws if
        // `list` is missing, the desired crash-in-dev behaviour).
        if (node.optional !== true) return
        if (rootObjectName(node.callee) === 'api') {
          context.report({ node, messageId: 'optionalCall' })
        }
      },
    }
  },
}
