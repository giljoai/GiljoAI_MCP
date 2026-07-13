/**
 * Project Tabs Store (Navigation Only)
 *
 * 0379c migration: project domain state (mission, staging, messages, jobs)
 * lives in dedicated stores. This store remains as a small navigation/global
 * reference for the currently viewed project in the UI.
 */

import { defineStore } from 'pinia'

export const useProjectTabsStore = defineStore('projectTabs', {
  state: () => ({
    currentProject: null,
    isLaunched: false,
  }),

  actions: {
    setCurrentProject(project) {
      this.currentProject = project || null
    },

    setLaunched(isLaunched) {
      this.isLaunched = Boolean(isLaunched)
    },

    $reset() {
      this.currentProject = null
      this.isLaunched = false
    },
  },
})
