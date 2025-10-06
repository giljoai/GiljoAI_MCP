@echo off
REM Quick test runner for Serena MCP integration tests (Windows)

setlocal enabledelayedexpansion

echo ==========================================
echo Serena MCP Integration Test Suite
echo ==========================================
echo.

REM Check if pytest is installed
pytest --version >nul 2>&1
if errorlevel 1 (
    echo pytest not found. Installing...
    pip install pytest pytest-asyncio pytest-cov
)

REM Parse command line argument
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

if /i "%TEST_TYPE%"=="api" (
    echo Running API endpoint tests only...
    pytest tests\integration\test_setup_serena_api.py -v --tb=short
    goto :end
)

if /i "%TEST_TYPE%"=="services" (
    echo Running service integration tests only...
    pytest tests\integration\test_serena_services_integration.py -v --tb=short
    goto :end
)

if /i "%TEST_TYPE%"=="platform" (
    echo Running cross-platform tests only...
    pytest tests\integration\test_serena_cross_platform.py -v --tb=short
    goto :end
)

if /i "%TEST_TYPE%"=="recovery" (
    echo Running error recovery tests only...
    pytest tests\integration\test_serena_error_recovery.py -v --tb=short
    goto :end
)

if /i "%TEST_TYPE%"=="security" (
    echo Running security tests only...
    pytest tests\integration\test_serena_security.py -v --tb=short
    goto :end
)

if /i "%TEST_TYPE%"=="coverage" (
    echo Running all tests with coverage report...
    pytest tests\integration\test_serena*.py ^
        --cov=src\giljo_mcp\services\serena_detector ^
        --cov=src\giljo_mcp\services\claude_config_manager ^
        --cov=src\giljo_mcp\services\config_service ^
        --cov-report=html ^
        --cov-report=term-missing ^
        -v

    echo.
    echo Coverage report generated: htmlcov\index.html
    goto :end
)

if /i "%TEST_TYPE%"=="fast" (
    echo Running fast tests only (no slow tests)...
    pytest tests\integration\test_serena*.py -m "not slow" -v
    goto :end
)

if /i "%TEST_TYPE%"=="all" (
    echo Running complete Serena MCP test suite...
    echo.

    echo [1/5] API Endpoint Tests
    pytest tests\integration\test_setup_serena_api.py -v --tb=short
    echo.

    echo [2/5] Service Integration Tests
    pytest tests\integration\test_serena_services_integration.py -v --tb=short
    echo.

    echo [3/5] Cross-Platform Tests
    pytest tests\integration\test_serena_cross_platform.py -v --tb=short
    echo.

    echo [4/5] Error Recovery Tests
    pytest tests\integration\test_serena_error_recovery.py -v --tb=short
    echo.

    echo [5/5] Security Tests
    pytest tests\integration\test_serena_security.py -v --tb=short
    echo.

    echo ==========================================
    echo All Serena MCP tests completed!
    echo ==========================================
    goto :end
)

REM Invalid argument
echo Usage: %0 [api^|services^|platform^|recovery^|security^|coverage^|fast^|all]
echo.
echo Options:
echo   api       - Run API endpoint tests only
echo   services  - Run service integration tests only
echo   platform  - Run cross-platform tests only
echo   recovery  - Run error recovery tests only
echo   security  - Run security tests only
echo   coverage  - Run all tests with coverage report
echo   fast      - Run fast tests only (skip slow tests)
echo   all       - Run complete test suite (default)

:end
endlocal
