<template>
  <div class="project-series-selector">
    <!-- Type Selection -->
    <v-select
      :model-value="projectTypeId"
      :items="typeItems"
      label="Type"
      item-title="display"
      item-value="id"
      density="compact"
      variant="outlined"
      clearable
      class="mb-3"
      aria-label="Project type"
      @update:model-value="handleTypeChange"
    >
      <template #item="{ props: itemProps, item }">
        <v-list-item v-if="item.raw.id === '__add_custom__'" v-bind="itemProps" @click.stop="showAddTypeModal = true">
          <template #prepend>
            <v-icon size="small">mdi-plus-circle</v-icon>
          </template>
        </v-list-item>
        <v-list-item v-else v-bind="itemProps">
          <template #prepend>
            <div
              :style="{ backgroundColor: item.raw.color, width: '12px', height: '12px', borderRadius: '50%' }"
            />
          </template>
        </v-list-item>
      </template>

      <template #selection="{ item }">
        <div class="d-flex align-center">
          <div
            :style="{ backgroundColor: item.raw.color, width: '12px', height: '12px', borderRadius: '50%', marginRight: '8px' }"
          />
          {{ item.raw.display }}
        </div>
      </template>
    </v-select>

    <!-- Series & Subseries Row -->
    <v-row dense>
      <v-col cols="7">
        <v-select
          :model-value="seriesNumber"
          :items="seriesItems"
          label="Series Number"
          item-title="display"
          item-value="value"
          density="compact"
          variant="outlined"
          clearable
          :disabled="!projectTypeId"
          :loading="loadingSeries"
          aria-label="Series number"
          @update:model-value="$emit('update:seriesNumber', $event)"
        />
      </v-col>
      <v-col cols="5">
        <v-select
          :model-value="subseries"
          :items="subseriesItems"
          label="Subseries"
          item-title="title"
          item-value="value"
          density="compact"
          variant="outlined"
          clearable
          :disabled="!seriesNumber"
          aria-label="Subseries letter"
          @update:model-value="$emit('update:subseries', $event)"
        />
      </v-col>
    </v-row>

    <!-- Live Preview -->
    <v-alert v-if="previewText" type="info" variant="tonal" density="compact" class="mt-1">
      <div class="d-flex align-center">
        <div
          v-if="selectedType"
          :style="{ backgroundColor: selectedType.color, width: '12px', height: '12px', borderRadius: '50%', marginRight: '8px', flexShrink: 0 }"
        />
        <strong>Preview: {{ previewText }}</strong>
      </div>
    </v-alert>

    <!-- Validation Warning -->
    <v-alert v-if="validationWarning" type="warning" variant="tonal" density="compact" class="mt-2">
      {{ validationWarning }}
    </v-alert>

    <!-- Add Type Modal -->
    <AddTypeModal
      v-model="showAddTypeModal"
      @type-created="handleTypeCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/services/api'
import AddTypeModal from './AddTypeModal.vue'

const props = defineProps({
  projectTypeId: { type: String, default: null },
  seriesNumber: { type: Number, default: null },
  subseries: { type: String, default: null },
})

const emit = defineEmits([
  'update:projectTypeId',
  'update:seriesNumber',
  'update:subseries',
  'validation-warning',
])

// State
const projectTypes = ref([])
const loadingTypes = ref(false)
const loadingSeries = ref(false)
const showAddTypeModal = ref(false)
const availableSeries = ref([])
const validationWarning = ref(null)

// Computed: selected type object
const selectedType = computed(() => {
  if (!props.projectTypeId) return null
  return projectTypes.value.find((t) => t.id === props.projectTypeId) || null
})

// Computed: type dropdown items
const typeItems = computed(() => {
  const items = projectTypes.value.map((t) => ({
    id: t.id,
    display: `${t.abbreviation} - ${t.label}`,
    color: t.color,
    abbreviation: t.abbreviation,
  }))
  items.push({
    id: '__add_custom__',
    display: 'Add custom type...',
    color: 'transparent',
    abbreviation: '',
  })
  return items
})

// Computed: series dropdown items
const seriesItems = computed(() => {
  return availableSeries.value.map((num) => ({
    value: num,
    display: String(num).padStart(4, '0'),
  }))
})

// Computed: subseries dropdown items
const subseriesItems = computed(() => {
  const items = [{ title: '(none)', value: null }]
  for (let i = 0; i < 26; i++) {
    const letter = String.fromCharCode(97 + i)
    items.push({ title: letter, value: letter })
  }
  return items
})

// Computed: live preview text
const previewText = computed(() => {
  if (!selectedType.value || !props.seriesNumber) return null
  const series = String(props.seriesNumber).padStart(4, '0')
  const sub = props.subseries || ''
  return `${selectedType.value.abbreviation}-${series}${sub}`
})

// Fetch project types on mount
async function fetchProjectTypes() {
  loadingTypes.value = true
  try {
    const { data } = await api.projectTypes.list()
    projectTypes.value = data
  } catch (err) {
    console.error('[ProjectSeriesSelector] Failed to fetch project types:', err)
  } finally {
    loadingTypes.value = false
  }
}

// Fetch available series numbers for a type
async function fetchAvailableSeries(typeId) {
  if (!typeId) {
    availableSeries.value = []
    return
  }
  loadingSeries.value = true
  try {
    const { data } = await api.projects.getAvailableSeries(typeId, 10)
    availableSeries.value = data.available_series_numbers || []
  } catch (err) {
    console.error('[ProjectSeriesSelector] Failed to fetch available series:', err)
    availableSeries.value = []
  } finally {
    loadingSeries.value = false
  }
}

// Client-side duplicate check
function checkDuplicate() {
  // No /validate-taxonomy endpoint - skip server validation
  // The unique constraint at DB level will catch real duplicates on save
  validationWarning.value = null
}

// Handlers
function handleTypeChange(typeId) {
  if (typeId === '__add_custom__') {
    showAddTypeModal.value = true
    return
  }
  emit('update:projectTypeId', typeId)
  emit('update:seriesNumber', null)
  emit('update:subseries', null)
  validationWarning.value = null
  if (typeId) {
    fetchAvailableSeries(typeId)
  } else {
    availableSeries.value = []
  }
}

function handleTypeCreated(newType) {
  projectTypes.value.push(newType)
  emit('update:projectTypeId', newType.id)
  emit('update:seriesNumber', null)
  emit('update:subseries', null)
  fetchAvailableSeries(newType.id)
}

// Watch for seriesNumber changes to re-check validation
watch(() => [props.seriesNumber, props.subseries], checkDuplicate)

// If editing and type is pre-selected, fetch its series
watch(
  () => props.projectTypeId,
  (newId) => {
    if (newId && newId !== '__add_custom__') {
      fetchAvailableSeries(newId)
    }
  },
)

onMounted(() => {
  fetchProjectTypes()
  if (props.projectTypeId) {
    fetchAvailableSeries(props.projectTypeId)
  }
})
</script>
