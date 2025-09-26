#!/usr/bin/env python3
"""Test script for the enhanced GUI wizard with profile selection"""

import sys
import tkinter as tk
from tkinter import messagebox

def test_gui():
    """Test the GUI wizard flow"""
    try:
        # Import the GUI module
        from setup_gui import gui
        
        print("Starting GUI wizard test...")
        print("✓ GUI module imported successfully")
        
        # The gui() function will start the GUI
        print("\nLaunching GUI wizard...")
        print("- Profile Selection page should appear after Welcome page")
        print("- Database settings should adapt to selected profile")
        print("- Review page should show selected profile")
        
        # Run the GUI
        gui()
        
    except ImportError as e:
        print(f"Error importing GUI module: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("GUI WIZARD TEST - Profile Selection Enhancement")
    print("=" * 60)
    print("\nThis will test the enhanced GUI wizard with:")
    print("1. New ProfileSelectionPage after Welcome")
    print("2. Profile-aware DatabasePage configuration")
    print("3. Profile display in ReviewPage")
    print("-" * 60)
    
    test_gui()