/**
 * Test suite for DatabaseStep component (Setup Wizard)
 * TDD approach: Tests verify database creation implementation
 *
 * Tests database creation flow for the setup wizard:
 * 1. Database creation API integration
 * 2. Success and error handling
 * 3. Form validation
 * 4. UI state management
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
// import DatabaseStep from '@/components/setup/DatabaseStep.vue' // module deleted/moved

describe.skip('DatabaseStep Component - module deleted/moved', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })

    // Mock fetch globally
    global.fetch = vi.fn(() =>
      Promise.reject(new Error('No mock configured'))
    )

    // Mock localStorage
    global.localStorage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    }

    // Mock console methods to suppress expected errors during tests
    global.console.error = vi.fn()
    global.console.log = vi.fn()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    vi.clearAllMocks()
    vi.resetAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render without errors', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()
      expect(wrapper.exists()).toBe(true)
    })

    it('should have initial database configuration with defaults', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.dbConfig.pg_host).toBe('localhost')
      expect(wrapper.vm.dbConfig.pg_port).toBe(5432)
      expect(wrapper.vm.dbConfig.pg_admin_user).toBe('postgres')
      expect(wrapper.vm.dbConfig.db_name).toBe('giljo_mcp')
    })

    it('should not be marked as created initially', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.dbCreated).toBe(false)
      expect(wrapper.vm.creating).toBe(false)
    })
  })

  describe('Database Creation Flow', () => {
    it('should call create-database API endpoint when creating database', async () => {
      global.fetch = vi.fn((url) => {
        // Handle onMount check
        if (url.includes('test-database')) {
          return Promise.reject(new Error('No database'))
        }
        // Handle creation
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user'
          })
        })
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await flushPromises()

      // Should have called create-database
      const createCall = global.fetch.mock.calls.find(call =>
        call[0].includes('/api/setup/create-database')
      )
      expect(createCall).toBeDefined()
      expect(createCall[1].method).toBe('POST')
    })

    it('should send all database configuration to API', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.reject(new Error('No database'))
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'custom_db',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user'
          })
        })
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      wrapper.vm.dbConfig.db_name = 'custom_db'
      await wrapper.vm.createDatabase()
      await flushPromises()

      const createCall = global.fetch.mock.calls.find(call =>
        call[0].includes('/api/setup/create-database')
      )
      const requestBody = JSON.parse(createCall[1].body)

      expect(requestBody.pg_host).toBe('localhost')
      expect(requestBody.pg_port).toBe(5432)
      expect(requestBody.pg_admin_user).toBe('postgres')
      expect(requestBody.pg_admin_password).toBe('test123')
      expect(requestBody.db_name).toBe('custom_db')
    })

    it('should show loading state during database creation', async () => {
      let resolveCreation
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.reject(new Error('No database'))
        }
        return new Promise(resolve => {
          resolveCreation = resolve
        })
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      const createPromise = wrapper.vm.createDatabase()

      // Should be creating
      expect(wrapper.vm.creating).toBe(true)

      // Resolve the promise
      resolveCreation({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          database: 'giljo_mcp'
        })
      })

      await createPromise
      await flushPromises()

      // Should finish creating
      expect(wrapper.vm.creating).toBe(false)
    })

    it('should mark database as created on successful creation', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.reject(new Error('No database'))
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user',
            owner_password: 'generated_pass1',
            app_password: 'generated_pass2'
          })
        })
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await flushPromises()

      expect(wrapper.vm.dbCreated).toBe(true)
      expect(wrapper.vm.dbResult.database).toBe('giljo_mcp')
      expect(wrapper.vm.dbResult.owner_user).toBe('giljo_owner')
      expect(wrapper.vm.dbResult.app_user).toBe('giljo_user')
    })

    it('should store credentials in localStorage after successful creation', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.reject(new Error('No database'))
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user',
            owner_password: 'generated_pass1',
            app_password: 'generated_pass2'
          })
        })
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await flushPromises()

      expect(global.localStorage.setItem).toHaveBeenCalledWith(
        'db_setup',
        expect.stringContaining('generated_pass1')
      )

      const storedData = JSON.parse(global.localStorage.setItem.mock.calls[0][1])
      expect(storedData.database).toBe('giljo_mcp')
      expect(storedData.owner_password).toBe('generated_pass1')
      expect(storedData.app_password).toBe('generated_pass2')
    })
  })

  describe('Error Handling', () => {
    it('should display error message when creation fails', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.reject(new Error('No database'))
        }
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({
            detail: 'Database already exists'
          })
        })
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await flushPromises()

      expect(wrapper.vm.error).toBe('Database already exists')
      expect(wrapper.vm.dbCreated).toBe(false)
    })

    it('should handle network errors gracefully', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.reject(new Error('No database'))
        }
        return Promise.reject(new Error('Network error'))
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await flushPromises()

      expect(wrapper.vm.error).toContain('Network error')
      expect(wrapper.vm.dbCreated).toBe(false)
    })

    it('should reset state when resetForm is called', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Set some error state
      wrapper.vm.error = 'Some error'
      wrapper.vm.dbCreated = true
      wrapper.vm.dbResult = { database: 'test' }
      wrapper.vm.testResult = { success: false }

      // Reset
      wrapper.vm.resetForm()
      await flushPromises()

      expect(wrapper.vm.error).toBeNull()
      expect(wrapper.vm.dbCreated).toBe(false)
      expect(wrapper.vm.dbResult).toBeNull()
      expect(wrapper.vm.testResult).toBeNull()
    })
  })

  describe('Test Connection Feature', () => {
    it('should call test-database API endpoint when testing connection', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              success: true,
              message: 'Connected'
            })
          })
        }
        return Promise.reject(new Error('Unexpected call'))
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.testConnection()
      await flushPromises()

      const testCalls = global.fetch.mock.calls.filter(call =>
        call[0].includes('/api/setup/test-database')
      )
      // At least 2 calls: one on mount, one from testConnection
      expect(testCalls.length).toBeGreaterThanOrEqual(2)
    })

    it('should show success message when connection test succeeds', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              success: true,
              message: 'Successfully connected to PostgreSQL!'
            })
          })
        }
        return Promise.reject(new Error('Unexpected'))
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.testConnection()
      await flushPromises()

      expect(wrapper.vm.testResult.success).toBe(true)
      expect(wrapper.vm.testResult.message).toBe('Successfully connected to PostgreSQL!')
    })

    it('should show error message when connection test fails', async () => {
      global.fetch = vi.fn((url) => {
        if (url.includes('test-database')) {
          return Promise.resolve({
            ok: false,
            json: () => Promise.resolve({
              detail: 'Connection refused'
            })
          })
        }
        return Promise.reject(new Error('Unexpected'))
      })

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.testConnection()
      await flushPromises()

      expect(wrapper.vm.testResult.success).toBe(false)
      expect(wrapper.vm.testResult.message).toContain('Connection')
    })
  })

  describe('Existing Database Detection', () => {
    it('should check if database already exists on mount', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Should have called test-database on mount
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/setup/test-database')
      )
    })

    it('should mark as created if database already exists', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.dbCreated).toBe(true)
      expect(wrapper.vm.dbResult.database).toBe('giljo_mcp')
      expect(wrapper.vm.dbResult.already_existed).toBe(true)
    })

    it('should show form if database does not exist', async () => {
      global.fetch = vi.fn(() =>
        Promise.reject(new Error('Database not found'))
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.dbCreated).toBe(false)
      expect(wrapper.vm.dbResult).toBeNull()
    })
  })

  describe('Form Validation', () => {
    it('should have validation rules for required fields', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Test required rule
      expect(wrapper.vm.rules.required('')).toBe('Required')
      expect(wrapper.vm.rules.required('value')).toBe(true)

      // Test port validation
      expect(wrapper.vm.rules.port(0)).toBe('Invalid port number')
      expect(wrapper.vm.rules.port(99999)).toBe('Invalid port number')
      expect(wrapper.vm.rules.port(5432)).toBe(true)
    })

    it('should not create database if form is invalid', async () => {
      global.fetch = vi.fn(() =>
        Promise.reject(new Error('No database'))
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      // Mock form validation to fail
      wrapper.vm.form = {
        validate: () => false
      }

      await wrapper.vm.createDatabase()

      // Should not have called API
      const createCalls = global.fetch.mock.calls.filter(call =>
        call[0] && call[0].includes('/api/setup/create-database')
      )
      expect(createCalls.length).toBe(0)
    })
  })

  describe('Navigation State', () => {
    it('should emit back event', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.$emit('back')

      expect(wrapper.emitted('back')).toBeTruthy()
    })

    it('should emit next event', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.$emit('next')

      expect(wrapper.emitted('next')).toBeTruthy()
    })
  })

  describe('Password Visibility', () => {
    it('should mask password by default', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      expect(wrapper.vm.showPassword).toBe(false)
    })

    it('should toggle password visibility', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      await flushPromises()

      const initialState = wrapper.vm.showPassword

      wrapper.vm.showPassword = !wrapper.vm.showPassword
      await flushPromises()

      expect(wrapper.vm.showPassword).toBe(!initialState)
    })
  })
})
