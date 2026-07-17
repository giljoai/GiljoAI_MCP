<template>
  <div class="beat gj-anim">
    <div class="beat-eyebrow">05 · The destination</div>
    <h2 class="beat-title">This is where you're going.</h2>
    <p class="beat-sub">A workspace a few weeks in: missions running, memory compounding, everything on a surface.</p>

    <div class="beat-stage">
      <div class="dash-card">
        <div class="dash-header">
          <div class="dash-brand">
            <img src="/icons/Giljo_YW_Face.svg" alt="" class="dash-face" />
            <span class="dash-title">DASHBOARD</span>
          </div>
          <span class="sample-pill">SAMPLE WORKSPACE</span>
        </div>

        <div class="stat-grid">
          <div class="stat-box">
            <span class="stat-label">STATUS DISTRIBUTION</span>
            <span class="stat-value">14 <span class="stat-unit">projects</span></span>
            <div class="stat-bar">
              <span style="width: 78%;" class="seg seg--complete" />
              <span style="width: 14%;" class="seg seg--idle" />
              <span style="width: 8%;" class="seg seg--live" />
            </div>
          </div>
          <div class="stat-box">
            <span class="stat-label">PROJECT TYPES</span>
            <span class="stat-value">14 <span class="stat-unit">types</span></span>
            <div class="stat-bar">
              <span style="width: 40%;" class="seg seg--sky" />
              <span style="width: 28%;" class="seg seg--amber" />
              <span style="width: 18%;" class="seg seg--lavender" />
              <span style="width: 14%;" class="seg seg--coral" />
            </div>
          </div>
          <div class="stat-box">
            <span class="stat-label">AGENT ROLES</span>
            <span class="stat-value">38 <span class="stat-unit">spawned</span></span>
            <div class="stat-bar">
              <span style="width: 34%;" class="seg seg--sky" />
              <span style="width: 24%;" class="seg seg--lavender" />
              <span style="width: 22%;" class="seg seg--amber" />
              <span style="width: 20%;" class="seg seg--mint" />
            </div>
          </div>
        </div>

        <div class="projects-strip">
          <span class="stat-label">PROJECTS</span>
          <div class="project-row">
            <span class="serial-chip">0014</span>
            <span class="project-name">Harden auth and request boundaries</span>
            <span class="project-status">Completed</span>
          </div>
          <div class="project-row">
            <span class="serial-chip">0013</span>
            <span class="project-name">Make realtime delivery reliable and compact</span>
            <span class="project-status">Completed</span>
          </div>
        </div>

        <div class="bottom-grid">
          <div class="bottom-box">
            <span class="stat-label">360 MEMORIES</span>
            <span class="memory-line">Hardened auth boundaries — OAuth, API-key, CSRF… <span class="memory-status">COMPLETED</span></span>
            <span class="memory-line">Realtime delivery integrated with frontend resync… <span class="memory-status">COMPLETED</span></span>
          </div>
          <div class="bottom-box">
            <span class="stat-label">RECENT COMMITS</span>
            <span class="memory-line"><span class="commit-hash">0d11201e</span> fix: bind websocket commands to identity</span>
            <span class="memory-line"><span class="commit-hash">c577c740</span> merge: harden realtime recovery (#6)</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '../../../styles/design-tokens' as *;

@keyframes gjPulseSoft {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
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
}

.dash-card {
  width: 620px;
  background: $elevation-raised;
  border-radius: $border-radius-rounded;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.08);
}

.dash-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dash-face {
  height: 15px;
}

.dash-title {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9.5px;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
}

.sample-pill {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.05);
  padding: 3px 8px;
  border-radius: $border-radius-pill;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 12px 16px 0;
}

.stat-box {
  background: $color-background-primary;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 8.5px;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.stat-value {
  font-family: 'Outfit', $typography-font-primary;
  font-weight: 700;
  font-size: 17px;
  color: $color-text-primary;
}

.stat-unit {
  font-weight: 400;
  font-size: 10px;
  color: var(--text-muted);
}

.stat-bar {
  display: flex;
  height: 5px;
  border-radius: $border-radius-pill;
  overflow: hidden;
}

.seg { display: block; }
.seg--complete { background: $color-status-complete; }
.seg--idle { background: $color-status-handed-over; }
.seg--live {
  background: $color-agent-researcher;
  animation: gjPulseSoft 2s ease infinite;
}
.seg--sky { background: $color-agent-implementor; }
.seg--amber { background: $color-agent-tester; }
.seg--lavender { background: $color-agent-reviewer; }
.seg--coral { background: $color-agent-analyzer; }
.seg--mint { background: $color-agent-researcher; }

.projects-strip {
  padding: 10px 16px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.project-row {
  display: flex;
  align-items: center;
  gap: 9px;
  background: $color-background-primary;
  border-radius: 9px;
  padding: 8px 12px;
}

.serial-chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9.5px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 7px;
  border-radius: 5px;
}

.project-name {
  flex: 1;
  font-size: 11.5px;
  color: $color-text-primary;
}

.project-status {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9.5px;
  color: $color-status-complete;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 10px 16px 14px;
}

.bottom-box {
  background: $color-background-primary;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.memory-line {
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.memory-status {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 8.5px;
  color: $color-status-complete;
}

.commit-hash {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9px;
  color: $color-agent-implementor;
}
</style>
