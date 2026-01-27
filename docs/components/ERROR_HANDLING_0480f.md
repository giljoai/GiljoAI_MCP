# Frontend Error Handling Implementation (Handover 0480f)

## Overview

Handover 0480f implements structured error handling on the frontend to support the new backend exception system. The backend now returns errors in a standardized format with machine-readable error codes.

## Error Response Format

The backend returns structured errors with this format:

```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "Project not found",
  "context": {"project_id": "123"},
  "timestamp": "2026-01-27T10:30:00Z",
  "status_code": 404
}
```

## Files Changed

### 1. Frontend Error Message Utility
**File:** `frontend/src/utils/errorMessages.js`

New utility providing:
- Error code to user-friendly message mapping
- Error response parsing (handles both structured and legacy errors)
- Validation error extraction

### 2. API Service Enhancement
**File:** `frontend/src/services/api.js`

Updates to response interceptor:
- Imports `parseErrorResponse` and `getErrorMessage` from errorMessages utility
- Detects structured errors (checks for `error_code` in response)
- Logs structured errors with full context for debugging
- Maintains backward compatibility with legacy error responses
- Preserves existing 401 redirect behavior
- Enhanced 403 logging with structured error details

## Usage in Components

### Option 1: Use Directly in Component (Recommended)

```javascript
import { parseErrorResponse, getErrorMessage } from '@/services/api'

export default {
  methods: {
    async loadProject() {
      try {
        const project = await api.projects.get(projectId)
        // Handle success
      } catch (error) {
        // Parse error response
        const errorInfo = parseErrorResponse(error)

        // Get user-friendly message
        const message = errorInfo.message // Already mapped to user-friendly text

        // Show in snackbar
        this.showSnackbar(message, 'error')

        // Log for debugging if needed
        console.error('Project load error:', {
          code: errorInfo.errorCode,
          context: errorInfo.context,
          timestamp: errorInfo.timestamp,
        })
      }
    },

    showSnackbar(message, type) {
      // Component's own snackbar logic
      this.snackbarMessage = message
      this.snackbarType = type
      this.showSnackbarFlag = true
    }
  }
}
```

### Option 2: Extract Validation Errors

For forms, handle validation errors with field details:

```javascript
import { parseErrorResponse } from '@/services/api'

export default {
  methods: {
    async submitForm(formData) {
      try {
        await api.projects.create(formData)
      } catch (error) {
        const errorInfo = parseErrorResponse(error)

        if (errorInfo.errors) {
          // Handle validation errors with field details
          console.error('Validation errors:', errorInfo.errors)
          // Map to form field errors if needed
        } else {
          // Handle general error
          this.formError = errorInfo.message
        }
      }
    }
  }
}
```

### Option 3: Check Error Type

```javascript
import { parseErrorResponse } from '@/services/api'

export default {
  methods: {
    async handleDelete(id) {
      try {
        await api.projects.delete(id)
      } catch (error) {
        const errorInfo = parseErrorResponse(error)

        // Check error type
        if (errorInfo.errorCode === 'RESOURCE_NOT_FOUND') {
          this.message = 'Project already deleted'
        } else if (errorInfo.errorCode === 'AUTHORIZATION_ERROR') {
          this.message = 'You do not have permission to delete this'
        } else {
          this.message = errorInfo.message
        }
      }
    }
  }
}
```

## Error Code Mapping

Common error codes and their user-friendly messages:

| Error Code | User Message |
|-----------|-------------|
| `RESOURCE_NOT_FOUND` | The requested item was not found |
| `VALIDATION_ERROR` | Please check your input |
| `AUTHENTICATION_ERROR` | Please log in again |
| `AUTHORIZATION_ERROR` | You do not have permission to perform this action |
| `PROJECTSTATEERROR` | Invalid state for this operation. Please check the project status |
| `TEMPLATENOTFOUNDERROR` | The template you requested could not be found |
| `CONFIGURATIONERROR` | A configuration error occurred |
| `DATABASEERROR` | A database error occurred. Please try again |
| `INTERNAL_SERVER_ERROR` | An unexpected error occurred. Please try again |

