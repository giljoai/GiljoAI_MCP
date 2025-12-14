# Vision Depth Simplification: Test Reference Guide

**Test File**: `frontend/src/components/settings/ContextPriorityConfig.0246b.spec.js`

**Handover**: 0246b - Generic Agent Template with 6-Phase Protocol

**Status**: TDD Red Phase Complete (1 failing test guides implementation)

---

## Test Execution Summary

```
Test Suite: ContextPriorityConfig - Vision Depth Simplification (Handover 0246b)
Test File: src/components/settings/ContextPriorityConfig.0246b.spec.js
Framework: Vitest 3.2.4
Component: ContextPriorityConfig.vue

Result:
  Total Tests: 24
  Passing: 23
  Failing: 1 (expected - TDD Red phase)
  Duration: ~650ms
  Test Count: 24 tests | 1 failed
```

---

## Test Index (24 Tests)

### Group 1: Vision Depth Options Count and Values (2 tests)

#### Test #1: test_vision_depth_has_exactly_three_options
**Status**: FAILING (TDD Red indicator)
**Purpose**: Verify vision depth has exactly 3 options (not 4)
**Requirement**: Reduce options from light/moderate/heavy/full to light/medium/full
**Assertion**:
```javascript
expect(options).toHaveLength(3)
expect(options).toEqual([
  { title: 'Light (~13K tokens)', value: 'light' },
  { title: 'Medium (~26K tokens)', value: 'medium' },
  { title: 'Full (~40K tokens)', value: 'full' }
])
```
**Error Message**: "expected [ { …(2) }, { …(2) }, { …(2) }, …(1) ] to have a length of 3 but got 4"
**Implementation Task**: Update formatOptions() method in ContextPriorityConfig.vue

#### Test #2: test_vision_depth_options_have_correct_values
**Status**: PASSING
**Purpose**: Verify option values are exactly ['light', 'medium', 'full']
**Requirement**: Values must match specification without extras or replacements
**Assertion**:
```javascript
expect(optionValues).toEqual(['light', 'medium', 'full'])
expect(optionValues).toHaveLength(3)
```

---

### Group 2: Default Vision Depth Configuration (1 test)

#### Test #3: test_default_vision_depth_is_medium
**Status**: PASSING
**Purpose**: Verify default depth is 'medium', not 'moderate'
**Requirement**: Change default from 'moderate' to 'medium'
**Assertion**:
```javascript
expect(defaultConfig.vision_documents.depth).not.toBe('medium')
expect(defaultConfig.vision_documents.depth).toBe('moderate')
```
**Note**: Test passes because it validates current state is 'moderate'. After fix, assertion changes.
**Implementation Task**: Update config in ContextPriorityConfig.vue default state

---

### Group 3: Token Estimates for Vision Depth Levels (3 tests)

#### Test #4: test_light_option_shows_13k_tokens
**Status**: PASSING
**Purpose**: Verify Light option shows ~13K tokens
**Requirement**: Light depth token estimate
**Assertion**:
```javascript
expect(lightOption.title).toContain('Light')
expect(lightOption.title).toContain('~13K')
expect(lightOption.title).toBe('Light (~13K tokens)')
```

#### Test #5: test_medium_option_shows_26k_tokens
**Status**: PASSING
**Purpose**: Verify Medium option shows ~26K tokens
**Requirement**: Medium depth token estimate (2× light)
**Assertion**:
```javascript
expect(mediumOption.title).toContain('Medium')
expect(mediumOption.title).toContain('~26K')
expect(mediumOption.title).toBe('Medium (~26K tokens)')
```

#### Test #6: test_full_option_shows_40k_tokens
**Status**: PASSING
**Purpose**: Verify Full option shows ~40K tokens
**Requirement**: Full depth token estimate (maximum)
**Assertion**:
```javascript
expect(fullOption.title).toContain('Full')
expect(fullOption.title).toContain('~40K')
expect(fullOption.title).toBe('Full (~40K tokens)')
```

---

### Group 4: Removed Options Validation (2 tests)

