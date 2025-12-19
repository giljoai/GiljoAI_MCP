# Handover 1005: Synchronize pyproject.toml

## Overview
- **Ticket**: 1005
- **Parent**: 1000 (Greptile Remediation)
- **Status**: Pending
- **Risk**: LOW
- **Tier**: 1 (Auto-Execute)
- **Effort**: 3 hours

## Mission
Align pyproject.toml versions with requirements.txt to prevent dependency conflicts.

## Files to Modify
- `pyproject.toml`
- `requirements.txt` (reference only)

## Pre-Implementation Research
1. Compare versions between both files
2. Identify missing dependencies in pyproject.toml
3. Verify bcrypt pinning is correct (passlib compatibility)

## Version Mismatches Found

| Package | requirements.txt | pyproject.toml | Action |
|---------|------------------|----------------|--------|
| httpx | >=0.25.0 | >=0.24.0 | Update to >=0.25.0 |
| websockets | >=12.0 | >=11.0 | Update to >=12.0 |
| alembic | >=1.12.0 | >=1.11.0 | Update to >=1.12.0 |
| asyncpg | >=0.29.0 | >=0.28.0 | Update to >=0.29.0 |

## Missing from pyproject.toml
- psycopg2-binary
- python-dotenv
- click
- colorama
- aiohttp
- psutil
- aiofiles
- tiktoken
- structlog

## Implementation Steps
1. Open pyproject.toml
2. Update version constraints to match requirements.txt
3. Add missing dependencies
4. Keep `bcrypt>=3.2.0,<4.0.0` (passlib compatibility)

## Verification
1. Run: `pip install -e .` (should succeed)
2. Run: `pip check` (no conflicts)
3. Run: `pytest tests/` (all pass)

## Cascade Risk
Low. Only affects `pip install -e .` behavior.

## Success Criteria
- pyproject.toml versions match requirements.txt
- `pip install -e .` works correctly
- No dependency conflicts
