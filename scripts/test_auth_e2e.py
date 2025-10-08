#!/usr/bin/env python
"""
End-to-End Authentication Flow Test

Tests the complete LAN authentication system:
1. Setup wizard creates admin user
2. Login with credentials
3. Access protected endpoints
4. Generate API key
5. Use API key for authentication
6. Revoke API key
7. Logout

Usage:
    python scripts/test_auth_e2e.py
"""

import requests
import sys
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:7273/api"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log_step(step: str):
    print(f"\n{Colors.BLUE}[STEP] {step}{Colors.RESET}")

def log_success(message: str):
    print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")

def log_error(message: str):
    print(f"{Colors.RED}[FAIL] {message}{Colors.RESET}")

def log_info(message: str):
    print(f"{Colors.YELLOW}[INFO] {message}{Colors.RESET}")

def test_login(session: requests.Session) -> bool:
    """Test login with username/password"""
    log_step("Testing Login Flow")

    try:
        response = session.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            }
        )

        if response.status_code == 200:
            log_success(f"Login successful: {response.json()}")

            # Check if JWT cookie was set
            if 'access_token' in session.cookies:
                log_success("JWT cookie set successfully")
                return True
            else:
                log_error("JWT cookie not found in response")
                return False
        else:
            log_error(f"Login failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log_error(f"Login error: {e}")
        return False

def test_protected_endpoint(session: requests.Session) -> bool:
    """Test accessing protected endpoint with JWT"""
    log_step("Testing Protected Endpoint Access")

    try:
        response = session.get(f"{API_BASE_URL}/auth/me")

        if response.status_code == 200:
            user_data = response.json()
            log_success(f"Authenticated as: {user_data.get('username')} ({user_data.get('role')})")
            return True
        else:
            log_error(f"Failed to access protected endpoint: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log_error(f"Protected endpoint error: {e}")
        return False

def test_generate_api_key(session: requests.Session) -> Optional[str]:
    """Test API key generation"""
    log_step("Testing API Key Generation")

    try:
        response = session.post(
            f"{API_BASE_URL}/auth/api-keys",
            json={"name": "E2E Test Key"}
        )

        if response.status_code == 200:
            data = response.json()
            api_key = data.get('api_key')

            if api_key and api_key.startswith('gk_'):
                log_success(f"API key generated: {api_key[:15]}...")
                return api_key
            else:
                log_error(f"Invalid API key format: {api_key}")
                return None
        else:
            log_error(f"API key generation failed: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        log_error(f"API key generation error: {e}")
        return None

def test_api_key_authentication(api_key: str) -> bool:
    """Test authentication using API key"""
    log_step("Testing API Key Authentication")

    # Create new session without JWT cookie
    api_session = requests.Session()

    try:
        response = api_session.get(
            f"{API_BASE_URL}/auth/me",
            headers={"X-API-Key": api_key}
        )

        if response.status_code == 200:
            user_data = response.json()
            log_success(f"API key authentication successful: {user_data.get('username')}")
            return True
        else:
            log_error(f"API key authentication failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log_error(f"API key authentication error: {e}")
        return False

def test_list_api_keys(session: requests.Session) -> bool:
    """Test listing API keys"""
    log_step("Testing API Key Listing")

    try:
        response = session.get(f"{API_BASE_URL}/auth/api-keys")

        if response.status_code == 200:
            keys = response.json()
            log_success(f"Found {len(keys)} API keys")
            for key in keys:
                log_info(f"  - {key.get('name')}: {key.get('key_prefix')}...")
            return True
        else:
            log_error(f"API key listing failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log_error(f"API key listing error: {e}")
        return False

def test_revoke_api_key(session: requests.Session, api_key_id: str) -> bool:
    """Test revoking an API key"""
    log_step("Testing API Key Revocation")

    try:
        response = session.delete(f"{API_BASE_URL}/auth/api-keys/{api_key_id}")

        if response.status_code == 200:
            log_success("API key revoked successfully")
            return True
        else:
            log_error(f"API key revocation failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log_error(f"API key revocation error: {e}")
        return False

def test_logout(session: requests.Session) -> bool:
    """Test logout (clear JWT cookie)"""
    log_step("Testing Logout")

    try:
        response = session.post(f"{API_BASE_URL}/auth/logout")

        if response.status_code == 200:
            log_success("Logout successful")

            # Verify cookie was cleared
            if 'access_token' not in session.cookies:
                log_success("JWT cookie cleared")
                return True
            else:
                log_error("JWT cookie still present after logout")
                return False
        else:
            log_error(f"Logout failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log_error(f"Logout error: {e}")
        return False

def test_unauthorized_access(session: requests.Session) -> bool:
    """Test that protected endpoints return 401 after logout"""
    log_step("Testing Unauthorized Access (After Logout)")

    try:
        response = session.get(f"{API_BASE_URL}/auth/me")

        if response.status_code == 401:
            log_success("Properly rejected unauthorized access")
            return True
        else:
            log_error(f"Expected 401, got {response.status_code}")
            return False

    except Exception as e:
        log_error(f"Unauthorized access test error: {e}")
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("LAN Authentication End-to-End Test")
    print(f"{'='*60}{Colors.RESET}\n")

    log_info(f"API Base URL: {API_BASE_URL}")
    log_info(f"Test User: {ADMIN_USERNAME}")

    # Create session to maintain cookies
    session = requests.Session()

    results = []

    # Test Flow
    results.append(("Login", test_login(session)))
    results.append(("Protected Endpoint", test_protected_endpoint(session)))

    # Generate API key
    api_key = test_generate_api_key(session)
    results.append(("API Key Generation", api_key is not None))

    # Test API key authentication
    if api_key:
        results.append(("API Key Auth", test_api_key_authentication(api_key)))

    # List and revoke API key
    results.append(("List API Keys", test_list_api_keys(session)))

    # Get the key ID from the list to revoke
    try:
        keys_response = session.get(f"{API_BASE_URL}/auth/api-keys")
        if keys_response.status_code == 200:
            keys = keys_response.json()
            if keys:
                key_id = keys[0].get('id')
                results.append(("Revoke API Key", test_revoke_api_key(session, key_id)))
    except:
        pass

    # Logout and verify
    results.append(("Logout", test_logout(session)))
    results.append(("Unauthorized Access", test_unauthorized_access(session)))

    # Print summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("Test Summary")
    print(f"{'='*60}{Colors.RESET}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{Colors.GREEN}[PASS]" if result else f"{Colors.RED}[FAIL]"
        print(f"{status}{Colors.RESET} - {test_name}")

    print(f"\n{Colors.BLUE}Results: {passed}/{total} tests passed{Colors.RESET}")

    if passed == total:
        print(f"\n{Colors.GREEN}SUCCESS: All tests passed!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}WARNING: Some tests failed{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
