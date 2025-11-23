<template>
  <v-dialog
    :model-value="modelValue"
    max-width="560"
    @update:model-value="$emit('update:model-value', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-tune</v-icon>
        Serena MCP – Advanced Settings
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="text" @click="$emit('update:model-value', false)" />
      </v-card-title>

      <v-divider></v-divider>

      <v-card-text>
        <v-form ref="form" v-model="valid">
          <div class="mb-4 text-medium-emphasis">
            Adjust how agent prompts use Serena. Tooltips explain each option.
          </div>

          <v-row>
            <v-col cols="12">
              <v-switch
                v-model="local.use_in_prompts"
                color="primary"
                inset
                :label="'Use in prompts'"
                :hint="'Include Serena usage guidance in agent prompts'"
                persistent-hint
              />
            </v-col>

            <v-col cols="12">
              <v-switch
                v-model="local.tailor_by_mission"
                color="primary"
                inset
                :label="'Tailor by mission'"
                :hint="'Adjust guidance to mission type (bugfix, feature, tests, etc.)'"
                persistent-hint
              />
            </v-col>

            <v-col cols="12">
              <v-switch
                v-model="local.dynamic_catalog"
                color="primary"
                inset
                :label="'Dynamic tool catalog'"
                :hint="'Recommend only Serena tools detected as available'"
                persistent-hint
              />
            </v-col>

            <v-col cols="12">
              <v-switch
                v-model="local.prefer_ranges"
                color="primary"
                inset
                :label="'Prefer range reads'"
                :hint="'Prefer reading only relevant line ranges before full-file'"
                persistent-hint
              />
            </v-col>

            <v-col cols="12" sm="6">
              <v-text-field
                v-model.number="local.max_range_lines"
                type="number"
                label="Max range lines"
                :rules="[(v) => (v && v > 0) || 'Must be a positive number']"
                :hint="'Largest recommended range before full-file (default 180)'"
                persistent-hint
                density="comfortable"
              />
            </v-col>

            <v-col cols="12" sm="6">
              <v-text-field
                v-model.number="local.context_halo"
                type="number"
                label="Context halo lines"
                :rules="[(v) => (v && v >= 0) || 'Must be zero or positive']"
                :hint="'Extra lines around target ranges for context (default 12)'"
                persistent-hint
                density="comfortable"
              />
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="$emit('update:model-value', false)">Cancel</v-btn>
        <v-btn color="primary" :disabled="!valid" @click="handleSave" :loading="saving">Save</v-btn>
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
      use_in_prompts: true,
      tailor_by_mission: true,
      dynamic_catalog: true,
      prefer_ranges: true,
      max_range_lines: 180,
      context_halo: 12,
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
