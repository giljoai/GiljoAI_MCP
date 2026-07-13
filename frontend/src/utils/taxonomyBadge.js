/**
 * Shared taxonomy-badge styling helpers.
 *
 * Used by ProjectsView and TasksView to render the tinted square serial badge
 * (e.g. `BE-0017`). Both views derive the color from
 * `item.project_type?.color` / `item.task_type?.color`, falling back to
 * `DEFAULT_PROJECT_TYPE_COLOR` when the type record is missing or has no
 * custom color.
 *
 * Style anatomy (see `.project-id-badge` CSS in ProjectsView and the
 * mirrored `.taxonomy-badge` rule in TasksView):
 *   - background: <color>26 (15% alpha tint, hex shorthand)
 *   - color:      <color>    (full-brightness foreground)
 *
 * The 15% tint matches the broader tinted-badge convention in `main.scss`
 * and is WCAG AA on the `#12202e` panel background.
 */
import { DEFAULT_PROJECT_TYPE_COLOR, RESERVED_TASK_TYPE_ABBR, TSK_TYPE_COLOR } from './constants'

/**
 * Build the inline style object for a taxonomy badge (project- or
 * task-side). Accepts an explicit color string; callers resolve the
 * `*_type?.color` fallback at the call site so the helper stays pure.
 *
 * @param {string} color - Hex color (e.g. `#6DB3E4`). If falsy, the
 *        `DEFAULT_PROJECT_TYPE_COLOR` constant is substituted.
 * @returns {{ backgroundColor: string, color: string }}
 */
export function taxonomyBadgeStyle(color) {
  const resolved = color || DEFAULT_PROJECT_TYPE_COLOR
  return {
    backgroundColor: `${resolved}26`,
    color: resolved,
  }
}

/**
 * True when a taxonomy alias denotes the reserved TSK tag — i.e. a task row
 * or a converted-from-task project (BE-6049c). Tolerant of both the
 * `TSK-nnnn` (BE-6049a) and legacy `TSKnnnn` shapes.
 *
 * @param {string} alias - e.g. `TSK-0042`.
 * @returns {boolean}
 */
export function isReservedTaskAlias(alias) {
  return typeof alias === 'string' && /^TSK(?=[-\d])/.test(alias)
}

/**
 * Resolve the effective badge color for a taxonomy row, guaranteeing the
 * reserved TSK tag always renders in the purple accent (`TSK_TYPE_COLOR`)
 * even when the row's embedded type record (and its `color`) was trimmed from
 * the list payload. TSK is detected from the type `abbreviation` OR a
 * `TSK-nnnn` alias; everything else falls back to the row color and then the
 * default. Pure — callers pass plain fields, no DOM/store access.
 *
 * @param {object} [opts]
 * @param {string} [opts.abbreviation] - Type abbreviation (e.g. `BE`, `TSK`).
 * @param {string} [opts.alias] - Taxonomy alias (e.g. `TSK-0042`).
 * @param {string} [opts.color] - The row's own type color.
 * @returns {string} Hex color.
 */
export function resolveTaxonomyColor({ abbreviation, alias, color } = {}) {
  if (abbreviation === RESERVED_TASK_TYPE_ABBR || isReservedTaskAlias(alias)) {
    return TSK_TYPE_COLOR
  }
  return color || DEFAULT_PROJECT_TYPE_COLOR
}

export { DEFAULT_PROJECT_TYPE_COLOR }
