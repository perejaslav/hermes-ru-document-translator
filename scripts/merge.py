"""Merge stage — assemble translated chunks into final document.

Produces two outputs:
- output/translated.debug.md  — with BLOCK_ID markers (for QA/reference)
- output/translated.md        — fully cleaned (no BLOCK_ID, no guardrails)

BLOCK_ID cleanup happens here so the user-facing output is always clean.
Also normalizes fenced code blocks (no leading spaces on triple backticks,
and strip BLOCK_ID markers that may appear inside code block content).
"""
import json
import re
from pathlib import Path


BLOCK_ID_PATTERN = re.compile(r'<!--BLOCK_ID:\s*([a-zA-Z0-9_-]+)\s*-->')
GUARDRAIL_OPEN_PATTERN = re.compile(r'<!--GUARDRAIL:[^>]+-->')
GUARDRAIL_CLOSE_FRAGMENT = '<---->'
GUARDRAIL_CLOSE_TAG = '<--GUARDRAIL_CLOSE-->'


def _normalize_fenced_code_blocks(text: str) -> str:
    """
    Normalize fenced code blocks: ensure no leading spaces on ``` fences,
    and strip BLOCK_ID markers that may appear inside code block content.

    Problem 1: opening/closing fences may have leading spaces (e.g. " ```python")
    Problem 2: code block content may have leading indentation (e.g. "    print())
    Problem 3: closing fence may have content on same line (e.g. "``` python")
    Problem 4: BLOCK_ID markers may be embedded inside code block content
               (LLM sometimes places them inside code blocks during translation)
    """
    lines = text.split('\n')
    result_lines = []
    in_fence = False
    fence_lang = ""

    for line in lines:
        fence_match = re.match(r'^(\s*)(`{3})(.*)$', line)

        if fence_match:
            leading_space = fence_match.group(1)
            fence = fence_match.group(2)
            fence_rest = fence_match.group(3)  # e.g. "python" or ""

            if not in_fence:
                # Opening fence: strip leading space
                in_fence = True
                fence_lang = fence_rest
                result_lines.append(fence + fence_rest)
            else:
                # Closing fence: strip leading space
                in_fence = False
                fence_lang = ""
                if fence_rest.strip():
                    result_lines.append(fence + fence_rest.strip())
                else:
                    result_lines.append(fence)
        elif in_fence:
            # Strip BLOCK_ID first (before lstrip), then remove leading whitespace
            # If we lstrip first, BLOCK_ID in the middle of line won't be stripped
            cleaned = BLOCK_ID_PATTERN.sub('', line)
            cleaned = cleaned.lstrip()
            result_lines.append(cleaned)
        else:
            result_lines.append(line)

    return '\n'.join(result_lines)


def run(workspace: Path, **kwargs) -> dict:
    """
    Merge translated chunks into final document (two versions).

    Steps:
    1. Load chunk index
    2. Read chunks in order
    3. Strip guardrail markers → translated.debug.md (keeps BLOCK_ID)
    4. Normalize fenced code blocks (fix leading spaces, strip BLOCK_ID inside code)
    5. Strip BLOCK_ID → translated.md (clean user output)
    6. Copy both to output/

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with merge results (two output paths)
    """
    # Load chunk index
    chunk_index_path = workspace / "state" / "chunk_index.json"
    if not chunk_index_path.exists():
        return {"status": "failed", "error": "chunk_index.json not found"}

    with open(chunk_index_path, 'r', encoding='utf-8') as f:
        chunk_data = json.load(f)

    chunks = chunk_data.get("chunks", [])
    translated_dir = workspace / "chunks" / "translated"

    merged_lines = []
    total_chars = 0
    chunks_merged = 0

    for chunk_info in chunks:
        chunk_id = chunk_info["chunk_id"]
        translated_path = translated_dir / f"{chunk_id}.md"

        if not translated_path.exists():
            merged_lines.append(f"\n<!-- MISSING CHUNK: {chunk_id} -->\n")
            continue

        with open(translated_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Strip guardrail markers (keep BLOCK_ID for debug version)
        content = GUARDRAIL_OPEN_PATTERN.sub('', content)
        content = content.replace(GUARDRAIL_CLOSE_TAG, '')
        content = content.replace(GUARDRAIL_CLOSE_FRAGMENT, '')

        merged_lines.append(content)
        merged_lines.append('\n')
        total_chars += len(content)
        chunks_merged += 1

    merged_text = '\n'.join(merged_lines)

    # Clean up excessive blank lines
    merged_text = re.sub(r'\n{3,}', '\n\n', merged_text)

    # Normalize fenced code blocks: fix fences and strip BLOCK_ID inside code
    merged_text = _normalize_fenced_code_blocks(merged_text)

    # Output directory
    output_dir = workspace / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. translated.debug.md — with BLOCK_ID (for QA/reference)
    debug_path = output_dir / "translated.debug.md"
    with open(debug_path, 'w', encoding='utf-8') as f:
        f.write(merged_text)

    # 2. translated.md — fully cleaned (no BLOCK_ID, no guardrails)
    clean_text = BLOCK_ID_PATTERN.sub('', merged_text)
    clean_path = output_dir / "translated.md"
    with open(clean_path, 'w', encoding='utf-8') as f:
        f.write(clean_text)

    # Count remaining artifacts
    guardrails_remaining = merged_text.count('<!--GUARDRAIL:')
    block_ids_remaining = BLOCK_ID_PATTERN.findall(merged_text)

    return {
        "status": "completed",
        "chunks_merged": chunks_merged,
        "total_chars": len(clean_text),
        "debug_path": str(debug_path),
        "output_path": str(clean_path),
        "guardrails_in_debug": guardrails_remaining,
        "block_ids_in_debug": len(block_ids_remaining),
        "block_ids_stripped": len(block_ids_remaining),
        "note": "BLOCK_ID stripped from translated.md; kept in translated.debug.md; fenced code blocks normalized; BLOCK_ID inside code blocks stripped"
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python merge.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)