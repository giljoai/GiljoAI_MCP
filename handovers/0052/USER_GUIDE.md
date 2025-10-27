# Field Priority Configuration - User Guide

**Feature Version**: v3.1 (Handover 0052)
**Last Updated**: 2025-10-27
**For**: GiljoAI MCP End Users

---

## What's New in v3.1

### Unassigned Category

We've added a fourth category called **"Unassigned"** to the Field Priority Configuration system. This ensures you never lose track of fields you remove from priority categories.

**Key Benefits**:
- **Complete Visibility**: See all 13 available fields at all times
- **Easy Recovery**: Quickly restore accidentally removed fields
- **No Data Loss**: Removed fields always visible and accessible
- **Clearer Understanding**: Know exactly which fields are included in agent missions

---

## Understanding Field Priority

### What is Field Priority?

Field Priority determines which product configuration fields are sent to AI agents during mission generation. This affects:

- **Token Budget**: How much context agents receive (max 2,000 tokens)
- **Mission Quality**: More relevant fields → better agent performance
- **Efficiency**: Focused context → 70% token reduction

### The Four Categories

#### 🔴 Priority 1 - Always Included

**Purpose**: Critical fields that agents MUST have for every mission

**Token Weight**: Highest (contributes most to token budget)

**Example Fields**:
- Tech Stack > Languages
- Tech Stack > Backend
- Features > Core

**When to Use**:
- Essential information agents need in every mission
- Fields that define the product's core identity
- Information that rarely changes

---

#### 🟠 Priority 2 - High Priority

**Purpose**: Important fields frequently needed by agents

**Token Weight**: Medium

**Example Fields**:
- Tech Stack > Frontend
- Tech Stack > Database
- Architecture > Pattern

**When to Use**:
- Important but not critical information
- Fields agents need for most (not all) missions
- Information that changes occasionally

---

#### 🔵 Priority 3 - Medium Priority

**Purpose**: Optional fields included when token budget allows

**Token Weight**: Low

**Example Fields**:
- Architecture > API Style
- Test Config > Strategy

**When to Use**:
- Supplementary information
- Fields that provide context but aren't essential
- Information that changes rarely

---

#### ⚪ Unassigned - Not Included in Missions (NEW)

**Purpose**: Fields NOT sent to AI agents (0 tokens)

**Token Weight**: Zero (does not consume token budget)

**Example Fields**:
- Tech Stack > Infrastructure (if not relevant to current missions)
- Architecture > Notes (if internal documentation only)
- Test Config > Coverage Target (if not needed by agents)

**When to Use**:
- Fields you're not ready to include yet
- Information not relevant to current product stage
- Temporarily disabled fields
- Recovery area for accidentally removed fields

---

## How to Use Unassigned Category

### Scenario 1: Removing a Field from Priorities

**Goal**: Remove "Database" field from Priority 2 (not needed for current missions)

**Steps**:

1. **Navigate to Settings**:
   - Click your avatar (top-right corner)
   - Select "Settings"
   - Click "General" tab

2. **Find the Field Priority Section**:
   - Scroll down to "Field Priority Configuration"
   - Locate "Priority 2 - High Priority" section

3. **Remove the Field**:
   - Find "Tech Stack > Database" chip
   - Click the **[✕]** button on the right side

4. **Observe the Result**:
   - Field fades out from Priority 2
   - Field appears in "Unassigned" category (bottom section)
   - Token count decreases automatically

5. **Save Changes**:
   - Click "Save Changes" button at bottom
   - See success notification: "Field priorities saved"

**Result**: "Database" field is no longer sent to agents. Token budget freed up for other fields.

---

### Scenario 2: Recovering an Accidentally Removed Field

**Goal**: You accidentally removed "Languages" field, now you want it back

**Steps**:

1. **Don't Panic**:
   - Field is NOT deleted, just moved to Unassigned

2. **Scroll to Unassigned Category**:
   - Look for the section with dashed border (bottom of page)
   - Label: "Unassigned - Not Included in Missions"

3. **Find Your Field**:
   - Locate "Tech Stack > Languages" chip
   - It's in grey color (vs colored chips in priority categories)

4. **Drag Back to Priority**:
   - Click and hold the "Languages" chip
   - Drag it to "Priority 1 - Always Included" section
   - Release mouse button

5. **Verify Restoration**:
   - Field appears in Priority 1 with red color
   - Token count increases
   - Field removed from Unassigned list

6. **Save Changes**:
   - Click "Save Changes"

**Result**: Field restored to Priority 1, mission context restored.

**Recovery Time**: Less than 5 seconds! ✅

---

### Scenario 3: Exploring Available Fields

