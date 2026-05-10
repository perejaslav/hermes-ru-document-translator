"""Protect spans stage — mark non-translatable content."""
import re
from pathlib import Path


PROTECTION_PATTERNS = [
    (r'`[^`]+`', 'inline_code'),  # Inline code
    (r'```[\s\S]*?```', 'code_block'),  # Code blocks
    (r'\[([^\]]+)\]\([^\)]+\)', 'link'),  # Links [text](url)
    (r'https?://\S+', 'url'),  # URLs
    (r'<[^>]+>', 'html_tag'),  # HTML tags
]


GUARDRAIL_OPEN = "<!--GUARDRAIL:"
GUARDRAIL_CLOSE = "-->"


def run(workspace: Path, **kwargs) -> dict:
    """
    Protect non-translatable spans with guardrail markers.

    Mark these with special markers so LLM doesn't translate them:
    - Code blocks
    - Inline code
    - URLs
    - HTML tags
    - Email addresses

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with protection results
    """
    source_path = workspace / "chunks" / "source" / "canonical.md"
    if not source_path.exists():
        return {"status": "failed", "error": "canonical.md not found"}

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    protected_count = 0
    result = content

    # Protect code blocks first (before other patterns)
    result = re.sub(
        r'(```[\s\S]*?```)',
        lambda m: f"{GUARDRAIL_OPEN}code_block{GuardrailCounter.next()}-->{m.group(1)}<--{GUARDRAIL_CLOSE}",
        result
    )

    # Protect inline code
    result = re.sub(
        r'(`[^`]+`)',
        lambda m: f"{GUARDRAIL_OPEN}inline_code{GuardrailCounter.next()}-->{m.group(1)}<--{GUARDRAIL_CLOSE}",
        result
    )

    # Protect URLs
    result = re.sub(
        r'(https?://\S+)',
        lambda m: f"{GUARDRAIL_OPEN}url{GuardrailCounter.next()}-->{m.group(1)}<--{GUARDRAIL_CLOSE}",
        result
    )

    # Protect email addresses
    result = re.sub(
        r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        lambda m: f"{GUARDRAIL_OPEN}email{GuardrailCounter.next()}-->{m.group(1)}<--{GUARDRAIL_CLOSE}",
        result
    )

    # Save (we keep protection markers in source for segmentation)
    # NOTE: markers will be stripped during merge
    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(result)

    protected_count = len(re.findall(GUARDRAIL_OPEN, result))

    return {
        "status": "completed",
        "protected_spans": protected_count,
        "note": "Guardrail markers added. They will be stripped during merge."
    }


class GuardrailCounter:
    """Simple counter for unique guardrail IDs."""
    _counter = 0

    @classmethod
    def next(cls):
        cls._counter += 1
        return cls._counter


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python protect_spans.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)