# -*- coding: utf-8 -*-
"""
Kisukisu — Desktop Application Launcher
Ensures correct package resolution, Windows taskbar icon binding, and UTF-8 console output.
"""
import sys
import os

# Set Windows AppUserModelID so the taskbar icon displays properly
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("kisukisu.presenter.app.1.0")
    except Exception:
        pass

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if sys.stdout:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure PyInstaller / local base directory is in sys.path
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from kisukisu.app import main

if __name__ == "__main__":
    main()
