# Performance Optimization Checklist
## Handover 0243f: Production-Ready Performance Validation

---

## Bundle Size Optimization

### Current Status Assessment

Run this to analyze current bundle:
```bash
npm run build
npm run analyze
```

### Critical Checks

- [ ] **NO nicepage.css imported**
  - Would add 1.65MB of bloat
  - Check: `grep -r "nicepage.css" src/`
  - Expected: No results

- [ ] **Vuetify tree-shaking enabled**
  - Check vite.config.ts has vite-plugin-vuetify with proper settings
  - Verify unused Vuetify components excluded from bundle
  - Expected: < 150KB Vuetify in final build

- [ ] **Code splitting for lazy routes**
  - LaunchTab: Dynamic import
  - JobsTab: Dynamic import
  - Message components: Dynamic import
  - Expected: Separate .js chunks in dist/assets/

- [ ] **Image optimization**
  - All PNG images converted to WebP where possible
  - Images use `loading="lazy"` attribute
  - Proper width/height attributes set
  - Expected: < 100KB total image size

### Bundle Size Targets

```
Ideal Distribution:
├── main-xxx.js       < 100KB gzipped
├── vendor-xxx.js     < 120KB gzipped
├── LaunchTab-xxx.js  < 40KB gzipped
├── JobsTab-xxx.js    < 40KB gzipped
├── styles-xxx.css    < 30KB gzipped
└── Total            < 500KB gzipped
```

### Verification Command

```bash
# After npm run build
du -sh dist/assets/*.js | sort -h
du -sh dist/assets/*.css | sort -h
gzip -k dist/assets/main*.js && du -sh dist/assets/main*.js.gz
```

Expected output: All gzipped files combined < 500KB

---

## Render Performance Optimization

### Component-Level Performance

#### LaunchTab Performance

- [ ] **Render time < 100ms**
  - Navigate to LaunchTab
  - Measure in Chrome DevTools → Performance
  - Record 5 navigations, average < 100ms

- [ ] **Three panels render correctly**
  - Each panel should load independently
  - No layout shift after load
  - CLS (Cumulative Layout Shift) < 0.1

- [ ] **Mission content appears quickly**
  - WebSocket event received and rendered < 200ms
  - No blocking JavaScript during render
  - TBT (Total Blocking Time) < 50ms

#### JobsTab Performance

- [ ] **Agent table renders < 100ms**
  - For typical load (5-10 agents)
  - Table rows visible immediately
  - Headers sticky during scroll

- [ ] **Status updates don't block UI**
  - WebSocket events debounced (100ms)
  - Status cell updates without full re-render
  - No frame drops (maintain 60 FPS)

- [ ] **Virtual scrolling for > 20 agents**
  - If agent list > 20: implement `v-virtual-scroll`
  - Render only visible rows
  - Expected: Smooth scroll even with 100+ agents

### Optimization Implementation

#### Debounce WebSocket Handlers

```typescript
// JobsTab.vue
import { debounce } from 'lodash-es'

const handleStatusUpdate = debounce((payload: any) => {
  agentsStore.updateAgentStatus(payload.agent_id, payload.status)
}, 100)  // Max 10 updates/second

onMounted(() => {
  websocket.on('agent:status_changed', handleStatusUpdate)
})

onUnmounted(() => {
  websocket.off('agent:status_changed', handleStatusUpdate)
  handleStatusUpdate.cancel()  // Cancel pending calls
})
```

#### Use v-memo for Static Content

```vue
<!-- JobsTab.vue agent cards -->
<div
  v-for="agent in agents"
  :key="agent.id"
  v-memo="[agent.id, agent.status, agent.health]"
  class="agent-card"
>
  <!-- Only re-renders if id/status/health change -->
  {{ agent.name }} - {{ agent.status }}
</div>
```

#### Computed Property Optimization

```typescript
// Before (re-computes every render)
<div>{{ agents.filter(a => a.status === 'Working...').length }}</div>

// After (cached result)
const workingCount = computed(() =>
  agents.value.filter(a => a.status === 'Working...').length
)
// <div>{{ workingCount }}</div>
```

---

## Memory Optimization

### Critical Memory Management

#### WebSocket Listener Cleanup

- [ ] **All listeners removed on unmount**
  ```typescript
  onUnmounted(() => {
    websocket.off('agent:status_changed', handlers.statusChanged)
    websocket.off('agent:health_update', handlers.healthUpdate)
    websocket.off('agent:job_complete', handlers.jobComplete)
  })
  ```

