# Quick Start Guide

Get up and running with the Context Configuration Test Suite in 5 minutes.

## Prerequisites

1. **Server Running**: GiljoAI MCP Server at `http://10.1.0.164:7274`
2. **Python 3.11+**: Check with `python --version`
3. **API Key**: Get from server admin or UI

## 1. Install Dependencies

```bash
pip install httpx
```

## 2. Set API Key

### Windows PowerShell
```powershell
$env:GILJO_API_KEY="your_api_key_here"
```

### Windows CMD
```cmd
set GILJO_API_KEY=your_api_key_here
```

### Linux/Mac
```bash
export GILJO_API_KEY="your_api_key_here"
```

## 3. Run Tests

```bash
cd F:/GiljoAI_MCP/handovers/context_test
python run_context_tests.py
```

**Expected Runtime**: ~30-45 seconds for all 57 tests

## 4. View Results

### Console Output
The script prints real-time progress and a final report:
```
================================================================================
GiljoAI Context Configuration Test Suite
================================================================================
Orchestrator ID: 6792fae5-c46b-4ed7-86d6-df58aa833df3
...
================================================================================
TEST REPORT
================================================================================
Total Tests: 57
Successful: 57
Failed: 0
Success Rate: 100.0%
...
```

### Result Files

1. **Individual Results**: `results/combo_001.json`, `combo_002.json`, etc.
2. **Summary**: `results/summary.json`

## 5. Analyze Results

```bash
python analyze_results.py
```

This generates:
- Token statistics (min/max/average)
- Priority impact analysis
- Depth impact analysis
- Edge case analysis
- CSV export (`results/results_export.csv`)

## Example Output

### Token Statistics
```
TOKEN STATISTICS
================================================================================

Minimum Tokens: 1842
Maximum Tokens: 8934
Average Tokens: 3456

Lowest Token Configuration:
  Edge Case - All OFF (minimum context): 1842 tokens

Highest Token Configuration:
  Edge Case - All Critical (maximum priority): 8934 tokens
```

### Priority Impact
```
PRIORITY IMPACT ANALYSIS
================================================================================

Token count by field priority level:

Field                OFF        Critical   Important  Reference
------------------------------------------------------------
product_core         N/A        2800       2735       2680
vision_documents     2400       4200       3800       3200
tech_stack           2600       2850       2735       2680
architecture         2680       3100       2900       2735
...
```

## Troubleshooting

### "GILJO_API_KEY environment variable not set"
**Solution**: Set the API key as shown in step 2

### "Connection refused"
**Solution**: Verify server is running:
```bash
curl http://10.1.0.164:7274/health
```

### "401 Unauthorized"
**Solution**: Check API key is valid and has proper permissions

## Next Steps

- Review individual test results in `results/` folder
- Analyze token patterns with `analyze_results.py`
- Import `results/results_export.csv` into Excel for custom analysis
- Review [README.md](README.md) for detailed documentation

## Quick Tips

1. **Run specific tests**: Edit `run_context_tests.py` and comment out unwanted test categories
2. **Adjust delay**: Change `DELAY_BETWEEN_CALLS` if rate limited
3. **Re-run failed tests**: Check `results/summary.json` for failed test IDs
4. **Compare runs**: Save `results/` folder before re-running tests

## File Structure

```
context_test/
├── run_context_tests.py      # Main test runner
├── analyze_results.py         # Results analysis tool
├── README.md                  # Full documentation
├── QUICKSTART.md             # This file
└── results/                   # Test outputs
    ├── combo_001.json        # Individual test results
    ├── combo_002.json
    ├── ...
    ├── summary.json          # Overall summary
    └── results_export.csv    # CSV export (after analysis)
```

## Support

For issues or questions:
- Check [README.md](README.md) for detailed documentation
- Review server logs: `~/.giljo_mcp/logs/`
- Contact: support@giljoai.com

---

**Happy Testing!** 🚀
