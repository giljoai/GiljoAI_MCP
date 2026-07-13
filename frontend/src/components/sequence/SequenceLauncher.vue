<template>
  <!-- FE-6131e / FE-6165f: shell for the "select → run" flow, reused by
       /projects and /roadmap. Renders the contextual bulk-action bar above the
       slotted list/table and exposes the selection API (selectedIds + toggle)
       to the slot so the host's checkboxes bind to it.
       Keeping all the selection/run wiring here keeps both host views thin
       (each near the 800-line guardrail). -->
  <div class="sequence-launcher">
    <SequenceBulkBar :count="selectedCount" @run="onRunClicked" @clear="clear" />

    <slot :selected-ids="selectedIds" :toggle="toggle" :clear="clear" :election-active="electionActive" />
  </div>
</template>

<script setup>
import { useSequenceRunner } from '@/composables/useSequenceRunner'
import SequenceBulkBar from '@/components/sequence/SequenceBulkBar.vue'

const {
  selection,
  selectedIds,
  selectedCount,
  electionActive,
  toggle,
  clear,
  resolveRunOrder,
  startSequence,
} = useSequenceRunner()

async function onRunClicked() {
  if (selection.value.size === 0) return
  const resolvedRows = await resolveRunOrder(Array.from(selection.value.values()))
  const resolvedOrder = resolvedRows.map((r) => r.project_id)
  const run = await startSequence({ projectIds: selectedIds.value, resolvedOrder })
  if (run) clear()
}

// Exposed for unit tests (assert the wired selection API).
defineExpose({ selectedIds, selectedCount, electionActive, toggle, clear })
</script>

<style scoped lang="scss">
.sequence-launcher {
  display: contents;
}
</style>