- [ ] **No listener accumulation on navigation**
  - Navigate away/back 10 times
  - Memory should not grow linearly
  - Check: DevTools → Memory → Detached DOM nodes count

#### Interval Timer Cleanup

- [ ] **useStalenessMonitor clears interval**
  ```typescript
  export function useStalenessMonitor(agents: Ref<Agent[]>) {
    const interval = setInterval(() => {
      checkStaleness(agents.value)
    }, 30000)

    onUnmounted(() => {
      clearInterval(interval)  // CRITICAL
    })
  }
  ```

- [ ] **No orphaned timers in background**
  - Navigate to Implement tab
  - Navigate to Launch tab
  - Navigate away from project
  - Check: DevTools → Sources → setTimeout/setInterval count

#### DOM Reference Management

- [ ] **WeakMap used for caching**
  - Prevents memory leaks from circular references
  - Automatic garbage collection when agent objects are freed

- [ ] **No strong references to detached DOM**
  - No stored references to removed elements
  - Use event delegation instead of element refs

### Memory Profiling Process

```bash
# 1. Start preview server
npm run preview

# 2. Open Chrome DevTools → Memory
# 3. Follow this sequence:
#    a. Heap Snapshot 1 (Initial state)
#    b. Navigate to LaunchTab
#    c. Heap Snapshot 2
#    d. Compare snapshots
#    Expected: < 5MB increase

# 4. Memory leak test:
#    a. Heap Snapshot 1
#    b. Tab navigation loop (10 times)
#    c. Force GC (DevTools → Three dots → Collect garbage)
#    d. Heap Snapshot 2
#    Expected: < 10MB increase
```

### Memory Targets

- **Initial load**: ~15MB
- **After LaunchTab nav**: ~18MB (< 5MB increase)
- **After JobsTab nav**: ~19MB (< 5MB cumulative)
- **After 10 tab navigations**: ~25MB (< 10MB increase)

---

## Lighthouse Audit

### Execution

```bash
# 1. Build production bundle
npm run build

# 2. Start preview server
npm run preview

# 3. Option A: Chrome DevTools (manual)
#    - Open http://localhost:7274/projects/test-project
#    - DevTools → Lighthouse
#    - Device: Desktop
#    - Categories: All
#    - Generate report

# 4. Option B: CLI (automated)
npx lighthouse http://localhost:7274/projects/test-project \
  --only-categories=performance \
  --output=html \
  --output-path=./lighthouse-report.html
```

### Performance Metrics Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Performance Score | > 90 | ? | ⏳ |
| First Contentful Paint (FCP) | < 1.5s | ? | ⏳ |
| Largest Contentful Paint (LCP) | < 2.5s | ? | ⏳ |
| Time to Interactive (TTI) | < 3.5s | ? | ⏳ |
| Total Blocking Time (TBT) | < 200ms | ? | ⏳ |
| Cumulative Layout Shift (CLS) | < 0.1 | ? | ⏳ |

### Interpreting Results

**Performance Score > 90** ✅
- Excellent user experience
- All metrics in green

**Performance Score 80-90** ⚠️
- Good performance
- May have 1-2 metrics in yellow
- Acceptable for production

**Performance Score < 80** ❌
- Optimization required
- Don't deploy until fixed

---

## Core Web Vitals Validation

### Field Testing

Use Chrome User Experience Report or field data:

```bash
# Check real user metrics (if deployed)
# https://developers.google.com/speed/pagespeed/insights/?url=...
```

### Lab Testing (Synthetic)

Run these tests regularly:

```bash
# 1. FCP test (First Contentful Paint)
#    Measure: Time to first content visible
#    Target: < 1.5s

# 2. LCP test (Largest Contentful Paint)
#    Measure: Time to largest visible content
#    Target: < 2.5s

# 3. TTI test (Time to Interactive)
#    Measure: Time until page is interactive
#    Target: < 3.5s

# 4. TBT test (Total Blocking Time)
#    Measure: Total time main thread blocked > 50ms
#    Target: < 200ms

# 5. CLS test (Cumulative Layout Shift)
#    Measure: Unexpected visual shift
#    Target: < 0.1
```

---

## Accessibility Performance

### Keyboard Navigation Testing

- [ ] **Tab through all interactive elements**
  - Logical tab order
  - Visible focus indicators
  - No focus traps

- [ ] **Enter/Space activate buttons**
  - Stage button responds to Enter
  - Action buttons respond to Enter/Space

- [ ] **Escape closes modals**
  - Modal close on Escape key
  - Focus returned to trigger element

### Screen Reader Compatibility

- [ ] **ARIA labels present**
  - Icon buttons have aria-label
  - Form inputs have labels
  - Status regions marked aria-live

