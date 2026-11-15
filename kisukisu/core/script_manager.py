# -*- coding: utf-8 -*-
"""
Kisukisu — Script library (local-first).

Scripts are stored as JSON files in ~/.kisukisu/scripts/.
* Atomic writes (a crash can never leave a half-written script)
* Soft delete: deleted scripts go to ~/.kisukisu/trash/ for 30 days
* Search, tag filter, sorting, duplicate, export, backup & restore
* Remembers where you stopped reading in each script
"""

import os
import re
import json
import time
import uuid
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Any

from .document_parser import DocumentParser, word_count
from .config import default_home

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
TRASH_DAYS = 30
SUPPORTED_IMPORTS = (".md", ".markdown", ".txt", ".docx", ".pdf")


def _atomic_write_json(path: Path, data: Any):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


class ScriptManager:
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self.base_dir = Path(storage_dir)
        else:
            self.base_dir = default_home() / "scripts"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.trash_dir = self.base_dir / "_trash"
        self.trash_dir.mkdir(parents=True, exist_ok=True)
        self.last_error = ""
        self.ensure_default_seeds()
        self.purge_old_trash()

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def valid_id(script_id) -> bool:
        return isinstance(script_id, str) and bool(_ID_RE.match(script_id))

    def _path(self, script_id: str) -> Path:
        if not self.valid_id(script_id):
            raise ValueError("Invalid script id")
        return self.base_dir / f"{script_id}.json"

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:8]

    # ── read ─────────────────────────────────────────────────────
    def list_scripts(self, search_query: str = "", tag: Optional[str] = None,
                     sort: str = "recent") -> List[Dict[str, Any]]:
        q = (search_query or "").strip().lower()
        scripts = []
        for file in self.base_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                if tag and tag not in data.get("tags", []):
                    continue
                if q:
                    hay = " ".join([
                        data.get("title", ""), data.get("description", ""),
                        data.get("raw_content", ""), " ".join(data.get("tags", [])),
                    ]).lower()
                    if q not in hay:
                        continue
                scripts.append(data)
            except Exception:
                continue

        if sort == "title":
            scripts.sort(key=lambda s: s.get("title", "").lower())
        elif sort == "longest":
            scripts.sort(key=lambda s: s.get("word_count", 0), reverse=True)
        else:
            scripts.sort(key=lambda s: s.get("updated_at", 0), reverse=True)
        return scripts

    def all_tags(self) -> List[str]:
        seen = {}
        for s in self.list_scripts():
            for t in s.get("tags", []):
                seen[t] = seen.get(t, 0) + 1
        return [t for t, _ in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0].lower()))]

    def get_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        try:
            path = self._path(script_id)
        except ValueError:
            return None
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    # ── write ────────────────────────────────────────────────────
    def save_script(self, script_data: Dict[str, Any]) -> bool:
        if not self.valid_id(script_data.get("id", "")):
            script_data["id"] = self._new_id()

        now = time.time()
        script_data.setdefault("created_at", now)
        script_data["updated_at"] = now

        if "raw_content" in script_data:
            script_data["sections"] = DocumentParser.parse_markdown_or_txt(
                script_data["raw_content"], script_data.get("title", "Script"))
            script_data["word_count"] = word_count(script_data["raw_content"])
        try:
            _atomic_write_json(self._path(script_data["id"]), script_data)
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    def update_progress(self, script_id: str, fraction: float):
        """Remember reading position without changing 'last edited'."""
        data = self.get_script(script_id)
        if not data:
            return False
        data["progress"] = max(0.0, min(1.0, float(fraction)))
        data["last_presented"] = time.time()
        try:
            _atomic_write_json(self._path(script_id), data)
            return True
        except Exception:
            return False

    def duplicate_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        data = self.get_script(script_id)
        if not data:
            return None
        copy = dict(data)
        copy["id"] = self._new_id()
        copy["title"] = f"{data.get('title', 'Script')} (copy)"
        for k in ("created_at", "progress", "last_presented"):
            copy.pop(k, None)
        return copy if self.save_script(copy) else None

    # ── trash (soft delete) ──────────────────────────────────────
    def delete_script(self, script_id: str) -> bool:
        try:
            path = self._path(script_id)
        except ValueError:
            return False
        if not path.exists():
            return False
        try:
            data = self.get_script(script_id) or {}
            data["deleted_at"] = time.time()
            _atomic_write_json(self.trash_dir / path.name, data)
            path.unlink()
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    def list_trash(self) -> List[Dict[str, Any]]:
        items = []
        for file in self.trash_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    items.append(json.load(f))
            except Exception:
                continue
        items.sort(key=lambda s: s.get("deleted_at", 0), reverse=True)
        return items

    def restore_script(self, script_id: str) -> bool:
        if not self.valid_id(script_id):
            return False
        src = self.trash_dir / f"{script_id}.json"
        if not src.exists():
            return False
        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.pop("deleted_at", None)
            _atomic_write_json(self._path(script_id), data)
            src.unlink()
            return True
        except Exception:
            return False

    def purge_script(self, script_id: str) -> bool:
        if not self.valid_id(script_id):
            return False
        f = self.trash_dir / f"{script_id}.json"
        try:
            f.unlink()
            return True
        except Exception:
            return False

    def empty_trash(self) -> int:
        n = 0
        for f in self.trash_dir.glob("*.json"):
            try:
                f.unlink()
                n += 1
            except Exception:
                pass
        return n

    def purge_old_trash(self):
        cutoff = time.time() - TRASH_DAYS * 86400
        for item in self.list_trash():
            if item.get("deleted_at", time.time()) < cutoff and item.get("id"):
                self.purge_script(item["id"])

    # ── import / export ──────────────────────────────────────────
    def import_from_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        self.last_error = ""
        path = Path(filepath)
        if not path.exists():
            self.last_error = "File not found."
            return None
        if path.suffix.lower() not in SUPPORTED_IMPORTS and path.suffix:
            # Unknown extension: still try as plain text.
            pass
        try:
            raw = DocumentParser.read_file(str(path))
        except (ValueError, ImportError) as e:
            self.last_error = str(e)
            return None
        except Exception as e:
            self.last_error = f"Could not read the file ({e})."
            return None
        if not raw.strip():
            self.last_error = "The file is empty."
            return None

        script = {
            "id": self._new_id(),
            "title": path.stem.replace("_", " ").replace("-", " ").strip().title() or "Imported Script",
            "description": f"Imported from {path.name}",
            "raw_content": raw,
            "tags": ["Imported"],
        }
        if self.save_script(script):
            return script
        self.last_error = self.last_error or "Could not save the script."
        return None

    def import_from_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        folder = Path(folder_path)
        if not folder.is_dir():
            return []
        imported = []
        for file in sorted(folder.iterdir()):
            if file.is_file() and file.suffix.lower() in SUPPORTED_IMPORTS:
                sc = self.import_from_file(str(file))
                if sc:
                    imported.append(sc)
        return imported

    def export_script(self, script: Dict[str, Any], dest: str) -> bool:
        """Export to .md / .txt / .json depending on the destination extension."""
        ext = Path(dest).suffix.lower()
        try:
            if ext == ".json":
                text = json.dumps(script, indent=2, ensure_ascii=False)
            elif ext == ".txt":
                secs = script.get("sections") or DocumentParser.parse_markdown_or_txt(
                    script.get("raw_content", ""), script.get("title", "Script"))
                text = DocumentParser.export_as_plain_text(secs)
            else:
                text = script.get("raw_content", "")
            Path(dest).write_text(text, encoding="utf-8")
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    # ── backup / restore ─────────────────────────────────────────
    def backup(self, zip_path: str, extra_files: Optional[List[Path]] = None) -> int:
        n = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in self.base_dir.glob("*.json"):
                z.write(f, f"scripts/{f.name}")
                n += 1
            for extra in extra_files or []:
                if extra.exists():
                    z.write(extra, extra.name)
        return n

    def restore(self, zip_path: str) -> int:
        """Merge scripts from a backup. Existing scripts are kept unless the backup copy is newer."""
        restored = 0
        with zipfile.ZipFile(zip_path) as z:
            for name in z.namelist():
                if not (name.startswith("scripts/") and name.endswith(".json")):
                    continue
                sid = Path(name).stem
                if name != f"scripts/{sid}.json" or not self.valid_id(sid):
                    continue            # reject anything with path tricks (.., nested folders)
                try:
                    data = json.loads(z.read(name).decode("utf-8"))
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                current = self.get_script(sid)
                if current and current.get("updated_at", 0) >= data.get("updated_at", 0):
                    continue
                data["id"] = sid
                _atomic_write_json(self._path(sid), data)
                restored += 1
        return restored

    # ── starter scripts (seeded once, never re-added after you delete them) ──
    def ensure_default_seeds(self):
        marker = self.base_dir / ".seeded"
        if marker.exists() or any(self.base_dir.glob("*.json")):
            marker.touch(exist_ok=True)
            return
        now = time.time()
        for sid, title, desc, tags, content in _SEEDS:
            self.save_script({
                "id": sid, "title": title, "description": desc,
                "raw_content": content, "tags": tags,
                "created_at": now, "updated_at": now,
            })
        marker.touch(exist_ok=True)


