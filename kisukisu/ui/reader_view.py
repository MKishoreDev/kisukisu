# -*- coding: utf-8 -*-
"""
Kisukisu — Presenter Reader (v1.1)

A real, well-behaved desktop window:
  * native title bar -> minimise / maximise / close always work, resizable, draggable
  * shows in the taskbar & Alt-Tab (hiding is an opt-in setting)
  * one continuous, pixel-smooth scrolling text area (no clipped text)
  * Normal · Compact (slim strip under the webcam) · Fullscreen modes
  * focus mode (current paragraph stays bright), reading ruler, cue chips
  * timer with time-remaining estimate, resume where you stopped
  * every shortcut rebindable, every visual setting live
  * window position/size is validated against the real monitors on every launch
"""

import re
import sys
import time
import bisect
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from ..core.config import config
from ..core.shortcuts import DEFAULT_SHORTCUTS, ALIASES, tk_sequences, pretty
from ..core.geometry import parse_geometry, format_geometry, clamp_rect, pick_monitor
from ..core.monitor_manager import MonitorManager
from ..core.document_parser import DocumentParser, format_cue, format_minutes
from ..utils import win_stealth as ws
from ..utils.resource_path import resource_path
from .themes import get_theme, Theme, mix
from .components import (
    make_pill_button, make_icon_button, set_active, resolve_font, ui_font,
    apply_window_icon, style_menu, Tooltip, Toast, LabeledSlider, SwitchRow,
    make_option_menu,
)

_INLINE_CUE = re.compile(r"\[[^\]\n]{1,60}\]")
MIN_W, MIN_H = 300, 130


