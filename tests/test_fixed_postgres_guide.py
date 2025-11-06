#!/usr/bin/env python3
"""Test the fixed PostgreSQL guide layout"""

import sys
import tkinter as tk
from tkinter import ttk


# Enable DPI awareness
if sys.platform == "win32":
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(2)
    except:
        pass

# Colors
COLORS = {
    "bg_primary": "#0e1c2d",
    "bg_elevated": "#1e3147",
    "text_primary": "#ffc300",
    "text_success": "#67bd6d",
    "text_light": "#e1e1e1",
}


def show_postgres_guide():
    """Show a properly formatted PostgreSQL guide window"""

    # Create window
    root = tk.Tk()
    root.title("PostgreSQL Installation Guide")
    root.geometry("800x600")
    root.configure(bg=COLORS["bg_primary"])
    root.resizable(False, False)

    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 400
    y = (root.winfo_screenheight() // 2) - 300
    root.geometry(f"800x600+{x}+{y}")

    # Configure styles
    style = ttk.Style()
    style.configure("TFrame", background=COLORS["bg_primary"])
    style.configure("TLabel", background=COLORS["bg_primary"], foreground="#ffffff")
    style.configure("TLabelframe", background=COLORS["bg_primary"], foreground="#ffffff")
    style.configure("TButton", font=("Segoe UI", 9))

    # Main container with padding
    main_container = ttk.Frame(root)
    main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Title
    title = tk.Label(
        main_container,
        text="PostgreSQL Installation Guide",
        font=("Segoe UI", 14, "bold"),
        fg="#ffffff",
        bg=COLORS["bg_primary"],
    )
    title.pack(pady=(0, 15))

    # Instructions in simple labels (NO TEXT WIDGET)
    inst_frame = ttk.LabelFrame(main_container, text="Quick Steps", padding=15)
    inst_frame.pack(fill=tk.X, pady=10)

    steps = [
        ("Step 1:", "Download PostgreSQL 18 from postgresql.org"),
        ("Step 2:", "Run installer as Administrator (Windows)"),
        ("Step 3:", "USE YOUR SETTINGS:"),
        ("", "  • Port: 5432 (YOU SELECTED THIS!)"),
        ("", "  • User: postgres (YOU SELECTED THIS!)"),
        ("", "  • Password: Choose and REMEMBER it"),
        ("Step 4:", "Complete installation"),
        ("Step 5:", "Test connection below"),
    ]

    for label, text in steps:
        frame = ttk.Frame(inst_frame)
        frame.pack(fill=tk.X, pady=2)

        if label:
            lbl = tk.Label(
                frame, text=label, font=("Segoe UI", 10, "bold"), fg=COLORS["text_primary"], bg=COLORS["bg_primary"]
            )
            lbl.pack(side=tk.LEFT, padx=(0, 5))

        txt = tk.Label(frame, text=text, font=("Segoe UI", 10), fg="#ffffff", bg=COLORS["bg_primary"])
        txt.pack(side=tk.LEFT)

    # Download button
    btn_frame = ttk.Frame(main_container)
    btn_frame.pack(fill=tk.X, pady=10)

    download_btn = ttk.Button(btn_frame, text="📥 Download PostgreSQL 18")
    download_btn.pack()

    # Test connection frame
    test_frame = ttk.LabelFrame(main_container, text="Test Connection", padding=10)
    test_frame.pack(fill=tk.X, pady=10)

    # Password entry
    pass_frame = ttk.Frame(test_frame)
    pass_frame.pack(fill=tk.X, pady=5)

    ttk.Label(pass_frame, text="Password:").pack(side=tk.LEFT, padx=5)
    pass_entry = ttk.Entry(pass_frame, show="*", width=30)
    pass_entry.pack(side=tk.LEFT, padx=5)

    test_btn = ttk.Button(test_frame, text="Test Connection")
    test_btn.pack(pady=5)

    # Bottom buttons
    bottom_frame = ttk.Frame(main_container)
    bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

    skip_btn = ttk.Button(bottom_frame, text="Skip (Use Existing)")
    skip_btn.pack(side=tk.LEFT)

    continue_btn = ttk.Button(bottom_frame, text="Continue Installation →", state="disabled")
    continue_btn.pack(side=tk.RIGHT)

    print("Window should display with:")
    print("- Title")
    print("- Instructions (as labels, not text widget)")
    print("- Download button")
    print("- Test connection section")
    print("- Skip and Continue buttons at bottom")

    root.mainloop()


if __name__ == "__main__":
    show_postgres_guide()
