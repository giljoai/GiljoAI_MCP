#!/bin/bash
# Validation script for Handover 0080 Integration Tests

echo "========================================="
echo "Handover 0080 Test Suite Validation"
echo "========================================="
echo ""

# Test file locations
TEST_FILES=(
    "tests/fixtures/succession_fixtures.py"
    "tests/integration/test_succession_workflow.py"
    "tests/integration/test_succession_edge_cases.py"
    "tests/integration/test_succession_multi_tenant.py"
    "tests/integration/test_succession_database_integrity.py"
    "tests/performance/test_succession_performance.py"
    "tests/security/test_succession_security.py"
)

echo "1. Checking test files exist..."
all_exist=true
for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (MISSING)"
        all_exist=false
    fi
done
echo ""

if [ "$all_exist" = false ]; then
    echo "ERROR: Some test files are missing!"
    exit 1
fi

echo "2. Counting test functions..."
for file in "${TEST_FILES[@]}"; do
    if [[ "$file" == *"fixtures"* ]]; then
        continue
    fi
    count=$(grep -c "^async def test_" "$file")
    echo "  $file: $count tests"
done
echo ""

total=$(grep -c "^async def test_" tests/integration/test_succession*.py tests/performance/test_succession*.py tests/security/test_succession*.py)
echo "Total test functions: $total"
echo ""

echo "3. Test discovery check..."
pytest tests/integration/test_succession_workflow.py --collect-only -q 2>&1 | tail -1
echo ""

echo "========================================="
echo "Validation Complete!"
echo "========================================="
echo ""
echo "To run all succession tests:"
echo "  pytest tests/integration/test_succession*.py tests/performance/test_succession*.py tests/security/test_succession*.py -v"
