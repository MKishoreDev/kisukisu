# -*- coding: utf-8 -*-
"""Kisukisu — Home: greeting, continue card, search / sort / tag filters, script cards."""

import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from . import ScrollPage
from ..components import (
    ui_font, make_pill_button, make_card, make_badge, make_option_menu, bind_wrap, style_menu,
    make_search_entry,
)
from ...core.config import config
from ...core.document_parser import estimate_minutes, format_minutes

SORTS = {"Recently edited": "recent", "Title A–Z": "title", "Longest first": "longest"}


def _bind_tree(widget, seq, fn, skip=(ctk.CTkButton,)):
    """Bind *fn* on a widget and all descendants (except buttons) so the whole card is clickable."""
    if not isinstance(widget, skip):
        try:
            widget.bind(seq, fn, add="+")
        except Exception:
            pass
    for child in widget.winfo_children():
        _bind_tree(child, seq, fn, skip)


class HomeView(ScrollPage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.state = app.home_state
        self.search_var = tk.StringVar(value=self.state["q"])
        self._search_job = None
        self._build_header()
        self._build_continue()
        self._build_filters()
        self.list_box = ctk.CTkFrame(self.content, fg_color="transparent")
        self.list_box.pack(fill="x", pady=(6, 0))
        self.list_box.grid_columnconfigure(0, weight=1)
        self.refresh_list()

    # ── header ──────────────────────────────────────────────────
    def _build_header(self):
        th = self.theme
        h = datetime.datetime.now().hour
        greet = "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"
        self.head = ctk.CTkFrame(self.content, fg_color="transparent")
        self.head.pack(fill="x")
        self.head.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(self.head, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text=f"{greet}.", font=ui_font(12), text_color=th.accent_light, anchor="w").pack(anchor="w")
        ctk.CTkLabel(left, text="What would you like to present today?", font=ui_font(22, "bold"),
                     text_color=th.text_main, anchor="w", justify="left").pack(anchor="w")

        self.actions = ctk.CTkFrame(self.head, fg_color="transparent")
        self.actions.grid(row=0, column=1, sticky="e", padx=(12, 0))
        make_pill_button(self.actions, "+ New script", self.app._create_new_script, th, primary=True,
                         width=118, height=38).pack(side="left", padx=3)
        self.btn_import = make_pill_button(self.actions, "Import  ▾", self._import_menu, th, width=100, height=38)
        self.btn_import.pack(side="left", padx=3)
        self._narrow = False
        self.head.bind("<Configure>", self._head_resize, add="+")

    def _head_resize(self, e):
        narrow = e.width < 640
        if narrow != self._narrow:
            self._narrow = narrow
            if narrow:
                self.actions.grid(row=1, column=0, sticky="w", padx=0, pady=(10, 0))
            else:
                self.actions.grid(row=0, column=1, sticky="e", padx=(12, 0), pady=0)

    def _import_menu(self):
        m = style_menu(tk.Menu(self, tearoff=0), self.theme)
        m.add_command(label="Import a file…   (.md .txt .docx .pdf)", command=self.app._import_file)
        m.add_command(label="Import a whole folder…", command=self.app._import_folder)
        try:
            m.tk_popup(self.btn_import.winfo_rootx(), self.btn_import.winfo_rooty() + self.btn_import.winfo_height() + 4)
        finally:
            m.grab_release()

    # ── continue card ───────────────────────────────────────────
    def _build_continue(self):
        th = self.theme
        sc = self.app.script_manager.get_script(config.get("last_script_id", "") or "")
        if not sc:
            return
        pct = int(float(sc.get("progress", 0) or 0) * 100)
        card = ctk.CTkFrame(self.content, fg_color=th.selected_bg, corner_radius=14, border_width=1,
                            border_color=th.accent)
        card.pack(fill="x", pady=(18, 4))
        card.grid_columnconfigure(0, weight=1)
        txt = ctk.CTkFrame(card, fg_color="transparent")
        txt.grid(row=0, column=0, sticky="ew", padx=18, pady=14)
        ctk.CTkLabel(txt, text="CONTINUE WHERE YOU LEFT OFF", font=ui_font(10, "bold"),
                     text_color=th.accent_light, anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt, text=sc.get("title", "Script"), font=ui_font(16, "bold"), text_color=th.text_main,
                     anchor="w").pack(anchor="w", pady=(2, 0))
        sub = f"{pct}% read · " if pct > 2 else ""
        ctk.CTkLabel(txt, text=f"{sub}{sc.get('word_count', 0):,} words", font=ui_font(11),
                     text_color=th.text_sub, anchor="w").pack(anchor="w")
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=0, column=1, padx=16)
        make_pill_button(btns, "Resume" if pct > 2 else "Present", lambda s=sc: self.app.launch_presenter(s),
                         th, primary=True, width=96, height=36).pack(side="left", padx=3)
        make_pill_button(btns, "Edit", lambda s=sc: self.app.switch_view("editor", s), th, width=64,
                         height=36).pack(side="left", padx=3)

    # ── filters ─────────────────────────────────────────────────
    def _build_filters(self):
        th = self.theme
        bar = ctk.CTkFrame(self.content, fg_color="transparent")
        bar.pack(fill="x", pady=(18, 6))
        bar.grid_columnconfigure(0, weight=1)
        self.search = make_search_entry(bar, th, "Search titles, notes and tags…  (Ctrl+F)", textvariable=self.search_var)
        self.search.grid(row=0, column=0, sticky="ew")
        self.search_var.trace_add("write", self._on_search)
        inv = {v: k for k, v in SORTS.items()}
        make_option_menu(bar, th, list(SORTS), self._on_sort, inv.get(self.state["sort"], "Recently edited"),
                         width=160).grid(row=0, column=1, padx=(10, 0))

        tags = self.app.script_manager.all_tags()[:7]
        if tags:
            row = ctk.CTkFrame(self.content, fg_color="transparent")
            row.pack(fill="x", pady=(2, 4))
            self._chip(row, "All", None)
            for t in tags:
                self._chip(row, t, t)

    def _chip(self, parent, text, tag):
        th = self.theme
        on = self.state["tag"] == tag
        ctk.CTkButton(parent, text=text, height=26, width=10, corner_radius=13,
                      fg_color=th.accent if on else th.pill_bg, hover_color=th.accent_hover if on else th.pill_hover,
                      text_color=th.on_accent if on else th.text_sub, font=ui_font(11, "bold"),
                      command=lambda: self._set_tag(tag)).pack(side="left", padx=(0, 6))

    def _set_tag(self, tag):
        self.state["tag"] = None if self.state["tag"] == tag else tag
        self.app.switch_view("home")

    def _on_sort(self, label):
        self.state["sort"] = SORTS.get(label, "recent")
        self.refresh_list()

    def _on_search(self, *_):
        self.state["q"] = self.search_var.get()
        if self._search_job:
            try:
                self.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.after(180, self.refresh_list)

    def focus_search(self):
        try:
            self.search.focus_set()
        except Exception:
            pass

    # ── list ────────────────────────────────────────────────────
    def refresh_list(self):
        self._search_job = None
        try:
            if not self.list_box.winfo_exists():
                return
        except Exception:
            return
        for w in self.list_box.winfo_children():
            w.destroy()
        q = self.state["q"].strip()
        scripts = self.app.script_manager.list_scripts(q, self.state["tag"], self.state["sort"])
        th = self.theme
        total = len(self.app.script_manager.list_scripts())
        label = f"Your scripts ({total})" if not q and not self.state["tag"] else f"{len(scripts)} result{'s' if len(scripts) != 1 else ''}"
        ctk.CTkLabel(self.list_box, text=label, font=ui_font(13, "bold"), text_color=th.text_sub,
                     anchor="w").grid(row=0, column=0, sticky="w", pady=(8, 4))
        if not scripts:
            self._empty(q or self.state["tag"])
            return
        for i, s in enumerate(scripts):
            self._card(s, i + 1)

    def _empty(self, filtered):
        th = self.theme
        box = ctk.CTkFrame(self.list_box, fg_color="transparent")
        box.grid(row=1, column=0, pady=50)
        title = "No matching scripts" if filtered else "Your library is empty"
        sub = "Try a different search or clear the tag filter." if filtered else \
              "Create a script, or import a Word, PDF, Markdown or text file."
        ctk.CTkLabel(box, text="கிசுகிசு", font=ui_font(26, "bold"), text_color=th.accent).pack()
        ctk.CTkLabel(box, text=title, font=ui_font(17, "bold"), text_color=th.text_main).pack(pady=(4, 0))
        ctk.CTkLabel(box, text=sub, font=ui_font(12), text_color=th.text_sub).pack(pady=(2, 14))
        if not filtered:
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack()
            make_pill_button(r, "+ New script", self.app._create_new_script, th, primary=True, width=120, height=38).pack(side="left", padx=4)
            make_pill_button(r, "Import file", self.app._import_file, th, width=110, height=38).pack(side="left", padx=4)

    def _card(self, s, row):
        th = self.theme
        card = make_card(self.list_box, th, corner_radius=14)
        card.grid(row=row, column=0, sticky="ew", pady=5)
        card.grid_columnconfigure(1, weight=1)
        card.configure(cursor="hand2")
        ctk.CTkFrame(card, fg_color=th.accent, width=4, corner_radius=2).grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 0), pady=10)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", padx=(14, 8), pady=(12, 12))
        info.grid_columnconfigure(0, weight=1)
        trow = ctk.CTkFrame(info, fg_color="transparent")
        trow.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(trow, text=s.get("title", "Untitled"), font=ui_font(15, "bold"), text_color=th.text_main,
                     anchor="w").pack(side="left")
        for tag in s.get("tags", [])[:3]:
            make_badge(trow, tag, th).pack(side="left", padx=(6, 0))

        secs = s.get("sections", [])
        preview = (secs[0].get("say", "") if secs else "") or s.get("description", "")
        preview = " ".join(preview.split())[:150]
        if preview:
            lp = ctk.CTkLabel(info, text=preview + ("…" if len(preview) >= 150 else ""), font=ui_font(12),
                              text_color=th.text_sub, anchor="w", justify="left")
            lp.grid(row=1, column=0, sticky="ew", pady=(3, 0))
            bind_wrap(lp, info, margin=6)

        words = s.get("word_count", len(s.get("raw_content", "").split()))
        try:
            when = datetime.datetime.fromtimestamp(s.get("updated_at", 0)).strftime("%b %d, %Y")
        except Exception:
            when = ""
        bits = [f"{len(secs)} section{'s' if len(secs) != 1 else ''}", f"{words:,} words",
                f"~{format_minutes(estimate_minutes(words, config.get('reading_wpm', 150)))}", when]
        pct = int(float(s.get("progress", 0) or 0) * 100)
        if 2 < pct < 98:
            bits.append(f"{pct}% read")
        ctk.CTkLabel(info, text="  ·  ".join(b for b in bits if b), font=ui_font(11), text_color=th.text_muted,
                     anchor="w").grid(row=2, column=0, sticky="w", pady=(4, 0))

        acts = ctk.CTkFrame(card, fg_color="transparent")
        acts.grid(row=0, column=2, padx=(0, 14), pady=12, sticky="e")
        make_pill_button(acts, "Present", lambda sc=s: self.app.launch_presenter(sc), th, primary=True,
                         width=84, height=34).pack(side="left", padx=3)
        make_pill_button(acts, "Edit", lambda sc=s: self.app.switch_view("editor", sc), th, width=60, height=34).pack(side="left", padx=3)
        more = ctk.CTkButton(acts, text="⋯", width=34, height=34, corner_radius=17, fg_color=th.pill_bg,
                             hover_color=th.pill_hover, text_color=th.text_sub, font=ui_font(15, "bold"))
        more.configure(command=lambda sc=s, b=more: self._more_menu(sc, b))
        more.pack(side="left", padx=3)

        def open_edit(_e=None, sc=s):
            self.app.switch_view("editor", sc)

        _bind_tree(card, "<Button-1>", open_edit)
        _bind_tree(card, "<Enter>", lambda e: card.configure(border_color=th.accent))
        _bind_tree(card, "<Leave>", lambda e: card.configure(border_color=th.border))

        state = {"narrow": False}

        def on_cfg(e):
            narrow = e.width < 600
            if narrow != state["narrow"]:
                state["narrow"] = narrow
                if narrow:
                    acts.grid(row=1, column=1, columnspan=2, sticky="w", padx=(14, 0), pady=(0, 12))
                else:
                    acts.grid(row=0, column=2, columnspan=1, sticky="e", padx=(0, 14), pady=12)
        card.bind("<Configure>", on_cfg, add="+")

    def _more_menu(self, s, btn):
        m = style_menu(tk.Menu(self, tearoff=0), self.theme)
        m.add_command(label="Duplicate", command=lambda: self._duplicate(s))
        m.add_command(label="Export…", command=lambda: self._export(s))
        m.add_separator()
        m.add_command(label="Delete", command=lambda: self.app._delete_script(s))
        try:
            m.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height() + 4)
        finally:
            m.grab_release()

    def _duplicate(self, s):
        if self.app.script_manager.duplicate_script(s.get("id")):
            self.app.toast("Script duplicated", "success")
            self.refresh_list()

    def _export(self, s):
        dest = filedialog.asksaveasfilename(
            parent=self.app, title="Export script", initialfile=s.get("title", "script"),
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Plain text", "*.txt"), ("JSON", "*.json")])
        if dest:
            ok = self.app.script_manager.export_script(s, dest)
            self.app.toast("Exported" if ok else "Export failed", "success" if ok else "error")
