<template>
  <v-dialog v-model="isOpen" max-width="800" persistent retain-focus scrollable>
    <v-card v-draggable class="smooth-border">
      <div class="dlg-header dlg-header--warning">
        <span class="dlg-title">Deleted Projects ({{ deletedProjects.length }})</span>
        <v-btn icon variant="text" class="dlg-close" aria-label="Close dialog" @click="isOpen = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </div>

      <v-card-text>
        <v-alert
          v-if="deletedProjects.length > 0"
          type="warning"
          variant="tonal"
          density="compact"
          class="mb-3"
        >
          Permanently deleting items will remove all related data immediately. This action cannot
          be undone.
        </v-alert>

        <v-list v-if="deletedProjects.length > 0" class="smooth-border rounded">
          <v-list-item v-for="(project, index) in deletedProjects" :key="project.id">
            <template v-slot:prepend>
              <v-icon icon="mdi-folder-minus"></v-icon>
            </template>

            <div class="flex-grow-1">
              <div class="font-weight-bold">{{ project.name }}</div>
              <div class="text-caption text-muted-a11y">
                {{ project.id }}
              </div>
            </div>

            <template v-slot:append>
              <div class="d-flex align-center ga-1">
                <v-btn
                  icon="mdi-delete-restore"
                  size="small"
                  variant="text"
                  :disabled="purgingProjectId === project.id || purgingAllDeleted"
                  title="Restore project"
                  aria-label="Restore deleted project"
                  @click="$emit('restore', project)"
                ></v-btn>
                <v-btn
                  icon="mdi-delete-forever"
                  size="small"
                  variant="text"
                  color="error"
                  :loading="purgingProjectId === project.id"
                  :disabled="purgingAllDeleted"
                  title="Permanently delete project"
                  aria-label="Permanently delete project"
                  data-testid="purge-project"
                  @click="$emit('purge', project)"
                ></v-btn>
              </div>
            </template>

            <v-divider v-if="index < deletedProjects.length - 1" class="my-2" />
          </v-list-item>
        </v-list>

        <div v-else class="text-center py-8 text-muted-a11y">
          <v-icon size="48" class="mb-4">mdi-folder-open</v-icon>
          <p>No deleted projects</p>
        </div>
      </v-card-text>

      <div class="dlg-footer">
        <v-spacer></v-spacer>
        <v-btn
          color="error"
          variant="flat"
          prepend-icon="mdi-delete-forever"
          :disabled="deletedProjects.length === 0 || purgingAllDeleted"
          :loading="purgingAllDeleted"
          data-testid="purge-projects-all"
          @click="$emit('purge-all')"
        >
          Delete All
        </v-btn>
        <v-btn variant="text" @click="isOpen = false">Close</v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  deletedProjects: {
    type: Array,
    default: () => [],
  },
  purgingProjectId: {
    type: String,
    default: null,
  },
  purgingAllDeleted: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'restore', 'purge', 'purge-all'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})
</script>
