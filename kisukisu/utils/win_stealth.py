# -*- coding: utf-8 -*-
"""
Kisukisu — Native Windows window helpers.

* Capture exclusion (WDA_EXCLUDEFROMCAPTURE): the window is skipped by screen
  sharing / recording on Windows 10 (2004+) and 11.
* Taskbar visibility (WS_EX_TOOLWINDOW) — opt-in, never the default.
* Topmost z-order, dark title bar, taskbar icon.

Everything here is a safe no-op on macOS / Linux.

IMPORTANT: Tk's winfo_id() is the *client* child window. The OS-level frame
window (the one Windows APIs expect) is its root ancestor — see top_level_hwnd().
"""

import sys
import os
import ctypes

WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
GA_ROOT = 2

_configured = False


def is_windows() -> bool:
    return sys.platform.startswith("win")


def _user32():
    """user32 with correct 64-bit argtypes (HWND is a pointer-sized handle)."""
    global _configured
    from ctypes import wintypes
    u = ctypes.windll.user32
    if not _configured:
        u.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        u.GetAncestor.restype = wintypes.HWND
        u.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        u.SetWindowDisplayAffinity.restype = wintypes.BOOL
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetWindowLongW.restype = ctypes.c_long
        u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        u.SetWindowLongW.restype = ctypes.c_long
        u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, wintypes.UINT]
        u.SetWindowPos.restype = wintypes.BOOL
        _configured = True
    return u


def top_level_hwnd(tk_window_id: int):
    """Real top-level HWND for a Tk window (pass widget.winfo_id())."""
    if not is_windows() or not tk_window_id:
        return None
    try:
        root = _user32().GetAncestor(tk_window_id, GA_ROOT)
        return root or tk_window_id
    except Exception:
        return tk_window_id


def set_capture_excluded(hwnd, exclude=True) -> bool:
    """Hide the window from screen capture / sharing (Windows 10 2004+)."""
    if not is_windows() or not hwnd:
        return False
    try:
        return bool(_user32().SetWindowDisplayAffinity(
            hwnd, WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE))
    except Exception:
        return False


def set_taskbar_hidden(hwnd, hidden=True) -> bool:
    """
    Remove / restore the taskbar button and Alt-Tab entry.
    The caller must withdraw() and deiconify() the window around this call
    for Windows to apply the change.
    """
    if not is_windows() or not hwnd:
        return False
    try:
        u = _user32()
        ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if hidden:
            ex = (ex & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
        else:
            ex = (ex & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        u.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        u.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010)
        return True
    except Exception:
        return False


def set_topmost(hwnd, on_top=True) -> bool:
    if not is_windows() or not hwnd:
        return False
    try:
        target = HWND_TOPMOST if on_top else HWND_NOTOPMOST
        return bool(_user32().SetWindowPos(
            hwnd, target, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER))
    except Exception:
        return False


def set_dark_titlebar(hwnd, dark=True) -> bool:
    """Match the native title bar to the theme (Windows 10 1809+/11)."""
    if not is_windows() or not hwnd:
        return False
    try:
        value = ctypes.c_int(1 if dark else 0)
        dwm = ctypes.windll.dwmapi
        for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (new / old id)
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                return True
    except Exception:
        pass
    return False


def set_win_taskbar_icon(hwnd, ico_path) -> bool:
    if not is_windows() or not hwnd or not ico_path or not os.path.exists(ico_path):
        return False
    try:
        u = ctypes.windll.user32
        IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x0080
        big = u.LoadImageW(None, os.path.abspath(ico_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        small = u.LoadImageW(None, os.path.abspath(ico_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        if big:
            u.SendMessageW(hwnd, WM_SETICON, 1, big)
        if small:
            u.SendMessageW(hwnd, WM_SETICON, 0, small)
        return True
    except Exception:
        return False


# ── backwards-compatible names ────────────────────────────────────
def apply_display_affinity(hwnd, exclude=True):
    return set_capture_excluded(hwnd, exclude)


def apply_toolwindow(hwnd, hide_from_taskbar=True):
    return set_taskbar_hidden(hwnd, hide_from_taskbar)


def force_always_on_top(hwnd, on_top=True):
    return set_topmost(hwnd, on_top)
