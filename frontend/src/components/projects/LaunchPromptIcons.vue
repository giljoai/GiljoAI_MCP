<template>
  <div class="launch-prompt-icons">
    <div
      v-for="(tool, key) in tools"
      :key="key"
      :class="['launch-prompt-icon', `launch-prompt-icon--${key}`]"
      :style="{ backgroundColor: tool.color }"
      role="button"
      tabindex="0"
      :aria-label="`Copy ${tool.name} command to clipboard`"
      :title="`Click to copy: ${tool.command}`"
      @click="copyCommand(tool)"
      @keydown.enter="copyCommand(tool)"
      @keydown.space.prevent="copyCommand(tool)"
    >
      <v-icon :icon="tool.icon" size="16" />
      <span class="launch-prompt-icon__label">{{ tool.name }}</span>
    </div>

    <!-- Toast notification for copy feedback -->
    <v-snackbar v-model="showToast" :timeout="2000" color="success" location="bottom right">
      <div class="d-flex align-center gap-2">
        <v-icon icon="mdi-check-circle" />
        <span>{{ toastMessage }}</span>
      </div>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { LAUNCH_PROMPT_TOOLS } from '@/config/agentColors.js'

/**
 * LaunchPromptIcons Component
 *
 * Displays 2-3 square icons with rounded corners representing AI coding tools
 * (Claude Code, Codex CLI, Gemini CLI). Clicking an icon copies the MCP
 * integration command to clipboard and shows a toast notification.
 *
 * Features:
 * - Square icons with tool-specific colors (orange, purple, blue)
 * - Icon + label for each tool
 * - Click to copy command to clipboard
 * - Toast notification on successful copy
 * - Keyboard accessible (Enter/Space to activate)
 * - Hover effects for visual feedback
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 * @see frontend/src/config/agentColors.js
 */

/**
 * Tools configuration from centralized config
 */
const tools = computed(() => LAUNCH_PROMPT_TOOLS)

/**
 * Toast notification state
 */
const showToast = ref(false)
const toastMessage = ref('')

/**
 * Copy command to clipboard and show toast
 */
async function copyCommand(tool) {
  try {
    await navigator.clipboard.writeText(tool.command)
    toastMessage.value = `Copied: ${tool.command}`
    showToast.value = true
  } catch (error) {
    console.error('Failed to copy command:', error)
    // Fallback for browsers without clipboard API
    fallbackCopyCommand(tool.command)
  }
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopyCommand(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()

  try {
    document.execCommand('copy')
    toastMessage.value = `Copied: ${text}`
    showToast.value = true
  } catch (error) {
    console.error('Fallback copy failed:', error)
    toastMessage.value = 'Failed to copy command'
    showToast.value = true
  } finally {
    document.body.removeChild(textarea)
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/agent-colors.scss' as *;

.launch-prompt-icons {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.launch-prompt-icon {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);

  &:hover {
    transform: scale(1.05);
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.3);
  }

  &:active {
    transform: scale(0.98);
  }

  &:focus {
    outline: 2px solid var(--color-accent-primary);
    outline-offset: 2px;
  }

  &:focus:not(:focus-visible) {
    outline: none;
  }

  &__label {
    white-space: nowrap;
  }

  /* Tool-specific colors */
  &--claudeCode {
    background-color: var(--tool-claude-code);
    &:hover {
      filter: brightness(0.9);
    }
  }

  &--codex {
    background-color: var(--tool-codex);
    &:hover {
      filter: brightness(0.9);
    }
  }

  &--gemini {
    background-color: var(--tool-gemini);
    &:hover {
      filter: brightness(0.9);
    }
  }
}

/* Accessibility: High contrast mode */
@media (prefers-contrast: high) {
  .launch-prompt-icon {
    border: 2px solid white;
    font-weight: 700;
  }
}

/* Responsive: Touch-friendly on mobile */
@media (max-width: 600px) {
  .launch-prompt-icons {
    gap: 6px;
  }

  .launch-prompt-icon {
    padding: 10px 14px;
    font-size: 13px;
    min-height: 44px; /* Touch target minimum */

    &__label {
      font-size: 12px;
    }
  }
}

/* Responsive: Stack vertically on very small screens */
@media (max-width: 400px) {
  .launch-prompt-icons {
    flex-direction: column;
    align-items: stretch;
  }

  .launch-prompt-icon {
    justify-content: center;
    width: 100%;
  }
}

/* Animation for toast snackbar */
:deep(.v-snackbar__content) {
  padding: 12px 16px;
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .launch-prompt-icon {
    transition: none;

    &:hover {
      transform: none;
    }

    &:active {
      transform: none;
    }
  }
}
</style>
