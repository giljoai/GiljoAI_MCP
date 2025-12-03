# Handover 0047 Testing Guide

## ✅ Quick Answer: No Reinstallation Needed!

**You can just restart backend/frontend and test immediately.**

---

## Why No Reinstallation Required

### Database Schema
- ✅ **No changes** to `models.py` (database tables unchanged)
- ✅ **No migrations** created or modified
- ✅ **Existing data** is 100% compatible

### What Changed
- ✅ **Code only**: Method signatures (sync → async)
- ✅ **Repository logic**: Same database queries, just async
- ✅ **API endpoints**: Same routes, just await chunker calls
- ✅ **No new dependencies**: Uses existing asyncio/FastAPI

---

## Testing Steps

### 1. Restart Backend

```bash
# Stop current backend (if running)
# Then restart:
python startup.py --dev
```

**Expected**: Server starts normally on port 7272

### 2. Restart Frontend (Optional)

```bash
cd frontend
npm run dev
```

**Expected**: Frontend starts on port 5173 (or configured port)

### 3. Manual Testing Checklist

#### Test 1: Upload Small Vision Document ✅

1. Open dashboard: `http://localhost:5173`
2. Navigate to a product
3. Upload vision document (< 20K tokens, e.g., 5 KB markdown file)
4. Check **"Auto-chunk on upload"** ✓
5. Click Upload

**Expected Results**:
- ✅ HTTP 201 response (document created)
- ✅ UI shows: "1 chunk • X KB" (not "0 chunks • 0 B")
- ✅ No errors in browser console
- ✅ No errors in backend logs

**If Broken (Before Fix)**:
- ❌ UI shows: "0 chunks • 0 B"
- ❌ Backend logs: "coroutine was never awaited" warning
- ❌ Database: `chunked=false`, `chunk_count=0`

#### Test 2: Upload Large Vision Document ✅

1. Upload vision document (> 20K tokens, e.g., 50 KB markdown file)
2. Check **"Auto-chunk on upload"** ✓
3. Click Upload

**Expected Results**:
- ✅ UI shows: "N chunks • X KB" (where N > 1)
- ✅ Multiple chunks created

#### Test 3: Rechunk Existing Document ✅

1. Find existing vision document
2. Click "Rechunk" button (three dots menu → Rechunk)

**Expected Results**:
- ✅ Success message: "Document re-chunked successfully"
- ✅ Chunk count updated in UI
- ✅ Old chunks deleted, new chunks created

#### Test 4: Upload with Auto-chunk Disabled

1. Upload vision document
2. **Uncheck** "Auto-chunk on upload"
3. Click Upload

**Expected Results**:
- ✅ Document created
- ✅ UI shows: "0 chunks • 0 B" (correct - chunking disabled)
- ✅ Can manually rechunk later

#### Test 5: Error Scenario (Empty File)

1. Create empty file: `touch empty.md`
2. Upload with auto-chunk enabled

**Expected Results**:
- ✅ HTTP 500 error
- ✅ Error message: "Document upload failed during chunking: Document has no content"
- ✅ Document **NOT** created in database (rollback worked)

---

## Database Verification (Optional)

If you want to verify chunks are actually in the database:

```bash
# Connect to PostgreSQL
psql -U postgres -d giljo_mcp

# Check chunked documents
SELECT id, document_name, chunked, chunk_count, total_tokens
FROM vision_documents
WHERE chunked = true
ORDER BY created_at DESC
LIMIT 5;

# Verify chunks exist
SELECT
    v.document_name,
    v.chunk_count as reported_count,
    COUNT(c.chunk_id) as actual_count
FROM vision_documents v
LEFT JOIN mcp_context_index c ON c.vision_document_id = v.id
WHERE v.chunked = true
GROUP BY v.id, v.document_name, v.chunk_count
ORDER BY v.created_at DESC
LIMIT 5;

# Should show matching counts (reported_count = actual_count)
```

**Expected**:
- `chunk_count` matches actual chunks in `mcp_context_index`
- All chunks have correct `vision_document_id` foreign key

---

## Backend Logs to Watch

```bash
# In another terminal, tail the logs
tail -f F:\GiljoAI_MCP\logs\api.log

# OR if using startup.py --dev (logs to console):
# Just watch the console output
```

**Good Signs** (After Fix):
```
INFO - Starting chunking for document <uuid>
INFO - Deleted 0 existing chunks for document <uuid>
INFO - Successfully chunked document <uuid>: 3 chunks, 1200 tokens
```

**Bad Signs** (Before Fix):
```
WARNING - coroutine 'get_by_id' was never awaited
ERROR - 'coroutine' object has no attribute 'storage_type'
WARNING - Chunking failed for document <uuid>: <error>
```

---

## If Tests Pass → Push to Master

### 1. Verify All Tests Pass

```bash
# Run unit tests
pytest tests/unit/test_vision_async_refactoring.py -v --no-cov

# Expected: 5 passed in 0.66s ✅
```

### 2. Verify Git Status

```bash
git status
# Expected: "Your branch is ahead of 'origin/master' by 6 commits"
# Expected: "nothing to commit, working tree clean"
```

### 3. Push to Master

```bash
git push origin master
```

---

## Rollback Plan (If Issues Arise)

If manual testing reveals issues:

### Option 1: Quick Rollback (Git)

```bash
# Rollback all async changes
git reset --hard e79fc0e

# Restart backend
python startup.py --dev
```

### Option 2: Debug and Fix

1. Check backend logs for specific errors
2. Check browser console for frontend errors
3. Verify database state with SQL queries above
4. Report findings for targeted fix

---

## Success Indicators

### ✅ Implementation is Working If:

1. **Upload Test**: Vision documents create chunks (not 0 chunks)
2. **UI Display**: Shows "N chunks • X KB" correctly
3. **Database**: `chunked=true`, `chunk_count` matches actual chunks
4. **Logs**: No async warnings, no coroutine errors
5. **Error Handling**: Empty files fail gracefully with clear message

### ❌ Implementation Has Issues If:

1. **Still 0 chunks**: Async conversion didn't work
2. **Async warnings**: Some await calls missed
3. **500 errors**: Unexpected exceptions during chunking
4. **Orphaned documents**: Documents created but not chunked (rollback failed)

---

## Performance Expectations

- **Small document** (5 KB): < 1 second
- **Medium document** (50 KB): < 3 seconds
- **Large document** (100 KB): < 5 seconds

If slower, check backend logs for bottlenecks.

---

## Summary

**No reinstallation needed** because:
- No database schema changes
- No new migrations
- No dependency changes
- Only code refactoring (sync → async)

**Testing Process**:
1. Restart backend: `python startup.py --dev`
2. Upload vision document with auto-chunk
3. Verify chunks created (UI shows "N chunks")
4. If working → `git push origin master`
5. If broken → `git reset --hard e79fc0e` (rollback)

**Expected Time**: 5-10 minutes for manual testing

**Confidence Level**: HIGH (5/5 unit tests passing, zero async warnings)

---

**Ready to test!** 🚀
