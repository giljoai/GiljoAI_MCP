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
      'src/components/settings/ContextPriorityConfig.vue',
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
      'vue/no-v-html': 'warn',
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
