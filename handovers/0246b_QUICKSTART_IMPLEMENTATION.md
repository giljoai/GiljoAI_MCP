# Vision Depth Simplification: Quick Start Implementation Guide

**Handover**: 0246b - Generic Agent Template with 6-Phase Protocol
**Feature**: Vision Depth Options Simplification (3 options instead of 4)
**Test Status**: TDD Red Phase Complete - 24 Tests, 1 Failing (expected)

---

## Summary

Convert vision depth options from 4 to 3:
- **OLD**: none, light, moderate, heavy
- **NEW**: light, medium, full

Update token estimates:
- Light: ~13K tokens
- Medium: ~26K tokens (replaces moderate)
- Full: ~40K tokens

---

## Files

### Test File
**Location**: `F:\GiljoAI_MCP\frontend\src\components\settings\ContextPriorityConfig.0246b.spec.js`
- 24 comprehensive tests
- Organized in 12 test groups
- 1 currently failing (guides implementation)
- 23 passing (document expected behavior)

### Documentation Files
1. `0246b_TDD_VISION_DEPTH_TESTS_SUMMARY.md` - Overview of test suite
2. `0246b_TEST_REFERENCE_GUIDE.md` - Detailed test reference (every test explained)
3. `0246b_QUICKSTART_IMPLEMENTATION.md` - This file

### Component to Modify
**Location**: `F:\GiljoAI_MCP\frontend\src\components\settings\ContextPriorityConfig.vue`

---

## Implementation Steps

### Step 1: Understand the Current Implementation

Open `ContextPriorityConfig.vue` and find the `formatOptions()` method (around line 323):

```javascript
function formatOptions(context: { key: string; options?: (string | number)[] }) {
  if (context.key === 'vision_documents') {
    return [
      { title: 'Low (5K tokens)', value: 'light', subtitle: '~250 sentences, 87% compression' },
      { title: 'Medium (12.5K tokens)', value: 'moderate', subtitle: '~625 sentences, 69% compression' },
      { title: 'High (25K tokens)', value: 'heavy', subtitle: '~1,250 sentences, 37% compression' },
      { title: 'Full (All)', value: 'full', subtitle: 'Complete document, no compression' }
    ]
  }
  // ... rest of method
}
```

### Step 2: Update formatOptions() for Vision Documents

Replace the vision_documents case with:

```javascript
if (context.key === 'vision_documents') {
  return [
    { title: 'Light (~13K tokens)', value: 'light' },
    { title: 'Medium (~26K tokens)', value: 'medium' },
    { title: 'Full (~40K tokens)', value: 'full' }
  ]
}
```

**Key Changes**:
- Remove 'heavy' option (was 4th item)
- Rename 'moderate' to 'medium'
- Update token estimates: 13K, 26K, 40K
- Simplify titles (remove subtitle and compression details)
- Remove old format descriptors

### Step 3: Update Default Config

Find the default `config` object (around line 250):

```javascript
const config = ref<Record<string, ContextConfig>>({
  // ... other config items
  vision_documents: { enabled: true, priority: 2, depth: 'moderate' },  // CHANGE THIS
  // ... other config items
})
```

Change to:

```javascript
const config = ref<Record<string, ContextConfig>>({
  // ... other config items
  vision_documents: { enabled: true, priority: 2, depth: 'medium' },  // CHANGED
  // ... other config items
})
```

### Step 4: Update API Defaults

In the `saveConfig()` method (around line 456), update the fallback:

```javascript
await axios.put('/api/v1/users/me/context/depth', {
  depth_config: {
    memory_last_n_projects: config.value.memory_360?.count || 3,
    git_commits: config.value.git_history?.count || 25,
    vision_documents: config.value.vision_documents?.depth || 'medium',  // CHANGED from 'moderate'
    agent_template_detail: config.value.agent_templates?.depth || 'type_only',
  }
})
```

### Step 5: Add Migration Helper (Optional but Recommended)

If you want to handle existing 'moderate' values gracefully, add this helper:

```javascript
function normalizeVisionDepth(depth: string | undefined): string {
  // Map old values to new values
  const depthMap: Record<string, string> = {
    'moderate': 'medium',  // Old → New
    'heavy': 'full',       // Old → New
    'light': 'light',
    'medium': 'medium',
    'full': 'full'
  }

  if (!depth || !depthMap[depth]) {
    return 'medium'  // Default to medium
  }

  return depthMap[depth]
}
```

Then in `fetchConfig()`, after loading from API:

```javascript
if (depthData.vision_documents && config.value.vision_documents) {
  config.value.vision_documents.depth = normalizeVisionDepth(depthData.vision_documents)
}
```

---

## Testing

### Run Tests

```bash
cd /f/GiljoAI_MCP/frontend

# Run all vision depth tests
npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js

# Expected output after fix:
# Test Files  1 passed (1)
# Tests  24 passed (24)
```

### Verify No Regressions

```bash
# Run existing vision tests
npm test -- src/components/settings/ContextPriorityConfig.vision.spec.js

# All should pass (tests for the old implementation may fail - that's OK)
```

### Manual Testing

1. Open browser to `http://localhost:5173` (or your dev server)
2. Navigate to Settings → Context Priority Configuration
3. Find "Vision Documents" row
4. Click the depth dropdown
5. Verify you see exactly 3 options:
   - Light (~13K tokens)
   - Medium (~26K tokens)
   - Full (~40K tokens)
