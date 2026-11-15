# -*- coding: utf-8 -*-
"""
Kisukisu — Welcome & Setup Screen
Minimalist, elegant introduction shown on first launch.
"""

import os
import sys
import tkinter as tk
import customtkinter as ctk
from ..ui.themes import Theme
from ..ui.components import make_pill_button
from .components import apply_window_icon


class WelcomeScreen(ctk.CTkToplevel):
    """Clean first-launch walkthrough."""

    def __init__(self, parent, theme: Theme, on_done=None, logo_img=None):
        super().__init__(parent)
        self.theme = theme
        self.on_done = on_done
        self.logo_img = logo_img
        self._step = 0

        self.title("Welcome to Kisukisu")
        self.geometry("540x460")
        self.resizable(False, False)
        self.configure(fg_color=self.theme.bg)
        self.transient(parent)
        self.after(100, lambda: (self.lift(), self.focus_force()))

        apply_window_icon(self)

        self.update_idletasks()
        try:
            px, py = parent.winfo_x(), parent.winfo_y()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x, y = px + max(0, (pw - 540) // 2), py + max(0, (ph - 460) // 2)
        except Exception:
            x, y = 200, 120
        self.geometry(f"540x460+{max(0, x)}+{max(0, y)}")

        self._build_step_0()

    def _build_step_0(self):
        self._clear()

        if self.logo_img:
            ctk.CTkLabel(self, image=self.logo_img, text="").pack(pady=(40, 6))
        else:
            ctk.CTkLabel(self, text="", height=30).pack(pady=(24, 6))

        ctk.CTkLabel(
            self, text="kisukisu.",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=self.theme.text_main,
        ).pack()

        ctk.CTkLabel(
            self, text="கிசுகிசு · Your little secret.",
            font=ctk.CTkFont(size=13),
            text_color=self.theme.accent_light,
        ).pack(pady=(2, 4))

        ctk.CTkLabel(
            self,
            text="A private presenter companion for reading notes,\nprompts and scripts smoothly during live sessions.",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_sub,
            justify="center",
        ).pack(pady=(8, 28))

        make_pill_button(
            self, "Get Started  →",
            command=self._build_step_1,
            theme=self.theme,
            primary=True, width=160, height=40,
        ).pack()

        self._dot_row(0)

    def _build_step_1(self):
        self._clear()

        ctk.CTkLabel(
            self, text="Choose how to start",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.theme.text_main,
        ).pack(pady=(32, 4))

        ctk.CTkLabel(
            self, text="Select an initial action to open your workspace.",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_sub,
        ).pack(pady=(0, 20))

        options = [
            ("+", "Write a new script", "Start with an empty template", "write"),
            ("↓", "Import document",   "Open an existing .md or .txt file", "import"),
            ("▶", "Try the 1-minute tour", "Open the reader with a sample script", "sample"),
        ]
        for icon, title, desc, action in options:
            self._option_card(icon, title, desc, action)

        self._dot_row(1)

    def _option_card(self, icon: str, title: str, desc: str, action: str):
        card = ctk.CTkFrame(
            self,
            fg_color=self.theme.card_bg,
            corner_radius=10,
            border_width=1,
            border_color=self.theme.border,
            cursor="hand2",
        )
        card.pack(fill="x", padx=44, pady=5)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(
            inner, text=icon,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.accent,
            width=28,
        ).pack(side="left", padx=(0, 10))

        txt_col = ctk.CTkFrame(inner, fg_color="transparent")
        txt_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            txt_col, text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.text_main,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            txt_col, text=desc,
            font=ctk.CTkFont(size=11),
            text_color=self.theme.text_sub,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            inner, text="→",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme.accent,
        ).pack(side="right")

        for w in [card, inner, txt_col]:
            w.bind("<Enter>", lambda e, c=card: c.configure(border_color=self.theme.accent))
            w.bind("<Leave>", lambda e, c=card: c.configure(border_color=self.theme.border))
            w.bind("<Button-1>", lambda e, a=action: self._on_choice(a))

    def _on_choice(self, action: str):
        self._selected_action = action
        self._build_step_2()

    def _build_step_2(self):
        self._clear()

        ctk.CTkLabel(
            self, text="Ready",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.theme.text_main,
        ).pack(pady=(44, 6))

        tips = [
            "Space  —  start / pause auto-scroll",
            "← →  —  previous / next section",
            "M  —  compact strip      F11  —  fullscreen",
            "T  —  keep above other windows",
            "Every key can be changed in Settings",
        ]
        ctk.CTkLabel(
            self,
            text="\n".join(f"  {t}" for t in tips),
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_sub,
            justify="left",
        ).pack(pady=(12, 28))

        make_pill_button(
            self, "Open Workspace",
            command=self._finish,
            theme=self.theme,
            primary=True, width=170, height=42,
        ).pack()

        self._dot_row(2)

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _dot_row(self, active: int):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(side="bottom", pady=18)
        for i in range(3):
            color = self.theme.accent if i == active else self.theme.border
            ctk.CTkFrame(row, fg_color=color, width=7, height=7, corner_radius=3).pack(
                side="left", padx=4
            )

    def _finish(self):
        if self.on_done:
            self.on_done(getattr(self, "_selected_action", "write"))
        self.destroy()
