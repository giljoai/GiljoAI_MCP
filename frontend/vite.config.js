import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Load frontend port from environment or use default
const FRONTEND_PORT = parseInt(process.env.VITE_FRONTEND_PORT || process.env.GILJO_FRONTEND_PORT || '7274', 10)

export default defineConfig({
  plugins: [vue()],
  server: {
    port: FRONTEND_PORT,
    host: true,
    strictPort: false, // Allow fallback to alternative port if occupied
    cors: true
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`
      }
    }
  }
})
