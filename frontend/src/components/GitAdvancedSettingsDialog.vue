<template>
  <v-dialog
    :model-value="modelValue"
    max-width="560"
    @update:model-value="$emit('update:model-value', $event)"
  >
    <v-card v-draggable>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-github</v-icon>
        Git Integration – Advanced Settings
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="text" @click="$emit('update:model-value', false)" />
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text>
        <v-form ref="form" v-model="valid">
          <div class="mb-4 text-medium-emphasis">
            Configure how Git integration works with 360 Memory and agent prompts.
          </div>

          <v-row>
            <v-col cols="12">
              <v-switch
                v-model="local.use_in_prompts"
                color="primary"
                inset
                :label="'Include in agent prompts'"
                :hint="'Tell agents that Git is available for version control operations'"
                persistent-hint
              />
            </v-col>

            <v-col cols="12">
              <v-switch
                v-model="local.include_commit_history"
                color="primary"
                inset
                :label="'Include commit history'"
                :hint="'Store git commit messages in 360 Memory at project closeout'"
                persistent-hint
              />
            </v-col>

            <v-col cols="12" sm="6">
              <v-text-field
                v-model.number="local.max_commits"
                type="number"
                label="Maximum commits"
                :rules="[(v) => (v && v > 0 && v <= 100) || 'Must be between 1 and 100']"
                :hint="'Number of recent commits to include (default 50)'"
                persistent-hint
                density="comfortable"
              />
            </v-col>

            <v-col cols="12" sm="6">
              <v-text-field
                v-model="local.branch_strategy"
                label="Default branch"
                :rules="[(v) => !!v || 'Branch strategy is required']"
                :hint="'Default branch name (e.g., main, master)'"
                persistent-hint
                density="comfortable"
              />
            </v-col>

            <v-col cols="12">
              <v-alert type="info" variant="tonal" density="compact">
                <div class="text-body-2">
                  <strong>Note:</strong> Git must be configured on your system with access to your
                  repositories. GiljoAI uses your local git credentials.
                </div>
              </v-alert>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="$emit('update:model-value', false)">Cancel</v-btn>
        <v-btn color="primary" :disabled="!valid" :loading="saving" @click="handleSave">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, reactive } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  value: {
    type: Object,
    default: () => ({
      use_in_prompts: false,
      include_commit_history: true,
      max_commits: 50,
      branch_strategy: 'main',
    }),
  },
})

const emit = defineEmits(['update:model-value', 'save'])

const form = ref(null)
const valid = ref(true)
const saving = ref(false)
const local = reactive({ ...props.value })

watch(
  () => props.value,
  (v) => {
    Object.assign(local, v || {})
  },
)

function handleSave() {
  saving.value = true
  // emit payload; parent calls API and closes dialog
  emit('save', { ...local }, () => {
    saving.value = false
  })
}
</script>

<style scoped></style>
