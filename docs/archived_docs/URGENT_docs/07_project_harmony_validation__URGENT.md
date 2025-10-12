Project: Installer-Application Harmony Validation
Context
We've refactored the GiljoAI MCP installer to be CLI-only with two modes (localhost/server). We need to validate that the new installer correctly configures everything the application expects, ensuring zero breakage between what the installer creates and what the application requires.
Mission
Perform comprehensive validation to ensure the refactored installer produces configurations, database structures, and runtime environments that perfectly match the application's requirements. Identify and fix any mismatches between installer outputs and application expectations.
Validation Scope
1. Configuration File Harmony
Verify the installer generates all required configuration fields that the application expects:
.env validation:

Check that all environment variables the application reads are present
Verify variable names match exactly (case-sensitive)
Confirm password formats are compatible with the application's auth system
Validate port numbers match service binding expectations
Ensure database connection string format matches application's parser

config.yaml validation:

Verify all required keys exist with correct nesting
Check data types match (strings vs integers vs booleans)
Confirm service names align with application's service discovery
Validate feature flags are recognized by the application
Ensure paths use correct separators for the platform

2. Database Schema Compatibility
Verify the installer's database setup matches application requirements:
Schema validation:

Confirm all tables expected by the application are created
Check column names, types, and constraints match ORM models
Verify indexes required for performance exist
Validate foreign key relationships are properly established
Ensure sequences/auto-increment fields are configured correctly

Role permissions:

Test that giljo_user has all permissions needed by the application
Verify giljo_owner can perform migrations
Confirm the application can connect with installer-generated credentials
Validate row-level security policies if any

3. Service Launch Validation
Ensure the launcher correctly starts the application:
Process startup:

Verify the launcher starts services in the order the application expects
Check that environment variables are properly loaded before app start
Confirm working directory is set correctly for relative imports
Validate Python path includes all necessary modules
Test that port bindings match application's listeners

Health checks:

Verify the application's health endpoints respond after launcher starts
Check database connectivity from the running application
Test inter-service communication (API ↔ WebSocket ↔ Dashboard)
Confirm message queue functionality between services

4. File System Validation
Ensure all paths and permissions are correct:
Directory structure:

Verify application can find and read config files
Check log directories are writable by the application
Confirm template directories are accessible
Validate static file paths for the dashboard
Test upload/download directories if any

Permissions:

Verify .env has restricted permissions but is readable by app
Check service scripts are executable
Confirm database files have correct ownership (if local)
Validate temp directory access

5. Cross-Platform Compatibility
Test that configurations work across platforms:
Platform-specific paths:

Verify pathlib.Path usage doesn't break application imports
Check log file paths work on all platforms
Confirm PID file locations are accessible
Validate socket file paths (Unix) or named pipes (Windows)

6. Migration Compatibility
Ensure database migrations work with installer setup:
Migration execution:

Test that Alembic can connect with installer-generated credentials
Verify migration history table is created correctly
Confirm all migrations run successfully on installer-created database
Check that rollback operations work

7. API Integration Points
Validate external integration configurations:
Service discovery:

Verify MCP tools can register with installer-configured endpoints
Check OAuth callbacks match configured URLs
Test webhook endpoints are accessible
Validate CORS settings match frontend origins

8. Error Recovery Validation
Test application behavior with installer edge cases:
Partial configuration:

Test application behavior if some config keys are missing
Verify graceful degradation without optional features
Check error messages reference correct config files
Validate fallback behaviors

Test Implementation Strategy
python# validation_tests.py

class InstallerApplicationHarmony:
    
    def test_config_compatibility(self):
        """Verify all config fields required by app are present"""
        # Run installer
        # Load generated config
        # Import application config parser
        # Verify all required fields exist
        
    def test_database_schema_match(self):
        """Verify installer creates schema app expects"""
        # Run installer with database creation
        # Import application models
        # Verify tables match SQLAlchemy models
        
    def test_service_startup(self):
        """Verify services start with installer config"""
        # Run installer
        # Start services with launcher
        # Test each service endpoint
        
    def test_authentication_flow(self):
        """Verify auth works with installer-generated credentials"""
        # Use installer-created admin user
        # Test login through application
        # Verify API key authentication
        
    def test_cross_platform_paths(self):
        """Verify paths work on all platforms"""
        # Run installer on each platform
        # Start application
        # Verify all file operations succeed
Specific Areas to Investigate

Config key naming: Ensure installer uses POSTGRES_PASSWORD if app expects it (not DB_PASSWORD)
Port variables: Check if app reads from .env or config.yaml for ports
SSL configuration: Verify app correctly detects SSL settings from installer
Database DSN format: Ensure connection string format matches app's expectations
Service names: Verify systemd/service names match app's process management
Log locations: Confirm app can write to installer-configured log paths
Migration state: Check if app expects certain migration state after install
Template paths: Verify template directory configuration matches app's loader
Static files: Ensure dashboard static file serving matches installer setup
WebSocket URLs: Verify WebSocket connection URLs match installer config

Success Criteria

 Application starts successfully with installer-generated configuration
 All database operations work with installer-created schema
 Authentication works with installer-configured credentials
 Services communicate properly with installer network settings
 No hardcoded paths break with installer directory structure
 Application handles both localhost and server modes correctly
 Zero manual configuration needed after installer completes
 Error messages correctly reference installer-created files
 Platform-specific features work on all supported OS
 Performance meets requirements with installer defaults

Deliverables

Compatibility Report: Document all configuration fields required by the application
Mismatch List: Any discrepancies between installer output and app expectations
Fix Requirements: Specific changes needed in installer or application
Test Suite: Automated tests to prevent future regression
Configuration Map: Visual diagram showing config flow from installer to app components

Priority Focus
Start with the most critical integration points:

Database connection and schema
Service startup and communication
Authentication and security
Configuration file formats
Cross-platform compatibility

This validation ensures the refactored installer remains a drop-in replacement that perfectly configures the application environment without any manual intervention or adjustments needed.