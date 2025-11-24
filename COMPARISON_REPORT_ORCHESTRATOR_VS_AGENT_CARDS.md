# Detailed Line-by-Line Comparison Report
## Orchestrator Card vs Agent Cards in LaunchTab.vue

**File:** `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue`
**Analysis Date:** 2025-11-23
**Report Type:** CSS/HTML Structure Comparison

---

## EXECUTIVE SUMMARY

The orchestrator card (lines 39-56) and agent slim cards (lines 63-90) have **12 major CSS/HTML inconsistencies** that create visual misalignment. The primary issues are:

1. **Avatar Size Mismatch:** 32px vs 40px (8px difference)
2. **Icon Rendering Differences:** Orchestrator icons lack flexbox centering
3. **Color Inconsistencies:** Eye icon uses darker color than edit icon
4. **Spacing Irregularities:** margin-bottom differs by 8px
5. **Accessibility Gaps:** Eye icon missing role/tabindex attributes
6. **Over-Engineering:** Agent icons have excessive CSS properties

---

## PART 1: HTML STRUCTURE COMPARISON

### Orchestrator Card HTML (Lines 39-56)

```html
39 │ <div class="orchestrator-card">
40 │   <v-avatar :color="orchestratorAvatarColor" size="32" class="agent-avatar">
41 │     <span class="orchestrator-text">Or</span>
42 │   </v-avatar>
43 │   <span class="agent-name">Orchestrator</span>
44 │   <v-icon size="small" class="eye-icon" title="View orchestrator details (read-only)">mdi-eye</v-icon>
45 │   <v-icon
46 │     size="small"
47 │     class="info-icon"
48 │     role="button"
49 │     tabindex="0"
50 │     title="View orchestrator template"
51 │     @click="handleOrchestratorInfo"
52 │     @keydown.enter="handleOrchestratorInfo"
53 │   >
54 │     mdi-information
55 │   </v-icon>
56 │ </div>
```

**Key Component Properties:**
- **Avatar Type:** `<v-avatar>` (Vuetify component)
- **Avatar Color Method:** `:color="orchestratorAvatarColor"` (computed property)
- **Avatar Size:** `size="32"` (explicit Vuetify prop)
- **Avatar Text:** Wrapped in `<span class="orchestrator-text">`
- **Name:** Static text `"Orchestrator"`
- **Icon 1 (Eye):** Simple v-icon, NO role/tabindex, NO @click handler
- **Icon 2 (Info):** v-icon WITH role/tabindex, WITH @click/@keydown handlers

---

### Agent Card HTML (Lines 63-90)

```html
63 │ <div
64 │   v-for="agent in nonOrchestratorAgents"
65 │   :key="agent.agent_id || agent.job_id"
66 │   class="agent-slim-card"
67 │ >
68 │   <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
69 │     {{ getAgentInitials(agent.agent_type) }}
70 │   </div>
71 │   <span class="agent-name">{{ agent.agent_type }}</span>
72 │   <v-icon
73 │     size="small"
73 │     class="edit-icon"
74 │     role="button"
75 │     tabindex="0"
76 │     title="Edit agent configuration"
77 │     @click="handleAgentEdit(agent)"
78 │     @keydown.enter="handleAgentEdit(agent)"
79 │   >mdi-pencil</v-icon>
80 │   <v-icon
81 │     size="small"
82 │     class="info-icon"
83 │     role="button"
84 │     tabindex="0"
85 │     title="View agent template"
86 │     @click="handleAgentInfo(agent)"
87 │     @keydown.enter="handleAgentInfo(agent)"
88 │   >mdi-information</v-icon>
89 │ </div>
90 │ </div>
```

**Key Component Properties:**
- **Avatar Type:** Plain `<div>` (NOT Vuetify component)
- **Avatar Color Method:** `:style="{background: getAgentColor()}"` (inline style binding)
- **Avatar Size:** NO explicit size attribute (relies on CSS 40px)
- **Avatar Text:** Direct text node `{{ getAgentInitials() }}`
- **Name:** Bound data `{{ agent.agent_type }}`
- **Icon 1 (Edit):** v-icon WITH role/tabindex, WITH @click/@keydown handlers
- **Icon 2 (Info):** v-icon WITH role/tabindex, WITH @click/@keydown handlers

---

### HTML Structure Difference Table

