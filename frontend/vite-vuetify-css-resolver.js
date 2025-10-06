export default function vuetifyCssResolverPlugin() {
  return {
    name: 'vuetify-css-resolver',
    resolveId(source) {
      // Match Vuetify and other CSS imports
      if (source.includes('vuetify') && source.endsWith('.css')) {
        return { id: source, external: true }
      }
      return null
    },
    load(id) {
      // For Vuetify CSS files, return an empty module
      if (id.includes('vuetify') && id.endsWith('.css')) {
        return 'export default ""'
      }
      return null
    }
  }
}