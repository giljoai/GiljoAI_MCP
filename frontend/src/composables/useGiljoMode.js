/**
 * CE-safe Giljo mode accessor.
 *
 * Centralizes `mode === 'ce' | 'saas'` comparisons so that adding a new
 * edition is a one-file change (giljo-internal/no-scattered-mode-checks).
 *
 * ADR-002 note: router guards and first-paint code MUST read mode from
 * setupService.checkEnhancedStatus(), NOT this composable. This composable
 * reads from configService (cached after fetchConfig()) and is suited for
 * component setup and post-mount contexts where config is already loaded.
 *
 * CE import safe: no dependency on saas/ directories.
 */
import configService from '@/services/configService'

/**
 * Stateless edition predicates over an already-resolved mode string.
 *
 * Use these when a component holds its own reactive mode ref (or reads mode
 * from setupService per ADR-002) and needs to centralize only the literal
 * comparison — reactivity and the mode source stay with the caller, the 'ce'
 * / 'saas' literals live here (giljo-internal/no-scattered-mode-checks).
 */

/** True when the given mode string is CE. @param {string} mode @returns {boolean} */
export function isCeModeValue(mode) {
  return mode === 'ce'
}

/**
 * True when the given mode string is any SaaS variant (saas or saas-production).
 * Mirrors useSaasMode.isSaas / useGiljoMode().isSaasMode.
 * @param {string} mode @returns {boolean}
 */
export function isSaasModeValue(mode) {
  return mode === 'saas' || mode === 'saas-production'
}

/** True when the given mode string is NOT CE. @param {string} mode @returns {boolean} */
export function isNonCeModeValue(mode) {
  return mode !== 'ce'
}

export function useGiljoMode() {
  /**
   * Returns the current giljo mode string as reported by configService.
   * @returns {string} e.g. 'ce', 'saas', 'saas-production', or 'unknown'
   */
  function getMode() {
    return configService.getGiljoMode()
  }

  /**
   * True when running in CE (self-hosted) mode.
   * @returns {boolean}
   */
  function isCeMode() {
    return getMode() === 'ce'
  }

  /**
   * True when running in SaaS or SaaS-production mode.
   * Matches the same set as useSaasMode.isSaas (saas/ composable);
   * use this in CE-exported code that cannot import from saas/.
   * @returns {boolean}
   */
  function isSaasMode() {
    const m = getMode()
    return m === 'saas' || m === 'saas-production'
  }

  /**
   * True when NOT in CE mode (SaaS, demo, or any unrecognised mode).
   * Equivalent to `mode !== 'ce'` guard patterns.
   * @returns {boolean}
   */
  function isNonCeMode() {
    return getMode() !== 'ce'
  }

  return { getMode, isCeMode, isSaasMode, isNonCeMode }
}
