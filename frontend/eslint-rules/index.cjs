/**
 * Local ESLint plugin: giljo-internal
 *
 * Eight rules wired in via IMP-0013 Phase 4 to catch the five confirmed
 * anti-patterns from an internal quality-sweep audit, plus
 * three repo-hygiene rules.
 *
 * Loaded by eslint.config.js as a local CommonJS module. Not published to npm.
 */
'use strict'

const noManualApiUrlComposition = require('./rules/no-manual-api-url-composition.cjs')
const noViteIgnoreSaasImport = require('./rules/no-vite-ignore-saas-import.cjs')
const vueRouterInstallAfterRoutes = require('./rules/vue-router-install-after-routes.cjs')
const axiosInterceptorRouteMetaAware = require('./rules/axios-interceptor-route-meta-aware.cjs')
const noSpeculativeLayoutFallback = require('./rules/no-speculative-layout-fallback.cjs')
const noOrphanedExports = require('./rules/no-orphaned-exports.cjs')
const noStaleTodos = require('./rules/no-stale-todos.cjs')
const noScatteredModeChecks = require('./rules/no-scattered-mode-checks.cjs')
const noVuetifyDialogChrome = require('./rules/no-vuetify-dialog-chrome.cjs')
const noOptionalCallOnApi = require('./rules/no-optional-call-on-api.cjs')

module.exports = {
  meta: { name: 'eslint-plugin-giljo-internal', version: '1.0.0' },
  rules: {
    'no-manual-api-url-composition': noManualApiUrlComposition,
    'no-vite-ignore-saas-import': noViteIgnoreSaasImport,
    'vue-router-install-after-routes': vueRouterInstallAfterRoutes,
    'axios-interceptor-route-meta-aware': axiosInterceptorRouteMetaAware,
    'no-speculative-layout-fallback': noSpeculativeLayoutFallback,
    'no-orphaned-exports': noOrphanedExports,
    'no-stale-todos': noStaleTodos,
    'no-scattered-mode-checks': noScatteredModeChecks,
    'no-vuetify-dialog-chrome': noVuetifyDialogChrome,
    'no-optional-call-on-api': noOptionalCallOnApi,
  },
}
