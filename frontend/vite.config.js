import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'path'
import fs from 'fs'
import yaml from 'js-yaml'

// Load frontend port from environment or use default
const FRONTEND_PORT = parseInt(process.env.VITE_FRONTEND_PORT || process.env.GILJO_FRONTEND_PORT || '7274', 10)

// v3.0 Unified Architecture: Always read dashboard_host from config.yaml
// Default to 0.0.0.0 (firewall controls access, not binding)
let dashboardHost = '0.0.0.0'
try {
  const configPath = resolve(__dirname, '../config.yaml')
  if (fs.existsSync(configPath)) {
    const configData = yaml.load(fs.readFileSync(configPath, 'utf8'))
    // v3.0: Read from server.dashboard_host (no mode-based logic)
    dashboardHost = configData?.server?.dashboard_host || '0.0.0.0'
    console.log(`[Vite] v3.0 binding to: ${dashboardHost}:${FRONTEND_PORT}`)
  } else {
    console.log(`[Vite] config.yaml not found, using default: ${dashboardHost}:${FRONTEND_PORT}`)
  }
} catch (err) {
  console.warn('[Vite] Could not read config.yaml, using default 0.0.0.0:', err.message)
}

// v3.0 Architecture: Always bind to what's in config (default 0.0.0.0)
// Firewall controls actual network access (defense in depth)
const HOST = dashboardHost

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      }
    }
  },
  server: {
    port: FRONTEND_PORT,
    host: HOST,
    strictPort: false, // Allow fallback to alternative port if occupied
    cors: true,
    fs: {
      // Allow serving files outside root - needed for symlinked development setup
      // NOTE: This only affects dev server, NOT production builds
      strict: false,
      allow: ['..']
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        additionalData: `@use "@/styles/variables.scss" as *;`
      }
    }
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./tests/setup.js'],
    deps: {
      inline: ['vuetify']
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        '*.config.js',
        'dist/'
      ]
    }
  }
})
