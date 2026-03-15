import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    include: ['tests/**/*.spec.js', 'tests/**/*.spec.ts', 'tests/**/*.spec.vue', 'src/**/*.spec.js', 'src/**/*.spec.ts', 'src/**/*.spec.vue'],
    exclude: ['tests/e2e/**', '**/node_modules/**'],
    deps: {
      inline: ['vuetify']
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: [
        'src/components/**',
        'src/services/**',
        'src/stores/**'
      ],
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/*.d.ts',
        '**/__tests__/**',
        '**/index.js'
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
