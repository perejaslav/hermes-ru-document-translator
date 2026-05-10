"""QA Gates — five-stage quality assurance for translated chunks."""

import json
import re
from pathlib import Path
from typing import Optional


def run_all_gates(project_dir: Path) -> dict:
    """Run all 5 QA gates and return summary."""
    from translator.pipeline.chunker import _extract_sentences

    manifest_path = project_dir / "chunks" / "manifest.json"
    if not manifest_path.exists():
        return {"error": "manifest.json not found"}

    with open(manifest_path) as f:
        manifest = json.load(f)

    wave2_dir = project_dir / "chunks" / "translated" / "wave2"
    if not wave2_dir.exists():
        return {"error": "wave2 directory not found"}

    foundation_dir = project_dir / "foundation"

    results = {}
    all_passed = True
    total_warnings = 0

    # Gate 1 — Terminology
    g1 = _gate_terminology(project_dir, manifest, foundation_dir)
    results["gate1_terminology"] = g1
    if g1["status"] != "PASS":
        all_passed = False
    total_warnings += g1.get("warnings", 0)

    # Gate 2 — Integrity
    g2 = _gate_integrity(project_dir, manifest, wave2_dir)
    results["gate2_integrity"] = g2
    if g2["status"] != "PASS":
        all_passed = False
    total_warnings += g2.get("warnings", 0)

    # Gate 3 — Style
    g3 = _gate_style(project_dir, manifest, foundation_dir)
    results["gate3_style"] = g3
    if g3["status"] != "PASS":
        all_passed = False
    total_warnings += g3.get("warnings", 0)

    # Gate 4 — Fluency
    g4 = _gate_fluency(project_dir, manifest, wave2_dir)
    results["gate4_fluency"] = g4
    if g4["status"] != "PASS":
        all_passed = False
    total_warnings += g4.get("warnings", 0)

    # Gate 5 — Formatting
    g5 = _gate_formatting(project_dir, manifest, wave2_dir)
    results["gate5_formatting"] = g5
    if g5["status"] != "PASS":
        all_passed = False
    total_warnings += g5.get("warnings", 0)

    # Gate 6 — Completeness (structural + reference parity)
    g6 = _gate_completeness(project_dir, manifest, wave2_dir)
    results["gate6_completeness"] = g6
    if g6["status"] != "PASS":
        all_passed = False
    total_warnings += g6.get("warnings", 0)

    # Write individual gate reports
    qa_dir = project_dir / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    _write_gate_report(qa_dir / "gate1_terminology.md", g1)
    _write_gate_report(qa_dir / "gate2_integrity.md", g2)
    _write_gate_report(qa_dir / "gate3_style.md", g3)
    _write_gate_report(qa_dir / "gate4_fluency.md", g4)
    _write_gate_report(qa_dir / "gate5_formatting.md", g5)
    _write_gate_report(qa_dir / "gate6_completeness.md", g6)

    # Write remediation.json
    remediation = _build_remediation(results, manifest)
    remediation_path = qa_dir / "remediation.json"
    remediation_path.write_text(json.dumps(remediation, indent=2, ensure_ascii=False), encoding='utf-8')

    # Write summary
    summary = _write_summary(qa_dir / "summary.md", results, all_passed, total_warnings)

    return {
        "overall": "PASS" if all_passed else ("WARN" if total_warnings > 0 else "FAIL"),
        "total_warnings": total_warnings,
        "gates": results,
        "remediation_path": str(remediation_path),
        "summary_path": str(qa_dir / "summary.md"),
    }


