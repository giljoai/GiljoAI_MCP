# Handover 0087: Token Estimation Active Project Link Bug Analysis

**Date**: November 2, 2025
**Type**: Bug Investigation & Fix
**Severity**: High - Core feature broken
**Author**: Deep Researcher Agent

## Issue Summary

The Context tab in User Settings (My Settings → Context) has lost its connection to the active product's token estimation. The feature should display real-time token estimation based on the currently active product's config_data fields, but is currently failing with a server-side error.

## Root Cause Analysis

**Primary Issue**: Function naming mismatch in `/api/endpoints/products.py`
- Line 707 calls `extract_field_value(product_config, field_path)` 
- The actual function is named `_get_nested_value` (defined at line 1501)
- This causes a **NameError** when the endpoint is called, breaking the entire token estimation feature

## Affected Components

### Backend
1. **File**: `api/endpoints/products.py`
   - **Endpoint**: `GET /api/v1/products/active/token-estimate` (line 632)
   - **Error Location**: Line 707 - incorrect function name
   - **Correct Function**: `_get_nested_value` at line 1501

### Frontend 
2. **File**: `frontend/src/views/UserSettings.vue`
   - **Function**: `fetchActiveProductTokenEstimate()` (line 955)
   - **Component**: Context tab token indicator (lines 202-218)
   - **Status**: Frontend code is correct and properly implemented

3. **File**: `frontend/src/services/api.js`
   - **Method**: `products.getActiveProductTokenEstimate()` (line 150)
   - **Status**: API service method correctly defined

## Code Review Findings

### Working Components ✅
- Frontend token estimation display logic
- API service method definition
- Token calculation algorithm
- Field priority configuration
- Drag-and-drop UI for field management

### Broken Component ❌
- Backend endpoint function call naming

## Specific Fix Required

**File**: `api/endpoints/products.py`
**Line**: 707
**Current (Broken)**:
```python
value = extract_field_value(product_config, field_path)
```

**Should Be**:
```python
value = _get_nested_value(product_config, field_path)
```

## Impact Analysis

### User Experience Impact
- Users cannot see token estimation for active products
- Field priority changes don't reflect in token counts
- Context budget planning is broken
- AI agents may exceed token limits unknowingly

### Technical Impact
- HTTP 500 errors on `/api/v1/products/active/token-estimate` endpoint
- Console errors in browser developer tools
- Fallback to generic calculation (inaccurate)
- Feature regression from Handover 0049

## Test Cases for Verification

1. **Active Product Token Estimation**
   - Navigate to My Settings → Context tab
   - Verify token indicator shows for active product
   - Confirm token counts update with field changes

2. **Field Priority Changes**
   - Drag fields between priority levels
   - Verify token estimate updates in real-time
   - Save changes and verify persistence

3. **No Active Product Fallback**
   - Deactivate all products
   - Verify graceful fallback message appears
   - Activate product and verify estimation returns

4. **API Response Validation**
   - Check browser console for errors
   - Verify API returns 200 status
   - Confirm response structure matches TokenEstimateResponse model

## Related Handovers

- **0049**: Original token estimation implementation
- **0048**: Field priority configuration system
- **0052**: Unassigned fields category addition
- **0050**: Single active product architecture

## Recommendations

1. **Immediate Fix**: Rename function call on line 707
2. **Add Unit Test**: Create test for `get_active_product_token_estimate` endpoint
3. **Improve Error Handling**: Add try-catch around `_get_nested_value` call
4. **Consider Refactoring**: Make helper function public (remove underscore prefix)
5. **Add Integration Test**: Test full flow from UI to backend

## Additional Observations

- The `_get_nested_value` function is well-implemented with proper dot notation support
- Frontend error handling is robust with graceful fallback
- The feature follows multi-tenant isolation correctly
- Token calculation formula (len/4) is industry standard

## Conclusion

This is a simple but critical bug caused by a function naming mismatch. The fix is straightforward - change one function name on line 707. All surrounding infrastructure is properly implemented and waiting to work once this naming issue is resolved.

## Context Field Priority Usage Analysis

**Investigation Date**: November 2, 2025
**Investigator**: Deep Researcher Agent

### Executive Summary

The field priority configuration system is actively used in multiple critical areas of the GiljoAI application, particularly in orchestrator prompt engineering and mission generation. The system allows users to control which product configuration fields are included in AI agent missions based on token budget constraints. However, there is a **critical gap**: the user_id is not being passed through to the mission generation process, meaning user-specific field priorities are currently being ignored in favor of system defaults.

### 1. All Locations Where Field Priority is Consumed

#### Primary Consumers:

