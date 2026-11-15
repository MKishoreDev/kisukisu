# -*- coding: utf-8 -*-
"""
Unit tests for DocumentParser in Kisukisu.
"""

import unittest
from kisukisu.core.document_parser import DocumentParser

class TestDocumentParser(unittest.TestCase):
    def test_empty_text(self):
        sections = DocumentParser.parse_markdown_or_txt("", "Empty")
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["title"], "Empty")

    def test_slide_markdown_parsing(self):
        markdown_sample = """
## Slide 1 — Introduction to Kisukisu
**ACTION:** [CLICK PRESENT]
**SAY:** Hello and welcome to today's presentation.

## Slide 2 — Architecture Overview
**ACTION:** [SWITCH TO SLIDE 2]
**SAY:** In this section we cover local-first design.
"""
        sections = DocumentParser.parse_markdown_or_txt(markdown_sample, "Test Doc")
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["num"], 1)
        self.assertIn("Introduction to Kisukisu", sections[0]["title"])
        self.assertIn("[CLICK PRESENT]", sections[0]["action"])
        self.assertIn("Hello and welcome", sections[0]["say"])

        self.assertEqual(sections[1]["num"], 2)
        self.assertIn("Architecture Overview", sections[1]["title"])

    def test_cue_extraction(self):
        sample = """
## Demo Section
[NEXT SLIDE]
[SWITCH TO BROWSER]
Here is the spoken presentation body.
"""
        sections = DocumentParser.parse_markdown_or_txt(sample, "Cues")
        self.assertEqual(len(sections), 1)
        self.assertIn("[NEXT SLIDE]", sections[0]["action"])
        self.assertIn("[SWITCH TO BROWSER]", sections[0]["action"])
        self.assertIn("spoken presentation body", sections[0]["say"])

    def test_tamil_unicode_support(self):
        tamil_sample = """
## பகுதி 1: வரவேற்பு
[CUE: புன்னகையுடன் பேசவும்]
**SAY:** அனைவருக்கும் இனிய வணக்கம்! கிசுகிசு செயலியைப் பற்றிப் பேசவுள்ளேன்.
"""
        sections = DocumentParser.parse_markdown_or_txt(tamil_sample, "தமிழ் உரை")
        self.assertEqual(len(sections), 1)
        self.assertIn("பகுதி 1", sections[0]["title"])
        self.assertIn("அனைவருக்கும் இனிய வணக்கம்", sections[0]["say"])

    def test_triple_dash_split(self):
        text = "First block\n---\nSecond block\n---\nThird block"
        sections = DocumentParser.parse_markdown_or_txt(text, "Dashes")
        self.assertEqual(len(sections), 3)

    def test_export_markdown(self):
        sections = [
            {"num": 1, "title": "Intro", "action": "[START]", "say": "Welcome everyone."},
            {"num": 2, "title": "Conclusion", "action": "[FINISH]", "say": "Thank you."}
        ]
        exported = DocumentParser.export_as_markdown(sections)
        self.assertIn("## Slide 1 — Intro", exported)
        self.assertIn("**ACTION:** [START]", exported)
        self.assertIn("**SAY:** Welcome everyone.", exported)

if __name__ == "__main__":
    unittest.main()