See `frontend/src/utils/errorMessages.js` for complete mapping.

## API Interceptor Logging

The response interceptor logs errors to the browser console for debugging:

### Structured Errors
```
[API] Structured error: {
  errorCode: "RESOURCE_NOT_FOUND",
  message: "Project not found",
  context: { project_id: "123" },
  timestamp: "2026-01-27T10:30:00Z",
  status: 404
}
```

### Validation Errors
```
[API] Validation errors: [
  { loc: ["body", "name"], msg: "Field required", type: "value_error.missing" },
  ...
]
```

### Legacy Errors
```
[API] Legacy error: {
  status: 500,
  message: "Internal server error",
  data: { ... }
}
```

### Network Errors
```
[API] Network error: Failed to connect to server...
```

## Backward Compatibility

The error handling maintains full backward compatibility:
- Legacy errors (without `error_code`) continue to work
- Network errors are handled the same way
- 401 redirect behavior is unchanged
- 403 forbidden handling enhanced

## Implementation Details

### parseErrorResponse()

Extracts structured error information from axios error response:

```javascript
const errorInfo = parseErrorResponse(error)
// Returns:
{
  errorCode: string,        // Machine-readable code
  message: string,          // User-friendly message (already mapped)
  context: object,          // Additional context from backend
  timestamp: string,        // ISO timestamp from backend
  status: number,           // HTTP status code
  isStructured: boolean,    // true if from new system
  errors: array|null        // Validation errors if present
}
```

### getErrorMessage()

Maps error codes to user-friendly messages:

```javascript
const message = getErrorMessage('RESOURCE_NOT_FOUND')
// Returns: "The requested item was not found"

// With fallback
const message = getErrorMessage('CUSTOM_CODE', 'Custom fallback message')
// Returns: "Custom fallback message" if code not found
```

## Testing Error Responses

### Mock Structured Error

```javascript
// In test file
const mockError = {
  response: {
    status: 404,
    data: {
      error_code: 'RESOURCE_NOT_FOUND',
      message: 'Project not found',
      context: { project_id: '123' },
      timestamp: '2026-01-27T10:30:00Z'
    }
  }
}

const errorInfo = parseErrorResponse(mockError)
expect(errorInfo.errorCode).toBe('RESOURCE_NOT_FOUND')
expect(errorInfo.message).toBe('Project not found')
```

### Mock Validation Error

```javascript
const mockError = {
  response: {
    status: 422,
    data: {
      error_code: 'VALIDATION_ERROR',
      message: 'Request validation failed',
      errors: [
        { loc: ['body', 'name'], msg: 'Field required' }
      ],
      timestamp: '2026-01-27T10:30:00Z'
    }
  }
}

const errorInfo = parseErrorResponse(mockError)
expect(errorInfo.errors).toBeDefined()
expect(errorInfo.errors.length).toBe(1)
```

## Best Practices

1. **Always use parseErrorResponse()** in catch blocks to get structured error info
2. **Display user-friendly messages** from parseErrorResponse().message to users
3. **Log full error context** for debugging: errorCode, context, timestamp
4. **Don't show technical error codes** to users - always map to friendly messages
5. **Handle validation errors** specially with field-level details if available
6. **Keep component snackbars local** - don't use a global toast system
7. **Preserve error context** when logging for troubleshooting

## Migration Guide

For existing components that catch errors:

### Before (Legacy)
```javascript
catch (error) {
  console.error('Error:', error.response?.data?.message)
  this.errorMessage = error.response?.data?.message || 'An error occurred'
}
```

### After (New)
```javascript
import { parseErrorResponse } from '@/services/api'

catch (error) {
  const errorInfo = parseErrorResponse(error)
  console.error('Error:', errorInfo)
  this.errorMessage = errorInfo.message  // Already user-friendly
}
```

## Related Files

- Backend: `api/exception_handlers.py` - Exception handler registration
- Backend: `src/giljo_mcp/exceptions.py` - Exception class definitions
- Frontend: `frontend/src/services/api.js` - API service with enhanced interceptor
- Frontend: `frontend/src/utils/errorMessages.js` - Error mapping utility
