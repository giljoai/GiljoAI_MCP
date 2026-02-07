#!/usr/bin/env python3
"""Patch complete-project-lifecycle.spec.ts to use auth bypass"""

import re


# Read the original file
with open("complete-project-lifecycle.spec.ts") as f:
    content = f.read()

# Add import statement after the helpers import
import_pattern = r"(} from './helpers')"
import_replacement = r"\1\nimport { setAuthTokenDirectly, navigateToProjectAuthenticated } from './auth-bypass'"
content = re.sub(import_pattern, import_replacement, content, count=1)

# Add cachedAuthToken variable
describe_pattern = r"(test\.describe\('Complete Project Lifecycle E2E', \(\) => \{[\s\S]*?let projectId: string)"
describe_replacement = r"\1\n  let cachedAuthToken: string | null = null"
content = re.sub(describe_pattern, describe_replacement, content, count=1)

# Replace beforeEach with beforeAll + new beforeEach
before_each_pattern = r"test\.beforeEach\(async \(\{ page \}\) => \{.*?await page\.waitForTimeout\(1000\)[\s]*\}\)"
before_each_replacement = """// Cache auth token across all tests for performance
  test.beforeAll(async ({ request }) => {
    console.log('[beforeAll] Fetching JWT token for all tests...')
    const response = await request.post('http://localhost:7272/api/auth/login', {
      data: {
        username: 'patrik',
        password: '***REMOVED***'
      }
    })

    if (!response.ok()) {
      throw new Error(`Failed to get cached JWT token: ${response.status()}`)
    }

    const headers = response.headers()
    const setCookieHeader = headers['set-cookie']
    const tokenMatch = setCookieHeader?.match(/access_token=([^;]+)/)

    if (!tokenMatch) {
      throw new Error('No access_token found in login response during beforeAll')
    }

    cachedAuthToken = tokenMatch[1]
    console.log('[beforeAll] JWT token cached successfully for all tests')
  })

  test.beforeEach(async ({ page }) => {
    // CRITICAL: Use auth bypass instead of login flow
    // This eliminates redirect issues and speeds up tests
    if (!cachedAuthToken) {
      throw new Error('No cached auth token - beforeAll failed')
    }

    // Set auth cookie directly (bypasses login flow)
    await setAuthTokenDirectly(page, cachedAuthToken)

    // Create test project via API
    projectId = await createTestProject(page, {
      name: 'Complete Lifecycle Test Project',
      description: 'Build a simple REST API with user authentication',
    })
    resourceIds.projectIds.push(projectId)

    // Navigate directly to project (no redirect!)
    await navigateToProjectAuthenticated(page, projectId, 'launch')
  })"""

content = re.sub(before_each_pattern, before_each_replacement, content, flags=re.DOTALL, count=1)

# Write the updated content
with open("complete-project-lifecycle.spec.ts", "w") as f:
    f.write(content)

print("Patched complete-project-lifecycle.spec.ts with auth bypass")
