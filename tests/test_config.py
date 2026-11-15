# -*- coding: utf-8 -*-
"""
Unit tests for Config and MonitorManager in Kisukisu.
"""

import tempfile
import unittest
from kisukisu.core.config import ConfigManager
from kisukisu.core.monitor_manager import MonitorManager

class TestConfigAndMonitors(unittest.TestCase):
    def test_config_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = ConfigManager(custom_path=tmpdir)
            self.assertEqual(cfg.get("theme"), "midnight")
            self.assertTrue(cfg.get("always_on_top"))
            self.assertEqual(cfg.get("font_size"), 24)

    def test_config_set_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = ConfigManager(custom_path=tmpdir)
            cfg.set("font_size", 18)
            self.assertEqual(cfg.get("font_size"), 18)

    def test_monitor_detection(self):
        monitors = MonitorManager.get_monitors()
        self.assertIsInstance(monitors, list)
        self.assertGreaterEqual(len(monitors), 1)
        self.assertIn("width", monitors[0])
        self.assertIn("height", monitors[0])

if __name__ == "__main__":
    unittest.main()
