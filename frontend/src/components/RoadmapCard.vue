<template>
  <div class="rm-card smooth-border">
    <!-- FE-6170 rank rail order: [grip] [#] [tick] (divider provided by box-shadow on rm-rank).
         Previous order was [tick] [in-chain-pill] [grip] [#]; ticket moved tick to after the
         number so the drag affordance is at the far left edge and the tick is closer to the body. -->
    <div class="rm-rank">
      <!-- Drag handle: vuedraggable (SortableJS) scopes the drag to this grip
           via its `handle: '.rm-grip'` option, so the action buttons stay
           clickable. FE-6022c: terminal-state items are NOT reorderable — they
           render a locked handle WITHOUT the .rm-grip class so SortableJS can't
           grab them. No native draggable attr / drag emits needed. -->
      <div
        v-if="!isTerminal"
        class="rm-grip"
        role="button"
        :aria-label="`Drag to reorder ${displayTitle}`"
        title="Drag to reorder"
      ></div>
      <div
        v-else
        class="rm-grip-locked"
        aria-hidden="true"
        title="Locked — this item has reached a terminal state"
      >
        <v-icon icon="mdi-lock-outline" size="14" />
      </div>
      <span class="rm-num">{{ rank }}</span>
      <!-- FE-6176: the rank-rail selection checkbox was REMOVED. Selection now
           happens only in link mode, via the checkbox that replaces the Activate
           button in the action rail (see below) — matching the /projects "Linked"
           column model. The rank rail is just the grip + number now. -->
    </div>

    <!-- Body -->
    <div class="rm-body">
      <div class="rm-top">
        <span v-if="aliasShown" class="rm-alias" :style="aliasStyle">{{ item.taxonomy_alias }}</span>
        <span class="rm-title">{{ displayTitle }}</span>
      </div>

      <div class="rm-meta">
        <span class="rm-badge" :style="typeBadgeStyle">{{ typeLabel }}</span>
        <span v-if="statusBadge" class="rm-badge" :style="statusBadge.style">
          <v-icon :icon="statusBadge.icon" size="13" class="rm-badge-icon" />{{ statusBadge.label }}
        </span>
        <!-- Risk + complexity carry a short tooltip (same v-tooltip pattern the
             action buttons use) so the low/med/high + light/med/heavy scales are
             self-explaining. -->
        <v-tooltip
          v-if="riskBadge"
          location="top"
          text="Chance this work causes problems or breaks things — low / med / high."
        >
          <template #activator="{ props: tipProps }">
            <span v-bind="tipProps" class="rm-badge" :style="riskBadge.style">
              <v-icon :icon="riskBadge.icon" size="13" class="rm-badge-icon" />{{ riskBadge.label }}
            </span>
          </template>
        </v-tooltip>
        <v-tooltip
          v-if="complexityBadge"
          location="top"
          text="Roughly how much effort to build — light / med / heavy."
        >
          <template #activator="{ props: tipProps }">
            <span v-bind="tipProps" class="rm-badge" :style="complexityBadge.style">
              <v-icon :icon="complexityBadge.icon" size="13" class="rm-badge-icon" />{{ complexityBadge.label }}
            </span>
          </template>
        </v-tooltip>
      </div>

      <!-- Blocked dependency row (FE-6022d): its own row under the badge row.
           Red label, NO icon, with the agent's free-text dependency note. Only
           shown when the agent flagged this item blocked via update_roadmap_metadata. -->
      <div v-if="item.blocked" class="rm-blocked-row">
        <span class="rm-blocked-label">Blocked</span>
        <span v-if="item.blocked_reason" class="rm-blocked-reason">reason: {{ item.blocked_reason }}</span>
      </div>
    </div>

    <!-- Action rail (type-dependent) -->
    <div class="rm-actions">
      <!-- FE-6176: link mode — a checkbox replaces the Activate button for every
           runnable project (inactive, incl. in-chain). Force-ticked when already
           in a chain run (selected || inChain); disabled when the run is locked
           (Staged tier). Untick at Editing tier calls removeMember via the parent.
           This mirrors the /projects "Linked" column exactly. -->
      <!-- FE-6180: /roadmap is plan+launch only. Once linked (any active-chain member),
           the tickbox greys and clicking it navigates to /projects (management lives there);
           reset/modify is NOT done on /roadmap. Non-chain rows tick freely. -->
      <v-tooltip
        v-if="linkMode && isProject && !isTerminal && !isActivated"
        :disabled="!inChain"
        text="Linked in a chain — reset or modify on the Projects page"
        location="top"
      >
        <template #activator="{ props: ttProps }">
          <span v-bind="ttProps" class="rm-link-wrap" @click.stop="inChain && $emit('open-chain', item)">
            <v-checkbox-btn
              :model-value="selected || inChain"
              :disabled="inChain"
              :style="inChain ? 'pointer-events: none' : undefined"
              density="compact"
              hide-details
              class="rm-link-mode-check"
              :aria-label="`Link ${displayTitle} to the chain`"
              :data-testid="`roadmap-select-checkbox-${item.id || item.project_id}`"
              @click.stop
              @update:model-value="$emit('toggle-select', item)"
            />
          </span>
        </template>
      </v-tooltip>
      <!-- FE-6170: outside link mode, a chain member shows an "In chain" badge in
           place of the Activate button so membership is visible in context. -->
      <span
        v-else-if="isProject && inChain"
        class="rm-badge rm-in-chain-pill"
        data-testid="roadmap-in-chain-pill"
      >
        <span class="mdi mdi-link-variant" aria-hidden="true" style="font-size: 11px; margin-right: 3px;" />
        In chain
      </span>
      <!-- Activated projects toggle to a Deactivate action (returns the project
           to inactive — same effect as the Projects-list hamburger "Deactivate").
           Only the live `active` status is reversible here; the truly terminal
           statuses (completed / cancelled / deleted) keep Activate disabled. -->
      <v-btn
        v-else-if="isProject && isActivated"
        color="warning"
        variant="tonal"
        size="small"
        prepend-icon="mdi-rocket-launch-outline"
        class="rm-primary-btn"
        :aria-label="`Deactivate project ${displayTitle}`"
        @click="$emit('deactivate', item)"
      >
        Deactivate
      </v-btn>
      <v-btn
        v-else-if="isProject"
        color="primary"
        variant="flat"
        size="small"
        prepend-icon="mdi-rocket-launch"
        class="rm-primary-btn"
        :class="{ 'rm-primary-btn--election-faded': electionActive }"
        :disabled="isTerminal || electionActive"
        :title="electionActive ? 'Projects are elected — use Run Sequential to launch them' : ''"
        :aria-label="`Activate project ${displayTitle}`"
        @click="$emit('activate', item)"
      >
        Activate
      </v-btn>
      <v-btn
        v-else
        variant="tonal"
        size="small"
        color="info"
        prepend-icon="mdi-folder-arrow-up-outline"
        class="rm-primary-btn rm-convert-btn"
        :disabled="isTerminal"
        :aria-label="`Convert task ${displayTitle} to a project`"
        @click="$emit('convert', item)"
      >
        Convert to Project
      </v-btn>

      <div class="rm-act-row">
        <v-tooltip location="top" :text="isProject ? 'Open project' : 'Open task'">
          <template #activator="{ props: tipProps }">
            <v-btn
              v-bind="tipProps"
              icon="mdi-eye-outline"
              variant="text"
              size="x-small"
              :aria-label="isProject ? 'Open project' : 'Open task'"
              @click="$emit('open', item)"
            />
          </template>
        </v-tooltip>
        <v-tooltip location="top" text="Demote to bottom">
          <template #activator="{ props: tipProps }">
            <v-btn
              v-bind="tipProps"
              icon="mdi-arrow-collapse-down"
              variant="text"
              size="x-small"
              aria-label="Demote to bottom"
              @click="$emit('demote', item)"
            />
          </template>
        </v-tooltip>
        <!-- Remove from roadmap (FE-6022c-polish). Deletes ONLY the roadmap_item
             server-side — the underlying project/task is untouched — and it's
             reversible via a Refresh re-rank, so no confirm dialog. Replaced the
             redundant 3-dot menu (Open + Demote already have icon buttons). -->
        <v-tooltip location="top" text="Remove from roadmap">
          <template #activator="{ props: tipProps }">
            <v-btn
              v-bind="tipProps"
              icon="mdi-close"
              variant="text"
              size="x-small"
              class="rm-remove-btn"
              :aria-label="`Remove ${displayTitle} from the roadmap`"
              @click="$emit('remove', item)"
            />
          </template>
        </v-tooltip>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * RoadmapCard — one ranked item (project or task) on the Roadmap pane.
 *
 * Presentational: it renders the contract item (FE-6022a GET /roadmap) and
 * emits intents; the parent (RoadmapView) owns fetch, reorder persistence,
 * and dialog wiring.
 *
 * Color discipline (CLAUDE.md "NO hardcoded hex"): badge colors come from the
 * sanctioned JS color sources — getAgentColor() and colorTokens — fed through
 * hexToRgba(hex, 0.15) to build the tinted-badge style (rgba background + full
 * color text + 8px radius), exactly the pattern StatusBadge / getAgentBadgeStyle
 * use. The grip/rail chrome uses CSS custom properties (--color-border etc).
 */
import { computed } from 'vue'
import { hexToRgba } from '@/utils/colorUtils'
import { getAgentColor } from '@/config/agentColors'
import { COLOR_BRAND, COLOR_COMPLETE, TEXT_MUTED } from '@/config/colorTokens'
import { taxonomyBadgeStyle, DEFAULT_PROJECT_TYPE_COLOR } from '@/utils/taxonomyBadge'

const props = defineProps({
  // A single roadmap item from the GET /api/v1/roadmap contract.
  item: {
    type: Object,
    required: true,
  },
  // Display position (1-based). NOT the raw `sort_order` int — see RoadmapView:
  // sort_order is an arbitrary ascending sort key; rank is the visible position.
  rank: {
    type: Number,
    required: true,
  },
  // FE-6131e: whether this card is checked for a sequential run.
  selected: {
    type: Boolean,
    default: false,
  },
  // FE-6165a: true while ANY project is elected for a sequential run. Fades +
  // disables this card's Activate button so the only launch affordance is Run
  // Sequential (you don't solo-activate a project mid-election).
  electionActive: {
    type: Boolean,
    default: false,
  },
  // FE-6165f: true when this project is a member of an active (in-flight)
  // sequential run. Checkbox is force-ticked + locked (disabled), and an
  // "In chain" pill is rendered so the user knows why.
  inChain: {
    type: Boolean,
    default: false,
  },
  // FE-6171b: true when the run containing this project is in the Staged (locked) tier.
  // Drives tickbox disable: Editing tier (inChain=true, lockedInChain=false) keeps the
  // tickbox enabled for removeMember. Staged/Ultralocked disables it.
  lockedInChain: {
    type: Boolean,
    default: false,
  },
  // FE-6176: link/chain mode — checkbox moves from rm-rank to the action rail,
  // replacing the Activate button for inactive non-terminal projects.
  linkMode: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['activate', 'deactivate', 'convert', 'open', 'demote', 'remove', 'toggle-select', 'open-chain'])

const isProject = computed(() => props.item.item_type === 'project')

// A project still in the live `active` status — the Activate button toggles to
// Deactivate (reversible back to inactive). Distinct from the truly terminal
// statuses (completed / cancelled / deleted) which stay disabled.
const isActivated = computed(() => isProject.value && props.item.status === 'active')

// taxonomy_alias can be '' in the contract — hide the chip when empty.
const aliasShown = computed(() => !!(props.item.taxonomy_alias && props.item.taxonomy_alias.trim()))

const displayTitle = computed(() => props.item.title || '(untitled)')

// Taxonomy alias chip: tinted with the item's per-taxonomy color (same helper +
// 15% tint the ProjectsTable / TasksTable serial badges use), so the roadmap
// matches the lists instead of a single static color. Falls back to the default
// type color when GET /roadmap reports no taxonomy_color.
const aliasStyle = computed(() =>
  taxonomyBadgeStyle(props.item.taxonomy_color || DEFAULT_PROJECT_TYPE_COLOR),
)

// --- Tinted badge styling (mirrors StatusBadge anatomy) ---
function tintedStyle(hex) {
  return {
    backgroundColor: hexToRgba(hex, 0.15),
    color: hex,
    borderRadius: '8px',
  }
}

const typeLabel = computed(() => (isProject.value ? 'PROJECT' : 'TASK'))
const typeBadgeStyle = computed(() =>
  tintedStyle(isProject.value ? COLOR_BRAND : getAgentColor('implementer').hex),
)

// Risk stoplight: low=success green, med=tester amber, high=analyzer red.
const RISK_MAP = {
  low: { label: 'LOW RISK', icon: 'mdi-shield-check', hex: COLOR_COMPLETE },
  med: { label: 'MED RISK', icon: 'mdi-shield-alert', hex: getAgentColor('tester').hex },
  high: { label: 'HIGH RISK', icon: 'mdi-shield-off', hex: getAgentColor('analyzer').hex },
}
const riskBadge = computed(() => {
  const r = RISK_MAP[props.item.risk]
  if (!r) return null
  return { label: r.label, icon: r.icon, style: tintedStyle(r.hex) }
})

// Terminal-state badge (FE-6022c): a project that has since been activated /
// completed / cancelled / deleted, or a task that's completed / cancelled,
// stays on the roadmap (GET surfaces it) but is no longer actionable — badge it
// and disable its actions. Inactive projects + pending/in-progress tasks get no
// badge (the normal, actionable state). Colors reuse the WCAG-AA palette already
// proven on this card — no new color tokens.
const PROJECT_STATUS_BADGE = {
  active: { label: 'ACTIVATED', icon: 'mdi-rocket-launch-outline', hex: COLOR_BRAND },
  completed: { label: 'COMPLETED', icon: 'mdi-check-circle-outline', hex: COLOR_COMPLETE },
  cancelled: { label: 'CANCELLED', icon: 'mdi-cancel', hex: TEXT_MUTED },
  terminated: { label: 'CANCELLED', icon: 'mdi-cancel', hex: TEXT_MUTED },
  deleted: { label: 'DELETED', icon: 'mdi-delete-outline', hex: getAgentColor('analyzer').hex },
}
const TASK_STATUS_BADGE = {
  completed: { label: 'COMPLETED', icon: 'mdi-check-circle-outline', hex: COLOR_COMPLETE },
  cancelled: { label: 'CANCELLED', icon: 'mdi-cancel', hex: TEXT_MUTED },
}
const statusBadge = computed(() => {
  const map = isProject.value ? PROJECT_STATUS_BADGE : TASK_STATUS_BADGE
  const s = map[props.item.status]
  if (!s) return null
  return { label: s.label, icon: s.icon, style: tintedStyle(s.hex) }
})
const isTerminal = computed(() => statusBadge.value !== null)

// Complexity: light/med/heavy — neutral muted tint.
const COMPLEXITY_MAP = {
  light: { label: 'LIGHT', icon: 'mdi-feather' },
  med: { label: 'MED', icon: 'mdi-weight' },
  heavy: { label: 'HEAVY', icon: 'mdi-weight' },
}
const complexityBadge = computed(() => {
  const c = COMPLEXITY_MAP[props.item.complexity]
  if (!c) return null
  return { label: c.label, icon: c.icon, style: tintedStyle(TEXT_MUTED) }
})

// Exposed for unit tests.
defineExpose({ isProject, isActivated, aliasShown, aliasStyle, typeLabel, riskBadge, complexityBadge, statusBadge, isTerminal, linkMode: computed(() => props.linkMode) })
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;

.rm-card {
  display: flex;
  align-items: stretch;
  background: rgb(var(--v-theme-surface));
  border-radius: $border-radius-md;
  overflow: hidden;
  transition:
    transform $transition-normal ease,
    box-shadow $transition-normal ease;
}

.rm-card:hover {
  transform: translateY(-2px);
}

/* Rank rail: dotted grip + sort_order number */
.rm-rank {
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding-right: 16px;
  box-shadow: inset -1px 0 0 var(--smooth-border-color, rgba(255, 255, 255, 0.06));
}

.rm-grip {
  align-self: stretch;
  width: 22px;
  cursor: grab;
  /* fine dotted pattern in the darker border-blue; brightens on hover */
  background:
    radial-gradient(var(--color-border) 0.9px, transparent 1.1px) 2px 2px / 4px 4px;
  transition: background $transition-fast ease;
}

.rm-grip:hover {
  background:
    radial-gradient(var(--color-agent-implementer) 0.9px, transparent 1.1px) 2px 2px /
    4px 4px;
}

.rm-grip:active {
  cursor: grabbing;
}

/* Terminal items are not reorderable — a muted, non-draggable lock replaces the
   dotted grip (no .rm-grip class, so SortableJS's handle selector can't grab it). */
.rm-grip-locked {
  align-self: stretch;
  width: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  color: var(--text-muted);
  opacity: 0.6;
}

.rm-num {
  font-family: ui-monospace, 'Cascadia Code', 'Roboto Mono', monospace;
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--color-accent-primary);
}

/* FE-6176: link-mode checkbox in the action rail (replaces Activate button). */
.rm-link-mode-check {
  align-self: center;
  margin: 0 auto;
}

/* FE-6165f: "In chain" locked-checkbox pill (tinted badge — implementer blue). */
.rm-in-chain-pill {
  background-color: rgba(109, 179, 228, 0.15); /* var(--color-agent-implementer) at 15% */
  color: var(--color-agent-implementer);
}

/* Body */
.rm-body {
  flex: 1;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.rm-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.rm-alias {
  /* color + background come from the per-taxonomy tinted inline style
     (taxonomyBadgeStyle), matching the project/task list serial badges. */
  font-family: ui-monospace, 'Cascadia Code', 'Roboto Mono', monospace;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: $border-radius-sharp;
}

/* Blocked dependency row — red label (no icon) + free-text reason. */
.rm-blocked-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.rm-blocked-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: $color-status-error;
}

.rm-blocked-reason {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.rm-title {
  font-size: 1rem;
  font-weight: 600;
}

.rm-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}

.rm-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: $border-radius-default;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.rm-badge-icon {
  margin-right: 1px;
}

/* Action rail */
.rm-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 8px;
  padding: 12px 14px;
  width: 188px;
  flex-shrink: 0;
  box-shadow: inset 1px 0 0 var(--smooth-border-color, rgba(255, 255, 255, 0.06));
}

.rm-primary-btn {
  text-transform: none;
  letter-spacing: 0;
  font-weight: 700;
}

/* FE-6165a: fade the per-card Activate while a sequential election is active. */
.rm-primary-btn--election-faded {
  opacity: 0.3;
}

.rm-act-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

@media (max-width: 760px) {
  .rm-card {
    flex-wrap: wrap;
  }
  .rm-actions {
    width: 100%;
    flex-direction: row;
    box-shadow: inset 0 1px 0 var(--smooth-border-color, rgba(255, 255, 255, 0.06));
  }
}
</style>
