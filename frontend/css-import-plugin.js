export default function cssImportPlugin() {
  return {
    name: 'css-import-plugin',
    resolveId(source) {
      if (source.endsWith('.css')) {
        return { id: source }
      }
      return null
    },
    load(id) {
      if (id.endsWith('.css')) {
        return ''
      }
      return null
    }
  }
}