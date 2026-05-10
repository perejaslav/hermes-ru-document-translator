#!/usr/bin/env python3
"""
Universal RU Document Translator — run_pipeline.py
CLI с подкомандами: doctor, prepare, qa, merge, export, report, resume, retry-failed

Usage:
    python3 ~/hermes-translator/scripts/run_pipeline.py doctor
    python3 ~/hermes-translator/scripts/run_pipeline.py prepare /path/to/doc.[ext]
    python3 ~/hermes-translator/scripts/run_pipeline.py qa /path/to/workspace
    python3 ~/hermes-translator/scripts/run_pipeline.py merge /path/to/workspace
    python3 ~/hermes-translator/scripts/run_pipeline.py export /path/to/workspace
    python3 ~/hermes-translator/scripts/run_pipeline.py report /path/to/workspace
    python3 ~/hermes-translator/scripts/run_pipeline.py resume /path/to/workspace
    python3 ~/hermes-translator/scripts/run_pipeline.py retry-failed /path/to/workspace
"""

import argparse
import importlib
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_doctor():
    """Проверить все зависимости и конфигурацию."""
    from translator.state.manifest import Manifest
    import fitz
    import docx
    import bs4
    import markdown_it
    import html2text
    import chardet
    import json

    print("=== Universal RU Document Translator — Doctor ===\n")

    # Python version
    import sys as _sys
    print(f"Python: {_sys.version.split()[0]}")

    # Check critical packages
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

    # Check system tools
    print("\n[System tools]")
    import shutil
    system_tools = [
        ("pandoc", shutil.which("pandoc")),
        ("xelatex", shutil.which("xelatex")),
        ("pdftotext", shutil.which("pdftotext")),
    ]
    for name, path in system_tools:
        if path:
            print(f"  ✓ {name}: {path}")
        else:
            print(f"  ⚠ {name}: not found (optional for MVP)")

    # Check fonts
    print("\n[Fonts]")
    font_dirs = [Path("/usr/share/fonts"), Path.home() / ".fonts"]
    found_fonts = []
    for fd in font_dirs:
        if fd.exists():
            found_fonts.extend(list(fd.rglob("NotoSerif*.ttf"))[:2])
            found_fonts.extend(list(fd.rglob("NotoSans*.ttf"))[:2])

    if found_fonts:
        print(f"  ✓ Noto fonts found: {len(found_fonts)} files")
    else:
        print("  ⚠ Noto fonts: not found (PDF export may fail)")

    # Check hermes-translator structure
    print("\n[hermes-translator structure]")
    required_dirs = [
        PROJECT_ROOT / "translator" / "extractors",
        PROJECT_ROOT / "translator" / "exporters",
        PROJECT_ROOT / "translator" / "qa",
        PROJECT_ROOT / "translator" / "state",
        PROJECT_ROOT / "translator" / "backends",
        PROJECT_ROOT / "translator" / "orchestration",
        PROJECT_ROOT / "scripts",
    ]
    for d in required_dirs:
        if d.exists():
            print(f"  ✓ {d.name}/")
        else:
            print(f"  ✗ {d.name}/: MISSING")
            all_ok = False

    # Check extractors
    extractors = ["txt", "markdown", "docx", "html", "pdf", "epub"]
    print("\n[Extractors]")
    for ext in extractors:
        f = PROJECT_ROOT / "translator" / "extractors" / f"{ext}.py"
        if f.exists():
            # Check if it's a stub
            content = f.read_text()
            if "NotImplementedError" in content and "v0.1" in content:
                print(f"  🟡 {ext}.py: stub only")
            else:
                print(f"  ✓ {ext}.py")
        else:
            print(f"  ✗ {ext}.py: MISSING")

    # Check exporters
    exporters = ["markdown", "txt", "docx", "html", "pdf", "epub"]
    print("\n[Exporters]")
    for exp in exporters:
        f = PROJECT_ROOT / "translator" / "exporters" / f"{exp}.py"
        if f.exists():
            content = f.read_text()
            if "NotImplementedError" in content and "v0.1" in content:
                print(f"  🟡 {exp}.py: stub only")
            else:
                print(f"  ✓ {exp}.py")
        else:
            print(f"  ✗ {exp}.py: MISSING")

    # Check scripts
    print("\n[Pipeline scripts]")
    scripts = [
        "run_pipeline",
        "ingest",
        "classify_document",
        "extract",
        "normalize",
        "protect_spans",
        "assign_block_ids",
        "segment",
        "build_glossary_inputs",
        "qa_chunk",
        "merge",
        "export",
        "final_report",
    ]
    for scr in scripts:
        f = PROJECT_ROOT / "scripts" / f"{scr}.py"
        if f.exists():
            print(f"  ✓ {scr}.py")
        else:
            print(f"  ✗ {scr}.py: MISSING")

    # Check config
    print("\n[Config]")
    cfg = PROJECT_ROOT / "config.yaml"
    if cfg.exists():
        print(f"  ✓ config.yaml")
    else:
        print(f"  ✗ config.yaml: MISSING")

    # Check skill
    print("\n[Skill]")
    skill_dir = Path.home() / ".hermes" / "skills" / "universal-ru-document-translator"
    if skill_dir.exists():
        print(f"  ✓ universal-ru-document-translator/ skill")
        if (skill_dir / "SKILL.md").exists():
            print(f"  ✓ SKILL.md")
    else:
        print(f"  ✗ universal-ru-document-translator/ skill: MISSING")

    # Summary
    print(f"\n{'='*50}")
    if all_ok:
        print("Doctor: ALL CHECKS PASSED ✓")
        print("Pipeline ready for: prepare, qa, merge, export, report")
    else:
        print("Doctor: SOME CHECKS FAILED ✗")
        print("Fix issues before running translation pipeline.")
    print(f"{'='*50}\n")


