import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const require = createRequire(import.meta.url)
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// CSS loader and transformer
export function load(url, context, defaultLoad) {
  if (url.endsWith('.css')) {
    return {
      format: 'module',
      source: 'export default ""',
      shortCircuit: true
    }
  }
  return defaultLoad(url, context, defaultLoad)
}

// Optional: Add resolver to handle CSS imports
export function resolve(specifier, context, defaultResolve) {
  if (specifier.endsWith('.css')) {
    return {
      url: specifier,
      format: 'module'
    }
  }
  return defaultResolve(specifier, context, defaultResolve)
}