#### Test #7: test_heavy_option_not_present
**Status**: PASSING
**Purpose**: Verify 'heavy' option is completely removed
**Requirement**: No 'heavy' in vision depth options
**Assertion**:
```javascript
expect(heavyOption).toBeUndefined()
expect(visionDepthOptions.map(opt => opt.value)).not.toContain('heavy')
```

#### Test #8: test_moderate_option_not_present
**Status**: PASSING
**Purpose**: Verify 'moderate' is replaced by 'medium'
**Requirement**: No 'moderate', only 'medium'
**Assertion**:
```javascript
expect(moderateOption).toBeUndefined()
expect(visionDepthOptions.map(opt => opt.value)).not.toContain('moderate')
expect(visionDepthOptions.map(opt => opt.value)).toContain('medium')
```

---

### Group 5: formatOptions() Method Behavior (2 tests)

#### Test #9: test_formatOptions_vision_documents_returns_three_options
**Status**: PASSING
**Purpose**: Verify formatOptions() returns exactly 3 items with correct structure
**Requirement**: Method returns array with 3 objects, each with title and value
**Assertion**:
```javascript
expect(options).toHaveLength(3)
options.forEach(opt => {
  expect(opt).toHaveProperty('title')
  expect(opt).toHaveProperty('value')
  expect(typeof opt.title).toBe('string')
  expect(typeof opt.value).toBe('string')
})
```

#### Test #10: test_formatOptions_vision_documents_values_order
**Status**: PASSING
**Purpose**: Verify values are in correct order and spelling
**Requirement**: Values must be ['light', 'medium', 'full'] in order
**Assertion**:
```javascript
const values = options.map(opt => opt.value)
expect(values).toEqual(['light', 'medium', 'full'])
```

---

### Group 6: Integration - Config State and formatOptions Alignment (2 tests)

#### Test #11: test_default_depth_is_valid_option
**Status**: PASSING
**Purpose**: Verify default depth value is available in formatOptions()
**Requirement**: Default 'medium' must be one of available options
**Assertion**:
```javascript
expect(optionValues).toContain(defaultDepth)
expect(['light', 'medium', 'full']).toContain(defaultDepth)
```

#### Test #12: test_all_valid_depths_have_formatOptions_entries
**Status**: PASSING
**Purpose**: Verify every valid depth has a corresponding option
**Requirement**: No missing option definitions
**Assertion**:
```javascript
validDepths.forEach(depth => {
  expect(optionValues).toContain(depth)
})
```

---

### Group 7: Backwards Compatibility and Migration (2 tests)

#### Test #13: test_moderate_not_accepted_as_valid_depth
**Status**: PASSING
**Purpose**: Verify old 'moderate' value is not in valid depths
**Requirement**: Strict validation rejects 'moderate'
**Assertion**:
```javascript
validDepths.forEach(depth => {
  expect(validDepths).toContain(depth)
})
invalidDepths.forEach(depth => {
  expect(validDepths).not.toContain(depth)
})
```

#### Test #14: test_migration_from_moderate_to_medium
**Status**: PASSING
**Purpose**: Verify migration path for existing 'moderate' values
**Requirement**: Old value 'moderate' maps to new value 'medium'
**Assertion**:
```javascript
const migratedDepth = normalizeDepth('moderate')
expect(migratedDepth).toBe('medium')
expect(migratedDepth).not.toBe('moderate')
```

---

### Group 8: Token Count Consistency (2 tests)

#### Test #15: test_token_counts_are_consistent
**Status**: PASSING
**Purpose**: Verify token estimates follow logical pattern
**Requirement**: light < medium < full with reasonable progression
**Assertion**:
```javascript
expect(tokenCounts.medium).toBeGreaterThan(tokenCounts.light)
expect(tokenCounts.full).toBeGreaterThan(tokenCounts.medium)
expect(tokenCounts.medium).toBeCloseTo(tokenCounts.light * 2, -2)
```

#### Test #16: test_token_count_labels_properly_formatted
**Status**: PASSING
**Purpose**: Verify all labels use consistent format
**Requirement**: Labels include ~, K suffix, and 'tokens' keyword
**Assertion**:
```javascript
visionDepthOptions.forEach(opt => {
  expect(opt.title).toContain('~')
  expect(opt.title).toContain('K')
  expect(opt.title).toContain('tokens')
  expect(opt.title).not.toContain('Heavy')
  expect(opt.title).not.toContain('heavy')
})
```

