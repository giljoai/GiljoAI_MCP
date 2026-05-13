/**
 * giljo-internal/vue-router-install-after-routes
 *
 * Flags `app.use(router)` calls that occur in the same module BEFORE one or
 * more `router.addRoute(...)` calls. Vue Router resolves routes at install
 * time; if dynamic routes are added afterwards, the very first navigation
 * (the bootstrap one) can land on the wrong route — anti-pattern C from the
 * IMP-0013 audit.
 *
 * Heuristic: within a module, if both `<id>.addRoute(...)` and
 * `<x>.use(<id>)` appear, then the `.use()` must be lexically after every
 * `addRoute()` for that identifier.
 */
'use strict'

function getCalleeName(node) {
  if (!node || node.type !== 'MemberExpression') return null
  if (node.property.type !== 'Identifier') return null
  return node.property.name
}

module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'app.use(router) must be called AFTER all router.addRoute(...) calls in the bootstrap module',
    },
    schema: [],
    messages: {
      ordering:
        'app.use({{routerName}}) appears before {{routerName}}.addRoute(...) on line {{addLine}}. Install the router AFTER all addRoute() calls so the first navigation resolves correctly.',
    },
  },
  create(context) {
    const addRouteCalls = [] // {name, line, node}
    const useCalls = [] // {arg, line, node}
    return {
      CallExpression(node) {
        const name = getCalleeName(node.callee)
        if (name === 'addRoute') {
          // router.addRoute(...) -- record the object name
          const obj = node.callee.object
          const id = obj && obj.type === 'Identifier' ? obj.name : null
          if (id) addRouteCalls.push({ name: id, line: node.loc.start.line, node })
        } else if (name === 'use') {
          // app.use(router) -- record first arg if identifier
          const arg = node.arguments[0]
          if (arg && arg.type === 'Identifier') {
            useCalls.push({ arg: arg.name, line: node.loc.start.line, node })
          }
        }
      },
      'Program:exit'() {
        for (const use of useCalls) {
          // Find any addRoute for the same identifier with a later line.
          const laterAdd = addRouteCalls.find(
            (a) => a.name === use.arg && a.line > use.line,
          )
          if (laterAdd) {
            context.report({
              node: use.node,
              messageId: 'ordering',
              data: { routerName: use.arg, addLine: String(laterAdd.line) },
            })
          }
        }
      },
    }
  },
}
