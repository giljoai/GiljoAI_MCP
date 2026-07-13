<template>
  <div class="intg-line intg-line--skills smooth-border">
    <div
      class="intg-line-icon intg-line-icon--link intg-line-icon--skills"
      title="Open the Skill Guide"
      @click="openSkillGuide"
    >
      <v-icon size="22">mdi-export</v-icon>
    </div>

    <div class="intg-line-main">
      <div class="intg-line-title-row">
        <span class="intg-line-title">Skills and Agents Export</span>
        <v-tooltip location="top" max-width="400">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="small" style="color: var(--text-muted)">mdi-help-circle-outline</v-icon>
          </template>
          <div>
            Once the MCP server is registered in your AI coding tool, run <code>giljo_setup</code> to install agents and skills in one step.
            <br /><br />
            After setup, re-run <code>giljo_setup</code> ("Agents only") to update agent templates,
            and use <code>/giljo</code> to create and read tasks and projects from your AI coding agent.
          </div>
        </v-tooltip>
      </div>
      <div class="intg-line-sub">Run setup inside your coding session</div>
    </div>

    <div class="intg-line-action">
      <div class="d-flex align-center" style="gap: 8px;">
        <span class="intg-line-sub" style="margin-top: 0">run</span>
        <span class="setup-cmd">giljo_setup</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

// In-app User Guide, scrolled to the "Installing Skills and Agents" section.
function openSkillGuide() {
  router.push({ name: 'UserGuide', hash: '#installing-skills-and-agents-giljo_setup' })
}
</script>

<style lang="scss" scoped>
@use '../styles/design-tokens' as *;
@use '../styles/intg-card';

/* Card accent token for the skills export line — brand-green nuance */
.intg-line--skills {
  --card-accent: #{$gradient-brand-end};
}

/* Bright GiljoAI brand-green nuance — icon and the fade behind it */
.intg-line-icon--skills {
  background: rgba(107, 207, 127, 0.14);
  color: $gradient-brand-end;
}

/* Framed command chip (mirrors design-system .cmd) */
.setup-cmd {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.22);
  color: var(--brand-yellow);
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  font-size: 0.8125rem;
  box-shadow: inset 0 0 0 1px rgba(255, 195, 0, 0.18);
}
</style>
