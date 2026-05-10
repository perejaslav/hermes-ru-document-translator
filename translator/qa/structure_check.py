"""Structure check QA — compare structure between source and translated."""
import re
from pathlib import Path


def check_structure(source_content: str, translated_content: str) -> dict:
    """Compare structural elements between source and translation."""

    def count_elements(content):
        headers = len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))
        paragraphs = len([p for p in content.split('\n\n') if p.strip()])
        list_items = len(re.findall(r'^[-*]\s+', content, re.MULTILINE))
        code_blocks = len(re.findall(r'```', content))
        links = len(re.findall(r'\[.+\]\(.+\)', content))
        return {
            "headers": headers,
            "paragraphs": paragraphs,
            "list_items": list_items,
            "code_blocks": code_blocks // 2,  # opening and closing
            "links": links
        }

    source_stats = count_elements(source_content)
    trans_stats = count_elements(translated_content)

    # Compare with tolerance
    def compare(key, tolerance=0.2):
        s = source_stats[key]
        t = trans_stats[key]
        if s == 0:
            return True
        ratio = t / s
        return abs(1 - ratio) <= tolerance

    differences = {}
    for key in source_stats:
        if not compare(key):
            differences[key] = {
                "source": source_stats[key],
                "translated": trans_stats[key]
            }

    return {
        "status": "completed",
        "source": source_stats,
        "translated": trans_stats,
        "differences": differences,
        "structure_preserved": len(differences) == 0
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) >= 3:
        with open(Path(sys.argv[1]), 'r') as f:
            source = f.read()
        with open(Path(sys.argv[2]), 'r') as f:
            translated = f.read()
    else:
        print("Usage: python structure_check.py <source.md> <translated.md>")
        sys.exit(1)

    result = check_structure(source, translated)
    print(result)