def cmd_prepare(input_path: str, lang: str = None, force: bool = False):
    """Prepare workspace: ingest → extract → normalize → protect → block_ids → segment."""
    from translator.state.manifest import Manifest, create_project_slug

    input_file = Path(input_path).resolve()
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)

    # Supported formats check
    supported = {'.txt', '.md', '.markdown', '.docx', '.html', '.htm', '.pdf'}
    if input_file.suffix.lower() not in supported:
        print(f"ERROR: Unsupported format: {input_file.suffix}")
        print(f"Supported: {', '.join(sorted(supported))}")
        sys.exit(1)

    print(f"Preparing: {input_file.name}")

    # Create workspace
    slug = create_project_slug(input_file)
    workspace = Path.home() / "translations" / slug

    if workspace.exists() and not force:
        print(f"\nWorkspace already exists: {workspace}")
        print("Use --force to overwrite")
        sys.exit(1)

    workspace.mkdir(parents=True, exist_ok=True)
    for subdir in ["input", "chunks/source", "chunks/translated", "output", "state"]:
        (workspace / subdir).mkdir(parents=True, exist_ok=True)

    print(f"Workspace: {workspace}")

    # Initialize manifest
    manifest = Manifest(workspace, input_file, lang)
    manifest.save()
    print("  ✓ manifest.json")

    # Initialize pipeline status
    from translator.state.status import PipelineStatus
    status = PipelineStatus(workspace)

    # Run mechanical stages
    stages = [
        ("ingest", "scripts.ingest"),
        ("classify", "scripts.classify_document"),
        ("extract", "scripts.extract"),
        ("normalize", "scripts.normalize"),
        ("protect_spans", "scripts.protect_spans"),
        ("block_ids", "scripts.assign_block_ids"),
        ("segment", "scripts.segment"),
    ]

    print("\n[Pipeline stages]")
    for stage_name, module_name in stages:
        print(f"  {stage_name}...", end=" ")
        status.set_stage(stage_name, "in_progress")
        try:
            mod = importlib.import_module(module_name, package=None)
            # Need to handle relative import within package
            if stage_name == "ingest":
                from scripts.ingest import run as stage_run
            elif stage_name == "classify":
                from scripts.classify_document import run as stage_run
            elif stage_name == "extract":
                from scripts.extract import run as stage_run
            elif stage_name == "normalize":
                from scripts.normalize import run as stage_run
            elif stage_name == "protect_spans":
                from scripts.protect_spans import run as stage_run
            elif stage_name == "block_ids":
                from scripts.assign_block_ids import run as stage_run
            elif stage_name == "segment":
                from scripts.segment import run as stage_run

            result = stage_run(workspace)
            stage_result = result.get("status", "unknown")
            if stage_result == "stub":
                status.set_stage(stage_name, "stub")
                print(f"stub (skipped)")
            elif stage_result == "completed":
                status.set_stage(stage_name, "completed")
                # Show key info
                if stage_name == "segment":
                    print(f"done ({result.get('total_chunks', '?')} chunks)")
                else:
                    print("done")
            else:
                status.set_stage(stage_name, stage_result)
                print(f"{stage_result}")
        except Exception as e:
            status.set_stage(stage_name, "failed", str(e))
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Mark LLM stages as pending
    for llm_stage in ["glossary", "translation", "qa", "merge", "export", "report"]:
        status.set_stage(llm_stage, "pending_agent")

    # Build glossary inputs (mechanical part — creates glossary_input.md)
    print("  glossary inputs...", end=" ")
    try:
        from scripts.build_glossary_inputs import run as glossary_inputs_run
        result = glossary_inputs_run(workspace)
        print("done")
        status.set_stage("glossary", "pending_agent")  # content still needs LLM
    except Exception as e:
        print(f"warning: {e}")

    # Create glossary.md placeholder (always exists per user requirement)
    # Real glossary content requires LLM; placeholder ensures output/glossary.md exists
    _create_glossary_placeholder(workspace)
    print("  glossary placeholder: created")

    # Mark glossary as completed (placeholder created; real glossary = pending_agent LLM step)
    status.set_stage("glossary", "completed")
    status.data["warnings"].append({
        "warning": "glossary.md is placeholder — real glossary requires LLM glossary generation",
        "at": datetime.now().isoformat()
    })

    # Set overall status and save
    status.data["overall_status"] = "PREPARED"
    status.save()

    # Also save stage_status.json (same data, separate file for convenience)
    stage_status_path = workspace / "state" / "stage_status.json"
    import json as _json
    with open(stage_status_path, 'w', encoding='utf-8') as f:
        _json.dump(status.data, f, indent=2, ensure_ascii=False)


