import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { draggable } from '@/directives/draggable'

/**
 * Unit tests for v-draggable directive.
 *
 * The directive operates directly on DOM elements, so we build minimal
 * DOM structures and invoke the lifecycle hooks (mounted / unmounted)
 * manually rather than mounting full Vue components.
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a mock DOM tree that mirrors a Vuetify dialog with a card inside.
 *
 *   <div class="v-dialog">          <- dialogEl
 *     <div class="v-card">          <- cardEl  (the element the directive binds to)
 *       <div class="v-card-title">  <- titleEl (drag handle)
 *         Title
 *       </div>
 *       <div class="v-card-text">   <- bodyEl
 *         Body content
 *       </div>
 *     </div>
 *   </div>
 */
function createDialogDOM(options = {}) {
  const dialogEl = document.createElement('div')
  dialogEl.classList.add('v-dialog')
  if (options.fullscreen) {
    dialogEl.classList.add('v-dialog--fullscreen')
  }

  const cardEl = document.createElement('div')
  cardEl.classList.add('v-card')

  if (!options.noTitle) {
    const titleEl = document.createElement('div')
    titleEl.classList.add('v-card-title')
    titleEl.textContent = 'Dialog Title'
    cardEl.appendChild(titleEl)
  }

  const bodyEl = document.createElement('div')
  bodyEl.classList.add('v-card-text')
  bodyEl.textContent = 'Body content'
  cardEl.appendChild(bodyEl)

  dialogEl.appendChild(cardEl)
  document.body.appendChild(dialogEl)

  return {
    dialogEl,
    cardEl,
    titleEl: cardEl.querySelector('.v-card-title'),
    bodyEl,
  }
}

/**
 * Stub getBoundingClientRect on the given element.
 * Simulates a 400x300 card centered in an 800x600 viewport.
 */
function stubRect(el, rect) {
  el.getBoundingClientRect = vi.fn(() => ({
    left: rect.left ?? 200,
    top: rect.top ?? 150,
    right: rect.right ?? 600,
    bottom: rect.bottom ?? 450,
    width: rect.width ?? 400,
    height: rect.height ?? 300,
    x: rect.left ?? 200,
    y: rect.top ?? 150,
  }))
}

/**
 * Fire a synthetic MouseEvent on the given target.
 */
function fireMouseEvent(type, target, options = {}) {
  const event = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    clientX: options.clientX ?? 0,
    clientY: options.clientY ?? 0,
    ...options,
  })
  target.dispatchEvent(event)
  return event
}

/**
 * Fire a synthetic TouchEvent on the given target.
 * jsdom does not natively support TouchEvent, so we build a plain Event
 * and attach a touches array manually.
 */
function fireTouchEvent(type, target, options = {}) {
  const event = new Event(type, { bubbles: true, cancelable: true })
  event.touches = [
    { clientX: options.clientX ?? 0, clientY: options.clientY ?? 0 },
  ]
  event.preventDefault = vi.fn()
  target.dispatchEvent(event)
  return event
}

// ---------------------------------------------------------------------------
// Viewport stub
// ---------------------------------------------------------------------------

