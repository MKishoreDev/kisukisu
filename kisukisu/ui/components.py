# -*- coding: utf-8 -*-
"""
Kisukisu — Reusable UI components (design system).

Everything visual in the app is built from these so spacing, radii, fonts and
colours stay consistent, and every control is themeable.
"""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from .themes import Theme
from ..utils.resource_path import resource_path

# ── fonts ─────────────────────────────────────────────────────────
_PREFERRED_UI = {
    "win32": ["Segoe UI", "Nirmala UI", "Arial"],
    "darwin": ["Helvetica Neue", "Arial"],
    "linux": ["Inter", "Noto Sans", "Ubuntu", "DejaVu Sans", "Arial"],
}
_CURATED_READER = [
    "Segoe UI", "Nirmala UI", "Inter", "Roboto", "Open Sans", "Noto Sans", "Noto Sans Tamil",
    "Calibri", "Verdana", "Tahoma", "Arial", "Helvetica Neue", "Georgia", "Cambria",
    "Times New Roman", "Atkinson Hyperlegible", "Lexend", "OpenDyslexic", "Consolas", "Courier New",
]
_family_cache = None


def installed_families():
    global _family_cache
    if _family_cache is None:
        try:
            _family_cache = {f.lower(): f for f in tkfont.families()}
        except Exception:
            _family_cache = {}
    return _family_cache


def resolve_font(preferred: str = "") -> str:
    """Return *preferred* if installed, otherwise the best platform default."""
    fams = installed_families()
    if preferred and (not fams or preferred.lower() in fams):
        return fams.get(preferred.lower(), preferred)
    key = "win32" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")
    for cand in _PREFERRED_UI[key]:
        if cand.lower() in fams:
            return fams[cand.lower()]
    return "TkDefaultFont"


def font_choices():
    """Curated installed fonts first, then everything else (alphabetical)."""
    fams = installed_families()
    curated = [fams[f.lower()] for f in _CURATED_READER if f.lower() in fams]
    rest = sorted((v for v in fams.values() if v not in curated and not v.startswith("@")), key=str.lower)
    return curated + rest or ["TkDefaultFont"]


def ui_font(size=13, weight="normal", slant="roman"):
    return ctk.CTkFont(family=resolve_font(), size=size, weight=weight, slant=slant)


# ── window helpers ────────────────────────────────────────────────
def apply_window_icon(win):
    """
    Set the Kisukisu icon. CustomTkinter overwrites the icon ~200 ms after a
    window opens on Windows, so we apply it again afterwards.
    """
    def _apply():
        try:
            ico = resource_path("assets", "logo.ico")
            png = resource_path("assets", "logo.png")
            if sys.platform == "win32" and os.path.exists(ico):
                win.iconbitmap(ico)
            elif os.path.exists(png):
                from PIL import Image, ImageTk
                win._kisu_icon = ImageTk.PhotoImage(Image.open(png))
                win.iconphoto(True, win._kisu_icon)
        except Exception:
            pass
    _apply()
    try:
        win.after(300, _apply)
    except Exception:
        pass


def style_menu(menu: tk.Menu, theme: Theme) -> tk.Menu:
    try:
        menu.configure(
            bg=theme.card_bg, fg=theme.text_main,
            activebackground=theme.accent, activeforeground=theme.on_accent,
            disabledforeground=theme.text_muted, bd=0, relief="flat",
            font=(resolve_font(), 10),
        )
    except Exception:
        pass
    return menu


def bind_wrap(label: ctk.CTkLabel, container, margin: int = 0, min_wrap: int = 120):
    """Keep a label's wraplength in sync with the width of its container (responsive text)."""
    def _on_cfg(e):
        try:
            label.configure(wraplength=max(min_wrap, e.width - margin))
        except Exception:
            pass
    container.bind("<Configure>", _on_cfg, add="+")


