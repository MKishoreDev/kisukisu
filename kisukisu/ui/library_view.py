# -*- coding: utf-8 -*-
"""
Kisukisu — Main window (library & studio).

One responsive window: a sidebar that collapses to icons on narrow windows,
and a stage that swaps between Home, Editor, Appearance, Settings, Recently
deleted, Privacy guide and About.
"""

import os
import sys
import queue
import webbrowser
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from .. import __version__
from ..core.config import config
from ..core.script_manager import ScriptManager
from ..core.monitor_manager import MonitorManager
from ..core.geometry import parse_geometry, format_geometry, clamp_rect
from ..utils.resource_path import resource_path
from ..utils import win_stealth as ws
from .themes import get_theme, Theme
from .components import (
    ui_font, make_separator, apply_window_icon, Toast, Tooltip,
)
from .reader_view import PresenterReaderWindow

GITHUB_URL = "https://github.com/MKishoreDev/kisukisu"
ISSUES_URL = GITHUB_URL + "/issues"
COLLAPSE_BELOW = 920          # window width under which the sidebar becomes icons-only

NAV_ITEMS = [
    ("home",       "⌂", "Home"),
    ("appearance", "◐", "Appearance"),
    ("settings",   "⚙", "Settings"),
    ("trash",      "⌫", "Recently deleted"),
    ("guide",      "◈", "Screen-share guide"),
    ("about",      "ⓘ", "About"),
]


class LibraryWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.script_manager = ScriptManager()
        self.theme: Theme = get_theme(config.get("theme", "midnight"))
        self.reader_window = None
        self.tray_queue: "queue.Queue[str]" = queue.Queue()
        self._minimized_for_reader = False
        self._draft_ids = set()
        self._current_view = "home"
        self.view = None
        self.home_state = {"q": "", "sort": "recent", "tag": None}
        self._capturing_key = False
        self._settings_tab = "General"
        self._sidebar_collapsed = None
        self._resize_job = None
        self._logo_img = None

        ctk.set_appearance_mode("dark" if self.theme.dark else "light")
        self.title("Kisukisu · கிசுகிசு")
        self.minsize(720, 520)
        self.configure(fg_color=self.theme.bg)
        self.geometry(self._initial_geometry())
        apply_window_icon(self)
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        self._build_skeleton()
        self.toast_mgr = Toast(self, self.theme)
        self._bind_shortcuts()
        self.switch_view("home")
        self.bind("<Configure>", self._on_configure, add="+")
        self.after(250, self._poll_tray)
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()
        self.after(80, lambda: ws.set_dark_titlebar(ws.top_level_hwnd(self.winfo_id()), self.theme.dark))

    # ═════════════════════════ window / geometry ═════════════════
    def _scale(self) -> float:
        try:
            return float(ctk.ScalingTracker.get_window_scaling(self))
        except Exception:
            return 1.0

    def _initial_geometry(self) -> str:
        monitors = MonitorManager.get_monitors(self)
        w, h, x, y = clamp_rect(config.get("main_w"), config.get("main_h"), config.get("main_x"),
                                config.get("main_y"), monitors, 0, min_w=720, min_h=520,
                                scale=self._scale())
        return format_geometry(w, h, x, y)

    def _save_main_geometry(self):
        try:
            if self.state() in ("iconic", "zoomed", "withdrawn"):
                return
            p = parse_geometry(self.geometry())
            if p and p[2] > -30000:
                for k, v in zip(("main_w", "main_h", "main_x", "main_y"), p):
                    config.set(k, v, save=False)
        except Exception:
            pass

    def _on_configure(self, e):
        if e.widget is not self:
            return
        if self._resize_job:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(80, self._after_resize)

    def _after_resize(self):
        self._resize_job = None
        want = bool(config.get("sidebar_collapsed")) or self.winfo_width() < COLLAPSE_BELOW
        if want != self._sidebar_collapsed:
            self._render_sidebar(want)

    # ═════════════════════════ skeleton & sidebar ════════════════
    def _build_skeleton(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, fg_color=self.theme.sidebar_bg, corner_radius=0, width=232)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.stage = ctk.CTkFrame(self, fg_color=self.theme.bg, corner_radius=0)
        self.stage.grid(row=0, column=1, sticky="nsew")
        self.stage.grid_columnconfigure(0, weight=1)
        self.stage.grid_rowconfigure(0, weight=1)
        self._render_sidebar(bool(config.get("sidebar_collapsed")) or self._geometry_width() < COLLAPSE_BELOW)

    def _geometry_width(self) -> int:
        p = parse_geometry(self.geometry())
        return p[0] if p else 1120

    def _load_logo(self, size):
        try:
            from PIL import Image
            path = resource_path("assets", "logo.png")
            if os.path.exists(path):
                img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
                return ctk.CTkImage(img, size=(size, size))
        except Exception:
            pass
        return None

    def _render_sidebar(self, collapsed: bool):
        th = self.theme
        self._sidebar_collapsed = collapsed
        for w in self.sidebar.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        self.sidebar.configure(width=68 if collapsed else 232)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(20, weight=1)

        # brand
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent", cursor="hand2")
        brand.grid(row=0, column=0, padx=10 if collapsed else 16, pady=(20, 6), sticky="ew")
        logo = self._load_logo(32)
        if logo:
            self._logo_img = logo
            lbl = ctk.CTkLabel(brand, image=logo, text="")
            lbl.pack(side="top" if collapsed else "left", padx=(0, 0 if collapsed else 10))
            lbl.bind("<Button-1>", lambda e: self.switch_view("home"))
        if not collapsed:
            box = ctk.CTkFrame(brand, fg_color="transparent")
            box.pack(side="left")
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(anchor="w")
            ctk.CTkLabel(row, text="kisukisu", font=ui_font(19, "bold"), text_color=th.text_main).pack(side="left")
            ctk.CTkLabel(row, text=".", font=ui_font(19, "bold"), text_color=th.accent).pack(side="left")
            ctk.CTkLabel(box, text="கிசுகிசு · Your little secret.", font=ui_font(10),
                         text_color=th.accent_light).pack(anchor="w")
            for w in (box, row):
                w.bind("<Button-1>", lambda e: self.switch_view("home"))
        brand.bind("<Button-1>", lambda e: self.switch_view("home"))

        make_separator(self.sidebar, th).grid(row=1, column=0, sticky="ew", padx=14, pady=8)

        self._nav_buttons = {}
        for i, (vid, icon, label) in enumerate(NAV_ITEMS):
            if collapsed:
                btn = ctk.CTkButton(self.sidebar, text=icon, width=44, height=40, corner_radius=10,
                                    fg_color="transparent", hover_color=th.hover_bg, text_color=th.text_sub,
                                    font=ui_font(16), command=lambda v=vid: self.switch_view(v))
                btn.grid(row=2 + i, column=0, padx=10, pady=2)
                Tooltip(btn, label, th)
            else:
                btn = ctk.CTkButton(self.sidebar, text=f"  {icon}   {label}", height=40, corner_radius=10,
                                    fg_color="transparent", hover_color=th.hover_bg, text_color=th.text_sub,
                                    font=ui_font(13), anchor="w", command=lambda v=vid: self.switch_view(v))
                btn.grid(row=2 + i, column=0, padx=12, pady=2, sticky="ew")
            self._nav_buttons[vid] = btn

        # bottom
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.grid(row=21, column=0, padx=10 if collapsed else 12, pady=14, sticky="ew")
        if collapsed:
            b = ctk.CTkButton(bottom, text="»", width=44, height=34, corner_radius=10, fg_color=th.pill_bg,
                              hover_color=th.pill_hover, text_color=th.text_sub, font=ui_font(14, "bold"),
                              command=self._toggle_sidebar)
            b.pack()
            Tooltip(b, "Expand sidebar", th)
        else:
            ctk.CTkButton(bottom, text="GitHub  ↗", height=34, corner_radius=17, fg_color=th.card_bg,
                          hover_color=th.pill_hover, text_color=th.accent_light, border_width=1,
                          border_color=th.border, font=ui_font(12, "bold"),
                          command=self._open_github).pack(fill="x")
            foot = ctk.CTkFrame(bottom, fg_color="transparent")
            foot.pack(fill="x", pady=(10, 0))
            ctk.CTkLabel(foot, text=f"v{__version__} · Local-first & private", font=ui_font(10),
                         text_color=th.text_muted).pack(side="left", padx=4)
            c = ctk.CTkButton(foot, text="«", width=28, height=24, corner_radius=8, fg_color="transparent",
                              hover_color=th.hover_bg, text_color=th.text_muted, font=ui_font(12, "bold"),
                              command=self._toggle_sidebar)
            c.pack(side="right")
            Tooltip(c, "Collapse sidebar", th)
        self._update_nav_selection(self._current_view)

    def _toggle_sidebar(self):
        config.set("sidebar_collapsed", not bool(config.get("sidebar_collapsed")))
        want = bool(config.get("sidebar_collapsed")) or self.winfo_width() < COLLAPSE_BELOW
        self._render_sidebar(want)

    def _update_nav_selection(self, active: str):
        th = self.theme
        highlight = {"editor": "home"}.get(active, active)
        for vid, btn in getattr(self, "_nav_buttons", {}).items():
            on = vid == highlight
            try:
                btn.configure(fg_color=th.selected_bg if on else "transparent",
                              text_color=th.accent if on else th.text_sub)
            except Exception:
                pass

    # ═════════════════════════ navigation ════════════════════════
    def switch_view(self, view_id: str, payload=None):
        if self.view is not None:
            try:
                self.view.flush()
            except Exception:
                pass
            self._cleanup_draft()
            try:
                self.view.destroy()
            except Exception:
                pass
            self.view = None

        # imports are local so the window opens fast and views stay independent
        from .views.home import HomeView
        from .views.editor import EditorView
        from .views.appearance import AppearanceView
        from .views.settings import SettingsView
        from .views.info import GuideView, AboutView, TrashView

        self._current_view = view_id
        self._update_nav_selection(view_id)
        if view_id == "editor":
            view = EditorView(self.stage, self, payload)
        else:
            cls = {"home": HomeView, "appearance": AppearanceView, "settings": SettingsView,
                   "trash": TrashView, "guide": GuideView, "about": AboutView}.get(view_id, HomeView)
            view = cls(self.stage, self)
        view.grid(row=0, column=0, sticky="nsew")
        self.view = view

    # compat alias used by older code / tests
    def _render_overview_view(self):
        self.switch_view("home")

    def toast(self, text: str, kind: str = "info", ms: int = 2600):
        self.toast_mgr.show(text, kind, ms)

    # ═════════════════════════ shortcuts ═════════════════════════
    def _bind_shortcuts(self):
        def guard(fn):
            def run(e=None):
                if self._capturing_key:
                    return None
                fn()
                return "break"
            return run
        self.bind("<Control-n>", guard(self._create_new_script))
        self.bind("<Control-o>", guard(self._import_file))
        self.bind("<Control-comma>", guard(lambda: self.switch_view("settings")))
        self.bind("<Control-f>", guard(self._focus_search))

    def _focus_search(self):
        fn = getattr(self.view, "focus_search", None)
        if fn:
            fn()
        elif self._current_view != "home":
            self.switch_view("home")

    # ═════════════════════════ script actions ════════════════════
    def _create_new_script(self):
        new_sc = {
            "title": "New Script",
            "description": "",
            "raw_content": ("## Welcome\n[CUE: Smile and make eye contact]\n"
                            "Hello everyone, and thank you for joining today.\n\n"
                            "## Main point\n[CUE: Next slide]\n"
                            "Today I'll walk you through the key ideas.\n"),
            "tags": [],
        }
        self.script_manager.save_script(new_sc)
        self._draft_ids.add(new_sc["id"])
        self._draft_template = (new_sc["title"], new_sc["raw_content"])
        self.switch_view("editor", new_sc)

    def _cleanup_draft(self):
        """Silently drop a brand-new script the user never touched."""
        for sid in list(self._draft_ids):
            sc = self.script_manager.get_script(sid)
            if sc is None:
                self._draft_ids.discard(sid)
                continue
            if (sc.get("title"), sc.get("raw_content")) == getattr(self, "_draft_template", None):
                if self._current_view != "editor" or not getattr(self.view, "script", None) is sc:
                    self.script_manager.base_dir.joinpath(f"{sid}.json").unlink(missing_ok=True)
                    self._draft_ids.discard(sid)
            else:
                self._draft_ids.discard(sid)

    def _delete_script(self, script_data: dict):
        title = script_data.get("title", "this script")
        if config.get("confirm_delete", True):
            if not messagebox.askyesno(
                    "Delete script", f"Move “{title}” to Recently deleted?\n\nYou can restore it for 30 days.",
                    icon="warning", parent=self):
                return
        if self.script_manager.delete_script(script_data.get("id")):
            self.toast(f"“{title}” moved to Recently deleted", "info")
        else:
            self.toast("Could not delete the script", "error")
        self.switch_view("home")

    def _import_file(self):
        from tkinter import filedialog
        f = filedialog.askopenfilename(
            parent=self, title="Import a script",
            filetypes=[("Scripts & documents", "*.md *.markdown *.txt *.docx *.pdf"),
                       ("Markdown / text", "*.md *.markdown *.txt"), ("Word", "*.docx"), ("PDF", "*.pdf"),
                       ("All files", "*.*")])
        if not f:
            return
        sc = self.script_manager.import_from_file(f)
        if sc:
            self.toast(f"Imported “{sc['title']}”", "success")
            self.switch_view("editor", sc)
        else:
            messagebox.showerror("Import failed", self.script_manager.last_error or "Could not import that file.", parent=self)

    def _import_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(parent=self, title="Import all scripts from a folder")
        if not folder:
            return
        imported = self.script_manager.import_from_folder(folder)
        if imported:
            self.toast(f"Imported {len(imported)} script{'s' if len(imported) != 1 else ''}", "success")
        else:
            self.toast("No .md, .txt, .docx or .pdf files found in that folder", "warning", 3500)
        self.switch_view("home")

    def _open_github(self):
        try:
            webbrowser.open(GITHUB_URL)
        except Exception:
            pass

    # ═════════════════════════ presenter ═════════════════════════
    def launch_presenter(self, script_data: dict):
        """Open the reader. The library stays where it is — nothing is hidden or trapped."""
        try:
            if script_data.get("id"):
                fresh = self.script_manager.get_script(script_data["id"])
                if fresh:
                    script_data = fresh
                config.set("last_script_id", script_data["id"])
        except Exception:
            pass
        if self.reader_window is not None:
            try:
                if self.reader_window.winfo_exists():
                    self.reader_window._on_close()
            except Exception:
                pass
            self.reader_window = None
        try:
            self.reader_window = PresenterReaderWindow(self, script_data)
        except Exception as e:                      # never leave the user with a dead button
            self.reader_window = None
            messagebox.showerror("Could not open the reader", f"{type(e).__name__}: {e}", parent=self)
            return
        self._minimized_for_reader = True
        self.withdraw()

    _launch_presenter = launch_presenter          # alias kept for the onboarding flow

    def on_reader_closed(self, reader):
        if self.reader_window is reader:
            self.reader_window = None
        if self._minimized_for_reader:
            self._minimized_for_reader = False
            try:
                self.deiconify()
                self.lift()
            except Exception:
                pass
        if self._current_view == "home" and self.view is not None:
            try:
                self.view.refresh_list()          # progress badges update
            except Exception:
                pass

    def _reader_alive(self):
        r = self.reader_window
        try:
            return r if r is not None and r.winfo_exists() else None
        except Exception:
            return None

    def refresh_reader(self, what: str = "visual"):
        """Push changed settings into an open reader immediately."""
        r = self._reader_alive()
        if not r:
            return
        try:
            if what == "visual":
                r.apply_settings(rerender=True)
            elif what == "pin":
                r.set_pinned(bool(config.get("always_on_top", True)))
            elif what == "taskbar":
                r.apply_taskbar_visibility()
            elif what == "capture":
                r.apply_capture_exclusion()
            elif what == "keys":
                r.rebind_keys()
            elif what == "theme":
                r.rebuild()
        except Exception:
            pass

    # ═════════════════════════ theme ═════════════════════════════
    def apply_theme(self, theme_key: str):
        config.set("theme", theme_key)
        self.theme = get_theme(theme_key)
        ctk.set_appearance_mode("dark" if self.theme.dark else "light")
        self.configure(fg_color=self.theme.bg)
        view_id, payload = self._current_view, None
        if view_id == "editor":
            try:
                self.view.flush()
                payload = self.view.script
            except Exception:
                view_id = "home"
        if self.view is not None:
            try:
                self.view.destroy()
            except Exception:
                pass
            self.view = None
        for w in list(self.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass
        self._sidebar_collapsed = None
        self._build_skeleton()
        self.toast_mgr = Toast(self, self.theme)
        self.switch_view(view_id, payload)
        self.refresh_reader("theme")
        self.after(50, lambda: ws.set_dark_titlebar(ws.top_level_hwnd(self.winfo_id()), self.theme.dark))

    _set_theme = apply_theme                       # compat with older callers/tests

    # ═════════════════════════ tray ══════════════════════════════
    def _poll_tray(self):
        try:
            while True:
                cmd = self.tray_queue.get_nowait()
                self._handle_tray(cmd)
        except queue.Empty:
            pass
        except Exception:
            pass
        try:
            self.after(250, self._poll_tray)
        except Exception:
            pass

    def _handle_tray(self, cmd: str):
        if cmd == "show":
            self.deiconify()
            self.lift()
            self.focus_force()
        elif cmd == "new":
            self.deiconify()
            self._create_new_script()
        elif cmd == "present_last":
            sc = self.script_manager.get_script(config.get("last_script_id", ""))
            if not sc:
                items = self.script_manager.list_scripts()
                sc = items[0] if items else None
            if sc:
                self.launch_presenter(sc)
        elif cmd == "quit":
            self._on_app_close()

    # ═════════════════════════ close ═════════════════════════════
    def _on_app_close(self):
        try:
            if self.view is not None:
                self.view.flush()
        except Exception:
            pass
        self._cleanup_draft()
        r = self._reader_alive()
        if r:
            try:
                r._on_close()
            except Exception:
                pass
        self._save_main_geometry()
        config.save()
        try:
            tray = getattr(self, "_tray_manager", None)
            if tray:
                tray.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
