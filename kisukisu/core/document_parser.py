# -*- coding: utf-8 -*-
"""
Kisukisu — Document parser & importer.

* Markdown / plain text -> structured sections (title, cue, spoken text, on-screen note)
* Recognises cues:  [CUE: ...]  [SWITCH SLIDE]  **ACTION:** ...  ⚡ CUE: ...
* Spoken text via **SAY:**  — or simply everything that isn't a cue/heading
* Unicode safe (Tamil, other Indic scripts, emoji)
* Import helpers for .docx (standard library only) and .pdf (optional `pypdf`)
* Export to Markdown / plain text
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

# ── regexes ──────────────────────────────────────────────────────
_HEADER_RE = re.compile(
    r"(?:^|\n)##[ \t]+"
    r"(?:(?:Slide|Section|Part|Step)[ \t]+)?"
    r"(?:(\d+)(?:[ \t]*[\u2014\u2013\-:.][ \t]*|[ \t]*(?=\n|$)))?"
    r"([^\n]*)"
)
_CUE_LINE_RE = re.compile(r"^[ \t]*(?:⚡[ \t]*CUE:[^\n]*|\[[^\]\n]{1,80}\])[ \t]*$", re.MULTILINE)
_ONSCREEN_RE = re.compile(
    r"\*\*On screen:\*\*(.*?)(?=\*\*(?:ACTION|Action):\*\*|\*\*(?:SAY|Say):\*\*|\Z)", re.DOTALL)
_ACTION_RE = re.compile(r"\*\*(?:ACTION|Action):\*\*(.*?)(?=\*\*(?:SAY|Say):\*\*|\Z)", re.DOTALL)
_SAY_RE = re.compile(r"\*\*(?:SAY|Say):\*\*(.*)", re.DOTALL)
_RULE_RE = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$", re.MULTILINE)


def clean_inline(text: str) -> str:
    """Remove Markdown emphasis markers so the reader shows clean prose."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\w)__(.+?)__(?!\w)", r"\1", text, flags=re.DOTALL)
    return text


def format_cue(raw: str) -> str:
    """'[CUE: Smile]' -> 'Smile',  '[NEXT SLIDE]' -> 'NEXT SLIDE'  (for display)."""
    raw = raw.strip()
    raw = re.sub(r"^⚡\s*CUE:\s*", "", raw)
    raw = re.sub(r"^\[\s*(?:CUE:\s*)?", "[", raw)
    raw = raw.replace("[", "").replace("]", "")
    return re.sub(r"\s+", " ", raw).strip()


def word_count(text: str) -> int:
    return len(text.split())


def estimate_minutes(words: int, wpm: int = 150) -> float:
    return words / max(1, wpm)


def format_minutes(minutes: float) -> str:
    if minutes < 1:
        return "< 1 min"
    return f"{int(round(minutes))} min"


