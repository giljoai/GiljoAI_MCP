<template>
  <div
    :class="['chat-head-badge', sizeClass, `chat-head-badge--${normalizedAgentType}`]"
    :style="{ backgroundColor: agentColor }"
    :title="tooltipText"
    role="img"
    :aria-label="ariaLabel"
  >
    {{ badgeId }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getAgentColor, getAgentBadgeId } from '@/config/agentColors.js'

/**
 * ChatHeadBadge Component
 *
 * Displays a circular badge with agent identification using the agent color system.
 * Used in message streams and agent communication displays.
 *
 * Features:
 * - Perfect circle with agent-specific color
 * - Two sizes: default (32px) and compact (24px)
 * - Badge ID displays: "Or", "Im", "I2", "I3" etc.
 * - 2px white border for visual separation
 * - White text, bold, centered
 * - Accessible with ARIA labels
 *
 * @see handovers/0077_launch_jobs_dual_tab_interface.md
 * @see frontend/src/config/agentColors.js
 */

const props = defineProps({
  /**
   * Agent type (orchestrator, analyzer, implementor, researcher, reviewer, tester)
   */
  agentDisplayName: {
    type: String,
    required: true,
    validator: (value) => {
      const validTypes = [
        // Canonical roles
        'orchestrator',
        'analyzer',
        'implementer',
        'documenter',
        'reviewer',
        'tester',
        // Legacy aliases kept for backward compatibility
        'implementor',
        'researcher',
      ]
      return validTypes.includes(value.toLowerCase())
    },
  },

  /**
   * Instance number for multiple agents of same type (1 = default)
   * Shows as "Im" for 1, "I2" for 2, "I3" for 3, etc.
   */
  instanceNumber: {
    type: Number,
    default: 1,
    validator: (value) => value >= 1 && value <= 99,
  },

  /**
   * Badge size: 'default' (32px), 'small' (28px), or 'compact' (24px)
   */
  size: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'small', 'compact'].includes(value),
  },
})

/**
 * Normalized agent type (lowercase for consistency)
 */
const normalizedAgentType = computed(() => {
  return props.agentDisplayName?.toLowerCase() || 'orchestrator'
})

/**
 * Get agent color configuration from centralized config
 */
const agentColorConfig = computed(() => {
  return getAgentColor(normalizedAgentType.value)
})

/**
 * Agent background color (hex)
 */
const agentColor = computed(() => {
  return agentColorConfig.value.hex
})

/**
 * Badge ID to display (e.g., "Or", "Im", "I2", "I3")
 */
const badgeId = computed(() => {
  return getAgentBadgeId(normalizedAgentType.value, props.instanceNumber)
})

/**
 * Size class for styling
 */
const sizeClass = computed(() => {
  if (props.size === 'compact') return 'chat-head-badge--compact'
  if (props.size === 'small') return 'chat-head-badge--small'
  return 'chat-head-badge--default'
})

/**
 * Tooltip text for hover
 */
const tooltipText = computed(() => {
  const config = agentColorConfig.value
  if (props.instanceNumber === 1) {
    return `${config.name} - ${config.description}`
  }
  return `${config.name} #${props.instanceNumber} - ${config.description}`
})

/**
 * Accessible ARIA label
 */
const ariaLabel = computed(() => {
  const config = agentColorConfig.value
  if (props.instanceNumber === 1) {
    return `${config.name} agent badge`
  }
  return `${config.name} agent instance ${props.instanceNumber} badge`
})
</script>

<style scoped lang="scss">
@use '@/styles/agent-colors.scss' as *;

.chat-head-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid white;
  color: white;
  font-weight: bold;
  flex-shrink: 0;
  user-select: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;

  &:hover {
    transform: scale(1.05);
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.3);
  }

  /* Default size: 32px */
  &--default {
    width: 32px;
    height: 32px;
    font-size: 13px;
  }

  /* Small size: 28px */
  &--small {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  /* Compact size: 24px */
  &--compact {
    width: 24px;
    height: 24px;
    font-size: 10px;
  }

  /* Agent-specific background colors */
  &--orchestrator {
    background-color: var(--agent-orchestrator-primary);
  }

  &--analyzer {
    background-color: var(--agent-analyzer-primary);
  }

  &--implementor {
    background-color: var(--agent-implementor-primary);
  }

  &--researcher {
    background-color: var(--agent-researcher-primary);
  }

  &--reviewer {
    background-color: var(--agent-reviewer-primary);
  }

  &--tester {
    background-color: var(--agent-tester-primary);
  }
}

/* Accessibility: High contrast mode support */
@media (prefers-contrast: high) {
  .chat-head-badge {
    border-width: 3px;
    font-weight: 900;
  }
}

/* Responsive: Ensure touch-friendly on mobile */
@media (max-width: 600px) {
  .chat-head-badge--default {
    width: 36px;
    height: 36px;
    font-size: 14px;
  }
}
</style>