def _gate_terminology(project_dir: Path, manifest: dict, foundation_dir: Path) -> dict:
    """Check terminology consistency against glossary."""
    glossary_path = foundation_dir / "glossary.md"
    issues = []
    terms_checked = 0

    if glossary_path.exists():
        content = glossary_path.read_text(encoding='utf-8')
        # Extract glossary terms from markdown table
        term_pattern = re.compile(r'\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|', re.MULTILINE)
        matches = term_pattern.findall(content)

        if matches:
            # Load wave2 chunks
            wave2_dir = project_dir / "chunks" / "translated" / "wave2"
            for chunk_meta in manifest["chunks"]:
                chunk_id = chunk_meta["id"]
                chunk_path = wave2_dir / f"{chunk_id}.md"
                if chunk_path.exists():
                    text = chunk_path.read_text(encoding='utf-8')
                    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL).strip()

                    for source_term, suggested_ru in matches:
                        source_term = source_term.strip()
                        if len(source_term) < 2:
                            continue
                        terms_checked += 1
                        # Check if source term appears untranslated
                        if re.search(r'\b' + re.escape(source_term) + r'\b', text, re.IGNORECASE):
                            # Check it's not the suggested Russian already
                            ru_term = suggested_ru.strip().strip('[]')
                            if ru_term != source_term and ru_term not in text:
                                issues.append(f"{chunk_id}: '{source_term}' may remain in original form")

    return {
        "status": "PASS" if len(issues) == 0 else "WARN",
        "terms_checked": terms_checked,
        "issues_found": len(issues),
        "details": issues[:10],  # first 10
    }


def _gate_integrity(project_dir: Path, manifest: dict, wave2_dir: Path) -> dict:
    """Check completeness — no missing or truncated chunks."""
    issues = []
    total = len(manifest["chunks"])
    missing = 0
    truncated = 0

    for chunk_meta in manifest["chunks"]:
        chunk_id = chunk_meta["id"]
        wave2_path = wave2_dir / f"{chunk_id}.md"

        if not wave2_path.exists():
            missing += 1
            issues.append(f"{chunk_id}: wave2 file missing")
            continue

        content = wave2_path.read_text(encoding='utf-8')
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL).strip()

        if len(content) < 20:
            truncated += 1
            issues.append(f"{chunk_id}: content suspiciously short ({len(content)} chars)")

        # Check length ratio against source
        src_wc = chunk_meta.get("word_count", 0)
        tr_wc = len(content.split())
        if src_wc > 0:
            ratio = tr_wc / src_wc
            if ratio < 0.3:
                issues.append(f"{chunk_id}: translation is {ratio:.0%} of source length")
                truncated += 1
            elif ratio > 2.5:
                issues.append(f"{chunk_id}: translation is {ratio:.0%} of source length (expansion)")

    if missing > 0 or truncated > 0:
        status = "FAIL" if missing > 0 else "WARN"
    else:
        status = "PASS"

    return {
        "status": status,
        "total_chunks": total,
        "missing": missing,
        "truncated": truncated,
        "issues_found": len(issues),
        "details": issues[:10],
    }


def _gate_style(project_dir: Path, manifest: dict, foundation_dir: Path) -> dict:
    """Check style guide compliance."""
    issues = []

    # Basic style checks (heuristic)
    wave2_dir = project_dir / "chunks" / "translated" / "wave2"

    for chunk_meta in manifest["chunks"]:
        chunk_id = chunk_meta["id"]
        chunk_path = wave2_dir / f"{chunk_id}.md"
        if not chunk_path.exists():
            continue

        content = chunk_path.read_text(encoding='utf-8')
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL).strip()

        # Check for common calques
        calque_patterns = [
            (r'\bбыть в состоянии\b', 'use "мочь" instead'),
            (r'\bв случае того\b', 'use "если" instead'),
            (r'\bс помощью\b(?!\s+чего)', 'consider simpler phrasing'),
            (r'\bтого факта что\b', 'use "что" instead'),
        ]

        for pattern, suggestion in calque_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"{chunk_id}: calque '{pattern}' — {suggestion}")

    return {
        "status": "PASS" if len(issues) == 0 else "WARN",
        "chunks_checked": len(manifest["chunks"]),
        "issues_found": len(issues),
        "details": issues[:10],
    }