1. **MissionPlanner** (`src/giljo_mcp/mission_planner.py`)
   - `_get_field_priority_config()` (line 417): Retrieves user's field priority or defaults
   - `_build_config_data_section()` (line 484): Builds mission content respecting priorities
   - `generate_missions()` (line 639): Main entry point accepting optional user_id
   - **Critical**: Lines 502-525 implement the priority-based token budget allocation

2. **OrchestratorPromptGenerator** (`src/giljo_mcp/prompt_generator.py`)
   - `_fetch_field_priorities()` (line 315): Extracts priorities from product config_data
   - `_build_discovery_section()` (line 442): Includes priority fields in prompt instructions
   - Lines 470-473: Explicitly instructs orchestrator about Priority 1-4 field handling

3. **Token Estimation Endpoint** (`api/endpoints/products.py`)
   - `get_active_product_token_estimate()` (line 632): Calculates tokens based on field priorities
   - Lines 695-699: Retrieves user's field_priority_config for calculation
   - **Bug**: Line 707 has function naming error (extract_field_value vs _get_nested_value)

4. **User Settings Endpoints** (`api/endpoints/users.py`)
   - `get_field_priority_config()` (line 596): Returns user's config or defaults
   - `update_field_priority_config()` (line 636): Updates user's custom priorities
   - `reset_field_priority_config()` (line 724): Resets to system defaults

### 2. How Orchestrator Uses Field Priority

The orchestrator uses field priority in a **two-stage process**:

#### Stage 1: Staging Prompt Generation (Working ✅)
When 'Stage Project' is clicked in the UI:
1. `OrchestratorPromptGenerator.generate()` is called
2. Field priorities are fetched from product config (line 329)
3. Instructions are generated telling the orchestrator which fields to prioritize
4. The orchestrator receives explicit rules:
   - 'PRIORITY 1 FIELDS (MUST INCLUDE)'
   - 'Only include Priority 1 fields in mission'
   - 'Include Priority 2 if token budget allows'
   - 'NEVER include Priority 3-4'

#### Stage 2: Mission Generation (Broken ❌)
When the orchestrator actually generates missions:
1. `ProjectOrchestrator.process_product_vision()` is called
2. It calls `generate_mission_plan()` which calls `mission_planner.generate_missions()`
3. **CRITICAL BUG**: No user_id is passed to `generate_missions()`
4. Result: System defaults are always used instead of user's custom priorities

### 3. The 'Stage Project' Function

**Location**: Frontend button in LaunchTab.vue → Backend `/api/prompts/staging/{project_id}`

**Purpose**: Generates a comprehensive orchestrator prompt that includes:
- Project context and mission
- Token budget allocation (20K total)
- Field priority instructions
- Agent selection guidance
- MCP tool usage instructions

**Process Flow**:
```
User clicks 'Stage Project' 
→ API call to /api/prompts/staging/{project_id}
→ OrchestratorPromptGenerator.generate()
→ Builds 5-phase orchestrator instructions
→ Returns 2000-3000 line prompt
→ User copies to AI coding tool
```

**Current Status**: ✅ Working correctly for prompt generation

### 4. Critical Issue: User ID Not Passed Through

```python
# orchestrator.py line 1606 - MISSING user_id parameter
missions = await self.mission_planner.generate_missions(
    requirements=requirements, 
    product=product
    # user_id=??? <- NOT PASSED, so defaults always used
)
```

This means all users get identical field prioritization (system defaults), and the sophisticated priority system is effectively unused.

### 5. Recommendations for Fixing Field Priority Issues

#### Priority 1: Critical Fixes
1. **Pass user_id through orchestration chain**:
   - Modify `orchestrator.process_product_vision()` to accept user_id
   - Pass user_id to `generate_mission_plan()` 
   - Ensure it reaches `mission_planner.generate_missions()`

2. **Fix function naming bug** (Already identified):
   - Line 707 of `api/endpoints/products.py`
   - Change `extract_field_value` to `_get_nested_value`

#### Priority 2: Architectural Improvements
3. **Add user context to orchestration**:
   - Store user_id in project metadata when created
   - Retrieve and use throughout orchestration lifecycle

4. **Enhanced logging**:
   - Log when defaults are used vs user config
   - Track field inclusion/exclusion decisions
   - Add metrics for token budget utilization

### 6. Final Analysis Conclusion

The field priority system is a well-designed feature with sophisticated token budget management and prompt engineering capabilities. However, it is currently **partially broken** due to:

1. **Function naming bug** preventing token estimation display
2. **Missing user_id parameter** in orchestration chain preventing user-specific priorities from being applied

Once these issues are fixed, the feature will significantly improve mission quality by respecting user-defined importance levels for product configuration fields. The fixes are straightforward but require careful implementation to ensure the user_id is properly threaded through multiple layers of the orchestration stack.
