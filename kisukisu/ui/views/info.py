# -*- coding: utf-8 -*-
"""Kisukisu — Screen-share guide, About, and Recently deleted."""

import os
import time
import webbrowser
from tkinter import messagebox
import customtkinter as ctk

from . import ScrollPage
from .. import components as C
from ..components import ui_font, make_pill_button, make_card, make_section, bind_wrap
from ... import __version__
from ...core.config import config
from ...utils.resource_path import resource_path
from ..library_view import GITHUB_URL, ISSUES_URL


def _para(parent, theme, text, size=12, color=None, pady=(0, 6)):
    lbl = ctk.CTkLabel(parent, text=text, font=ui_font(size), text_color=color or theme.text_sub,
                       justify="left", anchor="w")
    lbl.pack(anchor="w", fill="x", pady=pady)
    bind_wrap(lbl, parent, margin=6)
    return lbl


class GuideView(ScrollPage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        th = self.theme
        self.page_title("Screen-share guide", "An honest guide to keeping your notes private on a call.")
        items = [
            ("1 · Share one window, not the whole screen (works everywhere)",
             "In Meet, Zoom or Teams choose “Window” (or “Chrome tab”) and pick your slides. Anything else on your desktop — including Kisukisu — isn't shared. This is the most reliable method on every operating system."),
            ("2 · Use a second monitor (best for privacy)",
             "Put your slides on Display 2 and share only that display. Keep Kisukisu on your laptop screen. In Settings → Window you can choose which display the reader opens on."),
            ("3 · Windows capture exclusion (Windows 10 2004+ / 11)",
             "Kisukisu asks Windows to leave the reader out of screen capture, so it stays hidden even if you share the whole desktop. It is on by default and can be switched off in Settings → Window. It is not available on macOS or Linux, and some capture tools may behave differently — do a quick test share with a friend before an important talk."),
            ("Always test first",
             "Start a test meeting by yourself, share your screen, and look at the shared preview before you present for real."),
        ]
        for t, b in items:
            card, body = make_section(self.content, th, t)
            card.pack(fill="x", pady=6)
            _para(body, th, b)


class AboutView(ScrollPage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        th = self.theme
        self._banner_ref = None
        self.banner_lbl = None
        try:
            from PIL import Image
            p = resource_path("assets", "banner.jpg")
            if os.path.exists(p):
                self._banner_src = Image.open(p).convert("RGB")
                self.banner_lbl = ctk.CTkLabel(self.content, text="", corner_radius=16)
                self.banner_lbl.pack(fill="x", pady=(0, 16))
                self._banner_w = 0
                self.content.bind("<Configure>", self._fit_banner, add="+")
        except Exception:
            pass

        ctk.CTkLabel(self.content, text="kisukisu.", font=ui_font(30, "bold"), text_color=th.text_main, anchor="w").pack(anchor="w")
        ctk.CTkLabel(self.content, text="கிசுகிசு  ·  Your little secret.", font=ui_font(14), text_color=th.accent_light, anchor="w").pack(anchor="w")
        ctk.CTkLabel(self.content, text=f"Version {__version__}  ·  MIT licence  ·  Open source", font=ui_font(11),
                     text_color=th.text_muted, anchor="w").pack(anchor="w", pady=(2, 12))
        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(anchor="w", pady=(0, 10))
        make_pill_button(row, "GitHub  ↗", lambda: webbrowser.open(GITHUB_URL), th, primary=True, width=104, height=36).pack(side="left", padx=(0, 6))
        make_pill_button(row, "Report an issue  ↗", lambda: webbrowser.open(ISSUES_URL), th, width=140, height=36).pack(side="left", padx=3)

        self._card("What does Kisukisu mean?",
                   "Kisukisu (கிசுகிசு) is the Tamil word for a whisper — a hushed, quiet conversation. That is the idea: a little whisper that stays with you while you speak. It doesn't take the spotlight or interrupt your presentation; it simply helps you remember what comes next.")
        self._card("Why it exists",
                   "It started with a simple problem: when presenting, running a workshop or speaking in an online meeting, I wanted my script and notes within reach without constantly switching windows. Existing tools felt too complicated or too limited, so I built one myself.\n\nNo mandatory accounts. No subscriptions just to read your own notes. Built out of a personal need. Shared for everyone.")
        self._card("Our principles",
                   "•  Built for a real problem — solve an everyday frustration.\n•  Simplicity over complexity — it should make presenting easier, not become another thing to manage.\n•  Privacy by default — your scripts stay on your device.\n•  Open source for everyone — transparent, customisable and open to contributions.")
        self._card("Credits", "Built with Python, CustomTkinter, Pillow and pystray. Thank you to everyone who tests, reports bugs and contributes.")

    def _card(self, title, text):
        card, body = make_section(self.content, self.theme, title)
        card.pack(fill="x", pady=6)
        _para(body, self.theme, text, 12)

    def _fit_banner(self, e):
        w = max(320, min(e.width, 1040))
        if abs(w - self._banner_w) < 24 or self.banner_lbl is None:
            return
        self._banner_w = w
        h = int(w * self._banner_src.height / self._banner_src.width)
        self._banner_ref = ctk.CTkImage(self._banner_src, size=(w, h))
        try:
            self.banner_lbl.configure(image=self._banner_ref)
        except Exception:
            pass


class TrashView(ScrollPage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        th = self.theme
        self.page_title("Recently deleted", "Deleted scripts stay here for 30 days, then are removed for good.")
        self.list_box = ctk.CTkFrame(self.content, fg_color="transparent")
        self.list_box.pack(fill="x")
        self.refresh()

    def refresh(self):
        th = self.theme
        for w in self.list_box.winfo_children():
            w.destroy()
        items = self.app.script_manager.list_trash()
        if not items:
            ctk.CTkLabel(self.list_box, text="Nothing here. Deleted scripts will appear in this list.", font=ui_font(13),
                         text_color=th.text_sub).pack(pady=40)
            return
        make_pill_button(self.list_box, "Empty trash", self._empty, th, danger=True, width=110, height=32).pack(anchor="e", pady=(0, 8))
        for s in items:
            card = make_card(self.list_box, th, corner_radius=12)
            card.pack(fill="x", pady=5)
            card.grid_columnconfigure(0, weight=1)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.grid(row=0, column=0, sticky="w", padx=16, pady=12)
            ctk.CTkLabel(left, text=s.get("title", "Untitled"), font=ui_font(14, "bold"), text_color=th.text_main, anchor="w").pack(anchor="w")
            days = max(0, 30 - int((time.time() - s.get("deleted_at", time.time())) / 86400))
            ctk.CTkLabel(left, text=f"{s.get('word_count', 0):,} words · removed for good in {days} day{'s' if days != 1 else ''}",
                         font=ui_font(11), text_color=th.text_muted, anchor="w").pack(anchor="w")
            acts = ctk.CTkFrame(card, fg_color="transparent")
            acts.grid(row=0, column=1, padx=14)
            make_pill_button(acts, "Restore", lambda sid=s["id"]: self._restore(sid), th, primary=True, width=86, height=32).pack(side="left", padx=3)
            make_pill_button(acts, "Delete forever", lambda sid=s["id"]: self._purge(sid), th, width=120, height=32).pack(side="left", padx=3)

    def _restore(self, sid):
        if self.app.script_manager.restore_script(sid):
            self.app.toast("Script restored", "success")
        self.refresh()

    def _purge(self, sid):
        if messagebox.askyesno("Delete forever", "This script will be permanently deleted. Continue?", parent=self.app):
            self.app.script_manager.purge_script(sid)
            self.refresh()

    def _empty(self):
        if messagebox.askyesno("Empty trash", "Permanently delete everything in Recently deleted?", parent=self.app):
            n = self.app.script_manager.empty_trash()
            self.app.toast(f"Deleted {n} script{'s' if n != 1 else ''} for good", "info")
            self.refresh()
