"""Parallel translation orchestration — coordinate wave1/wave2 translation across chunks."""

import json
import threading
from pathlib import Path
from dataclasses import dataclass

from ..backends import get_backend, default_backend, BackendResult


@dataclass
class ChunkResult:
    chunk_id: str
    wave: int
    success: bool
    result: BackendResult | None = None
    error: str | None = None
    retries: int = 0


class ParallelTranslator:
    """Orchestrate parallel chunk translation with configurable concurrency."""

    def __init__(
        self,
        project_dir: Path,
        backend_name: str = "mock",
        max_workers: int = 3,
        retry_count: int = 1,
    ):
        self.project_dir = Path(project_dir)
        self.max_workers = max_workers
        self.retry_count = retry_count
        self._semaphore = threading.Semaphore(max_workers)
        self._results: list[ChunkResult] = []

    def translate_wave(
        self,
        wave: int,
        backend_name: str = "mock",
        chunk_ids: list[str] | None = None,
    ) -> list[ChunkResult]:
        """Translate all chunks for a given wave in parallel.

        Args:
            wave: 1 or 2
            backend_name: name of backend to use
            chunk_ids: specific chunk IDs to translate (None = all incomplete)

        Returns:
            list of ChunkResult for all chunks
        """
        manifest_path = self.project_dir / "chunks" / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found at {manifest_path}")

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Filter chunks to process
        if chunk_ids:
            chunks_to_process = [c for c in manifest["chunks"] if c["id"] in chunk_ids]
        else:
            status_key = "wave1_status" if wave == 1 else "wave2_status"
            chunks_to_process = [c for c in manifest["chunks"] if c.get(status_key) != "completed"]

        if not chunks_to_process:
            return []

        # Get backend
        if backend_name == "mock":
            backend = default_backend()
        else:
            backend = get_backend(backend_name)

        # Load foundation files
        foundation = self._load_foundation()

        # Load context
        context_map = self._load_context_map()

        results: list[ChunkResult] = []
        threads: list[threading.Thread] = []

        def translate_one(chunk: dict) -> ChunkResult:
            with self._semaphore:
                return self._translate_single(
                    chunk=chunk,
                    wave=wave,
                    backend=backend,
                    foundation=foundation,
                    context_map=context_map,
                )

        for chunk in chunks_to_process:
            t = threading.Thread(
                target=lambda c=chunk: results.append(translate_one(c))
            )
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # Persist results to manifest and wave directories
        self._persist_results(results, wave)

        return results

    def _translate_single(
        self,
        chunk: dict,
        wave: int,
        backend,
        foundation: dict,
        context_map: dict,
    ) -> ChunkResult:
        """Translate a single chunk with retry."""
        chunk_id = chunk["id"]

        # Load source chunk
        source_path = self.project_dir / "chunks" / "source" / f"{chunk_id}.md"
        if not source_path.exists():
            return ChunkResult(
                chunk_id=chunk_id,
                wave=wave,
                success=False,
                error=f"source chunk not found: {source_path}",
            )

        chunk_text = source_path.read_text(encoding="utf-8")
        # Strip YAML frontmatter
        chunk_text = self._strip_frontmatter(chunk_text)

        context = context_map.get(chunk_id, {})
        previous_context = context.get("previous")
        next_context = context.get("next")

        # For wave2, load wave1 result
        if wave == 2:
            wave1_path = self.project_dir / "chunks" / "translated" / "wave1" / f"{chunk_id}.md"
            if wave1_path.exists():
                # Prepend wave1 result for refinement instruction
                wave1_text = wave1_path.read_text(encoding="utf-8")
                wave1_text = self._strip_frontmatter(wave1_text)
                # Add wave1 as reference for the prompt
                # Actually the backend handles this via its prompt builder

        retries = 0
        last_error = None

        while retries <= self.retry_count:
            try:
                result = backend.translate_chunk(
                    chunk_text=chunk_text,
                    chunk_id=chunk_id,
                    wave=wave,
                    glossary=foundation.get("glossary"),
                    style=foundation.get("style"),
                    entities=foundation.get("entities"),
                    previous_context=previous_context,
                    next_context=next_context,
                )

                # Validate
                if len(result.text) < len(chunk_text) * 0.1:
                    raise ValueError(f"Translation suspiciously short: {len(result.text)} vs {len(chunk_text)}")

                # Write to wave directory
                wave_dir = self.project_dir / "chunks" / "translated" / f"wave{wave}"
                wave_dir.mkdir(parents=True, exist_ok=True)

                output_path = wave_dir / f"{chunk_id}.md"
                content = self._make_frontmatter(chunk_id, wave, result.backend_name) + result.text
                output_path.write_text(content, encoding="utf-8")

                return ChunkResult(
                    chunk_id=chunk_id,
                    wave=wave,
                    success=True,
                    result=result,
                    retries=retries,
                )

            except Exception as e:
                last_error = str(e)
                retries += 1

        return ChunkResult(
            chunk_id=chunk_id,
            wave=wave,
            success=False,
            error=last_error,
            retries=retries,
        )

    def _load_foundation(self) -> dict:
        """Load foundation files into a dict."""
        foundation_dir = self.project_dir / "foundation"
        result = {}
        for key in ["glossary", "style", "entities"]:
            path = foundation_dir / f"{key}.md"
            result[key] = path.read_text(encoding="utf-8") if path.exists() else None
        return result

    def _load_context_map(self) -> dict:
        """Load all context files into a dict keyed by chunk_id."""
        context_dir = self.project_dir / "chunks" / "context"
        if not context_dir.exists():
            return {}

        result = {}
        for path in context_dir.glob("*.context.md"):
            chunk_id = path.stem.replace(".context", "")
            content = path.read_text(encoding="utf-8")
            # Parse previous/next from content
            prev = self._extract_context_section(content, "Previous context")
            next_ctx = self._extract_context_section(content, "Next context")
            result[chunk_id] = {"previous": prev, "next": next_ctx}

        return result

    def _extract_context_section(self, content: str, section: str) -> str | None:
        """Extract a section from context file."""
        import re
        pattern = rf"## {section}\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            text = match.group(1).strip()
            return text if text and text != "None" else None
        return None

    def _strip_frontmatter(self, text: str) -> str:
        """Strip YAML frontmatter from markdown."""
        import re
        return re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL).strip()

    def _make_frontmatter(self, chunk_id: str, wave: int, backend_name: str) -> str:
        from datetime import datetime
        return f"---\nchunk_id: {chunk_id}\nwave: {wave}\nbackend: {backend_name}\ntranslated_at: {datetime.utcnow().isoformat()}Z\n---\n\n"

    def _persist_results(self, results: list[ChunkResult], wave: int) -> None:
        """Update manifest with translation results and backend metadata."""
        manifest_path = self.project_dir / "chunks" / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        from datetime import datetime
        now_iso = datetime.utcnow().isoformat() + "Z"
        status_key = f"wave{wave}_status"
        backend_key = f"wave{wave}_backend"
        model_key = f"wave{wave}_model"
        ts_key = f"wave{wave}_translated_at"
        error_key = f"wave{wave}_error"

        for chunk_meta in manifest["chunks"]:
            for res in results:
                if res.chunk_id == chunk_meta["id"]:
                    if res.success:
                        chunk_meta[status_key] = "completed"
                        if res.result:
                            chunk_meta[backend_key] = res.result.backend_name
                            if res.result.model:
                                chunk_meta[model_key] = res.result.model
                            chunk_meta[ts_key] = now_iso
                        # Clean any previous error
                        chunk_meta.pop(error_key, None)
                    else:
                        chunk_meta[status_key] = "failed"
                        chunk_meta[error_key] = res.error
                    break

        # Project-level metadata (from first successful result)
        successful_results = [r for r in results if r.success and r.result]
        if successful_results:
            first = successful_results[0].result
            manifest.setdefault("translation", {})
            manifest["translation"][f"wave{wave}_backend"] = first.backend_name
            manifest["translation"][f"wave{wave}_model"] = first.model
            manifest["translation"][f"wave{wave}_updated_at"] = now_iso

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Update stage status
        self._update_stage_status(wave, results)

    def _update_stage_status(self, wave: int, results: list[ChunkResult]) -> None:
        """Update stage_status.json with translation progress."""
        stage_path = self.project_dir / "state" / "stage_status.json"
        if not stage_path.exists():
            return

        with open(stage_path) as f:
            stage_status = json.load(f)

        wave_key = f"translation_wave{wave}"
        if wave_key in stage_status["stages"]:
            total = len(results)
            succeeded = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            stage_status["stages"][wave_key].update({
                "translated": succeeded,
                "failed": failed,
                "total": total,
                "status": "completed" if failed == 0 else ("warn" if succeeded > 0 else "failed"),
            })

        with open(stage_path, "w") as f:
            json.dump(stage_status, f, indent=2)