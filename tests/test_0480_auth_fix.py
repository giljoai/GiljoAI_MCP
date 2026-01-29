"""
Quick validation test for 0480 exception handling in auth/messages endpoints.

Validates that:
1. Auth endpoint login() does NOT check for dict["success"]
2. Messages endpoint send_message() does NOT check for dict["success"]
3. Code properly uses exception-based flow
"""

import pytest
import inspect


@pytest.mark.asyncio
async def test_auth_endpoint_does_not_check_dict_success():
    """
    Validate that auth.login() endpoint does NOT check result["success"].

    The endpoint should expect:
    - Service returns dict with data on success
    - Service raises exception on failure
    """
    from api.endpoints import auth as auth_module

    # Read the login function source
    source = inspect.getsource(auth_module.login)

    # Check that we don't have dict success checking
    assert 'if result["success"]' not in source, "Login endpoint still checking dict['success']"
    assert 'if not result["success"]' not in source, "Login endpoint still checking dict['success']"
    assert 'result.get("success")' not in source, "Login endpoint still checking dict['success']"

    # Check that we DO have exception-based flow
    assert 'await auth_service.authenticate_user' in source, "Login endpoint not calling service"
    assert 'auth_result' in source, "Login endpoint not using result variable"

    print("[PASS] Login endpoint does NOT check dict['success']")


@pytest.mark.asyncio
async def test_messages_endpoint_does_not_check_dict_success():
    """
    Validate that messages.send_message() endpoint does NOT check result["success"].

    The endpoint should expect:
    - Service returns dict with data on success
    - Service raises exception on failure
    """
    from api.endpoints import messages as messages_module

    # Read the send_message function source
    source = inspect.getsource(messages_module.send_message)

    # Check that we don't have dict success checking
    assert 'if result["success"]' not in source, "Messages endpoint still checking dict['success']"
    assert 'if not result["success"]' not in source, "Messages endpoint still checking dict['success']"
    assert 'result.get("success")' not in source, "Messages endpoint still checking dict['success']"

    # Check that we DO have exception-based flow (direct use of result)
    assert 'result["message_id"]' in source, "Messages endpoint not using result data directly"

    print("[PASS] Messages endpoint does NOT check dict['success']")


@pytest.mark.asyncio
async def test_auth_endpoint_updated_comment():
    """Verify the endpoint has the 0480 migration comment."""
    from api.endpoints import auth as auth_module

    source = inspect.getsource(auth_module.login)

    # Check for 0480 migration comment
    assert "0480 migration" in source or "Service raises AuthenticationError on failure" in source, \
        "Login endpoint missing 0480 migration documentation"

    print("[PASS] Login endpoint has 0480 migration documentation")


if __name__ == "__main__":
    import asyncio

    print("\n=== Testing 0480 Exception Handling Migration ===\n")

    asyncio.run(test_auth_endpoint_does_not_check_dict_success())
    asyncio.run(test_messages_endpoint_does_not_check_dict_success())
    asyncio.run(test_auth_endpoint_updated_comment())

    print("\n=== All 0480 validation tests passed! ===\n")
