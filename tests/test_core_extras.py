# -*- coding: utf-8 -*-
"""Tests for the v1.1 core: geometry, shortcuts, themes, config hardening, library features."""

import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from kisukisu.core.config import ConfigManager, DEFAULT_SETTINGS
from kisukisu.core.geometry import parse_geometry, format_geometry, clamp_rect
from kisukisu.core import shortcuts as sc
from kisukisu.core.script_manager import ScriptManager
from kisukisu.core.document_parser import DocumentParser, format_cue
from kisukisu.core.monitor_manager import parse_xrandr
from kisukisu.ui import themes as T

MON = [{"id": 0, "x": 0, "y": 0, "width": 1920, "height": 1080, "is_primary": True}]
TWO = MON + [{"id": 1, "x": 1920, "y": 0, "width": 2560, "height": 1440, "is_primary": False}]


class TestGeometry(unittest.TestCase):
    def test_parse_and_format(self):
        self.assertEqual(parse_geometry("580x460+60+-30"), (580, 460, 60, -30))   # Tk's "+-30" form
        self.assertEqual(parse_geometry("580x460-10+5"), (580, 460, -10, 5))
        self.assertIsNone(parse_geometry("garbage"))
        self.assertEqual(format_geometry(580, 460, 60, -30), "580x460+60-30")

    def test_never_offscreen(self):
        w, h, x, y = clamp_rect(640, 560, 99999, 99999, MON)
        self.assertTrue(0 <= x <= 1920 - w and 0 <= y <= 1080 - h)
        w, h, x, y = clamp_rect(640, 560, -5000, -5000, MON)
        self.assertTrue(x >= 0 and y >= 0)

    def test_never_bigger_than_screen(self):
        w, h, x, y = clamp_rect(9000, 9000, 0, 0, MON)
        self.assertLessEqual(w, 1920)
        self.assertLessEqual(h, 1080)

    def test_unplaced_window_gets_anchor(self):
        w, h, x, y = clamp_rect(760, 180, None, None, MON, anchor="top", min_h=110)
        self.assertEqual(h, 180)
        self.assertEqual(x, (1920 - 760) // 2)
        self.assertLess(y, 60)

    def test_disconnected_monitor_recovers(self):
        # remembered a spot on monitor 2, but only monitor 1 is connected now
        w, h, x, y = clamp_rect(640, 560, 2500, 100, MON)
        self.assertTrue(x + w <= 1920)

    def test_second_monitor_target(self):
        w, h, x, y = clamp_rect(640, 560, None, None, TWO, target_index=1)
        self.assertGreaterEqual(x, 1920)

    def test_dpi_scale(self):
        w, h, x, y = clamp_rect(1500, 900, 0, 0, MON, scale=1.5)   # 2250x1350 physical > screen
        self.assertLessEqual(w * 1.5, 1920 + 1)
        self.assertLessEqual(h * 1.5, 1080 + 1)


class TestShortcuts(unittest.TestCase):
    def test_defaults_are_unique(self):
        keys = [k.lower() for k in sc.DEFAULT_SHORTCUTS.values()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_action_has_label(self):
        self.assertEqual(set(sc.DEFAULT_SHORTCUTS), set(sc.LABELS))

    def test_conflict_detection(self):
        self.assertEqual(sc.find_conflict(sc.DEFAULT_SHORTCUTS, "toggle_pin", "m"), "toggle_compact")
        self.assertIsNone(sc.find_conflict(sc.DEFAULT_SHORTCUTS, "toggle_pin", "t"))

    def test_sequences_and_pretty(self):
        self.assertIn("<Control-W>", sc.tk_sequences("Control-w"))
        self.assertEqual(sc.pretty("Control-w"), "Ctrl + W")
        self.assertEqual(sc.pretty("space"), "Space")

    def test_key_from_event(self):
        ev = type("E", (), {"keysym": "w", "state": 0x4})()
        self.assertEqual(sc.key_from_event(ev), "Control-w")
        self.assertIsNone(sc.key_from_event(type("E", (), {"keysym": "Shift_L", "state": 0})()))


class TestConfigHardening(unittest.TestCase):
    def test_values_are_clamped(self):
        with tempfile.TemporaryDirectory() as d:
            c = ConfigManager(d)
            self.assertEqual(c.set("font_size", 9999), 96)
            self.assertEqual(c.set("opacity", 0.0), 0.40)
            self.assertEqual(c.set("auto_scroll_speed", "7"), 7)
            self.assertEqual(c.set("text_align", "banana"), "left")

    def test_corrupt_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "config.json").write_text("{ not json", encoding="utf-8")
            c = ConfigManager(d)
            self.assertEqual(c.get("theme"), "midnight")
            self.assertTrue(any(p.name.startswith("config.corrupt") for p in Path(d).iterdir()))

    def test_bad_types_fall_back(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "config.json").write_text(json.dumps({"font_size": "huge", "shortcuts": "x", "reader_x": "q"}), encoding="utf-8")
            c = ConfigManager(d)
            self.assertEqual(c.get("font_size"), DEFAULT_SETTINGS["font_size"])
            self.assertEqual(c.get("shortcuts"), sc.DEFAULT_SHORTCUTS)

    def test_partial_shortcut_overrides_merge(self):
        with tempfile.TemporaryDirectory() as d:
            c = ConfigManager(d)
            c.set_shortcut("toggle_pin", "p")
            c2 = ConfigManager(d)
            self.assertEqual(c2.get("shortcuts")["toggle_pin"], "p")
            self.assertEqual(c2.get("shortcuts")["play_pause"], "space")

    def test_reset_keeps_onboarding(self):
        with tempfile.TemporaryDirectory() as d:
            c = ConfigManager(d)
            c.set("onboarding_complete", True)
            c.set("font_size", 40)
            c.reset_defaults()
            self.assertEqual(c.get("font_size"), 24)
            self.assertTrue(c.get("onboarding_complete"))

    def test_window_remembering_none(self):
        with tempfile.TemporaryDirectory() as d:
            c = ConfigManager(d)
            self.assertIsNone(c.get("reader_x"))
            c.set("reader_x", -20)
            self.assertEqual(ConfigManager(d).get("reader_x"), -20)


class TestThemes(unittest.TestCase):
    def test_hex_helpers(self):
        self.assertEqual(T.normalize_hex("abc"), "#AABBCC")
        self.assertEqual(T.normalize_hex("zzz", "#000000"), "#000000")
        self.assertTrue(T.is_hex("#8055E8"))
        self.assertFalse(T.is_hex("8055E8"))

    def test_on_accent_is_readable(self):
        self.assertEqual(T.readable_on("#44FF44"), "#000000")
        self.assertEqual(T.readable_on("#8055E8"), "#FFFFFF")
        self.assertEqual(T.THEMES["terminal"].on_accent, "#000000")

    def test_derived_theme_complete(self):
        t = T.derive_theme("x", "X", False, "#FAF7F0", "#2D2420", "#E11D48")
        for field in t.__dataclass_fields__:
            self.assertTrue(getattr(t, field) not in (None, ""), field)
        self.assertFalse(t.dark)

    def test_custom_roundtrip_and_import_export(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["KISUKISU_HOME"] = d
            try:
                T.save_custom_theme("#10B981", "#0B1220", None, "#E5E7EB", "Emerald", True)
                self.assertEqual(T.get_theme("custom").accent, "#10B981")
                out = os.path.join(d, "t.json")
                self.assertTrue(T.export_theme(out))
                self.assertIsNotNone(T.import_theme(out))
                Path(d, "bad.json").write_text("[1,2,3]", encoding="utf-8")
                self.assertIsNone(T.import_theme(os.path.join(d, "bad.json")))
            finally:
                os.environ.pop("KISUKISU_HOME", None)


class TestParserV11(unittest.TestCase):
    def test_bracket_cue_with_colon_is_detected(self):
        s = DocumentParser.parse_markdown_or_txt("## A\n[CUE: Smile now]\n**SAY:** Hi\n", "x")[0]
        self.assertIn("Smile now", s["action"])
        self.assertEqual(s["say"], "Hi")
        self.assertNotIn("CUE", s["say"])

    def test_cue_lines_removed_from_spoken_text(self):
        s = DocumentParser.parse_markdown_or_txt("## A\n[NEXT SLIDE]\nHello there.\n", "x")[0]
        self.assertEqual(s["say"], "Hello there.")

    def test_markdown_noise_removed(self):
        s = DocumentParser.parse_markdown_or_txt("## A\n**SAY:** Hello **world**.\n\n---\n", "x")[0]
        self.assertEqual(s["say"], "Hello world.")

    def test_section_headers(self):
        secs = DocumentParser.parse_markdown_or_txt("## Section 1 — The Spark\na\n\n## 2024 Roadmap\nb\n\n## Section 3\nc", "x")
        self.assertEqual([s["title"] for s in secs], ["The Spark", "2024 Roadmap", "Section 3"])
        self.assertEqual([s["num"] for s in secs], [1, 2, 3])

    def test_preamble_becomes_intro(self):
        secs = DocumentParser.parse_markdown_or_txt("Intro text\n\n## A\nbody", "x")
        self.assertEqual(secs[0]["title"], "Introduction")
        self.assertEqual(len(secs), 2)

    def test_format_cue(self):
        self.assertEqual(format_cue("[CUE: Smile]"), "Smile")
        self.assertEqual(format_cue("[NEXT SLIDE]"), "NEXT SLIDE")
        self.assertEqual(format_cue("⚡ CUE: Go"), "Go")

    def test_crlf_files(self):
        secs = DocumentParser.parse_markdown_or_txt("## A\r\nx\r\n\r\n## B\r\ny", "x")
        self.assertEqual(len(secs), 2)

    def test_docx_import(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "talk.docx")
            xml = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                   '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Opening</w:t></w:r></w:p>'
                   '<w:p><w:r><w:t>Hello </w:t></w:r><w:r><w:t>தமிழ்</w:t></w:r></w:p></w:body></w:document>')
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("word/document.xml", xml)
            text = DocumentParser.read_file(path)
            self.assertIn("## Opening", text)
            self.assertIn("Hello தமிழ்", text)

    def test_bad_docx_message(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.docx")
            Path(p).write_text("not a zip")
            with self.assertRaises(ValueError):
                DocumentParser.extract_docx(p)


class TestLibraryV11(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="kisu_")
        self.m = ScriptManager(storage_dir=self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_seeds_only_once(self):
        for s in self.m.list_scripts():
            self.m.delete_script(s["id"])
        self.assertEqual(self.m.list_scripts(), [])
        self.assertEqual(len(ScriptManager(storage_dir=self.dir).list_scripts()), 0)   # not re-seeded

    def test_path_traversal_ids_rejected(self):
        self.assertIsNone(self.m.get_script("../../etc/passwd"))
        self.assertFalse(self.m.delete_script("../x"))
        self.assertFalse(self.m.restore_script("a/b"))

    def test_duplicate_and_sort_and_tags(self):
        a = {"title": "Zebra", "raw_content": "one two three", "tags": ["x"]}
        b = {"title": "Apple", "raw_content": "one", "tags": ["y"]}
        self.m.save_script(a); self.m.save_script(b)
        titles = [s["title"] for s in self.m.list_scripts(sort="title")]
        self.assertLess(titles.index("Apple"), titles.index("Zebra"))
        self.assertEqual([s["title"] for s in self.m.list_scripts(tag="x")], ["Zebra"])
        dup = self.m.duplicate_script(a["id"])
        self.assertEqual(dup["title"], "Zebra (copy)")
        self.assertNotEqual(dup["id"], a["id"])
        self.assertIn("x", self.m.all_tags())

    def test_progress_does_not_change_updated_at(self):
        a = {"title": "T", "raw_content": "hello"}
        self.m.save_script(a)
        before = self.m.get_script(a["id"])["updated_at"]
        self.assertTrue(self.m.update_progress(a["id"], 0.42))
        got = self.m.get_script(a["id"])
        self.assertEqual(got["updated_at"], before)
        self.assertAlmostEqual(got["progress"], 0.42)

    def test_trash_purge_and_empty(self):
        a = {"title": "T", "raw_content": "hello"}
        self.m.save_script(a)
        self.m.delete_script(a["id"])
        self.assertTrue(self.m.purge_script(a["id"]))
        self.assertEqual(self.m.list_trash(), [])

    def test_backup_and_restore(self):
        a = {"title": "Keep me", "raw_content": "important"}
        self.m.save_script(a)
        zp = os.path.join(self.dir, "b.zip")
        self.assertGreaterEqual(self.m.backup(zp), 1)
        self.m.delete_script(a["id"])
        self.m.purge_script(a["id"])
        self.assertGreaterEqual(self.m.restore(zp), 1)
        self.assertEqual(self.m.get_script(a["id"])["title"], "Keep me")

    def test_restore_ignores_malicious_names(self):
        zp = os.path.join(self.dir, "evil.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("scripts/../../evil.json", "{}")
            z.writestr("scripts/ok_1.json", json.dumps({"id": "ok_1", "title": "fine", "updated_at": 1}))
        self.assertEqual(self.m.restore(zp), 1)
        self.assertFalse(Path(self.dir, "..", "evil.json").exists())

    def test_export_formats(self):
        a = {"title": "T", "raw_content": "## A\n[CUE: x]\n**SAY:** hi"}
        self.m.save_script(a)
        for ext in (".md", ".txt", ".json"):
            out = os.path.join(self.dir, "out" + ext)
            self.assertTrue(self.m.export_script(self.m.get_script(a["id"]), out))
            self.assertTrue(Path(out).read_text(encoding="utf-8"))

    def test_import_errors_are_explained(self):
        p = os.path.join(self.dir, "empty.txt")
        Path(p).write_text("   ")
        self.assertIsNone(self.m.import_from_file(p))
        self.assertIn("empty", self.m.last_error.lower())

    def test_import_folder_picks_supported_files(self):
        f = os.path.join(self.dir, "inbox"); os.mkdir(f)
        Path(f, "a.md").write_text("## A\nhi"); Path(f, "b.txt").write_text("hello"); Path(f, "c.png").write_bytes(b"x")
        self.assertEqual(len(self.m.import_from_folder(f)), 2)

    def test_atomic_write_leaves_no_tmp(self):
        self.m.save_script({"title": "T", "raw_content": "x"})
        self.assertEqual(list(Path(self.dir).glob("*.tmp")), [])


class TestMonitorParsing(unittest.TestCase):
    def test_xrandr(self):
        out = ("HDMI-1 connected 1920x1080+1920+0 (normal left inverted right x axis y axis) 527mm x 296mm\n"
               "eDP-1 connected primary 1920x1080+0+0 (normal) 344mm x 193mm\nDP-2 disconnected (normal)\n")
        mons = parse_xrandr(out)
        self.assertEqual(len(mons), 2)
        self.assertTrue(any(m["is_primary"] and m["x"] == 0 for m in mons))


class TestMacOSCompatibility(unittest.TestCase):
    def test_macos_stealth_is_safe_noop(self):
        from unittest.mock import patch
        from kisukisu.utils.win_stealth import set_capture_excluded, is_windows, set_taskbar_hidden
        with patch("sys.platform", "darwin"):
            self.assertFalse(is_windows())
            self.assertFalse(set_capture_excluded(12345, True))
            self.assertFalse(set_taskbar_hidden(12345, True))

    def test_macos_monitor_fallback(self):
        from unittest.mock import patch
        from kisukisu.core.monitor_manager import MonitorManager
        with patch("sys.platform", "darwin"):
            mons = MonitorManager.get_monitors()
            self.assertGreaterEqual(len(mons), 1)
            self.assertTrue(mons[0]["is_primary"])
            self.assertIn("width", mons[0])
            self.assertIn("height", mons[0])


if __name__ == "__main__":
    unittest.main()
