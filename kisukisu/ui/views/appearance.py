# -*- coding: utf-8 -*-
"""Kisukisu — Appearance studio: themes, custom colours, typography — with a live preview."""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, colorchooser
import customtkinter as ctk

from . import ScrollPage
from ..components import (
    ui_font, make_pill_button, make_section, make_entry, make_segmented, LabeledSlider, SwitchRow,
    font_choices, resolve_font, bind_wrap,
)
from ..themes import (
    THEMES, get_theme, save_custom_theme, custom_theme_values, normalize_hex, is_hex, mix,
    export_theme, import_theme,
)
from ...core.config import config

ACCENTS = [("Violet", "#8055E8"), ("Emerald", "#10B981"), ("Sky", "#0EA5E9"), ("Coral", "#F97316"),
           ("Rose", "#F43F5E"), ("Gold", "#F59E0B"), ("Cyan", "#06B6D4")]


class PreviewPane(ctk.CTkFrame):
    """A miniature reader that mirrors the real one (colours, font, spacing, focus, ruler)."""

    def __init__(self, parent, theme):
        super().__init__(parent, fg_color=theme.reader_bg, corner_radius=14, border_width=1, border_color=theme.border)
        self.theme = theme
        head = ctk.CTkFrame(self, fg_color=theme.card_bg, corner_radius=0, height=34)
        head.pack(fill="x", padx=1, pady=(1, 0))
        ctk.CTkLabel(head, text="Preview", font=ui_font(11, "bold"), text_color=theme.text_main).pack(side="left", padx=14, pady=6)
        ctk.CTkLabel(head, text="2 / 5  ·  38%", font=ui_font(11, "bold"), text_color=theme.accent_light).pack(side="right", padx=14)
        bar = ctk.CTkProgressBar(self, height=3, corner_radius=0, fg_color=theme.border_subtle, progress_color=theme.accent)
        bar.pack(fill="x", padx=1)
        bar.set(0.38)
        self.txt = tk.Text(self, height=11, wrap="word", bd=0, highlightthickness=0, cursor="arrow", takefocus=0,
                           bg=theme.reader_bg, fg=theme.reader_text, padx=22, pady=14)
        self.txt.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.ruler = tk.Frame(self.txt, bg=mix(theme.accent, theme.reader_bg, 0.35), height=1)
        self._fonts = {}
        self.refresh()

    def _font(self, key, **kw):
        f = self._fonts.get(key)
        if f is None:
            f = self._fonts[key] = tkfont.Font(root=self, **kw)
        else:
            f.configure(**kw)
        return f

    def refresh(self):
        th, t = self.theme, self.txt
        fam = resolve_font(config.get("font_family"))
        size = max(11, min(30, int(config.get("font_size", 24) * 0.7)))
        weight = config.get("font_weight", "normal")
        body = self._font("body", family=fam, size=size, weight=weight)
        bold = self._font("bold", family=fam, size=size, weight="bold")
        cue = self._font("cue", family=fam, size=max(9, size // 2 + 1), weight="bold")
        align = config.get("text_align", "left")
        focus = config.get("focus_mode", True)
        dim = mix(th.reader_text, th.reader_bg, 0.58)
        try:
            self.configure(fg_color=th.reader_bg)
            t.configure(bg=th.reader_bg, fg=th.reader_text, font=body, spacing2=int(config.get("line_spacing", 8) * 0.7))
            gap = int(config.get("paragraph_gap", 18) * 0.7)
            t.tag_configure("para", foreground=dim if focus else th.reader_text, spacing3=gap, justify=align, font=body)
            t.tag_configure("cur", foreground=th.reader_text)
            t.tag_configure("cue", font=cue, foreground=th.cue_color, background=th.selected_bg, justify=align, spacing3=gap // 2 + 2)
            t.tag_configure("inl", font=bold, foreground=th.cue_color, background=th.selected_bg)
            t.tag_configure("title", font=bold, foreground=th.accent, justify=align, spacing3=4)
            pad = max(10, min(int(config.get("reader_padding", 36) * 0.7), 60))
            t.configure(padx=pad)
            t.configure(state="normal")
            t.delete("1.0", "end")
            t.insert("end", "Welcome to Kisukisu\n", "title")
            t.insert("end", " ▸ NEXT SLIDE \n", "cue")
            t.insert("end", "This is the paragraph you are reading right now. ", ("para", "cur"))
            t.insert("end", "It stays bright.\n", ("para", "cur"))
            t.insert("end", "Everything else fades back, so your eyes always know where you are. ", "para")
            t.insert("end", "[SWITCH SLIDE]", ("para", "inl"))
            t.insert("end", "\n", "para")
            t.insert("end", "கிசுகிசு — உங்கள் சிறிய ரகசியம்.\n", "para")
            t.configure(state="disabled")
            if config.get("show_ruler", True):
                self.ruler.place(relx=0, rely=0.34, relwidth=1, height=1)
            else:
                self.ruler.place_forget()
        except Exception:
            pass


class AppearanceView(ScrollPage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._refs = []
        self._row = 0
        th = self.theme
        self.page_title("Appearance", "Everything here updates the preview instantly — and an open reader window too.")

        self.grid_wrap = ctk.CTkFrame(self.content, fg_color="transparent")
        self.grid_wrap.pack(fill="x")
        self.grid_wrap.grid_columnconfigure(0, weight=1)
        self.left = ctk.CTkFrame(self.grid_wrap, fg_color="transparent")
        self.left.grid_columnconfigure(0, weight=1)
        self.right = ctk.CTkFrame(self.grid_wrap, fg_color="transparent", width=380)
        self.preview = PreviewPane(self.right, th)
        self.preview.pack(fill="x")
        self._stacked = None
        self._layout(1200)
        self.grid_wrap.bind("<Configure>", lambda e: self._layout(e.width), add="+")

        self._themes_section()
        self._custom_section()
        self._typography_section()
        self._behaviour_section()

    # responsive: preview beside controls on wide windows, above them on narrow ones
    def _layout(self, width):
        stacked = width < 900
        if stacked == self._stacked:
            return
        self._stacked = stacked
        for w in (self.left, self.right):
            w.grid_forget()
        if stacked:
            self.grid_wrap.grid_columnconfigure(1, weight=0, minsize=0)
            self.right.grid(row=0, column=0, sticky="ew", pady=(0, 14))
            self.left.grid(row=1, column=0, sticky="ew")
        else:
            self.grid_wrap.grid_columnconfigure(1, weight=0, minsize=380)
            self.left.grid(row=0, column=0, sticky="new", padx=(0, 18))
            self.right.grid(row=0, column=1, sticky="new")

    def _next(self, card):
        card.grid(row=self._row, column=0, sticky="ew", pady=7)
        self._row += 1

    def _changed(self, visual=True):
        self.preview.refresh()
        self.app.refresh_reader("visual")

    # ── themes ──────────────────────────────────────────────────
    def _themes_section(self):
        th = self.theme
        card, body = make_section(self.left, th, "Theme", "Pick a look for the whole app and the reader.")
        self._next(card)
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.grid(row=0, column=0, sticky="ew")
        keys = list(THEMES.keys())
        cols = 3
        for c in range(cols):
            grid.grid_columnconfigure(c, weight=1, uniform="th")
        for i, key in enumerate(keys):
            t = THEMES[key]
            active = key == config.get("theme", "midnight")
            tile = ctk.CTkFrame(grid, fg_color=t.bg, corner_radius=12, border_width=2 if active else 1,
                                border_color=th.accent if active else t.border, height=74, cursor="hand2")
            tile.grid(row=i // cols, column=i % cols, padx=5, pady=5, sticky="ew")
            tile.grid_propagate(False)
            ctk.CTkLabel(tile, text=t.display_name + ("  ✓" if active else ""), font=ui_font(12, "bold"),
                         text_color=t.text_main).place(x=12, y=10)
            for j, col in enumerate((t.accent, t.card_bg, t.text_sub)):
                ctk.CTkFrame(tile, fg_color=col, width=22, height=10, corner_radius=5).place(x=12 + j * 26, y=44)
            for w in [tile] + tile.winfo_children():
                w.bind("<Button-1>", lambda e, k=key: self.app.apply_theme(k))

    def _custom_section(self):
        th = self.theme
        card, body = make_section(self.left, th, "Custom theme", "Make it yours: choose three colours and Kisukisu derives the rest.")
        self._next(card)
        vals = custom_theme_values()
        self.cv = {k: tk.StringVar(value=vals[k]) for k in ("accent", "bg", "text")}
        self.cv_dark = tk.BooleanVar(value=vals["dark"])
        self.cv_name = tk.StringVar(value=vals["display_name"])
        self._swatches = {}
        for r, (key, label) in enumerate((("accent", "Accent"), ("bg", "Background"), ("text", "Text"))):
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.grid(row=r, column=0, sticky="ew", pady=4)
            ctk.CTkLabel(row, text=label, font=ui_font(12), text_color=th.text_main, width=90, anchor="w").pack(side="left")
            sw = ctk.CTkButton(row, text="", width=34, height=30, corner_radius=8, fg_color=self.cv[key].get(),
                               hover_color=self.cv[key].get(), border_width=1, border_color=th.border,
                               command=lambda k=key: self._pick(k))
            sw.pack(side="left", padx=(0, 8))
            self._swatches[key] = sw
            e = make_entry(row, th, 110, self.cv[key])
            e.pack(side="left")
            self.cv[key].trace_add("write", lambda *_, k=key: self._sync_swatch(k))
        quick = ctk.CTkFrame(body, fg_color="transparent")
        quick.grid(row=3, column=0, sticky="w", pady=(6, 2))
        ctk.CTkLabel(quick, text="Quick accents", font=ui_font(11), text_color=th.text_sub).pack(side="left", padx=(0, 10))
        for name, col in ACCENTS:
            ctk.CTkButton(quick, text="", width=24, height=24, corner_radius=12, fg_color=col, hover_color=col,
                          border_width=2, border_color=th.card_bg,
                          command=lambda c=col: self.cv["accent"].set(c)).pack(side="left", padx=3)
        r = SwitchRow(body, th, "Dark base", "Off = a light theme.", vals["dark"], lambda v: self.cv_dark.set(v))
        self._refs.append(r)
        r.grid(row=4, column=0, sticky="ew", pady=(8, 2))
        namerow = ctk.CTkFrame(body, fg_color="transparent")
        namerow.grid(row=5, column=0, sticky="ew", pady=(6, 2))
        ctk.CTkLabel(namerow, text="Name", font=ui_font(12), text_color=th.text_main, width=90, anchor="w").pack(side="left")
        make_entry(namerow, th, 180, self.cv_name).pack(side="left")
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=6, column=0, sticky="w", pady=(10, 0))
        make_pill_button(btns, "Apply theme", self._apply_custom, th, primary=True, width=112, height=34).pack(side="left", padx=(0, 6))
        make_pill_button(btns, "Export…", self._export_theme, th, width=84, height=34).pack(side="left", padx=3)
        make_pill_button(btns, "Import…", self._import_theme, th, width=84, height=34).pack(side="left", padx=3)

    def _sync_swatch(self, key):
        v = normalize_hex(self.cv[key].get(), "")
        if v:
            try:
                self._swatches[key].configure(fg_color=v, hover_color=v)
            except Exception:
                pass

    def _pick(self, key):
        res = colorchooser.askcolor(color=normalize_hex(self.cv[key].get(), "#8055E8"), parent=self.app, title="Choose a colour")
        if res and res[1]:
            self.cv[key].set(res[1].upper())

    def _apply_custom(self):
        vals = {k: self.cv[k].get() for k in self.cv}
        bad = [k for k, v in vals.items() if not is_hex(normalize_hex(v, ""))]
        if bad:
            self.app.toast("Use hex colours like #8055E8", "warning")
            return
        save_custom_theme(vals["accent"], vals["bg"], None, vals["text"], self.cv_name.get().strip() or "My Theme",
                          self.cv_dark.get())
        self.app.apply_theme("custom")
        self.app.toast("Custom theme applied", "success")

    def _export_theme(self):
        dest = filedialog.asksaveasfilename(parent=self.app, title="Export theme", defaultextension=".json",
                                            initialfile="kisukisu-theme.json", filetypes=[("Theme", "*.json")])
        if dest:
            ok = export_theme(dest)
            self.app.toast("Theme exported" if ok else "Export failed", "success" if ok else "error")

    def _import_theme(self):
        src = filedialog.askopenfilename(parent=self.app, title="Import theme", filetypes=[("Theme", "*.json")])
        if src:
            if import_theme(src):
                self.app.apply_theme("custom")
                self.app.toast("Theme imported", "success")
            else:
                self.app.toast("That file isn't a valid theme", "error")

    # ── typography ──────────────────────────────────────────────
    def _typography_section(self):
        th = self.theme
        card, body = make_section(self.left, th, "Reader typography", "How your words look while you present.")
        self._next(card)
        body.grid_columnconfigure(0, weight=1)
        r = 0
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=r, column=0, sticky="ew", pady=6)
        r += 1
        ctk.CTkLabel(row, text="Font", font=ui_font(12), text_color=th.text_main).pack(anchor="w")
        fonts = font_choices()
        cur = resolve_font(config.get("font_family"))
        self.font_box = ctk.CTkComboBox(
            row, values=fonts, width=300, height=34, corner_radius=8, fg_color=th.input_bg, border_color=th.border,
            button_color=th.pill_bg, button_hover_color=th.pill_hover, text_color=th.text_main,
            dropdown_fg_color=th.card_bg, dropdown_text_color=th.text_main, dropdown_hover_color=th.hover_bg,
            font=ui_font(12), command=self._set_font)
        self.font_box.set(cur)
        self.font_box.pack(anchor="w", pady=(4, 0))

        def slider(key, text, lo, hi, fmt, steps=None):
            nonlocal r
            def live(v):
                config.set(key, v, save=False)
                self._changed()
            s = LabeledSlider(body, th, text, lo, hi, config.get(key), steps=steps, fmt=fmt, on_change=live,
                              on_release=lambda v: config.save())
            self._refs.append(s)
            s.grid(row=r, column=0, sticky="ew", pady=7)
            r += 1

        slider("font_size", "Text size", 12, 72, lambda v: f"{int(v)} pt", 60)
        slider("line_spacing", "Line spacing", 0, 30, lambda v: f"{int(v)} px", 30)
        slider("paragraph_gap", "Paragraph gap", 0, 60, lambda v: f"{int(v)} px", 60)
        slider("reader_padding", "Side margins", 8, 120, lambda v: f"{int(v)} px", 56)

        seg = ctk.CTkFrame(body, fg_color="transparent")
        seg.grid(row=r, column=0, sticky="ew", pady=8)
        r += 1
        ctk.CTkLabel(seg, text="Weight", font=ui_font(12), text_color=th.text_main).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(seg, text="Alignment", font=ui_font(12), text_color=th.text_main).grid(row=0, column=1, sticky="w", padx=(24, 0))
        make_segmented(seg, th, ["Normal", "Bold"], lambda v: self._set("font_weight", v.lower()),
                       config.get("font_weight", "normal").capitalize()).grid(row=1, column=0, sticky="w", pady=(4, 0))
        make_segmented(seg, th, ["Left", "Center"], lambda v: self._set("text_align", v.lower()),
                       config.get("text_align", "left").capitalize()).grid(row=1, column=1, sticky="w", padx=(24, 0), pady=(4, 0))
        make_pill_button(body, "Reset typography", self._reset_typography, th, width=140, height=32).grid(row=r, column=0, sticky="w", pady=(8, 0))

    def _behaviour_section(self):
        th = self.theme
        card, body = make_section(self.left, th, "Reading aids & window", "Focus, guide line and transparency.")
        self._next(card)
        r = 0

        def toggle(key, title, desc):
            nonlocal r
            sr = SwitchRow(body, th, title, desc, config.get(key), lambda v: (config.set(key, v), self._changed()))
            self._refs.append(sr)
            sr.grid(row=r, column=0, sticky="ew", pady=6)
            r += 1

        toggle("focus_mode", "Focus mode", "Dim everything except the paragraph you are reading.")
        toggle("show_ruler", "Reading line", "A thin guide where your eyes rest.")
        s = LabeledSlider(body, th, "Reader window opacity", 0.40, 1.0, config.get("opacity"),
                          fmt=lambda v: f"{int(v * 100)}%",
                          on_change=lambda v: (config.set("opacity", v, save=False), self.app.refresh_reader("visual")),
                          on_release=lambda v: config.save())
        self._refs.append(s)
        s.grid(row=r, column=0, sticky="ew", pady=7)

    def _set(self, key, value):
        config.set(key, value)
        self._changed()

    def _set_font(self, name):
        config.set("font_family", name)
        self._changed()

    def _reset_typography(self):
        config.reset_defaults(["font_family", "font_size", "font_weight", "line_spacing", "paragraph_gap",
                               "text_align", "reader_padding"])
        self.app.switch_view("appearance")
        self.app.refresh_reader("visual")
        self.app.toast("Typography reset", "success")
