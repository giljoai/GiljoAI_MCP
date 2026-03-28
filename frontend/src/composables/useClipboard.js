/**
 * Clipboard Composable
 * Provides clipboard operations with fallback for unsupported browsers.
 *
 * Works on all access modes: localhost, LAN IP, WAN IP, DNS, HTTP, HTTPS.
 * Uses navigator.clipboard.writeText on secure contexts, falls back to
 * synchronous document.execCommand('copy') on non-secure contexts.
 */

import { ref } from 'vue'

export function useClipboard() {
  const copied = ref(false)

  /**
   * Copy text to clipboard using Clipboard API with textarea fallback
   * @param {string} text - Text to copy
   * @returns {Promise<boolean>} - Success status
   */
  const copy = async (text) => {
    try {
      // Primary method: Clipboard API (secure contexts)
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
        copied.value = true
        setTimeout(() => (copied.value = false), 2000)
        return true
      }

      // Fallback method: Textarea copy (non-secure contexts)
      return fallbackCopy(text)
    } catch (err) {
      console.warn('[Clipboard] Primary method failed, using fallback:', err)
      return fallbackCopy(text)
    }
  }

  /**
   * Fallback copy method using textarea element and execCommand.
   * Works on all origins when called within a user gesture.
   * @param {string} text - Text to copy
   * @returns {boolean} - Success status
   */
  const fallbackCopy = (text) => {
    try {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      textarea.style.top = '-9999px'
      textarea.style.opacity = '0'

      // Append inside the active Vuetify dialog/overlay if one exists,
      // otherwise document.body. Vuetify dialogs with retain-focus steal
      // focus from elements outside the dialog, breaking execCommand('copy').
      const container = document.querySelector('.v-overlay--active .v-overlay__content') || document.body
      container.appendChild(textarea)
      textarea.focus()
      textarea.select()

      const successful = document.execCommand('copy')
      container.removeChild(textarea)

      if (successful) {
        copied.value = true
        setTimeout(() => (copied.value = false), 2000)
        return true
      }

      return false
    } catch (err) {
      console.error('[Clipboard] Fallback method failed:', err)
      return false
    }
  }

  return {
    copied,
    copy,
  }
}
