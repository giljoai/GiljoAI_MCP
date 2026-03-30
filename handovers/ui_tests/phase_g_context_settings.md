# Phase G: User Context Settings

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** User logged in, test product exists from Phase A
**Creates data:** No — settings changes only

---

## Steps

### G1. Navigate to Context Settings
1. Go to Settings > Context tab
2. **Verify:** Context depth configuration loads
3. **Verify:** Per-category depth sliders or toggles visible
4. **Verify:** Zero console errors

### G2. View Product Context Tuning
1. Navigate to Products view
2. Click "Tune context" button on the test product
3. **Verify:** Context tuning dialog/panel opens
4. **Verify:** Category toggles and depth controls render
5. **Verify:** Current settings displayed
6. **Verify:** Zero console errors

### G3. Modify Context Depth
1. Change a context depth setting (e.g., increase or decrease one category)
2. Save the change
3. **Verify:** Save confirmation appears
4. **Verify:** Setting persists after closing and reopening the dialog
5. **Verify:** Zero console errors

### G4. Verify Context Categories
1. Review all available context categories
2. **Verify:** Each category has a clear label and description
3. **Verify:** Enable/disable toggles work
4. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Context settings load and display correctly
- [ ] Product-level context tuning accessible
- [ ] Context depth changes save and persist
- [ ] Zero console errors throughout
