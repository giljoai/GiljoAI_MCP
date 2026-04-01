"""
0873g - Text Color Token Enforcement
Replaces hardcoded hex color values with CSS custom property references.

Rules:
  - var(--text-muted, #8895a8) -> var(--text-muted)  [strip fallback, everywhere]
  - var(--text-secondary, #a3aac4) -> var(--text-secondary)  [strip fallback, everywhere]
  - var(--color-text-primary, #e1e1e1) -> var(--color-text-primary)  [strip fallback, everywhere]
  - bare #8895a8 in <style> blocks -> var(--text-muted)
  - bare #a3aac4 in <style> blocks -> var(--text-secondary)
  - bare #e1e1e1 in <style> blocks -> var(--color-text-primary)
  - bare #8895a8 in style="..." template attrs -> var(--text-muted)
  - bare #a3aac4 in style="..." template attrs -> var(--text-secondary)

Does NOT touch:
  - JS/script hex values used with hexToRgb/hexToRgba (color palette maps)
  - Comments
"""
import re
import sys
import os

TARGET_FILES = [
    # Style block changes (bare hex)
    "frontend/src/components/dashboard/ProductSelector.vue",
    "frontend/src/components/messages/BroadcastPanel.vue",
    "frontend/src/components/projects/AgentJobModal.vue",
    "frontend/src/components/projects/ProjectTabs.vue",
    "frontend/src/components/settings/tabs/IdentityTab.vue",
    "frontend/src/components/settings/tabs/NetworkSettingsTab.vue",
    "frontend/src/components/settings/tabs/SecuritySettingsTab.vue",
    "frontend/src/components/settings/tabs/SystemPromptTab.vue",
    "frontend/src/views/Login.vue",
    "frontend/src/views/MessagesView.vue",
    "frontend/src/views/SystemSettings.vue",
    "frontend/src/views/UserSettings.vue",
    "frontend/src/views/ProductsView.vue",
    # Style block fallback stripping
    "frontend/src/components/dashboard/RecentMemoriesList.vue",
    "frontend/src/components/dashboard/RecentProjectsList.vue",
    "frontend/src/views/DashboardView.vue",
    "frontend/src/views/WelcomeView.vue",
    # Template inline style changes
    "frontend/src/components/products/ProductDetailsDialog.vue",
    "frontend/src/components/products/ProductTuningReview.vue",
    "frontend/src/views/ProductDetailView.vue",
]

HEX_TO_VAR = {
    "#8895a8": "var(--text-muted)",
    "#a3aac4": "var(--text-secondary)",
    "#e1e1e1": "var(--color-text-primary)",
}

FALLBACK_PATTERNS = [
    (r"var\(--text-muted,\s*#8895a8\)", "var(--text-muted)"),
    (r"var\(--text-secondary,\s*#a3aac4\)", "var(--text-secondary)"),
    (r"var\(--color-text-primary,\s*#e1e1e1\)", "var(--color-text-primary)"),
    (r"var\(--color-text-secondary,\s*#a3aac4\)", "var(--color-text-secondary)"),
]


def replace_hex_in_text(text, hex_map):
    """Replace hex color values in a string, avoiding mid-word matches."""
    for hex_val, css_var in hex_map.items():
        # Negative lookbehind/ahead to avoid partial matches
        pattern = r"(?<![a-fA-F0-9])" + re.escape(hex_val) + r"(?![a-fA-F0-9])"
        text = re.sub(pattern, css_var, text)
    return text


def strip_fallbacks(content):
    """Strip known fallback values from CSS var() calls, applied globally."""
    for pattern, replacement in FALLBACK_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content


def replace_in_style_blocks(content):
    """Replace bare hex values within <style>...</style> blocks."""
    def process_style_block(m):
        tag = m.group(1)
        inner = m.group(2)
        close = m.group(3)
        inner = replace_hex_in_text(inner, HEX_TO_VAR)
        return tag + inner + close

    return re.sub(
        r"(<style[^>]*>)(.*?)(</style>)",
        process_style_block,
        content,
        flags=re.DOTALL,
    )


def replace_in_style_attrs(content):
    """Replace bare hex values within style=\"...\" template attributes."""
    def process_attr(m):
        attr_value = m.group(1)
        for hex_val, css_var in HEX_TO_VAR.items():
            attr_value = attr_value.replace(hex_val, css_var)
        return f'style="{attr_value}"'

    return re.sub(r'style="([^"]*)"', process_attr, content)


def process_file(filepath):
    if not os.path.exists(filepath):
        print(f"SKIP (not found): {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8-sig") as f:
        original = f.read()

    content = original

    # Step 1: Strip fallbacks globally (safe everywhere)
    content = strip_fallbacks(content)

    # Step 2: Replace bare hex in <style> blocks
    content = replace_in_style_blocks(content)

    # Step 3: Replace bare hex in template style="..." attributes
    content = replace_in_style_attrs(content)

    if content == original:
        print(f"  NO CHANGE: {filepath}")
        return False

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print(f"  MODIFIED: {filepath}")
    return True


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    modified = 0
    for rel_path in TARGET_FILES:
        full_path = os.path.join(base, rel_path.replace("/", os.sep))
        if process_file(full_path):
            modified += 1

    print(f"\nDone. {modified}/{len(TARGET_FILES)} files modified.")


if __name__ == "__main__":
    main()
