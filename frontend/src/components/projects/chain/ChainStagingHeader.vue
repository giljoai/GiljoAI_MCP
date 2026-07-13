<template>
  <!-- FE-6199: chain staging header — the overarching mission window plus the
       dedicated conductor card, shown together above the staging tabs. Chain mode
       only; the host gates with v-if so solo views never render this. -->
  <div v-if="chainCtx" class="chain-staging-header">
    <ChainMissionWindow :mission="chainCtx.chainMission || chainCtx.headMission" />
    <ChainConductorCard
      v-if="chainCtx.conductorAgent"
      :conductor="chainCtx.conductorAgent"
      :label="chainCtx.conductor?.label || 'Conductor'"
    />
  </div>
</template>

<script setup>
/**
 * ChainStagingHeader — FE-6199
 * Cohesive staging-header pair (overarching mission window + conductor card).
 * Pure composition of two display components; all data comes from chainCtx.
 * Edition scope: CE.
 */
import ChainMissionWindow from './ChainMissionWindow.vue'
import ChainConductorCard from './ChainConductorCard.vue'

defineProps({
  chainCtx: {
    type: Object,
    default: null,
  },
})
</script>
