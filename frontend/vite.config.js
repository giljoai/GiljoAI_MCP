import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'path'
import fs from 'fs'
import yaml from 'js-yaml'

// Load frontend port from environment or use default
const FRONTEND_PORT = parseInt(process.env.VITE_FRONTEND_PORT || process.env.GILJO_FRONTEND_PORT || '7274', 10)

// Load selected adapter IP from config.yaml for LAN mode binding
let selectedAdapterIP = null
try {
  const configPath = resolve(__dirname, '../config.yaml')
  if (fs.existsSync(configPath)) {
    const configData = yaml.load(fs.readFileSync(configPath, 'utf8'))
    const mode = configData?.installation?.mode
    if (mode === 'lan' || mode === 'server' || mode === 'wan') {
      selectedAdapterIP = configData?.server?.ip || configData?.security?.network?.initial_ip
      console.log(`[Vite] LAN mode detected - binding to selected adapter IP: ${selectedAdapterIP}`)
    } else {
      console.log(`[Vite] Localhost mode detected - binding to localhost only`)
    }
  }
} catch (err) {
  console.warn('[Vite] Could not read config.yaml, using default host settings:', err.message)
}

// Determine host binding based on mode
// - LAN/Server mode: Bind to selected adapter IP only
// - Localhost mode: Bind to localhost only (not 0.0.0.0)
const HOST = selectedAdapterIP || 'localhost'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        wizard: resolve(__dirname, 'wizard.html')
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
