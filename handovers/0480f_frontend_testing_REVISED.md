# Handover 0480f: Frontend Error Handling & Testing (REVISED)

**Date:** 2026-01-27
**From Agent:** Orchestrator
**To Agent:** Frontend Tester + Backend Tester
**Priority:** HIGH
**Estimated Complexity:** 6-10 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Remediation - REVISED)
**Prerequisite:** 0480e must be complete

---

## Executive Summary

### What
Update frontend to handle typed error responses and run integration tests.

---

## Tasks

### Task 1: Update API Interceptor

**Location:** `frontend/src/utils/api.js` (or similar)

```javascript
axios.interceptors.response.use(
  response => response,
  error => {
    const errorData = error.response?.data;

    if (errorData?.error_code) {
      // Structured error from new system
      const userMessage = getErrorMessage(errorData.error_code, errorData.message);
      toast.error(userMessage);
    } else {
      // Legacy error
      toast.error(error.response?.data?.detail || 'An error occurred');
    }

    return Promise.reject(error);
  }
);
```

### Task 2: Create Error Message Mapping

```javascript
const ERROR_MESSAGES = {
  'RESOURCE_NOT_FOUND': 'The requested item was not found',
  'VALIDATION_ERROR': 'Please check your input',
  'AUTHENTICATION_ERROR': 'Please log in again',
  'AUTHORIZATION_ERROR': 'You do not have permission',
  'DATABASE_ERROR': 'A system error occurred. Please try again.',
};

function getErrorMessage(errorCode, fallback) {
  return ERROR_MESSAGES[errorCode] || fallback || 'An error occurred';
}
```

### Task 3: Update Form Validation

Display field-level errors from 422 responses.

### Task 4: Run Integration Tests

```bash
pytest tests/test_exception_handlers.py -v
pytest tests/services/ -v -k "exception or error"
pytest tests/integration/ -v
```

### Task 5: Manual Testing Checklist

- [ ] 404 Not Found shows user-friendly message
- [ ] 400 Validation Error shows field-level errors
- [ ] 401 Unauthorized redirects to login
- [ ] 403 Forbidden shows access denied
- [ ] 500 Server Error shows generic message

---

## Success Criteria

- [ ] Frontend handles typed error responses
- [ ] All tests pass
- [ ] No regressions
- [ ] Manual testing complete

---

## Final Commit Message

```
feat(exceptions): Complete exception handling remediation (0480 series)

- Add HTTP status codes to existing BaseGiljoException
- Create global exception handler in api/exception_handlers.py
- Migrate services from dict returns to raising exceptions
- Remove redundant try/except from endpoints
- Update frontend error handling

Handovers: 0480a-0480f (REVISED)
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Reference

- Master handover: `handovers/0480_exception_handling_remediation_REVISED.md`
