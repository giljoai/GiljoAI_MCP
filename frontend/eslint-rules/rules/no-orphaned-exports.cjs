/**
 * giljo-internal/no-orphaned-exports
 *
 * WARN-level scaffold. Flags exports in a file that appear to be unused
 * project-wide. ESLint runs per-file and has no cross-file index in
 * standard mode, so this rule uses a heuristic: at lint time it greps the
 * project (capped) for an import of the exported name. Findings are
 * warnings, not errors, to avoid false positives on dynamic imports and
 * re-export barrels.
 *
 * Performance: the project scan is cached on first invocation per rule
 * instance, and the scan is bounded to `src/`. For large monorepos this
 * may need refinement; the IMP-0013 audit accepted warn-level as the
 * tradeoff.
 */
'use strict'

const fs = require('fs')
const path = require('path')

let projectImportIndex = null

function buildProjectImportIndex(projectRoot) {
  const index = new Set()
  function walk(dir) {
    let entries
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      const full = path.join(dir, e.name)
      if (e.isDirectory()) {
        if (e.name === 'node_modules' || e.name === 'dist' || e.name === '__tests__') continue
        walk(full)
      } else if (/\.(js|mjs|ts|tsx|jsx|vue)$/.test(e.name)) {
        let txt
        try {
          txt = fs.readFileSync(full, 'utf8')
        } catch {
          continue
        }
        // Capture identifiers in: import { X, Y as Z } from '...'
        const importRe = /import\s+(?:[\w*\s,{}]+)\s+from\s+['"][^'"]+['"]/g
        const matches = txt.match(importRe) || []
        for (const m of matches) {
          const braceMatch = m.match(/\{([^}]*)\}/)
          if (braceMatch) {
            for (const piece of braceMatch[1].split(',')) {
              const name = piece.trim().split(/\s+as\s+/)[0].trim()
              if (name) index.add(name)
            }
          }
          const defaultMatch = m.match(/import\s+([A-Za-z_$][\w$]*)/)
          if (defaultMatch) index.add(defaultMatch[1])
        }
        // Also dynamic: import('...').then(({ X }) => ...)
        const dynRe = /\{\s*([A-Za-z_$][\w$,\s]*)\}\s*=>/g
        let dm
        while ((dm = dynRe.exec(txt)) !== null) {
          for (const piece of dm[1].split(',')) {
            const name = piece.trim()
            if (name) index.add(name)
          }
        }
      }
    }
  }
  walk(path.join(projectRoot, 'src'))
  return index
}

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description:
        'warn on named exports that appear to be unused project-wide (heuristic; warn level only)',
    },
    schema: [],
    messages: {
      orphan:
        'Export `{{name}}` does not appear to be imported anywhere in src/. Verify and remove if dead.',
    },
  },
  create(context) {
    // Lazy-build the index. `cwd` is the project root when eslint is invoked from npm run lint.
    const cwd = context.cwd || process.cwd()
    if (!projectImportIndex) {
      try {
        projectImportIndex = buildProjectImportIndex(cwd)
      } catch {
        projectImportIndex = new Set()
      }
    }

    return {
      ExportNamedDeclaration(node) {
        // Skip re-exports `export { X } from './y'`
        if (node.source) return
        const names = []
        if (node.declaration) {
          if (node.declaration.type === 'FunctionDeclaration' || node.declaration.type === 'ClassDeclaration') {
            if (node.declaration.id) names.push(node.declaration.id.name)
          } else if (node.declaration.type === 'VariableDeclaration') {
            for (const d of node.declaration.declarations) {
              if (d.id && d.id.type === 'Identifier') names.push(d.id.name)
            }
          }
        }
        for (const spec of node.specifiers || []) {
          if (spec.exported && spec.exported.type === 'Identifier') names.push(spec.exported.name)
        }
        for (const name of names) {
          if (!projectImportIndex.has(name)) {
            context.report({ node, messageId: 'orphan', data: { name } })
          }
        }
      },
    }
  },
  // exposed for testability
  _resetCache() {
    projectImportIndex = null
  },
  _setCache(set) {
    projectImportIndex = set
  },
}