# ── buttons ───────────────────────────────────────────────────────
def make_pill_button(parent, text: str, command=None, theme: Theme = None,
                     width: int = 100, height: int = 36, primary: bool = False,
                     danger: bool = False, small: bool = False, tooltip: str = None
                     ) -> ctk.CTkButton:
    if small:
        height, font_size = 28, 11
    else:
        font_size = 12

    if theme is None:
        fg, hover, text_color = "#252535", "#2F2F44", "#F0EFF6"
    elif primary:
        fg, hover, text_color = theme.accent, theme.accent_hover, theme.on_accent
    elif danger:
        fg, hover, text_color = theme.error, "#B91C1C", "#FFFFFF"
    else:
        fg, hover, text_color = theme.pill_bg, theme.pill_hover, theme.text_main

    btn = ctk.CTkButton(
        parent, text=text, command=command, width=width, height=height,
        corner_radius=height // 2, fg_color=fg, hover_color=hover, text_color=text_color,
        font=ui_font(font_size, "bold"),
    )
    if tooltip and theme:
        Tooltip(btn, tooltip, theme)
    return btn


def make_icon_button(parent, text: str, command=None, theme: Theme = None,
                     size: int = 32, tooltip: str = None, active: bool = False) -> ctk.CTkButton:
    if theme:
        fg = theme.accent if active else theme.pill_bg
        hover = theme.accent_hover if active else theme.pill_hover
        tc = theme.on_accent if active else theme.text_main
    else:
        fg, hover, tc = "#252535", "#2F2F44", "#F0EFF6"
    btn = ctk.CTkButton(
        parent, text=text, command=command, width=size, height=size,
        corner_radius=size // 2, fg_color=fg, hover_color=hover, text_color=tc,
        font=ui_font(13, "bold"),
    )
    if tooltip and theme:
        Tooltip(btn, tooltip, theme)
    return btn


def set_active(btn: ctk.CTkButton, theme: Theme, active: bool):
    """Visually toggle an icon/pill button between normal and accent state."""
    btn.configure(
        fg_color=theme.accent if active else theme.pill_bg,
        hover_color=theme.accent_hover if active else theme.pill_hover,
        text_color=theme.on_accent if active else theme.text_sub,
    )


# ── containers & text ────────────────────────────────────────────
def make_card(parent, theme: Theme, corner_radius: int = 12, padx: int = 0, pady: int = 0
              ) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=theme.card_bg, corner_radius=corner_radius,
                        border_width=1, border_color=theme.border)


def make_label(parent, text: str, theme: Theme, size: int = 13, bold: bool = False,
               sub: bool = False, muted: bool = False, anchor: str = "w", **kw) -> ctk.CTkLabel:
    color = theme.text_muted if muted else (theme.text_sub if sub else theme.text_main)
    return ctk.CTkLabel(parent, text=text, text_color=color,
                        font=ui_font(size, "bold" if bold else "normal"), anchor=anchor, **kw)


def make_separator(parent, theme: Theme, horizontal: bool = True) -> ctk.CTkFrame:
    if horizontal:
        return ctk.CTkFrame(parent, fg_color=theme.border_subtle, height=1, corner_radius=0)
    return ctk.CTkFrame(parent, fg_color=theme.border_subtle, width=1, corner_radius=0)


def make_badge(parent, text: str, theme: Theme, color: str = None) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=ui_font(10, "bold"), text_color=theme.accent_light,
                        fg_color=color or theme.selected_bg, corner_radius=6, padx=6, pady=2)


def make_progress_bar(parent, theme: Theme, width: int = 200) -> ctk.CTkProgressBar:
    pb = ctk.CTkProgressBar(parent, width=width, height=3, corner_radius=2,
                            progress_color=theme.progress_color, fg_color=theme.border_subtle)
    pb.set(0)
    return pb


def make_search_entry(parent, theme: Theme, placeholder: str = "Search scripts…",
                      width: int = 240, textvariable=None) -> ctk.CTkEntry:
    return ctk.CTkEntry(
        parent, placeholder_text=placeholder, placeholder_text_color=theme.text_muted,
        fg_color=theme.input_bg, border_color=theme.border, text_color=theme.text_main,
        corner_radius=20, width=width, height=36, font=ui_font(13), textvariable=textvariable)


