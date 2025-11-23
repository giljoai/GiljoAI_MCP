<template>
  <v-alert
    :type="type"
    :variant="variant"
    :closable="closable"
    :prominent="prominent"
    :density="density"
    :border="border"
    :color="color"
    v-bind="$attrs"
  >
    <!-- 
      Icon handling: Vuetify v-alert automatically shows icons for typed alerts.
      We do NOT add duplicate icons here - let Vuetify handle it.
      For custom icons, use the 'icon' prop on v-alert itself.
    -->
    <slot />
  </v-alert>
</template>

<script setup lang="ts">
/**
 * AppAlert - Application-wide alert component
 *
 * A wrapper around Vuetify's v-alert that enforces consistent styling
 * and prevents duplicate icon issues.
 *
 * Usage:
 *   <AppAlert type="info">Your message here</AppAlert>
 *   <AppAlert type="success" variant="tonal">Success message</AppAlert>
 *   <AppAlert type="warning" closable>Warning with close button</AppAlert>
 *
 * Props are passed through to v-alert, so all v-alert props work.
 */

interface Props {
  /** Alert type - automatically shows appropriate icon */
  type?: 'success' | 'info' | 'warning' | 'error'
  /** Visual variant */
  variant?: 'text' | 'flat' | 'elevated' | 'tonal' | 'outlined' | 'plain'
  /** Show close button */
  closable?: boolean
  /** Prominent styling */
  prominent?: boolean
  /** Density */
  density?: 'default' | 'comfortable' | 'compact'
  /** Border style */
  border?: boolean | 'top' | 'bottom' | 'start' | 'end'
  /** Custom color (overrides type color) */
  color?: string
}

withDefaults(defineProps<Props>(), {
  type: 'info',
  variant: 'tonal',
  closable: false,
  prominent: false,
  density: 'default',
  border: false,
})
</script>

<style scoped>
/* 
  No custom styles needed - rely on Vuetify's design system.
  If application-wide alert customization is needed, add it here.
*/
</style>
