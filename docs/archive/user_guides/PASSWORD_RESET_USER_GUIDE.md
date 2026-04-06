# Password Reset User Guide

**GiljoAI MCP - Password Reset Functionality**
**Version**: 3.0
**Last Updated**: 2025-10-21

---

## Table of Contents

1. [Overview](#overview)
2. [Recovery PIN Basics](#recovery-pin-basics)
3. [Setting Up Your Recovery PIN](#setting-up-your-recovery-pin)
4. [Using Forgot Password](#using-forgot-password)
5. [Admin Password Reset](#admin-password-reset)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)
8. [FAQ](#faq)

---

## Overview

GiljoAI MCP uses a 4-digit recovery PIN system to help you recover your account if you forget your password. This guide explains how to set up and use the password reset features.

**Key Features**:
- Self-service password recovery using a 4-digit PIN
- Works offline (no email required)
- Admin can reset user passwords if needed
- Security features prevent unauthorized access

---

## Recovery PIN Basics

### What is a Recovery PIN?

A recovery PIN is a 4-digit number (like an ATM PIN) that allows you to reset your password if you forget it. It is stored securely (hashed with bcrypt) and never shown in plain text.

**PIN Requirements**:
- Exactly 4 digits (0000-9999)
- Numeric characters only
- You choose the PIN (no complexity requirements)

**Example PINs**:
- 1234 (valid but not recommended)
- 8765 (valid)
- 0000 (valid but not recommended)
- 9182 (valid and recommended)

**Important Notes**:
- Your recovery PIN is separate from your password
- You need BOTH username and PIN to reset your password
- If you forget both password AND PIN, contact your administrator

---

## Setting Up Your Recovery PIN

### Scenario 1: Fresh Installation (First Admin)

When you install GiljoAI MCP for the first time, you will create the admin account with a recovery PIN.

**Steps**:

1. Run `python startup.py` for the first time
2. The setup wizard will open in your browser
3. Complete the admin account form:
   - Enter your username (3-64 characters, letters/numbers/underscore/hyphen)
   - Enter your password (12+ characters, mixed case, digit, special character)
   - Confirm your password
   - **Enter a 4-digit recovery PIN** (choose a number you will remember)
   - **Confirm your recovery PIN** (must match)
4. Click "Create Admin Account"
5. You will be logged in automatically

**Your recovery PIN is now set and can be used to reset your password.**

---

### Scenario 2: New User (First Login)

If an administrator creates your account, you will receive a default password and must set up your recovery PIN on first login.

**Steps**:

1. Your administrator gives you:
   - Username: `john_doe`
   - Password: `GiljoMCP` (default password)

2. Go to the login page and enter your credentials

3. You will be redirected to the "Complete Account Setup" page

4. Complete the setup form:
   - Enter your current password: `GiljoMCP`
   - Enter a new password (12+ characters, mixed case, digit, special character)
   - Confirm your new password
   - **Enter a 4-digit recovery PIN** (choose a number you will remember)
   - **Confirm your recovery PIN** (must match)

5. Click "Complete Setup"

6. You will be redirected to the dashboard

**Your password is changed and recovery PIN is set.**

---

## Using Forgot Password

If you forget your password, you can reset it using your recovery PIN.

### Step-by-Step Instructions

1. **Go to the Login Page**
   - Navigate to your GiljoAI MCP login page
   - Example: `http://localhost:8000/login`

2. **Click "Forgot Password?"**
   - Below the login button, click the "Forgot Password?" link
   - A modal dialog will open

3. **Enter Your Username and PIN**
   - Enter your username (the one you use to log in)
   - Enter your 4-digit recovery PIN
   - Click "Verify PIN"

4. **If PIN is Correct**
   - The modal will show a password reset form
   - Enter your new password (12+ characters, mixed case, digit, special character)
   - Confirm your new password
   - Click "Reset Password"

5. **Success**
   - You will see a success message
   - The modal will close automatically
   - You can now log in with your new password

6. **If PIN is Incorrect**
   - You will see an error message: "Invalid username or PIN"
   - You have 5 attempts before your account is locked
   - The modal will show "Attempts remaining: X"

### Rate Limiting Protection

**Security Feature**: To prevent unauthorized access, the system limits failed PIN attempts.

**How it Works**:
- You have 5 attempts to enter the correct PIN
- After 5 failed attempts, your account is locked for 15 minutes
- During lockout, you cannot attempt password reset
- After 15 minutes, the lockout expires and you can try again

**Lockout Message**:
```
Account locked out due to too many failed attempts. Try again in 15 minutes.
```

**What to Do if Locked Out**:
1. Wait 15 minutes
2. Try again with the correct PIN
3. If you still can't remember, contact your administrator

---

## Admin Password Reset

If you are locked out and cannot remember your recovery PIN, your administrator can reset your password.

### For Users: Requesting a Password Reset

1. Contact your administrator (email, phone, or in-person)
2. Provide your username
3. Administrator will reset your password to the default: `GiljoMCP`
4. Log in with your username and the default password
5. You will be redirected to the "Complete Account Setup" page
6. Change your password and keep your recovery PIN (it is NOT changed by admin reset)

**Important**:
- Your recovery PIN remains unchanged during admin reset
- If you remember your PIN, you can still use "Forgot Password?" instead

---

### For Administrators: Resetting User Passwords

**Steps**:

1. Navigate to User Management
   - Click your avatar (top right)
   - Select "Users Management"

2. Find the user in the list
   - Use the search box if needed
   - Locate the user's row

3. Click "Reset Password"
   - Click the three-dot menu (⋮) in the Actions column
   - Select "Reset Password"

4. Confirm the reset
   - A confirmation dialog will appear
   - Review the warning messages:
     - Password will be reset to: `GiljoMCP`
     - User must change password on next login
     - Recovery PIN will remain unchanged
   - Click "Reset Password" to confirm

5. Notify the user
   - Tell the user their password is now `GiljoMCP`
   - User must log in and change password immediately
   - User's recovery PIN is still valid (if they set one)

**Important Notes**:
- User's recovery PIN is NOT changed by admin reset
- User will be forced to change password on next login
- Admin action is logged for security audit

---

## Troubleshooting

### Problem: "I forgot both my password AND my recovery PIN"

**Solution**: Contact your administrator for a password reset.

**Steps**:
1. Contact your administrator
2. Administrator resets your password to `GiljoMCP`
3. Log in with default password
4. Set a new password and a NEW recovery PIN

**Lesson**: Write down your recovery PIN in a secure location (like a password manager)

---

### Problem: "I'm locked out after 5 failed PIN attempts"

**Solution**: Wait 15 minutes, then try again.

**Steps**:
1. Wait 15 minutes for lockout to expire
2. Try "Forgot Password?" again with correct PIN
3. If you still can't remember your PIN, contact administrator

**Alternative**: Contact administrator for immediate password reset (bypasses lockout)

---

### Problem: "The Forgot Password button doesn't work"

**Troubleshooting Steps**:
1. Refresh the page (Ctrl+F5 or Cmd+Shift+R)
2. Clear your browser cache
3. Try a different browser
4. Check if JavaScript is enabled
5. Contact your administrator if issue persists

---

### Problem: "My recovery PIN isn't working"

**Possible Causes**:
1. You haven't set a recovery PIN yet (new users must set on first login)
2. You are entering the wrong PIN
3. You are locked out (5 failed attempts)

**Solutions**:
1. If new user: Log in with default password and set PIN on first login
2. Try different PINs you might have used
3. Wait 15 minutes if locked out
4. Contact administrator for password reset

---

### Problem: "I want to change my recovery PIN"

**Solution**: Currently, you can only change your recovery PIN by resetting your password.

**Steps (Self-Service)**:
1. Use "Forgot Password?" to reset your password with your current PIN
2. During password reset, you only change the password (PIN stays same)
3. Contact your administrator to reset your password to default
4. Log in with default password
5. Set new password AND new recovery PIN

**Alternative (Future Enhancement)**: A "Change PIN" feature will be added in a future release.

---

## Security Best Practices

### Choosing a Strong Recovery PIN

**Avoid Common PINs**:
- 0000, 1111, 2222, etc. (sequential digits)
- 1234, 4321 (sequential patterns)
- Your birthday (e.g., 0815 for August 15)
- Your year of birth (e.g., 1990)

**Recommended PINs**:
- Random 4-digit number (use password manager to generate)
- Combination of non-sequential digits
- Something memorable but not obvious

**Examples**:
- Good: 9182, 7054, 3296
- Bad: 1234, 0000, 1111

---

### Storing Your Recovery PIN Securely

**Recommended**:
- Store in a password manager (e.g., 1Password, LastPass, Bitwarden)
- Write down and keep in a secure location (safe, locked drawer)
- Share with a trusted person (if appropriate)

**NOT Recommended**:
- Plain text file on your computer
- Sticky note on your monitor
- Email or messaging apps
- Cloud storage without encryption

---

### Password Best Practices

**Strong Password Requirements**:
- At least 12 characters (longer is better)
- Mix of uppercase and lowercase letters
- At least one digit
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

**Example Strong Passwords**:
- `MyD0g!sAwesome2024`
- `Tr0ut#Fishing&Lakes`
- `C0ffee@Morning$Time`

**Password Manager Recommended**:
Use a password manager to generate and store strong, unique passwords.

---

### Account Security Tips

1. **Never share your password or PIN** with anyone (except administrator if needed)
2. **Use unique passwords** for each service (don't reuse)
3. **Change default passwords immediately** (GiljoMCP)
4. **Enable two-factor authentication** when available (future feature)
5. **Log out when done** (especially on shared computers)
6. **Report suspicious activity** to your administrator

---

## FAQ

### Q: What happens to my recovery PIN if an admin resets my password?

**A**: Your recovery PIN remains unchanged. You can still use "Forgot Password?" with your existing PIN after an admin reset.

---

### Q: Can I change my recovery PIN without resetting my password?

**A**: Not currently. You must go through the password reset process to set a new PIN. A "Change PIN" feature is planned for a future release.

---

### Q: How secure is the 4-digit recovery PIN?

**A**: The PIN is secured with:
- bcrypt hashing (same as passwords)
- Rate limiting (5 attempts, 15 minute lockout)
- Audit logging (all attempts tracked)
- Generic error messages (prevents user enumeration)

While 4 digits has limited entropy (10,000 combinations), the rate limiting makes brute force attacks impractical (would take ~5 weeks to try all combinations).

---

### Q: Can I use letters or special characters in my PIN?

**A**: No. The recovery PIN must be exactly 4 numeric digits (0-9).

---

### Q: What if I enter my PIN incorrectly?

**A**: You have 5 attempts. After 5 failed attempts, your account is locked for 15 minutes. The system will show you how many attempts remain.

---

### Q: Can I reset my password without the PIN?

**A**: Yes, your administrator can reset your password to the default (`GiljoMCP`). You can then log in and set a new password and PIN.

---

### Q: Will email-based password reset be available in the future?

**A**: Yes. Email-based password reset is planned for a future release. The recovery PIN will remain as a backup/offline option.

---

### Q: Is my recovery PIN visible to administrators?

**A**: No. Your recovery PIN is hashed with bcrypt before storage. Administrators cannot see your PIN. If you forget it, they can only reset your password to the default.

---

### Q: Can I use the same PIN as another user?

**A**: Yes, but it's not recommended for security reasons. Each user should have a unique PIN.

---

### Q: What happens if I try to reset someone else's password?

**A**: The system will return a generic error message ("Invalid username or PIN") without revealing whether the username exists. This prevents user enumeration attacks.

---

## Support

If you have questions or issues not covered in this guide:

1. **Check the Troubleshooting section** above
2. **Contact your administrator** for password resets or account issues
3. **Refer to the technical documentation** for developers/admins:
   - `PASSWORD_RESET_VALIDATION_REPORT.md` (detailed validation)
   - `PASSWORD_RESET_TECHNICAL_SUMMARY.md` (developer reference)
   - `Handover 0023` (implementation details)

---

**User Guide Version**: 1.0
**Last Updated**: 2025-10-21
**Handover**: 0023 - Password Reset Functionality
