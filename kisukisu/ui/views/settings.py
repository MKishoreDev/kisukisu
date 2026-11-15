# -*- coding: utf-8 -*-
"""Kisukisu — Settings: General · Reader · Window & Display · Shortcuts · Storage & Privacy."""

import os
import sys
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from . import ScrollPage
from ..components import (
    ui_font, make_pill_button, make_section, make_segmented, make_option_menu, LabeledSlider, SwitchRow, bind_wrap,
)
from ...core.config import config, DEFAULT_SETTINGS
from ...core import shortcuts as sc
from ...core.monitor_manager import MonitorManager
from ...utils import win_stealth as ws

TABS = ["General", "Reader", "Window", "Shortcuts", "Storage & privacy"]


class SettingsView(ScrollPage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._refs = []
        self._capture = None
        self.page_title("Settings", "Everything is saved automatically on this computer.")
        th = self.theme
        self.tab_bar = make_segmented(self.content, th, TABS, self._select_tab, app._settings_tab)
        self.tab_bar.pack(anchor="w", pady=(0, 14))
        self.body = ctk.CTkFrame(self.content, fg_color="transparent")
        self.body.pack(fill="x")
        self.body.grid_columnconfigure(0, weight=1)
        self._select_tab(app._settings_tab)

    def _select_tab(self, name):
        self.app._settings_tab = name
        self._cancel_capture()
        for w in self.body.winfo_children():
            w.destroy()
        self._refs = []
        self._r = 0
        {"General": self._general, "Reader": self._reader, "Window": self._window,
         "Shortcuts": self._shortcuts, "Storage & privacy": self._storage}[name]()

    # helpers
    def _card(self, title, sub=""):
        card, body = make_section(self.body, self.theme, title, sub)
        card.grid(row=self._r, column=0, sticky="ew", pady=7)
        self._r += 1
        return body

    def _toggle(self, body, row, key, title, desc="", after=None):
        def cb(v):
            config.set(key, v)
            if after:
                after()
        sr = SwitchRow(body, self.theme, title, desc, config.get(key), cb)
        self._refs.append(sr)
        sr.grid(row=row, column=0, sticky="ew", pady=6)

    def _slider(self, body, row, key, text, lo, hi, fmt, steps=None, after=None):
        def live(v):
            config.set(key, v, save=False)
            if after:
                after()
        s = LabeledSlider(body, self.theme, text, lo, hi, config.get(key), steps=steps, fmt=fmt, on_change=live,
                          on_release=lambda v: config.save())
        self._refs.append(s)
        s.grid(row=row, column=0, sticky="ew", pady=7)

    # ── tabs ────────────────────────────────────────────────────
    def _general(self):
        th = self.theme
        b = self._card("Editing & library")
        self._toggle(b, 0, "autosave", "Autosave while typing", "Your script is saved a moment after you stop typing.")
        self._toggle(b, 1, "confirm_delete", "Ask before deleting", "Deleted scripts always go to Recently deleted for 30 days.")
        self._toggle(b, 2, "minimize_library_on_present", "Minimise this window when presenting",
                     "Off by default so you can always switch back to the library.")
        self._slider(b, 3, "reading_wpm", "Speaking pace (for time estimates)", 60, 300, lambda v: f"{int(v)} words/min", 240)
        b2 = self._card("Welcome")
        make_pill_button(b2, "Show the welcome screen again", self._show_welcome, th, width=230, height=34).grid(row=0, column=0, sticky="w")

    def _show_welcome(self):
        config.set("onboarding_complete", False)
        self.app.toast("The welcome screen will appear next time you start Kisukisu", "info", 3200)

    def _reader(self):
        b = self._card("Scrolling", "How the reader moves while you speak.")
        self._slider(b, 0, "auto_scroll_speed", "Auto-scroll speed", 1, 10, lambda v: f"{int(v)}", 9, lambda: None)
        self._toggle(b, 1, "pause_between_sections", "Pause at each new section",
                     "Auto-scroll stops when a section starts — perfect when each section is a slide.")
        self._toggle(b, 2, "resume_position", "Resume where I stopped", "Reopening a script continues from your last position.")
        b2 = self._card("What the reader shows")
        refresh = lambda: self.app.refresh_reader("visual")
        self._toggle(b2, 0, "focus_mode", "Focus mode", "Highlight the current paragraph, dim the rest.", refresh)
        self._toggle(b2, 1, "show_ruler", "Reading line", "", refresh)
        self._toggle(b2, 2, "show_cues", "Cue markers", "Show [CUE: …] lines and highlight [bracketed] reminders.", refresh)
        self._toggle(b2, 3, "show_onscreen_ref", "On-screen references", "Show “On screen:” notes from your script.", refresh)
        self._toggle(b2, 4, "show_timer", "Timer", "Elapsed time and estimated time left.", refresh)
        self._slider(b2, 5, "ruler_position", "Reading line position", 0.15, 0.80, lambda v: f"{int(v * 100)}% from top", None, refresh)

    def _window(self):
        th = self.theme
        b = self._card("Reader window", "Behaviour of the floating reader.")
        self._toggle(b, 0, "always_on_top", "Always on top", "Keep the reader above your slides.", lambda: self.app.refresh_reader("pin"))
        self._toggle(b, 1, "remember_window", "Remember size & position", "Validated against your monitors every time, so it can never open off-screen.")
        self._toggle(b, 2, "start_compact", "Start in compact mode", "A slim strip you can park just under your webcam.")
        if ws.is_windows():
            self._toggle(b, 3, "hide_from_taskbar", "Hide from taskbar & Alt-Tab",
                         "Off by default. Turn on only if you want a fully invisible helper window.",
                         lambda: self.app.refresh_reader("taskbar"))
            self._toggle(b, 4, "screen_share_invisibility", "Hide from screen sharing & recording",
                         "Windows 10 (2004+) and 11 only. Meet, Zoom, Teams and OBS won't capture the reader.",
                         lambda: self.app.refresh_reader("capture"))
        else:
            ctk.CTkLabel(b, text="Screen-share hiding is Windows-only. On macOS/Linux share a single window or a second monitor — see the Screen-share guide.",
                         font=ui_font(11), text_color=th.text_sub, justify="left", anchor="w").grid(row=3, column=0, sticky="ew", pady=6)
        b2 = self._card("Display", "Where the reader opens.")
        labels = MonitorManager.get_display_labels(self.app)
        idx = min(config.get("selected_monitor", 0), len(labels) - 1)
        om = make_option_menu(b2, th, labels, lambda v: (config.set("selected_monitor", labels.index(v)),
                              self.app.toast("Reader will open on that display next time", "info")), labels[idx], 330)
        om.grid(row=0, column=0, sticky="w", pady=4)
        if len(labels) == 1:
            ctk.CTkLabel(b2, text="Only one display detected. Connect a second monitor to keep your notes private.",
                         font=ui_font(11), text_color=th.text_sub, anchor="w").grid(row=1, column=0, sticky="w")
        make_pill_button(b2, "Reset reader size & position", self._reset_window, th, width=210, height=34).grid(row=2, column=0, sticky="w", pady=(10, 0))

    def _reset_window(self):
        r = self.app._reader_alive()
        if r:
            r.reset_window_size()
        else:
            config.reset_defaults(["reader_w", "reader_h", "reader_x", "reader_y", "compact_w", "compact_h", "compact_x", "compact_y"])
        self.app.toast("Reader window reset", "success")

    # ── shortcuts ───────────────────────────────────────────────
    def _shortcuts(self):
        th = self.theme
        b = self._card("Reader shortcuts", "Click a key to change it, then press the new key. Esc cancels.")
        self._key_btns = {}
        current = {**sc.DEFAULT_SHORTCUTS, **(config.get("shortcuts") or {})}
        for i, (action, label) in enumerate(sc.LABELS.items()):
            row = ctk.CTkFrame(b, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=label, font=ui_font(12), text_color=th.text_main, anchor="w").grid(row=0, column=0, sticky="w")
            btn = ctk.CTkButton(row, text=sc.pretty(current[action]), width=130, height=30, corner_radius=8,
                                fg_color=th.pill_bg, hover_color=th.pill_hover, text_color=th.text_main,
                                font=ui_font(12, "bold"), command=lambda a=action: self._start_capture(a))
            btn.grid(row=0, column=1, sticky="e")
            self._key_btns[action] = btn
        make_pill_button(b, "Reset all to defaults", self._reset_keys, th, width=170, height=32).grid(
            row=len(sc.LABELS), column=0, sticky="w", pady=(12, 0))
        ctk.CTkLabel(b, text="Tip: ← → ↑ ↓ and Space work in the reader window when it is focused.",
                     font=ui_font(11), text_color=th.text_muted, anchor="w").grid(row=len(sc.LABELS) + 1, column=0, sticky="w", pady=(8, 0))

    def _start_capture(self, action):
        self._cancel_capture()
        self.app._capturing_key = True
        btn = self._key_btns[action]
        btn.configure(text="Press a key…", fg_color=self.theme.accent, text_color=self.theme.on_accent)
        root = self.app

        def on_key(e):
            if e.keysym == "Escape":
                self._cancel_capture()
                return "break"
            key = sc.key_from_event(e)
            if not key:
                return "break"
            current = {**sc.DEFAULT_SHORTCUTS, **(config.get("shortcuts") or {})}
            other = sc.find_conflict(current, action, key)
            if other:
                self.app.toast(f"“{sc.pretty(key)}” is already used for “{sc.LABELS[other]}”", "warning", 3200)
                return "break"
            config.set_shortcut(action, key)
            self._cancel_capture()
            self.app.refresh_reader("keys")
            self.app.toast("Shortcut saved", "success", 1400)
            return "break"

        fid = root.bind("<Key>", on_key, add="+")
        self._capture = (action, fid)

    def _cancel_capture(self):
        cap, self._capture = self._capture, None
        self.app._capturing_key = False
        if cap:
            action, fid = cap
            try:
                self.app.unbind("<Key>", fid)
            except Exception:
                pass
            btn = getattr(self, "_key_btns", {}).get(action)
            if btn is not None:
                try:
                    current = {**sc.DEFAULT_SHORTCUTS, **(config.get("shortcuts") or {})}
                    btn.configure(text=sc.pretty(current[action]), fg_color=self.theme.pill_bg, text_color=self.theme.text_main)
                except Exception:
                    pass

    def _reset_keys(self):
        config.set("shortcuts", dict(sc.DEFAULT_SHORTCUTS))
        self.app.refresh_reader("keys")
        self._select_tab("Shortcuts")

    def flush(self):
        self._cancel_capture()
        config.save()

    # ── storage & privacy ───────────────────────────────────────
    def _storage(self):
        th = self.theme
        b = self._card("Your data", "Everything lives in one folder on this computer.")
        ctk.CTkLabel(b, text=str(config.data_dir), font=ui_font(11), text_color=th.accent_light, anchor="w").grid(row=0, column=0, sticky="w")
        row = ctk.CTkFrame(b, fg_color="transparent")
        row.grid(row=1, column=0, sticky="w", pady=(10, 0))
        make_pill_button(row, "Open folder", self._open_folder, th, width=110, height=34).pack(side="left", padx=(0, 6))
        make_pill_button(row, "Back up…", self._backup, th, width=96, height=34).pack(side="left", padx=3)
        make_pill_button(row, "Restore…", self._restore, th, width=96, height=34).pack(side="left", padx=3)
        make_pill_button(row, "Export all as .md…", self._export_all, th, width=150, height=34).pack(side="left", padx=3)
        b2 = self._card("Reset", "Scripts are never touched by these.")
        make_pill_button(b2, "Reset all settings to defaults", self._reset_all, th, danger=True, width=220, height=34).grid(row=0, column=0, sticky="w")
        b3 = self._card("Privacy commitment")
        lbl = ctk.CTkLabel(b3, text="Kisukisu has no accounts, no analytics and makes no network connections. "
                                    "Your scripts, themes and settings never leave this computer. "
                                    "The only time the internet is touched is when you click a link such as GitHub.",
                           font=ui_font(12), text_color=th.text_sub, justify="left", anchor="w")
        lbl.grid(row=0, column=0, sticky="ew")
        bind_wrap(lbl, b3, margin=4)

    def _open_folder(self):
        path = str(config.data_dir)
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            self.app.toast("Could not open the folder", "error")

    def _backup(self):
        dest = filedialog.asksaveasfilename(parent=self.app, title="Back up", defaultextension=".zip",
                                            initialfile=f"kisukisu-backup-{time.strftime('%Y-%m-%d')}.zip",
                                            filetypes=[("Backup", "*.zip")])
        if dest:
            try:
                n = self.app.script_manager.backup(dest, [config.config_file, config.config_dir / "custom_theme.json"])
                self.app.toast(f"Backed up {n} scripts", "success")
            except Exception as e:
                self.app.toast(f"Backup failed: {e}", "error", 4000)

    def _restore(self):
        src = filedialog.askopenfilename(parent=self.app, title="Restore from backup", filetypes=[("Backup", "*.zip")])
        if src:
            try:
                n = self.app.script_manager.restore(src)
                self.app.toast(f"Restored {n} script{'s' if n != 1 else ''}", "success")
            except Exception as e:
                self.app.toast(f"Restore failed: {e}", "error", 4000)

    def _export_all(self):
        folder = filedialog.askdirectory(parent=self.app, title="Export every script to a folder")
        if folder:
            n = 0
            for s in self.app.script_manager.list_scripts():
                safe = "".join(c for c in s.get("title", "script") if c.isalnum() or c in " -_") .strip() or s.get("id", "script")
                if self.app.script_manager.export_script(s, os.path.join(folder, f"{safe}.md")):
                    n += 1
            self.app.toast(f"Exported {n} scripts", "success")

    def _reset_all(self):
        if messagebox.askyesno("Reset settings", "Reset every setting (theme, fonts, shortcuts…) to its default?\n\nYour scripts are not affected.", parent=self.app):
            config.reset_defaults()
            self.app.apply_theme(config.get("theme"))
            self.app.refresh_reader("visual")
            self.app.toast("Settings reset", "success")
