"""Ingest stage — copy input to workspace."""
import shutil
import hashlib
from pathlib import Path


def run(workspace: Path, **kwargs) -> dict:
    """
    Copy source file to workspace input/ directory.

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with ingestion results
    """
    from translator.state.manifest import Manifest

    manifest = Manifest.load(workspace)
    input_file = Path(manifest.input_path)

    # Copy to workspace
    dest = workspace / "input" / f"original{input_file.suffix}"
    shutil.copy2(input_file, dest)

    # Calculate checksum
    with open(dest, 'rb') as f:
        checksum = hashlib.md5(f.read()).hexdigest()

    return {
        "status": "completed",
        "copied_to": str(dest),
        "checksum": checksum,
        "size": dest.stat().st_size
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)