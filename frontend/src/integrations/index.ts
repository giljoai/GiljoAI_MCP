/**
 * Integrations Module
 *
 * Central hub for integration registry and related utilities.
 * This module provides the integration definitions consumed by
 * UserSettings and SystemSettings views.
 *
 * @module integrations
 */

export {
  INTEGRATIONS,
  getIntegrationById,
  getIntegrationsByKind,
  type Integration,
  type IntegrationKind,
} from './registry'