**Goal**: See what fields are available but not currently used

**Steps**:

1. **Navigate to Field Priority Configuration**:
   - Settings → General → Field Priority Configuration

2. **Scroll to Unassigned Section**:
   - Bottom section with dashed grey border
   - Contains all fields not in P1/P2/P3

3. **Review Available Fields**:
   - See full list of unassigned fields
   - Each chip shows field path (e.g., "Architecture > Design Patterns")

4. **Hover for Tooltip** (future enhancement):
   - Hover over info icon (ⓘ) for description
   - Understand what each field contains

5. **Add to Priority if Needed**:
   - Drag field from Unassigned to desired priority category
   - Field immediately available for agent missions

**Result**: Complete visibility of all 13 configuration fields.

---

### Scenario 4: Optimizing Token Budget

**Goal**: Reduce token usage from 1,850 to under 1,500

**Current State**:
```
Estimated Context Size for: TinyContacts
1,850 / 2,000 tokens (92%) [YELLOW/RED INDICATOR]
```

**Steps**:

1. **Identify Low-Value Fields**:
   - Review fields in Priority 2 and Priority 3
   - Ask: "Do agents really need this for most missions?"

2. **Move Fields to Unassigned**:
   - Drag "Tech Stack > Infrastructure" from P2 to Unassigned
   - Token count drops: 1,850 → 1,780 tokens
   - Drag "Architecture > Notes" from P3 to Unassigned
   - Token count drops: 1,780 → 1,720 tokens
   - Drag "Test Config > Coverage Target" from P3 to Unassigned
   - Token count drops: 1,720 → 1,665 tokens

3. **Monitor Token Indicator**:
   - Watch progress circle turn green
   - Final: 1,665 / 2,000 tokens (83%) [GREEN INDICATOR]

4. **Save Optimized Configuration**:
   - Click "Save Changes"

**Result**: Token budget optimized. Agents receive focused context. 70% token reduction achieved.

---

## Visual Guide

### Understanding the Interface

```
┌──────────────────────────────────────────────────────────────┐
│ Field Priority Configuration                                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                              │
│ ╔═══════════════════════════════════════════════════════╗   │
│ ║ Estimated Context Size for: TinyContacts              ║   │
│ ║ 1,247 / 2,000 tokens                        [62%] 🟢 ║   │ ← Token Budget Indicator
│ ╚═══════════════════════════════════════════════════════╝   │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 🔴 Priority 1 - Always Included          [420 tokens]  │  │ ← Always sent to agents
│ ├────────────────────────────────────────────────────────┤  │
│ │ Tech Stack > Languages              [✕]               │  │ ← Click [✕] to remove
│ │ Tech Stack > Backend                [✕]               │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 🟠 Priority 2 - High Priority            [327 tokens]  │  │ ← Frequently sent
│ ├────────────────────────────────────────────────────────┤  │
│ │ Tech Stack > Frontend               [✕]               │  │
│ │ Tech Stack > Database               [✕]               │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 🔵 Priority 3 - Medium Priority            [0 tokens]  │  │ ← Sent when budget allows
│ ├────────────────────────────────────────────────────────┤  │
│ │            Drag fields here                            │  │ ← Empty state
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│ │ ⚪ Unassigned - Not Included in Missions   [0 tokens]  │  │ ← NEW! Never sent to agents
│ ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤  │
│ │ Tech Stack > Infrastructure         [✕]               │  │ ← Dashed border
│ │ Architecture > API Style            [✕]               │  │   (indicates "not included")
│ │ Architecture > Design Patterns      [✕]               │  │
│ │ Architecture > Notes                [✕]               │  │
│ │ Features > Core                     [✕]               │  │
│ │ Test Config > Strategy              [✕]               │  │
│ │ Test Config > Frameworks            [✕]               │  │
│ │ Test Config > Coverage Target       [✕]               │  │
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
│                                                              │
│ [ Cancel ]                              [ Save Changes ]    │
└──────────────────────────────────────────────────────────────┘
```

### Token Budget Indicator

The progress circle at the top shows your token usage:

| Color | Percentage | Meaning |
|-------|------------|---------|
| 🟢 Green | 0-75% | Optimal - plenty of room for additional context |
| 🟡 Yellow | 76-90% | Good - approaching budget limit |
| 🟠 Orange | 91-100% | Warning - near budget limit |
| 🔴 Red | 101%+ | Over budget - consider removing fields |

**What Does Token Count Mean?**

Tokens are units of text used by AI agents. Each field consumes tokens based on its content length:
- Short field (e.g., "Python") = ~5 tokens
- Medium field (e.g., "Python 3.11+, TypeScript 5.0") = ~15 tokens
- Long field (e.g., detailed architecture notes) = ~100+ tokens

