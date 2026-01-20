# Manual Testing Checklist - Handover 0046 ProductsView

**Component**: ProductsView Unified Management
**Test Date**: 2025-10-25
**Tester**: QA Team
**Environment**: http://localhost:7275 (development)

---

## Pre-Test Setup

- [ ] Backend API running on http://localhost:7272
- [ ] PostgreSQL database running
- [ ] All critical API fixes applied
- [ ] Frontend dev server running on port 7275
- [ ] Logged in with valid tenant account
- [ ] Browser console open (F12)
- [ ] No cached data (clear localStorage if needed)

**Commands**:
```bash
# Backend
cd F:\GiljoAI_MCP
python startup.py --dev

# Frontend
cd F:\GiljoAI_MCP\frontend
npm run dev

# Clear cache
localStorage.clear()
window.location.reload()
```

---

## Test 1: Product Card Display

### 1.1 Navigation & View Load
- [ ] Navigate to /Products page
- [ ] Page loads without errors
- [ ] Summary cards display (Total Products, Active Products, Total Tasks, Active Agents)
- [ ] "New Product" button visible and clickable
- [ ] Search field visible
- [ ] No console errors

### 1.2 Product Card Content
**For each visible product card:**
- [ ] Product name displays correctly
- [ ] "Active" chip shows on active product only
- [ ] Unresolved Tasks count shows (not 0 if product has tasks)
- [ ] Unfinished Projects count shows (not 0 if product has projects)
- [ ] Vision Docs count shows (not 0 if product has documents)
- [ ] Created date formats correctly (e.g., "Jan 15, 2025")
- [ ] Card elevation increases when product is active (visual feedback)
- [ ] Card color tint shows for active product

### 1.3 Product Card Buttons
For each visible product:
- [ ] "Activate" button visible
- [ ] "Activate" button disabled if product already active
- [ ] Info (i) button visible
- [ ] Edit (pencil) button visible
- [ ] Delete (trash) button visible and colored red
- [ ] All buttons properly sized and spaced
- [ ] Hover effects visible (buttons should show feedback on hover)

### 1.4 Search Functionality
- [ ] Search by product name works
- [ ] Search by description works
- [ ] Clear search shows all products
- [ ] Search results update in real-time
- [ ] "No products found" message shows when search has no matches

### 1.5 Empty State
If no products exist:
- [ ] "No products found" message displays
- [ ] Helpful text suggests creating first product
- [ ] "New Product" button is prominent and clickable

---

## Test 2: Create Product

### 2.1 Dialog Open
- [ ] Click "New Product" button
- [ ] Create Product dialog opens
- [ ] Dialog has "Create New Product" title
- [ ] Dialog has two tabs: "Details" and "Vision Documents"
- [ ] Details tab is selected by default
- [ ] Close button (X) visible in top right

### 2.2 Details Tab
- [ ] Product Name field visible
- [ ] Product Name field shows "Name is required" error if empty
- [ ] Description field visible
- [ ] Description field has helpful hint text
- [ ] Description field auto-grows with text
- [ ] Both fields accept input

### 2.3 Vision Documents Tab
- [ ] Tab is clickable
- [ ] File input accepts .md, .txt, .markdown files
- [ ] File browser shows correct file type filter
- [ ] Can select multiple files
- [ ] Selected files display in list with:
  - [ ] File icon
  - [ ] File name
  - [ ] File size formatted (KB, MB)
  - [ ] Remove button (X) to delete from list
- [ ] "Files will be auto-chunked" info message shows
- [ ] Tab switching preserves selections

### 2.4 Form Validation
- [ ] Try to submit without product name → Error shows
- [ ] Fill product name → Error disappears
- [ ] Submit button disabled until name is provided
- [ ] Tab switches work while form invalid

### 2.5 File Upload
- [ ] Select 1 vision file
- [ ] File appears in "Files to Upload" list
- [ ] Select additional files (multi-select)
- [ ] All files show in list
- [ ] Click remove (X) on file → File disappears from list
- [ ] Try to select PDF file → Should be rejected or show error

### 2.6 Product Creation
- [ ] Fill in product name: "Test Product [timestamp]"
- [ ] Fill in description: "This is a test product"
- [ ] Select 1-2 vision files
- [ ] Click "Create Product"
- [ ] Dialog closes
- [ ] Success notification appears (toast/snackbar)
- [ ] New product appears in grid at top
- [ ] New product shows correct name
- [ ] Created date shows today's date
- [ ] Vision document count shows correct number
- [ ] No console errors

### 2.7 Dialog Close
- [ ] Click Cancel → Dialog closes without creating
- [ ] Click X → Dialog closes without creating
- [ ] Dialog clears form data for next use

---

## Test 3: Edit Product

