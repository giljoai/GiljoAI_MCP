/**
 * sequenceEventRoutes.js — FE-6165f
 *
 * Routes the `sequence:updated` WS event (broadcast by BE-6165c's
 * SequenceChainContextResolver on conductor self-registration + every run
 * advance) to the sequenceRunStore. The payload carries ONLY { run_id }, so the
 * store's handler re-fetches authoritative state (re-hydrate the active-election
 * set + refresh the cockpit's open run). This is what keeps the locked "In chain"
 * checkboxes + the cockpit live without a per-event diff.
 */
export const SEQUENCE_EVENT_ROUTES = {
  'sequence:updated': { store: 'sequenceRun', action: 'handleSequenceUpdated' },
}
