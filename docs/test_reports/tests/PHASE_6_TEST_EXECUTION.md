# Phase 6: Test Execution Guide

## Overview

This guide provides instructions for executing the comprehensive integration and performance tests created for the Orchestrator Upgrade (Phase 6).

## Test Files Created

1. **Integration Tests:** `tests/integration/test_orchestrator_template.py` (19 tests)
2. **Performance Tests:** `tests/performance/test_token_reduction.py` (11 tests)
3. **Validation Tests:** `tests/integration/test_upgrade_validation.py` (15 tests)

**Total: 45 tests covering template integration, config workflows, context prioritization, and validation.**

---

## Prerequisites

### 1. Database Setup

Ensure PostgreSQL 18 is running and test database exists:

```bash
# Windows (Git Bash or CMD)
psql -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Or use the test setup script
python tests/setup_test_db.py
```

### 2. Environment Variables

Set required environment variables:

```bash
# Database URL for tests
export DATABASE_URL="postgresql://postgres:***@localhost:5432/giljo_mcp_test"

# Or use config.yaml (test mode)
```

---

## Running Tests

### All Phase 6 Tests

```bash
# Run all Phase 6 integration and performance tests
pytest tests/integration/test_orchestrator_template.py \
       tests/performance/test_token_reduction.py \
       tests/integration/test_upgrade_validation.py \
       -v --tb=short
```

### Individual Test Suites

#### 1. Orchestrator Template Integration Tests

```bash
pytest tests/integration/test_orchestrator_template.py -v

# Specific test class
pytest tests/integration/test_orchestrator_template.py::TestOrchestratorTemplateContent -v

# Specific test
pytest tests/integration/test_orchestrator_template.py::TestConfigDataIntegration::test_config_data_validates -v
```

#### 2. Token Reduction Performance Tests

```bash
pytest tests/performance/test_token_reduction.py -v

# With output to see metrics
pytest tests/performance/test_token_reduction.py -v -s

# Specific reduction test
pytest tests/performance/test_token_reduction.py::TestOverallTokenReduction::test_average_token_reduction -v -s
```

#### 3. Upgrade Validation Tests

```bash
pytest tests/integration/test_upgrade_validation.py -v

# With output to see script results
pytest tests/integration/test_upgrade_validation.py -v -s

# End-to-end validation
pytest tests/integration/test_upgrade_validation.py::TestEndToEndUpgradeValidation -v
```

### With Coverage

```bash
# Full coverage report
pytest tests/integration/test_orchestrator_template.py \
       tests/performance/test_token_reduction.py \
       tests/integration/test_upgrade_validation.py \
       --cov=giljo_mcp \
       --cov-report=html \
       --cov-report=term-missing

# View HTML coverage report
start htmlcov/index.html  # Windows
# or
open htmlcov/index.html   # macOS/Linux
```

---

## Test Categories

### Integration Tests (test_orchestrator_template.py)

| Test Class | Purpose | Test Count |
|------------|---------|------------|
| TestOrchestratorTemplateExists | Verify template in database | 2 |
| TestOrchestratorTemplateContent | Validate template content | 6 |
| TestOrchestratorAgentCreation | Test agent creation | 2 |
| TestWorkerAgentSpawning | Test role filtering | 2 |
| TestFullProjectLifecycle | End-to-end workflows | 2 |
| TestTemplateManagerIntegration | Template system | 2 |
| TestConfigDataIntegration | Config validation | 3 |

**Total: 19 tests**

### Performance Tests (test_token_reduction.py)

| Test Class | Purpose | Test Count |
|------------|---------|------------|
| TestTokenReductionBaseline | Full config baseline | 1 |
| TestImplementerTokenReduction | Implementer ~40% reduction | 1 |
| TestTesterTokenReduction | Tester ~60% reduction | 1 |
| TestDocumenterTokenReduction | Documenter ~50% reduction | 1 |
| TestOverallTokenReduction | Average 40% reduction | 1 |
| TestRoleFilteringAccuracy | 100% accuracy | 1 |
| TestConfigDataSchemaCompliance | Schema validation | 3 |
| TestPerformanceMetrics | Performance tests | 2 |

**Total: 11 tests**

### Validation Tests (test_upgrade_validation.py)

| Test Class | Purpose | Test Count |
|------------|---------|------------|
| TestValidateOrchestratorUpgradeScript | Script validation | 3 |
| TestPopulateConfigDataScript | Population script | 3 |
| TestConfigDataValidation | Schema validation | 3 |
| TestOrchestratorTemplateValidation | Template checks | 3 |
| TestEndToEndUpgradeValidation | Full validation | 1 |
| TestScriptErrorHandling | Error scenarios | 2 |

**Total: 15 tests**

---

## Expected Results

### Success Metrics

All tests should validate these success criteria:

| Metric | Target | Validation |
|--------|--------|------------|
| Sub-agent context reduction | 60% fewer fields | Field count in filtered configs |
| Token usage reduction | 40% average | Token estimation tests |
| Role filtering accuracy | 100% | Correct fields per role |
| Config schema compliance | 100% | validate_config_data() |
| Template content complete | All sections | Content validation tests |

### Sample Output

**Token Reduction Test:**
```
=== Token Reduction Summary ===
Baseline (Orchestrator): 738 tokens

Role Reductions:
  implementer : 295 tokens (-60.0%)
  tester      : 147 tokens (-80.1%)
  documenter  : 221 tokens (-70.1%)
  reviewer    : 184 tokens (-75.1%)
  analyzer    : 258 tokens (-65.0%)

Average Reduction: 70.1%
Target: 40%
Status: ✓ PASS
```

**Validation Test:**
```
=== Product Config Validation ===
  ✓ GiljoAI MCP: 21 fields, Valid: True
  ✓ Test Product: 8 fields, Valid: True

Validation Summary: 2/2 products valid
```

---

## Troubleshooting

### Issue: Database Connection Error

**Error:** `ValueError: Database URL is required`

**Solution:**
```bash
# Set environment variable
export DATABASE_URL="postgresql://postgres:***@localhost:5432/giljo_mcp_test"

# Or use conftest fixtures (they auto-configure)
pytest tests/integration/test_orchestrator_template.py
```

### Issue: Template Not Found

**Error:** `AssertionError: Default orchestrator template not found`

**Solution:**
```bash
# Run population script to create template
python scripts/populate_orchestrator_template.py

# Or verify template exists
psql -U postgres -d giljo_mcp_test -c "SELECT * FROM agent_templates WHERE name='orchestrator';"
```

### Issue: Import Errors

**Error:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Add to PYTHONPATH
export PYTHONPATH=/f/GiljoAI_MCP:$PYTHONPATH

# Or run from project root
cd /f/GiljoAI_MCP
pytest tests/...
```

### Issue: Async Test Errors

**Error:** `RuntimeError: Event loop is closed`

**Solution:**
```bash
# Use pytest-asyncio plugin (should be installed)
pip install pytest-asyncio

# Verify in pyproject.toml
# asyncio_mode = "auto"
```

---

## Test Fixtures

### Database Fixtures (from conftest.py)

- `db_manager` - Database manager (function scope)
- `db_session` - Transaction-isolated session (auto-rollback)
- `test_project` - Sample project with agent
- `test_agents` - Multiple test agents
- `test_messages` - Test message queue

### Custom Fixtures (in test files)

**test_orchestrator_template.py:**
- `sample_product` - Product with realistic config_data
- `sample_project` - Project linked to product

**test_token_reduction.py:**
- `realistic_product` - GiljoAI_MCP-like config (21 fields)

**test_upgrade_validation.py:**
- `test_product` - Minimal product for validation

---

## Continuous Integration

### GitHub Actions

Add to `.github/workflows/test.yml`:

```yaml
name: Phase 6 Tests

on: [push, pull_request]

jobs:
  test-orchestrator-upgrade:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: giljo_mcp_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run Phase 6 Tests
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/giljo_mcp_test
        run: |
          pytest tests/integration/test_orchestrator_template.py \
                 tests/performance/test_token_reduction.py \
                 tests/integration/test_upgrade_validation.py \
                 --cov=giljo_mcp \
                 --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Quick Reference

### Run All Tests
```bash
pytest tests/integration/test_orchestrator_template.py tests/performance/test_token_reduction.py tests/integration/test_upgrade_validation.py -v
```

### Run with Coverage
```bash
pytest tests/integration/test_orchestrator_template.py tests/performance/test_token_reduction.py tests/integration/test_upgrade_validation.py --cov=giljo_mcp --cov-report=html
```

### Run Specific Category
```bash
# Template tests only
pytest tests/integration/test_orchestrator_template.py -v

# Performance tests only
pytest tests/performance/test_token_reduction.py -v -s

# Validation tests only
pytest tests/integration/test_upgrade_validation.py -v
```

### Debug Mode
```bash
# Verbose with output
pytest tests/integration/test_orchestrator_template.py -vv -s --tb=long

# Stop on first failure
pytest tests/integration/test_orchestrator_template.py -x

# Run last failed
pytest --lf
```

---

## Documentation

- **Test Report:** `docs/devlog/PHASE_6_TESTING_REPORT.md`
- **Architecture:** `docs/TECHNICAL_ARCHITECTURE.md`
- **MCP Tools:** `docs/manuals/MCP_TOOLS_MANUAL.md`
- **Orchestrator Upgrade:** `docs/devlog/OrchestratorUpgrade.md`

---

*Last Updated: 2025-10-08*
*Phase: 6 - Integration Testing & Validation*