def _create_glossary_placeholder(workspace: Path):
    """Create output/glossary.md with placeholder content and warning."""
    output_dir = workspace / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    glossary_path = output_dir / "glossary.md"
    manifest_path = workspace / "state" / "manifest.json"

    # Try to extract filename from manifest for context
    doc_name = "document"
    try:
        if manifest_path.exists():
            import json as _json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                m = _json.load(f)
                doc_name = Path(m.get("input_path", doc_name)).stem
    except Exception:
        pass

    placeholder_content = (
        f"# Glossary — {doc_name}\n"
        "\n"
        "**NOTE: This is an automatically generated placeholder glossary.**\n"
        "Real glossary with terminology choices requires LLM review of source content.\n"
        "\n"
        "## Known Terms\n"
        "\n"
        "*No terminology entries yet — pending LLM glossary generation.*\n"
        "\n"
        "---\n"
        "*Generated by Hermes Universal RU Document Translator v0.1*\n"
    )

    with open(glossary_path, 'w', encoding='utf-8') as f:
        f.write(placeholder_content)

    print(f"\n✓ Prepare complete")
    print(f"  Workspace: {workspace}")
    print(f"  status.json: {workspace}/state/status.json")
    print(f"  stage_status.json: {workspace}/state/stage_status.json")
    print(f"  Next steps:")
    print(f"    1. Build glossary (manual LLM call)")
    print(f"    2. Translate chunks (manual LLM calls or delegate_task)")
    print(f"    3. Run: run_pipeline.py qa {workspace}")
    print(f"    4. Run: run_pipeline.py merge {workspace}")
    print(f"    5. Run: run_pipeline.py export {workspace}")
    print(f"    6. Run: run_pipeline.py report {workspace}")


