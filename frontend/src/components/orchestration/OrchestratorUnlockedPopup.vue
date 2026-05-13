<template>
  <v-dialog
    v-model="localShow"
    max-width="480"
    role="dialog"
    aria-labelledby="orch-unlocked-title"
    data-testid="orchestrator-unlocked-popup"
  >
    <v-card class="smooth-border">
      <div id="orch-unlocked-title" class="dlg-header dlg-header--primary">
        <v-icon class="dlg-icon" icon="mdi-check-circle-outline" />
        <span class="dlg-title">Orchestrator unlocked</span>
      </div>
      <div class="orch-unlocked-body">
        <p>
          Your choice has been sent to the orchestrator. Please tell it to
          read its message and proceed.
        </p>
      </div>
      <div class="dlg-footer">
        <v-spacer />
        <v-btn
          color="primary"
          variant="flat"
          data-testid="orchestrator-unlocked-close"
          @click="close"
        >
          Close
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: { type: Boolean, required: true },
})
const emit = defineEmits(['close'])

const localShow = computed({
  get: () => props.show,
  set: (v) => { if (!v) emit('close') },
})

function close() {
  emit('close')
}
</script>

<style scoped lang="scss">
.orch-unlocked-body {
  padding: 20px 24px;

  p {
    margin: 0;
    font-size: 0.95rem;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.92);
  }
}
</style>