def _gate_fluency(project_dir: Path, manifest: dict, wave2_dir: Path) -> dict:
    """Check Russian language quality."""
    issues = []

    for chunk_meta in manifest["chunks"]:
        chunk_id = chunk_meta["id"]
        chunk_path = wave2_dir / f"{chunk_id}.md"
        if not chunk_path.exists():
            continue

        content = chunk_path.read_text(encoding='utf-8')
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL).strip()

        # Check for uncertainty markers
        if '[?]' in content:
            issues.append(f"{chunk_id}: uncertainty marker [?] found")

        # Check for remaining source language fragments
        english_fragments = re.findall(r'\b(the|a|an|and|or|but|is|are|was|were|to|of|in|for)\s+[а-яё]+', content.lower())
        if english_fragments:
            issues.append(f"{chunk_id}: possible English fragments detected")

        # Check for broken grammar (no spaces after punctuation)
        if re.search(r'[.,;:!?][a-zA-Zа-яёА-ЯЁ]', content):
            issues.append(f"{chunk_id}: missing space after punctuation")

    return {
        "status": "PASS" if len(issues) == 0 else "WARN",
        "chunks_checked": len(manifest["chunks"]),
        "issues_found": len(issues),
        "details": issues[:10],
    }


def _gate_formatting(project_dir: Path, manifest: dict, wave2_dir: Path) -> dict:
    """Check Markdown formatting preservation."""
    issues = []

    for chunk_meta in manifest["chunks"]:
        chunk_id = chunk_meta["id"]
        chunk_path = wave2_dir / f"{chunk_id}.md"
        src_path = project_dir / "chunks" / "source" / f"{chunk_id}.md"

        if not chunk_path.exists():
            continue

        content = chunk_path.read_text(encoding='utf-8')

        # Count markdown elements
        headers = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE))
        lists = len(re.findall(r'^\s*[-*]\s', content, re.MULTILINE))
        code_blocks = len(re.findall(r'```', content))

        if src_path.exists():
            src = src_path.read_text(encoding='utf-8')
            src_headers = len(re.findall(r'^#{1,6}\s', src, re.MULTILINE))
            src_lists = len(re.findall(r'^\s*[-*]\s', src, re.MULTILINE))
            src_code_blocks = len(re.findall(r'```', src))

            # Check significant loss of structure
            if src_headers > 0 and headers == 0:
                issues.append(f"{chunk_id}: all headers lost")
            if src_lists > 0 and lists == 0:
                issues.append(f"{chunk_id}: all lists lost")
            if src_code_blocks > 2 and code_blocks < src_code_blocks - 1:
                issues.append(f"{chunk_id}: code blocks may be damaged")

    return {
        "status": "PASS" if len(issues) == 0 else "WARN",
        "chunks_checked": len(manifest["chunks"]),
        "issues_found": len(issues),
        "details": issues[:10],
    }


