"""Placeholder and guardrail QA check."""
import re
from pathlib import Path


GUARDRAIL_OPEN_PATTERN = re.compile(r'<!--GUARDRAIL:')
GUARDRAIL_CLOSE_PATTERN = re.compile(r'<--GUARDRAIL_CLOSE-->')


def check_placeholders(md_content: str) -> dict:
    """Check for residual placeholders and guardrails."""
    issues = []

    open_count = len(GUARDRAIL_OPEN_PATTERN.findall(md_content))
    close_count = len(GUARDRAIL_CLOSE_PATTERN.findall(md_content))

    if open_count > 0:
        issues.append({
            "type": "residual_guardrails",
            "count": open_count,
            "message": f"{open_count} guardrail markers still present"
        })

    if open_count != close_count:
        issues.append({
            "type": "mismatched_guardrails",
            "message": f"Guardrail mismatch: {open_count} opens, {close_count} closes"
        })

    # Check for other placeholder patterns
    placeholder_pattern = re.compile(r'\{\{.*?\}\}')
    placeholders = placeholder_pattern.findall(md_content)
    if placeholders:
        issues.append({
            "type": "residual_placeholders",
            "count": len(placeholders),
            "placeholders": placeholders[:5],  # Show first 5
            "message": f"{len(placeholders)} placeholder patterns found"
        })

    return {
        "status": "completed",
        "issues_count": len(issues),
        "issues": issues,
        "clean": len(issues) == 0
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        with open(Path(sys.argv[1]), 'r') as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    result = check_placeholders(content)
    print(result)