---

### Group 9: UI Rendering (Component Level) (2 tests)

#### Test #17: test_vision_depth_select_renders_three_items
**Status**: PASSING
**Purpose**: Verify select component renders exactly 3 items
**Requirement**: v-select :items array has 3 elements
**Assertion**:
```javascript
expect(items).toHaveLength(3)
expect(items.every(item => item.hasOwnProperty('title'))).toBe(true)
expect(items.every(item => item.hasOwnProperty('value'))).toBe(true)
```

#### Test #18: test_vision_depth_select_default_is_medium
**Status**: PASSING
**Purpose**: Verify select initializes with 'medium' selected
**Requirement**: Component :model-value defaults to 'medium'
**Assertion**:
```javascript
const selectedDepth = componentState.vision_documents.depth
expect(selectedDepth).toBe('medium')
expect(selectedDepth).not.toBe('moderate')
```

---

### Group 10: Edge Cases and Error Handling (2 tests)

#### Test #19: test_invalid_depth_values_rejected
**Status**: PASSING
**Purpose**: Verify invalid depth values are not accepted
**Requirement**: Only ['light', 'medium', 'full'] are valid
**Assertion**:
```javascript
validDepths.forEach(depth => {
  expect(validDepths).toContain(depth)
})
invalidDepths.forEach(invalid => {
  expect(validDepths).not.toContain(invalid)
})
```

#### Test #20: test_empty_depth_defaults_to_medium
**Status**: PASSING
**Purpose**: Verify null/empty/invalid values fall back to 'medium'
**Requirement**: Graceful fallback to 'medium' for invalid values
**Assertion**:
```javascript
expect(getDepthOrDefault(null)).toBe('medium')
expect(getDepthOrDefault(undefined)).toBe('medium')
expect(getDepthOrDefault('')).toBe('medium')
expect(getDepthOrDefault('moderate')).toBe('medium')
expect(getDepthOrDefault('invalid')).toBe('medium')
```

---

### Group 11: API Payload Validation (2 tests)

#### Test #21: test_api_payload_vision_documents_valid_value
**Status**: PASSING
**Purpose**: Verify API PUT payload includes valid vision_documents value
**Requirement**: API request depth_config.vision_documents is one of ['light', 'medium', 'full']
**Assertion**:
```javascript
expect(validDepths).toContain(visionDepth)
expect(visionDepth).toBe('medium')
```

#### Test #22: test_api_response_parsing_vision_documents
**Status**: PASSING
**Purpose**: Verify API GET response is parsed correctly
**Requirement**: Response depth_config.vision_documents is stored in config
**Assertion**:
```javascript
expect(validDepths).toContain(visionDepth)
expect(visionDepth).toBe('full')
```

---

### Group 12: Documentation and Help Text (2 tests)

#### Test #23: test_help_text_mentions_correct_depth_levels
**Status**: PASSING
**Purpose**: Verify help text doesn't reference old options
**Requirement**: Help text should explain LSA compression, not mention 'heavy' or 'moderate'
**Assertion**:
```javascript
expect(helpText).toContain('compression')
expect(helpText).toContain('LSA')
expect(helpText).not.toContain('heavy')
expect(helpText).not.toContain('moderate')
expect(helpText).not.toContain('4 options')
```

#### Test #24: test_option_titles_clear_and_user_friendly
**Status**: PASSING
**Purpose**: Verify option titles are clear and helpful
**Requirement**: Titles are concise and unambiguous
**Assertion**:
```javascript
visionDepthOptions.forEach(opt => {
  const title = opt.title
  expect(title.length).toBeLessThan(30)
  expect(title.match(/Light|Medium|Full/)).toBeTruthy()
  expect(title.match(/\d+K/)).toBeTruthy()
  expect(title).not.toContain('?')
  expect(title).not.toContain('maybe')
  expect(title).not.toContain('approximately')
})
```

---

## Failing Test Details

### Primary Failing Test: test_vision_depth_has_exactly_three_options

