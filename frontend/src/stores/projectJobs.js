/**
 * projectJobs store
 * Manages project-level staging/launch state for jobs tab.
 * State-only; networking remains in callers.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useProjectJobsStore = defineStore('projectJobs', () => {
  const currentProjectId = ref(null)
  const projectDescription = ref('')
  const orchestratorMission = ref('')
  const missionDirty = ref(false)

  const stagingStatus = ref(null) // null | 'staging' | 'ready' | 'cancelled'
  const stagingStartedAt = ref(null)

  const launchComplete = ref(false)
  const launchError = ref(null)

  const isStaging = computed(() => stagingStatus.value === 'staging')
  const isLaunchReady = computed(() => stagingStatus.value === 'ready')
  const canLaunch = computed(
    () => isLaunchReady.value && !launchComplete.value && !launchError.value,
  )
  const hasStagingError = computed(() => stagingStatus.value === 'cancelled')

  const setProjectContext = ({ projectId = null, description = '' } = {}) => {
    currentProjectId.value = projectId
    projectDescription.value = description
  }

  const setMission = (mission) => {
    orchestratorMission.value = mission || ''
    missionDirty.value = true
  }

  const markMissionSaved = () => {
    missionDirty.value = false
  }

  const updateStagingStatus = (status, startedAt = null) => {
    stagingStatus.value = status
    if (startedAt) {
      stagingStartedAt.value = startedAt
    }

    if (status === 'staging') {
      launchComplete.value = false
      launchError.value = null
    }
  }

  const markLaunchComplete = () => {
    launchComplete.value = true
  }

  const setLaunchError = (message) => {
    launchError.value = message
  }

  const $reset = () => {
    currentProjectId.value = null
    projectDescription.value = ''
    orchestratorMission.value = ''
    missionDirty.value = false
    stagingStatus.value = null
    stagingStartedAt.value = null
    launchComplete.value = false
    launchError.value = null
  }

  return {
    // state
    currentProjectId,
    projectDescription,
    orchestratorMission,
    missionDirty,
    stagingStatus,
    stagingStartedAt,
    launchComplete,
    launchError,

    // getters
    isStaging,
    isLaunchReady,
    canLaunch,
    hasStagingError,

    // actions
    setProjectContext,
    setMission,
    markMissionSaved,
    updateStagingStatus,
    markLaunchComplete,
    setLaunchError,
    $reset,
  }
})
