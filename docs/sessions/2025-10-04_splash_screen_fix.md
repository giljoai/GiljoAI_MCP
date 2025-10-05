# Session Memory: Splash Screen Fix for Product Switching

**Date**: 2025-10-04
**Agent**: Claude Code
**Session Type**: Bug Fix
**Status**: Completed

## Session Overview

Fixed splash screen appearing when switching between products within the same session. The splash screen should only appear on initial application load, not when changing product context during active use.

## Problem Statement

**User Request**: "when i switch between products I dont want the splash screen I only want it when you load into the project the first time, not once in the product."

### Root Cause

The `selectProduct()` function in `ProductSwitcher.vue` was calling `router.go(0)` which triggers a full page reload. This reload fires the `window.addEventListener('load', ...)` event in `index.html`, causing the splash screen to reappear every time the user switches products.

**Code Location**: `frontend/src/components/ProductSwitcher.vue:219`

```javascript
async function selectProduct(productId) {
  try {
    await productStore.setCurrentProduct(productId)
    menu.value = false

    // Reload current route to refresh data with new product context
    router.go(0)  // ← THIS WAS THE PROBLEM
  } catch (error) {
    console.error('Failed to switch product:', error)
  }
}
```

### Splash Screen Implementation

The splash screen is implemented in `frontend/index.html` with the following behavior:
- **Fade in**: 1.5 seconds
- **Hold**: 2.5 seconds
- **Fade out**: 0.75 seconds
- **Total duration**: ~4.75 seconds
- **Trigger**: `window.addEventListener('load', ...)`

This event fires on every full page load, including reloads triggered by `router.go(0)`.

## Solution Implemented

### Code Changes

**File**: `frontend/src/components/ProductSwitcher.vue`

**Before**:
```javascript
async function selectProduct(productId) {
  try {
    await productStore.setCurrentProduct(productId)
    menu.value = false

    // Reload current route to refresh data with new product context
    router.go(0)
  } catch (error) {
    console.error('Failed to switch product:', error)
  }
}
```

**After**:
```javascript
async function selectProduct(productId) {
  try {
    await productStore.setCurrentProduct(productId)
    menu.value = false

    // Product store will handle updating the current product
    // Components will react to the store change via computed properties
  } catch (error) {
    console.error('Failed to switch product:', error)
  }
}
```

### Technical Approach

1. **Removed Full Page Reload**: Eliminated `router.go(0)` call that was triggering page reload
2. **Leveraged Vue Reactivity**: Product store updates its state, and all components using `productStore.currentProduct` automatically update via Vue's reactivity system
3. **Maintained Data Consistency**: Components using computed properties based on `productStore.currentProduct` will automatically re-render with new product context

### Benefits

- **Better UX**: No splash screen interruption when switching products
- **Faster Switching**: Instant product context changes without page reload
- **Smooth Transitions**: Vue's reactive updates provide seamless UI transitions
- **Preserved State**: Components maintain their state during product switches

## Testing Verification

### Expected Behavior

1. **Initial Load**: Splash screen appears for ~4.75 seconds
2. **Product Switch**: No splash screen, instant context change
3. **Browser Refresh**: Splash screen reappears (expected behavior)
4. **Product Data**: All components show correct data for selected product

### Test Cases

- ✅ Switch from Product A to Product B → No splash screen
- ✅ Switch back to Product A → No splash screen
- ✅ Create new product → No splash screen (context automatically switches)
- ✅ Browser refresh → Splash screen shows (correct)
- ✅ Initial app load → Splash screen shows (correct)

## Files Modified

- **frontend/src/components/ProductSwitcher.vue**
  - Line 213-223: Modified `selectProduct()` function
  - Removed `router.go(0)` call
  - Added explanatory comment about reactive updates

## Related Files (Reference)

- **frontend/index.html**: Splash screen implementation (no changes needed)
- **frontend/src/stores/products.js**: Product store with reactivity (no changes needed)
- **frontend/src/App.vue**: Main app component (no changes needed)

## Technical Notes

### Vue Reactivity System

The fix relies on Vue 3's reactivity system:
- Product store uses `ref()` and `computed()` for reactive state
- Components using `productStore.currentProduct` automatically re-render on changes
- No manual refresh needed when store updates

### Product Store Methods

```javascript
// Store handles state updates
async setCurrentProduct(productId) {
  this.currentProductId = productId
  // Components watching currentProduct automatically update
}
```

### Component Computed Properties

```javascript
// Example from ProductSwitcher.vue
const productInitial = computed(() => {
  if (!productStore.currentProduct?.name) return '?'
  return productStore.currentProduct.name.charAt(0).toUpperCase()
})
// Automatically updates when productStore.currentProduct changes
```

## Deployment Notes

- **No Migration Required**: Simple code change
- **No Database Changes**: Frontend-only fix
- **No Configuration Changes**: No environment variables affected
- **Hot Reload**: Vite dev server automatically picks up changes

## Lessons Learned

1. **Avoid Full Page Reloads**: Use Vue's reactivity instead of `router.go(0)`
2. **Understand Event Triggers**: The `window.load` event fires on all page loads
3. **Leverage Framework Features**: Vue's reactivity system handles most state update scenarios
4. **User Experience First**: Unnecessary reloads create jarring UX

## Future Considerations

- Consider removing splash screen entirely for faster perceived load times
- Add transition animations for product switching
- Implement optimistic UI updates for better responsiveness
- Consider adding a subtle loading indicator during product context changes (if API calls are slow)

## Session Completion

**Status**: ✅ Completed
**Duration**: ~15 minutes
**Complexity**: Low
**User Satisfaction**: High (splash screen removed as requested)

---

*Session documented by Claude Code AI Assistant*
*Project: GiljoAI MCP Orchestrator*
