#!/usr/bin/env node

/**
 * Selector Validation Script
 *
 * This script validates that all data-testid selectors exist in the frontend components.
 * It uses a simpler approach by checking the source code directly.
 *
 * Usage: node validate-selectors.js
 */

const fs = require('fs')
const path = require('path')

const RESULTS = {
  pass: [],
  fail: [],
  skip: [],
}

// Define all selectors to validate with their expected locations
const SELECTORS_TO_VALIDATE = [
  // LaunchTab.vue
  {
    selector: 'agent-type',
    component: 'LaunchTab.vue',
    path: 'src/components/projects/LaunchTab.vue',
    type: 'hidden span',
    status: 'expected',
  },
  {
    selector: 'status-chip',
    component: 'LaunchTab.vue',
    path: 'src/components/projects/LaunchTab.vue',
    type: 'hidden span',
    status: 'expected',
  },
  {
    selector: 'agent-card',
    component: 'LaunchTab.vue',
    path: 'src/components/projects/LaunchTab.vue',
    type: 'element',
    status: 'expected',
  },

  // CloseoutModal.vue
  {
    selector: 'submit-closeout-btn',
    component: 'CloseoutModal.vue',
    path: 'src/components/orchestration/CloseoutModal.vue',
    type: 'button',
    status: 'expected',
  },
  {
    selector: 'closeout-modal',
    component: 'CloseoutModal.vue',
    path: 'src/components/orchestration/CloseoutModal.vue',
    type: 'dialog',
    status: 'expected',
  },

  // MessageItem.vue
  {
    selector: 'message-item',
    component: 'MessageItem.vue',
    path: 'src/components/messages/MessageItem.vue',
    type: 'card',
    status: 'expected',
  },
  {
    selector: 'message-from',
    component: 'MessageItem.vue',
    path: 'src/components/messages/MessageItem.vue',
    type: 'span',
    status: 'expected',
  },
  {
    selector: 'message-to',
    component: 'MessageItem.vue',
    path: 'src/components/messages/MessageItem.vue',
    type: 'div',
    status: 'expected',
  },
  {
    selector: 'message-content',
    component: 'MessageItem.vue',
    path: 'src/components/messages/MessageItem.vue',
    type: 'div',
    status: 'expected',
  },

  // UserSettings.vue
  {
    selector: 'context-settings-tab',
    component: 'UserSettings.vue',
    path: 'src/views/UserSettings.vue',
    type: 'tab',
    status: 'expected',
  },
  {
    selector: 'agent-templates-settings-tab',
    component: 'UserSettings.vue',
    path: 'src/views/UserSettings.vue',
    type: 'tab',
    status: 'expected',
  },
  {
    selector: 'integrations-settings-tab',
    component: 'UserSettings.vue',
    path: 'src/views/UserSettings.vue',
    type: 'tab',
    status: 'expected',
  },

  // ContextPriorityConfig.vue - Dynamic selectors
  {
    selector: 'depth-* (dynamic)',
    component: 'ContextPriorityConfig.vue',
    path: 'src/components/settings/ContextPriorityConfig.vue',
    type: 'select (depth)',
    status: 'dynamic',
    pattern: ':data-testid="`depth-',
  },

  // GitIntegrationCard.vue
  {
    selector: 'github-integration-toggle',
    component: 'GitIntegrationCard.vue',
    path: 'src/components/settings/integrations/GitIntegrationCard.vue',
    type: 'switch',
    status: 'expected',
  },

  // TemplateManager.vue - Dynamic selectors
  {
    selector: 'template-toggle-* (dynamic)',
    component: 'TemplateManager.vue',
    path: 'src/components/TemplateManager.vue',
    type: 'switch (template)',
    status: 'dynamic',
    pattern: ':data-testid="`template-toggle-',
  },

  // ProjectsView.vue
  {
    selector: 'project-status',
    component: 'ProjectsView.vue',
    path: 'src/views/ProjectsView.vue',
    type: 'text',
    status: 'expected',
  },
]

function validateSelector(selectorConfig) {
  const filePath = path.join(__dirname, selectorConfig.path)

  // Check if file exists
  if (!fs.existsSync(filePath)) {
    return {
      status: 'FAIL',
      reason: `File not found: ${filePath}`,
    }
  }

  // Read file content
  let content
  try {
    content = fs.readFileSync(filePath, 'utf8')
  } catch (error) {
    return {
      status: 'FAIL',
      reason: `Error reading file: ${error.message}`,
    }
  }

  // Check for selector
  const testidAttribute = `data-testid="${selectorConfig.selector}"`
  const dynamicTestidPattern = selectorConfig.pattern
    ? new RegExp(selectorConfig.pattern)
    : null

  let found = false

  if (selectorConfig.status === 'dynamic' && dynamicTestidPattern) {
    // For dynamic selectors, check for the pattern
    found = dynamicTestidPattern.test(content)
  } else {
    // For static selectors, check for exact match
    found = content.includes(testidAttribute)
  }

  if (found) {
    return {
      status: 'PASS',
      reason: `Selector "${selectorConfig.selector}" found in ${selectorConfig.component}`,
    }
  } else {
    return {
      status: 'FAIL',
      reason: `Selector "${selectorConfig.selector}" NOT found in ${selectorConfig.component}`,
    }
  }
}

function main() {
  console.log('================================================================================')
  console.log('DATA-TESTID SELECTOR VALIDATION REPORT')
  console.log('================================================================================\n')

  let passCount = 0
  let failCount = 0
  let skipCount = 0

  // Validate each selector
  SELECTORS_TO_VALIDATE.forEach((selectorConfig) => {
    const result = validateSelector(selectorConfig)

    const icon = result.status === 'PASS' ? '✓' : '❌'
    console.log(`${icon} ${result.status.padEnd(6)} | ${selectorConfig.selector.padEnd(40)} | ${selectorConfig.component}`)
    console.log(`  └─ ${result.reason}\n`)

    if (result.status === 'PASS') {
      passCount++
      RESULTS.pass.push(selectorConfig.selector)
    } else if (result.status === 'SKIP') {
      skipCount++
      RESULTS.skip.push(selectorConfig.selector)
    } else {
      failCount++
      RESULTS.fail.push(selectorConfig.selector)
    }
  })

  // Print summary
  console.log('================================================================================')
  console.log('SUMMARY')
  console.log('================================================================================')
  console.log(`✓ PASS:  ${passCount} selectors`)
  console.log(`❌ FAIL:  ${failCount} selectors`)
  console.log(`⚠ SKIP:  ${skipCount} selectors`)
  console.log(`TOTAL:   ${SELECTORS_TO_VALIDATE.length} selectors\n`)

  if (failCount > 0) {
    console.log('FAILED SELECTORS:')
    RESULTS.fail.forEach((selector) => {
      console.log(`  - ${selector}`)
    })
    console.log()
  }

  // Exit with appropriate code
  process.exit(failCount > 0 ? 1 : 0)
}

main()
