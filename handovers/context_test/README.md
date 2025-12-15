# Context Configuration Test Suite

Comprehensive test suite for GiljoAI's context configuration system. Tests ALL combinations of priority and depth settings and captures `get_orchestrator_instructions` output for analysis.

## Purpose

This test suite validates the context management v2.0 system by:

1. **Testing priority configurations** - Each of 8 fields at 4 priority levels (OFF/Critical/Important/Reference)
2. **Testing depth configurations** - Each depth field at all valid levels
3. **Testing edge cases** - All OFF, All Critical, All Reference, Mixed priorities
4. **Capturing outputs** - Full `get_orchestrator_instructions` response for each combination
5. **Validating behavior** - Ensures configuration changes are reflected in output

## Test Credentials

**Pre-configured for specific test orchestrator:**

```python
ORCHESTRATOR_ID = "6792fae5-c46b-4ed7-86d6-df58aa833df3"
TENANT_KEY = "***REMOVED***"
PROJECT_ID = "97d95e5a-51dd-47ae-92de-7f8839de503a"
API_BASE_URL = "http://10.1.0.164:7274"
```

## Test Coverage

### 1. Baseline Test (1 test)

Tests current default configuration:
- All fields with default priorities
- All depth settings at default levels

### 2. Priority Sweep (32 tests)

Tests each of 8 priority fields at 4 levels:
- `product_core`: OFF, Critical, Important, Reference
- `vision_documents`: OFF, Critical, Important, Reference
- `tech_stack`: OFF, Critical, Important, Reference
- `architecture`: OFF, Critical, Important, Reference
- `testing_config`: OFF, Critical, Important, Reference
- `memory_360`: OFF, Critical, Important, Reference
- `git_history`: OFF, Critical, Important, Reference
- `agent_templates`: OFF, Critical, Important, Reference

**Priority Levels:**
- `OFF` = priority 4, toggle False (excluded from context)
- `Critical` = priority 1, toggle True (always included)
- `Important` = priority 2, toggle True (high priority)
- `Reference` = priority 3, toggle True (lower priority)

### 3. Depth Sweep (20 tests)

Tests each depth field at all valid levels:

- **vision_documents** (4 tests): `optional`, `light`, `medium`, `full`
- **memory_last_n_projects** (4 tests): `1`, `3`, `5`, `10`
- **git_commits** (5 tests): `5`, `10`, `25`, `50`, `100`
- **agent_templates** (2 tests): `type_only`, `full`

### 4. Edge Cases (4 tests)

- **All OFF**: Minimum context (only product_core enabled)
- **All Critical**: Maximum priority (all fields at priority 1)
- **All Reference**: Minimum priority (product_core at 1, rest at 3)
- **Mixed Priorities**: Alternating 1/2/3 pattern

**Total Tests: ~57 combinations**

## Installation

### Prerequisites

1. **Server running**: GiljoAI MCP Server at `http://10.1.0.164:7274`
2. **Python 3.11+**: Required for async/await syntax
3. **Dependencies**: `httpx` for HTTP requests

### Setup

```bash
# Install dependencies
pip install httpx

# Set API key environment variable
export GILJO_API_KEY="your_api_key_here"  # Linux/Mac
set GILJO_API_KEY=your_api_key_here       # Windows CMD
$env:GILJO_API_KEY="your_api_key_here"    # Windows PowerShell
```

## Usage

### Run Full Test Suite

```bash
cd F:/GiljoAI_MCP/handovers/context_test
python run_context_tests.py
```

### Expected Runtime

- ~57 tests at 0.5 seconds delay between calls
- Estimated runtime: **~30-45 seconds**

### Output

The script creates the following outputs in `results/` folder:

1. **Individual Test Results**: `combo_001.json`, `combo_002.json`, etc.
   - Full test configuration
   - Complete orchestrator instructions response
   - Validation results
   - Success/error status

2. **Summary File**: `summary.json`
   - Overall test statistics
   - Token usage statistics (min/max/average)
   - List of all tests with success status
   - Failed test details

## Output Format

### Individual Test Result (`combo_XXX.json`)

```json
{
  "combo_id": 1,
  "test_name": "Baseline - Default Configuration",
  "timestamp": "2025-12-15T10:30:00.123456",
  "input_config": {
    "field_priorities": {
      "product_core": {"toggle": true, "priority": 1},
      "vision_documents": {"toggle": true, "priority": 2},
      ...
    },
    "depth_config": {
      "vision_documents": "optional",
      "memory_last_n_projects": 5,
      "git_commits": 20,
      "agent_templates": "type_only"
    }
  },
  "output": {
    "orchestrator_id": "...",
    "project_id": "...",
    "mission": "...",
    "estimated_tokens": 2735,
    "field_priorities": {...},
    ...
  },
  "validation": {
    "has_mission": true,
    "has_estimated_tokens": true,
    "has_field_priorities": true,
    "field_priorities_match": true
  },
  "success": true,
  "error": null
}
```

### Summary File (`summary.json`)

