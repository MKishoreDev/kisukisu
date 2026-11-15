# -*- coding: utf-8 -*-
"""
Kisukisu — application entry point.
"""

import os
import sys
import argparse
import customtkinter as ctk

if sys.platform == "win32":
    try:
        if sys.stdout:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from . import __version__
    from .core.config import config
    from .core.script_manager import ScriptManager
    from .ui.library_view import LibraryWindow
    from .ui.themes import THEMES
    from .utils.resource_path import resource_path
except (ImportError, ValueError):            # running as a frozen script / from a different cwd
    from kisukisu import __version__
    from kisukisu.core.config import config
    from kisukisu.core.script_manager import ScriptManager
    from kisukisu.ui.library_view import LibraryWindow
    from kisukisu.ui.themes import THEMES
    from kisukisu.utils.resource_path import resource_path


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="kisukisu",
                                description="Kisukisu — Your little secret. A private presenter companion.")
    p.add_argument("-v", "--version", action="version", version=f"Kisukisu v{__version__}")
    p.add_argument("-f", "--file", type=str, help="Import a .md/.txt/.docx/.pdf file and present it.")
    p.add_argument("-s", "--script-id", type=str, help="Present an existing script by ID.")
    p.add_argument("-t", "--theme", choices=list(THEMES.keys()), help="Use a theme for this session.")
    return p.parse_args(argv)


def _logo_image(size=(80, 80)):
    try:
        from PIL import Image
        path = resource_path("assets", "logo.png")
        if os.path.exists(path):
            return ctk.CTkImage(Image.open(path).resize(size, Image.LANCZOS), size=size)
    except Exception:
        pass
    return None


def _start_tray(app):
    try:
        from .utils.tray_manager import TrayManager
    except (ImportError, ValueError):
        from kisukisu.utils.tray_manager import TrayManager
    try:
        tray = TrayManager(app, logo_path=resource_path("assets", "logo.png"))
        tray.start()
        app._tray_manager = tray
    except Exception:
        pass       # the tray is optional


def main(argv=None):
    args = parse_args(argv)
    if args.theme:
        config.set("theme", args.theme, save=False)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = LibraryWindow()
    _start_tray(app)

    sm = app.script_manager
    if not config.get("onboarding_complete", False):
        try:
            from .ui.welcome_screen import WelcomeScreen
        except (ImportError, ValueError):
            from kisukisu.ui.welcome_screen import WelcomeScreen

        def after_onboarding(action: str):
            config.set("onboarding_complete", True)
            if action == "write":
                app._create_new_script()
            elif action == "import":
                app._import_file()
            elif action == "sample":
                sc = sm.get_script("welcome-tour") or (sm.list_scripts() or [None])[0]
                if sc:
                    app.launch_presenter(sc)

        app.after(400, lambda: WelcomeScreen(app, app.theme, on_done=after_onboarding, logo_img=_logo_image()))

    if args.file and os.path.exists(args.file):
        sc = sm.import_from_file(args.file)
        if sc:
            app.after(500, lambda: app.launch_presenter(sc))
    elif args.script_id:
        sc = sm.get_script(args.script_id)
        if sc:
            app.after(500, lambda: app.launch_presenter(sc))

    app.mainloop()


if __name__ == "__main__":
    main()
