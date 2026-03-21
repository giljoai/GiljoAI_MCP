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

// Derive API proxy target from config.yaml
// CRITICAL: For Playwright tests, always use localhost (same machine)
// For production, external_host is used by clients to reach the server
let apiHost = '127.0.0.1'
let apiPort = 7272
let sslEnabled = false
let sslCertPath = null
let sslKeyPath = null
try {
  const configPath = resolve(__dirname, '../config.yaml')
  if (fs.existsSync(configPath)) {
    const configData = yaml.load(fs.readFileSync(configPath, 'utf8'))
    apiPort = parseInt(configData?.server?.api_port || 7272, 10)
    sslEnabled = configData?.features?.ssl_enabled === true
    sslCertPath = configData?.paths?.ssl_cert || null
    sslKeyPath = configData?.paths?.ssl_key || null
    // ALWAYS use localhost for Vite dev proxy (same machine as backend)
    // external_host is for client-to-server connections, not dev proxy
    apiHost = '127.0.0.1'
  }
} catch (err) {
  console.warn('[Vite] Could not determine API proxy target, defaulting to 127.0.0.1:7272:', err.message)
}
const apiProtocol = sslEnabled ? 'https' : 'http'
const API_TARGET = `${apiProtocol}://${apiHost}:${apiPort}`

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
    // Serve HTTPS when SSL is enabled in config.yaml (uses same certs as backend)
    ...(sslEnabled && sslCertPath && sslKeyPath && fs.existsSync(sslCertPath) && fs.existsSync(sslKeyPath) ? {
      https: {
        cert: fs.readFileSync(sslCertPath),
        key: fs.readFileSync(sslKeyPath),
      }
    } : {}),
    proxy: {
      // Proxy API to backend to avoid CORS in development
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        secure: false,
        ws: true,
        // Fix (Post-0128e): Ensure cookies are forwarded for authentication
        // Browser cookies need to reach backend for JWT auth to work over LAN/WAN
        cookieDomainRewrite: '', // Don't rewrite cookie domains
        preserveHeaderKeyCase: true, // Preserve header casing
        configure: (proxy, _options) => {
          // Ensure cookies are forwarded from browser to backend
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            if (req.headers.cookie) {
              proxyReq.setHeader('Cookie', req.headers.cookie)
            }
          })
        },
      },
      // MCP endpoints if used
      '/mcp': {
        target: API_TARGET,
        changeOrigin: true,
        secure: false,
        // Same cookie forwarding for MCP endpoints
        cookieDomainRewrite: '',
        preserveHeaderKeyCase: true,
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            if (req.headers.cookie) {
              proxyReq.setHeader('Cookie', req.headers.cookie)
            }
          })
        },
      },
    },
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
    environment: 'jsdom',
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
