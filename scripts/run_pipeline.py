#!/usr/bin/env python3
"""
Universal RU Document Translator — Unified Pipeline v0.2
CLI: doctor, prepare, translate, qa, repair, merge, export, report, status, list

Usage:
    python3 scripts/run_pipeline.py doctor
    python3 scripts/run_pipeline.py prepare /path/to/doc.md
    python3 scripts/run_pipeline.py translate <project_slug> --backend mock
    python3 scripts/run_pipeline.py qa <project_slug>
    python3 scripts/run_pipeline.py repair <project_slug> [--backend <name>]
    python3 scripts/run_pipeline.py merge <project_slug>
    python3 scripts/run_pipeline.py export <project_slug>
    python3 scripts/run_pipeline.py report <project_slug>
    python3 scripts/run_pipeline.py status <project_slug>
    python3 scripts/run_pipeline.py list
"""

import argparse
import importlib
import re
import sys
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Canonical pipeline stages
STAGE_ORDER = [
    "ingestion",
    "foundation",
    "chunking",
    "translation_wave1",
    "translation_wave2",
    "qa_gates",
    "assembly",
    "export",
    "report",
]

# Stage group labels
MECHANICAL_STAGES = ["ingestion", "foundation", "chunking"]
LLM_STAGES = ["translation_wave1", "translation_wave2", "qa_gates"]


def _project_dir(slug_or_path: str) -> Path:
    """Resolve project directory from slug or path."""
    p = Path(slug_or_path)
    if p.is_absolute() and p.exists():
        return p
    # Assume it's a slug
    return Path.home() / "translations" / slug_or_path


def _status_file(project_dir: Path) -> Path:
    return project_dir / "state" / "status.json"


def _stage_status_file(project_dir: Path) -> Path:
    return project_dir / "state" / "stage_status.json"


def _load_status(project_dir: Path) -> dict:
    sf = _status_file(project_dir)
    if sf.exists():
        with open(sf) as f:
            return json.load(f)
    return {"stages": {}, "overall_status": "UNKNOWN"}