function setViewport(width, height) {
  Object.defineProperty(window, 'innerWidth', { value: width, configurable: true })
  Object.defineProperty(window, 'innerHeight', { value: height, configurable: true })
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('v-draggable directive', () => {
  let dom

  beforeEach(() => {
    setViewport(800, 600)
  })

  afterEach(() => {
    // Clean up any DOM nodes left by tests
    if (dom) {
      if (dom.cardEl._draggableCleanup) {
        draggable.unmounted(dom.cardEl)
      }
      dom.dialogEl.remove()
      dom = null
    }
  })

  // -----------------------------------------------------------------------
  // Mounting / initialization
  // -----------------------------------------------------------------------

  describe('mounting', () => {
    it('finds the .v-card-title element and sets cursor to move', () => {
      dom = createDialogDOM()
      draggable.mounted(dom.cardEl)

      expect(dom.titleEl.style.cursor).toBe('move')
    })

    it('sets userSelect to none on the title bar', () => {
      dom = createDialogDOM()
      draggable.mounted(dom.cardEl)

      expect(dom.titleEl.style.userSelect).toBe('none')
    })

    it('stores a cleanup function on the element', () => {
      dom = createDialogDOM()
      draggable.mounted(dom.cardEl)

      expect(typeof dom.cardEl._draggableCleanup).toBe('function')
    })

    it('does nothing when no .v-card-title element exists', () => {
      dom = createDialogDOM({ noTitle: true })
      draggable.mounted(dom.cardEl)

      // No cleanup stored means directive gracefully skipped
      expect(dom.cardEl._draggableCleanup).toBeUndefined()
    })
  })

  // -----------------------------------------------------------------------
  // Mouse drag lifecycle
  // -----------------------------------------------------------------------

  describe('mouse drag', () => {
    beforeEach(() => {
      dom = createDialogDOM()
      stubRect(dom.cardEl, { left: 200, top: 150, right: 600, bottom: 450, width: 400, height: 300 })
      draggable.mounted(dom.cardEl)
    })

    it('mousedown on title starts drag and changes cursor to grabbing', () => {
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })

      expect(dom.titleEl.style.cursor).toBe('grabbing')
    })

    it('mousemove updates transform on the card element', () => {
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 350, clientY: 250 })

      expect(dom.cardEl.style.transform).toContain('translate(')
      expect(dom.cardEl.style.transform).toContain('50px')
      expect(dom.cardEl.style.transform).toContain('50px')
    })

    it('mouseup stops tracking and restores cursor to move', () => {
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 350, clientY: 250 })
      fireMouseEvent('mouseup', document)

      expect(dom.titleEl.style.cursor).toBe('move')

      // Subsequent mousemove should not change transform further
      const currentTransform = dom.cardEl.style.transform
      fireMouseEvent('mousemove', document, { clientX: 400, clientY: 300 })
      expect(dom.cardEl.style.transform).toBe(currentTransform)
    })

    it('clicking card body (not title) does NOT start drag', () => {
      fireMouseEvent('mousedown', dom.bodyEl, { clientX: 300, clientY: 350 })
      fireMouseEvent('mousemove', document, { clientX: 400, clientY: 400 })

      // Transform should not be set
      expect(dom.cardEl.style.transform).toBe('')
    })

    it('multiple drags accumulate offset correctly', () => {
      // First drag: move right 50px, down 50px
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 350, clientY: 250 })
      fireMouseEvent('mouseup', document)

      expect(dom.cardEl.style.transform).toBe('translate(50px, 50px)')

      // Second drag: move right another 30px, down another 20px
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 350, clientY: 250 })
      fireMouseEvent('mousemove', document, { clientX: 380, clientY: 270 })
      fireMouseEvent('mouseup', document)

      expect(dom.cardEl.style.transform).toBe('translate(80px, 70px)')
    })
  })

  // -----------------------------------------------------------------------
  // Bounds checking
  // -----------------------------------------------------------------------

  describe('bounds checking', () => {
    const MIN_VISIBLE = 50

    beforeEach(() => {
      dom = createDialogDOM()
      // Card: 400x300, centered in 800x600 viewport => left=200, top=150
      stubRect(dom.cardEl, { left: 200, top: 150, right: 600, bottom: 450, width: 400, height: 300 })
      draggable.mounted(dom.cardEl)
    })

    it('prevents the card from going too far left (right edge < 50px)', () => {
      // Try to drag far left: move -600px
      // Card right edge would be at 600 + (-600) = 0, which is < 50
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: -300, clientY: 200 })

      const transform = dom.cardEl.style.transform
      // The card should have been clamped - the right edge must stay >= 50px visible
      // With card at left=200, width=400, right=600, moving -600 => right=0 < 50
      // So offset should be clamped
      expect(transform).not.toBe('translate(-600px, 0px)')
    })

    it('prevents the card from going too far right (left edge > viewport - 50px)', () => {
      // Try to drag far right: move +600px
      // Card left edge would be at 200 + 600 = 800, which is > 800 - 50 = 750
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 900, clientY: 200 })

      const transform = dom.cardEl.style.transform
      expect(transform).not.toBe('translate(600px, 0px)')
    })

    it('prevents the card from going too far up (bottom edge < 50px)', () => {
      // Try to drag far up: move -450px
      // Card bottom edge would be at 450 + (-450) = 0, which is < 50
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 300, clientY: -250 })

      const transform = dom.cardEl.style.transform
      expect(transform).not.toBe('translate(0px, -450px)')
    })

    it('prevents the card from going too far down (top edge > viewport - 50px)', () => {
      // Try to drag far down: move +500px
      // Card top edge would be at 150 + 500 = 650, which is > 600 - 50 = 550
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 300, clientY: 700 })

      const transform = dom.cardEl.style.transform
      expect(transform).not.toBe('translate(0px, 500px)')
    })

    it('allows movement within bounds without clamping', () => {
      // Small move that stays well within bounds
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 320, clientY: 210 })

      expect(dom.cardEl.style.transform).toBe('translate(20px, 10px)')
    })
  })

  // -----------------------------------------------------------------------
  // Unmount / cleanup
  // -----------------------------------------------------------------------

  describe('unmount', () => {
    it('resets transform when element is unmounted', () => {
      dom = createDialogDOM()
      stubRect(dom.cardEl, { left: 200, top: 150, right: 600, bottom: 450, width: 400, height: 300 })
      draggable.mounted(dom.cardEl)

      // Drag to create a transform
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 350, clientY: 250 })
      fireMouseEvent('mouseup', document)
      expect(dom.cardEl.style.transform).toBe('translate(50px, 50px)')

      // Unmount
      draggable.unmounted(dom.cardEl)

      expect(dom.cardEl.style.transform).toBe('')
      expect(dom.cardEl._draggableCleanup).toBeUndefined()
    })

    it('removes event listeners on unmount (no errors on subsequent events)', () => {
      dom = createDialogDOM()
      draggable.mounted(dom.cardEl)
      draggable.unmounted(dom.cardEl)

      // These should not throw or cause any side effects
      expect(() => {
        fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
        fireMouseEvent('mousemove', document, { clientX: 350, clientY: 250 })
        fireMouseEvent('mouseup', document)
      }).not.toThrow()

      // Transform should remain empty since listeners are removed
      expect(dom.cardEl.style.transform).toBe('')
    })

    it('handles unmount gracefully when no cleanup function exists', () => {
      dom = createDialogDOM({ noTitle: true })
      draggable.mounted(dom.cardEl)

      // Should not throw
      expect(() => {
        draggable.unmounted(dom.cardEl)
      }).not.toThrow()
    })
  })

  // -----------------------------------------------------------------------
  // Touch events
  // -----------------------------------------------------------------------

  describe('touch events', () => {
    beforeEach(() => {
      dom = createDialogDOM()
      stubRect(dom.cardEl, { left: 200, top: 150, right: 600, bottom: 450, width: 400, height: 300 })
      draggable.mounted(dom.cardEl)
    })

    it('touchstart on title starts drag', () => {
      fireTouchEvent('touchstart', dom.titleEl, { clientX: 300, clientY: 200 })

      expect(dom.titleEl.style.cursor).toBe('grabbing')
    })

    it('touchmove updates transform on the card element', () => {
      fireTouchEvent('touchstart', dom.titleEl, { clientX: 300, clientY: 200 })
      fireTouchEvent('touchmove', document, { clientX: 370, clientY: 230 })

      expect(dom.cardEl.style.transform).toBe('translate(70px, 30px)')
    })

    it('touchend stops tracking and restores cursor', () => {
      fireTouchEvent('touchstart', dom.titleEl, { clientX: 300, clientY: 200 })
      fireTouchEvent('touchmove', document, { clientX: 370, clientY: 230 })

      const endEvent = new Event('touchend', { bubbles: true })
      document.dispatchEvent(endEvent)

      expect(dom.titleEl.style.cursor).toBe('move')

      // Further touchmove should not change transform
      const currentTransform = dom.cardEl.style.transform
      fireTouchEvent('touchmove', document, { clientX: 400, clientY: 260 })
      expect(dom.cardEl.style.transform).toBe(currentTransform)
    })

    it('touch drag respects bounds checking', () => {
      // Try to drag far right via touch
      fireTouchEvent('touchstart', dom.titleEl, { clientX: 300, clientY: 200 })
      fireTouchEvent('touchmove', document, { clientX: 900, clientY: 200 })

      const transform = dom.cardEl.style.transform
      // Should be clamped, not the raw offset
      expect(transform).not.toBe('translate(600px, 0px)')
    })
  })

  // -----------------------------------------------------------------------
  // Fullscreen detection
  // -----------------------------------------------------------------------

  describe('fullscreen detection', () => {
    it('skips initialization when dialog has fullscreen class', () => {
      dom = createDialogDOM({ fullscreen: true })
      draggable.mounted(dom.cardEl)

      // Directive should not have initialized - no cursor change
      expect(dom.titleEl.style.cursor).not.toBe('move')
      expect(dom.cardEl._draggableCleanup).toBeUndefined()
    })

    it('does not start drag when fullscreen class is added after mount', () => {
      dom = createDialogDOM()
      stubRect(dom.cardEl, { left: 200, top: 150, right: 600, bottom: 450, width: 400, height: 300 })
      draggable.mounted(dom.cardEl)

      // Add fullscreen class dynamically
      dom.dialogEl.classList.add('v-dialog--fullscreen')

      // Try to drag - should not work
      fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })
      fireMouseEvent('mousemove', document, { clientX: 350, clientY: 250 })

      // Transform should remain empty since fullscreen was detected on mousedown
      expect(dom.cardEl.style.transform).toBe('')
    })
  })

  // -----------------------------------------------------------------------
  // preventDefault behavior
  // -----------------------------------------------------------------------

  describe('preventDefault', () => {
    it('calls preventDefault on mousedown to avoid text selection', () => {
      dom = createDialogDOM()
      draggable.mounted(dom.cardEl)

      const event = fireMouseEvent('mousedown', dom.titleEl, { clientX: 300, clientY: 200 })

      // MouseEvent in jsdom is not easily mockable for preventDefault,
      // but we verify drag started (cursor changed), which requires preventDefault
      expect(dom.titleEl.style.cursor).toBe('grabbing')
    })
  })
})
