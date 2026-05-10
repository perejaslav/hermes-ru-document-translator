"""Foundation builder — generate glossary, style guide, and entity register from source text."""

import re
from pathlib import Path
from collections import Counter
from typing import Optional


def build_foundation(source_text: str, *, source_lang: str = "en") -> dict[str, Path]:
    """Build glossary, style, and entities from source text.

    Args:
        source_text: extracted source text
        source_lang: detected source language

    Returns:
        dict mapping foundation type to created file path
    """
    project_dir = Path.cwd()  # caller must set correct cwd

    # Determine word count
    words = source_text.split()
    word_count = len(words)

    foundation_dir = project_dir / "foundation"
    foundation_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Build glossary
    glossary_path = foundation_dir / "glossary.md"
    _build_glossary(source_text, glossary_path, word_count)
    results["glossary"] = glossary_path

    # Build style guide
    style_path = foundation_dir / "style.md"
    _build_style(source_text, style_path, word_count)
    results["style"] = style_path

    # Build entity register
    entities_path = foundation_dir / "entities.md"
    _build_entities(source_text, entities_path, source_lang)
    results["entities"] = entities_path

    return results


def _build_glossary(text: str, output_path: Path, word_count: int) -> None:
    """Generate glossary from source text using heuristics."""
    if word_count < 100:
        _create_placeholder(output_path, "glossary", "source text too short for reliable term extraction")
        return

    # Find repeated capitalized terms (likely technical/proper nouns)
    words = text.split()
    capitalized = [w.strip('.,;:!?()[]{}"\'') for w in words if w and w[0].isupper() and w[0].isalpha()]
    cap_counts = Counter(capitalized)

    # Find technical terms ( CamelCase or snake_case )
    camel_case = re.findall(r'\b[A-Z][a-z]+[A-Z]\w+|\b[a-z]+_[a-z]+\b', text)

    # Extract potential terms (repeated 2+ times, 2+ chars)
    candidates = []
    for word, count in cap_counts.items():
        if len(word) >= 3 and count >= 2:
            candidates.append((word, count))

    candidates.sort(key=lambda x: -x[1])

    lines = [
        "# Glossary",
        "",
        "> Bilingual terminology table. Generated heuristically — verify all terms.",
        "",
        "| source_term | suggested_ru | domain | preserve_original | notes |",
        "|---|---|---|---|---|",
    ]

    if candidates:
        for term, count in candidates[:30]:
            # Simple heuristic translation (prefix with term for now, LLM would do real translation)
            # For mock/heuristic mode, we just mark the term
            domain = "technical" if '_' in term.lower() or any(c.isupper() for c in term[1:]) else "general"
            notes = f"appears {count} times"
            lines.append(f"| {term} | [{term}] | {domain} | yes | {notes} |")
    else:
        lines.append("| — | — | — | — | no terms detected |")

    output_path.write_text('\n'.join(lines), encoding='utf-8')


def _build_style(text: str, output_path: Path, word_count: int) -> None:
    """Generate style guide from source text."""
    if word_count < 100:
        _create_placeholder(output_path, "style", "source text too short for style analysis")
        return

    # Analyze sentence length
    sentences = re.split(r'[.!?]+', text)
    sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
    avg_sentence_len = sum(sentence_lengths) / max(len(sentence_lengths), 1)

    # Analyze paragraph structure
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    has_lists = bool(re.search(r'^\s*[-*•]\s', text, re.MULTILINE))
    has_headers = bool(re.search(r'^#{1,6}\s', text, re.MULTILINE))

    # Determine tone from average sentence length
    if avg_sentence_len > 25:
        tone = "formal, complex sentences"
    elif avg_sentence_len > 15:
        tone = "semi-formal, moderate complexity"
    else:
        tone = "informal, simple sentences"

    lines = [
        "# Style Guide",
        "",
        "## Tone and register",
        f"- Detected tone: {tone}",
        f"- Average sentence length: {avg_sentence_len:.1f} words",
        "",
        "## Sentence structure",
        "- Use varied sentence lengths for natural Russian",
        "- Avoid extremely long sentences (>40 words) without commas",
        "- Prefer active voice",
        "",
        "## Domain conventions",
        "- Translate technical terms consistently",
        "- Maintain domain-specific capitalization",
        "",
        "## Formatting conventions",
        "- Preserve original heading hierarchy (H1, H2, H3)",
        "- Convert lists to Russian-appropriate markers (—, •)",
        "- Code blocks: preserve monospace formatting",
        "",
        "## Terms and constructions to avoid",
        "- Direct calques: 'быть в состоянии' → 'мочь', 'в случае того' → 'если'",
        "- Anglicisms where Russian equivalents exist",
        "- Word-by-word translation of compound terms",
        "",
        "## Example translation patterns",
        "- English: 'the system is able to process'",
        "- Russian: 'система может обрабатывать' (not 'система находится в состоянии обработки')",
    ]

    output_path.write_text('\n'.join(lines), encoding='utf-8')


def _build_entities(text: str, output_path: Path, source_lang: str) -> None:
    """Generate entity register from source text using heuristics."""
    lines = [
        "# Entity Register",
        "",
        "> Named entities extracted from source text. Verify translations.",
        "",
        "| entity | type | context | suggested_ru | preserve_original | consistency_note |",
        "|---|---|---|---|---|---|",
    ]

    # Heuristic: find capitalized multi-word sequences (likely names/places/orgs)
    # Pattern: 2-4 capitalized words in sequence
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b'
    matches = re.findall(pattern, text)

    seen = {}
    for entity in matches:
        entity = entity.strip()
        if len(entity.split()) >= 2 and len(entity) >= 5 and entity not in seen:
            # Determine type heuristically
            if any(w in entity for w in ['University', 'Institute', 'Company', 'Organization', 'Inc', 'Corp']):
                ent_type = "ORG"
            elif any(w in entity for w in ['of', 'in', 'at', 'von', 'de']):
                ent_type = "GPE"
            else:
                ent_type = "PERSON"  # could be any capitalized multi-word name

            count = len(re.findall(r'\b' + re.escape(entity) + r'\b', text))
            note = f"appears {count} times"
            lines.append(f"| {entity} | {ent_type} | ... | [{entity}] | no | {note} |")
            seen[entity] = True

    if not seen:
        lines.append("| — | — | — | — | — | no entities detected |")

    output_path.write_text('\n'.join(lines), encoding='utf-8')


def _create_placeholder(output_path: Path, kind: str, reason: str) -> None:
    """Create a placeholder foundation file with warning."""
    lines = [
        f"# {kind.title()}",
        "",
        f"> ⚠️ Placeholder: {reason}",
        "",
        "| source | target | notes |",
        "|---|---|---|",
        f"| [term] | [translation] | placeholder — {reason} |",
    ]
    output_path.write_text('\n'.join(lines), encoding='utf-8')