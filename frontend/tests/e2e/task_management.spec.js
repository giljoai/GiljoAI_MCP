import { test, expect } from '@playwright/test'

test.describe('Task Management User Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Login as developer
    await page.goto('/login')
    await page.fill('#username', 'testuser')
    await page.fill('#password', 'password')
    await page.click('button[type="submit"]')

    // Navigate to Tasks view
    await page.click('[data-test="nav-tasks"]')
  })

  test('Create task with user assignment', async ({ page }) => {
    // Open create task dialog
    await page.click('[data-test="create-task-button"]')

    // Fill task details
    await page.fill('[data-test="task-title-input"]', 'E2E Test Task')
    await page.fill('[data-test="task-description-input"]', 'End-to-end task creation test')

    // Select user from assignment dropdown
    await page.click('[data-test="assign-to-select"]')
    await page.click('[data-test="user-option-1"]')  // Assuming first option

    // Submit task creation
    await page.click('[data-test="submit-task-button"]')

    // Wait for task to appear in list
    await page.waitForSelector('[data-test="task-row-e2e-test-task"]')

    // Verify task details
    const taskRow = await page.locator('[data-test="task-row-e2e-test-task"]')
    await expect(taskRow).toBeVisible()
    await expect(taskRow).toContainText('E2E Test Task')
    await expect(taskRow).toContainText('Assigned to: User 1')
  })

  test('Convert task to project', async ({ page }) => {
    // Create a task first
    await page.click('[data-test="create-task-button"]')
    await page.fill('[data-test="task-title-input"]', 'Convertible Task')
    await page.fill('[data-test="task-description-input"]', 'Task to be converted to project')
    await page.click('[data-test="submit-task-button"]')

    // Find the newly created task
    const taskRow = await page.locator('[data-test="task-row-convertible-task"]')

    // Trigger conversion
    await taskRow.click('[data-test="convert-to-project"]')

    // Verify conversion dialog
    await expect(page.locator('[data-test="conversion-dialog"]')).toBeVisible()

    // Confirm conversion
    await page.click('[data-test="confirm-conversion"]')

    // Check for success notification
    const notification = await page.locator('[data-test="success-notification"]')
    await expect(notification).toBeVisible()
    await expect(notification).toContainText('Task successfully converted to project')

    // Navigate to projects to verify
    await page.click('[data-test="nav-projects"]')
    await expect(page.locator('[data-test="project-row-convertible-task"]')).toBeVisible()
  })

  test('Filter tasks by view type', async ({ page }) => {
    // Verify default "My Tasks" filter is active
    await expect(page.locator('[data-test="my-tasks-chip"]')).toHaveClass('v-chip--active')

    // For admin, test "All Tasks" filter
    await page.evaluate(() => {
      // Simulate admin login/role
      window.$store.user.currentUser.role = 'admin'
    })

    // Refresh page to apply role
    await page.reload()

    // Click "All Tasks" chip
    await page.click('[data-test="all-tasks-chip"]')

    // Verify task list updates
    const taskRows = await page.locator('[data-test="task-row"]')
    await expect(taskRows.count()).toBeGreaterThan(0)
  })

  test('Accessibility navigation', async ({ page }) => {
    // Test keyboard navigation to create task
    await page.keyboard.press('Tab')  // Move to create task button
    await page.keyboard.press('Enter')  // Open create task dialog

    // Verify dialog opened
    await expect(page.locator('[data-test="create-task-dialog"]')).toBeVisible()

    // Tab through task creation form
    await page.keyboard.press('Tab')  // Title input
    await page.keyboard.type('Keyboard Created Task')

    await page.keyboard.press('Tab')  // Description input
    await page.keyboard.type('Created using keyboard navigation')

    // Submit form
    await page.keyboard.press('Enter')

    // Verify task created
    await expect(page.locator('[data-test="task-row-keyboard-created-task"]')).toBeVisible()
  })
})