**Budget**: 2,000 tokens per mission (includes ~500 tokens for structure)

---

## Drag-and-Drop Tips

### How to Drag a Field

1. **Click and Hold**: Click on the field chip and hold mouse button
2. **Drag**: Move mouse to target category (chip becomes semi-transparent)
3. **Drop**: Release mouse button when over target category
4. **Confirm**: Field moves with smooth animation

### Visual Feedback During Drag

- **Dragging**: Field becomes semi-transparent (60% opacity)
- **Over Valid Zone**: Target category highlights with subtle border
- **Drop**: Field animates smoothly to new position
- **Token Update**: Token count animates to new value

### Keyboard Shortcuts (Accessibility)

| Key | Action |
|-----|--------|
| `Tab` | Navigate between categories |
| `Space` | Select field for moving |
| `Arrow Keys` | Move field between categories |
| `Enter` | Confirm move |
| `Escape` | Cancel move |
| `Delete` | Remove field to Unassigned |

---

## Frequently Asked Questions (FAQ)

### Q1: What happens to fields in the Unassigned category?

**A**: Fields in Unassigned are NOT sent to AI agents during mission generation. They consume 0 tokens and have no effect on agent behavior.

**Use Cases**:
- Temporarily disable fields you don't need right now
- Store fields you're not ready to use yet
- Recovery area for accidentally removed fields

---

### Q2: Can I permanently delete a field?

**A**: No, you cannot delete configuration fields. The 13 available fields are fixed by the system. You can only move them between priority categories or Unassigned.

**Why?**: All fields are part of your product configuration schema. Moving to Unassigned is equivalent to "not using" the field.

---

### Q3: How do I know which fields to prioritize?

**General Guidelines**:

**Priority 1 (Always Include)**:
- Programming languages (agents need to know what languages to use)
- Backend/Frontend stack (defines project structure)
- Core features (what the product does)

**Priority 2 (High Priority)**:
- Database technology (data persistence strategy)
- Architecture pattern (how components interact)
- Testing strategy (quality approach)

**Priority 3 (Medium Priority)**:
- API style (REST, GraphQL, etc.)
- Design patterns (optional context)
- Frameworks (supplementary info)

**Unassigned (Not Included)**:
- Infrastructure details (unless agents deploy code)
- Internal notes (not relevant to mission generation)
- Coverage targets (metrics, not instructions)

**Pro Tip**: Start with defaults, then adjust based on mission outcomes.

---

### Q4: What if I remove all fields to Unassigned?

**A**: You can move all fields to Unassigned, but this is NOT recommended.

**What Happens**:
- Token count drops to 500 (structure overhead only)
- Agents receive minimal context
- Mission quality significantly decreases
- System shows warning: "No fields assigned to priorities"

**Recommendation**: Always keep at least 3-5 critical fields in Priority 1.

---

### Q5: What if my token budget exceeds 2,000?

**A**: The system allows you to exceed 2,000 tokens (soft limit), but shows a warning.

**Warning Behavior**:
- Token indicator turns red
- Warning message appears: "Token budget exceeded!"
- Recommendation to move fields to lower priority or Unassigned

**Impact**:
- Agents may receive truncated context (depends on mission size)
- Performance may degrade slightly

**Solution**: Move some fields from P1 to P2, or from P2 to Unassigned.

---

### Q6: How do I reset to default configuration?

**Option 1: Manual Reset**:
1. Remove all fields to Unassigned
2. Manually drag default fields back to priority categories
3. Save changes

**Option 2: Reload Page Without Saving**:
1. Make changes
2. DON'T click "Save Changes"
3. Reload page (F5)
4. Changes discarded, defaults restored

**Future Enhancement**: "Reset to Defaults" button (planned for v3.2)

---

### Q7: Can I save different priority configurations for different products?

**A**: Currently, field priority configuration is **per-user**, not per-product. All your products share the same configuration.

**Workaround**:
- Manually adjust priorities when switching between products
- Use "Active Product" indicator to know which product is active
- Future enhancement: Per-product priority configuration (v4.0 roadmap)

---

### Q8: What's the difference between removing a field and moving it to Unassigned?

**A**: They are the SAME action. Clicking the **[✕]** button removes the field from its priority category and automatically moves it to Unassigned.

**Before (v3.0)**:
- Click [✕] → Field disappeared forever ❌

**After (v3.1)**:
- Click [✕] → Field moves to Unassigned ✅
- Field visible and recoverable

---

### Q9: How often should I update my field priorities?

**Recommendations**:

