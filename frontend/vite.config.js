import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'path'
import cssImportPlugin from './css-import-plugin.js'
import vuetifyCssResolverPlugin from './vite-vuetify-css-resolver.js'

// Load frontend port from environment or use default
const FRONTEND_PORT = parseInt(process.env.VITE_FRONTEND_PORT || process.env.GILJO_FRONTEND_PORT || '7274', 10)

export default defineConfig({
  plugins: [
    vue(),
    cssImportPlugin(),
    vuetifyCssResolverPlugin(),
    vuetify({
      autoImport: true,
      styles: {
        configFile: 'src/styles/settings.scss'
      }
    })
  ],
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
    host: true,
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
        additionalData: `
          @use "@/styles/variables.scss" as *;
          @import "vuetify/lib/styles/main.scss";
        `
      }
    },
    modules: {
      localsConvention: 'camelCaseOnly'
    }
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./vitest.setup.js'],
    deps: {
      inline: [
        'vuetify',
        '@vue/test-utils',
        '@pinia/testing'
      ]
    },
    css: {
      modules: {
        localsConvention: 'camelCase'
      }
    },
    optimizeDeps: {
      include: ['vuetify']
    },
    resolve: {
      conditions: ['default', 'import', 'module']
    },
    // @ts-ignore
    transformers: {
      '.css': './css-transformer.js'
    },
    define: {
      // Ensure test environment ignores specific imports
      'import.meta.env.VITE_CSS_SKIP': true
    },
    ssr: {
      noExternal: ['vuetify']
    },
    // Loader to ignore CSS files
    loader: {
      test: /\.css$/,
      loader: './vitest-loader.js'
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      include: ['src/**/*.{vue,js}'],
      exclude: [
        'node_modules/',
        'tests/',
        '*.config.js',
        'dist/',
        '**/*.spec.js',
        '**/*.css'
      ]
    }
  }
})
