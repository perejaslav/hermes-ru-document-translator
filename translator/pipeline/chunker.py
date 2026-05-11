"""Canonical chunker — split source text into chunks with separate context files.

Architecture:
- Source chunks stored in chunks/source/chunk_XXX.md (with YAML frontmatter)
- Context stored separately in chunks/context/chunk_XXX.context.md
- Prompts stored in chunks/prompts/chunk_XXX.waveN.prompt.md
- Manifest stored in chunks/manifest.json (single source of truth)
"""

import json
import hashlib
import re
from pathlib import Path
from dataclasses import dataclass


TARGET_WORDS = 800  # target words per chunk
MAX_WORDS = 1500
MIN_WORDS = 100
CONTEXT_SENTENCES = 2


@dataclass
class ChunkInfo:
    id: str
    text: str
    word_count: int
    char_start: int
    char_end: int
    has_previous_context: bool
    has_next_context: bool


def chunk_text(text: str, project_slug: str) -> list[ChunkInfo]:
    """Split text into chunks following canonical rules.

    Rules:
    - 500-1500 words per chunk (target ~800)
    - Prefer paragraph/heading boundaries
    - Never split mid-sentence
    - Never split code blocks
    - Stable IDs: chunk_001, chunk_002, ...
    """
    # Protect code blocks first
    protected, code_map = _protect_code_blocks(text)

    paragraphs = _split_into_paragraphs(protected)

    chunks = _create_chunks(paragraphs, project_slug)

    # Restore code blocks
    for chunk in chunks:
        chunk.text = _restore_code_blocks(chunk.text, code_map)

    return chunks


def _protect_code_blocks(text: str) -> tuple[str, dict]:
    """Replace code blocks with placeholders to prevent splitting."""
    code_map = {}
    pattern = r'(```[\s\S]*?```|`[^`\n]+`)'

    def replacer(match):
        placeholder = f"__CODE_BLOCK_{len(code_map)}_PLACEHOLDER__"
        code_map[placeholder] = match.group(0)
        return placeholder

    protected = re.sub(pattern, replacer, text)
    return protected, code_map


def _restore_code_blocks(text: str, code_map: dict) -> str:
    """Restore code blocks from placeholders."""
    result = text
    for placeholder, original in code_map.items():
        result = result.replace(placeholder, original)
    return result


