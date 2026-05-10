"""QA chunk stage — run deterministic QA checks.

Two modes:
1. Pre-merge (default): check translated chunks in chunks/translated/
2. Post-merge (when output/translated.md exists): check final translated.md

QA always runs on the FINAL output file (translated.md) after merge,
so qa_findings.json reflects the actual user-facing result.
"""
import json
import re
from pathlib import Path


BLOCK_ID_PATTERN = re.compile(r'<!--BLOCK_ID:\s*([a-zA-Z0-9_-]+)\s*-->')


def run(workspace: Path, **kwargs) -> dict:
    """
    Run deterministic QA checks.

    Pre-merge: checks translated chunks (chunks/translated/*.md)
    Post-merge: checks final output (output/translated.md)

    When both exist, post-merge takes priority — QA reports the
    actual user-facing result, not intermediate state.

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with QA results
    """
    # Load block index
    block_index_path = workspace / "state" / "block_index.json"
    if not block_index_path.exists():
        return {"status": "failed", "error": "block_index.json not found"}

    with open(block_index_path, 'r', encoding='utf-8') as f:
        block_data = json.load(f)

    source_blocks = set(block_data.get("blocks", {}).keys())

    findings = []
    total_checks = 0
    passed_checks = 0

    # Determine mode: post-merge if translated.md exists
    final_output = workspace / "output" / "translated.md"
    final_debug = workspace / "output" / "translated.debug.md"

    if final_output.exists():
        # === POST-MERGE MODE: check final output ===
        print("  Mode: post-merge (checking translated.md)")

        with open(final_output, 'r', encoding='utf-8') as f:
            content = f.read()

        total_checks = 1

        # Check 1: BLOCK_ID completeness in debug file
        if final_debug.exists():
            with open(final_debug, 'r', encoding='utf-8') as f:
                debug_content = f.read()
            translated_blocks = set(BLOCK_ID_PATTERN.findall(debug_content))
            missing = source_blocks - translated_blocks
            if missing:
                findings.append({
                    "check": "block_completeness",
                    "severity": "WARNING",
                    "message": f"Missing BLOCK_IDs: {missing}",
                    "note": "BLOCK_ID stripped from translated.md but present in translated.debug.md"
                })
            else:
                passed_checks += 1

        # Check 2: Language — Cyrillic presence
        cyrillic_count = len(re.findall(r'[\u0400-\u04FF]', content))
        if cyrillic_count < 10:
            findings.append({
                "check": "language",
                "severity": "WARNING",
                "message": "Translated text contains very few Cyrillic characters"
            })
        else:
            passed_checks += 1

        # Check 3: Guardrail markers (should be 0 in final output)
        guardrail_open = content.count('<!--GUARDRAIL:')
        guardrail_close = content.count('<--GUARDRAIL_CLOSE-->')
        guardrail_fragment = content.count('<---->')
        if guardrail_open > 0 or guardrail_close > 0 or guardrail_fragment > 0:
            findings.append({
                "check": "guardrails",
                "severity": "WARNING",
                "message": f"Guardrail artifacts: {guardrail_open} open, {guardrail_close} close, {guardrail_fragment} fragments"
            })
        else:
            passed_checks += 1

        # Check 4: BLOCK_ID presence in final output (should be 0 now)
        block_ids_in_final = BLOCK_ID_PATTERN.findall(content)
        if block_ids_in_final:
            findings.append({
                "check": "block_id_cleanup",
                "severity": "WARNING",
                "message": f"{len(block_ids_in_final)} BLOCK_ID markers still in translated.md"
            })
        else:
            passed_checks += 1

        # Check 5: Markdown structure (basic)
        lines = content.split('\n')
        unclosed_code_fences = sum(1 for i, l in enumerate(lines)
                                    if l.strip().startswith('```')
                                    and not any(l.strip() == '```' for l in lines[i+1:]))
        if unclosed_code_fences > 0:
            findings.append({
                "check": "markdown_structure",
                "severity": "WARNING",
                "message": f"Possibly unclosed code fences detected"
            })
        else:
            passed_checks += 1

        # Check 6: Empty file
        if len(content.strip()) == 0:
            findings.append({
                "check": "file_empty",
                "severity": "CRITICAL",
                "message": "translated.md is empty"
            })
        else:
            passed_checks += 1

    else:
        # === PRE-MERGE MODE: check translated chunks ===
        print("  Mode: pre-merge (checking chunks)")

        chunk_index_path = workspace / "state" / "chunk_index.json"
        if not chunk_index_path.exists():
            return {"status": "failed", "error": "chunk_index.json not found"}

        with open(chunk_index_path, 'r', encoding='utf-8') as f:
            chunk_data = json.load(f)

        chunks = chunk_data.get("chunks", [])
        translated_dir = workspace / "chunks" / "translated"

        for chunk_info in chunks:
            chunk_id = chunk_info["chunk_id"]
            translated_path = translated_dir / f"{chunk_id}.md"

            total_checks += 1

            if not translated_path.exists():
                findings.append({
                    "chunk_id": chunk_id,
                    "severity": "CRITICAL",
                    "check": "file_exists",
                    "message": "Translated chunk file not found"
                })
                continue

            with open(translated_path, 'r', encoding='utf-8') as f:
                translated_content = f.read()

            # Check 1: BLOCK_ID completeness
            translated_blocks = set(BLOCK_ID_PATTERN.findall(translated_content))
            missing = source_blocks - translated_blocks
            extra = translated_blocks - source_blocks

            if missing:
                findings.append({
                    "chunk_id": chunk_id,
                    "severity": "WARNING",
                    "check": "block_completeness",
                    "message": f"Missing BLOCK_IDs: {missing}"
                })
            else:
                passed_checks += 1

            # Check 2: Language — contains Cyrillic
            cyrillic_count = len(re.findall(r'[\u0400-\u04FF]', translated_content))
            if cyrillic_count < 10:
                findings.append({
                    "chunk_id": chunk_id,
                    "severity": "WARNING",
                    "check": "language",
                    "message": "Translated text contains very few Cyrillic characters"
                })

            # Check 3: Guardrail markers
            guardrail_count = translated_content.count('<!--GUARDRAIL:')
            if guardrail_count > 0:
                findings.append({
                    "chunk_id": chunk_id,
                    "severity": "WARNING",
                    "check": "guardrails",
                    "message": f"{guardrail_count} guardrail markers still present"
                })

    # Save QA findings
    qa_path = workspace / "state" / "qa_findings.json"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    with open(qa_path, 'w', encoding='utf-8') as f:
        json.dump({
            "findings": findings,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "mode": "post-merge" if final_output.exists() else "pre-merge",
            "summary": {
                "critical": len([f for f in findings if f["severity"] == "CRITICAL"]),
                "warnings": len([f for f in findings if f["severity"] == "WARNING"])
            }
        }, f, indent=2, ensure_ascii=False)

    return {
        "status": "completed",
        "total_chunks_checked": total_checks,
        "passed": passed_checks,
        "findings_count": len(findings),
        "qa_report": str(qa_path),
        "mode": "post-merge" if final_output.exists() else "pre-merge"
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python qa_chunk.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)