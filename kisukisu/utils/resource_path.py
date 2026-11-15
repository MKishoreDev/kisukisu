# -*- coding: utf-8 -*-
"""
Kisukisu — Resource Path Resolver
Handles development (source), installed package (pip/site-packages),
and PyInstaller bundle paths seamlessly.
"""
import os
import sys


def resource_path(*parts: str) -> str:
    """
    Get the absolute path to a resource.
    Works in:
      - PyInstaller bundle: relative to sys._MEIPASS
      - Installed package (pip): relative to kisukisu/ package directory
      - Development: relative to project root
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, *parts)

    # 1. Check inside package folder (e.g. site-packages/kisukisu/assets/...)
    pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    pkg_asset = os.path.join(pkg_dir, *parts)
    if os.path.exists(pkg_asset):
        return pkg_asset

    # 2. Check project root (e.g. repo_root/assets/...)
    root_dir = os.path.abspath(os.path.join(pkg_dir, ".."))
    root_asset = os.path.join(root_dir, *parts)
    if os.path.exists(root_asset):
        return root_asset

    # Fallback to project root path
    return os.path.join(root_dir, *parts)
