# Phase A: Product Creation, Vision Document Upload & Chunking

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** User logged in, on any page
**Creates data:** Yes — 1 test product + 1 vision document

---

## Steps

### A1. Navigate to Products
1. Click "Products" in navigation drawer
2. **Verify:** Products page loads, existing products visible
3. **Verify:** Zero console errors

### A2. Create New Product
1. Click "New Product" button
2. Fill in product form:
   - **Name:** `UI Test Product - [date]`
   - **Description:** `Automated UI test product for quality verification`
3. Complete any required fields (check tab order: setup, info, ...)
4. Save/submit the product
5. **Verify:** Product appears in the product list
6. **Verify:** Success notification/toast appears
7. **Verify:** Zero console errors

### A3. Upload Vision Document
1. Click on the newly created product to open details
2. Navigate to the vision/documents section
3. Upload test file: `C:\Projects\TinyContacts\docs\product_proposal.txt`
4. **Verify:** Upload progress indicator appears
5. **Verify:** Upload completes without error
6. **Verify:** Document appears in the document list
7. **Verify:** Zero console errors

### A4. Verify Chunking
1. After upload completes, check that the document was processed
2. **Verify:** Chunk count or chunk status is displayed
3. **Verify:** Document status shows as processed/ready
4. **Verify:** Zero console errors

### A5. Verify Product Detail View
1. Open the product detail dialog/view
2. **Verify:** All tabs load (check tab order matches 0769b findings: setup, info, ...)
3. **Verify:** Product metadata displays correctly
4. **Verify:** Vision document is listed with correct filename
5. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Product created successfully
- [ ] Vision document uploaded and chunked
- [ ] Product appears in list with correct details
- [ ] Zero console errors throughout

## Cleanup
Note the product ID for use in Phase B. Do NOT delete yet — needed for project creation.
