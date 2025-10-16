# Handover 0023: Password Reset Functionality

**Handover ID**: 0023
**Creation Date**: 2025-10-15
**Target Date**: TBD
**Priority**: MEDIUM
**Type**: FEATURE REQUEST / PROBLEM IDENTIFICATION
**Status**: Not Started - Requires Design Decision
**Dependencies**: None

---

## 1. Context and Background

**Purpose**: Implement a secure password reset mechanism for users who have forgotten their password or are locked out of the system.

**Current State**:
- Users can change password if they know current password (`/api/auth/change-password`)
- Default admin password can be changed during first-time setup
- **NO password reset mechanism exists** for forgotten passwords
- No "Forgot Password" link on login page
- No email-based password reset workflow
- No admin-initiated password reset for other users

**Problem Identification**:
During authentication debugging (Handover 0022), we identified that users who forget their password have NO way to reset it. This is a critical UX gap, especially for:
- Users who forget custom passwords after initial setup
- Network/LAN deployments where users cannot access the database directly
- Multi-user environments (future feature)

**Target State**:
- Secure password reset mechanism implemented
- User-friendly "Forgot Password" workflow
- Admin ability to reset user passwords (for multi-user future)
- Proper security measures (time-limited tokens, email verification, etc.)

---

## 2. Open Questions and Design Decisions Needed

### Critical Questions:

**Q1: Email Infrastructure**
- **Question**: Does GiljoAI MCP have email sending capability configured?
- **Impact**: Email-based password reset requires SMTP configuration
- **Options**:
  - a) Implement full email system (SMTP, templates, etc.)
  - b) Use alternative reset mechanism (admin-assisted, security questions, etc.)
  - c) Database-only reset (requires database access)
- **User Decision Required**: ⚠️ **YES**

**Q2: Single-User vs Multi-User Context**
- **Question**: Is password reset needed NOW (single admin user) or later (multi-user)?
- **Current State**: System has single admin user by default
- **Impact**:
  - Single-user: Simpler solution (database reset script, admin CLI tool)
  - Multi-user: Full featured reset system with email workflow
- **User Decision Required**: ⚠️ **YES**

**Q3: Security vs Convenience Trade-off**
- **Question**: What security level is appropriate for password reset?
- **Options**:
  - a) **High Security**: Email verification + time-limited token + 2FA
  - b) **Medium Security**: Email verification + time-limited token
  - c) **Low Security**: Admin can reset any password
  - d) **Emergency**: Database direct access (dev tool)
- **User Decision Required**: ⚠️ **YES**

**Q4: Deployment Context Impact**
- **Question**: Does reset mechanism differ for localhost vs LAN vs future SaaS?
- **Current Deployment**: v3.0 unified architecture (localhost + LAN)
- **Considerations**:
  - Localhost: Database access available (simpler solution)
  - LAN: Network users may not have DB access
  - SaaS (future): Requires full email-based reset
- **User Decision Required**: ⚠️ **YES**

---

## 3. Proposed Solutions (Pending User Decision)

### Solution A: Email-Based Password Reset (Standard Approach)

**Pros**:
- ✅ Industry standard UX
- ✅ Secure (time-limited tokens)
- ✅ Works for all deployment contexts
- ✅ Scales to multi-user

**Cons**:
- ❌ Requires email infrastructure (SMTP config, templates)
- ❌ More complex to implement
- ❌ Overkill for single-user localhost deployments

**Implementation Overview**:
```
1. User clicks "Forgot Password" on login page
2. System sends email with time-limited reset token (15 min expiry)
3. User clicks link in email → Redirected to reset password page
4. User enters new password (with validation)
5. Token validated and consumed → Password updated
6. User redirected to login with success message
```

**Files to Modify**:
- `api/endpoints/auth.py` - Add `/forgot-password` and `/reset-password` endpoints
- `frontend/src/views/Login.vue` - Add "Forgot Password" link
- `frontend/src/views/PasswordReset.vue` - New component for reset flow
- `src/giljo_mcp/email/` - New email service module (SMTP config, templates)
- `src/giljo_mcp/models.py` - Add `PasswordResetToken` table

---

### Solution B: Admin CLI Tool (Quick Fix for Single-User)

**Pros**:
- ✅ Simple to implement
- ✅ No email infrastructure needed
- ✅ Good for localhost/dev environments
- ✅ Database owner can always reset

**Cons**:
- ❌ Requires database access
- ❌ Not user-friendly for non-technical users
- ❌ Doesn't scale to multi-user
- ❌ Not suitable for production/SaaS

**Implementation Overview**:
```python
# scripts/reset_password.py
python scripts/reset_password.py --username admin --new-password "NewSecurePass123!"
```

**Files to Create**:
- `scripts/reset_password.py` - CLI tool to reset password directly in DB
- Update `dev_tool` to include password reset UI

---

### Solution C: Enhanced Dev Tool (Middle Ground)

**Pros**:
- ✅ User-friendly GUI
- ✅ No email needed
- ✅ Works for localhost + LAN (if user has dev tool access)
- ✅ Can be extended to admin panel later

**Cons**:
- ❌ Requires physical/network access to server
- ❌ Security concern (anyone with dev tool access can reset)
- ❌ Doesn't work for remote SaaS scenarios

**Implementation Overview**:
- Add "Reset Password" section to `dev_tool`
- Requires database credentials (security confirmation)
- Updates password hash directly in database
- Shows success/error messages

**Files to Modify**:
- `dev_tool` (Python GUI) - Add password reset tab
- Backend: Add admin endpoint `/admin/reset-user-password` (admin-only)

---

## 4. Technical Considerations

### Database Schema Changes (Solution A)

