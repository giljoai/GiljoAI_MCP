<template>
  <div class="guide-layout">
    <!-- Mobile TOC chip row (< 768px) -->
    <div v-if="isMobile" class="guide-toc-mobile">
      <div class="guide-toc-mobile-inner">
        <button
          v-for="entry in tocEntries"
          :key="entry.anchor"
          class="guide-toc-chip"
          :class="{ 'guide-toc-chip--active': activeTocAnchor === entry.anchor }"
          @click="scrollToAnchor(entry.anchor)"
        >
          {{ entry.text }}
        </button>
      </div>
    </div>

    <!-- Desktop layout: sidebar + content -->
    <div class="guide-inner">
      <!-- Left sidebar TOC (>= 768px) -->
      <aside v-if="!isMobile" class="guide-sidebar smooth-border">
        <div class="guide-sidebar-title">Contents</div>
        <nav class="guide-toc" aria-label="Table of contents">
          <button
            v-for="entry in tocEntries"
            :key="entry.anchor"
            class="guide-toc-item"
            :class="{ 'guide-toc-item--active': activeTocAnchor === entry.anchor }"
            @click="scrollToAnchor(entry.anchor)"
          >
            {{ entry.text }}
          </button>
        </nav>
      </aside>

      <!-- Content area -->
      <main class="guide-content" ref="contentRef">
        <div
          class="guide-prose"
          v-html="renderedMarkdown"
        />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import overviewMd from '../../../docs/PRODUCT_OVERVIEW.md?raw'
import gettingStartedMd from '../../../docs/GETTING_STARTED.md?raw'
import userGuideMd from '../../../docs/USER_GUIDE.md?raw'

const route = useRoute()
const { width } = useDisplay()

const isMobile = computed(() => width.value < 768)
const contentRef = ref(null)
const activeTocAnchor = ref('')

// Build combined markdown: overview + getting started + user guide
const combinedMarkdown = computed(() => {
  const parts = [overviewMd]
  if (gettingStartedMd) {
    parts.push(gettingStartedMd)
  }
  parts.push(userGuideMd)
  return parts.join('\n\n---\n\n')
})

// Configure marked with anchor IDs on h2 headings via marked.use() (v5+ API)
marked.use({
  renderer: {
    heading({ text, depth }) {
      if (depth === 2) {
        const anchor = headingToAnchor(text)
        return `<h2 id="${anchor}">${text}</h2>\n`
      }
      return `<h${depth}>${text}</h${depth}>\n`
    },
  },
})

const renderedMarkdown = computed(() => {
  const html = marked.parse(combinedMarkdown.value)
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
})

// Build TOC from ## headings
const tocEntries = computed(() => {
  const entries = []
  const lines = combinedMarkdown.value.split('\n')
  for (const line of lines) {
    const match = line.match(/^## (.+)$/)
    if (match) {
      const text = match[1].trim()
      entries.push({ text, anchor: headingToAnchor(text) })
    }
  }
  return entries
})

function headingToAnchor(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function scrollToAnchor(anchor) {
  const el = document.getElementById(anchor)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// IntersectionObserver for active section tracking
let observer = null

function setupObserver() {
  if (observer) {
    observer.disconnect()
  }
  if (!contentRef.value) return

  const headings = contentRef.value.querySelectorAll('h2[id]')
  if (!headings.length) return

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeTocAnchor.value = entry.target.id
        }
      }
    },
    {
      root: null,
      rootMargin: '-10% 0px -75% 0px',
      threshold: 0,
    }
  )

  headings.forEach((h) => observer.observe(h))
}

// Handle anchor from URL (e.g. /guide#products)
function handleUrlAnchor() {
  const hash = route.hash?.replace('#', '')
  if (hash) {
    nextTick(() => {
      setTimeout(() => scrollToAnchor(hash), 100)
    })
  }
}

onMounted(async () => {
  await nextTick()
  setupObserver()
  handleUrlAnchor()
})

watch(renderedMarkdown, async () => {
  await nextTick()
  setupObserver()
})

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<style scoped lang="scss">
@use '../styles/design-tokens' as *;
@use '../styles/variables' as *;