| Aspect | Orchestrator | Agent | Difference | Severity |
|--------|---|---|---|---|
| **Container Element** | `<div class="orchestrator-card">` | `<div class="agent-slim-card">` | Different class names | LOW |
| **Avatar Component** | `<v-avatar>` Vuetify component | Plain `<div>` | Different component type | HIGH - Should standardize |
| **Avatar Color** | `:color="prop"` | `:style="{background: fn()}"` | Different binding method | MEDIUM - Both work |
| **Avatar Size Attribute** | `size="32"` (Vuetify prop) | None (CSS only) | Size mismatch - 32px vs 40px | **CRITICAL** |
| **Avatar Text Container** | `<span>` element | Direct text node | Different wrapping | LOW - No visual impact |
| **First Icon Type** | `.eye-icon` (view-only) | `.edit-icon` (editable) | Different purpose | LOW - Intentional |
| **First Icon role/tabindex** | **MISSING** (BUG) | Present | Accessibility gap | **HIGH - WCAG violation** |
| **First Icon @click** | MISSING (BUG) | Present | Interactivity gap | **HIGH - Can't interact** |
| **Second Icon Type** | `.info-icon` | `.info-icon` | SAME | ✓ Good |
| **Second Icon role/tabindex** | Present | Present | SAME | ✓ Good |
| **Second Icon @click** | Present | Present | SAME | ✓ Good |

---

## PART 2: CSS STYLING - DEEP DIVE

### Container Styling Comparison

#### Orchestrator Card (Lines 562-569)

```scss
562 │ .orchestrator-card {
563 │   display: flex;
564 │   align-items: center;
565 │   gap: 12px;
566 │   border: $border-width-standard solid $color-text-highlight;
567 │   border-radius: $border-radius-pill;
568 │   padding: 12px 20px;
569 │   margin-bottom: 20px;
570 │ }
```

#### Agent Card (Lines 647-655)

```scss
647 │ .agent-slim-card {
648 │   display: flex;
649 │   align-items: center;
650 │   gap: 12px;
651 │   border: 2px solid $color-text-highlight;
652 │   border-radius: $border-radius-pill;
653 │   padding: 12px 20px;
654 │   margin-bottom: 12px;
655 │   background: transparent;
656 │ }
```

#### Container Differences Table

| Property | Orchestrator | Agent | Design Token Value | Difference | Impact |
|----------|---|---|---|---|---|
| `display` | `flex` | `flex` | N/A | ✓ SAME | Good alignment |
| `align-items` | `center` | `center` | N/A | ✓ SAME | Good vertical centering |
| `gap` | `12px` | `12px` | N/A | ✓ SAME | Good spacing between items |
| **`border`** | `$border-width-standard solid` | `2px solid` | `$border-width-standard` = `1px` | **MISMATCH** | **Orchestrator 1px, Agent 2px** |
| `border-radius` | `$border-radius-pill` | `$border-radius-pill` | `24px` | ✓ SAME | Good pill shape |
| `padding` | `12px 20px` | `12px 20px` | N/A | ✓ SAME | Good internal spacing |
| **`margin-bottom`** | `20px` | `12px` | N/A | **MISMATCH** | **8px difference - Orchestrator spaced further below** |
| **`background`** | Not set (inherits) | `transparent` | N/A | **DIFFERENT** | Agent explicitly transparent |

**Container Analysis:**
- **Border Width Issue:** Orchestrator uses `$border-width-standard` (likely 1px) while agent hardcodes `2px`
- **Margin Issue:** Orchestrator has 20px bottom margin vs agent's 12px (8px visual gap)
- **Background:** Agent explicitly sets transparent to override parent; orchestrator relies on inheritance

---

### Avatar Styling Comparison

#### Orchestrator Avatar (Lines 571-579)

```scss
571 │ .orchestrator-card .agent-avatar {
572 │   width: 40px;
573 │   height: 40px;
574 │   border-radius: 50%;
575 │   display: flex;
576 │   align-items: center;
577 │   justify-content: center;
578 │   flex-shrink: 0;
579 │ }
```

#### Agent Avatar (Lines 657-667)

```scss
657 │ .agent-slim-card .agent-avatar {
658 │   width: 40px;
659 │   height: 40px;
660 │   border-radius: 50%;
661 │   display: flex;
662 │   align-items: center;
663 │   justify-content: center;
664 │   color: white;
665 │   font-weight: $typography-font-weight-bold;
666 │   font-size: 14px;
667 │ }
```

**BUT WAIT - HTML Avatar Size Mismatch:**

The HTML reveals the actual problem:
```html
40 │ <v-avatar :color="orchestratorAvatarColor" size="32" class="agent-avatar">
```

**ACTUAL SIZES:**
- Orchestrator: `size="32"` in HTML overrides CSS, makes avatar **32px × 32px**
- Agent: CSS sets `width: 40px; height: 40px`, makes avatar **40px × 40px**

#### Avatar Differences Table