def _gate_completeness(project_dir: Path, manifest: dict, wave2_dir: Path) -> dict:
    """Check structural completeness — compression ratio, reference parity, headers.

    Flags chunks where the subagent summarised instead of translating:
    - Compression ratio below 50% (chars)
    - Reference loss > 30%
    - Plain-text headers from source missing in translation
    """
    issues = []
    total_source_chars = 0
    total_trans_chars = 0
    total_source_refs = 0
    total_trans_refs = 0
    severe_count = 0

    # Load canonical source to detect plain-text headers
    canonical_path = project_dir / "chunks" / "source" / "canonical.md"
    plain_headers: list[str] = []
    if canonical_path.exists():
        canon = canonical_path.read_text(encoding='utf-8')
        # Match lines that look like plain-text section headers (capitalized, standalone)
        plain_headers = re.findall(r'^([A-Z][A-Za-z\s/]{2,60})$', canon, re.MULTILINE)
        plain_headers = [h.strip() for h in plain_headers if len(h.strip()) > 3]

    # Load merged translation
    merged_path = project_dir / "output" / "translated.md"
    merged_text = ""
    if merged_path.exists():
        merged_text = merged_path.read_text(encoding='utf-8')
        merged_text = re.sub(r'^---\n.*?\n---\n', '', merged_text, flags=re.DOTALL).strip()

    # Check per-chunk completeness
    for chunk_meta in manifest["chunks"]:
        chunk_id = chunk_meta["id"]
        src_path = project_dir / "chunks" / "source" / f"{chunk_id}.md"
        tr_path = wave2_dir / f"{chunk_id}.md"

        if not src_path.exists() or not tr_path.exists():
            continue

        src = src_path.read_text(encoding='utf-8')
        src = re.sub(r'^---\n.*?\n---\n', '', src, flags=re.DOTALL).strip()

        tr = tr_path.read_text(encoding='utf-8')
        tr = re.sub(r'^---\n.*?\n---\n', '', tr, flags=re.DOTALL).strip()

        src_chars = len(src)
        tr_chars = len(tr)
        total_source_chars += src_chars
        total_trans_chars += tr_chars

        src_refs = len(re.findall(r'\[\d+\]', src))
        tr_refs = len(re.findall(r'\[\d+\]', tr))
        total_source_refs += src_refs
        total_trans_refs += tr_refs

        ratio = tr_chars / src_chars if src_chars > 0 else 1.0
        if ratio < 0.5:
            severe_count += 1
            ref_note = f", refs {src_refs}→{tr_refs}" if tr_refs < src_refs * 0.7 else ""
            issues.append(
                f"{chunk_id}: compression {ratio:.0%} (src={src_chars} → tr={tr_chars} chars{ref_note})"
            )

    # Global structural checks
    overall_ratio = total_trans_chars / total_source_chars if total_source_chars > 0 else 1.0
    if overall_ratio < 0.6:
        issues.append(
            f"OVERALL: translation is {overall_ratio:.0%} of source size "
            f"({total_source_chars} → {total_trans_chars} chars). "
            "Subagent likely summarised."
        )

    ref_ratio = total_trans_refs / total_source_refs if total_source_refs > 0 else 1.0
    if ref_ratio < 0.7:
        issues.append(
            f"REFERENCE LOSS: {total_source_refs} → {total_trans_refs} references "
            f"({ref_ratio:.0%} retained). Content likely dropped."
        )

    # Plain-text header preservation
    if plain_headers and merged_text:
        missing_headers = []
        known_translations = {
            "background": ["Предыстория", "Предпосылки"],
            "etymology": ["Этимология"],
            "geography": ["География"],
            "history": ["История"],
            "economy": ["Экономика"],
            "trade": ["Торговля"],
            "society": ["Общество"],
            "government": ["Государство", "Управление"],
            "religion": ["Религия"],
            "legacy": ["Наследие"],
            "language": ["Язык"],
            "writing": ["Письменность"],
            "art": ["Искусство"],
            "architecture": ["Архитектура"],
            "research": ["Исследования"],
            "sculpture": ["Скульптура"],
            "iconography": ["Иконография"],
            "inscriptions": ["Надписи"],
            "seals": ["Печати"],
        }

        for h in plain_headers:
            h_lower = h.lower().strip()
            # Check if original header appears in translation
            if h.strip() in merged_text:
                continue
            # Check known translations
            found = False
            for eng_word, ru_options in known_translations.items():
                if eng_word in h_lower:
                    for ru_opt in ru_options:
                        if ru_opt in merged_text:
                            found = True
                            break
                if found:
                    break
            if not found:
                missing_headers.append(h)

        if missing_headers:
            issues.append(
                f"HEADERS LOST: {len(missing_headers)} plain-text section headers "
                f"not found in translation: {', '.join(missing_headers[:8])}"
            )

    # Determine status
    if severe_count > 0:
        status = "FAIL" if severe_count >= 3 else "WARN"
    elif len(issues) == 0:
        status = "PASS"
    else:
        status = "WARN"

    return {
        "status": status,
        "total_chunks": len(manifest["chunks"]),
        "compressed_chunks": severe_count,
        "overall_ratio": round(overall_ratio, 2),
        "ref_ratio": round(ref_ratio, 2),
        "issues_found": len(issues),
        "details": issues[:15],
    }


