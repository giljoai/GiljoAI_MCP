# Handover 0052: Field Priority Unassigned Category - UX Specification

**Document Version**: 1.0
**Date**: 2025-10-27
**Approved By**: UX Designer

---

## Table of Contents

1. [User Experience Goals](#user-experience-goals)
2. [Visual Design Specifications](#visual-design-specifications)
3. [Interaction Patterns](#interaction-patterns)
4. [Accessibility Requirements](#accessibility-requirements)
5. [Responsive Behavior](#responsive-behavior)
6. [Error States & Edge Cases](#error-states--edge-cases)
7. [Before/After Comparisons](#beforeafter-comparisons)
8. [User Flows](#user-flows)

---

## User Experience Goals

### Primary Goals

1. **Transparency**: Users should see ALL available fields at all times
2. **Recoverability**: Users should easily recover accidentally removed fields
3. **Clarity**: Users should understand where fields go when removed
4. **Consistency**: Unassigned category should behave like other priority categories
5. **Confidence**: Users should feel safe experimenting with field priorities

### Success Metrics

- **Zero confusion**: Users immediately understand Unassigned category purpose
- **Quick recovery**: Users can recover removed field in <5 seconds
- **No dead ends**: No state where user feels "stuck" or confused
- **Natural flow**: Drag-and-drop feels intuitive and responsive

---

## Visual Design Specifications

### Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  Field Priority Configuration                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                              │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ Estimated Context Size for: TinyContacts               ┃  │
│  ┃ 1,247 / 2,000 tokens                         [62%] ⚫  ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Priority 1 - Always Included               [420 tokens] │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ┌────────────────────────────────────────────────────┐ │ │
│  │ │ 🔵 Tech Stack > Languages                    [✕]  │ │ │
│  │ │ 🔵 Tech Stack > Backend                      [✕]  │ │ │
│  │ └────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Priority 2 - High Priority                  [327 tokens] │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ┌────────────────────────────────────────────────────┐ │ │
│  │ │ 🟠 Tech Stack > Frontend                     [✕]  │ │ │
│  │ │ 🟠 Tech Stack > Database                     [✕]  │ │ │
│  │ │ 🟠 Architecture > Pattern                    [✕]  │ │ │
│  │ └────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Priority 3 - Medium Priority                  [0 tokens] │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ┌────────────────────────────────────────────────────┐ │ │
│  │ │           Drag fields here                         │ │ │
│  │ └────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │
│  │ Unassigned - Not Included in Missions       [0 tokens] │ │
│  ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤ │
│  │ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │ │
│  │ │ ⚪ Tech Stack > Infrastructure            [✕]    │ │ │
│  │ │ ⚪ Architecture > API Style               [✕]    │ │ │
│  │ │ ⚪ Architecture > Design Patterns         [✕]    │ │ │
│  │ │ ⚪ Architecture > Notes                   [✕]    │ │ │
│  │ │ ⚪ Features > Core                        [✕]    │ │ │
│  │ │ ⚪ Test Config > Strategy                 [✕]    │ │ │
│  │ │ ⚪ Test Config > Frameworks               [✕]    │ │ │
│  │ │ ⚪ Test Config > Coverage Target          [✕]    │ │ │
│  │ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │ │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │
│                                                              │
│  [ Cancel ]                             [ Save Changes ]    │
└──────────────────────────────────────────────────────────────┘
```

### Color Palette

#### Priority Categories (Existing)

**Priority 1 (Always Included)**:
- Background: `#FFEBEE` (red-lighten-5)
- Border: `#EF5350` (red-lighten-1)
- Icon: 🔴 Red circle
- Field chip: Red tonal variant

**Priority 2 (High Priority)**:
- Background: `#FFF3E0` (orange-lighten-5)
- Border: `#FF9800` (orange)
- Icon: 🟠 Orange circle
- Field chip: Orange tonal variant

**Priority 3 (Medium Priority)**:
- Background: `#E3F2FD` (blue-lighten-5)
- Border: `#2196F3` (blue)
- Icon: 🔵 Blue circle
- Field chip: Blue tonal variant

#### Unassigned Category (NEW)

**Unassigned (Not Included)**:
- Background: `#FAFAFA` (grey-lighten-4)
- Border: `#BDBDBD` (grey-lighten-1, **dashed**)
- Icon: ⚪ White/grey circle
- Field chip: Grey tonal variant
- **Visual Cue**: Dashed border indicates "optional/not included" state

### Typography

**Category Headers**:
```css
.category-header {
  font-size: 16px;
  font-weight: 600;
  color: #424242; /* grey-darken-3 */
}
```

**Token Badge**:
```css
.token-badge {
  font-size: 12px;
  font-weight: 500;
  color: #757575; /* grey-darken-1 */
}
```

**Field Names**:
```css
.field-name {
  font-size: 14px;
  font-weight: 400;
  color: #212121; /* grey-darken-4 */
}
```

**Helper Text**:
```css
.helper-text {
  font-size: 12px;
  font-weight: 400;
  color: #9E9E9E; /* grey */
  font-style: italic;
}
```

### Spacing & Dimensions

**Category Container**:
- Width: 100% (fluid)
- Min-height: 80px
- Padding: 16px
- Margin-bottom: 16px
- Border-radius: 4px

**Field Chips**:
- Height: 32px
- Padding: 8px 12px
- Margin: 4px
- Border-radius: 16px

**Drag Drop Zone**:
- Min-height: 60px
- Padding: 12px
- Border-width: 2px

---

## Interaction Patterns

### Drag-and-Drop Behavior

#### Visual Feedback During Drag

**1. Drag Start (Field Picked Up)**:
```
🔵 Tech Stack > Languages [✕]
    ↓ (cursor grabs chip)
┌─────────────────────────────────┐
│ 👆 Tech Stack > Languages       │ ← Semi-transparent (opacity: 0.6)
└─────────────────────────────────┘
```

**2. Drag Over Valid Drop Zone**:
```
┌────────────────────────────────────────────────────────┐
│ Priority 2 - High Priority                             │
├────────────────────────────────────────────────────────┤
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ 🟠 Tech Stack > Frontend                    [✕] ┃ │ ← Highlight zone
│ ┃ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┃ │ ← Insertion line
│ ┃ 🟠 Tech Stack > Database                    [✕] ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
└────────────────────────────────────────────────────────┘
```

**3. Drop (Field Released)**:
```
Smooth animation (200ms ease-out) to final position
Field color changes to match new category
Token count updates with animation
```

#### Cursor Changes

- **Idle**: `cursor: default`
- **Hovering over field**: `cursor: grab`
- **Dragging field**: `cursor: grabbing`
- **Over valid drop zone**: `cursor: grabbing` (no change)
- **Over invalid zone**: `cursor: not-allowed` (not applicable - all zones valid)

### Remove Button ([✕]) Behavior

**Visual States**:

**1. Default (Not Hovering)**:
```
Tech Stack > Languages [✕]
                        ↑
                     opacity: 0.5
                     color: grey
```

**2. Hover**:
```
Tech Stack > Languages [✕]
                        ↑
                     opacity: 1.0
                     color: red
                     cursor: pointer
```

**3. Click**:
```
Field fades out (100ms) from current category
    ↓
Field fades in (200ms) to Unassigned category
    ↓
Token count updates
```

### Tooltip Behavior

**Unassigned Category Header**:

**Tooltip Trigger**: Hover over info icon (ⓘ)

**Tooltip Content**:
```
╭──────────────────────────────────────────────╮
│ Fields in this category are NOT sent to AI  │
│ agents during mission generation.           │
│                                              │
│ Drag a field to Priority 1, 2, or 3 to      │
│ include it in agent missions.                │
╰──────────────────────────────────────────────╯
```

**Styling**:
- Background: `#424242` (dark grey)
- Text color: White
- Font size: 12px
- Max width: 300px
- Padding: 12px
- Border radius: 4px

### Empty State Behavior

#### Empty Priority Category (P1/P2/P3)

**Visual**:
```
┌────────────────────────────────────────────────────────┐
│ Priority 3 - Medium Priority                  [0 tokens] │
├────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────┐ │
│ │                                                    │ │
│ │           Drag fields here to assign               │ │
│ │           Medium Priority (P3)                     │ │
│ │                                                    │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

**Characteristics**:
- Text: Grey, centered, italic
- Background: Lighter shade of category color
- Dashed border (subtle)

#### Empty Unassigned Category

**Visual**:
```
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│ Unassigned - Not Included in Missions       [0 tokens] │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
│ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │
│ │                                                  │ │
│ │        ✓ All fields assigned to priorities      │ │
│ │                                                  │ │
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

**Characteristics**:
- Text: Green, centered, with checkmark
- Positive messaging (not negative "No unassigned fields")

### Token Count Updates

**Animation**:
```javascript
// When field moves between categories
Old Value: 1,247 tokens
    ↓
Number animates (500ms ease-out)
    ↓
New Value: 1,189 tokens
```

**Implementation**:
- Smooth number transition (not instant jump)
- Progress circle animates in sync
- Color changes if threshold crossed (green → yellow → red)

---

## Accessibility Requirements

### Keyboard Navigation

**Tab Order**:
1. Priority 1 container (focus on first field or container if empty)
2. Fields within Priority 1 (Tab to next, Shift+Tab to previous)
3. Priority 2 container
4. Fields within Priority 2
5. Priority 3 container
6. Fields within Priority 3
7. Unassigned container
8. Fields within Unassigned
9. Save Changes button
10. Cancel button

**Keyboard Shortcuts**:

| Key | Action |
|-----|--------|
| `Tab` | Navigate to next field/container |
| `Shift+Tab` | Navigate to previous field/container |
| `Space` | Select/grab field for drag |
| `Arrow Up/Down` | Move field within category |
| `Arrow Left/Right` | Move field to adjacent category |
| `Escape` | Cancel drag operation |
| `Delete` | Remove field from priority (move to Unassigned) |
| `Enter` | Confirm drag operation (drop) |

**Focus Indicators**:
```css
.field-chip:focus {
  outline: 2px solid #2196F3; /* Blue */
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(33, 150, 243, 0.2);
}
```

### Screen Reader Support

**ARIA Labels**:

**Category Headers**:
```html
<div
  role="region"
  aria-labelledby="priority-1-header"
  aria-describedby="priority-1-description"
>
  <h3 id="priority-1-header">Priority 1 - Always Included</h3>
  <p id="priority-1-description" class="sr-only">
    Fields in this category are always sent to AI agents with highest priority.
    Currently contains 2 fields worth 420 tokens.
  </p>
</div>
```

**Draggable Fields**:
```html
<div
  role="listitem"
  draggable="true"
  aria-label="Tech Stack Languages field, Priority 1, 210 tokens"
  aria-grabbed="false"
>
  Tech Stack > Languages [✕]
</div>
```

**During Drag**:
```html
<div
  aria-grabbed="true"
  aria-dropeffect="move"
>
  Tech Stack > Languages [✕]
</div>
```

**Screen Reader Announcements**:

**On Remove**:
```
"Tech Stack Languages removed from Priority 1, moved to Unassigned.
Token count decreased to 1,037 tokens."
```

**On Drag to Category**:
```
"Tech Stack Languages moved from Unassigned to Priority 2.
Token count increased to 1,247 tokens."
```

**On Save**:
```
"Field priorities saved successfully. Configuration updated."
```

### Color Contrast

**WCAG 2.1 Level AA Compliance**:

| Element | Foreground | Background | Contrast Ratio |
|---------|-----------|------------|----------------|
| Category header | `#424242` | `#FAFAFA` | 8.6:1 ✅ |
| Field chip text | `#212121` | `#FFEBEE` | 12.3:1 ✅ |
| Token badge | `#757575` | `#FFFFFF` | 4.7:1 ✅ |
| Helper text | `#9E9E9E` | `#FFFFFF` | 3.2:1 ⚠️ (use larger font) |

**Adjustments for Unassigned**:
- Field chip text on grey background: `#212121` on `#FAFAFA` = 13.1:1 ✅

---

## Responsive Behavior

### Desktop (≥1024px)

**Layout**: Vertical stacking of 4 categories, full width

```
┌─────────────────────────────────────┐
│ Priority 1                          │
├─────────────────────────────────────┤
│ [fields...]                         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Priority 2                          │
├─────────────────────────────────────┤
│ [fields...]                         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Priority 3                          │
├─────────────────────────────────────┤
│ [fields...]                         │
└─────────────────────────────────────┘

┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│ Unassigned                          │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
│ [fields...]                         │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

### Tablet (768px - 1023px)

**Layout**: Same as desktop (vertical stacking)

**Adjustments**:
- Slightly reduced padding (12px instead of 16px)
- Field chips wrap to multiple lines if needed

### Mobile (≤767px)

**Layout**: Vertical stacking with collapsible categories (future enhancement)

**Current**: Same as desktop/tablet (scroll vertically)

**Future Enhancement**: Accordion-style categories to reduce scrolling

---

## Error States & Edge Cases

### Error State 1: All Fields in One Category

**Scenario**: User drags all 13 fields into Priority 1

**Visual Feedback**:
```
┌────────────────────────────────────────────────────────┐
│ Priority 1 - Always Included              [2,850 tokens] │
├────────────────────────────────────────────────────────┤
│ ⚠️  WARNING: Token budget exceeded!                     │
│    Current: 2,850 / 2,000 tokens (142%)                │
│    Recommendation: Move some fields to P2 or Unassigned │
├────────────────────────────────────────────────────────┤
│ [13 field chips...]                                    │
└────────────────────────────────────────────────────────┘
```

**Behavior**:
- Allow user to save (soft warning, not blocking)
- Show warning banner at top of page
- Token indicator turns red

### Error State 2: All Fields in Unassigned

**Scenario**: User removes all fields from priority categories

**Visual Feedback**:
```
┌────────────────────────────────────────────────────────┐
│ Estimated Context Size for: TinyContacts               │
│ 500 / 2,000 tokens (25%)                     [🟢]     │
├────────────────────────────────────────────────────────┤
│ ℹ️  INFO: No fields assigned to priorities.             │
│    AI agents will receive minimal context.             │
│    Recommendation: Assign at least 3-5 critical fields  │
└────────────────────────────────────────────────────────┘

┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│ Unassigned - Not Included in Missions         [0 tokens] │
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
│ [13 field chips...]                                    │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

**Behavior**:
- Allow user to save (soft warning)
- Show informational message
- Token count shows only structure overhead (500 tokens)

### Edge Case 1: Rapid Drag Operations

**Scenario**: User drags multiple fields quickly in succession

**Behavior**:
- Debounce token calculation (300ms)
- Queue UI updates to prevent jank
- Show loading spinner if calculation takes >500ms (unlikely)

### Edge Case 2: Network Error on Save

**Scenario**: Save API call fails (network timeout, 500 error)

**Visual Feedback**:
```
╭────────────────────────────────────────────╮
│ ❌ Failed to save field priorities         │
│                                            │
│ Error: Network timeout                     │
│                                            │
│ [ Retry ]  [ Cancel ]                     │
╰────────────────────────────────────────────╯
```

**Behavior**:
- Show error toast notification
- Keep unsaved changes in UI (don't reset)
- Offer "Retry" button
- Don't navigate away from page

---

## Before/After Comparisons

### Comparison 1: Removing a Field

**BEFORE (Current Behavior)**:

```
Step 1: User clicks [✕] on "Database" in Priority 2
┌────────────────────────────────────────┐
│ Priority 2                             │
│ ┌────────────────────────────────────┐ │
│ │ Frontend              [✕]          │ │
│ │ Database              [✕]  ← Click │ │
│ │ Pattern               [✕]          │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘

Step 2: Field disappears ❌
┌────────────────────────────────────────┐
│ Priority 2                             │
│ ┌────────────────────────────────────┐ │
│ │ Frontend              [✕]          │ │
│ │ Pattern               [✕]          │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘

Result: User confused "Where did it go?"
```

**AFTER (With Unassigned Category)**:

```
Step 1: User clicks [✕] on "Database" in Priority 2
┌────────────────────────────────────────┐
│ Priority 2                             │
│ ┌────────────────────────────────────┐ │
│ │ Frontend              [✕]          │ │
│ │ Database              [✕]  ← Click │ │
│ │ Pattern               [✕]          │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘

Step 2: Field fades out and moves to Unassigned ✅
┌────────────────────────────────────────┐
│ Priority 2                             │
│ ┌────────────────────────────────────┐ │
│ │ Frontend              [✕]          │ │
│ │ Pattern               [✕]          │ │
│ └────────────────────────────────────┘ │
└────────────────────────────────────────┘
        ↓ (animated transition)
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│ Unassigned                             │
│ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ │
│ │ Database              [✕]  ← Added │ │
│ │ Infrastructure        [✕]          │ │
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘

Result: Clear feedback, field visible and recoverable
```

### Comparison 2: Field Inventory Visibility

**BEFORE**:

```
Visible: 7 fields (assigned to P1/P2/P3)
Hidden: 6 fields (removed, nowhere to be found)

User question: "What fields are available? Did I miss any?"
Answer: Unknown ❌
```

**AFTER**:

```
Visible: ALL 13 fields
  - P1: 2 fields
  - P2: 3 fields
  - P3: 2 fields
  - Unassigned: 6 fields

User question: "What fields are available?"
Answer: Scroll down, see all 13 in Unassigned ✅
```

---

## User Flows

### Flow 1: First-Time User Setup

**Goal**: User wants to configure field priorities for the first time

```
Step 1: User navigates to Settings → General
    ↓
Step 2: Sees 4 categories with default assignments
    - P1: 2 fields (Languages, Backend)
    - P2: 3 fields (Frontend, Database, Pattern)
    - P3: 2 fields (API Style, Strategy)
    - Unassigned: 6 fields (remaining)
    ↓
Step 3: User drags "Features > Core" from Unassigned to P1
    - Field moves with animation
    - Token count increases: 1,247 → 1,312 tokens
    ↓
Step 4: User drags "Infrastructure" from Unassigned to P3
    - Field moves with animation
    - Token count increases: 1,312 → 1,340 tokens
    ↓
Step 5: User clicks "Save Changes"
    - Success toast: "Field priorities saved"
    - Changes persist in database
```

### Flow 2: Advanced User Optimization

**Goal**: Experienced user wants to minimize token usage

```
Step 1: User sees token count is high (1,850 / 2,000)
    ↓
Step 2: User drags 3 fields from P2 to Unassigned
    - Database: 1,850 → 1,780
    - API Style: 1,780 → 1,720
    - Frameworks: 1,720 → 1,665
    ↓
Step 3: Token indicator turns green (83%)
    ↓
Step 4: User saves changes
    - Mission generation uses fewer tokens
    - More room for additional context
```

### Flow 3: Accidental Removal Recovery

**Goal**: User accidentally removes critical field

```
Step 1: User clicks [✕] on "Languages" (Priority 1)
    - Intended to remove "Database" but mis-clicked
    ↓
Step 2: Field moves to Unassigned immediately
    - Token count drops significantly
    - User notices error
    ↓
Step 3: User drags "Languages" from Unassigned back to P1
    - Field restored to original position
    - Token count returns to normal
    ↓
Step 4: Crisis averted in <5 seconds ✅
```

### Flow 4: Exploring Available Fields

**Goal**: User wants to see what fields are available

```
Step 1: User scrolls to Unassigned category
    ↓
Step 2: Sees 6 unassigned fields with descriptive names
    - Tech Stack > Infrastructure
    - Architecture > Design Patterns
    - Architecture > Notes
    - Features > Core
    - Test Config > Frameworks
    - Test Config > Coverage Target
    ↓
Step 3: User hovers over "Features > Core"
    - Tooltip shows: "Core features of this product"
    ↓
Step 4: User decides to add to P2 for next mission
    - Drags to P2
    - Saves changes
```

---

## Animation Specifications

### Drag Animation

**Duration**: 200ms
**Easing**: `cubic-bezier(0.4, 0, 0.2, 1)` (ease-in-out)
**Properties**:
- Transform (translate)
- Opacity

**Pseudocode**:
```css
@keyframes field-drag {
  0% {
    transform: translateY(0);
    opacity: 1;
  }
  100% {
    transform: translateY(var(--target-y));
    opacity: 0.6;
  }
}
```

### Remove Animation

**Phase 1: Fade Out** (100ms)
```css
.field-removing {
  opacity: 0;
  transform: scale(0.8);
  transition: all 100ms ease-in;
}
```

**Phase 2: Reflow** (100ms)
- Remaining fields shift to fill gap
- Smooth collapse animation

**Phase 3: Fade In to Unassigned** (200ms)
```css
.field-appearing {
  opacity: 0;
  transform: scale(0.8) translateY(-20px);
  animation: appear 200ms ease-out forwards;
}

@keyframes appear {
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
```

### Token Count Animation

**Number Transition** (500ms)
```javascript
// Use animated counter library or custom implementation
function animateValue(start, end, duration) {
  const range = end - start
  const startTime = performance.now()

  function update() {
    const elapsed = performance.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    const current = start + (range * easeOutQuad(progress))

    display(Math.round(current))

    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }

  requestAnimationFrame(update)
}
```

---

## Tooltips & Help Text

### Unassigned Category Header Tooltip

**Trigger**: Hover over info icon (ⓘ)

**Content**:
```
Fields in this category are NOT sent to AI agents
during mission generation.

Drag a field to Priority 1, 2, or 3 to include
it in agent missions and allocate token budget.
```

### Field Name Tooltips (Optional Future Enhancement)

**Trigger**: Hover over field chip for 500ms

**Content** (example for "Tech Stack > Languages"):
```
Tech Stack > Languages

Description: Programming languages used in this
product (e.g., Python, JavaScript, TypeScript)

Current value: "Python 3.11+, TypeScript 5.0"
Estimated tokens: 12

Click to view/edit in Product settings
```

### Empty State Help Text

**Priority Categories (Empty)**:
```
Drag fields here to assign [Priority Name]

Fields in this category receive [priority description]
and contribute to token budget allocation.
```

**Unassigned Category (Empty)**:
```
✓ All fields assigned to priorities

You've assigned all 13 available fields to priority
categories. Great job optimizing your configuration!
```

---

## Success Criteria (UX Metrics)

### Quantitative Metrics

- **Field Recovery Time**: <5 seconds from removal to restoration
- **Drag Operation Latency**: <100ms from drop to visual feedback
- **Token Recalculation**: <300ms after field movement
- **Animation Smoothness**: 60 FPS during all transitions

### Qualitative Metrics

- **User Confidence**: 90%+ of users feel confident experimenting with priorities
- **Error Recovery**: 95%+ of accidental removals recovered within 10 seconds
- **Clarity**: 100% of users understand Unassigned category purpose within 30 seconds
- **Satisfaction**: 4.5/5 average rating on post-implementation survey

---

**Document Status**: Approved for Implementation
**Next Steps**: See `IMPLEMENTATION_GUIDE.md` for development instructions

**End of UX_SPECIFICATION.md**