### 3.1 Dialog Open
- [ ] Click Edit button on a product card
- [ ] Edit Product dialog opens
- [ ] Dialog title shows "Edit Product"
- [ ] Details tab selected by default

### 3.2 Details Populated
- [ ] Product Name field pre-filled correctly
- [ ] Description field pre-filled correctly (or empty if none)
- [ ] Form validation still works
- [ ] Changes can be made to fields

### 3.3 Existing Vision Documents
- [ ] Switch to Vision Documents tab
- [ ] Existing documents list shows if any exist
- [ ] Each document shows:
  - [ ] Success checkmark (if chunked) or clock icon (if processing)
  - [ ] Document name
  - [ ] Chunk count
  - [ ] Created date
  - [ ] Delete button (red trash icon)

### 3.4 Add New Documents
- [ ] File input visible below existing documents
- [ ] Can add additional files
- [ ] New files show in upload list
- [ ] Can remove newly added files with X button

### 3.5 Delete Existing Document
- [ ] Click delete button on an existing document
- [ ] Confirmation dialog appears (if implemented)
- [ ] Confirm deletion → Document removes from list
- [ ] Success notification appears
- [ ] Document count in product decreases

### 3.6 Save Changes
- [ ] Modify product name
- [ ] Click "Save Changes"
- [ ] Dialog closes
- [ ] Success notification appears
- [ ] Product card updates with new name
- [ ] Product grid updates immediately

---

## Test 4: Product Details Dialog

### 4.1 Dialog Open
- [ ] Click Info (i) button on product card
- [ ] Product Details dialog opens
- [ ] Dialog title shows "Product Details"
- [ ] Close button visible

### 4.2 Content Display
- [ ] Product name displays prominently
- [ ] Product ID shows (truncated or full)
- [ ] Description displays (or "No description provided")
- [ ] Statistics section shows:
  - [ ] Unresolved Tasks count
  - [ ] Unfinished Projects count
- [ ] Vision Documents section shows:
  - [ ] Count of documents
  - [ ] List of documents with names
  - [ ] Chunk counts per document
  - [ ] File sizes formatted

### 4.3 Created/Updated Dates
- [ ] Created date displays correctly formatted
- [ ] Updated date displays (or Created if never updated)

### 4.4 Dialog Close
- [ ] Click Close button → Dialog closes
- [ ] Clicking outside dialog → Dialog closes (if not modal)

---

## Test 5: Delete Product

### 5.1 Dialog Open
- [ ] Click Delete button on product card
- [ ] Delete confirmation dialog opens
- [ ] Dialog title shows "Delete Product?"
- [ ] Title is red/error color
- [ ] Warning icon visible

### 5.2 Cascade Impact Display
- [ ] "Loading cascade impact..." message shows briefly
- [ ] Impact counts display:
  - [ ] Unfinished projects count + total projects
  - [ ] Unresolved tasks count + total tasks
  - [ ] Vision documents count
  - [ ] Context chunks count
- [ ] All numbers are accurate (verify against product details)
- [ ] Icons show for each impact type

### 5.3 Confirmation Requirements
- [ ] Type Product Name field visible with placeholder
- [ ] Checkbox "I understand this action is permanent" visible
- [ ] Delete Forever button is disabled initially
- [ ] Type wrong product name:
  - [ ] Error message shows "Product name does not match"
  - [ ] Delete button stays disabled
- [ ] Type correct product name:
  - [ ] Error message disappears
  - [ ] Delete button still disabled (unchecked checkbox)
- [ ] Check checkbox:
  - [ ] Delete button becomes enabled (if name correct)
- [ ] Uncheck checkbox:
  - [ ] Delete button becomes disabled

### 5.4 Abort Delete
- [ ] Click Cancel → Dialog closes without deleting
- [ ] Delete Forever button shows loading state while deleting

### 5.5 Complete Delete
- [ ] Type correct product name
- [ ] Check confirmation checkbox
- [ ] Click "Delete Forever"
- [ ] Loading indicator shows (spinning or progress)
- [ ] Dialog closes
- [ ] Success notification appears
- [ ] Product disappears from grid
- [ ] Summary card counts update (Total Products decreases)
- [ ] No console errors

### 5.6 Delete Non-Existent Product (Edge Case)
- [ ] If available, try to delete already-deleted product
- [ ] Should show 404 or "Product not found" error
- [ ] Error notification shows
- [ ] Dialog closes

---

## Test 6: Product-as-Context (Activate Product)

### 6.1 Activate Product
- [ ] Click "Activate" button on inactive product
- [ ] Button shows loading state (optional)
- [ ] Button changes to show "Active" (disabled state)
- [ ] Card highlights/shows active state
- [ ] Success notification appears (if implemented)
- [ ] ActiveProductDisplay chip updates (if visible in header)