6. Verify 'heavy' and 'moderate' are gone
7. Verify default selection is 'medium'

---

## Code Checklist

After implementation, verify:

### formatOptions() Method
- [ ] Returns exactly 3 options for vision_documents
- [ ] Option values are: 'light', 'medium', 'full'
- [ ] Option titles follow format: "Name (~##K tokens)"
- [ ] No 'heavy' or 'moderate' options
- [ ] Other context options unchanged

### Config Defaults
- [ ] Default depth is 'medium' (not 'moderate')
- [ ] Config structure matches ContextConfig interface
- [ ] No other vision_documents config needed

### API Integration
- [ ] saveConfig() sends 'medium' as fallback
- [ ] fetchConfig() handles old 'moderate' values (migration)
- [ ] API endpoint matches: `/api/v1/users/me/context/depth`

### No Side Effects
- [ ] Memory_360 config unchanged
- [ ] Git_history config unchanged
- [ ] Agent_templates config unchanged
- [ ] Priority configuration unchanged

---

## Test Results

### Before Implementation (TDD Red Phase)

```
Test Files  1 failed (1)
Tests  1 failed | 23 passed (24)

FAILING:
  × test_vision_depth_has_exactly_three_options
    → expected 4 options but got 3
```

### After Implementation (TDD Green Phase)

```
Test Files  1 passed (1)
Tests  24 passed (24)

PASSING:
  ✓ test_vision_depth_has_exactly_three_options
  ✓ test_vision_depth_options_have_correct_values
  ✓ test_default_vision_depth_is_medium
  ✓ test_light_option_shows_13k_tokens
  ✓ test_medium_option_shows_26k_tokens
  ✓ test_full_option_shows_40k_tokens
  ... (18 more passing tests)
```

---

## API Payload Examples

### Save Request (After Implementation)

```json
{
  "depth_config": {
    "memory_last_n_projects": 3,
    "git_commits": 25,
    "vision_documents": "medium",
    "agent_template_detail": "type_only"
  }
}
```

### Load Response (After Implementation)

Backend should return depth values as one of: 'light', 'medium', 'full'

```json
{
  "depth_config": {
    "vision_documents": "medium",
    "memory_last_n_projects": 3,
    "git_commits": 25,
    "agent_template_detail": "type_only"
  }
}
```

### Migration Scenario (With Old Data)

If backend returns old 'moderate' value:

```json
{
  "depth_config": {
    "vision_documents": "moderate"  // OLD VALUE
  }
}
```

The migration helper converts it:
```javascript
normalizeVisionDepth('moderate')  // Returns 'medium'
```

---

## Common Issues & Solutions

### Issue: Tests still fail after changes

**Solution**:
1. Verify exactly 3 items in return array
2. Check spelling: 'light', 'medium', 'full' (not 'moderate', 'heavy')
3. Check token format: '(~##K tokens)'
4. Run: `npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js`

### Issue: Component still shows old options

**Solution**:
1. Clear browser cache (Ctrl+Shift+Delete)
2. Restart dev server: `npm run dev`
3. Check formatOptions() was actually changed
4. Verify no other places set vision depth

### Issue: Default selection is wrong

**Solution**:
1. Verify config.vision_documents.depth = 'medium'
2. Check v-select :model-value binding
3. Verify getDepthValue() returns correct value

### Issue: API save fails with new value

**Solution**:
1. Verify backend accepts 'medium' (not just 'moderate')
2. Check saveConfig() sends correct field name
3. Verify endpoint is `/api/v1/users/me/context/depth`
4. Check backend migration logic

---

## Related Files

### Component Files
- `frontend/src/components/settings/ContextPriorityConfig.vue` - Main component
- `frontend/src/components/settings/UserSettings.vue` - Parent component

### Test Files
- `frontend/src/components/settings/ContextPriorityConfig.0246b.spec.js` - NEW (this test suite)
- `frontend/src/components/settings/ContextPriorityConfig.vision.spec.js` - Existing tests

### Documentation
- `handovers/0246b_vision_document_storage_simplification.md` - Related feature
- `handovers/0246a_staging_workflow.md` - Previous handover
- `handovers/0246c_dynamic_agent_discovery.md` - Next handover

---

## Estimated Time

- **Understanding**: 5-10 minutes (read test file comments)
- **Implementation**: 10-15 minutes (3 small code changes)
- **Testing**: 5 minutes (run tests, verify UI)
- **Code Review**: 5-10 minutes (verify all checklist items)

**Total**: 25-50 minutes

---

## Success Criteria

- [ ] All 24 tests pass
- [ ] No console errors or warnings
- [ ] UI dropdown shows exactly 3 options
- [ ] Default is 'medium'
- [ ] No 'heavy' or 'moderate' options visible
- [ ] API saves and loads correctly
- [ ] No regression in other settings

---

## Questions?

Refer to detailed documentation:
- **Test Overview**: `0246b_TDD_VISION_DEPTH_TESTS_SUMMARY.md`
- **Detailed Reference**: `0246b_TEST_REFERENCE_GUIDE.md`
- **Test File**: `ContextPriorityConfig.0246b.spec.js` (full test code with comments)

---

**Handover**: 0246b
**Phase**: TDD Red → Green → Refactor
**Status**: Ready for Implementation
**Created**: 2025-12-13