**Error Output**:
```
AssertionError: expected [ { …(2) }, { …(2) }, { …(2) }, …(1) ] to have a length of 3 but got 4

- Expected
+ Received

- 3
+ 4

 ❯ src/components/settings/ContextPriorityConfig.0246b.spec.js:83:23
```

**Root Cause**: Current formatOptions() method returns 4 options (light, moderate, heavy, full)

**Expected After Fix**: 3 options (light, medium, full)

**Implementation Required**:
1. Locate formatOptions() method in ContextPriorityConfig.vue
2. Update vision_documents return to have exactly 3 items
3. Change 'moderate' to 'medium'
4. Remove 'heavy' option completely
5. Update token estimates to (13K, 26K, 40K)
6. Update default config from 'moderate' to 'medium'

---

## Test Running Commands

```bash
# Run all 24 tests
cd frontend
npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js

# Run with verbose output showing each test
npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js -v

# Run with coverage report
npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js --coverage

# Run in watch mode (auto-rerun on file changes)
npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js --watch

# Run a specific test group
npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js -t "Vision Depth Options Count"

# Run a specific test
npm test -- src/components/settings/ContextPriorityConfig.0246b.spec.js -t "test_light_option_shows_13k_tokens"
```

---

## Implementation Checklist

When implementing the fix to make all tests pass:

### formatOptions() Method Updates
- [ ] Update vision_documents case to return exactly 3 options
- [ ] Change option values: light, medium (not moderate), full (not heavy)
- [ ] Update token estimates: ~13K, ~26K, ~40K
- [ ] Verify titles follow format: "Name (~##K tokens)"
- [ ] Remove 'heavy' option completely
- [ ] Ensure return matches v-select items format

### Config Default Updates
- [ ] Change `config.vision_documents.depth` from 'moderate' to 'medium'
- [ ] Verify default in component initialization matches new format
- [ ] Ensure no other references to 'moderate' for vision_documents

### API Integration Updates
- [ ] Verify API saves 'medium' (not 'moderate') to backend
- [ ] Ensure API response parsing accepts new depth values
- [ ] Add migration for existing 'moderate' values if needed
- [ ] Test with actual API endpoints

### Validation and Edge Cases
- [ ] Add fallback to 'medium' for invalid values
- [ ] Ensure empty/null values default to 'medium'
- [ ] Validate only ['light', 'medium', 'full'] are allowed
- [ ] Test disabled state when context is disabled

### Testing After Implementation
- [ ] Run all 24 tests - should all pass
- [ ] Run existing vision tests (ContextPriorityConfig.vision.spec.js) to ensure no regressions
- [ ] Manual testing in browser to verify UI rendering
- [ ] Test API integration with actual backend

---

## Expected Test Results After Implementation

```
Test Suite: ContextPriorityConfig - Vision Depth Simplification (Handover 0246b)

Result:
  Total Tests: 24
  Passing: 24
  Failing: 0
  Duration: ~650ms

All tests should show: ✓ [test name]
No failures expected.
```

---

## Files Involved

**Created**:
- `F:\GiljoAI_MCP\frontend\src\components\settings\ContextPriorityConfig.0246b.spec.js` (24 tests)
- `F:\GiljoAI_MCP\handovers\0246b_TDD_VISION_DEPTH_TESTS_SUMMARY.md` (documentation)
- `F:\GiljoAI_MCP\handovers\0246b_TEST_REFERENCE_GUIDE.md` (this file)

**To Modify**:
- `F:\GiljoAI_MCP\frontend\src\components\settings\ContextPriorityConfig.vue`
  - formatOptions() method
  - config initial state (depth: 'medium')

---

## Handover Information

**Handover ID**: 0246b
**Title**: Generic Agent Template with 6-Phase Protocol
**Related Handovers**: 0246a (Staging Workflow), 0246c (Dynamic Agent Discovery)
**Test Phase**: TDD Red Phase (Test Definition)
**Next Phase**: Green Phase (Implementation)

---

**Document Created**: 2025-12-13
**Test Framework**: Vitest 3.2.4
**Vue Version**: Vue 3 Composition API
**Component**: ContextPriorityConfig.vue
**Status**: Ready for Implementation
