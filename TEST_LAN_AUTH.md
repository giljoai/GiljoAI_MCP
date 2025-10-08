# How to Test LAN Authentication

## Quick Start (No Reinstall Needed!)

The authentication system is already installed. You just need to:
1. ✅ Services are already running (API on port 8823, Frontend on 7274)
2. ⚠️ Need to create the first admin user
3. 🧪 Test the login flow

---

## Step 1: Create Admin User via Setup Wizard

The easiest way is to use the existing setup wizard:

### Option A: Via Frontend UI (Recommended)
1. Open browser: **http://localhost:7274**
2. If you see the setup wizard → complete it with LAN mode selected
3. It will create the admin user automatically

### Option B: Via API Call
```bash
curl -X POST http://localhost:8823/api/setup/complete \
  -H "Content-Type: application/json" \
  -d '{
    "network_mode": "lan",
    "tools_attached": ["claude-code"],
    "serena_enabled": true,
    "lan_config": {
      "admin_username": "admin",
      "admin_password": "admin123",
      "server_ip": "10.1.0.164",
      "hostname": "giljo.local",
      "firewall_configured": true
    }
  }'
```

### Option C: Direct Database Insert (Advanced)
```bash
# Use the database credentials from your .env file
python -c "
import sys
sys.path.insert(0, 'src')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.hash import bcrypt
from uuid import uuid4
from giljo_mcp.models import User

# Update with your actual database password
engine = create_engine('postgresql://giljo_user:YOUR_PASSWORD@localhost:5432/giljo_mcp')
Session = sessionmaker(bind=engine)
session = Session()

user = User(
    id=uuid4(),
    username='admin',
    password_hash=bcrypt.hash('admin123'),
    role='admin',
    is_active=True,
    tenant_key='default'
)
session.add(user)
session.commit()
print('Admin user created!')
"
```

---

## Step 2: Test Login Flow

### Via Browser (Visual Test)
1. **Open Login Page**: http://localhost:7274/login
2. **Enter Credentials**:
   - Username: `admin`
   - Password: `admin123` (or whatever you set)
3. **Click "Sign In"**
4. **Should redirect to**: Dashboard (http://localhost:7274/)

### Via API (Command Line Test)
```bash
# Login and get JWT cookie
curl -X POST http://localhost:8823/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  -c cookies.txt \
  -v

# Should return 200 OK with:
# {
#   "message": "Login successful",
#   "username": "admin",
#   "role": "admin"
# }
```

---

## Step 3: Test API Key Generation

### Via Browser
1. **Go to Settings**: http://localhost:7274/settings
2. **Click "API Keys" tab**
3. **Click "Generate New Key"**
4. **Enter name**: "Test Key"
5. **Click "Generate"**
6. **Copy the key** (starts with `gk_`)
7. **Save it somewhere safe** (shown only once!)

### Via API
```bash
# Generate API key (using JWT cookie from login)
curl -X POST http://localhost:8823/api/auth/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Key"}' \
  -b cookies.txt

# Should return:
# {
#   "api_key": "gk_xxxxxxxxxxxxx",
#   "name": "Test Key",
#   "created_at": "2025-10-07T..."
# }
```

---

## Step 4: Test API Key Authentication

```bash
# Use the API key you generated
export API_KEY="gk_your_key_here"

# Test authenticated request
curl -X GET http://localhost:8823/api/auth/me \
  -H "X-API-Key: $API_KEY"

# Should return user info:
# {
#   "username": "admin",
#   "role": "admin",
#   "email": null
# }
```

---

## Step 5: Test Logout

### Via Browser
1. **Click user avatar** (top-right corner)
2. **Click "Logout"**
3. **Should redirect to**: Login page

### Via API
```bash
# Logout (clears JWT cookie)
curl -X POST http://localhost:8823/api/auth/logout \
  -b cookies.txt \
  -c cookies.txt

# Try to access protected endpoint (should fail)
curl -X GET http://localhost:8823/api/auth/me \
  -b cookies.txt

# Should return 401 Unauthorized
```

---

## Troubleshooting

### Issue 1: "Invalid credentials" when logging in
**Cause:** Admin user doesn't exist yet
**Solution:** Run one of the admin creation methods above (setup wizard recommended)

### Issue 2: Can't find login page
**Cause:** Frontend not running or wrong port
**Solution:**
```bash
cd frontend
npm run dev
# Opens on http://localhost:7274
```

### Issue 3: API returning "Not Found" (404)
**Cause:** Wrong port or API not running
**Solution:** Check which port API is running on:
```bash
curl http://localhost:8823/api/setup/status
# or try other ports: 7272, 7273
```

### Issue 4: "This endpoint requires authentication (not available in localhost mode)"
**Cause:** API is in localhost mode, not LAN mode
**Solution:**
1. Check config.yaml: `installation.mode` should be `lan` (not `localhost`)
2. Restart API server after changing mode

### Issue 5: Database connection error
**Cause:** PostgreSQL not running or wrong credentials
**Solution:**
```bash
# Check if PostgreSQL is running
# Windows: Check Services, look for "postgresql-x64-18"

# Test connection
# (Using psql if available in PATH)
```

---

## Current Service Status

**API Server:**
- ✅ Running on **http://localhost:8823**
- Mode: `local` (should be `lan` for auth to work fully)
- Auth endpoints available at: `/api/auth/*`

**Frontend:**
- ✅ Should be running on **http://localhost:7274**
- Login page: http://localhost:7274/login
- Dashboard: http://localhost:7274/

---

## Quick Test Checklist

- [ ] Open http://localhost:7274
- [ ] If setup wizard shows → complete it with LAN mode
- [ ] If dashboard shows → you may already be in localhost mode (no auth needed)
- [ ] Navigate to http://localhost:7274/login manually
- [ ] Login with admin/admin123
- [ ] Go to Settings → API Keys
- [ ] Generate a new API key
- [ ] Copy the key (shown once!)
- [ ] Use the key in an API request
- [ ] Logout and verify redirect to login

---

## Important Notes

1. **Localhost Bypass:** Requests from `127.0.0.1` may bypass authentication depending on mode
2. **Config Mode:** Check `config.yaml` - `installation.mode` should be `lan` for full auth
3. **First Time:** You MUST create an admin user before you can log in
4. **API Keys:** Shown only once after generation - copy immediately!
5. **Ports:** API auto-selects available port (check startup logs)

---

## For Production Deployment

See the comprehensive guides:
- **[LAN_AUTH_USER_GUIDE.md](docs/LAN_AUTH_USER_GUIDE.md)** - Complete user documentation
- **[LAN_AUTH_DEPLOYMENT_CHECKLIST.md](docs/LAN_AUTH_DEPLOYMENT_CHECKLIST.md)** - Production deployment
- **[LAN_AUTH_QUICK_REFERENCE.md](docs/LAN_AUTH_QUICK_REFERENCE.md)** - Quick reference

---

## Need Help?

The comprehensive documentation is in `docs/`:
- User Guide
- Architecture
- API Reference
- Deployment Checklist
- Migration Guide
- Quick Reference

**Everything is already installed - you just need to create the admin user and test!** 🚀
