/**
 * Integration Registry
 *
 * Centralized registry of all available integrations in GiljoAI MCP Server.
 * This registry defines integration metadata that the UI components consume
 * for rendering integration cards and configuration components.
 *
 * @module integrations/registry
 */

/**
 * Valid integration kinds/categories
 */
export type IntegrationKind = 'tooling' | 'ai_tool' | 'export' | 'scm'

/**
 * Integration definition structure
 */
export interface Integration {
  /** Unique identifier for the integration */
  id: string
  /** Display name shown in the UI */
  name: string
  /** Category/type of integration */
  kind: IntegrationKind
  /** Vue component name for user configuration in My Settings */
  userConfigComponent: string
  /** Optional description of what the integration does */
  description?: string
  /** Optional Material Design Icon identifier */
  icon?: string
  /** Optional Vue component name for admin info display in System Settings */
  adminInfoComponent?: string
}

/**
 * Central registry of all integrations
 *
 * This array defines all available integrations in the system.
 * Each integration specifies its metadata and the component to render
 * for configuration in My Settings (and optionally System Settings).
 */
export const INTEGRATIONS: Integration[] = [
  {
    id: 'mcp',
    name: 'GiljoAI MCP Integration',
    kind: 'tooling',
    userConfigComponent: 'AiToolConfigWizard',
    description:
      'Connect your AI coding tool to GiljoAI orchestration. Supports Claude Code, Codex CLI, and Gemini CLI.',
    icon: 'mdi-connection',
  },
  {
    id: 'slash_commands',
    name: 'Slash Commands',
    kind: 'tooling',
    userConfigComponent: 'SlashCommandSetup',
    description:
      'Setup slash commands for AI coding tools to import agent templates and trigger orchestrator features.',
    icon: 'mdi-slash-forward-box',
  },
  {
    id: 'claude_code',
    name: 'Claude Code Export',
    kind: 'export',
    userConfigComponent: 'ClaudeCodeExport',
    description:
      'Export agent templates directly to Claude Code for use in your development workflow.',
    icon: 'mdi-export',
  },
  {
    id: 'serena',
    name: 'Serena MCP',
    kind: 'ai_tool',
    userConfigComponent: 'SerenaIntegrationCard',
    description:
      'Intelligent codebase understanding and navigation. Provides deep semantic code analysis and symbol navigation.',
    icon: 'mdi-code-braces-box',
    adminInfoComponent: 'SerenaAdminInfo',
  },
  {
    id: 'github',
    name: 'Git + 360 Memory',
    kind: 'scm',
    userConfigComponent: 'GitIntegrationCard',
    description:
      'Track git commits in 360 Memory for orchestrator context. Captures commit history at project closeout.',
    icon: 'mdi-github',
  },
]

/**
 * Find an integration by its unique ID
 *
 * @param id - The integration ID to search for
 * @returns The matching Integration or undefined if not found
 *
 * @example
 * ```typescript
 * const mcp = getIntegrationById('mcp')
 * if (mcp) {
 *   console.log(mcp.name) // 'GiljoAI MCP Integration'
 * }
 * ```
 */
export function getIntegrationById(id: string): Integration | undefined {
  return INTEGRATIONS.find((integration) => integration.id === id)
}

/**
 * Get all integrations of a specific kind
 *
 * @param kind - The integration kind to filter by
 * @returns Array of integrations matching the specified kind
 *
 * @example
 * ```typescript
 * const toolingIntegrations = getIntegrationsByKind('tooling')
 * // Returns: [{ id: 'mcp', ... }, { id: 'slash_commands', ... }]
 * ```
 */
export function getIntegrationsByKind(kind: IntegrationKind): Integration[] {
  return INTEGRATIONS.filter((integration) => integration.kind === kind)
}