### 6.2 Product Persistence
- [ ] Refresh page (F5)
- [ ] Same product still shows as active
- [ ] Open browser dev tools → Application → LocalStorage
- [ ] Verify "currentProductId" is stored

### 6.3 Context Filtering (If Implemented)
- [ ] Go to Tasks page
- [ ] Verify only active product's tasks show
- [ ] Activate different product
- [ ] Tasks page updates to show new product's tasks
- [ ] Go to Projects page
- [ ] Verify only active product's projects show
- [ ] Switch products
- [ ] Projects update accordingly

### 6.4 Default Product
- [ ] Clear localStorage
- [ ] Reload page
- [ ] First product in list becomes active (if auto-selection implemented)

---

## Test 7: Accessibility & Keyboard Navigation

### 7.1 Keyboard Navigation
- [ ] Tab through product cards
- [ ] All buttons receive focus indicator
- [ ] Focus order is logical (left-to-right, top-to-bottom)
- [ ] Focus indicators are visible and contrasted

### 7.2 Dialog Keyboard
- [ ] Open Create dialog
- [ ] Tab navigates through form fields
- [ ] Tab can reach Cancel and Create buttons
- [ ] Enter submits form
- [ ] Escape closes dialog

### 7.3 Screen Reader Testing (If Possible)
- [ ] Icon buttons announce their purpose
- [ ] Dialog title announced when opened
- [ ] Form fields labeled correctly
- [ ] Error messages announced
- [ ] Notifications announced (live regions)

### 7.4 Color Contrast
- [ ] Delete warning text is readable
- [ ] Buttons have sufficient contrast
- [ ] Text on cards readable in all states

---

## Test 8: Error Handling & Edge Cases

### 8.1 Network Errors
- [ ] Disable network (dev tools)
- [ ] Try to create product
- [ ] Error notification shows
- [ ] Dialog remains open
- [ ] Re-enable network and retry
- [ ] Product creates successfully

### 8.2 Invalid File Upload
- [ ] Try to upload PDF file
- [ ] Error shows (either browser reject or API error)
- [ ] File doesn't upload
- [ ] Can continue to upload other files

### 8.3 Large File Upload
- [ ] Upload large file (10+ MB)
- [ ] Progress shows (if implemented)
- [ ] Upload completes or shows error
- [ ] No browser timeout

