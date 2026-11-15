# -*- coding: utf-8 -*-
"""
Kisukisu — Reader keyboard shortcuts (fully rebindable).

Keys are stored as Tk key names, optionally prefixed with "Control-" or "Alt-"
(e.g. "space", "Right", "F11", "Control-w").
"""

DEFAULT_SHORTCUTS = {
    "play_pause":        "space",
    "next_section":      "Right",
    "prev_section":      "Left",
    "scroll_down":       "Down",
    "scroll_up":         "Up",
    "page_down":         "Next",
    "page_up":           "Prior",
    "restart":           "Home",
    "jump_end":          "End",
    "speed_up":          "bracketright",
    "speed_down":        "bracketleft",
    "font_up":           "equal",
    "font_down":         "minus",
    "toggle_focus":      "f",
    "toggle_pin":        "t",
    "toggle_compact":    "m",
    "toggle_fullscreen": "F11",
    "sections_menu":     "s",
    "reset_timer":       "r",
    "close_reader":      "Control-w",
}

LABELS = {
    "play_pause":        "Play / pause auto-scroll",
    "next_section":      "Next section",
    "prev_section":      "Previous section",
    "scroll_down":       "Scroll down",
    "scroll_up":         "Scroll up",
    "page_down":         "Page down",
    "page_up":           "Page up",
    "restart":           "Back to the start",
    "jump_end":          "Jump to the end",
    "speed_up":          "Faster",
    "speed_down":        "Slower",
    "font_up":           "Bigger text",
    "font_down":         "Smaller text",
    "toggle_focus":      "Focus mode on/off",
    "toggle_pin":        "Always on top on/off",
    "toggle_compact":    "Compact mode on/off",
    "toggle_fullscreen": "Fullscreen on/off",
    "sections_menu":     "Section list",
    "reset_timer":       "Reset timer",
    "close_reader":      "Close reader",
}

# Extra keys that always trigger the same action (numpad / shifted variants).
ALIASES = {
    "font_up":   ("plus", "KP_Add"),
    "font_down": ("KP_Subtract",),
}

_MODIFIER_KEYSYMS = {
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
    "Meta_L", "Meta_R", "Super_L", "Super_R", "Caps_Lock", "Num_Lock",
    "ISO_Level3_Shift", "Win_L", "Win_R",
}

_PRETTY = {
    "space": "Space", "Right": "→", "Left": "←", "Up": "↑", "Down": "↓",
    "Next": "Page Down", "Prior": "Page Up", "equal": "=", "minus": "−",
    "plus": "+", "bracketleft": "[", "bracketright": "]", "Escape": "Esc",
    "Return": "Enter", "BackSpace": "Backspace",
}


def pretty(key: str) -> str:
    """Human-friendly label, e.g. 'Control-w' -> 'Ctrl + W'."""
    parts = key.split("-") if key and not key.endswith("-") else [key]
    out = []
    for p in parts:
        if p == "Control":
            out.append("Ctrl")
        elif p in _PRETTY:
            out.append(_PRETTY[p])
        elif len(p) == 1:
            out.append(p.upper())
        else:
            out.append(p)
    return " + ".join(out)


def key_from_event(event):
    """Convert a Tk key event into our stored key string (None for bare modifiers)."""
    sym = getattr(event, "keysym", "") or ""
    if not sym or sym in _MODIFIER_KEYSYMS:
        return None
    state = getattr(event, "state", 0) or 0
    prefix = ""
    if state & 0x4:
        prefix += "Control-"
    if state & 0x20000 or state & 0x8:
        prefix += "Alt-"
    return prefix + sym


def tk_sequences(key: str):
    """Tk bind sequences for a stored key (adds upper-case twin for letters)."""
    seqs = [f"<{key}>"]
    base = key.split("-")[-1]
    if len(base) == 1 and base.isalpha():
        seqs.append(f"<{key[:-1]}{base.upper()}>")
    return seqs


def find_conflict(shortcuts: dict, action: str, key: str):
    """Return another action already using *key*, or None."""
    for other, k in shortcuts.items():
        if other != action and k.lower() == key.lower():
            return other
    return None
