/**
 * IMP-0013 Phase 4 — regression fixtures for the 8 custom ESLint rules.
 *
 * Each rule gets at least one "bad" sample that MUST trigger and at least
 * one "good" sample that MUST NOT trigger. Uses ESLint's RuleTester which
 * registers its own describe/it; we call it at the top level so vitest's
 * suite-collection phase sees the assertions.
 */
import { RuleTester } from 'eslint'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const plugin = require('../../eslint-rules/index.cjs')

const ruleTester = new RuleTester({
  languageOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
})

// Prime the no-orphaned-exports cache with a deterministic set so the test
// is hermetic (no disk scan).
plugin.rules['no-orphaned-exports']._setCache(new Set(['Used']))

ruleTester.run(
  'giljo-internal/no-manual-api-url-composition',
  plugin.rules['no-manual-api-url-composition'],
  {
    valid: [
      { code: 'const u = getApiBaseUrl()' },
      { code: 'const u = `${origin}/api`' },
      {
        code:
          '// eslint-allow giljo-internal/no-manual-api-url-composition\nconst u = `${proto}://${host}:${port}`',
      },
    ],
    invalid: [
      {
        code: 'const u = `${proto}://${host}:${port}`',
        errors: [{ messageId: 'manual' }],
      },
    ],
  },
)

ruleTester.run(
  'giljo-internal/no-vite-ignore-saas-import',
  plugin.rules['no-vite-ignore-saas-import'],
  {
    valid: [
      { code: "const m = import('./foo.js')" },
      { code: "const all = import.meta.glob('./modules/*.js')" },
    ],
    invalid: [
      {
        code: "const m = import(/* @vite-ignore */ pathString)",
        errors: [{ messageId: 'viteIgnore' }],
      },
    ],
  },
)

ruleTester.run(
  'giljo-internal/vue-router-install-after-routes',
  plugin.rules['vue-router-install-after-routes'],
  {
    valid: [
      {
        code: "router.addRoute({ path: '/x', component: X });\napp.use(router);",
      },
      { code: 'app.use(somePinia)' },
    ],
    invalid: [
      {
        code: "app.use(router);\nrouter.addRoute({ path: '/x', component: X });",
        errors: [{ messageId: 'ordering' }],
      },
    ],
  },
)

ruleTester.run(
  'giljo-internal/axios-interceptor-route-meta-aware',
  plugin.rules['axios-interceptor-route-meta-aware'],
  {
    valid: [
      {
        code:
          "apiClient.interceptors.response.use(null, (error) => {\n" +
          "  if (error.config?.meta?.requiresAuth === false) return Promise.reject(error);\n" +
          "  router.push('/login');\n" +
          "});",
      },
      { code: "router.push('/login')" },
    ],
    invalid: [
      {
        code:
          "apiClient.interceptors.response.use(null, (error) => {\n" +
          "  router.push('/login');\n" +
          "});",
        errors: [{ messageId: 'missingGuard' }],
      },
    ],
  },
)

ruleTester.run(
  'giljo-internal/no-speculative-layout-fallback',
  plugin.rules['no-speculative-layout-fallback'],
  {
    valid: [
      { code: "const layout = route.name === undefined ? 'AuthLayout' : pick(route)" },
      { code: "const layout = route.name || 'AuthLayout'" },
    ],
    invalid: [
      {
        code: "const layout = route.name === undefined ? 'DashboardLayout' : pick(route)",
        errors: [{ messageId: 'sideEffectFallback' }],
      },
      {
        code: "const layout = route.name || 'DashboardLayout'",
        errors: [{ messageId: 'sideEffectFallback' }],
      },
    ],
  },
)

ruleTester.run(
  'giljo-internal/no-orphaned-exports',
  plugin.rules['no-orphaned-exports'],
  {
    valid: [{ code: 'export function Used() {}' }],
    invalid: [
      {
        code: 'export function Orphan() {}',
        errors: [{ messageId: 'orphan' }],
      },
    ],
  },
)

ruleTester.run('giljo-internal/no-stale-todos', plugin.rules['no-stale-todos'], {
  valid: [
    // Recent date, within 30 days of "now"
    {
      code: '// TODO 2026-05-10 fix later',
      options: [{ now: '2026-05-13' }],
    },
    // Has project id → ok regardless of age
    { code: '// TODO BE-5042 (2024-01-01) tracked elsewhere' },
  ],
  invalid: [
    {
      code: '// TODO 2025-01-01 fix this someday',
      options: [{ now: '2026-05-13' }],
      errors: [{ messageId: 'stale' }],
    },
    {
      code: '// FIXME totally unattributed',
      errors: [{ messageId: 'anonymous' }],
    },
  ],
})

ruleTester.run(
  'giljo-internal/no-scattered-mode-checks',
  plugin.rules['no-scattered-mode-checks'],
  {
    valid: [
      { code: 'if (isSaas()) doThing()' },
      {
        code: "if (mode === 'saas') doThing()",
        filename: '/x/composables/useEditionCapabilities.js',
      },
    ],
    invalid: [
      {
        code: "if (mode === 'saas') doThing()",
        filename: '/x/components/Foo.vue.js',
        errors: [{ messageId: 'scattered' }],
      },
      {
        code: "if (GILJO_MODE === 'demo') skip()",
        filename: '/x/services/foo.js',
        errors: [{ messageId: 'scattered' }],
      },
    ],
  },
)
