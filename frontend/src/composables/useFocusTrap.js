import { onMounted, onUnmounted, nextTick } from 'vue'

export function useFocusTrap(containerRef, options = {}) {
  const {
    initialFocus = null,
    returnFocus = true,
    escapeDeactivates = true,
    clickOutsideDeactivates = false,
  } = options

  let previouslyFocusedElement = null
  let isActive = false

  const focusableSelectors = [
    'a[href]:not([disabled])',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable]',
    'audio[controls]',
    'video[controls]',
  ].join(',')

  function getFocusableElements() {
    if (!containerRef.value) {
      return []
    }
    return Array.from(containerRef.value.querySelectorAll(focusableSelectors)).filter(
      (el) => el.offsetWidth > 0 && el.offsetHeight > 0,
    ) // Visible elements only
  }

  function handleKeyDown(event) {
    if (!isActive || !containerRef.value) {
      return
    }

    // Handle Escape key
    if (escapeDeactivates && event.key === 'Escape') {
      deactivate()
      return
    }

    // Handle Tab key for focus trap
    if (event.key === 'Tab') {
      const focusableElements = getFocusableElements()

      if (focusableElements.length === 0) {
        event.preventDefault()
        return
      }

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]
      const activeElement = document.activeElement

      // Shift+Tab on first element -> focus last
      if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
        return
      }

      // Tab on last element -> focus first
      if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
        return
      }

      // Check if focus is outside trap
      if (!containerRef.value.contains(activeElement)) {
        event.preventDefault()
        if (event.shiftKey) {
          lastElement.focus()
        } else {
          firstElement.focus()
        }
      }
    }
  }

  function handleClickOutside(event) {
    if (!isActive || !containerRef.value || !clickOutsideDeactivates) {
      return
    }

    if (!containerRef.value.contains(event.target)) {
      deactivate()
    }
  }

  function activate() {
    if (isActive) {
      return
    }

    isActive = true
    previouslyFocusedElement = document.activeElement

    // Add event listeners
    document.addEventListener('keydown', handleKeyDown, true)
    if (clickOutsideDeactivates) {
      document.addEventListener('mousedown', handleClickOutside, true)
      document.addEventListener('touchstart', handleClickOutside, true)
    }

    // Set initial focus
    nextTick(() => {
      if (initialFocus) {
        const element =
          typeof initialFocus === 'string'
            ? containerRef.value?.querySelector(initialFocus)
            : initialFocus

        if (element) {
          element.focus()
          return
        }
      }

      // Default to first focusable element
      const focusableElements = getFocusableElements()
      if (focusableElements.length > 0) {
        focusableElements[0].focus()
      }
    })
  }

  function deactivate() {
    if (!isActive) {
      return
    }

    isActive = false

    // Remove event listeners
    document.removeEventListener('keydown', handleKeyDown, true)
    document.removeEventListener('mousedown', handleClickOutside, true)
    document.removeEventListener('touchstart', handleClickOutside, true)

    // Return focus to previously focused element
    if (returnFocus && previouslyFocusedElement) {
      previouslyFocusedElement.focus()
    }
  }

  function pause() {
    if (!isActive) {
      return
    }
    document.removeEventListener('keydown', handleKeyDown, true)
  }

  function unpause() {
    if (!isActive) {
      return
    }
    document.addEventListener('keydown', handleKeyDown, true)
  }

  onMounted(() => {
    if (containerRef.value) {
      activate()
    }
  })

  onUnmounted(() => {
    deactivate()
  })

  return {
    activate,
    deactivate,
    pause,
    unpause,
  }
}
