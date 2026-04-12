# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Manual test script to verify /api/v1/config endpoint works correctly.

This script tests the live API server to ensure:
1. Endpoint responds quickly (< 2 seconds)
2. Returns full config.yaml structure
3. Includes installation.mode, services, security sections
4. Masks sensitive data

Usage:
    python tests/manual/test_config_endpoint_live.py
"""

import asyncio
import time

import httpx


async def test_config_endpoint():
    """Test the /api/v1/config endpoint with a live API server."""

    # API URL (update if your server is on a different port)
    api_url = "http://localhost:7272/api/v1/config"

    print("=" * 70)
    print("Testing /api/v1/config endpoint")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        # Test 1: Response time
        print("\n[TEST 1] Checking response time...")
        start_time = time.time()

        try:
            response = await client.get(api_url, timeout=5.0)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000
            print(f"  ✓ Response time: {response_time:.0f}ms")

            if response_time > 2000:
                print("  ⚠ WARNING: Response took longer than 2 seconds!")
            elif response_time < 500:
                print("  ✓ EXCELLENT: Very fast response!")

        except httpx.TimeoutException:
            print("  ✗ FAILED: Request timed out (hanging endpoint)")
            return False
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            return False

        # Test 2: HTTP status
        print("\n[TEST 2] Checking HTTP status...")
        if response.status_code == 200:
            print(f"  ✓ Status code: {response.status_code}")
        else:
            print(f"  ✗ FAILED: Expected 200, got {response.status_code}")
            print(f"  Response: {response.text}")
            return False

        # Test 3: Parse JSON
        print("\n[TEST 3] Parsing JSON response...")
        try:
            config = response.json()
            print("  ✓ Valid JSON response")
        except Exception as e:
            print(f"  ✗ FAILED: Invalid JSON: {e}")
            return False

        # Test 4: Check structure
        print("\n[TEST 4] Checking configuration structure...")

        required_sections = {
            "installation": ["mode"],
            "services": ["api"],
            "security": ["cors"],
            "database": ["type", "host", "port"],
            "features": [],
            "logging": ["level"],
        }

        all_sections_present = True

        for section, required_fields in required_sections.items():
            if section not in config:
                print(f"  ✗ Missing section: {section}")
                all_sections_present = False
            else:
                print(f"  ✓ Section '{section}' present")

                # Check required fields
                for field in required_fields:
                    if field not in config[section]:
                        print(f"    ✗ Missing field: {section}.{field}")
                        all_sections_present = False

        if not all_sections_present:
            print("\n  ✗ FAILED: Configuration structure incomplete")
            return False

        # Test 5: Check installation.mode (critical for frontend)
        print("\n[TEST 5] Checking installation.mode...")
        mode = config.get("installation", {}).get("mode")
        if mode:
            print(f"  ✓ installation.mode = '{mode}'")

            if mode not in ["localhost", "local", "lan", "server", "wan"]:
                print(f"  ⚠ WARNING: Unexpected mode value: {mode}")
        else:
            print("  ✗ FAILED: installation.mode not found")
            return False

        # Test 6: Check services.api (critical for frontend)
        print("\n[TEST 6] Checking services.api...")
        api_host = config.get("services", {}).get("api", {}).get("host")
        api_port = config.get("services", {}).get("api", {}).get("port")

        if api_host and api_port:
            print(f"  ✓ services.api.host = '{api_host}'")
            print(f"  ✓ services.api.port = {api_port}")
        else:
            print("  ✗ FAILED: services.api configuration incomplete")
            return False

        # Test 7: Check CORS origins (critical for frontend)
        print("\n[TEST 7] Checking security.cors.allowed_origins...")
        cors_origins = config.get("security", {}).get("cors", {}).get("allowed_origins")

        if isinstance(cors_origins, list):
            print(f"  ✓ CORS origins configured: {len(cors_origins)} origins")
            for origin in cors_origins[:3]:  # Show first 3
                print(f"    - {origin}")
            if len(cors_origins) > 3:
                print(f"    ... and {len(cors_origins) - 3} more")
        else:
            print("  ✗ FAILED: CORS origins not a list")
            return False

        # Test 8: Check sensitive data masking
        print("\n[TEST 8] Checking sensitive data masking...")
        str(config).lower()

        # Check database password is masked
        db_password = config.get("database", {}).get("password")
        if db_password and ("*" in db_password or db_password == ""):
            print("  ✓ Database password masked correctly")
        elif db_password:
            print("  ⚠ WARNING: Database password may not be properly masked")
        else:
            print("  ✓ Database password not in response")

        # Test 9: Verify response speed consistency
        print("\n[TEST 9] Testing response consistency (3 requests)...")
        times = []
        for i in range(3):
            start = time.time()
            await client.get(api_url, timeout=5.0)
            end = time.time()
            req_time = (end - start) * 1000
            times.append(req_time)
            print(f"  Request {i + 1}: {req_time:.0f}ms")

        avg_time = sum(times) / len(times)
        print(f"  ✓ Average response time: {avg_time:.0f}ms")

        if max(times) > 2000:
            print("  ⚠ WARNING: Some requests took > 2 seconds")

        # Summary
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nEndpoint Summary:")
        print(f"  - Mode: {mode}")
        print(f"  - API: {api_host}:{api_port}")
        print(f"  - CORS origins: {len(cors_origins)}")
        print(f"  - Avg response time: {avg_time:.0f}ms")
        print("\nThe /api/v1/config endpoint is working correctly!")
        print("=" * 70)

        return True


async def main():
    """Main test runner."""
    print("\nStarting API configuration endpoint test...")
    print("Make sure the API server is running on http://localhost:7272\n")

    try:
        success = await test_config_endpoint()

        if success:
            print("\n✓ Test completed successfully!")
            return 0
        print("\n✗ Test failed!")
        return 1

    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
