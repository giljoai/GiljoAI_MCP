/**
 * Test suite for DatabaseStep component (Setup Wizard)
 * TDD approach: Tests written BEFORE implementation modifications
 *
 * Tests database creation flow for the setup wizard:
 * 1. Database creation API call
 * 2. Success handling and UI feedback
 * 3. Error handling and retry logic
 * 4. Form validation
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import DatabaseStep from '@/components/setup/DatabaseStep.vue'

describe('DatabaseStep Component', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    vuetify = createVuetify({
      components,
      directives,
    })

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
    }
    vi.clearAllMocks()
    vi.resetAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render without errors', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('should display database configuration form initially', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      // Form should be visible
      const form = wrapper.find('form')
      expect(form.exists()).toBe(true)
    })

    it('should display info banner explaining database setup', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
      expect(alert.text()).toContain('PostgreSQL database')
    })

    it('should render all required database configuration fields', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      // Check for PostgreSQL host
      const hostField = wrapper.findAll('input').find(input =>
        input.element.value === 'localhost'
      )
      expect(hostField).toBeDefined()

      // Check that form has multiple text fields
      const textFields = wrapper.findAll('.v-text-field')
      expect(textFields.length).toBeGreaterThan(3)
    })

    it('should display progress indicator showing step 2 of 7', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const progressText = wrapper.text()
      expect(progressText).toContain('Step 2 of 7')
      expect(progressText).toContain('29%')
    })
  })

  describe('Form Validation', () => {
    it('should require PostgreSQL host', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      // Clear the host field
      wrapper.vm.dbConfig.pg_host = ''
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formValid).toBe(false)
    })

    it('should require PostgreSQL port', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      // Clear the port
      wrapper.vm.dbConfig.pg_port = null
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formValid).toBe(false)
    })

    it('should validate port is within valid range', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      // Test invalid port
      wrapper.vm.dbConfig.pg_port = 99999
      await wrapper.vm.$nextTick()

      const portValidation = wrapper.vm.rules.port(99999)
      expect(portValidation).toBe('Invalid port number')
    })

    it('should require admin username', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_user = ''
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formValid).toBe(false)
    })

    it('should require admin password', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = ''
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formValid).toBe(false)
    })
  })

  describe('Test Connection Feature', () => {
    it('should have test connection button', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const testButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Test Connection')
      )
      expect(testButton).toBeDefined()
    })

    it('should call test-database API endpoint when testing connection', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, message: 'Connected' })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.testConnection()

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/setup/test-database'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      )
    })

    it('should show success message when connection test succeeds', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, message: 'Successfully connected to PostgreSQL!' })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.testConnection()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.testResult).toEqual({
        success: true,
        message: 'Successfully connected to PostgreSQL!'
      })
    })

    it('should show error message when connection test fails', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ detail: 'Connection refused' })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.testConnection()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.testResult.success).toBe(false)
      expect(wrapper.vm.testResult.message).toContain('Connection')
    })
  })

  describe('Database Creation Flow', () => {
    it('should call create-database API endpoint when creating database', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/setup/create-database'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.any(String)
        })
      )
    })

    it('should send all database configuration to API', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      wrapper.vm.dbConfig.db_name = 'custom_db'
      await wrapper.vm.createDatabase()

      const callArgs = global.fetch.mock.calls[0]
      const requestBody = JSON.parse(callArgs[1].body)

      expect(requestBody).toEqual(expect.objectContaining({
        pg_host: 'localhost',
        pg_port: 5432,
        pg_admin_user: 'postgres',
        pg_admin_password: 'test123',
        db_name: 'custom_db'
      }))
    })

    it('should show loading state during database creation', async () => {
      global.fetch = vi.fn(() =>
        new Promise(resolve =>
          setTimeout(() =>
            resolve({
              ok: true,
              json: () => Promise.resolve({ success: true, database: 'giljo_mcp' })
            }),
            100
          )
        )
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      const createPromise = wrapper.vm.createDatabase()

      // Should be creating
      expect(wrapper.vm.creating).toBe(true)

      await createPromise
      await wrapper.vm.$nextTick()

      // Should finish creating
      expect(wrapper.vm.creating).toBe(false)
    })

    it('should display progress message during creation', async () => {
      global.fetch = vi.fn(() =>
        new Promise(resolve =>
          setTimeout(() =>
            resolve({
              ok: true,
              json: () => Promise.resolve({ success: true, database: 'giljo_mcp' })
            }),
            50
          )
        )
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      const createPromise = wrapper.vm.createDatabase()

      await wrapper.vm.$nextTick()

      // Check for loading indicator
      const loadingText = wrapper.text()
      expect(loadingText).toContain('Creating database')

      await createPromise
    })

    it('should mark database as created on successful creation', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
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
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.dbCreated).toBe(true)
      expect(wrapper.vm.dbResult).toEqual(expect.objectContaining({
        database: 'giljo_mcp',
        owner_user: 'giljo_owner',
        app_user: 'giljo_user'
      }))
    })

    it('should display success alert with database details after creation', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user',
            credentials_file: 'db_credentials_20231001_120000.txt'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const successAlert = wrapper.text()
      expect(successAlert).toContain('Database Created Successfully')
      expect(successAlert).toContain('giljo_mcp')
      expect(successAlert).toContain('giljo_owner')
      expect(successAlert).toContain('giljo_user')
    })

    it('should store credentials in localStorage after successful creation', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
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
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      expect(global.localStorage.setItem).toHaveBeenCalledWith(
        'db_setup',
        expect.stringContaining('generated_pass1')
      )
    })
  })

  describe('Error Handling', () => {
    it('should display error message when creation fails', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          json: () => Promise.resolve({
            detail: 'Database already exists'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.error).toBe('Database already exists')
    })

    it('should show error alert with troubleshooting tips on failure', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          json: () => Promise.resolve({
            detail: 'Connection refused'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const errorText = wrapper.text()
      expect(errorText).toContain('Connection refused')
      expect(errorText).toContain('Troubleshooting')
      expect(errorText).toContain('PostgreSQL 18')
    })

    it('should handle network errors gracefully', async () => {
      global.fetch = vi.fn(() =>
        Promise.reject(new Error('Network error'))
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.error).toContain('Network error')
    })

    it('should provide retry button after error', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ detail: 'Error' })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const retryButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Try Again')
      )
      expect(retryButton).toBeDefined()
    })

    it('should reset state when retry button is clicked', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ detail: 'Error' })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      // Error should be set
      expect(wrapper.vm.error).toBeTruthy()

      // Reset
      wrapper.vm.resetForm()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.error).toBeNull()
      expect(wrapper.vm.dbCreated).toBe(false)
    })
  })

  describe('Navigation', () => {
    it('should emit "back" event when back button is clicked', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const backButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Back')
      )

      await backButton.trigger('click')

      expect(wrapper.emitted('back')).toBeTruthy()
    })

    it('should show "Create Database" button when database not created', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const createButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Create Database')
      )

      expect(createButton).toBeDefined()
    })

    it('should show "Continue" button when database is created', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const continueButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Continue')
      )

      expect(continueButton).toBeDefined()
    })

    it('should emit "next" event when continue button is clicked', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      // Set database as created
      wrapper.vm.dbCreated = true
      wrapper.vm.dbResult = { database: 'giljo_mcp' }
      await wrapper.vm.$nextTick()

      const continueButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Continue')
      )

      await continueButton.trigger('click')

      expect(wrapper.emitted('next')).toBeTruthy()
    })

    it('should disable back button during creation', async () => {
      global.fetch = vi.fn(() =>
        new Promise(resolve =>
          setTimeout(() =>
            resolve({
              ok: true,
              json: () => Promise.resolve({ success: true, database: 'giljo_mcp' })
            }),
            100
          )
        )
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      const createPromise = wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const backButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Back')
      )

      expect(backButton.attributes('disabled')).toBeDefined()

      await createPromise
    })

    it('should disable create button during creation', async () => {
      global.fetch = vi.fn(() =>
        new Promise(resolve =>
          setTimeout(() =>
            resolve({
              ok: true,
              json: () => Promise.resolve({ success: true, database: 'giljo_mcp' })
            }),
            100
          )
        )
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      const createPromise = wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const createButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Create Database')
      )

      expect(createButton.attributes('disabled')).toBeDefined()

      await createPromise
    })
  })

  describe('Advanced Options', () => {
    it('should have expansion panel for advanced options', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const expansionPanel = wrapper.find('.v-expansion-panel')
      expect(expansionPanel.exists()).toBe(true)
      expect(wrapper.text()).toContain('Advanced Options')
    })

    it('should allow customizing database name in advanced options', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.db_name = 'custom_database'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.dbConfig.db_name).toBe('custom_database')
    })

    it('should allow customizing owner username in advanced options', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.db_owner_user = 'custom_owner'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.dbConfig.db_owner_user).toBe('custom_owner')
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

      // Wait for onMounted to complete
      await new Promise(resolve => setTimeout(resolve, 10))

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

      // Wait for onMounted to complete
      await new Promise(resolve => setTimeout(resolve, 10))
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.dbCreated).toBe(true)
    })
  })

  describe('Password Visibility Toggle', () => {
    it('should mask password by default', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      expect(wrapper.vm.showPassword).toBe(false)
    })

    it('should toggle password visibility when eye icon is clicked', async () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const initialState = wrapper.vm.showPassword

      // Toggle password visibility
      wrapper.vm.showPassword = !wrapper.vm.showPassword
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showPassword).toBe(!initialState)
    })
  })

  describe('Accessibility', () => {
    it('should have aria-live region for success message', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            database: 'giljo_mcp',
            owner_user: 'giljo_owner',
            app_user: 'giljo_user'
          })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const successAlert = wrapper.findAll('.v-alert').find(alert =>
        alert.text().includes('Successfully')
      )

      expect(successAlert.attributes('aria-live')).toBe('polite')
    })

    it('should have aria-live region for error message', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ detail: 'Error' })
        })
      )

      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      wrapper.vm.dbConfig.pg_admin_password = 'test123'
      await wrapper.vm.createDatabase()
      await wrapper.vm.$nextTick()

      const errorAlert = wrapper.findAll('.v-alert').find(alert =>
        alert.html().includes('error')
      )

      expect(errorAlert.attributes('aria-live')).toBe('polite')
    })

    it('should have aria-labels on navigation buttons', () => {
      wrapper = mount(DatabaseStep, {
        global: {
          plugins: [vuetify]
        }
      })

      const backButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Back')
      )

      expect(backButton.attributes('aria-label')).toBe('Go back to welcome')
    })
  })
})