def _split_into_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs at double newlines."""
    paras = []
    for block in text.split('\n\n'):
        block = block.strip()
        if block:
            paras.append(block)
    return paras


def _create_chunks(paragraphs: list[str], project_slug: str) -> list[ChunkInfo]:
    """Group paragraphs into chunks of target size."""
    chunks = []
    current_chunk_paras = []
    current_word_count = 0
    chunk_num = 1

    for para in paragraphs:
        para_words = len(para.split())

        # Check if single paragraph is too large
        if para_words > MAX_WORDS:
            # Flush current chunk
            if current_chunk_paras:
                chunks.append(_make_chunk(
                    current_chunk_paras, chunk_num, project_slug, len(chunks) > 0, False
                ))
                chunk_num += 1
                current_chunk_paras = []
                current_word_count = 0

            # Split oversized paragraph by sentences
            sub_chunks = _split_oversized_paragraph(para, project_slug, chunk_num)
            # Last sub-chunk will set has_next_context
            for i, sub in enumerate(sub_chunks):
                has_prev = i > 0
                has_next = i < len(sub_chunks) - 1
                chunks.append(ChunkInfo(
                    id=f"chunk_{chunk_num:03d}",
                    text=sub,
                    word_count=len(sub.split()),
                    char_start=0, char_end=0,
                    has_previous_context=has_prev,
                    has_next_context=has_next,
                ))
                chunk_num += 1
            continue

        # Check if adding this paragraph exceeds target
        if current_word_count + para_words > TARGET_WORDS and current_chunk_paras:
            # Finish current chunk
            chunks.append(_make_chunk(
                current_chunk_paras, chunk_num, project_slug, len(chunks) > 0, False
            ))
            chunk_num += 1
            current_chunk_paras = []
            current_word_count = 0

        current_chunk_paras.append(para)
        current_word_count += para_words

    # Don't forget last chunk
    if current_chunk_paras:
        chunks.append(_make_chunk(
            current_chunk_paras, chunk_num, project_slug, len(chunks) > 0, False
        ))

    # Set has_next_context for all chunks (last chunk = False)
    for i, chunk in enumerate(chunks):
        if i < len(chunks) - 1:
            chunk.has_next_context = True

    return chunks


def _split_oversized_paragraph(para: str, project_slug: str, chunk_num: int) -> list[str]:
    """Split oversized paragraph at sentence boundaries."""
    # Sentence pattern (handles common abbreviations)
    sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-ZА-ЯЁ])')

    sentences = sentence_end.split(para)
    sub_chunks = []
    current = []

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        current_words = sum(len(c.split()) for c in current)
        if current_words + len(sent.split()) > MAX_WORDS and current:
            sub_chunks.append(' '.join(current))
            current = [sent]
        else:
            current.append(sent)

    if current:
        sub_chunks.append(' '.join(current))

    return sub_chunks if sub_chunks else [para]


def _make_chunk(
    paragraphs: list[str],
    chunk_num: int,
    project_slug: str,
    has_previous_context: bool,
    has_next_context: bool
) -> ChunkInfo:
    """Create a ChunkInfo from paragraphs."""
    text = '\n\n'.join(paragraphs)
    word_count = len(text.split())

    return ChunkInfo(
        id=f"chunk_{chunk_num:03d}",
        text=text,
        word_count=word_count,
        char_start=0,  # char offsets computed after full pass
        char_end=0,
        has_previous_context=has_previous_context,
        has_next_context=has_next_context,
    )


def save_chunks(chunks: list[ChunkInfo], project_dir: Path) -> Path:
    """Save chunks to canonical directory structure.

    Creates:
    - chunks/source/chunk_XXX.md (with YAML frontmatter)
    - chunks/context/chunk_XXX.context.md
    - chunks/manifest.json
    """
    source_dir = project_dir / "chunks" / "source"
    context_dir = project_dir / "chunks" / "context"
    source_dir.mkdir(parents=True, exist_ok=True)
    context_dir.mkdir(parents=True, exist_ok=True)

    manifest_chunks = []
    total_chars = 0

    for i, chunk in enumerate(chunks):
        # Compute char offsets
        chunk.char_start = total_chars
        chunk.char_end = total_chars + len(chunk.text)
        total_chars += len(chunk.text) + 2  # for \n\n

        # Save source chunk with YAML header
        source_path = source_dir / f"{chunk.id}.md"
        content = _make_source_frontmatter(chunk) + chunk.text
        source_path.write_text(content, encoding='utf-8')

        # Save context file
        prev_context = _get_previous_context(chunks, i) if chunk.has_previous_context else None
        next_context = _get_next_context(chunks, i) if chunk.has_next_context else None

        context_path = context_dir / f"{chunk.id}.context.md"
        context_content = _make_context_file(chunk.id, prev_context, next_context)
        context_path.write_text(context_content, encoding='utf-8')

        # Build manifest entry
        manifest_chunks.append({
            "id": chunk.id,
            "word_count": chunk.word_count,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "source_hash": hashlib.sha256(chunk.text.encode()).hexdigest(),
            "has_previous_context": chunk.has_previous_context,
            "has_next_context": chunk.has_next_context,
            "wave1_status": "pending",
            "wave2_status": "pending",
            "qa_status": "pending",
        })

    # Save manifest
    manifest = {
        "project_slug": project_dir.name,
        "source_hash": hashlib.sha256('\n'.join(c.text for c in chunks).encode()).hexdigest(),
        "total_chunks": len(chunks),
        "chunks": manifest_chunks,
    }

    manifest_path = project_dir / "chunks" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    return manifest_path


def _make_source_frontmatter(chunk: ChunkInfo) -> str:
    from datetime import datetime
    return f"---\nchunk_id: {chunk.id}\nword_count: {chunk.word_count}\nproject: {chunk.id.split('_')[1]}\nwave: source\n---\n\n"


def _make_context_file(chunk_id: str, previous: str | None, next_ctx: str | None) -> str:
    lines = [f"# Context for {chunk_id}", "", "## Previous context", ""]
    if previous:
        lines.append(previous)
    else:
        lines.append("None.")
    lines.extend(["", "## Next context", ""])
    if next_ctx:
        lines.append(next_ctx)
    else:
        lines.append("None.")
    return '\n'.join(lines)


def _get_previous_context(chunks: list[ChunkInfo], index: int) -> str | None:
    """Get last 2 sentences of previous chunk."""
    if index == 0:
        return None
    prev_text = chunks[index - 1].text
    sentences = _extract_sentences(prev_text)
    if len(sentences) >= 2:
        return ' '.join(sentences[-2:])
    elif sentences:
        return sentences[-1]
    return None


def _get_next_context(chunks: list[ChunkInfo], index: int) -> str | None:
    """Get first 2 sentences of next chunk."""
    if index >= len(chunks) - 1:
        return None
    next_text = chunks[index + 1].text
    sentences = _extract_sentences(next_text)
    if len(sentences) >= 2:
        return ' '.join(sentences[:2])
    elif sentences:
        return sentences[0]
    return None


def _extract_sentences(text: str) -> list[str]:
    """Extract sentences from text."""
    # Split on sentence-ending punctuation
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def normalize_plain_text_headers(markdown: str) -> str:
    """Convert plain-text section headers to Markdown ## headers.

    Detects standalone lines that look like section headings:
    - Surrounded by blank lines
    - 3-80 characters, starts with uppercase
    - Does not end with a period
    - Does not contain citation markers like [N]
    - Not already a Markdown header
    - Not inside code blocks, not a table line, not a table caption

    Examples:
        ``Background`` → ``## Background``
        ``Political Structure and Dynasties`` → ``## Political Structure and Dynasties``
    """
    # Protect code blocks
    code_map = {}
    code_block_counter = 0

    def _protect_code(match: re.Match) -> str:
        nonlocal code_block_counter
        placeholder = f"__CODE_BLOCK_{code_block_counter}_PH__"
        code_map[placeholder] = match.group(0)
        code_block_counter += 1
        return placeholder

    protected = re.sub(r'(```[\s\S]*?```)', _protect_code, markdown)

    lines = protected.split('\n')
    result = list(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip: already a header, empty lines, inline code
        if not stripped:
            continue
        if stripped.startswith('#'):
            continue
        if stripped.startswith('|') or stripped.endswith('|'):
            # Table row
            continue
        if re.search(r'\[(\d+|[A-Za-z])\]', stripped):
            # Contains citation marker like [1], [N], [Ref]
            continue
        if stripped.startswith('>'):
            # Blockquote — skip
            continue

        # Length check
        if len(stripped) < 3 or len(stripped) > 80:
            continue

        # Must start with uppercase letter
        if not stripped[0].isupper():
            continue

        # Must not end with sentence-ending punctuation
        if stripped.endswith(('.', '!', '?')):
            continue

        # Must be standalone (blank line before and after, or start/end of file)
        has_blank_before = (i == 0) or (lines[i - 1].strip() == '')
        has_blank_after = (i == len(lines) - 1) or (lines[i + 1].strip() == '')

        if not (has_blank_before and has_blank_after):
            continue

        # Check it looks like a header (not a fragment)
        # Must contain mostly letters and spaces
        alpha_space = sum(1 for c in stripped if c.isalpha() or c.isspace())
        if alpha_space / max(len(stripped), 1) < 0.6:
            continue

        # Check not a table caption (line before table row)
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line.startswith('|') and next_line.endswith('|'):
                continue  # This line is a caption, not a header

        # It's a plain-text header — convert
        result[i] = f"## {stripped}"

    # Restore code blocks
    final = '\n'.join(result)
    for placeholder, original in code_map.items():
        final = final.replace(placeholder, original)

    return final