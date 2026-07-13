/**
 * useProjectDeletion Composable
 *
 * Owns the destructive project-lifecycle workflow extracted from ProjectsView
 * (INF-6055, to keep that view under the 800-line guardrail): soft-delete,
 * cancel, restore, and permanent purge (single + all). A cohesive group — every
 * function here removes or unwinds a project — mirroring the existing
 * useProjectFilters / useProjectCloseout / useProjectStaging split.
 *
 * Confirmation-dialog visibility refs and the "in-flight purge" flags live here;
 * the view binds them to its BaseDialog confirmation modals. The view still owns
 * the Deleted-Projects list dialog (`showDeletedDialog`) and the page re-fetch
 * (`reloadProjects`), both passed in, since those are shared with non-deletion
 * concerns.
 *
 * Behavior is byte-for-byte the prior in-view implementation; only the location
 * changed. Functions stay top-level setup bindings in the view (re-destructured),
 * so `wrapper.vm.<fn>` test access is preserved.
 */
import { ref } from 'vue'
import { useProjectStore } from '@/stores/projects'
import { useNotificationStore } from '@/stores/notifications'
import { useToast } from '@/composables/useToast'

export function useProjectDeletion({ showDeletedDialog, reloadProjects }) {
  const projectStore = useProjectStore()
  const notificationStore = useNotificationStore()
  const { showToast } = useToast()

  // Confirmation-dialog visibility + target state
  const showDeleteDialog = ref(false)
  const projectToDelete = ref(null)
  const projectToCancel = ref(null)
  const showCancelDialog = ref(false)
  const projectToPurge = ref(null)
  const showPurgeSingleDialog = ref(false)
  const showPurgeAllDialog = ref(false)

  // In-flight purge guards
  const purgingProjectId = ref(null)
  const purgingAllDeleted = ref(false)

  function confirmDelete(project) {
    projectToDelete.value = project
    showDeleteDialog.value = true
  }

  async function deleteProject() {
    if (projectToDelete.value) {
      try {
        await projectStore.deleteProject(projectToDelete.value.id)
        showDeleteDialog.value = false
        projectToDelete.value = null
      } catch (error) {
        console.error('Failed to delete project:', error)
        showToast({ message: 'Failed to delete project. Please try again.', type: 'error' })
      }
    }
  }

  async function executeCancelProject() {
    if (projectToCancel.value) {
      try {
        await projectStore.cancelProject(projectToCancel.value.id)
        notificationStore.clearForProject(projectToCancel.value.id)
        showCancelDialog.value = false
        projectToCancel.value = null
        await reloadProjects()
      } catch (error) {
        console.error('Failed to cancel project:', error)
        showToast({ message: 'Failed to cancel project. Please try again.', type: 'error' })
      }
    }
  }

  async function restoreFromDelete(project) {
    try {
      await projectStore.restoreProject(project.id)
      showDeletedDialog.value = false
    } catch (error) {
      console.error('Failed to restore project:', error)
      showToast({ message: 'Failed to restore project. Please try again.', type: 'error' })
    }
  }

  function confirmPurgeDeleted(project) {
    if (!project) return
    projectToPurge.value = project
    showPurgeSingleDialog.value = true
  }

  async function purgeDeletedProject(project) {
    if (!project || purgingProjectId.value || purgingAllDeleted.value) return

    purgingProjectId.value = project.id
    try {
      await projectStore.purgeDeletedProject(project.id)
      if (projectStore.deletedProjects.length === 0) {
        showDeletedDialog.value = false
      }
    } catch (error) {
      console.error('Failed to purge deleted project:', error)
      showToast({ message: 'Failed to permanently delete the project. Please try again.', type: 'error' })
    } finally {
      purgingProjectId.value = null
    }
  }

  function confirmPurgeAllDeleted() {
    if (projectStore.deletedProjects.length === 0 || purgingAllDeleted.value) return
    showPurgeAllDialog.value = true
  }

  async function executePurgeAll() {
    showPurgeAllDialog.value = false
    purgingAllDeleted.value = true
    try {
      await projectStore.purgeAllDeletedProjects()
      showDeletedDialog.value = false
    } catch (error) {
      console.error('Failed to purge all deleted projects:', error)
      showToast({ message: 'Failed to purge deleted projects. Please try again.', type: 'error' })
    } finally {
      purgingAllDeleted.value = false
      purgingProjectId.value = null
    }
  }

  return {
    showDeleteDialog,
    projectToDelete,
    projectToCancel,
    showCancelDialog,
    projectToPurge,
    showPurgeSingleDialog,
    showPurgeAllDialog,
    purgingProjectId,
    purgingAllDeleted,
    confirmDelete,
    deleteProject,
    executeCancelProject,
    restoreFromDelete,
    confirmPurgeDeleted,
    purgeDeletedProject,
    confirmPurgeAllDeleted,
    executePurgeAll,
  }
}
