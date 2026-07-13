/**
 * sequenceOrder.js — FE-6131e
 *
 * Pure (Vue-free) helpers for the Sequential Multi-Project Runner selection +
 * run flow. Kept dependency-free so the run-order resolution and the
 * dependency-chain locking are unit-testable in isolation (the composable
 * `useSequenceRunner` and the sequence cockpit both import from here).
 *
 * Spec: SEQUENTIAL_MULTI_PROJECT_RUNNER_2026-06-18.md §4 + decision #9.
 *   - Cap = 5 projects per sequence (decision #9).
 *   - Default run order = roadmap order (sort_order).
 *   - "Chain links locked in dependency order": projects whose taxonomy_alias
 *     shares a series base with a trailing subseries letter (e.g. BE-0001a,
 *     BE-0001b, BE-0001c) form a chain that MUST stay contiguous and in
 *     suffix order (a → b → c). There is no chain_id/depends_on column at the
 *     model layer (spec §3) — the series naming suffix IS the only dependency
 *     signal available to the frontend, so we lock on it.
 *
 * Edition scope: CE.
 */

// Hard cap on projects per sequence (spec decision #9; override lives in
// Settings → Danger Zone — not built here). The backend enforces the same cap
// (MAX_SEQUENCE_PROJECTS in models/sequence_runs.py); this mirrors it so the UI
// can disable "Run sequential" before a doomed POST.
export const MAX_SEQUENCE_PROJECTS = 5

// Uniform execution mode for the whole sequence (spec decision #7). Values MUST
// match the backend VALID_EXECUTION_MODES. The dashboard persists the chosen
// mode on the run record; the CLI orchestrator (session A) reads it to drive
// execution (spec §11 — the web cannot spawn). Default = multi_terminal (the
// interactive mode, spec §3 "Headless rule").
// BE-9035c: execution-mode collapse — backend now only accepts 2 canonical
// values; the per-CLI tokens are tolerated on read only, never written.
export const SEQUENCE_EXECUTION_MODES = [
  { value: 'multi_terminal', label: 'Multi-terminal (interactive)' },
  { value: 'subagent', label: 'Subagent (orchestrator-managed)' },
]

export const DEFAULT_EXECUTION_MODE = 'multi_terminal'

/**
 * Parse a taxonomy_alias into a chain key { base, suffix }, or null when it has
 * no trailing single lowercase subseries letter. "FE-6131e" → { base: "FE-6131",
 * suffix: "e" }; "FE-6131" (no suffix) and "" → null.
 *
 * @param {string} alias
 * @returns {{base: string, suffix: string}|null}
 */
export function parseChainKey(alias) {
  if (!alias || typeof alias !== 'string') return null
  // Require a digit before the trailing letter so a plain "FOO" isn't read as a
  // chain; the series number is always numeric (e.g. BE-0001a).
  const m = alias.trim().match(/^(.*[0-9])([a-z])$/)
  if (!m) return null
  return { base: m[1], suffix: m[2] }
}

/**
 * Identify multi-member dependency chains within a set of selected rows.
 *
 * @param {Array<{project_id: string, taxonomy_alias?: string}>} rows
 * @returns {Map<string, string[]>} base → ordered (a→b→c) member project_ids,
 *   only for bases with ≥ 2 selected members.
 */
export function computeChains(rows) {
  const groups = new Map()
  for (const r of rows || []) {
    const key = parseChainKey(r.taxonomy_alias)
    if (!key) continue
    if (!groups.has(key.base)) groups.set(key.base, [])
    groups.get(key.base).push({ id: r.project_id, suffix: key.suffix })
  }
  const chains = new Map()
  for (const [base, members] of groups) {
    if (members.length < 2) continue
    members.sort((a, b) => (a.suffix < b.suffix ? -1 : a.suffix > b.suffix ? 1 : 0))
    chains.set(
      base,
      members.map((m) => m.id),
    )
  }
  return chains
}

/**
 * Is this row a member of a multi-member chain (and therefore drag-locked)?
 *
 * @param {{taxonomy_alias?: string}} row
 * @param {Map<string, string[]>} chains
 * @returns {boolean}
 */
export function isChainLocked(row, chains) {
  const key = parseChainKey(row?.taxonomy_alias)
  return !!(key && chains && chains.has(key.base))
}

/**
 * Order selected rows by roadmap sort_order (default run order). Rows absent
 * from the roadmap sort to the end, preserving their incoming relative order
 * (stable). Does NOT mutate the input.
 *
 * @param {Array<{project_id: string}>} rows
 * @param {Map<string, number>} orderMap project_id → sort_order
 * @returns {Array}
 */
export function orderByRoadmap(rows, orderMap) {
  const map = orderMap || new Map()
  return (rows || [])
    .map((row, i) => ({
      row,
      rank: map.has(row.project_id) ? map.get(row.project_id) : Number.MAX_SAFE_INTEGER,
      i,
    }))
    .sort((a, b) => a.rank - b.rank || a.i - b.i)
    .map((w) => w.row)
}

/**
 * Re-assert chain contiguity + suffix order over a (possibly drag-scrambled)
 * list. Each chain's members are emitted together, in suffix order, at the
 * position of the chain's first-encountered member; non-chain ("free") rows keep
 * their position. Idempotent. Does NOT mutate the input.
 *
 * @param {Array<{project_id: string, taxonomy_alias?: string}>} rows
 * @param {Map<string, string[]>} chains
 * @returns {Array}
 */
export function normalizeChainOrder(rows, chains) {
  if (!chains || chains.size === 0) return [...(rows || [])]
  const byId = new Map((rows || []).map((r) => [r.project_id, r]))
  const emitted = new Set()
  const result = []
  for (const r of rows || []) {
    const key = parseChainKey(r.taxonomy_alias)
    if (key && chains.has(key.base)) {
      if (emitted.has(key.base)) continue
      for (const id of chains.get(key.base)) {
        if (byId.has(id)) result.push(byId.get(id))
      }
      emitted.add(key.base)
    } else {
      result.push(r)
    }
  }
  return result
}
