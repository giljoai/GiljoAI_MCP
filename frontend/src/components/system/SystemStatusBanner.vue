<!--
  Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
  Licensed under the Elastic License 2.0.
  See LICENSE in the project root for terms.
  [CE] Community Edition.

  IMP-5037b: SystemStatusBanner is now a filtered view of bannerNotifications.
  Each of the three legacy sub-banners (pending_migrations, update_available,
  skills_drift) is rendered by iterating the notification rows emitted by the
  backend. There is no client-side status polling for banner VISIBILITY; the
  Notification row IS the source of truth for whether a banner should be shown.
-->
<template>
  <div v-if="visibleBanners.length > 0" class="system-status-banner">
    <div
      v-for="n in visibleBanners"
      :key="n.id"
      class="system-banner-alert"
      :class="`system-banner-alert--${n.severity}`"
      role="alert"
      data-testid="system-banner"
    >
      <div class="system-banner-alert__content">
        <v-icon class="system-banner-alert__icon" :icon="iconFor(n)" size="18" />
        <span class="system-banner-alert__text">{{ n.body || n.title }}</span>
      </div>

      <div class="system-banner-alert__actions">
        <button
          v-if="hasCta(n)"
          data-testid="banner-cta-btn"
          class="system-banner-btn system-banner-btn--cta"
          @click="goTo(n)"
        >
          {{ n.cta_label || 'Go to settings' }}
        </button>

        <button
          v-if="n.dismissible"
          data-testid="banner-dismiss-btn"
          class="system-banner-btn system-banner-btn--dismiss"
          aria-label="Dismiss notification"
          @click="dismiss(n)"
        >
          <v-icon icon="mdi-close" size="16" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notifications'
import { useUserStore } from '@/stores/user'
import configService from '@/services/configService'
import { isSaasModeValue } from '@/composables/useGiljoMode'

const router = useRouter()
const notifStore = useNotificationStore()
const userStore = useUserStore()

/** CE system notification types handled by this banner. */
const CE_SYSTEM_TYPES = new Set([
  'system.pending_migrations',
  'system.update_available',
  'system.skills_drift',
])

/**
 * BE-6031c: SaaS defense-in-depth.
 * update_available and pending_migrations are CE self-host concepts; the
 * authoritative backend gate already suppresses them in SaaS mode.  This
 * computed provides a secondary render-layer guard so the banner never
 * displays those types even if a stale notification row survives a mode
 * transition.  skills_drift is retained: SaaS operators still need to know
 * when skills are out of sync.
 */
const giljoMode = ref('ce')
onMounted(async () => {
  try {
    await configService.fetchConfig()
    giljoMode.value = configService.getGiljoMode()
  } catch {
    giljoMode.value = 'ce'
  }
})

const ALLOWED_TYPES = computed(() => {
  if (isSaasModeValue(giljoMode.value)) {
    return new Set(['system.skills_drift'])
  }
  return CE_SYSTEM_TYPES
})

/** Defense-in-depth role guard. Server already enforces this; we guard render too. */
function userHasRole(roleFilter) {
  if (!roleFilter) return true
  const role = userStore.currentUser?.role?.toLowerCase() ?? ''
  return role === roleFilter.toLowerCase()
}

/** Icon mapping by notification type (fallback: severity-based). */
function iconFor(n) {
  if (n.type === 'system.pending_migrations') return 'mdi-database-alert'
  if (n.type === 'system.update_available') return 'mdi-download'
  if (n.type === 'system.skills_drift') return 'mdi-puzzle-outline'
  if (n.severity === 'warning' || n.severity === 'critical') return 'mdi-alert-outline'
  if (n.severity === 'error') return 'mdi-alert-circle-outline'
  return 'mdi-information-outline'
}

/** Filter bannerNotifications down to allowed types visible to this user. */
const visibleBanners = computed(() =>
  notifStore.bannerNotifications.filter(
    (n) => ALLOWED_TYPES.value.has(n.type) && userHasRole(n.role_filter),
  ),
)

/** GitHub releases landing page; fallback when a row carries no release_url. */
const RELEASES_URL = 'https://github.com/giljoai/GiljoAI_MCP/releases'

/**
 * External CTA target for "update available" banners. Self-host upgrades happen
 * in the user's terminal (git pull + restart, or re-run the installer), so the
 * button links out to GitHub releases rather than deep-linking in-app.
 * Returns null for every other banner type (those use an in-app cta_route).
 */
function externalHref(n) {
  if (n.type === 'system.update_available') {
    return n.payload?.release_url || RELEASES_URL
  }
  return null
}

/** A banner shows a CTA button if it has an in-app route OR an external link. */
function hasCta(n) {
  return Boolean(n.cta_route) || Boolean(externalHref(n))
}

function goTo(n) {
  const href = externalHref(n)
  if (href) {
    window.open(href, '_blank', 'noopener')
    return
  }
  if (n.cta_route) {
    router.push({ name: n.cta_route })
  }
}

function dismiss(n) {
  notifStore.markDismissed(n.id)
}
</script>

<style scoped lang="scss">
@use '@/styles/banner-unified' as banner;

.system-status-banner {
  position: sticky;
  top: 0;
  z-index: 100;
}

.system-banner-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 16px;
  font-size: 13px;
  border-radius: 0;
  // FE-6012: tint-over-surface fill (matches avatar-menu account-status notice exactly)
  background: var(--banner-bg);
  --smooth-border-color: var(--banner-border);

  &__content {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 0;
  }

  &__icon {
    flex-shrink: 0;
    color: var(--color-accent-primary);
  }

  &__text {
    // Light text on the translucent tint over the dark app surface → high contrast.
    color: var(--color-text-primary);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }
}

.system-banner-btn {
  border: none;
  cursor: pointer;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  transition: opacity 0.15s ease;
  line-height: 1;

  &:hover {
    opacity: 0.85;
  }

  &:focus-visible {
    outline: 2px solid var(--color-accent-primary);
    outline-offset: 2px;
  }

  &--cta {
    background-color: var(--color-accent-primary);
    color: var(--badge-text);
    padding: 5px 12px;
  }

  &--dismiss {
    background: transparent;
    color: rgba(255, 255, 255, 0.7);
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
