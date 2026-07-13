import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    // De-flake 2026-05-28: vitest pipes intercepted console output to the main
    // process over the worker RPC channel. Under parallel workers a console
    // log emitted as a worker is tearing down races the RPC close, surfacing as
    // "EnvironmentTeardownError: Closing rpc while onUserConsoleLog was pending"
    // and failing the whole run non-deterministically even when every test
    // passes. Disabling interception removes that RPC path (logs print
    // directly to stdout instead). Does not affect vi.spyOn(console) assertions.
    disableConsoleIntercept: true,
    include: ['tests/**/*.spec.js', 'tests/**/*.spec.ts', 'tests/**/*.spec.vue', 'src/**/*.spec.js', 'src/**/*.spec.ts', 'src/**/*.spec.vue'],
    exclude: ['tests/e2e/**', '**/node_modules/**'],
    server: {
      deps: {
        inline: ['vuetify']
      }
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
      '@': path.resolve(__dirname, './src'),
      '/icons': path.resolve(__dirname, './public/icons'),
    }
  }
})
