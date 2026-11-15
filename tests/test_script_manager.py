# -*- coding: utf-8 -*-
"""
Unit tests for ScriptManager in Kisukisu.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from kisukisu.core.script_manager import ScriptManager

class TestScriptManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="kisukisu_test_")
        self.manager = ScriptManager(storage_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initial_seeds(self):
        scripts = self.manager.list_scripts()
        # Seeded scripts should exist
        self.assertGreaterEqual(len(scripts), 1)

    def test_save_and_get_script(self):
        script_data = {
            "title": "My Keynote 2026",
            "description": "Opening keynote on AI tooling",
            "raw_content": "## Slide 1 — The Future\n**SAY:** AI is transforming development.",
            "tags": ["keynote", "ai"]
        }
        saved = self.manager.save_script(script_data)
        self.assertTrue(saved)
        self.assertIn("id", script_data)

        fetched = self.manager.get_script(script_data["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "My Keynote 2026")
        self.assertEqual(len(fetched["sections"]), 1)
        self.assertEqual(fetched["sections"][0]["title"], "The Future")

    def test_search_scripts(self):
        self.manager.save_script({
            "title": "Quarterly Business Review",
            "raw_content": "QBR presentation notes"
        })
        self.manager.save_script({
            "title": "Architecture Teardown",
            "raw_content": "Detailed database scaling notes"
        })

        results = self.manager.list_scripts(search_query="business")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Quarterly Business Review")

        db_results = self.manager.list_scripts(search_query="database")
        self.assertEqual(len(db_results), 1)
        self.assertEqual(db_results[0]["title"], "Architecture Teardown")

    def test_delete_script(self):
        sc = {
            "title": "To Be Deleted",
            "raw_content": "Draft notes"
        }
        self.manager.save_script(sc)
        sc_id = sc["id"]

        self.assertIsNotNone(self.manager.get_script(sc_id))
        deleted = self.manager.delete_script(sc_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.manager.get_script(sc_id))
        # soft delete: it is recoverable from the trash
        self.assertIn(sc_id, [t["id"] for t in self.manager.list_trash()])
        self.assertTrue(self.manager.restore_script(sc_id))
        self.assertIsNotNone(self.manager.get_script(sc_id))

    def test_import_file(self):
        temp_file = Path(self.test_dir) / "imported_speech.md"
        temp_file.write_text("## Slide 1 — Intro\n**SAY:** Hello world!", encoding="utf-8")

        imported = self.manager.import_from_file(str(temp_file))
        self.assertIsNotNone(imported)
        self.assertEqual(imported["title"], "Imported Speech")
        self.assertEqual(len(imported["sections"]), 1)

if __name__ == "__main__":
    unittest.main()
