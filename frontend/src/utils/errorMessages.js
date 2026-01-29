/**
 * Error Message Mapping Utility
 *
 * Maps backend error codes to user-friendly frontend messages.
 * Used by the API interceptor to provide consistent error messaging across the application.
 */

const ERROR_MESSAGES = {
  // Resource errors
  'RESOURCE_NOT_FOUND': 'The requested item was not found',
  'RESOURCENOTFOUNDERROR': 'The requested item was not found',

  // Validation errors
  'VALIDATION_ERROR': 'Please check your input',
  'SCHEMAVALIDATIONERROR': 'The submitted data does not match the expected format',
  'DATAVALIDATIONERROR': 'One or more fields contain invalid data',

  // Authentication and Authorization
  'AUTHENTICATION_ERROR': 'Please log in again',
  'AUTHENTICATIONERROR': 'Your session has expired. Please log in again',
  'AUTHORIZATION_ERROR': 'You do not have permission to perform this action',
  'AUTHORIZATIONERROR': 'You do not have permission to perform this action',

  // Template errors
  'TEMPLATENOTFOUNDERROR': 'The template you requested could not be found',
  'TEMPLATEVALIDATIONERROR': 'The template contains validation errors',
  'TEMPLATERENDERERROR': 'Failed to render the template',
  'TEMPLATEERROR': 'An error occurred with the template',

  // Project and orchestration errors
  'PROJECTSTATEERROR': 'Invalid state for this operation. Please check the project status',
  'PROJECTNOTFOUND': 'The project could not be found',
  'AGENTCREATIONERROR': 'Failed to create agent',
  'AGENTCOMMUNICATIONERROR': 'Failed to communicate with agent',
  'ORCHESTRATIONERROR': 'An orchestration error occurred',
  'HANDOFFERROR': 'Failed to hand off to another agent',

  // Configuration errors
  'CONFIGURATIONERROR': 'A configuration error occurred',
  'CONFIGVALIDATIONERROR': 'Configuration validation failed',

  // Database errors
  'DATABASEERROR': 'A database error occurred. Please try again',
  'DATABASECONNECTIONERROR': 'Failed to connect to database',
  'DATABASEMIGRATIONERROR': 'Database migration failed',
  'DATABASEINTEGRITYERROR': 'Database integrity constraint violated',

  // HTTP errors
  'HTTP_ERROR': 'A server error occurred',
  'INTERNAL_SERVER_ERROR': 'An unexpected error occurred. Please try again',

  // Git errors
  'GITOPERATIONERROR': 'A git operation failed',
  'GITAUTHENTICATIONERROR': 'Git authentication failed',
  'GITREPOSITORYERROR': 'Git repository operation failed',

  // Queue/Messaging errors
  'QUEUEEXCEPTION': 'A message queue error occurred',
  'CONSISTENCYERROR': 'A consistency check failed',
  'MESSAGEDELIVERYERROR': 'Failed to deliver message',

  // Rate limiting
  'RATELIMITERROR': 'Too many requests. Please try again later',

  // Context and session errors
  'CONTEXTERROR': 'A context error occurred',
  'CONTEXTLIMITERROR': 'Context size limit exceeded',
  'SESSIONERROR': 'A session error occurred',
  'SESSIONEXPIREDERROR': 'Your session has expired',

  // File system errors
  'FILESYSTEMERROR': 'A file system error occurred',
  'FILENOTFOUNDERROR': 'The requested file was not found',
  'PERMISSIONERROR': 'Permission denied',

  // MCP/Tool errors
  'MCPERROR': 'An MCP protocol error occurred',
  'TOOLERROR': 'Tool execution failed',
  'PROTOCOLERROR': 'Protocol error occurred',

  // Vision document errors
  'VISIONERROR': 'A vision document error occurred',
  'VISIONCHUNKINGERROR': 'Failed to chunk vision document',
  'VISIONPARSINGERROR': 'Failed to parse vision document',

  // Resource exhaustion
  'RESOURCEEXHAUSTEDERROR': 'Resource limit exceeded',
  'RETRYEXHAUSTEDERROR': 'Maximum retry attempts exceeded',
}

/**
 * Get user-friendly error message for a given error code
 *
 * @param {string} errorCode - Machine-readable error code from backend
 * @param {string} fallbackMessage - Optional fallback message if code not found
 * @returns {string} User-friendly error message
 */
export function getErrorMessage(errorCode, fallbackMessage = null) {
  if (!errorCode) {
    return fallbackMessage || 'An error occurred'
  }

  // Try exact match first
  if (ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode]
  }

  // Try case-insensitive match
  const upperCode = String(errorCode).toUpperCase()
  if (ERROR_MESSAGES[upperCode]) {
    return ERROR_MESSAGES[upperCode]
  }

  // Try with lowercased version for exception class names
  const lowerCode = String(errorCode).toLowerCase()
  const messageKey = Object.keys(ERROR_MESSAGES).find(
    key => key.toLowerCase() === lowerCode,
  )
  if (messageKey) {
    return ERROR_MESSAGES[messageKey]
  }

  // Return fallback or generic message
  return fallbackMessage || 'An error occurred'
}

/**
 * Extract detailed error information from error response
 *
 * @param {Error|Object} error - Axios error or error object
 * @returns {Object} Structured error information
 */
export function parseErrorResponse(error) {
  // Check for structured error (has error_code)
  if (error?.response?.data?.error_code) {
    const data = error.response.data
    return {
      errorCode: data.error_code,
      message: data.message || getErrorMessage(data.error_code),
      context: data.context || {},
      timestamp: data.timestamp,
      status: error.response.status,
      isStructured: true,
      errors: data.errors || null, // Validation errors
    }
  }

  // Handle validation errors (422)
  if (error?.response?.status === 422) {
    return {
      errorCode: 'VALIDATION_ERROR',
      message: getErrorMessage('VALIDATION_ERROR'),
      errors: error.response.data?.errors || null,
      status: 422,
      isStructured: false,
    }
  }

  // Handle legacy errors (no error_code)
  if (error?.response?.data?.message) {
    return {
      errorCode: 'HTTP_ERROR',
      message: error.response.data.message,
      status: error.response?.status,
      isStructured: false,
    }
  }

  // Handle network errors
  if (!error?.response) {
    return {
      errorCode: 'NETWORK_ERROR',
      message: 'Failed to connect to server. Please check your connection.',
      isStructured: false,
    }
  }

  // Fallback
  return {
    errorCode: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred',
    isStructured: false,
  }
}

export default {
  getErrorMessage,
  parseErrorResponse,
  ERROR_MESSAGES,
}
