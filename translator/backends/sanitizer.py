"""Sanitizer layer for subagent output validation and cleaning.

Handles:
- Conversational wrappers (\"Here's the translation:\", etc.)
- Markdown fence artifacts
- Reasoning blocks (<think>, <thinking>, <reasoning>)
- CJK contamination detection
"""

import re
from typing import Optional

# ── Reasoning block patterns ──────────────────────────────────────────────

THINK_PATTERNS = [
    r"<think>.*?</think>",
    r"<thinking>.*?</thinking>",
    r"<reasoning>.*?</reasoning>",
]

THINK_REGEXES = [re.compile(p, re.DOTALL | re.IGNORECASE) for p in THINK_PATTERNS]

# ── Wrapper patterns (existing) ───────────────────────────────────────────

WRAPPER_PATTERNS = [
    r"^(Вот |Вот перевод:|Пожалуйста,?\s*)",
    r"^(Here('s)? ?(is)? ?the? ?translation:?\s*)",
    r"^(Certainly|Of course|Sure)[,!]?\s*",
    r"^(Translation:\s*)",
    r"```(markdown|yaml|text|python|)\n",
    r"```\n",
]

WRAPPER_REGEXES = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in WRAPPER_PATTERNS]

# ── CJK Unicode ranges ───────────────────────────────────────────────────

CJK_RANGES = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0x2F800, 0x2FA1F), # CJK Compatibility Ideographs Supplement
    (0x3040, 0x309F),   # Hiragana
    (0x30A0, 0x30FF),   # Katakana
    (0xFF66, 0xFF9F),   # Half-width Katakana
    (0xAC00, 0xD7AF),   # Hangul Syllables
    (0x1100, 0x11FF),   # Hangul Jamo
    (0x3130, 0x318F),   # Hangul Compatibility Jamo
]


# ── Reasoning block cleaning ──────────────────────────────────────────────

def strip_reasoning_blocks(text: str) -> str:
    """Remove <think>, <thinking>, <reasoning> blocks entirely."""
    for regex in THINK_REGEXES:
        text = regex.sub("", text)
    return text


def collapse_blank_lines(text: str) -> str:
    """Replace 3+ consecutive blank lines with 2."""
    return re.sub(r"\n{3,}", "\n\n", text)


# ── CJK detection ────────────────────────────────────────────────────────

def _is_cjk(char: str) -> bool:
    """Check if a single character falls in any CJK range."""
    cp = ord(char)
    for lo, hi in CJK_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def detect_cjk_ratio(text: str) -> float:
    """Calculate ratio of CJK characters among non-space characters.

    Args:
        text: Input string.

    Returns:
        Float in [0.0, 1.0] — fraction of nonspace chars that are CJK.
    """
    if not text:
        return 0.0
    nonspace = "".join(text.split())
    if not nonspace:
        return 0.0
    cjk_count = sum(1 for ch in nonspace if _is_cjk(ch))
    return cjk_count / len(nonspace)


def has_suspicious_cjk(text: str, threshold: float = 0.02) -> bool:
    """Check if CJK ratio exceeds threshold.

    Args:
        text: Input string.
        threshold: Ratio above which content is flagged (default 0.02 = 2%).

    Returns:
        True if suspicious CJK contamination detected.
    """
    return detect_cjk_ratio(text) > threshold


# ── Main sanitizer ───────────────────────────────────────────────────────

def sanitize_subagent_output(output: str, chunk_id: str = "?") -> tuple[str, list[str]]:
    """Strip conversational wrappers, reasoning blocks, and non-translation noise.

    Args:
        output: Raw output from subagent.
        chunk_id: For error reporting.

    Returns:
        tuple of (cleaned_text, list_of_warnings).
    """
    warnings = []
    text = output

    # ── Strip trailing/leading whitespace ─────────────────────────────
    text = text.strip()

    # ── Remove reasoning blocks ───────────────────────────────────────
    cleaned = strip_reasoning_blocks(text)
    if cleaned != text:
        warnings.append(f"Stripped reasoning block(s)")
        text = cleaned

    # ── Collapse blank lines after reasoning block removal ────────────
    text = collapse_blank_lines(text)

    # ── Remove wrapper phrases at the beginning ────────────────────────
    for regex in WRAPPER_REGEXES:
        before = text
        text = regex.sub("", text)
        if text != before:
            warnings.append(f"Stripped wrapper pattern: {regex.pattern[:40]}...")

    # ── Remove markdown fences at start/end ────────────────────────────
    text = re.sub(r'^```[^\n]*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text)
    text = re.sub(r'\s*```\s*$', '', text)

    # ── Final strip ───────────────────────────────────────────────────
    text = text.strip()

    # ── Validate minimum content ratio ─────────────────────────────────
    if len(text) < 10:
        warnings.append(f"chunk_{chunk_id}: output suspiciously short ({len(text)} chars)")
        text = f"[translation unavailable for chunk {chunk_id}]"

    # ── Check for obvious non-translation markers ──────────────────────
    non_translation_markers = [
        "I cannot translate",
        "I'm sorry",
        "unable to translate",
        "translation error",
        "простите",
        "не могу перевести",
    ]
    for marker in non_translation_markers:
        if marker.lower() in text.lower():
            warnings.append(f"chunk_{chunk_id}: non-translation marker detected: '{marker}'")

    # ── CJK contamination warning ──────────────────────────────────────
    cjk_ratio = detect_cjk_ratio(text)
    if cjk_ratio > 0.02:
        warnings.append(
            f"chunk_{chunk_id}: suspicious CJK content detected "
            f"(ratio={cjk_ratio:.2%})"
        )
        # Prepend a warning comment (but keep the text intact)
        text = f"<!-- WARNING: suspicious CJK content detected (ratio={cjk_ratio:.2%}) -->\n{text}"

    return text, warnings


# ── Validation (unchanged from v1) ───────────────────────────────────────

def validate_translation_quality(text: str, source_text: str, chunk_id: str = "?") -> tuple[bool, list[str]]:
    """Check if translation appears to be valid.

    Returns:
        tuple of (is_valid, list_of_issues).
    """
    issues = []

    # Length ratio check
    if source_text:
        ratio = len(text) / max(len(source_text), 1)
        if ratio < 0.2:
            issues.append(f"chunk_{chunk_id}: translation is {ratio:.0%} of source length (possible truncation)")
        elif ratio > 3.0:
            issues.append(f"chunk_{chunk_id}: translation is {ratio:.0%} of source length (possible expansion)")

    # Check for embedded markdown structure
    has_any_markdown = bool(re.search(r'[#*`_\[\]()]', text))
    if not has_any_markdown and len(text) > 200:
        issues.append(f"chunk_{chunk_id}: no markdown formatting detected in long text")

    # Check for repeated characters (could indicate corruption)
    if re.search(r'(.)\1{10,}', text):
        issues.append(f"chunk_{chunk_id}: repeated character pattern detected (possible corruption)")

    is_valid = len(issues) == 0
    return is_valid, issues