def make_entry(parent, theme: Theme, width: int = 160, textvariable=None, placeholder: str = "") -> ctk.CTkEntry:
    return ctk.CTkEntry(
        parent, width=width, height=34, corner_radius=8, textvariable=textvariable,
        placeholder_text=placeholder, placeholder_text_color=theme.text_muted,
        fg_color=theme.input_bg, border_color=theme.border, text_color=theme.text_main, font=ui_font(12))


def make_segmented(parent, theme: Theme, values, command=None, value=None) -> ctk.CTkSegmentedButton:
    seg = ctk.CTkSegmentedButton(
        parent, values=list(values), command=command, height=32, corner_radius=10,
        fg_color=theme.pill_bg, selected_color=theme.accent, selected_hover_color=theme.accent_hover,
        unselected_color=theme.pill_bg, unselected_hover_color=theme.pill_hover,
        text_color=theme.text_main, font=ui_font(12, "bold"))
    if value is not None:
        seg.set(value)
    return seg


def make_option_menu(parent, theme: Theme, values, command=None, value=None, width: int = 190) -> ctk.CTkOptionMenu:
    om = ctk.CTkOptionMenu(
        parent, values=list(values), command=command, width=width, height=34, corner_radius=8,
        fg_color=theme.input_bg, button_color=theme.pill_bg, button_hover_color=theme.pill_hover,
        text_color=theme.text_main, dropdown_fg_color=theme.card_bg, dropdown_text_color=theme.text_main,
        dropdown_hover_color=theme.hover_bg, font=ui_font(12), dropdown_font=ui_font(12))
    if value is not None:
        om.set(value)
    return om


def make_section(parent, theme: Theme, title: str, subtitle: str = ""):
    """A titled card. Returns (card, body) — put your controls in *body*."""
    card = make_card(parent, theme, corner_radius=14)
    head = ctk.CTkFrame(card, fg_color="transparent")
    head.pack(fill="x", padx=20, pady=(16, 4))
    ctk.CTkLabel(head, text=title, font=ui_font(14, "bold"), text_color=theme.text_main, anchor="w"
                 ).pack(anchor="w")
    if subtitle:
        sub = ctk.CTkLabel(head, text=subtitle, font=ui_font(11), text_color=theme.text_sub,
                           anchor="w", justify="left")
        sub.pack(anchor="w", fill="x")
        bind_wrap(sub, head, margin=4)
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="x", padx=20, pady=(6, 16))
    body.grid_columnconfigure(0, weight=1)
    return card, body


class LabeledSlider:
    """Label + live value + slider. on_change fires while dragging, on_release once at the end."""

    def __init__(self, parent, theme: Theme, text, from_, to, value, steps=None,
                 fmt=lambda v: f"{v:g}", on_change=None, on_release=None):
        self.fmt, self.on_change, self.on_release = fmt, on_change, on_release
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.frame, text=text, font=ui_font(12), text_color=theme.text_main, anchor="w"
                     ).grid(row=0, column=0, sticky="w")
        self.value_lbl = ctk.CTkLabel(self.frame, text=fmt(value), font=ui_font(12, "bold"),
                                      text_color=theme.accent_light, anchor="e")
        self.value_lbl.grid(row=0, column=1, sticky="e")
        self.slider = ctk.CTkSlider(
            self.frame, from_=from_, to=to, number_of_steps=steps, height=16,
            progress_color=theme.accent, button_color=theme.accent, button_hover_color=theme.accent_hover,
            fg_color=theme.border, command=self._changed)
        self.slider.set(value)
        self.slider.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        try:
            self.slider.bind("<ButtonRelease-1>", self._released)
        except Exception:
            pass

    def _changed(self, v):
        self.value_lbl.configure(text=self.fmt(v))
        if self.on_change:
            self.on_change(v)

    def _released(self, _e=None):
        if self.on_release:
            self.on_release(self.slider.get())

    def set(self, v):
        self.slider.set(v)
        self.value_lbl.configure(text=self.fmt(v))

    def grid(self, **kw):
        self.frame.grid(**kw)
        return self

    def pack(self, **kw):
        self.frame.pack(**kw)
        return self


