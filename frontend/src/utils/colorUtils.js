/**
 * Shared color utility functions for the 0870 design system.
 * Extracted from duplicated hexToRgba helpers across multiple components.
 *
 * @module colorUtils
 */

/**
 * Convert a hex color string to an rgba() CSS value.
 * @param {string} hex - Hex color string (e.g. '#D4B08A')
 * @param {number} alpha - Alpha value between 0 and 1
 * @returns {string} CSS rgba() string
 */
export function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