_SEEDS = [
    ("welcome-tour", "Welcome to Kisukisu",
     "A 1-minute tour. Press Present and try Space, ← →, and M.",
     ["Start here"],
     """## Welcome
[CUE: Press Space to start the auto-scroll — press it again to pause]
Welcome to Kisukisu — your little secret.

This is the reader. The paragraph you are speaking stays bright; everything else fades back so your eyes always know where you are.

## Move around
[CUE: Use the arrow keys, or the toolbar below]
Press the right arrow for the next section, the left arrow to go back. Plus and minus change the text size. Square brackets like [SWITCH SLIDE] are cues — they stand out so you never miss a slide change.

## Make it yours
[CUE: Open Appearance in the library window]
Change fonts, colours, spacing, opacity, the reading ruler and every keyboard shortcut. Press M for compact mode, T to pin the window above your slides, and F11 for fullscreen.

## You are ready
[CUE: Smile]
Create a new script, import a Word, PDF, Markdown or text file, and present with confidence. Your words never leave this computer.
"""),
    ("tamil-demo", "கிசுகிசு அறிமுகம் (Tamil Demo)",
     "தமிழ் யூனிகோட் ஆதரவு மாதிரி — Tamil Unicode sample.",
     ["Tamil", "Demo"],
     """## பிரிவு 1 — வணக்கம்
[CUE: நேயர்களுக்கு வணக்கம் செலுத்துங்கள்]
**SAY:**
அனைவருக்கும் வணக்கம்! கிசுகிசு (Kisukisu) செயலிக்கு உங்களை அன்போடு வரவேற்கிறோம்.

இது உங்கள் தனிப்பட்ட மேடை உதவியாளர். உங்கள் குறிப்புகள் உங்கள் கணினியிலேயே பாதுகாப்பாக இருக்கும்.

---

## பிரிவு 2 — முதன்மை நன்மைகள்
[CUE: அடுத்த திரைக்கு மாறவும்]
**SAY:**
1. முழுமையான தனிநபர் தனியுரிமை.
2. இணைய வசதி இல்லாமலும் முழுமையாக இயங்கும்.
3. எந்த கூட்ட மென்பொருளுடனும் தடையின்றிப் பயன்படுத்தலாம்."""),
]
