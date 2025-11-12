"""
Load Testing Framework for GiljoAI MCP

Comprehensive Locust-based load testing suite for validating system capacity,
identifying bottlenecks, and establishing performance baselines.

Main Components:
- locustfile.py: Main load test configuration
- run_load_tests.py: Test orchestrator and report generator
- scenarios/: Specialized test scenarios (WebSocket, user workflows)

Usage:
    # Run all scenarios
    python tests/load/run_load_tests.py --all

    # Run specific scenario
    python tests/load/run_load_tests.py --scenario normal_load

    # Interactive mode
    locust -f tests/load/locustfile.py --host=http://localhost:7272

See README.md for detailed documentation.
"""
