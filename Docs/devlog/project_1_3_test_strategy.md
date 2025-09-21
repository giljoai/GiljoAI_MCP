# Test Strategy for GiljoAI Setup Script (Project 1.3)

## Overview
This document outlines the comprehensive testing strategy for the GiljoAI MCP setup.py script, focusing on cross-platform compatibility, user experience, and robust error handling.

## Test Scope

### 1. Platform Detection Tests
- **Windows Detection**
  - Verify correct identification on Windows 10/11
  - Test path separator handling (`\` vs `/`)
  - Validate Windows-specific directory paths
  - Check admin privileges detection

- **macOS Detection**
  - Verify correct identification on macOS
  - Test Unix-style path handling
  - Validate macOS-specific directory paths (e.g., ~/Library/)
  - Check permissions handling

- **Linux Detection**
  - Verify correct identification on various distributions
  - Test Unix-style path handling
  - Validate Linux-specific directory paths
  - Check sudo requirements detection

### 2. Database Setup Flow Tests

#### SQLite Configuration
- **Test Cases:**
  - Default SQLite selection flow
  - Custom database path input
  - Path validation (exists, writable)
  - Database file creation
  - Connection string generation
  - Migration from existing database

#### PostgreSQL Configuration
- **Test Cases:**
  - PostgreSQL selection flow
  - Credential collection (host, port, user, password, database)
  - Connection validation
  - SSL/TLS configuration options
  - Connection string generation
  - Database initialization
  - Error handling for connection failures

### 3. Environment File Generation

#### .env File Creation
- **Test Cases:**
  - Template detection (.env.example)
  - Variable substitution
  - Port configuration (6000-6003)
  - Database URL formatting
  - API key generation
  - Backup of existing .env
  - Validation of generated values

#### Configuration Validation
- **Test Cases:**
  - Required variables presence
  - Value format validation
  - Port availability checks
  - Path existence validation
  - Permission checks

### 4. Directory Structure Creation

#### Directory Setup
- **Test Cases:**
  - Required directories creation:
    - data/
    - logs/
    - config/
    - temp/
  - Permission setting (755 for dirs, 644 for files)
  - Existing directory handling
  - Cross-platform path creation
  - Error recovery on failure

### 5. Port Conflict Detection

#### Port Availability
- **Test Cases:**
  - Integration with check_ports.py
  - Detection of occupied ports
  - Suggestion of alternative ports
  - Service conflict detection (ports 5000-5003)
  - User-defined port validation

### 6. Migration Support

#### Database Migration
- **Test Cases:**
  - Detection of existing database installation
  - Migration prompt and confirmation
  - Configuration import
  - Database migration options
  - Rollback capability

### 7. Error Handling

#### Robustness Tests
- **Test Cases:**
  - Invalid user input handling
  - Network failure recovery
  - File permission errors
  - Disk space checks
  - Interrupt handling (Ctrl+C)
  - Rollback on failure
  - Clear error messages

### 8. User Experience

#### Interactive Flow
- **Test Cases:**
  - Clear prompts and instructions
  - Default value suggestions
  - Input validation feedback
  - Progress indicators
  - Success confirmation
  - Help text availability
  - Retry mechanisms

## Test Implementation Plan

### Phase 1: Unit Tests
```python
# test_setup_unit.py
- test_platform_detection()
- test_path_handling()
- test_env_generation()
- test_port_validation()
- test_database_url_formatting()
```

### Phase 2: Integration Tests
```python
# test_setup_integration.py
- test_full_sqlite_setup()
- test_full_postgresql_setup()
- test_migration_flow()
- test_error_recovery()
```

### Phase 3: Mock Interactive Tests
```python
# test_setup_interactive.py
- test_user_input_flow()
- test_validation_feedback()
- test_cancellation_handling()
```

## Test Data Requirements

### Mock Inputs
- Valid/invalid database credentials
- Various path formats
- Port configurations
- User responses (y/n, custom values)

### Expected Outputs
- Generated .env file content
- Directory structure
- Configuration files
- Success/error messages

## Success Criteria

1. **Platform Coverage**: Tests pass on Windows, macOS, and Linux
2. **Database Support**: Both SQLite and PostgreSQL flows work correctly
3. **Error Recovery**: All error scenarios handled gracefully
4. **User Experience**: Clear feedback and guidance throughout
5. **Migration Support**: Smooth transition from existing installations if present
6. **Configuration Validity**: Generated configs work with main application

## Risk Areas

1. **Cross-platform Path Handling**: Different OS path separators
2. **Permission Issues**: Admin/sudo requirements
3. **Network Dependencies**: PostgreSQL connection testing
4. **Port Conflicts**: Existing services on default ports
5. **Migration Complexity**: Data compatibility between versions

## Test Execution Timeline

- **Before Implementation**: Review requirements, prepare test cases
- **During Implementation**: Collaborate with implementer on testability
- **After Implementation**: Execute full test suite
- **Validation**: User acceptance testing scenarios

## Reporting

### Test Report Format
- Test case ID and description
- Platform tested
- Input data used
- Expected vs actual results
- Pass/fail status
- Screenshots/logs for failures
- Recommendations for fixes

## Automation Strategy

### CI/CD Integration
- GitHub Actions for multi-platform testing
- Docker containers for consistent environments
- Automated regression testing
- Coverage reporting

### Manual Testing
- User experience validation
- Edge case exploration
- Platform-specific quirks
- Migration scenario testing