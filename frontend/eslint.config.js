import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
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
  ...pluginVue.configs['flat/recommended'].map((config) => ({
    ...config,
    files: ['src/**/*.vue'],
  })),
  {
    files: ['src/**/*.vue'],
    languageOptions: {
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