def _save_status(project_dir: Path, data: dict):
    sf = _status_file(project_dir)
    sf.parent.mkdir(parents=True, exist_ok=True)
    with open(sf, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Also save as stage_status.json
    stf = _stage_status_file(project_dir)
    with open(stf, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _set_stage(project_dir: Path, stage: str, status: str, error: str = None):
    data = _load_status(project_dir)
    if stage not in data["stages"]:
        data["stages"][stage] = {"status": "pending", "started_at": None, "completed_at": None}
    stage_data = data["stages"][stage]
    if status == "in_progress" and stage_data["status"] == "pending":
        stage_data["started_at"] = datetime.now().isoformat()
    stage_data["status"] = status
    if status in ("completed", "failed", "skipped"):
        stage_data["completed_at"] = datetime.now().isoformat()
    if error:
        data.setdefault("errors", []).append({"stage": stage, "error": error})
    _save_status(project_dir, data)


def _get_stage_status(project_dir: Path, stage: str) -> str:
    data = _load_status(project_dir)
    return data.get("stages", {}).get(stage, {}).get("status", "pending")


# =============================================================================
# COMMANDS
# =============================================================================

def cmd_doctor():
    """Check all dependencies and configuration."""
    import shutil
    print("=== Universal RU Document Translator — Doctor ===\n")

    import sys as _sys
    print(f"Python: {_sys.version.split()[0]}")

    # Python packages
    packages = [
        ("PyMuPDF (fitz)", "fitz"),
        ("python-docx", "docx"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
        ("markdown-it-py", "markdown_it"),
        ("html2text", "html2text"),
        ("chardet", "chardet"),
    ]

    print("\n[Python packages]")
    all_ok = True
    for name, module_name in packages:
        try:
            mod = importlib.import_module(module_name)
            version = getattr(mod, '__version__', 'unknown')
            print(f"  ✓ {name}: {version}")
        except ImportError:
            print(f"  ✗ {name}: MISSING")
            all_ok = False

    # System tools
    print("\n[System tools]")
    system_tools = [
        ("pandoc", shutil.which("pandoc")),
        ("xelatex", shutil.which("xelatex")),
        ("pdftotext", shutil.which("pdftotext")),
    ]
    for name, path in system_tools:
        if path:
            print(f"  ✓ {name}: {path}")
        else:
            print(f"  ⚠ {name}: not found (optional)")

    # Package structure
    print("\n[Package structure]")
    required_dirs = [
        PROJECT_ROOT / "translator" / "extractors",
        PROJECT_ROOT / "translator" / "exporters",
        PROJECT_ROOT / "translator" / "qa",
        PROJECT_ROOT / "translator" / "state",
        PROJECT_ROOT / "translator" / "backends",
        PROJECT_ROOT / "translator" / "orchestration",
        PROJECT_ROOT / "translator" / "pipeline",
        PROJECT_ROOT / "scripts",
    ]
    for d in required_dirs:
        if d.exists():
            print(f"  ✓ {d.name}/")
        else:
            print(f"  ✗ {d.name}/: MISSING")
            all_ok = False

    # Backends
    print("\n[Backends]")
    try:
        from translator.backends import BACKEND_REGISTRY
        for name in BACKEND_REGISTRY:
            print(f"  ✓ {name}")
    except Exception as e:
        print(f"  ✗ backends: {e}")
        all_ok = False

    # Pipeline modules
    print("\n[Pipeline modules]")
    for mod_name in ["foundation_builder", "chunker"]:
        try:
            from translator.pipeline import __dict__
            mod_path = PROJECT_ROOT / "translator" / "pipeline" / f"{mod_name}.py"
            if mod_path.exists():
                print(f"  ✓ {mod_name}")
            else:
                print(f"  ✗ {mod_name}: missing")
                all_ok = False
        except Exception as e:
            print(f"  ✗ {mod_name}: {e}")

    # Hermes skill
    print("\n[Skill]")
    skill_path = Path.home() / ".hermes" / "skills" / "universal-ru-document-translator" / "SKILL.md"
    if skill_path.exists():
        print(f"  ✓ universal-ru-document-translator/ skill")
        print(f"  ✓ SKILL.md")
    else:
        print(f"  ⚠ skill not installed (optional)")

    print(f"\n{'Doctor: ALL CHECKS PASSED ✓' if all_ok else 'Doctor: SOME CHECKS FAILED ✗'}")
    print("Pipeline ready for: prepare, translate, qa, merge, export, report")
    return 0 if all_ok else 1


def cmd_list():
    """List all translation projects in ~/translations/."""
    translations_dir = Path.home() / "translations"
    if not translations_dir.exists():
        print(f"No projects found: {translations_dir} does not exist")
        return 0

    projects = sorted(translations_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    if not projects:
        print(f"No projects in {translations_dir}")
        return 0

    print(f"{'Project':<45} {'Status':<20} {'Stages'}")
    print("-" * 90)

    for project in projects:
        if not project.is_dir():
            continue
        status_path = project / "state" / "status.json"
        if status_path.exists():
            with open(status_path) as f:
                data = json.load(f)
            overall = data.get("overall_status", "?")
            stages = ", ".join([
                f"{s}={d.get('status', '?')}"
                for s, d in data.get("stages", {}).items()
                if d.get("status") not in ("pending",)
            ])
        else:
            overall = "no status"
            stages = ""
        print(f"{project.name:<45} {overall:<20} {stages[:40]}")

    print(f"\n{len(projects)} project(s) found")
    return 0


def cmd_status(project_slug: str):
    """Show detailed status of a project."""
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        print("Use 'list' command to see all projects")
        sys.exit(1)

    status_path = project_dir / "state" / "status.json"
    if not status_path.exists():
        print("No status file — project may be incomplete")
        sys.exit(1)

    with open(status_path) as f:
        data = json.load(f)

    overall = data.get("overall_status", "?")
    print(f"\nProject: {project_dir.name}")
    print(f"Overall: {overall}")
    print(f"Started: {data.get('started_at', '?')}")
    if data.get("completed_at"):
        print(f"Completed: {data.get('completed_at')}")

    print("\n[Stages]")
    for stage in STAGE_ORDER:
        stage_data = data.get("stages", {}).get(stage, {})
        status = stage_data.get("status", "?")
        icon = "✓" if status == "completed" else ("⚠" if status in ("failed", "warn") else ("○" if status == "pending" else "?"))
        started = stage_data.get("started_at", "")
        completed = stage_data.get("completed_at", "")
        note = f" ({completed[:10]})" if completed else (f" ({started[:10]})" if started else "")
        print(f"  {icon} {stage:<25} {status}{note}")

    # Warnings
    if data.get("warnings"):
        print(f"\n[Warnings]")
        for w in data["warnings"]:
            print(f"  ⚠ {w}")

    # Errors
    if data.get("errors"):
        print(f"\n[Errors]")
        for e in data["errors"]:
            print(f"  ✗ {e['stage']}: {e['error']}")

    # Chunk summary
    manifest_path = project_dir / "chunks" / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            m = json.load(f)
        total = m.get("total_chunks", 0)
        wave1_done = sum(1 for c in m.get("chunks", []) if c.get("wave1_status") == "completed")
        wave2_done = sum(1 for c in m.get("chunks", []) if c.get("wave2_status") == "completed")
        qa_done = sum(1 for c in m.get("chunks", []) if c.get("qa_status") == "completed")
        print(f"\n[Chunks] {total} total | wave1: {wave1_done}/{total} | wave2: {wave2_done}/{total} | qa: {qa_done}/{total}")

        # Backend metadata
        translation = m.get("translation", {})
        if translation:
            w1_backend = translation.get("wave1_backend", "?")
            w1_model = translation.get("wave1_model") or "model unknown"
            w2_backend = translation.get("wave2_backend", "?")
            w2_model = translation.get("wave2_model") or "model unknown"
            print(
                f"[Backend] wave1={w1_backend} ({w1_model}), "
                f"wave2={w2_backend} ({w2_model})"
            )

    return 0


def cmd_prepare(input_path: str, lang: str = None, force: bool = False):
    """Prepare workspace: ingestion → foundation → chunking."""
    from translator.state.manifest import Manifest, create_project_slug

    input_file = Path(input_path).resolve()
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)

    supported = {'.txt', '.md', '.markdown', '.docx', '.html', '.htm', '.pdf'}
    if input_file.suffix.lower() not in supported:
        print(f"ERROR: Unsupported format: {input_file.suffix}")
        print(f"Supported: {', '.join(sorted(supported))}")
        sys.exit(1)

    print(f"Preparing: {input_file.name}")

    # Create project directory
    slug = create_project_slug(input_file)
    project_dir = Path.home() / "translations" / slug

    if project_dir.exists() and not force:
        print(f"\nProject already exists: {project_dir}")
        print("Use --force to overwrite")
        sys.exit(1)

    # Create canonical directory structure
    for subdir in [
        "input",
        "chunks/source",
        "chunks/context",
        "chunks/translated/wave1",
        "chunks/translated/wave2",
        "foundation",
        "qa",
        "output",
        "state",
    ]:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    print(f"Project: {project_dir}")

    # Initialize status
    init_status = {
        "stages": {s: {"status": "pending", "started_at": None, "completed_at": None}
                   for s in STAGE_ORDER},
        "overall_status": "IN_PROGRESS",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "errors": [],
        "warnings": [],
    }
    _save_status(project_dir, init_status)

    # Copy source file
    import shutil
    shutil.copy2(input_file, project_dir / "input" / input_file.name)
    print(f"  ✓ source copied to input/")

    # Stage 1: Ingestion (extract text from source)
    print("\n[Stage 1: Ingestion]")
    _set_stage(project_dir, "ingestion", "in_progress")
    try:
        extracted_text = _ingest_file(input_file)
        canonical_path = project_dir / "chunks" / "source" / "canonical.md"
        canonical_path.write_text(extracted_text, encoding='utf-8')
        print(f"  ✓ extracted text ({len(extracted_text)} chars) → canonical.md")
        _set_stage(project_dir, "ingestion", "completed")
    except Exception as e:
        _set_stage(project_dir, "ingestion", "failed", str(e))
        print(f"  ✗ ingestion failed: {e}")
        sys.exit(1)

    # Stage 3: Header normalization (plain-text → ## headers)
    print("\n[Stage 2.5: Header Normalization]")
    canonical_path = project_dir / "chunks" / "source" / "canonical.md"
    try:
        from translator.pipeline.chunker import normalize_plain_text_headers as _normalize_headers
        raw_text = canonical_path.read_text(encoding='utf-8')
        normalized = _normalize_headers(raw_text)
        if normalized != raw_text:
            diff_lines = sum(1 for a, b in zip(normalized.splitlines(), raw_text.splitlines()) if a != b)
            canonical_path.write_text(normalized, encoding='utf-8')
            extracted_text = normalized  # ← sync in-memory for chunking stage
            print(f"  ✓ {diff_lines} plain-text headers converted to ## headers")
        else:
            print(f"  ✓ no plain-text headers found (already normalized)")
    except Exception as e:
        print(f"  ⚠ header normalization warning: {e} (continuing)")

    # Stage 3: Foundation (build glossary, style, entities)
    print("\n[Stage 3: Foundation]")
    _set_stage(project_dir, "foundation", "in_progress")
    try:
        from translator.pipeline.foundation_builder import build_foundation
        results = build_foundation(extracted_text, source_lang=lang or "en")
        for key, path in results.items():
            print(f"  ✓ {key}.md ({path.stat().st_size} bytes)")
        _set_stage(project_dir, "foundation", "completed")
    except Exception as e:
        _set_stage(project_dir, "foundation", "failed", str(e))
        print(f"  ⚠ foundation warning: {e} (continuing)")

    # Stage 4: Chunking (split into chunks with context)
    print("\n[Stage 4: Chunking]")
    _set_stage(project_dir, "chunking", "in_progress")
    try:
        from translator.pipeline.chunker import chunk_text, save_chunks
        chunks = chunk_text(extracted_text, slug)
        manifest_path = save_chunks(chunks, project_dir)
        print(f"  ✓ {len(chunks)} chunks created")
        print(f"  ✓ manifest.json saved")

        # Update LLM stages as pending
        for stage in ["translation_wave1", "translation_wave2", "qa_gates", "assembly"]:
            _set_stage(project_dir, stage, "pending")

        _set_stage(project_dir, "chunking", "completed")
    except Exception as e:
        _set_stage(project_dir, "chunking", "failed", str(e))
        print(f"  ✗ chunking failed: {e}")
        sys.exit(1)

    # Final status
    data = _load_status(project_dir)
    data["overall_status"] = "PREPARED"
    data["completed_at"] = datetime.now().isoformat()
    _save_status(project_dir, data)

    print(f"\n✓ Prepare complete")
    print(f"  Project: {slug}")
    print(f"  Location: {project_dir}")
    print(f"  Next step: translate")
    print(f"\n  To translate:")
    print(f"    .venv/bin/python scripts/run_pipeline.py translate {slug} --backend mock")


def cmd_translate(project_slug: str, backend: str | None = None, max_workers: int = 3):
    """Run wave1 and wave2 translation for all chunks."""
    if backend is None:
        backend = "mock"
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        sys.exit(1)

    manifest_path = project_dir / "chunks" / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found — run prepare first")
        sys.exit(1)

    print(f"Translating: {project_slug}")
    print(f"Backend: {backend} (workers: {max_workers})")

    # Check for already-completed chunks (resume)
    with open(manifest_path) as f:
        manifest = json.load(f)

    wave1_done = [c for c in manifest["chunks"] if c.get("wave1_status") == "completed"]
    wave2_done = [c for c in manifest["chunks"] if c.get("wave2_status") == "completed"]
    pending = [c for c in manifest["chunks"] if c.get("wave1_status") != "completed"]

    if pending:
        print(f"\n[Wave 1] {len(pending)} chunks to translate ({len(wave1_done)} done)")
    else:
        print(f"\n[Wave 1] All {len(wave1_done)} chunks already completed")

    if wave1_done and not wave2_done:
        print(f"[Wave 2] {len(wave1_done)} chunks to refine ({len(wave2_done)} done)")

    # Wave 1
    if pending:
        _set_stage(project_dir, "translation_wave1", "in_progress")
        try:
            from translator.orchestration.parallel_translator import ParallelTranslator
            translator = ParallelTranslator(project_dir, backend_name=backend, max_workers=max_workers)
            results_w1 = translator.translate_wave(wave=1, backend_name=backend)
            succeeded = sum(1 for r in results_w1 if r.success)
            failed = sum(1 for r in results_w1 if not r.success)
            print(f"  Wave 1: {succeeded} succeeded, {failed} failed")
            _set_stage(project_dir, "translation_wave1", "completed" if failed == 0 else "warn")
        except Exception as e:
            _set_stage(project_dir, "translation_wave1", "failed", str(e))
            print(f"  ✗ Wave 1 failed: {e}")

    # Wave 2 (only if wave1 completed)
    # Reload manifest to get updated wave1_status after wave1 run
    with open(manifest_path) as f:
        manifest = json.load(f)

    if any(c.get("wave1_status") == "completed" for c in manifest["chunks"]):
        wave2_pending = [c for c in manifest["chunks"] if c.get("wave1_status") == "completed" and c.get("wave2_status") != "completed"]
        if wave2_pending:
            print(f"\n[Wave 2] {len(wave2_pending)} chunks to refine")
            _set_stage(project_dir, "translation_wave2", "in_progress")
            try:
                from translator.orchestration.parallel_translator import ParallelTranslator
                translator = ParallelTranslator(project_dir, backend_name=backend, max_workers=max_workers)
                results_w2 = translator.translate_wave(wave=2, backend_name=backend)
                succeeded = sum(1 for r in results_w2 if r.success)
                failed = sum(1 for r in results_w2 if not r.success)
                print(f"  Wave 2: {succeeded} succeeded, {failed} failed")
                _set_stage(project_dir, "translation_wave2", "completed" if failed == 0 else "warn")
            except Exception as e:
                _set_stage(project_dir, "translation_wave2", "failed", str(e))
                print(f"  ✗ Wave 2 failed: {e}")
        else:
            all_w2_done = all(c.get("wave2_status") == "completed" for c in manifest["chunks"])
            if all_w2_done:
                print(f"[Wave 2] All chunks already completed")
            else:
                print(f"[Wave 2] No chunks ready (run wave1 first)")
    else:
        print(f"\n[Wave 2] Skipped — wave1 not completed")

    print(f"\n✓ Translation complete")
    print(f"  Next step: qa")


def cmd_qa(project_slug: str):
    """Run 5-gate QA on wave2 output."""
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        sys.exit(1)

    manifest_path = project_dir / "chunks" / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found — run prepare and translate first")
        sys.exit(1)

    print(f"Running QA: {project_slug}")

    _set_stage(project_dir, "qa_gates", "in_progress")
    try:
        from translator.qa.gates import run_all_gates
        result = run_all_gates(project_dir)

        overall = result.get("overall", "?")
        warnings = result.get("total_warnings", 0)
        print(f"\n[QA Summary] {overall}")
        for gate_name, gate_result in result.get("gates", {}).items():
            status = gate_result.get("status", "?")
            issues = gate_result.get("issues_found", 0)
            icon = "✓" if status == "PASS" else ("⚠" if status == "WARN" else "✗")
            print(f"  {icon} {gate_name}: {status} ({issues} issues)")

        if warnings > 0:
            print(f"\n  ⚠ {warnings} total warnings — run 'repair {project_slug}' if needed")
            _set_stage(project_dir, "qa_gates", "warn")
        else:
            _set_stage(project_dir, "qa_gates", "completed")

        print(f"\n  Report: {result.get('remediation_path', 'N/A')}")
        print(f"  Next step: merge")

    except Exception as e:
        _set_stage(project_dir, "qa_gates", "failed", str(e))
        print(f"  ✗ QA failed: {e}")
        sys.exit(1)


def _infer_repair_backend(manifest: dict, chunk_ids: list[str]) -> str | None:
    """Determine which backend was used for wave2 from manifest metadata.

    Checks in order:
    1. manifest-level 'translation.wave2_backend' field
    2. Individual chunk 'wave2_backend' fields for the flagged chunks
    Returns None if no backend can be inferred.
    """
    translation = manifest.get("translation", {})
    backend = translation.get("wave2_backend")
    if backend:
        return backend

    for chunk in manifest.get("chunks", []):
        if chunk.get("id") in chunk_ids:
            backend = chunk.get("wave2_backend")
            if backend:
                return backend

    return None


def cmd_repair(project_slug: str, backend: str | None = None):
    """Re-run wave2 for chunks flagged in remediation.json.

    Safety: refuses to auto-default to mock. Explicit --backend mock
    is still allowed for testing.
    """
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        sys.exit(1)

    remediation_path = project_dir / "qa" / "remediation.json"
    if not remediation_path.exists():
        print(f"ERROR: remediation.json not found — run qa first")
        sys.exit(1)

    with open(remediation_path) as f:
        remediation = json.load(f)

    chunk_issues = remediation.get("chunks", {})
    if not chunk_issues:
        print("No chunks flagged for repair")
        return 0

    # ── Backend safety logic ──────────────────────────────────────────────
    backend_was_explicit = backend is not None

    manifest_path = project_dir / "chunks" / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        if backend is None:
            backend = _infer_repair_backend(manifest, list(chunk_issues.keys()))

        if backend is None:
            print(
                "ERROR: repair backend unknown. Pass --backend explicitly. "
                "Refusing to use mock automatically."
            )
            sys.exit(1)

        if backend == "mock" and not backend_was_explicit:
            print(
                "ERROR: refusing implicit mock repair. "
                "Pass --backend mock explicitly for tests only."
            )
            sys.exit(1)
    # ── End safety logic ───────────────────────────────────────────────────

    print(f"Repairing {len(chunk_issues)} chunks: {project_slug} (backend: {backend})")

    for chunk_id, gates in chunk_issues.items():
        print(f"  {chunk_id}: {', '.join(gates)}")

    _set_stage(project_dir, "translation_wave2", "in_progress")
    try:
        from translator.orchestration.parallel_translator import ParallelTranslator
        translator = ParallelTranslator(project_dir, backend_name=backend, max_workers=2)
        results = translator.translate_wave(wave=2, backend_name=backend, chunk_ids=list(chunk_issues.keys()))
        succeeded = sum(1 for r in results if r.success)
        print(f"  Repair: {succeeded}/{len(results)} succeeded")
        _set_stage(project_dir, "translation_wave2", "completed")
    except Exception as e:
        _set_stage(project_dir, "translation_wave2", "failed", str(e))
        print(f"  ✗ repair failed: {e}")

    print(f"\nRe-run 'qa {project_slug}' after repair")
    return 0


def cmd_merge(project_slug: str):
    """Merge wave2 translated chunks into final translated.md."""
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        sys.exit(1)

    manifest_path = project_dir / "chunks" / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found")
        sys.exit(1)

    print(f"Merging: {project_slug}")

    _set_stage(project_dir, "assembly", "in_progress")
    try:
        from translator.pipeline.merge_chunks import merge_chunks
        output_path = merge_chunks(project_dir)

        wave2_dir = project_dir / "chunks" / "translated" / "wave2"
        if wave2_dir.exists():
            merged = list(wave2_dir.glob("*.md"))
            print(f"  ✓ {len(merged)} chunks merged → {output_path}")
        else:
            print(f"  ⚠ no wave2 output found")

        _set_stage(project_dir, "assembly", "completed")
        print(f"\n  Next step: export")

    except Exception as e:
        _set_stage(project_dir, "assembly", "failed", str(e))
        print(f"  ✗ merge failed: {e}")
        sys.exit(1)


def cmd_export(project_slug: str):
    """Export translated.md to all formats."""
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        sys.exit(1)

    translated_path = project_dir / "output" / "translated.md"
    if not translated_path.exists():
        print(f"ERROR: translated.md not found — run merge first")
        sys.exit(1)

    print(f"Exporting: {project_slug}")

    _set_stage(project_dir, "export", "in_progress")
    successful = 0

    try:
        from translator.exporters import exporters

        for fmt, exporter_fn in exporters:
            try:
                output_file = exporter_fn(project_dir)
                print(f"  ✓ .{fmt} → {output_file}")
                successful += 1
            except Exception as e:
                print(f"  ✗ .{fmt}: {str(e)[:60]}")

        _set_stage(project_dir, "export", "completed")
        print(f"\n✓ Export: {successful} format(s) successful")
        print(f"  Next step: report")

    except Exception as e:
        _set_stage(project_dir, "export", "failed", str(e))
        print(f"  ✗ export failed: {e}")
        sys.exit(1)


def cmd_report(project_slug: str):
    """Generate final translation report."""
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        sys.exit(1)

    print(f"Generating report: {project_slug}")

    _set_stage(project_dir, "report", "in_progress")

    try:
        # Compute final status
        status_data = _load_status(project_dir)

        # Check what stages are done
        stages_done = {
            s: status_data.get("stages", {}).get(s, {}).get("status")
            for s in STAGE_ORDER
        }

        all_done = all(s in ("completed", "skipped") for s in stages_done.values())
        has_warn = any(s == "warn" for s in stages_done.values())

        if all_done:
            overall = "SUCCESS"
        elif any(s in ("completed", "warn") for s in stages_done.values()):
            overall = "PARTIAL_SUCCESS"
        else:
            overall = "IN_PROGRESS"

        status_data["overall_status"] = overall
        status_data["completed_at"] = datetime.now().isoformat()
        _save_status(project_dir, status_data)

        # Generate markdown report
        report_path = project_dir / "output" / "translation_report.md"
        lines = [
            "# Translation Report",
            "",
            f"**Project:** {project_slug}",
            f"**Overall:** {overall}",
            f"**Generated:** {datetime.now().isoformat()}Z",
            "",
            "## Stage Status",
            "",
            "| Stage | Status |",
            "|---|---|",
        ]

        for stage in STAGE_ORDER:
            st = stages_done.get(stage, "?")
            icon = "✓" if st == "completed" else ("⚠" if st == "warn" else ("○" if st == "pending" else ("✗" if st == "failed" else "?")))
            lines.append(f"| {icon} {stage} | {st} |")

        # Chunk summary
        manifest_path = project_dir / "chunks" / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                m = json.load(f)
            total = m.get("total_chunks", 0)
            w1 = sum(1 for c in m.get("chunks", []) if c.get("wave1_status") == "completed")
            w2 = sum(1 for c in m.get("chunks", []) if c.get("wave2_status") == "completed")
            lines.extend(["", f"## Chunks", "", f"**Total:** {total}", f"**Wave 1:** {w1}/{total}", f"**Wave 2:** {w2}/{total}"])

        # QA summary
        qa_summary = project_dir / "qa" / "summary.md"
        if qa_summary.exists():
            lines.extend(["", "## QA Summary", "", f"_See qa/summary.md for details_"])

        # Output files
        output_dir = project_dir / "output"
        if output_dir.exists():
            files = sorted(output_dir.glob("*"))
            lines.extend(["", "## Output Files", ""])
            for f in files:
                lines.append(f"- {f.name} ({f.stat().st_size:,} bytes)")

        report_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"  ✓ report → {report_path}")

        _set_stage(project_dir, "report", "completed")
        print(f"\n✓ Report complete: {overall}")

    except Exception as e:
        _set_stage(project_dir, "report", "failed", str(e))
        print(f"  ✗ report failed: {e}")
        sys.exit(1)


# =============================================================================
# HELPERS
# =============================================================================

def cmd_clean(project_slug: str):
    """Strip YAML frontmatter and [N] citation markers from output.

    Removes pipeline artifacts from the final merged document:
    - YAML frontmatter (--- project: ... word_count: ... ---)
    - All [N] citation markers (brackets with digits)

    The original translated.md is overwritten.
    """
    project_dir = _project_dir(project_slug)
    if not project_dir.exists():
        print(f"ERROR: Project not found: {project_dir}")
        sys.exit(1)

    md_path = project_dir / "output" / "translated.md"
    if not md_path.exists():
        print(f"ERROR: translated.md not found at {md_path}")
        sys.exit(1)

    text = md_path.read_text(encoding='utf-8')
    original_len = len(text)

    # Strip YAML frontmatter
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL).strip()
    # Strip [N] citation markers
    text = re.sub(r'\[\d+\]', '', text)

    refs_removed = len(re.findall(r'\[\d+\]', text))
    md_path.write_text(text, encoding='utf-8')
    removed = original_len - len(text)
    print(f"✓ cleaned {project_slug}/output/translated.md")
    print(f"  removed {removed} chars (frontmatter + {refs_removed} citations)")
    print(f"  final size: {len(text):,} chars")


def _ingest_file(input_file: Path) -> str:
    """Extract text from supported formats."""
    ext = input_file.suffix.lower()

    if ext in ('.md', '.markdown', '.txt'):
        return input_file.read_text(encoding='utf-8')

    elif ext == '.docx':
        try:
            import docx
            doc = docx.Document(str(input_file))
            return '\n\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            raise RuntimeError(f"docx extraction failed: {e}")

    elif ext in ('.html', '.htm'):
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(input_file.read_text(encoding='utf-8'), 'html.parser')
            # Remove script and style elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = soup.get_text(separator='\n\n', strip=True)
            return text
        except Exception as e:
            raise RuntimeError(f"html extraction failed: {e}")

    elif ext == '.pdf':
        try:
            import fitz
            doc = fitz.open(str(input_file))
            pages = []
            for page in doc:
                text = page.get_text()
                if text.strip():
                    pages.append(text)
            doc.close()
            return '\n\n'.join(pages)
        except Exception as e:
            raise RuntimeError(f"pdf extraction failed: {e}")

    else:
        raise RuntimeError(f"Unsupported format: {ext}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Universal RU Document Translator v0.2 (Unified Pipeline)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="""
Available commands:
  doctor           Check dependencies and configuration
  list             List all translation projects
  status <slug>    Show detailed status of a project
  prepare <file>   Create project workspace from source file
  translate <slug> Translate all chunks (wave1 + wave2)
  qa <slug>        Run 5-gate QA
  repair <slug>    Re-translate flagged chunks
  merge <slug>     Merge chunks into final document
  export <slug>    Export to all formats
  report <slug>    Generate final report

Examples:
  python3 scripts/run_pipeline.py doctor
  python3 scripts/run_pipeline.py list
  python3 scripts/run_pipeline.py status my_project_slug
  python3 scripts/run_pipeline.py prepare /path/to/doc.md
  python3 scripts/run_pipeline.py translate my_project_slug --backend mock
  python3 scripts/run_pipeline.py qa my_project_slug
  python3 scripts/run_pipeline.py merge my_project_slug
  python3 scripts/run_pipeline.py export my_project_slug
  python3 scripts/run_pipeline.py report my_project_slug
        """,
    )

    parser.add_argument("command", help="Command to run")
    parser.add_argument("path", nargs="?", help="Document path or project slug")
    parser.add_argument("--lang", help="Source language (auto-detected if not set)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing project")
    parser.add_argument("--backend", default=None, help="Translation backend (default: auto-detect for repair, mock for translate)")
    parser.add_argument("--max-workers", type=int, default=3, help="Max parallel workers (default: 3)")

    args = parser.parse_args()
    cmd = args.command

    if cmd == "doctor":
        sys.exit(cmd_doctor())
    elif cmd == "list":
        sys.exit(cmd_list())
    elif cmd == "status":
        if not args.path:
            print("ERROR: status requires <project_slug>")
            sys.exit(1)
        sys.exit(cmd_status(args.path))
    elif cmd == "prepare":
        if not args.path:
            print("ERROR: prepare requires a document path")
            sys.exit(1)
        cmd_prepare(args.path, args.lang, args.force)
    elif cmd == "translate":
        if not args.path:
            print("ERROR: translate requires <project_slug>")
            sys.exit(1)
        cmd_translate(args.path, args.backend, args.max_workers)
    elif cmd == "qa":
        if not args.path:
            print("ERROR: qa requires <project_slug>")
            sys.exit(1)
        cmd_qa(args.path)
    elif cmd == "repair":
        if not args.path:
            print("ERROR: repair requires <project_slug>")
            sys.exit(1)
        cmd_repair(args.path, args.backend)
    elif cmd == "merge":
        if not args.path:
            print("ERROR: merge requires <project_slug>")
            sys.exit(1)
        cmd_merge(args.path)
    elif cmd == "export":
        if not args.path:
            print("ERROR: export requires <project_slug>")
            sys.exit(1)
        cmd_export(args.path)
    elif cmd == "report":
        if not args.path:
            print("ERROR: report requires <project_slug>")
            sys.exit(1)
        cmd_report(args.path)
    elif cmd == "clean":
        if not args.path:
            print("ERROR: clean requires <project_slug>")
            sys.exit(1)
        cmd_clean(args.path)
    else:
        print(f"Unknown command: {cmd}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()