| Property | Orchestrator | Agent | Actual Size | Difference | Impact |
|----------|---|---|---|---|---|
| `width` | CSS: `40px` | CSS: `40px` | HTML: `32px` (wins!) | **8px size mismatch** | **CRITICAL** |
| `height` | CSS: `40px` | CSS: `40px` | HTML: `32px` (wins!) | **8px size mismatch** | **CRITICAL** |
| `border-radius` | `50%` | `50%` | `50%` | ✓ SAME | Good circles |
| `display` | `flex` | `flex` | `flex` | ✓ SAME | Good centering |
| `align-items` | `center` | `center` | `center` | ✓ SAME | Vertical centering |
| `justify-content` | `center` | `center` | `center` | ✓ SAME | Horizontal centering |
| **`flex-shrink`** | `0` | **NOT SET** | Orchestrator: `0` / Agent: default | **DIFFERENT** | Agent can shrink; Orchestrator cannot |
| **`color`** | NOT SET | `white` | N/A | **DIFFERENT** | Agent text styled in avatar; Orch in span |
| **`font-weight`** | NOT SET | `bold` (14px) | N/A | **DIFFERENT** | Agent text styled in avatar; Orch in span |
| **`font-size`** | NOT SET | `14px` | N/A | **DIFFERENT** | Agent text styled in avatar; Orch in span |

**Avatar Analysis:**
- **Critical Bug:** Orchestrator avatar is 32px while agent avatars are 40px (8px smaller!)
- **Root Cause:** v-avatar `size="32"` prop in HTML overrides CSS width/height declarations
- **Text Styling:** Orchestrator uses separate `<span>` for styling; Agent uses avatar div styling
- **Shrinking:** Orchestrator won't shrink; Agent can (missing `flex-shrink: 0`)

---

### Agent Name Styling

#### Orchestrator Name (Lines 587-591)

```scss
587 │ .orchestrator-card .agent-name {
588 │   flex: 1;
589 │   color: $color-text-primary;
590 │   font-size: $typography-font-size-body;
591 │ }
```

#### Agent Name (Lines 669-674)

```scss
669 │ .agent-slim-card .agent-name {
670 │   flex: 1;
671 │   color: $color-text-primary;
572 │   font-size: $typography-font-size-body;
673 │   text-transform: capitalize;
674 │ }
```

#### Name Differences Table

| Property | Orchestrator | Agent | Token Value | Difference | Impact |
|----------|---|---|---|---|---|
| `flex` | `1` | `1` | N/A | ✓ SAME | Good spacing |
| `color` | `$color-text-primary` | `$color-text-primary` | `#e0e0e0` | ✓ SAME | Good contrast |
| `font-size` | `$typography-font-size-body` | `$typography-font-size-body` | `0.875rem` (14px) | ✓ SAME | Good readability |
| **`text-transform`** | NOT SET | `capitalize` | N/A | **DIFFERENT** | "Orchestrator" stays as-is; "analyzer" becomes "Analyzer" |

**Name Analysis:**
- Text color and size are consistent
- Agent capitalizes the agent_type name (good for "analyzer" → "Analyzer")
- Orchestrator doesn't capitalize (works fine for "Orchestrator")

---

### Eye vs Edit Icon Styling

#### Orchestrator Eye Icon (Lines 593-597)

```scss
593 │ .orchestrator-card .eye-icon {
594 │   color: $color-text-tertiary;
595 │   flex-shrink: 0;
596 │   margin-right: 4px;  // Reduced to 4px for tighter spacing
597 │ }
```

#### Agent Edit Icon (Lines 676-692)

```scss
676 │ .agent-slim-card .edit-icon {
677 │   color: $color-text-secondary;
678 │   flex-shrink: 0;
679 │   cursor: pointer;
680 │   transition: color 0.2s ease;
681 │   margin-right: 4px;  // Reduced from 8px to match orchestrator
682 │   display: inline-flex;  // Ensure icon renders properly
683 │   align-items: center;   // Vertically center within flex container
684 │   justify-content: center; // Center icon content
685 │   min-width: 24px;       // Minimum width to ensure visibility
686 │   visibility: visible;   // Explicit visibility
687 │   opacity: 1;            // Ensure full opacity
688 │
689 │   &:hover {
690 │     color: $color-text-highlight;
691 │   }
691 │ }
```

#### Icon Differences Table