def cmd_qa(workspace_path: str):
    """Run QA checks on translated chunks (pre-merge) and final output (post-merge)."""
    from translator.state.status import PipelineStatus

    workspace = Path(workspace_path).resolve()
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {workspace}")
        sys.exit(1)

    print(f"Running QA on: {workspace.name}")

    status = PipelineStatus.load(workspace)
    status.set_stage("qa", "in_progress")
    status.save()

    try:
        from scripts.qa_chunk import run as qa_run
        result = qa_run(workspace)

        status.set_stage("qa", "completed")
        status.save()
        _save_stage_status(workspace, status)

        print(f"\nQA Results:")
        print(f"  Total chunks checked: {result.get('total_chunks_checked', 0)}")
        print(f"  Passed: {result.get('passed', 0)}")
        print(f"  Findings: {result.get('findings_count', 0)}")
        if result.get('qa_report'):
            print(f"  Report: {result['qa_report']}")
    except Exception as e:
        status.set_stage("qa", "failed", str(e))
        status.save()
        _save_stage_status(workspace, status)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def cmd_merge(workspace_path: str):
    """Merge translated chunks into final document."""
    from translator.state.status import PipelineStatus

    workspace = Path(workspace_path).resolve()
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {workspace}")
        sys.exit(1)

    print(f"Merging: {workspace.name}")

    status = PipelineStatus.load(workspace)
    status.set_stage("merge", "in_progress")
    status.save()

    try:
        from scripts.merge import run as merge_run
        result = merge_run(workspace)

        status.set_stage("merge", "completed")
        status.save()
        _save_stage_status(workspace, status)

        print(f"\nMerge Results:")
        print(f"  Chunks merged: {result.get('chunks_merged', 0)}")
        print(f"  Total chars: {result.get('total_chars', 0)}")
        if result.get('output_path'):
            print(f"  Output: {result['output_path']}")
        print(f"  Debug: {result.get('debug_path', 'N/A')}")
        print(f"  BLOCK_ID stripped: {result.get('block_ids_stripped', 0)} (present in translated.debug.md only)")
    except Exception as e:
        status.set_stage("merge", "failed", str(e))
        status.save()
        _save_stage_status(workspace, status)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def _save_stage_status(workspace: Path, status):
    """Save stage_status.json as a copy of status.json."""
    import json as _json
    stage_status_path = workspace / "state" / "stage_status.json"
    with open(stage_status_path, 'w', encoding='utf-8') as f:
        _json.dump(status.data, f, indent=2, ensure_ascii=False)


def cmd_export(workspace_path: str):
    """Export translated.md to all available formats."""
    from translator.state.status import PipelineStatus

    workspace = Path(workspace_path).resolve()
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {workspace}")
        sys.exit(1)

    print(f"Exporting: {workspace.name}")

    status = PipelineStatus.load(workspace)
    status.set_stage("export", "in_progress")
    status.save()

    try:
        from scripts.export import run as export_run
        result = export_run(workspace)

        status.set_stage("export", "completed")
        status.save()
        _save_stage_status(workspace, status)

        print(f"\nExport Results:")
        print(f"  Formats attempted: {result.get('total_formats', 0)}")
        print(f"  Successful: {result.get('successful', 0)}")
        for r in result.get('results', []):
            fmt = r.get('format', '?')
            export_st = r.get('status', '?')
            if export_st == 'success':
                print(f"  ✓ .{fmt}")
            else:
                err = r.get('error', '')[:60]
                print(f"  ✗ .{fmt}: {err}")
    except Exception as e:
        status.set_stage("export", "failed", str(e))
        status.save()
        _save_stage_status(workspace, status)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def cmd_report(workspace_path: str):
    """Generate final translation report."""
    from translator.state.status import PipelineStatus

    workspace = Path(workspace_path).resolve()
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {workspace}")
        sys.exit(1)

    print(f"Generating report: {workspace.name}")

    status = PipelineStatus.load(workspace)
    status.set_stage("report", "in_progress")
    status.save()

    try:
        from scripts.final_report import run as report_run

        # CRITICAL: set_complete BEFORE running report so report sees final status
        status.set_stage("report", "completed")
        status.set_complete()  # Determine and set final overall_status (SUCCESS/PARTIAL_SUCCESS)
        status.save()
        _save_stage_status(workspace, status)

        result = report_run(workspace)

        print(f"\nReport Results:")
        print(f"  Status: {result.get('overall_status', 'UNKNOWN')}")
        if result.get('report_path'):
            print(f"  Report: {result['report_path']}")
        print(f"  Overall: {status.data.get('overall_status', 'UNKNOWN')}")
    except Exception as e:
        status.set_stage("report", "failed", str(e))
        status.save()
        _save_stage_status(workspace, status)
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def cmd_resume(workspace_path: str):
    """Resume interrupted pipeline from last completed stage."""
    from translator.state.status import PipelineStatus

    workspace = Path(workspace_path).resolve()
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {workspace}")
        sys.exit(1)

    print(f"Resume: {workspace.name}")

    status = PipelineStatus.load(workspace)
    print(f"\nCurrent status:")
    print(status.summary())

    # Find next pending stage
    from translator.state.status import STAGE_ORDER
    for stage in STAGE_ORDER:
        stage_data = status.data.get("stages", {}).get(stage, {})
        if stage_data.get("status") in ("pending", "failed"):
            print(f"\nNext stage to run: {stage}")
            break
    else:
        print("\nNo pending stages found. Pipeline may be complete.")


