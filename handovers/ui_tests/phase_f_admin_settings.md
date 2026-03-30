# Phase F: Admin Settings

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** User logged in with admin role
**Creates data:** No — read-only navigation

---

## Steps

### F1. Navigate to Admin Settings
1. Navigate to `/admin` or find admin settings via user menu
2. **Verify:** Admin settings page loads
3. **Verify:** Admin-only sections visible (user management, system config)
4. **Verify:** Zero console errors

### F2. User Management
1. Navigate to user management section
2. **Verify:** User list loads with current users
3. **Verify:** User roles displayed correctly
4. **Verify:** Date formatting on user creation dates
5. **Verify:** Zero console errors

### F3. System Configuration
1. Navigate to system/network configuration
2. **Verify:** Network settings display (bind address, ports, HTTPS status)
3. **Verify:** HTTPS instructions text matches 0769b updates
4. **Verify:** Database connection status visible
5. **Verify:** Zero console errors

### F4. Security Settings
1. Navigate to security settings tab
2. **Verify:** Security configuration loads (CSRF, CORS, session settings)
3. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Admin settings accessible
- [ ] User management renders correctly
- [ ] System configuration displays current values
- [ ] Network settings text matches recent updates
- [ ] Zero console errors across all admin sections
