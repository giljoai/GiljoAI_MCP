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
import { DEFAULT_PROJECT_TYPE_COLOR } from './constants'

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

export { DEFAULT_PROJECT_TYPE_COLOR }