def _write_gate_report(path: Path, result: dict) -> None:
    """Write a gate report to markdown file."""
    status_icon = "✓" if result["status"] == "PASS" else ("⚠" if result["status"] == "WARN" else "✗")
    lines = [
        f"# {path.stem.replace('_', ' ').title()}",
        "",
        f"**Status:** {status_icon} {result['status']}",
        "",
    ]
    if result.get("terms_checked"):
        lines.append(f"- Terms checked: {result['terms_checked']}")
    if result.get("total_chunks"):
        lines.append(f"- Chunks checked: {result['total_chunks']}")
    if result.get("chunks_checked"):
        lines.append(f"- Chunks checked: {result['chunks_checked']}")

    lines.append(f"- Issues found: {result.get('issues_found', 0)}")

    if result.get("details"):
        lines.append("")
        lines.append("### Issues")
        for detail in result["details"]:
            lines.append(f"- {detail}")

    path.write_text('\n'.join(lines), encoding='utf-8')


def _build_remediation(results: dict, manifest: dict) -> dict:
    """Build remediation.json from gate results.

    For gate6_completeness, generates actionable repair notes.
    """
    chunk_issues: dict[str, list[str]] = {}

    for gate_name, result in results.items():
        if not result.get("details"):
            continue

        is_completeness = gate_name == "gate6_completeness"

        for detail in result["details"]:
            # Try chunk_XXX pattern first (gate6 uses "chunk_005: compression ...")
            m = re.match(r"(chunk_\d+):\s*(.*)", detail)
            if m:
                chunk_id = m.group(1)
                rest = m.group(2)
                if is_completeness:
                    # Generate actionable remediation note
                    note = f"gate6: {rest}; retranslate without summarization; preserve all citations and structure"
                else:
                    gate_short = gate_name.replace("gate", "g").replace("_", "")[:3]
                    note = f"{gate_short}: {rest}"
                if chunk_id not in chunk_issues:
                    chunk_issues[chunk_id] = []
                chunk_issues[chunk_id].append(note)
                continue

            # Fallback: old split-format for other gates
            if ": " in detail:
                chunk_id = detail.split(": ")[0]
                if not re.match(r"chunk_\d+$", chunk_id):
                    continue
                gate_short = gate_name.replace("gate", "g").replace("_", "")[:3]
                if chunk_id not in chunk_issues:
                    chunk_issues[chunk_id] = []
                chunk_issues[chunk_id].append(gate_short)

    gate_summary = {k: {"status": v["status"]} for k, v in results.items()}

    return {
        "chunks": chunk_issues,
        "gates": gate_summary,
    }


def _write_summary(path: Path, results: dict, all_passed: bool, total_warnings: int) -> dict:
    """Write QA summary markdown."""
    lines = [
        "# Quality Gate Summary",
        "",
        "| Gate | Status | Notes |",
        "|---|---|---|",
    ]

    for gate_name, result in results.items():
        status = result["status"]
        icon = "✓" if status == "PASS" else ("⚠" if status == "WARN" else "✗")
        notes = f"{result.get('issues_found', 0)} issues"
        gate_display = gate_name.replace("_", " ").replace("gate", "Gate ").title()
        lines.append(f"| {icon} {gate_display} | {status} | {notes} |")

    overall = "PASS" if all_passed else ("WARN" if total_warnings > 0 else "FAIL")
    lines.extend(["", f"**Overall:** {overall}", f"**Total warnings:** {total_warnings}"])

    path.write_text('\n'.join(lines), encoding='utf-8')

    return {"overall": overall, "total_warnings": total_warnings}