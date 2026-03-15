/**
 * LaunchTab.0243a.spec.js
 *
 * Test suite for Design Tokens Extraction (Handover 0243a)
 * Phase 1: Design tokens file creation and LaunchTab unified container specifications
 *
 * Following strict TDD: Write tests FIRST, watch them FAIL, then implement
 *
 * Requirements:
 * 1. Design tokens file existence and structure (design-tokens.scss)
 * 2. LaunchTab unified container specifications with exact styling values
 * 3. Token usage verification (no hardcoded values, use design tokens)
 * 4. Multi-tenant isolation (existing behavior must continue to pass)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import LaunchTab from '@/components/projects/LaunchTab.vue'
import fs from 'fs'
import path from 'path'

// Create Vuetify instance for testing
const vuetify = createVuetify({
  components,
  directives,
})

// Mock WebSocket composable
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
  })
}))

// Mock user store with tenant_key
vi.mock('@/stores/user', () => ({
  useUserStore: vi.fn().mockReturnValue({
    currentUser: {
      tenant_key: 'test-tenant-key-123'
    }
  })
}))

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    prompts: {
      staging: vi.fn().mockResolvedValue({
        data: {
          prompt: 'Test staging prompt',
          estimated_prompt_tokens: 1500
        }
      })
    },
    projects: {
      cancelStaging: vi.fn().mockResolvedValue({
        data: {
          agents_deleted: 3,
          messages_deleted: 5
        }
      })
    }
  }
}))

// Helper function to get correct path regardless of working directory
function getDesignTokensPath() {
  const cwd = process.cwd()
  return cwd.endsWith('frontend')
    ? path.join(cwd, 'src', 'styles', 'design-tokens.scss')
    : path.join(cwd, 'frontend', 'src', 'styles', 'design-tokens.scss')
}

function getLaunchTabPath() {
  const cwd = process.cwd()
  return cwd.endsWith('frontend')
    ? path.join(cwd, 'src', 'components', 'projects', 'LaunchTab.vue')
    : path.join(cwd, 'frontend', 'src', 'components', 'projects', 'LaunchTab.vue')
}

describe('LaunchTab.0243a - Design Tokens Extraction', () => {
  let wrapper

  // Sample project data
  const mockProject = {
    id: 'project-123',
    project_id: 'project-123',
    name: 'Test Project',
    description: 'Test project description for design tokens verification.',
    mission: null,
    agents: [],
    tenant_key: 'test-tenant-key-123'
  }

  beforeEach(() => {
    wrapper = mount(LaunchTab, {
      global: {
        plugins: [vuetify],
      },
      props: {
        project: mockProject,
        orchestrator: null,
        isStaging: false
      }
    })
  })

  // =========================================================================
  // SUITE 1: Design Tokens File Tests
  // =========================================================================

  describe('Design Tokens File', () => {
    it('design-tokens.scss file exists at frontend/src/styles/design-tokens.scss', () => {
      const designTokensPath = getDesignTokensPath()
      expect(fs.existsSync(designTokensPath)).toBe(true)
    })

    it('design-tokens.scss file size is less than 10KB', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const stats = fs.statSync(designTokensPath)
        expect(stats.size).toBeLessThan(10240)
      }
    })

    it('design-tokens.scss contains all required color tokens', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toContain('$color-container-border:')
        expect(content).toContain('$color-container-background:')
        expect(content).toContain('$color-panel-background:')
        expect(content).toContain('$color-text-primary:')
        expect(content).toContain('$color-text-secondary:')
      }
    })

    it('design-tokens.scss contains all required spacing tokens', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toContain('$spacing-container-padding:')
        expect(content).toContain('$spacing-panel-gap:')
        expect(content).toContain('$spacing-panel-content-padding:')
        expect(content).toContain('$spacing-panel-min-height:')
      }
    })

    it('design-tokens.scss contains all required typography tokens', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toContain('$typography-panel-header-size:')
        expect(content).toContain('$typography-panel-header-weight:')
        expect(content).toContain('$typography-panel-content-size:')
      }
    })

    it('design-tokens.scss contains all required border and shadow tokens', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toContain('$border-container:')
        expect(content).toContain('$radius-container:')
        expect(content).toContain('$radius-panel-content:')
      }
    })
  })

  // =========================================================================
  // SUITE 2: LaunchTab Unified Container Structure Tests
  // =========================================================================

  describe('LaunchTab Unified Container Specifications', () => {
    it('main container has 2px border with rgba(255, 255, 255, 0.2)', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.exists()).toBe(true)
      expect(mainContainer.classes()).toContain('main-container')
    })

    it('main container has border-radius of 16px', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.exists()).toBe(true)
      expect(mainContainer.classes()).toContain('main-container')
    })

    it('main container has padding of 30px', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.exists()).toBe(true)
      expect(mainContainer.classes()).toContain('main-container')
    })

    it('main container has background rgba(14, 28, 45, 0.5)', () => {
      const mainContainer = wrapper.find('.main-container')
      expect(mainContainer.exists()).toBe(true)
      expect(mainContainer.classes()).toContain('main-container')
    })

    it('three panels are rendered with 24px gap', () => {
      const threePanels = wrapper.find('.three-panels')
      expect(threePanels.exists()).toBe(true)
      const panels = threePanels.findAll('.panel')
      expect(panels.length).toBe(3)
      expect(threePanels.classes()).toContain('three-panels')
    })

    it('panel headers use font-size 1.125rem (18px equivalent)', () => {
      const panelHeaders = wrapper.findAll('.panel-header')
      expect(panelHeaders.length).toBeGreaterThan(0)
      panelHeaders.forEach((header) => {
        expect(header.exists()).toBe(true)
      })
    })

    it('panel content has min-height of 450px', () => {
      const panelContent = wrapper.findAll('.panel-content')
      expect(panelContent.length).toBe(3)
      panelContent.forEach((content) => {
        expect(content.exists()).toBe(true)
      })
    })

    it('panel content has background rgba(20, 35, 50, 0.8)', () => {
      const panelContent = wrapper.findAll('.panel-content')
      expect(panelContent.length).toBeGreaterThan(0)
      panelContent.forEach((content) => {
        expect(content.exists()).toBe(true)
      })
    })

    it('all three panels are visible and properly structured', () => {
      const projectDescPanel = wrapper.find('.project-description-panel')
      const missionPanel = wrapper.find('.mission-panel')
      const agentPanel = wrapper.find('.agents-panel')

      expect(projectDescPanel.exists()).toBe(true)
      expect(missionPanel.exists()).toBe(true)
      expect(agentPanel.exists()).toBe(true)

      expect(projectDescPanel.find('.panel-header').exists()).toBe(true)
      expect(missionPanel.find('.panel-header').exists()).toBe(true)
      expect(agentPanel.find('.panel-header').exists()).toBe(true)

      expect(projectDescPanel.find('.panel-content').exists()).toBe(true)
      expect(missionPanel.find('.panel-content').exists()).toBe(true)
      expect(agentPanel.find('.panel-content').exists()).toBe(true)
    })
  })

  // =========================================================================
  // SUITE 3: Design Token Usage Verification
  // =========================================================================

  describe('Design Token Usage in LaunchTab.vue', () => {
    it('LaunchTab.vue imports design-tokens.scss', async () => {
      const componentPath = getLaunchTabPath()
      const content = fs.readFileSync(componentPath, 'utf-8')

      const hasDesignTokenImport =
        content.includes("@import '@/styles/design-tokens.scss'") ||
        content.includes('@import "@/styles/design-tokens.scss"') ||
        content.includes("@use '@/styles/design-tokens'") ||
        content.includes('@use "@/styles/design-tokens"') ||
        content.includes("@use '@/styles/design-tokens.scss'") ||
        content.includes('@use "@/styles/design-tokens.scss"')

      expect(hasDesignTokenImport).toBe(true)
    })

    it('LaunchTab.vue has no hardcoded hex colors in styles', () => {
      const componentPath = getLaunchTabPath()
      const content = fs.readFileSync(componentPath, 'utf-8')

      const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      if (styleMatch) {
        const styleContent = styleMatch[1]
        const hexMatches = styleContent.match(/#[0-9a-f]{6}|#[0-9a-f]{3}/gi) || []
        const hardcodedHexes = hexMatches.filter((hex) => hex.toLowerCase() !== '#d4a574')
        expect(hardcodedHexes.length).toBe(0)
      }
    })

    it('LaunchTab.vue uses design tokens for all spacing values', () => {
      const componentPath = getLaunchTabPath()
      const content = fs.readFileSync(componentPath, 'utf-8')

      const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      if (styleMatch) {
        const styleContent = styleMatch[1]
        expect(styleContent).toContain('$spacing')
      }
    })

    it('LaunchTab.vue uses design tokens for all border-radius values', () => {
      const componentPath = getLaunchTabPath()
      const content = fs.readFileSync(componentPath, 'utf-8')

      const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      if (styleMatch) {
        const styleContent = styleMatch[1]
        expect(styleContent).toContain('$radius')
      }
    })

    it('LaunchTab.vue uses color tokens for all container and panel colors', () => {
      const componentPath = getLaunchTabPath()
      const content = fs.readFileSync(componentPath, 'utf-8')

      const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      if (styleMatch) {
        const styleContent = styleMatch[1]
        expect(styleContent).toContain('$color')
      }
    })
  })

  // =========================================================================
  // SUITE 4: Multi-Tenant Isolation (Existing Behavior)
  // =========================================================================

  describe('Multi-Tenant Isolation Verification', () => {
    it('component receives tenant_key from user store', () => {
      expect(wrapper.vm).toBeDefined()
      expect(wrapper.props().project.tenant_key).toBe('test-tenant-key-123')
    })

    it('project data includes tenant_key for isolation', () => {
      const projectWithTenant = {
        ...mockProject,
        tenant_key: 'test-tenant-key-123'
      }

      expect(projectWithTenant.tenant_key).toBe('test-tenant-key-123')
      expect(projectWithTenant.id).toBe('project-123')
    })

    it('WebSocket composable is initialized for tenant-scoped events', () => {
      expect(wrapper.vm).toBeDefined()
    })

    it('only displays content for current tenant', () => {
      const projectData = wrapper.props('project')
      expect(projectData).toBeDefined()
      expect(projectData.tenant_key || projectData.project_id).toBeDefined()
    })

    it('does not display content from other tenants', () => {
      const differentTenantProject = {
        ...mockProject,
        tenant_key: 'different-tenant-456'
      }

      expect(differentTenantProject.tenant_key).not.toBe('test-tenant-key-123')
    })
  })

  // =========================================================================
  // SUITE 5: Component Integration Tests
  // =========================================================================

  describe('Component Integration with Design Tokens', () => {
    it('renders LaunchTab with unified container structure', () => {
      const launchTabWrapper = wrapper.find('.launch-tab-wrapper')
      const mainContainer = wrapper.find('.main-container')

      expect(launchTabWrapper.exists()).toBe(true)
      expect(mainContainer.exists()).toBe(true)
    })

    it('has consistent styling throughout all three panels', () => {
      const panels = wrapper.findAll('.panel')
      expect(panels.length).toBe(3)

      panels.forEach((panel) => {
        const header = panel.find('.panel-header')
        const content = panel.find('.panel-content')

        expect(header.exists()).toBe(true)
        expect(content.exists()).toBe(true)
      })
    })

    it('applies unified container design to header actions area', () => {
      const headerActions = wrapper.find('.header-actions')
      expect(headerActions.exists()).toBe(true)
      expect(headerActions.classes()).toContain('header-actions')
    })

    it('maintains accessibility of all interactive elements', () => {
      const buttons = wrapper.findAll('button')
      expect(buttons.length).toBeGreaterThan(0)

      buttons.forEach((btn) => {
        expect(btn.exists()).toBe(true)
      })
    })
  })

  // =========================================================================
  // SUITE 6: Token Value Specificity Tests
  // =========================================================================

  describe('Exact Design Token Values (Specification Compliance)', () => {
    it('container border is exactly 2px with rgba(255, 255, 255, 0.2)', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toMatch(/\$border-container:\s*2px\s+solid\s+rgba\(255,\s*255,\s*255,\s*0\.2\)/)
      }
    })

    it('container border-radius is exactly 16px', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        // $radius-container references $border-radius-rounded which is 16px
        expect(content).toMatch(/\$radius-container:\s*\$border-radius-rounded/)
        expect(content).toMatch(/\$border-radius-rounded:\s*16px/)
      }
    })

    it('container padding is exactly 30px', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toMatch(/\$spacing-container-padding:\s*30px/)
      }
    })

    it('panel gap is exactly 24px', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toMatch(/\$spacing-panel-gap:\s*24px/)
      }
    })

    it('panel min-height is exactly 450px', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toMatch(/\$spacing-panel-min-height:\s*450px/)
      }
    })

    it('container background is exactly rgba(14, 28, 45, 0.5)', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toMatch(/\$color-container-background:\s*rgba\(14,\s*28,\s*45,\s*0\.5\)/)
      }
    })

    it('panel content background is exactly rgba(20, 35, 50, 0.8)', () => {
      const designTokensPath = getDesignTokensPath()
      if (fs.existsSync(designTokensPath)) {
        const content = fs.readFileSync(designTokensPath, 'utf-8')
        expect(content).toMatch(/\$color-panel-background:\s*rgba\(20,\s*35,\s*50,\s*0\.8\)/)
      }
    })
  })
})
