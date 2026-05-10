# Kanban task_contracts — STUB (NOT IMPLEMENTED IN v0.1)
# Defines the contract that Kanban workers must follow

"""
Task Contract Specification (v0.2+)

Worker files writable:
  - chunks/translated/<chunk_id>.md     — translated chunk
  - chunks/glossary_additions.md        — glossary additions from worker
  - state/worker_status.json            — worker's current status

Orchestrator-only files:
  - state/status.json                   — overall pipeline status
  - state/chunk_index.json              — chunk tracking
  - state/block_index.json              — block tracking
  - output/translated.md                — final merged translation
  - output/translation_report.md        — final report

Worker contract for translation:
  Input:
    - chunks/source/<chunk_id>.md        — source chunk
    - output/glossary.md                — glossary (if exists)
    - output/style_guide.md             — style guide (if exists)
    - state/style_guide.md              — style guide (alternative location)

  Output:
    - chunks/translated/<chunk_id>.md    — translated chunk
    - state/worker_status.json          — status update

  Failure handling:
    - On failure: write error to chunks/translated/<chunk_id>.error
    - Update state/worker_status.json with failed status
    - Do NOT block other workers
"""


class TaskContract:
    """Task contract validator."""

    @staticmethod
    def validate_translation_input(workspace: Path, chunk_id: str) -> bool:
        """Validate that all required inputs exist for translation task."""
        required = [
            workspace / "chunks" / "source" / f"{chunk_id}.md",
        ]
        return all(p.exists() for p in required)

    @staticmethod
    def validate_translation_output(workspace: Path, chunk_id: str) -> bool:
        """Validate that translation output is valid."""
        output = workspace / "chunks" / "translated" / f"{chunk_id}.md"
        return output.exists() and output.stat().st_size > 0

    @staticmethod
    def get_worker_status(workspace: Path) -> dict | None:
        """Read worker status file."""
        status_file = workspace / "state" / "worker_status.json"
        if not status_file.exists():
            return None
        import json
        with open(status_file, 'r') as f:
            return json.load(f)