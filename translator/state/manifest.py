"""Manifest — document metadata and pipeline configuration."""
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime


def create_project_slug(input_path: Path) -> str:
    """
    Create safe project slug from input filename.

    Format: <sanitized_stem>_<YYYYMMDD>_<short_hash>

    Rules:
    - No slashes, quotes, colons, control chars
    - Spaces replaced with _
    - Cyrillic transliterated or replaced with safe slug
    """
    stem = input_path.stem

    # Sanitize: remove unsafe chars
    safe_stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', stem)
    safe_stem = safe_stem.strip('._ ')

    # Replace multiple underscores with single
    safe_stem = re.sub(r'_+', '_', safe_stem)

    # Truncate if too long (filename limit)
    if len(safe_stem) > 50:
        safe_stem = safe_stem[:50]

    # Replace Cyrillic with approximate transliteration
    # Simple approach: if has Cyrillic, create generic slug
    if re.search(r'[\u0400-\u04FF]', safe_stem):
        # Check if it's mostly Cyrillic — use hash suffix instead
        cyrillic_ratio = len(re.findall(r'[\u0400-\u04FF]', safe_stem)) / len(safe_stem)
        if cyrillic_ratio > 0.5:
            safe_stem = "doc"

    # Date
    date_str = datetime.now().strftime("%Y%m%d")

    # Short hash of full path for uniqueness
    path_hash = hashlib.md5(str(input_path.resolve()).encode()).hexdigest()[:6]

    return f"{safe_stem}_{date_str}_{path_hash}"


class Manifest:
    """Stores document metadata and pipeline configuration."""

    def __init__(self, workspace: Path, input_path: Path, lang: str = None):
        self.workspace = workspace
        self.input_path = input_path.resolve()
        self.source_lang = lang or "auto"
        self.target_lang = "ru"
        self.created_at = datetime.now().isoformat()
        self.version = "0.1.0"

        # File info
        self.original_size = input_path.stat().st_size
        self.original_extension = input_path.suffix.lower()

        # Project slug
        self.project_slug = create_project_slug(input_path)

        # Supported formats check
        supported = {'.txt', '.md', '.markdown', '.docx', '.html', '.htm', '.pdf'}
        self.format_supported = self.original_extension in supported

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "workspace": str(self.workspace),
            "project_slug": self.project_slug,
            "input": {
                "path": str(self.input_path),
                "size": self.original_size,
                "extension": self.original_extension,
                "format_supported": self.format_supported
            },
            "languages": {
                "source": self.source_lang,
                "target": self.target_lang
            },
            "created_at": self.created_at
        }

    def save(self):
        path = self.workspace / "state" / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, workspace: Path) -> "Manifest":
        path = workspace / "state" / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Reconstruct
        input_path = Path(data["input"]["path"])
        manifest = cls(
            Path(data["workspace"]),
            input_path,
            data["languages"]["source"]
        )
        return manifest