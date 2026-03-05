# Kickoff: Handover 0715 - Cleanup Services Core

**Series:** 0700 Code Cleanup Series
**Risk Level:** HIGH
**Estimated Effort:** 4-6 hours

---

## CRITICAL: Large File Handling

**Files over 500 lines MUST be read in 200-line batches.** Never skip large files.

**Key large files:**
- `project_service.py` (~1500 lines) - Read in 8 batches
- `orchestration_service.py` (~500 lines) - Read in 3 batches

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0715_cleanup_services_core.md`
2. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
3. **Comms**: `handovers/0700_series/comms_log.json`

---

## Mission

Clean up core services with many dependents:
- `orchestration_service.py` (12 TODOs - highest in codebase)
- `project_service.py`
- `product_service.py`
- `settings_service.py`
- `context_service.py`

---

## Phase 0: Validation Research (MANDATORY)

```bash
# Count TODOs in orchestration_service (priority target)
grep -n "TODO" src/giljo_mcp/services/orchestration_service.py

# Count all markers
for f in orchestration_service project_service product_service settings_service context_service; do
  echo "=== $f.py ==="
  grep -c "DEPRECATED\|TODO" src/giljo_mcp/services/${f}.py 2>/dev/null || echo "0"
done
```

---

## Execution Priority

1. **orchestration_service.py** - Resolve 12 TODOs (critical)
2. **project_service.py** - Verify soft delete, lifecycle methods
3. **product_service.py** - Verify vision chunking, no JSONB access
4. Run all service tests

---

## Success Criteria

- [ ] orchestration_service.py: 0 TODOs (from 12)
- [ ] All services: 0 DEPRECATED markers
- [ ] All service/integration tests pass
- [ ] Committed

---

## Communication

```json
{
  "from_handover": "0715",
  "to_handovers": ["0711"],
  "type": "info",
  "subject": "Services Core cleanup complete"
}
```
