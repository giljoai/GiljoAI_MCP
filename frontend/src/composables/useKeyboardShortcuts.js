import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useKeyboardShortcuts() {
  const router = useRouter()
  const isHelpModalOpen = ref(false)
  const shortcuts = ref([
    // Global Navigation
    { key: 'Ctrl+K, Cmd+K', description: 'Quick search/command palette', action: 'search' },
    { key: 'Alt+1', description: 'Navigate to Dashboard', action: () => router.push('/Dashboard') },
    { key: 'Alt+2', description: 'Navigate to Projects', action: () => router.push('/projects') },
    { key: 'Alt+4', description: 'Navigate to Messages', action: () => router.push('/messages') },
    { key: 'Alt+5', description: 'Navigate to Tasks', action: () => router.push('/tasks') },
    { key: 'Alt+6', description: 'Navigate to Settings', action: () => router.push('/settings') },
    { key: 'Escape', description: 'Close modals/dialogs', action: 'escape' },
    { key: '?', description: 'Show keyboard shortcuts help', action: () => showHelp() },

    // Project Management
    {
      key: 'N',
      description: 'New project (when in Projects view)',
      action: 'new-project',
      context: 'projects',
    },
    { key: 'E', description: 'Edit selected project', action: 'edit-project', context: 'projects' },
    { key: 'Delete', description: 'Delete selected item', action: 'delete-item' },

    // Message Composer
    { key: 'M', description: 'Open message composer', action: 'compose-message' },

    // Data Tables
    { key: '↑/↓', description: 'Navigate table rows', action: 'navigate-table' },
    { key: 'Enter', description: 'Open detail view', action: 'open-detail' },
    { key: '/', description: 'Focus search input', action: 'focus-search' },
  ])

  const activeShortcuts = ref(new Set())

  function showHelp() {
    isHelpModalOpen.value = true
  }

  function hideHelp() {
    isHelpModalOpen.value = false
  }

  function handleKeyDown(event) {
    // Ignore if user is typing in an input field
    if (event.target.matches('input, textarea, select, [contenteditable]')) {
      // Allow Escape to work in inputs
      if (event.key !== 'Escape') {
        return
      }
    }

    // Build key combination string
    const keys = []
    if (event.ctrlKey) {
      keys.push('Ctrl')
    }
    if (event.metaKey) {
      keys.push('Cmd')
    }
    if (event.altKey) {
      keys.push('Alt')
    }
    if (event.shiftKey) {
      keys.push('Shift')
    }

    // Add the actual key
    let key = event.key
    if (key === ' ') {
      key = 'Space'
    }
    if (key === 'ArrowUp') {
      key = '↑'
    }
    if (key === 'ArrowDown') {
      key = '↓'
    }
    if (key === 'ArrowLeft') {
      key = '←'
    }
    if (key === 'ArrowRight') {
      key = '→'
    }

    // Special handling for single keys
    if (!event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) {
      // Help modal - '?'
      if (
        event.key === '?' &&
        !event.target.matches('input, textarea, select, [contenteditable]')
      ) {
        event.preventDefault()
        showHelp()
        return
      }

      // Search focus - '/'
      if (
        event.key === '/' &&
        !event.target.matches('input, textarea, select, [contenteditable]')
      ) {
        event.preventDefault()
        const searchInput = document.querySelector('[data-search-input]')
        if (searchInput) {
          searchInput.focus()
        }
        window.dispatchEvent(
          new CustomEvent('keyboard-shortcut', { detail: { action: 'focus-search' } }),
        )
        return
      }

      // Other single key shortcuts
      const singleKeyShortcuts = ['N', 'E', 'M', 'R', 'Space', 'Enter', 'Delete', 'Escape']
      if (singleKeyShortcuts.includes(key)) {
        const shortcut = shortcuts.value.find((s) => s.key === key)
        if (shortcut) {
          event.preventDefault()
          if (typeof shortcut.action === 'function') {
            shortcut.action()
          } else {
            window.dispatchEvent(
              new CustomEvent('keyboard-shortcut', { detail: { action: shortcut.action } }),
            )
          }
        }
        return
      }
    }

    keys.push(key)
    const keyCombo = keys.join('+')

    // Check for Ctrl+K or Cmd+K
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard-shortcut', { detail: { action: 'search' } }))
      return
    }

    // Check for Alt+Number navigation
    if (event.altKey && event.key >= '1' && event.key <= '6') {
      event.preventDefault()
      const routes = ['/Dashboard', '/projects', '/messages', '/tasks', '/settings']
      const index = parseInt(event.key) - 1
      if (routes[index]) {
        router.push(routes[index])
      }
      return
    }

    // Check for arrow key navigation
    if (!event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) {
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        const activeElement = document.activeElement
        if (activeElement?.closest('[data-table]')) {
          event.preventDefault()
          window.dispatchEvent(
            new CustomEvent('keyboard-shortcut', {
              detail: {
                action: 'navigate-table',
                direction: event.key === 'ArrowUp' ? 'up' : 'down',
              },
            }),
          )
        }
      }
    }
    // Escape key
    if (event.key === 'Escape') {
      // First try to close help modal
      if (isHelpModalOpen.value) {
        event.preventDefault()
        hideHelp()
        return
      }
      // Then dispatch event for other modals
      window.dispatchEvent(new CustomEvent('keyboard-shortcut', { detail: { action: 'escape' } }))
    }
  }

  function registerShortcut(key, description, action, context = null) {
    shortcuts.value.push({ key, description, action, context })
  }

  function unregisterShortcut(key) {
    const index = shortcuts.value.findIndex((s) => s.key === key)
    if (index !== -1) {
      shortcuts.value.splice(index, 1)
    }
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeyDown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown)
  })

  return {
    shortcuts,
    isHelpModalOpen,
    showHelp,
    hideHelp,
    registerShortcut,
    unregisterShortcut,
  }
}
