"""
0873e: Replace hardcoded transition durations with design token variables.
"""

import re
import os

FILES = [
    "C:/Projects/GiljoAI_MCP/frontend/src/App.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ActiveProductDisplay.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/AgentExport.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/AiToolConfigWizard.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ConnectionStatus.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ToastManager.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/common/AgentTipsDialog.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/dashboard/ProductSelector.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/dashboard/RecentMemoriesList.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/dashboard/RecentProjectsList.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/messages/BroadcastPanel.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/messages/MessageItem.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/navigation/NavigationDrawer.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/navigation/NotificationDropdown.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/orchestration/AgentTableView.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/products/ProductDetailsDialog.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/projects/AgentJobModal.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/projects/JobsTab.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/projects/LaunchTab.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/projects/MessageAuditModal.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/projects/ProjectTabs.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/settings/ContextPriorityConfig.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/DashboardView.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/MessagesView.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/ProductsView.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/ProjectsView.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/SystemSettings.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/TasksView.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/UserSettings.vue",
    "C:/Projects/GiljoAI_MCP/frontend/src/views/WelcomeView.vue",
]

# Files needing <style> tag conversion and @use import
# value: (old_tag, new_tag)
NEEDS_IMPORT = {
    "C:/Projects/GiljoAI_MCP/frontend/src/App.vue":
        ('<style>', '<style lang="scss">'),
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ActiveProductDisplay.vue":
        ('<style scoped>', '<style lang="scss" scoped>'),
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ConnectionStatus.vue":
        ('<style scoped>', '<style lang="scss" scoped>'),
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ToastManager.vue":
        ('<style scoped>', '<style lang="scss" scoped>'),
}

# The @use path varies by depth — check file depth
USE_PATHS = {
    "C:/Projects/GiljoAI_MCP/frontend/src/App.vue": "@use '@/styles/design-tokens' as *;",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ActiveProductDisplay.vue": "@use '@/styles/design-tokens' as *;",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ConnectionStatus.vue": "@use '@/styles/design-tokens' as *;",
    "C:/Projects/GiljoAI_MCP/frontend/src/components/ToastManager.vue": "@use '@/styles/design-tokens' as *;",
}

# Ordered replacement pairs (old_string, new_string)
# More specific / longer patterns first to avoid partial matching
REPLACEMENTS = [
    # Multi-property patterns (most specific)
    ("transition: background 0.15s, opacity 0.15s;",
     "transition: background $transition-fast, opacity $transition-fast;"),
    ("transition: background 0.2s, color 0.2s, box-shadow 0.2s;",
     "transition: background $transition-normal, color $transition-normal, box-shadow $transition-normal;"),
    ("transition: transform 0.2s, box-shadow 0.2s;",
     "transition: transform $transition-normal, box-shadow $transition-normal;"),
    # Single-property: background
    ("transition: background 0.15s;",
     "transition: background $transition-fast;"),
    # Single-property: background-color
    ("transition: background-color 0.2s ease;",
     "transition: background-color $transition-normal ease;"),
    # Single-property: opacity
    ("transition: opacity 0.15s ease;",
     "transition: opacity $transition-fast ease;"),
    ("transition: opacity 0.15s;",
     "transition: opacity $transition-fast;"),
    ("transition: opacity 0.2s ease;",
     "transition: opacity $transition-normal ease;"),
    ("transition: opacity 0.2s;",
     "transition: opacity $transition-normal;"),
    ("transition: opacity 0.25s;",
     "transition: opacity $transition-normal;"),
    ("transition: opacity 0.3s;",
     "transition: opacity $transition-slow;"),
    # Single-property: transform
    ("transition: transform 0.25s;",
     "transition: $transition-transform;"),
    # Single-property: box-shadow
    ("transition: box-shadow 0.25s;",
     "transition: box-shadow $transition-normal;"),
    # Generic all — 0.15s
    ("transition: all 0.15s ease;",
     "transition: $transition-all-fast;"),
    ("transition: all 0.15s;",
     "transition: $transition-all-fast;"),
    # Generic all — 0.2s (normalize to normal)
    ("transition: all 0.2s ease;",
     "transition: all $transition-normal ease;"),
    ("transition: all 0.2s;",
     "transition: all $transition-normal;"),
    # Generic all — 0.25s (normalize to normal)
    ("transition: all 0.25s;",
     "transition: all $transition-normal;"),
    # Generic all — 0.3s
    ("transition: all 0.3s ease;",
     "transition: all $transition-slow ease;"),
    ("transition: all 0.3s;",
     "transition: all $transition-slow;"),
]


def is_in_keyframes(content, idx):
    """Return True if position idx is inside a @keyframes block."""
    preceding = content[:idx]
    kf_positions = [m.start() for m in re.finditer(r'@keyframes\s+\w+\s*\{', preceding)]
    if not kf_positions:
        return False
    last_kf = kf_positions[-1]
    section = preceding[last_kf:]
    open_b = section.count('{')
    close_b = section.count('}')
    return open_b > close_b


def is_in_deep(content, idx):
    """Return True if position idx is inside a :deep() selector."""
    # Look back to find if there's an unclosed :deep( before this line
    line_start = content.rfind('\n', 0, idx)
    # Check the current line for :deep( prefix
    line = content[line_start:idx]
    return ':deep(' in line


def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    changed = False

    # Step 1: Add @use import if needed
    if filepath in NEEDS_IMPORT:
        old_tag, new_tag = NEEDS_IMPORT[filepath]
        use_line = USE_PATHS[filepath]
        if old_tag in content:
            content = content.replace(
                old_tag,
                new_tag + '\n' + use_line,
                1
            )
            changed = True
            print(f"  [IMPORT] Added @use import: {os.path.basename(filepath)}")

    # Step 2: Apply transition replacements in style section only
    style_match = re.search(r'<style[^>]*>', content)
    if not style_match:
        print(f"  [SKIP] No <style> tag found: {filepath}")
        return

    style_start = style_match.start()

    for old, new in REPLACEMENTS:
        pos = style_start
        while True:
            idx = content.find(old, pos)
            if idx == -1:
                break
            if is_in_keyframes(content, idx):
                print(f"  [KEYFRAMES-SKIP] {old.strip()} in {os.path.basename(filepath)}")
                pos = idx + 1
                continue
            if is_in_deep(content, idx):
                print(f"  [DEEP-SKIP] {old.strip()} in {os.path.basename(filepath)}")
                pos = idx + 1
                continue
            content = content[:idx] + new + content[idx + len(old):]
            changed = True
            print(f"  [REPLACE] {old.strip()} -> {new.strip()} in {os.path.basename(filepath)}")
            pos = idx + len(new)

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [SAVED] {os.path.basename(filepath)}")
    else:
        print(f"  [NO-CHANGES] {os.path.basename(filepath)}")


if __name__ == '__main__':
    for f in FILES:
        print(f"\nProcessing: {os.path.basename(f)}")
        process_file(f)
    print("\n=== Done ===")
