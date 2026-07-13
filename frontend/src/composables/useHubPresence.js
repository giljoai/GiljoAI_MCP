/**
 * useHubPresence.js — FE-6054f
 *
 * Reactive `isHubPresent` = the Hub pane is the user's active focus.
 * True when ALL of:
 *   - document.visibilityState === 'visible'
 *   - document.hasFocus()
 *   - active route is /hub
 *
 * Listens to visibilitychange, window focus/blur, and watches the active route.
 * Cleans up on scope dispose.
 */
import { ref, computed, onScopeDispose, getCurrentScope } from 'vue'
import { useRoute } from 'vue-router'

export function useHubPresence() {
  const route = useRoute()

  // Track document visibility and focus as reactive refs so computed can depend on them
  const isVisible = ref(
    typeof document !== 'undefined' ? document.visibilityState === 'visible' : false,
  )
  const isFocused = ref(typeof document !== 'undefined' ? document.hasFocus() : false)

  function onVisibilityChange() {
    isVisible.value = document.visibilityState === 'visible'
  }

  function onFocus() {
    isFocused.value = true
  }

  function onBlur() {
    isFocused.value = false
  }

  if (typeof window !== 'undefined') {
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('focus', onFocus)
    window.addEventListener('blur', onBlur)

    if (getCurrentScope()) {
      onScopeDispose(() => {
        document.removeEventListener('visibilitychange', onVisibilityChange)
        window.removeEventListener('focus', onFocus)
        window.removeEventListener('blur', onBlur)
      })
    }
  }

  // route.path is reactive via Vue Router's reactive route object;
  // computed picks it up automatically when the route object is a reactive proxy.
  const isHubPresent = computed(
    () => isVisible.value && isFocused.value && route.path === '/hub',
  )

  return { isHubPresent }
}
