"""Export check QA — verify all exports were created and are valid."""
import os
from pathlib import Path


EXPORT_FORMATS = ['md', 'txt', 'docx', 'html', 'pdf']


def check_exports(workspace: Path) -> dict:
    """Verify that all declared exports exist and are non-empty."""
    output_dir = workspace / "output"
    results = {}

    for fmt in EXPORT_FORMATS:
        file_path = output_dir / f"translated.{fmt}"
        if file_path.exists():
            size = file_path.stat().st_size
            results[fmt] = {
                "exists": True,
                "size": size,
                "valid": size > 100  # Reasonable minimum size
            }
        else:
            results[fmt] = {
                "exists": False,
                "size": 0,
                "valid": False
            }

    guaranteed = ['md']
    guaranteed_present = all(results[f]["exists"] for f in guaranteed)
    any_success = any(results[f]["valid"] for f in results)

    return {
        "status": "completed",
        "formats": results,
        "guaranteed_present": guaranteed_present,
        "any_valid": any_success
    }


if __name__ == "__main__":
    import sys
    import json
    result = check_exports(Path(sys.argv[1] if len(sys.argv) > 1 else '.'))
    print(json.dumps(result, indent=2))