# -*- coding: utf-8 -*-
"""
Kisukisu — Local-first configuration.

Settings live in ~/.kisukisu/config.json (override with the KISUKISU_HOME
environment variable). Values are validated and clamped on load *and* on set,
writes are atomic, and a corrupt file is moved aside instead of crashing.
"""

import os
import json
import time
from pathlib import Path

from .shortcuts import DEFAULT_SHORTCUTS


def default_home() -> Path:
    env = os.environ.get("KISUKISU_HOME")
    return Path(env).expanduser() if env else Path.home() / ".kisukisu"


DEFAULT_SETTINGS = {
    # ── Appearance ────────────────────────────────────────────
    "theme": "midnight",
    "font_family": "",            # "" = best font available on this platform
    "font_size": 24,
    "font_weight": "normal",      # normal | bold
    "line_spacing": 8,            # extra px between wrapped lines
    "paragraph_gap": 18,          # px between paragraphs
    "text_align": "left",         # left | center
    "reader_padding": 36,         # max side margin in px
    "opacity": 0.96,
    # ── Reader behaviour ──────────────────────────────────────
    "auto_scroll_speed": 4,       # 1 (slow) … 10 (fast)
    "pause_between_sections": False,   # auto-scroll pauses when a new section starts (slide changes)
    "focus_mode": True,           # dim everything except the current paragraph
    "show_ruler": True,
    "ruler_position": 0.38,       # 0.15 … 0.80 of the reader height
    "show_cues": True,
    "show_onscreen_ref": True,
    "show_timer": True,
    "resume_position": True,
    "reading_wpm": 150,
    # ── Window ────────────────────────────────────────────────
    "always_on_top": True,
    "hide_from_taskbar": False,   # opt-in; hiding it made the window hard to reach
    "screen_share_invisibility": True,   # Windows 10 2004+/11 capture exclusion
    "remember_window": True,
    "start_compact": False,
    "minimize_library_on_present": False,
    "selected_monitor": 0,
    "reader_w": 640, "reader_h": 560, "reader_x": None, "reader_y": None,
    "compact_w": 760, "compact_h": 180, "compact_x": None, "compact_y": None,
    "main_w": 1120, "main_h": 720, "main_x": None, "main_y": None,
    "sidebar_collapsed": False,
    # ── General ───────────────────────────────────────────────
    "confirm_delete": True,
    "autosave": True,
    "onboarding_complete": False,
    "last_script_id": "",
    "shortcuts": dict(DEFAULT_SHORTCUTS),
}

# key -> (type, min, max)   (None = unbounded)
_NUMERIC = {
    "font_size": (int, 10, 96),
    "line_spacing": (int, 0, 40),
    "paragraph_gap": (int, 0, 80),
    "reader_padding": (int, 8, 160),
    "opacity": (float, 0.40, 1.0),
    "auto_scroll_speed": (int, 1, 10),
    "ruler_position": (float, 0.15, 0.80),
    "reading_wpm": (int, 60, 300),
    "selected_monitor": (int, 0, 16),
    "reader_w": (int, 320, 6000), "reader_h": (int, 160, 6000),
    "compact_w": (int, 320, 6000), "compact_h": (int, 110, 1200),
    "main_w": (int, 760, 6000), "main_h": (int, 520, 4000),
}
_NULLABLE_INT = ("reader_x", "reader_y", "compact_x", "compact_y", "main_x", "main_y")
_CHOICES = {
    "font_weight": ("normal", "bold"),
    "text_align": ("left", "center"),
}


class ConfigManager:
    def __init__(self, custom_path=None):
        self.config_dir = Path(custom_path) if custom_path else default_home()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.settings = self._fresh_defaults()
        self.load()

    # ── helpers ───────────────────────────────────────────────
    @staticmethod
    def _fresh_defaults():
        d = dict(DEFAULT_SETTINGS)
        d["shortcuts"] = dict(DEFAULT_SHORTCUTS)
        return d

    @staticmethod
    def _coerce(key, value):
        """Return a safe value for *key*, or the default if *value* is unusable."""
        default = DEFAULT_SETTINGS.get(key)
        try:
            if key in _NUMERIC:
                typ, lo, hi = _NUMERIC[key]
                v = typ(value)
                return max(lo, min(hi, v))
            if key in _NULLABLE_INT:
                return None if value is None else int(value)
            if key in _CHOICES:
                return value if value in _CHOICES[key] else default
            if key == "shortcuts":
                merged = dict(DEFAULT_SHORTCUTS)
                if isinstance(value, dict):
                    merged.update({k: str(v) for k, v in value.items() if k in DEFAULT_SHORTCUTS and v})
                return merged
            if isinstance(default, bool):
                return bool(value)
            if isinstance(default, str):
                return value if isinstance(value, str) else default
        except (TypeError, ValueError):
            return default
        return value

    # ── persistence ───────────────────────────────────────────
    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("config root must be an object")
                for k, v in loaded.items():
                    if k in DEFAULT_SETTINGS:
                        self.settings[k] = self._coerce(k, v)
            except Exception:
                # Keep the broken file for inspection, start clean.
                try:
                    self.config_file.replace(self.config_dir / f"config.corrupt-{int(time.time())}.json")
                except Exception:
                    pass
                self.settings = self._fresh_defaults()
        return self.settings

    def save(self):
        try:
            tmp = self.config_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.config_file)
            return True
        except Exception:
            return False

    # ── access ────────────────────────────────────────────────
    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value, save=True):
        """Set a value. Pass save=False while dragging sliders, then call save()."""
        self.settings[key] = self._coerce(key, value) if key in DEFAULT_SETTINGS else value
        if save:
            self.save()
        return self.settings[key]

    def set_shortcut(self, action, key, save=True):
        sc = dict(self.settings["shortcuts"])
        sc[action] = key
        self.settings["shortcuts"] = sc
        if save:
            self.save()

    def reset_defaults(self, keys=None):
        """Reset everything, or only the given keys."""
        fresh = self._fresh_defaults()
        if keys is None:
            keep_onboarding = self.settings.get("onboarding_complete", False)
            self.settings = fresh
            self.settings["onboarding_complete"] = keep_onboarding
        else:
            for k in keys:
                self.settings[k] = fresh[k]
        self.save()

    @property
    def data_dir(self) -> Path:
        return self.config_dir


# Global singleton
config = ConfigManager()
