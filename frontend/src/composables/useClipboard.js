/**
 * Clipboard Composable
 * Provides clipboard operations with fallback for unsupported browsers
 */

import { ref } from 'vue'

export function useClipboard() {
  const isSupported = ref(!!navigator.clipboard)
  const copied = ref(false)
  const error = ref(null)

  /**
   * Copy text to clipboard using Clipboard API with textarea fallback
   * @param {string} text - Text to copy
   * @returns {Promise<boolean>} - Success status
   */
  const copy = async (text) => {
    error.value = null

    try {
      // Primary method: Clipboard API
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
        copied.value = true
        setTimeout(() => (copied.value = false), 2000)
        return true
      }

      // Fallback method: Textarea copy
      return fallbackCopy(text)
    } catch (err) {
      console.warn('[Clipboard] Primary method failed, using fallback:', err)
      return fallbackCopy(text)
    }
  }

  /**
   * Fallback copy method using textarea element
   * @param {string} text - Text to copy
   * @returns {boolean} - Success status
   */
  const fallbackCopy = (text) => {
    try {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-999999px'
      textarea.style.top = '-999999px'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()

      const successful = document.execCommand('copy')
      document.body.removeChild(textarea)

      if (successful) {
        copied.value = true
        setTimeout(() => (copied.value = false), 2000)
        return true
      }

      error.value = 'Failed to copy to clipboard'
      return false
    } catch (err) {
      console.error('[Clipboard] Fallback method failed:', err)
      error.value = err.message
      return false
    }
  }

  /**
   * Reset copied state
   */
  const reset = () => {
    copied.value = false
    error.value = null
  }

  return {
    isSupported,
    copied,
    error,
    copy,
    reset,
  }
}