class PresenterReaderWindow(ctk.CTkToplevel):
    def __init__(self, parent_app, script_data: dict):
        super().__init__(parent_app)
        self.withdraw()                       # build first, show once ready (no flicker)
        self.parent_app = parent_app
        self.script_data = script_data
        self.theme: Theme = get_theme(config.get("theme", "midnight"))
        self._closed = False

        # ── content ──
        self.sections = script_data.get("sections") or DocumentParser.parse_markdown_or_txt(
            script_data.get("raw_content", ""), script_data.get("title", "Script"))
        if not self.sections:
            self.sections = [{"num": 1, "title": script_data.get("title", "Script"), "action": "",
                              "say": "Nothing to display.", "on_screen": ""}]

        # ── state ──
        self.mode = "compact" if config.get("start_compact") else "normal"   # normal | compact | full
        self._mode_before_full = "normal"
        self.playing = False
        self._job = None
        self._upd_job = None
        self._clock_job = None
        self._last_tick = 0.0
        self._acc = 0.0
        self._t_start = None
        self.cur_sec = 0
        self.cur_para = -1
        self.para_ranges = []        # (start_line, end_line, sec_idx)
        self.sec_lines = []
        self.words_after = []
        self._bound = []
        self._panel = None
        self._last_status = {}
        self.monitors = MonitorManager.get_monitors(self)
        self.pinned = bool(config.get("always_on_top", True))

        # ── window ──
        self.title(f"Kisukisu — {script_data.get('title', 'Script')}")
        self.configure(fg_color=self.theme.reader_bg)
        self.minsize(MIN_W, MIN_H)
        self.attributes("-alpha", config.get("opacity", 0.96))
        self.attributes("-topmost", self.pinned)
        self.geometry(self._geometry_for_mode(self.mode))
        apply_window_icon(self)

        self.toast = Toast(self, self.theme)
        self._make_fonts()
        self._build_ui()
        self._render_content()
        self.rebind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self._on_configure, add="+")
        self.bind("<Escape>", self._on_escape)

        self._apply_mode_layout()
        self.deiconify()
        self.after(60, self._post_show)

    # ═════════════════════════ helpers ═══════════════════════════
    def _alive(self) -> bool:
        if self._closed:
            return False
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def _px(self, v) -> int:
        """Config pixel values are defined at 96 dpi; scale them for this display."""
        try:
            scale = float(self.tk.call("tk", "scaling")) / 1.3333
        except Exception:
            scale = 1.0
        return max(0, int(round(float(v) * scale)))

    def _scale(self) -> float:
        try:
            return float(ctk.ScalingTracker.get_window_scaling(self))
        except Exception:
            return 1.0

    def _sc(self):
        sc = config.get("shortcuts") or DEFAULT_SHORTCUTS
        return {**DEFAULT_SHORTCUTS, **sc}

    def _tip(self, action: str, text: str) -> str:
        return f"{text}  ({pretty(self._sc().get(action, ''))})"

    # ═════════════════════════ geometry ══════════════════════════
    def _geometry_for_mode(self, mode: str) -> str:
        prefix = "compact" if mode == "compact" else "reader"
        remember = config.get("remember_window", True)
        w, h = config.get(f"{prefix}_w"), config.get(f"{prefix}_h")
        x = config.get(f"{prefix}_x") if remember else None
        y = config.get(f"{prefix}_y") if remember else None
        anchor = "top" if mode == "compact" else "right"
        min_h = 110 if mode == "compact" else MIN_H
        w, h, x, y = clamp_rect(w, h, x, y, self.monitors, config.get("selected_monitor", 0),
                                min_w=MIN_W, min_h=min_h, anchor=anchor, scale=self._scale())
        return format_geometry(w, h, x, y)

    def _save_geometry(self, mode: str):
        """Remember window size/position for *mode* — never while minimised, maximised or fullscreen."""
        if mode not in ("normal", "compact"):
            return
        try:
            if self.state() in ("iconic", "zoomed", "withdrawn"):
                return
            parsed = parse_geometry(self.geometry())
        except Exception:
            return
        if not parsed:
            return
        w, h, x, y = parsed
        if x <= -30000 or y <= -30000 or w < MIN_W or h < 100:
            return
        prefix = "compact" if mode == "compact" else "reader"
        for k, v in (("w", w), ("h", h), ("x", x), ("y", y)):
            config.set(f"{prefix}_{k}", v, save=False)

    def move_to_monitor(self, index: int):
        """Place the window on another display (used by the settings panel)."""
        self.monitors = MonitorManager.get_monitors(self)
        config.set("selected_monitor", index, save=False)
        parsed = parse_geometry(self.geometry())
        w, h = (parsed[0], parsed[1]) if parsed else (config.get("reader_w"), config.get("reader_h"))
        anchor = "top" if self.mode == "compact" else "right"
        w, h, x, y = clamp_rect(w, h, None, None, self.monitors, index, min_w=MIN_W, anchor=anchor,
                                scale=self._scale())
        self.geometry(format_geometry(w, h, x, y))
        config.save()

    def reset_window_size(self):
        for k in ("reader_w", "reader_h", "reader_x", "reader_y", "compact_w", "compact_h",
                  "compact_x", "compact_y"):
            config.set(k, None if k.endswith(("_x", "_y")) else
                       {"reader_w": 640, "reader_h": 560, "compact_w": 760, "compact_h": 180}[k], save=False)
        config.save()
        if self.mode != "full":
            self.geometry(self._geometry_for_mode(self.mode))

    # ═════════════════════════ fonts & tags ══════════════════════
    def _make_fonts(self):
        fam = resolve_font(config.get("font_family"))
        size, weight = int(config.get("font_size", 24)), config.get("font_weight", "normal")
        self.f_body = tkfont.Font(root=self, family=fam, size=size, weight=weight)
        self.f_bold = tkfont.Font(root=self, family=fam, size=size, weight="bold")
        self.f_title = tkfont.Font(root=self, family=fam, size=max(12, int(size * 0.72)), weight="bold")
        self.f_cue = tkfont.Font(root=self, family=fam, size=max(10, int(size * 0.5)), weight="bold")
        self.f_ref = tkfont.Font(root=self, family=fam, size=max(10, int(size * 0.5)), slant="italic")
        self.f_pad = tkfont.Font(root=self, family=fam, size=2)

    def _update_fonts(self):
        fam = resolve_font(config.get("font_family"))
        size, weight = int(config.get("font_size", 24)), config.get("font_weight", "normal")
        self.f_body.configure(family=fam, size=size, weight=weight)
        self.f_bold.configure(family=fam, size=size, weight="bold")
        self.f_title.configure(family=fam, size=max(12, int(size * 0.72)))
        self.f_cue.configure(family=fam, size=max(10, int(size * 0.5)))
        self.f_ref.configure(family=fam, size=max(10, int(size * 0.5)))

    def _line_px(self) -> int:
        try:
            return self.f_body.metrics("linespace") + self._px(config.get("line_spacing", 8))
        except Exception:
            return 36

    def _configure_tags(self):
        t, th = self.txt, self.theme
        focus = bool(config.get("focus_mode", True))
        align = config.get("text_align", "left")
        dim = mix(th.reader_text, th.reader_bg, 0.58)
        t.configure(bg=th.reader_bg, fg=th.reader_text, font=self.f_body,
                    spacing2=self._px(config.get("line_spacing", 8)), selectbackground=th.selected_bg)
        t.tag_configure("para", font=self.f_body, foreground=dim if focus else th.reader_text,
                        spacing3=self._px(config.get("paragraph_gap", 18)), justify=align)
        t.tag_configure("cur", foreground=th.reader_text)
        t.tag_configure("sec_title", font=self.f_title, foreground=th.accent, justify=align,
                        spacing1=self._px(34), spacing3=self._px(8))
        t.tag_configure("cue", font=self.f_cue, foreground=th.cue_color, background=th.selected_bg,
                        justify=align, spacing1=self._px(4), spacing3=self._px(10))
        t.tag_configure("inline_cue", font=self.f_bold, foreground=th.cue_color, background=th.selected_bg)
        t.tag_configure("ref", font=self.f_ref, foreground=th.text_muted, justify=align, spacing3=self._px(10))
        t.tag_configure("pad_top", font=self.f_pad)
        t.tag_configure("pad_bottom", font=self.f_pad)
        self._update_pads()

    def _update_pads(self):
        try:
            h = max(self.txt.winfo_height(), 200)
        except Exception:
            h = 400
        pos = float(config.get("ruler_position", 0.38))
        self.txt.tag_configure("pad_top", spacing1=int(h * pos * 0.55))
        self.txt.tag_configure("pad_bottom", spacing1=int(h * (1 - pos)))

    # ═════════════════════════ UI build ══════════════════════════
    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_body()
        self._build_toolbar()

    def _build_header(self):
        th = self.theme
        self.header = ctk.CTkFrame(self, fg_color=th.card_bg, corner_radius=0, height=44)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(1, weight=1)
        self.header.grid_rowconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(self.header, text=str(self.script_data.get("title", "Script"))[:60], font=ui_font(12, "bold"),
                                      text_color=th.text_main, anchor="w")
        self.lbl_title.grid(row=0, column=0, padx=(16, 8), sticky="w")

        self.lbl_timer = ctk.CTkLabel(self.header, text="", font=ui_font(11), text_color=th.text_sub,
                                      anchor="center", cursor="hand2")
        self.lbl_timer.grid(row=0, column=1, sticky="ew")
        self.lbl_timer.bind("<Button-1>", lambda e: self.reset_timer())
        Tooltip(self.lbl_timer, "Click to reset the timer", th)

        self.lbl_status = ctk.CTkLabel(self.header, text="", font=ui_font(11, "bold"),
                                       text_color=th.accent_light, anchor="e")
        self.lbl_status.grid(row=0, column=2, padx=(8, 16), sticky="e")

        self.progress = ctk.CTkProgressBar(self, height=3, corner_radius=0,
                                           fg_color=th.border_subtle, progress_color=th.progress_color)
        self.progress.grid(row=1, column=0, sticky="ew")
        self.progress.set(0)

    def _build_body(self):
        th = self.theme
        self.body = tk.Frame(self, bg=th.reader_bg, highlightthickness=0, bd=0)
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.scrollbar = ctk.CTkScrollbar(self.body, width=10, fg_color="transparent",
                                          button_color=th.border, button_hover_color=th.text_muted)
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 2), pady=4)

        self.txt = tk.Text(
            self.body, wrap="word", bd=0, highlightthickness=0, relief="flat", cursor="arrow",
            takefocus=0, undo=False, insertwidth=0, padx=24, pady=0,
            yscrollcommand=self._on_yscroll)
        self.txt.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.configure(command=self.txt.yview)
        # Remove the default Text key/mouse behaviour — we own every key and wheel event.
        self.txt.bindtags((str(self.txt), str(self.winfo_toplevel()), "all"))
        self.txt.bind("<MouseWheel>", self._on_wheel)
        self.txt.bind("<Button-4>", lambda e: self.scroll_up())
        self.txt.bind("<Button-5>", lambda e: self.scroll_down())
        self.txt.bind("<Button-1>", lambda e: self.focus_set())
        self.txt.bind("<Double-Button-1>", lambda e: self.toggle_play())
        self._configure_tags()

        # reading ruler (thin line + marker at the reading position)
        self.ruler = tk.Frame(self.body, bg=mix(th.accent, th.reader_bg, 0.35), height=1)
        self.ruler_mark = tk.Label(self.body, text="▸", bg=th.reader_bg, fg=th.accent,
                                   font=(resolve_font(), 11), bd=0, padx=0, pady=0)
        self._place_ruler()

    def _build_toolbar(self):
        th = self.theme
        self.toolbar = ctk.CTkFrame(self, fg_color=th.card_bg, corner_radius=0, height=56)
        self.toolbar.grid(row=3, column=0, sticky="ew")
        self.toolbar.grid_propagate(False)
        self.toolbar.grid_columnconfigure(1, weight=1)
        self.toolbar.grid_rowconfigure(0, weight=1)

        # left: navigation
        nav = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        nav.grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")
        self.btn_prev = make_icon_button(nav, "‹", self.prev_section, th, 36, self._tip("prev_section", "Previous section"))
        self.btn_prev.configure(font=ui_font(18, "bold"))
        self.btn_prev.pack(side="left", padx=2)
        self.btn_play = make_pill_button(nav, "▶", self.toggle_play, th, primary=True, width=54, height=36,
                                         tooltip=self._tip("play_pause", "Play / pause auto-scroll"))
        self.btn_play.pack(side="left", padx=4)
        self.btn_next = make_icon_button(nav, "›", self.next_section, th, 36, self._tip("next_section", "Next section"))
        self.btn_next.configure(font=ui_font(18, "bold"))
        self.btn_next.pack(side="left", padx=2)

        # middle: speed + font
        mid = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        mid.grid(row=0, column=1, sticky="ns")
        self.mid = ctk.CTkFrame(mid, fg_color="transparent")
        self.mid.place(relx=0.5, rely=0.5, anchor="center")
        self.g_speed = ctk.CTkFrame(self.mid, fg_color="transparent")
        self.g_speed.grid(row=0, column=0, padx=8)
        make_icon_button(self.g_speed, "−", self.speed_down, th, 30, self._tip("speed_down", "Slower")).pack(side="left", padx=2)
        self.lbl_speed = ctk.CTkLabel(self.g_speed, text="", font=ui_font(11, "bold"), text_color=th.text_sub, width=64)
        self.lbl_speed.pack(side="left")
        make_icon_button(self.g_speed, "+", self.speed_up, th, 30, self._tip("speed_up", "Faster")).pack(side="left", padx=2)
        self.g_font = ctk.CTkFrame(self.mid, fg_color="transparent")
        self.g_font.grid(row=0, column=1, padx=8)
        make_icon_button(self.g_font, "A−", self.font_down, th, 32, self._tip("font_down", "Smaller text")).pack(side="left", padx=2)
        make_icon_button(self.g_font, "A+", self.font_up, th, 32, self._tip("font_up", "Bigger text")).pack(side="left", padx=2)

        # right: view controls
        right = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        right.grid(row=0, column=2, padx=(6, 12), pady=10, sticky="e")
        self.btn_sections = make_icon_button(right, "☰", self.show_sections_menu, th, 36, self._tip("sections_menu", "Jump to section"))
        self.btn_pin = make_pill_button(right, "Pin", self.toggle_pin, th, width=48, height=34,
                                        tooltip=self._tip("toggle_pin", "Keep above other windows"))
        self.btn_mini = make_pill_button(right, "Mini", self.toggle_compact, th, width=52, height=34,
                                         tooltip=self._tip("toggle_compact", "Compact strip mode"))
        self.btn_full = make_pill_button(right, "Full", self.toggle_fullscreen, th, width=48, height=34,
                                         tooltip=self._tip("toggle_fullscreen", "Fullscreen"))
        self.btn_gear = make_icon_button(right, "⚙", self.open_settings, th, 36, "Reader settings")
        self._right_items = [self.btn_sections, self.btn_pin, self.btn_mini, self.btn_full, self.btn_gear]
        for i, b in enumerate(self._right_items):
            b.grid(row=0, column=i, padx=2)
        self._refresh_toolbar_state()

    def _refresh_toolbar_state(self):
        set_active(self.btn_pin, self.theme, self.pinned)
        set_active(self.btn_mini, self.theme, self.mode == "compact")
        set_active(self.btn_full, self.theme, self.mode == "full")
        self.btn_play.configure(text="❚❚" if self.playing else "▶")
        self.lbl_speed.configure(text=f"Speed {config.get('auto_scroll_speed', 4)}")

    # ═════════════════════════ rendering ═════════════════════════
    def _render_content(self):
        t = self.txt
        show_cues = bool(config.get("show_cues", True))
        show_ref = bool(config.get("show_onscreen_ref", True))
        t.configure(state="normal")
        t.delete("1.0", "end")
        self.para_ranges, self.sec_lines = [], []
        para_words = []

        def cur_line() -> int:
            return int(t.index("end-1c").split(".")[0])

        t.insert("end", "\n", "pad_top")
        for si, s in enumerate(self.sections):
            mark = f"sec{si}"
            t.mark_set(mark, "end-1c")
            t.mark_gravity(mark, "left")
            self.sec_lines.append(cur_line())

            title = (s.get("title") or "").strip()
            if title:
                t.insert("end", title + "\n", "sec_title")

            action = (s.get("action") or "").strip()
            if action and show_cues:
                for part in re.split(r"\s{2,}·\s{2,}|\n+", action):
                    cue = format_cue(part)
                    if cue:
                        t.insert("end", f" ▸ {cue} \n", "cue")

            on_screen = (s.get("on_screen") or "").strip()
            if on_screen and show_ref:
                t.insert("end", f"Reference · {on_screen}\n", "ref")

            say = (s.get("say") or "").strip()
            if not show_cues:
                say = re.sub(r"[ \t]*\[[^\]\n]{1,60}\]", "", say)
            for para in [p.strip() for p in re.split(r"\n\s*\n", say) if p.strip()]:
                start = cur_line()
                t.insert("end", para + "\n", "para")
                end = cur_line() - 1
                if show_cues:
                    for m in _INLINE_CUE.finditer(para):
                        a = f"{start}.0 + {m.start()}c"
                        b = f"{start}.0 + {m.end()}c"
                        t.tag_add("inline_cue", a, b)
                self.para_ranges.append((start, end, si))
                para_words.append(len(para.split()))
        t.insert("end", "\n", "pad_bottom")
        t.configure(state="disabled")

        total, acc = sum(para_words), 0
        self.words_after = []
        for w in para_words:
            self.words_after.append(total - acc)
            acc += w
        self.cur_para = -1
        self._starts = [r[0] for r in self.para_ranges]

    def _restore_position(self):
        p = self.script_data.get("progress", 0) if config.get("resume_position", True) else 0
        try:
            p = float(p)
        except (TypeError, ValueError):
            p = 0
        if 0.02 < p < 0.97:
            self.update_idletasks()
            lo, hi = self.txt.yview()
            self.txt.yview_moveto(p * max(0.0, 1 - (hi - lo)))
            self.toast.show(f"Resumed at {int(p * 100)}% · Home to restart", "info", 3200)

    # ═════════════════════════ scrolling & status ════════════════
    def _on_yscroll(self, lo, hi):
        try:
            self.scrollbar.set(lo, hi)
        except Exception:
            pass
        if self._upd_job is None and self._alive():
            self._upd_job = self.after(30, self._do_update)

    def _do_update(self):
        self._upd_job = None
        if not self._alive() or not self.para_ranges:
            return
        try:
            ruler_y = int(self.txt.winfo_height() * float(config.get("ruler_position", 0.38)))
            line = int(self.txt.index(f"@0,{ruler_y}").split(".")[0])
        except Exception:
            return

        i = max(0, bisect.bisect_right(self._starts, line) - 1)
        if i != self.cur_para:
            if config.get("focus_mode", True):
                self.txt.tag_remove("cur", "1.0", "end")
                s, e, _ = self.para_ranges[i]
                self.txt.tag_add("cur", f"{s}.0", f"{e}.end")
            self.cur_para = i

        new_sec = max(0, bisect.bisect_right(self.sec_lines, line + 1) - 1)
        if new_sec != self.cur_sec:
            moved_forward = new_sec > self.cur_sec
            self.cur_sec = new_sec
            if self.playing and moved_forward and config.get("pause_between_sections", False):
                self.pause()
                self.toast.show(f"Section {new_sec + 1} — press {pretty(self._sc()['play_pause'])} to continue", "info", 3000)
        self._update_status()

    def _progress(self) -> float:
        lo, hi = self.txt.yview()
        span = hi - lo
        if span >= 0.999:
            return (self.cur_para + 1) / max(1, len(self.para_ranges)) if self.cur_para >= 0 else 0.0
        return max(0.0, min(1.0, lo / max(1e-6, 1 - span)))

    def _update_status(self):
        n = len(self.sections)
        p = self._progress()
        self._set_text(self.lbl_status, "status", f"{self.cur_sec + 1} / {n}   ·   {int(p * 100)}%")
        try:
            self.progress.set(p)
        except Exception:
            pass
        self._update_clock()

    def _set_text(self, label, key, text):
        if self._last_status.get(key) != text:
            self._last_status[key] = text
            try:
                label.configure(text=text)
            except Exception:
                pass

    def _update_clock(self):
        if not config.get("show_timer", True):
            self._set_text(self.lbl_timer, "timer", "")
            return
        elapsed = int(time.monotonic() - self._t_start) if self._t_start else 0
        mm, ss = divmod(elapsed, 60)
        left = ""
        if self.cur_para >= 0 and self.cur_para < len(self.words_after):
            mins = self.words_after[self.cur_para] / max(1, config.get("reading_wpm", 150))
            left = f"   ·   ~{format_minutes(mins)} left"
        txt = f"{mm:02d}:{ss:02d}{left}" if self.winfo_width() >= 560 else f"{mm:02d}:{ss:02d}"
        self._set_text(self.lbl_timer, "timer", txt)

    def _clock_tick(self):
        self._clock_job = None
        if not self._alive():
            return
        self._update_clock()
        self._clock_job = self.after(1000, self._clock_tick)

    def reset_timer(self):
        self._t_start = time.monotonic() if self.playing else None
        self._last_status.pop("timer", None)
        self._update_clock()
        self.toast.show("Timer reset", "info", 1400)

    def _scroll_px(self, lines=1):
        lines = int(lines)
        if lines:
            self.txt.yview_scroll(lines, "units")
        return "break"

    def _on_wheel(self, e):
        step = -e.delta / 120.0 if sys.platform != "darwin" else -float(e.delta)
        lines = int(round(step)) or (1 if step > 0 else -1)
        self.txt.yview_scroll(lines, "units")
        return "break"

    # ═════════════════════════ playback ══════════════════════════
    def _px_per_sec(self) -> float:
        level = int(config.get("auto_scroll_speed", 4))
        return 0.2 + level * 0.25

    def toggle_play(self):
        self.pause() if self.playing else self.play()
        return "break"

    def play(self):
        lo, hi = self.txt.yview()
        if hi >= 0.999 and lo > 0:
            self.txt.yview_moveto(0)
        self.playing = True
        self._last_tick = time.perf_counter()
        self._acc = 0.0
        if self._t_start is None:
            self._t_start = time.monotonic()
            self._clock_tick()
        self._refresh_toolbar_state()
        if self._job is None:
            self._tick()

    def pause(self):
        self.playing = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        self._refresh_toolbar_state()

    def _tick(self):
        self._job = None
        if not self.playing or not self._alive():
            return
        now = time.perf_counter()
        dt = min(now - self._last_tick, 0.1)
        self._last_tick = now
        self._acc += self._px_per_sec() * dt
        n = int(self._acc)
        if n >= 1:
            self._acc -= n
            self.txt.yview_scroll(n, "units")
        if self.txt.yview()[1] >= 0.9995:
            self.pause()
            self.toast.show("End of script", "success", 2200)
            return
        self._job = self.after(16, self._tick)

    def speed_up(self):
        self._set_speed(config.get("auto_scroll_speed", 4) + 1)
        return "break"

    def speed_down(self):
        self._set_speed(config.get("auto_scroll_speed", 4) - 1)
        return "break"

    def _set_speed(self, v):
        v = config.set("auto_scroll_speed", v)
        self._refresh_toolbar_state()
        self.toast.show(f"Speed {v}", "info", 900)

    # ═════════════════════════ navigation ════════════════════════
    def _goto_section(self, i: int):
        i = max(0, min(len(self.sections) - 1, i))
        try:
            self.txt.yview(f"sec{i}")
            offset = int(self.txt.winfo_height() * float(config.get("ruler_position", 0.38))) - self._line_px()
            if offset > 0:
                self.txt.yview_scroll(-offset, "units")
        except Exception:
            pass

    def next_section(self):
        self._goto_section(self.cur_sec + 1)
        return "break"

    def prev_section(self):
        try:
            bb = self.txt.bbox(f"sec{self.cur_sec}")
            ruler_y = self.txt.winfo_height() * float(config.get("ruler_position", 0.38))
            near_start = bb is not None and abs(bb[1] - ruler_y) < self._line_px() * 2.2
        except Exception:
            near_start = False
        self._goto_section(self.cur_sec - 1 if near_start else self.cur_sec)
        return "break"

    def show_sections_menu(self):
        menu = style_menu(tk.Menu(self, tearoff=0), self.theme)
        for i, s in enumerate(self.sections):
            mark = "●  " if i == self.cur_sec else "     "
            label = f"{mark}{i + 1}.  {(s.get('title') or 'Section ' + str(i + 1))[:60]}"
            menu.add_command(label=label, command=lambda k=i: self._goto_section(k))
        try:
            x = self.btn_sections.winfo_rootx()
            y = self.btn_sections.winfo_rooty() - 6
            menu.tk_popup(x, max(0, y - 22 * len(self.sections)))
        finally:
            menu.grab_release()
        return "break"

    def restart(self):
        self.txt.yview_moveto(0)
        return "break"

    def jump_end(self):
        self.txt.yview_moveto(1)
        return "break"

    def page_down(self):
        self.txt.yview_scroll(1, "pages")
        return "break"

    def page_up(self):
        self.txt.yview_scroll(-1, "pages")
        return "break"

    def scroll_down(self):
        self.txt.yview_scroll(1, "units")
        return "break"

    def scroll_up(self):
        self.txt.yview_scroll(-1, "units")
        return "break"

    # ═════════════════════════ appearance ════════════════════════
    def font_up(self):
        config.set("font_size", config.get("font_size", 24) + 2)
        self.apply_settings()
        return "break"

    def font_down(self):
        config.set("font_size", config.get("font_size", 24) - 2)
        self.apply_settings()
        return "break"

    def toggle_focus(self):
        config.set("focus_mode", not config.get("focus_mode", True))
        self.apply_settings()
        self.toast.show("Focus mode " + ("on" if config.get("focus_mode") else "off"), "info", 1100)
        return "break"

    def apply_settings(self, rerender: bool = False):
        """Re-apply every visual setting from config (called live by the settings panel)."""
        if not self._alive():
            return
        try:
            anchor = self.txt.index("@0,0")
        except Exception:
            anchor = "1.0"
        self._update_fonts()
        self._configure_tags()
        if rerender:
            self._render_content()
        self._update_padding()
        self._place_ruler()
        try:
            self.attributes("-alpha", float(config.get("opacity", 0.96)))
        except Exception:
            pass
        self.update_idletasks()
        try:
            self.txt.yview(anchor)
        except Exception:
            pass
        self.cur_para = -1
        self._refresh_toolbar_state()
        self._do_update()

    def rebuild(self):
        """Full rebuild — used after a theme change."""
        was_playing = self.playing
        self.pause()
        self._close_panel()
        try:
            anchor = self.txt.index("@0,0")
        except Exception:
            anchor = "1.0"
        self.theme = get_theme(config.get("theme", "midnight"))
        self.toast.hide()
        for child in list(self.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self.toast = Toast(self, self.theme)
        self.configure(fg_color=self.theme.reader_bg)
        self._last_status = {}
        self._build_ui()
        self._render_content()
        self._apply_mode_layout()
        self.update_idletasks()
        try:
            self.txt.yview(anchor)
        except Exception:
            pass
        ws.set_dark_titlebar(ws.top_level_hwnd(self.winfo_id()), self.theme.dark)
        if was_playing:
            self.play()

    def _update_padding(self):
        w = max(self.winfo_width(), 300)
        pad = min(self._px(config.get("reader_padding", 36)), max(self._px(10), int(w * 0.07)))
        try:
            self.txt.configure(padx=pad)
        except Exception:
            pass

    def _place_ruler(self):
        if config.get("show_ruler", True):
            pos = float(config.get("ruler_position", 0.38))
            self.ruler.place(relx=0, rely=pos, relwidth=1, height=1)
            self.ruler_mark.place(relx=0, rely=pos, x=2, anchor="w")
            self.ruler.lift()
            self.ruler_mark.lift()
        else:
            self.ruler.place_forget()
            self.ruler_mark.place_forget()

    # ═════════════════════════ modes ═════════════════════════════
    def _apply_mode_layout(self):
        """Show/hide chrome for the current mode and tier the toolbar by width."""
        compact = self.mode == "compact"
        if compact:
            self.header.grid_remove()
            self.toolbar.configure(height=48)
        else:
            self.header.grid()
            self.toolbar.configure(height=56)
        self._refresh_toolbar_state()
        self._relayout()

    def _set_mode(self, mode: str):
        if mode == self.mode:
            return
        old = self.mode
        self._save_geometry(old)
        if old == "full":
            self.attributes("-fullscreen", False)
        self.mode = mode
        if mode == "full":
            self._mode_before_full = old
            self.attributes("-fullscreen", True)
        else:
            self.geometry(self._geometry_for_mode(mode))
        self._apply_mode_layout()
        self.after(80, lambda: self.apply_settings())
        config.save()

    def toggle_compact(self):
        self._set_mode("normal" if self.mode == "compact" else "compact")
        return "break"

    def toggle_fullscreen(self):
        if self.mode == "full":
            self._set_mode(self._mode_before_full if self._mode_before_full != "full" else "normal")
        else:
            self._set_mode("full")
        return "break"

    def _on_escape(self, _e=None):
        if self.mode == "full":
            self.toggle_fullscreen()
        elif self.mode == "compact":
            self.toggle_compact()
        elif self._panel is not None:
            self._close_panel()
        return "break"

    def _on_configure(self, e):
        if e.widget is not self:
            return
        if getattr(self, "_cfg_job", None):
            try:
                self.after_cancel(self._cfg_job)
            except Exception:
                pass
        self._cfg_job = self.after(60, self._after_resize)

    def _after_resize(self):
        self._cfg_job = None
        if not self._alive():
            return
        self._relayout()
        self._update_pads()
        self._update_padding()

    def _relayout(self):
        """Responsive toolbar: low-priority controls fold away as the window narrows."""
        try:
            w = self.winfo_width()
        except Exception:
            return
        if w <= 1:
            return
        compact = self.mode == "compact"

        def show(widget, cond):
            (widget.grid if cond else widget.grid_remove)()

        show(self.g_speed, w >= 520)
        show(self.g_font, w >= 640)
        show(self.btn_sections, w >= 420)
        show(self.btn_pin, w >= 380)
        show(self.btn_full, w >= 470 and not compact)
        # title in header: shorten to what fits
        title = self.script_data.get("title", "Script")
        max_chars = max(8, int((w - 260) / 8)) if w < 900 else 120
        self._set_text(self.lbl_title, "title", title if len(title) <= max_chars else title[:max_chars - 1] + "…")
        self._update_clock()

    # ═════════════════════════ window flags ══════════════════════
    def toggle_pin(self):
        self.set_pinned(not self.pinned)
        self.toast.show("Pinned above other windows" if self.pinned else "Unpinned", "info", 1300)
        return "break"

    def set_pinned(self, on: bool):
        self.pinned = bool(on)
        config.set("always_on_top", self.pinned)
        self.attributes("-topmost", self.pinned)
        ws.set_topmost(ws.top_level_hwnd(self.winfo_id()), self.pinned)
        if self._panel is not None:
            try:
                self._panel.attributes("-topmost", self.pinned)
            except Exception:
                pass
        self._refresh_toolbar_state()

    def apply_taskbar_visibility(self):
        """Windows only. Hiding needs a withdraw/deiconify round-trip to take effect."""
        if not ws.is_windows():
            return
        hidden = bool(config.get("hide_from_taskbar", False))
        try:
            if self.parent_app and self.parent_app.winfo_exists():
                if hidden:
                    self.parent_app.withdraw()
                else:
                    self.parent_app.deiconify()
            self.withdraw()
            self.update_idletasks()
            ws.set_taskbar_hidden(ws.top_level_hwnd(self.winfo_id()), hidden)
            self.deiconify()
            self.attributes("-topmost", self.pinned)
        except Exception:
            pass

    def apply_capture_exclusion(self):
        ws.set_capture_excluded(ws.top_level_hwnd(self.winfo_id()),
                                bool(config.get("screen_share_invisibility", True)))

    def _post_show(self):
        if not self._alive():
            return
        hwnd = ws.top_level_hwnd(self.winfo_id())
        ws.set_dark_titlebar(hwnd, self.theme.dark)
        self.apply_capture_exclusion()
        if config.get("hide_from_taskbar", False):
            self.apply_taskbar_visibility()
        self.update_idletasks()
        self._update_pads()
        self._update_padding()
        self._place_ruler()
        self._restore_position()
        self._do_update()
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    # ═════════════════════════ keyboard ══════════════════════════
    def rebind_keys(self):
        for seq in self._bound:
            try:
                self.unbind(seq)
            except Exception:
                pass
        self._bound = []
        actions = {
            "play_pause": self.toggle_play, "next_section": self.next_section,
            "prev_section": self.prev_section, "scroll_down": self.scroll_down,
            "scroll_up": self.scroll_up, "page_down": self.page_down, "page_up": self.page_up,
            "restart": self.restart, "jump_end": self.jump_end, "speed_up": self.speed_up,
            "speed_down": self.speed_down, "font_up": self.font_up, "font_down": self.font_down,
            "toggle_focus": self.toggle_focus, "toggle_pin": self.toggle_pin,
            "toggle_compact": self.toggle_compact, "toggle_fullscreen": self.toggle_fullscreen,
            "sections_menu": self.show_sections_menu, "reset_timer": lambda: self.reset_timer() or "break",
            "close_reader": lambda: self._on_close() or "break",
        }
        sc = self._sc()
        for action, handler in actions.items():
            keys = [sc.get(action)] + list(ALIASES.get(action, ()))
            for key in keys:
                if not key:
                    continue
                for seq in tk_sequences(key):
                    try:
                        self.bind(seq, lambda e, h=handler: h())
                        self._bound.append(seq)
                    except tk.TclError:
                        pass

    # ═════════════════════════ settings panel ════════════════════
    def open_settings(self):
        if self._panel is not None:
            try:
                if self._panel.winfo_exists():
                    self._panel.lift()
                    self._panel.focus_force()
                    return
            except Exception:
                pass
        self._panel = ReaderSettingsPanel(self)

    def _close_panel(self):
        if self._panel is not None:
            try:
                self._panel.destroy()
            except Exception:
                pass
            self._panel = None
        config.save()

    # ═════════════════════════ close ═════════════════════════════
    def _on_close(self):
        if self._closed:
            return
        self._closed = True
        for job in (self._job, self._upd_job, self._clock_job, getattr(self, "_cfg_job", None)):
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
        self.playing = False
        try:
            self._save_geometry(self.mode if self.mode != "full" else self._mode_before_full)
            if self.script_data.get("id"):
                parent = self.parent_app
                if hasattr(parent, "script_manager"):
                    parent.script_manager.update_progress(self.script_data["id"], self._progress())
        except Exception:
            pass
        config.save()
        if self._panel is not None:
            try:
                self._panel.destroy()
            except Exception:
                pass
        try:
            self.toast.hide()
        except Exception:
            pass
        cb = getattr(self.parent_app, "on_reader_closed", None)
        try:
            self.destroy()
        finally:
            if cb:
                try:
                    cb(self)
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════════
class ReaderSettingsPanel(ctk.CTkToplevel):
    """Live settings popover for the reader: everything applies instantly."""

    def __init__(self, reader: PresenterReaderWindow):
        super().__init__(reader)
        self.reader = reader
        self.theme = reader.theme
        th = self.theme
        self.title("Reader settings")
        self.configure(fg_color=th.bg)
        self.minsize(320, 360)
        self.attributes("-topmost", reader.pinned)
        apply_window_icon(self)

        # place beside the reader, on-screen
        try:
            reader.update_idletasks()
            rw, rh, rx, ry = parse_geometry(reader.geometry()) or (640, 560, 80, 80)
            pw, ph = 360, min(620, max(420, rh))
            w, h, x, y = clamp_rect(pw, ph, rx + rw + 12, ry, reader.monitors, config.get("selected_monitor", 0), min_w=320, min_h=360, scale=reader._scale())
            if x < rx + rw and x + w > rx:        # no room on the right -> put it on the left
                w, h, x, y = clamp_rect(pw, ph, rx - pw - 12, ry, reader.monitors, config.get("selected_monitor", 0), min_w=320, min_h=360, scale=reader._scale())
            self.geometry(format_geometry(w, h, x, y))
        except Exception:
            self.geometry("360x560")
        self.transient(reader)
        self.protocol("WM_DELETE_WINDOW", reader._close_panel)
        self.bind("<Escape>", lambda e: reader._close_panel())

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=6, pady=6)
        scroll.grid_columnconfigure(0, weight=1)
        self._row = 0
        self._refs = []          # keep control objects (and their Tk variables) alive

        def header(text):
            ctk.CTkLabel(scroll, text=text.upper(), font=ui_font(10, "bold"), text_color=th.text_muted,
                         anchor="w").grid(row=self._row, column=0, sticky="w", padx=12, pady=(14, 2))
            self._row += 1

        def add(obj):
            self._refs.append(obj)
            widget = obj.frame if isinstance(obj, (LabeledSlider, SwitchRow)) else obj
            widget.grid(row=self._row, column=0, sticky="ew", padx=12, pady=7)
            self._row += 1
            return widget

        def slider(key, text, lo, hi, fmt, steps=None, rerender=False):
            def live(v):
                config.set(key, v, save=False)
                reader.apply_settings(rerender)
            add(LabeledSlider(scroll, th, text, lo, hi, config.get(key), steps=steps, fmt=fmt,
                              on_change=live, on_release=lambda v: config.save()))

        def toggle(key, title, desc="", rerender=False, extra=None):
            def cb(v):
                config.set(key, v)
                if extra:
                    extra(v)
                reader.apply_settings(rerender)
            add(SwitchRow(scroll, th, title, desc, config.get(key), cb))

        header("Reading")
        slider("auto_scroll_speed", "Auto-scroll speed", 1, 10, lambda v: f"{int(v)}", steps=9)
        slider("font_size", "Text size", 12, 72, lambda v: f"{int(v)} pt", steps=60)
        slider("line_spacing", "Line spacing", 0, 30, lambda v: f"{int(v)} px", steps=30)
        slider("paragraph_gap", "Paragraph gap", 0, 60, lambda v: f"{int(v)} px", steps=60)
        slider("reader_padding", "Side margins", 8, 120, lambda v: f"{int(v)} px", steps=56)
        slider("ruler_position", "Reading line position", 0.15, 0.80, lambda v: f"{int(v * 100)}%")
        toggle("focus_mode", "Focus mode", "Dim everything except the paragraph you are reading.")
        toggle("show_ruler", "Reading line", "A thin guide where your eyes rest.")
        toggle("show_cues", "Cue markers", "Show [CUE] lines and highlight [brackets].", rerender=True)
        toggle("show_onscreen_ref", "On-screen references", "Show “On screen:” notes from your script.", rerender=True)
        toggle("pause_between_sections", "Pause at each section", "Auto-scroll stops when a new section starts — ideal for slide changes.")
        toggle("show_timer", "Show timer", "Elapsed time and estimated time left.")
        add(self._align_row(scroll))

        header("Window")
        slider("opacity", "Window opacity", 0.40, 1.0, lambda v: f"{int(v * 100)}%")
        toggle("always_on_top", "Always on top", "Keep the reader above your slides.",
               extra=lambda v: reader.set_pinned(v))
        if ws.is_windows():
            toggle("hide_from_taskbar", "Hide from taskbar & Alt-Tab",
                   "Off by default — turn on only if you want a fully invisible helper.",
                   extra=lambda v: reader.apply_taskbar_visibility())
            toggle("screen_share_invisibility", "Hide from screen sharing",
                   "Windows 10 (2004+) / 11: Meet, Zoom, Teams and recorders won't capture this window.",
                   extra=lambda v: reader.apply_capture_exclusion())
        labels = MonitorManager.get_display_labels(reader)
        if len(labels) > 1:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            ctk.CTkLabel(row, text="Move reader to", font=ui_font(12), text_color=th.text_main).pack(anchor="w")
            om = make_option_menu(row, th, labels, value=labels[min(config.get("selected_monitor", 0), len(labels) - 1)], width=290,
                                  command=lambda v: reader.move_to_monitor(labels.index(v)))
            om.pack(anchor="w", pady=(4, 0))
            add(row)
        btns = ctk.CTkFrame(scroll, fg_color="transparent")
        make_pill_button(btns, "Reset window size", reader.reset_window_size, th, width=150, height=32).pack(side="left", padx=(0, 8))
        make_pill_button(btns, "Done", reader._close_panel, th, primary=True, width=80, height=32).pack(side="left")
        add(btns)

    def _align_row(self, parent):
        th = self.theme
        row = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(row, text="Text alignment", font=ui_font(12), text_color=th.text_main).pack(anchor="w")
        from .components import make_segmented

        def cb(v):
            config.set("text_align", v.lower())
            self.reader.apply_settings()
        make_segmented(row, th, ["Left", "Center"], cb, config.get("text_align", "left").capitalize()).pack(anchor="w", pady=(4, 0))
        return row
