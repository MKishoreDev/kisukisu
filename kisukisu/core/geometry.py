# -*- coding: utf-8 -*-
"""
Kisukisu — Pure window-geometry helpers (no Tk required, fully unit-tested).

These keep the reader window sane: never off-screen, never bigger than the
display, never stuck at a size remembered from a monitor that is gone.
"""

import re
from typing import List, Dict, Optional, Tuple

_GEO_RE = re.compile(r"^\s*(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)\s*$")


def _signed(token: str) -> int:
    """Tk reports negative coordinates as '+-30'; accept '+60', '-30' and '+-30'."""
    return int(token.replace("+-", "-").replace("--", "-"))


def parse_geometry(geo: str) -> Optional[Tuple[int, int, int, int]]:
    """'580x460+60+-30' -> (580, 460, 60, -30). Returns None if malformed."""
    m = _GEO_RE.match(geo or "")
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    x, y = _signed(m.group(3)), _signed(m.group(4))
    return w, h, x, y


def format_geometry(w: int, h: int, x: int, y: int) -> str:
    return f"{int(w)}x{int(h)}{int(x):+d}{int(y):+d}"


def _area(m: Dict) -> Tuple[int, int, int, int]:
    """Usable area of a monitor (work area when known)."""
    return (m.get("wx", m["x"]), m.get("wy", m["y"]),
            m.get("ww", m["width"]), m.get("wh", m["height"]))


def pick_monitor(monitors: List[Dict], index: int = 0) -> Dict:
    if not monitors:
        return {"id": 0, "x": 0, "y": 0, "width": 1920, "height": 1080, "is_primary": True}
    if 0 <= index < len(monitors):
        return monitors[index]
    for m in monitors:
        if m.get("is_primary"):
            return m
    return monitors[0]


def _monitor_containing(monitors: List[Dict], cx: int, cy: int) -> Optional[Dict]:
    for m in monitors:
        ax, ay, aw, ah = _area(m)
        if ax <= cx < ax + aw and ay <= cy < ay + ah:
            return m
    return None


def clamp_rect(w, h, x, y, monitors: List[Dict], target_index: int = 0,
               min_w: int = 320, min_h: int = 160, anchor: str = "center",
               scale: float = 1.0) -> Tuple[int, int, int, int]:
    """
    Return a (w, h, x, y) that is guaranteed to be fully visible.

    * x/y of None (never placed) or off every monitor -> placed on the target
      monitor (`anchor`: "center", "top" = top-centre under the webcam,
      "right" = right side, handy for notes next to slides).
    * A rect already on a monitor is only nudged to fit inside it.
    * `scale` is the UI scale factor (e.g. 1.5 on a 150% display): w/h/min_w/min_h are
      logical units, x/y and monitor rectangles are physical pixels (as Windows reports).
    """
    scale = scale if scale and scale > 0 else 1.0
    try:
        w = int(w)
        h = int(h)
    except (TypeError, ValueError):
        w, h = min_w, min_h
    w, h = w * scale, h * scale                  # -> physical pixels for the maths below
    min_w, min_h = min_w * scale, min_h * scale

    target = pick_monitor(monitors, target_index)

    if x is not None and y is not None:
        mon = _monitor_containing(monitors, int(x + w // 2), int(y) + 20)
    else:
        mon = None

    placed = mon is not None
    mon = mon or target
    ax, ay, aw, ah = _area(mon)

    w = max(min_w, min(w, aw))
    h = max(min_h, min(h, ah))

    if not placed:
        if anchor == "top":
            x = ax + int((aw - w) // 2)
            y = ay + 24
        elif anchor == "right":
            x = ax + int(aw - w) - 40
            y = ay + 60
        else:
            x = ax + int((aw - w) // 2)
            y = ay + int((ah - h) // 2)
    x = max(ax, min(int(x), int(ax + aw - w)))
    y = max(ay, min(int(y), int(ay + ah - h)))
    return int(w / scale), int(h / scale), int(x), int(y)
