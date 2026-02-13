/**
 * v-draggable directive - Makes Vuetify dialog cards draggable by their title bar.
 *
 * Usage:
 *   <v-card v-draggable>
 *     <v-card-title>Drag me</v-card-title>
 *     <v-card-text>Content</v-card-text>
 *   </v-card>
 *
 * Drag handle:  .v-card-title element within the bound card.
 * Position:     Applied via CSS transform: translate(x, y).
 * Bounds:       Prevents dragging entirely off-screen -- at least 50px of the
 *               card must remain visible on every edge.
 * Reset:        Position resets when the element is unmounted (dialog close/reopen).
 * Touch:        Supports touchstart / touchmove / touchend for mobile devices.
 * Fullscreen:   Dragging is disabled when the parent dialog has the
 *               v-dialog--fullscreen class (checked both at mount and on each
 *               drag start so dynamically toggled fullscreen is handled).
 */

const MIN_VISIBLE_PX = 50

/**
 * Extract a clientX/clientY pair from either a MouseEvent or a TouchEvent.
 * Returns null if the event has no positional data (e.g. touchend).
 */
function getClientPosition(event) {
  if (event.clientX !== undefined && event.clientY !== undefined) {
    return { x: event.clientX, y: event.clientY }
  }
  if (event.touches && event.touches.length > 0) {
    return { x: event.touches[0].clientX, y: event.touches[0].clientY }
  }
  return null
}

/**
 * Return true when the element is inside a fullscreen Vuetify dialog.
 */
function isInsideFullscreenDialog(el) {
  const dialog = el.closest('.v-dialog')
  return dialog !== null && dialog.classList.contains('v-dialog--fullscreen')
}

export const draggable = {
  mounted(el) {
    const handle = el.querySelector('.v-card-title')
    if (!handle) return

    // If the dialog is fullscreen at mount time, skip entirely.
    if (isInsideFullscreenDialog(el)) return

    let isDragging = false
    let startX = 0
    let startY = 0
    let offsetX = 0
    let offsetY = 0

    // Style the drag handle
    handle.style.cursor = 'move'
    handle.style.userSelect = 'none'

    function onPointerDown(event) {
      // Re-check fullscreen on every drag start (handles dynamic toggle)
      if (isInsideFullscreenDialog(el)) return

      const pos = getClientPosition(event)
      if (!pos) return

      isDragging = true
      startX = pos.x - offsetX
      startY = pos.y - offsetY
      handle.style.cursor = 'grabbing'
      event.preventDefault()
    }

    function onPointerMove(event) {
      if (!isDragging) return

      const pos = getClientPosition(event)
      if (!pos) return

      let newX = pos.x - startX
      let newY = pos.y - startY

      // --- Bounds clamping ---------------------------------------------------
      // Project where the card rect would end up if we applied the proposed
      // offset, then clamp so that at least MIN_VISIBLE_PX of the card stays
      // inside the viewport on every side.
      const rect = el.getBoundingClientRect()
      const deltaX = newX - offsetX
      const deltaY = newY - offsetY

      const projectedLeft = rect.left + deltaX
      const projectedTop = rect.top + deltaY
      const projectedRight = projectedLeft + rect.width
      const projectedBottom = projectedTop + rect.height

      // Right edge of card must not go below MIN_VISIBLE_PX (too far left)
      if (projectedRight < MIN_VISIBLE_PX) {
        newX = offsetX
      }
      // Left edge of card must not exceed viewport width - MIN_VISIBLE_PX (too far right)
      if (projectedLeft > window.innerWidth - MIN_VISIBLE_PX) {
        newX = offsetX
      }
      // Bottom edge of card must not go below MIN_VISIBLE_PX (too far up)
      if (projectedBottom < MIN_VISIBLE_PX) {
        newY = offsetY
      }
      // Top edge of card must not exceed viewport height - MIN_VISIBLE_PX (too far down)
      if (projectedTop > window.innerHeight - MIN_VISIBLE_PX) {
        newY = offsetY
      }

      offsetX = newX
      offsetY = newY
      el.style.transform = `translate(${offsetX}px, ${offsetY}px)`
    }

    function onPointerUp() {
      if (!isDragging) return
      isDragging = false
      handle.style.cursor = 'move'
    }

    // Mouse events
    handle.addEventListener('mousedown', onPointerDown)
    document.addEventListener('mousemove', onPointerMove)
    document.addEventListener('mouseup', onPointerUp)

    // Touch events
    handle.addEventListener('touchstart', onPointerDown, { passive: false })
    document.addEventListener('touchmove', onPointerMove, { passive: false })
    document.addEventListener('touchend', onPointerUp)

    // Store cleanup so unmounted can tear everything down
    el._draggableCleanup = () => {
      handle.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('mousemove', onPointerMove)
      document.removeEventListener('mouseup', onPointerUp)
      handle.removeEventListener('touchstart', onPointerDown)
      document.removeEventListener('touchmove', onPointerMove)
      document.removeEventListener('touchend', onPointerUp)
      el.style.transform = ''
    }
  },

  unmounted(el) {
    if (el._draggableCleanup) {
      el._draggableCleanup()
      delete el._draggableCleanup
    }
  },
}
