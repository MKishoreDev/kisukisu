# -*- coding: utf-8 -*-
"""Kisukisu — main-window views. Each view is a frame that the app shell swaps in and out."""

import customtkinter as ctk

from ..components import ui_font

MAX_CONTENT_WIDTH = 1040


class BaseView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.app = app
        self.theme = app.theme

    def flush(self):
        """Called before the view is replaced (save pending work here)."""


class ScrollPage(BaseView):
    """A scrollable page whose content stays centred and readable on very wide windows."""

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.page = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=self.theme.border, scrollbar_button_hover_color=self.theme.text_muted)
        self.page.grid(row=0, column=0, sticky="nsew")
        self.content = ctk.CTkFrame(self.page, fg_color="transparent")
        self.content.pack(fill="x", padx=28, pady=(24, 28))
        self.content.grid_columnconfigure(0, weight=1)
        self._pad_job = None
        self.page.bind("<Configure>", self._on_page_configure, add="+")

    def _on_page_configure(self, e):
        if self._pad_job:
            try:
                self.after_cancel(self._pad_job)
            except Exception:
                pass
        self._pad_job = self.after(40, lambda w=e.width: self._set_pad(w))

    def _set_pad(self, width):
        self._pad_job = None
        try:
            pad = max(24, (width - MAX_CONTENT_WIDTH) // 2)
            self.content.pack_configure(padx=pad)
        except Exception:
            pass

    def page_title(self, title, subtitle=""):
        th = self.theme
        ctk.CTkLabel(self.content, text=title, font=ui_font(22, "bold"), text_color=th.text_main,
                     anchor="w").pack(anchor="w")
        if subtitle:
            from ..components import bind_wrap
            sub = ctk.CTkLabel(self.content, text=subtitle, font=ui_font(12), text_color=th.text_sub,
                               anchor="w", justify="left")
            sub.pack(anchor="w", fill="x", pady=(2, 0))
            bind_wrap(sub, self.content, margin=4)
        ctk.CTkFrame(self.content, fg_color="transparent", height=14).pack()