```json
{
  "test_run_timestamp": "2025-12-15T10:30:00.123456",
  "total_tests": 57,
  "successful_tests": 57,
  "failed_tests": 0,
  "test_credentials": {
    "orchestrator_id": "6792fae5-c46b-4ed7-86d6-df58aa833df3",
    "tenant_key": "***REMOVED***",
    "project_id": "97d95e5a-51dd-47ae-92de-7f8839de503a"
  },
  "results": [
    {
      "combo_id": 1,
      "test_name": "Baseline - Default Configuration",
      "success": true,
      "estimated_tokens": 2735,
      "validation": {...}
    },
    ...
  ]
}
```

## Validation

Each test validates the following:

1. **has_mission**: Output contains mission field with content
2. **has_estimated_tokens**: Output contains token estimate
3. **has_field_priorities**: Output includes field_priorities
4. **field_priorities_match**: Returned priorities match requested config

## Interpreting Results

### Token Statistics

- **Min Tokens**: Lowest token count (usually "All OFF" edge case)
- **Max Tokens**: Highest token count (usually "All Critical" edge case)
- **Average Tokens**: Mean across all successful tests

### Priority Behavior

- **Priority 4 (OFF)**: Field should NOT appear in mission
- **Priority 1 (Critical)**: Field should ALWAYS appear in mission
- **Priority 2 (Important)**: Field should appear with high priority content
- **Priority 3 (Reference)**: Field should appear with condensed content

### Depth Behavior

- **vision_documents**:
  - `optional`: Only if priority allows, minimal chunks
  - `light`: First 3 chunks
  - `medium`: First 5 chunks
  - `full`: All chunks

- **memory_last_n_projects**: Number of recent project summaries to include

- **git_commits**: Number of recent commits to include

- **agent_templates**:
  - `type_only`: Just template names and roles
  - `full`: Complete template content

## Troubleshooting

### API Key Error

```
ERROR: GILJO_API_KEY environment variable not set
```

**Solution**: Set the environment variable:
```bash
export GILJO_API_KEY="your_api_key_here"
```

### Connection Error

```
Error: Connection refused
```

**Solution**: Ensure server is running at `http://10.1.0.164:7274`

### Rate Limiting

If you encounter rate limiting errors:
1. Increase `DELAY_BETWEEN_CALLS` in script (default: 0.5 seconds)
2. Run tests in smaller batches

### Authentication Error

```
Error: 401 Unauthorized
```

**Solution**: Verify API key is correct and has proper permissions

## Advanced Usage

### Running Specific Test Categories

Edit `run_context_tests.py` and comment out test categories you don't need:

```python
# Generate test configurations
test_configs = []

# 1. Baseline
test_configs.append(TestConfigGenerator.baseline_test())

# 2. Priority sweep (comment out to skip)
# test_configs.extend(TestConfigGenerator.priority_sweep_tests())

# 3. Depth sweep
test_configs.extend(TestConfigGenerator.depth_sweep_tests())

# 4. Edge cases
test_configs.extend(TestConfigGenerator.edge_case_tests())
```

### Analyzing Results

Use Python to analyze results programmatically:

```python
import json
from pathlib import Path

# Load summary
with open("results/summary.json") as f:
    summary = json.load(f)

# Find tests with highest token counts
results = sorted(summary["results"], key=lambda r: r["estimated_tokens"], reverse=True)
print("Top 5 token-heavy configurations:")
for r in results[:5]:
    print(f"  {r['test_name']}: {r['estimated_tokens']} tokens")

# Find all failed tests
failed = [r for r in summary["results"] if not r["success"]]
if failed:
    print(f"\nFailed tests: {len(failed)}")
    for r in failed:
        print(f"  - {r['test_name']}")
```

## Architecture Notes

### Test Strategy

The test suite uses a **sweep-based approach** rather than full combinatorial testing:

- **Full combinatorial**: 4^8 priorities × 4×4×5×2 depths = **~16 million combinations** (infeasible)
- **Sweep-based**: ~57 meaningful tests covering all edge cases

This approach provides:
- **Complete coverage** of individual field behavior
- **Representative edge cases** for combined configurations
- **Practical runtime** (~30-45 seconds)

### API Endpoints Used

1. **PUT /api/users/me/field-priority**: Update field priority configuration
2. **PUT /api/users/me/context/depth**: Update depth configuration
3. **POST /mcp**: Call MCP tool `get_orchestrator_instructions`

### Configuration Format Conversion

The script converts between two configuration formats:

**Internal Format** (used in script):
```json
{
  "product_core": {"toggle": true, "priority": 1}
}
```

**API Format** (sent to server):
```json
{
  "version": "2.0",
  "priorities": {
    "product_core": 1
  }
}
```

Conversion logic:
- `toggle: false` → priority = 4 (EXCLUDED)
- `toggle: true` → use configured priority (1/2/3)

## Related Documentation

- [Context Management v2.0](../../docs/architecture/context-management-v2.md)
- [Orchestrator Instructions](../../docs/ORCHESTRATOR.md)
- [MCP Tools](../../docs/MCP_TOOLS.md)

## License

This test suite is part of GiljoAI MCP Server.

## Support

For issues or questions:
- Check logs in `~/.giljo_mcp/logs/`
- Review test output files in `results/`
- Contact: support@giljoai.com
