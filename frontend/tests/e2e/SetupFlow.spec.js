describe('GiljoAI MCP Setup Flow', () => {
  beforeEach(() => {
    // Reset application state or simulate fresh installation
    cy.resetApp()
  })

  it('completes full setup flow from welcome to dashboard', () => {
    // 1. Initial Welcome Screen
    cy.visit('/welcome')

    // Verify welcome page elements
    cy.contains('Welcome to GiljoAI MCP')
    cy.get('input[name="password"]').should('be.visible')

    // 2. Set Initial Password
    cy.get('input[name="password"]').type('StrongP@ssw0rd123!')
    cy.get('input[name="confirmPassword"]').type('StrongP@ssw0rd123!')
    cy.get('button[type="submit"]').click()

    // 3. Login Page
    cy.url().should('include', '/login')
    cy.get('input[name="username"]').type('admin')
    cy.get('input[name="password"]').type('StrongP@ssw0rd123!')
    cy.get('button[type="submit"]').click()

    // 4. Setup Wizard
    cy.url().should('include', '/setup')

    // Verify MCP Step
    cy.contains('MCP Configuration')
    cy.get('input[name="mcpSettings"]').type('Default MCP Config')
    cy.get('button[data-testid="next-mcp"]').click()

    // Verify Serena Step
    cy.contains('Serena Configuration')
    cy.get('input[name="serenaSettings"]').type('Default Serena Config')
    cy.get('button[data-testid="next-serena"]').click()

    // Verify Final Step
    cy.contains('Setup Complete')
    cy.get('button[data-testid="finish-setup"]').click()

    // 5. Dashboard
    cy.url().should('include', '/dashboard')
    cy.contains('Welcome to GiljoAI MCP Dashboard')

    // Verify Connection Status
    cy.get('[data-testid="connection-status"]')
      .should('be.visible')
      .and('contain', 'Connected')
  })

  it('validates password requirements during initial setup', () => {
    cy.visit('/welcome')

    // Weak password test
    cy.get('input[name="password"]').type('weak')
    cy.get('input[name="confirmPassword"]').type('weak')
    cy.get('button[type="submit"]').click()

    // Verify error message for weak password
    cy.contains('Password is too weak')

    // Mismatched passwords test
    cy.get('input[name="password"]').type('StrongP@ssw0rd123!')
    cy.get('input[name="confirmPassword"]').type('DifferentPassword123!')
    cy.get('button[type="submit"]').click()

    // Verify error message for password mismatch
    cy.contains('Passwords do not match')
  })

  it('handles network errors during setup', () => {
    // Simulate network failure
    cy.intercept('POST', '/api/auth/change-password', {
      statusCode: 500,
      body: { error: 'Network error' }
    })

    cy.visit('/welcome')

    cy.get('input[name="password"]').type('StrongP@ssw0rd123!')
    cy.get('input[name="confirmPassword"]').type('StrongP@ssw0rd123!')
    cy.get('button[type="submit"]').click()

    // Verify error handling
    cy.contains('Unable to complete setup')
    cy.get('[data-testid="error-message"]').should('be.visible')
  })

  it('tests mobile responsiveness of setup flow', () => {
    // Set mobile viewport
    cy.viewport('iphone-x')

    cy.visit('/welcome')

    // Verify mobile-specific layout
    cy.get('[data-testid="mobile-welcome"]').should('be.visible')

    // Complete setup flow (same as main test, but verifying mobile layout)
    cy.get('input[name="password"]').type('StrongP@ssw0rd123!')
    cy.get('input[name="confirmPassword"]').type('StrongP@ssw0rd123!')
    cy.get('button[type="submit"]').click()

    // Verify mobile responsiveness throughout flow
    cy.url().should('include', '/login')
    cy.get('[data-testid="mobile-login"]').should('be.visible')
  })
})