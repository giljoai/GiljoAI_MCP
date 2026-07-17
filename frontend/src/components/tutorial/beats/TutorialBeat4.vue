<template>
  <div class="beat gj-anim">
    <div class="beat-eyebrow">04 · 360 Memory</div>
    <h2 class="beat-title">Every project makes the next one smarter.</h2>
    <p class="beat-sub">
      When a mission closes, its decisions are written to memory. The next project inherits them.
      <router-link class="beat-readmore" :to="{ path: '/guide', hash: '#360-memory-and-follow-up-work' }" target="_blank" rel="noopener">Read more →</router-link>
    </p>

    <div class="beat-stage">
      <div class="memory-col">
        <div class="project-done">Project A · Complete.</div>
        <div class="stream-lane">
          <span class="stream-dot" style="animation-delay: 0s;" />
          <span class="stream-dot" style="animation-delay: 0.6s;" />
          <span class="stream-dot" style="animation-delay: 1.2s;" />
        </div>
        <div class="memory-node">
          <v-icon size="22" class="memory-icon">mdi-brain</v-icon>
          <div class="memory-text">
            <span class="memory-name">360 Memory</span>
            <span class="memory-tag">decisions · detours · why</span>
          </div>
        </div>
      </div>

      <v-icon size="26" class="arrow-icon">mdi-arrow-right</v-icon>

      <div class="briefed-card">
        <span class="briefed-title">Project B · starts briefed</span>
        <div class="briefed-chips">
          <span class="chip" style="animation-delay: 1.7s;">auth pattern</span>
          <span class="chip" style="animation-delay: 2s;">lib choices</span>
          <span class="chip" style="animation-delay: 2.3s;">edge cases</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '../../../styles/design-tokens' as *;

@keyframes gjStreamDown {
  0% { transform: translateY(0); opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { transform: translateY(90px); opacity: 0; }
}

@keyframes gjRise {
  0% { opacity: 0; transform: translateY(16px); }
  100% { opacity: 1; transform: translateY(0); }
}

@keyframes gjChipIn {
  0% { opacity: 0; transform: translateY(10px) scale(0.95); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}

.beat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.beat-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.2em;
  color: $color-brand-yellow;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.beat-title {
  margin: 0 0 6px;
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 700;
  font-size: 28px;
  letter-spacing: -0.02em;
  color: $color-text-primary;
}

.beat-sub {
  margin: 0 0 8px;
  font-size: 14.5px;
  line-height: 1.55;
  color: var(--text-secondary);
}

.beat-stage {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 36px;
}

.memory-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.project-done {
  background: $elevation-raised;
  border-radius: $border-radius-md;
  box-shadow: inset 0 0 0 1px rgba($color-agent-researcher, 0.4);
  padding: 13px 18px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: $color-agent-researcher;
}

.stream-lane {
  position: relative;
  width: 2px;
  height: 90px;
}

.stream-dot {
  position: absolute;
  left: -3px;
  width: 8px;
  height: 8px;
  border-radius: $border-radius-pill;
  background: $color-agent-researcher;
  animation: gjStreamDown 1.8s linear infinite;
}

.memory-node {
  display: flex;
  align-items: center;
  gap: 9px;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.35);
  padding: 15px 22px;
}

.memory-icon {
  color: $color-brand-yellow;
}

.memory-text {
  display: flex;
  flex-direction: column;
}

.memory-name {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  font-size: 14px;
  color: $color-text-primary;
}

.memory-tag {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
}

.arrow-icon {
  color: var(--text-muted);
}

.briefed-card {
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: gjRise 0.8s cubic-bezier(0.16, 1, 0.3, 1) 1.2s both;
}

.briefed-title {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 600;
  font-size: 14px;
  color: $color-text-primary;
}

.briefed-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  max-width: 220px;
}

.chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  color: $color-agent-researcher;
  background: rgba($color-agent-researcher, 0.12);
  padding: 4px 9px;
  border-radius: $border-radius-pill;
  animation: gjChipIn 0.4s ease both;
}
</style>
