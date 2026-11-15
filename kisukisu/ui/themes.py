# -*- coding: utf-8 -*-
"""
Kisukisu — Unified Design System & Theme Engine
Implements the full Kisukisu brand:
  Primary: Violet #8055E8   Secondary: Lavender #B7A0FF
  Dark BG: #111116           Light BG: #FAFAFC
  Accent text: #24232B       Sub text: #85838F
Presets: midnight, oled, paper, warm_cream, lavender, terminal — plus a fully custom theme.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Theme:
    name: str
    display_name: str
    dark: bool
    # Core backgrounds
    bg: str
    card_bg: str
    sidebar_bg: str
    input_bg: str
    # Text
    text_main: str
    text_sub: str
    text_muted: str
    # Brand / Accent
    accent: str             # Violet #8055E8
    accent_hover: str       # Violet darker
    accent_light: str       # Lavender #B7A0FF
    # Borders & dividers
    border: str
    border_subtle: str
    # Interactive states
    pill_bg: str
    pill_hover: str
    hover_bg: str
    selected_bg: str
    # Semantic
    success: str
    warning: str
    error: str
    # Reader specific
    reader_bg: str
    reader_text: str
    highlight_line: str
    cue_color: str
    progress_color: str
    on_accent: str = "#FFFFFF"   # text colour that is readable on the accent colour


THEMES: Dict[str, Theme] = {
    "midnight": Theme(
        name="midnight",
        display_name="Midnight",
        dark=True,
        bg="#111116",
        card_bg="#1A1A22",
        sidebar_bg="#0E0E14",
        input_bg="#1E1E28",
        text_main="#F0EFF6",
        text_sub="#A09DB8",
        text_muted="#5C5A72",
        accent="#8055E8",
        accent_hover="#6B44CC",
        accent_light="#B7A0FF",
        border="#2E2D3D",
        border_subtle="#222230",
        pill_bg="#252535",
        pill_hover="#2F2F44",
        hover_bg="#1E1E2E",
        selected_bg="#28223D",
        success="#34D399",
        warning="#FBBF24",
        error="#F87171",
        reader_bg="#111116",
        reader_text="#F0EFF6",
        highlight_line="#1E192E",
        cue_color="#B7A0FF",
        progress_color="#8055E8",
    ),
    "oled": Theme(
        name="oled",
        display_name="OLED Black",
        dark=True,
        bg="#000000",
        card_bg="#0D0D0D",
        sidebar_bg="#000000",
        input_bg="#121212",
        text_main="#FFFFFF",
        text_sub="#888888",
        text_muted="#444444",
        accent="#8055E8",
        accent_hover="#6B44CC",
        accent_light="#B7A0FF",
        border="#222222",
        border_subtle="#181818",
        pill_bg="#1A1A1A",
        pill_hover="#252525",
        hover_bg="#111111",
        selected_bg="#22173D",
        success="#34D399",
        warning="#FBBF24",
        error="#F87171",
        reader_bg="#000000",
        reader_text="#FFFFFF",
        highlight_line="#170F2B",
        cue_color="#B7A0FF",
        progress_color="#8055E8",
    ),
    "paper": Theme(
        name="paper",
        display_name="Paper White",
        dark=False,
        bg="#FAFAFC",
        card_bg="#FFFFFF",
        sidebar_bg="#F4F3F8",
        input_bg="#F8F7FC",
        text_main="#24232B",
        text_sub="#6B6880",
        text_muted="#A09DB8",
        accent="#8055E8",
        accent_hover="#6B44CC",
        accent_light="#B7A0FF",
        border="#E8E6F0",
        border_subtle="#F0EFF6",
        pill_bg="#F0EFF6",
        pill_hover="#E8E6F2",
        hover_bg="#F5F4FA",
        selected_bg="#EFEAF8",
        success="#059669",
        warning="#D97706",
        error="#DC2626",
        reader_bg="#FAFAFC",
        reader_text="#24232B",
        highlight_line="#F5F1FB",
        cue_color="#8055E8",
        progress_color="#8055E8",
    ),
    "warm_cream": Theme(
        name="warm_cream",
        display_name="Warm Cream",
        dark=False,
        bg="#FAF7F0",
        card_bg="#FFFFFF",
        sidebar_bg="#F5F0E8",
        input_bg="#FAF7F2",
        text_main="#2D2420",
        text_sub="#7A6E68",
        text_muted="#B0A8A0",
        accent="#8055E8",
        accent_hover="#6B44CC",
        accent_light="#B7A0FF",
        border="#E8E0D0",
        border_subtle="#F0EBE0",
        pill_bg="#F0EAE0",
        pill_hover="#E8E0D0",
        hover_bg="#F5F0E8",
        selected_bg="#EFE8F4",
        success="#059669",
        warning="#D97706",
        error="#DC2626",
        reader_bg="#FAF7F0",
        reader_text="#2D2420",
        highlight_line="#F5EEFA",
        cue_color="#8055E8",
        progress_color="#8055E8",
    ),
    "lavender": Theme(
        name="lavender",
        display_name="Lavender",
        dark=False,
        bg="#F5F3FF",
        card_bg="#FFFFFF",
        sidebar_bg="#EDE9FF",
        input_bg="#F8F6FF",
        text_main="#2D2460",
        text_sub="#7066A0",
        text_muted="#A09DC0",
        accent="#8055E8",
        accent_hover="#6B44CC",
        accent_light="#B7A0FF",
        border="#D8D2F5",
        border_subtle="#EAE6FF",
        pill_bg="#EAE6FF",
        pill_hover="#DDD8F5",
        hover_bg="#EDE9FF",
        selected_bg="#EDE6FD",
        success="#059669",
        warning="#D97706",
        error="#DC2626",
        reader_bg="#F5F3FF",
        reader_text="#2D2460",
        highlight_line="#F4EFFF",
        cue_color="#8055E8",
        progress_color="#8055E8",
    ),
    "terminal": Theme(
        name="terminal",
        display_name="Terminal",
        dark=True,
        bg="#0C1200",
        card_bg="#111A00",
        sidebar_bg="#080E00",
        input_bg="#141E00",
        text_main="#44FF44",
        text_sub="#22AA22",
        text_muted="#116611",
        accent="#44FF44",
        on_accent="#000000",
        accent_hover="#33EE33",
        accent_light="#88FF88",
        border="#1A2800",
        border_subtle="#141E00",
        pill_bg="#1A2800",
        pill_hover="#223300",
        hover_bg="#141E00",
        selected_bg="#162900",
        success="#44FF44",
        warning="#FFFF00",
        error="#FF4444",
        reader_bg="#0C1200",
        reader_text="#44FF44",
        highlight_line="#102000",
        cue_color="#88FF88",
        progress_color="#44FF44",
    ),
}

import os
import re
import json
from pathlib import Path

from ..core.config import default_home

# ── colour maths ──────────────────────────────────────────────────
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex(c) -> bool:
    return isinstance(c, str) and bool(_HEX_RE.match(c.strip()))


def normalize_hex(c, default="#000000") -> str:
    """Accepts '#abc', 'abc', '#aabbcc' -> '#aabbcc' (upper-case)."""
    if not isinstance(c, str):
        return default
    c = c.strip().lstrip("#")
    if len(c) == 3 and re.fullmatch(r"[0-9a-fA-F]{3}", c):
        c = "".join(ch * 2 for ch in c)
    return "#" + c.upper() if re.fullmatch(r"[0-9a-fA-F]{6}", c) else default


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1: str, c2: str, t: float) -> str:
    """Blend c1 -> c2 by t (0..1)."""
    a, b = _rgb(c1), _rgb(c2)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def luminance(c: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in _rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable_on(bg: str) -> str:
    """Black or white, whichever reads better on *bg*."""
    return "#000000" if luminance(bg) > 0.45 else "#FFFFFF"


def derive_theme(name, display_name, dark, bg, text, accent, card=None) -> Theme:
    """Build a complete, consistent theme from just a few base colours."""
    bg, text, accent = normalize_hex(bg, "#161622"), normalize_hex(text, "#FFFFFF"), normalize_hex(accent, "#8055E8")
    white, black = "#FFFFFF", "#000000"
    if dark:
        card = normalize_hex(card, mix(bg, white, 0.05)) if card else mix(bg, white, 0.05)
        sidebar = mix(bg, black, 0.30)
        inp, border, border_s = mix(bg, white, 0.08), mix(bg, white, 0.15), mix(bg, white, 0.08)
        pill, pill_h, hover = mix(bg, white, 0.11), mix(bg, white, 0.18), mix(bg, white, 0.06)
        success, warning, error = "#34D399", "#FBBF24", "#F87171"
    else:
        card = normalize_hex(card, mix(bg, white, 0.65)) if card else mix(bg, white, 0.65)
        sidebar = mix(bg, black, 0.035)
        inp, border, border_s = mix(bg, white, 0.45), mix(bg, black, 0.12), mix(bg, black, 0.06)
        pill, pill_h, hover = mix(bg, black, 0.06), mix(bg, black, 0.11), mix(bg, black, 0.04)
        success, warning, error = "#059669", "#D97706", "#DC2626"
    return Theme(
        name=name, display_name=display_name, dark=dark,
        bg=bg, card_bg=card, sidebar_bg=sidebar, input_bg=inp,
        text_main=text, text_sub=mix(text, bg, 0.32), text_muted=mix(text, bg, 0.58),
        accent=accent, accent_hover=mix(accent, black, 0.20), accent_light=mix(accent, white if dark else black, 0.30),
        border=border, border_subtle=border_s,
        pill_bg=pill, pill_hover=pill_h, hover_bg=hover,
        selected_bg=mix(bg, accent, 0.24 if dark else 0.16),
        success=success, warning=warning, error=error,
        reader_bg=bg, reader_text=text,
        highlight_line=mix(bg, accent, 0.10), cue_color=mix(accent, white if dark else black, 0.30),
        progress_color=accent, on_accent=readable_on(accent),
    )


# ── custom theme persistence ──────────────────────────────────────
def _custom_theme_path() -> Path:
    return default_home() / "custom_theme.json"


def _theme_from_dict(d: dict) -> Theme:
    dark = bool(d.get("dark", True))
    return derive_theme(
        "custom", str(d.get("display_name", "Custom"))[:24] or "Custom", dark,
        d.get("bg", "#161622"), d.get("text", d.get("text_main", "#F5F5FA")),
        d.get("accent", "#8055E8"), d.get("card_bg"),
    )


def load_custom_theme() -> Optional[Theme]:
    path = _custom_theme_path()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            theme = _theme_from_dict(json.load(f))
        THEMES["custom"] = theme
        return theme
    except Exception:
        return None


def custom_theme_values() -> dict:
    """Current base colours of the custom theme (for the editor UI)."""
    t = THEMES.get("custom")
    if t:
        return {"display_name": t.display_name, "dark": t.dark, "bg": t.bg,
                "text": t.text_main, "accent": t.accent}
    m = THEMES["midnight"]
    return {"display_name": "My Theme", "dark": True, "bg": m.bg, "text": m.text_main, "accent": m.accent}


def save_custom_theme(accent="#8055E8", bg="#161622", card_bg=None, text_main="#FFFFFF",
                      name="My Theme", dark=True) -> Theme:
    data = {
        "display_name": name, "dark": bool(dark),
        "accent": normalize_hex(accent, "#8055E8"), "bg": normalize_hex(bg, "#161622"),
        "text": normalize_hex(text_main, "#FFFFFF"),
    }
    if card_bg:
        data["card_bg"] = normalize_hex(card_bg, "")
    theme = _theme_from_dict(data)
    THEMES["custom"] = theme
    try:
        path = _custom_theme_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        pass
    return theme


def export_theme(dest: str) -> bool:
    try:
        with open(dest, "w", encoding="utf-8") as f:
            json.dump({"kisukisu_theme": 1, **custom_theme_values()}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def import_theme(src: str) -> Optional[Theme]:
    """Load a shared theme file. Only colours are read — nothing is executed."""
    try:
        with open(src, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or not all(is_hex(normalize_hex(d.get(k), "")) or k == "dark"
                                              for k in ("bg", "accent") if k in d):
            return None
        return save_custom_theme(d.get("accent", "#8055E8"), d.get("bg", "#161622"), d.get("card_bg"),
                                 d.get("text", d.get("text_main", "#FFFFFF")),
                                 str(d.get("display_name", "Imported"))[:24], bool(d.get("dark", True)))
    except Exception:
        return None


load_custom_theme()


def get_theme(name: str) -> Theme:
    if name == "custom" and "custom" not in THEMES:
        load_custom_theme()
    return THEMES.get(name, THEMES["midnight"])


def get_ctk_appearance(theme: Theme) -> str:
    return "dark" if theme.dark else "light"
