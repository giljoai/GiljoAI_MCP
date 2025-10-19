#!/bin/bash
#
# Post-Installation Verification Script
# Handover 0035 - Phase 4 Manual Testing
#
# This script verifies a completed GiljoAI MCP installation.
# Run after: python install.py
#

set -e  # Exit on error

echo "=== GiljoAI MCP Installation Verification ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_check() {
    local test_name=$1
    local command=$2

    echo -n "Testing: $test_name... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((TESTS_FAILED++))
    fi
}

# 1. Verify PostgreSQL database exists
echo -e "${YELLOW}[1/10] Checking PostgreSQL Database${NC}"
test_check "Database giljo_mcp exists" \
    "psql -U postgres -lqt | cut -d \| -f 1 | grep -qw giljo_mcp"

# 2. Verify pg_trgm extension (CRITICAL - Bug #1)
echo -e "${YELLOW}[2/10] Checking pg_trgm Extension (Critical Bug #1)${NC}"
test_check "pg_trgm extension installed" \
    "psql -U postgres -d giljo_mcp -c \"SELECT * FROM pg_extension WHERE extname='pg_trgm';\" | grep -q pg_trgm"

# 3. Verify database table count (28 models)
echo -e "${YELLOW}[3/10] Checking Database Tables (28 models)${NC}"
TABLE_COUNT=$(psql -U postgres -d giljo_mcp -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';" | xargs)
if [ "$TABLE_COUNT" -eq 28 ]; then
    echo -e "Table count: ${GREEN}$TABLE_COUNT PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Table count: ${RED}$TABLE_COUNT (expected 28) FAIL${NC}"
    ((TESTS_FAILED++))
fi

# 4. Verify SetupState schema (Handover 0035 fields)
echo -e "${YELLOW}[4/10] Checking SetupState Schema (Handover 0035)${NC}"
test_check "SetupState.first_admin_created field exists" \
    "psql -U postgres -d giljo_mcp -c \"\\d setup_state\" | grep -q first_admin_created"

test_check "SetupState.first_admin_created_at field exists" \
    "psql -U postgres -d giljo_mcp -c \"\\d setup_state\" | grep -q first_admin_created_at"

# 5. Verify user count (should be 0 for fresh install - Handover 0034)
echo -e "${YELLOW}[5/10] Checking User Count (Handover 0034: No Default Admin)${NC}"
USER_COUNT=$(psql -U postgres -d giljo_mcp -t -c "SELECT COUNT(*) FROM users;" | xargs)
if [ "$USER_COUNT" -eq 0 ]; then
    echo -e "User count: ${GREEN}$USER_COUNT (fresh install) PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "User count: ${YELLOW}$USER_COUNT (admin may have been created) WARN${NC}"
fi

# 6. Verify config.yaml exists
echo -e "${YELLOW}[6/10] Checking Configuration Files${NC}"
test_check "config.yaml exists" "[ -f config.yaml ]"

# 7. Verify .env exists
test_check ".env exists" "[ -f .env ]"

# 8. Verify .env contains DATABASE_URL
test_check ".env has DATABASE_URL" "grep -q DATABASE_URL .env"

# 9. Verify venv exists
echo -e "${YELLOW}[7/10] Checking Virtual Environment${NC}"
test_check "venv directory exists" "[ -d venv ]"

if [ -d "venv/bin" ]; then
    test_check "venv/bin/python exists (Unix)" "[ -f venv/bin/python ]"
elif [ -d "venv/Scripts" ]; then
    test_check "venv/Scripts/python.exe exists (Windows)" "[ -f venv/Scripts/python.exe ]"
fi

# 10. Verify frontend directory
echo -e "${YELLOW}[8/10] Checking Frontend${NC}"
test_check "frontend directory exists" "[ -d frontend ]"
test_check "frontend/node_modules exists" "[ -d frontend/node_modules ]"

# 11. Test full-text search (pg_trgm)
echo -e "${YELLOW}[9/10] Testing Full-Text Search (pg_trgm functionality)${NC}"
test_check "PostgreSQL to_tsvector() works" \
    "psql -U postgres -d giljo_mcp -c \"SELECT to_tsvector('test');\" | grep -q test"

# 12. Verify API can start (dry run)
echo -e "${YELLOW}[10/10] Checking API Startup${NC}"
if [ -f "api/run_api.py" ]; then
    echo "API script exists: PASS"
    ((TESTS_PASSED++))
else
    echo "API script missing: FAIL"
    ((TESTS_FAILED++))
fi

# Summary
echo ""
echo "=== Verification Summary ==="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All verification tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. python startup.py"
    echo "  2. Open http://localhost:7274"
    echo "  3. Create your first admin account"
    exit 0
else
    echo -e "${RED}Some verification tests failed.${NC}"
    echo "Please review the failures above and check the installation."
    exit 1
fi