### 8.4 Concurrent Operations
- [ ] Create product A
- [ ] While creating, try to open product B edit
- [ ] System handles gracefully (doesn't crash)

### 8.5 Very Long Names
- [ ] Create product with very long name (500+ chars)
- [ ] Name displays correctly in card
- [ ] Dialog shows full name
- [ ] No layout breaking

### 8.6 Special Characters
- [ ] Product name with special chars: "Test-Product_123 (copy)"
- [ ] Description with quotes, backticks, etc.
- [ ] Characters display and save correctly
- [ ] No XSS or encoding issues

---

## Test 9: Responsive Design

### 9.1 Mobile (< 768px)
- [ ] Navigate to /Products on mobile view
- [ ] Product cards stack in single column
- [ ] Action buttons visible and clickable on touch
- [ ] Dialog fits on screen
- [ ] Search field usable
- [ ] Create dialog is readable

### 9.2 Tablet (768px - 1024px)
- [ ] 2-column product layout
- [ ] All elements properly spaced
- [ ] Touch interactions work

### 9.3 Desktop (> 1024px)
- [ ] 3-4 column product layout (grid.sm/md/lg)
- [ ] Summary cards display in single row
- [ ] Comfortable spacing and sizing

---

## Test 10: Browser Compatibility

Test in each browser:

### Chrome/Chromium
- [ ] All features work
- [ ] No console errors
- [ ] File upload works
- [ ] Notifications display

### Firefox
- [ ] All features work
- [ ] File upload works
- [ ] Form validation works

### Safari (if available)
- [ ] All features work
- [ ] No layout issues
- [ ] File upload works

### Edge
- [ ] All features work
- [ ] No console errors

---

## Test 11: Data Consistency

### 11.1 Metrics Accuracy
After fixes applied:
- [ ] Product with 5 tasks, 2 completed → Shows "Unresolved Tasks: 3"
- [ ] Product with 3 projects, 1 completed → Shows "Unfinished Projects: 2"
- [ ] Product with 2 vision docs → Shows "Vision Docs: 2"

### 11.2 Cascade Delete Accuracy
- [ ] Create product with:
  - [ ] 2 projects, 1 unfinished
  - [ ] 3 tasks, 2 unresolved
  - [ ] 1 vision document
- [ ] Click delete
- [ ] Dialog shows:
  - [ ] "1 unfinished projects (2 total projects)"
  - [ ] "2 unresolved tasks (3 total tasks)"
  - [ ] "1 vision documents"
- [ ] Delete product
- [ ] Verify in database (or next load) all related data deleted

### 11.3 Multi-Tenant Isolation
- [ ] Create second tenant account
- [ ] Tenant A sees only their products
- [ ] Cannot access Tenant B's products
- [ ] Cannot delete Tenant B's products

---

## Test 12: Performance

### 12.1 Page Load
- [ ] /Products page loads in < 2 seconds
- [ ] No noticeable lag or jank

### 12.2 Create Product
- [ ] Form validation is instant
- [ ] Submit shows loading state
- [ ] Product appears immediately after creation

### 12.3 List Rendering
- [ ] With 50+ products, page doesn't lag
- [ ] Search filtering is responsive

### 12.4 File Upload
- [ ] 2MB file uploads in < 5 seconds
- [ ] No browser freezing during upload

---

## Test 13: Notifications & Feedback

### 13.1 Success Notifications
- [ ] Product created → "Product created successfully" notification appears
- [ ] Product updated → "Product updated successfully" notification appears
- [ ] Product deleted → "Product deleted successfully" notification appears
- [ ] Vision document deleted → "Document deleted successfully" notification appears
- [ ] Product activated → "Product activated successfully" notification appears (if implemented)

### 13.2 Error Notifications
- [ ] Invalid product name → Error shows
- [ ] File upload fails → "Upload failed: [reason]" shows
- [ ] Delete fails → "Delete failed: [reason]" shows
- [ ] Network error → "Network error" message shows

### 13.3 Loading States
- [ ] Create button shows loading spinner while creating
- [ ] Delete button shows loading spinner while deleting
- [ ] Dialog shows "Calculating impact..." while loading cascade data

### 13.4 Notification Duration
- [ ] Success notifications disappear after 3 seconds
- [ ] Error notifications stay longer (5+ seconds) or require dismissal

---

## Post-Test Verification

### Browser Console
- [ ] No JavaScript errors (red X in console)
- [ ] No console warnings (yellow triangle in console)
- [ ] Network requests all show 2xx/3xx status (no 4xx/5xx)

### API Calls
Open Dev Tools → Network tab:
- [ ] GET /api/products/ → 200
- [ ] POST /api/products/ → 201
- [ ] PUT /api/products/{id}/ → 200
- [ ] DELETE /api/products/{id}/ → 200
- [ ] GET /api/products/{id}/cascade-impact → 200
- [ ] POST /api/vision-documents/ → 201
- [ ] DELETE /api/vision-documents/{id}/ → 200

### Local Storage
Open Dev Tools → Application → Local Storage:
- [ ] "currentProductId" stores active product ID
- [ ] "auth_token" present (logged in)

---

## Issues Found During Testing

### Issue Template

```
Issue #: [Number]
Title: [Short title]
Severity: [Critical/High/Medium/Low]
Steps to Reproduce:
1. [Step]
2. [Step]
3. [Step]

Expected Result:
[What should happen]

Actual Result:
[What actually happened]

Screenshot/Console Error:
[Paste any error messages or image]

Browser/Platform:
[Chrome, Firefox, etc. on Windows/Mac/Linux]
```

---

## Test Summary

### Test Execution

| Test Area | Status | Notes |
|-----------|--------|-------|
| 1. Product Card Display | [ ] Pass [ ] Fail | |
| 2. Create Product | [ ] Pass [ ] Fail | |
| 3. Edit Product | [ ] Pass [ ] Fail | |
| 4. Product Details | [ ] Pass [ ] Fail | |
| 5. Delete Product | [ ] Pass [ ] Fail | |
| 6. Product Context | [ ] Pass [ ] Fail | |
| 7. Accessibility | [ ] Pass [ ] Fail | |
| 8. Error Handling | [ ] Pass [ ] Fail | |
| 9. Responsive Design | [ ] Pass [ ] Fail | |
| 10. Browser Compat | [ ] Pass [ ] Fail | |
| 11. Data Consistency | [ ] Pass [ ] Fail | |
| 12. Performance | [ ] Pass [ ] Fail | |
| 13. Notifications | [ ] Pass [ ] Fail | |

### Overall Result
- [ ] PASS - Ready for production
- [ ] PASS WITH NOTES - Production ready with known limitations
- [ ] FAIL - Issues must be fixed

### Issues Found: [Number]
- Critical: [Number]
- High: [Number]
- Medium: [Number]
- Low: [Number]

### Sign-Off

**Tested By**: [Name]
**Date**: [Date]
**Platform**: [OS, Browser, Versions]
**Environment**: Production/Staging/Development

**Approved By**: [QA Lead]
**Date**: [Date]

---

**Test Checklist Version**: 1.0
**Last Updated**: 2025-10-25
