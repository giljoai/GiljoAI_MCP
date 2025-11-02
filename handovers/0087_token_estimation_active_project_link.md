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