def cmd_retry_failed(workspace_path: str):
    """Retry failed chunks in workspace."""
    from translator.state.chunk_index import ChunkIndex

    workspace = Path(workspace_path).resolve()
    if not workspace.exists():
        print(f"ERROR: Workspace not found: {workspace}")
        sys.exit(1)

    print(f"Retry failed: {workspace.name}")

    chunk_index = ChunkIndex.load(workspace)
    failed = chunk_index.get_failed()

    if not failed:
        print("No failed chunks found")
        return

    print(f"Found {len(failed)} failed chunks: {', '.join(failed)}")
    print("\nTo retry:")
    print("  1. Translate each chunk via LLM")
    print("  2. Place translated files in chunks/translated/<chunk_id>.md")
    print("  3. Run: run_pipeline.py qa <workspace>")
    print("  4. Run: run_pipeline.py merge <workspace>")


def main():
    parser = argparse.ArgumentParser(
        description="Universal RU Document Translator v0.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="""
Available commands:
  doctor           Check dependencies and configuration
  prepare          Create workspace and run mechanical stages
  qa               Run QA checks on translated chunks
  merge            Merge translated chunks into final document
  export           Export translated.md to all formats
  report           Generate final translation report
  resume           Show pipeline status and next steps
  retry-failed     Show failed chunks for retry

Examples:
  python3 ~/hermes-translator/scripts/run_pipeline.py doctor
  python3 ~/hermes-translator/scripts/run_pipeline.py prepare /path/to/doc.md
  python3 ~/hermes-translator/scripts/run_pipeline.py qa ~/translations/doc_20250608_abc123/
  python3 ~/hermes-translator/scripts/run_pipeline.py merge ~/translations/doc_20250608_abc123/
  python3 ~/hermes-translator/scripts/run_pipeline.py export ~/translations/doc_20250608_abc123/
  python3 ~/hermes-translator/scripts/run_pipeline.py report ~/translations/doc_20250608_abc123/
"""
    )

    parser.add_argument("command", help="Command to run")
    parser.add_argument("path", nargs="?", help="Path to document or workspace")
    parser.add_argument("--lang", help="Source language (auto-detected if not set)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing workspace")

    args = parser.parse_args()  # sys.argv[1:] by default

    cmd = args.command

    if cmd == "doctor":
        cmd_doctor()
    elif cmd == "prepare":
        if not args.path:
            print("ERROR: prepare requires a document path")
            print("Usage: run_pipeline.py prepare /path/to/document.[ext]")
            sys.exit(1)
        cmd_prepare(args.path, args.lang, args.force)
    elif cmd == "qa":
        if not args.path:
            print("ERROR: qa requires a workspace path")
            print("Usage: run_pipeline.py qa ~/translations/<project>/")
            sys.exit(1)
        cmd_qa(args.path)
    elif cmd == "merge":
        if not args.path:
            print("ERROR: merge requires a workspace path")
            print("Usage: run_pipeline.py merge ~/translations/<project>/")
            sys.exit(1)
        cmd_merge(args.path)
    elif cmd == "export":
        if not args.path:
            print("ERROR: export requires a workspace path")
            print("Usage: run_pipeline.py export ~/translations/<project>/")
            sys.exit(1)
        cmd_export(args.path)
    elif cmd == "report":
        if not args.path:
            print("ERROR: report requires a workspace path")
            print("Usage: run_pipeline.py report ~/translations/<project>/")
            sys.exit(1)
        cmd_report(args.path)
    elif cmd == "resume":
        if not args.path:
            print("ERROR: resume requires a workspace path")
            print("Usage: run_pipeline.py resume ~/translations/<project>/")
            sys.exit(1)
        cmd_resume(args.path)
    elif cmd == "retry-failed":
        if not args.path:
            print("ERROR: retry-failed requires a workspace path")
            print("Usage: run_pipeline.py retry-failed ~/translations/<project>/")
            sys.exit(1)
        cmd_retry_failed(args.path)
    else:
        print(f"Unknown command: {cmd}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()