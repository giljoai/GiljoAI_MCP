import sys


sys.stdout.reconfigure(encoding="utf-8")

# Read original file
with open("docs/SERVER_ARCHITECTURE_TECH_STACK.md", encoding="utf-8") as f:
    lines = f.readlines()

# Save original line count
original_lines = len(lines)

# First insertion: Handovers 0042 and 0048 after line 396 (after "Cache invalidation" line)
# Find the line with "Cache invalidation"
insert_pos_1 = None
for i, line in enumerate(lines):
    if "Cache invalidation: <1ms all layers" in line:
        insert_pos_1 = i + 1
        break

if insert_pos_1 is None:
    print("ERROR: Could not find insertion point 1")
    sys.exit(1)

# Content for handovers 0042 and 0048
content_1 = open("handover_0042_0048.txt", encoding="utf-8").read()

# Insert at position
lines.insert(insert_pos_1, content_1 + "\n")

# Second insertion: Handover 0045 after HANDOVER 0020 archive status
# Find the line with archive status for 0020
insert_pos_2 = None
for i, line in enumerate(lines):
    if "Archive Status**: Moved to `handovers/completed/0020_HANDOVER" in line:
        insert_pos_2 = i + 1
        break

if insert_pos_2 is None:
    print("ERROR: Could not find insertion point 2")
    sys.exit(1)

# Content for handover 0045
content_2 = open("handover_0045.txt", encoding="utf-8").read()

# Insert at position
lines.insert(insert_pos_2, content_2 + "\n")

# Write updated file
with open("docs/SERVER_ARCHITECTURE_TECH_STACK.md", "w", encoding="utf-8") as f:
    f.writelines(lines)

new_lines = len(lines)
print(f"Original lines: {original_lines}")
print(f"New lines: {new_lines}")
print(f"Lines added: {new_lines - original_lines}")
print("SUCCESS: Architecture document updated")
