"""
Script to fix all ProductService unit tests by correcting async mock setup.
"""

import re


# Read the test file
with open("tests/unit/test_product_service.py", encoding="utf-8") as f:
    content = f.read()

# Pattern to find incorrectly configured mocks
# This pattern matches the old incorrect mock setup
old_pattern = r"""        db_manager = Mock\(\)
        session = AsyncMock\(\)

        db_manager\.get_session_async = AsyncMock\(return_value=AsyncMock\(
            __aenter__=AsyncMock\(return_value=session\),
            __aexit__=AsyncMock\(\)
        \)\)"""

# New correct mock setup (using the fixture pattern)
new_pattern = """        db_manager, session = mock_db_manager"""

# Replace all occurrences
# But we need to handle tests that don't use the fixture yet
# Count how many we're going to replace
matches = re.findall(old_pattern, content, re.MULTILINE)
print(f"Found {len(matches)} tests to fix")

# For tests that still manually create mocks, convert them to use mock_db_manager parameter
# First, let's update all function signatures that don't have mock_db_manager
def_pattern = r"    async def (test_\w+)\(self\):"
def_replacement = r"    async def \1(self, mock_db_manager):"

content = re.sub(def_pattern, def_replacement, content)

# Now replace all the old mock setup patterns
content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)

# Some tests might just have session setup without the full db_manager setup
# Let's also fix those patterns
simple_pattern1 = r"""        db_manager = Mock\(\)
        session = AsyncMock\(\)

        db_manager\.get_session_async = AsyncMock\(return_value=AsyncMock\(
            __aenter__=AsyncMock\(return_value=session\),
            __aexit__=AsyncMock\(\)
        \)\)

        # Mock"""

simple_replacement1 = """        db_manager, session = mock_db_manager

        # Mock"""

content = re.sub(simple_pattern1, simple_replacement1, content, flags=re.MULTILINE)

# Another common pattern with different formatting
simple_pattern2 = r"""        db_manager = Mock\(\)
        session = AsyncMock\(\)

        db_manager\.get_session_async = AsyncMock\(return_value=AsyncMock\(
            __aenter__=AsyncMock\(return_value=session\),
            __aexit__=AsyncMock\(\)
        \(\)"""

# Write the fixed content
with open("tests/unit/test_product_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ Fixed all ProductService unit tests")
