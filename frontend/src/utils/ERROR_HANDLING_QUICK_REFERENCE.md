# Frontend Error Handling Quick Reference

## Import Error Utilities in Your Component

```javascript
import { parseErrorResponse, getErrorMessage } from '@/services/api'
```

## Catch Errors and Get User-Friendly Messages

```javascript
try {
  await api.projects.get(projectId)
} catch (error) {
  const errorInfo = parseErrorResponse(error)
  console.log(errorInfo.message)  // User-friendly message
  this.showSnackbar(errorInfo.message, 'error')
}
```

## Check Error Type

```javascript
const errorInfo = parseErrorResponse(error)

if (errorInfo.errorCode === 'RESOURCE_NOT_FOUND') {
  // Handle not found
} else if (errorInfo.errorCode === 'AUTHORIZATION_ERROR') {
  // Handle permission denied
} else {
  // Handle other errors
}
```

## Handle Validation Errors (Forms)

```javascript
try {
  await api.projects.create(data)
} catch (error) {
  const errorInfo = parseErrorResponse(error)

  if (errorInfo.errors) {
    // Validation errors from backend (422)
    console.log('Field errors:', errorInfo.errors)
    // Map to form field errors
  } else {
    // General error
    this.formError = errorInfo.message
  }
}
```

## parseErrorResponse() Returns

```javascript
{
  errorCode: string,        // Machine-readable code
  message: string,          // User-friendly message
  context: object,          // Additional context from backend
  timestamp: string,        // ISO timestamp
  status: number,           // HTTP status
  isStructured: boolean,    // true if new system
  errors: array|null        // Validation errors if present
}
```

## Common Error Codes

| Code | Message |
|------|---------|
| RESOURCE_NOT_FOUND | The requested item was not found |
| VALIDATION_ERROR | Please check your input |
| AUTHENTICATION_ERROR | Please log in again |
| AUTHORIZATION_ERROR | You do not have permission to perform this action |
| PROJECTSTATEERROR | Invalid state for this operation |
| TEMPLATENOTFOUNDERROR | The template you requested could not be found |
| DATABASEERROR | A database error occurred. Please try again |
| INTERNAL_SERVER_ERROR | An unexpected error occurred. Please try again |

See `errorMessages.js` for complete list.

## Debug: Check Browser Console

Error logs appear with `[API]` prefix:

```
[API] Structured error: {
  errorCode: "...",
  message: "...",
  context: {...},
  timestamp: "...",
  status: ...
}
```

## Best Practices

1. Always use `parseErrorResponse()` in catch blocks
2. Display `errorInfo.message` to users
3. Check `errorInfo.errors` for validation details
4. Log full `errorInfo` for debugging
5. Use local component snackbars (no global toast)