- [ ] **Semantic HTML used**
  - `<button>` for buttons (not `<div>`)
  - `<a>` for links
  - `<table>` for data tables

### Mobile Accessibility

- [ ] **Touch target size > 48x48px**
  - Buttons easily tappable
  - Links have adequate spacing

- [ ] **Viewport meta tag present**
  - `<meta name="viewport" content="width=device-width, initial-scale=1">`
  - Prevents zoom issues

---

## Production Deployment Validation

### Pre-Deployment Checklist

#### Code Quality
- [ ] No console errors in production build
- [ ] No console warnings (address or suppress)
- [ ] No 4xx/5xx HTTP errors
- [ ] WebSocket connection successful

#### Performance
- [ ] Bundle size < 500KB gzipped
- [ ] Lighthouse performance > 90
- [ ] Core Web Vitals all in green
- [ ] No memory leaks detected

#### Security
- [ ] CSRF protection enabled
- [ ] XSS protection enabled
- [ ] CSP headers configured
- [ ] API rate limiting enabled

#### Functionality
- [ ] LaunchTab workflow end-to-end
- [ ] JobsTab agent management working
- [ ] Multi-tenant isolation verified
- [ ] WebSocket real-time updates working

#### User Experience
- [ ] Visual design matches Nicepage
- [ ] Responsive on mobile/tablet/desktop
- [ ] Touch interactions work
- [ ] Keyboard navigation works
- [ ] Screen reader accessible

### Deployment Steps

```bash
# 1. Build production bundle
npm run build

# 2. Analyze bundle
npm run analyze

# 3. Run performance audit
npm run preview
# Then run Lighthouse in Chrome DevTools

# 4. Run E2E tests
npm run test:e2e

# 5. Memory profiling
# Manual process in Chrome DevTools

# 6. Security scan
# npx npm-audit

# 7. Deploy to staging first
# Test in staging environment

# 8. Promote to production
```

---

## Ongoing Performance Monitoring

### Regular Audits (Weekly)

```bash
# Bundle size
npm run build && ls -lh dist/assets/

# Lighthouse (automated)
npx lighthouse https://production-url.com --only-categories=performance
```

### Metrics Dashboard

Set up monitoring for:
- Bundle size (alert if > 550KB)
- Lighthouse performance (alert if < 85)
- Core Web Vitals from field data
- Error rate from Sentry/monitoring tool

### Regression Testing

Before each release:
1. Run E2E tests: `npm run test:e2e`
2. Run unit tests: `npm run test:run`
3. Run Lighthouse: `npm run preview` → DevTools
4. Check memory: DevTools → Memory

---

## Optimization Priority

### P1 (Critical - Must Fix Before Production)
1. Bundle size < 500KB gzipped
2. E2E tests 100% passing
3. Multi-tenant isolation working
4. No WebSocket memory leaks

### P2 (High - Should Fix)
1. Lighthouse performance > 90
2. FCP < 1.5s
3. LCP < 2.5s
4. No console errors

### P3 (Nice to Have)
1. Keyboard navigation fully accessible
2. Screen reader fully compatible
3. Mobile responsiveness perfect
4. Animation performance smooth

---

## Common Performance Issues & Fixes

### Issue: Memory Leak on Tab Navigation
**Symptom**: Memory grows linearly with each navigation
**Fix**: Ensure all WebSocket listeners and timers are cleared on unmount

### Issue: Slow Status Updates
**Symptom**: UI freezes when status changes
**Fix**: Debounce WebSocket handlers (100ms), use v-memo

### Issue: Large Bundle Size
**Symptom**: Bundle > 500KB gzipped
**Fix**: Check for nicepage.css, enable tree-shaking, lazy load components

### Issue: CLS (Layout Shift)
**Symptom**: Content shifts position after load
**Fix**: Reserve space for dynamic content, set explicit dimensions

### Issue: High TBT (Blocking Time)
**Symptom**: Page unresponsive during interactions
**Fix**: Debounce event handlers, break heavy computations into microtasks

---

## Tools & Resources

- **Lighthouse**: https://developers.google.com/speed/pagespeed/insights
- **Chrome DevTools**: DevTools → Performance, Memory, Lighthouse tabs
- **Playwright**: https://playwright.dev/
- **Web Vitals**: https://web.dev/vitals/
- **Bundle Analyzer**: `npm run analyze`

---

**Last Updated**: 2025-11-23
**Phase**: Handover 0243f - FINAL PRODUCTION VALIDATION
**Status**: Ready for Implementation