| Property | Eye (Orch) | Edit (Agent) | Difference | Impact |
|----------|---|---|---|---|
| `color` | `$color-text-tertiary` | `$color-text-secondary` | **DIFFERENT** | Eye darker (#ccc) vs Edit lighter (#999) - WRONG! |
| `flex-shrink` | `0` | `0` | ✓ SAME | Good |
| `margin-right` | `4px` | `4px` | ✓ SAME | Good |
| **`cursor`** | NOT SET | `pointer` | **DIFFERENT** | Eye not interactive-looking; Edit is |
| **`transition`** | NOT SET | `color 0.2s ease` | **DIFFERENT** | Edit has hover animation; Eye doesn't |
| **`display`** | NOT SET | `inline-flex` | **DIFFERENT** | Edit centered; Eye not |
| **`align-items`** | NOT SET | `center` | **DIFFERENT** | Edit vertically centered; Eye not |
| **`justify-content`** | NOT SET | `center` | **DIFFERENT** | Edit horizontally centered; Eye not |
| **`min-width`** | NOT SET | `24px` | **DIFFERENT** | Edit has 24px min; Eye natural size (~16px) |
| **`visibility`** | NOT SET | `visible` | **DIFFERENT** | Edit explicit; Eye default |
| **`opacity`** | NOT SET | `1` | **DIFFERENT** | Edit explicit; Eye default |
| **`&:hover color`** | NOT SET | `$color-text-highlight` | **DIFFERENT** | Edit changes on hover; Eye doesn't |

**Color Bug Found!**
```
Eye Icon (Orchestrator):    $color-text-tertiary = #ccc (LIGHTER - WRONG!)
Edit Icon (Agent):         $color-text-secondary = #999 (DARKER - MORE CORRECT)
```

The eye icon is actually LIGHTER than the edit icon, making it harder to see!

**Icon Analysis - Root Cause of Spacing Illusion:**

The apparent spacing difference between edit+info and eye+info is caused by:

1. **Eye Icon (Orchestrator):**
   - No `display: inline-flex`
   - No `min-width`
   - Renders at natural v-icon size (~16px)
   - Total bounding box: ~16px

2. **Edit Icon (Agent):**
   - HAS `display: inline-flex`
   - HAS `min-width: 24px`
   - Renders with explicit 24px bounding box
   - Total bounding box: 24px

3. **Visual Result:**
   ```
   Orchestrator: [Avatar] [Name_______________] [Eye ~16px] [Info ~16px]
   Agent:        [Avatar] [Name_______________] [Edit 24px] [Info 24px]
   ```
   - Edit icon takes 8px MORE space than eye icon
   - Creates illusion of more spacing between icons

---

### Info Icon Styling

#### Orchestrator Info Icon (Lines 599-608)

```scss
599 │ .orchestrator-card .info-icon {
600 │   color: $color-text-tertiary;
601 │   flex-shrink: 0;
602 │   cursor: pointer;
603 │   transition: color 0.2s ease;
604 │
605 │   &:hover {
606 │     color: $color-text-highlight;
607 │   }
608 │ }
```

#### Agent Info Icon (Lines 694-709)

```scss
694 │ .agent-slim-card .info-icon {
695 │   color: $color-text-secondary;
696 │   flex-shrink: 0;
697 │   cursor: pointer;
698 │   transition: color 0.2s ease;
699 │   display: inline-flex;  // Ensure icon renders properly
700 │   align-items: center;   // Vertically center within flex container
701 │   justify-content: center; // Center icon content
702 │   min-width: 24px;       // Minimum width to ensure visibility
703 │   visibility: visible;   // Explicit visibility
704 │   opacity: 1;            // Ensure full opacity
705 │
706 │   &:hover {
707 │     color: $color-text-highlight;
708 │   }
709 │ }
```

#### Info Icon Differences Table

| Property | Orchestrator | Agent | Difference | Impact |
|----------|---|---|---|---|
| `color` | `$color-text-tertiary` | `$color-text-secondary` | **DIFFERENT** | Orch darker (#ccc) vs Agent lighter (#999) - INCONSISTENT |
| `flex-shrink` | `0` | `0` | ✓ SAME | Good |
| `cursor` | `pointer` | `pointer` | ✓ SAME | Good |
| `transition` | `color 0.2s ease` | `color 0.2s ease` | ✓ SAME | Good |
| **`display`** | NOT SET | `inline-flex` | **DIFFERENT** | Agent centered; Orch not |
| **`align-items`** | NOT SET | `center` | **DIFFERENT** | Agent vertically centered; Orch not |
| **`justify-content`** | NOT SET | `center` | **DIFFERENT** | Agent horizontally centered; Orch not |
| **`min-width`** | NOT SET | `24px` | **DIFFERENT** | Agent has 24px min; Orch natural (~16px) |
| **`visibility`** | NOT SET | `visible` | **DIFFERENT** | Agent explicit; Orch default |
| **`opacity`** | NOT SET | `1` | **DIFFERENT** | Agent explicit; Orch default |
| **`&:hover color`** | `$color-text-highlight` | `$color-text-highlight` | ✓ SAME | Good hover effect |

**Info Icon Analysis:**
- Same color inconsistency as eye/edit icons
- Both info icons over-engineered with unnecessary flexbox for a 24px element
- Should be simplified

---

## PART 3: ROOT CAUSE ANALYSIS

### Root Cause #1: Avatar Size Mismatch (32px vs 40px)

**Problem:** Orchestrator avatar appears 8px smaller than agent avatars

**Root Cause:**
```html
<!-- Orchestrator HTML (Line 40) -->
<v-avatar :color="orchestratorAvatarColor" size="32" class="agent-avatar">
                                              ^^^^^^^^
                                         THIS overrides CSS!

<!-- Agent HTML (Line 68) -->
<div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_type) }">
  {{getAgentInitials()}}
</div>
<!-- CSS: width: 40px; height: 40px -->
```

**Why It Happens:**
- Vuetify's `<v-avatar>` `size` prop generates inline styles that override CSS
- Agent cards use plain `<div>` which respects CSS width/height
- The CSS targets both with `.agent-avatar` class but HTML props take precedence

**Fix:** Change line 40 from `size="32"` to `size="40"` or `size="large"`

---

### Root Cause #2: Icon Rendering and Spacing Illusion

**Problem:** Icons appear to have different spacing due to different bounding boxes

**Root Cause:**

v-icon elements render at different sizes:

```scss
/* Orchestrator eye-icon (Lines 593-597) */
.eye-icon {
  color: $color-text-tertiary;
  flex-shrink: 0;
  margin-right: 4px;
  /* NO display, align-items, justify-content, min-width */
  /* Results in natural v-icon rendering (~16px) */
}

/* Agent edit-icon (Lines 676-692) */
.edit-icon {
  color: $color-text-secondary;
  flex-shrink: 0;
  margin-right: 4px;
  display: inline-flex;        /* Forces 24px bounding box */
  align-items: center;
  justify-content: center;
  min-width: 24px;             /* 24px minimum! */
  visibility: visible;
  opacity: 1;
  /* Results in 24px bounding box */
}
```

**Spacing Math:**
```
Orchestrator:
[Avatar: 40px] + [gap: 12px] + [Name: flex] + [Eye: ~16px] + [gap: 12px] + [Info: ~16px]
Total icon space: ~32px

Agent:
[Avatar: 40px] + [gap: 12px] + [Name: flex] + [Edit: 24px] + [gap: 12px] + [Info: 24px]
Total icon space: 48px

Difference: 16px extra space on agent cards!
```

---

### Root Cause #3: Color Inconsistency

**Problem:** Eye icon uses darker color (#ccc) than edit icon (#999)

**Current Color Mapping:**
```
Eye Icon:   $color-text-tertiary = #ccc (lighter - WRONG!)
Edit Icon:  $color-text-secondary = #999 (darker - MORE CORRECT)
Info Icon:  $color-text-tertiary = #ccc (orch) vs $color-text-secondary = #999 (agent)
```

**Design Token Values (from design-tokens.scss):**
```scss
$color-text-primary: #e0e0e0;    // Main text (brightest)
$color-text-secondary: #999;      // Labels, headers (medium)
$color-text-tertiary: #ccc;       // Subdued text (lighter - should be darkest?)
$color-text-highlight: #ffd700;   // Yellow
```

**The Bug:** The naming is backwards! Tertiary (subtler) should be darker than secondary.

---

### Root Cause #4: Margin-Bottom Inconsistency

**Problem:** Different vertical spacing between orchestrator and agent cards

```scss
.orchestrator-card {
  margin-bottom: 20px;  /* 8px MORE than agent */
}

.agent-slim-card {
  margin-bottom: 12px;  /* Standard gap between cards */
}
```

**Visual Impact:**
```
Orchestrator Card
[20px gap]          ← Extra space between orch and first agent
Agent Card 1
[12px gap]          ← Standard gap
Agent Card 2
[12px gap]          ← Standard gap
```

**Root Cause:** Inconsistent spacing definition during card implementation

---

## PART 4: COMPREHENSIVE CORRECTION GUIDE

### Critical Issues (Must Fix)

#### Issue #1: Avatar Size Mismatch
**Severity:** CRITICAL
**Lines Affected:** Line 40 (HTML)
**Current:**
```html
<v-avatar :color="orchestratorAvatarColor" size="32" class="agent-avatar">
```

**Fix:**
```html
<v-avatar :color="orchestratorAvatarColor" size="40" class="agent-avatar">
```

**Verification:** Both avatars should be 40px × 40px

---

#### Issue #2: Eye Icon Missing Accessibility Attributes
**Severity:** CRITICAL (WCAG Violation)
**Lines Affected:** Lines 44 (HTML)
**Current:**
```html
<v-icon size="small" class="eye-icon" title="View orchestrator details (read-only)">mdi-eye</v-icon>
```

**Fix:**
```html
<v-icon
  size="small"
  class="eye-icon"
  role="button"
  tabindex="0"
  title="View orchestrator details (read-only)"
  @click="handleOrchestratorView"
  @keydown.enter="handleOrchestratorView"
>mdi-eye</v-icon>
```

**Note:** Requires new handler `handleOrchestratorView()` or link to existing handler

---

### High Priority Issues (Should Fix)

#### Issue #3: Avatar Component Inconsistency
**Severity:** HIGH
**Lines Affected:** Lines 40 (Orch) vs 68 (Agent)
**Current:**
- Orchestrator: `<v-avatar>` component
- Agent: Plain `<div>`

**Recommendation:** Standardize to plain `<div>` for both
```html
<!-- Orchestrator -->
<div class="agent-avatar" :style="{ background: orchestratorAvatarColor }">
  <span class="orchestrator-text">Or</span>
</div>
```

**Benefit:** Removes Vuetify size prop override issue, cleaner styling

---

#### Issue #4: Icon Over-Engineering
**Severity:** HIGH
**Lines Affected:** Lines 682-687 (edit), 699-704 (info in agent)
**Current:**
```scss
.edit-icon {
  color: $color-text-secondary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;
  margin-right: 4px;
  display: inline-flex;      /* Unnecessary for v-icon */
  align-items: center;       /* Unnecessary for v-icon */
  justify-content: center;   /* Unnecessary for v-icon */
  min-width: 24px;          /* Makes icon take 8px more space */
  visibility: visible;       /* Default behavior */
  opacity: 1;               /* Default behavior */

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Fix:**
```scss
.edit-icon {
  color: $color-text-secondary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Benefit:** Removes 8px extra spacing, matches natural v-icon rendering

---

#### Issue #5: Color Inconsistency (Eye Icon Darker Than Edit)
**Severity:** HIGH
**Lines Affected:** Lines 594 (eye) vs 677 (edit)
**Current:**
```scss
.eye-icon {
  color: $color-text-tertiary;  /* #ccc - LIGHTER! */
  ...
}

.edit-icon {
  color: $color-text-secondary; /* #999 - DARKER */
  ...
}
```

**Fix:**
```scss
.eye-icon {
  color: $color-text-secondary; /* #999 - match edit icon */
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}

.edit-icon {
  color: $color-text-secondary; /* #999 - match eye icon */
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

---

### Medium Priority Issues (Consider Fixing)

#### Issue #6: Info Icon Color Inconsistency
**Severity:** MEDIUM
**Lines Affected:** Lines 600 (orch) vs 695 (agent)
**Current:**
```scss
.orchestrator-card .info-icon {
  color: $color-text-tertiary; /* #ccc */
}

.agent-slim-card .info-icon {
  color: $color-text-secondary; /* #999 */
}
```

**Recommendation:** Standardize both to `$color-text-secondary`

---

#### Issue #7: Avatar Text Styling Inconsistency
**Severity:** MEDIUM
**Lines Affected:** Lines 581-585 (orch) vs 664-666 (agent)

**Current:**
- Orchestrator: Text in `<span class="orchestrator-text">`
- Agent: Text directly in `.agent-avatar` div

**Recommendation:** Standardize both to style text directly in avatar element

---

#### Issue #8: Margin-Bottom Inconsistency
**Severity:** MEDIUM
**Lines Affected:** Lines 569 (orch) vs 654 (agent)
**Current:**
```scss
.orchestrator-card {
  margin-bottom: 20px; /* 8px MORE */
}

.agent-slim-card {
  margin-bottom: 12px;
}
```

**Fix:**
```scss
.orchestrator-card {
  margin-bottom: 12px; /* Standardize */
}

.agent-slim-card {
  margin-bottom: 12px;
}
```

---

#### Issue #9: Border Width Hardcoding
**Severity:** LOW
**Lines Affected:** Lines 566 (orch) vs 651 (agent)
**Current:**
```scss
.orchestrator-card {
  border: $border-width-standard solid $color-text-highlight; /* Variable */
}

.agent-slim-card {
  border: 2px solid $color-text-highlight; /* Hardcoded */
}
```

**Recommendation:** Use token for both
```scss
.agent-slim-card {
  border: $border-width-standard solid $color-text-highlight;
}
```

---

#### Issue #10: Text Transform on Agent Names
**Severity:** LOW
**Lines Affected:** Line 673 (agent)
**Current:**
```scss
.agent-slim-card .agent-name {
  text-transform: capitalize; /* Capitalizes agent_type */
}
```

**Note:** This is intentional (converts "analyzer" to "Analyzer"), not a bug

---

## PART 5: VISUAL COMPARISON TABLES

### Container Properties Summary

```
┌────────────────────────────────────┬──────────────┬──────────────┬─────────────┐
│ Property                           │ Orchestrator │ Agent        │ Status      │
├────────────────────────────────────┼──────────────┼──────────────┼─────────────┤
│ Display                            │ flex         │ flex         │ ✓ MATCH     │
│ Align-items                        │ center       │ center       │ ✓ MATCH     │
│ Gap                                │ 12px         │ 12px         │ ✓ MATCH     │
│ Border                             │ 1px token    │ 2px hardcode │ ✗ MISMATCH  │
│ Border-radius                      │ 24px token   │ 24px token   │ ✓ MATCH     │
│ Padding                            │ 12px 20px    │ 12px 20px    │ ✓ MATCH     │
│ Margin-bottom                      │ 20px         │ 12px         │ ✗ MISMATCH  │
│ Background                         │ inherit      │ transparent  │ ✗ DIFFERENT │
└────────────────────────────────────┴──────────────┴──────────────┴─────────────┘
```

### Avatar Properties Summary

```
┌────────────────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Property                           │ Orchestrator │ Agent        │ Status       │
├────────────────────────────────────┼──────────────┼──────────────┼──────────────┤
│ Component Type                     │ v-avatar     │ plain div    │ ✗ DIFFERENT  │
│ Width (actual)                     │ 32px (BUG)   │ 40px         │ ✗ 8px diff   │
│ Height (actual)                    │ 32px (BUG)   │ 40px         │ ✗ 8px diff   │
│ Border-radius                      │ 50%          │ 50%          │ ✓ MATCH      │
│ Display                            │ flex         │ flex         │ ✓ MATCH      │
│ Align-items                        │ center       │ center       │ ✓ MATCH      │
│ Justify-content                    │ center       │ center       │ ✓ MATCH      │
│ Flex-shrink                        │ 0            │ not set      │ ✗ DIFFERENT  │
│ Text color                         │ in span      │ white        │ ✗ DIFFERENT  │
│ Text font-weight                   │ in span      │ bold         │ ✗ DIFFERENT  │
│ Text font-size                     │ in span      │ 14px         │ ✗ DIFFERENT  │
└────────────────────────────────────┴──────────────┴──────────────┴──────────────┘
```

### Icon Properties Summary

```
┌────────────────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Property                           │ Eye (Orch)   │ Edit (Agent) │ Status       │
├────────────────────────────────────┼──────────────┼──────────────┼──────────────┤
│ Color                              │ tertiary#ccc │ secondary#99 │ ✗ MISMATCH   │
│ Flex-shrink                        │ 0            │ 0            │ ✓ MATCH      │
│ Cursor                             │ not set      │ pointer      │ ✗ DIFFERENT  │
│ Transition                         │ not set      │ color 0.2s   │ ✗ DIFFERENT  │
│ Margin-right                       │ 4px          │ 4px          │ ✓ MATCH      │
│ Display                            │ not set      │ inline-flex  │ ✗ DIFFERENT  │
│ Align-items                        │ not set      │ center       │ ✗ DIFFERENT  │
│ Justify-content                    │ not set      │ center       │ ✗ DIFFERENT  │
│ Min-width                          │ not set      │ 24px         │ ✗ DIFFERENT  │
│ Visibility                         │ not set      │ visible      │ ✗ DIFFERENT  │
│ Opacity                            │ not set      │ 1            │ ✗ DIFFERENT  │
│ Actual bounding box                │ ~16px        │ 24px         │ ✗ 8px diff   │
│ Role (accessibility)               │ MISSING ✗    │ button       │ ✗ WCAG BUG   │
│ Tabindex (accessibility)           │ MISSING ✗    │ 0            │ ✗ WCAG BUG   │
└────────────────────────────────────┴──────────────┴──────────────┴──────────────┘
```

---

## PART 6: IMPLEMENTATION SUMMARY

### Files to Modify
- `F:\GiljoAI_MCP\frontend\src\components\projects\LaunchTab.vue` (HTML + SCSS)

### Changes Required

#### 1. HTML Changes (High Priority)

**Line 40 - Fix Avatar Size**
```html
<!-- Before -->
<v-avatar :color="orchestratorAvatarColor" size="32" class="agent-avatar">

<!-- After -->
<v-avatar :color="orchestratorAvatarColor" size="40" class="agent-avatar">
```

**Lines 44 - Add Accessibility to Eye Icon**
```html
<!-- Before -->
<v-icon size="small" class="eye-icon" title="View orchestrator details (read-only)">mdi-eye</v-icon>

<!-- After -->
<v-icon
  size="small"
  class="eye-icon"
  role="button"
  tabindex="0"
  title="View orchestrator details (read-only)"
  @click="handleOrchestratorDetails"
  @keydown.enter="handleOrchestratorDetails"
>mdi-eye</v-icon>
```

#### 2. CSS Changes (High Priority)

**Lines 593-597 - Fix Eye Icon Styling**
```scss
/* Before */
.eye-icon {
  color: $color-text-tertiary;
  flex-shrink: 0;
  margin-right: 4px;
}

/* After */
.eye-icon {
  color: $color-text-secondary;  /* Match edit icon color */
  flex-shrink: 0;
  cursor: pointer;               /* Add interactivity */
  transition: color 0.2s ease;   /* Add hover animation */

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Lines 599-608 - Standardize Info Icon (Orchestrator)**
```scss
/* Before */
.info-icon {
  color: $color-text-tertiary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}

/* After */
.info-icon {
  color: $color-text-secondary;  /* Match agent info-icon */
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Lines 569 - Fix Orchestrator Margin**
```scss
/* Before */
.orchestrator-card {
  display: flex;
  align-items: center;
  gap: 12px;
  border: $border-width-standard solid $color-text-highlight;
  border-radius: $border-radius-pill;
  padding: 12px 20px;
  margin-bottom: 20px;  /* ← Change this */
}

/* After */
.orchestrator-card {
  display: flex;
  align-items: center;
  gap: 12px;
  border: $border-width-standard solid $color-text-highlight;
  border-radius: $border-radius-pill;
  padding: 12px 20px;
  margin-bottom: 12px;  /* ← Standardized */
}
```

**Lines 676-692 - Simplify Edit Icon**
```scss
/* Before */
.edit-icon {
  color: $color-text-secondary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;
  margin-right: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  visibility: visible;
  opacity: 1;

  &:hover {
    color: $color-text-highlight;
  }
}

/* After */
.edit-icon {
  color: $color-text-secondary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Lines 694-709 - Simplify Agent Info Icon**
```scss
/* Before */
.info-icon {
  color: $color-text-secondary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  visibility: visible;
  opacity: 1;

  &:hover {
    color: $color-text-highlight;
  }
}

/* After */
.info-icon {
  color: $color-text-secondary;
  flex-shrink: 0;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: $color-text-highlight;
  }
}
```

**Lines 651 - Fix Border Width in Agent Card**
```scss
/* Before */
border: 2px solid $color-text-highlight;

/* After */
border: $border-width-standard solid $color-text-highlight;
```

#### 3. JavaScript Changes (Medium Priority)

Add handler for eye icon click:
```javascript
/**
 * Handle Eye icon click for Orchestrator (view details)
 */
function handleOrchestratorDetails() {
  selectedAgent.value = {
    agent_type: 'orchestrator',
    agent_name: 'Orchestrator',
    id: 'orchestrator',
  }
  showDetailsModal.value = true
}
```

---

## PART 7: TESTING CHECKLIST

After implementing fixes, verify:

- [ ] Orchestrator avatar is exactly 40px × 40px (matches agent avatars)
- [ ] All 4 icons (eye, edit, both info) are the same size (~16px natural)
- [ ] Eye icon responds to click (is it functional?)
- [ ] Eye icon can be tabbed to (keyboard navigation)
- [ ] Eye icon changes color on hover
- [ ] Edit icon responds to click
- [ ] Both info icons respond to click
- [ ] Vertical spacing between orchestrator and agent cards is consistent (12px margin-bottom)
- [ ] No excessive spacing between edit and info icons
- [ ] All icons have the same visual hierarchy (color #999)
- [ ] Visual alignment is perfect in both normal and zoomed views (100%, 110%, 120%)
- [ ] Responsive design still works at different breakpoints
- [ ] Accessibility: All icons are keyboard accessible
- [ ] Accessibility: Tab order is logical
- [ ] Accessibility: Screen reader announces icons properly

---

## CONCLUSION

The orchestrator and agent cards have **12 major inconsistencies** across HTML structure and CSS styling. The critical issues are:

1. **Avatar size mismatch** (32px vs 40px) - Simple HTML fix
2. **Eye icon missing accessibility** (no role/tabindex) - WCAG violation
3. **Icon over-engineering** (unnecessary flexbox causing spacing issues)
4. **Color inconsistencies** (eye icon darker than edit icon)
5. **Margin inconsistencies** (20px vs 12px)

All issues are fixable with changes to `LaunchTab.vue`. Once corrected, both card types will be perfectly aligned and accessible.

