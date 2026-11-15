# -*- coding: utf-8 -*-
"""
Kisukisu — Multi-monitor detection.

Windows: Win32 EnumDisplayMonitors (with work areas, so the taskbar is respected).
Linux:   parses `xrandr --query` when available.
Other:   falls back to the primary screen size reported by Tk.
"""

import re
import sys
import subprocess
from typing import List, Dict, Any, Optional


def _windows_monitors() -> List[Dict[str, Any]]:
    import ctypes
    from ctypes import wintypes

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    monitors: List[Dict[str, Any]] = []
    user32 = ctypes.windll.user32
    proc_t = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def _cb(hmon, hdc, rect, data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        r = rect.contents
        entry = {
            "id": len(monitors), "x": r.left, "y": r.top,
            "width": r.right - r.left, "height": r.bottom - r.top,
            "is_primary": (r.left == 0 and r.top == 0),
        }
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            w = info.rcWork
            entry.update(wx=w.left, wy=w.top, ww=w.right - w.left, wh=w.bottom - w.top,
                         is_primary=bool(info.dwFlags & 1))
        monitors.append(entry)
        return 1

    user32.EnumDisplayMonitors(None, None, proc_t(_cb), 0)
    return monitors


_XRANDR_RE = re.compile(r"^(\S+) connected (primary )?(\d+)x(\d+)\+(\d+)\+(\d+)", re.MULTILINE)


def parse_xrandr(output: str) -> List[Dict[str, Any]]:
    mons = []
    for m in _XRANDR_RE.finditer(output):
        mons.append({
            "id": len(mons), "name": m.group(1), "is_primary": bool(m.group(2)),
            "width": int(m.group(3)), "height": int(m.group(4)),
            "x": int(m.group(5)), "y": int(m.group(6)),
        })
    return mons


def _linux_monitors() -> List[Dict[str, Any]]:
    out = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, timeout=2).stdout
    return parse_xrandr(out)


class MonitorManager:
    @staticmethod
    def get_monitors(root=None) -> List[Dict[str, Any]]:
        monitors: List[Dict[str, Any]] = []
        try:
            if sys.platform.startswith("win"):
                monitors = _windows_monitors()
            elif sys.platform.startswith("linux"):
                monitors = _linux_monitors()
        except Exception:
            monitors = []

        if not monitors:
            w, h = 1920, 1080
            if root is not None:
                try:
                    w, h = int(root.winfo_screenwidth()), int(root.winfo_screenheight())
                except Exception:
                    pass
            monitors = [{"id": 0, "x": 0, "y": 0, "width": w, "height": h, "is_primary": True}]

        # Put the primary monitor first so "Display 1" is what users expect.
        monitors.sort(key=lambda m: (not m.get("is_primary"), m["x"], m["y"]))
        for i, m in enumerate(monitors):
            m["id"] = i
        return monitors

    @staticmethod
    def get_display_labels(root=None) -> List[str]:
        labels = []
        for m in MonitorManager.get_monitors(root):
            tag = " (Primary)" if m.get("is_primary") else ""
            labels.append(f"Display {m['id'] + 1}: {m['width']}×{m['height']}{tag}")
        return labels
