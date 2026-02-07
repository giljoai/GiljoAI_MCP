"""Fix remaining ProductService tests that still use manual mock setup"""

import re


with open("tests/unit/test_product_service.py", encoding="utf-8") as f:
    lines = f.readlines()

# Track which lines to modify
in_test = False
test_start_line = -1
needs_fixture = False

modified_lines = []
i = 0

while i < len(lines):
    line = lines[i]

    # Check if we're at a test function definition without mock_db_manager
    if re.match(r"\s+async def test_\w+\(self\):", line):
        # This test needs the fixture added
        modified_line = line.replace("(self):", "(self, mock_db_manager):")
        modified_lines.append(modified_line)
        in_test = True
        test_start_line = i
        needs_fixture = True
        i += 1
        continue

    # If we're in a test that needs fixture, look for manual mock setup
    if in_test and needs_fixture:
        # Check for the manual mock setup pattern
        if "        db_manager = Mock()" in line:
            # Skip this line and next few lines that setup the mock
            j = i
            # Skip until we find the end of the mock setup
            while j < len(lines):
                current = lines[j]
                if (
                    "        db_manager" in current
                    or "        session" in current
                    or "get_session_async" in current
                    or "__aenter__" in current
                    or "__aexit__" in current
                ):
                    j += 1
                else:
                    break

            # Add the fixture usage instead
            modified_lines.append("        db_manager, session = mock_db_manager\n")
            modified_lines.append("\n")

            # Skip to after the mock setup
            i = j
            continue

        # Check if we've moved to the next test or class
        if (
            re.match(r"\s+async def test_", line) or re.match(r"class ", line) or i > test_start_line + 50
        ):  # Safety check
            in_test = False
            needs_fixture = False

    modified_lines.append(line)
    i += 1

# Write back
with open("tests/unit/test_product_service.py", "w", encoding="utf-8") as f:
    f.writelines(modified_lines)

print("Fixed remaining ProductService tests")
