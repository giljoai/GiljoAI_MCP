<template>
  <div class="guide-layout">
    <!-- Mobile TOC chip row (< 768px) -->
    <div v-if="isMobile" class="guide-toc-mobile">
      <div class="guide-toc-mobile-search">
        <v-icon size="16" class="guide-search-icon">mdi-magnify</v-icon>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search guide..."
          class="guide-search-input"
          @keydown.escape="searchQuery = ''"
        />
        <button v-if="searchQuery" class="guide-search-clear" @click="searchQuery = ''">
          <v-icon size="14">mdi-close</v-icon>
        </button>
      </div>
      <div v-if="!searchQuery" class="guide-toc-mobile-inner">
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
      <div v-else-if="searchResults.length" class="guide-search-results-mobile">
        <button
          v-for="result in searchResults"
          :key="result.anchor"
          class="guide-search-result"
          @click="goToSearchResult(result)"
        >
          <span class="guide-search-result-section">{{ result.section }}</span>
          <span class="guide-search-result-snippet" v-html="result.snippet" />
        </button>
      </div>
      <div v-else class="guide-search-empty">No results for "{{ searchQuery }}"</div>
    </div>

    <!-- Desktop layout: sidebar + content -->
    <div class="guide-inner">
      <!-- Left sidebar TOC (>= 768px) — fixed to viewport -->
      <aside v-if="!isMobile" class="guide-sidebar">
        <div class="guide-sidebar-header">
          <div class="guide-sidebar-title">Contents</div>
          <div class="guide-search-box">
            <v-icon size="16" class="guide-search-icon">mdi-magnify</v-icon>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search..."
              class="guide-search-input"
              @keydown.escape="searchQuery = ''"
            />
            <button v-if="searchQuery" class="guide-search-clear" @click="searchQuery = ''">
              <v-icon size="14">mdi-close</v-icon>
            </button>
          </div>
        </div>

        <!-- Search results in sidebar -->
        <div v-if="searchQuery && searchResults.length" class="guide-search-results">
          <button
            v-for="result in searchResults"
            :key="result.anchor"
            class="guide-search-result"
            @click="goToSearchResult(result)"
          >
            <span class="guide-search-result-section">{{ result.section }}</span>
            <span class="guide-search-result-snippet" v-html="result.snippet" />
          </button>
        </div>
        <div v-else-if="searchQuery" class="guide-search-empty">
          No results
        </div>

        <!-- TOC (hidden during search) -->
        <nav v-else class="guide-toc" aria-label="Table of contents">
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
const searchQuery = ref('')

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

// ─── SEARCH ───

// Build searchable sections: split markdown by ## headings
const searchableSections = computed(() => {
  const sections = []
  const lines = combinedMarkdown.value.split('\n')
  let currentSection = null

  for (const line of lines) {
    const match = line.match(/^## (.+)$/)
    if (match) {
      if (currentSection) sections.push(currentSection)
      currentSection = {
        title: match[1].trim(),
        anchor: headingToAnchor(match[1].trim()),
        text: '',
      }
    } else if (currentSection) {
      currentSection.text += line + '\n'
    }
  }
  if (currentSection) sections.push(currentSection)
  return sections
})

const searchResults = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q || q.length < 2) return []

  const results = []
  for (const section of searchableSections.value) {
    const plainText = section.text
      .replace(/[#*_`|[\]()>-]/g, '')
      .replace(/\n+/g, ' ')
      .trim()

    const idx = plainText.toLowerCase().indexOf(q)
    if (idx === -1 && !section.title.toLowerCase().includes(q)) continue

    let snippet = ''
    if (idx !== -1) {
      const start = Math.max(0, idx - 30)
      const end = Math.min(plainText.length, idx + q.length + 50)
      const raw = (start > 0 ? '...' : '') + plainText.slice(start, end) + (end < plainText.length ? '...' : '')
      snippet = raw.replace(
        new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
        '<mark>$1</mark>'
      )
    }

    results.push({
      section: section.title,
      anchor: section.anchor,
      snippet,
    })
  }
  return results.slice(0, 10)
})

function goToSearchResult(result) {
  searchQuery.value = ''
  nextTick(() => scrollToAnchor(result.anchor))
}

// ─── TOC HELPERS ───

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
  height: calc(100vh - 64px); // subtract app bar height
  background: var(--color-bg-primary, #0e1c2d);
  overflow: hidden;
}

// ─── MOBILE TOC + SEARCH ───

.guide-toc-mobile {
  padding: 10px 16px;
  background: var(--color-bg-secondary, #12202e);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.guide-toc-mobile-search {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.guide-toc-mobile-inner {
  display: flex;
  gap: 8px;
  white-space: nowrap;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;

  &::-webkit-scrollbar {
    display: none;
  }
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
  overflow: hidden;
}

// ─── SIDEBAR (fixed to viewport, scrolls independently) ───

.guide-sidebar {
  width: 220px;
  flex-shrink: 0;
  background: var(--color-bg-secondary, #12202e);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.08);
}

.guide-sidebar-header {
  padding: 20px 16px 12px;
  flex-shrink: 0;
}

.guide-sidebar-title {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted, #8895a8);
  margin-bottom: 12px;
}

// ─── SEARCH BOX ───

.guide-search-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 6px 10px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  transition: box-shadow 0.15s ease;

  &:focus-within {
    box-shadow: inset 0 0 0 1px rgba($yellow, 0.4);
  }
}

.guide-search-icon {
  color: var(--text-muted, #8895a8);
  flex-shrink: 0;
}

.guide-search-input {
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text-primary, #e1e1e1);
  font-size: 0.8rem;
  font-family: inherit;
  width: 100%;
  min-width: 0;

  &::placeholder {
    color: var(--text-muted, #8895a8);
  }
}

.guide-search-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-muted, #8895a8);
  padding: 2px;
  border-radius: 4px;
  flex-shrink: 0;

  &:hover {
    color: var(--color-text-primary, #e1e1e1);
  }
}

// ─── SEARCH RESULTS ───

.guide-search-results,
.guide-search-results-mobile {
  overflow-y: auto;
  flex: 1;
  padding: 0 12px 12px;
}

.guide-search-result {
  display: flex;
  flex-direction: column;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
  }
}

.guide-search-result-section {
  font-size: 0.8rem;
  font-weight: 600;
  color: $yellow;
  margin-bottom: 2px;
}

.guide-search-result-snippet {
  font-size: 0.75rem;
  color: var(--text-muted, #8895a8);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;

  :deep(mark) {
    background: rgba($yellow, 0.25);
    color: var(--color-text-primary, #e1e1e1);
    border-radius: 2px;
    padding: 0 2px;
  }
}

.guide-search-empty {
  padding: 16px;
  font-size: 0.8rem;
  color: var(--text-muted, #8895a8);
  text-align: center;
}

// ─── TOC (below search, scrolls independently) ───

.guide-toc {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  flex: 1;
  padding: 0 12px 16px;
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

// ─── CONTENT AREA (scrolls independently) ───

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
  scroll-margin-top: 16px;

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
  .guide-layout {
    height: auto;
    min-height: calc(100vh - 64px);
    overflow: visible;
  }

  .guide-inner {
    flex-direction: column;
    overflow: visible;
  }

  .guide-content {
    padding: 20px 16px;
    overflow: visible;
  }
}
</style>
