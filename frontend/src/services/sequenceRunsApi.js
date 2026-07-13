/**
 * Sequence Runs API (FE-6131e — binds to BE-6131a durable run record REST).
 *
 * The dashboard CREATES the record + OBSERVES; execution is CLI-driven by the
 * orchestrator session (spec §11 — the web cannot spawn). NO new MCP tool;
 * this consumes the existing api/endpoints/sequence_runs.py routes.
 *
 *   create() body: { project_ids, resolved_order, execution_mode,
 *     review_policy?, status?, current_index?, project_statuses? }
 *   - execution_mode ∈ {multi_terminal, subagent} (BE-9035c collapse; a
 *     handful of pre-collapse per-CLI tokens are tolerated on read only);
 *     review_policy ∈ {per_card, auto_close}.
 *   - cap is 5 project_ids (server-enforced; 422 on violation).
 *
 * Extracted from api.js (FE-6131e gating fixup) to keep api.js under the
 * 800-line CI guardrail. Import this module directly OR access via
 * api.sequenceRuns (api.js re-exports it on the default export).
 *
 * FE-6171b: added removeMember for granular project removal from a run.
 */
import { apiClient } from './api.js'

export const sequenceRunsApi = {
  create: (data) => apiClient.post('/api/v1/sequence-runs', data),
  get: (runId) => apiClient.get(`/api/v1/sequence-runs/${runId}`),
  update: (runId, data) => apiClient.patch(`/api/v1/sequence-runs/${runId}`, data),
  // BE-6165e: durable-election read-back. Pass { status: 'pending,running,stalled' }
  // (default) to hydrate the locked "In chain" checkboxes + detect an orphaned run.
  list: (params = {}) => apiClient.get('/api/v1/sequence-runs', { params }),
  // BE-6165e: end a run + free membership. mode = 'graceful' (-> terminated) | 'cancel' (-> cancelled).
  release: (runId, mode) => apiClient.post(`/api/v1/sequence-runs/${runId}/release`, null, { params: { mode } }),
  // FE-6178: "Deactivate Chain" back-out — reset all member projects to inactive +
  // dissolve the run (cancelled). The chain equivalent of solo Deactivate.
  deactivate: (runId) => apiClient.post(`/api/v1/sequence-runs/${runId}/deactivate`),
  // FE-6171b: remove ONE project from a run (Editing tier only).
  // BE refuses with 422 when run is locked/ultralocked/running.
  // When removal leaves 1 member the BE dissolves the run (→ cancelled); the lone
  // project is NOT auto-activated (FE-6174b removed collapse-to-solo).
  removeMember: (runId, projectId) =>
    apiClient.delete(`/api/v1/sequence-runs/${runId}/members/${projectId}`),
  // BE-9098: durably record a chain member as reviewed so the Review badge survives
  // refresh/navigation. Append-only + idempotent server-side; returns the updated run.
  markReviewed: (runId, projectId) =>
    apiClient.post(`/api/v1/sequence-runs/${runId}/members/${projectId}/review`),
}
