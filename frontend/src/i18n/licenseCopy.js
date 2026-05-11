/**
 * Edition-keyed license + tagline copy. Single source of truth for any UI
 * surface that names the edition or quotes license framing (Settings → About,
 * RegisterView edition badge, Welcome screen, install screens, etc.).
 *
 * Self-hosted CE ships under the Elastic License 2.0 (ELv2). Hosted offerings
 * (Solo, Team) are subscriptions provided by GiljoAI LLC under a separate
 * Commercial License. Only the framing differs:
 *   - ce   = self-hosted, free under ELv2
 *   - demo = "try before you buy" tone
 *   - solo = single-org commercial subscription
 *   - team = multi-seat commercial subscription
 *
 * To consume:
 *   import { getLicenseCopy } from '@/i18n/licenseCopy'
 *   const copy = getLicenseCopy(giljoMode.value)
 *   copy.editionLabel    // 'Community Edition'
 *   copy.tagline         // short headline-grade phrase
 *   copy.longDescription // 1-2 sentence about-dialog body
 *   copy.licenseLine     // license attribution line
 *   copy.ctaLabel        // primary CTA on registration / upgrade surfaces
 *
 * Edition-isolation note: this file is CE-safe. It contains no SaaS imports,
 * no SaaS-only routes, and no GILJO_MODE branching beyond the lookup map.
 * The Deletion Test holds.
 */

const LICENSE_NAME = 'Elastic License 2.0'

export const licenseCopy = {
  ce: {
    editionLabel: 'Community Edition',
    tagline: 'Self-hosted AI agent orchestration. Run it yourself or your team.',
    longDescription:
      'Free under the Elastic License 2.0. The license restricts only managed-service redistribution to third parties, license-key tampering, and removal of copyright notices — internal team and company use is fine.',
    licenseLine: LICENSE_NAME,
    ctaLabel: 'Download',
  },
  demo: {
    editionLabel: 'Demo Edition',
    tagline: 'Try GiljoAI in your browser. No install required.',
    longDescription:
      'Hosted demo accounts are read-mostly and reset periodically. Sign up for a full account to keep your data and unlock full write access.',
    licenseLine: `${LICENSE_NAME} (hosted demo)`,
    ctaLabel: 'Sign up',
  },
  solo: {
    editionLabel: 'Solo',
    tagline: 'GiljoAI for one organization, hosted by us.',
    longDescription:
      'Single-organization commercial subscription with hosted infrastructure, automatic updates, and email support. Provided under a Commercial License separate from ELv2.',
    licenseLine: 'Commercial — Solo',
    ctaLabel: 'Start Solo',
  },
  team: {
    editionLabel: 'Team',
    tagline: 'GiljoAI for multi-seat teams, hosted by us.',
    longDescription:
      'Multi-seat commercial subscription with shared organizations, role-based access, and priority support. Provided under a Commercial License separate from ELv2.',
    licenseLine: 'Commercial — Team',
    ctaLabel: 'Start Team',
  },
}

// Map runtime giljo_mode values onto the keys above. Backend currently ships
// 'ce', 'demo', 'saas', and 'saas-production'. The 'saas' family is treated as
// 'team' framing by default; specific surfaces can call getLicenseCopy('solo')
// directly when they know the active plan.
const MODE_ALIASES = {
  ce: 'ce',
  '': 'ce',
  demo: 'demo',
  saas: 'team',
  'saas-production': 'team',
  solo: 'solo',
  team: 'team',
}

/**
 * Resolve license copy for a given giljo_mode or explicit edition key.
 * Unknown values fall back to CE — the safest default for self-hosted users.
 *
 * @param {string} modeOrEdition - giljo_mode ('ce'|'demo'|'saas'|...) or
 *                                 edition key ('ce'|'demo'|'solo'|'team').
 * @returns {{editionLabel:string, tagline:string, longDescription:string,
 *           licenseLine:string, ctaLabel:string}}
 */
export function getLicenseCopy(modeOrEdition) {
  const key = MODE_ALIASES[modeOrEdition] || modeOrEdition
  return licenseCopy[key] || licenseCopy.ce
}

export const LICENSE_NAME_FULL = LICENSE_NAME
