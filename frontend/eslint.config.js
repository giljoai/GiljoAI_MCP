import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import globals from 'globals'

export default [
  {
    ignores: [
      'node_modules/',
      'dist/',
      'build/',
      'public/',
      '*.min.js',
      'vendor/',
      'coverage/',
      '__tests__/',
      'tests/',
      'playwright-report/',
      'test-results/',
      'src/types/**/*.ts',
      'src/**/*.ts',
      'src/integrations/**',
      'src/components/messages/**',
      'src/components/settings/ContextPriorityConfig.vue', // Uses lang="ts", needs TS parser in ESLint config
      'src/components/ui/**',
      'src/components/__tests__/StatusBadge.spec.js',
    ],
  },
  {
    files: ['src/**/*.{js,mjs,jsx,ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.vitest,
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_|^e$|^err$|^error$|^props$|^emit$',
          varsIgnorePattern: '^_|^err|^e$|^error$|^props$|^emit$|^theme$',
        },
      ],
      'prefer-const': 'error',
      'prefer-template': 'error',
      'prefer-arrow-callback': 'error',
      'no-var': 'error',
    },
  },
  {
    files: ['src/**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: '@babel/eslint-parser',
        requireConfigFile: false,
        sourceType: 'module',
        ecmaVersion: 2022,
        extraFileExtensions: ['.vue'],
        ecmaFeatures: {
          jsx: true,
          typescript: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.vitest,
      },
    },
    rules: {
      ...pluginVue.configs['vue3-recommended'].rules,
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'error',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_|^e$|^err$|^error$|^props$|^emit$',
          varsIgnorePattern: '^_|^err|^e$|^error$|^props$|^emit$|^theme$',
        },
      ],
      'prefer-const': 'error',
      'prefer-template': 'error',
      'prefer-arrow-callback': 'error',
      'no-var': 'error',
    },
    plugins: {
      vue: pluginVue,
    },
  },
  {
    // SEC-0003: these files intentionally use v-html and are audited to route
    // every value through the hardened useSanitizeMarkdown / sanitizeHtml
    // pipeline (see per-site justification comments in each file). The
    // vue/no-v-html rule is disabled here rather than via inline
    // `<!-- eslint-disable-next-line -->` comments because eslint-plugin-vue
    // v9.20 under ESLint flat config does not honour HTML-comment directives
    // (fixed in eslint-plugin-vue >=9.25). Keep this list MINIMAL -- any new
    // v-html site requires a separate reviewed entry.
    files: [
      'src/components/DatabaseConnection.vue',
      'src/components/messages/BroadcastPanel.vue',
      'src/components/messages/MessageItem.vue',
      'src/views/UserGuideView.vue',
    ],
    rules: {
      'vue/no-v-html': 'off',
    },
  },
  {
    files: ['src/**/*.spec.js', 'src/__tests__/**/*.js'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.vitest,
      },
    },
  },
]