class SwitchRow:
    """Title + helper text on the left, toggle on the right."""

    def __init__(self, parent, theme: Theme, title, desc="", value=False, command=None):
        self.var = tk.BooleanVar(value=bool(value))
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)
        txt = ctk.CTkFrame(self.frame, fg_color="transparent")
        txt.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(txt, text=title, font=ui_font(12, "bold"), text_color=theme.text_main, anchor="w"
                     ).pack(anchor="w")
        if desc:
            d = ctk.CTkLabel(txt, text=desc, font=ui_font(11), text_color=theme.text_sub,
                             anchor="w", justify="left")
            d.pack(anchor="w", fill="x")
            bind_wrap(d, self.frame, margin=90)
        self.switch = ctk.CTkSwitch(
            self.frame, text="", width=44, variable=self.var, progress_color=theme.accent,
            button_color="#FFFFFF", button_hover_color="#EEEEEE", fg_color=theme.border,
            command=(lambda: command(self.var.get())) if command else None)
        self.switch.grid(row=0, column=1, sticky="e")

    def grid(self, **kw):
        self.frame.grid(**kw)
        return self

    def pack(self, **kw):
        self.frame.pack(**kw)
        return self


# ── tooltip & toast ───────────────────────────────────────────────
class Tooltip:
    """Small hover hint. Safe on topmost windows."""

    def __init__(self, widget, text: str, theme: Theme, delay: int = 450):
        self.widget, self.text, self.theme, self.delay = widget, text, theme, delay
        self._tip = None
        self._job = None
        for seq, fn in (("<Enter>", self._schedule), ("<Leave>", self._hide), ("<ButtonPress>", self._hide)):
            try:
                widget.bind(seq, fn, add="+")
            except Exception:
                pass

    def _schedule(self, _e=None):
        self._cancel()
        try:
            self._job = self.widget.after(self.delay, self._show)
        except Exception:
            pass

    def _cancel(self):
        if self._job:
            try:
                self.widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _show(self):
        if self._tip or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() - 34
            tip = tk.Toplevel(self.widget)
            tip.overrideredirect(True)
            tip.attributes("-topmost", True)
            lbl = tk.Label(tip, text=self.text, bg=self.theme.card_bg, fg=self.theme.text_main,
                           bd=1, relief="solid", padx=8, pady=3, font=(resolve_font(), 9))
            lbl.configure(highlightbackground=self.theme.border)
            lbl.pack()
            tip.update_idletasks()
            w = tip.winfo_reqwidth()
            if y < 4:
                y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            tip.geometry(f"+{max(0, x - w // 2)}+{y}")
            self._tip = tip
        except Exception:
            self._tip = None

    def _hide(self, _e=None):
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


class Toast:
    """Non-blocking message that fades after a moment (replaces blocking message boxes)."""

    def __init__(self, parent, theme: Theme):
        self.parent, self.theme = parent, theme
        self._frame = None
        self._job = None

    def show(self, text: str, kind: str = "info", ms: int = 2600):
        color = {"success": self.theme.success, "error": self.theme.error,
                 "warning": self.theme.warning}.get(kind, self.theme.accent)
        try:
            self.hide()
            self._frame = ctk.CTkFrame(self.parent, fg_color=self.theme.card_bg, corner_radius=20,
                                       border_width=1, border_color=color)
            ctk.CTkLabel(self._frame, text="●", text_color=color, font=ui_font(10)
                         ).pack(side="left", padx=(14, 4), pady=8)
            ctk.CTkLabel(self._frame, text=text, text_color=self.theme.text_main, font=ui_font(12)
                         ).pack(side="left", padx=(0, 16), pady=8)
            self._frame.place(relx=0.5, rely=1.0, y=-24, anchor="s")
            self._frame.lift()
            self._job = self.parent.after(ms, self.hide)
        except Exception:
            self._frame = None

    def hide(self):
        if self._job:
            try:
                self.parent.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self._frame is not None:
            try:
                self._frame.destroy()
            except Exception:
                pass
            self._frame = None
