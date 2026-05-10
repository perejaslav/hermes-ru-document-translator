"""Sanitizer layer for subagent output validation and cleaning."""

import re
from typing import Optional


WRAPPER_PATTERNS = [
    r"^(Вот |Вот перевод:|Пожалуйста,?\s*)",
    r"^(Here('s)? ?(is)? ?the? ?translation:?\s*)",
    r"^(Certainly|Of course|Sure)[,!]?\s*",
    r"^(Translation:\s*)",
    r"```(markdown|yaml|text|python|)\n",
    r"```\n",
]

WRAPPER_REGEXES = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in WRAPPER_PATTERNS]


def sanitize_subagent_output(output: str, chunk_id: str = "?") -> tuple[str, list[str]]:
    """Strip conversational wrappers and non-translation noise from subagent output.

    Args:
        output: Raw output from subagent
        chunk_id: For error reporting

    Returns:
        tuple of (cleaned_text, list_of_warnings)
    """
    warnings = []
    text = output

    # Strip trailing/leading whitespace
    text = text.strip()

    # Remove wrapper phrases at the beginning
    for regex in WRAPPER_REGEXES:
        before = text
        text = regex.sub("", text)
        if text != before:
            warnings.append(f"Stripped wrapper pattern: {regex.pattern[:40]}...")

    # Remove markdown fences at start/end (handles fenced code blocks)
    # Opening fence
    text = re.sub(r'^```[^\n]*\n', '', text)
    # Closing fence (handles ``` on its own line at end)
    text = re.sub(r'\n```\s*$', '', text)
    # Also handle stray closing fences without leading newline
    text = re.sub(r'\s*```\s*$', '', text)

    # Strip any remaining leading/trailing newlines
    text = text.strip()

    # Validate minimum content ratio
    if len(text) < 10:
        warnings.append(f"chunk_{chunk_id}: output suspiciously short ({len(text)} chars)")
        text = f"[translation unavailable for chunk {chunk_id}]"

    # Check for obvious non-translation markers
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

    return text, warnings


def validate_translation_quality(text: str, source_text: str, chunk_id: str = "?") -> tuple[bool, list[str]]:
    """Check if translation appears to be valid.

    Returns:
        tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Length ratio check
    if source_text:
        ratio = len(text) / max(len(source_text), 1)
        if ratio < 0.2:
            issues.append(f"chunk_{chunk_id}: translation is {ratio:.0%} of source length (possible truncation)")
        elif ratio > 3.0:
            issues.append(f"chunk_{chunk_id}: translation is {ratio:.0%} of source length (possible expansion)")

    # Check for embedded markdown structure (should be present in good translation)
    has_any_markdown = bool(re.search(r'[#*`_\[\]()]', text))
    if not has_any_markdown and len(text) > 200:
        issues.append(f"chunk_{chunk_id}: no markdown formatting detected in long text")

    # Check for repeated characters (could indicate corruption)
    if re.search(r'(.)\1{10,}', text):
        issues.append(f"chunk_{chunk_id}: repeated character pattern detected (possible corruption)")

    is_valid = len(issues) == 0
    return is_valid, issues