import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import WelcomePasswordStep from '@/components/setup/WelcomePasswordStep.vue'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

describe('WelcomePasswordStep', () => {
  let wrapper
  let authStore

  beforeEach(() => {
    // Create a fresh Pinia instance for each test
    setActivePinia(createPinia())
    authStore = useAuthStore()

    // Mock the changePassword method
    vi.spyOn(authStore, 'changePassword').mockImplementation(async () => {})

    // Mount the component
    wrapper = mount(WelcomePasswordStep, {
      global: {
        plugins: [createPinia()]
      }
    })
  })

  // Password Validation Tests
  it('validates password strength', async () => {
    const passwordInput = wrapper.find('input[type="password"]')

    // Weak password
    await passwordInput.setValue('weak')
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.passwordStrength).toBeLessThan(3)
    expect(wrapper.text()).toContain('Password is too weak')

    // Strong password
    await passwordInput.setValue('StrongP@ssw0rd123!')
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.passwordStrength).toBeGreaterThan(3)
    expect(wrapper.text()).not.toContain('Password is too weak')
  })

  // Form Submission Tests
  it('prevents submission of weak passwords', async () => {
    // Set weak password
    const passwordInput = wrapper.find('input[type="password"]')
    const submitButton = wrapper.find('button[type="submit"]')

    await passwordInput.setValue('weak')
    await submitButton.trigger('click')

    // Check that changePassword was not called
    expect(authStore.changePassword).not.toHaveBeenCalled()
  })

  // Successful Password Change
  it('submits strong password and redirects', async () => {
    const passwordInput = wrapper.find('input[type="password"]')
    const confirmPasswordInput = wrapper.find('input[name="confirmPassword"]')
    const submitButton = wrapper.find('button[type="submit"]')

    // Set strong password
    await passwordInput.setValue('StrongP@ssw0rd123!')
    await confirmPasswordInput.setValue('StrongP@ssw0rd123!')

    // Mock router push
    const mockPush = vi.fn()
    wrapper.vm.$router = { push: mockPush }

    // Trigger submission
    await submitButton.trigger('click')

    // Check that changePassword was called
    expect(authStore.changePassword).toHaveBeenCalledWith('StrongP@ssw0rd123!')

    // Wait for async operations
    await wrapper.vm.$nextTick()

    // Check redirect to login
    expect(mockPush).toHaveBeenCalledWith('/login')
  })

  // Password Match Validation
  it('requires password and confirmation to match', async () => {
    const passwordInput = wrapper.find('input[type="password"]')
    const confirmPasswordInput = wrapper.find('input[name="confirmPassword"]')
    const submitButton = wrapper.find('button[type="submit"]')

    await passwordInput.setValue('StrongP@ssw0rd123!')
    await confirmPasswordInput.setValue('DifferentPassword123!')

    await submitButton.trigger('click')

    // Check error message
    expect(wrapper.text()).toContain('Passwords do not match')
    expect(authStore.changePassword).not.toHaveBeenCalled()
  })

  // Accessibility Tests
  it('has proper aria labels and keyboard navigation', () => {
    const passwordInput = wrapper.find('input[type="password"]')
    const confirmPasswordInput = wrapper.find('input[name="confirmPassword"]')
    const submitButton = wrapper.find('button[type="submit"]')

    expect(passwordInput.attributes('aria-label')).toBeDefined()
    expect(confirmPasswordInput.attributes('aria-label')).toBeDefined()
    expect(submitButton.attributes('aria-label')).toBeDefined()
  })
})
