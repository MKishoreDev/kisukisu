# -*- coding: utf-8 -*-
"""
Kisukisu — System tray.

pystray runs in its own thread, and Tk must only be touched from the main
thread — so menu clicks just put a command on a queue that the main window
polls (see LibraryWindow._poll_tray).
"""

import threading
from pathlib import Path

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except Exception:          # pystray can also fail on headless Linux
    TRAY_AVAILABLE = False


class TrayManager:
    def __init__(self, app_ref, logo_path: str = None):
        self.app_ref = app_ref
        self.logo_path = logo_path
        self.tray_icon = None
        self._thread = None

    def start(self):
        if not TRAY_AVAILABLE:
            return
        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()

    def _build_icon_image(self):
        try:
            if self.logo_path and Path(self.logo_path).exists():
                return Image.open(self.logo_path).resize((64, 64), Image.LANCZOS).convert("RGBA")
        except Exception:
            pass
        from PIL import ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([4, 4, 60, 60], fill="#8055E8")
        d.ellipse([20, 22, 44, 42], fill="#B7A0FF")
        return img

    def _send(self, cmd):
        def run(icon=None, item=None):
            try:
                self.app_ref.tray_queue.put(cmd)
            except Exception:
                pass
        return run

    def _run_tray(self):
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Kisukisu · கிசுகிசு", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Open Kisukisu", self._send("show"), default=True),
                pystray.MenuItem("Present last script", self._send("present_last")),
                pystray.MenuItem("+ New script", self._send("new")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._send("quit")),
            )
            self.tray_icon = pystray.Icon("kisukisu", self._build_icon_image(),
                                          "Kisukisu · Your little secret.", menu)
            self.tray_icon.run()
        except Exception:
            self.tray_icon = None

    def stop(self):
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
