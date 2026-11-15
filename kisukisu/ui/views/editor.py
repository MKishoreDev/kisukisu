# -*- coding: utf-8 -*-
"""Kisukisu — Script editor: insert helpers, syntax tint, find, outline, autosave, live stats."""

import re
import time
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

from . import BaseView
from ..components import (
    ui_font, make_pill_button, make_icon_button, make_entry, resolve_font, style_menu, Tooltip,
)
from ..themes import mix
from ...core.config import config
from ...core.document_parser import DocumentParser, estimate_minutes, format_minutes, word_count

_INLINE = re.compile(r"\[[^\]\n]{1,80}\]")


class EditorView(BaseView):
    def __init__(self, parent, app, script):
        super().__init__(parent, app)
        self.script = script
        self._dirty = False
        self._save_job = None
        self._hl_job = None
        self._outline_job = None
        self._outline_visible = None
        self._find_matches = []
        self._find_i = -1
        self.title_var = tk.StringVar(value=script.get("title", ""))
        self.editor_size = 13
        config.set("last_script_id", script.get("id", ""))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_header()
        self._build_tools()
        self._build_find_bar()
        self._build_body()
        self._build_footer()
        self._on_text_change(initial=True)
        self.txt.focus_set()
        self.bind("<Configure>", self._on_resize, add="+")

    # ── header ──────────────────────────────────────────────────
    def _build_header(self):
        th = self.theme
        h = ctk.CTkFrame(self, fg_color=th.card_bg, corner_radius=0, height=58)
        h.grid(row=0, column=0, sticky="ew")
        h.grid_propagate(False)
        h.grid_columnconfigure(1, weight=1)
        h.grid_rowconfigure(0, weight=1)
        make_pill_button(h, "← Back", lambda: self.app.switch_view("home"), th, width=76, height=34).grid(row=0, column=0, padx=(16, 8), pady=12)
        self.entry_title = ctk.CTkEntry(h, textvariable=self.title_var, fg_color="transparent", border_width=0,
                                        text_color=th.text_main, font=ui_font(16, "bold"), height=34,
                                        placeholder_text="Untitled script", placeholder_text_color=th.text_muted)
        self.entry_title.grid(row=0, column=1, sticky="ew", pady=12)
        self.title_var.trace_add("write", lambda *_: self._mark_dirty())
        right = ctk.CTkFrame(h, fg_color="transparent")
        right.grid(row=0, column=2, padx=(8, 16))
        self.lbl_status = ctk.CTkLabel(right, text="Saved ✓", font=ui_font(11), text_color=th.success)
        self.lbl_status.pack(side="left", padx=(0, 10))
        make_pill_button(right, "Export", self._export, th, width=70, height=34).pack(side="left", padx=3)
        make_pill_button(right, "▶  Present", self._present, th, primary=True, width=104, height=34,
                         tooltip="Save and open the reader  (Ctrl+Enter)").pack(side="left", padx=3)

    def _build_tools(self):
        th = self.theme
        bar = ctk.CTkFrame(self, fg_color=th.bg, corner_radius=0, height=48)
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 0))
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left")
        make_pill_button(left, "+ Section", lambda: self._insert("\n## New section\n[CUE: ]\n", 2), th, width=92, height=30, small=True,
                         tooltip="Insert a section heading").pack(side="left", padx=(0, 5))
        make_pill_button(left, "+ Cue", lambda: self._insert("[CUE: ]", 1), th, width=70, height=30, small=True,
                         tooltip="Insert a reminder like [CUE: Next slide]").pack(side="left", padx=5)
        make_pill_button(left, "+ Pause", lambda: self._insert("[PAUSE]"), th, width=78, height=30, small=True).pack(side="left", padx=5)
        make_icon_button(left, "↶", lambda: self._undo(), th, 30, "Undo  (Ctrl+Z)").pack(side="left", padx=(10, 2))
        make_icon_button(left, "↷", lambda: self._redo(), th, 30, "Redo  (Ctrl+Y)").pack(side="left", padx=2)
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right")
        make_icon_button(right, "A−", lambda: self._font(-1), th, 30, "Smaller editor text").pack(side="left", padx=2)
        make_icon_button(right, "A+", lambda: self._font(+1), th, 30, "Bigger editor text").pack(side="left", padx=2)
        make_pill_button(right, "Find", self.toggle_find, th, width=60, height=30, small=True, tooltip="Find  (Ctrl+F)").pack(side="left", padx=(8, 0))

    def _build_find_bar(self):
        th = self.theme
        self.find_bar = ctk.CTkFrame(self, fg_color=th.card_bg, corner_radius=10, border_width=1, border_color=th.border)
        self.find_var = tk.StringVar()
        self.find_entry = make_entry(self.find_bar, th, 220, self.find_var, "Find in script")
        self.find_entry.pack(side="left", padx=(10, 6), pady=8)
        self.find_var.trace_add("write", lambda *_: self._find_update())
        self.lbl_find = ctk.CTkLabel(self.find_bar, text="", font=ui_font(11), text_color=th.text_sub, width=70)
        self.lbl_find.pack(side="left")
        make_pill_button(self.find_bar, "↑", lambda: self._find_step(-1), th, width=34, height=28, small=True).pack(side="left", padx=2)
        make_pill_button(self.find_bar, "↓", lambda: self._find_step(1), th, width=34, height=28, small=True).pack(side="left", padx=2)
        make_pill_button(self.find_bar, "✕", self.toggle_find, th, width=34, height=28, small=True).pack(side="left", padx=(2, 10))
        self.find_entry.bind("<Return>", lambda e: self._find_step(1))
        self.find_entry.bind("<Escape>", lambda e: self.toggle_find())
        self._find_open = False

    # ── body ────────────────────────────────────────────────────
    def _build_body(self):
        th = self.theme
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=20, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.body = body

        wrap = ctk.CTkFrame(body, fg_color=th.card_bg, corner_radius=12, border_width=1, border_color=th.border)
        wrap.grid(row=0, column=0, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        self.txt = tk.Text(
            wrap, wrap="word", bg=th.card_bg, fg=th.text_main, insertbackground=th.accent,
            selectbackground=th.selected_bg, selectforeground=th.text_main, bd=0, relief="flat",
            highlightthickness=0, undo=True, maxundo=200, padx=22, pady=18, spacing1=2, spacing3=4,
            font=(resolve_font(), self.editor_size))
        self.txt.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        sb = ctk.CTkScrollbar(wrap, command=self.txt.yview, button_color=th.border, button_hover_color=th.text_muted)
        sb.grid(row=0, column=1, sticky="ns", padx=(0, 3), pady=6)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.insert("1.0", self.script.get("raw_content", ""))
        self.txt.edit_reset()

        self.txt.tag_configure("h", foreground=th.accent, font=(resolve_font(), self.editor_size, "bold"))
        self.txt.tag_configure("cue", foreground=th.cue_color, background=th.selected_bg)
        self.txt.tag_configure("meta", foreground=th.text_muted)
        self.txt.tag_configure("find", background=mix(th.card_bg, th.warning, 0.45))
        self.txt.tag_configure("find_cur", background=th.warning, foreground="#000000")
        self.txt.tag_raise("find")
        self.txt.tag_raise("find_cur")
        self.txt.bind("<<Modified>>", self._on_modified)
        self.txt.bind("<Control-s>", lambda e: self._save_now() or "break")
        self.txt.bind("<Control-y>", lambda e: self._redo() or "break")
        self.txt.bind("<Control-Return>", lambda e: self._present() or "break")
        self.txt.bind("<Control-f>", lambda e: self.toggle_find() or "break")

        # outline panel (only when the window is wide enough)
        self.outline = ctk.CTkFrame(body, fg_color=th.card_bg, corner_radius=12, border_width=1, border_color=th.border, width=230)
        self.outline.grid_propagate(False)
        ctk.CTkLabel(self.outline, text="OUTLINE", font=ui_font(10, "bold"), text_color=th.text_muted
                     ).pack(anchor="w", padx=14, pady=(12, 4))
        self.outline_list = ctk.CTkScrollableFrame(self.outline, fg_color="transparent", corner_radius=0)
        self.outline_list.pack(fill="both", expand=True, padx=4, pady=(0, 6))

    def _build_footer(self):
        th = self.theme
        f = ctk.CTkFrame(self, fg_color=th.sidebar_bg, corner_radius=0, height=32)
        f.grid(row=4, column=0, sticky="ew")
        f.grid_propagate(False)
        self.lbl_stats = ctk.CTkLabel(f, text="", font=ui_font(11), text_color=th.text_sub)
        self.lbl_stats.pack(side="left", padx=20)
        ctk.CTkLabel(f, text="Plain text works too — start a line with ##  for a new section.", font=ui_font(11),
                     text_color=th.text_muted).pack(side="right", padx=20)

    def _on_resize(self, e):
        want = e.width >= 1000
        if want != self._outline_visible:
            self._outline_visible = want
            if want:
                self.body.grid_columnconfigure(1, weight=0)
                self.outline.grid(row=0, column=1, sticky="ns", padx=(12, 0))
                self._refresh_outline()
            else:
                self.outline.grid_remove()

    # ── editing ─────────────────────────────────────────────────
    def _insert(self, text, caret_back=0):
        t = self.txt
        t.insert("insert", text)
        if caret_back:
            t.mark_set("insert", f"insert - {caret_back}c")
        t.focus_set()
        t.see("insert")
        self._on_text_change()

    def _undo(self):
        try:
            self.txt.edit_undo()
        except tk.TclError:
            pass

    def _redo(self):
        try:
            self.txt.edit_redo()
        except tk.TclError:
            pass

    def _font(self, d):
        self.editor_size = max(10, min(24, self.editor_size + d))
        self.txt.configure(font=(resolve_font(), self.editor_size))
        self.txt.tag_configure("h", font=(resolve_font(), self.editor_size, "bold"))

    def _on_modified(self, _e=None):
        if self.txt.edit_modified():
            self.txt.edit_modified(False)
            self._on_text_change()

    def _on_text_change(self, initial=False):
        self._update_stats()
        self._schedule(self, "_hl_job", 120, self._highlight)
        if self._outline_visible:
            self._schedule(self, "_outline_job", 400, self._refresh_outline)
        if not initial:
            self._mark_dirty()

    @staticmethod
    def _schedule(obj, attr, ms, fn):
        job = getattr(obj, attr, None)
        if job:
            try:
                obj.after_cancel(job)
            except Exception:
                pass
        setattr(obj, attr, obj.after(ms, fn))

    def _content(self) -> str:
        return self.txt.get("1.0", "end-1c")

    def _update_stats(self):
        text = self._content()
        words = word_count(text)
        secs = len(DocumentParser.parse_markdown_or_txt(text, "x")) if text.strip() else 0
        mins = format_minutes(estimate_minutes(words, config.get("reading_wpm", 150)))
        self.lbl_stats.configure(text=f"{words:,} words   ·   ~{mins} to read   ·   {secs} section{'s' if secs != 1 else ''}")

    def _highlight(self):
        self._hl_job = None
        t = self.txt
        for tag in ("h", "cue", "meta"):
            t.tag_remove(tag, "1.0", "end")
        for i, line in enumerate(self._content().split("\n"), 1):
            s = line.lstrip()
            if s.startswith("##"):
                t.tag_add("h", f"{i}.0", f"{i}.end")
            elif s.startswith(("**SAY", "**ACTION", "**On screen", "---")):
                t.tag_add("meta", f"{i}.0", f"{i}.end")
            for m in _INLINE.finditer(line):
                t.tag_add("cue", f"{i}.{m.start()}", f"{i}.{m.end()}")

    def _refresh_outline(self):
        self._outline_job = None
        if not self._outline_visible:
            return
        for w in self.outline_list.winfo_children():
            w.destroy()
        th = self.theme
        for i, line in enumerate(self._content().split("\n"), 1):
            if line.lstrip().startswith("##"):
                title = line.lstrip("# ").strip() or "Untitled section"
                ctk.CTkButton(self.outline_list, text=title[:34] + ("…" if len(title) > 34 else ""), anchor="w", height=30,
                              corner_radius=8, fg_color="transparent", hover_color=th.hover_bg, text_color=th.text_sub,
                              font=ui_font(12), command=lambda n=i: self._jump(n)).pack(fill="x", pady=1)

    def _jump(self, line):
        self.txt.mark_set("insert", f"{line}.0")
        self.txt.see(f"{line}.0")
        self.txt.yview(f"{line}.0 - 2 lines")
        self.txt.focus_set()

    # ── find ────────────────────────────────────────────────────
    def toggle_find(self):
        if self._find_open:
            self.find_bar.place_forget()
            self._find_open = False
            self.txt.tag_remove("find", "1.0", "end")
            self.txt.tag_remove("find_cur", "1.0", "end")
            self.txt.focus_set()
        else:
            self.find_bar.place(relx=1.0, x=-30, y=118, anchor="ne")
            self.find_bar.lift()
            self._find_open = True
            self.find_entry.focus_set()
            self._find_update()

    def _find_update(self):
        t = self.txt
        t.tag_remove("find", "1.0", "end")
        t.tag_remove("find_cur", "1.0", "end")
        self._find_matches, self._find_i = [], -1
        q = self.find_var.get()
        if not q:
            self.lbl_find.configure(text="")
            return
        pos = "1.0"
        while True:
            idx = t.search(q, pos, stopindex="end", nocase=True)
            if not idx:
                break
            end = f"{idx}+{len(q)}c"
            t.tag_add("find", idx, end)
            self._find_matches.append((idx, end))
            pos = end
        self.lbl_find.configure(text=f"{len(self._find_matches)} found" if self._find_matches else "No match")
        if self._find_matches:
            self._find_step(1)

    def _find_step(self, d):
        if not self._find_matches:
            return
        self._find_i = (self._find_i + d) % len(self._find_matches)
        idx, end = self._find_matches[self._find_i]
        self.txt.tag_remove("find_cur", "1.0", "end")
        self.txt.tag_add("find_cur", idx, end)
        self.txt.see(idx)
        self.lbl_find.configure(text=f"{self._find_i + 1} / {len(self._find_matches)}")

    # ── saving ──────────────────────────────────────────────────
    def _mark_dirty(self):
        self._dirty = True
        th = self.theme
        if config.get("autosave", True):
            self.lbl_status.configure(text="Saving…", text_color=th.warning)
            self._schedule(self, "_save_job", 600, self._save_now)
        else:
            self.lbl_status.configure(text="Unsaved changes", text_color=th.warning)

    def _save_now(self):
        self._save_job = None
        if not self._dirty:
            self.lbl_status.configure(text="Saved ✓", text_color=self.theme.success)
            return
        try:
            self.script["title"] = self.title_var.get().strip() or "Untitled Script"
            self.script["raw_content"] = self._content()
            ok = self.app.script_manager.save_script(self.script)
        except Exception:
            ok = False
        if ok:
            self._dirty = False
            self.lbl_status.configure(text=f"Saved ✓  {time.strftime('%H:%M')}", text_color=self.theme.success)
        else:
            self.lbl_status.configure(text="Could not save!", text_color=self.theme.error)
        return ok

    # alias used by older callers/tests
    def flush(self):
        if self._dirty:
            self._save_now()

    def _present(self):
        self._dirty = True
        self._save_now()
        self.app.launch_presenter(self.script)

    def _export(self):
        self._dirty = True
        self._save_now()
        dest = filedialog.asksaveasfilename(
            parent=self.app, title="Export script", initialfile=self.script.get("title", "script"),
            defaultextension=".md", filetypes=[("Markdown", "*.md"), ("Plain text", "*.txt"), ("JSON", "*.json")])
        if dest:
            ok = self.app.script_manager.export_script(self.script, dest)
            self.app.toast("Exported" if ok else "Export failed", "success" if ok else "error")
