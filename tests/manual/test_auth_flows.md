# Authentication Flow Manual Testing Checklist

**Test Date:** 2025-10-08
**Frontend URL:** http://10.1.0.164:7274
**API URL:** http://10.1.0.164:7272
**Mode:** LAN (local development)

## Prerequisites
- ✅ Frontend running on http://10.1.0.164:7274
- ✅ Backend API running on http://10.1.0.164:7272
- ✅ Database connection verified

## Test Credentials
- **Admin User:** admin / admin123
- **Developer User:** dev / dev123
- **Viewer User:** viewer / viewer123

---

## Test 1: Role Badge Display
**Objective:** Verify role badges show correct colors in user menu

### Steps:
1. Login as admin user
2. Click user menu (account icon in top-right)
3. **Expected:** See "admin" badge with red/error color
4. Logout
5. Login as developer user
6. Click user menu
7. **Expected:** See "developer" badge with blue/primary color
8. Logout
9. Login as viewer user
10. Click user menu
11. **Expected:** See "viewer" badge with green/success color

**Result:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________

---

## Test 2: Session Persistence on Page Refresh
**Objective:** User session persists across page refreshes

### Steps:
1. Login as any user (e.g., admin)
2. Navigate to Dashboard
3. Press F5 to refresh the page
4. **Expected:** User remains logged in, no redirect to login page
5. Navigate to Projects page
6. Press F5 to refresh
7. **Expected:** User remains logged in on Projects page
8. Check user menu
9. **Expected:** Username and role badge still displayed correctly

**Result:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________

---

## Test 3: Enhanced Error Handling
**Objective:** Login errors show specific, helpful messages

### Test 3a: Invalid Credentials
1. Go to login page
2. Enter username: "wronguser"
3. Enter password: "wrongpass"
4. Click "Sign In"
5. **Expected:** Error message: "Invalid username or password"
6. **Expected:** Password field is cleared
7. **Expected:** Username field retains "wronguser"

**Result:** ⬜ PASS / ⬜ FAIL

### Test 3b: Error Clears on Input
1. After seeing error from Test 3a
2. Start typing in username field
3. **Expected:** Error message disappears
4. Stop typing, let error appear again
5. Start typing in password field
6. **Expected:** Error message disappears

**Result:** ⬜ PASS / ⬜ FAIL

### Test 3c: Network Error (requires API offline)
1. Stop the API server
2. Try to login
3. **Expected:** Error message: "Network error - please check your connection and try again"
4. Restart API server

**Result:** ⬜ PASS / ⬜ FAIL (or SKIP if can't stop API)

**Notes:**
_____________________________________________

---

## Test 4: "Remember Me" Functionality
**Objective:** Username is saved and pre-filled when "Remember me" is checked

### Test 4a: Save Username
1. Go to login page
2. Enter username: "admin"
3. Check the "Remember me" checkbox
4. Enter password and login successfully
5. Logout
6. **Expected:** Redirected to login page
7. **Expected:** Username field pre-filled with "admin"
8. **Expected:** "Remember me" checkbox is checked

**Result:** ⬜ PASS / ⬜ FAIL

### Test 4b: Don't Save Username
1. After Test 4a, uncheck "Remember me"
2. Login successfully
3. Logout
4. **Expected:** Username field is empty
5. **Expected:** "Remember me" checkbox is unchecked

**Result:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________

---

## Test 5: Loading States
**Objective:** Form shows appropriate loading indicators during login

### Steps:
1. Go to login page
2. Enter valid credentials
3. Click "Sign In"
4. **During loading (observe quickly):**
   - ⬜ Button text changes to "Logging in..."
   - ⬜ Button shows loading spinner
   - ⬜ Username field is disabled (grayed out)
   - ⬜ Password field is disabled (grayed out)
   - ⬜ "Remember me" checkbox is disabled
   - ⬜ Button is disabled (can't double-click)
5. **After successful login:**
   - ⬜ Success message shows briefly: "Login successful! Redirecting..."
   - ⬜ Redirects to dashboard

**Result:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________

---

## Test 6: Localhost Bypass (if applicable)
**Objective:** Localhost (127.0.0.1) bypasses authentication completely

### Steps:
1. Access frontend at http://127.0.0.1:7274 (if available)
2. **Expected:** Direct access to dashboard, no login required
3. Try accessing protected routes
4. **Expected:** All routes accessible without login

**Result:** ⬜ PASS / ⬜ FAIL / ⬜ N/A (not localhost)

**Notes:**
_____________________________________________

---

## Test 7: Logout Functionality
**Objective:** Logout clears session and redirects to login

### Steps:
1. Login as any user
2. Click user menu
3. Click "Logout"
4. **Expected:** Redirected to login page
5. **Expected:** Cookie cleared (check browser DevTools > Application > Cookies)
6. Try to access /projects directly (type in URL bar)
7. **Expected:** Redirected back to login page with redirect parameter
8. Login successfully
9. **Expected:** Redirected to /projects (original destination)

**Result:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________

---

## Test 8: Protected Routes (Admin-Only)
**Objective:** Users page is only accessible to admin users

### Test 8a: Admin Access
1. Login as admin
2. Check navigation menu
3. **Expected:** "Users" menu item is visible
4. Click "Users"
5. **Expected:** Users management page loads successfully

**Result:** ⬜ PASS / ⬜ FAIL

### Test 8b: Non-Admin Access
1. Logout
2. Login as developer or viewer
3. Check navigation menu
4. **Expected:** "Users" menu item is NOT visible
5. Try to access /users directly (type in URL bar)
6. **Expected:** Redirected to dashboard (access denied)

**Result:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________

---

## Test 9: Redirect After Login
**Objective:** User is redirected to originally requested page after login

### Steps:
1. Logout (ensure not authenticated)
2. In URL bar, type: http://10.1.0.164:7274/projects
3. **Expected:** Redirected to login with ?redirect=/projects
4. Enter credentials and login
5. **Expected:** Automatically redirected to /projects page

**Result:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________

---

## Summary

**Total Tests:** 9 (with sub-tests)
**Passed:** _____ / 9
**Failed:** _____ / 9
**Skipped:** _____ / 9

### Issues Found:
1. _____________________________________________
2. _____________________________________________
3. _____________________________________________

### Recommendations:
- [ ] Ready for Phase 2
- [ ] Needs follow-up work (see issues above)

**Tester Name:** ___________________
**Completion Date:** ___________________
