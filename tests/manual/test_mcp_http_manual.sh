#!/bin/bash
# Manual Integration Tests for MCP-over-HTTP Implementation (Handover 0032)
#
# Prerequisites:
# - Server running on http://localhost:7272
# - Valid API key from database or environment
#
# Usage:
#   export API_KEY="your-api-key-here"
#   bash tests/manual/test_mcp_http_manual.sh

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
SERVER_URL="${SERVER_URL:-http://localhost:7272}"
API_KEY="${API_KEY}"

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Helper functions
function print_test_header() {
    echo ""
    echo "=========================================="
    echo "Test: $1"
    echo "=========================================="
}

function assert_status_code() {
    local expected=$1
    local actual=$2
    local test_name=$3

    ((TOTAL++))

    if [ "$expected" == "$actual" ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $test_name (Status: $actual)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}: $test_name (Expected: $expected, Got: $actual)"
        ((FAILED++))
        return 1
    fi
}

function assert_contains() {
    local response=$1
    local search_term=$2
    local test_name=$3

    ((TOTAL++))

    if echo "$response" | grep -q "$search_term"; then
        echo -e "${GREEN}✓ PASSED${NC}: $test_name (Contains: '$search_term')"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}: $test_name (Missing: '$search_term')"
        echo "Response: $response"
        ((FAILED++))
        return 1
    fi
}

function print_summary() {
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo "Total Tests: $TOTAL"
    echo -e "Passed: ${GREEN}$PASSED${NC}"
    echo -e "Failed: ${RED}$FAILED${NC}"

    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    fi
}

# Check prerequisites
if [ -z "$API_KEY" ]; then
    echo -e "${RED}ERROR: API_KEY environment variable not set${NC}"
    echo "Please set your API key: export API_KEY='your-api-key-here'"
    exit 1
fi

echo "MCP-over-HTTP Integration Tests"
echo "Server: $SERVER_URL"
echo "API Key: ${API_KEY:0:12}..."
echo ""

# Test 1: Server Health Check
print_test_header "Server Health Check"
RESPONSE=$(curl -s -w "\n%{http_code}" "$SERVER_URL/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "200" "$HTTP_CODE" "Server is running"
assert_contains "$BODY" "healthy" "Server status is healthy"

# Test 2: MCP Endpoint Accessibility (No Auth)
print_test_header "MCP Endpoint Accessibility (Without API Key)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {},
        "id": 1
    }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "200" "$HTTP_CODE" "MCP endpoint returns 200 (with JSON-RPC error)"
assert_contains "$BODY" "error" "Response contains error field"
assert_contains "$BODY" "X-API-Key" "Error mentions missing X-API-Key"

# Test 3: Invalid API Key
print_test_header "Authentication with Invalid API Key"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: invalid_key_12345" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {},
        "id": 1
    }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "200" "$HTTP_CODE" "Invalid API key returns 200 with error"
assert_contains "$BODY" "error" "Response contains error field"
assert_contains "$BODY" "Invalid API key" "Error indicates invalid key"

# Test 4: Valid API Key - Initialize Method
print_test_header "Initialize Method (Valid API Key)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "client_info": {"name": "manual-test", "version": "1.0"}
        },
        "id": 1
    }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "200" "$HTTP_CODE" "Initialize returns 200"
assert_contains "$BODY" '"jsonrpc":"2.0"' "Response is JSON-RPC 2.0"
assert_contains "$BODY" '"result"' "Response contains result field"
assert_contains "$BODY" '"serverInfo"' "Result contains serverInfo"
assert_contains "$BODY" '"giljo-mcp"' "Server name is giljo-mcp"

# Test 5: Tools List Method
print_test_header "Tools List Method"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "200" "$HTTP_CODE" "Tools list returns 200"
assert_contains "$BODY" '"jsonrpc":"2.0"' "Response is JSON-RPC 2.0"
assert_contains "$BODY" '"tools"' "Result contains tools array"
assert_contains "$BODY" '"name"' "Tools have name field"
assert_contains "$BODY" '"description"' "Tools have description field"
assert_contains "$BODY" '"inputSchema"' "Tools have inputSchema field"

# Test 6: Tools Call Method (list_projects)
print_test_header "Tools Call Method (list_projects)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "list_projects",
            "arguments": {}
        },
        "id": 3
    }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "200" "$HTTP_CODE" "Tools call returns 200"
assert_contains "$BODY" '"jsonrpc":"2.0"' "Response is JSON-RPC 2.0"
assert_contains "$BODY" '"content"' "Result contains content array"
assert_contains "$BODY" '"type":"text"' "Content has text type"

# Test 7: Unknown Method
print_test_header "Error Handling - Unknown Method"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "unknown/method",
        "params": {},
        "id": 4
    }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "200" "$HTTP_CODE" "Unknown method returns 200 with error"
assert_contains "$BODY" '"error"' "Response contains error field"
assert_contains "$BODY" '"-32601"' "Error code is -32601 (Method not found)"

# Test 8: Malformed Request (Missing Method)
print_test_header "Error Handling - Missing Method Field"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "params": {},
        "id": 5
    }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status_code "422" "$HTTP_CODE" "Missing method returns 422 (Validation error)"

# Test 9: Session Persistence - Multiple Requests with Same API Key
print_test_header "Session Persistence - Multiple Requests"

# First request
RESPONSE1=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"client_info": {"name": "persistence-test"}},
        "id": 10
    }')
HTTP_CODE1=$(echo "$RESPONSE1" | tail -n1)

# Second request (should reuse session)
RESPONSE2=$(curl -s -w "\n%{http_code}" -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 11
    }')
HTTP_CODE2=$(echo "$RESPONSE2" | tail -n1)

assert_status_code "200" "$HTTP_CODE1" "First request succeeds"
assert_status_code "200" "$HTTP_CODE2" "Second request succeeds (session reused)"

# Test 10: Full MCP Flow (Initialize → List → Call)
print_test_header "Full MCP Flow - Initialize → Tools List → Tools Call"

# Initialize
INIT_RESPONSE=$(curl -s -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "client_info": {"name": "flow-test", "version": "1.0"}
        },
        "id": 100
    }')

assert_contains "$INIT_RESPONSE" '"result"' "Initialize step succeeds"

# List tools
LIST_RESPONSE=$(curl -s -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 101
    }')

assert_contains "$LIST_RESPONSE" '"tools"' "Tools list step succeeds"

# Call tool
CALL_RESPONSE=$(curl -s -X POST "$SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "list_projects",
            "arguments": {}
        },
        "id": 102
    }')

assert_contains "$CALL_RESPONSE" '"content"' "Tools call step succeeds"

# Print summary
print_summary