class DocumentParser:
    # ── parsing ──────────────────────────────────────────────────
    @staticmethod
    def parse_markdown_or_txt(raw_text: str, filename: str = "Script") -> List[Dict[str, Any]]:
        raw_text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
        if not raw_text.strip():
            return [{
                "num": 1, "title": filename, "action": "",
                "say": "This script is empty. Open the editor and add some text.",
                "on_screen": "",
            }]

        matches = list(_HEADER_RE.finditer(raw_text))

        if not matches:
            dash_parts = [p for p in re.split(r"\n+[ \t]*-{3,}[ \t]*\n+", raw_text) if p.strip()]
            if len(dash_parts) > 1:
                return [DocumentParser._extract_section_data(part, i, f"Section {i}")
                        for i, part in enumerate(dash_parts, 1)]
            return [DocumentParser._extract_section_data(raw_text, 1, filename)]

        sections = []
        # Anything written before the first heading becomes an intro section.
        preamble = raw_text[:matches[0].start()].strip()
        if preamble:
            sections.append(DocumentParser._extract_section_data(preamble, 1, "Introduction"))

        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            num_str = m.group(1)
            idx = len(sections) + 1
            num = int(num_str) if num_str else idx
            title = (m.group(2) or "").strip() or f"Section {num}"
            sections.append(DocumentParser._extract_section_data(raw_text[start:end], num, title))
        return sections

    @staticmethod
    def _extract_section_data(block: str, num: int, title: str) -> Dict[str, Any]:
        os_match = _ONSCREEN_RE.search(block)
        os_text = clean_inline(os_match.group(1).strip()) if os_match else ""

        act_match = _ACTION_RE.search(block)
        if act_match:
            action_text = clean_inline(act_match.group(1).strip())
        else:
            cues = [c.strip() for c in _CUE_LINE_RE.findall(block)]
            action_text = "  ·  ".join(cues)

        say_match = _SAY_RE.search(block)
        body = say_match.group(1) if say_match else block
        if not say_match:
            body = re.sub(r"(?:^|\n)##[^\n]*", "", body, count=1)
            body = _ONSCREEN_RE.sub("", body)
            body = _ACTION_RE.sub("", body)
        body = _CUE_LINE_RE.sub("", body)
        body = _RULE_RE.sub("", body)
        body = clean_inline(body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()

        return {
            "num": num, "title": title, "action": action_text,
            "say": body, "on_screen": os_text, "raw_block": block,
        }

    # ── file import ──────────────────────────────────────────────
    @staticmethod
    def read_file(path: str) -> str:
        """Read .md/.txt/.docx/.pdf into text. Raises ValueError/ImportError with a friendly message."""
        p = Path(path)
        ext = p.suffix.lower()
        if ext == ".docx":
            return DocumentParser.extract_docx(p)
        if ext == ".pdf":
            return DocumentParser.extract_pdf(p)
        for enc in ("utf-8-sig", "utf-16", "cp1252"):
            try:
                return p.read_text(encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return p.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def extract_docx(path) -> str:
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        wq = "{%s}" % ns["w"]
        try:
            with zipfile.ZipFile(path) as z:
                xml_bytes = z.read("word/document.xml")
        except (zipfile.BadZipFile, KeyError):
            raise ValueError("That doesn't look like a valid .docx file.")
        root = ET.fromstring(xml_bytes)
        lines = []
        for p in root.iter(wq + "p"):
            style_el = p.find("w:pPr/w:pStyle", ns)
            style = (style_el.get(wq + "val") if style_el is not None else "") or ""
            parts = []
            for el in p.iter():
                if el.tag == wq + "t" and el.text:
                    parts.append(el.text)
                elif el.tag in (wq + "tab", wq + "br"):
                    parts.append(" ")
            text = "".join(parts).strip()
            if not text:
                lines.append("")
                continue
            low = style.lower()
            if low in ("title", "heading1", "heading 1", "heading2", "heading 2"):
                lines.append(f"\n## {text}\n")
            else:
                lines.append(text)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

    @staticmethod
    def extract_pdf(path) -> str:
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            raise ImportError("PDF import needs the 'pypdf' package.  Install it with:  pip install pypdf")
        try:
            reader = PdfReader(str(path))
            pages = [(pg.extract_text() or "").strip() for pg in reader.pages]
        except Exception as e:
            raise ValueError(f"Could not read that PDF ({e}).")
        text = "\n\n".join(p for p in pages if p)
        if not text.strip():
            raise ValueError("No selectable text found in that PDF (it may be a scan).")
        return text

    # ── export ───────────────────────────────────────────────────
    @staticmethod
    def export_as_markdown(sections: List[Dict[str, Any]]) -> str:
        blocks = []
        for s in sections:
            header = f"## Slide {s['num']} — {s['title']}\n\n"
            os_part = f"**On screen:** {s['on_screen']}\n\n" if s.get("on_screen") else ""
            act_part = f"**ACTION:** {s['action']}\n\n" if s.get("action") else ""
            say_part = f"**SAY:** {s.get('say', '')}\n"
            blocks.append(header + os_part + act_part + say_part)
        return "\n---\n\n".join(blocks)

    @staticmethod
    def export_as_plain_text(sections: List[Dict[str, Any]]) -> str:
        lines = []
        for s in sections:
            lines.append(f"=== {s['num']}. {s['title']} ===")
            if s.get("action"):
                lines.append(f"CUE: {format_cue(s['action'])}")
            lines.append("")
            lines.append(s.get("say", ""))
            lines.append("\n" + "-" * 50 + "\n")
        return "\n".join(lines)