```python
# src/giljo_mcp/models.py
class PasswordResetToken(Base):
    """Password reset tokens for forgot-password workflow"""
    __tablename__ = 'password_reset_tokens'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    token_hash = Column(String, nullable=False)  # Hashed token
    token_prefix = Column(String, nullable=False)  # First 8 chars for display
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 15 min expiry
    used_at = Column(DateTime(timezone=True))  # NULL = not used yet
    ip_address = Column(String)  # For security audit
    user_agent = Column(String)  # For security audit

    # Relationships
    user = relationship('User', back_populates='password_reset_tokens')
```

### API Endpoints (Solution A)

```python
# api/endpoints/auth.py

@router.post("/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db_session)):
    """
    Send password reset email to user.

    1. Find user by email
    2. Generate time-limited reset token (15 min)
    3. Send email with reset link
    4. Return success (don't reveal if email exists - security)
    """
    pass

@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    confirm_password: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Reset password using reset token.

    1. Validate token (not expired, not used)
    2. Validate password requirements
    3. Update user password
    4. Mark token as used
    5. Return success
    """
    pass
```

### Email Service (Solution A)

```python
# src/giljo_mcp/email/email_service.py
class EmailService:
    """Send transactional emails (password reset, notifications)"""

    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password

    async def send_password_reset_email(self, user_email: str, reset_token: str, reset_url: str):
        """Send password reset email with link"""
        template = self._load_template('password_reset.html')
        html_body = template.render(reset_url=reset_url, user_email=user_email)

        await self._send_email(
            to=user_email,
            subject="GiljoAI MCP - Password Reset Request",
            html_body=html_body
        )
```

---

## 5. Security Considerations

### Best Practices to Implement:

1. **Token Security**:
   - Hash tokens before storing in database (like API keys)
   - Use cryptographically secure random token generation
   - Time-limited tokens (15 minutes recommended)
   - One-time use only (mark as used after successful reset)

2. **Rate Limiting**:
   - Limit password reset requests per IP (prevent spam)
   - Limit password reset requests per email (prevent abuse)
   - Exponential backoff for failed attempts

3. **User Privacy**:
   - Don't reveal if email exists in system (prevent enumeration)
   - Always return success message even if email not found
   - Log all reset attempts for security audit

4. **Email Security**:
   - Use HTTPS-only reset links
   - Include IP address and timestamp in reset email
   - Warn user if they didn't request reset

---

## 6. Testing Requirements

### Unit Tests (Solution A):
```python
# tests/test_password_reset.py
def test_forgot_password_valid_email():
    """Test forgot password with valid email"""
    pass

def test_forgot_password_invalid_email():
    """Test forgot password with invalid/non-existent email"""
    pass

def test_reset_password_valid_token():
    """Test password reset with valid token"""
    pass

def test_reset_password_expired_token():
    """Test password reset with expired token"""
    pass

def test_reset_password_used_token():
    """Test password reset with already-used token"""
    pass
```

### Integration Tests:
- Email sending and delivery
- Token generation and validation
- Database updates after reset
- Frontend navigation flow

### Manual Testing:
1. Click "Forgot Password" on login
2. Enter email and submit
3. Receive email with reset link
4. Click reset link
5. Enter new password
6. Verify login with new password works
7. Verify old password no longer works
8. Verify reset link can't be used twice

---

## 7. Documentation Requirements

- User guide: "How to reset forgotten password"
- Admin guide: "Managing user password resets"
- Developer guide: "Email service configuration"
- Security audit documentation

---

## 8. Recommended Approach (Pending User Decision)

**For NOW (Single-User Localhost)**:
- Implement **Solution B** (Admin CLI Tool) as immediate fix
- Document in `/docs/guides/PASSWORD_RESET.md`
- Add to `dev_tool` for GUI access

**For FUTURE (Multi-User Production)**:
- Implement **Solution A** (Email-Based Reset) when multi-user launched
- Add to roadmap as Phase 2 enhancement
- Can coexist with CLI tool (different use cases)

---

## 9. Next Steps

**User Decisions Required**:
1. ⚠️ **Which solution to implement?** (A, B, C, or combination)
2. ⚠️ **When is this needed?** (Now vs later)
3. ⚠️ **Email infrastructure available?** (Can we send emails?)
4. ⚠️ **Security level preference?** (High/Medium/Low)

**Once Decisions Made**:
1. Create detailed implementation plan
2. Design database schema (if Solution A)
3. Configure email service (if Solution A)
4. Implement chosen solution
5. Write comprehensive tests
6. Update documentation
7. Test across all deployment contexts

---

## 10. Related Handovers

- **Handover 0022**: Authentication Cookie/JWT Debugging - Where this issue was identified
- **Future Multi-User Handover**: Will need full password reset system

---

**Handover Status**: Awaiting User Design Decisions
**Estimated Effort**:
- Solution A: 40-60 hours (full email-based system)
- Solution B: 4-8 hours (CLI tool)
- Solution C: 12-20 hours (dev tool integration)

**Impact**: Critical UX feature for users who forget passwords

---

## 11. Additional Notes

**Current Workaround** (Until Implemented):
- User with database access can reset password directly:
  ```sql
  -- Connect to database as postgres owner
  psql -U postgres -d giljo_mcp

  -- Reset admin password to 'admin' (user must change after login)
  UPDATE users
  SET password_hash = '$2b$12$...' -- bcrypt hash of 'admin'
  WHERE username = 'admin';
  ```

**Security Risk of Current Workaround**:
- Requires database credentials (high privilege)
- Manual SQL is error-prone
- No audit trail
- Not user-friendly

This handover documents the problem and proposes solutions, but **requires user input** on design decisions before implementation can begin.