.guide-layout {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: var(--color-bg-primary, #0e1c2d);
}

// ─── MOBILE TOC CHIP ROW ───

.guide-toc-mobile {
  overflow-x: auto;
  padding: 10px 16px;
  background: var(--color-bg-secondary, #12202e);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  position: sticky;
  top: 0;
  z-index: 10;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.guide-toc-mobile-inner {
  display: flex;
  gap: 8px;
  white-space: nowrap;
}

.guide-toc-chip {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.8rem;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-muted, #8895a8);
  transition: color 0.15s ease, background 0.15s ease;
  white-space: nowrap;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);

  &:hover {
    color: $yellow;
    background: rgba($yellow, 0.08);
  }

  &--active {
    color: $yellow;
    background: rgba($yellow, 0.1);
    box-shadow: inset 0 0 0 1px rgba($yellow, 0.3);
  }
}

// ─── DESKTOP TWO-COLUMN LAYOUT ───

.guide-inner {
  display: flex;
  flex: 1;
  min-height: 0;
}

// ─── SIDEBAR ───

.guide-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--color-bg-secondary, #12202e);
  padding: 24px 16px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  box-sizing: border-box;

  // Smooth border on right edge only via override
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.08);
}

.guide-sidebar-title {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted, #8895a8);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.guide-toc {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.guide-toc-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.875rem;
  line-height: 1.4;
  color: var(--text-muted, #8895a8);
  border-radius: 6px;
  transition: color 0.15s ease, background 0.15s ease;

  &:hover {
    color: var(--color-text-primary, #e1e1e1);
    background: rgba(255, 255, 255, 0.05);
  }

  &--active {
    color: $yellow;
    background: rgba($yellow, 0.08);
  }
}

// ─── CONTENT AREA ───

.guide-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px;
  background: var(--color-bg-primary, #0e1c2d);
}

.guide-prose {
  max-width: 800px;
  margin: 0 auto;
  color: var(--text-secondary, #a3aac4);
  line-height: 1.7;
  font-size: 0.95rem;
}

// ─── PROSE STYLES ───

.guide-prose :deep(h1) {
  color: var(--color-text-primary, #e1e1e1);
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 8px;
  line-height: 1.3;
}

.guide-prose :deep(h2) {
  color: var(--color-text-primary, #e1e1e1);
  font-size: 1.35rem;
  font-weight: 600;
  margin: 40px 0 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  line-height: 1.3;

  &:first-child {
    margin-top: 0;
    padding-top: 0;
    border-top: none;
  }
}

.guide-prose :deep(h3) {
  color: var(--color-text-primary, #e1e1e1);
  font-size: 1.1rem;
  font-weight: 600;
  margin: 28px 0 12px;
  line-height: 1.3;
}

.guide-prose :deep(h4) {
  color: var(--color-text-primary, #e1e1e1);
  font-size: 0.95rem;
  font-weight: 600;
  margin: 20px 0 8px;
}

.guide-prose :deep(p) {
  margin: 0 0 16px;
  color: var(--text-secondary, #a3aac4);
}

.guide-prose :deep(em) {
  color: var(--text-muted, #8895a8);
  font-style: italic;
}

.guide-prose :deep(strong) {
  color: var(--color-text-primary, #e1e1e1);
  font-weight: 600;
}

.guide-prose :deep(a) {
  color: $yellow;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.guide-prose :deep(ul),
.guide-prose :deep(ol) {
  margin: 0 0 16px;
  padding-left: 24px;
  color: var(--text-secondary, #a3aac4);
}

.guide-prose :deep(li) {
  margin-bottom: 6px;
  color: var(--text-secondary, #a3aac4);
}

.guide-prose :deep(code) {
  background: var(--color-bg-elevated, #1e3147);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.85em;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--color-text-primary, #e1e1e1);
}

.guide-prose :deep(pre) {
  background: var(--color-bg-elevated, #1e3147);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.875rem;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 0 0 20px;
  line-height: 1.6;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.07);

  code {
    background: transparent;
    padding: 0;
    border-radius: 0;
    font-size: inherit;
  }
}

.guide-prose :deep(hr) {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  margin: 32px 0;
}

.guide-prose :deep(blockquote) {
  border-left: 3px solid $yellow;
  margin: 0 0 16px;
  padding: 8px 16px;
  background: rgba($yellow, 0.05);
  border-radius: 0 6px 6px 0;
  color: var(--text-secondary, #a3aac4);
}

// ─── TABLE STYLES ───

.guide-prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 20px;
  font-size: 0.9rem;
}

.guide-prose :deep(thead) {
  background: rgba(255, 255, 255, 0.04);
}

.guide-prose :deep(th) {
  color: var(--color-text-primary, #e1e1e1);
  font-weight: 600;
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  white-space: nowrap;
}

.guide-prose :deep(td) {
  padding: 9px 14px;
  color: var(--text-secondary, #a3aac4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  vertical-align: top;
}

.guide-prose :deep(tbody tr:hover td) {
  background: rgba(255, 255, 255, 0.02);
}

// ─── RESPONSIVE ───

@media (max-width: 767px) {
  .guide-inner {
    flex-direction: column;
  }

  .guide-content {
    padding: 20px 16px;
  }
}
</style>