**Initial Setup**: Spend 10-15 minutes configuring priorities based on your product

**Regular Review**: Monthly (check if priorities still match current product stage)

**After Major Changes**: When product architecture or tech stack changes significantly

**Performance Issues**: If missions seem unfocused, review and adjust priorities

**Trigger Events**:
- New product features added
- Technology stack changes
- Architecture refactored
- Mission quality feedback from agents

---

### Q10: Why can't I see the Unassigned category?

**Possible Causes**:

1. **Not Updated to v3.1**:
   - Ask admin to update GiljoAI MCP Server
   - Check version: Settings → About

2. **Browser Cache**:
   - Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - Clear browser cache

3. **Scroll Position**:
   - Unassigned category is at the BOTTOM
   - Scroll down to see it

4. **All Fields Assigned**:
   - If all 13 fields are in P1/P2/P3, Unassigned will be empty
   - Look for message: "All fields assigned to priority categories"

---

## Best Practices

### 1. Start with Defaults, Then Optimize

- Use default configuration for first few missions
- Observe agent performance
- Adjust priorities based on outcomes
- Iterate until optimal

### 2. Review Token Budget Regularly

- Aim for 70-85% token usage (green/yellow indicator)
- Too low (<50%): Consider adding more fields to priorities
- Too high (>90%): Move low-value fields to Unassigned

### 3. Prioritize Based on Current Product Stage

**Early Stage (MVP)**:
- Focus on core features and tech stack (P1)
- Minimal architecture details (P3 or Unassigned)

**Growth Stage**:
- Add architecture patterns (P2)
- Include testing strategy (P2)
- Keep detailed notes in Unassigned

**Mature Stage**:
- Balance all categories
- Include design patterns (P3)
- Document everything in product config

### 4. Use Unassigned as a Staging Area

- Add new fields to Unassigned first
- Test missions without them
- Promote to priority category if needed

### 5. Document Your Reasoning

- Use product "Notes" field to explain priority choices
- Share configuration with team members
- Review decisions quarterly

---

## Troubleshooting

### Issue: Field disappeared and I can't find it

**Solution**: Scroll down to Unassigned category (dashed border, grey background). Field is there.

---

### Issue: Drag-and-drop not working

**Solutions**:
1. Ensure JavaScript enabled in browser
2. Try different browser (Chrome recommended)
3. Disable browser extensions that block drag-and-drop
4. Hard refresh page: `Ctrl+Shift+R`

---

### Issue: Token count not updating after moving field

**Solutions**:
1. Wait 1-2 seconds (animation delay)
2. Refresh page to recalculate
3. Save changes and reload
4. Contact support if persistent

---

### Issue: Changes not saving

**Solutions**:
1. Click "Save Changes" button (bottom of page)
2. Check for error messages (red toast notifications)
3. Verify network connection
4. Try again in 30 seconds (server may be updating)
5. Contact support if issue persists

---

## Getting Help

### In-App Help

- **Info Icons (ⓘ)**: Hover for contextual help on each category
- **Tooltips**: Hover over fields and buttons for explanations
- **Empty States**: Helpful messages when categories are empty

### Documentation

- **User Guide**: This document
- **Technical Architecture**: See ARCHITECTURE.md (for developers)
- **Implementation Guide**: See IMPLEMENTATION_GUIDE.md (for developers)

### Support

- **Email**: support@giljoai.com
- **GitHub Issues**: https://github.com/giljoai/mcp/issues
- **Community Forum**: https://community.giljoai.com

---

## What's Next?

### Planned Enhancements (v3.2 and beyond)

1. **Field Descriptions**: Hover tooltips showing what each field contains
2. **Reset to Defaults Button**: One-click reset to recommended configuration
3. **Per-Product Priorities**: Different configurations for different products
4. **Bulk Operations**: Select multiple fields and move at once
5. **Search/Filter**: Find fields quickly in large configurations
6. **Import/Export**: Share priority configurations between users
7. **Smart Recommendations**: AI-suggested priorities based on product type

---

## Changelog

### v3.1 (2025-10-27) - Handover 0052

**Added**:
- Unassigned category for removed fields
- Visual distinction (dashed border, grey background)
- Complete field visibility (all 13 fields always shown)
- Easy field recovery (drag from Unassigned to priority)
- Empty state messages for all categories

**Changed**:
- Remove button ([✕]) now moves to Unassigned instead of deleting
- Token calculation explicitly excludes unassigned fields

**Fixed**:
- Fields no longer disappear when removed
- No dead-end UX states
- Complete field inventory always visible

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**For Questions**: Contact your GiljoAI MCP Administrator

**End of USER_GUIDE.md**
